"""阶段 2 测试：组织层级 API（项目/产线/成员）、产线级 SOP、作用域过滤。

运行：python3 -m unittest discover -s tests -v
（tests/__init__.py 已把 DB 环境锁定为临时 SQLite，不触碰 MySQL 与生产数据）
"""

import io
import json
import unittest
import urllib.parse

from backend import app_db_org as org
from backend.app_db import create_user, ensure_database


class FakeRFile:
    def __init__(self, payload: bytes):
        self._buf = io.BytesIO(payload)

    def read(self, n=-1):
        return self._buf.read(n)


class FakeHandler:
    """模拟 http.server handler：只实现 service_org 用到的接口。"""

    def __init__(self, body=None):
        payload = body if isinstance(body, bytes) else (json.dumps(body or {}).encode("utf-8") if body else b"")
        self.headers = {"Content-Length": str(len(payload))}
        self.rfile = FakeRFile(payload)
        self.status = None
        self.payload = None

    def send_json(self, status, payload):
        self.status = status
        self.payload = payload


def parse(path: str):
    return urllib.parse.urlparse(path)


class Phase2TestCase(unittest.TestCase):
    def setUp(self):
        ensure_database()
        for table in (
            "project_members",
            "analysis_results",
            "tasks",
            "videos",
            "production_lines",
            "projects",
            "users",
        ):
            org._exec(f"DELETE FROM {table}", (), commit=True)
        create_user("admin", "x", "admin", None, "active", None, "kimi-2.5")
        create_user("alice", "x", "user", None, "active", None, "kimi-2.5")
        create_user("bob", "x", "user", None, "active", None, "kimi-2.5")
        self.admin = {"username": "admin", "role": "admin"}
        self.alice = {"username": "alice", "role": "user"}
        self.bob = {"username": "bob", "role": "user"}

    def _mk_project(self, code="P1", name="项目一", user=None):
        from backend.service_org import handle_create_project

        h = FakeHandler({"code": code, "name": name, "description": "d"})
        handle_create_project(h, user or self.admin)
        self.assertEqual(h.status, 200, msg=str(h.payload))
        return h.payload["project_id"]


class TestProjectApi(Phase2TestCase):
    def test_create_requires_admin(self):
        from backend.service_org import handle_create_project

        h = FakeHandler({"code": "P1", "name": "n"})
        handle_create_project(h, self.alice)
        self.assertEqual(h.status, 403)

    def test_create_and_creator_becomes_owner(self):
        from backend.service_org import handle_create_project, handle_list_projects

        pid = self._mk_project()
        roles = org.list_project_members(pid)
        self.assertEqual([(r["username"], r["role"]) for r in roles], [("admin", "owner")])

        h = FakeHandler()
        handle_list_projects(h, self.admin)
        self.assertEqual(h.status, 200)
        self.assertEqual(len(h.payload["projects"]), 1)
        self.assertEqual(h.payload["projects"][0]["my_role"], "owner")

    def test_create_duplicate_code_conflict(self):
        self._mk_project("DUP")
        from backend.service_org import handle_create_project

        h = FakeHandler({"code": "DUP", "name": "另一个"})
        handle_create_project(h, self.admin)
        self.assertEqual(h.status, 409)

    def test_create_missing_fields(self):
        from backend.service_org import handle_create_project

        h = FakeHandler({"code": "NO-NAME"})
        handle_create_project(h, self.admin)
        self.assertEqual(h.status, 400)

    def test_update_project(self):
        pid = self._mk_project("U1", "旧名")
        from backend.service_org import handle_update_project

        h = FakeHandler({"project_id": pid, "name": "新名", "status": "archived"})
        handle_update_project(h, self.admin)
        self.assertEqual(h.status, 200)
        row = org.get_project(pid)
        self.assertEqual(row["name"], "新名")
        self.assertEqual(row["status"], "archived")

        h404 = FakeHandler({"project_id": 99999, "name": "x"})
        handle_update_project(h404, self.admin)
        self.assertEqual(h404.status, 404)

    def test_list_projects_membership_filter(self):
        pid = self._mk_project("M1")
        org.add_project_member(pid, "alice", "viewer")
        # bob 无成员关系：回退默认项目，看不到 M1
        from backend.service_org import handle_list_projects

        h_alice = FakeHandler()
        handle_list_projects(h_alice, self.alice)
        codes_alice = [p["code"] for p in h_alice.payload["projects"]]
        self.assertIn("M1", codes_alice)
        self.assertEqual([p["my_role"] for p in h_alice.payload["projects"] if p["code"] == "M1"], ["viewer"])

        h_bob = FakeHandler()
        handle_list_projects(h_bob, self.bob)
        codes_bob = [p["code"] for p in h_bob.payload["projects"]]
        self.assertNotIn("M1", codes_bob)


