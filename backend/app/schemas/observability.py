"""
可观测性相关的 Pydantic schemas。
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class TraceItem(BaseModel):
    """单条 Agent 调用追踪记录"""
    id: int
    session_id: Optional[str] = None
    user_query: str
    reply_summary: Optional[str] = None
    tools_called: Optional[List[str]] = None
    tool_count: int = 0
    duration_ms: Optional[int] = None
    turn_count: int = 1
    token_usage: Optional[dict] = None
    status: str = "success"
    error_message: Optional[str] = None
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class TraceListResponse(BaseModel):
    """追踪记录列表响应"""
    traces: List[TraceItem]
    total: int


class ObservabilityStats(BaseModel):
    """可观测性聚合统计"""
    total_traces: int = 0
    total_success: int = 0
    total_errors: int = 0
    avg_duration_ms: float = 0.0
    max_duration_ms: int = 0
    min_duration_ms: int = 0
    total_tokens: int = 0
    avg_tokens_per_call: float = 0.0
    tool_usage_distribution: dict = Field(default_factory=dict)  # {"tool_name": count}
    recent_traces_24h: int = 0
    avg_turns: float = 0.0
