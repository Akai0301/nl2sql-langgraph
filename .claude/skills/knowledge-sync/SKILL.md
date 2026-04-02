---
name: knowledge-sync
description: |
  知识反馈与配置同步机制。确保项目代码变更能及时反馈到 .claude 配置。

  触发场景：
  - 完成新功能开发后同步文档
  - 发现并修复 Bug 后更新经验库
  - 项目结构变更后更新导航
  - 新增工具函数后更新技能
  - 开发完成后需要检查配置同步

  触发词：同步配置、更新文档、记录经验、知识反馈、配置同步、开发完成、同步更新
---

# 知识反馈与配置同步机制

## 一、机制总览

知识反馈系统采用**三层机制**确保配置同步：

```
┌─────────────────────────────────────────────────────────────────┐
│                    知识反馈系统架构                               │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: 自动检测层                                             │
│  ├─ skill-forced-eval.js → 纠正关键词检测 → lesson-learned       │
│  ├─ post-tool-use.js → 文件变更检测 → 配置同步提醒               │
│  └─ prepare-commit-msg.js → Git 提交 → AI 元数据注入            │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: 显式触发层                                             │
│  ├─ /remember 命令 → 手动记录经验                                │
│  ├─ /sync 命令 → 全量项目状态同步                                │
│  └─ knowledge-sync 技能 → 配置同步检查                           │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: 存储层                                                 │
│  ├─ .claude/memory/lessons.md → 经验教训                         │
│  ├─ .claude/memory/user.md → 用户偏好                           │
│  ├─ .claude/memory/project.md → 项目上下文                       │
│  ├─ CLAUDE.md → 项目规范                                         │
│  └─ skills/*/SKILL.md → 领域知识                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、自动触发机制（已实现）

### 2.1 纠正检测 → lesson-learned

位置：`.claude/hooks/skill-forced-eval.js`

```javascript
// 纠正关键词检测
const correctionKeywords = [
  '不对', '错了', '不是这样', '应该是', '应该用', '应该这样',
  '你搞错了', '你弄错了', '你写错了', '你理解错了',
  '记住', '记下来', '下次', '以后', '别再',
  '纠正', '更正', '修正', '这不对', '不应该',
];
```

**效果**：用户说纠正词 → 自动追加 `lesson-learned` 技能 → 记录到 lessons.md

### 2.2 经验库注入

每次会话开始时，Hook 自动注入 lessons.md 的规则速查表：

```javascript
// 提取 RULES_START 和 RULES_END 之间的内容
const rulesMatch = lessonsContent.match(/<!-- RULES_START -->([\s\S]*?)<!-- RULES_END -->/);
```

**效果**：历史纠正沉淀的规则自动加载到每次会话上下文

### 2.3 文件变更提醒

位置：`.claude/hooks/post-tool-use.js`

**当前检测**：
- `app/*.py` → 后端 API 变更 → 提醒同步 api-doc-sync

---

## 三、配置同步检查清单

### 3.1 新功能开发后检查

完成以下开发场景后，**必须执行配置同步检查**：

| 开发场景 | 需同步的配置 | 同步操作 |
|---------|-------------|---------|
| 新增 LangGraph 节点 | CLAUDE.md, langgraph-flow | 更新项目结构、节点列表 |
| 新增 State 字段 | CLAUDE.md, state.py 注释 | 更新状态定义说明 |
| 新增 API 接口 | api-doc-sync, CLAUDE.md | 生成接口文档、更新 API 列表 |
| 新增数据库表 | database-ops, db/*.sql | 更新表结构文档 |
| 新增工具函数 | utils-toolkit, project-navigator | 更新工具列表 |
| 新增前端组件 | ui-pc, CLAUDE.md | 更新组件列表 |

**执行流程**：

```
1. 完成功能开发
2. 测试验证通过
3. 执行配置同步检查（本技能）
4. 更新相关配置文件
5. 使用 /remember 记录关键决策
6. git commit（包含配置变更）
```

### 3.2 Bug 修复后检查

| Bug 类型 | 需同步的配置 | 同步操作 |
|---------|-------------|---------|
| LangGraph 流程错误 | lesson-learned, langgraph-flow | 记录经验、更新注意事项 |
| 数据库查询错误 | lesson-learned, database-ops | 记录经验、更新 SQL 规范 |
| SQL 生成错误 | lesson-learned, nl2sql-pipeline | 记录经验、更新模板 |
| 前端渲染错误 | lesson-learned, ui-pc | 记录经验、更新组件规范 |

### 3.3 项目结构变更后检查

| 变更类型 | 需同步的配置 | 同步操作 |
|---------|-------------|---------|
| 新增目录 | CLAUDE.md, project-navigator | 更新项目结构 |
| 重命名文件 | skills/*/SKILL.md | 更新文件路径引用 |
| 删除文件 | CLAUDE.md | 移除相关引用 |

