"""MySQL platform database tools for history and user data."""
from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Any

import pymysql
from pymysql.cursors import DictCursor


def _serialize_for_json(value: Any) -> Any:
    """Convert non-JSON-serializable types (like Decimal) to JSON-safe types."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (list, tuple)):
        return [_serialize_for_json(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize_for_json(v) for k, v in value.items()}
    return str(value)


def _get_mysql_env(name: str, default: str | None = None) -> str:
    v = os.getenv(name, default)
    if v is None or v == "":
        raise RuntimeError(f"缺少环境变量：{name}")
    return v


def get_mysql_connection():
    """Get MySQL connection for platform database."""
    host = _get_mysql_env("MYSQL_HOST", "localhost")
    port = int(_get_mysql_env("MYSQL_PORT", "3306"))
    user = _get_mysql_env("MYSQL_USER", "root")
    password = _get_mysql_env("MYSQL_PASSWORD", "")
    database = _get_mysql_env("MYSQL_DATABASE", "nl2sql_platform")

    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        cursorclass=DictCursor,
    )


# ============ Session CRUD ============

def create_session(title: str | None = None) -> dict[str, Any]:
    """Create a new chat session."""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cur:
            sql_stmt = """
            INSERT INTO chat_session (title)
            VALUES (%s)
            """
            cur.execute(sql_stmt, (title,))
            conn.commit()
            return get_session_by_id(cur.lastrowid)
    finally:
        conn.close()


def get_session_by_id(session_id: int) -> dict[str, Any]:
    """Get a session by ID."""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, created_at, updated_at FROM chat_session WHERE id = %s",
                (session_id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def update_session_title(session_id: int, title: str) -> dict[str, Any] | None:
    """Update session title."""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE chat_session SET title = %s WHERE id = %s",
                (title, session_id),
            )
            conn.commit()
            return get_session_by_id(session_id)
    finally:
        conn.close()


def list_sessions(page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """List sessions with pagination."""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cur:
            # Count total
            cur.execute("SELECT COUNT(*) as total FROM chat_session")
            total = cur.fetchone()["total"]

            # Get paginated results
            offset = (page - 1) * page_size
            cur.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM chat_session
                ORDER BY updated_at DESC
                LIMIT %s OFFSET %s
                """,
                (page_size, offset),
            )
            sessions = cur.fetchall()

            return {
                "items": sessions,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
            }
    finally:
        conn.close()


def delete_session(session_id: int) -> bool:
    """Delete a session and all its query history."""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chat_session WHERE id = %s", (session_id,))
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()


# ============ History CRUD ============

def create_history(
    session_id: int,
    question: str,
    sql: str | None,
    columns: list[str],
    rows: list[list[Any]],
    execution_error: str | None = None,
    is_favorite: bool = False,
) -> dict[str, Any]:
    """Create a new query history record."""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cur:
            sql_stmt = """
            INSERT INTO query_history (session_id, question, generated_sql, `columns`, `rows`, execution_error, is_favorite)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(sql_stmt, (
                session_id,
                question,
                sql,
                json.dumps(_serialize_for_json(columns), ensure_ascii=False),
                json.dumps(_serialize_for_json(rows), ensure_ascii=False),
                execution_error,
                1 if is_favorite else 0,
            ))
            conn.commit()

            # Update session updated_at
            cur.execute("UPDATE chat_session SET updated_at = CURRENT_TIMESTAMP WHERE id = %s", (session_id,))
            conn.commit()

            return get_history_by_id(cur.lastrowid)
    finally:
        conn.close()


def get_history_by_id(history_id: int) -> dict[str, Any]:
    """Get a history record by ID."""
    import json

    conn = get_mysql_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, session_id, question, generated_sql, `columns`, `rows`,
                          execution_error, is_favorite, retry_count, created_at, updated_at
                   FROM query_history WHERE id = %s""",
                (history_id,),
            )
            row = cur.fetchone()
            if row:
                row["columns"] = json.loads(row["columns"]) if row["columns"] else []
                row["rows"] = json.loads(row["rows"]) if row["rows"] else []
                row["is_favorite"] = bool(row["is_favorite"])
            return row
    finally:
        conn.close()


def list_history(
    page: int = 1,
    page_size: int = 20,
    session_id: int | None = None,
    is_favorite: bool | None = None,
    search: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """List query history with pagination and filters."""
    import json

    conn = get_mysql_connection()
    try:
        with conn.cursor() as cur:
            # Build WHERE clause
            conditions = []
            params = []

            if session_id is not None:
                conditions.append("session_id = %s")
                params.append(session_id)

            if is_favorite is not None:
                conditions.append("is_favorite = %s")
                params.append(1 if is_favorite else 0)

            if search:
                conditions.append("(question LIKE %s OR generated_sql LIKE %s)")
                params.extend([f"%{search}%", f"%{search}%"])

            if start_date:
                conditions.append("created_at >= %s")
                params.append(start_date)

            if end_date:
                conditions.append("created_at <= %s")
                params.append(end_date)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # Count total
            count_sql = f"SELECT COUNT(*) as total FROM query_history WHERE {where_clause}"
            cur.execute(count_sql, params)
            total = cur.fetchone()["total"]

            # Get paginated results
            offset = (page - 1) * page_size
            list_sql = f"""
            SELECT id, session_id, question, generated_sql, `columns`, `rows`, execution_error,
                   is_favorite, retry_count, created_at, updated_at
            FROM query_history
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """
            cur.execute(list_sql, params + [page_size, offset])
            rows = cur.fetchall()

            # Parse JSON fields
            for row in rows:
                row["columns"] = json.loads(row["columns"]) if row["columns"] else []
                row["rows"] = json.loads(row["rows"]) if row["rows"] else []
                row["is_favorite"] = bool(row["is_favorite"])

            return {
                "items": rows,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
            }
    finally:
        conn.close()


def update_history(
    history_id: int,
    is_favorite: bool | None = None,
) -> dict[str, Any] | None:
    """Update a history record (mainly for favorite toggle)."""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cur:
            updates = []
            params = []

            if is_favorite is not None:
                updates.append("is_favorite = %s")
                params.append(1 if is_favorite else 0)

            if not updates:
                return get_history_by_id(history_id)

            params.append(history_id)
            sql = f"UPDATE query_history SET {', '.join(updates)} WHERE id = %s"
            cur.execute(sql, params)
            conn.commit()
            return get_history_by_id(history_id)
    finally:
        conn.close()


def increment_retry_count(history_id: int) -> None:
    """Increment retry count for a history record."""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE query_history SET retry_count = retry_count + 1 WHERE id = %s",
                (history_id,),
            )
            conn.commit()
    finally:
        conn.close()


def delete_history(history_id: int) -> bool:
    """Delete a history record."""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM query_history WHERE id = %s", (history_id,))
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()


def delete_history_batch(history_ids: list[int]) -> int:
    """Delete multiple history records."""
    if not history_ids:
        return 0

    conn = get_mysql_connection()
    try:
        with conn.cursor() as cur:
            placeholders = ",".join(["%s"] * len(history_ids))
            cur.execute(
                f"DELETE FROM query_history WHERE id IN ({placeholders})",
                history_ids,
            )
            conn.commit()
            return cur.rowcount
    finally:
        conn.close()


def clear_all_history() -> int:
    """Clear all history records."""
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM query_history")
            deleted = cur.rowcount
            cur.execute("DELETE FROM chat_session")
            conn.commit()
            return deleted
    finally:
        conn.close()