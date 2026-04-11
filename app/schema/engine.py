"""
Schema 引擎：基于 M-Schema 标准提取数据库 Schema 信息。
支持 PostgreSQL、MySQL、SQLite 三种数据库类型。

功能：
1. 提取表列表和表注释
2. 提取主键、外键、索引
3. 提取字段信息（名称、类型、可空、默认值、注释）
4. 提取示例值（DISTINCT 前 N 个非空值）
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any, Optional

import psycopg
import pymysql
from pymysql.cursors import DictCursor

from app.core.config_service import DataSourceConfig


@dataclass
class FieldStatistics:
    """字段统计信息"""
    min_value: Optional[str] = None  # 最小值（数值/日期）
    max_value: Optional[str] = None  # 最大值（数值/日期）
    distinct_count: int = 0  # 不同值数量
    null_count: int = 0  # NULL 值数量
    total_count: int = 0  # 总行数
    value_distribution: dict[str, int] = field(default_factory=dict)  # 值分布（Enum 字段）


@dataclass
class FieldInfo:
    """字段信息模型"""
    name: str
    type: str
    primary_key: bool = False
    nullable: bool = True
    default: Optional[str] = None
    comment: Optional[str] = None
    examples: list[str] = field(default_factory=list)
    # XiYan 分类结果
    category: Optional[str] = None  # DateTime/Enum/Code/Text/Measure
    dim_or_meas: Optional[str] = None  # Dimension/Measure
    date_min_gran: Optional[str] = None  # YEAR/MONTH/DAY/HOUR/MINUTE/SECOND
    # 字段统计（P0 新增）
    statistics: Optional[FieldStatistics] = None


@dataclass
class TableInfo:
    """表信息模型"""
    name: str
    comment: Optional[str] = None
    fields: dict[str, FieldInfo] = field(default_factory=dict)
    primary_keys: list[str] = field(default_factory=list)
    # 表类型（fact/dimension/other）
    table_type: Optional[str] = None


@dataclass
class ForeignKeyInfo:
    """外键信息"""
    from_table: str
    from_column: str
    to_table: str
    to_column: str


@dataclass
class SchemaUnderstanding:
    """Schema 理解结果"""
    db_id: str
    tables: dict[str, TableInfo] = field(default_factory=dict)
    foreign_keys: list[ForeignKeyInfo] = field(default_factory=list)


class SchemaEngine:
    """Schema 提取引擎"""

    def __init__(self, config: DataSourceConfig):
        """
        初始化 Schema 引擎

        Args:
            config: 数据源配置
        """
        self.config = config
        self.ds_type = config.ds_type

    def extract_schema(
        self,
        include_examples: bool = True,
        example_limit: int = 5,
    ) -> SchemaUnderstanding:
        """
        提取完整 Schema 信息

        Args:
            include_examples: 是否提取示例值
            example_limit: 每个字段提取的示例值数量

        Returns:
            SchemaUnderstanding 对象
        """
        result = SchemaUnderstanding(db_id=self.config.ds_name or "unknown")

        if self.ds_type == "postgresql":
            self._extract_postgresql_schema(result, include_examples, example_limit)
        elif self.ds_type == "mysql":
            self._extract_mysql_schema(result, include_examples, example_limit)
        elif self.ds_type == "sqlite":
            self._extract_sqlite_schema(result, include_examples, example_limit)
        else:
            raise ValueError(f"Unsupported datasource type: {self.ds_type}")

        return result

    def _extract_postgresql_schema(
        self,
        result: SchemaUnderstanding,
        include_examples: bool,
        example_limit: int,
    ) -> None:
        """提取 PostgreSQL Schema"""
        dsn = self.config.get_dsn()

        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                # 1. 获取表列表
                cur.execute("""
                    SELECT
                        t.table_name,
                        pgd.description
                    FROM information_schema.tables t
                    LEFT JOIN pg_class pgc ON pgc.relname = t.table_name
                    LEFT JOIN pg_description pgd ON pgd.objoid = pgc.oid AND pgd.objsubid = 0
                    WHERE t.table_schema = 'public'
                      AND t.table_type = 'BASE TABLE'
                    ORDER BY t.table_name
                """)
                tables = cur.fetchall()

                for table_name, table_comment in tables:
                    table_info = TableInfo(name=table_name, comment=table_comment)
                    result.tables[table_name] = table_info

                # 2. 获取字段信息
                for table_name in result.tables:
                    # 获取主键
                    cur.execute("""
                        SELECT a.attname
                        FROM pg_index i
                        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                        WHERE i.indrelid = %s::regclass AND i.indisprimary
                    """, (table_name,))
                    pk_rows = cur.fetchall()
                    pk_columns = [row[0] for row in pk_rows]
                    result.tables[table_name].primary_keys = pk_columns

                    # 获取字段详情
                    cur.execute("""
                        SELECT
                            c.column_name,
                            c.data_type,
                            c.is_nullable,
                            c.column_default,
                            col_description(pgc.oid, c.ordinal_position) as column_comment
                        FROM information_schema.columns c
                        JOIN pg_class pgc ON pgc.relname = c.table_name
                        WHERE c.table_schema = 'public'
                          AND c.table_name = %s
                        ORDER BY c.ordinal_position
                    """, (table_name,))
                    columns = cur.fetchall()

                    for col_name, col_type, is_nullable, col_default, col_comment in columns:
                        field = FieldInfo(
                            name=col_name,
                            type=col_type,
                            primary_key=col_name in pk_columns,
                            nullable=is_nullable == "YES",
                            default=str(col_default) if col_default else None,
                            comment=col_comment,
                        )
                        result.tables[table_name].fields[col_name] = field

                        # 提取示例值
                        if include_examples:
                            try:
                                examples = self._fetch_postgresql_examples(
                                    conn, table_name, col_name, example_limit
                                )
                                field.examples = examples
                            except Exception:
                                pass

                # 3. 获取外键
                cur.execute("""
                    SELECT
                        tc.table_name,
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                      ON tc.constraint_name = kcu.constraint_name
                      AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                      ON ccu.constraint_name = tc.constraint_name
                      AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                      AND tc.table_schema = 'public'
                """)
                fk_rows = cur.fetchall()

                for from_table, from_column, to_table, to_column in fk_rows:
                    result.foreign_keys.append(ForeignKeyInfo(
                        from_table=from_table,
                        from_column=from_column,
                        to_table=to_table,
                        to_column=to_column,
                    ))

    def _fetch_postgresql_examples(
        self,
        conn,
        table_name: str,
        column_name: str,
        limit: int,
    ) -> list[str]:
        """提取 PostgreSQL 字段示例值"""
        safe_table = self._sanitize_identifier(table_name)
        safe_column = self._sanitize_identifier(column_name)

        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT DISTINCT {safe_column}
                FROM {safe_table}
                WHERE {safe_column} IS NOT NULL
                LIMIT {limit}
            """)
            rows = cur.fetchall()
            return [str(row[0]) for row in rows]

    def _extract_mysql_schema(
        self,
        result: SchemaUnderstanding,
        include_examples: bool,
        example_limit: int,
    ) -> None:
        """提取 MySQL Schema"""
        params = self._parse_mysql_config()

        conn = pymysql.connect(**params, cursorclass=DictCursor)
        try:
            with conn.cursor() as cur:
                database = params["database"]

                # 1. 获取表列表
                cur.execute("""
                    SELECT
                        TABLE_NAME as table_name,
                        TABLE_COMMENT as table_comment
                    FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = %s
                      AND TABLE_TYPE = 'BASE TABLE'
                    ORDER BY TABLE_NAME
                """, (database,))
                tables = cur.fetchall()

                for row in tables:
                    table_name = row["table_name"]
                    table_info = TableInfo(
                        name=table_name,
                        comment=row["table_comment"],
                    )
                    result.tables[table_name] = table_info

                # 2. 获取字段信息
                for table_name in result.tables:
                    # 获取主键
                    cur.execute("""
                        SELECT COLUMN_NAME
                        FROM information_schema.KEY_COLUMN_USAGE
                        WHERE TABLE_SCHEMA = %s
                          AND TABLE_NAME = %s
                          AND CONSTRAINT_NAME = 'PRIMARY'
                    """, (database, table_name))
                    pk_rows = cur.fetchall()
                    pk_columns = [row["COLUMN_NAME"] for row in pk_rows]
                    result.tables[table_name].primary_keys = pk_columns

                    # 获取字段详情
                    cur.execute("""
                        SELECT
                            COLUMN_NAME,
                            DATA_TYPE,
                            IS_NULLABLE,
                            COLUMN_DEFAULT,
                            COLUMN_COMMENT
                        FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = %s
                          AND TABLE_NAME = %s
                        ORDER BY ORDINAL_POSITION
                    """, (database, table_name))
                    columns = cur.fetchall()

                    for row in columns:
                        col_name = row["COLUMN_NAME"]
                        field = FieldInfo(
                            name=col_name,
                            type=row["DATA_TYPE"],
                            primary_key=col_name in pk_columns,
                            nullable=row["IS_NULLABLE"] == "YES",
                            default=str(row["COLUMN_DEFAULT"]) if row["COLUMN_DEFAULT"] else None,
                            comment=row["COLUMN_COMMENT"] or None,
                        )
                        result.tables[table_name].fields[col_name] = field

                        # 提取示例值
                        if include_examples:
                            try:
                                examples = self._fetch_mysql_examples(
                                    cur, database, table_name, col_name, example_limit
                                )
                                field.examples = examples
                            except Exception:
                                pass

                # 3. 获取外键
                cur.execute("""
                    SELECT
                        TABLE_NAME,
                        COLUMN_NAME,
                        REFERENCED_TABLE_NAME,
                        REFERENCED_COLUMN_NAME
                    FROM information_schema.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = %s
                      AND REFERENCED_TABLE_NAME IS NOT NULL
                """, (database,))
                fk_rows = cur.fetchall()

                for row in fk_rows:
                    result.foreign_keys.append(ForeignKeyInfo(
                        from_table=row["TABLE_NAME"],
                        from_column=row["COLUMN_NAME"],
                        to_table=row["REFERENCED_TABLE_NAME"],
                        to_column=row["REFERENCED_COLUMN_NAME"],
                    ))
        finally:
            conn.close()

    def _fetch_mysql_examples(
        self,
        cur,
        database: str,
        table_name: str,
        column_name: str,
        limit: int,
    ) -> list[str]:
        """提取 MySQL 字段示例值"""
        safe_table = self._sanitize_identifier(table_name)
        safe_column = self._sanitize_identifier(column_name)

        cur.execute(f"""
            SELECT DISTINCT {safe_column}
            FROM {database}.{safe_table}
            WHERE {safe_column} IS NOT NULL
            LIMIT {limit}
        """)
        rows = cur.fetchall()
        return [str(row[safe_column]) for row in rows]

    def _extract_sqlite_schema(
        self,
        result: SchemaUnderstanding,
        include_examples: bool,
        example_limit: int,
    ) -> None:
        """提取 SQLite Schema"""
        db_path = self.config.database or ":memory:"

        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()

            # 1. 获取表列表
            cur.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = cur.fetchall()

            for (table_name,) in tables:
                table_info = TableInfo(name=table_name)
                result.tables[table_name] = table_info

            # 2. 获取字段信息
            for table_name in result.tables:
                # 获取表结构
                cur.execute(f"PRAGMA table_info({self._sanitize_identifier(table_name)})")
                columns = cur.fetchall()

                # 获取主键
                cur.execute(f"PRAGMA table_xinfo({self._sanitize_identifier(table_name)})")
                pk_info = cur.fetchall()

                for row in columns:
                    # row: cid, name, type, notnull, default, pk
                    col_name = row[1]
                    is_pk = row[5] == 1

                    field = FieldInfo(
                        name=col_name,
                        type=row[2],
                        primary_key=is_pk,
                        nullable=row[3] == 0,  # notnull=0 表示可空
                        default=str(row[4]) if row[4] is not None else None,
                    )
                    result.tables[table_name].fields[col_name] = field

                    if is_pk:
                        result.tables[table_name].primary_keys.append(col_name)

                    # 提取示例值
                    if include_examples:
                        try:
                            examples = self._fetch_sqlite_examples(
                                conn, table_name, col_name, example_limit
                            )
                            field.examples = examples
                        except Exception:
                            pass

            # SQLite 外键需要通过 PRAGMA foreign_key_list 获取
            for table_name in result.tables:
                cur.execute(f"PRAGMA foreign_key_list({self._sanitize_identifier(table_name)})")
                fk_rows = cur.fetchall()

                for row in fk_rows:
                    # row: id, seq, table, from, to, ...
                    result.foreign_keys.append(ForeignKeyInfo(
                        from_table=table_name,
                        from_column=row[3],  # from
                        to_table=row[2],  # table (referenced)
                        to_column=row[4],  # to
                    ))
        finally:
            conn.close()

    def _fetch_sqlite_examples(
        self,
        conn,
        table_name: str,
        column_name: str,
        limit: int,
    ) -> list[str]:
        """提取 SQLite 字段示例值"""
        safe_table = self._sanitize_identifier(table_name)
        safe_column = self._sanitize_identifier(column_name)

        cur = conn.cursor()
        cur.execute(f"""
            SELECT DISTINCT {safe_column}
            FROM {safe_table}
            WHERE {safe_column} IS NOT NULL
            LIMIT {limit}
        """)
        rows = cur.fetchall()
        return [str(row[0]) for row in rows]

    def _parse_mysql_config(self) -> dict[str, Any]:
        """解析 MySQL 连接参数"""
        if self.config.dsn_override:
            import re
            match = re.match(
                r"mysql://([^:]+):([^@]*)@([^:]+):(\d+)/([^?]+)",
                self.config.dsn_override,
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
            "host": self.config.host or "localhost",
            "port": self.config.port or 3306,
            "user": self.config.username or "root",
            "password": self.config.password or "",
            "database": self.config.database or "test",
            "charset": "utf8mb4",
        }

    def _sanitize_identifier(self, identifier: str) -> str:
        """清理标识符，防止 SQL 注入"""
        import re
        # 只允许字母、数字、下划线
        return re.sub(r"[^a-zA-Z0-9_]", "", identifier)

    def extract_field_statistics(
        self,
        table_name: str,
        field_name: str,
        field_type: str,
        category: Optional[str] = None,
    ) -> FieldStatistics:
        """
        提取字段统计信息

        Args:
            table_name: 表名
            field_name: 字段名
            field_type: 字段类型
            category: 字段分类（DateTime/Enum/Code/Text/Measure）

        Returns:
            FieldStatistics 对象
        """
        if self.ds_type == "postgresql":
            return self._extract_postgresql_field_stats(table_name, field_name, field_type, category)
        elif self.ds_type == "mysql":
            return self._extract_mysql_field_stats(table_name, field_name, field_type, category)
        elif self.ds_type == "sqlite":
            return self._extract_sqlite_field_stats(table_name, field_name, field_type, category)
        else:
            return FieldStatistics()

    def _extract_postgresql_field_stats(
        self,
        table_name: str,
        field_name: str,
        field_type: str,
        category: Optional[str],
    ) -> FieldStatistics:
        """提取 PostgreSQL 字段统计"""
        dsn = self.config.get_dsn()
        safe_table = self._sanitize_identifier(table_name)
        safe_column = self._sanitize_identifier(field_name)

        stats = FieldStatistics()

        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                # 基础统计：总行数、NULL 数、不同值数
                cur.execute(f"""
                    SELECT
                        COUNT(*) as total,
                        COUNT({safe_column}) as non_null,
                        COUNT(DISTINCT {safe_column}) as distinct_count
                    FROM {safe_table}
                """)
                row = cur.fetchone()
                stats.total_count = row[0]
                stats.null_count = row[0] - row[1]
                stats.distinct_count = row[2]

                # 根据类型提取不同的统计
                type_upper = field_type.upper()

                # 数值类型：min/max
                if any(t in type_upper for t in ["INT", "DECIMAL", "FLOAT", "DOUBLE", "NUMERIC", "REAL"]):
                    cur.execute(f"""
                        SELECT
                            MIN({safe_column})::text,
                            MAX({safe_column})::text
                        FROM {safe_table}
                        WHERE {safe_column} IS NOT NULL
                    """)
                    row = cur.fetchone()
                    stats.min_value = row[0]
                    stats.max_value = row[1]

                # 时间类型：min/max
                elif any(t in type_upper for t in ["DATE", "TIME", "TIMESTAMP"]):
                    cur.execute(f"""
                        SELECT
                            MIN({safe_column})::text,
                            MAX({safe_column})::text
                        FROM {safe_table}
                        WHERE {safe_column} IS NOT NULL
                    """)
                    row = cur.fetchone()
                    stats.min_value = row[0]
                    stats.max_value = row[1]

                # Enum 类型：值分布
                elif category == "Enum" or stats.distinct_count <= 20:
                    if stats.distinct_count <= 50 and stats.distinct_count > 0:
                        cur.execute(f"""
                            SELECT {safe_column}, COUNT(*) as cnt
                            FROM {safe_table}
                            WHERE {safe_column} IS NOT NULL
                            GROUP BY {safe_column}
                            ORDER BY cnt DESC
                            LIMIT 20
                        """)
                        for row in cur.fetchall():
                            stats.value_distribution[str(row[0])] = row[1]

        return stats

    def _extract_mysql_field_stats(
        self,
        table_name: str,
        field_name: str,
        field_type: str,
        category: Optional[str],
    ) -> FieldStatistics:
        """提取 MySQL 字段统计"""
        params = self._parse_mysql_config()
        safe_table = self._sanitize_identifier(table_name)
        safe_column = self._sanitize_identifier(field_name)
        database = params["database"]

        stats = FieldStatistics()

        conn = pymysql.connect(**params, cursorclass=DictCursor)
        try:
            with conn.cursor() as cur:
                # 基础统计
                cur.execute(f"""
                    SELECT
                        COUNT(*) as total,
                        COUNT({safe_column}) as non_null,
                        COUNT(DISTINCT {safe_column}) as distinct_count
                    FROM {database}.{safe_table}
                """)
                row = cur.fetchone()
                stats.total_count = row["total"]
                stats.null_count = row["total"] - row["non_null"]
                stats.distinct_count = row["distinct_count"]

                type_upper = field_type.upper()

                # 数值类型
                if any(t in type_upper for t in ["INT", "DECIMAL", "FLOAT", "DOUBLE", "NUMERIC"]):
                    cur.execute(f"""
                        SELECT
                            MIN({safe_column}),
                            MAX({safe_column})
                        FROM {database}.{safe_table}
                        WHERE {safe_column} IS NOT NULL
                    """)
                    row = cur.fetchone()
                    stats.min_value = str(row["MIN({safe_column})"]) if row["MIN({safe_column})"] else None
                    stats.max_value = str(row["MAX({safe_column})"]) if row["MAX({safe_column})"] else None

                # 时间类型
                elif any(t in type_upper for t in ["DATE", "TIME", "DATETIME", "TIMESTAMP"]):
                    cur.execute(f"""
                        SELECT
                            MIN({safe_column}),
                            MAX({safe_column})
                        FROM {database}.{safe_table}
                        WHERE {safe_column} IS NOT NULL
                    """)
                    row = cur.fetchone()
                    stats.min_value = str(row[f"MIN({safe_column})"]) if row[f"MIN({safe_column})"] else None
                    stats.max_value = str(row[f"MAX({safe_column})"]) if row[f"MAX({safe_column})"] else None

                # Enum 类型
                elif category == "Enum" or stats.distinct_count <= 20:
                    if stats.distinct_count <= 50 and stats.distinct_count > 0:
                        cur.execute(f"""
                            SELECT {safe_column}, COUNT(*) as cnt
                            FROM {database}.{safe_table}
                            WHERE {safe_column} IS NOT NULL
                            GROUP BY {safe_column}
                            ORDER BY cnt DESC
                            LIMIT 20
                        """)
                        for row in cur.fetchall():
                            stats.value_distribution[str(row[safe_column])] = row["cnt"]

        finally:
            conn.close()

        return stats

    def _extract_sqlite_field_stats(
        self,
        table_name: str,
        field_name: str,
        field_type: str,
        category: Optional[str],
    ) -> FieldStatistics:
        """提取 SQLite 字段统计"""
        db_path = self.config.database or ":memory:"
        safe_table = self._sanitize_identifier(table_name)
        safe_column = self._sanitize_identifier(field_name)

        stats = FieldStatistics()

        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()

            # 基础统计
            cur.execute(f"""
                SELECT
                    COUNT(*) as total,
                    COUNT({safe_column}) as non_null,
                    COUNT(DISTINCT {safe_column}) as distinct_count
                FROM {safe_table}
            """)
            row = cur.fetchone()
            stats.total_count = row[0]
            stats.null_count = row[0] - row[1]
            stats.distinct_count = row[2]

            type_upper = field_type.upper()

            # 数值类型
            if "INT" in type_upper or "REAL" in type_upper or "NUMERIC" in type_upper:
                cur.execute(f"""
                    SELECT MIN({safe_column}), MAX({safe_column})
                    FROM {safe_table}
                    WHERE {safe_column} IS NOT NULL
                """)
                row = cur.fetchone()
                stats.min_value = str(row[0]) if row[0] is not None else None
                stats.max_value = str(row[1]) if row[1] is not None else None

            # Enum 类型
            elif category == "Enum" or stats.distinct_count <= 20:
                if stats.distinct_count <= 50 and stats.distinct_count > 0:
                    cur.execute(f"""
                        SELECT {safe_column}, COUNT(*) as cnt
                        FROM {safe_table}
                        WHERE {safe_column} IS NOT NULL
                        GROUP BY {safe_column}
                        ORDER BY cnt DESC
                        LIMIT 20
                    """)
                    for row in cur.fetchall():
                        stats.value_distribution[str(row[0])] = row[1]

        finally:
            conn.close()

        return stats

    def to_mschema_json(self, schema: SchemaUnderstanding) -> dict[str, Any]:
        """
        将 Schema 转换为 M-Schema JSON 格式

        M-Schema 是一种标准化的 Schema 表示格式，用于 NL2SQL 系统。
        """
        mschema = {
            "db_id": schema.db_id,
            "tables": {},
            "foreign_keys": [],
        }

        for table_name, table_info in schema.tables.items():
            table_data = {
                "name": table_name,
                "comment": table_info.comment,
                "fields": {},
                "primary_keys": table_info.primary_keys,
            }

            for field_name, field_info in table_info.fields.items():
                field_data = {
                    "name": field_name,
                    "type": field_info.type,
                    "primary_key": field_info.primary_key,
                    "nullable": field_info.nullable,
                    "default": field_info.default,
                    "comment": field_info.comment,
                    "examples": field_info.examples[:5] if field_info.examples else [],
                    "category": field_info.category,
                    "dim_or_meas": field_info.dim_or_meas,
                    "date_min_gran": field_info.date_min_gran,
                }
                # 添加统计信息（P0 新增）
                if field_info.statistics:
                    field_data["statistics"] = {
                        "min_value": field_info.statistics.min_value,
                        "max_value": field_info.statistics.max_value,
                        "distinct_count": field_info.statistics.distinct_count,
                        "null_count": field_info.statistics.null_count,
                        "total_count": field_info.statistics.total_count,
                        "value_distribution": field_info.statistics.value_distribution,
                    }
                table_data["fields"][field_name] = field_data

            mschema["tables"][table_name] = table_data

        for fk in schema.foreign_keys:
            mschema["foreign_keys"].append({
                "from_table": fk.from_table,
                "from_column": fk.from_column,
                "to_table": fk.to_table,
                "to_column": fk.to_column,
            })

        return mschema

    def to_mschema_text(self, schema: SchemaUnderstanding) -> str:
        """
        将 Schema 转换为 M-Schema 文本格式（用于 LLM Prompt）
        """
        lines = [f"数据库: {schema.db_id}", ""]

        for table_name, table_info in schema.tables.items():
            lines.append(f"表 {table_name}:")
            if table_info.comment:
                lines.append(f"  描述: {table_info.comment}")

            for field_name, field_info in table_info.fields.items():
                type_str = field_info.type
                pk_str = " [主键]" if field_info.primary_key else ""
                comment_str = f" # {field_info.comment}" if field_info.comment else ""

                lines.append(f"  - {field_name}: {type_str}{pk_str}{comment_str}")

                if field_info.examples:
                    examples_str = ", ".join(str(e) for e in field_info.examples[:3])
                    lines.append(f"    示例值: {examples_str}")

                # 添加统计信息（P0 新增）
                if field_info.statistics:
                    stats = field_info.statistics
                    stats_parts = []

                    # 数值/时间范围
                    if stats.min_value and stats.max_value:
                        stats_parts.append(f"范围: {stats.min_value} ~ {stats.max_value}")

                    # 不同值数量
                    if stats.distinct_count > 0:
                        fill_rate = (stats.total_count - stats.null_count) / stats.total_count * 100 if stats.total_count > 0 else 0
                        stats_parts.append(f"不同值: {stats.distinct_count}个, 填充率: {fill_rate:.1f}%")

                    # Enum 值分布
                    if stats.value_distribution and len(stats.value_distribution) > 0:
                        top_values = sorted(stats.value_distribution.items(), key=lambda x: x[1], reverse=True)[:5]
                        dist_str = ", ".join(f"{k}({v})" for k, v in top_values)
                        stats_parts.append(f"值分布: {dist_str}")

                    if stats_parts:
                        lines.append(f"    统计: {'; '.join(stats_parts)}")

            lines.append("")

        if schema.foreign_keys:
            lines.append("外键关系:")
            for fk in schema.foreign_keys:
                lines.append(f"  {fk.from_table}.{fk.from_column} -> {fk.to_table}.{fk.to_column}")

        return "\n".join(lines)