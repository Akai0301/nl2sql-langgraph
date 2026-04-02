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