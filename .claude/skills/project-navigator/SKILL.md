---
name: project-navigator
description: |
  当需要了解项目结构、查找文件、定位代码时自动使用此 Skill。提供项目结构导航和资源索引。

  触发场景：
  - 不知道文件在哪里
  - 想了解项目结构
  - 查找某个功能的代码位置
  - 了解模块职责
  - 查看已有的工具类、组件、API
  - 寻找参考代码

  触发词：项目结构、文件在哪、目录、模块、代码位置、找、定位、结构、在哪里、哪个文件、参考、已有
---

# 项目导航指南

> **说明**：本项目是纯后端项目（CodeAI），基于 FastAPI + Python 开发。

## 项目整体结构

```
codeai-backend/
├── app.py                           # 应用启动入口
├── server.py                        # FastAPI 应用配置
├── requirements.txt                 # Python 依赖包
├── requirements-pg.txt              # PostgreSQL 依赖包
├── alembic.ini                      # Alembic 数据库迁移配置
├── .env.dev                         # 开发环境配置
├── .env.prod                        # 生产环境配置
│
├── config/                          # 配置模块
│   ├── constant.py                  # 常量定义
│   ├── database.py                  # 数据库配置
│   ├── enums.py                     # 枚举定义
│   ├── env.py                       # 环境变量配置
│   └── get_db.py                    # 数据库会话获取
│
├── module_admin/                    # 系统管理模块（核心模块）
│   ├── controller/                  # 控制器层
│   ├── service/                      # 服务层
│   ├── dao/                         # 数据访问层
│   ├── entity/                      # 实体类
│   │   ├── do/                      # 数据对象（DO）
│   │   └── vo/                      # 视图对象（VO）
│   ├── annotation/                  # 自定义注解
│   └── aspect/                      # 切面（数据权限、接口认证）
│
├── module_generator/                # 代码生成器模块
│   ├── controller/                  # 控制器层
│   ├── service/                      # 服务层
│   ├── dao/                         # 数据访问层
│   ├── entity/                      # 实体类
│   └── templates/                   # 代码模板
│       ├── python/                  # Python 代码模板
│       ├── js/                      # JavaScript 代码模板
│       ├── vue/                     # Vue 代码模板
│       └── sql/                     # SQL 代码模板
│
├── utils/                           # 工具类模块
│   ├── common_util.py               # 通用工具
│   ├── response_util.py             # 响应工具
│   ├── page_util.py                 # 分页工具
│   ├── excel_util.py                # Excel 工具
│   ├── upload_util.py               # 文件上传工具
│   ├── log_util.py                  # 日志工具
│   ├── pwd_util.py                  # 密码工具
│   ├── string_util.py               # 字符串工具
│   ├── time_format_util.py          # 时间格式化工具
│   ├── cron_util.py                 # Cron 表达式工具
│   ├── gen_util.py                  # 代码生成工具
│   ├── import_util.py               # 导入工具
│   ├── message_util.py              # 消息工具
│   └── template_util.py             # 模板工具
│
├── exceptions/                      # 异常处理模块
│   ├── exception.py                 # 自定义异常
│   └── handle.py                    # 全局异常处理器
│
├── alembic/                         # 数据库迁移
│   ├── env.py                       # Alembic 环境配置
│   ├── script.py.mako               # 迁移脚本模板
│   └── versions/                    # 迁移版本文件
│
├── sql/                             # 数据库脚本
│   ├── codeai.sql            # MySQL 数据库脚本
│   └── codeai-pg.sql         # PostgreSQL 数据库脚本
│
├── assets/                          # 静态资源
│   └── font/                        # 字体文件
│
└── .claude/                         # Claude AI 配置目录
    └── skills/                      # 技能库
```

---

## 后端模块位置

### 已有主要模块

| 模块 | 位置 | 说明 |
|------|------|------|
| **系统管理** (Admin) | `module_admin/` | ⭐ 系统核心功能（用户、角色、菜单等） |
| **代码生成** (Generator) | `module_generator/` | 代码生成器 |

### 🔴 标准模块代码结构（三层架构）

> **重要**：本项目是三层架构（Controller → Service → DAO），**有 DAO 层**。

