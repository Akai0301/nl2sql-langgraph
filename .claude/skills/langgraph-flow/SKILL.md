---
name: langgraph-flow
description: LangGraph 流程开发规范。包含 State TypedDict 定义、节点函数开发、StateGraph 构建、SSE 流式接口等 LangGraph 核心开发指南。
---

# LangGraph 流程开发规范

本项目基于 LangGraph 实现梭子形多 Agent NL2SQL 流水线。本 Skill 提供完整的 LangGraph 开发指南。

## 核心概念

### 梭子形架构

```
问题 → 分析器 → [并行检索] → 合并 → 元数据分析 → SQL生成 → SQL执行
                      ↓
          ┌───────────┼───────────┐
          ↓           ↓           ↓
     知识检索     指标检索     元数据检索
          └───────────┼───────────┘
                      ↓
                上下文合并
```

### 关键组件

| 组件 | 文件 | 说明 |
|------|------|------|
| State | `app/state.py` | TypedDict 状态定义 |
| Nodes | `app/nodes.py` | 节点函数实现 |
| Tools | `app/tools.py` | PostgreSQL 工具函数 |
| MySQL Tools | `app/mysql_tools.py` | MySQL 工具函数 |
| Graph Builder | `app/graph_builder.py` | StateGraph 构建 |
| Streaming | `app/streaming.py` | SSE 流式接口 |

---

## State 定义规范

### 使用 TypedDict

```python
# app/state.py
from typing import TypedDict, Annotated, Sequence
from operator import add

class NL2SQLState(TypedDict, total=False):
    """NL2SQL 流程状态定义"""
    # 输入
    question: str                          # 用户问题

    # 分析阶段
    keywords: list[str]                    # 提取的关键词
    keyword_synonyms: list[str]            # 同义词

    # 检索阶段（并行）
    kb_hits: list[dict]                    # 知识库命中
    metric_hits: list[dict]                # 指标命中
    metadata_hits: list[dict]              # 元数据命中

    # 合并阶段
    candidate_tables: list[str]            # 候选表
    selected_tables: list[str]             # 选中的表
    join_logic: str                        # Join 逻辑

    # SQL 生成阶段
    generated_sql: str                     # 生成的 SQL
    sql_explanation: str                   # SQL 解释

    # 执行阶段
    columns: list[str]                     # 结果列
    rows: list[tuple]                      # 结果行
    attempt: int                           # 执行次数
    execution_error: str                   # 执行错误
```

### 状态字段规范

| 规则 | 说明 |
|------|------|
| 使用 `TypedDict` | 类型安全，IDE 友好 |
| `total=False` | 大多数字段可选 |
| 简单类型 | `str`、`int`、`list[str]` |
| 避免嵌套 | 扁平化结构 |

---

## 节点函数规范

### 基本结构

```python
# app/nodes.py
from app.state import NL2SQLState

async def analyze_question_node(state: NL2SQLState) -> dict:
    """问题分析节点：提取关键词和同义词"""
    try:
        question = state.get('question', '')

        # 1. 业务逻辑
        keywords = extract_keywords(question)
        synonyms = fetch_synonyms(keywords)

        # 2. 返回状态更新
        return {
            'keywords': keywords,
            'keyword_synonyms': synonyms
        }
    except Exception as e:
        logger.error(f'问题分析失败: {e}', exc_info=True)
        return {'keywords': [], 'keyword_synonyms': []}
```

### 节点函数规则

| 规则 | 说明 |
|------|------|
| 函数命名 | `*_node` 后缀 |
| 参数类型 | `NL2SQLState` |
| 返回类型 | `dict`（状态更新） |
| 异步函数 | 使用 `async def` |
| 异常处理 | 必须捕获异常，返回默认值 |
| 无副作用 | 不修改输入 state |

### 并行节点示例

```python
async def knowledge_retrieval_node(state: NL2SQLState) -> dict:
    """知识检索节点（并行执行）"""
    keywords = state.get('keywords', [])

    kb_hits = await fetch_kb_hits(keywords)

    return {'kb_hits': kb_hits}


async def metric_retrieval_node(state: NL2SQLState) -> dict:
    """指标检索节点（并行执行）"""
    keywords = state.get('keywords', [])

    metric_hits = await fetch_metric_hits(keywords)

    return {'metric_hits': metric_hits}


async def metadata_retrieval_node(state: NL2SQLState) -> dict:
    """元数据检索节点（并行执行）"""
    keywords = state.get('keywords', [])

    metadata_hits = await fetch_metadata_hits(keywords)

    return {'metadata_hits': metadata_hits}
```

---

## StateGraph 构建规范

### 图构建

