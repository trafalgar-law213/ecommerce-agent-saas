"""
会话相关的 Pydantic schemas。
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class MessageResponse(BaseModel):
    """单条消息"""
    id: int
    session_id: str
    role: str
    content: str
    tool_calls: Optional[list] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionResponse(BaseModel):
    """会话摘要"""
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionDetailResponse(SessionResponse):
    """会话详情（含消息列表）"""
    messages: List[MessageResponse] = []
