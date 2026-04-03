"""
知识库管理器：管理业务术语、示例 Q&A、指标口径、表说明等知识。
支持按数据源隔离知识库。
"""
from __future__ import annotations

import json
from typing import Any, Optional

from .config_service import KnowledgeConfig
from .mysql_tools import get_mysql_connection


# ============ 知识 CRUD 操作 ============

def create_knowledge(
    datasource_id: int,
    kb_type: str,
    kb_name: str,
    kb_content: Optional[str] = None,
    kb_metadata: Optional[dict[str, Any]] = None,
    is_active: bool = True,
) -> dict[str, Any]:
    """创建知识项"""
    conn = get_mysql_connection()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO knowledge_config
            (datasource_id, kb_type, kb_name, kb_content, kb_metadata, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            datasource_id,
            kb_type,
            kb_name,
            kb_content,
            json.dumps(kb_metadata or {}, ensure_ascii=False),
            1 if is_active else 0,
        ))
        conn.commit()

        knowledge_id = cur.lastrowid
        return {
            "id": knowledge_id,
            "datasource_id": datasource_id,
            "kb_type": kb_type,
            "kb_name": kb_name,
            "kb_content": kb_content,
            "kb_metadata": kb_metadata or {},
            "is_active": is_active,
        }


def get_knowledge_by_id(knowledge_id: int) -> Optional[dict[str, Any]]:
    """根据 ID 获取知识项"""
    conn = get_mysql_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, datasource_id, kb_type, kb_name, kb_content, kb_metadata, is_active,
                   created_at, updated_at
            FROM knowledge_config
            WHERE id = %s
        """, (knowledge_id,))
        row = cur.fetchone()
        if row:
            return _row_to_knowledge(row)
    return None


def list_knowledge(
    datasource_id: Optional[int] = None,
    kb_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    """
    列出知识项

    Args:
        datasource_id: 数据源 ID 筛选
        kb_type: 知识类型筛选（term/qa/metric/table_desc）
        is_active: 是否启用筛选
        page: 页码
        page_size: 每页数量

    Returns:
        {"items": [...], "total": int, "page": int, "page_size": int}
    """
    conn = get_mysql_connection()

    # 构建查询条件
    conditions = []
    params = []

    if datasource_id is not None:
        conditions.append("datasource_id = %s")
        params.append(datasource_id)

    if kb_type:
        conditions.append("kb_type = %s")
        params.append(kb_type)

    if is_active is not None:
        conditions.append("is_active = %s")
        params.append(1 if is_active else 0)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # 查询总数
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM knowledge_config WHERE {where_clause}", params)
        total = cur.fetchone()["COUNT(*)"]

        # 查询列表
        offset = (page - 1) * page_size
        cur.execute(f"""
            SELECT id, datasource_id, kb_type, kb_name, kb_content, kb_metadata, is_active,
                   created_at, updated_at
            FROM knowledge_config
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, params + [page_size, offset])

        rows = cur.fetchall()
        items = [_row_to_knowledge(row) for row in rows]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


def update_knowledge(
    knowledge_id: int,
    kb_name: Optional[str] = None,
    kb_content: Optional[str] = None,
    kb_metadata: Optional[dict[str, Any]] = None,
    is_active: Optional[bool] = None,
) -> Optional[dict[str, Any]]:
    """更新知识项"""
    conn = get_mysql_connection()

    updates = []
    params = []

    if kb_name is not None:
        updates.append("kb_name = %s")
        params.append(kb_name)

    if kb_content is not None:
        updates.append("kb_content = %s")
        params.append(kb_content)

    if kb_metadata is not None:
        updates.append("kb_metadata = %s")
        params.append(json.dumps(kb_metadata, ensure_ascii=False))

    if is_active is not None:
        updates.append("is_active = %s")
        params.append(1 if is_active else 0)

    if not updates:
        return get_knowledge_by_id(knowledge_id)

    params.append(knowledge_id)

    with conn.cursor() as cur:
        cur.execute(f"""
            UPDATE knowledge_config
            SET {", ".join(updates)}
            WHERE id = %s
        """, params)
        conn.commit()

    return get_knowledge_by_id(knowledge_id)


def delete_knowledge(knowledge_id: int) -> bool:
    """删除知识项"""
    conn = get_mysql_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM knowledge_config WHERE id = %s", (knowledge_id,))
        conn.commit()
        return cur.rowcount > 0


