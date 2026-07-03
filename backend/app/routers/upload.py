"""
文件上传路由 — CSV 上传与知识库文档上传。

POST /api/upload/csv          — 上传 CSV 销售数据
POST /api/upload/csv/{id}/analyze — 分析已上传的 CSV
GET  /api/analysis/{file_id}  — 获取分析结果
POST /api/knowledge/upload    — 上传知识库文档
GET  /api/knowledge/search    — 搜索知识库
GET  /api/knowledge/documents — 获取已上传的知识库文档列表
"""

import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session as DBSession

from ..config import UPLOAD_DIR
from ..database import get_db
from ..models.uploaded_file import UploadedFile
from ..schemas.upload import (
    UploadResponse,
    AnalysisResponse,
    KnowledgeSearchResponse,
    KnowledgeUploadResponse,
    KnowledgeDocumentItem,
)
from ..services.csv_service import load_csv, get_file_info, analyze as analyze_csv
from ..services.rag_service import rag_service

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload/csv", response_model=UploadResponse)
async def upload_csv(
    file: UploadFile = File(...),
    db: DBSession = Depends(get_db),
):
    """上传 CSV 销售数据文件。

    文件保存到 data/uploads/ 目录，并在数据库中创建记录。
    支持 .csv 格式，最大 10MB。
    """
    # ── 1. 校验文件类型 ───────────────────────────────────────
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="仅支持 .csv 格式的文件",
        )

    # ── 2. 保存文件 ───────────────────────────────────────────
    file_id = _generate_file_id()
    safe_filename = f"{file_id}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename

    try:
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:  # 10MB 限制
            raise HTTPException(status_code=400, detail="文件大小不能超过 10MB")

        file_path.write_bytes(content)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败：{str(e)}")

    # ── 3. 尝试解析 CSV（验证文件格式）───────────────────────
    try:
        df = load_csv(file_path)
        row_count = len(df)
        columns = df.columns.tolist()
    except Exception as e:
        # 删除无效文件
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=400,
            detail=f"CSV 文件解析失败：{str(e)}。请检查文件格式是否正确。",
        )

    # ── 4. 记录到数据库 ───────────────────────────────────────
    record = UploadedFile(
        id=file_id,
        filename=file.filename,
        file_type="csv",
        file_path=str(file_path),
        status="ready",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return UploadResponse(
        file_id=record.id,
        filename=record.filename,
        file_type=record.file_type,
        status=record.status,
        created_at=record.created_at,
    )


@router.post("/upload/csv/{file_id}/analyze", response_model=AnalysisResponse)
def analyze_uploaded_csv(
    file_id: str,
    query: str = "",
    db: DBSession = Depends(get_db),
):
    """分析已上传的 CSV 文件。

    Args:
        file_id: 文件 ID
        query: 分析查询（如"Top 5 商品""利润率""趋势"等），留空则返回概览
    """
    # ── 1. 查找文件记录 ───────────────────────────────────────
    record = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="文件不存在")
    if record.file_type != "csv":
        raise HTTPException(status_code=400, detail="仅支持分析 CSV 文件")

    file_path = Path(record.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件已被删除，请重新上传")

    # ── 2. 加载并分析 ─────────────────────────────────────────
    try:
        df = load_csv(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件读取失败：{str(e)}")

    info = get_file_info(df)

    if query:
        result = analyze_csv(df, query)
    else:
        result = analyze_csv(df, "概览")

    # 构建 analysis_result：合并 data + chart 信息，方便前端渲染
    analysis_data = result.get("data")
    if isinstance(analysis_data, dict):
        analysis_data = dict(analysis_data)  # 浅拷贝
        if result.get("chart_data"):
            analysis_data["chart_data"] = result["chart_data"]
        if result.get("chart_title"):
            analysis_data["chart_title"] = result["chart_title"]
    elif isinstance(analysis_data, list):
        analysis_data = {
            "records": analysis_data,
            "chart_data": result.get("chart_data"),
            "chart_title": result.get("chart_title"),
        }

    return AnalysisResponse(
        file_id=file_id,
        summary=result.get("summary", ""),
        columns=info["columns"],
        row_count=info["row_count"],
        analysis_result=analysis_data,
        visualization_suggestion=result.get("chart_type"),
    )


@router.get("/analysis/{file_id}", response_model=AnalysisResponse)
def get_analysis(file_id: str, db: DBSession = Depends(get_db)):
    """获取已上传 CSV 文件的信息（不执行分析查询）。"""
    record = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="文件不存在")

    file_path = Path(record.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件已被删除")

    try:
        df = load_csv(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件读取失败：{str(e)}")

    info = get_file_info(df)

    return AnalysisResponse(
        file_id=file_id,
        summary=f"文件已就绪：{record.filename}（{info['row_count']} 行 × {len(info['columns'])} 列）",
        columns=info["columns"],
        row_count=info["row_count"],
        analysis_result=None,
        visualization_suggestion=None,
    )


# ── 知识库文档上传与检索 ──────────────────────────────────────────

# 支持的知识库文档格式
_KNOWLEDGE_EXTENSIONS = {".pdf", ".docx", ".txt"}


@router.post("/knowledge/upload", response_model=KnowledgeUploadResponse)
async def upload_knowledge(
    file: UploadFile = File(...),
    db: DBSession = Depends(get_db),
):
    """上传知识库文档（PDF/DOCX/TXT）。

    文件保存到 data/uploads/，解析分块后向量化存入 Chroma。
    """
    # ── 1. 校验文件类型 ───────────────────────────────────────
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in _KNOWLEDGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式：{suffix}。支持的格式：PDF、DOCX、TXT",
        )

    # ── 2. 保存文件 ───────────────────────────────────────────
    file_id = _generate_file_id()
    safe_filename = f"{file_id}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename

    try:
        content = await file.read()
        if len(content) > 20 * 1024 * 1024:  # 20MB 限制（文档比 CSV 大）
            raise HTTPException(status_code=400, detail="文件大小不能超过 20MB")

        file_path.write_bytes(content)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败：{str(e)}")

    # ── 3. 解析文档并向量化 ────────────────────────────────────
    try:
        result = rag_service.ingest_document(file_path, file.filename)
    except Exception as e:
        # 删除无效文件
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=400,
            detail=f"文档解析失败：{str(e)}。请检查文件是否损坏或格式是否正确。",
        )

    # ── 4. 记录到数据库 ───────────────────────────────────────
    record = UploadedFile(
        id=file_id,
        filename=file.filename,
        file_type=suffix.lstrip("."),
        file_path=str(file_path),
        status="ready",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return KnowledgeUploadResponse(
        file_id=record.id,
        filename=record.filename,
        file_type=record.file_type,
        status=record.status,
        chunks=result["chunks"],
        created_at=record.created_at,
    )


@router.get("/knowledge/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    q: str = Query(..., min_length=1, description="搜索关键词或问题"),
    top_k: int = Query(5, ge=1, le=20, description="返回结果数量"),
):
    """在知识库中语义搜索相关内容。

    Args:
        q: 搜索查询（如 "退货流程" "客服话术"）
        top_k: 返回的最相关结果数量（默认 5，范围 1-20）
    """
    # 检查知识库是否有内容
    doc_count = rag_service.get_document_count()
    if doc_count == 0:
        return KnowledgeSearchResponse(
            query=q,
            results=[],
            total_documents=0,
        )

    try:
        results = rag_service.search(q, top_k=top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"知识库检索失败：{str(e)}")

    sources = rag_service.get_document_sources()

    return KnowledgeSearchResponse(
        query=q,
        results=results,
        total_documents=len(sources),
    )


@router.get("/knowledge/documents", response_model=list[KnowledgeDocumentItem])
def list_knowledge_documents(db: DBSession = Depends(get_db)):
    """获取所有已上传的知识库文档列表。"""
    docs = (
        db.query(UploadedFile)
        .filter(UploadedFile.file_type.in_(["pdf", "docx", "txt"]))
        .order_by(UploadedFile.created_at.desc())
        .all()
    )
    return [
        KnowledgeDocumentItem(
            filename=doc.filename,
            file_id=doc.id,
            file_type=doc.file_type,
            status=doc.status,
            created_at=doc.created_at,
        )
        for doc in docs
    ]


def _generate_file_id() -> str:
    """生成简短文件 ID。"""
    import uuid
    return str(uuid.uuid4())[:8]
