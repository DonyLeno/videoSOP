import base64
import hashlib
import logging
import os
from typing import Optional

_ENCRYPT_PREFIX = "enc:v1:"
_SECRET_ENV = "GENIVIEW_SECRET_KEY"
_KEY_FILE = os.path.join(os.getcwd(), ".geniview_secret_key")

logger = logging.getLogger("geniview.crypto")

_FERNET = None


def _load_fernet():
    global _FERNET
    if _FERNET is not None:
        return _FERNET
    try:
        from cryptography.fernet import Fernet
    except Exception:
        logger.warning("cryptography 库不可用，API Key 将保持原样存储")
        _FERNET = False
        return False

    secret = os.environ.get(_SECRET_ENV, "").strip()
    if not secret and os.path.exists(_KEY_FILE):
        try:
            with open(_KEY_FILE, "r", encoding="utf-8") as f:
                secret = f.read().strip()
        except Exception:
            secret = ""
    if not secret:
        try:
            secret = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")
            with open(_KEY_FILE, "w", encoding="utf-8") as f:
                f.write(secret)
            try:
                os.chmod(_KEY_FILE, 0o600)
            except Exception:
                pass
            logger.warning(
                "未设置 %s，已自动生成密钥文件 %s；删除或重置该文件将导致已存 API Key 无法解密",
                _SECRET_ENV,
                _KEY_FILE,
            )
        except Exception:
            logger.warning("密钥文件生成失败，API Key 将保持原样存储")
            _FERNET = False
            return False

    derived = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), b"geniview-api-key-v1", 120000)
    key = base64.urlsafe_b64encode(derived)
    _FERNET = Fernet(key)
    return _FERNET


def encrypt_secret(plain: Optional[str]) -> Optional[str]:
    text = (plain or "").strip()
    if not text:
        return None
    if text.startswith(_ENCRYPT_PREFIX):
        return text  # 已加密，避免二次加密
    f = _load_fernet()
    if not f:
        return text  # 无加密条件时保持原样（兼容旧数据读取）
    try:
        return _ENCRYPT_PREFIX + f.encrypt(text.encode("utf-8")).decode("utf-8")
    except Exception:
        logger.warning("加密 API Key 失败，将保持原样存储")
        return text


def decrypt_secret(stored: Optional[str]) -> Optional[str]:
    text = (stored or "").strip()
    if not text:
        return None
    if not text.startswith(_ENCRYPT_PREFIX):
        return text  # 兼容历史明文数据
    f = _load_fernet()
    if not f:
        logger.warning("无法解密 API Key（缺少 cryptography 或密钥），返回原值")
        return text
    try:
        return f.decrypt(text[len(_ENCRYPT_PREFIX):].encode("utf-8")).decode("utf-8")
    except Exception:
        logger.warning("解密 API Key 失败（密钥可能已变更）")
        return None


def mask_api_key(value: Optional[str]) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if len(raw) <= 8:
        return "******"
    return raw[:8] + "******"


def is_masked_value(value) -> bool:
    return "*" in str(value or "")
