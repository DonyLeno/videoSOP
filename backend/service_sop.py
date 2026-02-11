import io
import json
import os
import re
import subprocess
import urllib.parse
import zipfile

from backend.app_results_md import parse_md_content, update_md_content


def handle_get_sop_content(handler, user: dict) -> bool:
    try:
        sop_path = os.path.join(os.getcwd(), "data", "SOP.md")
        if os.path.exists(sop_path):
            with open(sop_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = ""
        handler.send_json(200, {"content": content})
        return True
    except Exception as e:
        handler.send_json(500, {"error": str(e)})
        return True


def handle_set_sop_content(handler, user: dict) -> bool:
    try:
        sop_path = os.path.join(os.getcwd(), "data", "SOP.md")
        content_length = int(handler.headers.get("Content-Length", "0") or "0")
        post_data = handler.rfile.read(content_length)
        data = json.loads(post_data.decode("utf-8"))
        new_content = data.get("content")
        os.makedirs(os.path.dirname(sop_path), exist_ok=True)
        with open(sop_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        handler.send_json(200, {"status": "success"})
        return True
    except Exception as e:
        handler.send_json(500, {"error": str(e)})
        return True


def handle_sop_clips_info(handler, parsed_path) -> bool:
    try:
        user = handler.get_auth_user()
        if not user:
            handler.send_json(401, {"error": "unauthorized"})
            return True
        path_arg = ""
        query = urllib.parse.parse_qs(parsed_path.query)
        if "path" in query:
            path_arg = query["path"][0]
        if not path_arg:
            handler.send_json(400, {"error": "missing_path"})
            return True
        if path_arg.startswith("/"):
            path_arg = path_arg[1:]
        real_file_path = os.path.join(os.getcwd(), path_arg)
        base_dir = os.path.dirname(real_file_path)
        file_name_no_ext = os.path.splitext(os.path.basename(real_file_path))[0]
        sop_root = os.path.join(base_dir, file_name_no_ext)
        if not os.path.exists(sop_root) or not os.path.isdir(sop_root):
            handler.send_json(200, {"exists": False})
            return True
        groups = []
        for entry in os.scandir(sop_root):
            if entry.is_dir():
                sop_name = entry.name
                files = []
                for f in os.scandir(entry.path):
                    if f.is_file() and f.name.lower().endswith(".mp4"):
                        files.append(f.name)
                files.sort()
                if files:
                    groups.append(
                        {
                            "name": sop_name,
                            "path": os.path.relpath(entry.path, os.getcwd()),
                            "files": [
                                {
                                    "name": fn,
                                    "url": f"/{os.path.relpath(os.path.join(entry.path, fn), os.getcwd())}",
                                }
                                for fn in files
                            ],
                        }
                    )
        groups.sort(key=lambda x: x["name"])
        if not groups:
            handler.send_json(200, {"exists": False})
            return True
        handler.send_json(
            200,
            {
                "exists": True,
                "root_path": os.path.relpath(sop_root, os.getcwd()),
                "groups": groups,
            },
        )
        return True
    except Exception as e:
        try:
            handler.send_json(500, {"error": "internal_error", "details": str(e)})
        except Exception:
            pass
        return True


def handle_download_folder(handler, parsed_path) -> bool:
    user = handler.get_auth_user()
    if not user:
        handler.send_json(401, {"error": "unauthorized"})
        return True
    path_arg = ""
    query = urllib.parse.parse_qs(parsed_path.query)
    if "path" in query:
        path_arg = query["path"][0]
    if not path_arg:
        handler.send_json(400, {"error": "missing_path"})
        return True
    if path_arg.startswith("/"):
        path_arg = path_arg[1:]
    real_path = os.path.join(os.getcwd(), path_arg)
    result_dir = os.path.join(os.getcwd(), "result")
    if not os.path.commonpath([real_path, result_dir]) == result_dir:
        handler.send_json(403, {"error": "forbidden_path"})
        return True
    if not os.path.exists(real_path) or not os.path.isdir(real_path):
        handler.send_json(404, {"error": "folder_not_found"})
        return True
    try:
        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(real_path):
                for file in files:
                    if file.lower().endswith((".mp4", ".md")):
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, real_path)
                        zf.write(file_path, arcname)
        mem_zip.seek(0)
        zip_filename = os.path.basename(real_path.rstrip("/")) + ".zip"
        handler.send_response(200)
        handler.send_header("Content-Type", "application/zip")
        handler.send_header("Content-Disposition", f'attachment; filename="{zip_filename}"')
        handler.send_header("Content-Length", str(len(mem_zip.getvalue())))
        handler.end_headers()
        handler.wfile.write(mem_zip.getvalue())
        return True
    except Exception as e:
        handler.send_json(500, {"error": "download_failed", "details": str(e)})
        return True


def handle_export_sop_clips(handler, user: dict) -> bool:
    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    post_data = handler.rfile.read(content_length)
    try:
        data = json.loads(post_data.decode("utf-8"))
    except Exception:
        data = {}
    file_path = data.get("path")
    video_path = data.get("video_path")
    if not file_path or not video_path:
        handler.send_json(400, {"error": "missing_path_or_video"})
        return True
    if file_path.startswith("/"):
        file_path = file_path[1:]
    if video_path.startswith("/"):
        video_path = video_path[1:]
    real_file_path = os.path.join(os.getcwd(), file_path)
    real_video_path = os.path.join(os.getcwd(), video_path)
    if not os.path.exists(real_file_path) or not os.path.exists(real_video_path):
        handler.send_json(404, {"error": "file_not_found"})
        return True
    actions = []
    try:
        if real_file_path.lower().endswith(".md"):
            with open(real_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            parsed = parse_md_content(content)
            actions = parsed.get("actions", [])
        else:
            with open(real_file_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)
            if isinstance(json_data, dict):
                actions = json_data.get("actions", [])
                if not actions and "model_output" in json_data:
                    actions = (json_data.get("model_output") or {}).get("actions", [])
    except Exception as e:
        handler.send_json(500, {"error": f"parse_error: {str(e)}"})
        return True
    if not actions:
        handler.send_json(400, {"error": "no_actions_found"})
        return True
    sop_groups = []
    current_sop = None
    current_group = []
    for act in actions:
        sop_val = str(act.get("sop") or "").strip()
        if sop_val != current_sop:
            if current_group:
                sop_groups.append({"sop": current_sop, "actions": current_group})
            current_sop = sop_val
            current_group = [act]
        else:
            current_group.append(act)
    if current_group:
        sop_groups.append({"sop": current_sop, "actions": current_group})

    export_count = 0
    base_dir = os.path.dirname(real_file_path)
    file_name_no_ext = os.path.splitext(os.path.basename(real_file_path))[0]
    output_root = os.path.join(base_dir, file_name_no_ext)
    try:
        for group in sop_groups:
            sop_name = group["sop"]
            if not sop_name:
                continue
            group_actions = group["actions"]
            if not group_actions:
                continue
            start_act = group_actions[0]
            end_act = group_actions[-1]
            try:
                s_time = float(start_act.get("start_time", 0))
                e_time = float(end_act.get("end_time", 0))
            except Exception:
                continue
            if e_time <= s_time:
                continue

            def sec_to_str(sec: float) -> str:
                m, s = divmod(sec, 60)
                h, m = divmod(m, 60)
                return f"{int(h):02d}-{int(m):02d}-{int(s):02d}"

            s_str = sec_to_str(s_time)
            e_str = sec_to_str(e_time)
            sop_name = str(sop_name).strip()
            m = re.search(r"(?i)\bSOP\s*(\d+)\b", sop_name)
            if m:
                safe_sop_name = f"SOP{m.group(1)}"
            else:
                safe_sop_name = "".join([c for c in sop_name if c.isalnum() or c in ("-", "_")]).strip()
            if not safe_sop_name:
                safe_sop_name = "Unknown_SOP"
            sop_dir = os.path.join(output_root, safe_sop_name)
            os.makedirs(sop_dir, exist_ok=True)
            filename = f"{safe_sop_name}_{s_str}_{e_str}.mp4"
            out_path = os.path.join(sop_dir, filename)
            duration = e_time - s_time
            md_content = update_md_content("", group_actions)
            md_filename = f"{os.path.splitext(filename)[0]}.md"
            md_path = os.path.join(sop_dir, md_filename)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            cmd = [
                "ffmpeg",
                "-y",
                "-ss",
                str(s_time),
                "-i",
                real_video_path,
                "-t",
                str(duration),
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                out_path,
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                try:
                    print(f"FFmpeg error for {filename}: {result.stderr.decode('utf-8')}")
                except Exception:
                    pass
            else:
                export_count += 1
        handler.send_json(200, {"status": "success", "count": export_count, "output_dir": output_root})
        return True
    except Exception as e:
        handler.send_json(500, {"error": f"export_failed: {str(e)}"})
        return True

