"""
CSV 数据分析工具 — 供 LangChain Agent 调用。

Agent 可以调用 analyze_sales_data 工具来分析用户已上传的销售 CSV 数据。
"""

from pathlib import Path

from langchain_core.tools import tool
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ...config import DATABASE_URL

# 工具内部独立创建数据库会话（不依赖 FastAPI Depends）
_engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,
)
_SessionLocal = sessionmaker(bind=_engine)


@tool
def analyze_sales_data(query: str) -> str:
    """分析用户已上传的电商销售 CSV 数据。

    当用户提出以下需求时，必须调用此工具：
    - 询问"Top N 商品"、"排名前几"、"卖得最好/最差的商品"
    - 询问"利润率"、"毛利"、"成本分析"
    - 询问"销售趋势"、"增长情况"、"走势"
    - 询问"分类汇总"、"哪个品类卖得好"
    - 任何需要查看实际销售数据才能回答的问题

    Args:
        query: 用户的分析需求，用自然语言描述。如 "Top 5 商品" "利润率分析" "最近30天趋势"

    Returns:
        分析结果的文字描述，包含具体数字和结论。
    """
    from ...models.uploaded_file import UploadedFile
    from ..csv_service import load_csv, analyze

    # 查找最近上传的 CSV 文件
    db = _SessionLocal()
    try:
        latest_csv = (
            db.query(UploadedFile)
            .filter(UploadedFile.file_type == "csv", UploadedFile.status == "ready")
            .order_by(UploadedFile.created_at.desc())
            .first()
        )

        if not latest_csv:
            return (
                "⚠️ 当前没有已上传的 CSV 文件。"
                "请提示用户先在「数据上传分析」页面上传销售数据 CSV 文件。"
            )

        file_path = Path(latest_csv.file_path)
        if not file_path.exists():
            return (
                f"⚠️ 文件记录存在但文件已被删除：{latest_csv.filename}。"
                "请提示用户重新上传 CSV 文件。"
            )

        # 加载并分析
        df = load_csv(file_path)
        result = analyze(df, query)

        # 构建返回给 Agent 的文本
        output_parts = [
            f"📁 数据来源：{latest_csv.filename}（{len(df)} 行 × {len(df.columns)} 列）",
            f"📋 数据列：{', '.join(df.columns.tolist())}",
            "",
            result.get("summary", "分析完成"),
        ]

        # 附上详细数据（供 Agent 引用）
        data = result.get("data")
        if isinstance(data, list) and data:
            output_parts.append("")
            output_parts.append("详细数据：")
            for i, row in enumerate(data[:10], 1):  # 最多 10 行
                row_str = " | ".join(f"{k}: {v}" for k, v in row.items())
                output_parts.append(f"  {i}. {row_str}")

        return "\n".join(output_parts)

    except Exception as e:
        return f"❌ 数据分析时出错：{str(e)}。请检查 CSV 文件格式是否正确。"
    finally:
        db.close()
