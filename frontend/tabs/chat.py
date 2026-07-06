"""
对话助手页面（Tab 1）。

多轮对话界面：
- 左侧：会话列表（新建/切换/删除）
- 右侧：聊天区域（历史消息 + 流式输入）
"""

import time
import streamlit as st
from utils.api_client import (
    send_message,
    send_message_stream,
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
    """右侧聊天区域：消息展示 + 流式发送。"""
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
                    "- 📚 退货流程是什么？")
        else:
            for msg in st.session_state.chat_messages:
                role = msg["role"]
                content = msg["content"]
                with st.chat_message(role):
                    st.markdown(content)
                    # 显示工具调用详情
                    if msg.get("tool_info"):
                        with st.expander("🔧 查看工具调用详情", expanded=False):
                            st.caption(msg["tool_info"])

    st.divider()

    # ── 输入区 ────────────────────────────────────────────────
    user_input = st.chat_input("输入你的问题...", key="chat_input")

    if user_input:
        # 立即显示用户消息
        st.session_state.chat_messages.append({"role": "user", "content": user_input})

        # 使用流式调用
        with st.chat_message("assistant"):
            # 占位符：流式文本 + 状态信息
            text_placeholder = st.empty()
            status_placeholder = st.empty()

            full_text = []
            tool_info_parts = []
            final_session_id = st.session_state.current_session_id

            try:
                event_generator = send_message_stream(
                    session_id=st.session_state.current_session_id,
                    message=user_input,
                )

                for event in event_generator:
                    event_type = event.get("type", "")

                    if event_type == "text":
                        # 流式文本内容
                        chunk = event.get("content", "")
                        full_text.append(chunk)
                        text_placeholder.markdown("".join(full_text) + "▌")

                    elif event_type == "tool_start":
                        tool_name = event.get("tool", "unknown")
                        tool_args = event.get("args", {})
                        # 友好的工具名称映射
                        tool_labels = {
                            "analyze_sales_data": "📊 正在分析销售数据...",
                            "search_knowledge_base": "📚 正在检索知识库...",
                            "generate_marketing_copy": "✍️ 正在生成文案...",
                        }
                        label = tool_labels.get(tool_name, f"🔧 正在调用 {tool_name}...")
                        status_placeholder.info(label)

                    elif event_type == "tool_end":
                        tool_name = event.get("tool", "unknown")
                        result_preview = event.get("result_preview", "")
                        status_placeholder.success(f"✅ {tool_name} 完成")
                        tool_info_parts.append(
                            f"**{tool_name}** 返回 {len(result_preview)} 字符"
                        )

                    elif event_type == "done":
                        # 移除光标，显示完整文本
                        final_text = "".join(full_text)
                        text_placeholder.markdown(final_text)

                        # 更新 session_id
                        new_id = event.get("session_id")
                        if new_id:
                            final_session_id = new_id

                        # 显示性能指标
                        duration_ms = event.get("duration_ms", 0)
                        duration_s = duration_ms / 1000
                        tool_calls = event.get("tool_calls") or []

                        metrics_parts = []
                        if duration_ms > 0:
                            metrics_parts.append(f"⏱ {duration_s:.1f}s")
                        if tool_calls:
                            metrics_parts.append(f"🔧 {len(tool_calls)} 次工具调用")

                        if metrics_parts:
                            status_placeholder.caption(" · ".join(metrics_parts))
                        else:
                            status_placeholder.empty()

                    elif event_type == "error":
                        status_placeholder.error(f"❌ {event.get('message', '未知错误')}")

            except Exception as e:
                status_placeholder.error(f"❌ 请求失败：{str(e)}")
                # 回退到非流式调用
                if not full_text:
                    try:
                        result = send_message(
                            session_id=st.session_state.current_session_id,
                            message=user_input,
                        )
                        final_text = result.get("reply", "抱歉，处理出错了。")
                        text_placeholder.markdown(final_text)
                        new_id = result.get("session_id")
                        if new_id:
                            final_session_id = new_id
                    except Exception as fallback_error:
                        text_placeholder.markdown(f"❌ 请求失败：{str(fallback_error)}")

            # 保存消息到 session_state
            final_text = "".join(full_text)
            if final_text:
                tool_info = "\n".join(tool_info_parts) if tool_info_parts else None
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": final_text,
                    "tool_info": tool_info,
                })

            # 更新 session_id
            if final_session_id != st.session_state.current_session_id:
                st.session_state.current_session_id = final_session_id

        st.rerun()
