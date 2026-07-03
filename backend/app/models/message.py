"""
消息（Message）ORM 模型。

记录每条对话消息，包括用户输入和 Agent 回复。
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from ..database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # "user" 或 "assistant"
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON, nullable=True)  # Agent 工具调用记录
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # 关联会话
    session = relationship("Session", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role})>"
