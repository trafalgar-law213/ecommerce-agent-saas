"""
Streamlit 前端 — API 调用工具。

封装所有对 FastAPI 后端的 HTTP 请求，统一处理错误和响应解析。
"""

import os
import requests
from typing import Optional, Tuple

# 后端地址（环境变量可配，默认本地开发地址）
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")


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
    """发送对话消息。"""
    payload = {"message": message}
    if session_id:
        payload["session_id"] = session_id
    resp = requests.post(f"{BACKEND_URL}/api/chat", json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


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
    """获取 CSV 分析结果。"""
    resp = requests.get(f"{BACKEND_URL}/api/analysis/{file_id}", timeout=10)
    resp.raise_for_status()
    return resp.json()


def search_knowledge(query: str) -> dict:
    """搜索知识库。"""
    resp = requests.get(
        f"{BACKEND_URL}/api/knowledge/search", params={"q": query}, timeout=10
    )
    resp.raise_for_status()
    return resp.json()


def delete_session(session_id: str) -> bool:
    """删除会话。"""
    resp = requests.delete(f"{BACKEND_URL}/api/sessions/{session_id}", timeout=10)
    return resp.status_code == 200
