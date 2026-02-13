import base64
import hashlib
import hmac
import os
import time
from typing import Optional

import mysql.connector  # type: ignore

from backend.app_config import (
    MYSQL_CONNECT_TIMEOUT,
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
)


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
    return mysql.connector.connect(**config)


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
