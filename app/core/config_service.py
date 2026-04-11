"""
配置服务：统一管理 AI 模型、数据源、知识库配置。
优先级：MySQL 配置表 > .env 文件 > 硬编码默认值
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.mysql_tools import get_mysql_connection


# ============ 配置数据类 ============

@dataclass
class AIModelConfig:
    """AI 模型配置"""
    id: Optional[int] = None
    config_name: str = ""
    provider: str = "openai"  # openai/anthropic/deepseek/custom
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: str = "gpt-4o-mini"
    is_active: bool = False
    thinking_mode: bool = False  # 是否为思考模式（不支持 tool_choice）
    extra_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class DataSourceConfig:
    """数据源配置"""
    id: Optional[int] = None
    ds_name: str = ""
    ds_type: str = "postgresql"  # postgresql/mysql/sqlite
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    dsn_override: Optional[str] = None
    is_query_target: bool = False
    extra_params: dict[str, Any] = field(default_factory=dict)

    def get_dsn(self) -> str:
        """构建完整 DSN"""
        if self.dsn_override:
            return self.dsn_override

        if self.ds_type == "postgresql":
            port = self.port or 5432
            return f"postgresql://{self.username or 'postgres'}:{self.password or ''}@{self.host or 'localhost'}:{port}/{self.database or 'postgres'}"

        elif self.ds_type == "mysql":
            port = self.port or 3306
            return f"mysql://{self.username or 'root'}:{self.password or ''}@{self.host or 'localhost'}:{port}/{self.database or 'test'}"

        elif self.ds_type == "sqlite":
            return self.database or ":memory:"  # SQLite 使用 database 作为文件路径

        return ""


@dataclass
class KnowledgeConfig:
    """知识库配置"""
    id: Optional[int] = None
    datasource_id: int = 0
    kb_type: str = "term"  # term/qa/metric/table_desc
    kb_name: str = ""
    kb_content: Optional[str] = None
    kb_metadata: dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


# ============ AI 配置读取 ============

def get_active_ai_config() -> AIModelConfig:
    """
    获取当前激活的 AI 模型配置。
    优先级：MySQL 配置表 > .env 文件 > 硬编码默认值
    """
    # Level 1: MySQL 配置表
    mysql_config = _fetch_active_ai_config_from_mysql()
    if mysql_config:
        return mysql_config

    # Level 2: .env 文件
    env_config = _get_ai_config_from_env()
    if env_config.api_key:
        return env_config

    # Level 3: 硬编码默认值（Mock 模式）
    return AIModelConfig(
        provider="mock",
        model_name="mock",
        is_active=True,
    )


def _fetch_active_ai_config_from_mysql() -> Optional[AIModelConfig]:
    """从 MySQL 配置表读取激活的 AI 配置"""
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, config_name, provider, base_url, api_key,
                       model_name, is_active, extra_params
                FROM ai_model_config
                WHERE is_active = 1
                LIMIT 1
            """)
            row = cur.fetchone()
            if row:
                extra_params = json.loads(row['extra_params'] or '{}')
                # thinking_mode 可以从 extra_params 或单独字段读取
                thinking_mode = extra_params.get('thinking_mode', False)
                # 某些端点默认启用思考模式（如 DashScope Anthropic 兼容端点）
                base_url = row['base_url'] or ''
                if 'dashscope.aliyuncs.com' in base_url:
                    thinking_mode = True

                return AIModelConfig(
                    id=row['id'],
                    config_name=row['config_name'],
                    provider=row['provider'],
                    base_url=row['base_url'],
                    api_key=row['api_key'],
                    model_name=row['model_name'],
                    is_active=bool(row['is_active']),
                    thinking_mode=thinking_mode,
                    extra_params=extra_params,
                )
    except Exception:
        pass
    return None


def _get_ai_config_from_env() -> AIModelConfig:
    """从环境变量获取默认 AI 配置"""
    provider = os.getenv("AI_PROVIDER", "openai")
    return AIModelConfig(
        config_name=".env 默认配置",
        provider=provider,
        base_url=os.getenv("OPENAI_API_BASE"),
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        is_active=True,
        extra_params={"temperature": 0},
    )


# ============ 数据源配置读取 ============

def get_query_datasource() -> DataSourceConfig:
    """
    获取用于问数查询的数据源配置。
    优先级：MySQL 配置表 is_query_target=1 > .env POSTGRES_DSN
    """
    # Level 1: MySQL 配置表
    mysql_ds = _fetch_query_datasource_from_mysql()
    if mysql_ds:
        return mysql_ds

    # Level 2: .env 文件
    env_ds = _get_datasource_from_env()
    if env_ds.get_dsn():
        return env_ds

    return DataSourceConfig()


