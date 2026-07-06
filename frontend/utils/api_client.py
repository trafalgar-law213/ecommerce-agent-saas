"""
Streamlit 前端 — API 调用工具。

封装所有对 FastAPI 后端的 HTTP 请求，统一处理错误和响应解析。
"""

import os
import json
import requests
from urllib.parse import quote
from typing import Optional, Tuple, Generator, Dict, Any

# 后端地址（环境变量可配，默认本地开发地址）
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").strip().rstrip("/")


def check_backend_health() -> Tuple[bool, str]:
    """检查后端健康状态。返回 (是否正常, 消息)。"""
    try:
        resp = requests.get(f"{BACKEND_URL}/api/health", timeout=3)
        data = resp.json()
        return True, f"{data.get('app', 'FastAPI')} v{data.get('version', '?')}"
    except requests.ConnectionError:
        return False, "无法连接后端服务，请确认 docker-compose up 已启动"
    except requests.Timeout:
        return False, "后端响应超时"
    except Exception as e:
        return False, str(e)


def send_message(session_id: Optional[str], message: str) -> dict:
    """发送对话消息（非流式）。"""
    payload = {"message": message}
    if session_id:
        payload["session_id"] = session_id
    resp = requests.post(f"{BACKEND_URL}/api/chat", json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


def send_message_stream(
    session_id: Optional[str], message: str
) -> Generator[Dict[str, Any], None, None]:
    """发送对话消息（流式 SSE）。

    逐事件 yield，事件类型：
    - {"type": "text", "content": "..."}
    - {"type": "tool_start", "tool": "...", "args": {...}}
    - {"type": "tool_end", "tool": "...", "result_preview": "..."}
    - {"type": "done", "session_id": "...", "duration_ms": N, "tool_calls": [...]}
    - {"type": "error", "message": "..."}

    Yields:
        Dict[str, Any]: SSE 事件数据
    """
    payload = {"message": message}
    if session_id:
        payload["session_id"] = session_id

    resp = requests.post(
        f"{BACKEND_URL}/api/chat/stream",
        json=payload,
        timeout=180,
        stream=True,
    )
    resp.raise_for_status()

    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("data: "):
            data_str = line[6:]
            try:
                event = json.loads(data_str)
                yield event
            except json.JSONDecodeError:
                continue


def get_sessions() -> list:
    """获取所有会话列表。"""
    resp = requests.get(f"{BACKEND_URL}/api/sessions", timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_session_messages(session_id: str) -> list:
    """获取某个会话的历史消息。"""
    resp = requests.get(f"{BACKEND_URL}/api/sessions/{session_id}/messages", timeout=10)
    resp.raise_for_status()
    return resp.json()


def upload_csv(file) -> dict:
    """上传 CSV 文件。"""
    files = {"file": (file.name, file.getvalue(), "text/csv")}
    resp = requests.post(f"{BACKEND_URL}/api/upload/csv", files=files, timeout=30)
    resp.raise_for_status()
    return resp.json()


def upload_knowledge(file) -> dict:
    """上传知识库文档。"""
    files = {"file": (file.name, file.getvalue())}
    resp = requests.post(
        f"{BACKEND_URL}/api/knowledge/upload", files=files, timeout=30
    )
    resp.raise_for_status()
    return resp.json()


def get_analysis(file_id: str) -> dict:
    """获取 CSV 文件基本信息。"""
    resp = requests.get(f"{BACKEND_URL}/api/analysis/{file_id}", timeout=10)
    resp.raise_for_status()
    return resp.json()


def analyze_csv(file_id: str, query: str = "") -> dict:
    """对已上传的 CSV 文件执行分析查询。"""
    resp = requests.post(
        f"{BACKEND_URL}/api/upload/csv/{file_id}/analyze",
        params={"query": query},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def get_uploaded_files() -> list:
    """获取所有已上传的文件列表。"""
    resp = requests.get(f"{BACKEND_URL}/api/upload/csv", timeout=10)
    resp.raise_for_status()
    return resp.json()


def search_knowledge(query: str, synthesize: bool = True) -> dict:
    """搜索知识库，默认启用 AI 合成回答。"""
    resp = requests.get(
        f"{BACKEND_URL}/api/knowledge/search",
        params={"q": query, "synthesize": synthesize},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def get_knowledge_documents() -> list:
    """获取知识库已上传文档列表。"""
    resp = requests.get(f"{BACKEND_URL}/api/knowledge/documents", timeout=10)
    resp.raise_for_status()
    return resp.json()


def delete_knowledge_document(filename: str) -> dict:
    """从知识库中删除指定文档。"""
    encoded = quote(filename, safe="")
    resp = requests.delete(
        f"{BACKEND_URL}/api/knowledge/documents/{encoded}", timeout=10
    )
    resp.raise_for_status()
    return resp.json()


def delete_session(session_id: str) -> bool:
    """删除会话。"""
    resp = requests.delete(f"{BACKEND_URL}/api/sessions/{session_id}", timeout=10)
    return resp.status_code == 200


# ── 可观测性 API ─────────────────────────────────────────────

def get_observability_traces(limit: int = 50, offset: int = 0) -> dict:
    """获取 Agent 调用追踪记录列表。"""
    resp = requests.get(
        f"{BACKEND_URL}/api/observability/traces",
        params={"limit": limit, "offset": offset},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def get_observability_stats() -> dict:
    """获取 Agent 调用聚合统计数据。"""
    resp = requests.get(f"{BACKEND_URL}/api/observability/stats", timeout=10)
    resp.raise_for_status()
    return resp.json()
