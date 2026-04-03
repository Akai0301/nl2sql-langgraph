# 系统设置接口文档

> **模块路径**：`/settings`
> **最后更新**：2026-04-03
> **负责人**：后端

---

## 目录

- [数据源接口](#数据源接口)
  - [获取当前激活数据源](#获取当前激活数据源)
  - [列出所有数据源](#列出所有数据源)
  - [切换数据源](#切换数据源)

---

## 数据源接口

### 获取当前激活数据源

**接口路径**：`GET /settings/datasource/active`
**接口描述**：获取当前用于问数的数据源信息（优先级：MySQL配置表 > .env）
**是否需要登录**：否

#### 响应参数

| 参数名 | 类型 | 说明 |
|-------|------|------|
| datasource | Object | 当前数据源信息，未配置时为 null |
| datasource.id | Integer | 数据源ID，来自 .env 时为 null |
| datasource.dsName | String | 数据源名称 |
| datasource.dsType | String | 数据库类型：postgresql/mysql/sqlite |
| datasource.host | String | 主机地址 |
| datasource.port | Integer | 端口 |
| datasource.database | String | 数据库名 |
| datasource.isFromEnv | Boolean | 是否来自 .env 配置 |
| message | String | 提示信息（如未配置时的提示）|

#### 响应示例

**已配置数据源：**
```json
{
  "datasource": {
    "id": 1,
    "ds_name": "生产环境数据库",
    "ds_type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "nl2sql",
    "is_from_env": false
  },
  "message": null
}
```

**使用 .env 配置：**
```json
{
  "datasource": {
    "id": null,
    "ds_name": ".env 默认数据源",
    "ds_type": "postgresql",
    "host": null,
    "port": null,
    "database": null,
    "is_from_env": true
  },
  "message": null
}
```

**未配置数据源：**
```json
{
  "datasource": null,
  "message": "未配置数据源，请先在系统设置中添加数据源或配置 .env 文件中的 POSTGRES_DSN"
}
```

---

### 列出所有数据源

**接口路径**：`GET /settings/datasource`
**接口描述**：获取所有数据源配置列表
**是否需要登录**：否

#### 响应参数

| 参数名 | 类型 | 说明 |
|-------|------|------|
| items | Array | 数据源列表 |
| items[].id | Integer | 数据源ID |
| items[].dsName | String | 数据源名称 |
| items[].dsType | String | 数据库类型 |
| items[].host | String | 主机地址 |
| items[].port | Integer | 端口 |
| items[].database | String | 数据库名 |
| items[].username | String | 用户名 |
| items[].isQueryTarget | Boolean | 是否为当前问数目标 |

#### 响应示例

```json
{
  "items": [
    {
      "id": 1,
      "ds_name": "生产环境数据库",
      "ds_type": "postgresql",
      "host": "localhost",
      "port": 5432,
      "database": "nl2sql",
      "username": "postgres",
      "is_query_target": true
    },
    {
      "id": 2,
      "ds_name": "测试环境数据库",
      "ds_type": "mysql",
      "host": "localhost",
      "port": 3306,
      "database": "test_db",
      "username": "root",
      "is_query_target": false
    }
  ]
}
```

---

### 切换数据源

**接口路径**：`POST /settings/datasource/{ds_id}/activate-query`
**接口描述**：设置指定数据源为问数查询目标
**是否需要登录**：否

#### 路径参数

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| ds_id | Integer | 是 | 数据源ID |

#### 响应参数

| 参数名 | 类型 | 说明 |
|-------|------|------|
| success | Boolean | 是否成功 |
| message | String | 提示信息 |

#### 响应示例

```json
{
  "success": true,
  "message": "已设置为问数目标"
}
```

#### 错误响应

```json
{
  "detail": "数据源不存在"
}
```

---

## 通用响应状态码

| code | 含义 | 场景 |
|------|------|------|
| `200` | 成功 | 请求成功 |
| `400` | 参数错误 | 请求参数不合法 |
| `404` | 未找到 | 数据源不存在 |
| `500` | 服务器错误 | 内部异常 |

---

## 前端对接说明

### 数据源切换流程

1. 页面加载时调用 `GET /settings/datasource/active` 获取当前数据源
2. 调用 `GET /settings/datasource` 获取数据源列表
3. 用户选择数据源后调用 `POST /settings/datasource/{id}/activate-query` 切换
4. 切换成功后重新查询数据

### 字段名映射

| 后端字段（snake_case） | 前端字段（camelCase） |
|----------------------|---------------------|
| ds_name | dsName |
| ds_type | dsType |
| is_query_target | isQueryTarget |
| is_from_env | isFromEnv |