---
name: performance-doctor
description: |
  后端性能问题诊断与优化。包含 SQL 优化、PostgreSQL + MySQL 双数据库优化、批量操作优化、接口优化、日志分析。

  触发场景:
  - 接口响应慢
  - SQL 慢查询优化
  - 分页查询优化
  - N+1 查询问题
  - 批量操作超时
  - 数据库连接池优化
  - LangGraph 流程性能

  触发词:性能优化、慢查询、SQL优化、索引优化、N+1、分页优化、EXPLAIN、响应慢、批量操作、连接池优化、PostgreSQL、MySQL

  注意:如果是排查功能性 Bug(代码报错、逻辑错误),请使用 bug-detective。
---

# 后端性能优化指南

> **适用于**: nl2sql-langgraph 后端（FastAPI + psycopg + PyMySQL + LangGraph）

---

## 目录

- [性能问题诊断流程](#性能问题诊断流程)
- [PostgreSQL 查询优化](#1-postgresql-查询优化)
- [MySQL 查询优化](#2-mysql-查询优化)
- [SQL 优化通用技巧](#3-sql-优化通用技巧)
- [批量操作优化](#4-批量操作优化)
- [接口优化](#5-接口优化)
- [LangGraph 性能优化](#6-langgraph-性能优化)
- [性能日志分析](#7-性能日志分析)
- [常见性能问题速查](#常见性能问题速查)

---

## 性能问题诊断流程

```
1. 定位问题
   ├─ 接口层面?→ 检查响应时间、调用链路
   ├─ SQL 层面?→ 检查慢查询、执行计划
   └─ LangGraph 层面?→ 检查节点执行时间、并行效率

2. 分析原因
   ├─ 使用工具测量（日志分析/数据库监控）
   └─ 找出瓶颈点

3. 实施优化
   └─ 针对性优化（索引/批量处理/并行执行）

4. 验证效果
   └─ 对比优化前后（响应时间/SQL 耗时）
```

---

## 1. PostgreSQL 查询优化

本项目使用 **psycopg** 直接连接 PostgreSQL，无 ORM 层。

### 连接池配置

```python
import psycopg
from psycopg_pool import AsyncConnectionPool

# 连接池配置
pool = AsyncConnectionPool(
    conninfo=POSTGRES_DSN,
    min_size=2,        # 最小连接数
    max_size=10,       # 最大连接数
    timeout=30,        # 获取连接超时
    max_idle=300,      # 最大空闲时间
)

# 使用连接池
async with pool.connection() as conn:
    async with conn.cursor() as cur:
        await cur.execute(query)
```

### 查询优化示例

```python
import psycopg

async def get_metrics_data(metric_names: list[str]):
    """获取指标数据"""
    # ✅ 推荐：使用 IN 批量查询
    async with await psycopg.AsyncConnection.connect(DSN) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                'SELECT * FROM metrics_catalog WHERE metric_name = ANY(%s)',
                [metric_names]
            )
            return await cur.fetchall()

    # ❌ 避免：循环单个查询（N次数据库访问）
    for name in metric_names:
        await cur.execute('SELECT * FROM metrics_catalog WHERE metric_name = %s', [name])
```

### 执行计划分析

```sql
-- 使用 EXPLAIN ANALYZE 分析
EXPLAIN ANALYZE SELECT * FROM lake_table_metadata WHERE metric_name = '订单金额';

-- 关注指标
-- Execution Time: 执行时间（ms）
-- Total Cost: 总成本（估计值）
-- Rows Removed by Filter: 被过滤掉的行数（多说明索引不够优化）
-- Seq Scan: 全表扫描（需要优化）
-- Index Scan: 索引扫描（较好）
```

### 索引优化

```sql
-- 创建索引
CREATE INDEX idx_metrics_name ON metrics_catalog(metric_name);
CREATE INDEX idx_kb_keyword ON enterprise_kb(keyword);

-- 复合索引
CREATE INDEX idx_orders_region_date ON fact_orders(region, order_date);

-- 查看索引
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'metrics_catalog';

-- 分析表统计信息
ANALYZE metrics_catalog;
```

---

## 2. MySQL 查询优化

本项目使用 **PyMySQL** 连接 MySQL，用于历史记录等平台数据。

### 连接管理

```python
import pymysql
from dbutils.pooled_db import PooledDB

# 连接池配置
mysql_pool = PooledDB(
    creator=pymysql,
    maxconnections=10,
    mincached=2,
    host=MYSQL_HOST,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    database=MYSQL_DATABASE,
    charset='utf8mb4'
)

# 使用连接池
def get_mysql_connection():
    return mysql_pool.connection()
```

### 分页查询优化

```python
async def get_history_list(page: int, page_size: int):
    """获取历史记录列表"""
    # ✅ 推荐：使用 LIMIT OFFSET
    offset = (page - 1) * page_size

    conn = get_mysql_connection()
    with conn.cursor() as cursor:
        # 先查总数
        cursor.execute('SELECT COUNT(*) FROM query_history WHERE del_flag = 0')
        total = cursor.fetchone()[0]

        # 再查数据
        cursor.execute(
            'SELECT * FROM query_history WHERE del_flag = 0 ORDER BY created_at DESC LIMIT %s OFFSET %s',
            (page_size, offset)
        )
        rows = cursor.fetchall()

    return {'total': total, 'rows': rows}

# ❌ 避免：深分页（offset 过大）
# 当 offset > 10000 时，考虑使用游标分页
```

### 深分页优化

```python
async def get_history_with_cursor(last_id: int, page_size: int):
    """游标分页（适用于深分页）"""
    conn = get_mysql_connection()
    with conn.cursor() as cursor:
        if last_id:
            cursor.execute(
                'SELECT * FROM query_history WHERE id < %s AND del_flag = 0 ORDER BY id DESC LIMIT %s',
                (last_id, page_size)
            )
        else:
            cursor.execute(
                'SELECT * FROM query_history WHERE del_flag = 0 ORDER BY id DESC LIMIT %s',
                (page_size,)
            )
        return cursor.fetchall()
```

---

## 3. SQL 优化通用技巧

### 慢查询分析

```sql
-- PostgreSQL 慢查询日志
-- postgresql.conf
log_min_duration_statement = 500  -- 超过 500ms 记录

-- MySQL 慢查询日志
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;  -- 超过 1 秒记录
```

### N+1 查询优化

```python
# ❌ 不好：N+1 查询
async def get_orders_with_users():
    orders = await get_orders()
    for order in orders:
        order['user'] = await get_user(order['user_id'])  # 每次循环都查询
    return orders

# ✅ 好的：批量查询 + 字典映射
async def get_orders_with_users_optimized():
    orders = await get_orders()
    user_ids = [order['user_id'] for order in orders]

    users = await get_users_by_ids(user_ids)
    user_dict = {user['id']: user for user in users}

    for order in orders:
        order['user'] = user_dict.get(order['user_id'])  # O(1) 查找
    return orders
```

### 索引使用原则

```
1. 最左前缀原则：复合索引 (a, b, c) 可以用于 a, (a, b), (a, b, c)
2. 避免在索引列上使用函数：WHERE LOWER(name) = 'xxx' → 索引失效
3. 避免 != 和 NOT IN：改用 IN 或 EXISTS
4. 注意索引选择性：选择性 = DISTINCT(column) / COUNT(*)
5. 定期 ANALYZE 表：更新统计信息
```

---

## 4. 批量操作优化

```python
# ✅ 推荐：分批插入（每批 500 条）
async def batch_insert_history(items: list):
    """批量插入历史记录"""
    batch_size = 500
    conn = get_mysql_connection()

    with conn.cursor() as cursor:
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            values = [(item['question'], item['sql']) for item in batch]
            cursor.executemany(
                'INSERT INTO query_history (question, generated_sql) VALUES (%s, %s)',
                values
            )
            conn.commit()

# ❌ 避免：一次性插入大量数据
cursor.executemany(sql, huge_list)  # 可能超时或内存溢出
```

---

## 5. 接口优化

### 只查询需要的字段

```python
# ❌ 不好：返回所有字段
async def list_history():
    cursor.execute('SELECT * FROM query_history')
    return cursor.fetchall()

# ✅ 好的：只返回需要的字段
async def list_history():
    cursor.execute('''
        SELECT id, question, created_at, is_favorite
        FROM query_history
        WHERE del_flag = 0
        ORDER BY created_at DESC
    ''')
    return cursor.fetchall()
```

### 异步并发优化

```python
import asyncio

# ✅ 推荐：使用 asyncio.gather 并发执行多个查询
async def get_query_context(question: str):
    kb_task = fetch_kb_hits(question)
    metrics_task = fetch_metrics_hits(question)
    metadata_task = fetch_metadata_hits(question)

    kb, metrics, metadata = await asyncio.gather(
        kb_task, metrics_task, metadata_task
    )
    return {'kb': kb, 'metrics': metrics, 'metadata': metadata}

# ❌ 避免：顺序执行多个查询
kb = await fetch_kb_hits(question)
metrics = await fetch_metrics_hits(question)
metadata = await fetch_metadata_hits(question)
```

---

## 6. LangGraph 性能优化

### 并行节点执行

LangGraph 支持并行执行多个节点，本项目使用梭子形架构：

```python
# app/graph_builder.py
from langgraph.graph import StateGraph

graph = StateGraph(NL2SQLState)

# 添加节点
graph.add_node('analyze_question', analyze_question_node)
graph.add_node('fetch_kb', fetch_kb_node)
graph.add_node('fetch_metrics', fetch_metrics_node)
graph.add_node('fetch_metadata', fetch_metadata_node)
graph.add_node('merge_context', merge_context_node)

# 并行执行三个检索节点
graph.add_edge('analyze_question', 'fetch_kb')
graph.add_edge('analyze_question', 'fetch_metrics')
graph.add_edge('analyze_question', 'fetch_metadata')

# 合并节点等待所有并行节点完成
graph.add_edge('fetch_kb', 'merge_context')
graph.add_edge('fetch_metrics', 'merge_context')
graph.add_edge('fetch_metadata', 'merge_context')
```

### 节点执行时间追踪

```python
import time

async def sql_execution_node(state: NL2SQLState) -> dict:
    """SQL 执行节点（带性能追踪）"""
    start_time = time.time()

    try:
        result = await execute_sql(state['generated_sql'])
        elapsed = time.time() - start_time
        logger.info(f'SQL 执行耗时: {elapsed:.2f}s')
        return result
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f'SQL 执行失败 (耗时 {elapsed:.2f}s): {e}', exc_info=True)
        raise
```

---

## 7. 性能日志分析

### 日志格式

```
日期时间 | 级别 | 模块:函数:行号 - 消息内容

示例：
2026-04-01 10:00:00 | INFO | app.nodes:sql_execution_node:45 - SQL 执行耗时: 1.23s
2026-04-01 10:00:01 | ERROR | app.tools:execute_sql:78 - SQL 执行失败: syntax error
```

### 性能分析场景

| 触发场景 | 关键词 | 分析重点 |
|---------|--------|----------|
| 接口响应慢 | "接口慢"、"超时" | SQL 执行时间、N+1 查询 |
| SQL 性能问题 | "SQL慢"、"查询慢" | EXPLAIN 分析、索引检查 |
| LangGraph 慢 | "流程慢"、"节点慢" | 节点执行时间、并行效率 |

---

## 常见性能问题速查

| 问题现象 | 可能原因 | 解决方案 |
|----------|----------|----------|
| 接口响应慢 | SQL 无索引 | 添加合适索引，使用 EXPLAIN 分析 |
| 接口响应慢 | N+1 查询 | 改为批量查询 + 字典映射 |
| 分页查询慢 | 深分页问题 | 使用游标分页或限制页码范围 |
| 批量操作超时 | 一次操作太多数据 | 分批处理，每批 500 条 |
| 数据库连接耗尽 | 连接未释放 | 确保连接正确关闭，使用连接池 |
| LangGraph 流程慢 | 节点顺序执行 | 检查是否可以并行执行 |
| 内存溢出 | 大数据量一次加载 | 分批处理、流式处理 |

---

## 性能指标

| 指标 | 良好 | 需优化 |
|------|------|--------|
| 接口响应时间 | < 500ms | > 2s |
| 数据库查询 | < 100ms | > 500ms |
| LangGraph 节点 | < 1s | > 3s |
| 数据库连接池使用率 | < 70% | > 85% |