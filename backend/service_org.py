"""阶段 2 组织层级 API：项目 / 产线 / 成员管理，以及产线级 SOP。

权限模型：
- admin：全部项目可见、可管理
- 项目 owner：可管理所属项目的产线与成员
- 普通用户：仅可见自己所属项目（user_visible_project_ids 过滤）
"""

import json
import urllib.parse
from typing import Dict, List, Optional

from backend.app_db import get_user_me
from backend.app_db_org import (
    MEMBER_ROLES,
    STATION_MAX_COUNT,
    STATION_ORIGIN_Y,
    add_project_member,
    can_manage_project,
    count_line_references,
    count_project_references,
    count_station_videos,
    create_default_stations,
    create_production_line,
    create_project,
    delete_production_line,
    delete_project,
    delete_station,
    get_member_role,
    get_production_line,
    get_project,
    get_project_by_code,
    get_station,
    list_production_lines,
    list_project_members,
    list_projects,
    list_stations,
    next_station_position,
    remove_project_member,
    update_production_line,
    update_project,
    update_station,
    user_visible_project_ids,
)
from backend.app_logging import get_logger

logger = get_logger("org")


def _read_json_body(handler) -> Dict[str, object]:
    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    post_data = handler.rfile.read(content_length)
    try:
        data = json.loads(post_data.decode("utf-8")) if post_data else {}
    except Exception:
        data = {}
    return data if isinstance(data, dict) else {}


def _parse_int_param(params: Dict[str, List[str]], key: str) -> Optional[int]:
    raw = (params.get(key) or [""])[0]
    return int(raw) if str(raw).strip().lstrip("-").isdigit() else None


def _project_summary(row: Dict[str, object], member_role: Optional[str] = None) -> Dict[str, object]:
    """去掉大字段后的项目视图，附带请求者在该项目中的角色。"""
    return {
        "id": row.get("id"),
        "code": row.get("code"),
        "name": row.get("name"),
        "description": row.get("description"),
        "status": row.get("status"),
        "created_by": row.get("created_by"),
        "created_at": row.get("created_at"),
        "my_role": member_role or "",
    }


# ---------------------------------------------------------------------------
# 项目
# ---------------------------------------------------------------------------


def handle_list_projects(handler, user: Dict[str, object]) -> bool:
    username = str(user.get("username") or "")
    role = str(user.get("role") or "")
    try:
        rows = list_projects(username or None, role)
    except Exception as e:
        logger.exception("项目列表查询失败")
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    visible = set(user_visible_project_ids(username, role))
    items = []
    for r in rows or []:
        try:
            pid = int(r.get("id"))
        except Exception:
            continue
        if pid not in visible:
            continue
        items.append(_project_summary(r, get_member_role(pid, username)))
    handler.send_json(200, {"projects": items})
    return True


def handle_create_project(handler, user: Dict[str, object]) -> bool:
    if str(user.get("role") or "") != "admin":
        handler.send_json(403, {"error": "forbidden", "details": "仅管理员可创建项目"})
        return True
    data = _read_json_body(handler)
    code = str(data.get("code") or "").strip()
    name = str(data.get("name") or "").strip()
    description = str(data.get("description") or "").strip() or None
    if not code or not name:
        handler.send_json(400, {"error": "missing_code_or_name", "details": "项目编号与名称必填"})
        return True
    if get_project_by_code(code):
        handler.send_json(409, {"error": "duplicate_code", "details": f"项目编号已存在: {code}"})
        return True
    try:
        creator = str(user.get("username") or "admin")
        pid = create_project(code, name, description, creator)
        if pid and creator:
            add_project_member(int(pid), creator, "owner")
    except Exception as e:
        logger.exception("创建项目失败")
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    handler.send_json(200, {"status": "success", "project_id": pid})
    return True


