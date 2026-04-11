"""SSE streaming support for LangGraph execution progress."""
from __future__ import annotations

import json
import time
from typing import Any, AsyncGenerator

from app.pipeline.graph_builder import build_graph


# Node display names for frontend
NODE_LABELS = {
    "analyze_question": "问题分析",
    "embedding_generation": "向量生成",
    "knowledge_retrieval": "知识检索",
    "metrics_retrieval": "指标检索",
    "metadata_retrieval": "元数据检索",
    "merge_context": "上下文合并",
    "metadata_analysis": "元数据分析",
    "sql_generation": "SQL生成",
    "sql_execution": "SQL执行",
}

# Graph structure for frontend visualization
GRAPH_STRUCTURE = {
    "nodes": [
        {"id": "start", "label": "开始", "type": "start"},
        {"id": "analyze_question", "label": "问题分析", "type": "process"},
        {"id": "embedding_generation", "label": "向量生成", "type": "process"},
        {"id": "knowledge_retrieval", "label": "知识检索", "type": "parallel"},
        {"id": "metrics_retrieval", "label": "指标检索", "type": "parallel"},
        {"id": "metadata_retrieval", "label": "元数据检索", "type": "parallel"},
        {"id": "merge_context", "label": "上下文合并", "type": "process"},
        {"id": "metadata_analysis", "label": "元数据分析", "type": "process"},
        {"id": "sql_generation", "label": "SQL生成", "type": "process"},
        {"id": "sql_execution", "label": "SQL执行", "type": "process"},
        {"id": "end", "label": "结束", "type": "end"},
    ],
    "edges": [
        {"source": "start", "target": "analyze_question"},
        {"source": "analyze_question", "target": "embedding_generation"},
        {"source": "embedding_generation", "target": "knowledge_retrieval"},
        {"source": "embedding_generation", "target": "metrics_retrieval"},
        {"source": "embedding_generation", "target": "metadata_retrieval"},
        {"source": "knowledge_retrieval", "target": "merge_context"},
        {"source": "metrics_retrieval", "target": "merge_context"},
        {"source": "metadata_retrieval", "target": "merge_context"},
        {"source": "merge_context", "target": "metadata_analysis"},
        {"source": "metadata_analysis", "target": "sql_generation"},
        {"source": "sql_generation", "target": "sql_execution"},
        {"source": "sql_execution", "target": "end"},
    ],
}


def _serialize_output(output: Any) -> dict[str, Any]:
    """Serialize node output for JSON transmission."""
    if isinstance(output, dict):
        return {k: _safe_serialize(v) for k, v in output.items()}
    return {"value": _safe_serialize(output)}


