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
from backend.app_db import add_detection_history, get_user_api_key_model
from backend.app_db_org import (
    TASK_STATUS_CANCELED,
    TASK_STATUS_FAILED,
    TASK_STATUS_PENDING,
    TASK_STATUS_RUNNING,
    TASK_STATUS_SUCCEEDED,
    create_task,
    ensure_default_scope,
    fail_stale_tasks,
    finish_task,
    get_line_sop,
    get_video_by_path,
    mark_task_running,
    register_analysis_result,
    update_task_progress,
)
from backend.app_logging import get_logger
from backend.service_media import _get_video_duration
from backend.translate import translate_file

logger = get_logger("analyze")

USER_TASKS: Dict[str, Dict[str, object]] = {}
USER_TASKS_LOCK = threading.Lock()
ANALYZE_SEMAPHORE = threading.Semaphore(ANALYZE_CONCURRENCY)

# 服务重启时被中断的任务 (username, task_id)，供 /api/task_status 兜底响应使用
INTERRUPTED_TASKS: set = set()


def recover_interrupted_tasks() -> int:
    """服务启动时调用：把遗留的 pending/running 任务标记为 failed(interrupted)。

    返回被中断任务数。之后用户轮询 task_status 会收到明确的失败原因，而非无限等待。
    """
    try:
        stale = fail_stale_tasks()
    except Exception:
        logger.warning("恢复中断任务失败", exc_info=True)
        return 0
    for row in stale or []:
        try:
            INTERRUPTED_TASKS.add((str(row.get("username")), int(row.get("id"))))
        except Exception:
            continue
    count = len(INTERRUPTED_TASKS)
    if count:
        logger.info("已将 %d 个重启前遗留任务标记为 failed(interrupted)", count)
    return count


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
    if not text:
        return "kimi-2.5"
    lowered = text.lower()
    if lowered in ("Geniviewk2.5", "Geniview-k2.5") or text == "GeniviewK2.5":
        return "kimi-2.5"
    if lowered in ("qwen3.5", "qwen3.5-plus", "qwen-3.5", "qwen-3.5-plus"):
        return "qwen3.5-plus"
    return text or model


def _is_qwen_model(model: str) -> bool:
    return str(model or "").lower().startswith("qwen3.5")


def _extract_tokens_from_md(path: str) -> Dict[str, Optional[int]]:
    token_input = None
    token_output = None
    token_thinking = None
    token_total = None
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = []
            for _ in range(30):
                line = f.readline()
                if not line:
                    break
                lines.append(line.strip())
    except Exception:
        return {
            "token_input": None,
            "token_output": None,
            "token_thinking": None,
            "token_total": None,
        }
    patterns = {
        "token_input": [
            r"Input Token\s*[:：]\s*(\d+)",
            r"输入\s*Token\s*[:：]\s*(\d+)",
            r"输入\s*token\s*[:：]\s*(\d+)",
        ],
        "token_output": [
            r"Output Token\s*[:：]\s*(\d+)",
            r"输出\s*Token\s*[:：]\s*(\d+)",
            r"输出\s*token\s*[:：]\s*(\d+)",
        ],
        "token_thinking": [
            r"Thinking Token\s*[:：]\s*(\d+)",
            r"思考\s*Token\s*[:：]\s*(\d+)",
            r"思考\s*token\s*[:：]\s*(\d+)",
        ],
        "token_total": [
            r"Total Token\s*[:：]\s*(\d+)",
            r"总\s*Token\s*[:：]\s*(\d+)",
        ],
    }
    import re

    for line in lines:
        for key, pats in patterns.items():
            if key == "token_input" and token_input is not None:
                continue
            if key == "token_output" and token_output is not None:
                continue
            if key == "token_thinking" and token_thinking is not None:
                continue
            if key == "token_total" and token_total is not None:
                continue
            for pat in pats:
                m = re.search(pat, line, flags=re.IGNORECASE)
                if not m:
                    continue
                val = m.group(1)
                try:
                    num = int(val)
                except Exception:
                    num = None
                if key == "token_input":
                    token_input = num
                elif key == "token_output":
                    token_output = num
                elif key == "token_thinking":
                    token_thinking = num
                elif key == "token_total":
                    token_total = num
                break
    if token_total is None:
        parts = [p for p in [token_input, token_output, token_thinking] if isinstance(p, int)]
        if parts:
            token_total = int(sum(parts))
    return {
        "token_input": token_input,
        "token_output": token_output,
        "token_thinking": token_thinking,
        "token_total": token_total,
    }


