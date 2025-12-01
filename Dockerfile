FROM docker.m.daocloud.io/library/python:3.11-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 安装系统依赖（Playwright Chromium 需要）
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
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
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装依赖（不安装项目本身）
RUN uv sync --frozen --no-install-project --no-cache

# 复制项目文件
COPY README.md .
COPY lib/ lib/
COPY config/ config/
COPY api.py .

# 安装项目
RUN uv sync --frozen --no-cache

# 安装 Playwright 浏览器
RUN uv run playwright install chromium
RUN uv run playwright install-deps chromium

# 暴露端口
EXPOSE 8688

# 启动 API 服务
CMD ["uv", "run", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8688"]
