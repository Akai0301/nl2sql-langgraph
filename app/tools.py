from __future__ import annotations

import json
import re
import os
from dataclasses import dataclass
from typing import Any

import psycopg


def _get_env(name: str, default: str | None = None) -> str:
    v = os.getenv(name, default)
    if v is None or v == "":
        raise RuntimeError(f"缺少环境变量：{name}")
    return v


def get_postgres_dsn() -> str:
    return _get_env("POSTGRES_DSN")


def safe_sql_validate(sql: str, sql_max_rows: int) -> tuple[str, str | None]:
    """
    轻量安全校验：
    - 只允许 SELECT
    - 禁止多语句（出现 ; 就拒绝）
    - 自动确保含 LIMIT（若原 SQL 没有 LIMIT，则附加 LIMIT）
    """
    s = sql.strip().rstrip(";")
    lowered = s.lower()
    if ";" in s:
        raise ValueError("SQL 不允许多语句（包含 ';'）")
    if not lowered.startswith("select"):
        raise ValueError("仅允许 SELECT 语句")

    # 如果没有 LIMIT，就加一个最大行数
    # 用正则判断是否包含 LIMIT，避免依赖空格/换行
    if not re.search(r"\blimit\b", lowered):
        s = f"{s} LIMIT {int(sql_max_rows)}"
        return s, "未检测到 LIMIT，已自动补充"

    return s, None


def execute_sql(sql: str, datasource_id: int | None = None) -> dict[str, Any]:
    """
    使用确定性的数据库直连 SELECT 执行。
    返回 columns/rows，方便前端稳定渲染。

    支持多数据源：如果指定 datasource_id，则使用该数据源；
    否则使用当前激活的问数数据源。
    """
    max_rows = int(os.getenv("SQL_MAX_ROWS", "200"))
    validated_sql, _ = safe_sql_validate(sql, max_rows)

    # 使用数据源管理器执行 SQL
    from .datasource_manager import execute_sql_on_datasource

    return execute_sql_on_datasource(validated_sql, ds_id=datasource_id, max_rows=max_rows)


def fetch_knowledge_hits(keywords: list[str]) -> list[dict[str, Any]]:
    """
    企业知识黑话/标准示例 Q&A 检索（示例实现：表驱动 + naive match）。
    """
    dsn = get_postgres_dsn()
    if not keywords:
        return []
    terms = [k.strip().lower() for k in keywords if k.strip()]

    patterns = [f"%{t}%" for t in terms]
    sql = """
    SELECT id, topic, business_meaning, example_question, example_sql_template
    FROM enterprise_kb
    WHERE lower(keyword_synonyms) LIKE ANY (%s)
    ORDER BY id
    LIMIT 20
    """
    with psycopg.connect(dsn) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(sql, (patterns,))
            return cur.fetchall()  # type: ignore[no-any-return]


def fetch_metrics_hits(keywords: list[str]) -> list[dict[str, Any]]:
    """
    指标检索（示例实现：表驱动 + naive match）。
    """
    dsn = get_postgres_dsn()
    if not keywords:
        return []
    terms = [k.strip().lower() for k in keywords if k.strip()]
    patterns = [f"%{t}%" for t in terms]
    sql = """
    SELECT id, metric_name, metric_synonyms, business_definition, aggregation_rule, target_column
    FROM metrics_catalog
    WHERE lower(metric_synonyms) LIKE ANY (%s) OR lower(metric_name) LIKE ANY (%s)
    ORDER BY id
    LIMIT 20
    """
    with psycopg.connect(dsn) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(sql, (patterns, patterns))
            return cur.fetchall()  # type: ignore[no-any-return]


def fetch_metadata_hits(topic_or_metrics: list[str]) -> list[dict[str, Any]]:
    """
    从数据湖/元数据表返回业务元数据（示例实现：直接查 lake_table_metadata）。
    topic_or_metrics 可以来自 metrics_hits.metric_name 或 keywords 命中的 topic。
    """
    dsn = get_postgres_dsn()
    if not topic_or_metrics:
        return []
    terms = [t.strip().lower() for t in topic_or_metrics if t.strip()]
    patterns = [f"%{t}%" for t in terms]
    sql = """
    SELECT id,
           topic,
           metric_name,
           fact_table,
           fact_time_column,
           fact_region_column,
           dimension_table,
           dimension_join_key,
           dimension_region_key,
           measure_column,
           measure_sql_expression,
           grain
    FROM lake_table_metadata
    WHERE lower(topic) LIKE ANY (%s) OR lower(metric_name) LIKE ANY (%s)
    ORDER BY id
    LIMIT 50
    """
    with psycopg.connect(dsn) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(sql, (patterns, patterns))
            return cur.fetchall()  # type: ignore[no-any-return]


# ============================================
# Schema Cache 相关函数（Phase 4.1 新增）
# ============================================

@dataclass
class SchemaCacheResult:
    """Schema 缓存结果"""
    id: int
    datasource_id: int
    schema_json: dict[str, Any]
    mschema_text: str
    table_count: int
    field_count: int
    learned_at: str | None