class TestLineApi(Phase2TestCase):
    def test_line_crud_and_sop(self):
        pid = self._mk_project("L1")
        from backend.service_org import handle_create_line, handle_list_lines, handle_update_line

        h = FakeHandler({"project_id": pid, "code": "LN1", "name": "总装一线", "sop_content": "步骤A"})
        handle_create_line(h, self.admin)
        self.assertEqual(h.status, 200, msg=str(h.payload))
        lid = h.payload["line_id"]

        # 列表带 sop_content
        hl = FakeHandler()
        handle_list_lines(hl, self.admin, parse(f"/api/lines?project_id={pid}"))
        self.assertEqual(hl.status, 200)
        self.assertEqual(len(hl.payload["lines"]), 1)
        self.assertEqual(hl.payload["lines"][0]["sop_content"], "步骤A")

        # 更新 SOP + 归档
        hu = FakeHandler({"line_id": lid, "sop_content": "新 SOP", "status": "archived", "name": "总装一线改"})
        handle_update_line(hu, self.admin)
        self.assertEqual(hu.status, 200)
        self.assertEqual(org.get_line_sop(lid), "新 SOP")
        self.assertEqual(org.get_production_line(lid)["status"], "archived")

    def test_line_duplicate_code_conflict(self):
        pid = self._mk_project("L2")
        from backend.service_org import handle_create_line

        for _ in range(2):
            h = FakeHandler({"project_id": pid, "code": "DUP", "name": "一线"})
            handle_create_line(h, self.admin)
        self.assertEqual(h.status, 409)

    def test_line_access_control(self):
        pid = self._mk_project("L3")
        other = self._mk_project("L4")
        org.add_project_member(pid, "alice", "owner")
        from backend.service_org import handle_create_line, handle_list_lines

        # alice 是 pid 的 owner：可建产线
        h = FakeHandler({"project_id": pid, "code": "LN-A", "name": "一线"})
        handle_create_line(h, self.alice)
        self.assertEqual(h.status, 200)

        # alice 不是 other 的成员：无权查看/创建
        h_forbidden = FakeHandler({"project_id": other, "code": "LN-B", "name": "二线"})
        handle_create_line(h_forbidden, self.alice)
        self.assertEqual(h_forbidden.status, 403)

        h_list = FakeHandler()
        handle_list_lines(h_list, self.alice, parse(f"/api/lines?project_id={other}"))
        self.assertEqual(h_list.status, 403)

    def test_list_lines_forbidden_project_for_plain_user(self):
        pid = self._mk_project("L5")
        from backend.service_org import handle_list_lines

        h = FakeHandler()
        handle_list_lines(h, self.bob, parse(f"/api/lines?project_id={pid}"))
        self.assertEqual(h.status, 403)


