# NL2SQL Agent 自主执行架构方案

> **目标**：从固定流水线改造为 ReAct Agent 模式，LLM 自主规划、调用工具、迭代优化 SQL

---

## 一、架构演进对比

### 1.1 现有架构（固定 DAG）

```
问题分析 → [并行检索] → 合并 → 元数据分析 → SQL生成 → SQL执行
              ↓
    ┌─────────┼─────────┐
    ↓         ↓         ↓
 知识检索  指标检索  元数据检索
    └─────────┼─────────┘

问题：
- 固定流程，无法跳过或迭代
- LLM 只在 SQL 生成阶段参与
- 重试能力有限（只重试 SQL 生成）
- 无工具选择能力
```

### 1.2 目标架构（ReAct Agent）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NL2SQL ReAct Agent                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                      Agent 主循环 (ReAct)                            │  │
│   │                                                                       │  │
│   │   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐         │  │
│   │   │  Think  │ →  │   Act   │ →  │ Observe │ →  │ Reflect │ → 循环  │  │
│   │   │  思考   │    │  行动   │    │  观察   │    │  反思   │         │  │
│   │   └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘         │  │
│   │        │              │              │              │               │  │
│   │        │              ↓              │              │               │  │
│   │        │     ┌────────────────┐      │              │               │  │
│   │        │     │  Tool Box      │      │              │               │  │
│   │        │     │  工具箱        │      │              │               │  │
│   │        │     ├────────────────┤      │              │               │  │
│   │        │     │ • analyze_question    │              │               │  │
│   │        │     │ • retrieve_knowledge  │              │               │  │
│   │        │     │ • retrieve_metrics    │              │               │  │
│   │        │     │ • retrieve_metadata   │              │               │  │
│   │        │     │ • get_schema          │              │               │  │
│   │        │     │ • generate_sql        │              │               │  │
│   │        │     │ • execute_sql         │              │               │  │
│   │        │     │ • explain_results     │              │               │  │
│   │        │     └────────────────┘      │              │               │  │
│   │        │                             │              │               │  │
│   │        └─────────────────────────────┴──────────────┘               │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│   输入: 用户自然语言问题                                                      │
│   输出: SQL + 执行结果 + 分析解释                                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、核心组件设计

### 2.1 Agent State（状态定义）

```python
from typing import Any, Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentMessage(TypedDict):
    """Agent 消息"""
    role: str  # system/user/assistant/tool
    content: str
    tool_calls: list[dict] | None
    tool_call_id: str | None


class NL2SQLAgentState(TypedDict, total=False):
    """Agent 状态"""
    
    # ===== 输入 =====
    question: str  # 用户问题
    datasource_id: int  # 数据源 ID
    
    # ===== Agent 消息历史 =====
    messages: Annotated[list[AgentMessage], add_messages]
    
    # ===== 思考过程 =====
    thoughts: list[str]  # LLM 思考记录
    current_thought: str  # 当前思考
    
    # ===== 工具调用记录 =====
    tool_history: list[dict[str, Any]]  # 工具调用历史
    
    # ===== 检索结果 =====
    keywords: list[str]  # 提取的关键词
    knowledge_hits: list[dict[str, Any]]
    metrics_hits: list[dict[str, Any]]
    metadata_hits: list[dict[str, Any]]
    mschema_context: str  # M-Schema 上下文
    
    # ===== 表选择 =====
    candidate_tables: list[str]
    selected_tables: list[str]
    selected_joins: list[dict[str, Any]]
    
    # ===== SQL 相关 =====
    generated_sql: str
    sql_rationale: str  # SQL 生成理由
    execution_error: str
    result: dict[str, Any]
    
    # ===== 迭代控制 =====
    iteration: int  # 当前迭代次数
    max_iterations: int  # 最大迭代次数
    should_finish: bool  # 是否应该结束
    
    # ===== 最终输出 =====
    final_answer: str  # 最终回答
```

### 2.2 Tool Box（工具定义）

