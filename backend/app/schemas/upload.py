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
    total_documents: int  # 知识库中的文档来源数


class KnowledgeUploadResponse(BaseModel):
    """知识库文档上传结果"""
    file_id: str
    filename: str
    file_type: str
    status: str
    chunks: int = 0  # 文档被分割的块数
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeDocumentItem(BaseModel):
    """知识库中的文档项"""
    filename: str
    file_id: str
    file_type: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
