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