def handle_update_project(handler, user: Dict[str, object]) -> bool:
    if str(user.get("role") or "") != "admin":
        handler.send_json(403, {"error": "forbidden", "details": "仅管理员可编辑项目"})
        return True
    data = _read_json_body(handler)
    try:
        pid = int(data.get("project_id") or data.get("id") or 0)
    except Exception:
        pid = 0
    if not pid:
        handler.send_json(400, {"error": "missing_project_id"})
        return True
    if not get_project(pid):
        handler.send_json(404, {"error": "project_not_found"})
        return True
    status = data.get("status")
    if status is not None and str(status) not in ("active", "archived"):
        handler.send_json(400, {"error": "invalid_status", "details": "status 仅支持 active/archived"})
        return True
    try:
        update_project(
            pid,
            name=str(data["name"]) if data.get("name") is not None else None,
            description=str(data["description"]) if data.get("description") is not None else None,
            status=str(status) if status is not None else None,
        )
    except Exception as e:
        logger.exception("更新项目失败: pid=%s", pid)
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    handler.send_json(200, {"status": "success"})
    return True


def handle_delete_project(handler, user: Dict[str, object]) -> bool:
    """POST /api/projects/delete —— 删除项目；项目下仍有视频/任务/结果时拒绝。"""
    data = _read_json_body(handler)
    try:
        pid = int(data.get("project_id") or data.get("id") or 0)
    except Exception:
        pid = 0
    if not pid:
        handler.send_json(400, {"error": "missing_project_id"})
        return True
    if not get_project(pid):
        handler.send_json(404, {"error": "project_not_found"})
        return True
    if not can_manage_project(user, pid):
        handler.send_json(403, {"error": "forbidden", "details": "仅管理员或项目 owner 可删除项目"})
        return True
    try:
        refs = count_project_references(pid)
    except Exception as e:
        logger.exception("项目占用统计失败: pid=%s", pid)
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    blocking = {
        "video_count": refs.get("video_count", 0),
        "task_count": refs.get("task_count", 0),
        "result_count": refs.get("result_count", 0),
    }
    if any(int(v or 0) > 0 for v in blocking.values()):
        handler.send_json(
            409,
            {
                "error": "project_in_use",
                "details": "项目下仍有视频、任务或结果，请先在设置页清理内容后再删除",
                "references": refs,
            },
        )
        return True
    try:
        counts = delete_project(pid)
    except Exception as e:
        logger.exception("删除项目失败: pid=%s", pid)
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    handler.send_json(200, {"status": "success", "deleted": counts})
    return True


# ---------------------------------------------------------------------------
# 产线
# ---------------------------------------------------------------------------


def _line_view(row: Dict[str, object]) -> Dict[str, object]:
    return {
        "id": row.get("id"),
        "project_id": row.get("project_id"),
        "code": row.get("code"),
        "name": row.get("name"),
        "process_desc": row.get("process_desc"),
        "sop_content": row.get("sop_content"),
        "status": row.get("status"),
        "created_at": row.get("created_at"),
    }


def handle_list_lines(handler, user: Dict[str, object], parsed_path) -> bool:
    try:
        params = urllib.parse.parse_qs(parsed_path.query or "")
    except Exception:
        params = {}
    project_id = _parse_int_param(params, "project_id")
    username = str(user.get("username") or "")
    role = str(user.get("role") or "")
    visible = set(user_visible_project_ids(username, role))
    if project_id and project_id not in visible:
        handler.send_json(403, {"error": "forbidden", "details": "无权访问该项目"})
        return True
    try:
        if project_id:
            rows = list_production_lines(project_id)
        else:
            rows: List[Dict[str, object]] = []
            for pid in sorted(visible):
                rows.extend(list_production_lines(pid))
    except Exception as e:
        logger.exception("产线列表查询失败")
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    handler.send_json(200, {"lines": [_line_view(r) for r in rows or []]})
    return True


