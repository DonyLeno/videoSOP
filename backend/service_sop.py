import json
import os
import urllib.parse
from typing import Dict, List, Optional

from backend.app_db_org import can_manage_project, get_line_sop, get_production_line, update_production_line
from backend.app_logging import get_logger

logger = get_logger("sop")


def _global_sop_path() -> str:
    return os.path.join(os.getcwd(), "data", "SOP.md")


def _parse_int_param(params: Dict[str, List[str]], key: str) -> Optional[int]:
    raw = (params.get(key) or [""])[0]
    return int(raw) if str(raw).strip().lstrip("-").isdigit() else None


def _read_global_sop() -> str:
    sop_path = _global_sop_path()
    if os.path.exists(sop_path):
        try:
            with open(sop_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            logger.warning("读取全局 SOP 失败: %s", sop_path, exc_info=True)
    return ""


def handle_get_sop_content(handler, user: dict, parsed_path=None) -> bool:
    """SOP 读取：带 line_id 时返回产线级 SOP，否则返回全局 data/SOP.md。"""
    line_id = None
    if parsed_path is not None:
        try:
            params = urllib.parse.parse_qs(parsed_path.query or "")
        except Exception:
            params = {}
        line_id = _parse_int_param(params, "line_id")
    try:
        if line_id:
            content = get_line_sop(line_id) or ""
        else:
            content = _read_global_sop()
        handler.send_json(200, {"content": content, "line_id": line_id, "scope": "line" if line_id else "global"})
        return True
    except Exception as e:
        handler.send_json(500, {"error": str(e)})
        return True


def handle_set_sop_content(handler, user: dict) -> bool:
    """SOP 保存：body 含 line_id 时写产线级 SOP（需项目管理权限），否则写全局文件。"""
    try:
        content_length = int(handler.headers.get("Content-Length", "0") or "0")
        post_data = handler.rfile.read(content_length)
        data = json.loads(post_data.decode("utf-8"))
        new_content = data.get("content")
        line_id_raw = data.get("line_id")
        line_id = int(line_id_raw) if line_id_raw else None
        if new_content is None:
            handler.send_json(400, {"error": "missing_content"})
            return True

        if line_id:
            line = get_production_line(line_id)
            if not line:
                handler.send_json(404, {"error": "line_not_found"})
                return True
            if not can_manage_project(user, int(line.get("project_id") or 0)):
                handler.send_json(403, {"error": "forbidden", "details": "仅管理员或项目 owner 可编辑产线 SOP"})
                return True
            update_production_line(line_id, sop_content=str(new_content))
            handler.send_json(200, {"status": "success", "scope": "line", "line_id": line_id})
            return True

        sop_path = _global_sop_path()
        os.makedirs(os.path.dirname(sop_path), exist_ok=True)
        with open(sop_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        handler.send_json(200, {"status": "success", "scope": "global"})
        return True
    except Exception as e:
        handler.send_json(500, {"error": str(e)})
        return True
