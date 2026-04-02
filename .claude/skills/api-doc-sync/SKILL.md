---
name: api-doc-sync
description: |
  接口文档同步生成规范。随着 /dev、/crud 开发或接口变更，自动以模块为粒度生成供前端对接的 Markdown 接口文档，保存到技能目录下的参考文档目录。

  触发场景：
  - /dev 或 /crud 命令完成后，自动同步生成对应模块的接口文档
  - 接口路径、参数、响应结构发生变化时更新文档
  - 用户明确要求生成或更新接口文档
  - 新增接口需要告知前端对接方式时
  - 前端开发人员询问接口规格时

  触发词：接口文档、API文档、生成文档、同步文档、前端对接、接口说明、接口规格、文档更新、接口变更、对接文档、接口清单

  注意：
  - 文档以模块为粒度，每个 module_xxx 对应一个 Markdown 文件
  - 文档保存路径：`.claude/skills/api-doc-sync/references/{模块名}-api.md`
  - 文档格式必须对前端友好，包含完整的字段说明和示例
---

# 接口文档同步生成规范（api-doc-sync）

## 概述

本规范定义了在 dev/crud 开发或接口变更后，如何自动生成并维护供前端对接的接口文档。

**核心原则**：
- 文档以**模块**为粒度（一个模块 = 一个 Markdown 文件）
- 文档保存到技能参考目录，集中管理，便于查阅
- 格式对前端友好，字段名使用**驼峰**（与前端对接格式一致）

---

## 文档保存路径规范

```
.claude/skills/api-doc-sync/references/
├── GLOBAL-INDEX.md                ← 【必须维护】全局索引，所有模块入口
├── module-admin-index.md          ← module_admin 内部索引
├── module-admin-user-api.md       # 用户管理接口
├── module-admin-dept-api.md       # 部门管理接口
├── module-admin-role-api.md       # 角色管理接口
├── module-xxx-yyy-api.md          # 自定义业务模块接口
└── _template-api.md               # 文档模板（参考使用）
```

**命名规则**：`{模块名}-{业务名}-api.md`，全小写横线分隔
- 模块 `module_admin` 下的用户管理 → `module-admin-user-api.md`
- 模块 `module_order` 下的订单管理 → `module-order-api.md`

> ⚠️ **每次新增模块文档后，必须同步更新 `GLOBAL-INDEX.md`**

---

## 触发时机与执行流程

### 什么时候生成文档

| 场景 | 动作 |
|------|------|
| `/dev` 新功能开发完成后 | 为新模块创建接口文档 |
| `/crud` 代码生成完成后 | 为生成的 CRUD 接口创建文档 |
| 接口路径/参数/响应变更后 | 更新对应模块的文档 |
| 用户说"同步/更新/生成接口文档" | 立即扫描并生成/更新文档 |

### 执行步骤

```
1. 识别当前操作涉及的模块（如 module_order）
2. 读取该模块 controller 层的所有接口定义
3. 读取对应的 VO/BO Pydantic 模型，提取字段说明
4. 按文档模板组织内容
5. 写入到 .claude/skills/api-doc-sync/references/{模块名}-api.md
6. 告知用户文档已生成/更新，并说明文件路径
```

---

## 接口文档格式规范

### 文档结构

```markdown
# {模块中文名} 接口文档

> **模块路径**：`/module-prefix`
> **最后更新**：YYYY-MM-DD
> **负责人**：后端

---

## 目录

- [接口1名称](#接口1锚点)
- [接口2名称](#接口2锚点)

---

## 接口列表

### 1. {接口名称}

**接口路径**：`GET /system/xxx/list`
**接口描述**：获取xxx分页列表
**权限标识**：`system:xxx:list`
**是否需要登录**：是

#### 请求参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|-------|------|------|------|------|
| pageNum | Integer | 否 | 页码，默认1 | 1 |
| pageSize | Integer | 否 | 每页数量，默认10 | 10 |
| xxxName | String | 否 | 名称（模糊匹配） | "测试" |

#### 响应参数

| 参数名 | 类型 | 说明 |
|-------|------|------|
| code | Integer | 状态码，200=成功 |
| msg | String | 提示信息 |
| rows | Array | 数据列表 |
| rows[].xxxId | Integer | 主键ID |
| rows[].xxxName | String | 名称 |
| total | Integer | 总记录数 |

#### 响应示例

```json
{
  "code": 200,
  "msg": "操作成功",
  "rows": [
    {
      "xxxId": 1,
      "xxxName": "示例名称",
      "status": "0",
      "createTime": "2024-01-01 12:00:00"
    }
  ],
  "total": 1
}
```
```

