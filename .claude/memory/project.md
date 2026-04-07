# 项目上下文

> **用途**：记录项目的业务背景、核心术语和技术决策，帮助 AI 理解项目全貌。
> **更新方式**：手动编辑，或通过 `/sync` 命令自动更新。

---

## 业务背景

本项目是 **NL2SQL 智能问数系统**，将自然语言转换为 SQL 查询。

### 核心功能
- 自然语言问题理解与关键词提取
- 企业知识库、指标目录、元数据检索
- SQL 语句生成（规则模式或 LLM 模式）
- SQL 执行与结果展示
- 查询历史记录管理

### 目标用户
- 数据分析师
- 业务人员
- 管理层

---

## 核心术语

### 架构术语
| 术语 | 说明 |
|------|------|
| 梭子形架构 | 扇出/扇入的多 Agent 流水线，中间并行检索 |
| State | LangGraph 状态，使用 TypedDict 定义 |
| Node | LangGraph 节点函数，接收 State 返回 dict |
| 并行边 | StateGraph 中的多路径并行执行 |

### 业务术语
| 术语 | 说明 |
|------|------|
| 知识检索 | 从 enterprise_kb 表检索业务术语和示例 Q&A |
| 指标检索 | 从 metrics_catalog 表检索指标定义和聚合规则 |
| 元数据检索 | 从 lake_table_metadata 表检索表结构和字段映射 |
| Mock 模式 | 基于规则引擎生成 SQL，无需 LLM API |
| LLM 模式 | 调用 OpenAI API 生成 SQL |

---

## 技术栈

### 后端
| 技术 | 用途 |
|------|------|
| Python 3.12+ | 主要开发语言 |
| FastAPI | Web 框架 |
| LangGraph | 流程编排 |
| psycopg | PostgreSQL 驱动 |
| PyMySQL | MySQL 驱动 |
| Pydantic | 数据验证 |
| OpenAI SDK | LLM 调用 |

### 前端
| 技术 | 用途 |
|------|------|
| Vue 3 | 前端框架 |
| TypeScript | 类型安全 |
| Pinia | 状态管理 |
| Element Plus | UI 组件库 |
| Vue Flow | 流程图可视化 |
| ECharts | 图表展示 |
| TailwindCSS | 样式框架 |

### 数据库
| 数据库 | 用途 |
|--------|------|
| PostgreSQL | 问数业务数据（知识库、指标、元数据、事实表） |
| MySQL | 平台数据（会话、历史记录） |

---

## 目录结构

```
nl2sql-langgraph/
├── app/                  # 后端 Python 模块
│   ├── state.py         # State 定义
│   ├── graph_builder.py # 图构建
│   ├── nodes.py         # 节点函数
│   ├── tools.py         # PostgreSQL 工具
│   ├── mysql_tools.py   # MySQL 工具
│   ├── streaming.py     # SSE 流式支持
│   └── main.py          # FastAPI 入口
├── frontend/            # Vue 3 前端
│   └── src/
│       ├── views/       # 页面组件
│       ├── stores/      # Pinia 状态
│       ├── api/         # API 调用
│       └── types/       # TypeScript 类型
├── db/                  # 数据库脚本
│   ├── schema.sql       # PostgreSQL 建表
│   ├── seed.sql         # PostgreSQL 种子数据
│   └── mysql_schema.sql # MySQL 建表
└── .claude/             # AI 助手配置
    ├── skills/          # 技能库
    ├── commands/        # 斜杠命令
    ├── hooks/           # 生命周期钩子
    └── memory/          # 记忆存储
```

---

## PostgreSQL 表结构详解

> **重要**：表结构变更时必须同步更新此文档，可通过 `db-meta-query` 技能查询实时结构。

### 表分类总览

| 分类 | 表数量 | 表名 | 数据特点 |
|------|--------|------|----------|
| **维度表** | 4 | `dim_region`, `dim_product`, `dim_customer`, `dim_channel` | 相对静态，用于 GROUP BY 维度 |
| **事实表** | 1 | `fact_orders` | 大量交易数据，用于聚合计算 |
| **知识库表** | 3 | `enterprise_kb`, `metrics_catalog`, `lake_table_metadata` | NL2SQL 专用，存储语义映射 |
| **学习结果表** | 1 | `field_metadata` | Schema 学习产物，LLM 生成内容 |

---

### 一、维度表

#### dim_region（地区维度表）
| 字段 | 类型 | 说明 |
|------|------|------|
| `region_id` | SERIAL | 主键 |
| `region_code` | TEXT | 地区编码（唯一，事实表关联键） |
| `region_name` | TEXT | 地区名称 |
| `province` / `city` | TEXT | 省/市 |
| `region_level` | TEXT | 层级：省/市/区 |
| `parent_region_id` | INTEGER | 父级地区 ID（支持层级结构） |