def _set_task_progress(username: str, phase: str, current: int, total: int) -> None:
    with USER_TASKS_LOCK:
        task = USER_TASKS.get(username)
        if not task:
            return
        task["phase"] = phase
        task["progress"] = {"current": int(current), "total": int(total)}
        task_id = task.get("task_id")
    if task_id:
        try:
            update_task_progress(int(task_id), phase, int(current), int(total))
        except Exception:
            logger.warning("任务进度写库失败: task_id=%s", task_id, exc_info=True)


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
    prompt_file: Optional[str] = None,
    sop_content: Optional[str] = None,
    result_timestamp: Optional[str] = None,
    ui_lang: Optional[str] = None,
) -> None:
    task = USER_TASKS.get(username)
    if not task:
        ANALYZE_SEMAPHORE.release()
        return

    task_id = task.get("task_id")
    project_id = task.get("project_id")
    line_id = task.get("line_id")
    video_id = task.get("video_id")
    if task_id:
        try:
            mark_task_running(int(task_id))
        except Exception:
            logger.warning("任务 started_at 写库失败: task_id=%s", task_id, exc_info=True)

    def log(msg: object) -> None:
        with USER_TASKS_LOCK:
            task["logs"].append(msg)

    def _fail_task(error_msg: str) -> None:
        """内存与 DB 同步置为失败。"""
        with USER_TASKS_LOCK:
            task["status"] = "failed"
            task["error_msg"] = error_msg
            task["phase"] = "failed"
        if task_id:
            try:
                finish_task(int(task_id), TASK_STATUS_FAILED, error=error_msg)
            except Exception:
                logger.warning("任务失败状态写库失败: task_id=%s", task_id, exc_info=True)

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
        warnings_filters = str(env.get("PYTHONWARNINGS") or "").strip()
        suppress_google_py39 = "ignore:You are using a Python version 3.9 past its end of life:FutureWarning"
        if warnings_filters:
            env["PYTHONWARNINGS"] = warnings_filters + "," + suppress_google_py39
        else:
            env["PYTHONWARNINGS"] = suppress_google_py39

        normalized_model = _normalize_kimi_cli_model(model)
        if normalized_model.startswith("kimi") or normalized_model.startswith("moonshot"):
            env["MOONSHOT_API_KEY"] = api_key
        elif _is_qwen_model(normalized_model):
            env["DASHSCOPE_API_KEY"] = api_key
            env.pop("http_proxy", None)
            env.pop("https_proxy", None)
            env.pop("HTTP_PROXY", None)
            env.pop("HTTPS_PROXY", None)
            env.pop("ALL_PROXY", None)
        else:
            env["GOOGLE_API_KEY"] = api_key

        python_exe = sys.executable
        prompt_file_arg = os.path.join("data", "ch_prompt.md")
        cmd_main = [
            python_exe,
            "main.py",
            source_video_path,
            "--model",
            normalized_model,
            "--out",
            result_path,
            "--prompt-file",
            prompt_file_arg,
        ]
        if not _is_qwen_model(normalized_model):
            cmd_main.extend(["--fps", str(fps), "--frames-dir", os.path.join("data", base_name)])
        if sop_content:
            cmd_main.extend(["--sop-content", sop_content])

        video_result_filename = result_filename.replace(".md", ".mp4")
        output_video_path = os.path.join("result", video_result_filename)

        total_images = 1
        if not _is_qwen_model(normalized_model):
            frames_dir = os.path.join("data", base_name)
            image_paths = _iter_image_files(frames_dir)
            total_images = len(image_paths)
            if total_images == 0:
                _fail_task("no_images_found")
                return
            if total_images > 1000:
                _fail_task("超过模型保存文件上限（1000个）。请降低帧率或者分拆视频重新上传，保证视频时长*帧率 < 1000")
                return

        max_retries = 3
        final_response = None
        for attempt in range(max_retries + 1):
            try:
                # 1. Copy video
                try:
                    if not os.path.exists(source_video_path):
                        raise FileNotFoundError(f"source video not found: {source_video_path}")
                    os.makedirs(os.path.dirname(output_video_path), exist_ok=True)
                    if not os.path.exists(output_video_path):
                        _append_task_log(username, f"[INFO] Copying video to {output_video_path}\n")
                        shutil.copy2(source_video_path, output_video_path)
                        _append_task_log(username, f"[INFO] Copied original video to {output_video_path}\n")
                except Exception as copy_err:
                    raise Exception(f"Copy failed: {str(copy_err)}")

                # 2. Analysis
                _set_task_progress(username, "analyze", 0, total_images)
                _append_task_log(username, f"[INFO] Starting analysis for {video_path} (Attempt {attempt + 1}/{max_retries + 1})\n")
                _append_task_log(username, f"[INFO] Prompt template: {prompt_file_arg}\n")

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
                                                batch_end = evt.get("batch_end")
                                                if isinstance(batch_end, int):
                                                    processed = int(batch_end)
                                                else:
                                                    processed = int(current_batch_start) + int(batch_count)
                                                _set_task_progress(username, "analyze", processed, total_images)
                                            elif evt_type == "moonshot.chat_completions.content.batch":
                                                current_batch_start = evt.get("batch_start", 0)
                                                batch_count = evt.get("batch_frame_count", 0)
                                                batch_end = evt.get("batch_end")
                                                if isinstance(batch_end, int):
                                                    processed = int(batch_end)
                                                else:
                                                    processed = int(current_batch_start) + int(batch_count)
                                                _set_task_progress(username, "analyze", processed, total_images)
                                            elif evt_type == "moonshot.chat_completions.request":
                                                _set_task_progress(username, "analyze", 0, total_images)
                                            elif evt_type == "moonshot.chat_completions.content":
                                                _set_task_progress(username, "analyze", total_images, total_images)
                                            elif evt_type == "qwen.chat_completions.request":
                                                _set_task_progress(username, "analyze", 0, total_images)
                                            elif evt_type == "qwen.chat_completions.content":
                                                _set_task_progress(username, "analyze", total_images, total_images)
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
                exit_code = int(proc_main.returncode or 0)
                if exit_code != 0:
                    status = "partial"
                    error_details = f"analysis_subprocess_failed(exit_code={exit_code}, model={normalized_model})"

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
                    stderr_tail = (analysis_stderr or "").strip()[-1200:]
                    stdout_tail = (analysis_stdout or "").strip()[-1200:]
                    details = stderr_tail or stdout_tail or "no_subprocess_output"
                    raise Exception(
                        f"result_not_generated_check_logs | model={normalized_model} | exit_code={exit_code} | details={details}"
                    )

                if exit_code != 0:
                    raise Exception(error_details or "analysis_failed")

                if _is_qwen_model(normalized_model):
                    _set_task_progress(username, "analyze", total_images, total_images)
                # Store response and break loop on success
                final_response = response
                break

            except Exception as attempt_err:
                _append_task_log(username, f"[WARNING] Attempt {attempt + 1} failed: {str(attempt_err)}\n")
                
                # Cleanup video and result on failure
                if output_video_path and os.path.exists(output_video_path):
                    try:
                        os.remove(output_video_path)
                        _append_task_log(username, f"[INFO] Deleted video {output_video_path} for cleanup\n")
                    except: pass
                
                if os.path.exists(result_path):
                    try:
                        os.remove(result_path)
                    except: pass

                if attempt == max_retries:
                    _fail_task(f"Failed after {max_retries + 1} attempts: {str(attempt_err)}")
                    return
                
                time.sleep(3)

        # Auto-translate result and complete task
        if final_response:
            if (ui_lang or "").strip().lower() == "en":
                try:
                    translate_api_key = None
                    if normalized_model.startswith("kimi") or normalized_model.startswith("moonshot"):
                        translate_api_key = api_key
                    _append_task_log(username, f"[INFO] Starting auto-translation for {result_path}...\n")
                    translate_file(result_path, translate_api_key)
                    _append_task_log(username, f"[INFO] Auto-translation completed.\n")
                except Exception as e:
                    _append_task_log(username, f"[WARNING] Auto-translation failed: {str(e)}\n")

            token_info = {"token_input": None, "token_output": None, "token_thinking": None, "token_total": None}
            try:
                token_info = _extract_tokens_from_md(result_path)
            except Exception as e:
                _append_task_log(username, f"[WARNING] token extraction failed: {str(e)}\n")

            try:
                video_duration = None
                if output_video_path and os.path.exists(output_video_path):
                    video_duration = _get_video_duration(output_video_path)
                if video_duration is None and source_video_path and os.path.exists(source_video_path):
                    video_duration = _get_video_duration(source_video_path)
                add_detection_history(
                    username=username,
                    video_name=os.path.basename(output_video_path) if output_video_path else None,
                    video_path=output_video_path,
                    result_path=result_path,
                    model=normalized_model,
                    created_at=datetime.datetime.now().isoformat(),
                    video_seconds=video_duration,
                    token_input=token_info.get("token_input"),
                    token_output=token_info.get("token_output"),
                    token_thinking=token_info.get("token_thinking"),
                    token_total=token_info.get("token_total"),
                    project_id=project_id,
                    line_id=line_id,
                    task_id=task_id,
                )
            except Exception as e:
                _append_task_log(username, f"[WARNING] history record failed: {str(e)}\n")

            # 结果登记入库（幂等，md_path 已存在则跳过）
            result_json_path = result_path[:-3] + ".json" if result_path.endswith(".md") else None
            if result_json_path and not os.path.exists(result_json_path):
                result_json_path = None
            en_md_path = os.path.join("result", f"en_{os.path.basename(result_path)}")
            if not os.path.exists(en_md_path):
                en_md_path = None
            stats_json = None
            if result_json_path:
                try:
                    with open(result_json_path, "r", encoding="utf-8") as f:
                        file_data = json.load(f)
                    stats_obj = (file_data or {}).get("stats")
                    if stats_obj is not None:
                        stats_json = json.dumps(stats_obj, ensure_ascii=False)
                except Exception:
                    stats_json = None
            try:
                if project_id:
                    register_analysis_result(
                        project_id=int(project_id),
                        md_path=result_path,
                        line_id=int(line_id) if line_id else None,
                        task_id=int(task_id) if task_id else None,
                        video_id=int(video_id) if video_id else None,
                        json_path=result_json_path,
                        video_copy_path=output_video_path,
                        en_md_path=en_md_path,
                        stats_json=stats_json,
                        created_by=username,
                    )
            except Exception as e:
                _append_task_log(username, f"[WARNING] result registration failed: {str(e)}\n")

            # 任务终态写库
            if task_id:
                try:
                    finish_task(
                        int(task_id),
                        TASK_STATUS_SUCCEEDED,
                        md_path=result_path,
                        json_path=result_json_path,
                        video_path=output_video_path,
                        token_input=token_info.get("token_input"),
                        token_output=token_info.get("token_output"),
                        token_thinking=token_info.get("token_thinking"),
                        token_total=token_info.get("token_total"),
                    )
                except Exception:
                    logger.warning("任务成功状态写库失败: task_id=%s", task_id, exc_info=True)
            # Update status to completed after translation
            with USER_TASKS_LOCK:
                task["result"] = final_response
                task["status"] = "completed"
                task["phase"] = "completed"

    except Exception as e:
        _fail_task(str(e))
        _append_task_log(username, f"\nERROR:{str(e)}\n")
    finally:
        ANALYZE_SEMAPHORE.release()


