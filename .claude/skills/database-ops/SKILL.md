---
name: database-ops
description: |
  数据库操作规范。包含建表模板、DO 实体类模板、八大数据库设计模式、多数据库兼容。

  触发场景：
  - 创建数据库表（MySQL/PostgreSQL）
  - 设计 DO 实体类（Base、del_flag、审计字段）
  - 配置逻辑删除、审计字段
  - 树结构表设计（祖先路径法/父子法）
  - 字典数据和菜单 SQL 配置

  触发词：数据库、SQL、建表、CREATE TABLE、DO、Base、del_flag、逻辑删除、字典、菜单SQL、表设计、字段设计、数据库设计
---

# 数据库操作规范（CodeAI 三层架构版）

> **⚠️ 重要声明**: 本项目是 **CodeAI 纯后端项目**，采用三层架构！
> 本文档规范基于 **SysUser** 和 **SysDept** 模块的真实实现。

## 核心架构特征

| 对比项 | 本项目 (CodeAI) |
|--------|--------------------------|
| **模块命名** | `module_*` |
| **架构** | 三层：Controller → Service → DAO → Database |
| **DO 基类** | `Base`（来自 `config.database`） |
| **主键策略** | 自增 ID（`autoincrement=True`） |
| **逻辑删除** | `del_flag CHAR(1)`（'0'=存在，'2'=删除） |
| **对象转换** | `model_dump()` |
| **表前缀** | 按模块区分：sys_/demo_/ 等 |

---

## 1. DO 数据库对象模板（带逻辑删除）

```python
from datetime import datetime
from sqlalchemy import BigInteger, CHAR, Column, DateTime, String
from config.database import Base


class DemoXxx(Base):
    """
    XXX 对象
    """

    __tablename__ = 'demo_xxx'
    __table_args__ = {'comment': 'XXX表'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='主键 ID')
    xxx_name = Column(String(100), nullable=False, comment='名称')
    status = Column(CHAR(1), nullable=True, server_default='0', comment='状态（0正常 1停用）')
    del_flag = Column(CHAR(1), nullable=True, server_default='0', comment='删除标志（0代表存在 2代表删除）')
    create_by = Column(String(64), nullable=True, server_default="'", comment='创建者')
    create_time = Column(DateTime, nullable=True, comment='创建时间', default=datetime.now())
    update_by = Column(String(64), nullable=True, server_default="'", comment='更新者')
    update_time = Column(DateTime, nullable=True, comment='更新时间', default=datetime.now())
```

---

## 2. MySQL CREATE TABLE 模板

```sql
CREATE TABLE `demo_xxx` (
    -- 主键
    `id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '主键 ID',

    -- 业务字段
    `xxx_name` VARCHAR(100) NOT NULL COMMENT '名称',
    `status` CHAR(1) DEFAULT '0' COMMENT '状态(0正常 1停用)',

    -- 删除标志
    `del_flag` CHAR(1) DEFAULT '0' COMMENT '删除标志(0代表存在 2代表删除)',

    -- 审计字段（必须）
    `create_by` VARCHAR(64) DEFAULT '' COMMENT '创建者',
    `create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_by` VARCHAR(64) DEFAULT '' COMMENT '更新者',
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `remark` VARCHAR(500) DEFAULT NULL COMMENT '备注',

    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='XXX表';
```

---

## 3. PostgreSQL CREATE TABLE 模板

```sql
CREATE TABLE demo_xxx (
    -- 主键
    id BIGSERIAL NOT NULL,

    -- 业务字段
    xxx_name VARCHAR(100) NOT NULL,
    status CHAR(1) DEFAULT '0',

    -- 删除标志
    del_flag CHAR(1) DEFAULT '0',

    -- 审计字段
    create_by VARCHAR(64) DEFAULT '',
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_by VARCHAR(64) DEFAULT '',
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    remark VARCHAR(500) DEFAULT NULL,

    PRIMARY KEY (id)
);

