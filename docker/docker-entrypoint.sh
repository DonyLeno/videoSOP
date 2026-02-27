#!/bin/bash
set -euo pipefail

MYSQL_DATADIR="/var/lib/mysql"
MYSQL_SOCKET="/run/mysqld/mysqld.sock"
MYSQL_PID="/run/mysqld/mysqld.pid"
INIT_MARKER="${MYSQL_DATADIR}/.gemini_initialized"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-123456}"
MYSQL_CLI=""
if command -v mariadb >/dev/null 2>&1; then
  MYSQL_CLI="mariadb"
elif command -v mysql >/dev/null 2>&1; then
  MYSQL_CLI="mysql"
else
  echo "mysql client not found (expected mariadb or mysql)"
  exit 1
fi

if [ ! -d "${MYSQL_DATADIR}/mysql" ]; then
  mkdir -p "${MYSQL_DATADIR}"
  chown -R mysql:mysql "${MYSQL_DATADIR}"
  mariadb-install-db --user=mysql --datadir="${MYSQL_DATADIR}" >/dev/null
fi
mkdir -p /run/mysqld
chown -R mysql:mysql /run/mysqld

mariadbd --user=mysql --datadir="${MYSQL_DATADIR}" --socket="${MYSQL_SOCKET}" --pid-file="${MYSQL_PID}" --skip-grant-tables --skip-networking &
INIT_DB_PID=$!

for i in {1..60}; do
  if env -u MYSQL_HOST -u MYSQL_PORT -u MYSQL_TCP_PORT -u MYSQL_UNIX_PORT "${MYSQL_CLI}" --no-defaults --protocol=socket --socket="${MYSQL_SOCKET}" -uroot -p"${MYSQL_PASSWORD}" -e "SELECT 1" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

env -u MYSQL_HOST -u MYSQL_PORT -u MYSQL_TCP_PORT -u MYSQL_UNIX_PORT "${MYSQL_CLI}" --no-defaults --protocol=socket --socket="${MYSQL_SOCKET}" -uroot -p"${MYSQL_PASSWORD}" <<SQL
FLUSH PRIVILEGES;
CREATE USER IF NOT EXISTS 'root'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('${MYSQL_PASSWORD}');
ALTER USER 'root'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('${MYSQL_PASSWORD}');
CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED VIA mysql_native_password USING PASSWORD('${MYSQL_PASSWORD}');
ALTER USER 'root'@'%' IDENTIFIED VIA mysql_native_password USING PASSWORD('${MYSQL_PASSWORD}');
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;
GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' WITH GRANT OPTION;
FLUSH PRIVILEGES;
SQL

if [ ! -f "${INIT_MARKER}" ]; then
  env -u MYSQL_HOST -u MYSQL_PORT -u MYSQL_TCP_PORT -u MYSQL_UNIX_PORT "${MYSQL_CLI}" --no-defaults --protocol=socket --socket="${MYSQL_SOCKET}" -uroot -p"${MYSQL_PASSWORD}" <<'SQL'
CREATE DATABASE IF NOT EXISTS geniview DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE geniview;
SOURCE /app/docker/docker-init.sql;
SQL
  touch "${INIT_MARKER}"
  chown mysql:mysql "${INIT_MARKER}"
fi

kill "${INIT_DB_PID}" || true
for i in {1..60}; do
  if ! kill -0 "${INIT_DB_PID}" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

mariadbd --user=mysql --datadir="${MYSQL_DATADIR}" --socket="${MYSQL_SOCKET}" --pid-file="${MYSQL_PID}" --bind-address=0.0.0.0 --port=3306 &

for i in {1..60}; do
  if env -u MYSQL_HOST -u MYSQL_PORT -u MYSQL_TCP_PORT -u MYSQL_UNIX_PORT "${MYSQL_CLI}" --no-defaults --protocol=socket --socket="${MYSQL_SOCKET}" -uroot -p"${MYSQL_PASSWORD}" -e "SELECT 1" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! env -u MYSQL_HOST -u MYSQL_PORT -u MYSQL_TCP_PORT -u MYSQL_UNIX_PORT "${MYSQL_CLI}" --no-defaults --protocol=socket --socket="${MYSQL_SOCKET}" -uroot -p"${MYSQL_PASSWORD}" -e "SELECT 1" >/dev/null 2>&1; then
  echo "MySQL not ready"
  exit 1
fi

exec python server.py
