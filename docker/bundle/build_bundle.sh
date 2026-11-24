#!/bin/bash
# 打包自包含 Docker 镜像（linux/amd64）：工程代码 + SQLite 数据 + 上传视频 + 检测结果。
# 用法：bash docker/bundle/build_bundle.sh
# 产出：docker/geniview-bundle-linux-amd64.tar.gz（docker load 即可运行）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CTX_DIR="${SCRIPT_DIR}/build-context"
IMAGE="${IMAGE_NAME:-geniview-bundle:latest}"
PLATFORM="${PLATFORM:-linux/amd64}"
PYTHON_BASE_IMAGE="${PYTHON_BASE_IMAGE:-docker.m.daocloud.io/library/python:3.12-slim}"
OUT_FILE="${ROOT_DIR}/docker/geniview-bundle-${PLATFORM#linux/}-$(date +%Y%m%d).tar.gz"

echo "[1/5] 生成构建上下文: ${CTX_DIR}"
rm -rf "${CTX_DIR}"
mkdir -p "${CTX_DIR}"
rsync -a \
  --exclude '.git' \
  --exclude 'backups' \
  --exclude 'logs' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.venv' \
  --exclude 'venv' \
  --exclude '.env' \
  --exclude 'docker' \
  --exclude 'result/qwen_input' \
  --exclude '*.tar' \
  --exclude '*.tar.gz' \
  "${ROOT_DIR}/" "${CTX_DIR}/"
cp "${SCRIPT_DIR}/Dockerfile" "${CTX_DIR}/Dockerfile"
cp "${SCRIPT_DIR}/.dockerignore" "${CTX_DIR}/.dockerignore"
cp "${SCRIPT_DIR}/constraints.txt" "${CTX_DIR}/constraints.txt"
mkdir -p "${CTX_DIR}/data" "${CTX_DIR}/result"

echo "[2/5] 迁移 MySQL 数据到 SQLite"
rm -f "${CTX_DIR}/data/geniview.sqlite3"
PYTHONPATH="${ROOT_DIR}" python3 "${SCRIPT_DIR}/migrate_to_sqlite.py" "${CTX_DIR}/data/geniview.sqlite3"

echo "[3/5] 在宿主机预装 linux amd64 依赖（uv，秒级完成）"
rm -rf "${CTX_DIR}/pylibs"
# 在构建目录内用相对路径执行，避免工程路径中的空格影响 uv 参数解析
(
  cd "${CTX_DIR}"
  uv pip install \
    --target pylibs \
    --python-version 3.12 \
    --python-platform x86_64-manylinux_2_28 \
    --only-binary :all: \
    -r requirements.txt \
    -c constraints.txt \
    --index-url https://mirrors.aliyun.com/pypi/simple
)

echo "[3/5] 下载 linux amd64 静态 ffmpeg"
FFMPEG_TMP="$(mktemp -d)"
curl -L --retry 3 --fail -o "${FFMPEG_TMP}/ffmpeg.tar.xz" \
  "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
tar -xJf "${FFMPEG_TMP}/ffmpeg.tar.xz" -C "${FFMPEG_TMP}"
FFMPEG_DIR="$(find "${FFMPEG_TMP}" -maxdepth 1 -type d -name 'ffmpeg-*-static' | head -n 1)"
cp "${FFMPEG_DIR}/ffmpeg" "${CTX_DIR}/ffmpeg"
cp "${FFMPEG_DIR}/ffprobe" "${CTX_DIR}/ffprobe"
chmod +x "${CTX_DIR}/ffmpeg" "${CTX_DIR}/ffprobe"
rm -rf "${FFMPEG_TMP}"

echo "[4/5] 构建镜像 ${IMAGE} (${PLATFORM})"
docker buildx build \
  --platform "${PLATFORM}" \
  --build-arg "PYTHON_BASE_IMAGE=${PYTHON_BASE_IMAGE}" \
  --provenance=false \
  --load \
  -t "${IMAGE}" \
  "${CTX_DIR}"

echo "[5/5] 导出镜像: ${OUT_FILE}"
docker save "${IMAGE}" | gzip -9 > "${OUT_FILE}"

echo "[完成]"
docker image inspect --format '镜像: {{.RepoTags}} | 平台: {{.Os}}/{{.Architecture}} | 大小: {{.Size}} bytes' "${IMAGE}"
ls -lh "${OUT_FILE}"
echo
echo "在 Linux amd64 机器上运行："
echo "  docker load -i $(basename "${OUT_FILE}")"
echo "  docker run -d --name geniview -p 8000:8000 ${IMAGE}"
