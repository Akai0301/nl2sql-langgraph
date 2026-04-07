from __future__ import annotations

import os
import re
from typing import Any

import psycopg
from pydantic import BaseModel, Field

from .prompt_templates import (
    METADATA_ANALYSIS_HUMAN,
    METADATA_ANALYSIS_SYSTEM,
    SQL_GENERATION_EXAMPLE_SECTION,
    SQL_GENERATION_HUMAN,
    SQL_GENERATION_MSCHEMA_SECTION,
    SQL_GENERATION_SEMANTIC_SECTION,
    SQL_GENERATION_SYSTEM,
)
from .state import NL2SQLState
from .tools import (
    execute_sql,
    fetch_knowledge_hits,
    fetch_metadata_hits,
    fetch_metadata_hits_with_cache,
    fetch_metrics_hits,
    get_postgres_dsn,
)


class SQLGenerationOutput(BaseModel):
    sql: str
    selected_tables: list[str] = Field(default_factory=list)
    rationale: str


class MetadataAnalysisOutput(BaseModel):
    selected_tables: list[str]
    selected_joins: list[dict[str, Any]] = Field(default_factory=list)
    rationale: str


def _use_mock_llm() -> bool:
    v = os.getenv("USE_MOCK_LLM", "true").strip().lower()
    return v in {"1", "true", "yes", "y", "on"}


def _get_openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _get_openai_base_url() -> str | None:
    return os.getenv("OPENAI_API_BASE")


def _extract_keywords_via_db(question: str) -> list[str]:
    """
    从企业词表中"匹配问题中出现的同义词"，确保 keywords 与后续检索项对齐。
    """
    dsn = get_postgres_dsn()
    q = question.lower()
    hit_terms: set[str] = set()

    def split_synonyms(s: str) -> list[str]:
        # seed.sql 中用 , 或 | 分隔同义词（示例）
        raw = re.split(r"[,\|;/]+", s)
        return [x.strip().lower() for x in raw if x.strip()]

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            # keyword_synonyms
            cur.execute("SELECT keyword_synonyms FROM enterprise_kb LIMIT 500")
            for (synonyms,) in cur.fetchall():
                for term in split_synonyms(str(synonyms or "")):
                    if term and term in q:
                        hit_terms.add(term)

            # metric_synonyms + metric_name
            cur.execute("SELECT metric_synonyms, metric_name FROM metrics_catalog LIMIT 500")
            for synonyms, metric_name in cur.fetchall():
                for term in split_synonyms(str(synonyms or "")):
                    if term and term in q:
                        hit_terms.add(term)
                if metric_name and str(metric_name).lower() in q:
                    hit_terms.add(str(metric_name).lower())

    # 去除过长"整句"噪声（naive 限制）
    filtered = [t for t in hit_terms if 1 <= len(t) <= 20]
    return sorted(filtered)[:30]


def analyze_question_node(state: NL2SQLState) -> dict[str, Any]:
    question = state["question"].strip()
    max_attempts = int(os.getenv("SQL_MAX_ATTEMPTS", "2"))

    try:
        keywords = _extract_keywords_via_db(question)
    except Exception:
        # 无法连接 DB 时，退化为朴素分词（只为可运行）
        tokens = re.split(r"[\s，。,.!?？;；:：、\(\)\[\]\{\}]+", question)
        keywords = [t.strip().lower() for t in tokens if t.strip()][:10]

    return {
        "keywords": keywords,
        "attempt": int(state.get("attempt", 1)) or 1,
        "max_attempts": max_attempts,
        "execution_error": "",
        "result": {},
    }


def knowledge_retrieval_node(state: NL2SQLState) -> dict[str, Any]:
    return {"knowledge_hits": fetch_knowledge_hits(state.get("keywords", []))}


def metrics_retrieval_node(state: NL2SQLState) -> dict[str, Any]:
    return {"metrics_hits": fetch_metrics_hits(state.get("keywords", []))}


