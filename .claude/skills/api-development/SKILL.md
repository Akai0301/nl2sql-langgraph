---
name: api-development
description: |
  后端 API 接口设计规范。基于 CodeAI 三层架构的 RESTful API 开发指南。

  触发场景：
  - 设计 RESTful API 接口
  - 编写 Controller 层代码
  - 配置接口权限、日志、数据验证
  - 接口返回值类型选择（ResponseUtil.success/failure/error）
  - 数据验证（@ValidateFields）

  触发词：API、接口、RESTful、Controller、APIRouter、CheckUserInterfaceAuth、@Log、@ValidateFields、ResponseUtil、接口规范
---

# API 接口设计规范（CodeAI 版本）

> **⚠️ 重要声明**: 本项目是 **CodeAI 纯后端项目**，采用三层架构！
> 本文档规范基于真实 API 实现。

## 核心架构特征

| 对比项 | 本项目 (CodeAI) |
|--------|----------------------|
| **语言** | Python 3.9+ |
| **Web框架** | FastAPI |
| **路由定义** | `APIRouter(prefix='/module/resource')` |
| **API 路径** | 标准 RESTful：`/list`、`/{id}`、`/export`、`/importData` |
| **权限控制** | `dependencies=[Depends(CheckUserInterfaceAuth('module:resource:operation'))]` |
| **操作日志** | `@Log(title='xxx', business_type=BusinessType.XXX)` 装饰器 |
| **数据验证** | `@ValidateFields(validate_model='model_name')` 装饰器 |
| **返回类型** | `ResponseUtil.success()` / `ResponseUtil.failure()` / `ResponseUtil.streaming()` |
| **分页返回** | `PageResponseModel` (rows, total, pageNum, pageSize) |
| **数据库** | SQLAlchemy (异步) + MySQL/PostgreSQL |
| **认证** | OAuth2 & JWT |

---

## 1. 标准 RESTful API 路径规范

### 路径格式

| 操作 | HTTP 方法 | 路径 | 说明 |
|------|---------|------|------|
| **列表查询** | GET | `/list` | 分页查询列表 |
| **获取详情** | GET | `/{id}` | 根据 ID 查询单个数据 |
| **新增** | POST | `/` (空) | 创建新数据 |
| **修改** | PUT | `/` (空) | 更新数据 |
| **删除** | DELETE | `/{ids}` | 批量删除 |
| **导出** | POST | `/export` | 导出数据到 Excel |
| **导入** | POST | `/importData` | 从 Excel 导入数据 |
| **自定义查询** | GET | `/page` | 自定义分页逻辑 |

### 路径示例

```python
from fastapi import APIRouter

userController = APIRouter(prefix='/system/user', dependencies=[Depends(LoginService.get_current_user)])

@userController.get('/list')          # GET /system/user/list
@userController.get('/{user_id}')    # GET /system/user/{user_id}
@userController.post()                # POST /system/user
@userController.put()                 # PUT /system/user
@userController.delete('/{user_ids}') # DELETE /system/user/{user_ids}
@userController.post('/export')       # POST /system/user/export
@userController.post('/importData')   # POST /system/user/importData
```

---

## 2. API 方法完整模板

### 2.1 列表查询（分页）

```python
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from utils.response_util import ResponseUtil
from utils.page_util import PageResponseModel
from module_admin.aspect.data_scope import GetDataScope
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.user_vo import UserPageQueryModel
from module_admin.service.user_service import UserService
from config.get_db import get_db

@userController.get(
    '/list',
    response_model=PageResponseModel,
    dependencies=[Depends(CheckUserInterfaceAuth('system:user:list'))]
)
async def get_system_user_list(
    request: Request,
    user_page_query: UserPageQueryModel = Depends(UserPageQueryModel.as_query),
    query_db: AsyncSession = Depends(get_db),
    data_scope_sql: str = Depends(GetDataScope('SysUser')),
):
    user_page_query_result = await UserService.get_user_list_services(
        query_db, user_page_query, data_scope_sql, is_page=True
    )
    logger.info('获取成功')

    return ResponseUtil.success(model_content=user_page_query_result)
```

