"""
SQL 验证修正服务：执行前检查 SQL 的有效性并尝试自动修正。

核心功能：
1. 表名验证：检查 SQL 中引用的表是否存在于数据源
2. 字段名验证：检查字段名是否存在于对应表中
3. 自动修正：根据 Schema 信息修正常见的字段名错误
4. 语法检查：基本的 SQL 语法验证
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

import sqlglot
from sqlglot import exp


@dataclass
class ValidationError:
    """验证错误"""
    error_type: str  # table_not_found, column_not_found, syntax_error
    message: str
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    original_sql: str
    corrected_sql: Optional[str] = None
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    corrections: list[str] = field(default_factory=list)


class SQLValidator:
    """SQL 验证器"""

    def __init__(self, schema_cache: dict[str, Any] | None = None):
        """
        初始化验证器

        Args:
            schema_cache: 从 schema_cache 表获取的 Schema 信息
                格式: {"tables": {"table_name": {"fields": {...}, "comment": ...}}}
        """
        self.schema_cache = schema_cache

    def validate_and_correct(self, sql: str, dialect: str = "postgres") -> ValidationResult:
        """
        验证并修正 SQL

        Args:
            sql: 待验证的 SQL
            dialect: SQL 方言（postgres, mysql, sqlite）

        Returns:
            ValidationResult 包含验证结果和修正后的 SQL
        """
        result = ValidationResult(is_valid=True, original_sql=sql)

        # 1. 语法检查
        syntax_errors = self._check_syntax(sql, dialect)
        if syntax_errors:
            result.is_valid = False
            result.errors.extend(syntax_errors)
            return result

        # 2. 如果没有 Schema 缓存，跳过表/字段验证
        if not self.schema_cache:
            result.warnings.append("未提供 Schema 缓存，跳过表/字段验证")
            return result

        # 3. 提取 SQL 中的表和字段
        try:
            parsed = sqlglot.parse(sql, dialect=dialect)
            if not parsed or not parsed[0]:
                result.errors.append(ValidationError(
                    error_type="syntax_error",
                    message="无法解析 SQL"
                ))
                result.is_valid = False
                return result

            ast = parsed[0]

            # 4. 验证表名
            tables_in_sql = self._extract_tables(ast)
            table_errors, table_corrections = self._validate_tables(tables_in_sql)
            result.errors.extend(table_errors)
            result.corrections.extend(table_corrections)

            # 5. 验证字段名
            column_errors, column_corrections = self._validate_columns(ast, tables_in_sql)
            result.errors.extend(column_errors)
            result.corrections.extend(column_corrections)

            # 6. 如果有修正，生成修正后的 SQL
            if result.corrections:
                result.corrected_sql = self._apply_corrections(sql, result.corrections, dialect)

            # 7. 更新验证状态
            if result.errors:
                # 只有表不存在或严重语法错误才标记为无效
                critical_errors = [e for e in result.errors if e.error_type == "table_not_found"]
                if critical_errors:
                    result.is_valid = False

        except Exception as e:
            result.warnings.append(f"SQL 解析警告: {str(e)}")

        return result

    def _check_syntax(self, sql: str, dialect: str) -> list[ValidationError]:
        """检查 SQL 语法"""
        errors = []
        try:
            sqlglot.parse(sql, dialect=dialect)
        except sqlglot.errors.ParseError as e:
            errors.append(ValidationError(
                error_type="syntax_error",
                message=f"SQL 语法错误: {str(e)}"
            ))
        return errors

    def _extract_tables(self, ast: exp.Expression) -> list[str]:
        """从 AST 中提取表名"""
        tables = []
        for table in ast.find_all(exp.Table):
            table_name = table.name
            if table_name:
                tables.append(table_name)
        return list(set(tables))

    def _validate_tables(self, tables: list[str]) -> tuple[list[ValidationError], list[str]]:
        """验证表名"""
        errors = []
        corrections = []

        if not self.schema_cache:
            return errors, corrections

        schema_tables = set(self.schema_cache.get("tables", {}).keys())

        for table_name in tables:
            # 直接匹配
            if table_name in schema_tables:
                continue

            # 大小写不敏感匹配
            matched = None
            for schema_table in schema_tables:
                if table_name.lower() == schema_table.lower():
                    matched = schema_table
                    break

            if matched:
                corrections.append(f"表名修正: {table_name} → {matched}")
            else:
                # 尝试模糊匹配（编辑距离）
                similar = self._find_similar_table(table_name, schema_tables)
                if similar:
                    errors.append(ValidationError(
                        error_type="table_not_found",
                        message=f"表 '{table_name}' 不存在",
                        table_name=table_name,
                        suggestion=f"您是否指 '{similar}'？"
                    ))
                else:
                    errors.append(ValidationError(
                        error_type="table_not_found",
                        message=f"表 '{table_name}' 不存在于数据源中",
                        table_name=table_name
                    ))

        return errors, corrections

    def _validate_columns(self, ast: exp.Expression, tables: list[str]) -> tuple[list[ValidationError], list[str]]:
        """验证字段名"""
        errors = []
        corrections = []

        if not self.schema_cache:
            return errors, corrections

        schema_tables = self.schema_cache.get("tables", {})

        # 获取所有字段引用
        for column in ast.find_all(exp.Column):
            column_name = column.name
            table_name = column.table if column.table else None

            # 如果字段名是 *，跳过
            if column_name == "*":
                continue

            # 确定要检查的表
            tables_to_check = [table_name] if table_name else tables

            for tbl in tables_to_check:
                if tbl not in schema_tables:
                    # 表不存在，已在表验证中报告
                    continue

                schema_fields = schema_tables[tbl].get("fields", {})
                field_names = set(schema_fields.keys())

                # 直接匹配
                if column_name in field_names:
                    continue

                # 大小写不敏感匹配
                matched = None
                for field_name in field_names:
                    if column_name.lower() == field_name.lower():
                        matched = field_name
                        break

                if matched:
                    corrections.append(f"字段修正: {tbl}.{column_name} → {tbl}.{matched}")
                else:
                    # 尝试模糊匹配
                    similar = self._find_similar_field(column_name, field_names)
                    if similar:
                        errors.append(ValidationError(
                            error_type="column_not_found",
                            message=f"字段 '{column_name}' 不存在于表 '{tbl}' 中",
                            table_name=tbl,
                            column_name=column_name,
                            suggestion=f"您是否指 '{similar}'？"
                        ))
                    else:
                        errors.append(ValidationError(
                            error_type="column_not_found",
                            message=f"字段 '{column_name}' 不存在于表 '{tbl}' 中",
                            table_name=tbl,
                            column_name=column_name
                        ))

        return errors, corrections

    def _find_similar_table(self, table_name: str, schema_tables: set[str]) -> Optional[str]:
        """查找相似的表名（基于编辑距离）"""
        def levenshtein_distance(s1: str, s2: str) -> int:
            if len(s1) < len(s2):
                return levenshtein_distance(s2, s1)
            if len(s2) == 0:
                return len(s1)
            previous_row = range(len(s2) + 1)
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row
            return previous_row[-1]

        best_match = None
        min_distance = float('inf')

        for schema_table in schema_tables:
            distance = levenshtein_distance(table_name.lower(), schema_table.lower())
            # 编辑距离阈值：最多允许 3 个字符差异
            if distance < min_distance and distance <= 3:
                min_distance = distance
                best_match = schema_table

        return best_match

    def _find_similar_field(self, field_name: str, schema_fields: set[str]) -> Optional[str]:
        """查找相似的字段名"""
        return self._find_similar_table(field_name, schema_fields)  # 复用同样的逻辑

    def _apply_corrections(self, sql: str, corrections: list[str], dialect: str) -> str:
        """应用修正到 SQL"""
        corrected_sql = sql

        for correction in corrections:
            # 解析修正信息
            if "表名修正:" in correction:
                match = re.search(r"表名修正: (\w+) → (\w+)", correction)
                if match:
                    old_name, new_name = match.groups()
                    # 替换表名（保留大小写匹配）
                    corrected_sql = re.sub(
                        rf'\b{re.escape(old_name)}\b',
                        new_name,
                        corrected_sql,
                        flags=re.IGNORECASE
                    )
            elif "字段修正:" in correction:
                match = re.search(r"字段修正: \w+\.(\w+) → \w+\.(\w+)", correction)
                if match:
                    old_name, new_name = match.groups()
                    corrected_sql = re.sub(
                        rf'\b{re.escape(old_name)}\b',
                        new_name,
                        corrected_sql,
                        flags=re.IGNORECASE
                    )

        return corrected_sql


def validate_sql_with_schema(
    sql: str,
    datasource_id: int,
    dialect: str = "postgres"
) -> ValidationResult:
    """
    使用数据源的 Schema 缓存验证 SQL

    Args:
        sql: 待验证的 SQL
        datasource_id: 数据源 ID
        dialect: SQL 方言

    Returns:
        ValidationResult
    """
    from .tools import fetch_schema_cache

    # 获取 Schema 缓存
    cache = fetch_schema_cache(datasource_id)

    if not cache:
        return ValidationResult(
            is_valid=True,
            original_sql=sql,
            warnings=["数据源未完成 Schema 学习，跳过验证"]
        )

    validator = SQLValidator(cache.schema_json)
    return validator.validate_and_correct(sql, dialect)


def format_validation_result(result: ValidationResult) -> str:
    """
    格式化验证结果为可读文本

    Args:
        result: 验证结果

    Returns:
        格式化的文本
    """
    lines = []

    if result.is_valid:
        lines.append("✅ SQL 验证通过")
    else:
        lines.append("❌ SQL 验证失败")

    if result.errors:
        lines.append("\n**错误:**")
        for error in result.errors:
            lines.append(f"- [{error.error_type}] {error.message}")
            if error.suggestion:
                lines.append(f"  💡 建议: {error.suggestion}")

    if result.warnings:
        lines.append("\n**警告:**")
        for warning in result.warnings:
            lines.append(f"- {warning}")

    if result.corrections:
        lines.append("\n**自动修正:**")
        for correction in result.corrections:
            lines.append(f"- {correction}")

    if result.corrected_sql:
        lines.append(f"\n**修正后的 SQL:**\n```sql\n{result.corrected_sql}\n```")

    return "\n".join(lines)