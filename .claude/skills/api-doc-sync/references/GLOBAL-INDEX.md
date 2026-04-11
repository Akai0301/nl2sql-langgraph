# 接口文档全局索引

> **最后更新**：2026-04-11
> **维护说明**：每次新增模块文档后，必须同步更新本索引

---

## 模块索引

| 模块 | 文档 | 路径前缀 | 说明 |
|------|------|---------|------|
| 系统设置 | [settings-api.md](./settings-api.md) | `/settings/` | AI配置、数据源配置、Schema学习、知识库管理 |

---

## 快速查找

### AI 配置相关

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 列出 AI 配置 | GET | `/settings/ai` | 获取所有 AI 模型配置列表 |
| 创建 AI 配置 | POST | `/settings/ai` | 创建新的 AI 模型配置 |
| 更新 AI 配置 | PATCH | `/settings/ai/{id}` | 更新 AI 模型配置 |
| 删除 AI 配置 | DELETE | `/settings/ai/{id}` | 删除 AI 模型配置 |
| 激活 AI 配置 | POST | `/settings/ai/{id}/activate` | 激活指定 AI 配置 |
| 测试 AI 连接 | POST | `/settings/ai/{id}/test` | 测试 AI 模型连接是否正常 |

### 数据源相关

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 获取当前激活数据源 | GET | `/settings/datasource/active` | 获取当前用于问数的数据源 |
| 列出所有数据源 | GET | `/settings/datasource` | 获取数据源列表 |
| 切换数据源 | POST | `/settings/datasource/{id}/activate-query` | 设置问数目标数据源 |

### Schema 学习相关

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 触发 Schema 学习 | POST | `/settings/datasource/{id}/learn` | 自动提取表结构、分类字段、生成描述 |
| 查询学习进度 | GET | `/settings/learning/{taskId}` | 查询学习任务进度 |
| 列出学习任务 | GET | `/settings/learning/tasks` | 列出学习任务记录 |
| 获取 Schema 缓存 | GET | `/settings/datasource/{id}/schema` | 获取 M-Schema JSON |
| 获取表列表 | GET | `/settings/datasource/{id}/schema/tables` | 获取数据源的表列表 |
| 获取表 Schema | GET | `/settings/datasource/{id}/schema/tables/{tableName}` | 获取单表详细 Schema |