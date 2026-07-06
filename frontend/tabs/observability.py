"""
Agent 可观测性面板（Tab 4）。

展示 Agent 调用的性能指标：
- 聚合统计卡片（总调用次数、平均耗时、Token 消耗等）
- 工具使用分布
- 最近调用追踪列表
"""

import streamlit as st
import pandas as pd
from utils.api_client import get_observability_traces, get_observability_stats


def render():
    st.header("🔍 Agent 可观测性")
    st.caption("监控每次 Agent 调用的耗时、工具使用、Token 消耗等指标")

    # ── 自动刷新 ──────────────────────────────────────────────
    col_refresh, col_auto = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 刷新数据", use_container_width=True):
            st.rerun()
    with col_auto:
        st.caption("提示：数据实时从后端拉取，对话后点击刷新查看最新指标")

    st.divider()

    # ── 加载统计数据 ──────────────────────────────────────────
    try:
        stats = get_observability_stats()
    except Exception as e:
        st.error(f"无法加载可观测性数据：{e}")
        st.info("请确认后端服务已启动，且至少进行过一次 Agent 对话")
        return

    if stats.get("total_traces", 0) == 0:
        st.info("📭 暂无 Agent 调用记录。去「对话助手」Tab 发送一条消息后，这里就会出现数据。")
        return

    # ── 统计卡片行 1 ──────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="📞 总调用次数",
            value=stats["total_traces"],
            delta=f"近24h: {stats['recent_traces_24h']}",
        )

    with col2:
        success_rate = (
            stats["total_success"] / stats["total_traces"] * 100
            if stats["total_traces"] > 0 else 0
        )
        st.metric(
            label="✅ 成功率",
            value=f"{success_rate:.1f}%",
            delta=f"{stats['total_errors']} 次失败" if stats["total_errors"] > 0 else None,
        )

    with col3:
        avg_ms = stats["avg_duration_ms"]
        avg_s = avg_ms / 1000
        st.metric(
            label="⏱ 平均耗时",
            value=f"{avg_s:.1f}s",
            delta=f"最长 {stats['max_duration_ms'] / 1000:.1f}s",
        )

    with col4:
        st.metric(
            label="🪙 总 Token 消耗",
            value=f"{stats['total_tokens']:,}",
            delta=f"平均 {stats['avg_tokens_per_call']:.0f}/次",
        )

    # ── 统计卡片行 2 ──────────────────────────────────────────
    col5, col6 = st.columns(2)

    with col5:
        st.metric(
            label="🔄 平均工具调用轮次",
            value=f"{stats['avg_turns']:.1f} 轮",
        )

    with col6:
        tool_dist = stats.get("tool_usage_distribution", {})
        most_used = max(tool_dist, key=tool_dist.get) if tool_dist else "—"
        st.metric(
            label="🔧 最常用工具",
            value=most_used if most_used != "—" else "—",
        )

    st.divider()

    # ── 工具使用分布 ──────────────────────────────────────────
    if tool_dist:
        st.subheader("🔧 工具使用分布")
        df_tools = pd.DataFrame(
            {"工具名称": list(tool_dist.keys()), "调用次数": list(tool_dist.values())}
        ).sort_values("调用次数", ascending=False)
        st.bar_chart(df_tools.set_index("工具名称"), use_container_width=True)

    st.divider()

    # ── 最近调用追踪列表 ──────────────────────────────────────
    st.subheader("📋 最近调用记录")

    try:
        traces_data = get_observability_traces(limit=30)
        traces = traces_data.get("traces", [])
    except Exception:
        st.warning("无法加载追踪记录")
        return

    if not traces:
        st.caption("（暂无记录）")
        return

    # 构建表格数据
    rows = []
    for t in traces:
        duration_s = (t.get("duration_ms") or 0) / 1000
        tools_called = t.get("tools_called") or []
        tools_str = ", ".join(tools_called) if tools_called else "（无工具）"
        token_total = (t.get("token_usage") or {}).get("total", 0)

        status_icon = "✅" if t.get("status") == "success" else "❌"

        rows.append({
            "时间": (t.get("created_at") or "")[:19],
            "查询": (t.get("user_query") or "")[:50],
            "状态": status_icon,
            "耗时": f"{duration_s:.1f}s",
            "工具": tools_str[:40],
            "轮次": t.get("turn_count", 1),
            "Token": token_total,
        })

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "时间": st.column_config.TextColumn(width="small"),
            "查询": st.column_config.TextColumn(width="medium"),
            "状态": st.column_config.TextColumn(width="small"),
            "耗时": st.column_config.TextColumn(width="small"),
            "工具": st.column_config.TextColumn(width="medium"),
            "轮次": st.column_config.NumberColumn(width="small"),
            "Token": st.column_config.NumberColumn(width="small"),
        },
    )

    st.caption(f"共 {traces_data.get('total', 0)} 条记录，显示最近 {len(traces)} 条")