class TestMemberApi(Phase2TestCase):
    def test_member_add_list_remove(self):
        pid = self._mk_project("MB1")
        from backend.service_org import handle_add_member, handle_list_members, handle_remove_member

        h = FakeHandler({"project_id": pid, "username": "alice", "role": "editor"})
        handle_add_member(h, self.admin)
        self.assertEqual(h.status, 200, msg=str(h.payload))

        hl = FakeHandler()
        handle_list_members(hl, self.admin, parse(f"/api/members?project_id={pid}"))
        self.assertEqual(hl.status, 200)
        self.assertEqual([(m["username"], m["role"], m["user_role"]) for m in hl.payload["members"]], [("admin", "owner", "admin"), ("alice", "editor", "user")])

        hr = FakeHandler({"project_id": pid, "username": "alice"})
        handle_remove_member(hr, self.admin)
        self.assertEqual(hr.status, 200)
        self.assertEqual([m["username"] for m in org.list_project_members(pid)], ["admin"])

    def test_add_unknown_user_404(self):
        pid = self._mk_project("MB2")
        from backend.service_org import handle_add_member

        h = FakeHandler({"project_id": pid, "username": "ghost", "role": "viewer"})
        handle_add_member(h, self.admin)
        self.assertEqual(h.status, 404)

    def test_add_invalid_role_400(self):
        pid = self._mk_project("MB3")
        from backend.service_org import handle_add_member

        h = FakeHandler({"project_id": pid, "username": "alice", "role": "boss"})
        handle_add_member(h, self.admin)
        self.assertEqual(h.status, 400)

    def test_add_inactive_user_400(self):
        create_user("carol", "x", "user", None, "inactive", None, "kimi-2.5")
        pid = self._mk_project("MB3B")
        from backend.service_org import handle_add_member

        h = FakeHandler({"project_id": pid, "username": "carol", "role": "viewer"})
        handle_add_member(h, self.admin)
        self.assertEqual(h.status, 400)
        self.assertEqual(h.payload["error"], "user_inactive")

    def test_owner_can_manage_but_not_others(self):
        pid = self._mk_project("MB4")
        other = self._mk_project("MB5")
        org.add_project_member(pid, "alice", "owner")
        from backend.service_org import handle_add_member

        # alice（非 admin）作为 pid 的 owner 可以加成员
        h = FakeHandler({"project_id": pid, "username": "bob", "role": "viewer"})
        handle_add_member(h, self.alice)
        self.assertEqual(h.status, 200)

        # 对 other 项目无权限
        h2 = FakeHandler({"project_id": other, "username": "bob", "role": "viewer"})
        handle_add_member(h2, self.alice)
        self.assertEqual(h2.status, 403)

        # bob 是普通成员，不能管理
        h3 = FakeHandler({"project_id": pid, "username": "bob", "role": "viewer"})
        handle_add_member(h3, self.bob)
        self.assertEqual(h3.status, 403)

    def test_owner_removal_only_by_admin(self):
        pid = self._mk_project("MB6")
        org.add_project_member(pid, "alice", "owner")
        from backend.service_org import handle_remove_member

        # alice 是 owner，不能移除同为 owner 的 admin
        h = FakeHandler({"project_id": pid, "username": "admin"})
        handle_remove_member(h, self.alice)
        self.assertEqual(h.status, 403)

        # admin 可以移除
        h2 = FakeHandler({"project_id": pid, "username": "alice"})
        handle_remove_member(h2, self.admin)
        self.assertEqual(h2.status, 200)


