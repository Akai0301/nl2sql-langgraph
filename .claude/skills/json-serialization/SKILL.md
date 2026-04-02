---
name: json-serialization
description: |
  当需要处理 JSON 序列化、反序列化、数据类型转换、日期处理时自动使用此 Skill。

  触发场景：
  - JSON 序列化/反序列化操作
  - Pydantic 模型定义与使用
  - 日期时间格式化与转换
  - 复杂类型转换
  - JSON 格式验证
  - 数据类型映射与转换

  触发词：JSON、序列化、反序列化、jsonable_encoder、日期格式、类型转换、JSON验证、Pydantic、BaseModel
---

# JSON 序列化与数据转换指南

> 本项目使用 **Pydantic** 进行数据验证和序列化，使用 **FastAPI** 的 `jsonable_encoder` 进行 JSON 序列化。

## 快速索引

| 功能 | 方法/类 | 说明 |
|------|---------|------|
| 对象转 JSON | `jsonable_encoder()` | FastAPI 内置序列化器 |
| JSON 转对象 | `json.loads()` | 标准 json 模块 |
| 对象转 JSON 字符串 | `json.dumps()` | 标准 json 模块 |
| 数据验证 | `BaseModel` | Pydantic 模型 |
| 别名生成 | `to_camel` | 驼峰转下划线 |
| ORM 转模型 | `from_attributes=True` | 从 ORM 对象创建 |

---

## 核心工具

### jsonable_encoder（FastAPI 内置）

> **位置**：`utils/response_util.py`

```python
from fastapi.encoders import jsonable_encoder

# 序列化任意 Python 对象为 JSON 兼容格式
result = {'code': 200, 'msg': '操作成功', 'data': user}
json_data = jsonable_encoder(result)
```

**特点**：
- 自动处理 datetime、date、time 等类型
- 自动处理 UUID、Decimal 等特殊类型
- 兼容 Pydantic 模型
- 兼容 SQLAlchemy ORM 对象

### 标准 json 模块

```python
import json

# JSON 字符串转对象
data = json.loads('{"name": "张三"}')

# 对象转 JSON 字符串
json_str = json.dumps({"name": "张三"}, ensure_ascii=False)

# 格式化输出
json_str = json.dumps(data, indent=2, ensure_ascii=False)
```

---

## Pydantic BaseModel

### 基本定义

```python
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import Optional


class UserModel(BaseModel):
    """
    用户模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    user_id: Optional[int] = Field(default=None, description='用户ID')
    user_name: Optional[str] = Field(default=None, description='用户账号')
    nick_name: Optional[str] = Field(default=None, description='用户昵称')
    email: Optional[str] = Field(default=None, description='用户邮箱')
    status: Optional[str] = Field(default='0', description='帐号状态（0正常 1停用）')
```

**ConfigDict 配置**：

| 配置 | 说明 | 示例 |
|------|------|------|
| `alias_generator=to_camel` | 字段名转为驼峰 | `user_name` → `userName` |
| `from_attributes=True` | 支持从 ORM 对象创建 | `UserModel.model_validate(user_obj)` |
| `extra='ignore'` | 忽略额外字段 | 不抛出验证错误 |
| `extra='forbid'` | 禁止额外字段 | 抛出验证错误 |

### 字段验证

```python
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Literal


class UserModel(BaseModel):
    """
    用户模型
    """

    model_config = ConfigDict(alias_generator=to_camel)

    # 必填字段
    user_name: str = Field(..., min_length=1, max_length=30, description='用户账号')

    # 可选字段
    nick_name: Optional[str] = Field(default=None, min_length=1, max_length=30, description='用户昵称')

    # 邮箱验证
    email: Optional[EmailStr] = Field(default=None, description='用户邮箱')

    # 枚举值
    status: Literal['0', '1'] = Field(default='0', description='帐号状态（0正常 1停用）')

    # 正则表达式
    phonenumber: Optional[str] = Field(
        default=None,
        pattern=r'^1[3-9]\d{9}$',
        description='手机号码'
    )

    # 自定义验证器
    @field_validator('user_name')
    @classmethod
    def validate_user_name(cls, v):
        if not v or v.strip() == '':
            raise ValueError('用户账号不能为空')
        return v.strip()
```

### 序列化与反序列化

```python
# 对象转 JSON 字符串
user = UserModel(user_name='admin', nick_name='管理员')
json_str = user.model_dump_json()
# 输出：{"userName":"admin","nickName":"管理员"}

# 对象转字典
user_dict = user.model_dump()
# 输出：{'user_name': 'admin', 'nick_name': '管理员'}

# 字典转对象（使用别名）
user = UserModel(**{'userName': 'admin', 'nickName': '管理员'})

# ORM 对象转模型
user = UserModel.model_validate(user_obj)

# JSON 字符串转对象
user = UserModel.model_validate_json('{"userName":"admin","nickName":"管理员"}')
```

---

## 响应工具类 ResponseUtil

> **位置**：`utils/response_util.py`

### 成功响应

