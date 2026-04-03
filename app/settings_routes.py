"""
系统设置 API 路由。
包含 AI 模型配置、数据源配置、知识库配置的管理接口。
"""
from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .config_service import (
    AIModelConfig,
    DataSourceConfig,
    list_ai_configs,
    list_datasource_configs,
    get_datasource_by_id,
)
from .datasource_manager import (
    test_datasource_connection,
    get_datasource_tables,
    get_table_columns,
    preview_table_data,
)
from .knowledge_manager import (
    create_knowledge,
    get_knowledge_by_id,
    list_knowledge,
    update_knowledge,
    delete_knowledge,
    batch_import_knowledge,
    list_knowledge_types,
    get_knowledge_type_info,
)
from .mysql_tools import get_mysql_connection


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
                "api_key": "***" if c.api_key else None,  # 隐藏 API Key
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
            req.api_key,
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
        params.append(req.api_key)

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
        cur.execute(f"""
            UPDATE ai_model_config
            SET {", ".join(updates)}
            WHERE id = %s
        """, params)
        conn.commit()

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="配置不存在")

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
    from .config_service import get_query_datasource

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