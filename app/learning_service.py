"""
Schema 学习服务：编排 Schema 学习流程。

流程：
1. 提取 Schema（SchemaEngine）
2. 分类字段（SchemaClassifier）
3. 生成描述（SchemaDescriptor）
4. 构建知识库（KnowledgeBuilder）
5. 缓存结果（SchemaCache）
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from .config_service import AIModelConfig, DataSourceConfig, get_active_ai_config, get_datasource_by_id
from .mysql_tools import get_mysql_connection
from .schema_classifier import SchemaClassifier
from .schema_descriptor import SchemaDescriptor
from .schema_engine import SchemaEngine, SchemaUnderstanding


@dataclass
class LearningProgress:
    """学习进度"""
    task_id: int
    datasource_id: int
    status: str  # pending/running/completed/failed
    progress: int  # 0-100
    current_step: str
    message: str
    error: Optional[str] = None


class LearningService:
    """Schema 学习服务"""

    def __init__(
        self,
        datasource_id: int,
        llm_config: AIModelConfig | None = None,
    ):
        """
        初始化学习服务

        Args:
            datasource_id: 数据源 ID
            llm_config: LLM 配置（可选，默认使用激活的配置）
        """
        self.datasource_id = datasource_id
        self.config = get_datasource_by_id(datasource_id)

        if not self.config:
            raise ValueError(f"数据源不存在: {datasource_id}")

        self.llm_config = llm_config or get_active_ai_config()
        self.task_id: int | None = None

    def start_learning(self) -> LearningProgress:
        """
        开始学习流程

        Returns:
            学习进度
        """
        # 创建学习任务
        self.task_id = self._create_task()

        try:
            return self._execute_learning()
        except Exception as e:
            self._update_task_status("failed", error=str(e))
            return LearningProgress(
                task_id=self.task_id,
                datasource_id=self.datasource_id,
                status="failed",
                progress=0,
                current_step="",
                message="学习失败",
                error=str(e),
            )

    def _execute_learning(self) -> LearningProgress:
        """执行学习流程"""
        self._update_task_status("running", progress=0, step="初始化", message="开始学习")

        # Step 1: 提取 Schema (20%)
        self._update_task_status("running", progress=10, step="提取 Schema", message="正在提取数据库结构")
        engine = SchemaEngine(self.config)
        schema = engine.extract_schema(include_examples=True, example_limit=5)

        self._update_task_status("running", progress=20, step="提取 Schema", message=f"已提取 {len(schema.tables)} 张表")

        # Step 2: 分类字段 (40%)
        self._update_task_status("running", progress=30, step="分类字段", message="正在分类字段")
        classifier = SchemaClassifier(self.llm_config)
        schema = classifier.classify_schema(schema)

        # 推断表类型
        for table_name, table in schema.tables.items():
            table.table_type = classifier.infer_table_type(table)

        self._update_task_status("running", progress=40, step="分类字段", message="字段分类完成")

        # Step 3: 生成描述 (70%)
        self._update_task_status("running", progress=50, step="生成描述", message="正在生成语义描述")
        descriptor = SchemaDescriptor(self.llm_config)
        schema = descriptor.generate_descriptions(schema)

        self._update_task_status("running", progress=70, step="生成描述", message="语义描述生成完成")

        # Step 4: 构建知识库 (85%)
        self._update_task_status("running", progress=75, step="构建知识库", message="正在构建知识库")
        knowledge_entries = descriptor.generate_knowledge_entries(schema)
        self._populate_knowledge_base(knowledge_entries, schema)

        self._update_task_status("running", progress=85, step="构建知识库", message="知识库构建完成")

        # Step 5: 缓存结果 (100%)
        self._update_task_status("running", progress=90, step="缓存结果", message="正在缓存 Schema")
        self._save_schema_cache(schema, engine)

        self._update_task_status("completed", progress=100, step="完成", message="学习完成")

        return LearningProgress(
            task_id=self.task_id,
            datasource_id=self.datasource_id,
            status="completed",
            progress=100,
            current_step="完成",
            message=f"学习完成，共处理 {len(schema.tables)} 张表",
        )

    def _create_task(self) -> int:
        """创建学习任务"""
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO learning_task (datasource_id, task_type, status, progress, current_step, message)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (self.datasource_id, "schema_learning", "pending", 0, "初始化", "任务已创建"))
            conn.commit()
            return cur.lastrowid

    def _update_task_status(
        self,
        status: str,
        progress: int = 0,
        step: str = "",
        message: str = "",
        error: str | None = None,
    ) -> None:
        """更新任务状态"""
        if not self.task_id:
            return

        conn = get_mysql_connection()
        with conn.cursor() as cur:
            if status == "running":
                cur.execute("""
                    UPDATE learning_task
                    SET status = %s, progress = %s, current_step = %s, message = %s, started_at = COALESCE(started_at, NOW())
                    WHERE id = %s
                """, (status, progress, step, message, self.task_id))
            elif status == "completed":
                cur.execute("""
                    UPDATE learning_task
                    SET status = %s, progress = %s, current_step = %s, message = %s, completed_at = NOW()
                    WHERE id = %s
                """, (status, progress, step, message, self.task_id))
            elif status == "failed":
                cur.execute("""
                    UPDATE learning_task
                    SET status = %s, progress = %s, current_step = %s, message = %s, error_message = %s, completed_at = NOW()
                    WHERE id = %s
                """, (status, progress, step, message, error, self.task_id))
            conn.commit()

    def _populate_knowledge_base(
        self,
        knowledge_entries: dict[str, list[dict[str, Any]]],
        schema: SchemaUnderstanding,
    ) -> None:
        """
        填充知识库到 PostgreSQL

        Args:
            knowledge_entries: 知识库条目
            schema: Schema 理解结果
        """
        import psycopg

        dsn = self.config.get_dsn()

        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                # 清空现有数据（可选，根据需求决定）
                # cur.execute("DELETE FROM field_metadata")

                # 插入字段级元数据
                for table_name, table in schema.tables.items():
                    for field_name, field in table.fields.items():
                        cur.execute("""
                            INSERT INTO field_metadata (
                                table_name, column_name, data_type,
                                is_primary_key, is_nullable, column_default, column_comment,
                                field_category, dim_or_meas, date_granularity,
                                examples, llm_description
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (table_name, column_name) DO UPDATE SET
                                data_type = EXCLUDED.data_type,
                                is_primary_key = EXCLUDED.is_primary_key,
                                is_nullable = EXCLUDED.is_nullable,
                                column_default = EXCLUDED.column_default,
                                column_comment = EXCLUDED.column_comment,
                                field_category = EXCLUDED.field_category,
                                dim_or_meas = EXCLUDED.dim_or_meas,
                                date_granularity = EXCLUDED.date_granularity,
                                examples = EXCLUDED.examples,
                                llm_description = EXCLUDED.llm_description,
                                updated_at = NOW()
                        """, (
                            table_name, field_name, field.type,
                            field.primary_key, field.nullable, field.default, field.comment,
                            field.category, field.dim_or_meas, field.date_min_gran,
                            json.dumps(field.examples[:10]) if field.examples else None,
                            field.comment,
                        ))

            conn.commit()

    def _save_schema_cache(
        self,
        schema: SchemaUnderstanding,
        engine: SchemaEngine,
    ) -> None:
        """
        保存 Schema 缓存到 MySQL

        Args:
            schema: Schema 理解结果
            engine: Schema 引擎
        """
        schema_json = engine.to_mschema_json(schema)
        schema_text = engine.to_mschema_text(schema)

        # 计算字段总数
        field_count = sum(len(t.fields) for t in schema.tables.values())

        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO schema_cache (
                    datasource_id, schema_json, mschema_text, table_count, field_count, learning_status
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    schema_json = VALUES(schema_json),
                    mschema_text = VALUES(mschema_text),
                    table_count = VALUES(table_count),
                    field_count = VALUES(field_count),
                    learning_status = VALUES(learning_status),
                    learned_at = NOW()
            """, (
                self.datasource_id,
                json.dumps(schema_json, ensure_ascii=False),
                schema_text,
                len(schema.tables),
                field_count,
                "completed",
            ))
            conn.commit()


