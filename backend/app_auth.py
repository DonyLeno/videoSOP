"""登录 Token 管理（阶段 4：内存缓存 + DB 持久化）。

- TOKENS 是进程内缓存；auth_tokens 表是权威数据源。
- 服务重启后缓存为空，首个携带旧 Token 的请求自动从 DB 回填 → 重启不掉线（TTL 内）。
- revoke_token / revoke_user_tokens 同步删除 DB 行与缓存项 → 登出/踢人即时生效。
- last_seen 写库限频（每 token 60s 一次），避免每请求一次 UPDATE。
- DB 异常时降级为纯内存行为，保证登录/鉴权不被数据库故障拖死。
"""

import hashlib
import secrets
import threading
import time
from typing import Dict, Optional

from backend.app_config import TOKEN_TTL_SECONDS
from backend.app_logging import get_logger

logger = get_logger("auth")

TOKENS: Dict[str, Dict[str, object]] = {}
_LOCK = threading.Lock()
_LAST_SEEN_WRITES: Dict[str, float] = {}
_SEEN_WRITE_INTERVAL = 60.0


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _cache_put(token: str, info: Dict[str, object]) -> None:
    with _LOCK:
        TOKENS[token] = info


def _cache_pop(token: str) -> None:
    with _LOCK:
        TOKENS.pop(token, None)


def create_token(username: str, role: str, ttl_seconds: Optional[float] = None) -> str:
    ttl = float(ttl_seconds) if ttl_seconds is not None else float(TOKEN_TTL_SECONDS)
    token = secrets.token_urlsafe(32)
    now = time.time()
    info = {"username": username, "role": role, "expires_at": now + ttl}
    _cache_put(token, info)
    try:
        from backend.app_db_auth import upsert_token

        upsert_token(_hash_token(token), username, role, now, now + ttl)
    except Exception:
        logger.warning("Token 持久化失败，降级为内存会话: username=%s", username, exc_info=True)
    return token


def _hydrate_from_db(token: str) -> Optional[Dict[str, object]]:
    """缓存未命中时从 DB 回填。"""
    try:
        from backend.app_db_auth import get_token

        row = get_token(_hash_token(token))
    except Exception:
        logger.warning("从 DB 读取会话失败", exc_info=True)
        return None
    if not row or int(row.get("revoked") or 0) != 0:
        return None
    expires_at = float(row.get("expires_at") or 0.0)
    if expires_at < time.time():
        return None
    return {"username": row.get("username"), "role": row.get("role"), "expires_at": expires_at}


def _maybe_touch(token: str, force: bool = False) -> None:
    """限频回写 last_seen_at。"""
    try:
        from backend.app_db_auth import touch_token

        h = _hash_token(token)
        now = time.time()
        last = _LAST_SEEN_WRITES.get(h, 0.0)
        if force or now - last >= _SEEN_WRITE_INTERVAL:
            touch_token(h, now)
            _LAST_SEEN_WRITES[h] = now
    except Exception:
        pass


def get_token_info(token: str) -> Optional[Dict[str, object]]:
    if not token:
        return None
    with _LOCK:
        info = TOKENS.get(token)
    if info is not None:
        expires_at = info.get("expires_at")
        if isinstance(expires_at, (int, float)) and expires_at < time.time():
            _cache_pop(token)
            return None
        _maybe_touch(token)
        return info

    # 缓存未命中：服务重启场景，从 DB 恢复会话
    info = _hydrate_from_db(token)
    if info is None:
        return None
    _cache_put(token, info)
    _maybe_touch(token, force=True)
    return info


def revoke_token(token: str) -> bool:
    """登出：吊销当前 Token。返回是否找到并吊销。"""
    if not token:
        return False
    _cache_pop(token)
    _LAST_SEEN_WRITES.pop(_hash_token(token), None)
    try:
        from backend.app_db_auth import delete_token

        delete_token(_hash_token(token))
        return True
    except Exception:
        logger.warning("吊销 Token 失败", exc_info=True)
        return False


def revoke_user_tokens(username: str) -> int:
    """强制下线某用户全部会话，返回吊销数量。"""
    if not username:
        return 0
    with _LOCK:
        victims = [t for t, info in TOKENS.items() if info.get("username") == username]
        for t in victims:
            TOKENS.pop(t, None)
    try:
        from backend.app_db_auth import delete_user_tokens

        return int(delete_user_tokens(username))
    except Exception:
        logger.warning("强制下线失败: username=%s", username, exc_info=True)
        return len(victims)


def reset_cache() -> None:
    """模拟服务重启：清空进程内缓存（测试用）。"""
    with _LOCK:
        TOKENS.clear()
        _LAST_SEEN_WRITES.clear()