```python
from langchain_core.tools import tool
from typing import Literal


@tool
def analyze_question(question: str) -> dict:
    """
    分析用户问题，提取关键信息。
    
    Args:
        question: 用户自然语言问题
        
    Returns:
        包含意图、关键词、指标、维度、时间范围的字典
    """
    # LLM 分析问题，提取：
    # - 意图类型（查询/对比/趋势/排名）
    # - 关键词列表
    # - 提及的指标（销售额、订单量等）
    # - 提及的维度（地区、产品、时间等）
    # - 时间范围（最近30天、去年同期等）
    pass


@tool
def retrieve_knowledge(keywords: list[str]) -> list[dict]:
    """
    从企业知识库检索业务术语和示例。
    
    Args:
        keywords: 关键词列表
        
    Returns:
        匹配的知识条目列表
    """
    pass


@tool
def retrieve_metrics(metric_names: list[str]) -> list[dict]:
    """
    检索指标定义和聚合规则。
    
    Args:
        metric_names: 指标名称列表
        
    Returns:
        指标定义列表（含聚合规则、目标字段）
    """
    pass


@tool
def retrieve_metadata(topics: list[str]) -> list[dict]:
    """
    检索业务元数据（表/字段映射）。
    
    Args:
        topics: 主题或指标名称列表
        
    Returns:
        元数据命中列表
    """
    pass


@tool
def get_schema(table_names: list[str] | None = None) -> str:
    """
    获取数据库 Schema 信息（M-Schema 格式）。
    
    Args:
        table_names: 可选，指定表名列表。不传则返回所有表。
        
    Returns:
        M-Schema 格式的表结构描述
    """
    pass


@tool
def generate_sql(
    question: str,
    selected_tables: list[str],
    schema_context: str,
    knowledge_context: str,
    previous_error: str | None = None
) -> dict:
    """
    生成 SQL 查询语句。
    
    Args:
        question: 用户问题
        selected_tables: 选中的表
        schema_context: Schema 上下文
        knowledge_context: 知识上下文
        previous_error: 之前执行失败的错误信息（用于修正）
        
    Returns:
        包含 sql 和 rationale 的字典
    """
    pass


@tool
def execute_sql(sql: str) -> dict:
    """
    执行 SQL 并返回结果。
    
    Args:
        sql: SQL 查询语句
        
    Returns:
        包含 columns、rows 的结果字典
    """
    pass


@tool
def explain_results(question: str, sql: str, result: dict) -> str:
    """
    用自然语言解释查询结果。
    
    Args:
        question: 原始问题
        sql: 执行的 SQL
        result: 查询结果
        
    Returns:
        自然语言解释
    """
    pass


# 工具列表
TOOLS = [
    analyze_question,
    retrieve_knowledge,
    retrieve_metrics,
    retrieve_metadata,
    get_schema,
    generate_sql,
    execute_sql,
    explain_results,
]
```

### 2.3 Agent 节点设计

```python
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode


def agent_think_node(state: NL2SQLAgentState) -> dict:
    """
    Agent 思考节点：LLM 决定下一步行动
    """
    from .llm_provider import create_llm
    from .prompt_templates import AGENT_SYSTEM_PROMPT
    
    llm = create_llm()
    llm_with_tools = llm.bind_tools(TOOLS)
    
    # 构建消息
    messages = state.get("messages", [])
    if not messages:
        messages = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": f"用户问题：{state['question']}"},
        ]
    
    # 调用 LLM
    response = llm_with_tools.invoke(messages)
    
    # 提取思考内容（如果有）
    thought = response.content or ""
    
    return {
        "messages": [response],
        "current_thought": thought,
        "thoughts": state.get("thoughts", []) + [thought] if thought else state.get("thoughts", []),
    }


def should_continue(state: NL2SQLAgentState) -> str:
    """
    条件边：决定是继续调用工具还是结束
    """
    messages = state.get("messages", [])
    if not messages:
        return "think"
    
    last_message = messages[-1]
    
    # 如果有工具调用，继续执行
    if last_message.get("tool_calls"):
        return "tools"
    
    # 如果应该结束
    if state.get("should_finish") or state.get("iteration", 0) >= state.get("max_iterations", 10):
        return END
    
    # 否则继续思考
    return "think"


def agent_reflect_node(state: NL2SQLAgentState) -> dict:
    """
    反思节点：分析执行结果，决定是否需要修正
    """
    from .llm_provider import create_llm
    from .prompt_templates import REFLECTION_PROMPT
    
    llm = create_llm()
    
    # 构建反思上下文
    context = {
        "question": state["question"],
        "generated_sql": state.get("generated_sql", ""),
        "execution_error": state.get("execution_error", ""),
        "result": state.get("result", {}),
        "tool_history": state.get("tool_history", []),
    }
    
    prompt = REFLECTION_PROMPT.format(**context)
    response = llm.invoke(prompt)
    
    # 解析反思结果
    reflection = parse_reflection(response.content)
    
    return {
        "iteration": state.get("iteration", 0) + 1,
        "should_finish": reflection.get("should_finish", False),
        "messages": [{"role": "assistant", "content": response.content}],
    }


def build_agent_graph():
    """
    构建 ReAct Agent 图
    """
    builder = StateGraph(NL2SQLAgentState)
    
    # 添加节点
    builder.add_node("think", agent_think_node)
    builder.add_node("tools", ToolNode(TOOLS))
    builder.add_node("reflect", agent_reflect_node)
    
    # 添加边
    builder.add_edge(START, "think")
    builder.add_edge("tools", "reflect")
    
    # 条件边
    builder.add_conditional_edges("think", should_continue, {
        "tools": "tools",
        "think": "think",
        END: END,
    })
    
    builder.add_conditional_edges("reflect", lambda state: "think" if not state.get("should_finish") else END, {
        "think": "think",
        END: END,
    })
    
    return builder.compile()
```