---

## 各接口类型的标准格式

### 分页查询接口

```markdown
### {序号}. 获取{业务名}列表

**接口路径**：`GET /{前缀}/list`
**接口描述**：分页查询{业务名}列表
**权限标识**：`{module}:{entity}:list`
**是否需要登录**：是

#### 请求参数（Query 参数）

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| pageNum | Integer | 否 | 页码，默认1 |
| pageSize | Integer | 否 | 每页数量，默认10 |
| {queryField1} | String | 否 | {字段说明} |
| beginTime | String | 否 | 开始时间（YYYY-MM-DD） |
| endTime | String | 否 | 结束时间（YYYY-MM-DD） |

#### 响应结构

```json
{
  "code": 200,
  "msg": "操作成功",
  "rows": [ { ...{实体字段} } ],
  "total": 100
}
```
```

---

### 获取详情接口

```markdown
### {序号}. 获取{业务名}详情

**接口路径**：`GET /{前缀}/{id}`
**接口描述**：根据ID获取{业务名}详情
**权限标识**：`{module}:{entity}:query`
**是否需要登录**：是

#### 路径参数

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| {entityId} | Integer | 是 | {业务名}ID |

#### 响应结构

```json
{
  "code": 200,
  "msg": "操作成功",
  "data": { ...{实体字段} }
}
```
```

---

### 新增接口

```markdown
### {序号}. 新增{业务名}

**接口路径**：`POST /{前缀}`
**接口描述**：新增{业务名}
**权限标识**：`{module}:{entity}:add`
**是否需要登录**：是
**请求格式**：`application/json`

#### 请求体（Body）

| 参数名 | 类型 | 必填 | 说明 | 约束 |
|-------|------|------|------|------|
| {field1} | String | 是 | {字段说明} | 最大长度100 |
| {field2} | String | 否 | {字段说明} | |
| status | String | 否 | 状态：0=正常，1=停用 | 默认"0" |
| remark | String | 否 | 备注 | 最大长度500 |

#### 响应结构

```json
{
  "code": 200,
  "msg": "新增成功"
}
```
```

---

### 修改接口

```markdown
### {序号}. 修改{业务名}

**接口路径**：`PUT /{前缀}`
**接口描述**：修改{业务名}
**权限标识**：`{module}:{entity}:edit`
**是否需要登录**：是
**请求格式**：`application/json`

#### 请求体（Body）

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| {entityId} | Integer | 是 | 主键ID（必填） |
| {field1} | String | 否 | {字段说明} |
| status | String | 否 | 状态：0=正常，1=停用 |

#### 响应结构

```json
{
  "code": 200,
  "msg": "修改成功"
}
```
```

---

### 删除接口

```markdown
### {序号}. 删除{业务名}

**接口路径**：`DELETE /{前缀}/{ids}`
**接口描述**：根据ID删除{业务名}（支持批量删除）
**权限标识**：`{module}:{entity}:remove`
**是否需要登录**：是

#### 路径参数

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| ids | String | 是 | ID列表，逗号分隔（如：1,2,3） |

#### 响应结构

```json
{
  "code": 200,
  "msg": "删除成功"
}
```
```

---

### 导出接口

```markdown
### {序号}. 导出{业务名}

**接口路径**：`POST /{前缀}/export`
**接口描述**：导出{业务名}列表为 Excel
**权限标识**：`{module}:{entity}:export`
**是否需要登录**：是
**请求格式**：`application/json`

#### 请求体（Body）

与分页查询参数相同（不传 pageNum/pageSize，导出全部）

#### 响应

直接返回 Excel 文件流（`Content-Type: application/vnd.ms-excel`）
```

---

## 字段类型对照表

