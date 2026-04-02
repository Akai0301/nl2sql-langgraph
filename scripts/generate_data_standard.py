#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据标准文档生成脚本
查询数据库所有表结构，生成完整的 Markdown 格式数据标准文档

运行方式:
  python scripts/generate_data_standard.py
  python scripts/generate_data_standard.py --output docs/data-standard.md
"""
import argparse
import asyncio
import re
from datetime import datetime
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


# ============== 数据库查询函数 ==============

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
            rows = result.fetchall()
            tables = [{'table_name': row[0], 'table_comment': row[1] or ''} for row in rows]
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
            rows = result.fetchall()
            tables = [{
                'table_name': row[0],
                'table_comment': row[1] or '',
                'table_rows': row[2],
                'data_length': row[3],
                'create_time': str(row[4]) if row[4] else None,
                'update_time': str(row[5]) if row[5] else None,
            } for row in rows]

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
                    CASE WHEN pk.contype = 'p' THEN 'PRI' ELSE '' END as column_key,
                    '' as column_default,
                    '' as extra
                FROM pg_attribute a
                LEFT JOIN pg_constraint pk ON pk.conrelid = a.attrelid
                    AND pk.contype = 'p'
                    AND a.attnum = ANY(pk.conkey)
                WHERE a.attrelid = (:table_name)::regclass
                  AND a.attnum > 0
                  AND NOT a.attisdropped
                ORDER BY a.attnum
            """), {'table_name': f'public.{table_name}'})
            rows = result.fetchall()
            columns = [{
                'column_name': row[0],
                'column_type': row[1],
                'is_nullable': row[2],
                'column_key': row[5] or '',
                'column_comment': row[4] or '',
                'ordinal_position': row[3],
                'column_default': row[6] or '',
                'extra': row[7] or '',
                'is_primary': row[5] == 'PRI',
                'is_auto_increment': False,
            } for row in rows]
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
            rows = result.fetchall()
            columns = [{
                'column_name': row[0],
                'column_type': row[1],
                'is_nullable': row[2],
                'column_key': row[3],
                'column_default': row[4] or '',
                'extra': row[5] or '',
                'column_comment': row[6] or '',
                'ordinal_position': row[7],
                'is_primary': row[3] == 'PRI',
                'is_auto_increment': 'auto_increment' in (row[5] or '').lower(),
            } for row in rows]

    await engine.dispose()
    return columns


async def get_table_indexes(config: dict, table_name: str) -> list:
    """获取表的索引信息"""
    if config['db_type'] == 'postgresql':
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

        rows = result.fetchall()
        indexes = {}
        for row in rows:
            idx_name = row[0]
            if idx_name not in indexes:
                indexes[idx_name] = {
                    'index_name': idx_name,
                    'is_unique': not row[2],
                    'index_type': row[4],
                    'columns': [],
                }
            indexes[idx_name]['columns'].append(row[1])

    await engine.dispose()
    return list(indexes.values())


async def get_table_ddl(config: dict, table_name: str) -> str:
    """获取表的 DDL"""
    url = get_db_url(config)
    engine = create_async_engine(url, echo=False)

    async with engine.connect() as conn:
        if config['db_type'] == 'postgresql':
            ddl = None
        else:
            result = await conn.execute(text(f"SHOW CREATE TABLE {table_name}"))
            row = result.fetchone()
            ddl = row[1] if row else None

    await engine.dispose()
    return ddl


# ============== 文档生成函数 ==============

def get_table_category(table_name: str) -> tuple:
    """
    根据表名前缀获取表分类

    :return: (分类名称, 分类描述)
    """
    categories = {
        'sys_': ('系统管理', '系统基础功能相关表，包括用户、角色、权限、菜单、部门等'),
        'gen_': ('代码生成', '代码生成器相关表，包括生成配置、模板等'),
        'demo_': ('示例模块', '示例业务表'),
        'act_': ('工作流引擎', 'Activiti/WarmFlow 工作流相关表'),
        'flow_': ('工作流引擎', 'WarmFlow 工作流相关表'),
    }

    for prefix, (name, desc) in categories.items():
        if table_name.startswith(prefix):
            return (name, desc)

    return ('业务模块', '业务功能相关表')


def format_data_size(size_bytes: int) -> str:
    """格式化数据大小"""
    if size_bytes is None:
        return 'N/A'
    if size_bytes < 1024:
        return f'{size_bytes} B'
    elif size_bytes < 1024 * 1024:
        return f'{size_bytes / 1024:.2f} KB'
    elif size_bytes < 1024 * 1024 * 1024:
        return f'{size_bytes / (1024 * 1024):.2f} MB'
    else:
        return f'{size_bytes / (1024 * 1024 * 1024):.2f} GB'


