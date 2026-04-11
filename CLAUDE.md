# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 构建与运行命令

```powershell
# 安装后端依赖
pip install -r requirements.txt

# 配置环境变量（复制后编辑 .env，填入数据库连接信息）
copy .env.example .env

# 初始化 PostgreSQL 表结构和种子数据（用于问数业务）
psql $env:POSTGRES_DSN -f .\db\schema.sql
psql $env:POSTGRES_DSN -f .\db\seed.sql

# 初始化 pgvector 向量字段（用于混合检索）
psql $env:POSTGRES_DSN -f .\db\vector_schema.sql

# 初始化 Embedding 数据（使用通义千问 API）
python scripts/init_embeddings.py

# 仅统计待处理数量（不执行 embedding 生成）
python scripts/init_embeddings.py --dry-run

# 初始化 MySQL 表结构（用于平台数据：历史记录等）
mysql -h $env:MYSQL_HOST -u $env:MYSQL_USER -p$env:MYSQL_PASSWORD < .\db\mysql_schema.sql

# 启动 API 服务
uvicorn app.main:app --reload --port 8000

# 测试同步接口
curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d "{\"question\":\"查询过去30天按地区的订单金额\"}"

# 测试流式接口（SSE）
curl "http://localhost:8000/stream?question=查询过去30天按地区的订单金额"

# 安装前端依赖
cd frontend && npm install

# 启动前端开发服务器
cd frontend && npm run dev

# 构建前端（输出到 static/ 目录）
cd frontend && npm run build
```

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `POSTGRES_DSN` | PostgreSQL 连接串（用于问数业务数据） | 必填 |
| `MYSQL_HOST` | MySQL 主机 | `localhost` |
| `MYSQL_PORT` | MySQL 端口 | `3306` |
| `MYSQL_USER` | MySQL 用户名 | `root` |
| `MYSQL_PASSWORD` | MySQL 密码 | - |
| `MYSQL_DATABASE` | MySQL 数据库名 | `nl2sql_platform` |
| `USE_MOCK_LLM` | `true` 使用规则生成 SQL，`false` 使用 OpenAI | `true` |
| `OPENAI_API_KEY` | OpenAI API Key（当 `USE_MOCK_LLM=false` 时必填） | - |
| `OPENAI_API_BASE` | OpenAI API Base URL（可选，用于代理） | - |
| `OPENAI_MODEL` | 模型名称 | `gpt-4o-mini` |
| `SQL_MAX_ROWS` | 返回最大行数 | `200` |
| `SQL_MAX_ATTEMPTS` | SQL 执行失败重试次数 | `2` |
| `QWEN_API_KEY` | 通义千问 API Key（用于 Embedding） | - |
| `QWEN_API_BASE` | 通义千问 API 地址 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `QWEN_EMBEDDING_MODEL` | Embedding 模型名称 | `text-embedding-v3` |
| `QWEN_EMBEDDING_DIM` | Embedding 向量维度 | `1024` |

### AI 配置优先级

配置读取顺序：**MySQL 配置表 > .env 文件 > 硬编码默认值**

| 配置来源 | 说明 | 配置位置 |
|---------|------|---------|
| MySQL 配置表 | 最高优先级，支持多配置切换 | `ai_model_config` 表 |
| .env 文件 | 默认配置，无需数据库 | 项目根目录 `.env` |
| 硬编码默认值 | 兜底配置 | `config_service.py` |

### 思考模式模型适配

某些 LLM 端点（如 DashScope Anthropic 兼容端点）默认启用 **thinking mode**，不支持 `tool_choice` 参数。

| 模型类型 | 调用方式 | 说明 |
|---------|---------|------|
| 思考模式 | `llm.invoke()` + JSON prompt + 手动解析 | 检测 `thinking_mode=True` 或 DashScope 端点 |
| 非思考模式 | `with_structured_output()` | 标准 OpenAI/Anthropic API |

**关键文件**：
- `app/core/config_service.py`: AIModelConfig 增加 `thinking_mode` 属性
- `app/pipeline/nodes.py`: sql_generation_node 条件分支处理

## 项目结构