**关键点**:
- `response_model=PageResponseModel` - 指定分页响应模型
- `Depends(UserPageQueryModel.as_query)` - 查询参数模型
- `Depends(CheckUserInterfaceAuth('system:user:list'))` - 权限检查
- `Depends(GetDataScope('SysUser'))` - 数据权限
- `ResponseUtil.success(model_content=...)` - 返回分页结果
- `is_page=True` - 启用分页

---

### 2.2 获取详情

```python
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from utils.response_util import ResponseUtil
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.user_vo import UserDetailModel, CurrentUserModel
from module_admin.service.user_service import UserService
from module_admin.service.login_service import LoginService
from config.get_db import get_db

@userController.get(
    '/{user_id}',
    response_model=UserDetailModel,
    dependencies=[Depends(CheckUserInterfaceAuth('system:user:query'))]
)
async def query_detail_system_user(
    request: Request,
    user_id: int,
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
    data_scope_sql: str = Depends(GetDataScope('SysUser')),
):
    if not current_user.user.admin:
        await UserService.check_user_data_scope_services(query_db, user_id, data_scope_sql)
    detail_user_result = await UserService.user_detail_services(query_db, user_id)
    logger.info(f'获取user_id为{user_id}的信息成功')

    return ResponseUtil.success(model_content=detail_user_result)
```

**关键点**:
- `/{user_id}` - 路径参数
- `response_model=UserDetailModel` - 指定响应模型
- `Depends(LoginService.get_current_user)` - 获取当前登录用户
- `ResponseUtil.success(model_content=...)` - 返回详情数据
- 权限字符串格式：`module:resource:operation`

---

### 2.3 新增数据

```python
from datetime import datetime
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic_validation_decorator import ValidateFields
from config.enums import BusinessType
from module_admin.annotation.log_annotation import Log
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.user_vo import AddUserModel, CurrentUserModel
from module_admin.service.user_service import UserService
from module_admin.service.login_service import LoginService
from utils.response_util import ResponseUtil
from config.get_db import get_db

@userController.post('', dependencies=[Depends(CheckUserInterfaceAuth('system:user:add'))])
@ValidateFields(validate_model='add_user')
@Log(title='用户管理', business_type=BusinessType.INSERT)
async def add_system_user(
    request: Request,
    add_user: AddUserModel,
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
    dept_data_scope_sql: str = Depends(GetDataScope('SysDept')),
    role_data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    if not current_user.user.admin:
        await DeptService.check_dept_data_scope_services(query_db, add_user.dept_id, dept_data_scope_sql)
        await RoleService.check_role_data_scope_services(
            query_db, ','.join([str(item) for item in add_user.role_ids]), role_data_scope_sql
        )
    add_user.password = PwdUtil.get_password_hash(add_user.password)
    add_user.create_by = current_user.user.user_name
    add_user.create_time = datetime.now()
    add_user.update_by = current_user.user.user_name
    add_user.update_time = datetime.now()
    add_user_result = await UserService.add_user_services(query_db, add_user)
    logger.info(add_user_result.message)

    return ResponseUtil.success(msg=add_user_result.message)
```

**关键点**:
- `@ValidateFields(validate_model='add_user')` - 数据验证装饰器
- `@Log(title='用户管理', business_type=BusinessType.INSERT)` - 操作日志
- `add_user: AddUserModel` - Pydantic 模型接收请求体
- 设置 `create_by`、`create_time`、`update_by`、`update_time` 字段
- `ResponseUtil.success(msg=...)` - 返回成功消息

---

### 2.4 修改数据

```python
from datetime import datetime
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic_validation_decorator import ValidateFields
from config.enums import BusinessType
from module_admin.annotation.log_annotation import Log
from module_admin.aspect.data_scope import GetDataScope
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.user_vo import EditUserModel, CurrentUserModel
from module_admin.service.user_service import UserService
from module_admin.service.login_service import LoginService
from utils.response_util import ResponseUtil
from config.get_db import get_db

@userController.put('', dependencies=[Depends(CheckUserInterfaceAuth('system:user:edit'))])
@ValidateFields(validate_model='edit_user')
@Log(title='用户管理', business_type=BusinessType.UPDATE)
async def edit_system_user(
    request: Request,
    edit_user: EditUserModel,
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
    user_data_scope_sql: str = Depends(GetDataScope('SysUser')),
    dept_data_scope_sql: str = Depends(GetDataScope('SysDept')),
    role_data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    await UserService.check_user_allowed_services(edit_user)
    if not current_user.user.admin:
        await UserService.check_user_data_scope_services(query_db, edit_user.user_id, user_data_scope_sql)
        await DeptService.check_dept_data_scope_services(query_db, edit_user.dept_id, dept_data_scope_sql)
        await RoleService.check_role_data_scope_services(
            query_db, ','.join([str(item) for item in edit_user.role_ids]), role_data_scope_sql
        )
    edit_user.update_by = current_user.user.user_name
    edit_user.update_time = datetime.now()
    edit_user_result = await UserService.edit_user_services(query_db, edit_user)
    logger.info(edit_user_result.message)

    return ResponseUtil.success(msg=edit_user_result.message)
```

