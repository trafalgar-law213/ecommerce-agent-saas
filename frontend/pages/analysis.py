"""
数据上传分析页面（Tab 2）。

支持上传 CSV 销售数据，查看文件信息，
并通过自然语言查询让 AI 自动分析数据。
"""

import streamlit as st
import pandas as pd
from utils.api_client import upload_csv, get_analysis, analyze_csv


def render():
    st.header("📊 数据上传分析")
    st.caption("上传电商销售 CSV 数据，AI 自动分析 Top N、利润率、趋势等指标。")

    # ── 初始化 session_state ──────────────────────────────────
    if "uploaded_file_id" not in st.session_state:
        st.session_state.uploaded_file_id = None
    if "uploaded_file_info" not in st.session_state:
        st.session_state.uploaded_file_info = None
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None

    # ── 上传区域 ──────────────────────────────────────────────
    st.subheader("📤 上传 CSV 文件")

    col_upload, col_info = st.columns([1, 1])

    with col_upload:
        uploaded_file = st.file_uploader(
            "选择 CSV 文件",
            type=["csv"],
            help="支持标准 CSV 格式，建议包含以下列：日期、商品名称、分类、单价、销量、销售额、成本",
        )

        if uploaded_file is not None:
            if st.button("🚀 上传并加载", type="primary", use_container_width=True):
                with st.spinner("正在上传并解析 CSV..."):
                    try:
                        result = upload_csv(uploaded_file)
                        file_id = result.get("file_id")
                        st.session_state.uploaded_file_id = file_id
                        st.session_state.analysis_result = None

                        # 获取文件基本信息
                        info = get_analysis(file_id)
                        st.session_state.uploaded_file_info = info
                        st.success(f"✅ 上传成功！文件 ID：{file_id}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 上传失败：{str(e)}")

    # ── 文件信息展示 ──────────────────────────────────────────
    file_info = st.session_state.uploaded_file_info

    with col_info:
        if file_info:
            st.subheader("📋 文件信息")
            st.metric("文件名", uploaded_file.name if uploaded_file else "—")
            st.metric("数据量", f"{file_info.get('row_count', 0)} 行 × {len(file_info.get('columns', []))} 列")
            st.caption(f"列名：{', '.join(file_info.get('columns', []))}")

    # ── 数据预览 ──────────────────────────────────────────────
    if file_info:
        st.divider()
        st.subheader("👀 数据预览")

        # 尝试加载本地 CSV 做预览（如果用户刚上传的话）
        if uploaded_file is not None:
            try:
                uploaded_file.seek(0)
                df_preview = pd.read_csv(uploaded_file)
                st.dataframe(df_preview.head(10), use_container_width=True)
            except Exception:
                st.caption("（预览不可用，请查看下方分析结果）")

    # ── 分析区域 ──────────────────────────────────────────────
    if st.session_state.uploaded_file_id:
        st.divider()
        st.subheader("🔍 AI 数据分析")

        st.markdown("""
        输入你的分析需求，AI 将自动计算。例如：
        - `Top 5 商品`
        - `利润率分析`
        - `销售趋势`
        - `分类汇总`
        """)

        col_query, col_btn = st.columns([3, 1])
        with col_query:
            analysis_query = st.text_input(
                "分析需求",
                placeholder="如：Top 10 商品、利润率、销售趋势...",
                key="analysis_query",
                label_visibility="collapsed",
            )
        with col_btn:
            analyze_btn = st.button("🔍 分析", use_container_width=True, type="primary")

        if analyze_btn and analysis_query:
            _run_analysis(analysis_query)

        # ── 分析结果展示 ──────────────────────────────────────
        result = st.session_state.analysis_result
        if result:
            st.divider()
            st.subheader("📊 分析结果")

            summary = result.get("summary", "")
            if summary:
                st.markdown(summary)

            chart_type = result.get("visualization_suggestion")
            chart_data = result.get("analysis_result", {})

            if chart_type and isinstance(chart_data, dict):
                chart_inner = chart_data.get("chart_data") or chart_data
                labels = chart_inner.get("labels", [])
                values = chart_inner.get("values", [])
                chart_title = chart_inner.get("chart_title", "")

                if labels and values and len(labels) == len(values):
                    chart_df = pd.DataFrame({"类别": labels, "数值": values})

                    if chart_type == "bar":
                        st.bar_chart(
                            chart_df.set_index("类别"),
                            use_container_width=True,
                        )
                    elif chart_type == "line":
                        st.line_chart(
                            chart_df.set_index("类别"),
                            use_container_width=True,
                        )
                    else:
                        st.bar_chart(
                            chart_df.set_index("类别"),
                            use_container_width=True,
                        )

            # 表格数据
            if isinstance(chart_data, list) and chart_data:
                st.dataframe(pd.DataFrame(chart_data), use_container_width=True)

        # ── 提示：也可在对话中使用 ────────────────────────────
        if st.session_state.uploaded_file_id:
            st.divider()
            st.info(
                '💡 **提示**：切换到「💬 对话助手」Tab，'
                '你可以直接用自然语言问 AI 相关问题（如「帮我分析 Top 5 商品」），'
                'Agent 会自动调用分析工具获取数据。'
            )


def _run_analysis(query: str):
    """执行分析查询并更新 session_state。"""
    file_id = st.session_state.uploaded_file_id
    if not file_id:
        st.error("请先上传 CSV 文件")
        return

    with st.spinner(f"AI 正在分析：{query}..."):
        try:
            result = analyze_csv(file_id, query)
            st.session_state.analysis_result = result
            st.rerun()
        except Exception as e:
            st.error(f"❌ 分析失败：{str(e)}")
