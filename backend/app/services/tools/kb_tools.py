"""
知识库检索工具 — 供 LangChain Agent 调用。

Agent 可以调用 search_knowledge_base 工具在用户上传的 SOP 知识库中检索相关内容。
"""

from langchain_core.tools import tool

from ..rag_service import rag_service


@tool
def search_knowledge_base(query: str) -> str:
    """在电商运营知识库中检索与用户问题相关的内容。

    当用户提出以下需求时，必须调用此工具：
    - 询问"退货流程"、"退款政策"、"售后处理"等运营 SOP 问题
    - 询问"客服话术"、"回复模板"、"投诉处理"等话术类问题
    - 询问"发货规范"、"物流问题"、"库存管理"等仓储物流问题
    - 任何可能存在于内部运营文档中的流程、规范、话术类问题

    Args:
        query: 用户的问题或搜索关键词。如 "退货流程" "客服话术 投诉" "发货时效"

    Returns:
        知识库中检索到的相关内容，包含片段文本和来源文档。
        如果知识库为空，会提示需要先上传文档。
    """

    # 检查知识库是否有内容
    doc_count = rag_service.get_document_count()
    if doc_count == 0:
        return (
            "ℹ️ 当前知识库中没有文档。"
            "请提示用户先在「知识库管理」页面上传运营 SOP、客服话术等文档（支持 PDF、DOCX、TXT 格式）。"
            "在知识库有内容之前，请根据你的通用知识尽力回答用户的问题。"
        )

    # 执行检索
    try:
        results = rag_service.search(query, top_k=5)
    except Exception as e:
        return f"❌ 知识库检索出错：{str(e)}。请稍后重试或提示用户检查文档格式。"

    if not results:
        return (
            f"🔍 在知识库（共 {doc_count} 个文档片段）中未找到与「{query}」相关的明确内容。"
            "请根据你的通用知识尽力回答用户的问题，并建议用户上传相关文档以获得更准确的答案。"
        )

    # 构建返回给 Agent 的文本
    output_parts = [
        f"📚 知识库检索结果（共 {doc_count} 个片段，返回 {len(results)} 条相关结果）：",
        "",
    ]

    for i, r in enumerate(results, 1):
        score_pct = (1.0 - r["score"]) * 100 if r["score"] < 1.0 else r["score"] * 100
        output_parts.append(
            f"--- 片段 {i}（相关度 {score_pct:.0f}%，来源：{r['source']}）---"
        )
        # 截断过长内容
        content = r["content"].strip()[:800]
        output_parts.append(content)
        output_parts.append("")

    output_parts.append("请基于以上文档片段回答用户问题，并在回复中注明信息来源。")

    return "\n".join(output_parts)
