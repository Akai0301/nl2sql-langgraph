# /progress - 项目进度梳理

作为项目进度分析助手，帮您快速分析开发进度、识别完成度和待办事项。

## 🎯 执行流程

### 第一步：扫描项目模块（强制执行）

```bash
# 扫描后端文件
Glob pattern: "app/*.py"

# 扫描前端文件
Glob pattern: "frontend/src/**/*.vue"
Glob pattern: "frontend/src/**/*.ts"

# 扫描数据库文件
Glob pattern: "db/*.sql"
```

### 第二步：分析代码完整性

#### 后端核心文件检查

| 文件 | 必须 | 说明 |
|------|------|------|
| `app/state.py` | ✅ | State 定义 |
| `app/nodes.py` | ✅ | 节点函数 |
| `app/tools.py` | ✅ | PostgreSQL 工具 |
| `app/mysql_tools.py` | ✅ | MySQL 工具 |
| `app/graph_builder.py` | ✅ | 图构建 |
| `app/main.py` | ✅ | 应用入口 |
| `app/streaming.py` | ✅ | SSE 流式接口 |

#### 前端核心文件检查

| 目录/文件 | 必须 | 说明 |
|-----------|------|------|
| `views/QueryView.vue` | ✅ | 主页面 |
| `stores/queryStore.ts` | ✅ | 状态管理 |
| `api/query.ts` | ✅ | API 封装 |

### 第三步：扫描代码待办（TODO/FIXME）

```bash
# 扫描需要处理的代码注释
Grep pattern: "TODO:|FIXME:" path: app/ glob: "*.py" output_mode: content -B 1
Grep pattern: "TODO:|FIXME:" path: frontend/src/ glob: "*.ts" output_mode: content -B 1
```

---

## 📊 输出格式

```markdown
# 📊 项目进度报告

**生成时间**：YYYY-MM-DD HH:mm
**检查范围**：全量代码

---

## 🎯 项目概况

- **项目名称**：nl2sql-langgraph
- **技术栈**：FastAPI + psycopg + LangGraph + Vue 3
- **数据库**：PostgreSQL + MySQL
- **当前阶段**：[开发中/测试中/已上线]

---

## 📈 后端模块进度

| 文件 | 状态 | 说明 |
|------|------|------|
| `state.py` | ✅ | State 定义完整 |
| `nodes.py` | ✅ | 6 个节点实现 |
| `tools.py` | ✅ | 数据库工具完整 |
| `graph_builder.py` | ✅ | 梭子形流程完整 |
| `streaming.py` | ✅ | SSE 接口完整 |

---

## 📈 前端模块进度

| 目录 | 状态 | 说明 |
|------|------|------|
| `views/` | ✅ | 主页面完整 |
| `components/` | ✅ | 组件完整 |
| `stores/` | ✅ | 状态管理完整 |
| `api/` | ✅ | API 封装完整 |

---

## 📝 代码待办事项

### TODO 项 (X 个)

| 文件 | 行号 | 内容 |
|------|------|------|
| `[文件名].py` | [行号] | [描述] |

### FIXME 项 (X 个)

| 文件 | 行号 | 内容 |
|------|------|------|
| `[文件名].py` | [行号] | [描述] |

---

## 💡 改进建议

### 高优先级

1. **待完成功能**
   - [描述]
   - 建议：[建议]

### 中优先级

1. **代码优化**
   - [描述]

---

## ✅ 检查通过项

- [x] State 使用 TypedDict
- [x] 节点函数返回 dict
- [x] 使用 async/await
- [x] 前端使用 Vue 3 Composition API
- [x] 状态管理使用 Pinia
```

---

## 📊 完成度判定标准

| 进度 | 状态 | 说明 |
|------|------|------|
| 100% | ✅ 已完成 | 核心功能全部实现 |
| 70-99% | 🟢 基本完成 | 主要功能完成 |
| 40-69% | 🟡 进行中 | 开发中 |
| 1-39% | 🔴 早期阶段 | 刚开始 |

---

## 使用示例

```
用户：/progress

Claude：
🔍 正在扫描项目结构...
📊 分析代码完整性...

[输出完整的进度报告]
```