---

## 三、提示词设计

### 3.1 Agent System Prompt

```python
AGENT_SYSTEM_PROMPT = """你是一个企业级 NL2SQL Agent，负责将自然语言问题转化为 SQL 查询。

## 你的能力

你可以使用以下工具：
1. **analyze_question** - 分析问题，提取意图、关键词、指标、维度、时间范围
2. **retrieve_knowledge** - 从企业知识库检索业务术语
3. **retrieve_metrics** - 检索指标定义和聚合规则
4. **retrieve_metadata** - 检索表/字段映射
5. **get_schema** - 获取数据库表结构（M-Schema）
6. **generate_sql** - 生成 SQL 查询
7. **execute_sql** - 执行 SQL
8. **explain_results** - 用自然语言解释结果

## 工作流程

你应该遵循 ReAct 模式：

1. **Think（思考）**：分析当前状态，决定下一步行动
2. **Act（行动）**：选择并调用合适的工具
3. **Observe（观察）**：观察工具返回结果
4. **Reflect（反思）**：评估结果，决定是否需要修正

## 决策指南

### 问题分析阶段
- 首先调用 `analyze_question` 理解用户意图
- 识别问题中的指标（如"销售额"、"订单量"）
- 识别维度（如"按地区"、"按月份"）
- 识别时间范围（如"最近30天"、"去年同期"）

### 检索阶段
- 根据分析结果，调用 `retrieve_metrics` 获取指标定义
- 调用 `retrieve_metadata` 获取表/字段映射
- 调用 `get_schema` 获取完整的表结构信息

### SQL 生成阶段
- 调用 `generate_sql` 生成 SQL
- 使用检索到的 Schema 和知识上下文
- 确保使用正确的表名和字段名

### 执行和修正阶段
- 调用 `execute_sql` 执行 SQL
- 如果执行失败，分析错误原因
- 可能需要重新检索、修正 SQL、或换表

### 结果解释阶段
- 调用 `explain_results` 用自然语言解释结果
- 回答用户原始问题

## 错误处理

当 SQL 执行失败时：
1. 分析错误类型（语法错误、字段不存在、表不存在等）
2. 如果是字段/表不存在，重新调用 `get_schema` 确认
3. 如果是语法错误，调用 `generate_sql` 时传入 previous_error
4. 最多尝试 3 次修正

## 输出格式

当你完成所有工作后，用以下格式输出最终答案：

```
## 查询结果

[自然语言回答用户问题]

## SQL 语句

```sql
[生成的 SQL]
```

## 数据

[查询结果表格或图表描述]
```
"""
```

### 3.2 Reflection Prompt

