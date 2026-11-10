"""阶段 4.2 批次 I：API 路由表（http.server 与 ASGI 双入口共用）。

统一签名：route(handler, user, parsed_path) -> bool
鉴权豁免名单 _AUTH_EXEMPT：version/login 免鉴权；task_events 因 EventSource
无法携带 Authorization 头，由各入口自行实现 Bearer/?token= 双通道鉴权。
"""
from typing import Callable, Dict, FrozenSet

from backend.service_analyze import handle_analyze, handle_task_status
from backend.service_media import (
    handle_clear_all_content,
    handle_delete_video,
    handle_ensure_playable,
    handle_extract_frames,
    handle_list_videos,
    handle_upload,
    handle_video_info,
)
from backend.service_org import (
    handle_add_member,
    handle_create_line,
    handle_create_project,
    handle_create_station,
    handle_delete_line,
    handle_delete_project,
    handle_delete_station,
    handle_list_lines,
    handle_list_members,
    handle_list_projects,
    handle_remove_member,
    handle_update_line,
    handle_update_project,
    handle_update_station,
)
from backend.service_project import handle_project_workspace
from backend.service_results import (
    get_latest_version,
    handle_list_results,
    handle_list_revisions,
    handle_result_details,
    handle_restore_revision,
    handle_update_result,
)
from backend.service_sop import handle_get_sop_content, handle_set_sop_content
from backend.service_thumbs import handle_result_thumbs
from backend.service_users import (
    handle_create_user,
    handle_list_users,
    handle_login,
    handle_logout,
    handle_me,
    handle_revoke_user_sessions,
    handle_user_history,
    handle_update_user,
)


def _route_version(handler, user, parsed_path):
    handler.send_json(200, {"version": get_latest_version()})


GET_ROUTES: Dict[str, Callable] = {
    "/api/version": _route_version,  # 免鉴权（见 _AUTH_EXEMPT）
    "/api/sop_content": lambda h, u, p: handle_get_sop_content(h, u, p),
    "/api/me": lambda h, u, p: handle_me(h, u),
    "/api/users": lambda h, u, p: handle_list_users(h, u),
    "/api/user_history": lambda h, u, p: handle_user_history(h, u, p),
    "/api/task_status": lambda h, u, p: handle_task_status(h, u),
    "/api/list_videos": lambda h, u, p: handle_list_videos(h, u, p),
    "/api/projects": lambda h, u, p: handle_list_projects(h, u),
    "/api/project_workspace": lambda h, u, p: handle_project_workspace(h, u, p),
    "/api/lines": lambda h, u, p: handle_list_lines(h, u, p),
    "/api/members": lambda h, u, p: handle_list_members(h, u, p),
    "/api/list_results": lambda h, u, p: handle_list_results(h, u, p),
    "/api/result_details": lambda h, u, p: handle_result_details(h, p),
    "/api/result_thumbs": lambda h, u, p: handle_result_thumbs(h, u, p),
    "/api/result_revisions": lambda h, u, p: handle_list_revisions(h, u, p),
    "/api/video_info": lambda h, u, p: handle_video_info(h, p),
}

POST_ROUTES: Dict[str, Callable] = {
    "/api/login": lambda h, u, p: handle_login(h),  # 免鉴权（见 _AUTH_EXEMPT）
    "/api/users": lambda h, u, p: handle_create_user(h, u),
    "/api/users/update": lambda h, u, p: handle_update_user(h, u),
    "/api/logout": lambda h, u, p: handle_logout(h, u),
    "/api/users/revoke_sessions": lambda h, u, p: handle_revoke_user_sessions(h, u),
    "/api/sop_content": lambda h, u, p: handle_set_sop_content(h, u),
    "/api/projects": lambda h, u, p: handle_create_project(h, u),
    "/api/projects/update": lambda h, u, p: handle_update_project(h, u),
    "/api/projects/delete": lambda h, u, p: handle_delete_project(h, u),
    "/api/lines": lambda h, u, p: handle_create_line(h, u),
    "/api/lines/update": lambda h, u, p: handle_update_line(h, u),
    "/api/lines/delete": lambda h, u, p: handle_delete_line(h, u),
    "/api/stations/create": lambda h, u, p: handle_create_station(h, u),
    "/api/stations/update": lambda h, u, p: handle_update_station(h, u),
    "/api/stations/delete": lambda h, u, p: handle_delete_station(h, u),
    "/api/members": lambda h, u, p: handle_add_member(h, u),
    "/api/members/remove": lambda h, u, p: handle_remove_member(h, u),
    "/api/update_result": lambda h, u, p: handle_update_result(h, u),
    "/api/result_revisions/restore": lambda h, u, p: handle_restore_revision(h, u),
    "/api/upload": lambda h, u, p: handle_upload(h, u, p),
    "/api/content/clear": lambda h, u, p: handle_clear_all_content(h, u),
    "/api/videos/delete": lambda h, u, p: handle_delete_video(h, u),
    "/api/videos/ensure_playable": lambda h, u, p: handle_ensure_playable(h, u),
    "/api/extract_frames": lambda h, u, p: handle_extract_frames(h, u),
    "/api/analyze": lambda h, u, p: handle_analyze(h, u),
}

_AUTH_EXEMPT: FrozenSet[str] = frozenset({"/api/version", "/api/login", "/api/task_events"})
