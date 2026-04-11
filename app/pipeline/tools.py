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
    from app.core.datasource_manager import execute_sql_on_datasource

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
    from app.core.mysql_tools import get_mysql_connection

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
            # 支持两种格式：dict 或 tuple
            if isinstance(fk, dict):
                lines.append(f"- {fk.get('from_table', '')}.{fk.get('from_column', '')} → {fk.get('to_table', '')}.{fk.get('to_column', '')}")
            else:
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


def semantic_field_matching(
    question: str,
    datasource_id: int,
    top_k: int = 10,
) -> tuple[list[dict[str, Any]], str]:
    """
    语义化字段匹配：使用 LLM 理解问题与字段的语义关联。

    这是 P2 优化：替代简单的关键词匹配，用 LLM 理解语义。

    Args:
        question: 用户问题
        datasource_id: 数据源 ID
        top_k: 返回 top K 个最相关字段

    Returns:
        (matched_fields, reasoning)
        - matched_fields: 匹配的字段列表，包含 table_name, field_name, relevance_score
        - reasoning: LLM 推理过程
    """
    # 获取 Schema 缓存
    cache = fetch_schema_cache(datasource_id)
    if not cache or not cache.schema_json:
        return [], "Schema 缓存不存在"

    # 构建候选字段列表
    candidate_fields = []
    for table_name, table_info in cache.schema_json.get("tables", {}).items():
        for field_name, field_info in table_info.get("fields", {}).items():
            candidate_fields.append({
                "table_name": table_name,
                "field_name": field_name,
                "type": field_info.get("type", "unknown"),
                "comment": field_info.get("comment"),
                "category": field_info.get("category"),
                "dim_or_meas": field_info.get("dim_or_meas"),
            })

    if not candidate_fields:
        return [], "没有候选字段"

    # 调用语义匹配服务
    try:
        from app.pipeline.semantic_matcher import SemanticMatcher
        matcher = SemanticMatcher()
        result = matcher.full_match(
            question=question,
            schema_fields=candidate_fields,
            schema_tables=[
                {
                    "name": name,
                    "comment": info.get("comment"),
                    "table_type": info.get("table_type"),
                }
                for name, info in cache.schema_json.get("tables", {}).items()
            ],
        )

        # 转换结果
        matched_fields = [
            {
                "table_name": f.table_name,
                "field_name": f.field_name,
                "type": f.field_type,
                "comment": f.comment,
                "relevance_score": f.relevance_score,
                "match_reason": f.match_reason,
            }
            for f in result.matched_fields[:top_k]
        ]

        return matched_fields, result.reasoning

    except ImportError:
        # 降级：返回空列表
        return [], "语义匹配服务不可用"


def format_semantic_context(
    matched_fields: list[dict[str, Any]],
    reasoning: str,
) -> str:
    """
    格式化语义匹配结果为 LLM Prompt 上下文

    Args:
        matched_fields: 匹配的字段列表
        reasoning: 推理过程

    Returns:
        格式化的上下文字符串
    """
    if not matched_fields:
        return ""

    lines = ["## 语义匹配的字段（LLM 推理）", ""]

    for f in matched_fields:
        lines.append(f"### {f['table_name']}.{f['field_name']}")
        lines.append(f"- 类型: {f.get('type', 'unknown')}")
        if f.get("comment"):
            lines.append(f"- 注释: {f['comment']}")
        lines.append(f"- 相关性: {f.get('relevance_score', 0):.2f}")
        lines.append(f"- 匹配原因: {f.get('match_reason', '')}")
        lines.append("")

    if reasoning:
        lines.append(f"**推理过程**: {reasoning}")

    return "\n".join(lines)


