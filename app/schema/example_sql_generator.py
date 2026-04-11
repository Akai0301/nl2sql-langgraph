"""
示例 SQL 生成器：学习阶段自动生成典型查询示例。

生成策略：
1. 简单查询：SELECT * FROM table LIMIT 10
2. 聚合查询：按时间/维度分组统计度量
3. 排名查询：TOP N 排行榜
4. 时间范围查询：最近 N 天的数据
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.schema.engine import SchemaUnderstanding, TableInfo, FieldInfo


@dataclass
class ExampleSQL:
    """示例 SQL"""
    question: str  # 自然语言问题
    sql: str       # SQL 语句
    category: str  # simple/aggregate/rank/time_range
    description: str  # 示例说明


class ExampleSQLGenerator:
    """示例 SQL 生成器"""

    def __init__(self, schema: SchemaUnderstanding, dialect: str = "postgres"):
        """
        初始化生成器

        Args:
            schema: Schema 理解结果
            dialect: SQL 方言
        """
        self.schema = schema
        self.dialect = dialect

    def generate_examples(self, max_per_table: int = 3) -> list[ExampleSQL]:
        """
        生成示例 SQL

        Args:
            max_per_table: 每张表最多生成几个示例

        Returns:
            示例 SQL 列表
        """
        examples = []

        for table_name, table_info in self.schema.tables.items():
            table_examples = self._generate_table_examples(table_name, table_info)
            examples.extend(table_examples[:max_per_table])

        return examples

    def _generate_table_examples(self, table_name: str, table_info: TableInfo) -> list[ExampleSQL]:
        """为单表生成示例 SQL"""
        examples = []

        # 获取字段分类
        measure_fields = [f for f in table_info.fields.values() if f.category == "Measure"]
        time_fields = [f for f in table_info.fields.values() if f.category == "DateTime"]
        dimension_fields = [f for f in table_info.fields.values() if f.dim_or_meas == "Dimension" and f.category not in ("DateTime",)]

        # 1. 简单查询示例
        examples.append(self._generate_simple_query(table_name, table_info))

        # 2. 聚合查询示例（如果有度量字段）
        if measure_fields:
            examples.append(self._generate_aggregate_query(
                table_name, table_info, measure_fields[0], dimension_fields, time_fields
            ))

        # 3. 排名查询示例（如果有度量字段）
        if measure_fields and dimension_fields:
            examples.append(self._generate_rank_query(
                table_name, table_info, measure_fields[0], dimension_fields[0]
            ))

        # 4. 时间范围查询示例（如果有时间字段）
        if time_fields and measure_fields:
            examples.append(self._generate_time_range_query(
                table_name, table_info, time_fields[0], measure_fields[0]
            ))

        return examples

    def _generate_simple_query(self, table_name: str, table_info: TableInfo) -> ExampleSQL:
        """生成简单查询示例"""
        # 选择有注释的字段展示
        display_fields = []
        for field_name, field_info in list(table_info.fields.items())[:5]:
            display_fields.append(field_name)

        if len(display_fields) < len(table_info.fields):
            display_fields.append("...")

        sql = f"SELECT {', '.join(display_fields[:5])} FROM {table_name} LIMIT 10"

        table_comment = table_info.comment or table_name
        question = f"查看{table_comment}的前10条记录"

        return ExampleSQL(
            question=question,
            sql=sql,
            category="simple",
            description=f"简单查询示例：从{table_name}表获取前10条记录"
        )

    def _generate_aggregate_query(
        self,
        table_name: str,
        table_info: TableInfo,
        measure_field: FieldInfo,
        dimension_fields: list[FieldInfo],
        time_fields: list[FieldInfo],
    ) -> ExampleSQL:
        """生成聚合查询示例"""
        measure_name = measure_field.name
        measure_comment = measure_field.comment or measure_name

        # 选择一个分组维度
        group_by = None
        if dimension_fields:
            group_by = dimension_fields[0].name
        elif time_fields:
            group_by = f"DATE_TRUNC('month', {time_fields[0].name})"

        if group_by:
            sql = f"""SELECT {group_by} AS dimension,
       SUM({measure_name}) AS total_{measure_name}
FROM {table_name}
GROUP BY {group_by}
ORDER BY total_{measure_name} DESC
LIMIT 10"""

            dimension_comment = dimension_fields[0].comment if dimension_fields else "时间"
            question = f"按{dimension_comment}统计{measure_comment}的总和"
        else:
            sql = f"""SELECT SUM({measure_name}) AS total_{measure_name}
FROM {table_name}"""

            question = f"计算{measure_comment}的总和"

        return ExampleSQL(
            question=question,
            sql=sql.strip(),
            category="aggregate",
            description=f"聚合查询示例：按维度分组统计{measure_name}"
        )

    def _generate_rank_query(
        self,
        table_name: str,
        table_info: TableInfo,
        measure_field: FieldInfo,
        dimension_field: FieldInfo,
    ) -> ExampleSQL:
        """生成排名查询示例"""
        measure_name = measure_field.name
        measure_comment = measure_field.comment or measure_name
        dimension_name = dimension_field.name
        dimension_comment = dimension_field.comment or dimension_name

        sql = f"""SELECT {dimension_name},
       SUM({measure_name}) AS total_{measure_name}
FROM {table_name}
GROUP BY {dimension_name}
ORDER BY total_{measure_name} DESC
LIMIT 10"""

        question = f"查询{measure_comment}最高的前10个{dimension_comment}"

        return ExampleSQL(
            question=question,
            sql=sql.strip(),
            category="rank",
            description=f"排名查询示例：TOP 10 {dimension_name} 按 {measure_name} 排序"
        )

    def _generate_time_range_query(
        self,
        table_name: str,
        table_info: TableInfo,
        time_field: FieldInfo,
        measure_field: FieldInfo,
    ) -> ExampleSQL:
        """生成时间范围查询示例"""
        time_name = time_field.name
        time_comment = time_field.comment or time_name
        measure_name = measure_field.name
        measure_comment = measure_field.comment or measure_name

        sql = f"""SELECT DATE_TRUNC('day', {time_name}) AS day,
       SUM({measure_name}) AS total_{measure_name}
FROM {table_name}
WHERE {time_name} >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', {time_name})
ORDER BY day"""

        question = f"查询最近30天每天的{measure_comment}趋势"

        return ExampleSQL(
            question=question,
            sql=sql.strip(),
            category="time_range",
            description=f"时间范围查询示例：最近30天的{measure_name}趋势"
        )

    def format_examples_for_prompt(self, examples: list[ExampleSQL]) -> str:
        """
        格式化示例 SQL 为 Prompt 格式

        Args:
            examples: 示例 SQL 列表

        Returns:
            格式化的文本
        """
        if not examples:
            return ""

        lines = ["## 示例 SQL 查询", ""]

        for i, example in enumerate(examples, 1):
            lines.append(f"### 示例 {i}: {example.question}")
            lines.append(f"```sql")
            lines.append(example.sql)
            lines.append(f"```")
            lines.append(f"// {example.description}")
            lines.append("")

        return "\n".join(lines)


def generate_example_sql_for_schema(
    schema: SchemaUnderstanding,
    dialect: str = "postgres",
    max_per_table: int = 3,
) -> list[ExampleSQL]:
    """
    为 Schema 生成示例 SQL

    Args:
        schema: Schema 理解结果
        dialect: SQL 方言
        max_per_table: 每张表最多生成几个示例

    Returns:
        示例 SQL 列表
    """
    generator = ExampleSQLGenerator(schema, dialect)
    return generator.generate_examples(max_per_table)