```python
from utils.response_util import ResponseUtil

# 基本成功响应
return ResponseUtil.success(msg='操作成功')

# 带 data 的成功响应
return ResponseUtil.success(data=user)

# 带 rows 的成功响应（分页）
return ResponseUtil.success(rows=user_list, total=100)

# 带 dict_content 的成功响应
return ResponseUtil.success(dict_content={'key': 'value'})

# 带 model_content 的成功响应
return ResponseUtil.success(model_content=user_model)

# 自定义响应头
return ResponseUtil.success(headers={'X-Custom-Header': 'value'})
```

### 失败响应

```python
# 基本失败响应
return ResponseUtil.failure(msg='操作失败')

# 带 data 的失败响应
return ResponseUtil.failure(data=error_info)
```

### 错误响应

```python
# 基本错误响应
return ResponseUtil.error(msg='系统错误')

# 带 data 的错误响应
return ResponseUtil.error(data=error_detail)
```

### 流式响应

```python
from fastapi import BackgroundTasks

# 文件下载
return ResponseUtil.streaming(data=file_generator)

# 带后台任务
background_tasks.add_task(cleanup_task)
return ResponseUtil.streaming(data=file_generator, background=background_task)
```

---

## 日期时间处理

### datetime 序列化

```python
from datetime import datetime
from pydantic import BaseModel


class LogModel(BaseModel):
    """
    日志模型
    """

    model_config = ConfigDict(alias_generator=to_camel)

    create_time: Optional[datetime] = Field(default=None, description='创建时间')
    update_time: Optional[datetime] = Field(default=None, description='更新时间')


# 序列化
log = LogModel(create_time=datetime.now())
json_str = log.model_dump_json()
# 输出：{"createTime":"2026-02-06T14:30:45.123456"}
```

### 日期格式化

```python
from datetime import datetime
from pydantic import BaseModel, field_serializer


class UserModel(BaseModel):
    """
    用户模型
    """

    model_config = ConfigDict(alias_generator=to_camel)

    login_date: Optional[datetime] = Field(default=None, description='最后登录时间')

    @field_serializer('login_date')
    @classmethod
    def serialize_login_date(cls, value: datetime) -> str:
        if value:
            return value.strftime('%Y-%m-%d %H:%M:%S')
        return None


# 序列化
user = UserModel(login_date=datetime.now())
json_str = user.model_dump_json()
# 输出：{"loginDate":"2026-02-06 14:30:45"}
```

---

## 复杂类型处理

### 嵌套模型

```python
from typing import List, Optional


class RoleModel(BaseModel):
    """
    角色模型
    """

    model_config = ConfigDict(alias_generator=to_camel)

    role_id: Optional[int] = Field(default=None, description='角色ID')
    role_name: Optional[str] = Field(default=None, description='角色名称')


class UserModel(BaseModel):
    """
    用户模型
    """

    model_config = ConfigDict(alias_generator=to_camel)

    user_id: Optional[int] = Field(default=None, description='用户ID')
    user_name: Optional[str] = Field(default=None, description='用户账号')
    roles: Optional[List[RoleModel]] = Field(default=None, description='角色列表')


# 使用
user = UserModel(
    user_name='admin',
    roles=[
        RoleModel(role_id=1, role_name='管理员'),
        RoleModel(role_id=2, role_name='普通用户')
    ]
)
```

### 泛型类型

```python
from typing import List, Dict, TypeVar, Generic

T = TypeVar('T')


class PageResponseModel(BaseModel, Generic[T]):
    """
    分页响应模型
    """

    model_config = ConfigDict(alias_generator=to_camel)

    total: int = Field(description='总记录数')
    rows: List[T] = Field(description='数据列表')


# 使用
UserPageResponse = PageResponseModel[UserModel]
page = UserPageResponse(total=100, rows=[user1, user2])
```

---

## JSON 验证

### 基本验证

```python
import json

def is_json(text: str) -> bool:
    """
    判断是否为合法 JSON

    :param text: 待验证文本
    :return: 是否为合法 JSON
    """
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, TypeError):
        return False

def is_json_object(text: str) -> bool:
    """
    判断是否为 JSON 对象

    :param text: 待验证文本
    :return: 是否为 JSON 对象
    """
    try:
        data = json.loads(text)
        return isinstance(data, dict)
    except (json.JSONDecodeError, TypeError):
        return False

def is_json_array(text: str) -> bool:
    """
    判断是否为 JSON 数组

    :param text: 待验证文本
    :return: 是否为 JSON 数组
    """
    try:
        data = json.loads(text)
        return isinstance(data, list)
    except (json.JSONDecodeError, TypeError):
        return False
```

### 使用示例

```python
# 验证 JSON
if not is_json(data):
    raise ServiceException(message='数据格式不正确')

# 验证 JSON 对象
if not is_json_object(config_value):
    raise ServiceException(message='配置必须是 JSON 对象格式')

# 验证 JSON 数组
if not is_json_array(data_list):
    raise ServiceException(message='数据必须是 JSON 数组格式')
```

---

## 使用示例

### Service 中的 JSON 操作

