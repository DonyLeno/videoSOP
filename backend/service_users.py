import json
from typing import Dict, List

from backend.app_auth import create_token
from backend.app_db import (
    create_user,
    get_user_login,
    get_user_me,
    hash_password,
    list_users,
    update_user,
    verify_password,
)


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
        row = get_user_login(username)
    except Exception as e:
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    if not row:
        handler.send_json(401, {"error": "invalid_credentials"})
        return True
    stored_hash, role = row
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
        ok = create_user(
            username=username,
            password_hash=hash_password(password),
            role=role,
            email=email,
            status=status,
            api_key=api_key,
            model=model,
        )
        if not ok:
            handler.send_json(409, {"error": "username_exists"})
            return True
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
        fields: Dict[str, object] = {}
        if email is not None:
            fields["email"] = email
        if role is not None:
            if role not in ("admin", "user"):
                handler.send_json(400, {"error": "invalid_role"})
                return True
            fields["role"] = role
        if status is not None:
            if status not in ("active", "inactive"):
                handler.send_json(400, {"error": "invalid_status"})
                return True
            fields["status"] = status
        if api_key is not None:
            normalized_key = str(api_key).strip()
            fields["api_key"] = normalized_key or None
        if model is not None:
            fields["model"] = str(model).strip()
        if new_password:
            fields["password_hash"] = hash_password(new_password)
        ok = update_user(username, fields)
        if not ok:
            handler.send_json(404, {"error": "user_not_found"})
            return True
    except Exception as e:
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    handler.send_json(200, {"status": "success"})
    return True


def handle_me(handler, user: Dict[str, object]) -> bool:
    try:
        username = str(user.get("username") or "").strip()
        u = get_user_me(username)
    except Exception as e:
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True

    if not u:
        handler.send_json(404, {"error": "user_not_found"})
        return True

    handler.send_json(200, {"user": u})
    return True


def handle_list_users(handler, user: Dict[str, object]) -> bool:
    if user.get("role") != "admin":
        handler.send_json(403, {"error": "forbidden"})
        return True
    try:
        items = list_users()
    except Exception as e:
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    handler.send_json(200, {"users": items})
    return True
