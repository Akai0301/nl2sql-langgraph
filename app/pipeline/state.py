from __future__ import annotations

from typing import Any, Annotated, Optional, TypedDict


class NL2SQLState(TypedDict, total=False):
    # Input
    question: str
    datasource_id: int  # 可选：指定数据源 ID

    # Derived by analyzer
    keywords: list[str]

    # Spoke outputs
    knowledge_hits: list[dict[str, Any]]
    metrics_hits: list[dict[str, Any]]
    metadata_hits: list[dict[str, Any]]

    # M-Schema context (Phase 4.1 新增)
    mschema_context: str  # 从 schema_cache 获取的 M-Schema 格式化上下文

    # Semantic context (P2 新增)
    semantic_context: str  # 语义匹配的字段上下文

    # Example SQLs context (P4 新增)
    example_sqls_context: str  # 示例 SQL 上下文

    # Converged by analysis
    candidate_tables: list[str]
    selected_tables: list[str]
    selected_joins: list[dict[str, Any]]

    # SQL generation/execution
    generated_sql: str
    execution_error: str
    result: dict[str, Any]

    # Control
    attempt: int
    max_attempts: int