def handle_create_line(handler, user: Dict[str, object]) -> bool:
    """POST /api/lines/create —— 创建产线，station_count 指定初始工位数量。"""
    data = _read_json_body(handler)
    try:
        project_id = int(data.get("project_id") or 0)
    except Exception:
        project_id = 0
    if not project_id:
        handler.send_json(400, {"error": "missing_project_id"})
        return True
    if not can_manage_project(user, project_id):
        handler.send_json(403, {"error": "forbidden", "details": "仅管理员或项目 owner 可创建产线"})
        return True
    code = str(data.get("code") or "").strip()
    name = str(data.get("name") or "").strip()
    if not code or not name:
        handler.send_json(400, {"error": "missing_code_or_name", "details": "产线编号与名称必填"})
        return True
    try:
        station_count = int(data.get("station_count") or 0)
    except Exception:
        station_count = 0
    if station_count < 0 or station_count > STATION_MAX_COUNT:
        handler.send_json(
            400,
            {"error": "invalid_station_count", "details": f"工位数量需在 0~{STATION_MAX_COUNT} 之间"},
        )
        return True
    for existing in list_production_lines(project_id) or []:
        if str(existing.get("code") or "") == code:
            handler.send_json(409, {"error": "duplicate_code", "details": f"产线编号已存在: {code}"})
            return True
    try:
        lid = create_production_line(
            project_id,
            code,
            name,
            process_desc=str(data.get("process_desc") or "").strip() or None,
            sop_content=str(data.get("sop_content") or "") or None,
        )
        if station_count:
            create_default_stations(lid, station_count)
    except Exception as e:
        logger.exception("创建产线失败: project_id=%s", project_id)
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    handler.send_json(200, {"status": "success", "line_id": lid, "station_count": station_count})
    return True


def handle_update_line(handler, user: Dict[str, object]) -> bool:
    data = _read_json_body(handler)
    try:
        line_id = int(data.get("line_id") or data.get("id") or 0)
    except Exception:
        line_id = 0
    if not line_id:
        handler.send_json(400, {"error": "missing_line_id"})
        return True
    line = get_production_line(line_id)
    if not line:
        handler.send_json(404, {"error": "line_not_found"})
        return True
    project_id = int(line.get("project_id") or 0)
    if not can_manage_project(user, project_id):
        handler.send_json(403, {"error": "forbidden", "details": "仅管理员或项目 owner 可编辑产线"})
        return True
    status = data.get("status")
    if status is not None and str(status) not in ("active", "archived"):
        handler.send_json(400, {"error": "invalid_status", "details": "status 仅支持 active/archived"})
        return True
    try:
        update_production_line(
            line_id,
            name=str(data["name"]) if data.get("name") is not None else None,
            process_desc=str(data["process_desc"]) if data.get("process_desc") is not None else None,
            sop_content=str(data["sop_content"]) if data.get("sop_content") is not None else None,
            status=str(status) if status is not None else None,
        )
    except Exception as e:
        logger.exception("更新产线失败: line_id=%s", line_id)
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    handler.send_json(200, {"status": "success"})
    return True


def handle_delete_line(handler, user: Dict[str, object]) -> bool:
    """POST /api/lines/delete —— 删除产线；产线下仍有视频/任务/结果时拒绝。"""
    data = _read_json_body(handler)
    try:
        line_id = int(data.get("line_id") or data.get("id") or 0)
    except Exception:
        line_id = 0
    if not line_id:
        handler.send_json(400, {"error": "missing_line_id"})
        return True
    line = get_production_line(line_id)
    if not line:
        handler.send_json(404, {"error": "line_not_found"})
        return True
    project_id = int(line.get("project_id") or 0)
    if not can_manage_project(user, project_id):
        handler.send_json(403, {"error": "forbidden", "details": "仅管理员或项目 owner 可删除产线"})
        return True
    try:
        refs = count_line_references(line_id)
    except Exception as e:
        logger.exception("产线占用统计失败: line_id=%s", line_id)
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    if any(int(v or 0) > 0 for v in refs.values()):
        handler.send_json(
            409,
            {
                "error": "line_in_use",
                "details": "该产线下仍有视频、任务或结果，请先清理后再删除",
                "references": refs,
            },
        )
        return True
    try:
        delete_production_line(line_id)
    except Exception as e:
        logger.exception("删除产线失败: line_id=%s", line_id)
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    handler.send_json(200, {"status": "success"})
    return True


# ---------------------------------------------------------------------------
# 工位（产线内 2.5D 布局）
# ---------------------------------------------------------------------------


def _station_context(station_id: int):
    """返回 (station, project_id, error_response)。"""
    station = get_station(station_id)
    if not station:
        return None, 0, (404, {"error": "station_not_found", "details": "工位不存在"})
    line = get_production_line(int(station.get("line_id") or 0))
    if not line:
        return None, 0, (404, {"error": "line_not_found", "details": "产线不存在"})
    return station, int(line.get("project_id") or 0), None


