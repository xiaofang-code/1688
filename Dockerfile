FROM python:3.11-slim

# 安装系统依赖（Playwright 需要）
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libwayland-client0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 复制项目文件
COPY pyproject.toml .
COPY lib/ lib/
COPY config/ config/
COPY api.py .

# 安装依赖
RUN uv sync --frozen --no-cache

# 安装 Playwright 浏览器
RUN uv run playwright install chromium
RUN uv run playwright install-deps chromium

# 暴露端口
EXPOSE 8000

# 启动 API 服务
CMD ["uv", "run", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]