def metadata_retrieval_node(state: NL2SQLState) -> dict[str, Any]:
    """
    元数据检索节点：优先从 schema_cache 获取 M-Schema，回退到 lake_table_metadata。

    Phase 4.1 增强：
    - 如果指定了 datasource_id，优先从 MySQL schema_cache 获取完整的 M-Schema
    - 同时保留 lake_table_metadata 的检索结果（保持兼容）
    - 返回 mschema_context 用于后续 SQL 生成

    P2 增强：
    - 使用语义匹配服务理解问题与字段的关联
    - 返回 semantic_context 用于 LLM Prompt
    """
    metrics_hits = state.get("metrics_hits", []) or []
    metric_names = [m.get("metric_name") for m in metrics_hits if m.get("metric_name")]
    # 用 metric_names 优先，其次才用 keywords 做 topic 推断
    topic_or_metrics = [str(x) for x in metric_names] + [str(k) for k in state.get("keywords", [])]
    datasource_id = state.get("datasource_id")
    question = state.get("question", "")

    # 使用增强的检索函数（带缓存）
    metadata_hits, mschema_context = fetch_metadata_hits_with_cache(
        topic_or_metrics,
        datasource_id=datasource_id,
    )

    # P2: 语义化字段匹配
    semantic_context = ""
    if datasource_id and question:
        from .tools import semantic_field_matching, format_semantic_context
        matched_fields, reasoning = semantic_field_matching(
            question=question,
            datasource_id=datasource_id,
            top_k=10,
        )
        if matched_fields:
            semantic_context = format_semantic_context(matched_fields, reasoning)

    # P4: 获取示例 SQL
    example_sqls_context = ""
    if datasource_id:
        from .tools import fetch_example_sqls, format_example_sqls_context
        example_sqls = fetch_example_sqls(datasource_id)
        if example_sqls:
            example_sqls_context = format_example_sqls_context(example_sqls)

    return {
        "metadata_hits": metadata_hits,
        "mschema_context": mschema_context,
        "semantic_context": semantic_context,
        "example_sqls_context": example_sqls_context,
    }


def merge_context_node(state: NL2SQLState) -> dict[str, Any]:
    metadata_hits = state.get("metadata_hits", []) or []
    candidate_tables = sorted({m.get("fact_table") for m in metadata_hits if m.get("fact_table")})
    return {
        "candidate_tables": candidate_tables,
        # selected_tables/joins 由后续节点决定
    }


def metadata_analysis_node(state: NL2SQLState) -> dict[str, Any]:
    candidate_tables = state.get("candidate_tables", []) or []
    metadata_hits = state.get("metadata_hits", []) or []
    selected_tables = candidate_tables[:]  # 示例：直接全选

    selected_joins: list[dict[str, Any]] = []
    for m in metadata_hits:
        dim_table = m.get("dimension_table")
        if dim_table:
            # seed 示例里 dimension_table 可能为空；这里保留接口以便扩展
            selected_joins.append(
                {
                    "fact_table": m.get("fact_table"),
                    "dimension_table": dim_table,
                    "dimension_join_key": m.get("dimension_join_key"),
                    "dimension_region_key": m.get("dimension_region_key"),
                }
            )

    # 示例实现：选择全部候选表；join 计划基于元数据中的 dimension_* 字段（当前 seed 未提供 dimension，故为空）
    return {
        "selected_tables": selected_tables,
        "selected_joins": selected_joins,
    }


