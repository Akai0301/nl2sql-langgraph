---
name: db-meta-query
description: |
  数据库元数据查询与 SQL 执行工具。通过 Python 脚本获取数据库表结构、字段信息、DDL、索引等元数据信息，并支持执行任意 SQL 语句。

  触发场景：
  - 查询数据库中有哪些表
  - 查询表的结构和字段信息
  - 获取表的 DDL（CREATE TABLE 语句）
  - 查询表的索引、外键信息
  - 获取数据库元数据进行代码生成
  - 执行 SQL 查询（SELECT）
  - 执行 SQL 修改（INSERT/UPDATE/DELETE）
  - 执行 DDL 语句（CREATE/ALTER/DROP）
  - 数据库数据快速验证和调试

  触发词：数据库表、表结构、DDL、表字段、列信息、索引、外键、元数据、information_schema、SHOW CREATE TABLE、DESCRIBE、数据库元数据、执行SQL、SQL查询、SQL执行、数据库查询
---

# 数据库元数据查询与 SQL 执行工具

## 概述

本技能用于通过 Python 脚本操作数据库，包括：
- 数据库表列表查询
- 表结构（字段、类型、注释）
- DDL（CREATE TABLE 语句）
- 索引信息
- 外键约束
- **执行任意 SQL 语句（查询/修改/DDL）**

**与 `database-ops` 的区别**：
- `database-ops`: 专注于**建表和 DO 设计**（创建表、编写 SQLAlchemy Model）
- `db-meta-query`: 专注于**查询元数据和执行 SQL**（读取表结构、获取 DDL、执行 SQL）

---

## 数据库配置

### 方式一：从 .env.dev 文件读取（推荐）

脚本独立运行，不依赖项目配置模块：

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库元数据查询脚本
运行方式: python scripts/db_meta.py [命令] [参数]
"""
import os
import re
from pathlib import Path

def load_env_config(env_file: str = '.env.dev') -> dict:
    """
    从 .env 文件读取数据库配置

    :param env_file: 环境配置文件路径
    :return: 数据库配置字典
    """
    # 查找配置文件（支持相对路径和绝对路径）
    config_path = Path(env_file)
    if not config_path.is_absolute():
        # 尝试在当前目录或项目根目录查找
        for search_path in ['.', '..', '../..', '../../..']:
            candidate = Path(search_path) / env_file
            if candidate.exists():
                config_path = candidate
                break

    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    config = {}
    with open(config_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue
            # 解析 KEY = VALUE 格式
            match = re.match(r"^([A-Z_]+)\s*=\s*(.+)$", line)
            if match:
                key, value = match.groups()
                # 去除引号和尾随空格
                value = value.strip().strip("'\"")
                # 转换布尔值
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                else:
                    # 尝试转换为数字
                    try:
                        if '.' in value:
                            value = float(value)
                        else:
                            value = int(value)
                    except ValueError:
                        pass
                config[key] = value

    return config


def get_db_config() -> dict:
    """获取数据库配置"""
    config = load_env_config('.env.dev')
    return {
        'db_type': config.get('DB_TYPE', 'mysql'),
        'db_host': config.get('DB_HOST', '127.0.0.1'),
        'db_port': config.get('DB_PORT', 3306),
        'db_username': config.get('DB_USERNAME', 'root'),
        'db_password': config.get('DB_PASSWORD', ''),
        'db_database': config.get('DB_DATABASE', 'codeai'),
    }


if __name__ == '__main__':
    db_config = get_db_config()
    print(f"数据库类型: {db_config['db_type']}")
    print(f"数据库主机: {db_config['db_host']}")
    print(f"数据库端口: {db_config['db_port']}")
    print(f"数据库用户: {db_config['db_username']}")
    print(f"数据库名称: {db_config['db_database']}")
```

### 方式二：从项目配置模块读取

在项目内部运行时，可直接使用配置模块：

```python
from config.env import DataBaseConfig

db_type = DataBaseConfig.db_type
db_host = DataBaseConfig.db_host
db_port = DataBaseConfig.db_port
db_username = DataBaseConfig.db_username
db_password = DataBaseConfig.db_password
db_database = DataBaseConfig.db_database
```

### 配置文件格式（.env.dev）

```ini
# -------- 数据库配置 --------
# 数据库类型，可选的有'mysql'、'postgresql'，默认为'mysql'
DB_TYPE = 'mysql'
# 数据库主机
DB_HOST = '127.0.0.1'
# 数据库端口
DB_PORT = 3306
# 数据库用户名
DB_USERNAME = 'root'
# 数据库密码
DB_PASSWORD = 'mysqlroot'
# 数据库名称
DB_DATABASE = 'codeai'
```

---

## SQL 执行功能

本技能支持执行任意 SQL 语句，包括查询（SELECT）、修改（INSERT/UPDATE/DELETE）和 DDL（CREATE/ALTER/DROP）。

### 执行 SQL 脚本模板

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库 SQL 执行脚本
支持执行 SELECT、INSERT、UPDATE、DELETE、DDL 等 SQL 语句

运行方式:
  python scripts/db_exec.py "SELECT * FROM sys_user LIMIT 10"
  python scripts/db_exec.py "INSERT INTO sys_dict_data VALUES (...)"
  python scripts/db_exec.py "UPDATE sys_user SET status = '0' WHERE user_id = 1"
  python scripts/db_exec.py --file scripts/sql/init_data.sql
"""
import asyncio
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


# ============== 配置读取 ==============