**关键点**:
- `@ValidateFields(validate_model='edit_user')` - 数据验证装饰器
- `@Log(title='用户管理', business_type=BusinessType.UPDATE)` - 操作日志
- `check_user_allowed_services()` - 检查用户是否允许操作
- 数据权限检查
- 设置 `update_by`、`update_time` 字段

---

### 2.5 删除数据

```python
from datetime import datetime
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from config.enums import BusinessType
from module_admin.annotation.log_annotation import Log
from module_admin.aspect.data_scope import GetDataScope
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.user_vo import DeleteUserModel, CurrentUserModel, UserModel
from module_admin.service.user_service import UserService
from module_admin.service.login_service import LoginService
from utils.response_util import ResponseUtil
from config.get_db import get_db

@userController.delete('/{user_ids}', dependencies=[Depends(CheckUserInterfaceAuth('system:user:remove'))])
@Log(title='用户管理', business_type=BusinessType.DELETE)
async def delete_system_user(
    request: Request,
    user_ids: str,
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
    data_scope_sql: str = Depends(GetDataScope('SysUser')),
):
    user_id_list = user_ids.split(',') if user_ids else []
    if user_id_list:
        if current_user.user.user_id in list(map(int, user_id_list)):
            logger.warning('当前登录用户不能删除')

            return ResponseUtil.failure(msg='当前登录用户不能删除')
        for user_id in user_id_list:
            await UserService.check_user_allowed_services(UserModel(userId=int(user_id)))
            if not current_user.user.admin:
                await UserService.check_user_data_scope_services(query_db, int(user_id), data_scope_sql)
    delete_user = DeleteUserModel(userIds=user_ids, updateBy=current_user.user.user_name, updateTime=datetime.now())
    delete_user_result = await UserService.delete_user_services(query_db, delete_user)
    logger.info(delete_user_result.message)

    return ResponseUtil.success(msg=delete_user_result.message)
```

**关键点**:
- `/{user_ids}` - 路径参数（逗号分隔的 ID）
- `user_ids.split(',')` - 将字符串转换为列表
- 检查是否删除当前登录用户
- 检查每个用户是否允许删除
- 数据权限检查
- `ResponseUtil.failure(msg=...)` - 返回失败消息

---

### 2.6 导出数据

```python
from fastapi import Depends, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from config.enums import BusinessType
from module_admin.annotation.log_annotation import Log
from module_admin.aspect.data_scope import GetDataScope
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.user_vo import UserPageQueryModel
from module_admin.service.user_service import UserService
from utils.common_util import bytes2file_response
from utils.response_util import ResponseUtil
from config.get_db import get_db

@userController.post('/export', dependencies=[Depends(CheckUserInterfaceAuth('system:user:export'))])
@Log(title='用户管理', business_type=BusinessType.EXPORT)
async def export_system_user_list(
    request: Request,
    user_page_query: UserPageQueryModel = Form(),
    query_db: AsyncSession = Depends(get_db),
    data_scope_sql: str = Depends(GetDataScope('SysUser')),
):
    user_query_result = await UserService.get_user_list_services(
        query_db, user_page_query, data_scope_sql, is_page=False
    )
    user_export_result = await UserService.export_user_list_services(user_query_result)
    logger.info('导出成功')

    return ResponseUtil.streaming(data=bytes2file_response(user_export_result))
```

**关键点**:
- `@Log(title='用户管理', business_type=BusinessType.EXPORT)` - 操作日志
- `user_page_query: UserPageQueryModel = Form()` - 表单参数
- `is_page=False` - 不分页，获取全量数据
- `bytes2file_response()` - 将字节转换为文件响应
- `ResponseUtil.streaming(data=...)` - 流式响应

