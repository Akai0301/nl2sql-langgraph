---
name: add-skill
description: |
  当需要为框架增加新技能、为新的模块功能编写技能文档时自动使用此 Skill。

  触发场景：
  - 需要为新模块添加技能
  - 需要为新功能编写技能文档
  - 需要扩展框架的技能系统
  - 需要将实现步骤转化为可复用技能

  触发词：添加技能、创建技能、新技能、技能开发、写技能、技能文档、skill 创建
---

# 技能创建指南

## 概述

本指南用于在 CodeAI 框架中添加新的技能（Skill）。技能通过 UserPromptSubmit Hook 自动评估和激活，确保 AI 在编码前加载领域专业知识。

**技能系统工作原理**：

```
用户提交问题
  ↓ skill-forced-eval.js Hook 触发
注入技能评估指令
  ↓ AI 评估匹配的技能
逐个调用 Skill(技能名)
  ↓ 读取 .claude/skills/{技能名}/SKILL.md
AI 获得领域知识后开始实现
```

---

## YAML 头部规范

每个 SKILL.md 文件**必须**以 YAML 头部开始：

```yaml
---
name: {技能名称}
description: |
  {第一行：简短描述（一句话说明技能用途或定位）}

  触发场景：
  - {场景1}
  - {场景2}
  - {场景3}
  （至少3个场景）

  触发词：{关键词1}、{关键词2}、{关键词3}、{关键词4}、{关键词5}
  （至少5个触发词，用中文顿号分隔）
---
```

### name 字段规范

| 规则 | 说明 | 示例 |
|------|------|------|
| **格式** | kebab-case（全小写，横线连接） | `json-serialization` |
| **禁止** | 下划线、驼峰、空格 | ~~`json_serialization`~~, ~~`jsonSerialization`~~ |
| **长度** | 1-4 个单词 | `ui-pc`, `crud-development`, `redis-cache` |

### description 第一行风格

第一行没有强制格式，参考现有技能的两种常见风格：

**风格 A：直述型**（多数技能采用）
```yaml
description: |
  后端 CRUD 开发规范。基于 CodeAI 三层架构。
  后端安全开发规范。包含 OAuth2 & JWT 认证授权、数据脱敏。
  后端工具类使用指南。包含 ResponseUtil、PageUtil 等。
```

**风格 B：触发型**
```yaml
description: |
  当需要进行技术选型、对比方案时自动使用此 Skill。
  当需要为框架增加新技能时自动使用此 Skill。
```

### 实际技能 YAML 头部示例

```yaml
---
name: crud-development
description: |
  后端 CRUD 开发规范。基于 CodeAI 三层架构（Controller → Service → DAO）。

  触发场景：
  - 新建业务模块的 CRUD 功能
  - 创建 DO、VO、Service、DAO、Controller
  - 分页查询、新增、修改、删除、导出
  - 查询条件构建

  触发词：CRUD、增删改查、新建模块、DO、VO、Service、DAO、Controller、分页查询、ResponseUtil、PageResponseModel
---
```

```yaml
---
name: api-development
description: |
  后端 API 开发规范。基于 FastAPI 框架和 RESTful 设计风格。

  触发场景：
  - 新建 API 接口
  - 接口路径设计
  - 请求参数验证
  - 响应格式规范

  触发词：API、接口开发、FastAPI、RESTful、路径设计、参数验证、响应格式
---
```

```yaml
---
name: redis-cache
description: |
  当需要使用Redis缓存、分布式锁、限流等功能时自动使用此Skill。

  触发场景：
  - 使用Redis缓存数据
  - 实现分布式锁
  - 实现接口限流

  触发词：Redis、缓存、Cache、分布式锁、限流、RateLimiter
---
```

---

## 第 1 步：规划

### 1.1 定义技能属性

创建前先明确：

| 属性 | 说明 | 示例 |
|------|------|------|
| **名称** | kebab-case 格式 | `payment-gateway` |
| **类别** | 后端/通用/前端 | 后端 |
| **触发场景** | 至少 3 个具体场景 | 支付接入、退款处理、对账 |
| **触发词** | 至少 5 个关键词 | 支付、退款、订单、对账、Payment |
| **参考代码** | 项目中的真实代码位置 | `module_admin/` |

### 1.2 检查范围冲突

查看现有技能列表，确保不与已有技能重叠：

**当前已有技能**（`.claude/skills/` 下）：

