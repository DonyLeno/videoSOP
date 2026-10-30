"""阶段 3 测试：动作首帧缩略图、结果修订留痕与回滚。

运行：python3 -m unittest discover -s tests -v
（tests/__init__.py 已把 DB 锁定为临时 SQLite；本文件再 chdir 到临时目录，
确保 service_results / service_thumbs 的相对路径文件操作不触碰生产 result/）
"""

import io
import json
import os
import shutil
import tempfile
import unittest
import urllib.parse

from backend import app_db_org as org
from backend.app_db import ensure_database
from backend.app_results_md import update_md_content
from backend.service_results import (
    _read_current_actions,
    handle_list_revisions,
    handle_restore_revision,
    handle_update_result,
)
from backend.service_thumbs import _actions_signature, get_or_build_thumbs, handle_result_thumbs


class FakeRFile:
    def __init__(self, payload: bytes):
        self._buf = io.BytesIO(payload)

    def read(self, n=-1):
        return self._buf.read(n)


class FakeHandler:
    """同时覆盖 send_json 与手工三件套两种响应路径的假 handler。"""

    def __init__(self, body=None):
        payload = body if isinstance(body, bytes) else (json.dumps(body or {}).encode("utf-8") if body else b"")
        self.headers = {"Content-Length": str(len(payload))}
        self.rfile = FakeRFile(payload)
        self.status = None
        self.payload = None
        self._out = io.BytesIO()

    def send_json(self, status, payload):
        self.status = status
        self.payload = payload

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        pass

    def end_headers(self):
        pass

    @property
    def wfile(self):
        return self._out

    def json_out(self):
        return json.loads(self._out.getvalue().decode("utf-8"))


def parse(path: str):
    return urllib.parse.urlparse(path)


ACTIONS_V1 = [
    {"index": "1", "label": "拿取零件", "start_time": 0.0, "end_time": 2.0,
     "value_added": "增值", "duration": "2.0", "time_range": "0.00 - 2.00"},
    {"index": "2", "label": "装配", "start_time": 2.0, "end_time": 5.0,
     "value_added": "非增值", "duration": "3.0", "time_range": "2.00 - 5.00"},
    {"index": "3", "label": "检查外观", "start_time": 5.0, "end_time": 6.0,
     "value_added": "增值", "duration": "1.0", "time_range": "5.00 - 6.00"},
]

ACTIONS_V2 = [
    dict(ACTIONS_V1[0], label="拿取零件（修订）"),
    *ACTIONS_V1[1:],
]


