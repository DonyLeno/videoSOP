# 阶段 4.2 批次 G：纯应用镜像（数据库拆分为独立 mariadb 服务，见 docker-compose.yml）
ARG PYTHON_BASE_IMAGE=docker.m.daocloud.io/library/python:3.12-slim
FROM ${PYTHON_BASE_IMAGE}
ARG TARGETARCH
ARG APP_VERSION=""

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
ENV APP_VERSION=${APP_VERSION}
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}

WORKDIR /app

RUN if [ -f /etc/apt/sources.list ]; then sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list; fi && \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; fi

# libgl1/libglib2.0-0：OpenCV 运行依赖；xz-utils：ffmpeg 静态包解压
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    libgl1 \
    libglib2.0-0 \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# 静态 ffmpeg（官方源无 ffmpeg，静态包免依赖且跨架构可用）
RUN set -eux; \
    case "${TARGETARCH:-}" in \
        amd64) ffmpeg_pkg="ffmpeg-release-amd64-static.tar.xz" ;; \
        arm64) ffmpeg_pkg="ffmpeg-release-arm64-static.tar.xz" ;; \
        *) echo "Unsupported TARGETARCH: ${TARGETARCH:-}" >&2; exit 1 ;; \
    esac; \
    tmpdir="$(mktemp -d)"; \
    cd "${tmpdir}"; \
    curl -L -o ffmpeg.tar.xz "https://johnvansickle.com/ffmpeg/releases/${ffmpeg_pkg}"; \
    tar -xJf ffmpeg.tar.xz; \
    dir="$(find . -maxdepth 1 -type d -name 'ffmpeg-*-static' | head -n 1)"; \
    mv "${dir}/ffmpeg" "${dir}/ffprobe" /usr/local/bin/; \
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe; \
    cd /; \
    rm -rf "${tmpdir}"

COPY requirements.txt .

RUN pip install --no-cache-dir --retries 10 --timeout 300 -r requirements.txt

# Copy project files
COPY . .

RUN chmod +x /app/docker/docker-entrypoint.sh

# Expose port
EXPOSE 8000

# Run the server
CMD ["/app/docker/docker-entrypoint.sh"]
