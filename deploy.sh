#!/bin/bash
set -e

# 检查是否安装了 docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# 检查镜像包是否存在
TAR_FILE="gemini-project.tar"
if [ ! -f "$TAR_FILE" ]; then
    echo "Error: $TAR_FILE not found in current directory."
    exit 1
fi

# 检查目录是否存在，不存在则创建
mkdir -p data
mkdir -p result

echo "Step 1: Loading Docker image from $TAR_FILE..."
docker load -i "$TAR_FILE"

echo "Step 2: Starting services with Docker Compose..."
docker compose up -d

echo "================================================="
echo "Deployment successfully completed!"
echo "Service is running at: http://localhost:8000"
echo "Data directory: $(pwd)/data"
echo "Result directory: $(pwd)/result"
echo "================================================="
