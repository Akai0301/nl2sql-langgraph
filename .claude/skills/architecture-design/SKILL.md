---
name: architecture-design
description: |
  系统架构设计、模块划分、代码重构、技术栈选型。核心内容：三层架构规范、业务模块划分、表设计规范、技术栈优先级决策。

  触发场景：
  - 系统整体架构设计
  - 新业务模块的模块划分与结构规划
  - 代码分层与重构策略
  - 依赖关系梳理与解耦
  - 架构演进路径建议（从单体到微服务）
  - 领域边界划分与包结构设计
  - 技术栈选型与方案决策

  触发词：架构设计、模块划分、三层架构、分层、领域划分、重构、解耦、依赖管理、系统设计、代码组织、技术栈、架构演进

  注意：
  1. 具体技术对比（Redis vs 本地缓存）→ 使用 tech-decision
  2. 开发具体 CRUD 模块 → 使用 crud-development
  3. 数据库建表与字典配置 → 使用 database-ops
  4. 本项目是纯后端项目（无前端代码）
---

# 架构设计指南

## 本项目技术栈

### 核心技术架构

| 层级 | 技术栈 | 版本 | 说明 |
|------|--------|------|------|
| **后端框架** | FastAPI | 0.116.1 | 核心框架 |
| **开发语言** | Python | 3.9+ | LTS 版本 |
| **ORM** | SQLAlchemy | 2.0.43 | 持久层框架（异步） |
| **安全** | PyJWT | 2.10.1 | 认证授权 |
| **数据库** | MySQL 8.0+ | 8.0+ | 主数据库（支持多库） |
| **缓存** | Redis | 6.4.0 | 分布式缓存 |
| **任务调度** | APScheduler | 3.11.0 | 定时任务 |
| **工具库** | loguru | 0.7.3 | 日志工具 |
| **密码加密** | passlib | 1.7.4 | 密码哈希 |

**注：** 本项目是纯后端项目，前端项目独立维护。

### 扩展技术栈（按优先级）

#### 1️⃣ 高优先级技术（优先选择）

| 技术 | 优先级 | 使用场景 | 说明 |
|------|--------|---------|------|
| **Redis** | ⭐⭐⭐⭐⭐ | 缓存、分布式锁、会话管理 | 优先选择（已集成） |
| **WebSocket** | ⭐⭐⭐⭐⭐ | 实时推送、在线聊天、消息通知 | 实时通信首选（已集成） |
| **PyJWT** | ⭐⭐⭐⭐⭐ | 权限控制、登录认证、Token管理 | 项目安全核心 |
| **SQLAlchemy** | ⭐⭐⭐⭐⭐ | ORM、CRUD | 项目数据访问核心（异步） |
| **FastAPI** | ⭐⭐⭐⭐⭐ | Web 框架、API 路由 | 项目核心框架 |
| **APScheduler** | ⭐⭐⭐⭐ | 定时任务、复杂调度 | 项目定时任务框架（已集成） |

#### 2️⃣ 中优先级技术（按需使用）

| 技术 | 优先级 | 使用场景 | 说明 |
|------|--------|---------|------|
| **SSE** | ⭐⭐⭐⭐ | 服务端推送、单向消息 | 实时通知场景（已集成） |
| **openpyxl** | ⭐⭐⭐⭐ | Excel 导入导出 | Excel 处理（已集成） |
| **pandas** | ⭐⭐⭐ | 数据处理、数据分析 | 数据处理（已集成） |
| **Pillow** | ⭐⭐⭐ | 图片处理 | 图片操作（已集成） |
| **psutil** | ⭐⭐⭐ | 系统监控 | 系统资源监控（已集成） |

#### 3️⃣ 扩展能力（按需集成）

| 技术 | 优先级 | 使用场景 | 集成状态 |
|------|--------|---------|---------|
| **数据加密** | ⭐⭐⭐⭐ | 敏感数据加密、字段级加密 | ✅ 已集成 |
| **数据脱敏** | ⭐⭐⭐⭐ | 身份证、手机号脱敏 | ✅ 已集成 |
| **防重复提交** | ⭐⭐⭐⭐ | 表单防重复、API 幂等 | ✅ 已集成 |
| **国际化翻译** | ⭐⭐⭐ | 多语言支持 | ✅ 已集成 |
| **审计日志** | ⭐⭐⭐ | 操作日志、变更追溯 | ✅ 已集成 |
| **接口限流** | ⭐⭐⭐ | 接口频率限制、防滥用 | ✅ 已集成 |

#### 4️⃣ 需自行扩展的技术