```
module_admin/
├── controller/                      # 控制器层
│   ├── user_controller.py          # 用户控制器
│   ├── role_controller.py          # 角色控制器
│   ├── menu_controller.py          # 菜单控制器
│   ├── dept_controller.py          # 部门控制器
│   ├── post_controller.py          # 岗位控制器
│   ├── dict_controller.py          # 字典控制器
│   ├── config_controller.py        # 参数配置控制器
│   ├── notice_controller.py        # 通知公告控制器
│   ├── log_controller.py           # 日志控制器
│   ├── job_controller.py           # 定时任务控制器
│   ├── online_controller.py        # 在线用户控制器
│   ├── cache_controller.py         # 缓存控制器
│   ├── captcha_controller.py       # 验证码控制器
│   ├── server_controller.py       # 服务器监控控制器
│   ├── common_controller.py       # 公共控制器
│   └── login_controller.py        # 登录控制器
│
├── service/                         # 服务层
│   ├── user_service.py             # 用户服务
│   ├── role_service.py             # 角色服务
│   ├── menu_service.py             # 菜单服务
│   ├── dept_service.py             # 部门服务
│   ├── post_service.py             # 岗位服务
│   ├── dict_service.py             # 字典服务
│   ├── config_service.py           # 参数配置服务
│   ├── notice_service.py           # 通知公告服务
│   ├── log_service.py              # 日志服务
│   ├── job_service.py              # 定时任务服务
│   ├── job_log_service.py          # 定时任务日志服务
│   ├── online_service.py           # 在线用户服务
│   ├── cache_service.py            # 缓存服务
│   ├── captcha_service.py          # 验证码服务
│   ├── server_service.py           # 服务器监控服务
│   ├── common_service.py           # 公共服务
│   └── login_service.py            # 登录服务
│
├── dao/                             # 数据访问层
│   ├── user_dao.py                 # 用户 DAO
│   ├── role_dao.py                 # 角色 DAO
│   ├── menu_dao.py                 # 菜单 DAO
│   ├── dept_dao.py                 # 部门 DAO
│   ├── post_dao.py                 # 岗位 DAO
│   ├── dict_dao.py                 # 字典 DAO
│   ├── config_dao.py               # 参数配置 DAO
│   ├── notice_dao.py               # 通知公告 DAO
│   ├── log_dao.py                  # 日志 DAO
│   ├── job_dao.py                  # 定时任务 DAO
│   ├── job_log_dao.py              # 定时任务日志 DAO
│   ├── login_dao.py                # 登录 DAO
│   └── menu_dao.py                 # 菜单 DAO
│
├── entity/                          # 实体类
│   ├── do/                         # 数据对象（DO）
│   │   ├── user_do.py              # 用户 DO
│   │   ├── role_do.py              # 角色 DO
│   │   ├── menu_do.py              # 菜单 DO
│   │   ├── dept_do.py              # 部门 DO
│   │   ├── post_do.py              # 岗位 DO
│   │   ├── dict_do.py              # 字典 DO
│   │   ├── config_do.py            # 参数配置 DO
│   │   ├── notice_do.py            # 通知公告 DO
│   │   ├── log_do.py               # 日志 DO
│   │   ├── job_do.py               # 定时任务 DO
│   │   └── menu_do.py              # 菜单 DO
│   └── vo/                         # 视图对象（VO）
│       ├── user_vo.py              # 用户 VO
│       ├── role_vo.py              # 角色 VO
│       ├── menu_vo.py              # 菜单 VO
│       ├── dept_vo.py              # 部门 VO
│       ├── post_vo.py              # 岗位 VO
│       ├── dict_vo.py              # 字典 VO
│       ├── config_vo.py            # 参数配置 VO
│       ├── notice_vo.py            # 通知公告 VO
│       ├── log_vo.py               # 日志 VO
│       ├── job_vo.py               # 定时任务 VO
│       ├── login_vo.py             # 登录 VO
│       ├── online_vo.py            # 在线用户 VO
│       ├── cache_vo.py             # 缓存 VO
│       ├── server_vo.py            # 服务器监控 VO
│       └── common_vo.py            # 公共 VO
│
├── annotation/                      # 自定义注解
│   ├── log_annotation.py           # 日志注解
│   └── pydantic_annotation.py      # Pydantic 注解
│
└── aspect/                          # 切面
    ├── data_scope.py               # 数据权限切面
    └── interface_auth.py            # 接口认证切面
```