def load_env_config(env_file: str = '.env.dev') -> dict:
    """从 .env 文件读取配置"""
    config_path = Path(env_file)
    if not config_path.is_absolute():
        for search_path in ['.', '..', '../..', '../../..']:
            candidate = Path(search_path) / env_file
            if candidate.exists():
                config_path = candidate
                break

    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    config = {}
    with open(config_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            match = re.match(r"^([A-Z_]+)\s*=\s*(.+)$", line)
            if match:
                key, value = match.groups()
                value = value.strip().strip("'\"")
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                else:
                    try:
                        value = int(value) if '.' not in value else float(value)
                    except ValueError:
                        pass
                config[key] = value
    return config


def get_db_config() -> dict:
    """获取数据库配置"""
    config = load_env_config('.env.dev')
    return {
        'db_type': config.get('DB_TYPE', 'mysql'),
        'db_host': config.get('DB_HOST', '127.0.0.1'),
        'db_port': config.get('DB_PORT', 3306),
        'db_username': config.get('DB_USERNAME', 'root'),
        'db_password': config.get('DB_PASSWORD', ''),
        'db_database': config.get('DB_DATABASE', 'codeai'),
    }


def get_db_url(config: dict) -> str:
    """构建数据库连接 URL"""
    password = quote_plus(str(config['db_password']))
    if config['db_type'] == 'postgresql':
        return f"postgresql+asyncpg://{config['db_username']}:{password}@{config['db_host']}:{config['db_port']}/{config['db_database']}"
    else:
        return f"mysql+asyncmy://{config['db_username']}:{password}@{config['db_host']}:{config['db_port']}/{config['db_database']}"


# ============== SQL 执行函数 ==============

async def execute_sql(config: dict, sql: str, params: dict = None):
    """
    执行 SQL 语句

    :param config: 数据库配置
    :param sql: SQL 语句
    :param params: 参数（可选）
    :return: 执行结果
    """
    url = get_db_url(config)
    engine = create_async_engine(url, echo=False)

    sql_upper = sql.strip().upper()
    is_query = sql_upper.startswith('SELECT') or sql_upper.startswith('SHOW') or sql_upper.startswith('DESCRIBE') or sql_upper.startswith('EXPLAIN')

    async with engine.connect() as conn:
        try:
            result = await conn.execute(text(sql), params or {})

            if is_query:
                # 查询语句：返回结果集
                columns = list(result.keys()) if result.returns_rows else []
                rows = [dict(row._mapping) for row in result] if result.returns_rows else []
                await conn.commit()
                return {
                    'success': True,
                    'type': 'query',
                    'columns': columns,
                    'rows': rows,
                    'row_count': len(rows),
                }
            else:
                # 修改语句：返回影响行数
                await conn.commit()
                return {
                    'success': True,
                    'type': 'modify',
                    'rowcount': result.rowcount,
                    'message': f'影响 {result.rowcount} 行',
                }
        except Exception as e:
            await conn.rollback()
            return {
                'success': False,
                'type': 'error',
                'error': str(e),
                'message': f'执行失败: {e}',
            }
        finally:
            await engine.dispose()


async def execute_sql_file(config: dict, file_path: str):
    """
    执行 SQL 文件

    :param config: 数据库配置
    :param file_path: SQL 文件路径
    :return: 执行结果列表
    """
    path = Path(file_path)
    if not path.exists():
        return {'success': False, 'error': f'文件不存在: {file_path}'}

    with open(path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # 按分号分割 SQL 语句（忽略注释）
    statements = []
    for stmt in sql_content.split(';'):
        stmt = stmt.strip()
        # 跳过空语句和注释
        if stmt and not stmt.startswith('--') and not stmt.startswith('/*'):
            statements.append(stmt)

    results = []
    for i, stmt in enumerate(statements, 1):
        print(f"\n执行第 {i}/{len(statements)} 条语句...")
        result = await execute_sql(config, stmt)
        results.append({
            'index': i,
            'sql': stmt[:100] + '...' if len(stmt) > 100 else stmt,
            'result': result,
        })

    return {
        'success': True,
        'total': len(statements),
        'results': results,
    }


def format_output(result: dict):
    """格式化输出结果"""
    if not result.get('success'):
        print(f"\n❌ 执行失败: {result.get('error', '未知错误')}")
        return

    if result.get('type') == 'query':
        rows = result.get('rows', [])
        columns = result.get('columns', [])
        row_count = result.get('row_count', 0)

        print(f"\n✅ 查询成功，共 {row_count} 行")
        print("-" * 120)

        if columns and rows:
            # 计算每列宽度
            widths = {col: len(col) for col in columns}
            for row in rows:
                for col in columns:
                    val = str(row.get(col, ''))[:50]  # 限制显示长度
                    widths[col] = max(widths[col], len(val))

            # 打印表头
            header = ' | '.join(col.ljust(widths[col]) for col in columns)
            print(header)
            print("-" * len(header))

            # 打印数据行
            for row in rows[:100]:  # 最多显示 100 行
                line = ' | '.join(str(row.get(col, '')).ljust(widths[col])[:widths[col]] for col in columns)
                print(line)

            if row_count > 100:
                print(f"\n... 还有 {row_count - 100} 行未显示")

    elif result.get('type') == 'modify':
        print(f"\n✅ 执行成功: {result.get('message', '')}")

    elif result.get('type') == 'error':
        print(f"\n❌ 执行失败: {result.get('error', '未知错误')}")


def print_usage():
    """打印使用说明"""
    print("""
数据库 SQL 执行脚本

用法:
  python scripts/db_exec.py "<SQL语句>"
  python scripts/db_exec.py --file <SQL文件路径>
  python scripts/db_exec.py --help

参数:
  --file, -f    从文件读取 SQL 语句
  --help, -h    显示帮助信息

示例:
  # 查询数据
  python scripts/db_exec.py "SELECT * FROM sys_user LIMIT 10"

  # 查询表结构
  python scripts/db_exec.py "DESCRIBE sys_user"

  # 插入数据
  python scripts/db_exec.py "INSERT INTO sys_dict_data (dict_code, dict_sort, dict_label, dict_value, dict_type) VALUES (100, 1, '测试', 'test', 'sys_normal_disable')"

  # 更新数据
  python scripts/db_exec.py "UPDATE sys_user SET nick_name = '管理员' WHERE user_id = 1"

  # 删除数据
  python scripts/db_exec.py "DELETE FROM sys_dict_data WHERE dict_code = 100"

  # 执行 SQL 文件
  python scripts/db_exec.py --file scripts/sql/init_data.sql

注意:
  - SELECT/SHOW/DESCRIBE/EXPLAIN 语句返回查询结果
  - INSERT/UPDATE/DELETE/DDL 语句返回影响行数
  - SQL 语句需要用引号包裹
  - Windows PowerShell 建议使用双引号
""")


async def main_async(sql: str = None, file_path: str = None):
    """异步主函数"""
    config = get_db_config()

    if file_path:
        print(f"正在执行 SQL 文件: {file_path}")
        result = await execute_sql_file(config, file_path)
        if result.get('success'):
            total = result.get('total', 0)
            results = result.get('results', [])
            success_count = sum(1 for r in results if r['result'].get('success'))
            print(f"\n✅ 执行完成: {success_count}/{total} 条成功")
            for r in results:
                if not r['result'].get('success'):
                    print(f"  ❌ 第 {r['index']} 条失败: {r['result'].get('error')}")
        else:
            print(f"❌ 执行失败: {result.get('error')}")
    elif sql:
        result = await execute_sql(config, sql)
        format_output(result)
    else:
        print_usage()


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)

    # 解析参数
    sql = None
    file_path = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ['--help', '-h']:
            print_usage()
            sys.exit(0)
        elif arg in ['--file', '-f']:
            if i + 1 < len(args):
                file_path = args[i + 1]
                i += 2
                continue
            else:
                print("错误: --file 参数需要指定文件路径")
                sys.exit(1)
        else:
            sql = arg
            # 处理带空格的 SQL
            if i + 1 < len(args) and not args[i + 1].startswith('--'):
                sql = ' '.join(args[i:])
                break
        i += 1

    asyncio.run(main_async(sql, file_path))


if __name__ == '__main__':
    main()
```

### 快速执行 SQL 命令

```bash
# 查询数据
python scripts/db_exec.py "SELECT * FROM sys_user LIMIT 10"

# 查询表结构
python scripts/db_exec.py "DESCRIBE sys_user"

# 显示建表语句
python scripts/db_exec.py "SHOW CREATE TABLE sys_user"

# 统计查询
python scripts/db_exec.py "SELECT COUNT(*) as total FROM sys_user"

# 多表关联查询
python scripts/db_exec.py "SELECT u.user_name, d.dept_name FROM sys_user u LEFT JOIN sys_dept d ON u.dept_id = d.dept_id LIMIT 10"

# 插入数据
python scripts/db_exec.py "INSERT INTO sys_dict_data (dict_code, dict_sort, dict_label, dict_value, dict_type) VALUES (100, 1, '测试', 'test', 'sys_normal_disable')"

# 更新数据
python scripts/db_exec.py "UPDATE sys_user SET nick_name = '管理员' WHERE user_id = 1"

# 删除数据
python scripts/db_exec.py "DELETE FROM sys_dict_data WHERE dict_code = 100"

# 执行 SQL 文件
python scripts/db_exec.py --file scripts/sql/init_data.sql
```

### Windows PowerShell 注意事项

```powershell
# PowerShell 中使用双引号
.\venv\Scripts\python.exe scripts/db_exec.py "SELECT * FROM sys_user LIMIT 10"

# 如果 SQL 包含特殊字符，使用转义
.\venv\Scripts\python.exe scripts/db_exec.py "SELECT * FROM sys_user WHERE user_name LIKE '%admin%'"
```

### 项目内调用方式

在项目代码中可以直接使用 DAO 层的数据库连接执行 SQL：

```python
from sqlalchemy import text
from module_admin.dao.user_dao import UserDao
from config.database import async_db_session

# 方式一：使用现有的数据库会话
async with async_db_session() as session:
    result = await session.execute(text("SELECT * FROM sys_user LIMIT 10"))
    rows = [dict(row._mapping) for row in result]

# 方式二：在 DAO 中封装
class CustomDao:
    """自定义 SQL 执行"""

    @staticmethod
    async def execute_query(sql: str, params: dict = None):
        """执行查询 SQL"""
        async with async_db_session() as session:
            result = await session.execute(text(sql), params or {})
            return [dict(row._mapping) for row in result]

    @staticmethod
    async def execute_modify(sql: str, params: dict = None):
        """执行修改 SQL"""
        async with async_db_session() as session:
            result = await session.execute(text(sql), params or {})
            await session.commit()
            return result.rowcount
```

### 安全注意事项

1. **SQL 注入防护**：执行用户输入的 SQL 时要特别小心，生产环境建议使用参数化查询
2. **事务管理**：INSERT/UPDATE/DELETE 操作会自动提交事务，失败时自动回滚
3. **权限控制**：确保数据库用户只有必要的权限
4. **数据备份**：执行删除或修改操作前，建议先备份数据

```python
# 安全的参数化查询示例
sql = "SELECT * FROM sys_user WHERE user_name = :username"
result = await execute_sql(config, sql, {'username': 'admin'})
```

---

## 完整脚本模板（独立运行）

### 通用元数据查询脚本

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库元数据查询脚本
支持 MySQL 和 PostgreSQL

运行方式:
  python scripts/db_meta.py tables              # 查询所有表
  python scripts/db_meta.py columns <表名>      # 查询表结构
  python scripts/db_meta.py ddl <表名>          # 蟥询表DDL
  python scripts/db_meta.py indexes <表名>      # 查询表索引
  python scripts/db_meta.py fks [表名]          # 查询外键约束
  python scripts/db_meta.py info <表名>         # 查询表完整信息
"""
import asyncio
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


# ============== 配置读取 ==============

def load_env_config(env_file: str = '.env.dev') -> dict:
    """从 .env 文件读取配置"""
    config_path = Path(env_file)
    if not config_path.is_absolute():
        for search_path in ['.', '..', '../..', '../../..']:
            candidate = Path(search_path) / env_file
            if candidate.exists():
                config_path = candidate
                break

    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    config = {}
    with open(config_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            match = re.match(r"^([A-Z_]+)\s*=\s*(.+)$", line)
            if match:
                key, value = match.groups()
                value = value.strip().strip("'\"")
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                else:
                    try:
                        value = int(value) if '.' not in value else float(value)
                    except ValueError:
                        pass
                config[key] = value
    return config


def get_db_config() -> dict:
    """获取数据库配置"""
    config = load_env_config('.env.dev')
    return {
        'db_type': config.get('DB_TYPE', 'mysql'),
        'db_host': config.get('DB_HOST', '127.0.0.1'),
        'db_port': config.get('DB_PORT', 3306),
        'db_username': config.get('DB_USERNAME', 'root'),
        'db_password': config.get('DB_PASSWORD', ''),
        'db_database': config.get('DB_DATABASE', 'codeai'),
    }


def get_db_url(config: dict) -> str:
    """构建数据库连接 URL"""
    password = quote_plus(str(config['db_password']))
    if config['db_type'] == 'postgresql':
        return f"postgresql+asyncpg://{config['db_username']}:{password}@{config['db_host']}:{config['db_port']}/{config['db_database']}"
    else:
        return f"mysql+asyncmy://{config['db_username']}:{password}@{config['db_host']}:{config['db_port']}/{config['db_database']}"


# ============== 查询函数 ==============

async def get_all_tables(config: dict) -> list:
    """获取所有表列表"""
    url = get_db_url(config)
    engine = create_async_engine(url, echo=False)

    async with engine.connect() as conn:
        if config['db_type'] == 'postgresql':
            result = await conn.execute(text("""
                SELECT
                    tablename as table_name,
                    obj_description((schemaname || '.' || tablename)::regclass) as table_comment
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
            """))
            tables = [{'table_name': row.table_name, 'table_comment': row.table_comment or ''} for row in result]
        else:
            result = await conn.execute(text("""
                SELECT
                    table_name,
                    table_comment,
                    table_rows,
                    data_length,
                    create_time,
                    update_time
                FROM information_schema.tables
                WHERE table_schema = :db_name
                ORDER BY table_name
            """), {'db_name': config['db_database']})
            tables = [{
                'table_name': row.table_name,
                'table_comment': row.table_comment or '',
                'table_rows': row.table_rows,
                'data_length': row.data_length,
                'create_time': str(row.create_time) if row.create_time else None,
                'update_time': str(row.update_time) if row.update_time else None,
            } for row in result]

    await engine.dispose()
    return tables


async def get_table_columns(config: dict, table_name: str) -> list:
    """获取表的字段信息"""
    url = get_db_url(config)
    engine = create_async_engine(url, echo=False)

    async with engine.connect() as conn:
        if config['db_type'] == 'postgresql':
            result = await conn.execute(text("""
                SELECT
                    a.attname as column_name,
                    pg_catalog.format_type(a.atttypid, a.atttypmod) as column_type,
                    CASE WHEN a.attnotnull THEN 'NO' ELSE 'YES' END as is_nullable,
                    a.attnum as ordinal_position,
                    col_description(a.attrelid, a.attnum) as column_comment,
                    CASE WHEN pk.contype = 'p' THEN 'PRI' ELSE '' END as column_key
                FROM pg_attribute a
                LEFT JOIN pg_constraint pk ON pk.conrelid = a.attrelid
                    AND pk.contype = 'p'
                    AND a.attnum = ANY(pk.conkey)
                WHERE a.attrelid = (:table_name)::regclass
                  AND a.attnum > 0
                  AND NOT a.attisdropped
                ORDER BY a.attnum
            """), {'table_name': f'public.{table_name}'})
            columns = [{
                'column_name': row.column_name,
                'column_type': row.column_type,
                'is_nullable': row.is_nullable,
                'column_key': row.column_key or '',
                'column_comment': row.column_comment or '',
                'ordinal_position': row.ordinal_position,
                'is_primary': row.column_key == 'PRI',
            } for row in result]
        else:
            result = await conn.execute(text("""
                SELECT
                    column_name,
                    column_type,
                    is_nullable,
                    column_key,
                    column_default,
                    extra,
                    column_comment,
                    ordinal_position
                FROM information_schema.columns
                WHERE table_schema = :db_name
                  AND table_name = :table_name
                ORDER BY ordinal_position
            """), {'db_name': config['db_database'], 'table_name': table_name})
            columns = [{
                'column_name': row.column_name,
                'column_type': row.column_type,
                'is_nullable': row.is_nullable,
                'column_key': row.column_key,
                'column_default': row.column_default,
                'extra': row.extra,
                'column_comment': row.column_comment or '',
                'ordinal_position': row.ordinal_position,
                'is_primary': row.column_key == 'PRI',
                'is_auto_increment': 'auto_increment' in (row.extra or '').lower(),
            } for row in result]

    await engine.dispose()
    return columns


async def get_table_ddl(config: dict, table_name: str) -> str:
    """获取表的 DDL"""
    url = get_db_url(config)
    engine = create_async_engine(url, echo=False)

    async with engine.connect() as conn:
        if config['db_type'] == 'postgresql':
            result = await conn.execute(text("""
                SELECT
                    'CREATE TABLE ' || relname || ' (' ||
                    string_agg(
                        a.attname || ' ' ||
                        pg_catalog.format_type(a.atttypid, a.atttypmod) ||
                        CASE WHEN a.attnotnull THEN ' NOT NULL' ELSE '' END,
                        ', '
                        ORDER BY a.attnum
                    ) || ');' as ddl
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_attribute a ON a.attrelid = c.oid
                WHERE c.relname = :table_name
                  AND n.nspname = 'public'
                  AND a.attnum > 0
                  AND NOT a.attisdropped
                GROUP BY c.relname
            """), {'table_name': table_name})
            row = result.fetchone()
            ddl = row[0] if row else None
        else:
            result = await conn.execute(text(f"SHOW CREATE TABLE {table_name}"))
            row = result.fetchone()
            ddl = row[1] if row else None

    await engine.dispose()
    return ddl


async def get_table_indexes(config: dict, table_name: str) -> list:
    """获取表的索引信息"""
    if config['db_type'] == 'postgresql':
        print("PostgreSQL 索引查询暂未实现")
        return []

    url = get_db_url(config)
    engine = create_async_engine(url, echo=False)

    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT
                index_name,
                column_name,
                non_unique,
                seq_in_index,
                index_type
            FROM information_schema.statistics
            WHERE table_schema = :db_name
              AND table_name = :table_name
            ORDER BY index_name, seq_in_index
        """), {'db_name': config['db_database'], 'table_name': table_name})

        indexes = {}
        for row in result:
            idx_name = row.index_name
            if idx_name not in indexes:
                indexes[idx_name] = {
                    'index_name': idx_name,
                    'is_unique': not row.non_unique,
                    'index_type': row.index_type,
                    'columns': [],
                }
            indexes[idx_name]['columns'].append(row.column_name)

    await engine.dispose()
    return list(indexes.values())


async def get_table_foreign_keys(config: dict, table_name: str = None) -> list:
    """获取表的外键约束"""
    if config['db_type'] == 'postgresql':
        print("PostgreSQL 外键查询暂未实现")
        return []

    url = get_db_url(config)
    engine = create_async_engine(url, echo=False)

    async with engine.connect() as conn:
        params = {'db_name': config['db_database']}
        sql = """
            SELECT
                kcu.table_name,
                kcu.column_name,
                kcu.referenced_table_name,
                kcu.referenced_column_name,
                rc.constraint_name
            FROM information_schema.key_column_usage kcu
            JOIN information_schema.referential_constraints rc
                ON kcu.constraint_name = rc.constraint_name
                AND kcu.table_schema = rc.constraint_schema
            WHERE kcu.table_schema = :db_name
              AND kcu.referenced_table_name IS NOT NULL
        """
        if table_name:
            sql += " AND kcu.table_name = :table_name"
            params['table_name'] = table_name

        result = await conn.execute(text(sql), params)
        fks = [{
            'table_name': row.table_name,
            'column_name': row.column_name,
            'referenced_table': row.referenced_table_name,
            'referenced_column': row.referenced_column_name,
            'constraint_name': row.constraint_name,
        } for row in result]

    await engine.dispose()
    return fks


async def get_table_full_info(config: dict, table_name: str) -> dict:
    """获取表的完整信息"""
    result = {
        'table_name': table_name,
        'columns': await get_table_columns(config, table_name),
        'indexes': await get_table_indexes(config, table_name),
        'foreign_keys': await get_table_foreign_keys(config, table_name),
        'ddl': await get_table_ddl(config, table_name),
    }
    return result


# ============== 格式化输出 ==============

def print_tables(tables: list):
    """打印表列表"""
    print(f"\n{'表名':<35} | {'注释'}")
    print("-" * 80)
    for t in tables:
        print(f"{t['table_name']:<35} | {t['table_comment']}")
    print(f"\n共 {len(tables)} 张表")


def print_columns(columns: list, table_name: str):
    """打印表结构"""
    print(f"\n表: {table_name}")
    print("-" * 120)
    print(f"{'字段名':<25} {'类型':<25} {'可空':<6} {'键':<6} {'默认值':<15} {'注释'}")
    print("-" * 120)
    for col in columns:
        default = str(col.get('column_default', ''))[:15] if col.get('column_default') else ''
        print(f"{col['column_name']:<25} {col['column_type']:<25} {col['is_nullable']:<6} {col.get('column_key', ''):<6} {default:<15} {col['column_comment']}")


def print_indexes(indexes: list, table_name: str):
    """打印索引信息"""
    print(f"\n表: {table_name} 的索引信息")
    print("-" * 80)
    for idx in indexes:
        unique_str = '唯一' if idx['is_unique'] else '非唯一'
        print(f"索引名: {idx['index_name']}")
        print(f"  类型: {idx['index_type']} | {unique_str}")
        print(f"  字段: {', '.join(idx['columns'])}")
        print()


def print_foreign_keys(fks: list):
    """打印外键信息"""
    if fks:
        print("\n外键约束:")
        print("-" * 100)
        print(f"{'表名':<20} {'字段':<20} {'引用表':<20} {'引用字段':<20} {'约束名'}")
        print("-" * 100)
        for fk in fks:
            print(f"{fk['table_name']:<20} {fk['column_name']:<20} {fk['referenced_table']:<20} {fk['referenced_column']:<20} {fk['constraint_name']}")
    else:
        print("未找到外键约束")


# ============== 主函数 ==============

def print_usage():
    """打印使用说明"""
    print("""
数据库元数据查询与 SQL 执行脚本

用法:
  python scripts/db_meta.py tables              # 查询所有表
  python scripts/db_meta.py columns <表名>      # 查询表结构
  python scripts/db_meta.py ddl <表名>          # 查询表DDL
  python scripts/db_meta.py indexes <表名>      # 查询表索引
  python scripts/db_meta.py fks [表名]          # 查询外键约束
  python scripts/db_meta.py info <表名>         # 查询表完整信息
  python scripts/db_meta.py config              # 显示当前配置
  python scripts/db_meta.py exec "<SQL>"        # 执行 SQL 语句
  python scripts/db_meta.py exec --file <文件>  # 执行 SQL 文件

示例:
  python scripts/db_meta.py tables
  python scripts/db_meta.py columns sys_user
  python scripts/db_meta.py ddl sys_user
  python scripts/db_meta.py info sys_user
  python scripts/db_meta.py exec "SELECT * FROM sys_user LIMIT 10"
  python scripts/db_meta.py exec "UPDATE sys_user SET status = '0' WHERE user_id = 1"
  python scripts/db_meta.py exec --file scripts/sql/init_data.sql
""")


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)

    command = sys.argv[1].lower()
    config = get_db_config()

    if command == 'config':
        print("当前数据库配置:")
        print(f"  类型: {config['db_type']}")
        print(f"  主机: {config['db_host']}")
        print(f"  端口: {config['db_port']}")
        print(f"  用户: {config['db_username']}")
        print(f"  数据库: {config['db_database']}")
        return

    if command == 'tables':
        tables = asyncio.run(get_all_tables(config))
        print_tables(tables)

    elif command == 'columns':
        if len(sys.argv) < 3:
            print("错误: 请指定表名")
            print("用法: python scripts/db_meta.py columns <表名>")
            sys.exit(1)
        table_name = sys.argv[2]
        columns = asyncio.run(get_table_columns(config, table_name))
        print_columns(columns, table_name)

    elif command == 'ddl':
        if len(sys.argv) < 3:
            print("错误: 请指定表名")
            print("用法: python scripts/db_meta.py ddl <表名>")
            sys.exit(1)
        table_name = sys.argv[2]
        ddl = asyncio.run(get_table_ddl(config, table_name))
        print(f"\n-- {table_name} DDL")
        print("-" * 80)
        print(ddl)

    elif command == 'indexes':
        if len(sys.argv) < 3:
            print("错误: 请指定表名")
            print("用法: python scripts/db_meta.py indexes <表名>")
            sys.exit(1)
        table_name = sys.argv[2]
        indexes = asyncio.run(get_table_indexes(config, table_name))
        print_indexes(indexes, table_name)

    elif command == 'fks':
        table_name = sys.argv[2] if len(sys.argv) > 2 else None
        fks = asyncio.run(get_table_foreign_keys(config, table_name))
        print_foreign_keys(fks)

    elif command == 'info':
        if len(sys.argv) < 3:
            print("错误: 请指定表名")
            print("用法: python scripts/db_meta.py info <表名>")
            sys.exit(1)
        table_name = sys.argv[2]
        info = asyncio.run(get_table_full_info(config, table_name))
        print(json.dumps(info, indent=2, ensure_ascii=False, default=str))

    else:
        print(f"未知命令: {command}")
        print_usage()


if __name__ == '__main__':
    main()
```

---

## 单独功能脚本

### 查询所有表（独立脚本）

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查询数据库中所有表
运行: python scripts/list_tables.py
"""
import asyncio
import re
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


def load_env_config(env_file: str = '.env.dev') -> dict:
    """从 .env 文件读取配置"""
    config_path = Path(env_file)
    if not config_path.is_absolute():
        for search_path in ['.', '..', '../..', '../../..']:
            candidate = Path(search_path) / env_file
            if candidate.exists():
                config_path = candidate
                break

    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    config = {}
    with open(config_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            match = re.match(r"^([A-Z_]+)\s*=\s*(.+)$", line)
            if match:
                key, value = match.groups()
                value = value.strip().strip("'\"")
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                else:
                    try:
                        value = int(value) if '.' not in value else float(value)
                    except ValueError:
                        pass
                config[key] = value
    return config


def get_db_config() -> dict:
    """获取数据库配置"""
    config = load_env_config('.env.dev')
    return {
        'db_type': config.get('DB_TYPE', 'mysql'),
        'db_host': config.get('DB_HOST', '127.0.0.1'),
        'db_port': config.get('DB_PORT', 3306),
        'db_username': config.get('DB_USERNAME', 'root'),
        'db_password': config.get('DB_PASSWORD', ''),
        'db_database': config.get('DB_DATABASE', 'codeai'),
    }


async def get_all_tables():
    """获取所有表"""
    config = get_db_config()
    password = quote_plus(str(config['db_password']))

    if config['db_type'] == 'postgresql':
        url = f"postgresql+asyncpg://{config['db_username']}:{password}@{config['db_host']}:{config['db_port']}/{config['db_database']}"
    else:
        url = f"mysql+asyncmy://{config['db_username']}:{password}@{config['db_host']}:{config['db_port']}/{config['db_database']}"

    engine = create_async_engine(url, echo=False)

    async with engine.connect() as conn:
        if config['db_type'] == 'postgresql':
            result = await conn.execute(text("""
                SELECT tablename as table_name,
                       obj_description((schemaname || '.' || tablename)::regclass) as table_comment
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
            """))
            tables = [{'table_name': row.table_name, 'table_comment': row.table_comment or ''} for row in result]
        else:
            result = await conn.execute(text("""
                SELECT table_name, table_comment, table_rows, create_time, update_time
                FROM information_schema.tables
                WHERE table_schema = :db_name
                ORDER BY table_name
            """), {'db_name': config['db_database']})
            tables = [{
                'table_name': row.table_name,
                'table_comment': row.table_comment or '',
                'table_rows': row.table_rows,
                'create_time': str(row.create_time) if row.create_time else None,
            } for row in result]

    await engine.dispose()

    print(f"\n{'表名':<35} | {'注释':<40} | {'行数'}")
    print("-" * 90)
    for t in tables:
        print(f"{t['table_name']:<35} | {t['table_comment']:<40} | {t.get('table_rows', 'N/A')}")
    print(f"\n共 {len(tables)} 张表")


if __name__ == '__main__':
    asyncio.run(get_all_tables())
```

### 查询表结构（独立脚本）

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查询表结构
运行: python scripts/show_columns.py <表名>
"""
import asyncio
import re
import sys
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


def load_env_config(env_file: str = '.env.dev') -> dict:
    """从 .env 文件读取配置"""
    config_path = Path(env_file)
    if not config_path.is_absolute():
        for search_path in ['.', '..', '../..', '../../..']:
            candidate = Path(search_path) / env_file
            if candidate.exists():
                config_path = candidate
                break

    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    config = {}
    with open(config_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            match = re.match(r"^([A-Z_]+)\s*=\s*(.+)$", line)
            if match:
                key, value = match.groups()
                value = value.strip().strip("'\"")
                config[key] = value
    return config


def get_db_config() -> dict:
    """获取数据库配置"""
    config = load_env_config('.env.dev')
    return {
        'db_type': config.get('DB_TYPE', 'mysql'),
        'db_host': config.get('DB_HOST', '127.0.0.1'),
        'db_port': int(config.get('DB_PORT', 3306)),
        'db_username': config.get('DB_USERNAME', 'root'),
        'db_password': config.get('DB_PASSWORD', ''),
        'db_database': config.get('DB_DATABASE', 'codeai'),
    }


async def get_table_columns(table_name: str):
    """获取表字段"""
    config = get_db_config()
    password = quote_plus(str(config['db_password']))

    if config['db_type'] == 'postgresql':
        url = f"postgresql+asyncpg://{config['db_username']}:{password}@{config['db_host']}:{config['db_port']}/{config['db_database']}"
    else:
        url = f"mysql+asyncmy://{config['db_username']}:{password}@{config['db_host']}:{config['db_port']}/{config['db_database']}"

    engine = create_async_engine(url, echo=False)

    async with engine.connect() as conn:
        if config['db_type'] == 'postgresql':
            result = await conn.execute(text("""
                SELECT a.attname as column_name,
                       pg_catalog.format_type(a.atttypid, a.atttypmod) as column_type,
                       CASE WHEN a.attnotnull THEN 'NO' ELSE 'YES' END as is_nullable,
                       col_description(a.attrelid, a.attnum) as column_comment
                FROM pg_attribute a
                WHERE a.attrelid = (:table_name)::regclass
                  AND a.attnum > 0 AND NOT a.attisdropped
                ORDER BY a.attnum
            """), {'table_name': f'public.{table_name}'})
            columns = [{
                'column_name': row.column_name,
                'column_type': row.column_type,
                'is_nullable': row.is_nullable,
                'column_comment': row.column_comment or '',
            } for row in result]
        else:
            result = await conn.execute(text("""
                SELECT column_name, column_type, is_nullable, column_key,
                       column_default, extra, column_comment
                FROM information_schema.columns
                WHERE table_schema = DATABASE() AND table_name = :table_name
                ORDER BY ordinal_position
            """), {'table_name': table_name})
            columns = [{
                'column_name': row.column_name,
                'column_type': row.column_type,
                'is_nullable': row.is_nullable,
                'column_key': row.column_key,
                'column_default': row.column_default,
                'extra': row.extra,
                'column_comment': row.column_comment or '',
            } for row in result]

    await engine.dispose()

    print(f"\n表: {table_name}")
    print("-" * 100)
    print(f"{'字段名':<25} {'类型':<20} {'可空':<6} {'键':<6} {'注释'}")
    print("-" * 100)
    for col in columns:
        key = col.get('column_key', '')
        print(f"{col['column_name']:<25} {col['column_type']:<20} {col['is_nullable']:<6} {key:<6} {col['column_comment']}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python scripts/show_columns.py <表名>")
        print("示例: python scripts/show_columns.py sys_user")
        sys.exit(1)

    table_name = sys.argv[1]
    asyncio.run(get_table_columns(table_name))
```

### 获取表 DDL（独立脚本）

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
获取表的 DDL（CREATE TABLE 语句）
运行: python scripts/show_ddl.py <表名>
"""
import asyncio
import re
import sys
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


def load_env_config(env_file: str = '.env.dev') -> dict:
    """从 .env 文件读取配置"""
    config_path = Path(env_file)
    if not config_path.is_absolute():
        for search_path in ['.', '..', '../..', '../../..']:
            candidate = Path(search_path) / env_file
            if candidate.exists():
                config_path = candidate
                break

    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    config = {}
    with open(config_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            match = re.match(r"^([A-Z_]+)\s*=\s*(.+)$", line)
            if match:
                key, value = match.groups()
                value = value.strip().strip("'\"")
                config[key] = value
    return config


def get_db_config() -> dict:
    """获取数据库配置"""
    config = load_env_config('.env.dev')
    return {
        'db_type': config.get('DB_TYPE', 'mysql'),
        'db_host': config.get('DB_HOST', '127.0.0.1'),
        'db_port': int(config.get('DB_PORT', 3306)),
        'db_username': config.get('DB_USERNAME', 'root'),
        'db_password': config.get('DB_PASSWORD', ''),
        'db_database': config.get('DB_DATABASE', 'codeai'),
    }


async def get_table_ddl(table_name: str):
    """获取表 DDL"""
    config = get_db_config()
    password = quote_plus(str(config['db_password']))

    if config['db_type'] == 'postgresql':
        print("PostgreSQL DDL 获取暂未完全实现")
        return

    url = f"mysql+asyncmy://{config['db_username']}:{password}@{config['db_host']}:{config['db_port']}/{config['db_database']}"
    engine = create_async_engine(url, echo=False)

    async with engine.connect() as conn:
        result = await conn.execute(text(f"SHOW CREATE TABLE {table_name}"))
        row = result.fetchone()

    await engine.dispose()

    if row:
        print(f"\n-- {table_name} DDL")
        print("-" * 80)
        print(row[1])


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python scripts/show_ddl.py <表名>")
        print("示例: python scripts/show_ddl.py sys_user")
        sys.exit(1)

    table_name = sys.argv[1]
    asyncio.run(get_table_ddl(table_name))
```

---

## 快速使用命令

创建脚本后，可以使用以下命令：

### 方式一：使用项目虚拟环境（推荐）

```bash
# Windows (PowerShell/CMD)
.\venv\Scripts\python.exe scripts\db_meta.py tables

# Windows (Git Bash)
./venv/Scripts/python scripts/db_meta.py tables

# Linux/macOS
./venv/bin/python scripts/db_meta.py tables

# 或先激活虚拟环境后再运行
# Windows
.\venv\Scripts\activate && python scripts/db_meta.py tables
# Linux/macOS
source venv/bin/activate && python scripts/db_meta.py tables
```

### 方式二：使用系统 Python

```bash
# 查询所有表
python scripts/db_meta.py tables

# 查询表结构
python scripts/db_meta.py columns sys_user

# 获取表 DDL
python scripts/db_meta.py ddl sys_user

# 查询表索引
python scripts/db_meta.py indexes sys_user

# 查询外键约束
python scripts/db_meta.py fks
python scripts/db_meta.py fks sys_user

# 查询表完整信息（JSON 格式）
python scripts/db_meta.py info sys_user

# 显示当前配置
python scripts/db_meta.py config
```

---

## 虚拟环境自动检测脚本

以下脚本会自动检测并使用项目的虚拟环境运行：

### 自动检测虚拟环境的启动脚本 (run_db_meta.py)

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库元数据查询启动脚本
自动检测并使用项目虚拟环境运行 db_meta.py

运行方式:
  python run_db_meta.py tables              # 查询所有表
  python run_db_meta.py columns <表名>      # 查询表结构
  python run_db_meta.py ddl <表名>          # 查询表DDL
  python run_db_meta.py indexes <表名>      # 查询表索引
  python run_db_meta.py fks [表名]          # 查询外键约束
  python run_db_meta.py info <表名>         # 查询表完整信息
"""
import os
import subprocess
import sys
from pathlib import Path


def find_venv_python() -> str:
    """
    自动检测项目虚拟环境中的 Python 解释器

    支持以下虚拟环境目录：
    - venv/
    - .venv/
    - env/

    :return: 虚拟环境中的 Python 解释器路径，未找到则返回系统 Python
    """
    # 获取项目根目录（脚本所在目录）
    script_dir = Path(__file__).parent.resolve()

    # 常见的虚拟环境目录名
    venv_names = ['venv', '.venv', 'env']

    # 常见的项目根目录标识文件
    project_markers = ['.env.dev', 'pyproject.toml', 'requirements.txt', 'main.py']

    # 向上查找项目根目录
    search_dir = script_dir
    for _ in range(5):  # 最多向上查找 5 层
        # 检查是否是项目根目录
        for marker in project_markers:
            if (search_dir / marker).exists():
                # 在项目根目录查找虚拟环境
                for venv_name in venv_names:
                    venv_dir = search_dir / venv_name
                    if venv_dir.exists():
                        # Windows: venv/Scripts/python.exe
                        # Linux/macOS: venv/bin/python
                        if sys.platform == 'win32':
                            python_path = venv_dir / 'Scripts' / 'python.exe'
                        else:
                            python_path = venv_dir / 'bin' / 'python'

                        if python_path.exists():
                            return str(python_path)
                break
        search_dir = search_dir.parent

    # 在当前目录查找虚拟环境
    for venv_name in venv_names:
        venv_dir = script_dir / venv_name
        if venv_dir.exists():
            if sys.platform == 'win32':
                python_path = venv_dir / 'Scripts' / 'python.exe'
            else:
                python_path = venv_dir / 'bin' / 'python'

            if python_path.exists():
                return str(python_path)

    # 未找到虚拟环境，返回系统 Python
    return sys.executable


def get_db_meta_script() -> str:
    """
    查找 db_meta.py 脚本路径

    :return: db_meta.py 的完整路径
    """
    script_dir = Path(__file__).parent.resolve()

    # 可能的位置
    possible_paths = [
        script_dir / 'scripts' / 'db_meta.py',
        script_dir / 'db_meta.py',
        script_dir.parent / 'scripts' / 'db_meta.py',
    ]

    for path in possible_paths:
        if path.exists():
            return str(path)

    raise FileNotFoundError(f"未找到 db_meta.py 脚本，请检查文件位置")


def main():
    """主函数"""
    # 获取虚拟环境 Python
    venv_python = find_venv_python()
    print(f"使用 Python: {venv_python}")

    # 获取 db_meta.py 脚本路径
    try:
        db_meta_script = get_db_meta_script()
    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)

    # 构建命令
    args = [venv_python, db_meta_script] + sys.argv[1:]

    # 运行脚本
    result = subprocess.run(args)
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
```

### 使用方法

将上述脚本保存为 `run_db_meta.py`，放在项目根目录或 `scripts/` 目录下：

```bash
# 自动使用虚拟环境运行
python run_db_meta.py tables
python run_db_meta.py columns sys_user
python run_db_meta.py ddl sys_user
```

---

## 在 Claude Code 中运行

当使用 Claude Code 执行数据库元数据查询时，推荐使用以下方式：

```bash
# Windows PowerShell
.\venv\Scripts\python.exe scripts/db_meta.py tables

# Linux/macOS
./venv/bin/python scripts/db_meta.py tables

# 或使用自动检测脚本
python run_db_meta.py tables
```

---

## 注意事项

1. **异步连接**：脚本使用异步 SQLAlchemy，必须使用 `async/await`
2. **数据库类型**：支持 MySQL 和 PostgreSQL，自动根据 `DB_TYPE` 切换
3. **密码转义**：密码中的特殊字符会自动 URL 编码
4. **配置文件查找**：脚本会自动在当前目录及上级目录查找 `.env.dev` 文件
5. **虚拟环境**：
   - 推荐使用项目虚拟环境运行脚本，确保依赖一致
   - Windows: `.\venv\Scripts\python.exe scripts/db_meta.py`
   - Linux/macOS: `./venv/bin/python scripts/db_meta.py`
   - 可使用自动检测脚本 `run_db_meta.py` 自动查找虚拟环境
6. **SQL 执行安全**：
   - 执行 INSERT/UPDATE/DELETE 操作前建议备份数据
   - 生产环境谨慎执行 DDL 语句（CREATE/ALTER/DROP）
   - 建议使用参数化查询防止 SQL 注入
   - SQL 文件按分号分割执行，每条语句独立提交

---

## 项目中的参考实现

项目中已有数据库元数据查询的实现，位于 `module_generator/dao/gen_dao.py`：

| 方法 | 功能 |
|------|------|
| `get_gen_db_table_list` | 获取数据库表列表 |
| `get_gen_db_table_columns_by_name` | 获取表的字段信息 |

---

## 注意

- 如果需要**创建表、设计 DO 实体类**，请使用 `database-ops` 技能
- 本技能专注于**查询**数据库元数据，不涉及数据修改