#### dim_product（产品维度表）
| 字段 | 类型 | 说明 |
|------|------|------|
| `product_id` | SERIAL | 主键 |
| `product_code` | TEXT | 产品编码（唯一，事实表关联键） |
| `product_name` | TEXT | 产品名称 |
| `category_l1` / `category_l2` | TEXT | 一级/二级品类 |
| `brand` | TEXT | 品牌 |
| `unit_price` | NUMERIC(10,2) | 单价 |
| `status` | TEXT | 状态（默认 active） |

#### dim_customer（客户维度表）
| 字段 | 类型 | 说明 |
|------|------|------|
| `customer_id` | SERIAL | 主键 |
| `customer_code` | TEXT | 客户编码（唯一，事实表关联键） |
| `customer_name` | TEXT | 客户名称 |
| `gender` / `age_group` | TEXT | 性别/年龄段 |
| `member_level` | TEXT | 会员等级：普通/银卡/金卡/钻石 |
| `register_date` | DATE | 注册日期 |
| `city` | TEXT | 所在城市 |

#### dim_channel（渠道维度表）
| 字段 | 类型 | 说明 |
|------|------|------|
| `channel_id` | SERIAL | 主键 |
| `channel_code` | TEXT | 渠道编码（唯一，事实表关联键） |
| `channel_name` | TEXT | 渠道名称 |
| `channel_type` | TEXT | 类型：线上/线下 |
| `platform` | TEXT | 平台：APP/小程序/门店 |

---

### 二、事实表

#### fact_orders（订单事实表）- 核心业务表
| 字段 | 类型 | 说明 |
|------|------|------|
| `order_id` | BIGINT | 主键 |
| `order_date` | DATE | 下单日期（索引） |
| `order_time` | TIMESTAMP | 下单时间戳 |
| `customer_code` | TEXT | 客户编码（关联 dim_customer） |
| `product_code` | TEXT | 产品编码（关联 dim_product） |
| `region_code` | TEXT | 地区编码（关联 dim_region） |
| `channel_code` | TEXT | 渠道编码（关联 dim_channel） |
| `quantity` | INTEGER | 数量 |
| `unit_price` | NUMERIC(10,2) | 单价 |
| `order_amount` | NUMERIC(18,2) | 订单金额 |
| `discount_amount` | NUMERIC(18,2) | 优惠金额 |
| `actual_amount` | NUMERIC(18,2) | 实付金额 |
| `profit_amount` | NUMERIC(18,2) | 利润金额 |
| `order_status` | TEXT | 订单状态 |

**关键设计特点**：
- 使用 **业务编码（code）** 而非 ID 关联维度表，便于直接查询
- 包含完整金额链路：`order_amount` → `discount_amount` → `actual_amount` → `profit_amount`
- 核心索引：`order_date`, `customer_code`, `product_code`, `region_code`, `channel_code`

---

### 三、知识库表（NL2SQL 核心表）

#### enterprise_kb（企业知识库/术语表）
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | SERIAL | 主键 |
| `topic` | TEXT | 主题分类 |
| `keyword_synonyms` | TEXT | 关键词同义词列表 |
| `business_meaning` | TEXT | 业务含义解释 |
| `example_question` | TEXT | 示例问题 |
| `example_sql_template` | TEXT | 示例 SQL 模板 |

**NL2SQL 作用**：`retrieve_knowledge_node` 节点从中检索业务术语、同义词映射、示例 SQL

#### metrics_catalog（指标口径目录）
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | SERIAL | 主键 |
| `metric_name` | TEXT | 指标名称 |
| `metric_synonyms` | TEXT | 指标同义词 |
| `business_definition` | TEXT | 业务定义 |
| `aggregation_rule` | TEXT | 聚合规则（SUM/COUNT/AVG 等） |
| `target_column` | TEXT | 目标列名 |

**NL2SQL 作用**：`retrieve_metrics_node` 节点从中检索指标定义、聚合规则

#### lake_table_metadata（湖表业务元数据）
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | SERIAL | 主键 |
| `topic` | TEXT | 主题 |
| `metric_name` | TEXT | 指标名称 |
| `fact_table` | TEXT | 事实表名 |
| `fact_time_column` | TEXT | 时间字段 |
| `fact_region_column` | TEXT | 地区字段 |
| `dimension_table` | TEXT | 维度表名 |
| `dimension_join_key` | TEXT | 维度关联键 |
| `measure_column` | TEXT | 度量字段 |
| `measure_sql_expression` | TEXT | 度量 SQL 表达式 |
| `table_type` | VARCHAR(20) | 表类型：fact/dimension/other |
| `table_comment` | TEXT | 表注释 |
| `field_type` | VARCHAR(20) | 字段类型：DateTime/Enum/Code/Text/Measure |
| `is_dimension` | BOOLEAN | 是否为维度字段 |
| `date_granularity` | VARCHAR(20) | 时间颗粒度 |
| `examples` | JSONB | 示例值列表 |
| `llm_description` | TEXT | LLM 生成的描述 |

