from __future__ import annotations

from typing import Any, Annotated, Optional, TypedDict


class RetrievalHit(TypedDict, total=False):
    """
    检索命中结果（支持混合检索 + RRF 融合）

    每个命中结果可能包含以下字段：
    - rrf_score: RRF 融合分数（越高越相关）
    - like_rank: LIKE 检索排名（None 表示未命中）
    - vector_rank: 向量检索排名（None 表示未命中）
    - cosine_similarity: 向量相似度（0-1，越高越相似）
    - cosine_distance: 余弦距离（0-2，越小越相似）
    """
    rrf_score: float
    like_rank: Optional[int]
    vector_rank: Optional[int]
    cosine_similarity: Optional[float]
    cosine_distance: Optional[float]


class NL2SQLState(TypedDict, total=False):
    # Input
    question: str
    datasource_id: int  # 可选：指定数据源 ID

    # Derived by analyzer
    keywords: list[str]

    # Spoke outputs（混合检索结果，携带 rrf_score）
    knowledge_hits: list[dict[str, Any]]  # 每个 hit 可能包含 rrf_score
    metrics_hits: list[dict[str, Any]]    # 每个 hit 可能包含 rrf_score
    metadata_hits: list[dict[str, Any]]   # 每个 hit 可能包含 rrf_score

    # Query embedding（用于混合检索）
    query_embedding: list[float]  # 问题的向量（1024 维）

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

    # Token usage tracking
    token_usage: dict[str, int]  # prompt_tokens, completion_tokens, total_tokens

