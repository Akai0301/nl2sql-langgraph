# /check - 代码规范检查

作为代码规范检查助手，自动检测项目代码是否符合 nl2sql-langgraph 规范。

## 检查范围

支持三种检查模式：

1. **全量检查**：`/check` - 检查所有代码
2. **目录检查**：`/check app` - 检查指定目录
3. **文件检查**：`/check nodes.py` - 检查指定文件

---

## 检查清单总览

| 检查项 | 级别 | 说明 |
|--------|------|------|
| State TypedDict 定义 | 🔴 严重 | State 必须继承 TypedDict |
| 节点函数返回 dict | 🔴 严重 | 节点函数必须返回字典 |
| 异步编程 | 🔴 严重 | 必须使用 async/await |
| 工具函数规范 | 🔴 | 工具函数必须正确处理异常 |
| API 路由规范 | 🟡 警告 | 接口路径必须规范 |
| Pydantic 模型使用 | 🟡 警告 | 必须正确使用 BaseModel |
| 前端 TypeScript | 🟡 警告 | 必须有类型定义 |

---

## 检查详情

### 1. State TypedDict 定义 [🔴 严重]

```bash
# 检查 State 是否使用 TypedDict
Grep pattern: "class.*State.*TypedDict" path: app/state.py output_mode: content
```

```python
# ❌ 错误
class NL2SQLState:
    question: str

# ✅ 正确
from typing import TypedDict

class NL2SQLState(TypedDict, total=False):
    question: str
    generated_sql: str
```

### 2. 节点函数返回 dict [🔴 严重]

```bash
# 检查节点函数是否返回 dict
Grep pattern: "async def.*_node" path: app/nodes.py output_mode: content
Grep pattern: "return \{" path: app/nodes.py output_mode: count
```

```python
# ❌ 错误
async def analyze_node(state):
    return some_object  # 非 dict 类型

# ✅ 正确
async def analyze_node(state: NL2SQLState) -> dict:
    return {'keywords': extracted_keywords}
```

### 3. 异步编程 [🔴 严重]

```bash
# 检查是否使用 async/await
Grep pattern: "async def" path: app/ glob: "*.py" output_mode: count
Grep pattern: "await " path: app/ glob: "*.py" output_mode: count
```

```python
# ❌ 错误（同步操作）
def execute_sql(query):
    conn = psycopg.connect(DSN)
    return conn.execute(query)

# ✅ 正确（异步操作）
async def execute_sql(query: str):
    async with await psycopg.AsyncConnection.connect(DSN) as conn:
        async with conn.cursor() as cur:
            await cur.execute(query)
            return await cur.fetchall()
```

### 4. 工具函数规范 [🔴]

```bash
# 检查工具函数
Grep pattern: "async def" path: app/tools.py output_mode: content
```

**规范要求**：
- 使用 async/await
- 正确处理异常
- 使用连接池或上下文管理器

### 5. API 路由规范 [🟡 警告]

```bash
# 检查 API 路由
Grep pattern: "@router\.(get|post|delete)" path: app/ output_mode: content
```

**规范要求**：

| 操作 | HTTP 方法 | 路径格式 |
|------|---------|--------|
| 查询 | POST | `/query` |
| 流式查询 | GET | `/stream` |
| 历史列表 | GET | `/history` |
| 删除记录 | DELETE | `/history/{id}` |

### 6. Pydantic 模型使用 [🟡 警告]

```bash
# 检查 Pydantic 模型
Grep pattern: "class.*BaseModel" path: app/ output_mode: content
```

```python
# ❌ 错误
class QueryRequest:
    question: str

# ✅ 正确
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
```

### 7. 前端 TypeScript [🟡 警告]

```bash
# 检查 TypeScript 类型
Grep pattern: "interface\|type" path: frontend/src/types/ output_mode: files_with_matches
```

---

## 输出格式

```markdown
# 🔍 代码规范检查报告

**检查时间**：YYYY-MM-DD HH:mm
**检查范围**：[全量 / 目录名 / 文件名]

---

## 📋 检查结果汇总

| 类别 | 通过 | 警告 | 错误 |
|------|------|------|------|
| 后端 Python | X | X | X |
| 前端 TypeScript | X | X | X |

---

## 🔴 严重问题（必须修复）

### 1. [问题类型]

**文件**：`path/to/file.py:42`
**问题**：节点函数返回非字典类型
**代码**：
\```python
return some_object
\```
**修复**：
\```python
return {'field': value}
\```

---

## 🟡 警告问题（建议修复）

### 1. [问题类型]
...

---

## ✅ 检查通过项

- [x] State 使用 TypedDict
- [x] 节点函数返回 dict
- [x] 使用 async/await
- ...
```

---

## 检查优先级

### 开发完成后必查（阻塞提交）

1. State 是否使用 TypedDict
2. 节点函数是否返回 dict
3. 是否使用 async/await 异步编程
4. 工具函数是否正确处理异常

### 代码审查建议查

1. Pydantic 模型是否正确使用
2. API 路径是否规范
3. 前端是否有类型定义

---

## 参考

- 正确 State 定义：`app/state.py`
- 正确节点函数：`app/nodes.py`
- 正确工具函数：`app/tools.py`
- 正确 API 路由：`app/main.py`