#!/bin/bash
set -e

# Build the image for linux/amd64
echo "Building Docker image for linux/amd64..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION="v10.6.2"
MARIADB_BASE_IMAGE="${MARIADB_BASE_IMAGE:-docker.m.daocloud.io/library/mariadb:11}"
docker build --platform linux/amd64 --build-arg "MARIADB_BASE_IMAGE=${MARIADB_BASE_IMAGE}" -f "${ROOT_DIR}/docker/Dockerfile" -t "gemini-project:${VERSION}" "${ROOT_DIR}"

# Also tag as latest for docker-compose compatibility
docker tag "gemini-project:${VERSION}" gemini-project:latest

# Save the image to a tar file
OUT_TAR_VERSIONED="${SCRIPT_DIR}/gemini-project-${VERSION}-amd64.tar"
OUT_TAR_LATEST="${SCRIPT_DIR}/gemini-project.tar"
echo "Saving image to ${OUT_TAR_VERSIONED}..."
docker save -o "${OUT_TAR_VERSIONED}" "gemini-project:${VERSION}" gemini-project:latest
cp -f "${OUT_TAR_VERSIONED}" "${OUT_TAR_LATEST}"

echo "Done! Image saved to ${OUT_TAR_VERSIONED} and ${OUT_TAR_LATEST}"
