"""
数据上传分析页面（Tab 2）。

支持上传 CSV 销售数据，由 Agent 自动分析。
"""

import streamlit as st


def render():
    st.header("📊 数据上传分析")
    st.markdown("上传电商销售 CSV 数据，AI 自动计算 Top N 商品、利润率等指标。")

    # ── 占位提示 ──────────────────────────────────────────────
    st.info("🚧 数据分析功能将在 **第 2 周期** 实现。当前为页面占位。")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("上传数据")
        st.file_uploader("选择 CSV 文件", type=["csv"], disabled=True)
        st.button("上传并分析", disabled=True)
    with col2:
        st.subheader("分析结果")
        st.caption("（分析结果将在此处展示）")
