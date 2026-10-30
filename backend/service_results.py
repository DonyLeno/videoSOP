import json
import os
import urllib.parse
from typing import Dict, List, Optional

from backend.app_config import APP_VERSION
from backend.app_db_org import (
    add_result_revision,
    get_result_revision,
    list_analysis_results_for_user,
    list_result_revisions,
)
from backend.app_logging import get_logger
from backend.app_results_md import parse_md_content, update_md_content

logger = get_logger("results")


def _parse_int_param(params: Dict[str, List[str]], key: str) -> Optional[int]:
    raw = (params.get(key) or [""])[0]
    return int(raw) if str(raw).strip().lstrip("-").isdigit() else None


def handle_list_results(handler, user: Optional[Dict[str, object]] = None, parsed_path=None) -> bool:
    """结果列表：优先走 analysis_results 表（按用户可见项目过滤），DB 无记录时回退目录扫描。"""
    try:
        project_id = None
        line_id = None
        if parsed_path is not None:
            try:
                params = urllib.parse.parse_qs(parsed_path.query or "")
            except Exception:
                params = {}
            project_id = _parse_int_param(params, "project_id")
            line_id = _parse_int_param(params, "line_id")

        rows: List[Dict[str, object]] = []
        username = str((user or {}).get("username") or "")
        role = str((user or {}).get("role") or "")
        if username:
            try:
                rows = list_analysis_results_for_user(username, role, project_id, line_id)
            except Exception:
                logger.warning("结果列表查库失败，回退目录扫描", exc_info=True)
                rows = []

        files: List[str] = []
        for r in rows:
            md_path = str(r.get("md_path") or "")
            if md_path:
                basename = os.path.basename(md_path)
                if os.path.exists(os.path.join("result", basename)):
                    files.append(basename)
            vid_path = str(r.get("video_copy_path") or "")
            if vid_path:
                basename = os.path.basename(vid_path)
                if os.path.exists(os.path.join("result", basename)):
                    files.append(basename)
        if files:
            seen = set()
            ordered = [f for f in files if not (f in seen or seen.add(f))]
            handler.send_json(200, {"files": ordered})
            return True

        # 回退：DB 无记录（未跑迁移脚本），保持旧行为可用
        legacy: List[str] = []
        if os.path.exists("result"):
            legacy = [f for f in os.listdir("result") if f.endswith((".json", ".mp4", ".md"))]
        if legacy:
            logger.warning("analysis_results 表为空，结果列表回退目录扫描；建议运行 scripts/migrate_phase1.py")
        handler.send_json(200, {"files": legacy})
        return True
    except Exception as e:
        handler.send_json(500, {"error": str(e)})
        return True


