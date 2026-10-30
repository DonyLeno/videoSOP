"""阶段 1 数据底座测试：组织层级、任务持久化、结果入库、权限过滤、迁移幂等。

运行：python3 -m unittest discover -s tests -v
（tests/__init__.py 已把 DB 环境锁定为临时 SQLite，不触碰 MySQL 与生产数据）
"""

import os
import unittest

from backend import app_db_org as org
from backend.app_db import ensure_database


class Phase1TestCase(unittest.TestCase):
    """公共基类：每个测试前重建干净数据库。"""

    def setUp(self):
        ensure_database()
        for table in (
            "project_members",
            "analysis_results",
            "tasks",
            "videos",
            "production_lines",
            "projects",
        ):
            org._exec(f"DELETE FROM {table}", (), commit=True)


class TestOrgTables(Phase1TestCase):
    def test_default_scope(self):
        scope = org.ensure_default_scope()
        self.assertGreater(scope["project_id"], 0)
        self.assertGreater(scope["line_id"], 0)
        # 幂等：再取一次结果一致
        scope2 = org.ensure_default_scope()
        self.assertEqual(scope, scope2)

    def test_project_create_idempotent(self):
        pid1 = org.create_project("T1", "测试项目1")
        pid2 = org.create_project("T1", "同名重复创建")
        self.assertIsNotNone(pid1)
        self.assertEqual(pid1, pid2)

    def test_line_unique_per_project(self):
        pid = org.create_project("T2", "测试项目2")
        lid1 = org.create_production_line(pid, "L1", "一线")
        lid2 = org.create_production_line(pid, "L1", "一线重复")
        self.assertEqual(lid1, lid2)
        # 同 code 不同项目不冲突
        pid_other = org.create_project("T2B", "另一个项目")
        lid3 = org.create_production_line(pid_other, "L1", "一线")
        self.assertNotEqual(lid1, lid3)

    def test_member_role_and_visibility(self):
        pid = org.create_project("T3", "成员项目")
        org.add_project_member(pid, "user1", "editor")
        members = org.list_project_members(pid)
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0]["username"], "user1")
        # 重复添加幂等
        org.add_project_member(pid, "user1", "editor")
        self.assertEqual(len(org.list_project_members(pid)), 1)

        self.assertIn(pid, org.user_visible_project_ids("user1"))
        # admin 全部可见
        self.assertIn(pid, org.user_visible_project_ids("admin", role="admin"))

    def test_visibility_fallback_to_default(self):
        # 无成员关系的普通用户回退默认项目（兼容存量行为）
        org.ensure_default_scope()
        rows = org.list_projects("user1")
        self.assertTrue(all(str(r["code"]) != "T9" for r in rows))

    def test_video_register_idempotent(self):
        scope = org.ensure_default_scope()
        vid1 = org.register_video(scope["project_id"], "a.mp4", "data/a.mp4", uploaded_by="user1")
        vid2 = org.register_video(scope["project_id"], "a.mp4", "data/a.mp4", uploaded_by="user1")
        self.assertEqual(vid1, vid2)

    def test_list_videos_visibility(self):
        scope = org.ensure_default_scope()
        other = org.create_project("V2", "他人项目")
        org.register_video(scope["project_id"], "mine.mp4", "data/mine.mp4", uploaded_by="user1")
        org.register_video(other, "secret.mp4", "data/secret.mp4", uploaded_by="admin")
        # user1 非成员项目视频不可见
        names = [r["filename"] for r in org.list_videos_for_user("user1")]
        self.assertIn("mine.mp4", names)
        self.assertNotIn("secret.mp4", names)
        # admin 全可见
        names_admin = [r["filename"] for r in org.list_videos_for_user("admin", role="admin")]
        self.assertIn("secret.mp4", names_admin)


class TestTaskPersistence(Phase1TestCase):
    def test_task_lifecycle(self):
        tid = org.create_task("user1", "kimi-2.5", progress_total=10, progress_unit="frame")
        self.assertIsNotNone(tid)
        row = org.get_task(tid)
        self.assertEqual(row["status"], org.TASK_STATUS_RUNNING)
        self.assertEqual(row["progress_total"], 10)

        org.update_task_progress(tid, "analyze", 5, 10)
        row = org.get_task(tid)
        self.assertEqual(row["progress_current"], 5)

        org.finish_task(
            tid,
            org.TASK_STATUS_SUCCEEDED,
            md_path="result/a.md",
            json_path="result/a.json",
            video_path="result/a.mp4",
            token_input=100,
            token_output=50,
        )
        row = org.get_task(tid)
        self.assertEqual(row["status"], org.TASK_STATUS_SUCCEEDED)
        self.assertEqual(row["result_md_path"], "result/a.md")
        self.assertEqual(row["token_input"], 100)
        self.assertIsNotNone(row["finished_at"])

        latest = org.get_latest_task_for_user("user1")
        self.assertEqual(int(latest["id"]), tid)

    def test_fail_stale_tasks(self):
        t1 = org.create_task("user1", "kimi-2.5")
        t2 = org.create_task("user2", "qwen3.5-plus")
        # t1 已终态：不应被 fail_stale 影响
        org.finish_task(t1, org.TASK_STATUS_FAILED, error="boom")

        stale = org.fail_stale_tasks()
        stale_ids = [int(r["id"]) for r in stale]
        self.assertIn(t2, stale_ids)
        self.assertNotIn(t1, stale_ids)

        row2 = org.get_task(t2)
        self.assertEqual(row2["status"], org.TASK_STATUS_FAILED)
        self.assertEqual(row2["error"], "interrupted_by_restart")
        row1 = org.get_task(t1)
        self.assertEqual(row1["error"], "boom")

    def test_task_row_to_response_mapping(self):
        from backend.service_analyze import _task_row_to_response

        resp = _task_row_to_response(
            {
                "status": "succeeded",
                "result_md_path": "result/x.md",
                "result_video_path": "result/x.mp4",
                "error": None,
                "phase": "completed",
                "progress_current": 10,
                "progress_total": 10,
                "model": "kimi-2.5",
                "progress_unit": "frame",
                "id": 7,
            }
        )
        self.assertEqual(resp["status"], "completed")
        self.assertEqual(resp["result"]["json_path"], "result/x.md")
        self.assertEqual(resp["task_id"], 7)

        resp_failed = _task_row_to_response({"status": "failed", "error": "interrupted_by_restart", "id": 8})
        self.assertEqual(resp_failed["status"], "failed")
        self.assertEqual(resp_failed["error_msg"], "interrupted_by_restart")
        self.assertIsNone(resp_failed["result"])


