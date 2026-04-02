# nl2sql-langgraph

基于 **LangGraph** 的「梭子形多 Agent 协作」NL2SQL 系统，支持自然语言转 SQL 查询、流式执行、会话管理、历史记录。

## 架构概览

### 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              前端层 (Vue 3)                              │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ 查询输入  │  │ 流程可视化 │  │ 结果展示  │  │ 图表面板  │  │ 历史记录  │  │
│  │InputBox  │  │FlowGraph │  │ResultTable│  │ChartPanel│  │Sidebar   │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │             │             │             │             │        │
│       └─────────────┴─────────────┴─────────────┴─────────────┘        │
│                                   │                                    │
│                          Pinia Store (queryStore)                      │
│                     ┌─────────────┴─────────────┐                      │
│                     │  currentSessionId         │                      │
│                     │  conversations[]          │                      │
│                     │  result / error           │                      │
│                     └─────────────┬─────────────┘                      │
└───────────────────────────────────┼─────────────────────────────────────┘
                                    │ SSE / HTTP
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            后端层 (FastAPI)                              │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      API Routes                                 │   │
│  │  POST /query  │  GET /stream  │  GET /history  │  /history/session │
│  └─────────────────────────────┬───────────────────────────────────┘   │
│                                │                                        │
│  ┌─────────────────────────────┴───────────────────────────────────┐   │
│  │                    LangGraph 执行引擎                             │   │
│  │                                                                  │   │
│  │   问题 → 分析器 ──────→ [并行检索] ──────→ 合并 → SQL生成 → 执行   │   │
│  │                           │                                      │   │
│  │              ┌────────────┼────────────┐                         │   │
│  │              ↓            ↓            ↓                         │   │
│  │         知识检索      指标检索      元数据检索                     │   │
│  │              └────────────┼────────────┘                         │   │
│  │                           ↓                                      │   │
│  │                     上下文合并                                    │   │
│  └─────────────────────────────┬───────────────────────────────────┘   │
│                                │                                        │
│  ┌─────────────────────────────┴───────────────────────────────────┐   │
│  │                    MySQL Tools (会话管理)                         │   │
│  │          create_session() / create_history()                     │   │
│  └─────────────────────────────┬───────────────────────────────────┘   │
└────────────────────────────────┼────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
┌──────────────────────────────┐  ┌──────────────────────────────────────┐
│   PostgreSQL (业务数据)       │  │        MySQL (平台数据)              │
├──────────────────────────────┤  ├──────────────────────────────────────┤
│  enterprise_kb    企业知识库  │  │  chat_session        会话表         │
│  metrics_catalog  指标口径    │  │  query_history       问答对表       │
│  lake_table_metadata 元数据   │  │  user_preferences    用户偏好       │
│  fact_orders      订单事实表  │  │                                      │
│  dim_customer     客户维度    │  │  会话结构:                           │
│  dim_product      产品维度    │  │  session_1                           │
│  dim_region       地区维度    │  │    └─ history_1 (问答对)            │
│  dim_channel      渠道维度    │  │    └─ history_2 (重新回答)          │
└──────────────────────────────┘  │  session_2                           │
                                  │    └─ history_3                      │
                                  └──────────────────────────────────────┘
```

### LangGraph 执行流程（梭子形）

```
                    ┌─────────────────┐
                    │   问题分析       │
                    │ analyze_question │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ 知识检索  │  │ 指标检索  │  │ 元数据检索 │
        │knowledge │  │ metrics  │  │ metadata │
        │retrieval │  │retrieval │  │retrieval │
        └────┬─────┘  └────┬─────┘  └────┬─────┘
              │              │              │
              └──────────────┼──────────────┘
                             ▼
                    ┌─────────────────┐
                    │   上下文合并     │
                    │  merge_context  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   元数据分析     │
                    │metadata_analysis│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    SQL生成      │
                    │  sql_generation │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    SQL执行      │
                    │  sql_execution  │
                    └─────────────────┘