```python
REFLECTION_PROMPT = """请分析当前执行状态，决定下一步行动。

## 当前状态

**用户问题**：{question}

**生成的 SQL**：
```sql
{generated_sql}
```

**执行结果**：
- 错误信息：{execution_error}
- 返回数据行数：{result_rows}

**工具调用历史**：
{tool_history}

**当前迭代次数**：{iteration}

## 请回答

1. 当前执行是否成功？
2. 如果失败，原因是什么？（SQL 语法错误 / 字段不存在 / 表不存在 / 数据问题）
3. 需要修正吗？如何修正？
4. 是否应该结束？（已得到结果 / 无法修复 / 达到最大迭代次数）

输出 JSON 格式：
```json
{{
  "success": true/false,
  "error_type": "sql_syntax/field_not_found/table_not_found/data_issue/none",
  "should_retry": true/false,
  "retry_action": "regenerate_sql/retrieve_schema/change_table/none",
  "should_finish": true/false,
  "next_action": "具体下一步行动说明"
}}
```
"""
```

---

## 四、实施路径

### Phase 1: State 和 Tool 定义（0.5 天）

| 步骤 | 文件 | 内容 |
|------|------|------|
| 1.1 | `app/agent_state.py` | 定义 `NL2SQLAgentState` |
| 1.2 | `app/agent_tools.py` | 定义所有 Tool 函数 |
| 1.3 | `app/prompt_templates.py` | 添加 Agent 提示词 |

### Phase 2: Agent 节点开发（1 天）

| 步骤 | 文件 | 内容 |
|------|------|------|
| 2.1 | `app/agent_nodes.py` | 实现 `agent_think_node` |
| 2.2 | `app/agent_nodes.py` | 实现 `agent_reflect_node` |
| 2.3 | `app/agent_nodes.py` | 实现工具调用处理 |

### Phase 3: Graph 构建（0.5 天）

| 步骤 | 文件 | 内容 |
|------|------|------|
| 3.1 | `app/agent_graph.py` | 构建 ReAct Agent 图 |
| 3.2 | `app/agent_graph.py` | 添加条件边和迭代控制 |

### Phase 4: API 集成（0.5 天）

| 步骤 | 文件 | 内容 |
|------|------|------|
| 4.1 | `app/streaming.py` | 适配 Agent SSE 流式输出 |
| 4.2 | `app/main.py` | 添加 Agent 查询路由 |

### Phase 5: 测试与优化（0.5 天）

| 步骤 | 内容 |
|------|------|
| 5.1 | 单元测试：各 Tool 函数 |
| 5.2 | 集成测试：完整 Agent 流程 |
| 5.3 | 性能优化：减少不必要的 LLM 调用 |

---

## 五、关键文件清单

| 文件 | 用途 | 状态 |
|------|------|------|
| `app/agent_state.py` | Agent 状态定义 | 待开发 |
| `app/agent_tools.py` | 工具函数定义 | 待开发 |
| `app/agent_nodes.py` | Agent 节点实现 | 待开发 |
| `app/agent_graph.py` | Agent 图构建 | 待开发 |
| `app/prompt_templates.py` | 提示词模板（扩展）| 待修改 |
| `app/streaming.py` | SSE 流式输出（适配）| 待修改 |

---

## 六、风险与应对

| 风险 | 概率 | 应对策略 |
|------|------|---------|
| LLM 调用次数过多导致成本高 | 高 | 设置 max_iterations=5，缓存检索结果 |
| Agent 陷入死循环 | 中 | 添加 should_finish 强制结束条件 |
| 工具调用失败 | 中 | 添加工具调用重试机制 |
| LLM 生成无效 SQL | 中 | SQL 执行前添加语法校验 |

---

## 七、与现有架构的兼容

### 保留的组件

- `app/tools.py`：现有的检索函数可被 Tool 调用
- `app/learning_service.py`：Schema 学习服务继续使用
- `app/mysql_tools.py`：数据库工具继续使用

### 替换的组件

- `app/state.py` → `app/agent_state.py`
- `app/graph_builder.py` → `app/agent_graph.py`
- `app/nodes.py` → `app/agent_nodes.py`

### 迁移策略

1. 保留原有 `/query` 和 `/stream` 接口
2. 新增 `/agent/query` 和 `/agent/stream` 接口
3. 前端可切换使用新旧接口