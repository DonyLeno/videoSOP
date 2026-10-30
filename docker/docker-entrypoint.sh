#!/bin/bash
set -euo pipefail

# 阶段 4.2 批次 G：应用容器入口。数据库已拆分为独立 mariadb 服务（compose 服务名 db），
# 此处仅等待数据库端口就绪（compose healthcheck 已保证，这里做兜底），然后启动应用。

MYSQL_HOST="${MYSQL_HOST:-db}"
MYSQL_PORT="${MYSQL_PORT:-3306}"

echo "Waiting for database at ${MYSQL_HOST}:${MYSQL_PORT} ..."
for i in $(seq 1 120); do
  if python -c "import os,socket; socket.create_connection((os.environ['MYSQL_HOST'], int(os.environ['MYSQL_PORT'])), timeout=2).close()" 2>/dev/null; then
    echo "Database is ready."
    break
  fi
  if [ "$i" -eq 120 ]; then
    echo "Database not ready after 120s, exiting."
    exit 1
  fi
  sleep 1
done

exec python server.py
