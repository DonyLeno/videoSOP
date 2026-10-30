import json
import threading
import time
import urllib.parse
from typing import Dict, List

from backend.app_auth import create_token, revoke_token, revoke_user_tokens
from backend.app_config import LOGIN_LOCKOUT_SECONDS, LOGIN_MAX_FAILURES
from backend.app_crypto import is_masked_value, mask_api_key
from backend.app_db import (
    create_user,
    get_user_login,
    get_user_me,
    hash_password,
    list_detection_history,
    list_users,
    update_user,
    verify_password,
)
from backend.app_logging import get_logger

logger = get_logger("users")

_LOGIN_FAILURES: Dict[str, List[float]] = {}
_LOGIN_FAILURES_LOCK = threading.Lock()


def _login_allowed(username: str):
    """返回 (是否允许尝试, 需等待秒数)。超过窗口内最大失败次数则锁定。"""
    now = time.time()
    key = username.lower()
    with _LOGIN_FAILURES_LOCK:
        stamps = [ts for ts in _LOGIN_FAILURES.get(key, []) if now - ts < LOGIN_LOCKOUT_SECONDS]
        if stamps:
            _LOGIN_FAILURES[key] = stamps
        else:
            _LOGIN_FAILURES.pop(key, None)
        if len(stamps) >= LOGIN_MAX_FAILURES:
            return False, max(1, int(LOGIN_LOCKOUT_SECONDS - (now - stamps[0])) + 1)
    return True, 0


def _register_login_failure(username: str) -> None:
    key = username.lower()
    with _LOGIN_FAILURES_LOCK:
        _LOGIN_FAILURES.setdefault(key, []).append(time.time())


def _clear_login_failures(username: str) -> None:
    with _LOGIN_FAILURES_LOCK:
        _LOGIN_FAILURES.pop(username.lower(), None)


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
    allowed, retry_after = _login_allowed(username)
    if not allowed:
        logger.warning("登录尝试被限速: username=%s, retry_after=%ss", username, retry_after)
        handler.send_json(429, {"error": "too_many_attempts", "retry_after": retry_after})
        return True
    try:
        row = get_user_login(username)
    except Exception as e:
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    if not row:
        _register_login_failure(username)
        logger.warning("登录失败（用户不存在）: username=%s", username)
        handler.send_json(401, {"error": "invalid_credentials"})
        return True
    stored_hash, role = row
    if not verify_password(password, stored_hash):
        _register_login_failure(username)
        logger.warning("登录失败（密码错误）: username=%s", username)
        handler.send_json(401, {"error": "invalid_credentials"})
        return True
    _clear_login_failures(username)
    logger.info("登录成功: username=%s", username)
    token = create_token(username, role)
    handler.send_json(200, {"token": token, "user": {"username": username, "role": role}})
    return True


def handle_logout(handler, user: Dict[str, object]) -> bool:
    """POST /api/logout：吊销当前 Token（登出）。"""
    auth = handler.headers.get("Authorization", "")
    token = auth.split(" ", 1)[1].strip() if auth.startswith("Bearer ") else ""
    if token:
        revoke_token(token)
    logger.info("用户登出: username=%s", (user or {}).get("username"))
    handler.send_json(200, {"status": "logged_out"})
    return True


def handle_revoke_user_sessions(handler, user: Dict[str, object]) -> bool:
    """POST /api/users/revoke_sessions body={"username": "..."} —— admin 强制下线某用户。"""
    if user.get("role") != "admin":
        handler.send_json(403, {"error": "forbidden"})
        return True
    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    post_data = handler.rfile.read(content_length)
    try:
        data = json.loads(post_data.decode("utf-8")) if post_data else {}
    except Exception:
        data = {}
    target = (data.get("username") or "").strip()
    if not target:
        handler.send_json(400, {"error": "missing_username"})
        return True
    if target == user.get("username"):
        handler.send_json(400, {"error": "cannot_revoke_self"})
        return True
    count = revoke_user_tokens(target)
    logger.warning("管理员强制下线用户: admin=%s target=%s sessions=%d", user.get("username"), target, count)
    handler.send_json(200, {"status": "ok", "revoked": count})
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
            if is_masked_value(normalized_key):
                # 前端回传掩码值表示未修改，跳过更新
                pass
            else:
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

    u["api_key"] = mask_api_key(u.get("api_key"))
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
    for item in items:
        item["api_key"] = mask_api_key(item.get("api_key"))
    handler.send_json(200, {"users": items})
    return True


def handle_user_history(handler, user: Dict[str, object], parsed_path) -> bool:
    try:
        params = urllib.parse.parse_qs(parsed_path.query or "")
    except Exception:
        params = {}
    target = ""
    if params.get("username"):
        target = str(params.get("username")[0] or "").strip()
    if not target:
        target = str(user.get("username") or "").strip()
    if not target:
        handler.send_json(400, {"error": "missing_username"})
        return True
    if user.get("role") != "admin" and target != str(user.get("username") or "").strip():
        handler.send_json(403, {"error": "forbidden"})
        return True
    try:
        limit = params.get("limit")
        limit_val = int(limit[0]) if limit else 200
        items = list_detection_history(target, limit_val)
    except Exception as e:
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    handler.send_json(200, {"items": items})
    return True
