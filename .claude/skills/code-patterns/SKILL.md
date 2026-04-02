---
name: code-patterns
description: |
  后端代码禁令和编码规范速查。本项目是 FastAPI + Python 后端项目。

  触发场景：
  - 查看项目禁止事项（后端代码）
  - 命名规范速查
  - Git 提交规范
  - 避免过度工程
  - 代码风格检查

  触发词：规范、禁止、命名、Git提交、代码风格、不能用、不允许、包名、架构

  注意：后端 CRUD 开发规范请激活 crud-development，API 开发规范请激活 api-development，数据库设计规范请 activate database-ops。
---

# 代码规范速查

## 🚫 后端禁令速查表

> **快速查表**：一眼定位所有后端代码禁止写法

| 禁止项 | ❌ 禁止写法 | ✅ 正确写法 | 原因 |
|--------|-----------|-----------|------|
| 包名规范 | `com.ruoyi.*` 或 `plus.ruoyi.*` | `module_*` | 模块化规范 |
| 同步数据库操作 | `session.execute()` | `await session.execute()` | 异步架构 |
| 返回字典 | `return {'code': 200, 'data': {...}}` | `ResponseUtil.success(data=...)` | 统一响应格式 |
| Service设计 | `class XxxService(object)` | `class XxxService:` | 静态方法模式 |
| 查询构建 | 在 Controller 层构建 | **DAO 层** | 职责分离 |
| 接口路径 | `/pageXxxs`, `/getXxx/{id}` | `/list`, `/{id}`, `/` | RESTful 规范 |
| 对象转换 | 手动字典转换 | `model.model_dump()` | Pydantic 规范 |
| 主键策略 | 不使用自增 | `autoincrement=True` | 数据库规范 |
| 返回String陷阱 | `ResponseUtil.success(data=stringValue)` | `ResponseUtil.success(dict_content={...})` | 响应格式规范 |
| DO基类 | 无基类继承 | `class XxxDO(Base)` | SQLAlchemy 规范 |
| Redis缓存 | 返回不可变集合 | 返回可变集合 | Redis 序列化 |
| 响应类型 | 直接返回字典 | 使用 `ResponseUtil` | 统一响应 |
| Bash命令 | `> nul` | `> /dev/null 2>&1` | Windows 兼容性 |

---

## 🚫 后端禁令（12 条）

### 1. 模块命名规范

```python
# ✅ 正确：使用 module_ 前缀
module_admin/
module_generator/
module_task/

# ❌ 错误：使用其他命名方式
com.ruoyi.admin/
plus.ruoyi.generator/
business/
```

### 2. 禁止使用同步数据库操作

```python
# ✅ 正确：使用异步操作
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user_list(query_db: AsyncSession):
    result = await query_db.execute(select(SysUser))
    return result.scalars().all()

# ❌ 错误：使用同步操作
def get_user_list(query_db: Session):
    result = query_db.execute(select(SysUser))
    return result.scalars().all()
```

### 3. 禁止直接返回字典作为响应

```python
# ✅ 正确：使用 ResponseUtil
from utils.response_util import ResponseUtil

return ResponseUtil.success(data=user_list)
return ResponseUtil.success(msg='操作成功', dict_content={'key': 'value'})

# ❌ 错误：直接返回字典
return {'code': 200, 'msg': '操作成功', 'data': user_list}
```

### 4. Service 层使用静态方法

```python
# ✅ 正确：使用类静态方法
class UserService:
    @classmethod
    async def get_user_list_services(cls, query_db: AsyncSession, query_object: UserPageQueryModel):
        return await UserDao.get_user_list(query_db, query_object)

# ❌ 错误：使用实例方法或继承
class UserService(object):
    def __init__(self):
        pass
    
    def get_user_list_services(self, query_db, query_object):
        pass
```

### 5. 查询条件必须在 DAO 层构建

> **本项目是三层架构**，数据库查询逻辑在 **DAO 层**。

```python
# ✅ 正确：在 DAO 层构建查询条件
class UserDao:
    @classmethod
    async def get_user_list(cls, db: AsyncSession, query_object: UserPageQueryModel):
        query = (
            select(SysUser)
            .where(
                SysUser.del_flag == '0',
                SysUser.user_name.like(f'%{query_object.user_name}%') if query_object.user_name else True,
            )
            .order_by(SysUser.user_id)
        )
        return await PageUtil.paginate(db, query, query_object.page_num, query_object.page_size)

# ❌ 错误：在 Controller 或 Service 层构建查询条件
@userController.get('/list')
async def get_user_list(query_db: AsyncSession = Depends(get_db)):
    query = select(SysUser).where(SysUser.del_flag == '0')  # 禁止！
    result = await query_db.execute(query)
```