| Python/SQLAlchemy 类型 | 文档中写法 | 说明 |
|----------------------|-----------|------|
| `String` / `VARCHAR` | `String` | 字符串 |
| `BigInteger` / `Integer` | `Integer` | 整数 |
| `CHAR(1)` | `String` | 单字符，通常是状态码 |
| `DateTime` | `String` | 日期时间，格式 `YYYY-MM-DD HH:mm:ss` |
| `Text` | `String` | 长文本 |
| `Optional[xxx]` | `{类型}（可选）` | 非必填字段 |
| `List[xxx]` | `Array` | 数组类型 |

---

## 通用响应状态码

| code | 含义 | 场景 |
|------|------|------|
| `200` | 成功 | 所有成功操作 |
| `400` | 参数错误 | 请求参数不合法（ValidateFields 拦截）|
| `401` | 未登录 | Token 过期或未携带 |
| `403` | 无权限 | 接口权限不足 |
| `500` | 服务器内部错误 | 业务异常（ServiceException）|

---

## 请求头规范

前端调用所有接口（除登录、验证码）均需携带：

```
Authorization: Bearer {token}
Content-Type: application/json  （POST/PUT 请求）
```

---

## 文档生成执行规则

### 规则 1：必须在 dev/crud 完成后执行

每次执行 `/dev` 或 `/crud` 命令后，**必须**检查是否需要生成或更新接口文档：
1. 识别本次涉及的模块（从 controller 文件路径判断）
2. 检查是否已有该模块的接口文档（`references/` 下是否存在）
3. 若无 → 创建新文档；若有 → 追加或更新变更的接口

### 规则 2：从 Controller 读取接口定义

生成文档时必须读取实际的 controller 文件，不得凭空猜测：

```python
# 从 controller 文件提取以下信息：
# 1. APIRouter prefix → 接口前缀
# 2. @xxxController.get('/list') → HTTP 方法和路径
# 3. CheckUserInterfaceAuth('system:xxx:list') → 权限标识
# 4. 函数参数类型（VO/BO Pydantic 模型）→ 请求参数
# 5. ResponseUtil 返回类型 → 响应结构
```

### 规则 3：从 VO/BO 读取字段定义

```python
# 从 Pydantic 模型提取：
# 1. 字段名（Python snake_case → 前端 camelCase）
# 2. 字段类型（Optional[str] → String）
# 3. Field(description='xxx') → 字段说明
# 4. 是否 Optional → 是否必填
```

### 规则 4：字段名转换规则

文档中的字段名**统一使用驼峰**（与前端 JS/TS 对接一致）：

| Python（snake_case）| 文档/前端（camelCase）|
|--------------------|--------------------|
| `user_id` | `userId` |
| `dept_name` | `deptName` |
| `create_time` | `createTime` |
| `del_flag` | `delFlag` |

### 规则 5：告知用户文档位置

生成文档后必须输出：
```
接口文档已生成/更新：
📄 .claude/skills/api-doc-sync/references/{模块名}-api.md
```

### 规则 6：维护全局索引（GLOBAL-INDEX.md）

每次新增模块文档后，必须更新全局索引：

```markdown
# 接口文档全局索引

| 模块 | 索引/文档 | 路径前缀 |
|------|---------|---------|
| module_admin（系统管理） | [module-admin-index.md](./module-admin-index.md) | `/system/`、`/monitor/` |
| module_xxx（业务模块） | [module-xxx-api.md](./module-xxx-api.md) | `/xxx/` |
```

> 前台开发查文档的起点就是这个 `GLOBAL-INDEX.md`

---

## 完整文档示例

参考文件：`.claude/skills/api-doc-sync/references/_template-api.md`

实际生成的模块文档示例见 `references/` 目录下各 `*-api.md` 文件。

---

## 注意

- 文档字段名统一使用驼峰（`camelCase`），不使用下划线
- 状态字段（`status`）的枚举值必须注明含义（如 `0=正常，1=停用`）
- 时间字段格式统一说明为 `YYYY-MM-DD HH:mm:ss`
- 带数据权限的接口（`GetDataScope`）无需在文档中特别说明，对前端透明
- 文件上传接口请参考 `file-oss-management` 技能，使用 `multipart/form-data`
