"""
Schema 描述生成器：基于 XiYan 提示词模板生成中文语义描述。

功能：
1. 数据库整体理解（领域/业务场景）
2. 表描述生成（业务含义、用途）
3. 字段描述生成（业务含义、维度/度量角色）
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .config_service import AIModelConfig
from .llm_provider import create_llm
from .prompt_templates import (
    DB_UNDERSTANDING_PROMPT,
    FIELD_CLASSIFICATION_PROMPT,
    FIELD_DESC_PROMPT,
    TABLE_DESC_PROMPT,
)

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from .schema_engine import FieldInfo, SchemaUnderstanding, TableInfo


class SchemaDescriptor:
    """Schema 语义描述生成器"""

    def __init__(
        self,
        llm_config: AIModelConfig | None = None,
        language: str = "zh",
    ):
        """
        初始化描述生成器

        Args:
            llm_config: LLM 配置
            language: 输出语言（默认中文）
        """
        self.llm: BaseChatModel | None = None
        if llm_config and llm_config.provider != "mock":
            self.llm = create_llm(llm_config)
        self.language = language

    def generate_descriptions(
        self,
        schema: "SchemaUnderstanding",
    ) -> "SchemaUnderstanding":
        """
        生成所有表和字段的中文描述

        Args:
            schema: Schema 理解结果

        Returns:
            更新了描述的 Schema
        """
        if not self.llm:
            # 如果没有 LLM，生成默认描述
            return self._generate_default_descriptions(schema)

        # 1. 先理解数据库整体
        db_context = self._understand_database(schema)

        # 2. 为每张表生成描述
        for table_name, table in schema.tables.items():
            # 生成表描述
            if not table.comment:
                table.comment = self._generate_table_desc(table, db_context)

            # 3. 为每个字段生成描述
            for field_name, field in table.fields.items():
                if not field.comment:
                    field.comment = self._generate_field_desc(table, field, db_context)

        return schema

    def _understand_database(self, schema: "SchemaUnderstanding") -> str:
        """
        理解数据库整体业务领域

        Args:
            schema: Schema 理解结果

        Returns:
            数据库业务上下文描述
        """
        if not self.llm:
            return f"数据库 {schema.db_id} 包含 {len(schema.tables)} 张表"

        # 生成 Schema 概览
        schema_overview = self._generate_schema_overview(schema)

        prompt = DB_UNDERSTANDING_PROMPT.format(
            db_name=schema.db_id,
            tables=", ".join(schema.tables.keys()),
            schema_overview=schema_overview,
        )

        try:
            response = self.llm.invoke(prompt)
            return response.content if hasattr(response, "content") else str(response)
        except Exception:
            return f"数据库 {schema.db_id} 包含 {len(schema.tables)} 张表"

    def _generate_table_desc(
        self,
        table: "TableInfo",
        db_context: str,
    ) -> str:
        """
        生成表描述

        Args:
            table: 表信息
            db_context: 数据库上下文

        Returns:
            表描述
        """
        if not self.llm:
            return self._default_table_desc(table)

        # 构建字段概览
        fields_overview = "\n".join([
            f"- {f.name}: {f.type} ({f.category or '未知'})"
            for f in table.fields.values()
        ])

        prompt = TABLE_DESC_PROMPT.format(
            table_name=table.name,
            fields_overview=fields_overview,
            db_context=db_context,
        )

        try:
            response = self.llm.invoke(prompt)
            return response.content.strip() if hasattr(response, "content") else str(response).strip()
        except Exception:
            return self._default_table_desc(table)

    def _generate_field_desc(
        self,
        table: "TableInfo",
        field: "FieldInfo",
        db_context: str,
    ) -> str:
        """
        生成字段描述

        Args:
            table: 表信息
            field: 字段信息
            db_context: 数据库上下文

        Returns:
            字段描述
        """
        if not self.llm:
            return self._default_field_desc(field)

        prompt = FIELD_DESC_PROMPT.format(
            table_name=table.name,
            field_name=field.name,
            field_type=field.type,
            category=field.category or "未知",
            examples=field.examples[:3] if field.examples else [],
            db_context=db_context,
        )

        try:
            response = self.llm.invoke(prompt)
            return response.content.strip() if hasattr(response, "content") else str(response).strip()
        except Exception:
            return self._default_field_desc(field)

    def classify_string_field_with_llm(
        self,
        field: "FieldInfo",
        examples: list[str],
    ) -> str:
        """
        使用 LLM 分类字符串字段

        Args:
            field: 字段信息
            examples: 示例值

        Returns:
            分类结果（Enum/Code/Text/Measure）
        """
        if not self.llm:
            return "Text"

        prompt = FIELD_CLASSIFICATION_PROMPT.format(
            field_name=field.name,
            field_type=field.type,
            examples=examples[:5] if examples else [],
            comment=field.comment or "无",
        )

        try:
            response = self.llm.invoke(prompt)
            content = response.content.lower() if hasattr(response, "content") else str(response).lower()

            if "枚举" in content or "enum" in content:
                return "Enum"
            elif "编码" in content or "code" in content:
                return "Code"
            elif "度量" in content or "measure" in content:
                return "Measure"

            return "Text"
        except Exception:
            return "Text"

    def _generate_schema_overview(self, schema: "SchemaUnderstanding") -> str:
        """生成 Schema 概览字符串"""
        lines = []
        for table_name, table in schema.tables.items():
            lines.append(f"表 {table_name}:")
            for field_name, field in table.fields.items():
                lines.append(f"  - {field_name}: {field.type}")
        return "\n".join(lines)

    def _generate_default_descriptions(
        self,
        schema: "SchemaUnderstanding",
    ) -> "SchemaUnderstanding":
        """生成默认描述（无 LLM 时使用）"""
        for table_name, table in schema.tables.items():
            if not table.comment:
                table.comment = self._default_table_desc(table)

            for field_name, field in table.fields.items():
                if not field.comment:
                    field.comment = self._default_field_desc(field)

        return schema

    def _default_table_desc(self, table: "TableInfo") -> str:
        """生成默认表描述"""
        pk_str = f"，主键: {', '.join(table.primary_keys)}" if table.primary_keys else ""
        field_count = len(table.fields)
        measure_count = sum(
            1 for f in table.fields.values()
            if f.category == "Measure"
        )

        if measure_count > 0:
            return f"数据表，包含 {field_count} 个字段，其中 {measure_count} 个度量字段{pk_str}"
        else:
            return f"数据表，包含 {field_count} 个字段{pk_str}"

    def _default_field_desc(self, field: "FieldInfo") -> str:
        """生成默认字段描述"""
        desc_parts = [f.name]

        if field.primary_key:
            desc_parts.append("主键")
        if field.category == "DateTime":
            desc_parts.append("时间字段")
            if field.date_min_gran:
                desc_parts.append(f"颗粒度: {field.date_min_gran}")
        elif field.category == "Measure":
            desc_parts.append("度量字段")
        elif field.category == "Enum":
            desc_parts.append("枚举字段")
        elif field.category == "Code":
            desc_parts.append("编码字段")

        return "，".join(desc_parts)

    def generate_knowledge_entries(
        self,
        schema: "SchemaUnderstanding",
    ) -> dict[str, list[dict[str, Any]]]:
        """
        从 Schema 生成知识库条目

        Args:
            schema: Schema 理解结果

        Returns:
            知识库条目，按类型分组
        """
        entries = {
            "enterprise_kb": [],
            "metrics_catalog": [],
            "lake_table_metadata": [],
        }

        for table_name, table in schema.tables.items():
            # 表级知识库条目
            entries["lake_table_metadata"].append({
                "topic": table_name,
                "table_name": table_name,
                "table_comment": table.comment,
                "table_type": table.table_type,
                "primary_keys": table.primary_keys,
                "field_count": len(table.fields),
            })

            for field_name, field in table.fields.items():
                # 术语知识库条目
                if field.category == "Enum" and field.examples:
                    entries["enterprise_kb"].append({
                        "topic": field_name,
                        "keyword_synonyms": ", ".join(str(e) for e in field.examples[:10]),
                        "business_meaning": field.comment or field_name,
                        "table_name": table_name,
                    })
                elif field.comment:
                    entries["enterprise_kb"].append({
                        "topic": field_name,
                        "keyword_synonyms": field_name,
                        "business_meaning": field.comment,
                        "table_name": table_name,
                    })

                # 指标知识库条目
                if field.category == "Measure":
                    entries["metrics_catalog"].append({
                        "metric_name": field_name,
                        "metric_synonyms": field.comment or field_name,
                        "business_definition": field.comment,
                        "aggregation_rule": self._infer_aggregation_rule(field),
                        "table_name": table_name,
                        "column_name": field_name,
                    })

        return entries

    def _infer_aggregation_rule(self, field: "FieldInfo") -> str:
        """推断字段的聚合规则"""
        name_lower = field.name.lower()

        if any(kw in name_lower for kw in ["amount", "price", "cost", "total", "sum", "金额", "价格", "费用", "总计"]):
            return "SUM"
        elif any(kw in name_lower for kw in ["count", "qty", "quantity", "数量"]):
            return "SUM"
        elif any(kw in name_lower for kw in ["rate", "ratio", "percent", "avg", "average", "比率", "占比", "平均"]):
            return "AVG"
        elif any(kw in name_lower for kw in ["max", "min", "最大", "最小"]):
            if "max" in name_lower or "最大" in name_lower:
                return "MAX"
            return "MIN"

        return "SUM"  # 默认求和