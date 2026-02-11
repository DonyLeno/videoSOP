import json
from typing import Dict, List

from backend.app_auth import create_token
from backend.app_db import get_db_connection, hash_password, verify_password


def handle_login(handler) -> bool:
    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    post_data = handler.rfile.read(content_length)
    try:
        data = json.loads(post_data.decode("utf-8")) if post_data else {}
    except Exception:
        data = {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        handler.send_json(400, {"error": "missing_credentials"})
        return True
    try:
        conn = get_db_connection(use_database=True)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username, password_hash, role FROM users WHERE username = %s",
            (username,),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    if not row:
        handler.send_json(401, {"error": "invalid_credentials"})
        return True
    stored_hash = row[1]
    role = row[2]
    if not verify_password(password, stored_hash):
        handler.send_json(401, {"error": "invalid_credentials"})
        return True
    token = create_token(username, role)
    handler.send_json(200, {"token": token, "user": {"username": username, "role": role}})
    return True


def handle_create_user(handler, user: Dict[str, object]) -> bool:
    if user.get("role") != "admin":
        handler.send_json(403, {"error": "forbidden"})
        return True
    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    post_data = handler.rfile.read(content_length)
    try:
        data = json.loads(post_data.decode("utf-8")) if post_data else {}
    except Exception:
        data = {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    role = (data.get("role") or "user").strip() or "user"
    email = (data.get("email") or "").strip() or None
    status = (data.get("status") or "active").strip() or "active"
    api_key = (data.get("api_key") or "").strip() or None
    model = (data.get("model") or "kimi-2.5").strip()
    if not username or not password:
        handler.send_json(400, {"error": "missing_username_or_password"})
        return True
    if role not in ("admin", "user"):
        handler.send_json(400, {"error": "invalid_role"})
        return True
    if status not in ("active", "inactive"):
        handler.send_json(400, {"error": "invalid_status"})
        return True
    try:
        conn = get_db_connection(use_database=True)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            handler.send_json(409, {"error": "username_exists"})
            return True
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, email, status, api_key, model) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (username, hash_password(password), role, email, status, api_key, model),
        )
        cursor.close()
        conn.close()
    except Exception as e:
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    handler.send_json(200, {"status": "success"})
    return True


def handle_update_user(handler, user: Dict[str, object]) -> bool:
    if user.get("role") != "admin":
        handler.send_json(403, {"error": "forbidden"})
        return True
    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    post_data = handler.rfile.read(content_length)
    try:
        data = json.loads(post_data.decode("utf-8")) if post_data else {}
    except Exception:
        data = {}
    username = (data.get("username") or "").strip()
    if not username:
        handler.send_json(400, {"error": "missing_username"})
        return True
    role = data.get("role")
    email = data.get("email")
    status = data.get("status")
    new_password = data.get("new_password")
    api_key = data.get("api_key")
    model = data.get("model")
    try:
        conn = get_db_connection(use_database=True)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
        row = cursor.fetchone()
        if not row:
            cursor.close()
            conn.close()
            handler.send_json(404, {"error": "user_not_found"})
            return True
        sets = []
        params: List[object] = []
        if email is not None:
            sets.append("email=%s")
            params.append(email)
        if role is not None:
            if role not in ("admin", "user"):
                handler.send_json(400, {"error": "invalid_role"})
                cursor.close()
                conn.close()
                return True
            sets.append("role=%s")
            params.append(role)
        if status is not None:
            if status not in ("active", "inactive"):
                handler.send_json(400, {"error": "invalid_status"})
                cursor.close()
                conn.close()
                return True
            sets.append("status=%s")
            params.append(status)
        if api_key is not None:
            normalized_key = str(api_key).strip()
            sets.append("api_key=%s")
            params.append(normalized_key or None)
        if model is not None:
            sets.append("model=%s")
            params.append(str(model).strip())
        if new_password:
            sets.append("password_hash=%s")
            params.append(hash_password(new_password))
        if sets:
            params.append(username)
            cursor.execute(
                f"UPDATE users SET {', '.join(sets)} WHERE username=%s",
                tuple(params),
            )
        cursor.close()
        conn.close()
    except Exception as e:
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    handler.send_json(200, {"status": "success"})
    return True


def handle_me(handler, user: Dict[str, object]) -> bool:
    try:
        conn = get_db_connection(use_database=True)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username, role, email, status, created_at, data_usage, api_key, model FROM users WHERE username = %s",
            (user.get("username"),),
        )
        r = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True

    if not r:
        handler.send_json(404, {"error": "user_not_found"})
        return True

    user_data = {
        "username": r[0],
        "role": r[1],
        "email": r[2],
        "status": r[3],
        "created_at": r[4].isoformat() if hasattr(r[4], "isoformat") else str(r[4]),
        "data_usage": int(r[5] or 0),
        "api_key": r[6],
        "model": r[7],
    }
    handler.send_json(200, {"user": user_data})
    return True


def handle_list_users(handler, user: Dict[str, object]) -> bool:
    if user.get("role") != "admin":
        handler.send_json(403, {"error": "forbidden"})
        return True
    try:
        conn = get_db_connection(use_database=True)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username, role, email, status, created_at, data_usage, api_key, model FROM users ORDER BY id ASC"
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    items = []
    for r in rows:
        items.append(
            {
                "username": r[0],
                "role": r[1],
                "email": r[2],
                "status": r[3],
                "created_at": r[4].isoformat() if hasattr(r[4], "isoformat") else str(r[4]),
                "data_usage": int(r[5] or 0),
                "api_key": r[6],
                "model": r[7],
            }
        )
    handler.send_json(200, {"users": items})
    return True

