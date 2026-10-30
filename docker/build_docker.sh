#!/bin/bash
set -e

# Build the application image (database runs as a separate mariadb service, see docker-compose.yml)
echo "Building Docker application image..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION="${APP_VERSION:-}"
if [ -z "${VERSION}" ]; then
  if [ -f "${ROOT_DIR}/docs/version.md" ]; then
    VERSION="$(grep -m1 '^## ' "${ROOT_DIR}/docs/version.md" | sed 's/^## //')"
  fi
fi
VERSION="${VERSION:-v2.0}"
PYTHON_BASE_IMAGE="${PYTHON_BASE_IMAGE:-docker.m.daocloud.io/library/python:3.12-slim}"
PLATFORM="${PLATFORM:-linux/amd64}"

docker build --platform "${PLATFORM}" \
  --build-arg "PYTHON_BASE_IMAGE=${PYTHON_BASE_IMAGE}" \
  --build-arg "APP_VERSION=${VERSION}" \
  -f "${ROOT_DIR}/docker/Dockerfile" -t "gemini-project:${VERSION}" "${ROOT_DIR}"

# Also tag as latest for docker-compose compatibility
docker tag "gemini-project:${VERSION}" gemini-project:latest

# Save the image to a tar file (offline deployment use)
ARCH="${PLATFORM#linux/}"
OUT_TAR_VERSIONED="${SCRIPT_DIR}/gemini-project-${VERSION}-${ARCH}.tar"
echo "Saving image to ${OUT_TAR_VERSIONED}..."
rm -f "${SCRIPT_DIR}/gemini-project.tar"
docker save -o "${OUT_TAR_VERSIONED}" "gemini-project:${VERSION}"

echo "Done! Image saved to ${OUT_TAR_VERSIONED}"