| 技术 | 使用场景 | 说明 |
|------|---------|------|
| **Celery** | 高吞吐消息队列、分布式任务 | 高并发场景可自行引入 |
| **MQTT** | 物联网设备通信 | IoT 场景可使用 paho-mqtt |
| **LangChain** | AI 大模型集成 | AI 业务可自行集成 |

### 技术选型决策树

```
需要实时通信？
├─ 是 → WebSocket（首选，已集成）
└─ 否 → 需要消息队列？
         ├─ 是 → Redis Streams（优先，轻量级）
         │       或 Celery（自行引入，高吞吐）
         └─ 否 → 需要定时任务？
                ├─ 是 → APScheduler（已集成）
                └─ 否 → 需要缓存？
                       └─ 是 → Redis（首选，已集成）
```

---

## 本项目架构

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        客户端                                │
├──────────────────┬──────────────────┬───────────────────────┤
│     PC Web       │     小程序        │         App           │
│   (独立项目)      │   (独立项目)      │     (独立项目)         │
└────────┬─────────┴────────┬─────────┴───────────┬───────────┘
         │                  │                     │
         └──────────────────┼─────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      API 网关 (可选)                          │
│                   Nginx / API Gateway                       │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      后端服务                                │
│           FastAPI Application (uvicorn)                      │
├─────────────────────────────────────────────────────────────┤
│  ┌────────────┐ ┌────────────┐ ┌──────────────┐ ┌────────────┐│
│  │module_admin│ │module_xxx  │ │module_yyy    │ │module_zzz  ││
│  │  系统管理   │ │  业务模块   │ │   业务模块    │ │  业务模块   ││
│  │  (sys_*)   │ │ (xxx_*)    │ │   (yyy_*)    │ │  (zzz_*)   ││
│  └────────────┘ └────────────┘ └──────────────┘ └────────────┘│
├─────────────────────────────────────────────────────────────┤
│                    utils (工具类)                            │
│ response_util/page_util/pwd_util/upload_util/excel_util    │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      数据与存储层                             │
├──────────┬──────────┬──────────┬──────────────────────────────┤
│  MySQL   │  Redis   │   OSS    │   可选扩展中间件              │
│ (主数据)  │  (缓存)  │ (文件)   │  (Celery/MQTT/APScheduler)  │
└──────────┴──────────┴──────────┴──────────────────────────────┘
```

### 🔴 后端三层架构（本项目核心）

本项目采用 **三层架构**：Controller (路由) → Service (服务层) → DAO (数据访问层)

```
┌──────────────────────────────────────────────────────────────┐
│                    Controller 层 (路由)                      │
│     • 接收 HTTP 请求、参数校验、返回 ResponseUtil 响应       │
│     • 路由：/list, /{id}, /, /, /{ids}, /export            │
│     • 使用 FastAPI 装饰器 (@get, @post, @put, @delete)      │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                      Service 层                              │
│     • 业务逻辑处理、事务管理、编排协调                        │
│     • 数据权限构建 (GetDataScope)                            │
│     • 使用 SQLAlchemy 异步查询                               │
│     • 调用 DAO 层进行数据访问                                │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                      DAO 层                                  │
│     • 使用 SQLAlchemy ORM 映射、SQL 执行                      │
│     • 异步数据库操作 (AsyncSession)                          │
└──────────────────────────────────────────────────────────────┘
```

**为什么是三层？**
- **Controller 层**：负责路由定义、请求参数验证、响应格式统一
- **Service 层**：负责业务逻辑处理、数据权限控制、事务管理
- **DAO 层**：负责数据访问、SQL 执行、ORM 映射

---

## 架构设计原则

### 1. 单一职责

```python
# ✅ 好的设计：每个类只负责一件事
class OrderService:
    # 只处理订单业务
    pass

class PaymentService:
    # 只处理支付业务
    pass

# ❌ 不好的设计：一个类做太多事
class OrderService:
    # 订单 + 支付 + 物流 + 通知...
    pass
```

### 2. 开闭原则

```python
# ✅ 好的设计：对扩展开放，对修改关闭
from abc import ABC, abstractmethod

class PaymentStrategy(ABC):
    @abstractmethod
    def pay(self, order):
        pass

class WechatPayment(PaymentStrategy):
    def pay(self, order):
        # 微信支付逻辑
        pass

class AlipayPayment(PaymentStrategy):
    def pay(self, order):
        # 支付宝支付逻辑
        pass

# 新增支付方式只需新增实现类

# ❌ 不好的设计：新增功能需要修改原有代码
def pay(order, payment_type):
    if payment_type == "wechat":
        # 微信支付
        pass
    elif payment_type == "alipay":
        # 支付宝支付
        pass
    # 新增支付方式需要修改这里
