"""项目工作台聚合接口：一个项目内的视频、任务、结果、产线与成员。

前端以项目为核心，进入项目后通过本接口一次性拿到工作区数据，避免
逐个项目查询列表后再拼装。接口只做只读聚合，写操作仍复用既有 API。
"""

import os
import urllib.parse
from typing import Dict, List, Optional

from backend.app_db_org import (
    can_manage_project,
    get_member_role,
    get_project,
    list_analysis_results_for_user,
    list_production_lines,
    list_project_members,
    list_station_video_counts,
    list_stations_for_project,
    list_tasks_for_project,
    list_videos_for_user,
    user_visible_project_ids,
)
from backend.app_logging import get_logger

logger = get_logger("project")

_TASK_STATUS_ACTIVE = ("pending", "running")


def _parse_int_param(params: Dict[str, List[str]], key: str) -> Optional[int]:
    raw = (params.get(key) or [""])[0]
    return int(raw) if str(raw).strip().lstrip("-").isdigit() else None


def _basename(path: str) -> str:
    return os.path.basename(str(path or "").replace("\\", "/"))


def _base_stem(name: str) -> str:
    return os.path.splitext(_basename(name))[0]


def _existing_rel(path: str, folder: str) -> str:
    """返回磁盘上真实存在的相对路径，不存在则返回空串。"""
    rel = str(path or "").strip().lstrip("/")
    if rel and os.path.exists(rel):
        return rel
    name = _basename(rel)
    if not name:
        return ""
    candidate = os.path.join(folder, name)
    return candidate if os.path.exists(candidate) else ""


def _line_key(value) -> str:
    """把数据库中的产线 ID 统一成字符串键，便于跨类型比较。"""
    try:
        return str(int(value))
    except Exception:
        return ""


def _line_view(row: Dict[str, object], include_sop: bool) -> Dict[str, object]:
    view = {
        "id": row.get("id"),
        "project_id": row.get("project_id"),
        "code": row.get("code"),
        "name": row.get("name"),
        "process_desc": row.get("process_desc"),
        "status": row.get("status"),
        "created_at": row.get("created_at"),
        "has_sop": bool(str(row.get("sop_content") or "").strip()),
    }
    if include_sop:
        view["sop_content"] = row.get("sop_content") or ""
    return view


def _task_view(row: Dict[str, object]) -> Dict[str, object]:
    return {
        "id": row.get("id"),
        "username": row.get("username"),
        "video_id": row.get("video_id"),
        "line_id": row.get("line_id"),
        "model": row.get("model"),
        "status": row.get("status"),
        "phase": row.get("phase"),
        "progress_current": row.get("progress_current"),
        "progress_total": row.get("progress_total"),
        "progress_unit": row.get("progress_unit"),
        "error": row.get("error"),
        "result_md_path": row.get("result_md_path"),
        "result_json_path": row.get("result_json_path"),
        "result_video_path": row.get("result_video_path"),
        "created_at": row.get("created_at"),
        "finished_at": row.get("finished_at"),
    }


def _result_view(row: Dict[str, object]) -> Optional[Dict[str, object]]:
    md_path = _existing_rel(str(row.get("md_path") or ""), "result")
    if not md_path:
        return None
    video_copy_path = _existing_rel(str(row.get("video_copy_path") or ""), "result")
    json_path = _existing_rel(str(row.get("json_path") or ""), "result")
    return {
        "id": row.get("id"),
        "task_id": row.get("task_id"),
        "video_id": row.get("video_id"),
        "line_id": row.get("line_id"),
        "md_path": md_path,
        "json_path": json_path,
        "video_copy_path": video_copy_path,
        "display_name": _basename(md_path),
        "video_name": _basename(video_copy_path),
        "created_at": row.get("created_at"),
        "created_by": row.get("created_by"),
    }