**关键点**：
- Service 层**不继承任何基类**，直接注入 DAO
- DAO 层使用 SQLAlchemy 进行数据库操作
- VO 使用 Pydantic BaseModel 进行数据验证
- 使用 `@as_query` 注解将 VO 转换为查询参数

---

## 核心工具类位置

| 工具类 | 位置 | 说明 |
|--------|------|------|
| `ResponseUtil` | `utils/response_util.py` | 响应工具类（必须使用） |
| `PageUtil` | `utils/page_util.py` | 分页工具类 |
| `ExcelUtil` | `utils/excel_util.py` | Excel 导入导出工具 |
| `UploadUtil` | `utils/upload_util.py` | 文件上传工具 |
| `LogUtil` | `utils/log_util.py` | 日志工具 |
| `PwdUtil` | `utils/pwd_util.py` | 密码加密工具 |
| `StringUtil` | `utils/string_util.py` | 字符串工具 |
| `TimeFormatUtil` | `utils/time_format_util.py` | 时间格式化工具 |
| `CronUtil` | `utils/cron_util.py` | Cron 表达式工具 |
| `GenUtil` | `utils/gen_util.py` | 代码生成工具 |
| `ImportUtil` | `utils/import_util.py` | 导入工具 |
| `MessageUtil` | `utils/message_util.py` | 消息工具 |
| `TemplateUtil` | `utils/template_util.py` | 模板工具 |
| `CommonUtil` | `utils/common_util.py` | 通用工具 |
| `ServiceException` | `exceptions/exception.py` | 业务异常 |
| `LoginException` | `exceptions/exception.py` | 登录异常 |
| `AuthException` | `exceptions/exception.py` | 认证异常 |

---

## 配置文件位置

| 配置 | 位置 | 说明 |
|------|------|------|
| 应用启动 | `app.py` | 应用启动入口 |
| 应用配置 | `server.py` | FastAPI 应用配置 |
| Python 依赖 | `requirements.txt` | Python 依赖包 |
| PostgreSQL 依赖 | `requirements-pg.txt` | PostgreSQL 依赖包 |
| 开发环境配置 | `.env.dev` | 开发环境配置（数据库连接等） |
| 生产环境配置 | `.env.prod` | 生产环境配置 |
| Alembic 配置 | `alembic.ini` | 数据库迁移配置 |
| 常量定义 | `config/constant.py` | 常量定义 |
| 数据库配置 | `config/database.py` | 数据库配置 |
| 枚举定义 | `config/enums.py` | 枚举定义 |
| 环境变量 | `config/env.py` | 环境变量配置 |
| 数据库会话 | `config/get_db.py` | 数据库会话获取 |

---

## 数据库脚本位置

| 脚本 | 位置 | 说明 |
|------|------|------|
| MySQL 脚本 | `sql/codeai.sql` | MySQL 数据库初始化脚本 |
| PostgreSQL 脚本 | `sql/codeai-pg.sql` | PostgreSQL 数据库初始化脚本 |

---

## 快速查找

### 我想找...

| 需求 | 位置 |
|------|------|
| 参考后端代码 | `module_admin/` 的系统模块 |
| 看 Controller 怎么写 | `module_admin/controller/user_controller.py` |
| 看 Service 怎么写 | `module_admin/service/user_service.py` |
| 看 DAO 怎么写 | `module_admin/dao/user_dao.py` |
| 看 DO 怎么写 | `module_admin/entity/do/user_do.py` |
| 看 VO 怎么写 | `module_admin/entity/vo/user_vo.py` |
| 数据库表结构 | `sql/codeai.sql` |
| 工具类 | `utils/` |
| 异常处理 | `exceptions/` |
| 数据库迁移 | `alembic/` |
| 代码生成器 | `module_generator/` |

---

## 模块与表前缀对应

| 模块 | 表前缀 | 包路径 |
|------|--------|--------|
| admin | `sys_` | `module_admin` |
| generator | `gen_` | `module_generator` |
| 自定义业务 | 自定义 | `module_xxx` |

---

## 常用查找命令

```bash
# 查找 Python 文件
Glob module_admin/**/*[类名]*.py

# 查找包含特定内容的文件
Grep "[关键词]" module_admin/ --type py

# 查找配置文件
Glob .env.*

# 查找 Service 类
Glob module_admin/service/*_service.py

# 查找 DAO 类
Glob module_admin/dao/*_dao.py

# 查找 Controller 类
Glob module_admin/controller/*_controller.py

# 查找 VO 类
Glob module_admin/entity/vo/*_vo.py

# 查找 DO 类
Glob module_admin/entity/do/*_do.py

# 查找工具类
Glob utils/*_util.py

# 查找异常类
Glob exceptions/*.py
```

