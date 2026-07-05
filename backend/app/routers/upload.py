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

    # ── 1.5 检查同名文件是否已存在 ─────────────────────────────
    existing_sources = rag_service.get_document_sources()
    if file.filename in existing_sources:
        raise HTTPException(
            status_code=409,
            detail=f"文档「{file.filename}」已存在于知识库中，不允许重复上传。如需更新，请先删除旧版本。",
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
    synthesize: bool = Query(False, description="是否使用 AI 将检索结果合成为单个回答"),
):
    """在知识库中语义搜索相关内容。

    Args:
        q: 搜索查询（如 "退货流程" "客服话术"）
        top_k: 返回的最相关结果数量（默认 5，范围 1-20）
        synthesize: 是否使用 AI 合成回答（默认 False，返回原始片段列表）
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

    synthesized = None
    if synthesize and results:
        synthesized = _synthesize_answer(q, results)

    return KnowledgeSearchResponse(
        query=q,
        results=results,
        total_documents=len(sources),
        synthesized=synthesized,
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


@router.delete("/knowledge/documents/{filename}")
def delete_knowledge_document(
    filename: str,
    db: DBSession = Depends(get_db),
):
    """从知识库中彻底删除指定文档。

    删除范围：
    1. Chroma 向量库中的所有分块
    2. uploaded_files 表中的所有同名数据库记录
    3. data/uploads/ 中的磁盘文件
    """
    deleted_count = 0

    # ── 1. 删除 Chroma 向量数据 ──────────────────────────────
    chroma_deleted = rag_service.delete_document(filename)

    # ── 2. 删除数据库中的所有同名记录 ─────────────────────────
    db_records = (
        db.query(UploadedFile)
        .filter(UploadedFile.filename == filename)
        .all()
    )
    for record in db_records:
        # 删除磁盘文件
        file_path = Path(record.file_path) if record.file_path else None
        if file_path and file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass  # 文件可能已被删除，忽略
        db.delete(record)
        deleted_count += 1

    db.commit()

    # ── 3. 判断结果 ──────────────────────────────────────────
    if deleted_count == 0 and not chroma_deleted:
        raise HTTPException(
            status_code=404,
            detail=f"文档「{filename}」不存在。可能已被删除或文件名拼写有误。",
        )

    return {
        "status": "ok",
        "filename": filename,
        "deleted_records": deleted_count,
        "chroma_deleted": chroma_deleted,
        "message": f"文档「{filename}」已彻底删除（数据库 {deleted_count} 条记录 + Chroma 分块）",
    }


def _generate_file_id() -> str:
    """生成简短文件 ID。"""
    import uuid
    return str(uuid.uuid4())[:8]


def _synthesize_answer(query: str, results: list) -> str:
    """使用 DeepSeek 将多个检索片段合成为一个连贯的回答。

    Args:
        query: 用户原始查询
        results: rag_service.search() 返回的片段列表

    Returns:
        AI 合成的回答文本
    """
    from langchain_openai import ChatOpenAI
    from ..config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

    # 拼接检索到的上下文
    context_parts = []
    for i, r in enumerate(results, 1):
        source = r.get("source", "未知")
        content = r.get("content", "")
        context_parts.append(f"【来源 {i}：{source}】\n{content}")

    context = "\n\n".join(context_parts)

    prompt = f"""你是一个电商运营专家助手。请根据以下知识库检索结果，用简洁专业的中文回答用户的问题。

要求：
- 综合所有相关片段，给出一个完整、连贯的答案
- 不要逐条列举，而是自然整合
- 如果涉及步骤/流程，用清晰的编号列表呈现
- 答案末尾注明参考了哪些文档来源
- 如果检索结果不足以完整回答问题，诚实说明

用户问题：{query}

知识库检索结果：
{context}

请回答："""

    try:
        llm = ChatOpenAI(
            model=DEEPSEEK_MODEL,
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.3,
            max_tokens=1024,
        )
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        _logger = __import__("logging").getLogger(__name__)
        _logger.error(f"AI 合成回答失败：{e}", exc_info=True)
        return f"（AI 合成失败：{e}）"
