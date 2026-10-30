#!/bin/bash
# Geniview 备份脚本：数据库 dump + data/ 与 result/ 归档，滚动保留 N 份
# 用法：./scripts/backup.sh [保留份数，默认 7]
# 建议 cron（每日 02:30）：30 2 * * * cd /path/to/geniview && ./scripts/backup.sh >> logs/backup.log 2>&1

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

KEEP="${1:-7}"
BACKUP_DIR="${GENIVIEW_BACKUP_DIR:-$ROOT/backups}"
STAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "[$(date '+%F %T')] backup start (keep=$KEEP, dir=$BACKUP_DIR)"

# ---------------------------------------------------------------------------
# 1. 数据库备份（按 app_config 的 DB_MODE 自动选择）
# ---------------------------------------------------------------------------
DB_MODE="${DB_MODE:-auto}"
DB_NAME="${MYSQL_DATABASE:-geniview}"
DB_USER="${MYSQL_USER:-root}"
DB_PASS="${MYSQL_PASSWORD:-123456}"
DB_HOST="${MYSQL_HOST:-127.0.0.1}"
DB_PORT="${MYSQL_PORT:-3306}"

dump_file="$BACKUP_DIR/db_${STAMP}.sql"
if [ "$DB_MODE" = "sqlite" ]; then
    SQLITE_PATH="${SQLITE_PATH:-$ROOT/data/geniview.sqlite3}"
    if [ -f "$SQLITE_PATH" ]; then
        sqlite3 "$SQLITE_PATH" ".backup '$dump_file'"
        echo "  sqlite backup -> $dump_file"
    else
        echo "  sqlite db not found at $SQLITE_PATH, skip db backup"
    fi
else
    if command -v mysqldump >/dev/null 2>&1; then
        MYSQL_PWD="$DB_PASS" mysqldump \
            -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" \
            --single-transaction --routines --triggers "$DB_NAME" > "$dump_file"
        echo "  mysql backup -> $dump_file ($(du -h "$dump_file" | cut -f1))"
    else
        echo "  WARNING: mysqldump not found, skip db backup"
    fi
fi

# ---------------------------------------------------------------------------
# 2. data/ 与 result/ 归档（含缩略图与 SOP）
# ---------------------------------------------------------------------------
for dir in data result; do
    if [ -d "$dir" ]; then
        archive="$BACKUP_DIR/${dir}_${STAMP}.tar.gz"
        tar -czf "$archive" --exclude "$dir/thumbs/cache" "$dir" 2>/dev/null || tar -czf "$archive" "$dir"
        echo "  $dir/ -> $archive ($(du -h "$archive" | cut -f1))"
    fi
done

# ---------------------------------------------------------------------------
# 3. 滚动清理：每类仅保留最新 KEEP 份
# ---------------------------------------------------------------------------
for prefix in db_ data_ result_; do
    ls -1t "$BACKUP_DIR"/${prefix}* 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r f; do
        rm -f "$f"
        echo "  pruned old backup: $(basename "$f")"
    done
done

echo "[$(date '+%F %T')] backup done"
