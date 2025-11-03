# 使用官方Python运行时作为基础镜像
FROM python:3.11-slim

# 设置标签信息
LABEL maintainer="wwwzhouhui <75271002@qq.com>" \
      version="1.0.0" \
      description="PDFTranslate MCP Server - 基于BabelDOC的PDF文档翻译服务" \
      org.opencontainers.image.source="https://github.com/wwwzhouhui/pdftranslate_web"

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # MCP服务器配置
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8006 \
    # 翻译默认配置
    DEFAULT_LANG_IN=en \
    DEFAULT_LANG_OUT=zh \
    QPS=4 \
    WATERMARK_OUTPUT_MODE=no_watermark \
    NO_DUAL=false \
    NO_MONO=false \
    # 日志配置
    LOG_LEVEL=INFO

# 安装运行时系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgcc-s1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 复制MCP服务器项目文件
COPY pyproject.toml /app/
COPY main.py /app/
COPY config.ini /app/
COPY .env.example /app/
COPY README.md /app/

# 安装Python依赖
RUN pip install --upgrade pip && \
    pip install . && \
    pip install cos-python-sdk-v5

# 创建非root用户和home目录
RUN groupadd -r mcpuser && useradd -r -g mcpuser -m mcpuser

# 预先下载TikToken模型文件以避免运行时网络下载
# 使用root用户执行，然后设置正确的权限
RUN python -c "import tiktoken; enc = tiktoken.get_encoding('o200k_base'); print('TikToken model loaded successfully')" || \
    python -c "import tiktoken; enc = tiktoken.encoding_for_model('gpt-4o'); print('GPT-4o tokenizer loaded successfully')"

# 预先下载BabelDOC字体文件以避免运行时网络超时
COPY preload_fonts.py /tmp/preload_fonts.py
RUN python3 /tmp/preload_fonts.py && rm /tmp/preload_fonts.py

# 创建必要的目录并设置权限
RUN mkdir -p /app/temp /app/uploads /app/downloads /app/logs \
    /home/mcpuser/.cache/babeldoc/tiktoken \
    /home/mcpuser/.cache/babeldoc/fonts \
    && chown -R mcpuser:mcpuser /app /home/mcpuser

# 确保字体缓存目录可以被mcpuser访问
# 方案1: 复制字体文件（推荐）
RUN if [ -d /root/.cache/babeldoc/fonts ]; then \
        echo "=== 复制字体文件到mcpuser目录 ==="; \
        mkdir -p /home/mcpuser/.cache/babeldoc/fonts; \
        cp -r /root/.cache/babeldoc/fonts/* /home/mcpuser/.cache/babeldoc/fonts/ 2>/dev/null || echo "无字体文件可复制"; \
        chown -R mcpuser:mcpuser /home/mcpuser/.cache/babeldoc; \
        chmod -R 755 /home/mcpuser/.cache/babeldoc; \
        echo "✅ 字体权限设置完成"; \
    fi

# 方案2: 创建符号链接（备用）
RUN if [ -d /root/.cache/babeldoc/fonts ] && [ ! -L /home/mcpuser/.cache/babeldoc/fonts ]; then \
        rmdir /home/mcpuser/.cache/babeldoc/fonts 2>/dev/null || true; \
        ln -sf /root/.cache/babeldoc/fonts /home/mcpuser/.cache/babeldoc/fonts; \
        echo "✅ 创建字体符号链接"; \
    fi

# 确保TikToken缓存目录有正确的权限（需要在用户创建后再次设置）
RUN mkdir -p /root/.cache/tiktoken 2>/dev/null || true

# 切换到非root用户
USER mcpuser

# 暴露MCP服务器端口
EXPOSE 8006

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${MCP_PORT:-8006}/sse || exit 1

# 启动MCP服务器
CMD ["python", "main.py"]