```

### 3. 依赖倒置

```python
# ✅ 好的设计：依赖抽象而非具体实现
class OrderService:
    def __init__(self, payment_service: PaymentStrategy):
        self.payment_service = payment_service  # 依赖抽象

# ❌ 不好的设计：直接依赖具体实现
class OrderService:
    def __init__(self):
        self.payment_service = WechatPayment()  # 依赖具体类
```

---

## 模块划分与表前缀规范

### 核心约束（必须遵守）

**模块路径必须是 `module_xxx/`**

### 标准模块与表前缀对应

| 模块 | 目录路径 | 包路径 | 表前缀 | 用途 |
|------|---------|--------|--------|------|
| **系统管理** | `module_admin/` | `module_admin` | `sys_` | 系统管理功能 |

### 业务模块扩展（按业务领域）

创建新业务模块时，遵循以下规范：

| 业务领域 | 新模块命名 | 包路径 | 表前缀 |
|---------|----------|--------|--------|
| **基础业务** | `module_xxx/` | `module_xxx` | `xxx_` |
| **商城业务** | `module_mall/` | `module_mall` | `m_` |
| **物联网** | `module_iot/` | `module_iot` | `iot_` |

### 关键设计原则

**1. 表前缀与模块一一对应**
```
✅ 正确：sys_user 表 → module_admin 模块
❌ 错误：sys_user 表 → module_demo 模块（前缀与模块不符）
```

**2. Python 类名不带前缀**
```python
# ✅ 正确
class User(Base):
    __tablename__ = 'sys_user'  # 表名带前缀
    # 类名不带 sys 前缀

class TestDemo(Base):
    __tablename__ = 'test_demo'  # 表名带前缀
    # 类名不带 test 前缀
```

**3. 所有业务表继承基类**
```python
# ✅ 正确：支持多租户
from sqlalchemy import Column, BigInteger, DateTime, String
from datetime import datetime

class BaseModel:
    # 基类提供：tenant_id, create_dept, create_by, create_time, update_by, update_time
    tenant_id = Column(String(20), default='000000', comment='租户ID')
    create_dept = Column(BigInteger, comment='创建部门')
    create_by = Column(String(64), nullable=True, server_default="'", comment='创建者')
    create_time = Column(DateTime, default=datetime.now, comment='创建时间')
    update_by = Column(String(64), nullable=True, server_default="'", comment='更新者')
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    del_flag = Column(String(1), default='0', comment='删除标志(0正常 1已删除)')

class Order(BaseModel):
    # 子类需自行定义：
    id = Column(BigInteger, primary_key=True, comment='主键ID')
    # 其他业务字段...
```

**4. 主键使用自增 ID**
```python
# ✅ 正确：使用自增主键
id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')

# ❌ 错误：SQL 中使用雪花 ID（本项目使用自增）
# id BIGINT NOT NULL COMMENT '主键ID'  -- 禁止！本项目用自增ID
```

### 🔴 模块内部结构规范（三层架构）

以 `User` 表为例：

```
module_admin/
├── controller/
│   └── user_controller.py          # APIRouter 路由
├── service/
│   └── user_service.py             # 业务逻辑层
├── dao/
│   └── user_dao.py                 # 数据访问层
├── entity/
│   ├── do/
│   │   └── user_do.py              # 数据对象 (DO)
│   └── vo/
│       └── user_vo.py              # 视图对象 (VO)
├── annotation/
│   ├── log_annotation.py           # 日志装饰器
│   └── pydantic_annotation.py      # 参数验证装饰器
└── aspect/
    ├── data_scope.py               # 数据权限切面
    └── interface_auth.py           # 接口权限切面
```

**Controller 实现示例（路由层）：**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from config.get_db import get_db
from module_admin.service.user_service import UserService
from module_admin.entity.vo.user_vo import UserPageQueryModel
from utils.response_util import ResponseUtil
from utils.page_util import PageResponseModel

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
    # 获取分页数据
    user_page_query_result = await UserService.get_user_list_services(
        query_db, user_page_query, data_scope_sql, is_page=True
    )
    return ResponseUtil.success(model_content=user_page_query_result)
```

**Service 实现示例（服务层）：**

