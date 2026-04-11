from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.pipeline.nodes import (
    analyze_question_node,
    embedding_generation_node,
    knowledge_retrieval_node,
    merge_context_node,
    metadata_analysis_node,
    metadata_retrieval_node,
    metrics_retrieval_node,
    sql_execution_node,
    sql_generation_node,
)
from app.pipeline.state import NL2SQLState


def build_graph():
    """
    梭子形主流程（Phase 3 增强：混合检索 + RRF 融合）：

    QuestionAnalyzer -> EmbeddingGeneration -> Supervisor(隐含在图的 fan-out) ->
    并行检索(spokes, 混合检索) -> 汇总 -> MetadataAnalysis -> SQLGeneration -> SQLExecution

    新增 embedding_generation_node：
    - 在 analyze_question 后执行
    - 生成问题的向量用于混合检索
    - 如果 QWEN_API_KEY 未配置，跳过向量生成
    """
    builder = StateGraph(NL2SQLState)

    builder.add_node("analyze_question", analyze_question_node)
    builder.add_node("embedding_generation", embedding_generation_node)
    builder.add_node("knowledge_retrieval", knowledge_retrieval_node)
    builder.add_node("metrics_retrieval", metrics_retrieval_node)
    builder.add_node("metadata_retrieval", metadata_retrieval_node)
    builder.add_node("merge_context", merge_context_node)
    builder.add_node("metadata_analysis", metadata_analysis_node)
    builder.add_node("sql_generation", sql_generation_node)
    builder.add_node("sql_execution", sql_execution_node)

    # Entry: analyze_question -> embedding_generation
    builder.add_edge(START, "analyze_question")
    builder.add_edge("analyze_question", "embedding_generation")

    # Fan-out: embedding_generation -> parallel retrieval nodes
    builder.add_edge("embedding_generation", "knowledge_retrieval")
    builder.add_edge("embedding_generation", "metrics_retrieval")
    builder.add_edge("embedding_generation", "metadata_retrieval")

    # Fan-in: merge_context 依赖三条 spoke 的输出（并行执行）
    builder.add_edge("knowledge_retrieval", "merge_context")
    builder.add_edge("metrics_retrieval", "merge_context")
    builder.add_edge("metadata_retrieval", "merge_context")

    builder.add_edge("merge_context", "metadata_analysis")
    builder.add_edge("metadata_analysis", "sql_generation")
    builder.add_edge("sql_generation", "sql_execution")

    def route_after_sql_execution(state: NL2SQLState):
        if state.get("execution_error"):
            # execution_error 非空，进入重试（在 sql_execution_node 内 attempt 已经递增）
            if int(state.get("attempt", 1)) < int(state.get("max_attempts", 2)):
                return "sql_generation"
        return END

    builder.add_conditional_edges("sql_execution", route_after_sql_execution)
    return builder.compile()