---

## 四、Memory 目录结构

```
.claude/memory/
├── lessons.md          # 经验教训（纠正记录）
├── user.md             # 用户偏好（开发风格、习惯）
└── project.md          # 项目上下文（业务背景、术语）
```

### 4.1 lessons.md 格式

```markdown
<!-- RULES_START -->
## 规则速查表

| 规则 | 说明 |
|------|------|
| [R001] 节点函数返回 dict | LangGraph 节点必须返回字典 |
| [R002] State 使用 TypedDict | 状态定义必须继承 TypedDict |
<!-- RULES_END -->

## 详细记录

### [R001] 2026-04-01 | ARCH | 🔴 强制

**❌ 错误行为**：节点函数返回了非字典类型

**✅ 正确做法**：节点返回值必须是 dict，会与 State 合并

**根本原因**：误解 LangGraph 节点函数的返回机制

**沉淀规则**：节点函数返回 dict | LangGraph 节点必须返回字典

**影响范围**：langgraph-flow, 所有节点开发任务
```

### 4.2 user.md 格式（用户偏好）

```markdown
# 用户偏好记录

## 开发风格
- 偏好简洁代码，避免过度工程
- 优先使用 async/await

## 命名习惯
- 文件名使用下划线分隔
- 类名使用 PascalCase

## 禁止事项
- 不要添加过多注释
- 不要使用过时的语法
```

### 4.3 project.md 格式（项目上下文）

```markdown
# 项目上下文

## 业务背景
本项目是 NL2SQL 智能问数系统，将自然语言转换为 SQL 查询。

## 核心术语
- 梭子形架构：扇出/扇入的多 Agent 流水线
- 知识检索：从 enterprise_kb 表检索业务术语
- 指标检索：从 metrics_catalog 表检索指标定义

## 技术栈
- LangGraph：流程编排
- PostgreSQL：业务数据存储
- MySQL：平台数据存储
```

---

## 五、执行配置同步

### 5.1 检查代码变更

```bash
# 查看最近修改的文件
git diff --name-only HEAD~5

# 检查是否有配置需要同步
# 如果修改了以下目录，需要同步配置：
# - app/ → 同步 CLAUDE.md, langgraph-flow, api-doc-sync
# - frontend/ → 同步 ui-pc, store-pc, router-pc
# - db/ → 同步 database-ops
```

### 5.2 更新配置文件

根据检查结果，更新以下配置：

| 检测到变更 | 更新操作 |
|-----------|---------|
| `app/*.py` | 检查是否新增节点/接口，更新 CLAUDE.md |
| `app/state.py` | 更新状态定义说明 |
| `app/nodes.py` | 更新节点列表 |
| `app/tools.py` | 更新工具函数列表 |
| `frontend/src/**/*.vue` | 更新组件列表 |
| `db/*.sql` | 更新表结构文档 |

### 5.3 输出同步报告

```markdown
# 配置同步报告

**同步时间**：YYYY-MM-DD HH:mm
**检测范围**：最近 X 次提交

## 需同步的配置

| 配置文件 | 变更原因 | 状态 |
|---------|---------|------|
| CLAUDE.md | 新增节点函数 | ✅ 已更新 |
| langgraph-flow/SKILL.md | 新增节点示例 | ✅ 已更新 |
| api-doc-sync/references/ | 新增接口 | ✅ 已生成 |

## 无需同步

- project-navigator：无新增目录
- user.md：无用户偏好变更
```

---

## 六、与其他机制协作

### 6.1 与 /remember 命令协作

```
/remember → lesson-learned → lessons.md
knowledge-sync → 检查 lessons.md 是否需要同步到 CLAUDE.md
```

### 6.2 与 /sync 命令协作

```
/sync → 全量项目状态同步
knowledge-sync → 专注于配置文件同步检查
```

### 6.3 触发时机建议

| 场景 | 推荐机制 |
|------|---------|
| 用户纠正错误 | 自动 → lesson-learned |
| 开发完成 | 手动 → knowledge-sync |
| 定期整理 | 手动 → /sync |
| 记录决策 | 手动 → /remember |

---

## 七、最佳实践

### 7.1 开发完成后的标准流程

```
1. ✅ 测试功能是否正常
2. ✅ 执行 knowledge-sync 检查配置
3. ✅ 更新相关配置文件
4. ✅ 使用 /remember 记录关键决策
5. ✅ git commit（包含代码 + 配置变更）
```

### 7.2 周度维护

```
1. 清理过时的 memory 记录
2. 运行 /sync 全量同步
3. 检查配置与代码的一致性
4. 更新技能触发词（如有新模式）
```

### 7.3 经验记录原则

```
- 只记录真实纠正，不猜测
- 规则摘要 ≤30 字
- 立即写入，不等到会话结束
- 类别准确，影响同步决策
```