COMMENT ON TABLE demo_xxx IS 'XXX表';
COMMENT ON COLUMN demo_xxx.id IS '主键 ID';
COMMENT ON COLUMN demo_xxx.xxx_name IS '名称';
COMMENT ON COLUMN demo_xxx.del_flag IS '删除标志(0代表存在 2代表删除)';
```

---

## 4. 八大数据库设计模式

### 模式一：树结构 - 祖先路径法（推荐）

```sql
CREATE TABLE demo_tree (
    id BIGINT(20) NOT NULL AUTO_INCREMENT,
    parent_id BIGINT(20) DEFAULT 0,
    ancestors VARCHAR(500) DEFAULT '',  -- 祖先路径：0,1,2,3
    name VARCHAR(100) NOT NULL,
    del_flag CHAR(1) DEFAULT '0',
    create_by VARCHAR(64) DEFAULT '',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_by VARCHAR(64) DEFAULT '',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_ancestors (ancestors)
) ENGINE=InnoDB COMMENT='树形表';
```

**优势**：快速查询所有祖先和子孙节点（无需递归）

**DO 示例**：
```python
from sqlalchemy import BigInteger, Column, Integer, String
from config.database import Base


class DemoTree(Base):
    __tablename__ = 'demo_tree'
    __table_args__ = {'comment': '树形表'}

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键 ID')
    parent_id = Column(BigInteger, server_default='0', comment='父节点 ID')
    ancestors = Column(String(500), server_default="'", comment='祖级列表')
    name = Column(String(100), nullable=False, comment='节点名称')
    del_flag = Column(CHAR(1), server_default='0', comment='删除标志')