```
nl2sql-langgraph/
├── app/                          # 后端 Python 模块
│   ├── __init__.py
│   ├── main.py                   # FastAPI 应用入口（API 路由 + 静态文件服务）
│   ├── state.py                  # NL2SQLState TypedDict（图状态定义）
│   ├── graph_builder.py          # LangGraph StateGraph 构建（梭子形流程）
│   ├── nodes.py                  # 所有节点函数（问题分析、检索、SQL 生成/执行）
│   ├── tools.py                  # PostgreSQL 数据库工具（execute_sql、fetch_*_hits）
│   ├── mysql_tools.py            # MySQL 数据库工具（历史记录 CRUD）
│   ├── history_routes.py         # 历史记录 API 路由
│   ├── prompt_templates.py       # LLM SQL 生成的系统/用户提示词
│   ├── streaming.py              # SSE 流式执行支持
│   ├── agent_state.py            # ReAct Agent 状态定义
│   ├── agent_tools.py            # ReAct Agent 工具函数（8 个 LangChain Tool）
│   ├── agent_nodes.py            # ReAct Agent 节点函数（think/tools/reflect）
│   ├── agent_graph.py            # ReAct Agent LangGraph 构建
│   ├── agent_routes.py           # ReAct Agent API 路由
│   ├── semantic_matcher.py       # 语义字段匹配服务
│   ├── sql_validator.py          # SQL 验证与自动修正
│   ├── example_sql_generator.py  # 示例 SQL 生成器
│   ├── schema_engine.py          # Schema 提取引擎
│   ├── learning_service.py       # Schema 学习服务
│   └── settings_routes.py        # 设置管理 API 路由
├── db/                           # 数据库脚本
│   ├── __init__.py
│   ├── schema.sql                # PostgreSQL 表结构定义
│   ├── seed.sql                  # PostgreSQL 种子数据
│   ├── vector_schema.sql         # pgvector 向量字段定义
│   └── mysql_schema.sql          # MySQL 平台数据库表结构
├── scripts/                      # 脚本目录
│   └── init_embeddings.py        # Embedding 初始化脚本
├── frontend/                     # Vue 3 前端
│   ├── src/
│   │   ├── api/
│   │   │   └── query.ts          # API 调用封装（fetch + 历史记录 API）
│   │   ├── stores/
│   │   │   └── queryStore.ts     # Pinia 状态管理
│   │   ├── types/
│   │   │   └── index.ts          # TypeScript 类型定义
│   │   ├── views/
│   │   │   ├── QueryView.vue     # 主查询页面
│   │   │   └── components/
│   │   │       ├── QueryInput.vue        # 查询输入框
│   │   │       ├── InputBox.vue          # 输入框组件
│   │   │       ├── FlowGraph.vue         # LangGraph 流程图可视化（Vue Flow）
│   │   │       ├── StepProgressBar.vue   # 步骤进度条
│   │   │       ├── MessageCard.vue       # 消息卡片
│   │   │       ├── ResultTable.vue       # 结果表格
│   │   │       ├── ChartPanel.vue        # 图表面板（ECharts）
│   │   │       ├── HistoryPanel.vue      # 历史记录面板（搜索、筛选、分页）
│   │   │       ├── Sidebar.vue           # 侧边栏
│   │   │       ├── ExampleQuestions.vue  # 示例问题
│   │   │       └── step-details/         # 步骤详情组件
│   │   │           ├── AnalysisStepDetail.vue
│   │   │           ├── RetrievalStepDetail.vue
│   │   │           ├── RetrievalList.vue
│   │   │           ├── SQLStepDetail.vue
│   │   │           └── ExecutionStepDetail.vue
│   │   ├── App.vue
│   │   └── main.ts
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
├── static/                       # 前端构建输出（由 npm run build 生成）
├── .env.example                  # 环境变量示例
├── requirements.txt              # Python 依赖
├── pyproject.toml                # 项目配置
└── README.md
```

## 架构：「梭子形」混合检索 NL2SQL 流水线

基于 LangGraph 的自然语言转 SQL 系统，采用扇出/扇入（梭子形）架构，支持**混合检索（LIKE + 向量 + RRF 融合）**：

```
问题 → 分析器 → 向量生成 → [并行混合检索] → 合并 → 元数据分析 → SQL生成 → SQL执行
                           ↓
         ┌─────────────────┼─────────────────┐
         ↓                 ↓                 ↓
    知识检索(混合)     指标检索(混合)     元数据检索(混合)
         │                 │                 │
         ├─ LIKE匹配       ├─ LIKE匹配       ├─ LIKE匹配
         ├─ 向量检索       ├─ 向量检索       ├─ 向量检索
         │  (多embedding)  │  (多embedding)  │  (多embedding)
         └─ RRF融合        └─ RRF融合        └─ RRF融合
         └─────────────────┼─────────────────┘
                           ↓
                上下文合并 → 选择表/JOIN → 生成SQL → 执行
```

### 混合检索核心机制

#### 1. RRF（Reciprocal Rank Fusion）算法

**公式**：`RRF_score(d) = Σ 1/(k + rank_i(d))`，其中 `k=60`