```python
import json
from sqlalchemy.ext.asyncio import AsyncSession
from exceptions.exception import ServiceException
from module_admin.entity.vo.common_vo import CrudResponseModel
from module_admin.entity.vo.config_vo import ConfigModel


class ConfigService:
    """
    配置管理服务
    """

    @classmethod
    async def get_config_services(cls, query_db: AsyncSession, config_key: str):
        """
        获取配置服务

        :param query_db: orm对象
        :param config_key: 配置键
        :return: 配置对象
        """
        config = await ConfigDao.get_config_by_key(query_db, config_key)
        if not config:
            return None

        # JSON 字符串转对象
        try:
            config_value = json.loads(config.config_value)
        except json.JSONDecodeError:
            raise ServiceException(message='配置值格式不正确')

        return config_value

    @classmethod
    async def save_config_services(cls, query_db: AsyncSession, config_key: str, value: dict):
        """
        保存配置服务

        :param query_db: orm对象
        :param config_key: 配置键
        :param value: 配置值
        :return: 操作结果
        """
        # 对象转 JSON 字符串
        config_value = json.dumps(value, ensure_ascii=False)

        config = ConfigModel(config_key=config_key, config_value=config_value)
        await ConfigDao.add_config(query_db, config)
        await query_db.commit()

        return CrudResponseModel(is_success=True, message='保存成功')

    @classmethod
    async def import_data_services(cls, data_list: str):
        """
        导入数据服务

        :param data_list: 数据列表 JSON 字符串
        :return: 操作结果
        """
        # 验证 JSON 数组
        if not is_json_array(data_list):
            raise ServiceException(message='数据格式不正确，应为 JSON 数组')

        # JSON 字符串转对象列表
        data = json.loads(data_list)

        # 处理数据...
        return CrudResponseModel(is_success=True, message='导入成功')
```

### Controller 中的响应

```python
from fastapi import APIRouter, Depends
from module_admin.entity.vo.user_vo import UserModel, UserPageQueryModel
from utils.response_util import ResponseUtil


userController = APIRouter(prefix='/system/user')


@userController.get('/list')
async def get_user_list(user_page_query: UserPageQueryModel = Depends(UserPageQueryModel.as_query)):
    """
    获取用户列表

    :param user_page_query: 查询参数
    :return: 用户列表
    """
    users = await UserService.get_user_list_services(user_page_query)

    # 返回分页数据
    return ResponseUtil.success(model_content=users)


@userController.post('')
async def add_user(user: UserModel):
    """
    新增用户

    :param user: 用户对象
    :return: 操作结果
    """
    result = await UserService.add_user_services(user)

    return ResponseUtil.success(msg='新增成功')
```

---

## 常见问题

### 1. 什么时候用 BaseModel vs dict？

```python
# ✅ 需要验证和序列化时使用 BaseModel
class UserModel(BaseModel):
    user_name: str
    email: EmailStr

user = UserModel(user_name='admin', email='admin@example.com')

# ✅ 简单数据传递使用 dict
data = {'user_name': 'admin', 'email': 'admin@example.com'}
```

### 2. 如何处理 ORM 对象？

```python
# ✅ 使用 from_attributes=True
class UserModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_name: str

# 从 ORM 对象创建
user = UserModel.model_validate(user_obj)
```

### 3. 如何自定义字段别名？

```python
# ✅ 使用 alias_generator=to_camel（全局）
class UserModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)
    user_name: str  # 序列化为 userName

# ✅ 使用 Field.alias（单个字段）
class UserModel(BaseModel):
    user_name: str = Field(alias='userName')
```

### 4. 如何处理可选字段？

```python
from typing import Optional

class UserModel(BaseModel):
    user_name: str  # 必填
    email: Optional[str] = None  # 可选
    phone: Optional[str] = Field(default=None, description='手机号码')
```

### 5. 如何验证 JSON 字符串？

```python
import json

def validate_json(data: str) -> dict:
    """
    验证并解析 JSON

    :param data: JSON 字符串
    :return: 解析后的字典
    """
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        raise ServiceException(message=f'JSON 格式错误: {e}')
```

---

## 禁止事项

```python
# ❌ 禁止：直接使用 json.dumps 序列化 ORM 对象
json.dumps(user_obj)

# ✅ 正确：使用 jsonable_encoder 或 BaseModel
from fastapi.encoders import jsonable_encoder
jsonable_encoder(user_obj)

# ❌ 禁止：不验证直接解析 JSON
data = json.loads(user_input)

# ✅ 正确：先验证再解析
if is_json(user_input):
    data = json.loads(user_input)
else:
    raise ServiceException(message='数据格式不正确')

# ❌ 禁止：不使用 from_attributes=True
class UserModel(BaseModel):
    user_name: str

# ✅ 正确：使用 from_attributes=True
class UserModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_name: str

# ❌ 禁止：手动处理日期序列化
json.dumps({'time': datetime.now()})

# ✅ 正确：使用 Pydantic 自动处理
class LogModel(BaseModel):
    create_time: datetime
```
