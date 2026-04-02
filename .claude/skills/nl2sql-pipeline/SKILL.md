---
name: nl2sql-pipeline
description: NL2SQL 业务管道规范。包含问题分析、知识检索、SQL 生成、SQL 执行等业务流程开发指南，以及 PostgreSQL + MySQL 双数据库架构说明。
---

# NL2SQL 业务管道规范

本项目是一个自然语言转 SQL 系统，采用 LangGraph 梭子形架构。本 Skill 提供业务层面的开发指南。

## 业务流程

### 完整流程图

```
问题 → 问题分析 → [并行检索] → 上下文合并 → 元数据分析 → SQL生成 → SQL执行
                      ↓
          ┌───────────┼───────────┐
          ↓           ↓           ↓
     知识检索     指标检索     元数据检索
          └───────────┼───────────┘
                      ↓
                上下文合并
```

### 流程步骤

| 步骤 | 节点 | 说明 |
|------|------|------|
| 1 | `analyze_question` | 提取关键词和同义词 |
| 2 | `knowledge_retrieval` | 检索企业知识库 |
| 3 | `metric_retrieval` | 检索指标口径目录 |
| 4 | `metadata_retrieval` | 检索湖表元数据 |
| 5 | `merge_context` | 合并检索结果，提取候选表 |
| 6 | `metadata_analysis` | 分析表关联，选择最佳表 |
| 7 | `sql_generation` | 生成 SQL 语句 |
| 8 | `sql_execution` | 执行 SQL，返回结果 |

---

## 数据库架构

### 双数据库设计

| 数据库 | 用途 | 表 |
|--------|------|-----|
| PostgreSQL | 问数业务数据 | `enterprise_kb`, `metrics_catalog`, `lake_table_metadata`, `fact_orders` |
| MySQL | 平台数据 | `query_history`, `user_preferences` |

### PostgreSQL 表结构

#### enterprise_kb（企业知识库）

```sql
CREATE TABLE enterprise_kb (
    id SERIAL PRIMARY KEY,
    keyword_synonyms VARCHAR(500),       -- 关键词同义词
    business_meaning TEXT,               -- 业务含义
    example_sql_template TEXT,           -- 示例 SQL 模板
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### metrics_catalog（指标口径目录）

```sql
CREATE TABLE metrics_catalog (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(200),            -- 指标名称
    metric_synonyms VARCHAR(500),        -- 指标同义词
    business_definition TEXT,            -- 业务定义
    aggregation_rule VARCHAR(100),       -- 聚合规则（SUM/COUNT/AVG）
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### lake_table_metadata（湖表元数据）

```sql
CREATE TABLE lake_table_metadata (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(100),                  -- 主题域
    metric_name VARCHAR(200),            -- 关联指标
    fact_table VARCHAR(200),             -- 事实表名
    measure_sql_expression TEXT,         -- 度量 SQL 表达式
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### fact_orders（订单事实表）

```sql
CREATE TABLE fact_orders (
    id SERIAL PRIMARY KEY,
    order_date DATE,                     -- 订单日期
    region VARCHAR(50),                  -- 地区
    product_name VARCHAR(200),           -- 产品名称
    order_amount DECIMAL(18, 2),         -- 订单金额
    quantity INT,                        -- 数量
    created_at TIMESTAMP DEFAULT NOW()
);
```

### MySQL 表结构

#### query_history（查询历史）

```sql
CREATE TABLE query_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    question VARCHAR(1000),              -- 用户问题
    generated_sql TEXT,                  -- 生成的 SQL
    columns JSON,                        -- 结果列
    rows JSON,                           -- 结果行
    is_favorite BOOLEAN DEFAULT FALSE,   -- 是否收藏
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_created_at (created_at),
    INDEX idx_is_favorite (is_favorite)
);
```

---

## 问题分析阶段

### 关键词提取

```python
async def analyze_question_node(state: NL2SQLState) -> dict:
    """问题分析：提取关键词"""
    question = state.get('question', '')

    # 1. 从数据库词表提取关键词
    keywords = await extract_keywords_from_lexicon(question)

    # 2. 获取同义词
    synonyms = await fetch_synonyms(keywords)

    return {
        'keywords': keywords,
        'keyword_synonyms': synonyms
    }
