# ── 后端 FastAPI 服务 ───────────────────────────────────────────
# 基于 Python 3.11，使用 uvicorn 运行

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（chromadb 可能需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/
COPY data/ ./data/

# 声明挂载点（运行时数据持久化）
VOLUME ["/app/data"]

# 暴露端口
EXPOSE 8000

# 启动服务
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
