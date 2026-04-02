# /start - 项目快速了解

新成员快速了解项目的必看命令。自动检测项目类型、扫描模块结构、生成项目概览。

---

## 🎯 适用场景

| 场景 | 说明 |
|------|------|
| **初次接触** | 新成员第一次接触项目 |
| **项目交接** | 接手他人的项目 |
| **重新梳理** | 距上次熟悉项目已久，需要快速回顾 |
| **窗口切换** | 在新的 Claude 会话中快速了解项目 |

---

## 🚀 执行流程

### 第一步：识别项目类型和框架（强制执行）

#### 1.1 读取项目配置

```bash
# 扫描项目结构
Glob pattern: "app/*.py"
Glob pattern: "frontend/src/**/*.vue"

# 查看最近 3 条 Git 提交
git log -3 --oneline --format="%h %s (%ar)"
```

#### 1.2 分析项目架构

**识别核心模块**：
- ✅ `app/` - 后端 Python 模块（LangGraph 节点、工具、状态）
- ✅ `frontend/` - Vue 3 前端
- ✅ `db/` - 数据库脚本

---

### 第二步：判断项目开发阶段

#### 2.1 检查核心文件

```bash
# 检查后端核心文件
Glob pattern: "app/state.py"
Glob pattern: "app/nodes.py"
Glob pattern: "app/tools.py"
Glob pattern: "app/graph_builder.py"

# 检查前端核心文件
Glob pattern: "frontend/src/views/QueryView.vue"
Glob pattern: "frontend/src/stores/queryStore.ts"
```

#### 2.2 检查文档状态

```bash
# 检查文档是否存在
Glob pattern: "docs/*.md"
```

---

### 第三步：生成项目概览报告

```markdown
# 👋 欢迎使用 nl2sql-langgraph

**项目类型**：LangGraph 梭子形 NL2SQL 流水线
**技术栈**：FastAPI + psycopg + LangGraph + Vue 3
**数据库**：PostgreSQL + MySQL 双库架构

---

## 📦 项目结构

| 目录 | 说明 |
|------|------|
| `app/` | 后端 Python 模块 |
| `frontend/` | Vue 3 前端 |
| `db/` | 数据库脚本 |

---

## 🎯 核心组件

### 后端 (app/)

| 文件 | 说明 |
|------|------|
| `state.py` | NL2SQLState TypedDict 状态定义 |
| `nodes.py` | LangGraph 节点函数 |
| `tools.py` | PostgreSQL 数据库工具 |
| `mysql_tools.py` | MySQL 数据库工具 |
| `graph_builder.py` | StateGraph 构建 |
| `streaming.py` | SSE 流式接口 |
| `main.py` | FastAPI 应用入口 |

### 前端 (frontend/)

| 目录 | 说明 |
|------|------|
| `views/` | 页面组件 |
| `components/` | UI 组件 |
| `stores/` | Pinia 状态管理 |
| `api/` | API 调用封装 |

### 数据库 (db/)

| 文件 | 说明 |
|------|------|
| `schema.sql` | PostgreSQL 表结构 |
| `seed.sql` | 种子数据 |
| `mysql_schema.sql` | MySQL 表结构 |

---

## 📐 架构：「梭子形」多 Agent NL2SQL 流水线

```
问题 → 分析器 → [并行检索] → 合并 → SQL生成 → SQL执行
                  ↓
      ┌───────────┼───────────┐
      ↓           ↓           ↓
 知识检索     指标检索     元数据检索
      └───────────┼───────────┘
                  ↓
            上下文合并
```

---

## 🚀 快速开始

### 启动后端

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
copy .env.example .env

# 初始化数据库
psql $env:POSTGRES_DSN -f db/schema.sql
psql $env:POSTGRES_DSN -f db/seed.sql
mysql < db/mysql_schema.sql

# 启动服务
uvicorn app.main:app --reload --port 8000
```

### 启动前端

```bash
cd frontend
npm install
npm run dev
```

---

## 📚 相关命令

| 命令 | 说明 | 何时使用 |
|------|------|---------|
| `/progress` | 查看项目进度 | 了解完成情况 |
| `/check` | 代码规范检查 | 代码审查前 |
| `/next` | 获取建议 | 不知道做什么 |
```

---

## 🎓 新成员入门清单

- [ ] 阅读项目根目录的 `CLAUDE.md` 了解开发规范
- [ ] 运行 `/start` 了解项目现状
- [ ] 运行 `/progress` 查看详细进度
- [ ] 查看 `app/state.py` 了解状态定义
- [ ] 查看 `app/nodes.py` 了解节点实现

---

## 💡 常见问题

### Q: 项目是什么架构？
A: LangGraph 梭子形多 Agent NL2SQL 流水线，基于 StateGraph 编排。

### Q: 如何开发新节点？
A: 参考 `app/nodes.py` 中现有节点的实现模式。

### Q: 如何了解代码规范？
A:
1. 查看 `CLAUDE.md` 文件
2. 运行 `/check` 命令检查规范
3. 参考 `app/` 目录现有代码

---

## 🔗 核心命令速览

```bash
# 了解项目
/start          # 项目概览
/progress       # 详细进度

# 代码管理
/check          # 代码规范检查

# 项目管理
/next           # 获取建议
/sync           # 全量同步
```