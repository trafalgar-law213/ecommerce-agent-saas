"""
可观测性路由 — Agent 调用追踪查询与统计。

GET  /api/observability/traces  — 追踪记录列表
GET  /api/observability/stats   — 聚合统计
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from ..database import get_db
from ..models.agent_trace import AgentTrace
from ..schemas.observability import TraceItem, TraceListResponse, ObservabilityStats

router = APIRouter(prefix="/api/observability", tags=["observability"])


@router.get("/traces", response_model=TraceListResponse)
def list_traces(
    limit: int = Query(default=50, ge=1, le=200, description="返回条数"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    db: DBSession = Depends(get_db),
):
    """获取 Agent 调用追踪记录列表（按时间倒序）。"""
    total = db.query(func.count(AgentTrace.id)).scalar() or 0

    traces = (
        db.query(AgentTrace)
        .order_by(AgentTrace.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for t in traces:
        items.append(TraceItem(
            id=t.id,
            session_id=t.session_id,
            user_query=t.user_query,
            reply_summary=t.reply_summary,
            tools_called=t.tools_called,
            tool_count=t.tool_count,
            duration_ms=t.duration_ms,
            turn_count=t.turn_count,
            token_usage=t.token_usage,
            status=t.status,
            error_message=t.error_message,
            created_at=t.created_at.isoformat() if t.created_at else None,
        ))

    return TraceListResponse(traces=items, total=total)


@router.get("/stats", response_model=ObservabilityStats)
def get_stats(db: DBSession = Depends(get_db)):
    """获取 Agent 调用的聚合统计数据。"""
    all_traces = db.query(AgentTrace)
    total = all_traces.count()

    if total == 0:
        return ObservabilityStats()

    # 成功/失败计数
    total_success = all_traces.filter(AgentTrace.status == "success").count()
    total_errors = all_traces.filter(AgentTrace.status == "error").count()

    # 耗时统计
    duration_stats = db.query(
        func.avg(AgentTrace.duration_ms),
        func.max(AgentTrace.duration_ms),
        func.min(AgentTrace.duration_ms),
    ).filter(AgentTrace.duration_ms.isnot(None)).first()

    avg_duration = duration_stats[0] or 0.0
    max_duration = duration_stats[1] or 0
    min_duration = duration_stats[2] or 0

    # Token 统计（SQLite 不支持 JSON 字段内联查询，遍历计算）
    total_tokens = 0
    token_traces = db.query(AgentTrace.token_usage).filter(
        AgentTrace.token_usage.isnot(None)
    ).all()
    for (token_usage,) in token_traces:
        if isinstance(token_usage, dict):
            total_tokens += token_usage.get("total", 0)
    avg_tokens = (total_tokens / total) if total > 0 else 0.0

    # 平均轮次
    avg_turns_result = db.query(func.avg(AgentTrace.turn_count)).scalar()
    avg_turns = avg_turns_result or 0.0

    # 24 小时内的追踪数
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_24h = all_traces.filter(AgentTrace.created_at >= since_24h).count()

    # 工具使用分布（遍历所有记录统计）
    tool_distribution: dict = {}
    all_traces_with_tools = (
        db.query(AgentTrace.tools_called)
        .filter(AgentTrace.tools_called.isnot(None))
        .all()
    )
    for (tools_list,) in all_traces_with_tools:
        if isinstance(tools_list, list):
            for tool_name in tools_list:
                tool_distribution[tool_name] = tool_distribution.get(tool_name, 0) + 1

    return ObservabilityStats(
        total_traces=total,
        total_success=total_success,
        total_errors=total_errors,
        avg_duration_ms=round(avg_duration, 1),
        max_duration_ms=max_duration,
        min_duration_ms=min_duration,
        total_tokens=total_tokens,
        avg_tokens_per_call=round(avg_tokens, 1),
        tool_usage_distribution=tool_distribution,
        recent_traces_24h=recent_24h,
        avg_turns=round(avg_turns, 1),
    )