def _task_row_to_response(row: Dict[str, object]) -> Dict[str, object]:
    """把 DB 任务行转换为 /api/task_status 响应结构（与内存视图字段兼容）。"""
    st = str(row.get("status") or "")
    status_map = {
        TASK_STATUS_PENDING: "running",
        TASK_STATUS_RUNNING: "running",
        TASK_STATUS_SUCCEEDED: "completed",
        TASK_STATUS_FAILED: "failed",
        TASK_STATUS_CANCELED: "failed",
    }
    result = None
    if st == TASK_STATUS_SUCCEEDED:
        result = {
            "status": "success",
            "json_path": row.get("result_md_path"),
            "video_path": row.get("result_video_path"),
        }
    return {
        "status": status_map.get(st, st),
        "logs": [],
        "result": result,
        "error_msg": row.get("error"),
        "phase": row.get("phase"),
        "progress": {
            "current": int(row.get("progress_current") or 0),
            "total": int(row.get("progress_total") or 0),
        },
        "kind": "analyze",
        "model": row.get("model"),
        "progress_unit": row.get("progress_unit"),
        "task_id": row.get("id"),
    }


def handle_task_status(handler, user: Dict[str, object]) -> bool:
    from backend.service_events import _task_status_payload

    response = _task_status_payload(str(user.get("username") or ""))
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

        fps_raw = data.get("fps", 3.0)
        api_key = None
        user_model = None
        username = user.get("username") if isinstance(user, dict) else None
        if username:
            try:
                api_key, user_model = get_user_api_key_model(str(username))
            except Exception as e:
                handler.send_json(500, {"error": "db_error", "details": str(e)})
                return True

        if text_model:
            model = text_model
        elif user_model:
            model = user_model
        else:
            model = "kimi-2.5"
        normalized_model = _normalize_kimi_cli_model(model)
        is_qwen = _is_qwen_model(normalized_model)

        try:
            fps = float(fps_raw)
            if fps != fps or fps <= 0:
                fps = 3.0
        except Exception:
            fps = 3.0

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

        image_count = 1
        if not is_qwen:
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

        ui_lang_raw = handler.headers.get("X-UI-Lang", "") or data.get("ui_lang", "") or ""
        ui_lang = str(ui_lang_raw).strip().lower()
        prompt_path = os.path.join("data", "ch_prompt.md")
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

        # 归属解析：优先请求显式携带，其次视频登记信息，最后默认项目
        project_id = data.get("project_id") or None
        line_id = data.get("line_id") or None
        video_id = None
        try:
            vrow = get_video_by_path(video_path)
            if vrow:
                video_id = vrow.get("id")
                project_id = project_id or vrow.get("project_id")
                line_id = line_id or vrow.get("line_id")
        except Exception:
            logger.warning("查询视频归属失败: path=%s", video_path, exc_info=True)
        if not project_id:
            try:
                scope = ensure_default_scope()
                project_id = scope["project_id"]
                line_id = line_id or scope["line_id"]
            except Exception:
                logger.warning("默认项目解析失败", exc_info=True)

        # SOP 注入：产线级 SOP 优先（按 line_id），无则回退全局 data/SOP.md
        sop_content = ""
        line_sop = None
        if line_id:
            try:
                line_sop = get_line_sop(int(line_id))
            except Exception:
                logger.warning("读取产线 SOP 失败: line_id=%s", line_id, exc_info=True)
        if line_sop is not None and str(line_sop).strip():
            sop_content = str(line_sop)
        elif os.path.exists(sop_path):
            try:
                with open(sop_path, "r", encoding="utf-8") as f:
                    sop_content = f.read()
            except Exception:
                sop_content = ""

        # 重复提交检查（先于任务落库，避免 409 时留下孤儿任务行）
        with USER_TASKS_LOCK:
            if username in USER_TASKS and USER_TASKS[username]["status"] == "running":
                handler.send_json(409, {"error": "task_already_running", "details": "当前已有正在进行的任务，请等待其完成"})
                return True

        # 任务持久化：DB 为权威状态源
        task_id = None
        try:
            task_id = create_task(
                username=str(username or ""),
                model=normalized_model,
                video_id=int(video_id) if video_id else None,
                project_id=int(project_id) if project_id else None,
                line_id=int(line_id) if line_id else None,
                progress_total=image_count,
                progress_unit=("request" if is_qwen else "frame"),
            )
        except Exception as e:
            handler.send_json(500, {"error": "task_create_failed", "details": str(e)})
            return True

        try:
            with USER_TASKS_LOCK:
                USER_TASKS[username] = {
                    "status": "running",
                    "logs": [],
                    "result": None,
                    "error_msg": None,
                    "created_at": time.time(),
                    "phase": "analyze",
                    "progress": {"current": 0, "total": image_count},
                    "kind": "analyze",
                    "model": normalized_model,
                    "progress_unit": ("request" if is_qwen else "frame"),
                    "prompt_path": prompt_path,
                    "ui_lang": ui_lang,
                    "task_id": task_id,
                    "project_id": int(project_id) if project_id else None,
                    "line_id": int(line_id) if line_id else None,
                    "video_id": int(video_id) if video_id else None,
                }
            t = threading.Thread(
                target=background_analyze_task,
                args=(username, video_path, normalized_model, fps, api_key, prompt_path, sop_content, timestamp, ui_lang),
                daemon=True,
            )
            t.start()
            handler.send_json(
                200,
                {
                    "status": "started",
                    "message": "任务已在后台启动",
                    "video_path": output_video_path,
                    "prompt_path": prompt_path,
                    "resolved_model": normalized_model,
                    "ui_lang": ui_lang,
                },
            )
            started = True
        except Exception as e:
            handler.send_json(500, {"error": "internal_error", "details": str(e)})
            return True
        return True
    finally:
        if not started:
            ANALYZE_SEMAPHORE.release()
