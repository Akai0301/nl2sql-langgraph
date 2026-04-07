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
- [Schema 学习接口](#schema-学习接口)
  - [触发 Schema 学习](#触发-schema-学习)
  - [查询学习进度](#查询学习进度)
  - [列出学习任务](#列出学习任务)
  - [获取 Schema 缓存](#获取-schema-缓存)
  - [获取表列表](#获取表列表)
  - [获取表 Schema](#获取表-schema)

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

## Schema 学习接口

### 触发 Schema 学习

**接口路径**：`POST /settings/datasource/{ds_id}/learn`
**接口描述**：触发数据库 Schema 学习，自动提取表结构、分类字段、生成语义描述
**是否需要登录**：否

#### 路径参数

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| ds_id | Integer | 是 | 数据源ID |

#### 响应参数

| 参数名 | 类型 | 说明 |
|-------|------|------|
| success | Boolean | 是否成功 |
| taskId | Integer | 任务ID，用于查询进度 |
| status | String | 任务状态：pending/running/completed/failed |
| message | String | 提示信息 |

#### 响应示例

```json
{
  "success": true,
  "task_id": 1,
  "status": "running",
  "message": "开始学习"
}
```

#### 错误响应

```json
{
  "detail": "数据源不存在"
}
```

```json
{
  "detail": "数据源连接失败: Connection refused"
}
```

---

### 查询学习进度

**接口路径**：`GET /settings/learning/{task_id}`
**接口描述**：查询 Schema 学习任务的执行进度
**是否需要登录**：否

#### 路径参数

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| task_id | Integer | 是 | 任务ID |

#### 响应参数

| 参数名 | 类型 | 说明 |
|-------|------|------|
| taskId | Integer | 任务ID |
| datasourceId | Integer | 数据源ID |
| status | String | 状态：pending/running/completed/failed |
| progress | Integer | 进度 0-100 |
| currentStep | String | 当前执行步骤 |
| message | String | 提示信息 |
| error | String | 错误信息（失败时） |

#### 响应示例

**学习中：**
```json
{
  "task_id": 1,
  "datasource_id": 1,
  "status": "running",
  "progress": 50,
  "current_step": "生成描述",
  "message": "正在生成语义描述",
  "error": null
}
```

**完成：**
```json
{
  "task_id": 1,
  "datasource_id": 1,
  "status": "completed",
  "progress": 100,
  "current_step": "完成",
  "message": "学习完成，共处理 5 张表",
  "error": null
}
```

---

### 列出学习任务

**接口路径**：`GET /settings/learning/tasks`
**接口描述**：列出学习任务记录
**是否需要登录**：否

#### 查询参数

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| datasource_id | Integer | 否 | 按数据源筛选 |

#### 响应示例

```json
{
  "items": [
    {
      "task_id": 2,
      "datasource_id": 1,
      "status": "completed",
      "progress": 100,
      "current_step": "完成",
      "message": "学习完成，共处理 5 张表",
      "error": null
    },
    {
      "task_id": 1,
      "datasource_id": 1,
      "status": "failed",
      "progress": 30,
      "current_step": "分类字段",
      "message": "学习失败",
      "error": "LLM API 调用超时"
    }
  ]
}
```

---

### 获取 Schema 缓存

**接口路径**：`GET /settings/datasource/{ds_id}/schema`
**接口描述**：获取数据源的 Schema 缓存（M-Schema JSON 格式）
**是否需要登录**：否

#### 响应参数

| 参数名 | 类型 | 说明 |
|-------|------|------|
| id | Integer | 缓存ID |
| datasourceId | Integer | 数据源ID |
| schemaJson | Object | M-Schema JSON 格式 |
| mschemaText | String | M-Schema 文本格式（用于 Prompt） |
| tableCount | Integer | 表数量 |
| fieldCount | Integer | 字段总数 |
| learnedAt | String | 学习时间（ISO 格式） |

#### 响应示例

```json
{
  "id": 1,
  "datasource_id": 1,
  "schema_json": {
    "db_id": "生产环境数据库",
    "tables": {
      "fact_orders": {
        "name": "fact_orders",
        "comment": "订单事实表",
        "table_type": "fact",
        "primary_keys": ["order_id"],
        "fields": {
          "order_id": {
            "name": "order_id",
            "type": "bigint",
            "primary_key": true,
            "category": "Code",
            "dim_or_meas": "Dimension"
          },
          "order_amount": {
            "name": "order_amount",
            "type": "numeric",
            "primary_key": false,
            "category": "Measure",
            "dim_or_meas": "Measure",
            "comment": "订单金额"
          }
        }
      }
    },
    "foreign_keys": []
  },
  "mschema_text": "数据库: 生产环境数据库\n\n表 fact_orders:\n  - order_id: bigint [主键]\n  - order_amount: numeric # 订单金额\n",
  "table_count": 5,
  "field_count": 32,
  "learned_at": "2026-04-03T10:30:00"
}
```

---

### 获取表列表

**接口路径**：`GET /settings/datasource/{ds_id}/schema/tables`
**接口描述**：获取数据源的表列表及基本信息
**是否需要登录**：否

#### 响应参数

| 参数名 | 类型 | 说明 |
|-------|------|------|
| items | Array | 表列表 |
| items[].name | String | 表名 |
| items[].comment | String | 表注释 |
| items[].tableType | String | 表类型：fact/dimension/other |
| items[].primaryKeys | Array | 主键列表 |
| items[].fieldCount | Integer | 字段数量 |
| total | Integer | 总数 |

#### 响应示例

```json
{
  "items": [
    {
      "name": "fact_orders",
      "comment": "订单事实表",
      "table_type": "fact",
      "primary_keys": ["order_id"],
      "field_count": 12
    },
    {
      "name": "dim_customer",
      "comment": "客户维度表",
      "table_type": "dimension",
      "primary_keys": ["customer_id"],
      "field_count": 8
    }
  ],
  "total": 5
}
```

---

### 获取表 Schema

**接口路径**：`GET /settings/datasource/{ds_id}/schema/tables/{table_name}`
**接口描述**：获取单表的详细 Schema 信息
**是否需要登录**：否

#### 路径参数

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| ds_id | Integer | 是 | 数据源ID |
| table_name | String | 是 | 表名 |

#### 响应参数

| 参数名 | 类型 | 说明 |
|-------|------|------|
| name | String | 表名 |
| comment | String | 表注释 |
| tableType | String | 表类型：fact/dimension/other |
| primaryKeys | Array | 主键列表 |
| fields | Array | 字段列表 |
| fields[].name | String | 字段名 |
| fields[].type | String | 数据类型 |
| fields[].primaryKey | Boolean | 是否主键 |
| fields[].nullable | Boolean | 是否可空 |
| fields[].comment | String | 字段注释 |
| fields[].category | String | 分类：DateTime/Enum/Code/Text/Measure |
| fields[].dimOrMeas | String | 维度/度量：Dimension/Measure |
| fields[].dateMinGran | String | 时间颗粒度（仅 DateTime 类型） |
| fields[].examples | Array | 示例值列表 |

#### 响应示例

```json
{
  "name": "fact_orders",
  "comment": "订单事实表",
  "table_type": "fact",
  "primary_keys": ["order_id"],
  "fields": [
    {
      "name": "order_id",
      "type": "bigint",
      "primary_key": true,
      "nullable": false,
      "comment": "订单ID",
      "category": "Code",
      "dim_or_meas": "Dimension",
      "date_min_gran": null,
      "examples": ["100001", "100002", "100003"]
    },
    {
      "name": "order_date",
      "type": "date",
      "primary_key": false,
      "nullable": false,
      "comment": "下单日期",
      "category": "DateTime",
      "dim_or_meas": "Dimension",
      "date_min_gran": "DAY",
      "examples": ["2024-01-01", "2024-01-02", "2024-01-03"]
    },
    {
      "name": "order_amount",
      "type": "numeric",
      "primary_key": false,
      "nullable": false,
      "comment": "订单金额",
      "category": "Measure",
      "dim_or_meas": "Measure",
      "date_min_gran": null,
      "examples": ["1299.00", "599.50", "2999.00"]
    }
  ]
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