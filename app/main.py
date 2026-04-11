from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from app.pipeline.graph_builder import build_graph
from app.pipeline.streaming import stream_query_simple, GRAPH_STRUCTURE
from app.routes.history import router as history_router
from app.routes.settings import router as settings_router

# Load .env from project root
ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(ENV_PATH)

app = FastAPI(title="nl2sql-langgraph")


# CORS middleware - must handle OPTIONS requests
@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    # Handle OPTIONS preflight requests
    if request.method == "OPTIONS":
        return JSONResponse(
            content={},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            }
        )

    # SPA routing: if browser requests HTML and path matches API route, serve SPA
    accept_header = request.headers.get("accept", "")
    path = request.url.path.strip('/')

    # Check if this is a browser navigation (accepts HTML) to a frontend route
    is_browser_request = "text/html" in accept_header
    is_api_path = path.startswith(('settings', 'history', 'query', 'stream', 'graph', 'api'))

    if is_browser_request and is_api_path and request.method == "GET":
        # This is likely a browser navigation to a frontend route, serve SPA
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)

    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


# Include history router
app.include_router(history_router)

# Include settings router
app.include_router(settings_router)

GRAPH = build_graph()


# ============ Request/Response Models ============

class QueryRequest(BaseModel):
    question: str = Field(..., description="用户自然语言问题")
    datasource_id: int | None = Field(None, description="数据源ID，不传则使用默认数据源")


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
    # 设置数据源（如果指定）
    if req.datasource_id:
        from app.core.datasource_manager import set_current_datasource
        set_current_datasource(req.datasource_id)

    initial_state = {
        "question": req.question,
        "attempt": 1,
        "max_attempts": int(os.getenv("SQL_MAX_ATTEMPTS", "2")),
        "datasource_id": req.datasource_id,
    }
    state = GRAPH.invoke(initial_state)

    result = state.get("result") or {}

    # Save to history
    try:
        from app.core.mysql_tools import create_history
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
    datasource_id: int | None = Query(None, description="数据源ID，不传则使用默认数据源"),
):
    """SSE streaming endpoint for real-time progress updates."""
    max_attempts = int(os.getenv("SQL_MAX_ATTEMPTS", "2"))
    return StreamingResponse(
        stream_query_simple(question, max_attempts, session_id, datasource_id),
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
@app.exception_handler(404)
async def spa_fallback(request, exc):
    """Serve SPA - return index.html for 404s that are not API routes."""
    # API paths should return 404
    path = request.url.path.strip('/')
    if path.startswith(('settings', 'history', 'query', 'stream', 'graph', 'api')):
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    # Check for static file
    file_path = STATIC_DIR / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)

    # Serve index.html for SPA routing
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    return JSONResponse(status_code=404, content={"detail": "Frontend not built. Run 'npm run build' in frontend directory."})