| 参数 | 说明 |
|------|------|
| `k` | 平滑参数，默认 60 |
| `rank_i(d)` | 文档 d 在第 i 个检索列表中的排名 |
| `RRF_score` | 最终融合分数，越高越相关 |

**算法特点**：
- 无需分数归一化，直接基于排名融合
- 对各检索系统权重平等，避免调参复杂度
- 同时命中多路检索的结果分数叠加，提升召回

#### 2. 多路检索并行执行

| 检索方式 | 说明 | 优势 |
|---------|------|------|
| **LIKE 检索** | SQL `LIKE ANY (%keyword%)` 匹配 | 精确关键词命中，覆盖已知术语 |
| **向量检索** | pgvector `embedding <=> query_vector` 余弦距离 | 语义相似度匹配，覆盖同义表述 |

**向量检索多 Embedding 字段**：

| 表名 | Embedding 字段 | 用途 |
|------|---------------|------|
| `enterprise_kb` | `keyword_embedding` | 关键词语义匹配 |
| `enterprise_kb` | `business_embedding` | 业务含义语义匹配 |
| `metrics_catalog` | `metric_embedding` | 指标名称语义匹配 |
| `metrics_catalog` | `synonym_embedding` | 指标同义词语义匹配 |
| `lake_table_metadata` | `topic_embedding` | 主题语义匹配 |
| `lake_table_metadata` | `metric_embedding` | 指标语义匹配 |

向量检索对每个表的多个 embedding 字段分别查询，结果合并去重（取最小 cosine_distance）。

#### 3. 检索结果字段

每条检索结果包含以下融合相关字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `rrf_score` | float | RRF 融合分数（越高越相关） |
| `like_rank` | int/null | LIKE 检索排名（未命中为 null） |
| `vector_rank` | int/null | 向量检索排名（未命中为 null） |
| `cosine_distance` | float/null | 向量余弦距离（越小越相似） |
| `cosine_similarity` | float/null | 余弦相似度 = 1 - cosine_distance |
| `_retrieval_method` | string | 检索来源标记 |

**`_retrieval_method` 标记值**：

| 值 | 含义 | 触发条件 |
|----|------|---------|
| `"hybrid"` | LIKE + 向量融合命中 | `like_rank` 和 `vector_rank` 都不为 null |
| `"like_only"` | 仅 LIKE 命中 | `like_rank` 不为 null，`vector_rank` 为 null |
| `"vector_only"` | 仅向量命中 | `like_rank` 为 null，`vector_rank` 不为 null |

#### 4. 混合检索函数

| 函数 | 表名 | LIKE 条件 | Embedding 字段 |
|------|------|----------|---------------|
| `hybrid_knowledge_search()` | `enterprise_kb` | `keyword_synonyms`, `business_meaning` | `keyword_embedding`, `business_embedding` |
| `hybrid_metrics_search()` | `metrics_catalog` | `metric_synonyms`, `metric_name` | `metric_embedding`, `synonym_embedding` |
| `hybrid_metadata_search()` | `lake_table_metadata` | `topic`, `metric_name` | `topic_embedding`, `metric_embedding` |

#### 5. 降级机制

当 `QWEN_API_KEY` 未配置时：
- `embedding_generation_node` 跳过向量生成
- 检索退化为**纯 LIKE 模式**
- `_retrieval_method` 全部为 `"like_only"`

#### 6. 前端可视化

检索结果在前端 `RetrievalStepDetail.vue` 和 `RetrievalList.vue` 中展示：
- **混合状态徽章**：显示「混合检索已激活」
- **检索方法统计**：hybrid/like_only/vector_only 计数
- **RRF 分数展示**：每条结果的 `rrf_score` 值
- **检索方法徽章**：每条结果的 `_retrieval_method` 标记（蓝/黄/绿三色）

### 核心组件

| 文件 | 说明 |
|------|------|
| [app/pipeline/state.py](app/pipeline/state.py) | `NL2SQLState` TypedDict，包含 query_embedding |
| [app/pipeline/graph_builder.py](app/pipeline/graph_builder.py) | LangGraph StateGraph 构建，含 embedding_generation_node |
| [app/pipeline/nodes.py](app/pipeline/nodes.py) | 所有节点函数（含 embedding_generation_node） |
| [app/pipeline/tools.py](app/pipeline/tools.py) | 混合检索函数：`reciprocal_rank_fusion()`、`vector_search()`、`hybrid_*_search()` |
| [app/core/embedding_service.py](app/core/embedding_service.py) | 通义千问 Embedding 服务（text-embedding-v3，1024 维） |
| [app/pipeline/streaming.py](app/pipeline/streaming.py) | SSE 流式执行支持 |

### 执行流程