---

## 三层架构代码示例

### Controller 结构（重点参考）

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from module_admin.entity.vo.user_vo import UserModel, UserPageQueryModel
from module_admin.service.user_service import UserService
from utils.response_util import ResponseUtil
from config.get_db import get_db


userController = APIRouter(prefix='/system/user')


@userController.get('/list')
async def get_user_list(
    user_page_query: UserPageQueryModel = Depends(UserPageQueryModel.as_query),
    query_db: AsyncSession = Depends(get_db)
):
    """
    获取用户列表

    :param user_page_query: 查询参数
    :param query_db: 数据库会话
    :return: 用户列表
    """
    users = await UserService.get_user_list_services(query_db, user_page_query)

    return ResponseUtil.success(model_content=users)


@userController.get('/{user_id}')
async def get_user_info(
    user_id: int,
    query_db: AsyncSession = Depends(get_db)
):
    """
    获取用户详情

    :param user_id: 用户ID
    :param query_db: 数据库会话
    :return: 用户详情
    """
    user = await UserService.user_detail_services(query_db, user_id)

    return ResponseUtil.success(data=user)


@userController.post('')
async def add_user(
    user: UserModel,
    request: Request,
    query_db: AsyncSession = Depends(get_db)
):
    """
    新增用户

    :param user: 用户对象
    :param request: Request 对象
    :param query_db: 数据库会话
    :return: 操作结果
    """
    await UserService.add_user_services(request, query_db, user)
    await query_db.commit()

    return ResponseUtil.success(msg='新增成功')


@userController.put('')
async def edit_user(
    user: UserModel,
    request: Request,
    query_db: AsyncSession = Depends(get_db)
):
    """
    修改用户

    :param user: 用户对象
    :param request: Request 对象
    :param query_db: 数据库会话
    :return: 操作结果
    """
    await UserService.edit_user_services(request, query_db, user)
    await query_db.commit()

    return ResponseUtil.success(msg='修改成功')


@userController.delete('/{user_ids}')
async def delete_user(
    user_ids: str,
    request: Request,
    query_db: AsyncSession = Depends(get_db)
):
    """
    删除用户

    :param user_ids: 用户ID（逗号分隔）
    :param request: Request 对象
    :param query_db: 数据库会话
    :return: 操作结果
    """
    await UserService.delete_user_services(request, query_db, user_ids)
    await query_db.commit()

    return ResponseUtil.success(msg='删除成功')
```

### Service 结构

```python
from sqlalchemy.ext.asyncio import AsyncSession
from module_admin.dao.user_dao import UserDao
from module_admin.entity.vo.user_vo import UserModel
from exceptions.exception import ServiceException


class UserService:
    """
    用户管理服务
    """

    @classmethod
    async def get_user_list_services(cls, query_db: AsyncSession, user_page_query: UserPageQueryModel):
        """
        获取用户列表服务

        :param query_db: 数据库会话
        :param user_page_query: 查询参数
        :return: 用户列表
        """
        user_list_result = await UserDao.get_user_list(query_db, user_page_query)

        return user_list_result

    @classmethod
    async def add_user_services(cls, request: Request, query_db: AsyncSession, user: UserModel):
        """
        新增用户服务

        :param request: Request 对象
        :param query_db: 数据库会话
        :param user: 用户对象
        :return: 新增用户校验结果
        """
        if await cls.check_user_name_unique_services(query_db, user):
            raise ServiceException(message=f'新增用户{user.user_name}失败，登录账号已存在')
        else:
            try:
                await UserDao.add_user_dao(query_db, user)
                await query_db.commit()
            except Exception as e:
                await query_db.rollback()
                raise e
