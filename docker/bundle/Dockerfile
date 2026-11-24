# 自包含离线镜像：内置 SQLite 数据库、已上传视频、检测结果与 Linux amd64 依赖，面向 linux/amd64 部署。
# 构建上下文由 docker/bundle/build_bundle.sh 生成（含 data/、result/、pylibs/、ffmpeg/ffprobe），构建过程无需联网。
ARG PYTHON_BASE_IMAGE=docker.m.daocloud.io/library/python:3.12-slim
FROM ${PYTHON_BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DB_MODE=sqlite \
    SQLITE_PATH=/app/data/geniview.sqlite3 \
    PORT=8000 \
    TZ=Asia/Shanghai

WORKDIR /app

# 仅安装 OpenCV 运行期需要的 glib（apt 只拉少量包）
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; fi && \
    if [ -f /etc/apt/sources.list ]; then sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list; fi && \
    apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 宿主机预下载的 ffmpeg / ffprobe（linux amd64 静态二进制）
COPY ffmpeg /usr/local/bin/ffmpeg
COPY ffprobe /usr/local/bin/ffprobe
RUN chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe

# 宿主机用 uv 预装的 linux x86_64 依赖，避免在 QEMU 容器内联网安装
COPY pylibs/ /usr/local/lib/python3.12/site-packages/

COPY . .

EXPOSE 8000

# 单进程启动；数据库、视频、结果均已内置，无需外部 MySQL
CMD ["python", "server.py"]
