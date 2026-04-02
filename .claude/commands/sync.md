# /sync - 项目代码状态同步

一键同步项目代码状态、生成项目文档、确保代码与文档数据一致。适合定期整理或发现数据不一致时使用。

---

## 🎯 适用场景

| 场景 | 说明 |
|------|------|
| **定期整理** | 每周末整理项目代码状态和文档 |
| **数据不一致** | 手动修改过代码或文档后需要重新同步 |
| **项目交接** | 新成员加入或项目交接时全量检查 |

---

## 🚀 执行流程

### 第一步：扫描项目代码状态

#### 1.1 扫描后端模块

```bash
# 扫描后端文件
Glob pattern: "app/*.py"

# 统计代码行数
wc -l app/*.py
```

#### 1.2 扫描前端模块

```bash
# 扫描前端文件
Glob pattern: "frontend/src/**/*.vue"
Glob pattern: "frontend/src/**/*.ts"
```

#### 1.3 扫描数据库模块

```bash
# 扫描数据库脚本
Glob pattern: "db/*.sql"
```

#### 1.4 扫描代码规范问题

```bash
# 检查后端代码
Grep pattern: "async def" path: app/ glob: "*.py" output_mode: count
Grep pattern: "await " path: app/ glob: "*.py" output_mode: count
```

#### 1.5 扫描 TODO/FIXME 标记

```bash
# 扫描待办标记
Grep pattern: "TODO:|FIXME:|XXX:" path: app/ glob: "*.py" output_mode: content -B 1
Grep pattern: "TODO:|FIXME:|XXX:" path: frontend/src/ glob: "*.ts" output_mode: content -B 1
```

---

### 第二步：分析 Git 提交历史

```bash
# 获取最近提交
git log -10 --oneline

# 统计最近 7 天提交
git log --since="7 days ago" --oneline
```

---

### 第三步：生成项目同步报告

```markdown
# 🔄 项目代码状态同步报告

**同步时间**：YYYY-MM-DD HH:mm
**上次同步**：YYYY-MM-DD（距今 X 天）

---

## 📈 最新进展

### Git 提交摘要
- **最新提交**：[commit message] ([hash])
- **最近 7 天**：X 次提交

### 代码统计
| 模块 | 文件数 | 说明 |
|------|--------|------|
| 后端 (app/) | X | Python 模块 |
| 前端 (frontend/) | X | Vue 组件 |
| 数据库 (db/) | X | SQL 脚本 |

---

## ⚠️ 紧急问题（必须立即处理）

### 高优先级 FIXME
| 文件 | 行号 | 问题 |
|------|------|------|
| [文件名].py | [行号] | [问题描述] |

---

## 📝 待办事项更新

### 新增待办（本次扫描发现）
- [ ] [FIXME 描述]（高优先级）
- [ ] [TODO 描述]（中优先级）

### 当前进行中
| 任务 | 优先级 | 进度 |
|------|--------|------|
| [任务描述] | [优先级] | XX% |

---

## ✅ 检查通过项

- [x] State 使用 TypedDict
- [x] 节点函数返回 dict
- [x] 使用 async/await
- [x] 前端使用 TypeScript
```

---

## 🎯 与其他命令的协作

### 工作流建议
1. **日常开发** → `/update-status` 增量更新
2. **每周末** → `/sync` 全量同步，生成报告
3. **遇到问题** → `/check` 检查代码规范
4. **规划工作** → `/progress` 查看进度，`/next` 获取建议

### 命令关系图
```
/start (快速了解)
   ↓
/check (检查规范)
   ↓
/sync (同步并生成报告) ← 您在这里
   ↓
/progress (查看进度)
   ↓
/next (获取建议)
```

---

## 📌 同步说明

- 本报告基于当前代码扫描和 Git 提交综合生成
- 与 `/progress` 的区别：/progress 只读查看，/sync 生成综合报告
- 与 `/check` 的关系：/check 检查代码规范，/sync 整合检查结果
- 建议每周运行一次 `/sync` 命令进行定期整理