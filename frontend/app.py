"""
Streamlit 前端主入口。

三个功能 Tab：
  - 对话助手（chat.py）
  - 数据上传分析（analysis.py）
  - 知识库管理（knowledge.py）
"""

import streamlit as st

st.set_page_config(
    page_title="电商智能客服与选品助手",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 侧边栏 ──────────────────────────────────────────────────────
st.sidebar.title("🛒 Agent SaaS")
st.sidebar.markdown("电商智能客服与选品助手")
st.sidebar.divider()

# 后端连接状态
from utils.api_client import check_backend_health

backend_ok, backend_msg = check_backend_health()
if backend_ok:
    st.sidebar.success(f"🟢 后端已连接 ({backend_msg})")
else:
    st.sidebar.error(f"🔴 后端未连接 — {backend_msg}")

st.sidebar.divider()
st.sidebar.caption("基于 LangChain + DeepSeek")
st.sidebar.caption("Python 3.11 · FastAPI · Chroma")

# ── Tab 导航 ────────────────────────────────────────────────────
tab_chat, tab_analysis, tab_knowledge = st.tabs(
    ["💬 对话助手", "📊 数据上传分析", "📚 知识库管理"]
)

with tab_chat:
    from tabs import chat
    chat.render()

with tab_analysis:
    from tabs import analysis
    analysis.render()

with tab_knowledge:
    from tabs import knowledge
    knowledge.render()
