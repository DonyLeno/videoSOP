"""阶段 4 批次 F 测试：SSE 任务事件流。

覆盖：
- _task_status_payload：内存优先 + DB 兜底 + none 语义
- iter_task_events：无任务单次 none、变化检测、终态结束、恒定 payload 不重复 yield
- handle_task_status 改造后仍与事件流共用同一 payload 构造
- SSE 路由响应头与事件格式（FakeHandler + BytesIO）

运行：python3 -m unittest discover -s tests -v
（tests/__init__.py 已锁定临时 SQLite）
"""

import io
import json
import threading
import time
import unittest

from backend.app_db import ensure_database
from backend.service_analyze import USER_TASKS, handle_task_status
from backend.service_events import _task_status_payload, iter_task_events


class FakeRFile:
    def read(self, n=-1):
        return b""


class FakeHandler:
    """最小 handler：send_json / SSE 头写入均可捕获。"""

    def __init__(self, auth_user=None):
        self.headers = {"Content-Length": "0"}
        self.rfile = FakeRFile()
        self.status = None
        self.payload = None
        self.response_headers = {}
        self.wfile = io.BytesIO()
        self._auth_user = auth_user

    def send_json(self, status, payload):
        self.status = status
        self.payload = payload

    def send_response(self, code):
        self.status = code

    def send_header(self, key, value):
        self.response_headers[key] = value

    def end_headers(self):
        pass

    def get_media_auth_user(self):
        return self._auth_user


class Phase4EventsTestCase(unittest.TestCase):
    TEST_USER = "sse_test_user"

    def setUp(self):
        ensure_database()
        USER_TASKS.pop(self.TEST_USER, None)

    def tearDown(self):
        USER_TASKS.pop(self.TEST_USER, None)

    def _inject_task(self, **overrides):
        task = {
            "status": "running",
            "logs": ["line1"],
            "result": None,
            "error_msg": None,
            "phase": "analyzing",
            "progress": {"current": 1, "total": 10},
            "kind": "analyze",
            "model": "test-model",
            "progress_unit": "request",
            "task_id": 123,
        }
        task.update(overrides)
        USER_TASKS[self.TEST_USER] = task
        return task

    # ------------------------------------------------------------------
    # _task_status_payload
    # ------------------------------------------------------------------

    def test_payload_none_when_no_task(self):
        payload = _task_status_payload(self.TEST_USER)
        self.assertEqual(payload, {"status": "none"})

    def test_payload_memory_first(self):
        self._inject_task()
        payload = _task_status_payload(self.TEST_USER)
        self.assertEqual(payload["status"], "running")
        self.assertEqual(payload["logs"], ["line1"])
        self.assertEqual(payload["progress"], {"current": 1, "total": 10})
        self.assertEqual(payload["task_id"], 123)

    def test_payload_bytes_log_decoded(self):
        self._inject_task(logs=[b"raw bytes log"])
        payload = _task_status_payload(self.TEST_USER)
        self.assertEqual(payload["logs"], ["raw bytes log"])

    def test_handle_task_status_uses_shared_payload(self):
        """handle_task_status 应返回与 _task_status_payload 完全一致的响应。"""
        self._inject_task()
        handler = FakeHandler()
        ok = handle_task_status(handler, {"username": self.TEST_USER})
        self.assertTrue(ok)
        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.payload, _task_status_payload(self.TEST_USER))

    # ------------------------------------------------------------------
    # iter_task_events
    # ------------------------------------------------------------------

    def test_events_single_none_when_no_task(self):
        events = list(iter_task_events(self.TEST_USER, poll_interval=0.01))
        self.assertEqual(events, [{"status": "none"}])

    def test_events_detect_change_and_terminate(self):
        task = self._inject_task()
        gen = iter_task_events(self.TEST_USER, poll_interval=0.01)

        first = next(gen)
        self.assertEqual(first["status"], "running")

        # 变更任务：追加日志 + 完成
        task["logs"].append("line2")
        task["status"] = "completed"
        task["result"] = {"status": "success", "json_path": "a.md", "video_path": "v.mp4"}

        second = next(gen)
        self.assertEqual(second["status"], "completed")
        self.assertEqual(second["logs"], ["line1", "line2"])

        # 终态后流结束
        with self.assertRaises(StopIteration):
            next(gen)
        gen.close()

    def test_events_constant_payload_not_repeated(self):
        """payload 无变化时不重复推送；变为终态后立即推送并结束。"""
        task = self._inject_task()
        events = []
        done = threading.Event()

        def run():
            for payload in iter_task_events(self.TEST_USER, poll_interval=0.02):
                events.append(payload)
            done.set()

        worker = threading.Thread(target=run, daemon=True)
        worker.start()

        # 0.3s 内任务恒定 running：仅首个事件
        time.sleep(0.3)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["status"], "running")

        # 变更为终态：推送 failed 并结束
        task["status"] = "failed"
        task["error_msg"] = "boom"
        self.assertTrue(done.wait(2))
        self.assertEqual(events[-1]["status"], "failed")

    def test_events_failed_terminal(self):
        self._inject_task(status="failed", error_msg="boom")
        events = list(iter_task_events(self.TEST_USER, poll_interval=0.01))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["status"], "failed")
        self.assertEqual(events[0]["error_msg"], "boom")


class Phase4SSERouteTestCase(unittest.TestCase):
    """SSE 事件格式冒烟（ASGI 版路由测试见 tests/test_phase4_asgi.py）。"""

    TEST_USER = "sse_route_user"

    def setUp(self):
        ensure_database()
        USER_TASKS.pop(self.TEST_USER, None)

    def tearDown(self):
        USER_TASKS.pop(self.TEST_USER, None)

    def test_sse_event_format_for_none(self):
        """无任务时事件流应产出单个 none 事件后结束（格式与 ASGI 端点一致）。"""
        events = list(iter_task_events(self.TEST_USER, poll_interval=0.01))
        self.assertEqual(events, [{"status": "none"}])

    def test_sse_event_format_terminal(self):
        USER_TASKS[self.TEST_USER] = {
            "status": "completed",
            "logs": [],
            "result": None,
            "error_msg": None,
            "phase": "completed",
            "progress": None,
            "kind": "analyze",
            "model": "m",
            "progress_unit": None,
            "task_id": 7,
        }
        events = list(iter_task_events(self.TEST_USER, poll_interval=0.01))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