def fetch_example_sqls(datasource_id: int) -> list[dict[str, Any]]:
    """
    获取数据源的示例 SQL

    Args:
        datasource_id: 数据源 ID

    Returns:
        示例 SQL 列表
    """
    from app.core.mysql_tools import get_mysql_connection

    conn = get_mysql_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT example_sqls
            FROM schema_cache
            WHERE datasource_id = %s AND learning_status = 'completed'
        """, (datasource_id,))
        row = cur.fetchone()

        if row and row["example_sqls"]:
            example_sqls = row["example_sqls"]
            if isinstance(example_sqls, str):
                import json
                example_sqls = json.loads(example_sqls)
            return example_sqls

    return []


def format_example_sqls_context(example_sqls: list[dict[str, Any]]) -> str:
    """
    格式化示例 SQL 为 LLM Prompt 上下文

    Args:
        example_sqls: 示例 SQL 列表

    Returns:
        格式化的上下文字符串
    """
    if not example_sqls:
        return ""

    lines = ["## 参考示例 SQL", ""]

    for i, example in enumerate(example_sqls[:5], 1):  # 最多展示 5 个
        lines.append(f"### 示例 {i}: {example.get('question', '')}")
        lines.append("```sql")
        lines.append(example.get("sql", ""))
        lines.append("```")
        if example.get("description"):
            lines.append(f"// {example['description']}")
        lines.append("")

    return "\n".join(lines)


# ============================================
# 混合检索 + RRF 融合（Phase 3 新增）
# ============================================

def reciprocal_rank_fusion(
    like_results: list[dict[str, Any]],
    vector_results: list[dict[str, Any]],
    k: int = 60,
) -> list[dict[str, Any]]:
    """
    RRF 算法融合 LIKE 检索和向量检索结果

    公式: RRF_score(d) = Σ 1/(k + rank_i(d))

    Args:
        like_results: LIKE 检索结果（按匹配顺序）
        vector_results: 向量检索结果（按 cosine_distance 升序）
        k: RRF 参数（默认 60）

    Returns:
        融合结果，包含 rrf_score 字段，按 rrf_score 降序排列
    """
    # 使用字典存储分数和元数据
    rrf_scores: dict[int, dict[str, Any]] = {}

    # LIKE 结果排名（排名越靠前分数越高）
    for rank, item in enumerate(like_results, 1):
        item_id = item.get("id")
        if item_id is None:
            continue

        if item_id not in rrf_scores:
            rrf_scores[item_id] = {
                "item": item.copy(),
                "rrf_score": 0.0,
                "like_rank": rank,
                "vector_rank": None,
                "cosine_distance": None,
            }

        rrf_scores[item_id]["rrf_score"] += 1.0 / (k + rank)
        rrf_scores[item_id]["like_rank"] = rank

    # 向量结果排名
    for rank, item in enumerate(vector_results, 1):
        item_id = item.get("id")
        if item_id is None:
            continue

        cosine_distance = item.get("cosine_distance")

        if item_id not in rrf_scores:
            rrf_scores[item_id] = {
                "item": item.copy(),
                "rrf_score": 0.0,
                "like_rank": None,
                "vector_rank": rank,
                "cosine_distance": cosine_distance,
            }

        rrf_scores[item_id]["rrf_score"] += 1.0 / (k + rank)
        rrf_scores[item_id]["vector_rank"] = rank

        # 更新 cosine_distance（如果之前没有）
        if rrf_scores[item_id]["cosine_distance"] is None:
            rrf_scores[item_id]["cosine_distance"] = cosine_distance

    # 组装结果并计算 cosine_similarity
    fused_results = []
    for item_id, data in rrf_scores.items():
        result = data["item"]
        result["rrf_score"] = round(data["rrf_score"], 6)
        result["like_rank"] = data["like_rank"]
        result["vector_rank"] = data["vector_rank"]
        result["cosine_distance"] = data["cosine_distance"]

        # 计算 cosine_similarity（如果存在 cosine_distance）
        if data["cosine_distance"] is not None:
            result["cosine_similarity"] = round(1.0 - data["cosine_distance"], 6)
        else:
            result["cosine_similarity"] = None

        # 标记检索来源方式
        like_rank = data["like_rank"]
        vector_rank = data["vector_rank"]
        if like_rank is not None and vector_rank is not None:
            result["_retrieval_method"] = "hybrid"  # LIKE + 向量融合
        elif like_rank is not None:
            result["_retrieval_method"] = "like_only"  # 仅 LIKE
        else:
            result["_retrieval_method"] = "vector_only"  # 仅向量

        fused_results.append(result)

    # 按 rrf_score 降序排列
    fused_results.sort(key=lambda x: x["rrf_score"], reverse=True)

    return fused_results


def vector_search(
    table: str,
    query_embedding: list[float],
    embedding_column: str,
    select_columns: list[str],
    top_k: int = 20,
) -> list[dict[str, Any]]:
    """
    PostgreSQL 向量检索（pgvector）

    使用余弦距离: embedding <=> query_vector
    返回 cosine_distance（越小越相似）

    Args:
        table: 表名
        query_embedding: 查询向量（1024 维）
        embedding_column: embedding 字段名
        select_columns: 返回字段列表
        top_k: 返回数量

    Returns:
        检索结果，包含 cosine_distance 字段
    """
    dsn = get_postgres_dsn()

    # 格式化向量
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    # 构建向量检索 SQL
    sql = f"""
        SELECT {", ".join(select_columns)},
               {embedding_column} <=> '{embedding_str}'::vector AS cosine_distance
        FROM {table}
        WHERE {embedding_column} IS NOT NULL
        ORDER BY cosine_distance ASC
        LIMIT {top_k}
    """

    with psycopg.connect(dsn) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(sql)
            results = cur.fetchall()

            # 计算 cosine_similarity
            for r in results:
                if r.get("cosine_distance") is not None:
                    r["cosine_similarity"] = 1.0 - r["cosine_distance"]

            return results


def hybrid_knowledge_search(
    keywords: list[str],
    query_embedding: list[float],
    top_k: int = 20,
    rrf_k: int = 60,
) -> list[dict[str, Any]]:
    """
    企业知识库混合检索：LIKE + 向量并行，RRF 融合

    Args:
        keywords: LIKE 搜索关键词列表
        query_embedding: 查询向量
        top_k: 各路检索数量
        rrf_k: RRF 参数

    Returns:
        融合结果，包含 rrf_score、like_rank、vector_rank、cosine_similarity
    """
    dsn = get_postgres_dsn()
    select_columns = ["id", "topic", "keyword_synonyms", "business_meaning", "example_question", "example_sql_template"]

    # 1. LIKE 检索（原有逻辑）
    like_results = []
    if keywords:
        terms = [k.strip().lower() for k in keywords if k.strip()]
        patterns = [f"%{t}%" for t in terms]
        sql = """
            SELECT {0}
            FROM enterprise_kb
            WHERE lower(keyword_synonyms) LIKE ANY (%s)
               OR lower(business_meaning) LIKE ANY (%s)
            ORDER BY id
            LIMIT {1}
        """.format(", ".join(select_columns), top_k)

        with psycopg.connect(dsn) as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(sql, (patterns, patterns))
                like_results = cur.fetchall()

    # 2. 向量检索（多 embedding 字段：keyword_embedding + business_embedding）
    vector_results = []

    # 检索 keyword_embedding
    keyword_hits = vector_search(
        table="enterprise_kb",
        query_embedding=query_embedding,
        embedding_column="keyword_embedding",
        select_columns=select_columns,
        top_k=top_k,
    )
    vector_results.extend(keyword_hits)

    # 检索 business_embedding
    business_hits = vector_search(
        table="enterprise_kb",
        query_embedding=query_embedding,
        embedding_column="business_embedding",
        select_columns=select_columns,
        top_k=top_k,
    )
    vector_results.extend(business_hits)

    # 去重（按 id）
    seen_ids: set[int] = set()
    unique_vector_results: list[dict[str, Any]] = []
    for item in vector_results:
        item_id = item.get("id")
        if item_id not in seen_ids:
            seen_ids.add(item_id)
            unique_vector_results.append(item)
        else:
            # 如果已存在，更新为更小的 cosine_distance
            for existing in unique_vector_results:
                if existing.get("id") == item_id:
                    if item.get("cosine_distance") is not None and existing.get("cosine_distance") is not None:
                        if item["cosine_distance"] < existing["cosine_distance"]:
                            existing["cosine_distance"] = item["cosine_distance"]
                    break

    # 按 cosine_distance 重新排序
    unique_vector_results.sort(
        key=lambda x: x.get("cosine_distance", 1.0) if x.get("cosine_distance") is not None else 1.0
    )
    unique_vector_results = unique_vector_results[:top_k]

    # 3. RRF 融合
    fused_results = reciprocal_rank_fusion(like_results, unique_vector_results, rrf_k)

    return fused_results[:top_k]


def hybrid_metrics_search(
    keywords: list[str],
    query_embedding: list[float],
    top_k: int = 20,
    rrf_k: int = 60,
) -> list[dict[str, Any]]:
    """
    指标目录混合检索：LIKE + 向量并行，RRF 融合

    Args:
        keywords: LIKE 搜索关键词列表
        query_embedding: 查询向量
        top_k: 各路检索数量
        rrf_k: RRF 参数

    Returns:
        融合结果，包含 rrf_score、like_rank、vector_rank、cosine_similarity
    """
    dsn = get_postgres_dsn()
    select_columns = ["id", "metric_name", "metric_synonyms", "business_definition", "aggregation_rule", "target_column"]

    # 1. LIKE 检索
    like_results = []
    if keywords:
        terms = [k.strip().lower() for k in keywords if k.strip()]
        patterns = [f"%{t}%" for t in terms]
        sql = """
            SELECT {0}
            FROM metrics_catalog
            WHERE lower(metric_synonyms) LIKE ANY (%s)
               OR lower(metric_name) LIKE ANY (%s)
            ORDER BY id
            LIMIT {1}
        """.format(", ".join(select_columns), top_k)

        with psycopg.connect(dsn) as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(sql, (patterns, patterns))
                like_results = cur.fetchall()

    # 2. 向量检索（metric_embedding + synonym_embedding）
    vector_results = []

    metric_hits = vector_search(
        table="metrics_catalog",
        query_embedding=query_embedding,
        embedding_column="metric_embedding",
        select_columns=select_columns,
        top_k=top_k,
    )
    vector_results.extend(metric_hits)

    synonym_hits = vector_search(
        table="metrics_catalog",
        query_embedding=query_embedding,
        embedding_column="synonym_embedding",
        select_columns=select_columns,
        top_k=top_k,
    )
    vector_results.extend(synonym_hits)

    # 去重
    seen_ids: set[int] = set()
    unique_vector_results: list[dict[str, Any]] = []
    for item in vector_results:
        item_id = item.get("id")
        if item_id not in seen_ids:
            seen_ids.add(item_id)
            unique_vector_results.append(item)

    unique_vector_results.sort(
        key=lambda x: x.get("cosine_distance", 1.0) if x.get("cosine_distance") is not None else 1.0
    )
    unique_vector_results = unique_vector_results[:top_k]

    # 3. RRF 融合
    fused_results = reciprocal_rank_fusion(like_results, unique_vector_results, rrf_k)

    return fused_results[:top_k]


def hybrid_metadata_search(
    topics_or_metrics: list[str],
    query_embedding: list[float],
    top_k: int = 30,
    rrf_k: int = 60,
) -> list[dict[str, Any]]:
    """
    元数据混合检索：LIKE + 向量并行，RRF 融合

    Args:
        topics_or_metrics: LIKE 搜索的主题或指标列表
        query_embedding: 查询向量
        top_k: 各路检索数量
        rrf_k: RRF 参数

    Returns:
        融合结果，包含 rrf_score、like_rank、vector_rank、cosine_similarity
    """
    dsn = get_postgres_dsn()
    select_columns = [
        "id", "topic", "metric_name",
        "fact_table", "fact_time_column", "fact_region_column",
        "dimension_table", "dimension_join_key", "dimension_region_key",
        "measure_column", "measure_sql_expression", "grain"
    ]

    # 1. LIKE 检索
    like_results = []
    if topics_or_metrics:
        terms = [t.strip().lower() for t in topics_or_metrics if t.strip()]
        patterns = [f"%{t}%" for t in terms]
        sql = """
            SELECT {0}
            FROM lake_table_metadata
            WHERE lower(topic) LIKE ANY (%s)
               OR lower(metric_name) LIKE ANY (%s)
            ORDER BY id
            LIMIT {1}
        """.format(", ".join(select_columns), top_k)

        with psycopg.connect(dsn) as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(sql, (patterns, patterns))
                like_results = cur.fetchall()

    # 2. 向量检索（topic_embedding + metric_embedding）
    vector_results = []

    topic_hits = vector_search(
        table="lake_table_metadata",
        query_embedding=query_embedding,
        embedding_column="topic_embedding",
        select_columns=select_columns,
        top_k=top_k,
    )
    vector_results.extend(topic_hits)

    metric_hits = vector_search(
        table="lake_table_metadata",
        query_embedding=query_embedding,
        embedding_column="metric_embedding",
        select_columns=select_columns,
        top_k=top_k,
    )
    vector_results.extend(metric_hits)

    # 去重
    seen_ids: set[int] = set()
    unique_vector_results: list[dict[str, Any]] = []
    for item in vector_results:
        item_id = item.get("id")
        if item_id not in seen_ids:
            seen_ids.add(item_id)
            unique_vector_results.append(item)

    unique_vector_results.sort(
        key=lambda x: x.get("cosine_distance", 1.0) if x.get("cosine_distance") is not None else 1.0
    )
    unique_vector_results = unique_vector_results[:top_k]

    # 3. RRF 融合
    fused_results = reciprocal_rank_fusion(like_results, unique_vector_results, rrf_k)

    return fused_results[:top_k]


async def hybrid_search_all(
    keywords: list[str],
    question: str,
    top_k: int = 20,
    rrf_k: int = 60,
) -> dict[str, list[dict[str, Any]]]:
    """
    全量混合检索：并行检索知识库、指标、元数据

    生成问题向量后，并行执行三路混合检索

    Args:
        keywords: 关键词列表（用于 LIKE 检索）
        question: 用户问题（用于生成向量）
        top_k: 各路检索数量
        rrf_k: RRF 参数

    Returns:
        {
            "knowledge_hits": [...],
            "metrics_hits": [...],
            "metadata_hits": [...]
        }
        每个结果包含 rrf_score
    """
    from app.core.embedding_service import embed_query

    # 生成查询向量
    query_embedding = await embed_query(question)

    # 并行检索（这里用同步函数，实际可在 LangGraph 节点中异步调用）
    knowledge_hits = hybrid_knowledge_search(keywords, query_embedding, top_k, rrf_k)
    metrics_hits = hybrid_metrics_search(keywords, query_embedding, top_k, rrf_k)

    # 元数据检索使用 metrics_hits 的 metric_name 作为输入
    metric_names = [h.get("metric_name") for h in metrics_hits if h.get("metric_name")]
    metadata_hits = hybrid_metadata_search(
        topics_or_metrics=keywords + metric_names,
        query_embedding=query_embedding,
        top_k=30,
        rrf_k=rrf_k,
    )

    return {
        "knowledge_hits": knowledge_hits,
        "metrics_hits": metrics_hits,
        "metadata_hits": metadata_hits,
    }

