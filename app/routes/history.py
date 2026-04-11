"""Query history API routes."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.mysql_tools import (
    create_history,
    delete_history,
    delete_history_batch,
    list_history,
    update_history,
    clear_all_history,
    get_history_by_id,
    # Session operations
    create_session,
    get_session_by_id,
    list_sessions,
    update_session_title,
    delete_session,
)


router = APIRouter(prefix="/history", tags=["history"])


# ============ Request/Response Models ============

class SessionCreateRequest(BaseModel):
    title: str | None = None


class HistoryCreateRequest(BaseModel):
    session_id: int
    question: str
    sql: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    execution_error: str | None = None
    is_favorite: bool = False


class HistoryUpdateRequest(BaseModel):
    is_favorite: bool | None = None


class HistoryBatchDeleteRequest(BaseModel):
    ids: list[int]


class SessionListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int


class HistoryListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============ Session API Endpoints ============

@router.post("/session", response_model=dict[str, Any])
def create_new_session(req: SessionCreateRequest = None):
    """Create a new chat session."""
    title = req.title if req else None
    return create_session(title=title)


@router.get("/session", response_model=SessionListResponse)
def get_session_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """List chat sessions with pagination."""
    return list_sessions(page=page, page_size=page_size)


@router.get("/session/{session_id}", response_model=dict[str, Any])
def get_session_record(session_id: int):
    """Get a single session."""
    record = get_session_by_id(session_id)
    if not record:
        raise HTTPException(status_code=404, detail="Session not found")
    return record


@router.patch("/session/{session_id}", response_model=dict[str, Any])
def update_session_record(session_id: int, req: SessionCreateRequest):
    """Update session title."""
    if not req.title:
        raise HTTPException(status_code=400, detail="Title is required")
    record = update_session_title(session_id, req.title)
    if not record:
        raise HTTPException(status_code=404, detail="Session not found")
    return record


@router.delete("/session/{session_id}")
def delete_session_record(session_id: int):
    """Delete a session and all its query history."""
    success = delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "message": "Session deleted"}


# ============ History API Endpoints ============

@router.post("", response_model=dict[str, Any])
def create_history_record(req: HistoryCreateRequest):
    """Create a new query history record."""
    return create_history(
        session_id=req.session_id,
        question=req.question,
        sql=req.sql,
        columns=req.columns,
        rows=req.rows,
        execution_error=req.execution_error,
        is_favorite=req.is_favorite,
    )


@router.get("", response_model=HistoryListResponse)
def get_history_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session_id: Optional[int] = Query(None, description="会话ID筛选"),
    is_favorite: Optional[bool] = Query(None, description="是否收藏筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
):
    """List query history with pagination and filters."""
    return list_history(
        page=page,
        page_size=page_size,
        session_id=session_id,
        is_favorite=is_favorite,
        search=search,
        start_date=start_date,
        end_date=end_date,
    )


@router.post("/batch-delete")
def batch_delete_history(req: HistoryBatchDeleteRequest):
    """Delete multiple history records."""
    count = delete_history_batch(req.ids)
    return {"success": True, "deleted_count": count}


@router.delete("/clear")
def clear_history():
    """Clear all history records and sessions."""
    count = clear_all_history()
    return {"success": True, "deleted_count": count}


@router.get("/{history_id}", response_model=dict[str, Any])
def get_history_record(history_id: int):
    """Get a single history record."""
    record = get_history_by_id(history_id)
    if not record:
        raise HTTPException(status_code=404, detail="History record not found")
    return record


@router.patch("/{history_id}", response_model=dict[str, Any])
def update_history_record(history_id: int, req: HistoryUpdateRequest):
    """Update a history record (mainly for favorite toggle)."""
    record = update_history(
        history_id=history_id,
        is_favorite=req.is_favorite,
    )
    if not record:
        raise HTTPException(status_code=404, detail="History record not found")
    return record


@router.delete("/{history_id}")
def delete_history_record(history_id: int):
    """Delete a history record."""
    success = delete_history(history_id)
    if not success:
        raise HTTPException(status_code=404, detail="History record not found")
    return {"success": True, "message": "History record deleted"}