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
<!-- RULES_END -->

---

## 详细错误日志

> 按时间倒序排列，最新在前。

<!-- LOG_START -->
<!-- 此区域由 lesson-learned skill 自动追加 -->

### [R001] 2026-04-06 | CODE | 🟠 重要

**❌ 错误行为**：启动后端时使用了错误的虚拟环境路径，或直接调用 `uvicorn` 命令

**✅ 正确做法**：
- 虚拟环境路径：`D:\01_AlCoding_Test\langgraph_agent_venv`
- 启动命令：`cd d:/01_AlCoding_Test/nl2sql-langgraph && D:/01_AlCoding_Test/langgraph_agent_venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000`
- 必须从项目根目录启动，确保 `.env` 文件路径正确解析

**根本原因**：
1. 虚拟环境不在项目目录内，与项目齐平放置
2. 使用 `--app-dir` 参数会导致 `.env` 路径解析错误
3. 直接调用 `uvicorn` 会因 PATH 环境变量找不到命令

**沉淀规则**：后端启动使用正确虚拟环境路径 | 虚拟环境在 `D:\01_AlCoding_Test\langgraph_agent_venv`，必须从项目目录启动

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
<!-- LOG_END -->