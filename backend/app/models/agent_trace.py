"""
Agent 调用追踪（AgentTrace）ORM 模型。

记录每次 Agent 调用的性能指标和工具使用情况，
用于可观测性面板展示和性能分析。
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON

from ..database import Base


class AgentTrace(Base):
    __tablename__ = "agent_traces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String, ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    user_query = Column(Text, nullable=False)
    reply_summary = Column(Text, nullable=True)  # 回复摘要（前 200 字）
    tools_called = Column(JSON, nullable=True)    # ["analyze_sales_data", ...]
    tool_count = Column(Integer, default=0)
    duration_ms = Column(Integer, nullable=True)  # 总耗时（毫秒）
    turn_count = Column(Integer, default=1)       # Agent 工具调用轮次
    token_usage = Column(JSON, nullable=True)     # {"prompt": N, "completion": N, "total": N}
    status = Column(String(20), default="success")  # "success" | "error"
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<AgentTrace(id={self.id}, status={self.status}, duration={self.duration_ms}ms)>"