def batch_import_knowledge(
    datasource_id: int,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    批量导入知识

    Args:
        datasource_id: 数据源 ID
        items: 知识项列表，每项包含 kb_type, kb_name, kb_content, kb_metadata

    Returns:
        {"success": int, "failed": int, "total": int}
    """
    success = 0
    failed = 0

    conn = get_mysql_connection()
    with conn.cursor() as cur:
        for item in items:
            try:
                cur.execute("""
                    INSERT INTO knowledge_config
                    (datasource_id, kb_type, kb_name, kb_content, kb_metadata, is_active)
                    VALUES (%s, %s, %s, %s, %s, 1)
                """, (
                    datasource_id,
                    item.get("kb_type", "term"),
                    item.get("kb_name", ""),
                    item.get("kb_content"),
                    json.dumps(item.get("kb_metadata", {}), ensure_ascii=False),
                ))
                success += 1
            except Exception:
                failed += 1

        conn.commit()

    return {
        "success": success,
        "failed": failed,
        "total": len(items),
    }


# ============ 知识检索 ============

def fetch_knowledge_for_datasource(
    datasource_id: int,
    keywords: list[str],
    kb_types: Optional[list[str]] = None,
) -> dict[str, list[dict[str, Any]]]:
    """
    根据关键词检索数据源的知识

    Args:
        datasource_id: 数据源 ID
        keywords: 关键词列表
        kb_types: 知识类型列表（可选）

    Returns:
        {"terms": [...], "qa": [...], "metrics": [...], "table_desc": [...]}
    """
    result = {
        "terms": [],
        "qa": [],
        "metrics": [],
        "table_desc": [],
    }

    if not keywords:
        return result

    conn = get_mysql_connection()
    with conn.cursor() as cur:
        # 构建关键词搜索条件
        keyword_conditions = " OR ".join(["kb_name LIKE %s"] * len(keywords))
        keyword_conditions += " OR " + " OR ".join(["kb_content LIKE %s"] * len(keywords))

        # 类型筛选
        type_condition = ""
        params = []

        if kb_types:
            placeholders = ", ".join(["%s"] * len(kb_types))
            type_condition = f"AND kb_type IN ({placeholders})"
            params = kb_types[:]

        # 构建完整参数
        like_params = [f"%{kw}%" for kw in keywords] * 2  # name 和 content 各一次

        cur.execute(f"""
            SELECT id, datasource_id, kb_type, kb_name, kb_content, kb_metadata, is_active
            FROM knowledge_config
            WHERE datasource_id = %s AND is_active = 1
                  {type_condition}
                  AND ({keyword_conditions})
            LIMIT 100
        """, [datasource_id] + params + like_params)

        rows = cur.fetchall()

        for row in rows:
            kb_type = row["kb_type"]
            item = _row_to_knowledge(row)

            if kb_type == "term" and "terms" in result:
                result["terms"].append(item)
            elif kb_type == "qa" and "qa" in result:
                result["qa"].append(item)
            elif kb_type == "metric" and "metrics" in result:
                result["metrics"].append(item)
            elif kb_type == "table_desc" and "table_desc" in result:
                result["table_desc"].append(item)

    return result


def get_all_active_knowledge_for_datasource(
    datasource_id: int,
) -> list[dict[str, Any]]:
    """获取数据源的所有激活知识（用于上下文构建）"""
    conn = get_mysql_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, datasource_id, kb_type, kb_name, kb_content, kb_metadata, is_active
            FROM knowledge_config
            WHERE datasource_id = %s AND is_active = 1
            ORDER BY kb_type, created_at
        """, (datasource_id,))
        rows = cur.fetchall()
        return [_row_to_knowledge(row) for row in rows]


# ============ 辅助函数 ============

def _row_to_knowledge(row: dict[str, Any]) -> dict[str, Any]:
    """将数据库行转换为知识字典"""
    kb_metadata = row.get("kb_metadata")
    if isinstance(kb_metadata, str):
        try:
            kb_metadata = json.loads(kb_metadata)
        except Exception:
            kb_metadata = {}
    elif kb_metadata is None:
        kb_metadata = {}

    return {
        "id": row["id"],
        "datasource_id": row["datasource_id"],
        "kb_type": row["kb_type"],
        "kb_name": row["kb_name"],
        "kb_content": row["kb_content"],
        "kb_metadata": kb_metadata,
        "is_active": bool(row["is_active"]),
        "created_at": str(row.get("created_at", "")),
        "updated_at": str(row.get("updated_at", "")),
    }


# ============ 知识类型定义 ============

KNOWLEDGE_TYPES = {
    "term": {
        "name": "业务术语",
        "description": "业务术语解释、同义词映射",
        "content_template": json.dumps({
            "term": "术语名称",
            "synonyms": ["同义词1", "同义词2"],
            "meaning": "术语含义解释",
        }, ensure_ascii=False, indent=2),
    },
    "qa": {
        "name": "示例 Q&A",
        "description": "常见问题的 SQL 示例",
        "content_template": json.dumps({
            "question": "用户问题",
            "sql": "SELECT ... FROM ...",
            "rationale": "SQL 生成逻辑说明",
        }, ensure_ascii=False, indent=2),
    },
    "metric": {
        "name": "指标口径",
        "description": "指标口径定义、计算规则",
        "content_template": json.dumps({
            "metric_name": "指标名称",
            "definition": "指标定义",
            "aggregation": "SUM/COUNT/AVG",
            "business_rule": "业务规则说明",
        }, ensure_ascii=False, indent=2),
    },
    "table_desc": {
        "name": "表说明",
        "description": "表/字段的业务含义说明",
        "content_template": json.dumps({
            "table_name": "表名",
            "description": "表用途说明",
            "columns": [
                {"name": "字段名", "meaning": "字段含义"},
            ],
        }, ensure_ascii=False, indent=2),
    },
}


def get_knowledge_type_info(kb_type: str) -> Optional[dict[str, Any]]:
    """获取知识类型信息"""
    return KNOWLEDGE_TYPES.get(kb_type)


def list_knowledge_types() -> list[dict[str, Any]]:
    """列出所有知识类型"""
    return [
        {"type": kb_type, **info}
        for kb_type, info in KNOWLEDGE_TYPES.items()
    ]