### 6. 接口路径必须使用标准 RESTful 格式

```python
# ✅ 正确：标准 RESTful 路径
@userController.get('/list')              # 分页/列表查询
@userController.get('/{user_id}')          # 获取详情
@userController.post('')                   # 新增（空路径）
@userController.put('')                   # 修改（空路径）
@userController.delete('/{user_ids}')     # 删除
@userController.post('/export')            # 导出

# ❌ 错误：包含动词或实体名
@userController.get('/pageUsers')
@userController.get('/getUser/{id}')
@userController.post('/addUser')
@userController.put('/updateUser')
```

### 7. 禁止手动进行对象转换

```python
# ✅ 正确：使用 Pydantic 的 model_dump
user_dict = user_model.model_dump(by_alias=True)
user_dict = user_model.model_dump(exclude_unset=True)

# ❌ 错误：手动转换
user_dict = {
    'user_id': user.user_id,
    'user_name': user.user_name,
    'nick_name': user.nick_name,
}
```

### 8. 主键策略规范

```python
# ✅ 正确：使用自增主键
from sqlalchemy import Column, BigInteger

user_id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='用户ID')

# ❌ 错误：不指定自增或使用其他策略
user_id = Column(BigInteger, primary_key=True, comment='用户ID')
```

### 9. ResponseUtil 返回规范

```python
# 场景：返回字符串或简单值

# ❌ 错误：使用 data 参数返回字符串
return ResponseUtil.success(data=token)  # 可能导致混淆

# ✅ 正确：使用 dict_content 返回自定义字段
return ResponseUtil.success(dict_content={'token': token})
return ResponseUtil.success(msg='获取成功', dict_content={'imgUrl': avatar_path})

# ✅ 正确：返回复杂对象
return ResponseUtil.success(model_content=user_model)
return ResponseUtil.success(data=user_list)
```

### 10. DO 必须继承 Base

```python
# ✅ 正确：继承 Base
from config.database import Base
from sqlalchemy import Column, BigInteger, String

class SysUser(Base):
    __tablename__ = 'sys_user'
    __table_args__ = {'comment': '用户信息表'}
    
    user_id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='用户ID')
    user_name = Column(String(30), nullable=False, comment='用户账号')

# ❌ 错误：不继承基类
class SysUser:
    __tablename__ = 'sys_user'
    
    user_id = Column(BigInteger, primary_key=True)
```

### 11. Redis 缓存禁止返回不可变集合

```python
# ❌ 错误：返回不可变集合
# 会导致 Redis 反序列化失败
@cache
async def get_user_list():
    return tuple(user_list)  # 禁止！
    return frozenset(user_set)  # 禁止！

# ✅ 正确：返回可变集合
@cache
async def get_user_list():
    return list(user_list)  # ✅
    return set(user_set)  # ✅
    return dict(user_dict)  # ✅
```

### 12. 响应类型规范

```python
# ✅ 正确：使用 ResponseUtil 工具类
from utils.response_util import ResponseUtil

return ResponseUtil.success(data=result)
return ResponseUtil.failure(msg='操作失败')
return ResponseUtil.unauthorized(msg='未登录')
return ResponseUtil.forbidden(msg='无权限')
return ResponseUtil.error(msg='服务器错误')
return ResponseUtil.streaming(data=bytes_data)

# ❌ 错误：直接返回字典或使用其他方式
return {'code': 200, 'data': result}
return JSONResponse(content={'code': 200, 'data': result})
```

---

## 📝 命名规范速查

### 后端命名

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块目录 | `module_*` | `module_admin`, `module_generator` |
| 类名 | 大驼峰 | `UserService`, `UserDao` |
| 方法名 | 小驼峰 | `get_user_list_services`, `add_user_dao` |
| 变量名 | 小驼峰 | `user_name`, `create_time` |
| 常量 | 全大写下划线 | `MAX_PAGE_SIZE`, `SUCCESS` |
| 表名 | 小写下划线 | `sys_user`, `test_demo` |
| 字段名 | 小写下划线 | `user_name`, `create_time` |

### 文件命名后缀

