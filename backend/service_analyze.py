import datetime
import json
import os
import select
import shutil
import subprocess
import sys
import threading
import time
from typing import Dict, List, Optional

from backend.app_config import ANALYZE_CONCURRENCY
from backend.app_db import get_db_connection


USER_TASKS: Dict[str, Dict[str, object]] = {}
USER_TASKS_LOCK = threading.Lock()
ANALYZE_SEMAPHORE = threading.Semaphore(ANALYZE_CONCURRENCY)


def _iter_image_files(root: str) -> List[str]:
    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    paths: List[str] = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext in exts:
                paths.append(os.path.join(dirpath, name))
    paths.sort()
    return paths


def _normalize_kimi_cli_model(model: str) -> str:
    text = str(model or "").strip()
    lowered = text.lower()
    if lowered in ("genieviewk2.5", "genieview-k2.5") or text == "GenieviewK2.5":
        return "kimi-2.5"
    return text or model


def _set_task_progress(username: str, phase: str, current: int, total: int) -> None:
    with USER_TASKS_LOCK:
        task = USER_TASKS.get(username)
        if not task:
            return
        task["phase"] = phase
        task["progress"] = {"current": int(current), "total": int(total)}


def _append_task_log(username: str, message: str) -> None:
    with USER_TASKS_LOCK:
        task = USER_TASKS.get(username)
        if not task:
            return
        task.setdefault("logs", []).append(message)


