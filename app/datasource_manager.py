"""
数据源管理器：管理多数据库连接，支持查询时动态切换。
支持 PostgreSQL、MySQL、SQLite 三种数据库类型。
"""
from __future__ import annotations

import os
import sqlite3
from typing import Any, Optional

import psycopg
import pymysql
from pymysql.cursors import DictCursor

from .config_service import DataSourceConfig, get_datasource_by_id, get_datasource_by_name, get_query_datasource


# 当前请求的数据源（请求级别，用于动态切换）
_current_datasource_id: Optional[int] = None


def set_current_datasource(ds_id: Optional[int]) -> None:
    """设置当前请求的数据源 ID"""
    global _current_datasource_id
    _current_datasource_id = ds_id


def get_current_datasource_config() -> DataSourceConfig:
    """
    获取当前数据源配置。
    优先级：
    1. 请求级别设置的 _current_datasource_id
    2. MySQL 配置表 is_query_target=1
    3. .env POSTGRES_DSN
    """
    global _current_datasource_id

    if _current_datasource_id:
        config = get_datasource_by_id(_current_datasource_id)
        if config:
            return config

    return get_query_datasource()


def execute_sql_on_datasource(
    sql: str,
    ds_id: Optional[int] = None,
    ds_name: Optional[str] = None,
    max_rows: int = 200,
) -> dict[str, Any]:
    """
    在指定数据源上执行 SQL 查询。

    Args:
        sql: SQL 语句
        ds_id: 数据源 ID（可选）
        ds_name: 数据源名称（可选）
        max_rows: 最大返回行数

    Returns:
        {"columns": [...], "rows": [...]}
    """
    config = _resolve_datasource_config(ds_id, ds_name)
    return _execute_sql_with_config(sql, config, max_rows)


def _resolve_datasource_config(
    ds_id: Optional[int],
    ds_name: Optional[str],
) -> DataSourceConfig:
    """解析数据源配置"""
    if ds_id:
        config = get_datasource_by_id(ds_id)
        if config:
            return config

    if ds_name:
        config = get_datasource_by_name(ds_name)
        if config:
            return config

    return get_current_datasource_config()


def _execute_sql_with_config(
    sql: str,
    config: DataSourceConfig,
    max_rows: int = 200,
) -> dict[str, Any]:
    """根据配置执行 SQL"""
    if config.ds_type == "postgresql":
        return _execute_postgresql(sql, config, max_rows)

    elif config.ds_type == "mysql":
        return _execute_mysql(sql, config, max_rows)

    elif config.ds_type == "sqlite":
        return _execute_sqlite(sql, config, max_rows)

    else:
        raise ValueError(f"Unsupported datasource type: {config.ds_type}")


def _execute_postgresql(
    sql: str,
    config: DataSourceConfig,
    max_rows: int,
) -> dict[str, Any]:
    """执行 PostgreSQL SQL"""
    dsn = config.get_dsn()

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)

            # 对于 SELECT 查询获取结果
            if cur.description:
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]

                # 限制行数
                if len(rows) > max_rows:
                    rows = rows[:max_rows]

                return {
                    "columns": columns,
                    "rows": [list(r) for r in rows],
                    "row_count": len(rows),
                }

            # 对于 INSERT/UPDATE/DELETE 返回影响行数
            return {
                "columns": [],
                "rows": [],
                "row_count": cur.rowcount,
            }


def _execute_mysql(
    sql: str,
    config: DataSourceConfig,
    max_rows: int,
) -> dict[str, Any]:
    """执行 MySQL SQL"""
    params = _parse_mysql_config(config)

    conn = pymysql.connect(**params, cursorclass=DictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)

            # 对于 SELECT 查询获取结果
            if cur.description:
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]

                # 限制行数
                if len(rows) > max_rows:
                    rows = rows[:max_rows]

                # DictCursor 返回字典，转换为列表
                return {
                    "columns": columns,
                    "rows": [[row.get(col) for col in columns] for row in rows],
                    "row_count": len(rows),
                }

            # 对于 INSERT/UPDATE/DELETE 返回影响行数
            return {
                "columns": [],
                "rows": [],
                "row_count": cur.rowcount,
            }
    finally:
        conn.close()


def _parse_mysql_config(config: DataSourceConfig) -> dict[str, Any]:
    """解析 MySQL 连接参数"""
    if config.dsn_override:
        # 解析 DSN: mysql://user:pass@host:port/database
        import re
        match = re.match(
            r"mysql://([^:]+):([^@]*)@([^:]+):(\d+)/([^?]+)",
            config.dsn_override,
        )
        if match:
            return {
                "host": match.group(3),
                "port": int(match.group(4)),
                "user": match.group(1),
                "password": match.group(2),
                "database": match.group(5),
                "charset": "utf8mb4",
            }

    return {
        "host": config.host or "localhost",
        "port": config.port or 3306,
        "user": config.username or "root",
        "password": config.password or "",
        "database": config.database or "test",
        "charset": "utf8mb4",
    }


def _execute_sqlite(
    sql: str,
    config: DataSourceConfig,
    max_rows: int,
) -> dict[str, Any]:
    """执行 SQLite SQL"""
    db_path = config.database or ":memory:"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(sql)

        # 对于 SELECT 查询获取结果
        if cur.description:
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]

            # 限制行数
            if len(rows) > max_rows:
                rows = rows[:max_rows]

            return {
                "columns": columns,
                "rows": [list(r) for r in rows],
                "row_count": len(rows),
            }

        # 对于 INSERT/UPDATE/DELETE 返回影响行数
        return {
            "columns": [],
            "rows": [],
            "row_count": cur.rowcount,
        }
    finally:
        conn.close()


