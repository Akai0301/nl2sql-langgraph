---
name: error-handler
description: |
  后端异常处理规范。包含 FastAPI 异常处理、参数校验、日志规范、数据库异常处理。

  触发场景：
  - 抛出业务异常（HTTPException）
  - 全局异常处理器配置
  - 参数校验异常处理
  - 日志记录规范
  - 数据库异常处理（psycopg/PyMySQL）
  - LangGraph 节点异常处理

  触发词：异常、HTTPException、raise、错误处理、全局异常、参数校验、日志、logger、错误码、try-except、异常捕获
---

# 后端异常处理指南

> **适用于**: nl2sql-langgraph 后端（FastAPI + psycopg + PyMySQL + LangGraph）

---

## 快速索引

| 场景 | 推荐方式 |
|------|---------|
| 业务异常 | `raise HTTPException(status_code=400, detail='用户不存在')` |
| 参数校验 | Pydantic 自动校验 或 手动校验 |
| 数据库异常 | `psycopg.errors` 或 `pymysql.MySQLError` |
| 日志记录 | `logger.error(msg, exc_info=True)` |
| LangGraph 节点异常 | 返回带 error 字段的 State |

---

## 1. 业务异常 - HTTPException

### 基本用法

```python
from fastapi import HTTPException

# ✅ 基本用法：抛出业务异常
raise HTTPException(status_code=400, detail='用户不存在')

# ✅ 带额外信息
raise HTTPException(
    status_code=404,
    detail={'message': '查询历史不存在', 'id': history_id}
)

# ✅ 常见 HTTP 状态码
raise HTTPException(status_code=400, detail='参数错误')      # 客户端错误
raise HTTPException(status_code=404, detail='资源不存在')    # 资源未找到
raise HTTPException(status_code=500, detail='服务器内部错误') # 服务器错误
```

### HTTP 状态码规范

| 状态码 | 说明 | 使用场景 |
|--------|------|---------|
| 200 | 成功 | 正常响应 |
| 400 | 请求错误 | 参数校验失败、业务逻辑错误 |
| 404 | 未找到 | 资源不存在 |
| 422 | 实体错误 | Pydantic 校验失败（自动处理） |
| 500 | 服务器错误 | 未预期的异常 |

---

## 2. 全局异常处理器

在 `app/main.py` 中配置全局异常处理器：

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)