```python
class UserService:
    """
    用户管理模块服务层
    """

    @classmethod
    async def get_user_list_services(
        cls, query_db: AsyncSession, query_object: UserPageQueryModel, data_scope_sql: str, is_page: bool = False
    ):
        """
        获取用户列表信息service

        :param query_db: orm对象
        :param query_object: 查询参数对象
        :param data_scope_sql: 数据权限对应的查询sql语句
        :param is_page: 是否开启分页
        :return: 用户列表信息对象
        """
        query_result = await UserDao.get_user_list(query_db, query_object, data_scope_sql, is_page)
        if is_page:
            user_list_result = PageResponseModel(
                **{
                    **query_result.model_dump(by_alias=True),
                    'rows': [{**row[0], 'dept': row[1]} for row in query_result.rows],
                }
            )
        else:
            user_list_result = []
            if query_result:
                user_list_result = [{**row[0], 'dept': row[1]} for row in query_result]

        return user_list_result
```

**DAO 实现示例（数据访问层）：**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from module_admin.entity.do.user_do import User

class UserDao:
    """
    用户管理模块数据访问层
    """

    @classmethod
    async def get_user_list(
        cls, query_db: AsyncSession, query_object: UserPageQueryModel, data_scope_sql: str, is_page: bool = False
    ):
        """
        获取用户列表信息dao

        :param query_db: orm对象
        :param query_object: 查询参数对象
        :param data_scope_sql: 数据权限对应的查询sql语句
        :param is_page: 是否开启分页
        :return: 用户列表信息对象
        """
        query = (
            select(User, Dept)
            .outerjoin(Dept, and_(User.dept_id == Dept.dept_id, Dept.status == '0'))
            .where(
                User.del_flag == '0',
                User.status == '0',
            )
        )
        # 添加查询条件
        if query_object.user_name:
            query = query.where(User.user_name.like(f'%{query_object.user_name}%'))
        if query_object.phonenumber:
            query = query.where(User.phonenumber.like(f'%{query_object.phonenumber}%'))
        if query_object.status:
            query = query.where(User.status == query_object.status)
        if query_object.dept_id:
            query = query.where(User.dept_id == query_object.dept_id)
        if query_object.begin_time and query_object.end_time:
            query = query.where(
                User.create_time.between(query_object.begin_time, query_object.end_time)
            )
        # 添加数据权限
        if data_scope_sql:
            query = query.where(text(data_scope_sql))
        
        # 执行查询
        if is_page:
            # 分页查询
            result = await paginate(query_db, query)
        else:
            # 不分页查询
            result = await query_db.execute(query)
            result = result.all()
        
        return result