```

### 会话与问答对关系

```
┌─────────────────────────────────────────────────────────────┐
│                        会话 (Session)                        │
│  session_id: 1                                               │
│  title: "查询过去30天各地区的订单金额"                         │
│  created_at: 2026-04-01 10:00:00                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 问答对 1 (history_id: 101)                            │   │
│  │ question: "查询过去30天各地区的订单金额"                │   │
│  │ sql: SELECT region, SUM(...) FROM ...                 │   │
│  │ created_at: 2026-04-01 10:00:05                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 问答对 2 (history_id: 102)  ← 重新回答生成             │   │
│  │ question: "查询过去30天各地区的订单金额"                │   │
│  │ sql: SELECT region, SUM(...) FROM ...  (新SQL)        │   │
│  │ created_at: 2026-04-01 10:01:30                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 环境要求

- Python **3.12+**
- PostgreSQL（业务数据）
- MySQL（平台数据：历史记录等）
- Node.js 18+（前端开发）

## 快速开始

### 1. 安装后端依赖

```powershell
pip install -r requirements.txt
```

### 2. 配置环境变量

```powershell
copy .env.example .env
```

编辑 `.env`，配置数据库连接信息。

### 3. 初始化数据库

**PostgreSQL（业务数据）：**
```powershell
psql $env:POSTGRES_DSN -f .\db\schema.sql
psql $env:POSTGRES_DSN -f .\db\seed.sql
```

**生成增强示例数据（可选）：**
```powershell
python db/generate_sample_data.py
```

**MySQL（平台数据）：**
```powershell
mysql -h $env:MYSQL_HOST -u $env:MYSQL_USER -p$env:MYSQL_PASSWORD < .\db\mysql_schema.sql
```

### 4. 启动后端服务

```powershell
uvicorn app.main:app --reload --port 8000
```

### 5. 安装并启动前端

```powershell
cd frontend && npm install
cd frontend && npm run dev
```

### 6. 访问应用

| 服务 | 地址 |
|------|------|
| 前端页面 | http://localhost:8000/ |
| API 文档 | http://localhost:8000/docs |
| 自定义域名 | http://nl2sql.local:8000/ |

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `POSTGRES_DSN` | PostgreSQL 连接串 | 必填 |
| `MYSQL_HOST` | MySQL 主机 | `localhost` |
| `MYSQL_PORT` | MySQL 端口 | `3306` |
| `MYSQL_USER` | MySQL 用户名 | `root` |
| `MYSQL_PASSWORD` | MySQL 密码 | - |
| `MYSQL_DATABASE` | MySQL 数据库名 | `nl2sql_platform` |
| `USE_MOCK_LLM` | `true` 规则生成，`false` 用 LLM | `true` |
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `OPENAI_API_BASE` | API Base URL（代理） | - |
| `OPENAI_MODEL` | 模型名称 | `gpt-4o-mini` |
| `SQL_MAX_ROWS` | 返回最大行数 | `200` |
| `SQL_MAX_ATTEMPTS` | SQL 重试次数 | `2` |

## 项目结构

```
nl2sql-langgraph/
├── app/                          # 后端 Python 模块
│   ├── main.py                   # FastAPI 入口
│   ├── state.py                  # NL2SQLState 状态定义
│   ├── graph_builder.py          # LangGraph 图构建
│   ├── nodes.py                  # 节点函数
│   ├── tools.py                  # PostgreSQL 工具
│   ├── mysql_tools.py            # MySQL 工具
│   ├── history_routes.py         # 历史记录路由
│   ├── prompt_templates.py       # LLM 提示词
│   └── streaming.py              # SSE 流式支持
├── db/                           # 数据库脚本
│   ├── schema.sql                # PostgreSQL 表结构
│   ├── seed.sql                  # PostgreSQL 种子数据
│   ├── generate_sample_data.py   # 数据生成脚本
│   └── mysql_schema.sql          # MySQL 表结构
├── frontend/                     # Vue 3 前端
│   ├── src/
│   │   ├── api/query.ts          # API 调用
│   │   ├── stores/queryStore.ts  # Pinia 状态
│   │   ├── types/index.ts        # TypeScript 类型
│   │   ├── views/
│   │   │   ├── QueryView.vue
│   │   │   └── components/
│   │   │       ├── QueryInput.vue
│   │   │       ├── InputBox.vue
│   │   │       ├── FlowGraph.vue         # Vue Flow 流程图
│   │   │       ├── StepProgressBar.vue
│   │   │       ├── MessageCard.vue
│   │   │       ├── ResultTable.vue
│   │   │       ├── ChartPanel.vue        # ECharts 图表
│   │   │       ├── HistoryPanel.vue
│   │   │       ├── Sidebar.vue
│   │   │       ├── ExampleQuestions.vue  # 示例问题
│   │   │       └── step-details/         # 步骤详情组件
│   │   └── App.vue
│   └ package.json
│   └ vite.config.ts
│   └ tailwind.config.js
├── static/                       # 前端构建输出
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 示例数据

运行 `python db/generate_sample_data.py` 可生成增强示例数据：

| 维度 | 数量 | 说明 |
|------|------|------|
| 客户 | 50 | 钻石/金卡/银卡/普通会员分布 |
| 产品 | 28 | 低端到奢侈品全价位覆盖 |
| 订单 | 1100+ | 2024.10 - 2026.03 时间范围 |
| 时间范围 | 18个月 | 支持 YoY 同比分析 |

**支持的查询场景：**

| 类别 | 示例问题 |
|------|---------|
| 销售分析 | 查询过去30天各地区的订单金额 |
| 同比分析 | 2025年12月销售额同比增长率 |
| 环比分析 | 各月份环比增长率 |
| 客户分析 | 各会员等级的消费金额分布 |
| RFM分析 | 消费金额超过5万的客户有哪些 |
| 分布分析 | 订单金额区间分布 |
| 占比分析 | 各品类销售额占比 |

## API 接口

### POST /query
同步查询，返回完整结果。

```json
// Request
{ "question": "查询过去30天按地区的订单金额" }