| 类型 | 后缀 | 示例 |
|------|------|------|
| 数据库实体 | `_do.py` | `user_do.py` |
| 视图对象 | `_vo.py` | `user_vo.py` |
| 控制器 | `_controller.py` | `user_controller.py` |
| 服务层 | `_service.py` | `user_service.py` |
| 数据访问层 | `_dao.py` | `user_dao.py` |

### 类命名

| 类型 | 命名规范 | 示例 |
|------|---------|------|
| 数据库实体 | `SysXxx` 或 `XxxDO` | `SysUser`, `UserDO` |
| 视图对象 | `XxxModel` 或 `XxxVO` | `UserModel`, `UserVO` |
| 服务类 | `XxxService` | `UserService` |
| 数据访问类 | `XxxDao` | `UserDao` |
| 控制器 | `xxxController` | `userController` |

### 方法命名

| 操作 | Service 方法 | DAO 方法 | Controller URL |
|------|-------------|----------|----------------|
| 分页查询 | `get_xxx_list_services` | `get_xxx_list` | `GET /list` |
| 查询单个 | `xxx_detail_services` | `get_xxx_detail_by_id` | `GET /{id}` |
| 新增 | `add_xxx_services` | `add_xxx_dao` | `POST /` |
| 修改 | `edit_xxx_services` | `edit_xxx_dao` | `PUT /` |
| 删除 | `delete_xxx_services` | `delete_xxx_dao` | `DELETE /{ids}` |
| 导出 | `export_xxx_list_services` | - | `POST /export` |

---

## ✅ 避免过度工程

### 不要做的事

1. **不要创建不必要的抽象**
   - 只有一处使用的代码不需要抽取
   - 三处以上相同代码才考虑抽取

2. **不要添加不需要的功能**
   - 只实现当前需求
   - 不要"以防万一"添加功能

3. **不要过早优化**
   - 优先使用简单直接的方案
   - 复杂方案需要有明确理由

4. **不要添加无用注释**
   - 不要给显而易见的代码加注释
   - 只在逻辑复杂处添加注释

5. **不要保留废弃代码**
   - 删除不用的代码，不要注释保留
   - Git 有历史记录

---

## 📦 Git 提交规范

### 格式

```
<type>(<scope>): <description>
```

### 类型

| type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修复 Bug |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响逻辑） |
| `refactor` | 重构（不是新功能或修复） |
| `perf` | 性能优化 |
| `test` | 测试 |
| `chore` | 构建/工具 |

### 示例

```bash
feat(admin): 新增用户反馈功能
fix(admin): 修复订单状态显示错误
docs(readme): 更新安装说明
refactor(common): 重构分页查询工具类
perf(admin): 优化用户列表查询性能
```

---

## 🔗 相关 Skill

| 需要了解 | 激活 Skill |
|---------|-----------|
| 后端 CRUD 开发规范 | `crud-development` |
| API 开发规范 | `api-development` |
| 数据库设计规范 | `database-ops` |
| 系统架构设计 | `architecture-design` |
| 技术方案决策 | `tech-decision` |

---

## 🏗️ 项目架构说明

### 三层架构

```
Controller（控制器层）
    ↓ 接收请求、参数校验、响应封装
Service（服务层）
    ↓ 业务逻辑处理、事务管理
DAO（数据访问层）
    ↓ 数据库操作（SQLAlchemy）
Database（数据库）
```

### 核心技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.116.1 | Web 框架 |
| SQLAlchemy | 2.0.43 | ORM 框架（异步） |
| Pydantic | - | 数据验证和序列化 |
| Alembic | 1.16.4 | 数据库迁移 |
| Redis | 6.4.0 | 缓存和会话管理 |

### 模块结构

```
module_xxx/
├── controller/          # 控制器层
│   └── xxx_controller.py
├── service/             # 服务层
│   └── xxx_service.py
├── dao/                 # 数据访问层
│   └── xxx_dao.py
└── entity/              # 实体类
    ├── do/              # 数据库对象
    │   └── xxx_do.py
    └── vo/              # 视图对象
        └── xxx_vo.py
```

### 依赖注入

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from config.get_db import get_db

@userController.get('/list')
async def get_user_list(
    query_db: AsyncSession = Depends(get_db),  # 数据库会话
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),  # 当前用户
    data_scope_sql: str = Depends(GetDataScope('SysUser')),  # 数据权限
):
    pass
```

### 响应格式

```python
{
    "code": 200,
    "msg": "操作成功",
    "success": true,
    "data": {...},
    "time": "2024-01-01 12:00:00"
}
```
