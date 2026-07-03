# ── 前端 Streamlit 服务 ─────────────────────────────────────────
# 基于 Python 3.11，运行 Streamlit 应用

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建 Streamlit 配置目录
RUN mkdir -p /root/.streamlit

# Streamlit 配置：禁用自动打开浏览器、允许外部访问
RUN echo '[server]\n\
headless = true\n\
address = "0.0.0.0"\n\
port = 8501\n\
enableCORS = false\n\
enableXsrfProtection = false\n'\
> /root/.streamlit/config.toml

# 暴露端口
EXPOSE 8501

# 启动服务
CMD ["streamlit", "run", "app.py", "--server.port=8501"]