def handle_result_details(handler, parsed_path) -> bool:
    import urllib.parse

    try:
        params = urllib.parse.parse_qs(parsed_path.query)
        rel_path = (params.get("path") or [""])[0]
        rel_path = rel_path.lstrip("/")
        rel_path = os.path.normpath(rel_path)
        if (
            not rel_path
            or rel_path.startswith("..")
            or rel_path.startswith("/")
            or not rel_path.startswith("result/")
        ):
            handler.send_json(400, {"error": "invalid path"})
            return True
        abs_path = os.path.join(os.getcwd(), rel_path)
        if not os.path.exists(abs_path):
            handler.send_json(404, {"error": "file not found"})
            return True
        if abs_path.lower().endswith(".json"):
            with open(abs_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            handler.send_json(200, data)
            return True
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        parsed = parse_md_content(content)
        handler.send_json(200, parsed)
        return True
    except Exception as e:
        handler.send_json(500, {"error": str(e)})
        return True


def _normalize_actions_for_compare(actions) -> List[Dict[str, str]]:
    """规范化动作列表用于变更检测：忽略空值键，数值统一为 3 位小数字符串。"""
    out: List[Dict[str, str]] = []
    for a in actions or []:
        if not isinstance(a, dict):
            continue
        item: Dict[str, str] = {}
        for k, v in a.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                item[str(k)] = format(float(v), ".3f")
                continue
            s = str(v if v is not None else "").strip()
            if s:
                item[str(k)] = s
        out.append(item)
    return out


def _actions_changed(old_actions, new_actions) -> bool:
    return _normalize_actions_for_compare(old_actions) != _normalize_actions_for_compare(new_actions)


def _read_current_actions(real_path: str) -> List[Dict[str, object]]:
    """读取结果文件中当前的动作列表（用于修订留痕）。"""
    try:
        if real_path.lower().endswith(".json"):
            with open(real_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for candidate in (data, data.get("model_output"), data.get("output")):
                    if isinstance(candidate, dict) and isinstance(candidate.get("actions"), list):
                        return candidate["actions"]
            if isinstance(data, list):
                return data
            return []
        with open(real_path, "r", encoding="utf-8") as f:
            content = f.read()
        return parse_md_content(content).get("actions") or []
    except Exception:
        logger.warning("读取当前动作失败: %s", real_path, exc_info=True)
        return []


def handle_update_result(handler, user: Optional[Dict[str, object]] = None) -> bool:
    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    post_data = handler.rfile.read(content_length)
    try:
        data = json.loads(post_data.decode("utf-8"))
        json_path = data.get("json_path") or data.get("filename") or data.get("path")
        new_actions = data.get("actions")
        if not json_path or new_actions is None:
            handler.send_response(400)
            handler.send_header("Content-type", "application/json")
            handler.end_headers()
            handler.wfile.write(json.dumps({"error": "Missing json_path or actions"}).encode("utf-8"))
            return True
        if json_path.startswith("/"):
            json_path = json_path[1:]
        real_path = os.path.join(os.getcwd(), json_path)
        if not os.path.exists(real_path):
            handler.send_response(404)
            handler.send_header("Content-type", "application/json")
            handler.end_headers()
            handler.wfile.write(json.dumps({"error": "File not found"}).encode("utf-8"))
            return True
        # 修改前留痕（仅当结果有变化时）
        try:
            old_actions = _read_current_actions(real_path)
            if _actions_changed(old_actions, new_actions):
                add_result_revision(
                    json_path,
                    old_actions,
                    created_by=str((user or {}).get("username") or ""),
                    revision_note="before_update",
                )
        except Exception:
            logger.warning("结果修订留痕失败: %s", json_path, exc_info=True)
        if real_path.lower().endswith(".md"):
            with open(real_path, "r", encoding="utf-8") as f:
                content = f.read()
            new_content = update_md_content(content, new_actions)
            with open(real_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            parsed = parse_md_content(new_content)
            handler.send_response(200)
            handler.send_header("Content-type", "application/json")
            handler.end_headers()
            handler.wfile.write(json.dumps({"status": "success", "data": parsed}).encode("utf-8"))
            return True

        with open(real_path, "r", encoding="utf-8") as f:
            file_data = json.load(f)

        def calculate_stats(actions: List[Dict[str, object]]):
            total_actions = len(actions)
            if total_actions == 0:
                return {
                    "total_actions": 0,
                    "unique_action_type_count": 0,
                    "avg_action_duration": 0.0,
                    "action_types": [],
                }
            by_label: Dict[str, Dict[str, float]] = {}
            total_duration = 0.0
            for act in actions:
                label = act.get("label", "Unknown")
                try:
                    start = float(act.get("start_time", 0))
                    end = float(act.get("end_time", 0))
                    duration = max(0, end - start)
                except Exception:
                    duration = 0
                total_duration += duration
                if label not in by_label:
                    by_label[label] = {"count": 0.0, "total_duration": 0.0}
                by_label[label]["count"] += 1.0
                by_label[label]["total_duration"] += float(duration)
            avg_action_duration = total_duration / total_actions if total_actions > 0 else 0
            action_types = []
            for label, v in by_label.items():
                avg = v["total_duration"] / v["count"] if v["count"] > 0 else 0
                action_types.append({"label": label, "count": int(v["count"]), "avg_duration": round(avg, 2)})
            action_types.sort(key=lambda x: x["count"], reverse=True)
            return {
                "total_actions": total_actions,
                "unique_action_type_count": len(by_label),
                "avg_action_duration": round(avg_action_duration, 2),
                "action_types": action_types,
            }

        new_stats = calculate_stats(new_actions)
        if isinstance(file_data, dict):
            file_data["actions"] = new_actions
            file_data["stats"] = new_stats
            if "model_output" in file_data and isinstance(file_data["model_output"], dict):
                file_data["model_output"]["actions"] = new_actions
                file_data["model_output"]["stats"] = new_stats
            if "output" in file_data and isinstance(file_data["output"], dict):
                file_data["output"]["actions"] = new_actions
                file_data["output"]["stats"] = new_stats
            file_data["computed_stats"] = new_stats
        with open(real_path, "w", encoding="utf-8") as f:
            json.dump(file_data, f, indent=2, ensure_ascii=False)
        handler.send_response(200)
        handler.send_header("Content-type", "application/json")
        handler.end_headers()
        handler.wfile.write(
            json.dumps(
                {"status": "success", "json_path": json_path, "stats": new_stats, "data": file_data}
            ).encode("utf-8")
        )
        return True
    except Exception as e:
        handler.send_response(500)
        handler.send_header("Content-type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        return True


def handle_list_revisions(handler, user: Optional[Dict[str, object]], parsed_path) -> bool:
    """GET /api/result_revisions?path=result/xxx.md —— 某结果的修订历史。"""
    try:
        params = urllib.parse.parse_qs(parsed_path.query or "")
        rel_path = (params.get("path") or [""])[0]
        rel_path = rel_path.lstrip("/")
        rel_path = os.path.normpath(rel_path)
        if not rel_path or rel_path.startswith("..") or not rel_path.startswith("result/"):
            handler.send_json(400, {"error": "invalid path", "revisions": []})
            return True
        rows = list_result_revisions(rel_path)
        handler.send_json(200, {"revisions": rows or []})
        return True
    except Exception as e:
        handler.send_json(500, {"error": str(e), "revisions": []})
        return True


def handle_restore_revision(handler, user: Optional[Dict[str, object]]) -> bool:
    """POST /api/result_revisions/restore body={"revision_id": N} —— 回滚到指定修订。"""
    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    post_data = handler.rfile.read(content_length)
    try:
        data = json.loads(post_data.decode("utf-8"))
        revision_id = data.get("revision_id")
        if revision_id is None or not str(revision_id).strip().isdigit():
            handler.send_json(400, {"error": "Missing revision_id"})
            return True
        rev = get_result_revision(int(revision_id))
        if not rev:
            handler.send_json(404, {"error": "revision not found"})
            return True
        json_path = str(rev.get("result_path") or "")
        restore_actions = rev.get("actions") or []
        if json_path.startswith("/"):
            json_path = json_path[1:]
        real_path = os.path.join(os.getcwd(), json_path)
        if not os.path.exists(real_path):
            handler.send_json(404, {"error": "File not found"})
            return True

        # 回滚前把当前版本留痕，保证回滚本身也可撤销
        try:
            current = _read_current_actions(real_path)
            if current and _actions_changed(current, restore_actions):
                add_result_revision(
                    json_path,
                    current,
                    created_by=str((user or {}).get("username") or ""),
                    revision_note=f"before_restore#{revision_id}",
                )
        except Exception:
            logger.warning("回滚前留痕失败: %s", json_path, exc_info=True)

        if real_path.lower().endswith(".md"):
            with open(real_path, "r", encoding="utf-8") as f:
                content = f.read()
            new_content = update_md_content(content, restore_actions)
            with open(real_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            parsed = parse_md_content(new_content)
        else:
            with open(real_path, "r", encoding="utf-8") as f:
                file_data = json.load(f)
            if isinstance(file_data, dict):
                file_data["actions"] = restore_actions
                if isinstance(file_data.get("model_output"), dict):
                    file_data["model_output"]["actions"] = restore_actions
                if isinstance(file_data.get("output"), dict):
                    file_data["output"]["actions"] = restore_actions
            with open(real_path, "w", encoding="utf-8") as f:
                json.dump(file_data, f, indent=2, ensure_ascii=False)
            parsed = file_data

        handler.send_json(
            200,
            {"status": "success", "restored_revision": int(revision_id), "data": parsed},
        )
        return True
    except Exception as e:
        handler.send_json(500, {"error": str(e)})
        return True


def get_latest_version() -> str:
    try:
        if APP_VERSION:
            return APP_VERSION
        candidate_paths = [
            "docs/version.md",
            "version.md",
        ]
        version_path = next((p for p in candidate_paths if os.path.exists(p)), "")
        if not version_path:
            return "Unknown"
        with open(version_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("## "):
                    return line.strip().replace("## ", "")
        return "Unknown"
    except Exception:
        return "Unknown"
