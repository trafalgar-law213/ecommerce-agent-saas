"""
对话路由 — POST /api/chat。

接收用户消息，调用 Agent，保存消息到数据库，返回回复。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from ..database import get_db
from ..models.session import Session
from ..models.message import Message
from ..schemas.chat import ChatRequest, ChatResponse
from ..services.agent_service import agent_service

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: DBSession = Depends(get_db)):
    """多轮对话入口。

    接收用户消息，调用 LangChain Agent 生成回复。
    - 如果未传 session_id，自动创建新会话
    - 自动加载该会话的历史消息作为上下文
    """
    # ── 1. 获取或创建会话 ─────────────────────────────────────
    if request.session_id:
        session = db.query(Session).filter(Session.id == request.session_id).first()
        if not session:
            # session_id 不存在，按新会话处理
            session = Session()
            db.add(session)
            db.flush()
    else:
        session = Session()
        db.add(session)
        db.flush()

    # ── 2. 自动生成会话标题 ───────────────────────────────────
    if session.title == "新对话":
        session.title = request.message[:30] + ("..." if len(request.message) > 30 else "")

    # ── 3. 保存用户消息 ────────────────────────────────────────
    user_msg = Message(
        session_id=session.id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)
    db.flush()

    # ── 4. 加载历史消息 ────────────────────────────────────────
    history = (
        db.query(Message)
        .filter(Message.session_id == session.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    history_dicts = [
        {"role": msg.role, "content": msg.content}
        for msg in history
        if msg.id != user_msg.id  # 排除刚存入的当前消息
    ]

    # ── 5. 调用 Agent ──────────────────────────────────────────
    result = agent_service.run(
        user_message=request.message,
        history_messages=history_dicts,
    )

    # ── 6. 保存 Agent 回复 ────────────────────────────────────
    assistant_msg = Message(
        session_id=session.id,
        role="assistant",
        content=result["reply"],
        tool_calls=result.get("tool_calls") or None,
    )
    db.add(assistant_msg)

    # ── 7. 更新会话活跃时间 ───────────────────────────────────
    from datetime import datetime, timezone
    session.updated_at = datetime.now(timezone.utc)

    db.commit()

    return ChatResponse(
        session_id=session.id,
        reply=result["reply"],
        tool_calls=result.get("tool_calls") if result.get("tool_calls") else None,
    )