// Response
{
  "question": "...",
  "sql": "SELECT ...",
  "columns": ["region", "metric_value"],
  "rows": [["华东", 12345.67]],
  "attempt": 1
}
```

### GET /stream
SSE 流式接口，实时返回执行进度。

**参数：**
- `question`: 用户问题（必填）
- `session_id`: 会话ID（可选，不传则创建新会话）

### 会话 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/history/session` | 创建新会话 |
| GET | `/history/session` | 会话列表（分页） |
| GET | `/history/session/{id}` | 获取单个会话 |
| PATCH | `/history/session/{id}` | 更新会话标题 |
| DELETE | `/history/session/{id}` | 删除会话及问答对 |

### 问答对 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/history` | 问答对列表（分页、搜索、筛选） |
| GET | `/history/{id}` | 单条问答对 |
| PATCH | `/history/{id}` | 更新（收藏状态） |
| DELETE | `/history/{id}` | 删除单条 |
| POST | `/history/batch-delete` | 批量删除 |
| DELETE | `/history/clear` | 清空所有 |

## 数据库表

### PostgreSQL（业务数据）

| 表名 | 说明 |
|------|------|
| `enterprise_kb` | 企业知识库/术语表 |
| `metrics_catalog` | 指标口径目录 |
| `lake_table_metadata` | 湖表业务元数据 |
| `fact_orders` | 订单事实表 |
| `dim_customer` | 客户维度表 |
| `dim_product` | 产品维度表 |
| `dim_region` | 地区维度表 |
| `dim_channel` | 渠道维度表 |

### MySQL（平台数据）

| 表名 | 说明 |
|------|------|
| `chat_session` | 会话表（每个对话对应一个会话） |
| `query_history` | 问答对表（属于某个会话，支持重新回答） |
| `user_preferences` | 用户偏好（预留） |

**表关系：**
```
chat_session (1) ──────< (N) query_history
     │                        │
     │                        │
     ├─ id                    ├─ id
     ├─ title                 ├─ session_id (FK)
     ├─ created_at            ├─ question
     └─ updated_at            ├─ generated_sql
                              ├─ columns / rows
                              ├─ retry_count
                              └─ created_at
```

## 技术栈

**后端：** Python 3.12+, FastAPI, LangGraph, LangChain, psycopg, PyMySQL

**前端：** Vue 3, TypeScript, Vite, Pinia, Element Plus, Vue Flow, ECharts, TailwindCSS

## 测试命令

```powershell
# 同步接口
curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d "{\"question\":\"查询过去30天按地区的订单金额\"}"

# 流式接口
curl "http://localhost:8000/stream?question=查询过去30天按地区的订单金额"

# 自定义域名访问
curl -X POST http://nl2sql.local:8000/query -H "Content-Type: application/json" -d "{\"question\":\"2025年12月销售额同比增长率\"}"
```