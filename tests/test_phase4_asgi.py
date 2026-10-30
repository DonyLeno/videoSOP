"""阶段 4 批次 I 测试：FastAPI(ASGI) 迁移冒烟。

覆盖：API 鉴权（401/200）、版本接口、SSE 响应头、静态资源 no-store、
媒体文件鉴权与 Range 206、CORS 预检、404。

运行：python3 -m unittest discover -s tests -v
（依赖 httpx 的 TestClient；tests/__init__.py 已锁定临时 SQLite）
"""

import datetime
import os
import unittest

from fastapi.testclient import TestClient

from backend import app_auth
from backend.app_db import create_user, ensure_database
from backend.app_db_auth import delete_user_tokens, ensure_auth_tables
from backend.app_asgi import ASGIHandlerAdapter, app
from backend.service_analyze import USER_TASKS


class Phase4ASGITestCase(unittest.TestCase):
    TEST_USER = "asgi_test_user"

    @classmethod
    def setUpClass(cls):
        ensure_database()
        ensure_auth_tables()
        # 幂等插入测试用户（/api/me 等接口需 users 表中存在该账号）
        create_user(cls.TEST_USER, "x" * 64, "user", None, "active", None, "gemini-2.5-flash")
        app_auth.reset_cache()
        cls.client = TestClient(app)

    def setUp(self):
        delete_user_tokens(self.TEST_USER)
        USER_TASKS.pop(self.TEST_USER, None)

    def tearDown(self):
        USER_TASKS.pop(self.TEST_USER, None)

    def _token(self):
        token = app_auth.create_token(self.TEST_USER, "user", ttl_seconds=3600)
        self.assertIsNotNone(token)
        return token

    # ------------------------------------------------------------------
    # API 鉴权与基础路由
    # ------------------------------------------------------------------

    def test_version_public(self):
        res = self.client.get("/api/version")
        self.assertEqual(res.status_code, 200)
        self.assertIn("version", res.json())

    def test_api_401_without_token(self):
        res = self.client.get("/api/me")
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json(), {"error": "unauthorized"})

    def test_me_with_token(self):
        res = self.client.get("/api/me", headers={"Authorization": f"Bearer {self._token()}"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["user"]["username"], self.TEST_USER)

    def test_api_404_unknown(self):
        res = self.client.get("/api/not_exists")
        self.assertEqual(res.status_code, 404)

    def test_api_post_404_unknown(self):
        # 未知 API 路径：无对应 POST 路由（FastAPI 对已有 GET 路由的路径返回 405，其余 404）
        res = self.client.post("/api/not_exists", json={})
        self.assertIn(res.status_code, (404, 405))

    def test_cors_preflight(self):
        res = self.client.options(
            "/api/login",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("access-control-allow-origin"), "*")

    # ------------------------------------------------------------------
    # SSE
    # ------------------------------------------------------------------

    def test_sse_401_without_token(self):
        res = self.client.get("/api/task_events")
        self.assertEqual(res.status_code, 401)

    def test_sse_content_type_and_none_event(self):
        token = self._token()
        res = self.client.get(f"/api/task_events?token={token}")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.headers.get("content-type", "").startswith("text/event-stream"))
        self.assertEqual(res.headers.get("cache-control"), "no-cache")
        body = res.text
        self.assertTrue(body.startswith("event: status\ndata: "))
        self.assertIn('"status": "none"', body)

    # ------------------------------------------------------------------
    # 媒体：鉴权、Range、穿越防护
    # ------------------------------------------------------------------

    def test_media_401_without_token(self):
        res = self.client.get("/data/somefile.mp4")
        self.assertEqual(res.status_code, 401)

    def test_media_range_206(self):
        target = os.path.join("data", "_asgi_range_test.bin")
        with open(target, "wb") as f:
            f.write(b"0123456789abcdef")
        try:
            token = self._token()
            res = self.client.get(
                "/data/_asgi_range_test.bin",
                headers={"Authorization": f"Bearer {token}", "Range": "bytes=2-5"},
            )
            self.assertEqual(res.status_code, 206)
            self.assertEqual(res.content, b"2345")
            self.assertEqual(res.headers.get("content-range"), "bytes 2-5/16")
        finally:
            if os.path.exists(target):
                os.remove(target)

    def test_media_query_token_200(self):
        target = os.path.join("data", "_asgi_query_token.bin")
        with open(target, "wb") as f:
            f.write(b"hello")
        try:
            token = self._token()
            res = self.client.get(f"/data/_asgi_query_token.bin?token={token}")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.content, b"hello")
        finally:
            if os.path.exists(target):
                os.remove(target)

    def test_media_path_traversal_forbidden(self):
        token = self._token()
        res = self.client.get(
            "/data/..%2f..%2fserver.py",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertIn(res.status_code, (403, 404))

    def test_media_404_missing(self):
        token = self._token()
        res = self.client.get(
            "/data/__not_exists__.mp4",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(res.status_code, 404)

    # ------------------------------------------------------------------
    # 静态资源
    # ------------------------------------------------------------------

    def test_index_served_with_no_store(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/html", res.headers.get("content-type", ""))
        self.assertEqual(res.headers.get("cache-control"), "no-store")

    def test_static_asset_mapped_to_web(self):
        res = self.client.get("/assets/app.js")
        self.assertEqual(res.status_code, 200)
        self.assertIn("javascript", res.headers.get("content-type", ""))

    def test_static_404(self):
        res = self.client.get("/__not_exists__.js")
        self.assertEqual(res.status_code, 404)

    def test_head_auto_supported(self):
        res = self.client.head("/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content, b"")

    # ------------------------------------------------------------------
    # 响应序列化：MySQL datetime 必须能正常序列化（原 http.server 用 default=str）
    # ------------------------------------------------------------------

    def test_adapter_serializes_datetime(self):
        adapters = ASGIHandlerAdapter.__new__(ASGIHandlerAdapter)
        adapters.json_response = (
            200,
            {"created_at": datetime.datetime(2026, 10, 25, 12, 0, 0), "name": "测试"},
        )
        adapters.raw_status = None
        adapters.raw_headers = []
        adapters.wfile = __import__("io").BytesIO()

        res = adapters.to_response()
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"2026-10-25 12:00:00", res.body)
        self.assertIn("测试".encode("utf-8"), res.body)


if __name__ == "__main__":
    unittest.main()
