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

echo "[3/5] 预下载 amd64 依赖 wheel"
rm -rf "${CTX_DIR}/wheels"
mkdir -p "${CTX_DIR}/wheels"
python3 -m pip download \
  -r "${CTX_DIR}/requirements.txt" \
  -c "${CTX_DIR}/constraints.txt" \
  -d "${CTX_DIR}/wheels" \
  --only-binary=:all: \
  --platform manylinux_2_28_x86_64 \
  --platform manylinux2014_x86_64 \
  --platform manylinux1_x86_64 \
  --platform any \
  --python-version 3.12 \
  --implementation cp \
  --abi cp312 \
  -i https://mirrors.aliyun.com/pypi/simple

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
