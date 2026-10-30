"""阶段 4 测试：Token 持久化、登出吊销、强制下线。

运行：python3 -m unittest discover -s tests -v
（tests/__init__.py 已锁定临时 SQLite；auth_tokens 表由 ensure_auth_tables 幂等创建）
"""

import io
import json
import time
import unittest

from backend import app_auth
from backend.app_db import ensure_database
from backend.app_db_auth import (
    delete_user_tokens,
    ensure_auth_tables,
    get_token,
    purge_expired_tokens,
    upsert_token,
)
from backend.service_users import handle_logout, handle_revoke_user_sessions


class FakeRFile:
    def __init__(self, payload: bytes):
        self._buf = io.BytesIO(payload)

    def read(self, n=-1):
        return self._buf.read(n)


class FakeHandler:
    def __init__(self, body=None, token=None):
        payload = b""
        if body is not None:
            payload = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        self.headers = {"Content-Length": str(len(payload))}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        self.rfile = FakeRFile(payload)
        self.status = None
        self.payload = None

    def send_json(self, status, payload):
        self.status = status
        self.payload = payload


class Phase4AuthTestCase(unittest.TestCase):
    def setUp(self):
        ensure_database()
        ensure_auth_tables()
        app_auth.reset_cache()
        delete_user_tokens("alice")
        delete_user_tokens("bob")
        self.admin = {"username": "root", "role": "admin"}

    def test_token_survives_cache_reset(self):
        """模拟服务重启：内存清空后旧 Token 仍在 TTL 内有效。"""
        token = app_auth.create_token("alice", "user", ttl_seconds=3600)
        self.assertIsNotNone(app_auth.get_token_info(token))
        # 重启
        app_auth.reset_cache()
        info = app_auth.get_token_info(token)
        self.assertIsNotNone(info)
        self.assertEqual(info["username"], "alice")
        self.assertEqual(info["role"], "user")

    def test_expired_token_rejected_after_restart(self):
        token = app_auth.create_token("alice", "user", ttl_seconds=3600)
        # 手动把 DB 行改为已过期，再清缓存
        import hashlib

        h = hashlib.sha256(token.encode()).hexdigest()
        from backend.app_db_org import _exec

        _exec(
            "UPDATE auth_tokens SET expires_at=? WHERE token_hash=?",
            (time.time() - 10, h),
            commit=True,
        )
        app_auth.reset_cache()
        self.assertIsNone(app_auth.get_token_info(token))

    def test_logout_revokes_token(self):
        token = app_auth.create_token("alice", "user", ttl_seconds=3600)
        h = FakeHandler(token=token)
        handle_logout(h, {"username": "alice", "role": "user"})
        self.assertEqual(h.status, 200)
        # 缓存与 DB 均失效（即使重启也不能用）
        self.assertIsNone(app_auth.get_token_info(token))
        app_auth.reset_cache()
        self.assertIsNone(app_auth.get_token_info(token))
        import hashlib

        self.assertIsNone(get_token(hashlib.sha256(token.encode()).hexdigest()))

    def test_revoke_user_sessions_admin_only(self):
        h = FakeHandler({"username": "bob"})
        handle_revoke_user_sessions(h, {"username": "alice", "role": "user"})
        self.assertEqual(h.status, 403)

    def test_revoke_user_sessions_kicks_all(self):
        t1 = app_auth.create_token("bob", "user", ttl_seconds=3600)
        t2 = app_auth.create_token("bob", "user", ttl_seconds=3600)
        self.assertIsNotNone(app_auth.get_token_info(t1))
        self.assertIsNotNone(app_auth.get_token_info(t2))
        h = FakeHandler({"username": "bob"})
        handle_revoke_user_sessions(h, self.admin)
        self.assertEqual(h.status, 200)
        self.assertEqual(h.payload["revoked"], 2)
        # 重启后依然失效
        app_auth.reset_cache()
        self.assertIsNone(app_auth.get_token_info(t1))
        self.assertIsNone(app_auth.get_token_info(t2))

    def test_admin_cannot_kick_self(self):
        h = FakeHandler({"username": "root"})
        handle_revoke_user_sessions(h, self.admin)
        self.assertEqual(h.status, 400)

    def test_missing_username_400(self):
        h = FakeHandler({})
        handle_revoke_user_sessions(h, self.admin)
        self.assertEqual(h.status, 400)

    def test_purge_expired(self):
        token = app_auth.create_token("alice", "user", ttl_seconds=1)
        time.sleep(1.1)
        removed = purge_expired_tokens()
        self.assertGreaterEqual(removed, 1)
        app_auth.reset_cache()
        self.assertIsNone(app_auth.get_token_info(token))

    def test_upsert_revives_row_and_duplicate_login_ok(self):
        """重复登录写同一 token 不会冲突（极端情况下 upsert 可用）。"""
        token = app_auth.create_token("alice", "user", ttl_seconds=3600)
        import hashlib

        h = hashlib.sha256(token.encode()).hexdigest()
        upsert_token(h, "alice", "user", time.time(), time.time() + 100)
        row = get_token(h)
        self.assertIsNotNone(row)
        self.assertEqual(int(row["revoked"]), 0)


if __name__ == "__main__":
    unittest.main()