| 分类 | 技能 |
|------|------|
| 后端开发 | crud-development, api-development, database-ops, backend-annotations, utils-toolkit, error-handler |
| 安全权限 | security-guard, data-permission |
| 中间件 | redis-cache, json-serialization, scheduled-jobs, file-oss-management |
| 通信集成 | websocket-sse |
| 质量保障 | test-development, bug-detective, performance-doctor, code-patterns |
| 架构决策 | architecture-design, tech-decision, brainstorm, project-navigator |
| 工具流程 | git-workflow, task-tracker, add-skill |
| 特殊功能 | banana-image, collaborating-with-codex, collaborating-with-gemini |
| 业务功能 | workflow-engine, store-pc |

如果新技能与现有技能有交集，在 SKILL.md 中用"注意"段落说明边界：
```markdown
注意：如果是认证授权（登录、Token、OAuth2），请使用 security-guard。
```

---

## 第 2 步：编写 SKILL.md


### 2.1 文件位置

```
.claude/skills/{技能名}/SKILL.md
```

> ⚠️ **创建文件规则（必须遵守，否则工具调用会静默失败）**
>
> - **优先使用 Write 工具**创建 SKILL.md，Write 会自动创建父目录，无需额外 mkdir
> - 若必须使用 Bash，**只允许相对路径**：`mkdir -p ".claude/skills/{技能名}"`
> - **禁止**使用绝对 Windows 路径（如 `D:\...`、`C:\...`）——Git Bash 不识别反斜杠路径，会导致整个工具调用静默失败
>
> **正确方式（Write 工具）**：
> ```
> 直接用 Write 工具，file_path = ".claude/skills/{技能名}/SKILL.md"
> Write 工具会自动创建 .claude/skills/{技能名}/ 目录
> ```
>
> **如需 Bash（仅相对路径）**：
> ```bash
> mkdir -p ".claude/skills/{技能名}"
> ```


### 2.2 推荐内容结构

```markdown
---
name: {技能名称}
description: |
  {描述、触发场景、触发词}
---

# {技能标题}

## 概述
{简明介绍，1-2 段}

## 核心工具类/API
{主要类和方法列表}

## 使用规范
{最佳实践和规则}

## 代码示例
{真实代码片段，来自项目实际代码}

## 常见错误
{正确做法 vs 错误做法对比}

## 注意
{与其他技能的边界说明}
```

### 2.3 内容质量要点

- **代码示例必须来自项目实际代码**，不要虚构类名、方法名
- **模块路径统一**，使用项目中的实际路径（如 `module_admin/controller/`、`module_admin/service/`）
- **三层架构**：Controller → Service → DAO（FastAPI 路由 → 服务层 → 数据访问层）
- **技术栈一致性**：使用 FastAPI 装饰器、SQLAlchemy ORM、Pydantic 模型
- **响应规范**：使用 `ResponseUtil` 统一响应格式
- 技能不需要固定行数要求，以内容实用为准（实际范围 200-650 行）

### 2.4 不同类型技能的侧重

| 类型 | 侧重 | 示例 |
|------|------|------|
| 后端开发类 | 代码模板、标准写法、禁止项 | crud-development |
| 工具类 | API 列表、使用示例、返回值 | utils-toolkit |
| 中间件类 | 配置方法、集成步骤、注意事项 | redis-cache |
| 流程类 | 步骤说明、决策树、检查清单 | brainstorm |

---

## 第 3 步：注册技能

技能需要在两个位置注册，才能被系统识别和激活。

### 3.1 在 Hook 中注册

**文件**：`.claude/hooks/skill-forced-eval.js`

在 `可用技能（纯后端项目）：` 列表中添加一行：

```javascript
- {技能名}: {触发词，用/分隔}
```

**示例**：
```javascript
- payment-gateway: 支付/退款/对账/Payment/支付宝/微信支付
```

**注意**：按逻辑分组插入，不是追加到末尾。例如，支付相关技能应插入到"中间件"或"通信集成"组附近。

### 3.2 在 AGENTS.md 中注册

**文件**：`AGENTS.md` 的"技能清单与触发条件"表格

在对应分类下添加一行：

```markdown
| `{技能名}` | {触发条件简述} |
```

**示例**：
```markdown
| `payment-gateway` | 支付接入、退款、对账、支付宝/微信支付 |
```

### 3.3 验证注册