def _safe_serialize(value: Any) -> Any:
    """Safely serialize a value for JSON."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    # Handle Decimal type from database
    from decimal import Decimal
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (list, tuple)):
        return [_safe_serialize(v) for v in value]
    if isinstance(value, dict):
        return {k: _safe_serialize(v) for k, v in value.items()}
    return str(value)


def _sse_event(event: str, data: dict[str, Any]) -> str:
    """Create an SSE event string with JSON-serialized data."""
    # Use _safe_serialize to handle Decimal and other non-JSON types
    safe_data = _safe_serialize(data)
    json_data = json.dumps(safe_data, ensure_ascii=False)
    return f"event: {event}\ndata: {json_data}\n\n"


async def stream_query_execution(
    question: str,
    max_attempts: int = 2,
) -> AsyncGenerator[str, None]:
    """
    Execute the LangGraph with streaming progress updates.
    Yields SSE events for each node execution.
    """
    graph = build_graph()
    initial_state: dict[str, Any] = {
        "question": question,
        "attempt": 1,
        "max_attempts": max_attempts,
    }

    # Yield initial state with graph structure
    yield _sse_event("init", {
        "graph": GRAPH_STRUCTURE,
        "question": question,
    })

    # Track node statuses
    node_statuses: dict[str, str] = {}

    valid_nodes = [
        "analyze_question", "embedding_generation", "knowledge_retrieval", "metrics_retrieval",
        "metadata_retrieval", "merge_context", "metadata_analysis",
        "sql_generation", "sql_execution"
    ]

    # Use astream_events for detailed progress tracking
    try:
        async for event in graph.astream_events(initial_state, version="v2"):
            event_kind = event.get("event")

            if event_kind == "on_chain_start":
                node_name = event.get("name", "")
                if node_name in valid_nodes:
                    node_statuses[node_name] = "running"
                    yield _sse_event("node_start", {
                        "node": node_name,
                        "label": NODE_LABELS.get(node_name, node_name),
                        "status": "running",
                    })

            elif event_kind == "on_chain_end":
                node_name = event.get("name", "")
                output = event.get("data", {}).get("output", {})
                if node_name in valid_nodes:
                    node_statuses[node_name] = "completed"
                    yield _sse_event("node_complete", {
                        "node": node_name,
                        "label": NODE_LABELS.get(node_name, node_name),
                        "status": "completed",
                        "output": _serialize_output(output),
                    })

            elif event_kind == "on_chain_error":
                node_name = event.get("name", "")
                error_msg = event.get("data", {}).get("error", "Unknown error")
                if node_name:
                    node_statuses[node_name] = "error"
                    yield _sse_event("node_error", {
                        "node": node_name,
                        "label": NODE_LABELS.get(node_name, node_name),
                        "status": "error",
                        "error": str(error_msg),
                    })

    except Exception as e:
        yield _sse_event("error", {"error": str(e)})
        return

    # Get final state from synchronous invoke for result
    final_state = graph.invoke(initial_state)
    result = final_state.get("result") or {}

    # Yield final result
    yield _sse_event("result", {
        "question": final_state.get("question") or question,
        "sql": final_state.get("generated_sql"),
        "columns": result.get("columns") or [],
        "rows": result.get("rows") or [],
        "attempt": int(final_state.get("attempt", 1)),
        "execution_error": final_state.get("execution_error") or None,
    })


async def stream_query_simple(
    question: str,
    max_attempts: int = 2,
    session_id: int | None = None,
    datasource_id: int | None = None,
) -> AsyncGenerator[str, None]:
    """
    Simple streaming that executes nodes sequentially and yields progress.
    Used when astream_events is not available or graph is not async.
    """
    import app.pipeline.nodes as nodes

    # 设置数据源（如果指定）
    if datasource_id:
        from app.core.datasource_manager import set_current_datasource
        set_current_datasource(datasource_id)

    # Yield initial state with graph structure
    yield _sse_event("init", {
        "graph": GRAPH_STRUCTURE,
        "question": question,
    })

    state: dict[str, Any] = {
        "question": question,
        "attempt": 1,
        "max_attempts": max_attempts,
        "datasource_id": datasource_id,
    }

    # Track timing and token usage
    node_timings: dict[str, dict[str, float]] = {}
    total_start_time = time.time()
    token_usage: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    # Execute nodes in order
    node_sequence = [
        ("analyze_question", nodes.analyze_question_node),
        ("embedding_generation", nodes.embedding_generation_node),
        ("knowledge_retrieval", nodes.knowledge_retrieval_node),
        ("metrics_retrieval", nodes.metrics_retrieval_node),
        ("metadata_retrieval", nodes.metadata_retrieval_node),
        ("merge_context", nodes.merge_context_node),
        ("metadata_analysis", nodes.metadata_analysis_node),
        ("sql_generation", nodes.sql_generation_node),
        ("sql_execution", nodes.sql_execution_node),
    ]

    for node_name, node_func in node_sequence:
        # Record start time
        node_start_time = time.time()

        # Yield node start
        yield _sse_event("node_start", {
            "node": node_name,
            "label": NODE_LABELS.get(node_name, node_name),
            "status": "running",
        })

        try:
            # Execute node (handle async functions)
            import asyncio
            if asyncio.iscoroutinefunction(node_func):
                output = await node_func(state)
            else:
                output = node_func(state)
            state.update(output)

            # Record end time and calculate duration
            node_end_time = time.time()
            duration_ms = round((node_end_time - node_start_time) * 1000, 1)
            node_timings[node_name] = {
                "start": node_start_time,
                "end": node_end_time,
                "duration_ms": duration_ms,
            }

            # Extract token usage from sql_generation output (if available)
            if node_name == "sql_generation" and output:
                if "token_usage" in output:
                    tu = output["token_usage"]
                    if isinstance(tu, dict):
                        token_usage["prompt_tokens"] += tu.get("prompt_tokens", 0)
                        token_usage["completion_tokens"] += tu.get("completion_tokens", 0)
                        token_usage["total_tokens"] += tu.get("total_tokens", 0)

            # Yield node complete with timing
            yield _sse_event("node_complete", {
                "node": node_name,
                "label": NODE_LABELS.get(node_name, node_name),
                "status": "completed",
                "output": _serialize_output(output),
                "duration_ms": duration_ms,
            })

            # Check for retry after sql_execution
            if node_name == "sql_execution" and state.get("execution_error"):
                if state.get("attempt", 1) < state.get("max_attempts", 2):
                    # Retry: go back to sql_generation
                    yield _sse_event("retry", {
                        "attempt": state.get("attempt"),
                        "max_attempts": state.get("max_attempts"),
                        "error": state.get("execution_error"),
                    })
                    # Re-execute sql_generation and sql_execution
                    for retry_node, retry_func in [
                        ("sql_generation", nodes.sql_generation_node),
                        ("sql_execution", nodes.sql_execution_node),
                    ]:
                        retry_start = time.time()
                        yield _sse_event("node_start", {
                            "node": retry_node,
                            "label": NODE_LABELS.get(retry_node, retry_node),
                            "status": "running",
                        })
                        retry_output = retry_func(state)
                        state.update(retry_output)
                        retry_end = time.time()
                        retry_duration = round((retry_end - retry_start) * 1000, 1)

                        # Accumulate token usage for retry
                        if retry_node == "sql_generation" and retry_output:
                            if "token_usage" in retry_output:
                                tu = retry_output["token_usage"]
                                if isinstance(tu, dict):
                                    token_usage["prompt_tokens"] += tu.get("prompt_tokens", 0)
                                    token_usage["completion_tokens"] += tu.get("completion_tokens", 0)
                                    token_usage["total_tokens"] += tu.get("total_tokens", 0)

                        yield _sse_event("node_complete", {
                            "node": retry_node,
                            "label": NODE_LABELS.get(retry_node, retry_node),
                            "status": "completed" if not state.get("execution_error") else "error",
                            "output": _serialize_output(retry_output),
                            "duration_ms": retry_duration,
                        })

        except Exception as e:
            node_end_time = time.time()
            duration_ms = round((node_end_time - node_start_time) * 1000, 1)
            yield _sse_event("node_error", {
                "node": node_name,
                "label": NODE_LABELS.get(node_name, node_name),
                "status": "error",
                "error": str(e),
                "duration_ms": duration_ms,
            })
            break

    # Calculate total execution time
    total_duration_ms = round((time.time() - total_start_time) * 1000, 1)

    # Yield final result
    result = state.get("result") or {}

    # Save to history with session_id
    try:
        from app.core.mysql_tools import create_history, create_session
        # Create session if not provided
        actual_session_id = session_id
        if actual_session_id is None:
            # Create new session with question as title
            session = create_session(title=question[:50] if len(question) > 50 else question)
            actual_session_id = session["id"]

        create_history(
            session_id=actual_session_id,
            question=state.get("question") or question,
            sql=state.get("generated_sql"),
            columns=result.get("columns") or [],
            rows=result.get("rows") or [],
            execution_error=state.get("execution_error") or None,
        )
    except Exception:
        pass  # Don't fail query if history save fails

    yield _sse_event("result", {
        "question": state.get("question") or question,
        "sql": state.get("generated_sql"),
        "columns": result.get("columns") or [],
        "rows": result.get("rows") or [],
        "attempt": int(state.get("attempt", 1)),
        "execution_error": state.get("execution_error") or None,
        "session_id": actual_session_id,
        "node_timings": node_timings,
        "total_duration_ms": total_duration_ms,
        "token_usage": token_usage,
    })
