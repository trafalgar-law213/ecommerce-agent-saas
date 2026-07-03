"""
文件上传路由 — CSV 上传与知识库文档上传。

POST /api/upload/csv       — 上传 CSV 销售数据
POST /api/upload/csv/{id}/analyze — 分析已上传的 CSV
GET  /api/analysis/{file_id} — 获取分析结果
"""

import shutil
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session as DBSession

from ..config import UPLOAD_DIR
from ..database import get_db
from ..models.uploaded_file import UploadedFile
from ..schemas.upload import UploadResponse, AnalysisResponse
from ..services.csv_service import load_csv, get_file_info, analyze as analyze_csv

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


def _generate_file_id() -> str:
    """生成简短文件 ID。"""
    import uuid
    return str(uuid.uuid4())[:8]