```bash
# 检查 hook 文件
grep "payment-gateway" .claude/hooks/skill-forced-eval.js

# 检查 AGENTS.md
grep "payment-gateway" AGENTS.md
```

---

## 第 4 步：Codex 同步

项目同时支持 Claude Code（`.claude/`）和 Codex CLI（`.codex/`）两个系统。

### 同步步骤

```bash
# 1. 创建 Codex 目录
mkdir -p .codex/skills/{技能名}

# 2. 复制文件
cp .claude/skills/{技能名}/SKILL.md .codex/skills/{技能名}/SKILL.md

# 3. 验证一致性
diff .claude/skills/{技能名}/SKILL.md .codex/skills/{技能名}/SKILL.md
```

**注意**：
- `.codex/skills/` 中额外存放斜杠命令型技能（如 dev, crud, check 等），这些不需要在 `.claude/` 中创建
- 普通技能（非斜杠命令）需要保持两个目录一致

---

## 第 5 步：验证

### 完整检查清单

**文件**：
- [ ] `.claude/skills/{技能名}/SKILL.md` 已创建
- [ ] `.codex/skills/{技能名}/SKILL.md` 已同步

**YAML 头部**：
- [ ] `name` 使用 kebab-case 格式
- [ ] description 包含触发场景（至少 3 个）
- [ ] description 包含触发词（至少 5 个）
- [ ] 各部分之间有空行

**注册**：
- [ ] `.claude/hooks/skill-forced-eval.js` 已添加技能条目
- [ ] `AGENTS.md` 已添加技能条目

**内容**：
- [ ] 代码示例来自项目实际代码，无虚构内容
- [ ] 与现有技能无范围冲突（或已说明边界）
- [ ] 技术栈引用正确（FastAPI、Python、SQLAlchemy、Pydantic）
- [ ] 模块路径引用正确（如 `module_admin/`）
- [ ] 响应规范使用 `ResponseUtil`

---

## 常见陷阱
### 0. Windows 绝对路径导致工具调用静默失败

**症状**：mkdir 命令整个不执行，或目录创建在错误位置（如 `codeai.claude` 而非 `codeai\.claude`）

**原因**：使用了绝对 Windows 路径（`D:\001work\...`），Git Bash 无法识别反斜杠路径

**解决**：
- 优先使用 Write 工具（自动创建父目录）
- 如用 Bash，使用相对路径：`mkdir -p ".claude/skills/{技能名}"`

### 1. 遗漏注册

**症状**：技能文件存在但从不被激活

**原因**：只创建了 SKILL.md，没有在 Hook 和 AGENTS.md 中注册

**解决**：完成第 3 步的两处注册

### 2. 触发词过于宽泛

**症状**：技能在不相关场景被频繁误触发

**原因**：触发词太通用（如"开发"、"功能"）

**解决**：使用具体术语（如"CRUD开发"、"支付接入"）

### 3. 代码示例虚构

**症状**：AI 参考技能生成的代码使用了不存在的类或方法

**原因**：编写技能时没有验证引用的类名、方法名在项目中真实存在

**解决**：编写前用 Grep/Glob 搜索确认引用的类和方法确实存在

### 4. 忘记同步到 Codex

**症状**：Claude Code 中正常，Codex CLI 中找不到技能

**原因**：只在 `.claude/skills/` 创建，未复制到 `.codex/skills/`

**解决**：`cp .claude/skills/{技能名}/SKILL.md .codex/skills/{技能名}/SKILL.md`

### 5. 技术栈不一致

**症状**：技能中的代码示例与项目实际技术栈不符

**原因**：使用了 Python 2.x 语法、过时的 FastAPI 特性或错误的 ORM 用法

**解决**：参考项目中的实际代码，确保使用 Python 3.9+ 语法、最新的 FastAPI 装饰器和 SQLAlchemy ORM 用法

### 6. 响应格式不规范

**症状**：AI 生成的代码使用了自定义响应格式，而非项目统一的响应规范

**原因**：技能中没有强调使用 `ResponseUtil` 统一响应格式

**解决**：在技能中明确要求使用 `ResponseUtil.success()`、`ResponseUtil.error()` 等方法

### 7. 技能范围与现有技能重叠

**症状**：同一个问题触发多个技能，指导矛盾

**解决**：在 SKILL.md 末尾添加"注意"段落说明边界，例如：
```
注意：如果是认证授权（登录、Token、OAuth2），请使用 security-guard。
```