```

### 词表匹配策略

| 策略 | 说明 |
|------|------|
| 精确匹配 | 完全匹配词表中的关键词 |
| 模糊匹配 | 使用 ILIKE 进行模糊匹配 |
| 同义词扩展 | 匹配同义词并返回标准词 |

---

## 检索阶段

### 知识检索

```python
async def knowledge_retrieval_node(state: NL2SQLState) -> dict:
    """检索企业知识库"""
    keywords = state.get('keywords', [])

    # 检索知识库
    kb_hits = await fetch_kb_hits(keywords)

    return {'kb_hits': kb_hits}


async def fetch_kb_hits(keywords: list[str]) -> list[dict]:
    """从 enterprise_kb 检索"""
    async with await psycopg.AsyncConnection.connect(POSTGRES_DSN) as conn:
        async with conn.cursor() as cur:
            # 使用 ANY 和 ILIKE 进行模糊匹配
            sql = '''
                SELECT keyword_synonyms, business_meaning, example_sql_template
                FROM enterprise_kb
                WHERE EXISTS (
                    SELECT 1 FROM unnest($1::text[]) kw
                    WHERE keyword_synonyms ILIKE '%' || kw || '%'
                )
            '''
            await cur.execute(sql, (keywords,))
            return [dict(zip(['keyword_synonyms', 'business_meaning', 'example_sql_template'], row))
                    for row in await cur.fetchall()]
```

### 指标检索

```python
async def metric_retrieval_node(state: NL2SQLState) -> dict:
    """检索指标口径目录"""
    keywords = state.get('keywords', [])

    metric_hits = await fetch_metric_hits(keywords)

    return {'metric_hits': metric_hits}


async def fetch_metric_hits(keywords: list[str]) -> list[dict]:
    """从 metrics_catalog 检索"""
    async with await psycopg.AsyncConnection.connect(POSTGRES_DSN) as conn:
        async with conn.cursor() as cur:
            sql = '''
                SELECT metric_name, metric_synonyms, business_definition, aggregation_rule
                FROM metrics_catalog
                WHERE EXISTS (
                    SELECT 1 FROM unnest($1::text[]) kw
                    WHERE metric_name ILIKE '%' || kw || '%'
                       OR metric_synonyms ILIKE '%' || kw || '%'
                )
            '''
            await cur.execute(sql, (keywords,))
            return [dict(zip(['metric_name', 'metric_synonyms', 'business_definition', 'aggregation_rule'], row))
                    for row in await cur.fetchall()]
```

### 元数据检索

```python
async def metadata_retrieval_node(state: NL2SQLState) -> dict:
    """检索湖表元数据"""
    keywords = state.get('keywords', [])

    metadata_hits = await fetch_metadata_hits(keywords)

    return {'metadata_hits': metadata_hits}


async def fetch_metadata_hits(keywords: list[str]) -> list[dict]:
    """从 lake_table_metadata 检索"""
    async with await psycopg.AsyncConnection.connect(POSTGRES_DSN) as conn:
        async with conn.cursor() as cur:
            sql = '''
                SELECT topic, metric_name, fact_table, measure_sql_expression
                FROM lake_table_metadata
                WHERE EXISTS (
                    SELECT 1 FROM unnest($1::text[]) kw
                    WHERE metric_name ILIKE '%' || kw || '%'
                       OR topic ILIKE '%' || kw || '%'
                )
            '''
            await cur.execute(sql, (keywords,))
            return [dict(zip(['topic', 'metric_name', 'fact_table', 'measure_sql_expression'], row))
                    for row in await cur.fetchall()]
```

---

## 合并与分析阶段

### 上下文合并

```python
async def merge_context_node(state: NL2SQLState) -> dict:
    """合并检索结果，提取候选表"""
    metadata_hits = state.get('metadata_hits', [])

    # 从元数据命中中提取候选表
    candidate_tables = list(set(hit['fact_table'] for hit in metadata_hits))

    return {'candidate_tables': candidate_tables}
```

### 元数据分析

```python
async def metadata_analysis_node(state: NL2SQLState) -> dict:
    """分析表关联，选择最佳表"""
    candidate_tables = state.get('candidate_tables', [])
    metric_hits = state.get('metric_hits', [])

    # 简单实现：选择第一个候选表
    selected_tables = candidate_tables[:1] if candidate_tables else []

    # 确定 Join 逻辑（如果有多个表）
    join_logic = generate_join_logic(selected_tables)

    return {
        'selected_tables': selected_tables,
        'join_logic': join_logic
    }
