# .claude 目录架构详解

> **项目**: nl2sql-langgraph（LangGraph 梭子形 NL2SQL 流水线）
> **描述**: Claude Code 智能开发助手配置目录
> **最后更新**: 2026-04-02

---

## 目录结构概览

```
.claude/
├── agents/                    # AI Agent 配置
│   ├── code-reviewer.md       # 代码审查 Agent
│   └── project-manager.md     # 项目管理 Agent
│
├── audio/                     # 音效资源
│   └── completed.wav          # 任务完成提示音
│
├── commands/                  # 斜杠命令定义（9个）
│   ├── add-todo.md           # /add-todo - 添加待办
│   ├── check.md              # /check - 代码规范检查
│   ├── init-docs.md          # /init-docs - 初始化文档
│   ├── next.md               # /next - 下一步建议
│   ├── progress.md           # /progress - 项目进度梳理
│   ├── remember.md           # /remember - 记录经验
│   ├── start.md              # /start - 项目快速了解
│   ├── sync.md               # /sync - 代码状态同步
│   └── update-status.md      # /update-status - 状态更新
│
├── docs/                      # 开发文档（4个）
│   ├── AI代码追踪系统设计手册.md  # AI 代码追踪系统完整设计
│   ├── 环境配置指南.md        # 环境变量配置（双数据库 + LLM）
│   ├── LLM集成指南.md         # Mock/LLM 模式配置与 Prompt 模板
│   └── 数据库连接手册.md      # PostgreSQL + MySQL 双库架构
│
├── hooks/                     # 生命周期钩子（5个）
│   ├── post-tool-use.js      # 工具使用后钩子（AI代码追踪）
│   ├── pre-tool-use.js       # 工具使用前钩子（安全拦截）
│   ├── prepare-commit-msg.js # Git提交消息钩子（注入AI元数据）
│   ├── skill-forced-eval.js  # 强制技能评估钩子
│   └── stop.js               # 会话结束钩子
│
├── skills/                    # 技能库（31个技能）
│   ├── add-skill/            # 添加新技能
│   ├── api-development/      # FastAPI API 开发规范
│   ├── api-doc-sync/         # 接口文档同步生成
│   ├── architecture-design/  # 架构设计
│   ├── brainstorm/           # 头脑风暴
│   ├── bug-detective/        # Bug排查（含 LangGraph 调试）
│   ├── code-patterns/        # 代码规范（LangGraph 模式）
│   ├── database-ops/         # 数据库操作（双库架构）
│   ├── db-meta-query/        # 数据库元数据查询与 SQL 执行
│   ├── dev-docs/             # 研发交付文档生成
│   ├── error-handler/        # 异常处理（含 LangGraph 节点）
│   ├── git-workflow/         # Git工作流
│   ├── http-client/          # 前端 HTTP 客户端（fetch + SSE）
│   ├── json-serialization/   # JSON序列化
│   ├── knowledge-sync/       # 知识反馈与配置同步
│   ├── langgraph-flow/       # LangGraph 流程开发规范
│   ├── lesson-learned/       # 错误记录与经验沉淀
│   ├── nl2sql-pipeline/      # NL2SQL 业务管道规范
│   ├── openai-interaction/   # OpenAI模型交互
│   ├── performance-doctor/   # 性能优化（含 LangGraph 流程）
│   ├── project-navigator/    # 项目导航
│   ├── router-pc/            # 前端路由（Vue Router）
│   ├── store-pc/             # 前端状态管理（Pinia）
│   ├── task-tracker/         # 任务跟踪
│   ├── tech-decision/        # 技术决策
│   ├── test-development/     # 测试开发
│   ├── ui-enhancement/       # UI现代化优化
│   ├── ui-pc/                # Vue 3 + TailwindCSS 组件开发
│   ├── usql-client/          # usql数据库命令行
│   ├── utils-toolkit/        # 工具类
│   └── websocket-sse/        # SSE 流式通信
│
├── templates/                 # 文档模板（3个）
│   ├── 待办清单模板.md        # 待办清单模板
│   ├── 需求文档模板.md        # 需求文档模板
│   └── 项目状态模板.md        # 项目状态模板
│
├── ARCHITECTURE.md           # 本文档
├── framework-config.json     # 框架配置
├── settings.json             # Claude 设置（钩子配置）
└── settings.local.json       # 本地 Claude 设置（不提交）
```

---

## 项目架构：LangGraph 梭子形流水线

nl2sql-langgraph 基于 LangGraph StateGraph 构建，采用**扇出/扇入（梭子形）架构**：

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

### 核心组件

| 文件 | 说明 |
|------|------|
| `app/state.py` | `NL2SQLState` TypedDict，定义图状态 |
| `app/graph_builder.py` | LangGraph StateGraph 构建，包含并行边 |
| `app/nodes.py` | 所有节点函数（问题分析、检索节点、SQL 生成、SQL 执行） |
| `app/tools.py` | PostgreSQL 数据库工具（execute_sql、fetch_*_hits） |
| `app/mysql_tools.py` | MySQL 数据库工具（历史记录 CRUD） |
| `app/streaming.py` | SSE 流式执行支持 |

