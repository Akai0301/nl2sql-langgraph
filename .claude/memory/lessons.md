# 项目经验库 - nl2sql-langgraph

> **用途**：团队共享的错误记录与经验沉淀，每条来源于真实纠正。
> **加载方式**：由 `skill-forced-eval.js` Hook 在每次会话注入摘要，确保 Agent 下次不犯同样错误。
> **更新方式**：激活 `lesson-learned` Skill，或执行 `/remember` 命令。

---

## 规则速查表（最新沉淀，Hook 会自动注入此区域）

> 格式：`[ID] 类别 | 规则` — Agent 必须在每次实现前检查此表

<!-- RULES_START -->
<!-- 此区域由 lesson-learned skill 自动维护，请勿手动编辑格式 -->
| [R001] | CODE | 后端启动使用正确虚拟环境路径 |
| [R002] | SYNC | 数据库表变更时同步更新 project.md 表结构文档 |
| [R003] | CODE | 本地域名使用 nl2sql.local:8000 |
| [R004] | CODE | 思考模式模型不支持 tool_choice，使用 JSON 输出 |
<!-- RULES_END -->

---

## 详细错误日志

> 按时间倒序排列，最新在前。

<!-- LOG_START -->
<!-- 此区域由 lesson-learned skill 自动追加 -->

### [R001] 2026-04-06 | CODE | 🟠 重要

**❌ 错误行为**：启动后端时使用了错误的虚拟环境路径，或直接调用 `uvicorn` 命令

**✅ 正确做法**：
- 虚拟环境路径：`D:\01_AlCoding_Test\nl2sql-langgraph\venv`（项目根目录）
- 启动命令：`cd d:/01_AlCoding_Test/nl2sql-langgraph && venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000`
- 必须从项目根目录启动，确保 `.env` 文件路径正确解析

**根本原因**：
1. 虚拟环境现在在项目目录内，路径更简洁
2. 使用 `--app-dir` 参数会导致 `.env` 路径解析错误
3. 直接调用 `uvicorn` 会因 PATH 环境变量找不到命令

**沉淀规则**：后端启动使用正确虚拟环境路径 | 虚拟环境在项目根目录 `venv/`，必须从项目目录启动

**影响范围**：所有后端启动任务、bug-detective 排查时

---

### [R002] 2026-04-06 | SYNC | 🟠 重要

**❌ 错误行为**：修改数据库表结构后未同步更新 project.md 中的表结构文档

**✅ 正确做法**：
- 表结构变更后，使用 `db-meta-query` 技能查询最新结构
- 更新 project.md 的"PostgreSQL 表结构详解"章节
- 新增表时同时更新 schema.sql 和 CLAUDE.md

**根本原因**：
1. 表结构文档分散在多处（project.md、CLAUDE.md、schema.sql）
2. 缺乏变更后的同步检查机制

**沉淀规则**：数据库表变更时同步更新 project.md 表结构文档 | 表结构变更必须同步文档

**影响范围**：database-ops, db-meta-query, 所有涉及表修改的任务

---

### [R003] 2026-04-08 | CODE | 🟠 重要

**❌ 错误行为**：API 请求使用 `localhost:8000` 而非已配置的本地域名

**✅ 正确做法**：
- 本地域名：`http://nl2sql.local:8000`（已在 hosts 文件配置 127.0.0.1 nl2sql.local）
- 所有 API 请求、前端代理、测试都应使用此域名
- 前端 vite.config.ts 代理目标应为 `http://nl2sql.local:8000`

**根本原因**：
1. hosts 已配置本地域名便于统一管理和记忆
2. 使用统一域名避免跨域和路径问题

**沉淀规则**：本地域名使用 nl2sql.local:8000 | API 请求统一使用本地域名

**影响范围**：http-client, websocket-sse, 前端开发, API 测试

---

### [R004] 2026-04-11 | CODE | 🔴 强制

**❌ 错误行为**：使用 `with_structured_output()` 调用思考模式模型（如 DashScope Anthropic 端点），导致 tool_choice 参数报错

**✅ 正确做法**：
- 思考模式模型：使用普通 `llm.invoke()` + JSON 格式 prompt + 手动解析
- 非思考模式模型：使用 `with_structured_output()` 结构化输出
- 配置检测：`config.thinking_mode` 或 `provider=anthropic` 或 DashScope 端点自动判断

**根本原因**：
1. DashScope Anthropic 兼容端点默认启用 thinking mode
2. thinking mode 下不支持 `tool_choice="required"` 参数
3. `with_structured_output()` 内部使用 tool_choice 强制调用

**沉淀规则**：思考模式模型不支持 tool_choice，使用 JSON 输出 | 检测 thinking_mode 后选择正确调用方式

**影响范围**：openai-interaction, sql_generation_node, 所有 LLM 结构化输出场景

---
<!-- LOG_END -->