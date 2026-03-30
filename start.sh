#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

PROXY_HOST="${PROXY_HOST:-127.0.0.1}"
PROXY_PORT="${PROXY_PORT:-7890}"
PROXY_URL="http://${PROXY_HOST}:${PROXY_PORT}"
APP_PORT="${PORT:-8000}"

if ! lsof -nP -iTCP:${PROXY_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
  if python3 -c "import proxy" >/dev/null 2>&1; then
    nohup env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY python3 -m proxy --hostname "${PROXY_HOST}" --port "${PROXY_PORT}" >/tmp/genieview-proxy.log 2>&1 &
    sleep 1
  elif [ -x "$HOME/Library/Python/3.9/bin/proxy" ]; then
    nohup env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY "$HOME/Library/Python/3.9/bin/proxy" --hostname "${PROXY_HOST}" --port "${PROXY_PORT}" >/tmp/genieview-proxy.log 2>&1 &
    sleep 1
  else
    echo "未找到本地代理程序，请先安装 proxy.py: env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY python3 -m pip install --user proxy.py"
    exit 1
  fi
fi

if ! lsof -nP -iTCP:${PROXY_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
  echo "代理启动失败：${PROXY_HOST}:${PROXY_PORT}"
  exit 1
fi

export http_proxy="${PROXY_URL}"
export https_proxy="${PROXY_URL}"
export HTTP_PROXY="${PROXY_URL}"
export HTTPS_PROXY="${PROXY_URL}"
unset ALL_PROXY || true

if [ -f ".env" ]; then
  set -a
  . ./.env
  set +a
fi

: "${MOONSHOT_MAX_FRAMES_PER_REQUEST:=80}"
: "${MOONSHOT_MIN_FRAMES_PER_REQUEST:=20}"
: "${MOONSHOT_JPEG_QUALITY:=68}"
: "${MOONSHOT_IMAGE_MAX_EDGE:=768}"
export MOONSHOT_MAX_FRAMES_PER_REQUEST
export MOONSHOT_MIN_FRAMES_PER_REQUEST
export MOONSHOT_JPEG_QUALITY
export MOONSHOT_IMAGE_MAX_EDGE

existing_pid="$(lsof -ti tcp:${APP_PORT} -sTCP:LISTEN | head -n 1 || true)"
if [ -n "${existing_pid}" ]; then
  cmdline="$(ps -p "${existing_pid}" -o command= || true)"
  if echo "${cmdline}" | grep -q "server.py"; then
    kill "${existing_pid}" || true
    sleep 1
  else
    echo "端口 ${APP_PORT} 已被占用（PID ${existing_pid}），请先释放端口后再启动。"
    exit 1
  fi
fi

echo "代理已就绪: ${PROXY_URL}"
echo "启动服务: http://127.0.0.1:${APP_PORT}"
exec python3 server.py
