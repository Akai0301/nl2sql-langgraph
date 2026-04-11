"""
语义字段匹配服务：使用 LLM 理解问题与字段的语义关联。

核心功能：
1. 语义化问题分析：提取意图、指标、维度、时间范围
2. 语义化字段匹配：将问题中的概念映射到具体字段
3. 表选择推理：基于语义相似度选择相关表
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from .config_service import AIModelConfig, get_active_ai_config
from .llm_provider import create_llm


@dataclass
class QuestionAnalysis:
    """问题分析结果"""
    intent: str  # 查询/对比/趋势/排名/统计
    metrics: list[str]  # 提及的指标（如"销售额"、"订单量"）
    dimensions: list[str]  # 提及的维度（如"地区"、"产品"）
    time_range: Optional[str]  # 时间范围（如"最近30天"、"2024年"）
    filters: dict[str, str]  # 过滤条件（如"地区=华东"）
    aggregation: Optional[str]  # 聚合方式（sum/count/avg）
    limit: Optional[int]  # 限制数量（如 top 10）


@dataclass
class FieldMatch:
    """字段匹配结果"""
    table_name: str
    field_name: str
    field_type: str
    comment: Optional[str]
    relevance_score: float  # 0-1 相关性得分
    match_reason: str  # 匹配原因


@dataclass
class SemanticMatchResult:
    """语义匹配结果"""
    analysis: QuestionAnalysis
    matched_fields: list[FieldMatch] = field(default_factory=list)
    selected_tables: list[str] = field(default_factory=list)
    reasoning: str = ""


# 提示词模板
QUESTION_ANALYSIS_PROMPT = """你是一个 NL2SQL 系统的问题分析专家。请分析以下自然语言问题，提取关键信息。

用户问题：{question}

请输出 JSON 格式的分析结果：
```json
{{
  "intent": "查询意图（query/compare/trend/rank/statistics）",
  "metrics": ["提及的指标，如销售额、订单量等"],
  "dimensions": ["提及的维度，如地区、产品、时间等"],
  "time_range": "时间范围描述，如最近30天、2024年Q1",
  "filters": {{"字段名": "值"}，如 {{"地区": "华东"}}},
  "aggregation": "聚合方式（sum/count/avg/max/min）",
  "limit": 数字或 null
}}
```

注意：
- intent 类型说明：query=简单查询, compare=对比分析, trend=趋势分析, rank=排名, statistics=统计
- metrics 是指标名称，通常是数值型概念
- dimensions 是分组维度，通常用于 GROUP BY
- 只输出 JSON，不要输出其他内容"""

FIELD_MATCHING_PROMPT = """你是一个 NL2SQL 系统的字段匹配专家。请根据问题分析结果，从候选字段中选择最相关的字段。

用户问题：{question}

问题分析：
{analysis}

候选字段列表：
{candidate_fields}

请选择最相关的字段，输出 JSON 数组：
```json
[
  {{
    "table_name": "表名",
    "field_name": "字段名",
    "relevance_score": 0.95,
    "match_reason": "匹配原因"
  }}
]
```

选择原则：
1. 优先匹配指标相关的度量字段（如销售额 → order_amount）
2. 其次匹配维度字段（如地区 → region_name）
3. 考虑字段注释与问题关键词的语义相似度
4. relevance_score 在 0-1 之间，越高越相关
5. 只输出最相关的前 10 个字段
6. 只输出 JSON 数组，不要输出其他内容"""

TABLE_SELECTION_PROMPT = """你是一个 NL2SQL 系统的表选择专家。请根据问题分析和字段匹配结果，选择最相关的表。

用户问题：{question}

问题分析：
{analysis}

匹配的字段：
{matched_fields}

候选表列表：
{candidate_tables}

请选择最相关的表，输出 JSON 格式：
```json
{{
  "selected_tables": ["表名1", "表名2"],
  "reasoning": "选择这些表的原因"
}}
```

