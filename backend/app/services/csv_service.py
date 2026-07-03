"""
CSV 数据分析服务。

使用 pandas 加载 CSV 文件，根据用户自然语言查询执行分析计算。
支持的查询类型：Top N 商品、利润率、趋势、分类汇总、基本统计。
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any


def _to_native(obj):
    """递归转换 numpy 类型为 Python 原生类型，确保 JSON 可序列化。"""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_to_native(v) for v in obj]
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


# 缓存已加载的 DataFrame（key = file_id）
_loaded_dfs: Dict[str, pd.DataFrame] = {}


def load_csv(file_path: Path) -> pd.DataFrame:
    """加载 CSV 文件为 pandas DataFrame。

    Args:
        file_path: CSV 文件的绝对路径

    Returns:
        pandas DataFrame

    Raises:
        ValueError: 文件为空或无法解析
    """
    df = pd.read_csv(file_path)

    if df.empty:
        raise ValueError("CSV 文件为空，请检查文件内容")

    # 自动清理列名（去除首尾空格）
    df.columns = df.columns.str.strip()
    return df


def get_file_info(df: pd.DataFrame) -> dict:
    """获取 CSV 文件的基本信息。

    Args:
        df: pandas DataFrame

    Returns:
        包含列名、行数、基本统计信息的字典
    """
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

    info = {
        "columns": df.columns.tolist(),
        "row_count": len(df),
        "numeric_columns": numeric_cols,
        "sample_head": df.head(5).to_dict(orient="records"),
    }

    # 如果有数值列，补充基本统计
    if numeric_cols:
        info["basic_stats"] = df[numeric_cols].describe().to_dict()

    return info


def analyze(df: pd.DataFrame, query: str) -> dict:
    """根据自然语言查询分析 CSV 数据。

    Args:
        df: pandas DataFrame
        query: 用户的自然语言查询，如"Top 5 商品""利润率""趋势"等

    Returns:
        分析结果字典，包含 result_type、data、summary 等字段
    """
    query_lower = query.lower()

    # ── 检测查询类型 ──────────────────────────────────────────
    # Top N 检测
    if _match_any(query_lower, ["top", "排名", "前", "最高", "最低", "top n"]):
        return _analyze_top_n(df, query)

    # 利润率检测
    if _match_any(query_lower, ["利润", "利润率", "profit", "margin", "毛利", "成本"]):
        return _analyze_profit(df, query)

    # 趋势检测
    if _match_any(query_lower, ["趋势", "变化", "趋势", "增长", "下降", "trend", "走势"]):
        return _analyze_trend(df, query)

    # 分类汇总检测
    if _match_any(query_lower, ["分类", "类别", "品类", "category", "汇总", "分组", "group"]):
        return _analyze_category(df, query)

    # 默认：返回整体概览
    return _analyze_overview(df)


def _match_any(query_lower: str, keywords: list) -> bool:
    """检查查询中是否包含任意关键词。"""
    return any(kw in query_lower for kw in keywords)


def _find_column(df: pd.DataFrame, candidates: list) -> Optional[str]:
    """在 DataFrame 中查找匹配的列名。

    Args:
        df: DataFrame
        candidates: 候选列名列表（按优先级排列）

    Returns:
        匹配到的列名，未找到返回 None
    """
    cols_lower = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in cols_lower:
            return cols_lower[c.lower()]
    return None


def _analyze_top_n(df: pd.DataFrame, query: str) -> dict:
    """分析 Top N 商品。

    自动识别数值列（销量/销售额）和名称列，计算排名。
    """
    # 尝试找到"名称"列和"数值"列
    name_col = _find_column(df, ["商品名称", "商品名", "产品名称", "product", "name", "商品"])
    amount_col = _find_column(df, ["销售额", "销售金额", "总销售额", "revenue", "sales", "金额"])
    qty_col = _find_column(df, ["销量", "销售数量", "数量", "quantity", "qty", "件数"])

    sort_col = amount_col or qty_col
    if not sort_col:
        return {
            "result_type": "top_n",
            "summary": "❌ 未找到可用于排名的数值列（如：销售额、销量），请检查 CSV 列名。",
            "data": {},
        }

    # 确定 Top N
    n = 5
    import re
    n_match = re.search(r"top\s*(\d+)", query, re.IGNORECASE)
    if n_match:
        n = int(n_match.group(1))
    # 也检测中文 "前X"
    cn_match = re.search(r"前\s*(\d+)", query)
    if cn_match:
        n = int(cn_match.group(1))

    # 排序
    descending = not _match_any(query.lower(), ["最低", "bottom", "最差", "最不"])
    top_df = df.sort_values(by=sort_col, ascending=not descending).head(n)

    if name_col:
        display_cols = [name_col, sort_col]
    else:
        display_cols = [c for c in df.columns if c == sort_col][:1]
        # 加上第一列作为标识
        if df.columns[0] not in display_cols:
            display_cols.insert(0, df.columns[0])

    # 确保列存在
    display_cols = [c for c in display_cols if c in df.columns]

    direction = "最高" if descending else "最低"
    return _to_native({
        "result_type": "top_n",
        "summary": f"📊 **{direction} {n} 名**（按 {sort_col} 排序）",
        "data": top_df[display_cols].to_dict(orient="records"),
        "columns": display_cols,
        "chart_type": "bar",
        "chart_title": f"{direction}{n}名商品 ({sort_col})",
        "chart_data": {
            "labels": top_df[name_col].tolist() if name_col else top_df.iloc[:, 0].tolist(),
            "values": top_df[sort_col].tolist(),
        },
    })


def _analyze_profit(df: pd.DataFrame, query: str) -> dict:
    """分析利润率/毛利。

    自动查找单价/销售额和成本列，计算利润。
    """
    revenue_col = _find_column(df, ["销售额", "总销售额", "单价", "售价", "revenue", "price", "金额"])
    cost_col = _find_column(df, ["成本", "成本价", "进价", "cost", "进货价"])
    profit_col = _find_column(df, ["利润", "毛利", "profit", "margin"])

    # 情况 1：已有利润列
    if profit_col:
        total_profit = float(df[profit_col].sum())
        avg_profit = float(df[profit_col].mean())
        return _to_native({
            "result_type": "profit",
            "summary": f"💰 **利润分析**\n- 总利润：¥{total_profit:,.2f}\n- 平均利润：¥{avg_profit:,.2f}",
            "data": {
                "total_profit": round(total_profit, 2),
                "avg_profit": round(avg_profit, 2),
            },
        })

    # 情况 2：有销售额和成本列，自动计算
    if revenue_col and cost_col:
        df_copy = df.copy()
        df_copy["利润"] = df_copy[revenue_col] - df_copy[cost_col]
        df_copy["利润率"] = (df_copy["利润"] / df_copy[revenue_col] * 100).round(1)

        total_revenue = float(df_copy[revenue_col].sum())
        total_cost = float(df_copy[cost_col].sum())
        total_profit = total_revenue - total_cost
        overall_margin = (total_profit / total_revenue * 100) if total_revenue else 0

        name_col = _find_column(df, ["商品名称", "商品名", "产品名称", "name", "商品"])
        top_profit = df_copy.nlargest(5, "利润率")

        return _to_native({
            "result_type": "profit",
            "summary": (
                f"💰 **利润率分析**\n"
                f"- 总销售额：¥{total_revenue:,.2f}\n"
                f"- 总成本：¥{total_cost:,.2f}\n"
                f"- 总利润：¥{total_profit:,.2f}\n"
                f"- 整体利润率：{overall_margin:.1f}%"
            ),
            "data": {
                "total_revenue": round(total_revenue, 2),
                "total_cost": round(total_cost, 2),
                "total_profit": round(total_profit, 2),
                "overall_margin_pct": round(overall_margin, 1),
            },
            "chart_type": "bar",
            "chart_title": "各商品利润率 Top 5",
            "chart_data": {
                "labels": top_profit[name_col].tolist() if name_col else top_profit.iloc[:, 0].tolist(),
                "values": top_profit["利润率"].tolist(),
            },
        })

    # 情况 3：没有相关列
    return {
        "result_type": "profit",
        "summary": "❌ 未找到利润、销售额或成本相关列，无法进行利润分析。请确保 CSV 包含相关数据列。",
        "data": {},
    }


def _analyze_trend(df: pd.DataFrame, query: str) -> dict:
    """分析销售趋势。

    自动识别日期列和数值列，按时间聚合分析趋势。
    """
    date_col = _find_column(df, ["日期", "时间", "日期时间", "date", "时间戳", "下单时间", "销售日期"])
    amount_col = _find_column(df, ["销售额", "总销售额", "金额", "revenue", "sales", "销量"])

    if not date_col:
        return {
            "result_type": "trend",
            "summary": "❌ 未找到日期相关列（如：日期、时间），无法分析趋势。",
            "data": {},
        }

    if not amount_col:
        return {
            "result_type": "trend",
            "summary": "❌ 未找到数值相关列（如：销售额、销量），无法分析趋势。",
            "data": {},
        }

    # 转换日期并排序
    df_copy = df.copy()
    df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors="coerce")
    df_copy = df_copy.dropna(subset=[date_col])

    if df_copy.empty:
        return {
            "result_type": "trend",
            "summary": "❌ 日期列解析失败，请检查日期格式。",
            "data": {},
        }

    # 按日聚合
    daily = df_copy.groupby(df_copy[date_col].dt.date)[amount_col].sum().reset_index()
    daily.columns = ["date", "total"]

    if len(daily) < 2:
        return _to_native({
            "result_type": "trend",
            "summary": "📈 **趋势分析**\n数据仅覆盖 1 天，不足以分析趋势。建议上传更长时间跨度的数据。",
            "data": daily.to_dict(orient="records"),
        })

    # 计算趋势指标
    first_half = float(daily.head(len(daily) // 2)["total"].mean())
    second_half = float(daily.tail(len(daily) // 2)["total"].mean())
    change_pct = ((second_half - first_half) / first_half * 100) if first_half else 0

    direction = "上升" if change_pct > 0 else "下降"
    return _to_native({
        "result_type": "trend",
        "summary": (
            f"📈 **销售趋势分析**\n"
            f"- 数据范围：{daily['date'].min()} ~ {daily['date'].max()}（共 {len(daily)} 天）\n"
            f"- 前半段日均：¥{first_half:,.2f}\n"
            f"- 后半段日均：¥{second_half:,.2f}\n"
            f"- 趋势：{direction} {abs(change_pct):.1f}%"
        ),
        "data": daily.to_dict(orient="records"),
        "chart_type": "line",
        "chart_title": f"每日{amount_col}趋势",
        "chart_data": {
            "labels": [str(d) for d in daily["date"].tolist()],
            "values": daily["total"].tolist(),
        },
    })


def _analyze_category(df: pd.DataFrame, query: str) -> dict:
    """按分类汇总分析。"""
    cat_col = _find_column(df, ["分类", "类别", "品类", "商品分类", "category", "类目", "类型", "大类"])
    amount_col = _find_column(df, ["销售额", "总销售额", "金额", "revenue", "sales", "销量"])

    if not cat_col:
        return {
            "result_type": "category",
            "summary": "❌ 未找到分类相关列（如：分类、类别、品类），无法进行分类汇总。",
            "data": {},
        }

    if not amount_col:
        return {
            "result_type": "category",
            "summary": "❌ 未找到数值相关列（如：销售额、销量），无法进行汇总计算。",
            "data": {},
        }

    grouped = df.groupby(cat_col)[amount_col].agg(["sum", "mean", "count"]).reset_index()
    grouped.columns = [cat_col, f"总{amount_col}", f"平均{amount_col}", "商品数"]
    grouped = grouped.sort_values(by=f"总{amount_col}", ascending=False)

    return _to_native({
        "result_type": "category",
        "summary": f"📂 **分类汇总**（按 {amount_col}）\n共 {len(grouped)} 个分类",
        "data": grouped.to_dict(orient="records"),
        "chart_type": "bar",
        "chart_title": f"各分类{amount_col}对比",
        "chart_data": {
            "labels": grouped[cat_col].tolist(),
            "values": grouped[f"总{amount_col}"].tolist(),
        },
    })


def _analyze_overview(df: pd.DataFrame) -> dict:
    """整体数据概览。"""
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

    summary_parts = [f"📋 **数据概览**\n- 共 {len(df)} 行，{len(df.columns)} 列"]

    if numeric_cols:
        for col in numeric_cols[:5]:  # 最多显示 5 个数值列的汇总
            total = df[col].sum()
            avg = df[col].mean()
            summary_parts.append(f"- {col}：合计 {total:,.2f}，均值 {avg:,.2f}")

    return _to_native({
        "result_type": "overview",
        "summary": "\n".join(summary_parts),
        "data": {
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": df.columns.tolist(),
            "numeric_summary": {
                col: {"sum": round(float(df[col].sum()), 2), "mean": round(float(df[col].mean()), 2)}
                for col in numeric_cols[:5]
            } if numeric_cols else {},
        },
    })