---

### 2.7 导入数据

```python
from fastapi import Depends, File, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from config.enums import BusinessType
from module_admin.annotation.log_annotation import Log
from module_admin.aspect.data_scope import GetDataScope
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_admin.service.user_service import UserService
from module_admin.service.login_service import LoginService
from utils.response_util import ResponseUtil
from config.get_db import get_db

@userController.post('/importData', dependencies=[Depends(CheckUserInterfaceAuth('system:user:import'))])
@Log(title='用户管理', business_type=BusinessType.IMPORT)
async def batch_import_system_user(
    request: Request,
    file: UploadFile = File(...),
    update_support: bool = Query(alias='updateSupport'),
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
    user_data_scope_sql: str = Depends(GetDataScope('SysUser')),
    dept_data_scope_sql: str = Depends(GetDataScope('SysDept')),
):
    batch_import_result = await UserService.batch_import_user_services(
        request, query_db, file, update_support, current_user, user_data_scope_sql, dept_data_scope_sql
    )
    logger.info(batch_import_result.message)

    return ResponseUtil.success(msg=batch_import_result.message)
```

**关键点**:
- `@Log(title='用户管理', business_type=BusinessType.IMPORT)` - 操作日志
- `file: UploadFile = File(...)` - 文件上传
- `update_support: bool = Query(alias='updateSupport')` - 查询参数
- `ResponseUtil.success(msg=...)` - 返回导入结果

---

### 2.8 导入模板下载

```python
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.service.user_service import UserService
from utils.common_util import bytes2file_response
from utils.response_util import ResponseUtil
from config.get_db import get_db

@userController.post('/importTemplate', dependencies=[Depends(CheckUserInterfaceAuth('system:user:import'))])
async def export_system_user_template(request: Request, query_db: AsyncSession = Depends(get_db)):
    user_import_template_result = await UserService.get_user_import_template_services()
    logger.info('获取成功')

    return ResponseUtil.streaming(data=bytes2file_response(user_import_template_result))
```

**关键点**:
- `bytes2file_response()` - 将字节转换为文件响应
- `ResponseUtil.streaming(data=...)` - 流式响应

---

## 3. 注解和装饰器使用规范

### 3.1 权限控制 - CheckUserInterfaceAuth

```python
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth

# 格式：dependencies=[Depends(CheckUserInterfaceAuth('module:resource:operation'))]
dependencies=[Depends(CheckUserInterfaceAuth('system:user:list'))]     # list - 列表查询
dependencies=[Depends(CheckUserInterfaceAuth('system:user:query'))]    # query - 详情查询
dependencies=[Depends(CheckUserInterfaceAuth('system:user:add'))]      # add - 新增
dependencies=[Depends(CheckUserInterfaceAuth('system:user:edit'))]     # edit - 修改
dependencies=[Depends(CheckUserInterfaceAuth('system:user:remove'))]   # remove - 删除
dependencies=[Depends(CheckUserInterfaceAuth('system:user:export'))]   # export - 导出
dependencies=[Depends(CheckUserInterfaceAuth('system:user:import'))]   # import - 导入
```

**权限字符串规则**:
- 格式：`module:resource:operation`
- `module` - 业务模块名（如 system、demo、business）
- `resource` - 资源名称（如 user、role、menu）
- `operation` - 操作类型（list、query、add、edit、remove、export、import）

**多权限支持**:
```python
# 支持多个权限，任一通过即可
dependencies=[Depends(CheckUserInterfaceAuth(['system:user:add', 'system:user:edit']))]

# 严格模式：所有权限都必须通过
dependencies=[Depends(CheckUserInterfaceAuth(['system:user:add', 'system:user:edit'], is_strict=True))]
```

---

### 3.2 操作日志 - @Log

```python
from config.enums import BusinessType
from module_admin.annotation.log_annotation import Log

# 格式：@Log(title='功能名称', business_type=BusinessType.XXX)
@Log(title='用户管理', business_type=BusinessType.INSERT)   # 新增
@Log(title='用户管理', business_type=BusinessType.UPDATE)   # 修改
@Log(title='用户管理', business_type=BusinessType.DELETE)   # 删除
@Log(title='用户管理', business_type=BusinessType.EXPORT)   # 导出
@Log(title='用户管理', business_type=BusinessType.IMPORT)   # 导入
@Log(title='用户管理', business_type=BusinessType.GRANT)    # 授权
@Log(title='用户管理', business_type=BusinessType.OTHER)   # 其他
```

