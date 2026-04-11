"""
系统设置 API 路由。
包含 AI 模型配置、数据源配置、知识库配置的管理接口。
"""
from __future__ import annotations

import json
import time
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.config_service import (
    AIModelConfig,
    DataSourceConfig,
    list_ai_configs,
    list_datasource_configs,
    get_datasource_by_id,
)
from app.core.datasource_manager import (
    test_datasource_connection,
    get_datasource_tables,
    get_table_columns,
    preview_table_data,
)
from app.schema.knowledge_manager import (
    create_knowledge,
    get_knowledge_by_id,
    list_knowledge,
    update_knowledge,
    delete_knowledge,
    batch_import_knowledge,
    list_knowledge_types,
    get_knowledge_type_info,
)
from app.core.mysql_tools import get_mysql_connection


router = APIRouter(prefix="/settings", tags=["settings"])


# ============ Request/Response Models ============

class AIConfigCreateRequest(BaseModel):
    config_name: str = Field(..., min_length=1, max_length=100)
    provider: str = Field(..., pattern="^(openai|anthropic|deepseek|custom)$")
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: str = Field(..., min_length=1)
    extra_params: dict[str, Any] = Field(default_factory=dict)


class AIConfigUpdateRequest(BaseModel):
    config_name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    extra_params: Optional[dict[str, Any]] = None


class DataSourceCreateRequest(BaseModel):
    ds_name: str = Field(..., min_length=1, max_length=100)
    ds_type: str = Field(..., pattern="^(postgresql|mysql|sqlite)$")
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    dsn_override: Optional[str] = None
    extra_params: dict[str, Any] = Field(default_factory=dict)


class DataSourceUpdateRequest(BaseModel):
    ds_name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    dsn_override: Optional[str] = None
    extra_params: Optional[dict[str, Any]] = None


class KnowledgeCreateRequest(BaseModel):
    kb_type: str = Field(..., pattern="^(term|qa|metric|table_desc)$")
    kb_name: str = Field(..., min_length=1, max_length=100)
    kb_content: Optional[str] = None
    kb_metadata: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class KnowledgeUpdateRequest(BaseModel):
    kb_name: Optional[str] = None
    kb_content: Optional[str] = None
    kb_metadata: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class KnowledgeImportRequest(BaseModel):
    items: list[dict[str, Any]]


# ============ AI 配置 API ============

@router.get("/ai")
def api_list_ai_configs():
    """列出所有 AI 模型配置"""
    configs = list_ai_configs()
    active = next((c for c in configs if c.is_active), None)

    return {
        "items": [
            {
                "id": c.id,
                "config_name": c.config_name,
                "provider": c.provider,
                "base_url": c.base_url,
                "api_key": None,  # 不返回实际值，由前端按需获取
                "has_api_key": bool(c.api_key),  # 标记是否已配置
                "model_name": c.model_name,
                "is_active": c.is_active,
                "extra_params": c.extra_params,
            }
            for c in configs
        ],
        "active": {
            "id": active.id,
            "config_name": active.config_name,
            "provider": active.provider,
            "model_name": active.model_name,
        } if active else None,
    }


@router.get("/ai/{config_id}/api-key")
def api_get_ai_config_api_key(config_id: int):
    """获取 AI 配置的 API Key（用于前端显示已保存的密钥）"""
    conn = get_mysql_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT api_key FROM ai_model_config WHERE id = %s", (config_id,))
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="配置不存在")

    return {"api_key": row["api_key"] or ""}