def fetch_schema_cache(datasource_id: int) -> SchemaCacheResult | None:
    """
    从 MySQL schema_cache 表获取数据源的 Schema 缓存。

    Args:
        datasource_id: 数据源 ID

    Returns:
        Schema 缓存结果，如果不存在则返回 None
    """
    from .mysql_tools import get_mysql_connection

    conn = get_mysql_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, datasource_id, schema_json, mschema_text, table_count, field_count, learned_at
            FROM schema_cache
            WHERE datasource_id = %s AND learning_status = 'completed'
        """, (datasource_id,))
        row = cur.fetchone()

        if row:
            return SchemaCacheResult(
                id=row["id"],
                datasource_id=row["datasource_id"],
                schema_json=json.loads(row["schema_json"]) if isinstance(row["schema_json"], str) else row["schema_json"],
                mschema_text=row["mschema_text"] or "",
                table_count=row["table_count"],
                field_count=row["field_count"],
                learned_at=row["learned_at"].isoformat() if row["learned_at"] else None,
            )

    return None


def fetch_table_schema_from_cache(datasource_id: int, table_name: str) -> dict[str, Any] | None:
    """
    从 Schema 缓存中获取单表的详细 Schema。

    Args:
        datasource_id: 数据源 ID
        table_name: 表名

    Returns:
        单表 Schema 信息，如果不存在则返回 None
    """
    cache = fetch_schema_cache(datasource_id)
    if not cache or not cache.schema_json:
        return None

    tables = cache.schema_json.get("tables", {})
    return tables.get(table_name)


def format_mschema_context(
    schema_cache: SchemaCacheResult | None,
    keywords: list[str],
    max_tables: int = 10,
) -> str:
    """
    格式化 M-Schema 上下文，用于 LLM Prompt。

    优先从 schema_cache 获取完整的 M-Schema 信息，
    如果没有缓存则返回空字符串（后续节点会回退到 lake_table_metadata）。

    Args:
        schema_cache: Schema 缓存结果
        keywords: 关键词列表（用于筛选相关表）
        max_tables: 最大返回表数

    Returns:
        格式化的 M-Schema 文本
    """
    if not schema_cache or not schema_cache.schema_json:
        return ""

    schema_json = schema_cache.schema_json
    tables = schema_json.get("tables", {})

    if not tables:
        return ""

    # 关键词匹配筛选表
    keywords_lower = [k.lower() for k in keywords]
    matched_tables: dict[str, Any] = {}

    for table_name, table_info in tables.items():
        # 检查表名是否匹配关键词
        table_name_lower = table_name.lower()
        table_comment = (table_info.get("comment") or "").lower()

        # 检查字段名和注释是否匹配关键词
        field_matches = []
        fields = table_info.get("fields", {})
        for field_name, field_info in fields.items():
            field_name_lower = field_name.lower()
            field_comment = (field_info.get("comment") or "").lower()

            for kw in keywords_lower:
                if kw in field_name_lower or kw in field_comment:
                    field_matches.append(field_name)
                    break

        # 如果表名、表注释或字段匹配，则包含该表
        is_matched = False
        for kw in keywords_lower:
            if kw in table_name_lower or kw in table_comment:
                is_matched = True
                break

        if is_matched or field_matches:
            matched_tables[table_name] = table_info

    # 如果没有匹配的表，返回所有表（限制数量）
    if not matched_tables:
        matched_tables = dict(list(tables.items())[:max_tables])

    # 构建格式化文本
    lines = []
    lines.append("## 数据库 Schema（M-Schema 格式）\n")

    for table_name, table_info in list(matched_tables.items())[:max_tables]:
        table_comment = table_info.get("comment", "")
        table_type = table_info.get("table_type", "other")
        primary_keys = table_info.get("primary_keys", [])
        fields = table_info.get("fields", {})

        lines.append(f"### 表: {table_name}")
        if table_comment:
            lines.append(f"- 注释: {table_comment}")
        if table_type != "other":
            lines.append(f"- 类型: {table_type}")
        if primary_keys:
            lines.append(f"- 主键: {', '.join(primary_keys)}")

        lines.append("- 字段:")
        for field_name, field_info in fields.items():
            field_type = field_info.get("type", "unknown")
            field_comment = field_info.get("comment", "")
            field_category = field_info.get("category", "")
            dim_or_meas = field_info.get("dim_or_meas", "")
            is_pk = " [主键]" if field_info.get("primary_key") else ""

            line = f"  - {field_name}: {field_type}{is_pk}"
            if field_comment:
                line += f" # {field_comment}"
            if field_category and field_category != "Text":
                line += f" [{field_category}]"
            if dim_or_meas and dim_or_meas != "Dimension":
                line += f" ({dim_or_meas})"
            lines.append(line)

        lines.append("")  # 空行分隔

    # 添加外键信息
    foreign_keys = schema_json.get("foreign_keys", [])
    if foreign_keys:
        lines.append("### 外键关系:")
        for fk in foreign_keys:
            lines.append(f"- {fk[0]}.{fk[1]} → {fk[2]}.{fk[3]}")
        lines.append("")

    return "\n".join(lines)


def fetch_metadata_hits_with_cache(
    topic_or_metrics: list[str],
    datasource_id: int | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """
    增强的元数据检索：优先从 Schema 缓存获取，回退到 lake_table_metadata。

    Args:
        topic_or_metrics: 主题或指标名称列表
        datasource_id: 数据源 ID（可选）

    Returns:
        (metadata_hits, mschema_context)
        - metadata_hits: 从 lake_table_metadata 检索的原始结果（保持兼容）
        - mschema_context: 从 schema_cache 生成的 M-Schema 格式上下文
    """
    # 1. 始终从 lake_table_metadata 获取基础结果（保持兼容）
    metadata_hits = fetch_metadata_hits(topic_or_metrics)

    # 2. 如果有数据源 ID，尝试从 schema_cache 获取增强上下文
    mschema_context = ""
    if datasource_id:
        cache = fetch_schema_cache(datasource_id)
        if cache:
            mschema_context = format_mschema_context(cache, topic_or_metrics)

    return metadata_hits, mschema_context