def _mock_sql_generation(state: NL2SQLState) -> SQLGenerationOutput:
    """增强版 Mock SQL 生成，支持多维度、多表关联查询"""
    question = state["question"]
    q = question.lower()
    metadata_hits = state.get("metadata_hits", []) or []
    metrics_hits = state.get("metrics_hits", []) or []

    # ========== 1) 识别指标 ==========
    metric_name = None
    if metrics_hits:
        metric_name = metrics_hits[0].get("metric_name")
    if not metric_name:
        if any(k in q for k in ["利润", "毛利"]):
            metric_name = "利润"
        elif any(k in q for k in ["优惠", "折扣"]):
            metric_name = "优惠金额"
        elif any(k in q for k in ["客单价", "笔单价"]):
            metric_name = "客单价"
        elif any(k in q for k in ["数量", "销量", "件数"]):
            metric_name = "销售数量"
        elif any(k in q for k in ["订单数", "订单数量", "下单数", "单量", "笔数"]):
            metric_name = "订单数"
        elif any(k in q for k in ["金额", "销售额", "gmv", "成交额", "销售", "趋势", "消费"]):
            metric_name = "销售额"
        else:
            metric_name = "销售额"  # 默认指标

    # 指标对应的 SQL 表达式
    metric_expressions = {
        "销售额": "SUM(f.actual_amount)",
        "订单数": "COUNT(f.order_id)",
        "利润": "SUM(f.profit_amount)",
        "优惠金额": "SUM(f.discount_amount)",
        "客单价": "AVG(f.actual_amount)",
        "销售数量": "SUM(f.quantity)",
    }
    measure_expr = metric_expressions.get(metric_name, "SUM(f.actual_amount)")

    # ========== 2) 识别时间范围 ==========
    days = None
    m = re.search(r"(最近|过去|近)\s*(\d+)\s*天", q)
    if m:
        days = int(m.group(2))
    elif "半年" in q or "6个月" in q:
        days = 180
    elif "一年" in q or "全年" in q or "去年" in q:
        days = 365
    elif "本月" in q:
        days = 30
    elif "上周" in q or "近7天" in q or "本周" in q:
        days = 7
    elif any(k in q for k in ["最近", "过去", "近"]):
        days = 30  # 默认30天

    time_filter = None
    if days is not None:
        time_filter = f"f.order_date >= (current_date - interval '{days} days')"

    # ========== 3) 识别分组维度 ==========
    # 需要JOIN的维度表
    join_dims = []
    group_parts = []
    select_parts = []
    order_parts = []
    where_parts = []

    if time_filter:
        where_parts.append(time_filter)

    # 时间分组
    group_by_time = any(k in q for k in ["按月", "分月", "按月份", "月度", "月份", "趋势", "走势", "按季", "季度"])
    if group_by_time:
        if "季" in q:
            select_parts.append("DATE_TRUNC('quarter', f.order_date)::date AS quarter")
            group_parts.append("DATE_TRUNC('quarter', f.order_date)::date")
            order_parts.append("quarter")
        else:
            select_parts.append("DATE_TRUNC('month', f.order_date)::date AS month")
            group_parts.append("DATE_TRUNC('month', f.order_date)::date")
            order_parts.append("month")

    # 地区维度
    group_by_region = any(k in q for k in ["地区", "区域", "大区", "省份", "省", "城市", "市"])
    if group_by_region:
        join_dims.append("dim_region")
        if "大区" in q:
            # 需要关联到父级区域
            select_parts.append("r2.region_name AS region")
            group_parts.append("r2.region_name")
            order_parts.append("region")
        elif "省份" in q or "省" in q:
            select_parts.append("r.province AS province")
            group_parts.append("r.province")
            order_parts.append("province")
        else:
            select_parts.append("r.region_name AS region")
            group_parts.append("r.region_name")
            order_parts.append("region")

    # 产品维度
    group_by_product = any(k in q for k in ["品类", "类目", "产品", "商品", "品牌"])
    if group_by_product:
        join_dims.append("dim_product")
        if "品牌" in q:
            select_parts.append("p.brand AS brand")
            group_parts.append("p.brand")
            order_parts.append("brand")
        elif "品类" in q or "类目" in q:
            select_parts.append("p.category_l1 AS category")
            group_parts.append("p.category_l1")
            order_parts.append("category")

    # 客户维度
    group_by_customer = any(k in q for k in ["会员", "客户", "等级", "vip"])
    if group_by_customer:
        join_dims.append("dim_customer")
        if "等级" in q or "会员" in q:
            select_parts.append("c.member_level AS member_level")
            group_parts.append("c.member_level")
            order_parts.append("member_level")
        else:
            # 默认按客户姓名分组（如"消费前10的客户"）
            select_parts.append("c.customer_name AS customer_name")
            group_parts.append("c.customer_name")
            order_parts.append("customer_name")

    # 渠道维度
    group_by_channel = any(k in q for k in ["渠道", "线上", "线下", "平台", "app", "小程序", "门店"])
    if group_by_channel:
        join_dims.append("dim_channel")
        if "平台" in q or "app" in q or "小程序" in q:
            select_parts.append("ch.platform AS platform")
            group_parts.append("ch.platform")
            order_parts.append("platform")
        else:
            select_parts.append("ch.channel_name AS channel")
            group_parts.append("ch.channel_name")
            order_parts.append("channel")

    # ========== 4) 特殊过滤条件 ==========
    # 产品相关
    if "手机" in q:
        join_dims.append("dim_product")
        where_parts.append("p.category_l2 = '手机'")
        if not group_by_product:
            select_parts.append("p.product_name AS product")
            group_parts.append("p.product_name")
            order_parts.append("product")
    elif "电脑" in q or "笔记本" in q:
        join_dims.append("dim_product")
        where_parts.append("p.category_l2 = '电脑'")
        if not group_by_product:
            select_parts.append("p.product_name AS product")
            group_parts.append("p.product_name")
            order_parts.append("product")

    # 客户等级过滤
    if "钻石" in q:
        join_dims.append("dim_customer")
        where_parts.append("c.member_level = '钻石'")
    elif "金卡" in q:
        join_dims.append("dim_customer")
        where_parts.append("c.member_level = '金卡'")
    elif "银卡" in q:
        join_dims.append("dim_customer")
        where_parts.append("c.member_level = '银卡'")

    # 渠道类型过滤
    if "线上" in q and "渠道" not in q:
        join_dims.append("dim_channel")
        where_parts.append("ch.channel_type = '线上'")
    elif "线下" in q and "渠道" not in q:
        join_dims.append("dim_channel")
        where_parts.append("ch.channel_type = '线下'")

    # ========== 5) 识别 TOP N 需求 ==========
    top_n = None
    m = re.search(r"top\s*(\d+)|前\s*(\d+)|(\d+)\s*大", q)
    if m:
        top_n = int(m.group(1) or m.group(2) or m.group(3))
    if any(k in q for k in ["排名", "排行", "top"]):
        top_n = top_n or 10

    # ========== 6) 构建 SQL ==========
    # 添加度量
    select_parts.append(f"{measure_expr} AS metric_value")

    # FROM 子句
    sql = "SELECT " + ", ".join(select_parts) + "\nFROM fact_orders f"

    # JOIN 子句
    if "dim_region" in join_dims:
        if "大区" in q:
            # 需要二次关联获取大区
            sql += "\nJOIN dim_region r ON f.region_code = r.region_code"
            sql += "\nJOIN dim_region r2 ON r.parent_region_id = r2.region_id"
        else:
            sql += "\nJOIN dim_region r ON f.region_code = r.region_code"
    if "dim_product" in join_dims:
        sql += "\nJOIN dim_product p ON f.product_code = p.product_code"
    if "dim_customer" in join_dims:
        sql += "\nJOIN dim_customer c ON f.customer_id = c.customer_id"
    if "dim_channel" in join_dims:
        sql += "\nJOIN dim_channel ch ON f.channel_id = ch.channel_id"

    # WHERE 子句
    if where_parts:
        sql += "\nWHERE " + " AND ".join(where_parts)

    # GROUP BY 子句
    if group_parts:
        sql += "\nGROUP BY " + ", ".join(group_parts)

    # ORDER BY 子句
    if top_n:
        sql += "\nORDER BY metric_value DESC"
    elif order_parts:
        sql += "\nORDER BY " + ", ".join(order_parts)

    # LIMIT 子句
    max_rows = int(os.getenv("SQL_MAX_ROWS", "200"))
    limit = min(top_n, max_rows) if top_n else max_rows
    sql += f"\nLIMIT {limit}"

    return SQLGenerationOutput(
        sql=sql,
        selected_tables=state.get("selected_tables", []) or state.get("candidate_tables", []),
        rationale=f"Mock 规则生成：指标={metric_name}，维度={join_dims or ['无']}，时间范围={f'{days}天' if days else '全部'}，分组={group_parts or ['无']}。",
    )


