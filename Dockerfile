# 使用官方Python运行时作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    git \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgcc-s1 \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY pyproject.toml /app/
COPY src/ /app/src/
COPY scripts/ /app/scripts/
COPY simaple/ /app/simaple/
COPY README.md /app/

# 安装Python依赖
RUN pip install --upgrade pip && \
    pip install -e .

# 使用root用户执行，然后设置正确的权限
RUN python -c "import tiktoken; enc = tiktoken.get_encoding('o200k_base'); print('TikToken model loaded successfully')" || \
    python -c "import tiktoken; enc = tiktoken.encoding_for_model('gpt-4o'); print('GPT-4o tokenizer loaded successfully')"

# 预先下载BabelDOC字体文件以避免运行时网络超时
COPY preload_fonts.py /tmp/preload_fonts.py
RUN python3 /tmp/preload_fonts.py && rm /tmp/preload_fonts.py

# 确保字体缓存目录存在且权限正确
RUN mkdir -p /root/.cache/babeldoc/fonts && \
    chmod -R 755 /root/.cache/babeldoc 2>/dev/null || true && \
    ls -lah /root/.cache/babeldoc/fonts/ | head -20

# 复制启动脚本
COPY docker/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# 暴露端口
EXPOSE 8000 7860

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["/app/start.sh"]