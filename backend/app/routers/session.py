"""
会话路由 — 会话列表、消息历史、删除会话。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from ..database import get_db
from ..models.session import Session
from ..models.message import Message
from ..schemas.session import SessionResponse, SessionDetailResponse, MessageResponse

router = APIRouter(prefix="/api", tags=["sessions"])


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(db: DBSession = Depends(get_db)):
    """获取所有会话列表，按活跃时间倒序排列。"""
    sessions = (
        db.query(Session)
        .order_by(Session.updated_at.desc())
        .all()
    )
    return sessions


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session_detail(session_id: str, db: DBSession = Depends(get_db)):
    """获取某个会话的详情（含所有历史消息）。"""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "messages": session.messages,
    }


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
def get_session_messages(session_id: str, db: DBSession = Depends(get_db)):
    """获取某个会话的所有消息（前端加载历史记录用）。"""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return messages


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: DBSession = Depends(get_db)):
    """删除指定会话及其所有消息。"""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    db.delete(session)
    db.commit()
    return {"ok": True, "deleted": session_id}
