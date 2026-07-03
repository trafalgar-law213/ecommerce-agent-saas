"""
知识库管理页面（Tab 3）。

上传 SOP 文档（PDF/DOCX/TXT），建立向量检索知识库。
"""

import streamlit as st


def render():
    st.header("📚 知识库管理")
    st.markdown("上传运营 SOP、客服话术等文档，AI 将基于这些内容回答问题。")

    # ── 占位提示 ──────────────────────────────────────────────
    st.info("🚧 知识库功能将在 **第 3 周期** 实现。当前为页面占位。")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("上传文档")
        st.file_uploader(
            "选择文件",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            disabled=True,
        )
        st.button("上传到知识库", disabled=True)
    with col2:
        st.subheader("已上传文档")
        st.caption("（文档列表将在此处展示）")