def get_learning_progress(task_id: int) -> LearningProgress | None:
    """
    获取学习进度

    Args:
        task_id: 任务 ID

    Returns:
        学习进度，如果任务不存在则返回 None
    """
    conn = get_mysql_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, datasource_id, status, progress, current_step, message, error_message
            FROM learning_task
            WHERE id = %s
        """, (task_id,))
        row = cur.fetchone()

        if row:
            return LearningProgress(
                task_id=row["id"],
                datasource_id=row["datasource_id"],
                status=row["status"],
                progress=row["progress"],
                current_step=row["current_step"],
                message=row["message"],
                error=row["error_message"],
            )

    return None


def get_schema_cache(datasource_id: int) -> dict[str, Any] | None:
    """
    获取 Schema 缓存

    Args:
        datasource_id: 数据源 ID

    Returns:
        Schema 缓存数据，如果不存在则返回 None
    """
    conn = get_mysql_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, schema_json, mschema_text, table_count, field_count, learned_at
            FROM schema_cache
            WHERE datasource_id = %s AND learning_status = 'completed'
        """, (datasource_id,))
        row = cur.fetchone()

        if row:
            # PyMySQL 返回 JSON 列为字符串，需要解析
            schema_json = row["schema_json"]
            if isinstance(schema_json, str):
                schema_json = json.loads(schema_json)

            return {
                "id": row["id"],
                "datasource_id": datasource_id,
                "schema_json": schema_json,
                "mschema_text": row["mschema_text"],
                "table_count": row["table_count"],
                "field_count": row["field_count"],
                "learned_at": row["learned_at"].isoformat() if row["learned_at"] else None,
            }

    return None


def list_learning_tasks(datasource_id: int | None = None) -> list[LearningProgress]:
    """
    列出学习任务

    Args:
        datasource_id: 数据源 ID（可选，不传则列出所有）

    Returns:
        学习任务列表
    """
    conn = get_mysql_connection()
    with conn.cursor() as cur:
        if datasource_id:
            cur.execute("""
                SELECT id, datasource_id, status, progress, current_step, message, error_message
                FROM learning_task
                WHERE datasource_id = %s
                ORDER BY created_at DESC
                LIMIT 20
            """, (datasource_id,))
        else:
            cur.execute("""
                SELECT id, datasource_id, status, progress, current_step, message, error_message
                FROM learning_task
                ORDER BY created_at DESC
                LIMIT 20
            """)

        rows = cur.fetchall()

        return [
            LearningProgress(
                task_id=row["id"],
                datasource_id=row["datasource_id"],
                status=row["status"],
                progress=row["progress"],
                current_step=row["current_step"],
                message=row["message"],
                error=row["error_message"],
            )
            for row in rows
        ]