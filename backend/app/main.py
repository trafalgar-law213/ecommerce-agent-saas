"""
FastAPI 应用入口。

创建应用实例，注册路由，配置 CORS，并声明启动事件。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import APP_NAME, APP_VERSION
from .database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库表。"""
    init_db()
    yield


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="电商智能客服与选品助手 Agent SaaS — 基于 LangChain + DeepSeek",
    lifespan=lifespan,
)

# CORS 配置（允许 Streamlit 前端跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本地开发允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 健康检查端点 ────────────────────────────────────────────────

@app.get("/api/health", tags=["system"])
async def health_check():
    """健康检查端点，供前端和 Docker 探活使用。"""
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}


# ── 注册业务路由 ──────────────────────────────────────────────

from .routers import chat, session, upload
app.include_router(chat.router)
app.include_router(session.router)
app.include_router(upload.router)
# 后续周期激活：
# from .routers import analysis
# app.include_router(analysis.router)