选择原则：
1. 优先选择包含最多匹配字段的表
2. 考虑表的类型（事实表优先用于指标查询）
3. 考虑表之间的关联关系
4. 避免选择不相关的表"""


class SemanticMatcher:
    """语义匹配服务"""

    def __init__(self, llm_config: AIModelConfig | None = None):
        self.llm_config = llm_config or get_active_ai_config()
        self.llm = create_llm(self.llm_config)

    def analyze_question(self, question: str) -> QuestionAnalysis:
        """
        分析用户问题，提取关键信息

        Args:
            question: 用户问题

        Returns:
            QuestionAnalysis 对象
        """
        prompt = QUESTION_ANALYSIS_PROMPT.format(question=question)

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            # 提取 JSON
            json_str = self._extract_json(content)
            data = json.loads(json_str)

            return QuestionAnalysis(
                intent=data.get("intent", "query"),
                metrics=data.get("metrics", []),
                dimensions=data.get("dimensions", []),
                time_range=data.get("time_range"),
                filters=data.get("filters", {}),
                aggregation=data.get("aggregation"),
                limit=data.get("limit"),
            )
        except Exception:
            # 降级：返回基础分析
            return QuestionAnalysis(
                intent="query",
                metrics=[],
                dimensions=[],
                time_range=None,
                filters={},
                aggregation=None,
                limit=None,
            )

    def match_fields(
        self,
        question: str,
        analysis: QuestionAnalysis,
        candidate_fields: list[dict[str, Any]],
    ) -> list[FieldMatch]:
        """
        语义化字段匹配

        Args:
            question: 用户问题
            analysis: 问题分析结果
            candidate_fields: 候选字段列表

        Returns:
            匹配的字段列表
        """
        if not candidate_fields:
            return []

        # 格式化候选字段
        fields_text = "\n".join([
            f"- {f['table_name']}.{f['field_name']}: {f.get('type', 'unknown')}"
            f" #{f.get('comment', '')} [{f.get('category', '')}]"
            for f in candidate_fields[:50]  # 限制数量
        ])

        prompt = FIELD_MATCHING_PROMPT.format(
            question=question,
            analysis=json.dumps(analysis.__dict__, ensure_ascii=False, indent=2),
            candidate_fields=fields_text,
        )

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            # 提取 JSON
            json_str = self._extract_json(content)
            data = json.loads(json_str)

            matches = []
            for item in data:
                matches.append(FieldMatch(
                    table_name=item.get("table_name", ""),
                    field_name=item.get("field_name", ""),
                    field_type=item.get("field_type", ""),
                    comment=item.get("comment"),
                    relevance_score=float(item.get("relevance_score", 0.5)),
                    match_reason=item.get("match_reason", ""),
                ))

            # 按相关性排序
            matches.sort(key=lambda x: x.relevance_score, reverse=True)
            return matches[:10]

        except Exception:
            return []

    def select_tables(
        self,
        question: str,
        analysis: QuestionAnalysis,
        matched_fields: list[FieldMatch],
        candidate_tables: list[dict[str, Any]],
    ) -> tuple[list[str], str]:
        """
        选择相关表

        Args:
            question: 用户问题
            analysis: 问题分析结果
            matched_fields: 匹配的字段
            candidate_tables: 候选表列表

        Returns:
            (选中的表名列表, 推理过程)
        """
        if not candidate_tables:
            return [], "没有候选表"

        # 格式化匹配字段
        fields_text = "\n".join([
            f"- {f.table_name}.{f.field_name}: {f.match_reason}"
            for f in matched_fields
        ])

        # 格式化候选表
        tables_text = "\n".join([
            f"- {t['name']}: {t.get('comment', '')} [{t.get('table_type', '')}]"
            for t in candidate_tables
        ])

        prompt = TABLE_SELECTION_PROMPT.format(
            question=question,
            analysis=json.dumps(analysis.__dict__, ensure_ascii=False, indent=2),
            matched_fields=fields_text,
            candidate_tables=tables_text,
        )

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)

            # 提取 JSON
            json_str = self._extract_json(content)
            data = json.loads(json_str)

            return (
                data.get("selected_tables", []),
                data.get("reasoning", ""),
            )

        except Exception:
            # 降级：基于匹配字段的表选择
            table_scores: dict[str, int] = {}
            for f in matched_fields:
                table_scores[f.table_name] = table_scores.get(f.table_name, 0) + 1

            sorted_tables = sorted(table_scores.items(), key=lambda x: x[1], reverse=True)
            return [t[0] for t in sorted_tables[:3]], "基于字段匹配数量选择"

    def full_match(
        self,
        question: str,
        schema_fields: list[dict[str, Any]],
        schema_tables: list[dict[str, Any]],
    ) -> SemanticMatchResult:
        """
        完整的语义匹配流程

        Args:
            question: 用户问题
            schema_fields: Schema 字段列表
            schema_tables: Schema 表列表

        Returns:
            SemanticMatchResult 对象
        """
        # Step 1: 分析问题
        analysis = self.analyze_question(question)

        # Step 2: 匹配字段
        matched_fields = self.match_fields(question, analysis, schema_fields)

        # Step 3: 选择表
        selected_tables, reasoning = self.select_tables(
            question, analysis, matched_fields, schema_tables
        )

        return SemanticMatchResult(
            analysis=analysis,
            matched_fields=matched_fields,
            selected_tables=selected_tables,
            reasoning=reasoning,
        )

    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON"""
        import re

        # 尝试匹配 ```json ... ``` 块
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if json_match:
            return json_match.group(1).strip()

        # 尝试匹配直接的对象或数组
        json_match = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", text)
        if json_match:
            return json_match.group(1).strip()

        return "{}"