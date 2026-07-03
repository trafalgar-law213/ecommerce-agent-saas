"""
对话相关的 Pydantic schemas（请求/响应模型）。
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """POST /api/chat 请求体"""
    session_id: Optional[str] = Field(
        default=None,
        description="会话 ID。为空则创建新会话。",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="用户消息内容",
    )


class ChatResponse(BaseModel):
    """POST /api/chat 响应体"""
    session_id: str
    reply: str
    tool_calls: Optional[List[dict]] = Field(
        default=None,
        description="Agent 调用的工具记录",
    )

    model_config = {"from_attributes": True}
