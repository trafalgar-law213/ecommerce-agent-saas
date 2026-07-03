"""
对话助手页面（Tab 1）。

多轮对话界面：
- 左侧：会话列表（新建/切换/删除）
- 右侧：聊天区域（历史消息 + 输入框）
"""

import streamlit as st
from utils.api_client import (
    send_message,
    get_sessions,
    get_session_messages,
    delete_session,
)


def render():
    st.header("💬 对话助手")
    st.caption("向 AI 助手提问：数据分析、文案生成、SOP 知识查询……")

    # ── 初始化 session_state ──────────────────────────────────
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # ── 左右布局 ──────────────────────────────────────────────
    sidebar_left, chat_right = st.columns([1, 3])

    # ── 左侧：会话列表 ────────────────────────────────────────
    with sidebar_left:
        render_session_sidebar()

    # ── 右侧：聊天区域 ────────────────────────────────────────
    with chat_right:
        render_chat_area()


def render_session_sidebar():
    """左侧边栏：会话管理。"""
    st.subheader("📋 会话列表")

    # 新建会话按钮
    if st.button("➕ 新建会话", use_container_width=True):
        st.session_state.current_session_id = None
        st.session_state.chat_messages = []
        st.rerun()

    st.divider()

    # 加载会话列表
    try:
        sessions = get_sessions()
    except Exception:
        st.warning("无法加载会话列表，请确认后端服务已启动")
        return

    if not sessions:
        st.caption("（暂无历史会话）")
        return

    # 显示会话列表
    for sess in sessions:
        col_btn, col_del = st.columns([4, 1])
        with col_btn:
            title = sess.get("title", "新对话")
            is_active = sess["id"] == st.session_state.current_session_id
            btn_label = f"{'🟢 ' if is_active else ''}{title[:20]}"
            if st.button(
                btn_label,
                key=f"session_{sess['id']}",
                use_container_width=True,
                help=f"创建时间：{sess.get('created_at', '')[:19]}",
            ):
                st.session_state.current_session_id = sess["id"]
                # 加载该会话的历史消息
                try:
                    msgs = get_session_messages(sess["id"])
                    st.session_state.chat_messages = [
                        {"role": m["role"], "content": m["content"]}
                        for m in msgs
                    ]
                except Exception:
                    st.session_state.chat_messages = []
                st.rerun()
        with col_del:
            if st.button("🗑", key=f"del_{sess['id']}", help="删除此会话"):
                try:
                    delete_session(sess["id"])
                    if sess["id"] == st.session_state.current_session_id:
                        st.session_state.current_session_id = None
                        st.session_state.chat_messages = []
                    st.rerun()
                except Exception as e:
                    st.error(f"删除失败：{e}")


def render_chat_area():
    """右侧聊天区域：消息展示 + 发送。"""
    current_id = st.session_state.current_session_id

    if current_id:
        st.caption(f"当前会话：{current_id}")
    else:
        st.caption("当前会话：新对话（发送第一条消息后自动创建）")

    # ── 消息展示区 ────────────────────────────────────────────
    chat_container = st.container()
    with chat_container:
        if not st.session_state.chat_messages:
            st.info("👋 欢迎！你可以问我：\n\n"
                    "- 📊 帮我分析上传的销售数据\n"
                    "- ✍️ 为这款商品写一段小红书文案\n"
                    "- 📚 退货流程是什么？\n\n"
                    "（数据分析、文案生成、知识库功能将在后续版本中逐步开放）")
        else:
            for msg in st.session_state.chat_messages:
                role = msg["role"]
                content = msg["content"]
                with st.chat_message(role):
                    st.markdown(content)

    st.divider()

    # ── 输入区 ────────────────────────────────────────────────
    user_input = st.chat_input("输入你的问题...", key="chat_input")

    if user_input:
        # 立即显示用户消息
        st.session_state.chat_messages.append({"role": "user", "content": user_input})

        with st.spinner("AI 思考中..."):
            try:
                result = send_message(
                    session_id=st.session_state.current_session_id,
                    message=user_input,
                )
                reply = result.get("reply", "抱歉，处理出错了。")
                tool_calls = result.get("tool_calls")

                # 更新当前 session_id（新建会话时后端返回新的 ID）
                new_session_id = result.get("session_id")
                if new_session_id and new_session_id != st.session_state.current_session_id:
                    st.session_state.current_session_id = new_session_id

                # 显示 Agent 回复
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": reply,
                })

                # 如果有工具调用，显示提示
                if tool_calls:
                    st.caption(f"🔧 Agent 调用了工具：{len(tool_calls)} 次")

            except Exception as e:
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": f"❌ 请求失败：{str(e)}",
                })

        st.rerun()
