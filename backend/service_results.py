import json
import os
from typing import Dict, List

from backend.app_config import APP_VERSION
from backend.app_results_md import parse_md_content, update_md_content


def handle_list_results(handler) -> bool:
    try:
        files = []
        if os.path.exists("result"):
            files = [f for f in os.listdir("result") if f.endswith((".json", ".mp4", ".md"))]
        handler.send_response(200)
        handler.send_header("Content-type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"files": files}).encode("utf-8"))
        return True
    except Exception as e:
        handler.send_response(500)
        handler.end_headers()
        handler.wfile.write(str(e).encode("utf-8"))
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


def handle_update_result(handler) -> bool:
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