```

### DAO 结构

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from module_admin.entity.do.user_do import SysUser
from module_admin.entity.vo.user_vo import UserModel, UserPageQueryModel


class UserDao:
    """
    用户管理 DAO
    """

    @classmethod
    async def get_user_list(cls, query_db: AsyncSession, user_page_query: UserPageQueryModel):
        """
        获取用户列表

        :param query_db: 数据库会话
        :param user_page_query: 查询参数
        :return: 用户列表
        """
        query = select(SysUser)

        if user_page_query.user_name:
            query = query.where(SysUser.user_name.like(f'%{user_page_query.user_name}%'))

        if user_page_query.status:
            query = query.where(SysUser.status == user_page_query.status)

        if user_page_query.dept_id:
            query = query.where(SysUser.dept_id == user_page_query.dept_id)

        if user_page_query.begin_time:
            query = query.where(SysUser.create_time >= user_page_query.begin_time)

        if user_page_query.end_time:
            query = query.where(SysUser.create_time <= user_page_query.end_time)

        user_list = await query_db.execute(query)
        return user_list.scalars().all()

    @classmethod
    async def add_user_dao(cls, query_db: AsyncSession, user: UserModel):
        """
        新增用户

        :param query_db: 数据库会话
        :param user: 用户对象
        :return: 新增结果
        """
        user_do = SysUser(**user.model_dump())
        query_db.add(user_do)
        await query_db.flush()
        return user_do
```

### VO 结构

```python
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import List, Literal, Optional


class UserModel(BaseModel):
    """
    用户表对应 pydantic 模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    user_id: Optional[int] = Field(default=None, description='用户ID')
    dept_id: Optional[int] = Field(default=None, description='部门ID')
    user_name: Optional[str] = Field(default=None, description='用户账号')
    nick_name: Optional[str] = Field(default=None, description='用户昵称')
    user_type: Optional[str] = Field(default=None, description='用户类型（00系统用户）')
    email: Optional[str] = Field(default=None, description='用户邮箱')
    phonenumber: Optional[str] = Field(default=None, description='手机号码')
    sex: Optional[Literal['0', '1', '2']] = Field(default=None, description='用户性别（0男 1女 2未知）')
    avatar: Optional[str] = Field(default=None, description='头像地址')
    password: Optional[str] = Field(default=None, description='密码')
    status: Optional[Literal['0', '1']] = Field(default=None, description='帐号状态（0正常 1停用）')
    del_flag: Optional[Literal['0', '2']] = Field(default=None, description='删除标志（0代表存在 2代表删除）')
    login_ip: Optional[str] = Field(default=None, description='最后登录IP')
    login_date: Optional[datetime] = Field(default=None, description='最后登录时间')
    pwd_update_date: Optional[datetime] = Field(default=None, description='密码最后更新时间')
    create_by: Optional[str] = Field(default=None, description='创建者')
    create_time: Optional[datetime] = Field(default=None, description='创建时间')
    update_by: Optional[str] = Field(default=None, description='更新者')
    update_time: Optional[datetime] = Field(default=None, description='更新时间')
    remark: Optional[str] = Field(default=None, description='备注')
    admin: Optional[bool] = Field(default=False, description='是否为admin')


class UserPageQueryModel(UserModel):
    """
    用户分页查询模型
    """

    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')
    begin_time: Optional[str] = Field(default=None, description='开始时间')
    end_time: Optional[str] = Field(default=None, description='结束时间')
```

### DO 结构

```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime


Base = declarative_base()


class SysUser(Base):
    """
    用户表
    """

    __tablename__ = 'sys_user'

    user_id = Column(Integer, primary_key=True, autoincrement=True, comment='用户ID')
    dept_id = Column(Integer, comment='部门ID')
    user_name = Column(String(30), comment='用户账号')
    nick_name = Column(String(30), comment='用户昵称')
    user_type = Column(String(2), default='00', comment='用户类型（00系统用户）')
    email = Column(String(50), comment='用户邮箱')
    phonenumber = Column(String(11), comment='手机号码')
    sex = Column(String(1), comment='用户性别（0男 1女 2未知）')
    avatar = Column(String(100), comment='头像地址')
    password = Column(String(100), comment='密码')
    status = Column(String(1), default='0', comment='帐号状态（0正常 1停用）')
    del_flag = Column(String(1), default='0', comment='删除标志（0代表存在 2代表删除）')
    login_ip = Column(String(128), comment='最后登录IP')
    login_date = Column(DateTime, comment='最后登录时间')
    pwd_update_date = Column(DateTime, comment='密码最后更新时间')
    create_by = Column(String(64), comment='创建者')
    create_time = Column(DateTime, comment='创建时间')
    update_by = Column(String(64), comment='更新者')
    update_time = Column(DateTime, comment='更新时间')
    remark = Column(String(500), comment='备注')
```
