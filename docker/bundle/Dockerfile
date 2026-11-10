# 自包含离线镜像：内置 SQLite 数据库、已上传视频与检测结果，面向 linux/amd64 部署。
# 构建上下文由 docker/bundle/build_bundle.sh 生成（已包含 data/ 与 result/）。
ARG PYTHON_BASE_IMAGE=docker.m.daocloud.io/library/python:3.12-slim
FROM ${PYTHON_BASE_IMAGE}

ARG TARGETARCH=amd64
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=${PIP_INDEX_URL} \
    DB_MODE=sqlite \
    SQLITE_PATH=/app/data/geniview.sqlite3 \
    PORT=8000

WORKDIR /app

RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; fi && \
    if [ -f /etc/apt/sources.list ]; then sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list; fi && \
    apt-get update && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        curl \
        ffmpeg \
        libgl1 \
        libglib2.0-0 \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY constraints.txt .
# 依赖 wheel 由 build_bundle.sh 在宿主机预下载（构建机网络通常远快于 QEMU 容器）
COPY wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels -c constraints.txt -r requirements.txt \
    && rm -rf /wheels

COPY . .

EXPOSE 8000

# 单进程启动；数据库、视频、结果均已内置，无需外部 MySQL
CMD ["python", "server.py"]