**NL2SQL 作用**：`retrieve_metadata_node` 节点从中检索指标对应的表名、字段名、JOIN 关系

---

### 四、学习结果表

#### field_metadata（字段级元数据表）- Schema 学习存储
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | SERIAL | 主键 |
| `table_name` | TEXT | 表名 |
| `column_name` | TEXT | 字段名 |
| `data_type` | TEXT | 数据类型 |
| `is_primary_key` | BOOLEAN | 是否主键 |
| `is_nullable` | BOOLEAN | 是否可空 |
| `column_comment` | TEXT | 字段注释 |
| `field_category` | VARCHAR(20) | 字段分类：DateTime/Enum/Code/Text/Measure |
| `dim_or_meas` | VARCHAR(20) | 维度/度量 |
| `date_granularity` | VARCHAR(20) | 时间颗粒度 |
| `examples` | JSONB | 示例值列表 |
| `llm_description` | TEXT | LLM 生成的描述 |
| `business_term` | TEXT | 业务术语 |
| `synonym` | TEXT | 同义词 |

**用途**：存储 Schema 学习服务生成的字段语义描述、分类、示例值

---

### 各表在 LangGraph 流程中的作用

```
问题分析 → [并行检索] → 合并 → 元数据分析 → SQL生成 → SQL执行
              ↓
    ┌─────────┼─────────┐
    ↓         ↓         ↓
enterprise_kb  metrics_catalog  lake_table_metadata
    └─────────┼─────────┘
              ↓
        上下文合并 → 选择表/JOIN → 生成SQL → 执行(fact_orders)
```

| 表 | 检索节点 | 提供的上下文 |
|----|----------|-------------|
| `enterprise_kb` | `retrieve_knowledge_node` | 业务术语解释、同义词映射、示例 SQL 模板 |
| `metrics_catalog` | `retrieve_metrics_node` | 指标定义、聚合规则（如何计算）、目标列 |
| `lake_table_metadata` | `retrieve_metadata_node` | 指标对应的表名、字段名、JOIN 关系 |
| `fact_orders` | SQL 执行节点 | 实际业务数据，验证生成的 SQL |
| `field_metadata` | Schema 学习服务 | 字段语义描述、分类、示例值 |

---

### 表结构同步机制

> **当表结构变更时，必须执行以下同步操作**：

| 变更类型 | 同步操作 | 触发技能 |
|---------|---------|---------|
| 新增表 | 更新 schema.sql + 此文档 + CLAUDE.md | `database-ops` |
| 新增字段 | 更新 schema.sql + 此文档 | `db-meta-query` |
| 字段类型变更 | 更新 schema.sql + 此文档 | `db-meta-query` |
| 索引变更 | 更新 schema.sql | `db-meta-query` |

**同步检查命令**：
```bash
# 查询当前表结构，对比文档
python scripts/db_meta.py tables
python scripts/db_meta.py columns <表名>
```

---

## 关键设计决策

### 1. 双数据库架构
- **PostgreSQL**：存储业务数据（知识库、指标、事实表）
- **MySQL**：存储平台数据（会话、历史）
- **原因**：业务数据需要复杂的 JSON 查询能力，平台数据需要简单可靠的关系存储

### 2. 梭子形流水线
- 分析节点提取关键词后，三个检索节点并行执行
- 合并节点汇总检索结果后，生成并执行 SQL
- **原因**：并行检索提升响应速度

### 3. Mock + LLM 双模式
- Mock 模式：基于规则，快速响应，适合开发和测试
- LLM 模式：基于 AI，理解自然语言，适合生产环境
- **原因**：降低开发门槛，同时保留生产环境能力

---

## 已知限制

1. **Mock 模式**只能处理预定义的问题模板
2. **LLM 模式**需要 OpenAI API Key
3. **SQL 执行**只允许 SELECT 语句
4. **并发**当前为单实例部署，无分布式支持

---

## 开发环境配置

### Python 虚拟环境
- **路径**：`D:\01_AlCoding_Test\langgraph_agent_venv`（与项目目录齐平）
- **启动后端**：`cd d:/01_AlCoding_Test/nl2sql-langgraph && D:/01_AlCoding_Test/langgraph_agent_venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000`
- **注意**：必须从项目根目录启动，确保 `.env` 文件路径正确解析