def _fetch_query_datasource_from_mysql() -> Optional[DataSourceConfig]:
    """从 MySQL 配置表读取问数数据源"""
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, ds_name, ds_type, host, port, `database`,
                       username, password, dsn_override, is_query_target, extra_params
                FROM datasource_config
                WHERE is_query_target = 1
                LIMIT 1
            """)
            row = cur.fetchone()
            if row:
                return DataSourceConfig(
                    id=row['id'],
                    ds_name=row['ds_name'],
                    ds_type=row['ds_type'],
                    host=row['host'],
                    port=row['port'],
                    database=row['database'],
                    username=row['username'],
                    password=row['password'],
                    dsn_override=row['dsn_override'],
                    is_query_target=bool(row['is_query_target']),
                    extra_params=json.loads(row['extra_params'] or '{}'),
                )
    except Exception:
        pass
    return None


def _get_datasource_from_env() -> DataSourceConfig:
    """从环境变量获取默认数据源配置"""
    dsn = os.getenv("POSTGRES_DSN", "")
    if not dsn:
        return DataSourceConfig()

    # 解析 DSN: postgresql://user:pass@host:port/database
    return DataSourceConfig(
        ds_name=".env 默认数据源",
        ds_type="postgresql",
        dsn_override=dsn,
        is_query_target=True,
    )


def get_datasource_by_id(ds_id: int) -> Optional[DataSourceConfig]:
    """根据 ID 获取数据源配置"""
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, ds_name, ds_type, host, port, `database`,
                       username, password, dsn_override, is_query_target, extra_params
                FROM datasource_config
                WHERE id = %s
            """, (ds_id,))
            row = cur.fetchone()
            if row:
                return DataSourceConfig(
                    id=row['id'],
                    ds_name=row['ds_name'],
                    ds_type=row['ds_type'],
                    host=row['host'],
                    port=row['port'],
                    database=row['database'],
                    username=row['username'],
                    password=row['password'],
                    dsn_override=row['dsn_override'],
                    is_query_target=bool(row['is_query_target']),
                    extra_params=json.loads(row['extra_params'] or '{}'),
                )
    except Exception:
        pass
    return None


def get_datasource_by_name(ds_name: str) -> Optional[DataSourceConfig]:
    """根据名称获取数据源配置"""
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, ds_name, ds_type, host, port, `database`,
                       username, password, dsn_override, is_query_target, extra_params
                FROM datasource_config
                WHERE ds_name = %s
            """, (ds_name,))
            row = cur.fetchone()
            if row:
                return DataSourceConfig(
                    id=row['id'],
                    ds_name=row['ds_name'],
                    ds_type=row['ds_type'],
                    host=row['host'],
                    port=row['port'],
                    database=row['database'],
                    username=row['username'],
                    password=row['password'],
                    dsn_override=row['dsn_override'],
                    is_query_target=bool(row['is_query_target']),
                    extra_params=json.loads(row['extra_params'] or '{}'),
                )
    except Exception:
        pass
    return None


# ============ 配置列表查询 ============

def list_ai_configs() -> list[AIModelConfig]:
    """列出所有 AI 配置"""
    configs = []
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, config_name, provider, base_url, api_key,
                       model_name, is_active, extra_params
                FROM ai_model_config
                ORDER BY is_active DESC, created_at DESC
            """)
            for row in cur.fetchall():
                configs.append(AIModelConfig(
                    id=row['id'],
                    config_name=row['config_name'],
                    provider=row['provider'],
                    base_url=row['base_url'],
                    api_key=row['api_key'],
                    model_name=row['model_name'],
                    is_active=bool(row['is_active']),
                    extra_params=json.loads(row['extra_params'] or '{}'),
                ))
    except Exception:
        pass
    return configs


def list_datasource_configs() -> list[DataSourceConfig]:
    """列出所有数据源配置"""
    configs = []
    try:
        conn = get_mysql_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, ds_name, ds_type, host, port, `database`,
                       username, password, dsn_override, is_query_target, extra_params
                FROM datasource_config
                ORDER BY is_query_target DESC, created_at DESC
            """)
            for row in cur.fetchall():
                configs.append(DataSourceConfig(
                    id=row['id'],
                    ds_name=row['ds_name'],
                    ds_type=row['ds_type'],
                    host=row['host'],
                    port=row['port'],
                    database=row['database'],
                    username=row['username'],
                    password=row['password'],
                    dsn_override=row['dsn_override'],
                    is_query_target=bool(row['is_query_target']),
                    extra_params=json.loads(row['extra_params'] or '{}'),
                ))
    except Exception:
        pass
    return configs