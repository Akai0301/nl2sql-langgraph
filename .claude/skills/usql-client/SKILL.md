---
name: usql-client
description: |
  基于 usql 的通用数据库命令行操作工具。直接用 usql.exe 连接项目数据库，以原生 SQL 终端方式执行查询、查看数据、批量操作。

  触发场景：
  - 用户明确提到 usql 或需要数据库命令行交互体验
  - 需要执行临时 SQL 查询（SELECT 数据、验证结果）
  - 需要执行数据修改（INSERT/UPDATE/DELETE）且不涉及代码生成
  - 需要进入数据库交互终端（usql 交互模式）
  - 需要将查询结果导出为 CSV 文件

  触发词：usql、usql连接、usql查询、usql执行、数据库命令行、SQL命令行、usql工具、usql客户端、连接数据库命令行
---

# usql 数据库命令行操作

## 概述

本技能使用项目内置的 `usql.exe`（位于 `.claude/skills/usql-client/scripts/usql.exe`）连接项目数据库，
通过 `usql_runner.py` 助手脚本**自动读取 `.env.dev` 配置**，无需手动输入连接信息。

脚本会自动检测并优先使用**项目虚拟环境**中的 Python，回退到系统 Python（`py` / `python3` / `python`）。

---

## 与 db-meta-query 的场景区分

这是两个功能相近但定位不同的技能，用以下决策表判断：

| 场景 | 用哪个技能 | 理由 |
|------|-----------|------|
| 查询表结构，**目的是生成 DO/VO 代码** | `db-meta-query` | 输出 Python 结构化数据，直接用于代码生成 |
| 获取 DDL（CREATE TABLE 语句），**用于分析建表规范** | `db-meta-query` | 输出完整建表 SQL，便于 AI 分析 |
| 查询索引、外键、元数据，**用于性能优化分析** | `db-meta-query` | 结构化 Python 输出，便于后续处理 |
| **临时查询业务数据**（SELECT 看看数据内容） | `usql-client` | 快速、直接，类原生 SQL 终端体验 |
| **修改数据**（INSERT / UPDATE / DELETE） | `usql-client` | usql 直接执行，无需 Python 依赖 |
| **导出数据到 CSV** | `usql-client` | usql 内置 CSV 导出，一行命令完成 |
| 用户说"用 usql 执行" | `usql-client` | 用户明确指定工具 |
| **进入 SQL 交互终端** | `usql-client` | 仅 usql 支持交互模式 |

**一句话总结**：
- `db-meta-query` → **结构化输出**，给 AI 读，用于代码生成/分析
- `usql-client` → **直接执行**，给人看，用于数据查询/修改/导出

---

## 工具位置

```
.claude/skills/usql-client/
├── SKILL.md                # 本技能文档
└── scripts/
    ├── usql.exe            # usql 可执行文件（用户自行放置）
    └── usql_runner.py      # 助手脚本（自动读取 .env.dev 并调用 usql）
```

> **注意**：`usql.exe` 需要用户手动放置到 `scripts/` 目录下。

---

## Python 环境优先级

`usql_runner.py` 脚本启动时会**自动检测并切换**到正确的 Python：

```
优先级 1：项目虚拟环境（venv/Scripts/python.exe 或 .venv/Scripts/python.exe）
优先级 2：项目同名其他 venv（env/Scripts/python.exe）
优先级 3：系统 Python（当前调用方，如 py / python3 / python）
```

检测逻辑：
- 从脚本路径向上查找含 `.env.dev` 或 `requirements.txt` 的目录作为项目根
- 在项目根下按顺序查找 `venv/`、`.venv/`、`env/` 目录
- 若找到 venv 且当前 Python 不在其中，自动用 `os.execv` 切换并重启脚本

**AI 调用规范**：使用 `py`（Windows Python Launcher）或路径最短的可用命令：

```bash
# 推荐：py（Windows 项目优先）
py .claude/skills/usql-client/scripts/usql_runner.py --sql "SHOW TABLES"

# 备用：python3
python3 .claude/skills/usql-client/scripts/usql_runner.py --sql "SHOW TABLES"
```

---

## 数据库配置（自动读取 .env.dev）

项目 `.env.dev` 中的数据库配置项：

| 配置项 | 说明 |
|--------|------|
| `DB_TYPE` | 数据库类型（`mysql` / `postgresql`） |
| `DB_HOST` | 数据库主机 |
| `DB_PORT` | 数据库端口 |
| `DB_USERNAME` | 用户名 |
| `DB_PASSWORD` | 密码 |
| `DB_DATABASE` | 数据库名 |

---

## usql_runner.py 用法

### 执行单条 SQL

