"""阶段 4：登录 Token 持久化。

解决 P0-5「Token 纯内存，服务重启全员掉线、无法踢人」：
- auth_tokens 表保存全部有效会话；只存 token 的 SHA-256 摘要，不存明文（DB 泄露也无法冒用）。
- app_auth 在内存缓存之外以本表为权威数据源，服务重启后旧 Token 仍然有效（TTL 内）。
- 登出 / 强制下线 = 删除对应行，内存缓存同步失效。
"""

import time
from typing import Optional

from backend.app_db_org import _exec, _use_mysql

_AUTH_DDL_MYSQL = [
    """
    CREATE TABLE IF NOT EXISTS auth_tokens (
        token_hash VARCHAR(64) NOT NULL PRIMARY KEY,
        username VARCHAR(64) NOT NULL,
        role VARCHAR(16) NOT NULL,
        created_at DOUBLE NOT NULL,
        expires_at DOUBLE NOT NULL,
        last_seen_at DOUBLE NULL,
        revoked TINYINT NOT NULL DEFAULT 0,
        INDEX idx_auth_tokens_user (username)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]

_AUTH_DDL_SQLITE = [
    """
    CREATE TABLE IF NOT EXISTS auth_tokens (
        token_hash TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at REAL NOT NULL,
        expires_at REAL NOT NULL,
        last_seen_at REAL,
        revoked INTEGER NOT NULL DEFAULT 0
    )
    """,
]

_auth_tables_ready = False


def ensure_auth_tables() -> None:
    """幂等建表（进程内只执行一次 DDL）。"""
    global _auth_tables_ready
    if _auth_tables_ready:
        return
    stmts = _AUTH_DDL_SQLITE if not _use_mysql() else _AUTH_DDL_MYSQL
    for stmt in stmts:
        _exec(stmt, (), commit=True)
    _auth_tables_ready = True


def upsert_token(token_hash: str, username: str, role: str, created_at: float, expires_at: float) -> None:
    """写入/复活一条会话（跨 MySQL/SQLite）。"""
    ensure_auth_tables()
    if not _use_mysql():
        sql = (
            "INSERT INTO auth_tokens (token_hash, username, role, created_at, expires_at, last_seen_at, revoked) "
            "VALUES (?, ?, ?, ?, ?, ?, 0) "
            "ON CONFLICT(token_hash) DO UPDATE SET username=excluded.username, role=excluded.role, "
            "created_at=excluded.created_at, expires_at=excluded.expires_at, revoked=0"
        )
    else:
        sql = (
            "INSERT INTO auth_tokens (token_hash, username, role, created_at, expires_at, last_seen_at, revoked) "
            "VALUES (?, ?, ?, ?, ?, ?, 0) "
            "ON DUPLICATE KEY UPDATE username=VALUES(username), role=VALUES(role), "
            "created_at=VALUES(created_at), expires_at=VALUES(expires_at), revoked=0"
        )
    _exec(
        sql,
        (token_hash, username, role, float(created_at), float(expires_at), float(created_at)),
        commit=True,
    )


def get_token(token_hash: str) -> Optional[dict]:
    ensure_auth_tables()
    return _exec(
        "SELECT token_hash, username, role, created_at, expires_at, last_seen_at, revoked "
        "FROM auth_tokens WHERE token_hash=?",
        (token_hash,),
        fetch="one",
    )


def touch_token(token_hash: str, seen_at: float) -> None:
    ensure_auth_tables()
    _exec(
        "UPDATE auth_tokens SET last_seen_at=? WHERE token_hash=?",
        (float(seen_at), token_hash),
        commit=True,
    )


def delete_token(token_hash: str) -> None:
    ensure_auth_tables()
    _exec("DELETE FROM auth_tokens WHERE token_hash=?", (token_hash,), commit=True)


def delete_user_tokens(username: str) -> int:
    """删除某用户全部有效会话（强制下线），返回删除条数。"""
    ensure_auth_tables()
    rowcount = _exec(
        "DELETE FROM auth_tokens WHERE username=?",
        (username,),
        commit=True,
        want_rowcount=True,
    )
    return 0 if rowcount is None else int(rowcount)


def purge_expired_tokens(now: Optional[float] = None) -> int:
    """清理已过期会话行。"""
    ensure_auth_tables()
    ts = float(now) if now is not None else time.time()
    rowcount = _exec(
        "DELETE FROM auth_tokens WHERE expires_at < ?",
        (ts,),
        commit=True,
        want_rowcount=True,
    )
    return 0 if rowcount is None else int(rowcount)