def _match_result_to_video(
    result: Dict[str, object],
    videos_by_id: Dict[int, Dict[str, object]],
    videos: List[Dict[str, object]],
) -> Optional[Dict[str, object]]:
    video_id = result.get("video_id")
    if video_id is not None:
        try:
            matched = videos_by_id.get(int(video_id))
        except Exception:
            matched = None
        if matched:
            return matched

    result_stem = _base_stem(str(result.get("display_name") or ""))
    if result_stem.startswith("en_"):
        result_stem = result_stem[3:]
    best = None
    best_len = -1
    for video in videos:
        stem = _base_stem(str(video.get("filename") or ""))
        if not stem:
            continue
        if result_stem == stem or result_stem.startswith(stem):
            if len(stem) > best_len:
                best = video
                best_len = len(stem)
    return best


def handle_project_workspace(handler, user: Dict[str, object], parsed_path) -> bool:
    """GET /api/project_workspace?project_id=N&line_id=N —— 项目工作台聚合数据。"""
    try:
        params = urllib.parse.parse_qs(parsed_path.query or "")
    except Exception:
        params = {}
    project_id = _parse_int_param(params, "project_id")
    line_id = _parse_int_param(params, "line_id")
    if not project_id:
        handler.send_json(400, {"error": "missing_project_id"})
        return True

    username = str(user.get("username") or "")
    role = str(user.get("role") or "")
    visible = set(user_visible_project_ids(username, role))
    if project_id not in visible:
        handler.send_json(403, {"error": "forbidden", "details": "无权访问该项目"})
        return True

    project = get_project(project_id)
    if not project:
        handler.send_json(404, {"error": "project_not_found"})
        return True

    can_manage = can_manage_project(user, project_id)
    try:
        line_rows = list_production_lines(project_id) or []
        # 先取项目全量数据，用于产线维度的计数，再按 line_id 过滤当前视图
        all_video_rows = list_videos_for_user(username, role, project_id, None) or []
        all_result_rows = list_analysis_results_for_user(
            username, role, project_id, None, limit=2000
        ) or []
        all_task_rows = list_tasks_for_project(project_id, None, limit=500) or []
        member_rows = list_project_members(project_id) or []
        station_rows = list_stations_for_project(project_id)
        station_video_counts = (
            list_station_video_counts(line_id) if line_id else {}
        )
    except Exception as e:
        logger.exception("项目工作台查询失败: project_id=%s", project_id)
        handler.send_json(500, {"error": "db_error", "details": str(e)})
        return True

    line_stats: Dict[str, Dict[str, int]] = {}

    def bump(value, key: str) -> None:
        line_key = _line_key(value)
        if not line_key:
            return
        bucket = line_stats.setdefault(
            line_key, {"video_count": 0, "result_count": 0, "task_count": 0}
        )
        bucket[key] += 1

    for row in all_video_rows:
        bump(row.get("line_id"), "video_count")
    for row in all_result_rows:
        bump(row.get("line_id"), "result_count")
    for row in all_task_rows:
        bump(row.get("line_id"), "task_count")

    if line_id:
        current_key = str(line_id)
        video_rows = [r for r in all_video_rows if _line_key(r.get("line_id")) == current_key]
        result_rows = [r for r in all_result_rows if _line_key(r.get("line_id")) == current_key]
        task_rows = [r for r in all_task_rows if _line_key(r.get("line_id")) == current_key]
    else:
        video_rows = all_video_rows
        result_rows = all_result_rows
        task_rows = all_task_rows

    lines = [_line_view(row, include_sop=can_manage) for row in line_rows]
    stations_by_line: Dict[str, List[Dict[str, object]]] = {}
    station_names: Dict[str, str] = {}
    for station in station_rows:
        stations_by_line.setdefault(_line_key(station.get("line_id")), []).append(station)
        station_names[_line_key(station.get("id"))] = str(station.get("name") or "")
    for line in lines:
        line_key = _line_key(line.get("id"))
        line["stats"] = line_stats.get(
            line_key, {"video_count": 0, "result_count": 0, "task_count": 0}
        )
        line["stats"]["station_count"] = len(stations_by_line.get(line_key, []))
    line_names = {str(l.get("id")): str(l.get("name") or "") for l in lines}

    stations: List[Dict[str, object]] = []
    if line_id:
        for station in stations_by_line.get(str(line_id), []):
            sid = _line_key(station.get("id"))
            stations.append(
                {
                    "id": station.get("id"),
                    "line_id": station.get("line_id"),
                    "code": station.get("code"),
                    "name": station.get("name"),
                    "description": station.get("description") or "",
                    "sop_content": station.get("sop_content") or "",
                    "pos_x": float(station.get("pos_x") or 0),
                    "pos_y": float(station.get("pos_y") or 0),
                    "rotation": float(station.get("rotation") or 0),
                    "video_count": station_video_counts.get(int(sid), 0) if sid.isdigit() else 0,
                }
            )

    results: List[Dict[str, object]] = []
    for row in result_rows:
        view = _result_view(row)
        if view is not None:
            results.append(view)

    videos: List[Dict[str, object]] = []
    videos_by_id: Dict[int, Dict[str, object]] = {}
    for row in video_rows:
        stored_path = _existing_rel(str(row.get("stored_path") or ""), "data")
        if not stored_path:
            continue
        video = {
            "id": row.get("id"),
            "project_id": row.get("project_id"),
            "line_id": row.get("line_id"),
            "line_name": line_names.get(str(row.get("line_id")), ""),
            "station_id": row.get("station_id"),
            "station_name": station_names.get(_line_key(row.get("station_id")), ""),
            "filename": row.get("filename") or _basename(stored_path),
            "stored_path": stored_path,
            "duration_sec": row.get("duration_sec"),
            "size_bytes": row.get("size_bytes"),
            "uploaded_by": row.get("uploaded_by"),
            "created_at": row.get("created_at"),
            "latest_result": None,
            "latest_task": None,
        }
        videos.append(video)
        try:
            videos_by_id[int(row.get("id"))] = video
        except Exception:
            continue

    for result in results:
        matched = _match_result_to_video(result, videos_by_id, videos)
        if matched is not None:
            result["video_name"] = result.get("video_name") or matched.get("filename")
            result["video_id"] = result.get("video_id") or matched.get("id")
            if matched.get("latest_result") is None:
                matched["latest_result"] = result

    tasks = [_task_view(row) for row in task_rows]
    latest_task_by_video: Dict[int, Dict[str, object]] = {}
    for task in tasks:
        video_id = task.get("video_id")
        if video_id is None:
            continue
        try:
            key = int(video_id)
        except Exception:
            continue
        if key not in latest_task_by_video:
            latest_task_by_video[key] = task

    for video in videos:
        try:
            video["latest_task"] = latest_task_by_video.get(int(video.get("id")))
        except Exception:
            video["latest_task"] = None

    members = [
        {
            "username": row.get("username"),
            "role": row.get("role"),
            "created_at": row.get("created_at"),
        }
        for row in member_rows
    ]

    stats = {
        "video_count": len(videos),
        "result_count": len(results),
        "task_count": len(tasks),
        "running_task_count": sum(1 for t in tasks if t.get("status") in _TASK_STATUS_ACTIVE),
        "line_count": len(lines),
        "member_count": len(members),
    }

    handler.send_json(
        200,
        {
            "project": {
                "id": project.get("id"),
                "code": project.get("code"),
                "name": project.get("name"),
                "description": project.get("description"),
                "status": project.get("status"),
                "created_at": project.get("created_at"),
                "my_role": get_member_role(project_id, username),
            },
            "can_manage": can_manage,
            "lines": lines,
            "stations": stations,
            "members": members,
            "stats": stats,
            "videos": videos,
            "results": results,
            "tasks": tasks,
        },
    )
    return True
