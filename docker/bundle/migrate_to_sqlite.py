"""把当前 MySQL 数据迁移到 SQLite，供自包含 Docker 镜像离线运行。

用法（在项目根目录执行）：
    DB_MODE=mysql python3 docker/bundle/migrate_to_sqlite.py <输出 sqlite 路径>

说明：
- 只迁移业务表；登录会话（auth_tokens）不迁移，容器内需重新登录。
- 按 MySQL 与 SQLite 的公共列写入，避免两边 schema 细微差异导致失败。
- 目标 SQLite 文件已存在时按主键覆盖（INSERT OR REPLACE）。
"""

import datetime
import decimal
import os
import sqlite3
import sys

import mysql.connector

TABLES = [
    "users",
    "detection_history",
    "projects",
    "production_lines",
    "line_stations",
    "project_members",
    "videos",
    "tasks",
    "analysis_results",
    "result_revisions",
]


def _normalize(value):
    if isinstance(value, datetime.datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, datetime.date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, decimal.Decimal):
        return float(value)
    return value


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: migrate_to_sqlite.py <sqlite_path>", file=sys.stderr)
        return 2
    target = os.path.abspath(sys.argv[1])
    os.makedirs(os.path.dirname(target), exist_ok=True)

    # 让应用按 SQLite 模式建好全部表（users / detection_history / 项目产线工位等）
    os.environ["DB_MODE"] = "sqlite"
    os.environ["SQLITE_PATH"] = target
    from backend.app_db import ensure_database

    ensure_database()

    source = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", "123456"),
        database=os.getenv("MYSQL_DATABASE", "geniview"),
    )

    sq = sqlite3.connect(target)
    for table in TABLES:
        my_cur = source.cursor(dictionary=True)
        try:
            my_cur.execute(f"SELECT * FROM `{table}`")
        except mysql.connector.Error as exc:
            print(f"skip {table}: {exc}")
            continue
        rows = my_cur.fetchall()
        my_cur.close()
        if not rows:
            print(f"{table}: 0")
            continue
        sq_cols = {row[1] for row in sq.execute(f"PRAGMA table_info({table})")}
        if not sq_cols:
            print(f"skip {table}: sqlite 无此表")
            continue
        cols = [c for c in rows[0].keys() if c in sq_cols]
        placeholders = ",".join(["?"] * len(cols))
        if table == "users":
            # 清掉 SQLite 初始化时写入的默认账号，保持与 MySQL 完全一致
            sq.execute("DELETE FROM users")
        sql = f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
        sq.executemany(sql, [[_normalize(row[c]) for c in cols] for row in rows])
        sq.commit()
        print(f"{table}: {len(rows)}")

    sq.close()
    source.close()
    print(f"done -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