1. `analyze_question_node`: 通过数据库词表匹配提取问题关键词
2. `embedding_generation_node`: 生成问题的向量嵌入（1024 维）
   - 调用 `QwenEmbeddingService.embed_text()`
   - 如果 `QWEN_API_KEY` 未配置，跳过向量生成，检索退化为纯 LIKE
3. 三个并行检索节点执行混合检索：
   - `knowledge_retrieval_node`: 调用 `hybrid_knowledge_search()`
   - `metrics_retrieval_node`: 调用 `hybrid_metrics_search()`
   - `metadata_retrieval_node`: 调用 `hybrid_metadata_search()`
   - 每个节点都执行 LIKE + 多向量字段检索 + RRF 融合
4. `merge_context_node`: 从元数据命中中收集候选表
5. `metadata_analysis_node`: 选择表和 join 逻辑
6. `sql_generation_node`: 生成 SQL（规则模式或 LLM 模式）
7. `sql_execution_node`: 执行 SQL，失败时自动重试

## 数据库架构

系统使用双数据库架构：

| 数据库 | 用途 | 表 |
|--------|------|-----|
| PostgreSQL + pgvector | 问数业务数据 + 向量检索 | `enterprise_kb`, `metrics_catalog`, `lake_table_metadata`, `fact_orders` |
| MySQL | 平台数据 | `query_history`, `user_preferences` |

### PostgreSQL 表（业务数据）

| 表名 | 说明 | 向量字段 |
|------|------|---------|
| `enterprise_kb` | 企业知识库/术语表 | `keyword_embedding`, `business_embedding` |
| `metrics_catalog` | 指标口径目录 | `metric_embedding`, `synonym_embedding` |
| `lake_table_metadata` | 湖表业务元数据 | `topic_embedding`, `metric_embedding` |
| `fact_orders` | 示例事实表（用于测试） | - |

### pgvector 向量索引

所有向量字段使用 HNSW 索引（高性能近似检索）：
- 索引参数：`m = 16, ef_construction = 64`
- 距离度量：余弦距离（`vector_cosine_ops`）
- 向量维度：1024

### MySQL 表（平台数据）

| 表名 | 说明 |
|------|------|
| `query_history` | 查询历史记录（question、generated_sql、columns、rows、is_favorite） |
| `user_preferences` | 用户偏好设置（预留） |

## API 接口

### POST /query
同步查询接口，返回完整结果。执行后自动保存到历史记录。

```json
// Request
{ "question": "查询过去30天按地区的订单金额" }

// Response
{
  "question": "查询过去30天按地区的订单金额",
  "sql": "SELECT region, SUM(order_amount) AS metric_value FROM fact_orders WHERE ...",
  "columns": ["region", "metric_value"],
  "rows": [["华东", 12345.67], ["华南", 9876.54]],
  "attempt": 1,
  "execution_error": null
}
```

### GET /stream
SSE 流式接口，实时返回执行进度。执行后自动保存到历史记录。

```
event: init
data: {"graph": {...}, "question": "..."}

event: node_start
data: {"node": "analyze_question", "label": "问题分析", "status": "running"}

event: node_complete
data: {"node": "analyze_question", "label": "问题分析", "status": "completed", "output": {...}}

event: result
data: {"question": "...", "sql": "...", "columns": [...], "rows": [...]}
```

### GET /graph/structure
返回 LangGraph 图结构，供前端可视化。

### 历史记录 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/history` | 获取历史列表（支持分页、搜索、筛选） |
| GET | `/history/{id}` | 获取单条历史记录 |
| PATCH | `/history/{id}` | 更新历史记录（收藏状态） |
| DELETE | `/history/{id}` | 删除单条历史记录 |
| POST | `/history/batch-delete` | 批量删除历史记录 |
| DELETE | `/history/clear` | 清空所有历史记录 |

**历史列表查询参数：**
- `page`: 页码（默认 1）
- `page_size`: 每页数量（默认 20）
- `is_favorite`: 是否收藏筛选
- `search`: 搜索关键词（问题或 SQL）
- `start_date`: 开始日期
- `end_date`: 结束日期

## 技术栈

**后端：**
- Python 3.12+
- FastAPI + Uvicorn
- LangGraph（状态图编排）
- LangChain + OpenAI（可选 LLM 模式）
- psycopg（PostgreSQL 驱动）
- pgvector（向量检索扩展）
- PyMySQL（MySQL 驱动）
- Pydantic（数据验证）
- OpenAI SDK（通义千问 Embedding）

**前端：**
- Vue 3 + TypeScript
- Vite
- Pinia（状态管理）
- Element Plus（UI 组件库）
- Vue Flow（流程图可视化）
- ECharts（图表）
- TailwindCSS