def background_analyze_task(
    username: str,
    video_path: str,
    model: str,
    fps: float,
    api_key: str,
    sop_content: Optional[str] = None,
    result_timestamp: Optional[str] = None,
) -> None:
    task = USER_TASKS.get(username)
    if not task:
        ANALYZE_SEMAPHORE.release()
        return

    def log(msg: object) -> None:
        with USER_TASKS_LOCK:
            task["logs"].append(msg)

    try:
        os.makedirs("result", exist_ok=True)
        source_video_path = video_path
        if not os.path.exists(source_video_path):
            candidate = os.path.join("data", os.path.basename(video_path))
            if os.path.exists(candidate):
                source_video_path = candidate
        base_name = os.path.basename(source_video_path).rsplit(".", 1)[0]
        timestamp = str(result_timestamp).strip() if result_timestamp else ""
        if not timestamp:
            timestamp = datetime.datetime.now().strftime("%d.%H.%M.%S")
        result_filename = f"{base_name}_{timestamp}.md"
        result_path = os.path.join("result", result_filename)

        env = os.environ.copy()
        env.pop("GOOGLE_API_KEY", None)
        env.pop("GEMINI_API_KEY", None)
        env.pop("MOONSHOT_API_KEY", None)

        normalized_model = _normalize_kimi_cli_model(model)
        if normalized_model.startswith("kimi") or normalized_model.startswith("moonshot"):
            env["MOONSHOT_API_KEY"] = api_key
        else:
            env["GOOGLE_API_KEY"] = api_key

        python_exe = sys.executable
        cmd_main = [
            python_exe,
            "main.py",
            source_video_path,
            "--model",
            normalized_model,
            "--out",
            result_path,
            "--fps",
            str(fps),
            "--frames-dir",
            os.path.join("data", base_name),
            "--prompt-file",
            "data/prompt.md",
        ]
        if sop_content:
            cmd_main.extend(["--sop-content", sop_content])

        video_result_filename = result_filename.replace(".md", ".mp4")
        output_video_path = os.path.join("result", video_result_filename)
        try:
            if not os.path.exists(source_video_path):
                raise FileNotFoundError(f"source video not found: {source_video_path}")
            os.makedirs(os.path.dirname(output_video_path), exist_ok=True)
            _append_task_log(username, f"[INFO] Skipping YOLO detection. Copying video to {output_video_path}\n")
            shutil.copy2(source_video_path, output_video_path)
            _append_task_log(username, f"[INFO] Copied original video to {output_video_path}\n")
        except Exception as copy_err:
            _append_task_log(username, f"[ERROR] Copy failed: {str(copy_err)}\n")
            output_video_path = None

        frames_dir = os.path.join("data", base_name)
        image_paths = _iter_image_files(frames_dir)
        total_images = len(image_paths)
        if total_images == 0:
            with USER_TASKS_LOCK:
                task["status"] = "failed"
                task["error_msg"] = "no_images_found"
            return
        if total_images > 1000:
            with USER_TASKS_LOCK:
                task["status"] = "failed"
                task["error_msg"] = "超过模型保存文件上限（1000个）。请降低帧率或者分拆视频重新上传，保证视频时长*帧率 < 1000"
            return

        _set_task_progress(username, "analyze", 0, 0)
        _append_task_log(username, f"[INFO] Starting analysis for {video_path}\n")

        proc_main = subprocess.Popen(
            cmd_main,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=env,
        )
        analysis_stdout = ""
        analysis_stderr = ""

        fds = [proc_main.stdout.fileno(), proc_main.stderr.fileno()]
        while fds:
            ready, _, _ = select.select(fds, [], [])
            for fd in ready:
                if fd == proc_main.stdout.fileno():
                    line = proc_main.stdout.readline()
                    if line:
                        analysis_stdout += line
                        log(f"[ANALYSIS]{line}".encode("utf-8"))
                        try:
                            stripped = line.strip()
                            if stripped.startswith("{") and stripped.endswith("}"):
                                evt = json.loads(stripped)
                                if isinstance(evt, dict):
                                    evt_type = evt.get("event")
                                    if evt_type == "moonshot.chat_completions.request.batch":
                                        current_batch_start = evt.get("batch_start", 0)
                                        batch_count = evt.get("batch_frame_count", 0)
                                        processed = current_batch_start + int(batch_count / 3)
                                        _set_task_progress(username, "analyze", processed, total_images)
                                    elif evt_type == "moonshot.chat_completions.content.batch":
                                        current_batch_start = evt.get("batch_start", 0)
                                        batch_count = evt.get("batch_frame_count", 0)
                                        processed = current_batch_start + batch_count
                                        _set_task_progress(username, "analyze", processed, total_images)
                                    elif evt_type == "kimi.files.cleared":
                                        count = evt.get("count", 0)
                                        log(f"[INFO] 已清理 Kimi 云端历史文件: {count} 个\n".encode("utf-8"))
                        except Exception:
                            pass
                    else:
                        fds.remove(fd)
                elif fd == proc_main.stderr.fileno():
                    line = proc_main.stderr.readline()
                    if line:
                        analysis_stderr += line
                        log(f"[ANALYSIS_ERR]{line}".encode("utf-8"))
                    else:
                        fds.remove(fd)
            if not fds or (proc_main.poll() is not None):
                break

        status = "success"
        error_details = None
        if (proc_main.returncode or 0) != 0:
            status = "partial"
            error_details = "Gemini analysis failed"

        response = {
            "status": status,
            "json_path": result_path,
            "video_path": output_video_path,
            "error": error_details,
            "logs": {
                "analysis": {"command": " ".join(cmd_main), "stdout": analysis_stdout, "stderr": analysis_stderr},
                "annotation": {"command": "skipped", "stdout": "", "stderr": ""},
            },
        }

        if not os.path.exists(result_path):
            with USER_TASKS_LOCK:
                task["status"] = "failed"
                task["error_msg"] = "result_not_generated_check_logs"
                task["phase"] = "failed"
            return

        if (proc_main.returncode or 0) != 0:
            with USER_TASKS_LOCK:
                task["result"] = response
                task["status"] = "failed"
                task["error_msg"] = error_details or "analysis_failed"
                task["phase"] = "failed"
            return

        with USER_TASKS_LOCK:
            task["result"] = response
            task["status"] = "completed"
            task["phase"] = "completed"
    except Exception as e:
        with USER_TASKS_LOCK:
            task["status"] = "failed"
            task["error_msg"] = str(e)
            task["phase"] = "failed"
            task["logs"].append(f"\nERROR:{str(e)}\n")
    finally:
        ANALYZE_SEMAPHORE.release()


def handle_task_status(handler, user: Dict[str, object]) -> bool:
    username = str(user.get("username") or "")
    task = USER_TASKS.get(username)
    if not task:
        handler.send_json(200, {"status": "none"})
        return True
    with USER_TASKS_LOCK:
        response = {
            "status": task.get("status", "unknown"),
            "logs": list(task.get("logs", [])),
            "result": task.get("result"),
            "error_msg": task.get("error_msg"),
            "phase": task.get("phase"),
            "progress": task.get("progress"),
            "kind": task.get("kind"),
        }
        decoded_logs = []
        for log in response["logs"]:
            if isinstance(log, bytes):
                decoded_logs.append(log.decode("utf-8", errors="replace"))
            else:
                decoded_logs.append(str(log))
        response["logs"] = decoded_logs
    handler.send_json(200, response)
    return True


