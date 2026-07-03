"""
应用配置管理。

所有配置项通过环境变量读取，提供合理的默认值用于本地开发。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 自动加载 backend/../.env 文件
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# 项目根目录（backend/）
BASE_DIR = Path(__file__).resolve().parent.parent

# ── DeepSeek API 配置 ──────────────────────────────────────────
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your_deepseek_api_key_here")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# ── 应用配置 ────────────────────────────────────────────────────
APP_NAME = os.getenv("APP_NAME", "电商智能客服与选品助手")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")

# ── 数据库配置 ──────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'app.db'}")

# ── 文件存储配置 ────────────────────────────────────────────────
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "data" / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ── Chroma 向量库配置 ───────────────────────────────────────────
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", BASE_DIR / "data" / "chroma"))
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