async def generate_markdown_doc(config: dict, tables: list, output_path: str):
    """生成 Markdown 格式的数据标准文档"""

    # 文档头部
    content = f"""# 数据标准文档

> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> **数据库**: {config['db_database']}
> **数据库类型**: {config['db_type']}
> **表总数**: {len(tables)}

---

## 目录

"""

    # 按分类组织表
    categorized_tables = {}
    for table in tables:
        category, _ = get_table_category(table['table_name'])
        if category not in categorized_tables:
            categorized_tables[category] = []
        categorized_tables[category].append(table)

    # 生成目录
    for category in categorized_tables.keys():
        content += f"- [{category}](#{category.lower().replace(' ', '-')})\n"
        for table in categorized_tables[category]:
            anchor = table['table_name'].lower()
            content += f"  - [{table['table_name']}](#{anchor})\n"

    content += "\n---\n\n"

    # 生成每个分类的表详情
    for category, category_tables in categorized_tables.items():
        _, category_desc = get_table_category(category_tables[0]['table_name'])
        content += f"## {category}\n\n> {category_desc}\n\n"

        for table in category_tables:
            table_name = table['table_name']
            table_comment = table['table_comment'] or '暂无描述'

            content += f"### {table_name}\n\n"
            content += f"**描述**: {table_comment}\n\n"

            # 表基本信息
            if 'table_rows' in table:
                content += f"| 属性 | 值 |\n"
                content += f"|------|----|\n"
                content += f"| 数据行数 | {table.get('table_rows', 'N/A')} |\n"
                content += f"| 数据大小 | {format_data_size(table.get('data_length', 0))} |\n"
                if table.get('create_time'):
                    content += f"| 创建时间 | {table['create_time']} |\n"
                if table.get('update_time'):
                    content += f"| 更新时间 | {table['update_time']} |\n"
                content += "\n"

            # 字段信息表格
            columns = await get_table_columns(config, table_name)
            content += "#### 字段列表\n\n"
            content += "| 序号 | 字段名 | 类型 | 可空 | 键 | 默认值 | 说明 |\n"
            content += "|------|--------|------|------|-----|--------|------|\n"

            for col in columns:
                key_info = col['column_key']
                if col['is_auto_increment']:
                    key_info += ' (自增)'
                default_val = col['column_default'] if col['column_default'] else ''
                if len(default_val) > 20:
                    default_val = default_val[:20] + '...'

                content += f"| {col['ordinal_position']} | {col['column_name']} | {col['column_type']} | {col['is_nullable']} | {key_info} | {default_val} | {col['column_comment']} |\n"

            content += "\n"

            # 索引信息
            indexes = await get_table_indexes(config, table_name)
            if indexes:
                content += "#### 索引列表\n\n"
                content += "| 索引名 | 类型 | 唯一性 | 字段 |\n"
                content += "|--------|------|--------|------|\n"
                for idx in indexes:
                    unique_str = '是' if idx['is_unique'] else '否'
                    content += f"| {idx['index_name']} | {idx['index_type']} | {unique_str} | {', '.join(idx['columns'])} |\n"
                content += "\n"

            # DDL 信息
            ddl = await get_table_ddl(config, table_name)
            if ddl:
                content += "#### DDL 语句\n\n"
                content += f"```sql\n{ddl}\n```\n\n"

            content += "---\n\n"

    # 附录：字段类型说明
    content += """## 附录

### 字段类型说明

| 类型 | 说明 | 常用场景 |
|------|------|---------|
| BIGINT | 64位整数 | 主键ID、外键、数量统计 |
| INT | 32位整数 | 状态值、排序号 |
| VARCHAR | 可变长度字符串 | 名称、编码、描述 |
| CHAR | 定长字符串 | 标志位、状态码 |
| TEXT | 长文本 | 内容、详情 |
| DATETIME | 日期时间 | 创建时间、更新时间 |
| TIMESTAMP | 时间戳 | 时间记录 |
| DECIMAL | 精确小数 | 金额、比率 |
| TINYINT | 小整数 | 布尔值、小范围枚举 |

### 通用字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | BIGINT | 主键ID，自增 |
| del_flag | CHAR(1) | 删除标志：0-正常，2-已删除 |
| create_by | VARCHAR(64) | 创建者 |
| create_time | DATETIME | 创建时间 |
| update_by | VARCHAR(64) | 更新者 |
| update_time | DATETIME | 更新时间 |
| remark | VARCHAR(500) | 备注 |

### 命名规范

1. **表名**: 使用蛇形命名法，全部小写，如 `sys_user`
2. **字段名**: 使用蛇形命名法，全部小写，如 `user_name`
3. **主键**: 统一使用 `id` 命名
4. **外键**: 使用 `关联表_id` 格式，如 `dept_id`
5. **状态字段**: 使用 `status`，值为 CHAR(1) 类型
6. **标志字段**: 使用 `xxx_flag` 格式，如 `del_flag`

---

*本文档由数据标准文档生成脚本自动生成*
"""

    # 写入文件
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)

    return output_file


async def main_async(output_path: str):
    """异步主函数"""
    config = get_db_config()
    print(f"正在连接数据库: {config['db_host']}:{config['db_port']}/{config['db_database']}")

    # 获取所有表
    print("正在查询数据库表列表...")
    tables = await get_all_tables(config)
    print(f"共发现 {len(tables)} 张表")

    # 生成文档
    print("正在生成数据标准文档...")
    output_file = await generate_markdown_doc(config, tables, output_path)
    print(f"文档已生成: {output_file}")

    return output_file


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='生成数据标准文档')
    parser.add_argument('--output', '-o', default='docs/data-standard.md',
                        help='输出文件路径 (默认: docs/data-standard.md)')
    args = parser.parse_args()

    asyncio.run(main_async(args.output))


if __name__ == '__main__':
    main()