**BusinessType 枚举值**:
```python
class BusinessType(Enum):
    OTHER = 0      # 其它
    INSERT = 1     # 新增
    UPDATE = 2     # 修改
    DELETE = 3     # 删除
    GRANT = 4      # 授权
    EXPORT = 5     # 导出
    IMPORT = 6     # 导入
    FORCE = 7      # 强退
    GENCODE = 8    # 生成代码
    CLEAN = 9      # 清空数据
```

**日志类型**:
```python
# 默认为操作日志
@Log(title='用户管理', business_type=BusinessType.INSERT)

# 登录日志
@Log(title='用户登录', business_type=BusinessType.OTHER, log_type='login')
```

---

### 3.3 数据验证 - @ValidateFields

```python
from pydantic_validation_decorator import ValidateFields

# 格式：@ValidateFields(validate_model='model_name')
@ValidateFields(validate_model='add_user')
@ValidateFields(validate_model='edit_user')
@ValidateFields(validate_model='add_role')
@ValidateFields(validate_model='edit_role')
```

**使用场景**:
- 新增数据时验证
- 修改数据时验证
- 需要自定义验证逻辑的地方

**验证模型命名规范**:
- 新增模型：`add_{resource}`（如 `add_user`、`add_role`）
- 修改模型：`edit_{resource}`（如 `edit_user`、`edit_role`）

---

### 3.4 数据权限 - GetDataScope

```python
from module_admin.aspect.data_scope import GetDataScope

# 格式：data_scope_sql: str = Depends(GetDataScope('TableName'))
data_scope_sql: str = Depends(GetDataScope('SysUser'))
data_scope_sql: str = Depends(GetDataScope('SysDept'))
data_scope_sql: str = Depends(GetDataScope('SysRole'))
```

**使用场景**:
- 列表查询时过滤数据权限
- 详情查询时检查数据权限
- 删除/修改时检查数据权限

---

## 4. 返回值类型规范

### 4.1 ResponseUtil.success() - 成功响应

```python
from utils.response_util import ResponseUtil

# 返回成功（包含数据）
return ResponseUtil.success(data=data)

# 返回成功（包含模型）
return ResponseUtil.success(model_content=model)

# 返回成功（包含字典）
return ResponseUtil.success(dict_content={'key': 'value'})

# 返回成功（仅消息）
return ResponseUtil.success(msg='操作成功')

# 返回成功（消息 + 数据）
return ResponseUtil.success(msg='操作成功', data=data)

# 返回成功（消息 + 模型）
return ResponseUtil.success(msg='获取成功', model_content=model)
```

**响应格式**:
```json
{
  "code": 200,
  "msg": "操作成功",
  "success": true,
  "time": "2024-01-01 12:00:00",
  "data": {...}
}
```

---

### 4.2 ResponseUtil.failure() - 失败响应

```python
from utils.response_util import ResponseUtil

# 返回失败（仅消息）
return ResponseUtil.failure(msg='操作失败')

# 返回失败（消息 + 数据）
return ResponseUtil.failure(msg='操作失败', data=data)
```

**响应格式**:
```json
{
  "code": 500,
  "msg": "操作失败",
  "success": false,
  "time": "2024-01-01 12:00:00"
}
```

---

### 4.3 ResponseUtil.error() - 错误响应

```python
from utils.response_util import ResponseUtil

# 返回错误（仅消息）
return ResponseUtil.error(msg='接口异常')

# 返回错误（消息 + 数据）
return ResponseUtil.error(msg='接口异常', data=data)
```

**响应格式**:
```json
{
  "code": 1,
  "msg": "接口异常",
  "success": false,
  "time": "2024-01-01 12:00:00"
}
```

---

### 4.4 ResponseUtil.streaming() - 流式响应

```python
from utils.response_util import ResponseUtil
from utils.common_util import bytes2file_response

# 导出文件
return ResponseUtil.streaming(data=bytes2file_response(file_bytes))

# 下载模板
return ResponseUtil.streaming(data=bytes2file_response(template_bytes))
```

**使用场景**:
- 导出 Excel 文件
- 下载导入模板
- 返回二进制文件