### 数据库架构

双数据库架构：

| 数据库 | 用途 | 驱动 | 核心表 |
|--------|------|------|--------|
| PostgreSQL | 问数业务数据 | `psycopg` | `enterprise_kb`, `metrics_catalog`, `lake_table_metadata`, `fact_orders` |
| MySQL | 平台数据 | `PyMySQL` | `chat_session`, `query_history` |

---

## 核心组件详解

### 1. 技能系统 (skills/)

技能系统采用 **YAML 头部 + Markdown 内容** 的格式定义。

#### 技能分类（31个）

| 类别 | 技能 | 用途 |
|------|------|------|
| **LangGraph 核心** | langgraph-flow | StateGraph 构建、节点函数开发、SSE 流式 |
| | nl2sql-pipeline | 问题分析、检索、SQL 生成、执行等业务流程 |
| **开发核心** | api-development | FastAPI 接口设计 |
| | api-doc-sync | 接口文档同步生成 |
| | database-ops | 双数据库操作规范 |
| | db-meta-query | 数据库元数据查询与 SQL 执行 |
| | usql-client | usql 数据库命令行工具 |
| **质量保障** | bug-detective | Bug排查（含 LangGraph 调试） |
| | error-handler | 异常处理（含 LangGraph 节点） |
| | performance-doctor | 性能优化（含 LangGraph 流程） |
| | test-development | 测试开发 |
| **工程化** | git-workflow | Git工作流 |
| | code-patterns | 代码规范（LangGraph 模式） |
| | project-navigator | 项目导航 |
| | task-tracker | 任务跟踪 |
| | knowledge-sync | 知识反馈与配置同步 |
| | lesson-learned | 错误记录与经验沉淀 |
| | dev-docs | 研发交付文档生成 |
| **数据处理** | json-serialization | JSON处理 |
| | utils-toolkit | 工具类 |
| **前端（PC端）** | ui-pc | Vue 3 + TailwindCSS 组件开发 |
| | ui-enhancement | UI现代化优化 |
| | store-pc | Pinia状态管理 |
| | router-pc | Vue Router路由 |
| | http-client | fetch + SSE 流式消费 |
| **实时通信** | websocket-sse | SSE 流式通信 |
| **AI协作** | openai-interaction | OpenAI模型交互 |
| **元技能** | add-skill | 创建新技能 |
| | brainstorm | 头脑风暴 |
| | architecture-design | 架构设计 |
| | tech-decision | 技术决策 |

#### 技能激活流程

```
用户输入
    ↓
skill-forced-eval.js Hook 触发
    ↓
评估匹配的技能（基于触发词和场景）
    ↓
逐个调用 Skill(skill-name)
    ↓
读取 .claude/skills/{skill-name}/SKILL.md
    ↓
AI 获得领域知识，开始实现
```

---

### 2. 斜杠命令系统 (commands/)

#### 命令清单（9个）

| 命令 | 功能 | 适用场景 |
|------|------|----------|
| `/start` | 项目快速了解 | 新成员入职、项目交接 |
| `/check` | 代码规范检查 | 代码审查、LangGraph 规范检查 |
| `/progress` | 项目进度梳理 | 生成进度报告 |
| `/sync` | 代码状态同步 | 全量同步代码与文档 |
| `/update-status` | 状态智能更新 | 增量更新项目状态 |
| `/add-todo` | 添加待办事项 | 任务管理 |
| `/next` | 下一步建议 | 获取开发建议 |
| `/init-docs` | 初始化文档 | 项目启动时 |
| `/remember` | 记录经验 | 错误经验、最佳实践 |

---

### 3. 生命周期钩子 (hooks/)

#### 钩子类型（5个）

| 钩子 | 触发时机 | 功能 |
|------|----------|------|
| `skill-forced-eval.js` | 用户提交问题时 | 强制评估并激活相关技能 |
| `pre-tool-use.js` | Bash/Write 工具执行前 | 阻止危险命令、提醒敏感操作 |
| `post-tool-use.js` | Write/Edit 工具执行后 | 记录 AI 修改文件到 session，用于代码追踪 |
| `prepare-commit-msg.js` | git commit 时 | 注入 AI 元数据 Trailers（AI-Lines 等）到提交消息 |
| `stop.js` | Claude 回答结束时 | 清理临时文件、播放完成音效 |

---

### 4. 文档系统 (docs/)

#### 开发文档（4个）

| 文档 | 用途 | 目标读者 |
|------|------|----------|
| `AI代码追踪系统设计手册.md` | AI 代码追踪系统完整设计 | 所有开发者、架构师 |
| `环境配置指南.md` | 环境变量配置（双数据库 + LLM） | 所有开发者 |
| `LLM集成指南.md` | Mock/LLM 模式配置与 Prompt 模板 | 后端开发者 |
| `数据库连接手册.md` | PostgreSQL + MySQL 双库架构 | 数据库设计者 |

---

### 5. 配置文件

#### framework-config.json

框架核心配置，定义模块分类和扫描规则：