```

### 表设计规范

#### 建表模板（MySQL）

```sql
CREATE TABLE xxx_table (
    -- 主键（自增 ID）
    id              BIGINT(20)    NOT NULL AUTO_INCREMENT COMMENT '主键ID',

    -- 多租户字段（必须）
    tenant_id       VARCHAR(20)   DEFAULT '000000' COMMENT '租户ID',

    -- 业务字段
    xxx_name        VARCHAR(100)  NOT NULL COMMENT '名称',
    status          CHAR(1)       DEFAULT '0' COMMENT '状态',
    remark          VARCHAR(500)  DEFAULT NULL COMMENT '备注',

    -- 审计字段（必须）
    create_dept     BIGINT(20)    DEFAULT NULL COMMENT '创建部门',
    create_by       BIGINT(20)    DEFAULT NULL COMMENT '创建人',
    create_time     DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_by       BIGINT(20)    DEFAULT NULL COMMENT '更新人',
    update_time     DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    -- 逻辑删除
    del_flag        CHAR(1)       DEFAULT '0' COMMENT '删除标志(0正常 1已删除)',

    PRIMARY KEY (id),
    INDEX idx_tenant_id (tenant_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='xxx表';
```

**建表注意事项：**
- 表前缀与模块必须对应
- 必须包含 `tenant_id`（支持多租户）
- 必须包含审计字段
- 必须包含逻辑删除字段（`del_flag`）
- 主键使用 `AUTO_INCREMENT`（本项目使用自增 ID）
- 添加必要的索引

#### 多数据库支持

| 数据库 | SQL 文件位置 |
|--------|------------|
| MySQL | `script/sql/ry_vue_fastapi.sql` |
| PostgreSQL | `script/sql/postgres/` |

---

## 实战架构案例

### 案例 1：订单系统架构

**需求：** 电商订单创建、支付、发货

**模块划分：**
```
module_mall/
├── order/              # 订单模块（m_order）
├── goods/              # 商品模块（m_goods）
└── payment/            # 支付模块（m_payment）
```

**包路径规范：**
```
module_mall.controller.order_controller.OrderController
module_mall.service.order_service.OrderService
module_mall.dao.order_dao.OrderDao
module_mall.entity.do.order_do.Order
module_mall.entity.vo.order_vo.OrderVO
```

**技术选型：**
```
├── 数据存储
│   ├── MySQL（订单主数据）
│   ├── Redis（库存缓存、分布式锁）
│   └── OSS（发票、物流单图片）
├── 消息通信
│   ├── WebSocket（订单状态实时推送）
│   └── Redis Streams（订单异步处理）
└── 定时任务
    ├── APScheduler（对账任务）
```

**代码结构示例：**

```python
# module_mall/controller/order_controller.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from config.get_db import get_db
from module_mall.service.order_service import OrderService
from module_mall.entity.vo.order_vo import OrderPageQueryModel
from utils.response_util import ResponseUtil
from utils.page_util import PageResponseModel

orderController = APIRouter(prefix='/mall/order', dependencies=[Depends(LoginService.get_current_user)])

@orderController.get(
    '/list',
    response_model=PageResponseModel,
    dependencies=[Depends(CheckUserInterfaceAuth('mall:order:list'))]
)
async def get_order_list(
    request: Request,
    order_page_query: OrderPageQueryModel = Depends(OrderPageQueryModel.as_query),
    query_db: AsyncSession = Depends(get_db),
    data_scope_sql: str = Depends(GetDataScope('MallOrder')),
):
    order_page_query_result = await OrderService.get_order_list_services(
        query_db, order_page_query, data_scope_sql, is_page=True
    )
    return ResponseUtil.success(model_content=order_page_query_result)
```

---

## 架构演进路径

### 从单体到微服务

**当前阶段：单体应用**
```
FastAPI Application
├── module_admin (系统管理)
├── module_mall (商城业务)
└── module_iot (物联网)
```

**演进阶段 1：模块化拆分**
```
FastAPI Application (主应用)
├── 系统管理模块 (独立服务)
├── 商城业务模块 (独立服务)
└── 物联网模块 (独立服务)
```

**演进阶段 2：微服务化**
```
API Gateway
├── 系统管理服务
├── 商城业务服务
├── 物联网服务
└── 通用服务 (认证、配置、监控)
```

### 演进建议

1. **初期（0-1年）**：保持单体架构，通过模块划分实现业务隔离
2. **中期（1-3年）**：根据业务复杂度，逐步拆分独立服务
3. **后期（3年以上）**：全面微服务化，引入服务治理

---

## 常见架构问题与解决方案

### 1. 循环依赖

**问题：** 模块之间相互依赖，导致无法启动

**解决方案：**
- 提取公共模块到 `utils/` 或 `common/`
- 使用依赖注入（FastAPI 的 Depends）
- 重构代码，减少模块间耦合

### 2. 数据权限控制

**问题：** 不同用户只能看到自己的数据

**解决方案：**
- 使用 `GetDataScope` 切面自动添加数据权限 SQL
- 在 Service 层调用 DAO 时传入 `data_scope_sql`
- 在 DAO 层使用 `text(data_scope_sql)` 添加查询条件

### 3. 接口权限控制

**问题：** 不同用户只能访问特定接口

**解决方案：**
- 使用 `CheckUserInterfaceAuth` 装饰器进行权限检查
- 在路由定义时添加 `dependencies=[Depends(CheckUserInterfaceAuth('权限标识'))]`
- 权限标识格式：`模块:功能:操作`（如 `system:user:list`）

### 4. 事务管理

**问题：** 多个数据库操作需要保证原子性

**解决方案：**
- 使用 SQLAlchemy 的 `AsyncSession` 进行事务管理
- 在 Service 层使用 `async with query_db.begin():` 开启事务
- 异常时自动回滚，成功时自动提交

---

## 注意事项

1. **本项目是纯后端项目**，前端代码独立维护
2. **所有 API 响应必须使用 `ResponseUtil`**，确保响应格式统一
3. **分页查询必须返回 `PageResponseModel`**，包含 rows、total、pageNum、pageSize
4. **数据库操作必须使用异步方式**，使用 `AsyncSession` 和 `await`
5. **所有业务表必须包含审计字段**：tenant_id、create_dept、create_by、create_time、update_by、update_time、del_flag
6. **主键使用自增 ID**，不使用雪花 ID
7. **表前缀与模块必须对应**，确保代码组织清晰
8. **三层架构必须严格遵守**：Controller → Service → DAO
9. **权限控制必须使用装饰器**：`CheckUserInterfaceAuth` 和 `GetDataScope`
10. **日志记录必须使用 `@Log` 装饰器**，记录关键操作

---

## 相关技能

- **crud-development**：CRUD 开发规范
- **api-development**：API 开发规范
- **database-ops**：数据库操作规范
- **security-guard**：安全权限控制
- **data-permission**：数据权限控制
- **tech-decision**：技术选型决策