class TestSopByLine(Phase2TestCase):
    def test_get_line_sop_vs_global(self):
        from backend.service_sop import handle_get_sop_content, handle_set_sop_content

        pid = self._mk_project("SP1")
        lid = org.create_production_line(pid, "LN1", "一线", sop_content="产线 SOP 内容")

        h = FakeHandler()
        handle_get_sop_content(h, self.admin, parse(f"/api/sop_content?line_id={lid}"))
        self.assertEqual(h.status, 200)
        self.assertEqual(h.payload["content"], "产线 SOP 内容")
        self.assertEqual(h.payload["scope"], "line")

        # 全局读取不传 line_id
        h2 = FakeHandler()
        handle_get_sop_content(h2, self.admin, parse("/api/sop_content"))
        self.assertEqual(h2.payload["scope"], "global")

    def test_set_line_sop_permission(self):
        pid = self._mk_project("SP2")
        lid = org.create_production_line(pid, "LN1", "一线")
        org.add_project_member(pid, "alice", "owner")
        from backend.service_sop import handle_set_sop_content

        # 项目 owner 可写产线 SOP
        h = FakeHandler({"line_id": lid, "content": "SOP v2"})
        handle_set_sop_content(h, self.alice)
        self.assertEqual(h.status, 200, msg=str(h.payload))
        self.assertEqual(org.get_line_sop(lid), "SOP v2")

        # bob（非成员）无权
        h2 = FakeHandler({"line_id": lid, "content": "恶意覆盖"})
        handle_set_sop_content(h2, self.bob)
        self.assertEqual(h2.status, 403)
        self.assertEqual(org.get_line_sop(lid), "SOP v2")

    def test_analyze_sop_priority_line_over_global(self):
        """产线有 SOP 时优先产线内容；无产线 SOP 时 get_line_sop 返回 None（回退全局文件）。"""
        pid = self._mk_project("SP3")
        lid_with = org.create_production_line(pid, "LN1", "一线", sop_content="产线专属")
        lid_without = org.create_production_line(pid, "LN2", "二线")
        self.assertEqual(org.get_line_sop(lid_with), "产线专属")
        self.assertIsNone(org.get_line_sop(lid_without))


class TestScopeFilter(Phase2TestCase):
    def test_list_videos_with_scope_query(self):
        import os

        from backend.service_media import handle_list_videos

        os.makedirs("data", exist_ok=True)
        tmp_files = []
        try:
            for name in ("_p2_scope_a.mp4", "_p2_scope_b.mp4", "_p2_scope_c.mp4"):
                path = os.path.join("data", name)
                with open(path, "wb") as f:
                    f.write(b"0")
                tmp_files.append(path)

            p1 = self._mk_project("SC1")
            p2 = self._mk_project("SC2")
            org.register_video(p1, "_p2_scope_a.mp4", tmp_files[0], uploaded_by="admin")
            org.register_video(p1, "_p2_scope_c.mp4", tmp_files[2], uploaded_by="admin")
            org.register_video(p2, "_p2_scope_b.mp4", tmp_files[1], uploaded_by="admin")

            h = FakeHandler()
            handle_list_videos(h, self.admin, parse(f"/api/list_videos?project_id={p1}"))
            self.assertEqual(h.status, 200)
            names = list(h.payload["files"])
            self.assertIn("_p2_scope_a.mp4", names)
            self.assertIn("_p2_scope_c.mp4", names)
            self.assertNotIn("_p2_scope_b.mp4", names)

            # line 过滤
            lid = org.create_production_line(p1, "LN1", "一线")
            org.register_video(p1, "_p2_scope_c.mp4", tmp_files[2], line_id=lid, uploaded_by="admin")
            h2 = FakeHandler()
            handle_list_videos(h2, self.admin, parse(f"/api/list_videos?project_id={p1}&line_id={lid}"))
            self.assertEqual(list(h2.payload["files"]), ["_p2_scope_c.mp4"])
        finally:
            for path in tmp_files:
                if os.path.exists(path):
                    os.remove(path)

    def test_results_offset_pagination(self):
        p1 = self._mk_project("PG1")
        for i in range(5):
            org.register_analysis_result(p1, f"result/r{i}.md", created_by="admin")
        rows_page1 = org.list_analysis_results_for_user("admin", role="admin", project_id=p1, limit=2, offset=0)
        rows_page2 = org.list_analysis_results_for_user("admin", role="admin", project_id=p1, limit=2, offset=2)
        self.assertEqual(len(rows_page1), 2)
        self.assertEqual(len(rows_page2), 2)
        ids1 = {int(r["id"]) for r in rows_page1}
        ids2 = {int(r["id"]) for r in rows_page2}
        self.assertFalse(ids1 & ids2)


if __name__ == "__main__":
    unittest.main()
