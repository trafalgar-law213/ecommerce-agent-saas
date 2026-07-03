"""
对话助手页面（Tab 1）。

提供多轮对话界面，支持新建/切换会话。
"""

import streamlit as st


def render():
    st.header("💬 对话助手")
    st.markdown("向 AI 助手提问：销售数据分析、营销文案生成、SOP 知识库查询……")

    # ── 占位提示 ──────────────────────────────────────────────
    st.info("🚧 对话功能将在 **第 1 周期** 实现。当前为页面占位。")

    # 模拟布局预览
    col1, col2 = st.columns([3, 1])
    with col2:
        st.caption("📋 会话列表")
        st.button("+ 新建会话", disabled=True)
        st.selectbox("历史会话", ["（暂无会话）"], disabled=True)
    with col1:
        st.text_area("输入你的问题...", placeholder="例如：帮我分析昨天 Top 5 商品的利润率", disabled=True, height=120)
        st.button("发送", disabled=True)