@router.post("/ai")
def api_create_ai_config(req: AIConfigCreateRequest):
    """创建新的 AI 模型配置"""
    conn = get_mysql_connection()
    with conn.cursor() as cur:
        # 检查名称是否重复
        cur.execute("SELECT id FROM ai_model_config WHERE config_name = %s", (req.config_name,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="配置名称已存在")

        cur.execute("""
            INSERT INTO ai_model_config
            (config_name, provider, base_url, api_key, model_name, is_active, extra_params)
            VALUES (%s, %s, %s, %s, %s, 0, %s)
        """, (
            req.config_name,
            req.provider,
            req.base_url,
            req.api_key.strip() if req.api_key else None,  # 去除首尾空格
            req.model_name,
            json.dumps(req.extra_params, ensure_ascii=False),
        ))
        conn.commit()

        config_id = cur.lastrowid

    return {
        "id": config_id,
        "config_name": req.config_name,
        "provider": req.provider,
        "base_url": req.base_url,
        "model_name": req.model_name,
    }


@router.patch("/ai/{config_id}")
def api_update_ai_config(config_id: int, req: AIConfigUpdateRequest):
    """更新 AI 模型配置"""
    conn = get_mysql_connection()

    updates = []
    params = []

    if req.config_name is not None:
        updates.append("config_name = %s")
        params.append(req.config_name)

    if req.base_url is not None:
        updates.append("base_url = %s")
        params.append(req.base_url)

    if req.api_key is not None:
        updates.append("api_key = %s")
        params.append(req.api_key.strip())  # 去除首尾空格

    if req.model_name is not None:
        updates.append("model_name = %s")
        params.append(req.model_name)

    if req.extra_params is not None:
        updates.append("extra_params = %s")
        params.append(json.dumps(req.extra_params, ensure_ascii=False))

    if not updates:
        raise HTTPException(status_code=400, detail="没有要更新的字段")

    params.append(config_id)

    with conn.cursor() as cur:
        # 先检查记录是否存在（MySQL UPDATE 在值不变时 rowcount 会返回 0）
        cur.execute("SELECT id FROM ai_model_config WHERE id = %s", (config_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="配置不存在")

        cur.execute(f"""
            UPDATE ai_model_config
            SET {", ".join(updates)}
            WHERE id = %s
        """, params)
        conn.commit()

        cur.execute("SELECT * FROM ai_model_config WHERE id = %s", (config_id,))
        row = cur.fetchone()

    return {
        "id": row["id"],
        "config_name": row["config_name"],
        "provider": row["provider"],
        "base_url": row["base_url"],
        "model_name": row["model_name"],
        "is_active": bool(row["is_active"]),
    }


@router.delete("/ai/{config_id}")
def api_delete_ai_config(config_id: int):
    """删除 AI 模型配置"""
    conn = get_mysql_connection()
    with conn.cursor() as cur:
        # 检查是否为激活配置
        cur.execute("SELECT is_active FROM ai_model_config WHERE id = %s", (config_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="配置不存在")

        if row["is_active"]:
            raise HTTPException(status_code=400, detail="无法删除激活中的配置")

        cur.execute("DELETE FROM ai_model_config WHERE id = %s", (config_id,))
        conn.commit()

    return {"success": True, "message": "配置已删除"}


@router.post("/ai/{config_id}/activate")
def api_activate_ai_config(config_id: int):
    """激活指定 AI 配置"""
    conn = get_mysql_connection()
    with conn.cursor() as cur:
        # 检查配置是否存在
        cur.execute("SELECT id FROM ai_model_config WHERE id = %s", (config_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="配置不存在")

        # 取消所有激活
        cur.execute("UPDATE ai_model_config SET is_active = 0")

        # 激活指定配置
        cur.execute("UPDATE ai_model_config SET is_active = 1 WHERE id = %s", (config_id,))
        conn.commit()

    return {"success": True, "message": "配置已激活"}


class AITestRequest(BaseModel):
    """LLM 连接测试请求（可选参数覆盖）"""
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None


@router.post("/ai/{config_id}/test")
def api_test_ai_config(config_id: int, req: Optional[AITestRequest] = None):
    """
    测试 AI 模型配置连接

    发送一个简单的测试请求验证：
    - API Key 是否有效
    - base_url 是否可达
    - 模型是否可用

    支持 OpenAI、Anthropic、DeepSeek 等协议
    """
    from app.core.llm_provider import create_llm
    from app.core.config_service import AIModelConfig

    # 从数据库获取配置
    conn = get_mysql_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, config_name, provider, base_url, api_key,
                   model_name, is_active, extra_params
            FROM ai_model_config
            WHERE id = %s
        """, (config_id,))
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="配置不存在")

    # 构建配置对象（允许请求参数覆盖）
    base_url = req.base_url if req and req.base_url else row["base_url"]
    api_key = req.api_key if req and req.api_key else row["api_key"]
    model_name = req.model_name if req and req.model_name else row["model_name"]

    config = AIModelConfig(
        id=row["id"],
        config_name=row["config_name"],
        provider=row["provider"],
        base_url=base_url,
        api_key=api_key,
        model_name=model_name,
        extra_params=json.loads(row["extra_params"] or "{}"),
    )

    # 执行测试
    return _test_llm_connection(config)


def _test_llm_connection(config: AIModelConfig) -> dict:
    """
    测试 LLM 连接的实际逻辑

    发送简单的 prompt 测试模型响应
    """
    provider = config.provider.lower()
    start_time = time.time()

    try:
        if provider == "mock":
            return {
                "success": True,
                "message": "Mock 模式，无需连接测试",
                "provider": provider,
                "model": config.model_name,
                "latency_ms": 0,
                "response_preview": "规则引擎模式",
            }

        if provider in ("openai", "deepseek", "custom"):
            return _test_openai_compatible(config, start_time)

        elif provider == "anthropic":
            return _test_anthropic(config, start_time)

        else:
            return {
                "success": False,
                "message": f"不支持的提供商: {provider}",
                "provider": provider,
                "latency_ms": int((time.time() - start_time) * 1000),
            }

    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "provider": provider,
            "model": config.model_name,
            "latency_ms": int((time.time() - start_time) * 1000),
        }


def _test_openai_compatible(config: AIModelConfig, start_time: float) -> dict:
    """测试 OpenAI 兼容协议（OpenAI、DeepSeek、Custom）"""
    from openai import OpenAI

    if not config.api_key:
        return {
            "success": False,
            "message": "API Key 未配置",
            "provider": config.provider,
            "latency_ms": int((time.time() - start_time) * 1000),
        }

    # 设置 base_url
    base_url = config.base_url
    if config.provider == "deepseek" and not base_url:
        base_url = "https://api.deepseek.com/v1"

    if config.provider == "openai" and not base_url:
        base_url = "https://api.openai.com/v1"

    if not base_url:
        return {
            "success": False,
            "message": "API Base URL 未配置",
            "provider": config.provider,
            "latency_ms": int((time.time() - start_time) * 1000),
        }

    # 创建客户端并发送测试请求
    client = OpenAI(
        api_key=config.api_key,
        base_url=base_url,
        timeout=30.0,
    )

    response = client.chat.completions.create(
        model=config.model_name,
        messages=[{"role": "user", "content": "Hello, this is a connection test. Please respond with 'OK'."}],
        max_tokens=10,
    )

    latency_ms = int((time.time() - start_time) * 1000)
    content = response.choices[0].message.content or ""

    return {
        "success": True,
        "message": f"连接成功，模型响应正常",
        "provider": config.provider,
        "model": config.model_name,
        "base_url": base_url,
        "latency_ms": latency_ms,
        "response_preview": content[:100],
        "tokens_used": {
            "prompt": response.usage.prompt_tokens,
            "completion": response.usage.completion_tokens,
            "total": response.usage.total_tokens,
        },
    }


def _test_anthropic(config: AIModelConfig, start_time: float) -> dict:
    """测试 Anthropic Claude 协议"""
    from anthropic import Anthropic

    if not config.api_key:
        return {
            "success": False,
            "message": "API Key 未配置",
            "provider": "anthropic",
            "latency_ms": int((time.time() - start_time) * 1000),
        }

    # 支持自定义 base_url（如阿里云 GLM）
    client_kwargs = {
        "api_key": config.api_key,
        "timeout": 30.0,
    }
    if config.base_url:
        client_kwargs["base_url"] = config.base_url

    client = Anthropic(**client_kwargs)

    response = client.messages.create(
        model=config.model_name,
        max_tokens=10,
        messages=[{"role": "user", "content": "Hello, this is a connection test. Please respond with 'OK'."}],
    )

    latency_ms = int((time.time() - start_time) * 1000)

    # 安全解析响应内容（支持 ThinkingBlock 等）
    content = ""
    if response.content:
        for block in response.content:
            # TextBlock 有 text 属性
            if hasattr(block, "text"):
                content += block.text
            # ThinkingBlock 有 thinking 属性
            elif hasattr(block, "thinking"):
                content += block.thinking

    return {
        "success": True,
        "message": f"连接成功，模型响应正常",
        "provider": "anthropic",
        "model": config.model_name,
        "latency_ms": latency_ms,
        "response_preview": content[:100],
        "tokens_used": {
            "prompt": response.usage.input_tokens,
            "completion": response.usage.output_tokens,
            "total": response.usage.input_tokens + response.usage.output_tokens,
        },
    }


# ============ 数据源 API ============

@router.get("/datasource")
def api_list_datasources():
    """列出所有数据源配置"""
    configs = list_datasource_configs()

    return {
        "items": [
            {
                "id": c.id,
                "ds_name": c.ds_name,
                "ds_type": c.ds_type,
                "host": c.host,
                "port": c.port,
                "database": c.database,
                "username": c.username,
                "is_query_target": c.is_query_target,
            }
            for c in configs
        ],
    }


@router.get("/datasource/active")
def api_get_active_datasource():
    """获取当前用于问数的数据源（优先级：MySQL配置表 > .env）"""
    from app.core.config_service import get_query_datasource

    config = get_query_datasource()

    if not config or not config.get_dsn():
        return {
            "datasource": None,
            "message": "未配置数据源，请先在系统设置中添加数据源或配置 .env 文件中的 POSTGRES_DSN",
        }

    return {
        "datasource": {
            "id": config.id,
            "ds_name": config.ds_name or ".env 默认数据源",
            "ds_type": config.ds_type,
            "host": config.host,
            "port": config.port,
            "database": config.database,
            "is_from_env": config.id is None,  # 标识是否来自 .env
        },
        "message": None,
    }


@router.post("/datasource")
def api_create_datasource(req: DataSourceCreateRequest):
    """创建新数据源配置"""
    conn = get_mysql_connection()
    with conn.cursor() as cur:
        # 检查名称是否重复
        cur.execute("SELECT id FROM datasource_config WHERE ds_name = %s", (req.ds_name,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="数据源名称已存在")

        cur.execute("""
            INSERT INTO datasource_config
            (ds_name, ds_type, host, port, `database`, username, password, dsn_override, is_query_target, extra_params)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, %s)
        """, (
            req.ds_name,
            req.ds_type,
            req.host,
            req.port,
            req.database,
            req.username,
            req.password,
            req.dsn_override,
            json.dumps(req.extra_params, ensure_ascii=False),
        ))
        conn.commit()

        ds_id = cur.lastrowid

    return {
        "id": ds_id,
        "ds_name": req.ds_name,
        "ds_type": req.ds_type,
    }


@router.get("/datasource/{ds_id}")
def api_get_datasource(ds_id: int):
    """获取单个数据源详情"""
    config = get_datasource_by_id(ds_id)
    if not config:
        raise HTTPException(status_code=404, detail="数据源不存在")

    return {
        "id": config.id,
        "ds_name": config.ds_name,
        "ds_type": config.ds_type,
        "host": config.host,
        "port": config.port,
        "database": config.database,
        "username": config.username,
        "is_query_target": config.is_query_target,
        "extra_params": config.extra_params,
    }


@router.patch("/datasource/{ds_id}")
def api_update_datasource(ds_id: int, req: DataSourceUpdateRequest):
    """更新数据源配置"""
    conn = get_mysql_connection()

    updates = []
    params = []

    if req.ds_name is not None:
        updates.append("ds_name = %s")
        params.append(req.ds_name)

    if req.host is not None:
        updates.append("host = %s")
        params.append(req.host)

    if req.port is not None:
        updates.append("port = %s")
        params.append(req.port)

    if req.database is not None:
        updates.append("`database` = %s")
        params.append(req.database)

    if req.username is not None:
        updates.append("username = %s")
        params.append(req.username)

    if req.password is not None:
        updates.append("password = %s")
        params.append(req.password)

    if req.dsn_override is not None:
        updates.append("dsn_override = %s")
        params.append(req.dsn_override)

    if req.extra_params is not None:
        updates.append("extra_params = %s")
        params.append(json.dumps(req.extra_params, ensure_ascii=False))

    if not updates:
        raise HTTPException(status_code=400, detail="没有要更新的字段")

    params.append(ds_id)

    with conn.cursor() as cur:
        cur.execute(f"""
            UPDATE datasource_config
            SET {", ".join(updates)}
            WHERE id = %s
        """, params)
        conn.commit()

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="数据源不存在")

    return api_get_datasource(ds_id)


@router.delete("/datasource/{ds_id}")
def api_delete_datasource(ds_id: int):
    """删除数据源配置"""
    conn = get_mysql_connection()
    with conn.cursor() as cur:
        # 检查是否为问数目标
        cur.execute("SELECT is_query_target FROM datasource_config WHERE id = %s", (ds_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="数据源不存在")

        if row["is_query_target"]:
            raise HTTPException(status_code=400, detail="无法删除正在使用的问数目标数据源")

        cur.execute("DELETE FROM datasource_config WHERE id = %s", (ds_id,))
        conn.commit()

    return {"success": True, "message": "数据源已删除"}


@router.post("/datasource/{ds_id}/test")
def api_test_datasource(ds_id: int):
    """测试数据源连接"""
    config = get_datasource_by_id(ds_id)
    if not config:
        raise HTTPException(status_code=404, detail="数据源不存在")

    result = test_datasource_connection(config)
    return result


@router.post("/datasource/{ds_id}/activate-query")
def api_set_query_datasource(ds_id: int):
    """设置指定数据源为问数查询目标"""
    conn = get_mysql_connection()
    with conn.cursor() as cur:
        # 检查数据源是否存在
        cur.execute("SELECT id FROM datasource_config WHERE id = %s", (ds_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="数据源不存在")

        # 取消所有问数目标
        cur.execute("UPDATE datasource_config SET is_query_target = 0")

        # 设置指定数据源为问数目标
        cur.execute("UPDATE datasource_config SET is_query_target = 1 WHERE id = %s", (ds_id,))
        conn.commit()

    return {"success": True, "message": "已设置为问数目标"}


@router.get("/datasource/{ds_id}/tables")
def api_get_datasource_tables(ds_id: int):
    """获取数据源的表列表"""
    config = get_datasource_by_id(ds_id)
    if not config:
        raise HTTPException(status_code=404, detail="数据源不存在")

    tables = get_datasource_tables(config)
    return {"items": tables, "total": len(tables)}


@router.get("/datasource/{ds_id}/table/{table_name}")
def api_get_table_info(ds_id: int, table_name: str):
    """获取表的字段信息"""
    config = get_datasource_by_id(ds_id)
    if not config:
        raise HTTPException(status_code=404, detail="数据源不存在")

    columns = get_table_columns(config, table_name)
    return {"table_name": table_name, "columns": columns}


@router.get("/datasource/{ds_id}/table/{table_name}/preview")
def api_preview_table(ds_id: int, table_name: str, limit: int = Query(100, ge=1, le=1000)):
    """预览表数据"""
    config = get_datasource_by_id(ds_id)
    if not config:
        raise HTTPException(status_code=404, detail="数据源不存在")

    result = preview_table_data(config, table_name, limit)
    return result


# ============ 知识库 API ============

@router.get("/knowledge/types")
def api_list_knowledge_types():
    """列出知识类型"""
    return {"items": list_knowledge_types()}


@router.get("/datasource/{ds_id}/knowledge")
def api_list_knowledge(
    ds_id: int,
    kb_type: Optional[str] = Query(None, pattern="^(term|qa|metric|table_desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """列出数据源的知识项"""
    result = list_knowledge(
        datasource_id=ds_id,
        kb_type=kb_type,
        is_active=None,
        page=page,
        page_size=page_size,
    )
    return result


@router.post("/datasource/{ds_id}/knowledge")
def api_create_knowledge(ds_id: int, req: KnowledgeCreateRequest):
    """创建知识项"""
    # 验证数据源存在
    config = get_datasource_by_id(ds_id)
    if not config:
        raise HTTPException(status_code=404, detail="数据源不存在")

    result = create_knowledge(
        datasource_id=ds_id,
        kb_type=req.kb_type,
        kb_name=req.kb_name,
        kb_content=req.kb_content,
        kb_metadata=req.kb_metadata,
        is_active=req.is_active,
    )
    return result


@router.get("/datasource/{ds_id}/knowledge/{knowledge_id}")
def api_get_knowledge(ds_id: int, knowledge_id: int):
    """获取单个知识项"""
    knowledge = get_knowledge_by_id(knowledge_id)
    if not knowledge or knowledge["datasource_id"] != ds_id:
        raise HTTPException(status_code=404, detail="知识项不存在")

    return knowledge


@router.patch("/datasource/{ds_id}/knowledge/{knowledge_id}")
def api_update_knowledge(ds_id: int, knowledge_id: int, req: KnowledgeUpdateRequest):
    """更新知识项"""
    # 验证知识项属于该数据源
    knowledge = get_knowledge_by_id(knowledge_id)
    if not knowledge or knowledge["datasource_id"] != ds_id:
        raise HTTPException(status_code=404, detail="知识项不存在")

    result = update_knowledge(
        knowledge_id=knowledge_id,
        kb_name=req.kb_name,
        kb_content=req.kb_content,
        kb_metadata=req.kb_metadata,
        is_active=req.is_active,
    )
    return result


@router.delete("/datasource/{ds_id}/knowledge/{knowledge_id}")
def api_delete_knowledge(ds_id: int, knowledge_id: int):
    """删除知识项"""
    # 验证知识项属于该数据源
    knowledge = get_knowledge_by_id(knowledge_id)
    if not knowledge or knowledge["datasource_id"] != ds_id:
        raise HTTPException(status_code=404, detail="知识项不存在")

    success = delete_knowledge(knowledge_id)
    return {"success": success, "message": "知识项已删除"}


@router.post("/datasource/{ds_id}/knowledge/import")
def api_import_knowledge(ds_id: int, req: KnowledgeImportRequest):
    """批量导入知识"""
    # 验证数据源存在
    config = get_datasource_by_id(ds_id)
    if not config:
        raise HTTPException(status_code=404, detail="数据源不存在")

    result = batch_import_knowledge(
        datasource_id=ds_id,
        items=req.items,
    )
    return result


# ============ Schema 学习 API ============

@router.post("/datasource/{ds_id}/learn")
def api_trigger_schema_learning(ds_id: int):
    """
    触发数据库 Schema 学习

    流程：
    1. 验证数据源存在且可连接
    2. 执行学习任务
    3. 返回任务 ID 供查询进度
    """
    from .learning_service import LearningService

    # 验证数据源
    config = get_datasource_by_id(ds_id)
    if not config:
        raise HTTPException(status_code=404, detail="数据源不存在")

    # 测试连接
    test_result = test_datasource_connection(config)
    if not test_result.get("success"):
        raise HTTPException(status_code=400, detail=f"数据源连接失败: {test_result.get('message')}")

    # 开始学习
    try:
        service = LearningService(ds_id)
        progress = service.start_learning()

        return {
            "success": True,
            "task_id": progress.task_id,
            "status": progress.status,
            "message": progress.message,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"学习失败: {str(e)}")


@router.get("/learning/{task_id}")
def api_get_learning_progress(task_id: int):
    """查询 Schema 学习进度"""
    from .learning_service import get_learning_progress

    progress = get_learning_progress(task_id)
    if not progress:
        raise HTTPException(status_code=404, detail="任务不存在")

    return {
        "task_id": progress.task_id,
        "datasource_id": progress.datasource_id,
        "status": progress.status,
        "progress": progress.progress,
        "current_step": progress.current_step,
        "message": progress.message,
        "error": progress.error,
    }


@router.get("/learning/tasks")
def api_list_learning_tasks(
    datasource_id: Optional[int] = Query(None),
):
    """列出学习任务"""
    from .learning_service import list_learning_tasks

    tasks = list_learning_tasks(datasource_id)
    return {
        "items": [
            {
                "task_id": t.task_id,
                "datasource_id": t.datasource_id,
                "status": t.status,
                "progress": t.progress,
                "current_step": t.current_step,
                "message": t.message,
                "error": t.error,
            }
            for t in tasks
        ],
    }


@router.get("/datasource/{ds_id}/schema")
def api_get_schema_cache(ds_id: int):
    """获取数据源的 Schema 缓存"""
    from .learning_service import get_schema_cache

    cache = get_schema_cache(ds_id)
    if not cache:
        raise HTTPException(status_code=404, detail="Schema 缓存不存在，请先执行学习")

    return cache


@router.get("/datasource/{ds_id}/schema/tables")
def api_get_schema_tables(ds_id: int):
    """获取数据源的表级 Schema 信息"""
    from .learning_service import get_schema_cache

    cache = get_schema_cache(ds_id)
    if not cache:
        raise HTTPException(status_code=404, detail="Schema 缓存不存在，请先执行学习")

    schema_json = cache.get("schema_json", {})
    tables = schema_json.get("tables", {})

    return {
        "items": [
            {
                "name": name,
                "comment": info.get("comment"),
                "table_type": info.get("table_type"),
                "primary_keys": info.get("primary_keys", []),
                "field_count": len(info.get("fields", {})),
            }
            for name, info in tables.items()
        ],
        "total": len(tables),
    }


@router.get("/datasource/{ds_id}/schema/tables/{table_name}")
def api_get_table_schema(ds_id: int, table_name: str):
    """获取单表的 Schema 信息"""
    from .learning_service import get_schema_cache

    cache = get_schema_cache(ds_id)
    if not cache:
        raise HTTPException(status_code=404, detail="Schema 缓存不存在，请先执行学习")

    schema_json = cache.get("schema_json", {})
    tables = schema_json.get("tables", {})

    if table_name not in tables:
        raise HTTPException(status_code=404, detail=f"表 {table_name} 不存在")

    table_info = tables[table_name]

    return {
        "name": table_name,
        "comment": table_info.get("comment"),
        "table_type": table_info.get("table_type"),
        "primary_keys": table_info.get("primary_keys", []),
        "fields": [
            {
                "name": fname,
                "type": finfo.get("type"),
                "primary_key": finfo.get("primary_key"),
                "nullable": finfo.get("nullable"),
                "comment": finfo.get("comment"),
                "category": finfo.get("category"),
                "dim_or_meas": finfo.get("dim_or_meas"),
                "date_min_gran": finfo.get("date_min_gran"),
                "examples": finfo.get("examples", []),
            }
            for fname, finfo in table_info.get("fields", {}).items()
        ],
    }


@router.delete("/datasource/{ds_id}/schema/cache")
def api_clear_schema_cache(ds_id: int):
    """
    清空数据源的 Schema 缓存

    删除 schema_cache 表中的记录，允许重新学习
    """
    from .mysql_tools import get_mysql_connection

    conn = get_mysql_connection()
    with conn.cursor() as cur:
        # 检查是否存在
        cur.execute("""
            SELECT id FROM schema_cache WHERE datasource_id = %s
        """, (ds_id,))
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Schema 缓存不存在")

        # 删除缓存
        cur.execute("""
            DELETE FROM schema_cache WHERE datasource_id = %s
        """, (ds_id,))
        conn.commit()

    return {"success": True, "message": "Schema 缓存已清空"}


@router.post("/datasource/{ds_id}/schema/relearn")
def api_relearn_schema(ds_id: int):
    """
    清空并重新学习 Schema

    先清空现有缓存，然后启动新的学习任务
    """
    from .mysql_tools import get_mysql_connection
    from .learning_service import trigger_schema_learning

    # 清空现有缓存
    conn = get_mysql_connection()
    with conn.cursor() as cur:
        cur.execute("""
            DELETE FROM schema_cache WHERE datasource_id = %s
        """, (ds_id,))
        conn.commit()

    # 启动新的学习任务
    result = trigger_schema_learning(ds_id)

    return {
        "success": result.get("success", False),
        "task_id": result.get("task_id"),
        "message": "已清空历史学习内容，正在重新学习",
    }