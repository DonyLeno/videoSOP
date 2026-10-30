#!/bin/bash
set -e

# 阶段 4.2 批次 G：离线部署脚本（镜像 tar + docker compose 双服务：app + mariadb）
# 数据库数据存放在 named volume db_data；/data /result 挂载宿主机目录。

# 检查是否安装了 docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# 检查镜像包是否存在（优先使用环境变量指定的 tar）
TAR_FILE="${TAR_FILE:-gemini-project.tar}"
if [ ! -f "$TAR_FILE" ]; then
    CANDIDATE_TAR="$(ls -t gemini-project-v*-*.tar 2>/dev/null | head -n 1 || true)"
    if [ -n "$CANDIDATE_TAR" ] && [ -f "$CANDIDATE_TAR" ]; then
        TAR_FILE="$CANDIDATE_TAR"
    else
        echo "Error: image tar not found. Tried: ${TAR_FILE}"
        exit 1
    fi
fi

APP_IMAGE_TAG="${APP_IMAGE_TAG:-}"
if [ -z "$APP_IMAGE_TAG" ]; then
    base="$(basename "$TAR_FILE")"
    if [[ "$base" == gemini-project-v*-*.tar ]]; then
        APP_IMAGE_TAG="${base#gemini-project-}"
        APP_IMAGE_TAG="${APP_IMAGE_TAG%-*.tar}"
    fi
fi
export APP_IMAGE_TAG

# 检查目录是否存在，不存在则创建
mkdir -p data
mkdir -p result

echo "Step 1: Loading Docker image from $TAR_FILE..."
docker load -i "$TAR_FILE"

echo "Step 2: Starting services with Docker Compose (app + db)..."
docker compose -f docker/docker-compose.yml up -d

echo "================================================="
echo "Deployment successfully completed!"
echo "Service is running at: http://localhost:8000"
echo "Data directory: $(pwd)/data"
echo "Result directory: $(pwd)/result"
echo "MySQL data: named volume 'docker_db_data' (docker volume inspect docker_db_data)"
echo "================================================="
