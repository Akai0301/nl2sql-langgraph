"""
Schema 字段分类器：基于 XiYan 算法对字段进行分类。

分类类型：
- DateTime: 时间日期类型，自动推断颗粒度
- Enum: 枚举类型，取值有限且固定（DISTINCT < 20）
- Code: 编码类型，有特定业务意义的编码（如 ID、产品编码）
- Text: 自由文本，无固定格式
- Measure: 度量类型，可进行聚合计算的数值

分类结果用于：
1. 确定 SQL 生成时的维度/度量角色
2. 选择合适的聚合函数
3. 推断时间字段的筛选条件
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

from app.core.config_service import AIModelConfig
from app.core.llm_provider import create_llm

if TYPE_CHECKING:
    from app.schema.engine import FieldInfo, SchemaUnderstanding

FieldType = Literal["DateTime", "Enum", "Code", "Text", "Measure"]


class SchemaClassifier:
    """字段分类器 - 基于 XiYan 算法"""

    # 时间类型关键词
    DATETIME_KEYWORDS = [
        "date", "time", "datetime", "timestamp", "year", "month", "day", "hour", "minute", "second",
        "created", "updated", "deleted", "时间", "日期", "创建", "更新", "删除",
    ]

    # ID 类关键词
    ID_KEYWORDS = [
        "id", "_id", "code", "_code", "no", "_no", "number", "_number",
        "key", "_key", "uuid", "guid",
    ]

    # 度量类关键词
    MEASURE_KEYWORDS = [
        "amount", "price", "cost", "total", "sum", "count", "avg", "average",
        "qty", "quantity", "value", "money", "fee", "rate", "ratio", "percent",
        "金额", "数量", "价格", "费用", "总计", "平均值", "比率", "占比",
    ]

    # 枚举类关键词
    ENUM_KEYWORDS = [
        "status", "type", "level", "gender", "sex", "state", "flag", "category",
        "status", "type", "level", "gender", "sex", "state", "flag", "category",
        "状态", "类型", "级别", "性别", "类别", "分类",
    ]

    def __init__(self, llm_config: AIModelConfig | None = None):
        """
        初始化分类器

        Args:
            llm_config: LLM 配置（可选，用于复杂字段的分类）
        """
        self.llm = create_llm(llm_config) if llm_config and llm_config.provider != "mock" else None

    def classify_field(
        self,
        field: "FieldInfo",
        examples: list[str] | None = None,
    ) -> "FieldInfo":
        """
        分类单个字段

        Args:
            field: 字段信息
            examples: 示例值列表（可选，优先使用 field.examples）

        Returns:
            更新了分类信息的字段
        """
        examples = examples or field.examples or []
        type_upper = field.type.upper()

        # 1. DateTime 判断
        if self._is_datetime_type(type_upper):
            field.category = "DateTime"
            field.date_min_gran = self._infer_date_granularity(examples)
            field.dim_or_meas = "Dimension"
            return field

        # 2. Bool 判断
        if "BOOL" in type_upper:
            field.category = "Enum"
            field.dim_or_meas = "Dimension"
            return field

        # 3. 根据示例值数量判断 Enum
        if 0 < len(examples) <= 20:
            # 如果示例值数量有限，可能是 Enum
            if self._looks_like_enum(field.name, examples):
                field.category = "Enum"
                field.dim_or_meas = "Dimension"
                return field

        # 4. 数值类型：判断 Measure vs Code
        if self._is_numeric_type(type_upper):
            if self._is_code_field(field.name):
                field.category = "Code"
                field.dim_or_meas = "Dimension"
            else:
                field.category = "Measure"
                field.dim_or_meas = "Measure"
            return field

        # 5. 字符串类型：根据名称和示例判断
        if self._is_string_type(type_upper):
            # 先检查是否是已知的枚举字段
            if self._is_enum_field(field.name):
                field.category = "Enum"
                field.dim_or_meas = "Dimension"
                return field

            # 检查是否是 ID 类
            if self._is_code_field(field.name):
                field.category = "Code"
                field.dim_or_meas = "Dimension"
                return field

            # 检查示例值是否像枚举
            if examples and len(examples) <= 20:
                if self._looks_like_enum(field.name, examples):
                    field.category = "Enum"
                    field.dim_or_meas = "Dimension"
                    return field

            # 默认为 Text
            field.category = "Text"
            field.dim_or_meas = "Dimension"
            return field

        # 6. 默认
        field.category = "Text"
        field.dim_or_meas = "Dimension"
        return field

    def classify_schema(self, schema: "SchemaUnderstanding") -> "SchemaUnderstanding":
        """
        分类整个 Schema

        Args:
            schema: Schema 理解结果

        Returns:
            更新了分类信息的 Schema
        """
        for table_name, table in schema.tables.items():
            for field_name, field in table.fields.items():
                self.classify_field(field)

        return schema

    def _is_datetime_type(self, type_upper: str) -> bool:
        """判断是否是时间类型"""
        datetime_types = [
            "DATE", "TIME", "DATETIME", "TIMESTAMP",
            "YEAR", "TIMESTAMPTZ", "TIMESTAMP WITH TIME ZONE",
        ]
        return any(t in type_upper for t in datetime_types)

    def _is_numeric_type(self, type_upper: str) -> bool:
        """判断是否是数值类型"""
        numeric_types = [
            "INT", "INTEGER", "BIGINT", "SMALLINT", "TINYINT",
            "DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "REAL",
            "MONEY", "CURRENCY",
        ]
        return any(t in type_upper for t in numeric_types)

    def _is_string_type(self, type_upper: str) -> bool:
        """判断是否是字符串类型"""
        string_types = [
            "CHAR", "VARCHAR", "TEXT", "STRING",
            "NCHAR", "NVARCHAR", "NTEXT",
            "CLOB", "NCLOB",
        ]
        return any(t in type_upper for t in string_types)

    def _is_code_field(self, field_name: str) -> bool:
        """判断是否是编码字段"""
        name_lower = field_name.lower()
        return any(kw in name_lower for kw in self.ID_KEYWORDS)

    def _is_enum_field(self, field_name: str) -> bool:
        """判断是否是枚举字段"""
        name_lower = field_name.lower()
        return any(kw in name_lower for kw in self.ENUM_KEYWORDS)

    def _looks_like_enum(self, field_name: str, examples: list[str]) -> bool:
        """
        根据示例值判断是否像枚举

        判断依据：
        1. 所有示例值长度较短（< 50 字符）
        2. 示例值不是纯数字（排除 ID）
        3. 字段名包含枚举关键词
        """
        if not examples:
            return False

        # 检查示例值长度
        avg_len = sum(len(str(e)) for e in examples) / len(examples)
        if avg_len > 50:
            return False

        # 检查是否是纯数字（可能是 ID）
        all_numeric = all(
            re.match(r"^\d+\.?\d*$", str(e)) is not None
            for e in examples
        )
        if all_numeric:
            return False

        # 字段名包含枚举关键词
        if self._is_enum_field(field_name):
            return True

        return True

    def _infer_date_granularity(self, examples: list[str]) -> str:
        """
        推断时间字段最小颗粒度

        颗粒度层级：YEAR < MONTH < DAY < HOUR < MINUTE < SECOND
        """
        if not examples:
            return "DAY"

        example = str(examples[0])

        # 根据格式推断
        # YYYY-MM-DD HH:mm:ss
        if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", example):
            return "SECOND"
        # YYYY-MM-DD HH:mm
        if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}", example):
            return "MINUTE"
        # YYYY-MM-DD HH
        if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}", example):
            return "HOUR"
        # YYYY-MM-DD
        if re.match(r"^\d{4}-\d{2}-\d{2}", example):
            return "DAY"
        # YYYY-MM
        if re.match(r"^\d{4}-\d{2}", example):
            return "MONTH"
        # YYYY
        if re.match(r"^\d{4}$", example):
            return "YEAR"

        # 根据长度推断
        if len(example) <= 4:
            return "YEAR"
        elif len(example) <= 7:
            return "MONTH"
        elif len(example) <= 10:
            return "DAY"
        elif len(example) <= 13:
            return "HOUR"
        elif len(example) <= 16:
            return "MINUTE"

        return "SECOND"

    def infer_table_type(
        self,
        table: "TableInfo",
    ) -> Literal["fact", "dimension", "other"]:
        """
        推断表的类型

        判断规则：
        - 事实表：包含 Measure 类型字段 + 时间字段 + 可聚合
        - 维度表：主键是 Code 类型 + 包含多个 Dimension 字段 + 无 Measure 字段
        - 其他：不符合以上规则的表

        Args:
            table: 表信息

        Returns:
            表类型
        """
        has_measure = any(
            f.category == "Measure" or f.dim_or_meas == "Measure"
            for f in table.fields.values()
        )
        has_time = any(
            f.category == "DateTime"
            for f in table.fields.values()
        )
        has_dim = any(
            f.dim_or_meas == "Dimension"
            for f in table.fields.values()
        )

        if has_measure and has_time:
            return "fact"
        elif has_dim and not has_measure:
            return "dimension"

        return "other"

    def get_table_time_field(self, table: "TableInfo") -> str | None:
        """
        获取表的时间字段

        优先选择：
        1. 主键中的时间字段
        2. 名称包含 created/updated 的时间字段
        3. 第一个 DateTime 类型字段

        Args:
            table: 表信息

        Returns:
            时间字段名，如果没有则返回 None
        """
        datetime_fields = [
            (name, field)
            for name, field in table.fields.items()
            if field.category == "DateTime"
        ]

        if not datetime_fields:
            return None

        # 优先选择主键中的时间字段
        for name, field in datetime_fields:
            if field.primary_key:
                return name

        # 其次选择 created/updated 相关字段
        for name, field in datetime_fields:
            name_lower = name.lower()
            if any(kw in name_lower for kw in ["created", "updated", "create", "update"]):
                return name

        # 最后选择第一个 DateTime 字段
        return datetime_fields[0][0]

    def get_table_measure_fields(self, table: "TableInfo") -> list[str]:
        """
        获取表的度量字段列表

        Args:
            table: 表信息

        Returns:
            度量字段名列表
        """
        return [
            name
            for name, field in table.fields.items()
            if field.category == "Measure" or field.dim_or_meas == "Measure"
        ]

    def get_table_dimension_fields(self, table: "TableInfo") -> list[str]:
        """
        获取表的维度字段列表

        Args:
            table: 表信息

        Returns:
            维度字段名列表
        """
        return [
            name
            for name, field in table.fields.items()
            if field.dim_or_meas == "Dimension"
        ]