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
│   └── streaming.py              # SSE 流式执行支持
├── db/                           # 数据库脚本
│   ├── __init__.py
│   ├── schema.sql                # PostgreSQL 表结构定义
│   ├── seed.sql                  # PostgreSQL 种子数据
│   └── mysql_schema.sql          # MySQL 平台数据库表结构
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

## 架构：「梭子形」多 Agent NL2SQL 流水线

基于 LangGraph 的自然语言转 SQL 系统，采用扇出/扇入（梭子形）架构：

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

**核心组件：**

- [app/state.py](app/state.py): `NL2SQLState` TypedDict，定义图状态
- [app/graph_builder.py](app/graph_builder.py): LangGraph StateGraph 构建，包含并行边
- [app/nodes.py](app/nodes.py): 所有节点函数（问题分析、检索节点、SQL 生成、SQL 执行）
- [app/tools.py](app/tools.py): PostgreSQL 数据库工具（execute_sql、fetch_*_hits 函数）
- [app/mysql_tools.py](app/mysql_tools.py): MySQL 数据库工具（历史记录 CRUD）
- [app/history_routes.py](app/history_routes.py): 历史记录 API 路由
- [app/prompt_templates.py](app/prompt_templates.py): LLM SQL 生成的系统/用户提示词
- [app/streaming.py](app/streaming.py): SSE 流式执行支持

**执行流程：**
1. `analyze_question_node`: 通过数据库词表匹配提取问题关键词
2. 三个并行检索节点从以下表获取上下文：
   - `enterprise_kb`: 业务术语和示例 Q&A
   - `metrics_catalog`: 指标定义和聚合规则
   - `lake_table_metadata`: 指标对应的表/字段映射
3. `merge_context_node`: 从元数据命中中收集候选表
4. `metadata_analysis_node`: 选择表和 join 逻辑
5. `sql_generation_node`: 生成 SQL（规则模式或 LLM 模式）
6. `sql_execution_node`: 执行 SQL，失败时自动重试

## 数据库架构

系统使用双数据库架构：

| 数据库 | 用途 | 表 |
|--------|------|-----|
| PostgreSQL | 问数业务数据 | `enterprise_kb`, `metrics_catalog`, `lake_table_metadata`, `fact_orders` |
| MySQL | 平台数据 | `query_history`, `user_preferences` |

### PostgreSQL 表（业务数据）

| 表名 | 说明 |
|------|------|
| `enterprise_kb` | 企业知识库/术语表（keyword_synonyms、business_meaning、example_sql_template） |
| `metrics_catalog` | 指标口径目录（metric_name、metric_synonyms、business_definition、aggregation_rule） |
| `lake_table_metadata` | 湖表业务元数据（topic、metric_name、fact_table、measure_sql_expression） |
| `fact_orders` | 示例事实表（用于测试） |

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
- PyMySQL（MySQL 驱动）
- Pydantic（数据验证）

**前端：**
- Vue 3 + TypeScript
- Vite
- Pinia（状态管理）
- Element Plus（UI 组件库）
- Vue Flow（流程图可视化）
- ECharts（图表）
- TailwindCSS