class Phase3TestCase(unittest.TestCase):
    def setUp(self):
        ensure_database()
        org._exec("DELETE FROM result_revisions", (), commit=True)
        self._old_cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp(prefix="geniview_p3_")
        os.chdir(self.tmp)
        os.makedirs("result", exist_ok=True)
        self.user = {"username": "tester", "role": "admin"}

    def tearDown(self):
        os.chdir(self._old_cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_md(self, name, actions):
        content = update_md_content("", actions)
        path = os.path.join("result", name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"result/{name}"


class TestResultRevisions(Phase3TestCase):
    def test_update_creates_revision_snapshot(self):
        rel = self._write_md("a.md", ACTIONS_V1)
        h = FakeHandler({"json_path": rel, "actions": ACTIONS_V2})
        handle_update_result(h, self.user)
        self.assertEqual(h.status, 200, msg=str(h.json_out()))
        # 留痕应保存修改前的 v1
        rows = org.list_result_revisions(rel)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["action_count"], 3)
        self.assertEqual(rows[0]["revision_note"], "before_update")
        self.assertEqual(rows[0]["created_by"], "tester")

    def test_no_revision_when_nothing_changed(self):
        rel = self._write_md("a.md", ACTIONS_V1)
        h = FakeHandler({"json_path": rel, "actions": ACTIONS_V1})
        handle_update_result(h, self.user)
        self.assertEqual(h.status, 200)
        rows = org.list_result_revisions(rel)
        self.assertEqual(len(rows), 0)

    def test_list_revisions_api(self):
        rel = self._write_md("a.md", ACTIONS_V1)
        h = FakeHandler({"json_path": rel, "actions": ACTIONS_V2})
        handle_update_result(h, self.user)
        h2 = FakeHandler()
        handle_list_revisions(h2, self.user, parse(f"/api/result_revisions?path={urllib.parse.quote(rel)}"))
        self.assertEqual(h2.status, 200)
        self.assertEqual(len(h2.payload["revisions"]), 1)

    def test_list_revisions_rejects_bad_path(self):
        h = FakeHandler()
        handle_list_revisions(h, self.user, parse("/api/result_revisions?path=../etc/passwd"))
        self.assertEqual(h.status, 400)

    def test_restore_rollback_flow(self):
        rel = self._write_md("a.md", ACTIONS_V1)
        # 第一次修订：v1 -> v2（留痕 v1）
        handle_update_result(FakeHandler({"json_path": rel, "actions": ACTIONS_V2}), self.user)
        # 第二次修订：v2 -> v1（留痕 v2）
        handle_update_result(FakeHandler({"json_path": rel, "actions": ACTIONS_V1}), self.user)
        rows = org.list_result_revisions(rel)
        self.assertEqual(len(rows), 2)
        # 最新一条快照是 v2（label = 装配 前的「拿取零件（修订）」）
        newest = org.get_result_revision(rows[0]["id"])
        self.assertEqual(newest["actions"][0]["label"], "拿取零件（修订）")
        # 回滚到该快照
        h = FakeHandler({"revision_id": rows[0]["id"]})
        handle_restore_revision(h, self.user)
        self.assertEqual(h.status, 200, msg=str(h.payload))
        # 文件内容应恢复为 v2
        current = _read_current_actions(os.path.join("result", "a.md"))
        self.assertEqual(current[0]["label"], "拿取零件（修订）")
        # 回滚本身也留痕（before_restore）
        rows_after = org.list_result_revisions(rel)
        self.assertEqual(len(rows_after), 3)
        self.assertTrue(rows_after[0]["revision_note"].startswith("before_restore#"))

    def test_restore_json_result(self):
        json_path = os.path.join("result", "j.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({"actions": ACTIONS_V1, "stats": {}}, f, ensure_ascii=False)
        handle_update_result(
            FakeHandler({"json_path": "result/j.json", "actions": ACTIONS_V2}), self.user
        )
        rows = org.list_result_revisions("result/j.json")
        self.assertEqual(len(rows), 1)
        h = FakeHandler({"revision_id": rows[0]["id"]})
        handle_restore_revision(h, self.user)
        self.assertEqual(h.status, 200)
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["actions"][0]["label"], "拿取零件")


class TestResultThumbs(Phase3TestCase):
    def test_invalid_path_returns_empty(self):
        data = get_or_build_thumbs("../etc/passwd")
        self.assertEqual(data["thumbs"], [])
        h = FakeHandler()
        handle_result_thumbs(h, self.user, parse("/api/result_thumbs?path=result/missing.md"))
        self.assertEqual(h.status, 200)
        self.assertEqual(h.payload["thumbs"], [])

    def test_no_video_returns_empty(self):
        self._write_md("a.md", ACTIONS_V1)
        data = get_or_build_thumbs("result/a.md")
        self.assertEqual(data["thumbs"], [])
        self.assertEqual(data["count"], 3)

    def test_cache_hit_from_meta(self):
        rel = self._write_md("a.md", ACTIONS_V1)
        base = "a"
        thumb_dir = os.path.join("result", "thumbs", base)
        os.makedirs(thumb_dir, exist_ok=True)
        thumb_files = [f"result/thumbs/{base}/a{i:03d}.jpg" for i in range(1, len(ACTIONS_V1) + 1)]
        for tf in thumb_files:
            with open(tf, "wb") as f:
                f.write(b"\xff\xd8fake")
        with open(os.path.join(thumb_dir, "meta.json"), "w", encoding="utf-8") as f:
            json.dump({"signature": _actions_signature(ACTIONS_V1), "thumbs": thumb_files}, f)
        data = get_or_build_thumbs(rel)
        self.assertEqual(data["thumbs"], thumb_files)
        self.assertEqual(data["count"], 3)

    def test_extract_from_real_video(self):
        try:
            import cv2
            import numpy
        except Exception:
            self.skipTest("cv2/numpy 不可用")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter("result/v.mp4", fourcc, 25, (64, 64))
        if not writer.isOpened():
            self.skipTest("环境不支持 mp4 编码")
        for i in range(150):
            frame = (i * 5) % 255
            writer.write(numpy.full((64, 64, 3), frame, dtype=numpy.uint8))
        writer.release()
        rel = self._write_md("v.md", ACTIONS_V1[:2])
        data = get_or_build_thumbs(rel)
        self.assertEqual(data["count"], 2)
        self.assertTrue(all(data["thumbs"]), msg=str(data))
        for tf in data["thumbs"]:
            self.assertTrue(os.path.isfile(tf))
        # 第二次调用应命中缓存且结果一致
        data2 = get_or_build_thumbs(rel)
        self.assertEqual(data2["thumbs"], data["thumbs"])

    def test_en_prefix_shares_thumbs(self):
        rel = self._write_md("en_a.md", ACTIONS_V1)
        base = "a"
        thumb_dir = os.path.join("result", "thumbs", base)
        os.makedirs(thumb_dir, exist_ok=True)
        thumb_files = [f"result/thumbs/{base}/a{i:03d}.jpg" for i in range(1, len(ACTIONS_V1) + 1)]
        for tf in thumb_files:
            with open(tf, "wb") as f:
                f.write(b"\xff\xd8fake")
        with open(os.path.join(thumb_dir, "meta.json"), "w", encoding="utf-8") as f:
            json.dump({"signature": _actions_signature(ACTIONS_V1), "thumbs": thumb_files}, f)
        data = get_or_build_thumbs(rel)
        self.assertEqual(data["thumbs"], thumb_files)


if __name__ == "__main__":
    unittest.main()