# ============ 数据源元数据查询 ============

def get_datasource_tables(config: DataSourceConfig) -> list[dict[str, Any]]:
    """获取数据源的表列表"""
    if config.ds_type == "postgresql":
        return _get_postgresql_tables(config)

    elif config.ds_type == "mysql":
        return _get_mysql_tables(config)

    elif config.ds_type == "sqlite":
        return _get_sqlite_tables(config)

    return []


def _get_postgresql_tables(config: DataSourceConfig) -> list[dict[str, Any]]:
    """获取 PostgreSQL 表列表"""
    dsn = config.get_dsn()

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    table_name,
                    table_type
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            rows = cur.fetchall()
            return [
                {"table_name": row[0], "table_type": row[1]}
                for row in rows
            ]


def _get_mysql_tables(config: DataSourceConfig) -> list[dict[str, Any]]:
    """获取 MySQL 表列表"""
    params = _parse_mysql_config(config)

    conn = pymysql.connect(**params, cursorclass=DictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    table_name,
                    table_type
                FROM information_schema.tables
                WHERE table_schema = %s
                ORDER BY table_name
            """, (params["database"],))
            rows = cur.fetchall()
            return [
                {"table_name": row["table_name"], "table_type": row["table_type"]}
                for row in rows
            ]
    finally:
        conn.close()


def _get_sqlite_tables(config: DataSourceConfig) -> list[dict[str, Any]]:
    """获取 SQLite 表列表"""
    db_path = config.database or ":memory:"

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                name,
                type
            FROM sqlite_master
            WHERE type IN ('table', 'view')
            ORDER BY name
        """)
        rows = cur.fetchall()
        return [
            {"table_name": row[0], "table_type": row[1]}
            for row in rows
        ]
    finally:
        conn.close()


def get_table_columns(
    config: DataSourceConfig,
    table_name: str,
) -> list[dict[str, Any]]:
    """获取表的字段信息"""
    if config.ds_type == "postgresql":
        return _get_postgresql_columns(config, table_name)

    elif config.ds_type == "mysql":
        return _get_mysql_columns(config, table_name)

    elif config.ds_type == "sqlite":
        return _get_sqlite_columns(config, table_name)

    return []


def _get_postgresql_columns(
    config: DataSourceConfig,
    table_name: str,
) -> list[dict[str, Any]]:
    """获取 PostgreSQL 表字段"""
    dsn = config.get_dsn()

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            rows = cur.fetchall()
            return [
                {
                    "column_name": row[0],
                    "data_type": row[1],
                    "is_nullable": row[2],
                    "column_default": row[3],
                }
                for row in rows
            ]


def _get_mysql_columns(
    config: DataSourceConfig,
    table_name: str,
) -> list[dict[str, Any]]:
    """获取 MySQL 表字段"""
    params = _parse_mysql_config(config)

    conn = pymysql.connect(**params, cursorclass=DictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """, (params["database"], table_name))
            rows = cur.fetchall()
            return [
                {
                    "column_name": row["column_name"],
                    "data_type": row["data_type"],
                    "is_nullable": row["is_nullable"],
                    "column_default": row["column_default"],
                }
                for row in rows
            ]
    finally:
        conn.close()


def _get_sqlite_columns(
    config: DataSourceConfig,
    table_name: str,
) -> list[dict[str, Any]]:
    """获取 SQLite 表字段"""
    db_path = config.database or ":memory:"

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table_name})")
        rows = cur.fetchall()
        return [
            {
                "column_name": row[1],
                "data_type": row[2],
                "is_nullable": "YES" if row[3] == 0 else "NO",
                "column_default": row[4],
            }
            for row in rows
        ]
    finally:
        conn.close()


def preview_table_data(
    config: DataSourceConfig,
    table_name: str,
    limit: int = 100,
) -> dict[str, Any]:
    """预览表数据"""
    # 安全处理表名（防止 SQL 注入）
    safe_table = _sanitize_table_name(table_name)

    sql = f"SELECT * FROM {safe_table} LIMIT {limit}"
    return _execute_sql_with_config(sql, config, max_rows=limit)


def _sanitize_table_name(table_name: str) -> str:
    """清理表名，防止 SQL 注入"""
    # 只允许字母、数字、下划线
    import re
    safe = re.sub(r"[^a-zA-Z0-9_]", "", table_name)
    return safe


def test_datasource_connection(config: DataSourceConfig) -> dict[str, Any]:
    """测试数据源连接"""
    try:
        if config.ds_type == "postgresql":
            dsn = config.get_dsn()
            with psycopg.connect(dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            return {"success": True, "message": "连接成功"}

        elif config.ds_type == "mysql":
            params = _parse_mysql_config(config)
            conn = pymysql.connect(**params)
            conn.close()
            return {"success": True, "message": "连接成功"}

        elif config.ds_type == "sqlite":
            db_path = config.database or ":memory:"
            conn = sqlite3.connect(db_path)
            conn.close()
            return {"success": True, "message": "连接成功"}

        else:
            return {"success": False, "message": f"不支持的数据库类型: {config.ds_type}"}

    except Exception as e:
        return {"success": False, "message": str(e)}