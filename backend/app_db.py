import base64
import hashlib
import hmac
import os
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import mysql.connector  # type: ignore
except Exception:
    mysql = None  # type: ignore[assignment]

import sqlite3

from backend.app_config import (
    MYSQL_CONNECT_TIMEOUT,
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
)

_DB_MODE = (os.environ.get("DB_MODE", "auto") or "auto").strip().lower()
_SQLITE_PATH = os.environ.get("SQLITE_PATH") or os.path.join(os.getcwd(), "data", "geniview.sqlite3")


def _mysql_available() -> bool:
    return bool(globals().get("mysql")) and hasattr(mysql, "connector")  # type: ignore[name-defined]


def get_db_connection(use_database: bool = True):
    config = {
        "host": MYSQL_HOST,
        "port": MYSQL_PORT,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "autocommit": True,
        "connection_timeout": MYSQL_CONNECT_TIMEOUT,
    }
    if use_database:
        config["database"] = MYSQL_DATABASE
    if not _mysql_available():
        raise RuntimeError("mysql_connector_unavailable")
    return mysql.connector.connect(**config)  # type: ignore[name-defined]


def _get_sqlite_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(_SQLITE_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(_SQLITE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return f"{base64.b64encode(salt).decode('utf-8')}:{base64.b64encode(digest).decode('utf-8')}"


def verify_password(password: str, stored: Optional[str]) -> bool:
    if not stored or ":" not in stored:
        return False
    salt_b64, digest_b64 = stored.split(":", 1)
    try:
        salt = base64.b64decode(salt_b64.encode("utf-8"))
        expected = base64.b64decode(digest_b64.encode("utf-8"))
    except Exception:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return hmac.compare_digest(digest, expected)


def ensure_database() -> None:
    if _DB_MODE == "sqlite":
        _ensure_sqlite()
        return

    if _DB_MODE in ("mysql", "auto"):
        ok = False
        if _DB_MODE == "auto":
            try:
                conn = get_db_connection(use_database=False)
                conn.close()
                ok = True
            except Exception:
                ok = False
        else:
            ok = True

        if not ok:
            _ensure_sqlite()
            return

        _ensure_mysql()
        return

    raise RuntimeError("invalid_db_mode")


def _ensure_mysql() -> None:
    last_err: Optional[Exception] = None
    conn = None
    for _ in range(60):
        try:
            conn = get_db_connection(use_database=False)
            last_err = None
            break
        except Exception as e:
            last_err = e
            time.sleep(1)
    if conn is None:
        raise last_err or RuntimeError("db_connect_failed")
    cursor = conn.cursor()
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cursor.close()
    conn.close()

    last_err = None
    conn = None
    for _ in range(60):
        try:
            conn = get_db_connection(use_database=True)
            last_err = None
            break
        except Exception as e:
            last_err = e
            time.sleep(1)
    if conn is None:
        raise last_err or RuntimeError("db_connect_failed")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(64) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(32) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS detection_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(64) NOT NULL,
            video_name VARCHAR(255),
            video_path TEXT,
            result_path TEXT,
            model VARCHAR(64),
            video_seconds DOUBLE,
            token_input INT,
            token_output INT,
            token_thinking INT,
            token_total INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_detection_history_user_time (username, created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    cursor.execute(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='users'",
        (MYSQL_DATABASE,),
    )
    existing_cols = {row[0] for row in cursor.fetchall()}
    if "email" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN email VARCHAR(255) DEFAULT NULL")
    if "status" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT 'active'")
    if "data_usage" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN data_usage BIGINT NOT NULL DEFAULT 0")
    if "api_key" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN api_key VARCHAR(255) DEFAULT NULL")
    if "model" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN model VARCHAR(64) DEFAULT NULL")
    cursor.execute("SELECT username FROM users WHERE username IN (%s, %s)", ("admin", "user1"))
    existing = {row[0] for row in cursor.fetchall()}
    seeds = [
        ("admin", "geniviewa", "admin", "admin@example.com"),
        ("user1", "userpass1", "user", "user1@example.com"),
    ]
    for username, password, role, email in seeds:
        if username in existing:
            continue
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, email, status) VALUES (%s, %s, %s, %s, %s)",
            (username, hash_password(password), role, email, "active"),
        )
    cursor.close()
    conn.close()


def _ensure_sqlite() -> None:
    conn = _get_sqlite_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            email TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            data_usage INTEGER NOT NULL DEFAULT 0,
            api_key TEXT,
            model TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS detection_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            video_name TEXT,
            video_path TEXT,
            result_path TEXT,
            model TEXT,
            video_seconds REAL,
            token_input INTEGER,
            token_output INTEGER,
            token_thinking INTEGER,
            token_total INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    seeds = [
        ("admin", "geniviewa", "admin", "admin@example.com"),
        ("user1", "userpass1", "user", "user1@example.com"),
    ]
    for username, password, role, email in seeds:
        cur.execute("SELECT username FROM users WHERE username=?", (username,))
        if cur.fetchone():
            continue
        cur.execute(
            "INSERT INTO users (username, password_hash, role, email, status) VALUES (?, ?, ?, ?, ?)",
            (username, hash_password(password), role, email, "active"),
        )
    conn.commit()
    conn.close()


def _row_to_user_dict(row: Any) -> Dict[str, object]:
    created_at = row["created_at"] if isinstance(row, sqlite3.Row) else row[4]
    created_at_text = (
        created_at.isoformat() if hasattr(created_at, "isoformat") else (str(created_at) if created_at else "")
    )
    return {
        "username": row["username"] if isinstance(row, sqlite3.Row) else row[0],
        "role": row["role"] if isinstance(row, sqlite3.Row) else row[1],
        "email": row["email"] if isinstance(row, sqlite3.Row) else row[2],
        "status": row["status"] if isinstance(row, sqlite3.Row) else row[3],
        "created_at": created_at_text,
        "data_usage": int((row["data_usage"] if isinstance(row, sqlite3.Row) else row[5]) or 0),
        "api_key": row["api_key"] if isinstance(row, sqlite3.Row) else row[6],
        "model": row["model"] if isinstance(row, sqlite3.Row) else row[7],
    }


def get_user_login(username: str) -> Optional[Tuple[str, str]]:
    u = (username or "").strip()
    if not u:
        return None
    if _DB_MODE == "sqlite" or (_DB_MODE == "auto" and not _mysql_available()):
        conn = _get_sqlite_connection()
        cur = conn.cursor()
        cur.execute("SELECT password_hash, role FROM users WHERE username=?", (u,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        return (str(row["password_hash"]), str(row["role"]))
    try:
        conn = get_db_connection(use_database=True)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, role FROM users WHERE username = %s", (u,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception:
        if _DB_MODE == "auto":
            conn = _get_sqlite_connection()
            cur = conn.cursor()
            cur.execute("SELECT password_hash, role FROM users WHERE username=?", (u,))
            row = cur.fetchone()
            conn.close()
            if not row:
                return None
            return (str(row["password_hash"]), str(row["role"]))
        raise
    if not row:
        return None
    return (str(row[0]), str(row[1]))


def get_user_me(username: str) -> Optional[Dict[str, object]]:
    u = (username or "").strip()
    if not u:
        return None
    if _DB_MODE == "sqlite" or (_DB_MODE == "auto" and not _mysql_available()):
        conn = _get_sqlite_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT username, role, email, status, created_at, data_usage, api_key, model FROM users WHERE username=?",
            (u,),
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        return _row_to_user_dict(row)
    try:
        conn = get_db_connection(use_database=True)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username, role, email, status, created_at, data_usage, api_key, model FROM users WHERE username = %s",
            (u,),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception:
        if _DB_MODE == "auto":
            conn = _get_sqlite_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT username, role, email, status, created_at, data_usage, api_key, model FROM users WHERE username=?",
                (u,),
            )
            row = cur.fetchone()
            conn.close()
            if not row:
                return None
            return _row_to_user_dict(row)
        raise
    if not row:
        return None
    return _row_to_user_dict(row)


def _row_to_history_dict(row: Any) -> Dict[str, object]:
    created_at = row["created_at"] if isinstance(row, sqlite3.Row) else row[11]
    created_at_text = (
        created_at.isoformat() if hasattr(created_at, "isoformat") else (str(created_at) if created_at else "")
    )
    return {
        "id": row["id"] if isinstance(row, sqlite3.Row) else row[0],
        "username": row["username"] if isinstance(row, sqlite3.Row) else row[1],
        "video_name": row["video_name"] if isinstance(row, sqlite3.Row) else row[2],
        "video_path": row["video_path"] if isinstance(row, sqlite3.Row) else row[3],
        "result_path": row["result_path"] if isinstance(row, sqlite3.Row) else row[4],
        "model": row["model"] if isinstance(row, sqlite3.Row) else row[5],
        "video_seconds": row["video_seconds"] if isinstance(row, sqlite3.Row) else row[6],
        "token_input": row["token_input"] if isinstance(row, sqlite3.Row) else row[7],
        "token_output": row["token_output"] if isinstance(row, sqlite3.Row) else row[8],
        "token_thinking": row["token_thinking"] if isinstance(row, sqlite3.Row) else row[9],
        "token_total": row["token_total"] if isinstance(row, sqlite3.Row) else row[10],
        "created_at": created_at_text,
    }


def add_detection_history(
    username: str,
    video_name: Optional[str],
    video_path: Optional[str],
    result_path: Optional[str],
    model: Optional[str],
    created_at: Optional[str],
    video_seconds: Optional[float],
    token_input: Optional[int],
    token_output: Optional[int],
    token_thinking: Optional[int],
    token_total: Optional[int],
) -> bool:
    u = (username or "").strip()
    if not u:
        return False
    if _DB_MODE == "sqlite" or (_DB_MODE == "auto" and not _mysql_available()):
        conn = _get_sqlite_connection()
        cur = conn.cursor()
        if created_at:
            cur.execute(
                """
                INSERT INTO detection_history
                (username, video_name, video_path, result_path, model, video_seconds, token_input, token_output, token_thinking, token_total, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    u,
                    video_name,
                    video_path,
                    result_path,
                    model,
                    video_seconds,
                    token_input,
                    token_output,
                    token_thinking,
                    token_total,
                    created_at,
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO detection_history
                (username, video_name, video_path, result_path, model, video_seconds, token_input, token_output, token_thinking, token_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    u,
                    video_name,
                    video_path,
                    result_path,
                    model,
                    video_seconds,
                    token_input,
                    token_output,
                    token_thinking,
                    token_total,
                ),
            )
        conn.commit()
        conn.close()
        return True
    try:
        conn = get_db_connection(use_database=True)
        cursor = conn.cursor()
        if created_at:
            cursor.execute(
                """
                INSERT INTO detection_history
                (username, video_name, video_path, result_path, model, video_seconds, token_input, token_output, token_thinking, token_total, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    u,
                    video_name,
                    video_path,
                    result_path,
                    model,
                    video_seconds,
                    token_input,
                    token_output,
                    token_thinking,
                    token_total,
                    created_at,
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO detection_history
                (username, video_name, video_path, result_path, model, video_seconds, token_input, token_output, token_thinking, token_total)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    u,
                    video_name,
                    video_path,
                    result_path,
                    model,
                    video_seconds,
                    token_input,
                    token_output,
                    token_thinking,
                    token_total,
                ),
            )
        cursor.close()
        conn.close()
        return True
    except Exception:
        if _DB_MODE == "auto":
            return add_detection_history(
                u,
                video_name,
                video_path,
                result_path,
                model,
                created_at,
                video_seconds,
                token_input,
                token_output,
                token_thinking,
                token_total,
            )
        raise


def list_detection_history(username: str, limit: int = 200) -> List[Dict[str, object]]:
    u = (username or "").strip()
    if not u:
        return []
    lim = max(1, min(int(limit or 200), 500))
    if _DB_MODE == "sqlite" or (_DB_MODE == "auto" and not _mysql_available()):
        conn = _get_sqlite_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, username, video_name, video_path, result_path, model, video_seconds, token_input, token_output, token_thinking, token_total, created_at
            FROM detection_history
            WHERE username=?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (u, lim),
        )
        rows = cur.fetchall() or []
        conn.close()
        return [_row_to_history_dict(r) for r in rows]
    try:
        conn = get_db_connection(use_database=True)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, username, video_name, video_path, result_path, model, video_seconds, token_input, token_output, token_thinking, token_total, created_at
            FROM detection_history
            WHERE username=%s
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """,
            (u, lim),
        )
        rows = cursor.fetchall() or []
        cursor.close()
        conn.close()
        return [_row_to_history_dict(r) for r in rows]
    except Exception:
        if _DB_MODE == "auto":
            return list_detection_history(u, lim)
        raise


def list_users() -> List[Dict[str, object]]:
    if _DB_MODE == "sqlite" or (_DB_MODE == "auto" and not _mysql_available()):
        conn = _get_sqlite_connection()
        cur = conn.cursor()
        cur.execute("SELECT username, role, email, status, created_at, data_usage, api_key, model FROM users")
        rows = cur.fetchall() or []
        conn.close()
        return [_row_to_user_dict(r) for r in rows]
    try:
        conn = get_db_connection(use_database=True)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username, role, email, status, created_at, data_usage, api_key, model FROM users ORDER BY id ASC"
        )
        rows = cursor.fetchall() or []
        cursor.close()
        conn.close()
        return [_row_to_user_dict(r) for r in rows]
    except Exception:
        if _DB_MODE == "auto":
            conn = _get_sqlite_connection()
            cur = conn.cursor()
            cur.execute("SELECT username, role, email, status, created_at, data_usage, api_key, model FROM users")
            rows = cur.fetchall() or []
            conn.close()
            return [_row_to_user_dict(r) for r in rows]
        raise


def create_user(
    username: str,
    password_hash: str,
    role: str,
    email: Optional[str],
    status: str,
    api_key: Optional[str],
    model: str,
) -> bool:
    u = (username or "").strip()
    if not u:
        return False
    if _DB_MODE == "sqlite" or (_DB_MODE == "auto" and not _mysql_available()):
        conn = _get_sqlite_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE username=?", (u,))
        if cur.fetchone():
            conn.close()
            return False
        cur.execute(
            "INSERT INTO users (username, password_hash, role, email, status, api_key, model) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (u, password_hash, role, email, status, api_key, model),
        )
        conn.commit()
        conn.close()
        return True
    try:
        conn = get_db_connection(use_database=True)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username=%s", (u,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return False
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, email, status, api_key, model) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (u, password_hash, role, email, status, api_key, model),
        )
        cursor.close()
        conn.close()
        return True
    except Exception:
        if _DB_MODE == "auto":
            conn = _get_sqlite_connection()
            cur = conn.cursor()
            cur.execute("SELECT username FROM users WHERE username=?", (u,))
            if cur.fetchone():
                conn.close()
                return False
            cur.execute(
                "INSERT INTO users (username, password_hash, role, email, status, api_key, model) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (u, password_hash, role, email, status, api_key, model),
            )
            conn.commit()
            conn.close()
            return True
        raise


def update_user(username: str, fields: Dict[str, object]) -> bool:
    u = (username or "").strip()
    if not u:
        return False
    if _DB_MODE == "sqlite" or (_DB_MODE == "auto" and not _mysql_available()):
        allowed = {"email", "role", "status", "api_key", "model", "password_hash"}
        sets = []
        params: List[object] = []
        for k, v in (fields or {}).items():
            if k not in allowed:
                continue
            sets.append(f"{k}=?")
            params.append(v)
        if not sets:
            return True
        params.append(u)
        conn = _get_sqlite_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE username=?", (u,))
        if not cur.fetchone():
            conn.close()
            return False
        cur.execute(f"UPDATE users SET {', '.join(sets)} WHERE username=?", tuple(params))
        conn.commit()
        conn.close()
        return True
    try:
        conn = get_db_connection(use_database=True)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username=%s", (u,))
        row = cursor.fetchone()
        if not row:
            cursor.close()
            conn.close()
            return False
        sets = []
        params: List[object] = []
        mapping = {
            "email": "email",
            "role": "role",
            "status": "status",
            "api_key": "api_key",
            "model": "model",
            "password_hash": "password_hash",
        }
        for k, v in (fields or {}).items():
            col = mapping.get(k)
            if not col:
                continue
            sets.append(f"{col}=%s")
            params.append(v)
        if sets:
            params.append(u)
            cursor.execute(f"UPDATE users SET {', '.join(sets)} WHERE username=%s", tuple(params))
        cursor.close()
        conn.close()
        return True
    except Exception:
        if _DB_MODE == "auto":
            return update_user(u, fields)
        raise


def get_user_api_key_model(username: str) -> Tuple[Optional[str], Optional[str]]:
    u = (username or "").strip()
    if not u:
        return (None, None)
    if _DB_MODE == "sqlite" or (_DB_MODE == "auto" and not _mysql_available()):
        conn = _get_sqlite_connection()
        cur = conn.cursor()
        cur.execute("SELECT api_key, model FROM users WHERE username=?", (u,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return (None, None)
        api_key = str(row["api_key"]).strip() if row["api_key"] is not None else None
        model = str(row["model"]).strip() if row["model"] is not None else None
        return (api_key or None, model or None)
    try:
        conn = get_db_connection(use_database=True)
        cursor = conn.cursor()
        cursor.execute("SELECT api_key, model FROM users WHERE username=%s", (u,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception:
        if _DB_MODE == "auto":
            return get_user_api_key_model(u)
        raise
    if not row:
        return (None, None)
    api_key = str(row[0]).strip() if row[0] is not None else None
    model = str(row[1]).strip() if row[1] is not None else None
    return (api_key or None, model or None)