```bash
# 查看所有表
py .claude/skills/usql-client/scripts/usql_runner.py --sql "SHOW TABLES"

# 查询数据
py .claude/skills/usql-client/scripts/usql_runner.py --sql "SELECT * FROM sys_user LIMIT 5"

# 查看表结构（这是查数据，不是代码生成用途）
py .claude/skills/usql-client/scripts/usql_runner.py --sql "DESCRIBE sys_user"
```

### 执行 SQL 文件

```bash
py .claude/skills/usql-client/scripts/usql_runner.py --file ./scripts/init.sql
```

### 进入交互模式

```bash
py .claude/skills/usql-client/scripts/usql_runner.py --interactive
```

### 指定其他环境配置

```bash
# 使用 .env.prod 配置
py .claude/skills/usql-client/scripts/usql_runner.py --env .env.prod --sql "SELECT COUNT(*) FROM sys_user"
```

### 导出数据

```bash
# CSV 格式输出
py .claude/skills/usql-client/scripts/usql_runner.py --sql "SELECT * FROM sys_user" --format csv

# 导出到文件
py .claude/skills/usql-client/scripts/usql_runner.py \
  --sql "SELECT * FROM sys_user" \
  --output ./output/users.csv \
  --format csv
```

### 仅查看 DSN（调试用）

```bash
py .claude/skills/usql-client/scripts/usql_runner.py --show-dsn
```

---

## 直接使用 usql.exe

如果需要直接调用 usql，DSN 格式如下：

```bash
# MySQL
.claude/skills/usql-client/scripts/usql.exe \
  "mysql://用户名:密码@主机:端口/数据库名" \
  -c "SELECT * FROM sys_user LIMIT 5"

# PostgreSQL
.claude/skills/usql-client/scripts/usql.exe \
  "postgres://用户名:密码@主机:端口/数据库名" \
  -c "SELECT * FROM sys_user LIMIT 5"
```

---

## 常用 usql 内置命令

在 usql 交互模式下可使用以下命令：

| 命令 | 说明 |
|------|------|
| `\l` | 列出所有数据库 |
| `\d` | 列出当前数据库所有表 |
| `\d 表名` | 查看指定表的结构（字段、类型） |
| `\di` | 列出所有索引 |
| `\q` | 退出 usql |
| `\i 文件路径` | 执行 SQL 文件 |
| `\o 输出文件` | 将查询结果输出到文件 |
| `\timing` | 开启/关闭执行时间显示 |
| `\x` | 切换扩展显示模式（列模式/行模式） |
| `\pset format csv` | 设置输出格式为 CSV |

---

## AI 调用模式（Bash 工具）

当 AI 需要执行数据库操作时，统一使用以下格式（`py` 优先）：

```bash
# 查询业务数据
py .claude/skills/usql-client/scripts/usql_runner.py \
  --sql "SELECT user_id, user_name, status FROM sys_user WHERE del_flag='0' LIMIT 10"

# 修改数据
py .claude/skills/usql-client/scripts/usql_runner.py \
  --sql "UPDATE sys_user SET status='1' WHERE user_id=108"

# 验证插入结果
py .claude/skills/usql-client/scripts/usql_runner.py \
  --sql "SELECT COUNT(*) as total FROM sys_menu WHERE menu_name LIKE '%xxx%'"

# 查询字典数据
py .claude/skills/usql-client/scripts/usql_runner.py \
  --sql "SELECT dict_type, dict_label, dict_value FROM sys_dict_data WHERE dict_type='sys_normal_disable'"
```

---

## 常见错误处理

| 错误 | 原因 | 解决方案 |
|------|------|---------|
| `usql.exe not found` | usql.exe 未放置 | 将 usql.exe 放到 `scripts/` 目录 |
| `.env.dev not found` | 配置文件路径不对 | 在项目根目录执行脚本，或用 `--env` 指定路径 |
| `connection refused` | 数据库连接失败 | 检查 `.env.dev` 中的 HOST/PORT/密码 |
| `Access denied` | 认证失败 | 检查用户名和密码 |
| `Unknown database` | 数据库名不存在 | 检查 `DB_DATABASE` 配置 |
| `Python was not found` | py / python 均不可用 | 安装 Python 或在 Microsoft Store 中获取 |

---

## 注意

- `usql.exe` 仅支持 Windows，Linux/macOS 用户需下载对应平台的 usql 二进制
- 如果目的是**为代码生成获取表结构/DDL/索引元数据**，请使用 `db-meta-query` 技能
- 如果目的是**建表和 DO 设计**，请使用 `database-ops` 技能
- 密码包含特殊字符时，DSN 中需要 URL 编码（如 `@` → `%40`，`#` → `%23`），`usql_runner.py` 已自动处理
