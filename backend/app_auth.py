import secrets
import time
from typing import Dict, Optional

from backend.app_config import TOKEN_TTL_SECONDS


TOKENS: Dict[str, Dict[str, object]] = {}


def create_token(username: str, role: str) -> str:
    token = secrets.token_urlsafe(32)
    TOKENS[token] = {"username": username, "role": role, "expires_at": time.time() + TOKEN_TTL_SECONDS}
    return token


def get_token_info(token: str) -> Optional[Dict[str, object]]:
    if not token:
        return None
    info = TOKENS.get(token)
    if not info:
        return None
    expires_at = info.get("expires_at")
    if isinstance(expires_at, (int, float)) and expires_at < time.time():
        TOKENS.pop(token, None)
        return None
    return info

