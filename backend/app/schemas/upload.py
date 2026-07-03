"""
文件上传与分析相关的 Pydantic schemas。
"""

from datetime import datetime
from typing import Optional, List, Union, Any

from pydantic import BaseModel


class UploadResponse(BaseModel):
    """文件上传结果"""
    file_id: str
    filename: str
    file_type: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisResponse(BaseModel):
    """CSV 分析结果"""
    file_id: str
    summary: str
    columns: List[str]
    row_count: int
    analysis_result: Optional[Union[dict, list]] = None
    visualization_suggestion: Optional[str] = None


class KnowledgeSearchResponse(BaseModel):
    """知识库检索结果"""
    query: str
    results: List[dict]  # [{"content": "...", "source": "...", "score": 0.95}, ...]