app = FastAPI()

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """处理 HTTPException"""
    return JSONResponse(
        status_code=exc.status_code,
        content={'detail': exc.detail}
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """处理 Pydantic 校验错误"""
    logger.warning(f'参数校验失败: {exc}')
    return JSONResponse(
        status_code=422,
        content={'detail': exc.errors()}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理未捕获的异常"""
    logger.exception(f'未处理的异常: {exc}')
    return JSONResponse(
        status_code=500,
        content={'detail': '服务器内部错误'}
    )
```

---

## 3. 参数校验

### 使用 Pydantic 自动校验

```python
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional


class QueryRequest(BaseModel):
    """查询请求模型"""
    question: str = Field(..., min_length=1, max_length=500, description='自然语言问题')

    @field_validator('question')
    @classmethod
    def validate_question(cls, v):
        if not v or not v.strip():
            raise ValueError('问题不能为空')
        return v.strip()


class HistoryQueryParams(BaseModel):
    """历史记录查询参数"""
    page: int = Field(1, ge=1, description='页码')
    page_size: int = Field(20, ge=1, le=100, description='每页数量')
    is_favorite: Optional[bool] = Field(None, description='是否收藏')
    search: Optional[str] = Field(None, max_length=100, description='搜索关键词')
```

### 路径参数校验

```python
from fastapi import APIRouter, Path, Query

router = APIRouter()

@router.get('/history/{id}')
async def get_history(
    id: int = Path(..., ge=1, description='历史记录ID')
):
    """获取单条历史记录"""
    # id 会自动转换为 int，小于 1 会返回 422
    pass

@router.get('/history')
async def list_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """获取历史记录列表"""
    pass
```

### 手动校验

```python
from fastapi import HTTPException

async def delete_history(id: int):
    """删除历史记录"""
    # 业务校验
    history = await get_history_by_id(id)
    if not history:
        raise HTTPException(status_code=404, detail=f'历史记录 {id} 不存在')

    # 执行删除
    await do_delete(id)
```

---

## 4. 数据库异常处理

### PostgreSQL 异常（psycopg）

```python
import psycopg
from psycopg import errors

async def execute_sql(query: str):
    """执行 SQL 查询"""
    try:
        async with await psycopg.AsyncConnection.connect(DSN) as conn:
            async with conn.cursor() as cur:
                await cur.execute(query)
                return await cur.fetchall()
    except psycopg.Error as e:
        logger.error(f'SQL 执行失败: {e}', exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f'SQL 执行失败: {str(e)}'
        )

# 常见 psycopg 异常
# errors.SyntaxError         - SQL 语法错误
# errors.UndefinedTable      - 表不存在
# errors.UndefinedColumn     - 列不存在
# errors.UniqueViolation     - 唯一约束冲突
# errors.ForeignKeyViolation - 外键约束冲突
# errors.ConnectionError     - 连接错误
```

### MySQL 异常（PyMySQL）

```python
import pymysql
from pymysql import MySQLError

async def save_history(question: str, sql: str):
    """保存历史记录"""
    try:
        conn = pymysql.connect(**mysql_config)
        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT INTO query_history (question, generated_sql) VALUES (%s, %s)',
                (question, sql)
            )
            conn.commit()
    except MySQLError as e:
        logger.error(f'MySQL 操作失败: {e}', exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f'数据库操作失败'
        )
    finally:
        conn.close()
```

---

## 5. LangGraph 节点异常处理

在 LangGraph 节点函数中，异常处理应返回带 error 字段的 State：

```python
from app.state import NL2SQLState

async def sql_execution_node(state: NL2SQLState) -> dict:
    """SQL 执行节点"""
    sql = state.get('generated_sql')
    attempt = state.get('attempt', 0)
    max_attempts = state.get('max_attempts', 2)

    try:
        result = await execute_sql(sql)
        return {
            'columns': result['columns'],
            'rows': result['rows'],
            'execution_error': None
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f'SQL 执行失败 (attempt {attempt + 1}): {error_msg}', exc_info=True)

        if attempt + 1 < max_attempts:
            # 可以重试
            return {
                'attempt': attempt + 1,
                'execution_error': error_msg
            }
        else:
            # 已达最大重试次数，标记为最终失败
            return {
                'attempt': attempt + 1,
                'execution_error': error_msg,
                'final_error': error_msg
            }
```

---

## 6. 日志规范

### 日志级别

| 级别 | 使用场景 | 示例 |
|------|---------|------|
| ERROR | 系统错误、业务异常 | 数据库连接失败、SQL 执行错误 |
| WARNING | 警告信息、潜在问题 | 重试操作、降级处理 |
| INFO | 重要业务流程、操作记录 | 查询执行、历史记录保存 |
| DEBUG | 开发调试信息 | SQL 语句、中间变量 |

### 日志最佳实践

```python
import logging

logger = logging.getLogger(__name__)

# ✅ 好的：使用 f-string 或 format
logger.info(f'处理查询: {question}')
logger.info('处理查询: {}'.format(question))

# ❌ 不好：字符串拼接
logger.info('处理查询: ' + question)

# ✅ 好的：异常日志带堆栈
try:
    do_something()
except Exception as e:
    logger.error(f'处理失败: {e}', exc_info=True)

# ✅ 好的：使用 logger.exception（自动带堆栈）
try:
    do_something()
except Exception as e:
    logger.exception('处理失败')

# ✅ 好的：判断日志级别（避免不必要的序列化开销）
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(f'详细数据: {json.dumps(data)}')
```

### 日志配置

```python
# app/main.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
```

---

## 7. 错误响应格式

### 统一响应格式

```python
from pydantic import BaseModel
from typing import Any, Optional


class ApiResponse(BaseModel):
    """统一 API 响应格式"""
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[str] = None


# 成功响应
{
    "success": true,
    "data": {...},
    "message": "操作成功"
}

# 错误响应
{
    "success": false,
    "error": "参数错误",
    "message": "问题不能为空"
}
```

### SSE 流式响应中的错误

```python
async def stream_query(question: str):
    """SSE 流式查询"""
    yield f'event: init\ndata: {json.dumps({"graph": {...}})}\n\n'

    try:
        # 执行查询
        for event in execute_query(question):
            yield f'event: {event.type}\ndata: {json.dumps(event.data)}\n\n'
    except Exception as e:
        # 发送错误事件
        yield f'event: error\ndata: {json.dumps({"error": str(e)})}\n\n'
```

---

## 错误处理检查清单

- [ ] 业务异常使用 `raise HTTPException(status_code=xxx, detail='msg')`
- [ ] 参数校验使用 Pydantic 模型
- [ ] 数据库操作使用 try-except 捕获异常
- [ ] 日志记录异常堆栈：`logger.error(msg, exc_info=True)` 或 `logger.exception(msg)`
- [ ] LangGraph 节点返回带 error 字段的 State
- [ ] 错误信息使用用户友好语言

---

## 快速对照表

| ❌ 错误写法 | ✅ 正确写法 |
|-----------|-----------|
| `raise Exception('msg')` | `raise HTTPException(status_code=400, detail='msg')` |
| `log.error('失败: ' + str(e))` | `logger.error(f'失败: {e}', exc_info=True)` |
| `logger.exception(e)` | `logger.exception('处理失败')` |
| 直接返回错误信息 | 使用统一响应格式 |
| 吞掉异常不做处理 | 记录日志并适当抛出 |