def sql_generation_node(state: NL2SQLState) -> dict[str, Any]:
    use_mock = _use_mock_llm()
    keywords = state.get("keywords", [])
    knowledge_hits = state.get("knowledge_hits", []) or []
    metrics_hits = state.get("metrics_hits", []) or []
    metadata_hits = state.get("metadata_hits", []) or []
    candidate_tables = state.get("candidate_tables", []) or []
    selected_tables = state.get("selected_tables", []) or candidate_tables

    # Phase 4.2: 获取 M-Schema 上下文
    mschema_context = state.get("mschema_context", "") or ""

    # P2: 获取语义匹配上下文
    semantic_context = state.get("semantic_context", "") or ""

    # P4: 获取示例 SQL 上下文
    example_sqls_context = state.get("example_sqls_context", "") or ""

    if use_mock:
        out = _mock_sql_generation(state)
        return {"generated_sql": out.sql, "execution_error": "", "selected_tables": out.selected_tables}

    # LLM 路径：使用新的配置服务和提供商适配器
    question = state["question"]
    max_attempts = int(state.get("max_attempts", 2))
    attempt = int(state.get("attempt", 1))

    knowledge_context = "\n".join(
        [f"- topic={h.get('topic')} meaning={h.get('business_meaning')}" for h in knowledge_hits[:5]]
    )
    metrics_context = "\n".join(
        [
            f"- metric_name={m.get('metric_name')} def={m.get('business_definition')} rule={m.get('aggregation_rule')}"
            for m in metrics_hits[:5]
        ]
    )
    metadata_context = "\n".join(
        [
            f"- topic={m.get('topic')} metric={m.get('metric_name')} fact_table={m.get('fact_table')} time_col={m.get('fact_time_column')} region_col={m.get('fact_region_column')} measure={m.get('measure_sql_expression')}"
            for m in metadata_hits[:10]
        ]
    )

    # Phase 4.2: 构建 M-Schema 部分（如果有缓存）
    mschema_section = ""
    if mschema_context:
        mschema_section = SQL_GENERATION_MSCHEMA_SECTION.format(mschema_context=mschema_context)

    # P2: 构建语义匹配部分（如果有匹配结果）
    semantic_section = ""
    if semantic_context:
        semantic_section = SQL_GENERATION_SEMANTIC_SECTION.format(semantic_context=semantic_context)

    # P4: 构建示例 SQL 部分（如果有示例）
    example_sqls_section = ""
    if example_sqls_context:
        example_sqls_section = SQL_GENERATION_EXAMPLE_SECTION.format(example_sqls_context=example_sqls_context)

    system_prompt = SQL_GENERATION_SYSTEM + f"\n当前重试 attempt={attempt}/{max_attempts}。"
    human_prompt = SQL_GENERATION_HUMAN.format(
        question=question,
        keywords=keywords,
        knowledge_context=knowledge_context or "(空)",
        metrics_context=metrics_context or "(空)",
        metadata_context=metadata_context or "(空)",
        mschema_section=mschema_section,
        semantic_section=semantic_section,
        example_sqls_section=example_sqls_section,
        candidate_tables=candidate_tables or [],
    )

    try:
        # 使用新的配置服务和 LLM 提供商适配器
        from .config_service import get_active_ai_config
        from .llm_provider import create_llm

        config = get_active_ai_config()
        llm = create_llm(config)

        if llm is None:
            # Mock 模式（配置返回 None）
            out = _mock_sql_generation(state)
            return {"generated_sql": out.sql, "execution_error": "", "selected_tables": out.selected_tables}

    except ImportError as e:
        raise RuntimeError(
            "LLM 依赖未安装。建议先安装依赖（pip install langchain-openai langchain-anthropic），或保持 USE_MOCK_LLM=true（默认）。"
        ) from e

    structured = llm.with_structured_output(SQLGenerationOutput)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": human_prompt},
    ]

    # Invoke LLM and get structured output
    out = structured.invoke(messages)

    # Extract token usage from response if available
    token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    # Note: structured output may not expose usage_metadata directly
    # Try to get it from the raw response if available
    if hasattr(out, '__pydantic_extra__') and out.__pydantic_extra__:
        usage = out.__pydantic_extra__.get('usage_metadata', {})
        if usage:
            token_usage = {
                "prompt_tokens": usage.get('input_tokens', 0),
                "completion_tokens": usage.get('output_tokens', 0),
                "total_tokens": usage.get('total_tokens', 0),
            }

    return {
        "generated_sql": out.sql,
        "execution_error": "",
        "selected_tables": out.selected_tables,
        "token_usage": token_usage,
    }