---

### 4.5 PageResponseModel - 分页响应

```python
from utils.page_util import PageResponseModel

@userController.get('/list', response_model=PageResponseModel)
async def get_list(...):
    return ResponseUtil.success(model_content=page_result)
```

**响应格式**:
```json
{
  "code": 200,
  "msg": "操作成功",
  "success": true,
  "time": "2024-01-01 12:00:00",
  "rows": [...],
  "total": 100,
  "pageNum": 1,
  "pageSize": 10,
  "hasNext": true
}
```

---

## 5. 参数接收规范

### 5.1 路径参数

```python
@userController.get('/{user_id}')
async def get_user(user_id: int):
    pass
```

---

### 5.2 查询参数

```python
from fastapi import Query

@userController.get('/list')
async def get_list(
    page_num: int = Query(default=1, alias='pageNum'),
    page_size: int = Query(default=10, alias='pageSize'),
):
    pass
```

---

### 5.3 请求体参数

```python
from pydantic import BaseModel

class AddUserModel(BaseModel):
    user_name: str
    nick_name: str
    password: str

@userController.post()
async def add_user(add_user: AddUserModel):
    pass
```

---

### 5.4 表单参数

```python
from fastapi import Form

@userController.post('/export')
async def export_data(
    user_page_query: UserPageQueryModel = Form(),
):
    pass
```

---

### 5.5 文件上传

```python
from fastapi import UploadFile, File

@userController.post('/importData')
async def import_data(
    file: UploadFile = File(...),
):
    pass
```

---

### 5.6 依赖注入参数

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from config.get_db import get_db
from module_admin.service.login_service import LoginService
from module_admin.entity.vo.user_vo import CurrentUserModel

