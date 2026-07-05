"""
知识库管理页面（Tab 3）。

上传运营 SOP、客服话术等文档（PDF/DOCX/TXT），
自动分块向量化存入 Chroma，支持语义搜索测试。
"""

import streamlit as st
import time

from utils.api_client import (
    upload_knowledge,
    search_knowledge,
    get_knowledge_documents,
    delete_knowledge_document,
)


def render():
    st.header("📚 知识库管理")
    st.markdown(
        "上传运营 SOP、客服话术等文档，AI 将基于这些内容回答运营问题。"
        "支持 PDF、DOCX、TXT 格式，文档将自动分块并向量化存储。"
    )

    # ── 上传区域 ──────────────────────────────────────────────
    st.subheader("📤 上传文档")

    uploaded_files = st.file_uploader(
        "选择文件（可批量上传）",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        key="knowledge_uploader",
        help="支持 PDF、DOCX、TXT 格式，单文件最大 20MB",
    )

    if uploaded_files:
        if st.button("🚀 上传到知识库", type="primary", use_container_width=True):
            for file in uploaded_files:
                with st.status(f"正在处理：{file.name}……", expanded=True) as status:
                    try:
                        # 上传并解析
                        st.write("⏳ 上传文件中……")
                        result = upload_knowledge(file)

                        # 显示结果
                        st.write(
                            f"✅ 上传成功！文档被分为 **{result.get('chunks', 0)}** 个片段"
                        )
                        st.write(f"📄 文件名：{result['filename']}")
                        st.write(f"📋 类型：{result['file_type']}")
                        status.update(
                            label=f"✅ {file.name} — 处理完成",
                            state="complete",
                        )
                    except Exception as e:
                        status.update(
                            label=f"❌ {file.name} — 上传失败",
                            state="error",
                        )
                        st.error(f"上传失败：{e}")

            # 刷新页面
            time.sleep(1)
            st.rerun()

    st.divider()

    # ── 已上传文档列表 ────────────────────────────────────────
    st.subheader("📋 已上传文档")

    try:
        docs = get_knowledge_documents()
    except Exception:
        docs = []

    if not docs:
        st.info("还没有上传任何文档。请先上传 SOP 或客服话术文档。")
        st.caption(
            "💡 提示：项目 `mock_data/` 目录下有示例文档 "
            "`sample_sop.txt` 可用于测试。"
        )
    else:
        for doc in docs:
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                file_icon = {"pdf": "📕", "docx": "📘", "txt": "📄"}.get(
                    doc.get("file_type", ""), "📎"
                )
                st.markdown(f"{file_icon} **{doc['filename']}**")
            with col2:
                st.caption(f"类型：{doc.get('file_type', '').upper()}")
            with col3:
                st.caption(f"状态：{doc.get('status', '')}")
            with col4:
                filename = doc["filename"]
                file_id = doc.get("file_id", filename)
                if st.button("🗑️ 删除", key=f"del_kb_{file_id}", use_container_width=True):
                    try:
                        delete_knowledge_document(filename)
                        st.success(f"已删除「{filename}」")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"删除失败：{e}")

    st.divider()

    # ── 搜索测试 ──────────────────────────────────────────────
    st.subheader("🔍 搜索测试")
    st.caption("输入问题，测试知识库检索效果（不影响对话助手 Agent 正常使用）")

    search_query = st.text_input(
        "搜索关键词或问题",
        placeholder="例如：退货流程、客服话术、发货时效……",
        key="kb_search_input",
    )

    if search_query:
        with st.spinner(f"正在搜索：「{search_query}」……"):
            try:
                result = search_knowledge(search_query, synthesize=True)
                total = result.get("total_documents", 0)
                results = result.get("results", [])
                synthesized = result.get("synthesized", "")

                if not results:
                    st.warning(
                        f"未找到与「{search_query}」相关的内容。"
                        f"知识库中共有 {total} 个文档来源。"
                    )
                else:
                    # ── AI 合成回答（优先展示）─────────────────
                    if synthesized:
                        st.success("✅ AI 合成回答")
                        st.markdown(synthesized)

                    # ── 原始检索片段（折叠）─────────────────────
                    with st.expander(
                        f"📋 检索详情（{len(results)} 个片段，来自 {total} 个文档）",
                        expanded=False,
                    ):
                        for i, r in enumerate(results, 1):
                            score_pct = (
                                (1.0 - r["score"]) * 100
                                if r["score"] < 1.0
                                else r["score"] * 100
                            )
                            st.caption(
                                f"片段 {i}  ·  相关度 {score_pct:.0f}%  ·  来源：{r['source']}"
                            )
                            st.markdown(r["content"][:1000])
                            if i < len(results):
                                st.divider()
            except Exception as e:
                st.error(f"搜索失败：{e}")