def handle_create_station(handler, user: Dict[str, object]) -> bool:
    """POST /api/stations/create —— 在产线内新增一个工位。"""
    data = _read_json_body(handler)
    try:
        line_id = int(data.get("line_id") or 0)
    except Exception:
        line_id = 0
    if not line_id:
        handler.send_json(400, {"error": "missing_line_id"})
        return True
    line = get_production_line(line_id)
    if not line:
        handler.send_json(404, {"error": "line_not_found"})
        return True
    project_id = int(line.get("project_id") or 0)
    if not can_manage_project(user, project_id):
        handler.send_json(403, {"error": "forbidden", "details": "仅管理员或项目 owner 可新增工位"})
        return True
    try:
        existing = list_stations(line_id)
        if len(existing) >= STATION_MAX_COUNT:
            handler.send_json(400, {"error": "too_many_stations", "details": f"单条产线最多 {STATION_MAX_COUNT} 个工位"})
            return True
        name = str(data.get("name") or "").strip()
        try:
            pos_x = float(data.get("pos_x")) if data.get("pos_x") is not None else None
            pos_y = float(data.get("pos_y")) if data.get("pos_y") is not None else None
        except Exception:
            pos_x, pos_y = None, None
        if pos_x is None and pos_y is None:
            pos_x, pos_y = next_station_position(line_id), STATION_ORIGIN_Y
        ids = create_default_stations(line_id, 1, start_index=len(existing))
        if not ids:
            handler.send_json(500, {"error": "create_failed", "details": "工位创建失败"})
            return True
        station_id = ids[0]
        update_station(station_id, name=name or None, pos_x=pos_x, pos_y=pos_y)
    except Exception as e:
        logger.exception("新增工位失败: line_id=%s", line_id)
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    handler.send_json(200, {"status": "success", "station_id": station_id})
    return True


def handle_update_station(handler, user: Dict[str, object]) -> bool:
    """POST /api/stations/update —— 修改工位名称、说明、SOP 或平面坐标。"""
    data = _read_json_body(handler)
    try:
        station_id = int(data.get("station_id") or data.get("id") or 0)
    except Exception:
        station_id = 0
    if not station_id:
        handler.send_json(400, {"error": "missing_station_id"})
        return True
    station, project_id, error = _station_context(station_id)
    if error:
        handler.send_json(*error)
        return True
    if not can_manage_project(user, project_id):
        handler.send_json(403, {"error": "forbidden", "details": "仅管理员或项目 owner 可编辑工位"})
        return True
    name = data.get("name")
    pos_x = data.get("pos_x")
    pos_y = data.get("pos_y")
    rotation = data.get("rotation")
    description = data.get("description")
    sop_content = data.get("sop_content")
    if name is not None and not str(name).strip():
        handler.send_json(400, {"error": "empty_station_name"})
        return True
    if description is not None and len(str(description)) > 2000:
        handler.send_json(400, {"error": "station_description_too_long", "max_length": 2000})
        return True
    if sop_content is not None and len(str(sop_content)) > 20000:
        handler.send_json(400, {"error": "station_sop_too_long", "max_length": 20000})
        return True
    try:
        if pos_x is not None:
            pos_x = min(max(float(pos_x), 0.0), 100.0)
        if pos_y is not None:
            pos_y = min(max(float(pos_y), 0.0), 100.0)
        if rotation is not None:
            rotation = float(rotation)
        update_station(
            station_id,
            name=str(name).strip() if name is not None else None,
            pos_x=pos_x,
            pos_y=pos_y,
            rotation=rotation,
            description=str(description) if description is not None else None,
            sop_content=str(sop_content) if sop_content is not None else None,
        )
    except Exception as e:
        logger.exception("更新工位失败: station_id=%s", station_id)
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    handler.send_json(200, {"status": "success"})
    return True