def handle_analyze(handler, user: Dict[str, object]) -> bool:
    acquired = ANALYZE_SEMAPHORE.acquire(blocking=False)
    if not acquired:
        handler.send_json(429, {"error": "server_busy", "details": "服务器正在处理其他检测任务，请稍后重试"})
        return True
    started = False
    try:
        content_length = int(handler.headers.get("Content-Length", "0") or "0")
        post_data = handler.rfile.read(content_length)
        try:
            data = json.loads(post_data.decode("utf-8"))
        except Exception:
            data = {}

        video_path = data.get("video_path")
        raw_model = data.get("model")
        text_model = str(raw_model).strip() if raw_model is not None else ""
        model = "kimi-2.5"

        fps_raw = data.get("fps", 2.0)
        api_key = None
        user_model = None
        username = user.get("username") if isinstance(user, dict) else None
        if username:
            try:
                conn = get_db_connection(use_database=True)
                cursor = conn.cursor()
                cursor.execute("SELECT api_key, model FROM users WHERE username=%s", (username,))
                row = cursor.fetchone()
                cursor.close()
                conn.close()
                if row:
                    api_key = str(row[0]).strip() or None
                    if row[1]:
                        user_model = str(row[1]).strip()
            except Exception as e:
                handler.send_json(500, {"error": "db_error", "details": str(e)})
                return True

        if text_model:
            model = text_model
        elif user_model:
            model = user_model
        else:
            model = "kimi-2.5"

        try:
            fps = float(fps_raw)
            if fps != fps or fps < 0:
                fps = 0.0
        except Exception:
            fps = 0.0

        if not video_path:
            handler.send_response(400)
            handler.send_header("Content-type", "application/json")
            handler.end_headers()
            handler.wfile.write(json.dumps({"error": "Missing video_path"}).encode("utf-8"))
            return True

        video_path = str(video_path).strip()
        if not video_path.startswith("data/"):
            video_path = os.path.join("data", os.path.basename(video_path))
        if not os.path.exists(video_path):
            handler.send_json(404, {"error": "video_not_found", "details": f"未找到视频文件: {video_path}"})
            return True

        base_name = os.path.basename(str(video_path)).rsplit(".", 1)[0]
        timestamp = datetime.datetime.now().strftime("%d.%H.%M.%S")
        output_video_path = os.path.join("result", f"{base_name}_{timestamp}.mp4")
        try:
            os.makedirs("result", exist_ok=True)
            shutil.copy2(video_path, output_video_path)
        except Exception as e:
            handler.send_json(500, {"error": "copy_failed", "details": str(e)})
            return True

        if not api_key:
            handler.send_json(
                400,
                {"error": "missing_user_api_key", "details": "当前用户未配置 API Key", "video_path": output_video_path},
            )
            return True

        frames_dir = os.path.join("data", base_name)
        if not os.path.isdir(frames_dir):
            handler.send_json(
                400,
                {
                    "error": "missing_frames_dir",
                    "details": "请先上传视频并完成图片拆分后再开始检测",
                    "video_path": output_video_path,
                },
            )
            return True
        image_count = len(_iter_image_files(frames_dir))
        if image_count == 0:
            handler.send_json(
                400,
                {"error": "missing_frames", "details": "未找到拆分后的图片，请先完成图片拆分", "video_path": output_video_path},
            )
            return True
        if image_count > 1000:
            handler.send_json(
                400,
                {
                    "error": "too_many_frames",
                    "details": "超过模型保存文件上限（1000个）。请降低帧率或者分拆视频重新上传，保证视频时长*帧率 < 1000",
                    "video_path": output_video_path,
                },
            )
            return True

        prompt_path = os.path.join("data", "prompt.md")
        if not os.path.exists(prompt_path):
            handler.send_json(
                500,
                {
                    "error": "missing_prompt_template",
                    "details": f"未找到 prompt 模板文件: {prompt_path}",
                    "video_path": output_video_path,
                },
            )
            return True

        sop_path = os.path.join("data", "SOP.md")
        sop_content = ""
        if os.path.exists(sop_path):
            try:
                with open(sop_path, "r", encoding="utf-8") as f:
                    sop_content = f.read()
            except Exception:
                sop_content = ""

        try:
            with USER_TASKS_LOCK:
                if username in USER_TASKS and USER_TASKS[username]["status"] == "running":
                    handler.send_json(409, {"error": "task_already_running", "details": "当前已有正在进行的任务，请等待其完成"})
                    return True
                USER_TASKS[username] = {
                    "status": "running",
                    "logs": [],
                    "result": None,
                    "error_msg": None,
                    "created_at": time.time(),
                    "phase": "analyze",
                    "progress": {"current": 0, "total": image_count},
                    "kind": "analyze",
                }
            t = threading.Thread(
                target=background_analyze_task,
                args=(username, video_path, model, fps, api_key, sop_content, timestamp),
                daemon=True,
            )
            t.start()
            handler.send_json(200, {"status": "started", "message": "任务已在后台启动", "video_path": output_video_path})
            started = True
        except Exception as e:
            handler.send_json(500, {"error": "internal_error", "details": str(e)})
            return True
        return True
    finally:
        if not started:
            ANALYZE_SEMAPHORE.release()