```

---

## SQL 生成阶段

### 规则模式（USE_MOCK_LLM=true）

```python
async def sql_generation_node(state: NL2SQLState) -> dict:
    """生成 SQL"""
    if USE_MOCK_LLM:
        return await generate_sql_by_rules(state)
    else:
        return await generate_sql_by_llm(state)


async def generate_sql_by_rules(state: NL2SQLState) -> dict:
    """基于规则生成 SQL"""
    question = state.get('question', '')
    selected_tables = state.get('selected_tables', ['fact_orders'])
    metric_hits = state.get('metric_hits', [])

    # 确定聚合函数
    agg_func = 'SUM'
    if metric_hits:
        agg_rule = metric_hits[0].get('aggregation_rule', 'SUM')
        if agg_rule in ['SUM', 'COUNT', 'AVG', 'MAX', 'MIN']:
            agg_func = agg_rule

    # 确定分组字段
    group_by = detect_group_by(question)

    # 确定时间过滤
    time_filter = detect_time_filter(question)

    # 构建 SQL
    sql = f'''
        SELECT {group_by}, {agg_func}(order_amount) AS metric_value
        FROM {selected_tables[0]}
        WHERE {time_filter}
        GROUP BY {group_by}
        ORDER BY metric_value DESC
    '''

    return {'generated_sql': sql.strip()}
```

### LLM 模式（USE_MOCK_LLM=false）

```python
async def generate_sql_by_llm(state: NL2SQLState) -> dict:
    """使用 LLM 生成 SQL"""
    from openai import AsyncOpenAI
    from app.prompt_templates import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

    client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)

    # 构建上下文
    context = build_context_for_llm(state)

    # 调用 LLM
    response = await client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                question=state.get('question'),
                context=context
            )}
        ],
        temperature=0
    )

    sql = response.choices[0].message.content

    return {'generated_sql': sql}
```

---

## SQL 执行阶段

### 执行与重试

```python
async def sql_execution_node(state: NL2SQLState) -> dict:
    """执行 SQL"""
    sql = state.get('generated_sql', '')
    attempt = state.get('attempt', 0) + 1

    try:
        result = await execute_sql(sql)
        return {
            'columns': result['columns'],
            'rows': result['rows'],
            'attempt': attempt,
            'execution_error': None
        }
    except Exception as e:
        logger.error(f'SQL 执行失败 (attempt {attempt}): {e}')
        return {
            'attempt': attempt,
            'execution_error': str(e)
        }
```

### 历史记录保存

```python
async def save_to_history(state: NL2SQLState) -> None:
    """保存查询历史到 MySQL"""
    await save_query_history(
        question=state.get('question'),
        sql=state.get('generated_sql'),
        columns=state.get('columns', []),
        rows=state.get('rows', [])
    )
```

---

## 最佳实践

### ✅ 推荐做法

1. **关键词提取**
   - 使用数据库词表匹配
   - 支持同义词扩展
   - 记录匹配日志

2. **检索阶段**
   - 并行执行三个检索
   - 使用参数化查询
   - 限制返回数量

3. **SQL 生成**
   - 优先使用规则模式
   - LLM 模式作为增强
   - 验证 SQL 语法

4. **SQL 执行**
   - 设置最大重试次数
   - 记录执行错误
   - 限制返回行数

### ❌ 避免做法

1. **关键词提取**
   - ❌ 硬编码关键词
   - ❌ 不处理同义词

2. **检索阶段**
   - ❌ 串行执行检索
   - ❌ SQL 字符串拼接
   - ❌ 返回过多数据

3. **SQL 生成**
   - ❌ 直接拼接用户输入
   - ❌ 不验证 SQL 语法
   - ❌ 不限制查询范围

4. **SQL 执行**
   - ❌ 无限重试
   - ❌ 不记录错误
   - ❌ 返回全部数据

---

## 参考文件

- [app/nodes.py](app/nodes.py) - 所有节点实现
- [app/tools.py](app/tools.py) - PostgreSQL 工具
- [app/mysql_tools.py](app/mysql_tools.py) - MySQL 工具
- [app/prompt_templates.py](app/prompt_templates.py) - LLM 提示词
- [db/schema.sql](db/schema.sql) - PostgreSQL 表结构
- [db/mysql_schema.sql](db/mysql_schema.sql) - MySQL 表结构