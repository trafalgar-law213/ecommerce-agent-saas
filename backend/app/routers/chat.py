"""
对话路由 — POST /api/chat 和 POST /api/chat/stream。

接收用户消息，调用 Agent，保存消息到数据库，返回回复。
"""

import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession

from ..database import get_db
from ..models.session import Session
from ..models.message import Message
from ..models.agent_trace import AgentTrace
from ..schemas.chat import ChatRequest, ChatResponse
from ..services.agent_service import agent_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


def _save_trace(
    db: DBSession,
    session_id: str,
    user_query: str,
    reply: str,
    trace_data: dict,
):
    """保存 Agent 调用追踪记录到数据库。"""
    try:
        trace = AgentTrace(
            session_id=session_id,
            user_query=user_query,
            reply_summary=(reply or "")[:200] if reply else None,
            tools_called=trace_data.get("tools_called"),
            tool_count=trace_data.get("tool_count", 0),
            duration_ms=trace_data.get("duration_ms"),
            turn_count=trace_data.get("turn_count", 1),
            token_usage=trace_data.get("token_usage"),
            status=trace_data.get("status", "success"),
        )
        db.add(trace)
    except Exception:
        logger.exception("保存 Agent 追踪记录失败")


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
        if msg.id != user_msg.id
    ]

    # ── 5. 调用 Agent ──────────────────────────────────────────
    result = agent_service.run(
        user_message=request.message,
        history_messages=history_dicts,
    )

    reply = result.get("reply", "抱歉，处理出错了。")
    tool_calls = result.get("tool_calls")
    trace_data = result.get("trace", {})

    # ── 6. 保存 Agent 回复 ────────────────────────────────────
    assistant_msg = Message(
        session_id=session.id,
        role="assistant",
        content=reply,
        tool_calls=tool_calls or None,
    )
    db.add(assistant_msg)

    # ── 7. 保存 Agent 追踪记录 ────────────────────────────────
    _save_trace(db, session.id, request.message, reply, trace_data)

    # ── 8. 更新会话活跃时间 ───────────────────────────────────
    from datetime import datetime, timezone
    session.updated_at = datetime.now(timezone.utc)

    db.commit()

    return ChatResponse(
        session_id=session.id,
        reply=reply,
        tool_calls=tool_calls if tool_calls else None,
    )


@router.post("/chat/stream")
def chat_stream(request: ChatRequest, db: DBSession = Depends(get_db)):
    """多轮对话入口（流式 SSE）。

    与 /api/chat 功能相同，但通过 Server-Sent Events 流式返回：
    - text 事件：AI 回复文本
    - tool_start / tool_end 事件：工具调用进度
    - done 事件：完整追踪数据

    前端使用 st.write_stream() 消费此端点。
    """
    # ── 1. 获取或创建会话 ─────────────────────────────────────
    if request.session_id:
        session = db.query(Session).filter(Session.id == request.session_id).first()
        if not session:
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
        if msg.id != user_msg.id
    ]

    # ── 5. 流式调用 Agent ─────────────────────────────────────
    # 先在 DB 外收集完整结果，再一次性写入
    session_id = session.id
    user_query = request.message

    def event_generator():
        full_reply = []
        tool_calls_result = None
        trace_result = None

        try:
            for event in agent_service.run_stream(
                user_message=user_query,
                history_messages=history_dicts,
            ):
                event_type = event.get("type", "")

                if event_type == "done":
                    tool_calls_result = event.get("tool_calls")
                    trace_result = {
                        "duration_ms": event.get("duration_ms"),
                        "tool_count": len(tool_calls_result) if tool_calls_result else 0,
                        "tools_called": (
                            [tc["tool"] for tc in tool_calls_result]
                            if tool_calls_result else None
                        ),
                        "turn_count": 1,
                        "token_usage": event.get("token_usage"),
                        "status": "success",
                    }
                    # 发送带 session_id 的 done 事件
                    done_data = {
                        "type": "done",
                        "session_id": session_id,
                        "duration_ms": event.get("duration_ms"),
                        "tool_calls": tool_calls_result,
                    }
                    yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"

                elif event_type == "error":
                    trace_result = {
                        "duration_ms": event.get("duration_ms", 0),
                        "tool_count": 0,
                        "tools_called": None,
                        "turn_count": 0,
                        "token_usage": {},
                        "status": "error",
                        "error_message": event.get("message", ""),
                    }
                    error_data = {"type": "error", "message": event.get("message", "")}
                    yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

                else:
                    # text / tool_start / tool_end 事件
                    if event_type == "text":
                        full_reply.append(event.get("content", ""))
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.exception("SSE 流式生成异常")
            error_data = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

        finally:
            # 写入数据库（在流结束后）
            reply_text = "".join(full_reply)
            try:
                # 保存 Agent 回复
                assistant_msg = Message(
                    session_id=session_id,
                    role="assistant",
                    content=reply_text or "抱歉，处理出错了。",
                    tool_calls=tool_calls_result or None,
                )
                db.add(assistant_msg)

                # 保存追踪记录
                _save_trace(
                    db, session_id, user_query,
                    reply_text, trace_result or {},
                )

                # 更新会话活跃时间
                from datetime import datetime, timezone
                session = db.query(Session).filter(Session.id == session_id).first()
                if session:
                    session.updated_at = datetime.now(timezone.utc)

                db.commit()
            except Exception:
                logger.exception("SSE 流结束后写入数据库失败")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )
