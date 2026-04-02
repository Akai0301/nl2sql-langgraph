from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from .graph_builder import build_graph
from .streaming import stream_query_simple, GRAPH_STRUCTURE
from .history_routes import router as history_router

# Load .env from project root
ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(ENV_PATH)

app = FastAPI(title="nl2sql-langgraph")


@app.middleware("http")
async def add_cors_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


@app.options("/{path:path}")
async def options_handler(path: str):
    return JSONResponse(content={}, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    })

# Include history router
app.include_router(history_router)

GRAPH = build_graph()


# ============ Request/Response Models ============

class QueryRequest(BaseModel):
    question: str = Field(..., description="用户自然语言问题")


class QueryResponse(BaseModel):
    question: str
    sql: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    attempt: int = 1
    execution_error: str | None = None


# ============ API Endpoints ============

@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    """Synchronous query endpoint."""
    initial_state = {
        "question": req.question,
        "attempt": 1,
        "max_attempts": int(os.getenv("SQL_MAX_ATTEMPTS", "2")),
    }
    state = GRAPH.invoke(initial_state)

    result = state.get("result") or {}

    # Save to history
    try:
        from .mysql_tools import create_history
        create_history(
            question=state.get("question") or req.question,
            sql=state.get("generated_sql"),
            columns=result.get("columns") or [],
            rows=result.get("rows") or [],
            execution_error=state.get("execution_error") or None,
        )
    except Exception:
        pass  # Don't fail query if history save fails

    return QueryResponse(
        question=state.get("question") or req.question,
        sql=state.get("generated_sql"),
        columns=result.get("columns") or [],
        rows=result.get("rows") or [],
        attempt=int(state.get("attempt", 1)),
        execution_error=state.get("execution_error") or None,
    )


@app.get("/stream")
async def stream_query(
    question: str = Query(..., description="用户自然语言问题"),
    session_id: int | None = Query(None, description="会话ID，不传则创建新会话"),
):
    """SSE streaming endpoint for real-time progress updates."""
    max_attempts = int(os.getenv("SQL_MAX_ATTEMPTS", "2"))
    return StreamingResponse(
        stream_query_simple(question, max_attempts, session_id),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/graph/structure")
def get_graph_structure():
    """Return the LangGraph structure for frontend visualization."""
    return GRAPH_STRUCTURE


# ============ Static Files (Frontend) ============

# Get the frontend static directory
STATIC_DIR = Path(__file__).parent.parent / "static"

# Mount static files if the directory exists
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/", response_class=FileResponse)
async def serve_frontend():
    """Serve the frontend index.html."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Frontend not built. Run 'npm run build' in frontend directory."}


# SPA fallback - serve index.html for all unmatched routes
# Note: This must come AFTER all API routes are defined
@app.get("/{path:path}", response_class=FileResponse)
async def serve_spa(path: str):
    """Serve SPA - return index.html for client-side routing."""
    # First check if it's a static file request
    file_path = STATIC_DIR / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)

    # Otherwise serve index.html for SPA routing
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    return {"message": "Frontend not built. Run 'npm run build' in frontend directory."}