def handle_delete_station(handler, user: Dict[str, object]) -> bool:
    """POST /api/stations/delete —— 删除工位；工位已绑定视频时拒绝。"""
    data = _read_json_body(handler)
    try:
        station_id = int(data.get("station_id") or data.get("id") or 0)
    except Exception:
        station_id = 0
    if not station_id:
        handler.send_json(400, {"error": "missing_station_id"})
        return True
    station, project_id, error = _station_context(station_id)
    if error:
        handler.send_json(*error)
        return True
    if not can_manage_project(user, project_id):
        handler.send_json(403, {"error": "forbidden", "details": "仅管理员或项目 owner 可删除工位"})
        return True
    try:
        video_count = count_station_videos(station_id)
    except Exception as e:
        logger.exception("工位占用统计失败: station_id=%s", station_id)
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    if video_count > 0:
        handler.send_json(
            409,
            {
                "error": "station_in_use",
                "details": f"该工位已绑定 {video_count} 个视频，无法删除",
                "video_count": video_count,
            },
        )
        return True
    try:
        delete_station(station_id)
    except Exception as e:
        logger.exception("删除工位失败: station_id=%s", station_id)
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    handler.send_json(200, {"status": "success"})
    return True


# ---------------------------------------------------------------------------
# 项目成员
# ---------------------------------------------------------------------------


def handle_list_members(handler, user: Dict[str, object], parsed_path) -> bool:
    try:
        params = urllib.parse.parse_qs(parsed_path.query or "")
    except Exception:
        params = {}
    project_id = _parse_int_param(params, "project_id")
    if not project_id:
        handler.send_json(400, {"error": "missing_project_id"})
        return True
    if not can_manage_project(user, project_id):
        handler.send_json(403, {"error": "forbidden", "details": "仅管理员或项目 owner 可查看成员"})
        return True
    try:
        rows = list_project_members(project_id)
    except Exception as e:
        logger.exception("成员列表查询失败: project_id=%s", project_id)
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    members = []
    for r in rows or []:
        u = None
        try:
            u = get_user_me(str(r.get("username") or ""))
        except Exception:
            u = None
        members.append(
            {
                "username": r.get("username"),
                "role": r.get("role"),
                "created_at": r.get("created_at"),
                "user_role": (u or {}).get("role"),
                "status": (u or {}).get("status"),
            }
        )
    handler.send_json(200, {"members": members})
    return True


def handle_add_member(handler, user: Dict[str, object]) -> bool:
    data = _read_json_body(handler)
    try:
        project_id = int(data.get("project_id") or 0)
    except Exception:
        project_id = 0
    if not project_id:
        handler.send_json(400, {"error": "missing_project_id"})
        return True
    if not can_manage_project(user, project_id):
        handler.send_json(403, {"error": "forbidden", "details": "仅管理员或项目 owner 可管理成员"})
        return True
    username = str(data.get("username") or "").strip()
    role = str(data.get("role") or "editor").strip() or "editor"
    if not username:
        handler.send_json(400, {"error": "missing_username"})
        return True
    if role not in MEMBER_ROLES:
        handler.send_json(400, {"error": "invalid_role", "details": "角色仅支持 owner/editor/viewer"})
        return True
    target = None
    try:
        target = get_user_me(username)
    except Exception:
        target = None
    if not target:
        handler.send_json(404, {"error": "user_not_found", "details": f"用户不存在: {username}"})
        return True
    if str(target.get("status") or "active") != "active":
        handler.send_json(400, {"error": "user_inactive", "details": f"用户已停用: {username}"})
        return True
    try:
        add_project_member(project_id, username, role)
    except Exception as e:
        logger.exception("添加成员失败: project_id=%s, username=%s", project_id, username)
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    handler.send_json(200, {"status": "success"})
    return True


def handle_remove_member(handler, user: Dict[str, object]) -> bool:
    data = _read_json_body(handler)
    try:
        project_id = int(data.get("project_id") or 0)
    except Exception:
        project_id = 0
    if not project_id:
        handler.send_json(400, {"error": "missing_project_id"})
        return True
    if not can_manage_project(user, project_id):
        handler.send_json(403, {"error": "forbidden", "details": "仅管理员或项目 owner 可管理成员"})
        return True
    username = str(data.get("username") or "").strip()
    if not username:
        handler.send_json(400, {"error": "missing_username"})
        return True
    if str(user.get("role") or "") != "admin" and get_member_role(project_id, username) == "owner":
        handler.send_json(403, {"error": "forbidden", "details": "仅管理员可移除项目 owner"})
        return True
    try:
        remove_project_member(project_id, username)
    except Exception as e:
        logger.exception("移除成员失败: project_id=%s, username=%s", project_id, username)
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True
    handler.send_json(200, {"status": "success"})
    return True