```

---

### 模式二：树结构 - 简单父子法

```sql
CREATE TABLE demo_tree_simple (
    id BIGINT(20) NOT NULL AUTO_INCREMENT,
    parent_id BIGINT(20) DEFAULT 0,
    name VARCHAR(100) NOT NULL,
    del_flag CHAR(1) DEFAULT '0',
    create_by VARCHAR(64) DEFAULT '',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_by VARCHAR(64) DEFAULT '',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB COMMENT='简单树形表';
```

**适用**：二级分类、简单层级

---

### 模式三：软删除（逻辑删除）

```python
# DO 中定义
del_flag = Column(CHAR(1), nullable=True, server_default='0', comment='删除标志（0代表存在 2代表删除）')

# SQL 查询时过滤
query = select(DemoXxx).where(DemoXxx.del_flag == '0')

# 删除时更新标志
update_stmt = update(DemoXxx).where(DemoXxx.id == xxx_id).values(del_flag='2')
```

**优势**：数据可恢复，审计日志完整

---

### 模式四：审计追踪（自动填充）

```python
from datetime import datetime


class DemoAudit(Base):
    __tablename__ = 'demo_audit'
    __table_args__ = {'comment': '带审计的表'}

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键 ID')
    
    # 审计字段（必须）
    create_by = Column(String(64), server_default="'", comment='创建者')
    create_time = Column(DateTime, default=datetime.now(), comment='创建时间')
    update_by = Column(String(64), server_default="'", comment='更新者')
    update_time = Column(DateTime, default=datetime.now(), comment='更新时间')
```

**注意**：在 Service 层手动设置 `create_by`、`update_by`、`create_time`、`update_time`

---

### 模式五：状态字段（字典驱动）

```python
status = Column(CHAR(1), server_default='0', comment='状态（0正常 1停用）')
```

**配合字典表**：不硬编码状态值，支持动态扩展

---

### 模式六：数据权限控制

```python
# DO 中包含数据权限字段
dept_id = Column(BigInteger, nullable=True, comment='部门 ID')
user_id = Column(BigInteger, nullable=True, comment='用户 ID')

# Controller 中使用 GetDataScope 依赖
data_scope_sql: str = Depends(GetDataScope('DemoXxx'))

# DAO 中执行数据权限
query = select(DemoXxx).where(DemoXxx.del_flag == '0', eval(data_scope_sql))
```

**权限类型**（通过 `sys_role.data_scope` 配置）：
- 1=全部数据权限、2=自定义数据权限、3=本部门数据权限
- 4=本部门及以下数据权限、5=仅本人数据权限

---

### 模式七：关联表（多对多）

```sql
CREATE TABLE demo_xxx_role (
    xxx_id BIGINT(20) NOT NULL COMMENT 'XXX ID',
    role_id BIGINT(20) NOT NULL COMMENT '角色 ID',
    PRIMARY KEY (xxx_id, role_id)
) ENGINE=InnoDB COMMENT='XXX和角色关联表';
```

**DO 示例**：
```python
class DemoXxxRole(Base):
    __tablename__ = 'demo_xxx_role'
    __table_args__ = {'comment': 'XXX和角色关联表'}

    xxx_id = Column(BigInteger, primary_key=True, nullable=False, comment='XXX ID')
    role_id = Column(BigInteger, primary_key=True, nullable=False, comment='角色 ID')
```

---

### 模式八：跨数据库兼容

| 场景 | MySQL | PostgreSQL |
|------|-------|-----------|
| 主键自增 | `AUTO_INCREMENT` | `BIGSERIAL` |
| 默认值 | `DEFAULT '0'` | `DEFAULT '0'` |
| 日期函数 | `CURRENT_TIMESTAMP` | `CURRENT_TIMESTAMP` |
| NULL 默认值 | `DEFAULT NULL` | `DEFAULT NULL` |

**SQLAlchemy 工具**：
```python
from utils.common_util import SqlalchemyUtil
from config.env import DataBaseConfig

# 跨数据库兼容的 NULL 默认值
server_default=SqlalchemyUtil.get_server_default_null(DataBaseConfig.db_type, False)
```

---

## 5. 模块表前缀参考

| 模块 | 前缀 | 模块路径 | 示例表 |
|------|------|---------|---------|
| admin | `sys_` | `module_admin/` | sys_user, sys_menu |
| generator | `gen_` | `module_generator/` | gen_table, gen_column |
| 自定义 | 自定义 | `module_xxx/` | demo_xxx |

---

## 6. 常见错误对比

### ❌ 不要做

```sql
-- 错误1: 使用 TINYINT 存储删除标志
del_flag TINYINT(1)  -- ❌ 应该用 CHAR(1)

-- 错误2: 软删除字段缺少注释
del_flag CHAR(1)  -- ❌ 应添加注释说明用途

-- 错误3: 缺少审计字段
CREATE TABLE xxx (id BIGINT)  -- ❌ 缺少 create_by, update_by 等

-- 错误4: 字段名不规范
userName VARCHAR(50)  -- ❌ 应该是 user_name

-- 错误5: 使用雪花 ID 而非自增
id BIGINT(20) NOT NULL  -- ❌ 应该使用 AUTO_INCREMENT
```

### ✅ 正确做法

```sql
-- 正确1: 使用 CHAR(1) 存储删除标志
del_flag CHAR(1) DEFAULT '0' COMMENT '删除标志(0代表存在 2代表删除)'

-- 正确2: 添加完整注释
del_flag CHAR(1) DEFAULT '0' COMMENT '删除标志(0代表存在 2代表删除)'

-- 正确3: 包含所有审计字段
CREATE TABLE xxx (
    create_by VARCHAR(64) DEFAULT '' COMMENT '创建者',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_by VARCHAR(64) DEFAULT '' COMMENT '更新者',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
)

-- 正确4: 字段名使用蛇形命名法
user_name VARCHAR(50)

-- 正确5: 使用自增 ID
id BIGINT(20) NOT NULL AUTO_INCREMENT
```

---

## 7. 检查清单

生成表前必须检查：

- [ ] **主键是否是 BIGINT(20) AUTO_INCREMENT？**
- [ ] **是否有 del_flag CHAR(1) 字段？**（逻辑删除）
- [ ] **是否有完整的审计字段？**（create_by, create_time, update_by, update_time）
- [ ] **字段名是否全部使用蛇形命名法？**（xxx_name 而非 xxxName）
- [ ] **所有字段是否有注释？**
- [ ] **DO 是否继承 Base？**
- [ ] **DO 中 del_flag 类型是否是 CHAR(1)？**
- [ ] **DO 中主键是否使用 autoincrement=True？**
- [ ] **SQL 脚本是否保存到正确目录？**（sql/codeai.sql 或 sql/codeai-pg.sql）

---

## 8. SQL 文件位置

| 数据库 | 脚本位置 |
|--------|---------|
| MySQL | `sql/codeai.sql` |
| PostgreSQL | `sql/codeai-pg.sql` |

---

## 参考实现

查看已有的完整实现：

- **DO 参考**: `module_admin/entity/do/user_do.py`
- **DO 参考**: `module_admin/entity/do/dept_do.py`
- **表结构参考**: `sql/codeai.sql` 中的 sys_user 和 sys_dept 表

**特别注意**：
- ✅ 软删除字段类型是 `CHAR(1)`（不是 BIGINT）
- ✅ 软删除值是 '0'（存在）或 '2'（删除）
- ✅ 主键使用自增 `AUTO_INCREMENT`（不是雪花 ID）
- ✅ DO 继承 `Base`（不是 TenantEntity）
- ✅ 审计字段手动设置（不是自动填充）