```python
# app/graph_builder.py
from langgraph.graph import StateGraph, END
from app.state import NL2SQLState
from app.nodes import (
    analyze_question_node,
    knowledge_retrieval_node,
    metric_retrieval_node,
    metadata_retrieval_node,
    merge_context_node,
    metadata_analysis_node,
    sql_generation_node,
    sql_execution_node,
)

def build_nl2sql_graph():
    """构建 NL2SQL StateGraph"""
    # 创建图
    graph = StateGraph(NL2SQLState)

    # 添加节点
    graph.add_node('analyze_question', analyze_question_node)
    graph.add_node('knowledge_retrieval', knowledge_retrieval_node)
    graph.add_node('metric_retrieval', metric_retrieval_node)
    graph.add_node('metadata_retrieval', metadata_retrieval_node)
    graph.add_node('merge_context', merge_context_node)
    graph.add_node('metadata_analysis', metadata_analysis_node)
    graph.add_node('sql_generation', sql_generation_node)
    graph.add_node('sql_execution', sql_execution_node)

    # 设置入口
    graph.set_entry_point('analyze_question')

    # 添加边
    graph.add_edge('analyze_question', 'knowledge_retrieval')
    graph.add_edge('analyze_question', 'metric_retrieval')
    graph.add_edge('analyze_question', 'metadata_retrieval')

    # 合并节点等待所有并行节点完成
    graph.add_edge('knowledge_retrieval', 'merge_context')
    graph.add_edge('metric_retrieval', 'merge_context')
    graph.add_edge('metadata_retrieval', 'merge_context')

    # 后续流程
    graph.add_edge('merge_context', 'metadata_analysis')
    graph.add_edge('metadata_analysis', 'sql_generation')
    graph.add_edge('sql_generation', 'sql_execution')
    graph.add_edge('sql_execution', END)

    return graph.compile()
```

### 条件边

```python
def should_retry(state: NL2SQLState) -> str:
    """判断是否需要重试 SQL"""
    if state.get('execution_error') and state.get('attempt', 0) < 3:
        return 'sql_generation'
    return END

# 添加条件边
graph.add_conditional_edges(
    'sql_execution',
    should_retry,
    {
        'sql_generation': 'sql_generation',
        END: END
    }
)
```

---

## 工具函数规范

### 数据库工具

```python
# app/tools.py
import psycopg
from typing import Optional

async def execute_sql(sql: str) -> dict:
    """执行 SQL 查询"""
    async with await psycopg.AsyncConnection.connect(POSTGRES_DSN) as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql)
            columns = [desc[0] for desc in cur.description]
            rows = await cur.fetchall()
            return {'columns': columns, 'rows': rows}


async def fetch_kb_hits(keywords: list[str]) -> list[dict]:
    """获取知识库命中"""
    if not keywords:
        return []

    async with await psycopg.AsyncConnection.connect(POSTGRES_DSN) as conn:
        async with conn.cursor() as cur:
            # 使用参数化查询防止 SQL 注入
            placeholders = ','.join(['%s'] * len(keywords))
            sql = f'''
                SELECT keyword_synonyms, business_meaning, example_sql_template
                FROM enterprise_kb
                WHERE keyword_synonyms ILIKE ANY (ARRAY[{placeholders}])
            '''
            await cur.execute(sql, keywords)
            return [dict(zip(['keyword_synonyms', 'business_meaning', 'example_sql_template'], row))
                    for row in await cur.fetchall()]
```

### MySQL 工具

```python
# app/mysql_tools.py
import pymysql
from typing import Optional

async def save_query_history(question: str, sql: str, columns: list, rows: list) -> int:
    """保存查询历史到 MySQL"""
    import json

    conn = pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )
    try:
        with conn.cursor() as cur:
            sql_str = '''
                INSERT INTO query_history (question, generated_sql, columns, rows, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            '''
            cur.execute(sql_str, (question, sql, json.dumps(columns), json.dumps(rows)))
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()
```

---

## SSE 流式接口规范

### 流式执行

```python
# app/streaming.py
from fastapi import Response
from app.graph_builder import build_nl2sql_graph
import json

async def stream_query(question: str):
    """SSE 流式执行查询"""
    graph = build_nl2sql_graph()

    async for event in graph.astream({'question': question}):
        # 发送 SSE 事件
        yield f"data: {json.dumps(event)}\n\n"


# FastAPI 路由
@app.get("/stream")
async def stream_endpoint(question: str):
    """SSE 流式查询接口"""
    return Response(
        stream_query(question),
        media_type="text/event-stream"
    )
```

### 事件格式

```python
# 发送节点开始事件
{
    "event": "node_start",
    "node": "analyze_question",
    "label": "问题分析",
    "status": "running"
}

# 发送节点完成事件
{
    "event": "node_complete",
    "node": "analyze_question",
    "label": "问题分析",
    "status": "completed",
    "output": {"keywords": ["订单", "金额"]}
}

# 发送最终结果
{
    "event": "result",
    "question": "查询过去30天订单金额",
    "sql": "SELECT ...",
    "columns": ["region", "metric_value"],
    "rows": [["华东", 12345.67]]
}
```

---

## 最佳实践

### ✅ 推荐做法

1. **State 定义**
   - 使用 TypedDict
   - 字段名清晰
   - 扁平化结构

2. **节点函数**
   - 纯函数，返回 dict
   - 异常处理完整
   - 日志记录充分

3. **工具函数**
   - 使用连接池
   - 参数化查询
   - 异步 I/O

4. **图构建**
   - 单一入口
   - 明确出口
   - 并行节点独立

### ❌ 避免做法

1. **State 定义**
   - ❌ 使用普通 dict
   - ❌ 嵌套过深
   - ❌ 字段名模糊

2. **节点函数**
   - ❌ 直接修改 state
   - ❌ 抛出未捕获异常
   - ❌ 同步数据库操作

3. **工具函数**
   - ❌ SQL 字符串拼接
   - ❌ 每次创建新连接
   - ❌ 阻塞操作

---

## 参考文件

- [app/state.py](app/state.py) - State 定义
- [app/nodes.py](app/nodes.py) - 节点函数
- [app/tools.py](app/tools.py) - PostgreSQL 工具
- [app/mysql_tools.py](app/mysql_tools.py) - MySQL 工具
- [app/graph_builder.py](app/graph_builder.py) - 图构建
- [app/streaming.py](app/streaming.py) - SSE 流式接口