@userController.get('/list')
async def get_list(
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    pass
```

---

## 6. 常见错误对比

### ❌ 不要做

```python
# 错误 1: 不使用权限检查
@userController.get('/list')
async def get_list(...):
    pass  # ❌ 缺少 dependencies=[Depends(CheckUserInterfaceAuth(...))]

# 错误 2: 不使用操作日志
@userController.post()
async def add_user(...):
    pass  # ❌ 缺少 @Log 装饰器

# 错误 3: 新增/修改不验证数据
@userController.post()
async def add_user(add_user: AddUserModel):
    pass  # ❌ 缺少 @ValidateFields 装饰器

# 错误 4: 不使用 ResponseUtil
@userController.get('/list')
async def get_list(...):
    return {'code': 200, 'data': data}  # ❌ 应使用 ResponseUtil.success()

# 错误 5: 导出返回 JSON
@userController.post('/export')
async def export_data(...):
    return ResponseUtil.success(data=data)  # ❌ 应返回流式响应

# 错误 6: 不设置 create_by、update_by
@userController.post()
async def add_user(add_user: AddUserModel):
    await UserService.add_user_services(query_db, add_user)  # ❌ 缺少设置审计字段
```

### ✅ 正确做法

```python
# 正确 1: 使用权限检查
@userController.get('/list', dependencies=[Depends(CheckUserInterfaceAuth('system:user:list'))])
async def get_list(...):
    pass  # ✅

# 正确 2: 使用操作日志
@Log(title='用户管理', business_type=BusinessType.INSERT)
@userController.post()
async def add_user(...):
    pass  # ✅

# 正确 3: 使用数据验证
@ValidateFields(validate_model='add_user')
@userController.post()
async def add_user(add_user: AddUserModel):
    pass  # ✅

# 正确 4: 使用 ResponseUtil
@userController.get('/list')
async def get_list(...):
    return ResponseUtil.success(model_content=data)  # ✅

# 正确 5: 导出返回流式响应
@userController.post('/export')
async def export_data(...):
    return ResponseUtil.streaming(data=bytes2file_response(file_bytes))  # ✅

# 正确 6: 设置审计字段
@userController.post()
async def add_user(
    add_user: AddUserModel,
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    add_user.create_by = current_user.user.user_name
    add_user.create_time = datetime.now()
    add_user.update_by = current_user.user.user_name
    add_user.update_time = datetime.now()
    await UserService.add_user_services(query_db, add_user)  # ✅
```

---

## 7. 检查清单

生成 API 代码前必须检查：

- [ ] **权限检查是否添加**？(`dependencies=[Depends(CheckUserInterfaceAuth(...))]`)
- [ ] **操作日志是否添加**？(`@Log(title='xxx', business_type=BusinessType.XXX)`)
- [ ] **新增/修改是否验证数据**？(`@ValidateFields(validate_model='xxx')`)
- [ ] **返回值是否使用 ResponseUtil**？(success/failure/error/streaming)
- [ ] **HTTP 方法是否正确**？(GET查询, POST新增/导出/导入, PUT修改, DELETE删除)
- [ ] **路径是否遵循 RESTful 规范**？(/list, /{id}, /export, /importData)
- [ ] **审计字段是否设置**？(create_by, create_time, update_by, update_time)
- [ ] **数据权限是否检查**？(GetDataScope)
- [ ] **当前用户是否获取**？(Depends(LoginService.get_current_user))
- [ ] **分页参数是否正确**？(is_page=True/False)
- [ ] **导出是否使用流式响应**？(ResponseUtil.streaming)
- [ ] **文件上传是否使用 UploadFile**？(File(...))
- [ ] **表单参数是否使用 Form()**？(Form())
- [ ] **查询参数是否使用 Query()**？(Query(alias='xxx'))

---

## 8. 完整示例

### 8.1 完整的 CRUD Controller

```python
from datetime import datetime
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic_validation_decorator import ValidateFields
from config.enums import BusinessType
from config.get_db import get_db
from module_admin.annotation.log_annotation import Log
from module_admin.aspect.data_scope import GetDataScope
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.user_vo import (
    AddUserModel,
    DeleteUserModel,
    EditUserModel,
    UserDetailModel,
    UserPageQueryModel,
    CurrentUserModel,
)
from module_admin.service.user_service import UserService
from module_admin.service.login_service import LoginService
from utils.common_util import bytes2file_response
from utils.log_util import logger
from utils.page_util import PageResponseModel
from utils.response_util import ResponseUtil

userController = APIRouter(prefix='/system/user', dependencies=[Depends(LoginService.get_current_user)])

@userController.get(
    '/list',
    response_model=PageResponseModel,
    dependencies=[Depends(CheckUserInterfaceAuth('system:user:list'))]
)
async def get_system_user_list(
    request: Request,
    user_page_query: UserPageQueryModel = Depends(UserPageQueryModel.as_query),
    query_db: AsyncSession = Depends(get_db),
    data_scope_sql: str = Depends(GetDataScope('SysUser')),
):
    user_page_query_result = await UserService.get_user_list_services(
        query_db, user_page_query, data_scope_sql, is_page=True
    )
    logger.info('获取成功')

    return ResponseUtil.success(model_content=user_page_query_result)

@userController.get(
    '/{user_id}',
    response_model=UserDetailModel,
    dependencies=[Depends(CheckUserInterfaceAuth('system:user:query'))]
)
async def query_detail_system_user(
    request: Request,
    user_id: int,
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
    data_scope_sql: str = Depends(GetDataScope('SysUser')),
):
    if not current_user.user.admin:
        await UserService.check_user_data_scope_services(query_db, user_id, data_scope_sql)
    detail_user_result = await UserService.user_detail_services(query_db, user_id)
    logger.info(f'获取user_id为{user_id}的信息成功')

    return ResponseUtil.success(model_content=detail_user_result)

@userController.post('', dependencies=[Depends(CheckUserInterfaceAuth('system:user:add'))])
@ValidateFields(validate_model='add_user')
@Log(title='用户管理', business_type=BusinessType.INSERT)
async def add_system_user(
    request: Request,
    add_user: AddUserModel,
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    add_user.create_by = current_user.user.user_name
    add_user.create_time = datetime.now()
    add_user.update_by = current_user.user.user_name
    add_user.update_time = datetime.now()
    add_user_result = await UserService.add_user_services(query_db, add_user)
    logger.info(add_user_result.message)

    return ResponseUtil.success(msg=add_user_result.message)

@userController.put('', dependencies=[Depends(CheckUserInterfaceAuth('system:user:edit'))])
@ValidateFields(validate_model='edit_user')
@Log(title='用户管理', business_type=BusinessType.UPDATE)
async def edit_system_user(
    request: Request,
    edit_user: EditUserModel,
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
    data_scope_sql: str = Depends(GetDataScope('SysUser')),
):
    await UserService.check_user_allowed_services(edit_user)
    if not current_user.user.admin:
        await UserService.check_user_data_scope_services(query_db, edit_user.user_id, data_scope_sql)
    edit_user.update_by = current_user.user.user_name
    edit_user.update_time = datetime.now()
    edit_user_result = await UserService.edit_user_services(query_db, edit_user)
    logger.info(edit_user_result.message)

    return ResponseUtil.success(msg=edit_user_result.message)

@userController.delete('/{user_ids}', dependencies=[Depends(CheckUserInterfaceAuth('system:user:remove'))])
@Log(title='用户管理', business_type=BusinessType.DELETE)
async def delete_system_user(
    request: Request,
    user_ids: str,
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
    data_scope_sql: str = Depends(GetDataScope('SysUser')),
):
    user_id_list = user_ids.split(',') if user_ids else []
    if user_id_list:
        if current_user.user.user_id in list(map(int, user_id_list)):
            logger.warning('当前登录用户不能删除')
            return ResponseUtil.failure(msg='当前登录用户不能删除')
        for user_id in user_id_list:
            await UserService.check_user_allowed_services(UserModel(userId=int(user_id)))
            if not current_user.user.admin:
                await UserService.check_user_data_scope_services(query_db, int(user_id), data_scope_sql)
    delete_user = DeleteUserModel(userIds=user_ids, updateBy=current_user.user.user_name, updateTime=datetime.now())
    delete_user_result = await UserService.delete_user_services(query_db, delete_user)
    logger.info(delete_user_result.message)

    return ResponseUtil.success(msg=delete_user_result.message)

@userController.post('/export', dependencies=[Depends(CheckUserInterfaceAuth('system:user:export'))])
@Log(title='用户管理', business_type=BusinessType.EXPORT)
async def export_system_user_list(
    request: Request,
    user_page_query: UserPageQueryModel = Form(),
    query_db: AsyncSession = Depends(get_db),
    data_scope_sql: str = Depends(GetDataScope('SysUser')),
):
    user_query_result = await UserService.get_user_list_services(
        query_db, user_page_query, data_scope_sql, is_page=False
    )
    user_export_result = await UserService.export_user_list_services(user_query_result)
    logger.info('导出成功')

    return ResponseUtil.streaming(data=bytes2file_response(user_export_result))

@userController.post('/importData', dependencies=[Depends(CheckUserInterfaceAuth('system:user:import'))])
@Log(title='用户管理', business_type=BusinessType.IMPORT)
async def batch_import_system_user(
    request: Request,
    file: UploadFile = File(...),
    update_support: bool = Query(alias='updateSupport'),
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    batch_import_result = await UserService.batch_import_user_services(
        request, query_db, file, update_support, current_user
    )
    logger.info(batch_import_result.message)

    return ResponseUtil.success(msg=batch_import_result.message)
```

---

## 9. 参考实现

查看已有的完整实现：

- **Controller 参考**: [user_controller.py](file:///d:\001工作\ai_code\CodeAI-v1.7.0\CodeAI-v1.7.0\codeai-backend\module_admin\controller\user_controller.py)
- **Controller 参考**: [role_controller.py](file:///d:\001工作\ai_code\CodeAI-v1.7.0\CodeAI-v1.7.0\codeai-backend\module_admin\controller\role_controller.py)
- **Controller 参考**: [login_controller.py](file:///d:\001工作\ai_code\CodeAI-v1.7.0\CodeAI-v1.7.0\codeai-backend\module_admin\controller\login_controller.py)
- **响应工具**: [response_util.py](file:///d:\001工作\ai_code\CodeAI-v1.7.0\CodeAI-v1.7.0\codeai-backend\utils\response_util.py)
- **分页工具**: [page_util.py](file:///d:\001工作\ai_code\CodeAI-v1.7.0\CodeAI-v1.7.0\codeai-backend\utils\page_util.py)
- **权限检查**: [interface_auth.py](file:///d:\001工作\ai_code\CodeAI-v1.7.0\CodeAI-v1.7.0\codeai-backend\module_admin\aspect\interface_auth.py)
- **日志装饰器**: [log_annotation.py](file:///d:\001工作\ai_code\CodeAI-v1.7.0\CodeAI-v1.7.0\codeai-backend\module_admin\annotation\log_annotation.py)