def sql_execution_node(state: NL2SQLState) -> dict[str, Any]:
    """
    SQL 执行节点：
    1. P3: 执行前验证 SQL（表名/字段名检查）
    2. 如果有修正建议，使用修正后的 SQL
    3. 执行 SQL 并返回结果
    """
    sql = state.get("generated_sql") or ""
    max_attempts = int(state.get("max_attempts", 2))
    attempt = int(state.get("attempt", 1))
    datasource_id = state.get("datasource_id")

    # P3: SQL 验证（如果有数据源 ID）
    validated_sql = sql
    validation_info = {}
    if datasource_id:
        try:
            from .sql_validator import validate_sql_with_schema, format_validation_result
            validation_result = validate_sql_with_schema(sql, datasource_id)

            if validation_result.corrected_sql:
                # 使用修正后的 SQL
                validated_sql = validation_result.corrected_sql
                validation_info["original_sql"] = sql
                validation_info["corrected_sql"] = validated_sql
                validation_info["corrections"] = validation_result.corrections

            if validation_result.errors:
                validation_info["errors"] = [
                    {"type": e.error_type, "message": e.message, "suggestion": e.suggestion}
                    for e in validation_result.errors
                ]

        except Exception:
            # 验证失败不影响执行，继续使用原始 SQL
            pass

    try:
        result = execute_sql(validated_sql, datasource_id=datasource_id)
        response = {"result": result, "execution_error": ""}
        if validation_info:
            response["validation_info"] = validation_info
        return response
    except Exception as e:
        # 若还没到 max_attempts，则把 attempt 推进到下一轮
        next_attempt = attempt
        if attempt < max_attempts:
            next_attempt = attempt + 1
        return {
            "execution_error": str(e),
            "result": {},
            "attempt": next_attempt,
            "validation_info": validation_info if validation_info else None,
        }
