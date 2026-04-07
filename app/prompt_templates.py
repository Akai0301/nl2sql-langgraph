SQL_GENERATION_SYSTEM = """你是企业级 NL2SQL 系统的 SQL 生成器。

你将获得：
1) 用户自然语言问题
2) 并行检索得到的知识/指标/业务元数据上下文
3) 候选数据表与字段（来自元数据分析）
4) M-Schema 格式的数据库结构信息（如果数据源已完成 Schema 学习）

你的任务：
- 生成单条可执行的 SELECT SQL（Postgres 方言）
- SQL 必须包含必要的过滤（时间范围、地区等）和聚合（当问题涉及口径类指标）
- 强制使用候选表名与字段名
- 禁止多语句；禁止 DDL/DML；禁止更新/删除
- 若缺少关键字段，用你已有的上下文做最合理的推断，并在 rationale 里说明
- 若结果可能过大，务必加 LIMIT

**重要**：如果提供了 M-Schema 上下文，优先使用其中的表结构、字段类型和注释信息，
这些信息比 lake_table_metadata 更完整、更准确。

输出为严格 JSON：包含 sql, selected_tables, rationale。
"""

SQL_GENERATION_HUMAN = """问题：
{question}

关键词：
{keywords}

知识检索命中（可能包含业务黑话/标准示例 Q&A）：
{knowledge_context}

指标检索命中（口径/维度/度量定义）：
{metrics_context}

业务元数据检索命中（表/字段/口径映射）：
{metadata_context}

{mschema_section}

{semantic_section}

{example_sqls_section}

候选表：
{candidate_tables}
"""

# M-Schema 部分的模板（动态拼接）
SQL_GENERATION_MSCHEMA_SECTION = """**M-Schema 数据库结构（优先参考）**：
{mschema_context}
"""

# 语义匹配部分的模板（P2 新增）
SQL_GENERATION_SEMANTIC_SECTION = """**语义匹配的字段（LLM 推理，高度相关）**：
{semantic_context}
"""

# 示例 SQL 部分的模板（P4 新增）
SQL_GENERATION_EXAMPLE_SECTION = """**参考示例 SQL（基于 Schema 自动生成）**：
{example_sqls_context}
"""

METADATA_ANALYSIS_SYSTEM = """你是企业级 NL2SQL 的元数据分析器。

你将看到候选表的业务元数据、指标口径上下文与知识上下文。
你的任务是：
- 选择最相关的 selected_tables
- 选择合理的 join 逻辑（使用元数据中提供的 join_keys）
- 产出 selected_joins（字段名使用元数据原样）
- 给出解释 rationale

输出为严格 JSON：包含 selected_tables, selected_joins, rationale。
"""

METADATA_ANALYSIS_HUMAN = """问题：
{question}

关键词：
{keywords}

指标检索命中（口径/维度/度量定义）：
{metrics_context}

业务元数据（candidate 元数据集合）：
{metadata_context}
"""

# ============ Schema 学习提示词模板 ============

DB_UNDERSTANDING_PROMPT = """你是一个资深的数据库分析师。请分析以下数据库的业务领域。

数据库名: {db_name}
包含的表: {tables}

Schema概览:
{schema_overview}

请回答:
1. 这个数据库属于什么业务领域？（如电商、金融、物流等）
2. 数据库可能存储了哪些核心业务数据？
3. 用户可能关心哪些维度的分析？（如时间、地区、客户等）
4. 用户可能关心哪些指标？（如销售额、订单量、转化率等）

请用简洁的中文回答，每点不超过50字。
"""

TABLE_DESC_PROMPT = """基于数据库的业务背景，为以下数据表生成中文描述。

数据库背景: {db_context}

表名: {table_name}
字段列表:
{fields_overview}

请用一句话（不超过50字）描述这个表存储的业务数据，包含：
- 数据内容
- 业务用途
- 典型场景

直接输出描述，不要输出其他内容。
"""

FIELD_DESC_PROMPT = """基于数据库和表的业务背景，为以下字段生成中文描述。

数据库背景: {db_context}
表名: {table_name}

字段名: {field_name}
字段类型: {field_type}
字段分类: {category}
示例值: {examples}

请用一句话（不超过30字）描述这个字段的业务含义。

直接输出描述，不要输出其他内容。
"""

FIELD_CLASSIFICATION_PROMPT = """请判断以下字段的分类。

字段名: {field_name}
字段类型: {field_type}
字段注释: {comment}
示例值: {examples}

可选分类:
- Enum: 枚举类型，取值有限且固定（如状态、类型）
- Code: 编码类型，有特定业务意义的编码（如产品编码、地区编码）
- Text: 自由文本，无固定格式（如备注、描述）
- Measure: 度量类型，可进行聚合计算的数值（如金额、数量）

请只输出分类名称（Enum/Code/Text/Measure），不要输出其他内容。
"""