```json
{
  "framework": {
    "backend": {
      "modules": ["app"],
      "coreFiles": ["state.py", "graph_builder.py", "nodes.py", "tools.py", "streaming.py"]
    },
    "frontend": {
      "modules": ["frontend"],
      "coreFiles": ["queryStore.ts", "query.ts"]
    }
  },
  "scanRules": {
    "backend": {
      "requiredFiles": ["State", "Node", "Tools"],
      "completenessFormula": "存在核心组件数 / 3 * 100%"
    }
  }
}
```

#### settings.json

Claude Code 设置，配置所有钩子触发规则：

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [{"type": "command", "command": "node .claude/hooks/skill-forced-eval.js"}]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash|Write",
        "hooks": [{"type": "command", "command": "node .claude/hooks/pre-tool-use.js", "timeout": 5000}]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{"type": "command", "command": "node .claude/hooks/post-tool-use.js", "timeout": 3000}]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [{"type": "command", "command": "node .claude/hooks/stop.js", "timeout": 10000}]
      }
    ]
  }
}
```

---

## AI 代码追踪系统

### 系统概述

追踪 Claude Code 产生的代码量，统计 AI 代码在项目中的占比，并在 git commit 时自动注入元数据。

### 组件关系

```
Claude Code Write/Edit
    ↓ PostToolUse Hook
post-tool-use.js
    ↓ 记录文件路径
ai-sessions/{user}-ai-session-{host}.json (pendingFiles)
    ↓ git commit 触发
prepare-commit-msg.js（Git Hook）
    ↓ 计算行数 + 注入 Trailers
git log（包含 AI-Lines、AI-Model 等元数据）
    ↓ 分析
scripts/ai-tracker/report.py
    ↓
AI 代码占比报告
```

详细设计见：`docs/AI代码追踪系统设计手册.md`

---

## 工作流程

### LangGraph 节点开发流程

```
1. 需求分析
   └─> 使用 brainstorm 技能进行需求分析

2. 状态定义
   └─> 使用 langgraph-flow 技能定义 State TypedDict

3. 节点函数开发
   └─> 使用 langgraph-flow 技能开发节点函数
   └─> 使用 nl2sql-pipeline 技能实现业务逻辑

4. 数据库操作
   └─> 使用 database-ops 技能进行数据库操作
   └─> 使用 db-meta-query 技能查询元数据

5. 代码检查
   └─> 使用 /check 命令检查 LangGraph 规范

6. 文档更新
   └─> 使用 /update-status 更新项目状态
   └─> 使用 dev-docs 技能生成研发文档

7. 提交代码
   └─> git commit（自动注入 AI 元数据）
   └─> AI 代码行数自动统计
```

### 日常开发流程

```
开始工作
    ↓
/start          - 快速了解项目状态
    ↓
开发节点或功能
    ↓
/check          - 代码规范检查
    ↓
/update-status  - 更新项目状态
    ↓
/next           - 获取下一步建议
    ↓
结束工作（AI代码自动追踪）
```

---

## 技术栈映射

| 层级 | 技术 | 对应技能 |
|------|------|----------|
| **流程编排** | LangGraph | langgraph-flow, nl2sql-pipeline |
| **Web框架** | FastAPI | api-development |
| **数据库（业务）** | PostgreSQL + psycopg | database-ops, db-meta-query |
| **数据库（平台）** | MySQL + PyMySQL | database-ops |
| **数据验证** | Pydantic | json-serialization |
| **流式通信** | SSE | websocket-sse, http-client |
| **AI模型** | OpenAI | openai-interaction |
| **前端框架** | Vue 3 + TailwindCSS | ui-pc, ui-enhancement |
| **前端状态** | Pinia | store-pc |
| **前端路由** | Vue Router | router-pc |
| **流程图可视化** | Vue Flow | ui-pc |
| **图表** | ECharts | ui-pc |
| **数据库CLI** | usql | usql-client |

---

## 扩展机制

### 添加新技能

1. 创建目录 `.claude/skills/{skill-name}/`
2. 编写 `SKILL.md`，包含 YAML 头部和详细内容
3. 在 `skill-forced-eval.js` 中添加触发词映射
4. 使用 `add-skill` 技能验证格式

### 添加新命令

1. 在 `.claude/commands/` 创建 `{command-name}.md`
2. 定义命令功能和执行流程
3. 在文档中注册新命令

---

## 最佳实践

1. **技能优先**: 开发前先确认相关技能是否已加载
2. **文档同步**: 每次功能完成后及时更新项目文档
3. **规范检查**: 定期使用 `/check` 检查代码规范
4. **经验记录**: 使用 `/remember` 记录错误经验
5. **增量更新**: 日常使用 `/update-status`，定期使用 `/sync`
6. **AI追踪**: 每次 commit 自动记录 AI 代码占比

---

## 维护说明

- **更新日期**: 手动维护本文档顶部的最后更新日期
- **文档同步**: 所有文档应与项目代码保持同步
- **技能维护**: 定期检查技能内容是否与最新代码规范一致
- **AI追踪设计**: 详见 `docs/AI代码追踪系统设计手册.md`