class TestAnalysisResults(Phase1TestCase):
    def test_register_idempotent(self):
        pid = org.create_project("R1", "结果项目")
        rid1 = org.register_analysis_result(pid, "result/x.md", created_by="user1")
        rid2 = org.register_analysis_result(pid, "result/x.md", created_by="user1")
        self.assertEqual(rid1, rid2)

    def test_list_visibility_filter(self):
        p1 = org.create_project("R2", "项目A")
        p2 = org.create_project("R3", "项目B")
        org.add_project_member(p1, "user1", "editor")
        org.register_analysis_result(p1, "result/a.md", created_by="user1")
        org.register_analysis_result(p2, "result/b.md", created_by="admin")

        rows_user = org.list_analysis_results_for_user("user1")
        self.assertEqual([r["md_path"] for r in rows_user], ["result/a.md"])

        rows_admin = org.list_analysis_results_for_user("admin", role="admin")
        self.assertEqual(len(rows_admin), 2)

    def test_project_filter_param(self):
        p1 = org.create_project("R4", "项目C")
        p2 = org.create_project("R5", "项目D")
        org.register_analysis_result(p1, "result/c.md")
        org.register_analysis_result(p2, "result/d.md")
        rows = org.list_analysis_results_for_user("admin", role="admin", project_id=p1)
        self.assertEqual([r["md_path"] for r in rows], ["result/c.md"])


class TestDetectionHistoryScope(Phase1TestCase):
    def test_add_history_with_scope(self):
        from backend.app_db import add_detection_history, list_detection_history

        ok = add_detection_history(
            "user1",
            "a.mp4",
            "result/a.mp4",
            "result/a.md",
            "kimi-2.5",
            None,
            12.5,
            10,
            20,
            None,
            30,
            project_id=3,
            line_id=4,
            task_id=5,
        )
        self.assertTrue(ok)
        # list_detection_history 返回旧字段结构，向后兼容
        items = list_detection_history("user1")
        self.assertEqual(len(items), 1)


class TestMigrationIdempotent(Phase1TestCase):
    def test_migrate_runs_twice_without_duplicates(self):
        import subprocess
        import sys

        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env = dict(os.environ)
        # 与 tests/__init__.py 相同的隔离 SQLite，保证不碰 MySQL/生产库
        env["DB_MODE"] = os.environ["DB_MODE"]
        env["SQLITE_PATH"] = os.environ["SQLITE_PATH"]
        # 迁移脚本按 cwd 下的 data/ result/ 扫描；测试 cwd 即项目根（真实存量文件，
        # 但写入的是隔离 SQLite，重跑两次验证幂等）
        for _ in range(2):
            proc = subprocess.run(
                [sys.executable, os.path.join(root, "scripts", "migrate_phase1.py")],
                capture_output=True,
                text=True,
                env=env,
                cwd=root,
                timeout=120,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr[-2000:])

        counts = {
            "projects": org._exec("SELECT COUNT(*) AS c FROM projects", fetch="one")["c"],
            "videos": org._exec("SELECT COUNT(*) AS c FROM videos", fetch="one")["c"],
            "results": org._exec("SELECT COUNT(*) AS c FROM analysis_results", fetch="one")["c"],
            "members": org._exec("SELECT COUNT(*) AS c FROM project_members", fetch="one")["c"],
        }
        # 第二遍跑完不产生重复：项目只有一个（默认），视频/结果数与文件数一致
        self.assertEqual(counts["projects"], 1)
        data_files = [
            f
            for f in os.listdir(os.path.join(root, "data"))
            if f.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm"))
        ]
        self.assertEqual(counts["videos"], len(data_files))
        md_files = [
            f
            for f in os.listdir(os.path.join(root, "result"))
            if f.endswith(".md") and not f.startswith("en_")
        ]
        self.assertEqual(counts["results"], len(md_files))


if __name__ == "__main__":
    unittest.main()
