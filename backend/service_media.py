import json
import os
import shutil
import subprocess
import urllib.parse
from typing import Dict, List, Optional

from backend.app_config import ALLOWED_UPLOAD_EXTS, MAX_UPLOAD_BYTES
from backend.app_db_org import ensure_default_scope, get_station, list_videos_for_user, register_video
from backend.app_logging import get_logger

logger = get_logger("media")

_VIDEO_EXTS = (".mp4", ".mov", ".avi", ".mkv", ".webm")


def _parse_int_param(params: Dict[str, List[str]], key: str) -> Optional[int]:
    raw = (params.get(key) or [""])[0]
    return int(raw) if str(raw).strip().lstrip("-").isdigit() else None


def _resolve_scope(parsed_path=None) -> Dict[str, Optional[int]]:
    """解析上传归属：query 携带 project_id/line_id/station_id 时用之，否则默认项目。"""
    project_id = None
    line_id = None
    station_id = None
    if parsed_path is not None:
        try:
            params = urllib.parse.parse_qs(parsed_path.query or "")
        except Exception:
            params = {}
        project_id = _parse_int_param(params, "project_id")
        line_id = _parse_int_param(params, "line_id")
        station_id = _parse_int_param(params, "station_id")
    if not project_id:
        scope = ensure_default_scope()
        return {
            "project_id": scope["project_id"],
            "line_id": line_id or scope["line_id"],
            "station_id": station_id,
        }
    return {"project_id": project_id, "line_id": line_id, "station_id": station_id}


def ensure_720p(video_path: str) -> None:
    try:
        cmd_probe = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=s=x:p=0",
            video_path,
        ]
        proc = subprocess.run(cmd_probe, capture_output=True, text=True)
        if proc.returncode != 0:
            return
        out = (proc.stdout or "").strip()
        parts = out.split("x")
        if len(parts) != 2:
            return
        w, h = int(parts[0]), int(parts[1])
        if min(w, h) <= 720:
            return
        scale_filter = "scale=-2:720" if w >= h else "scale=720:-2"
        dir_name = os.path.dirname(video_path)
        base_name = os.path.basename(video_path)
        name, ext = os.path.splitext(base_name)
        compressed_path = os.path.join(dir_name, f"{name}_720p{ext}")
        cmd_ffmpeg = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vf",
            scale_filter,
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-c:a",
            "copy",
            compressed_path,
        ]
        res = subprocess.run(cmd_ffmpeg, capture_output=True, text=True)
        if res.returncode == 0:
            os.replace(compressed_path, video_path)
        else:
            if os.path.exists(compressed_path):
                os.remove(compressed_path)
    except Exception:
        return


def _get_video_duration(video_path: str):
    duration = None
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_path,
        ],
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        out = (probe.stdout or "").strip()
        if out:
            try:
                duration = float(out)
            except Exception:
                duration = None
    if duration is None:
        try:
            import cv2  # type: ignore

            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 0
            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            cap.release()
            if fps > 0 and frames > 0:
                duration = float(frames) / float(fps)
        except Exception:
            duration = None
    return duration


def _trim_video_to_180(video_path: str) -> bool:
    duration = _get_video_duration(video_path)
    if duration is not None and duration <= 180:
        return True
    base, ext = os.path.splitext(video_path)
    trimmed_path = f"{base}_trim180{ext or '.mp4'}"
    trim = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-t",
            "180",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            trimmed_path,
        ],
        capture_output=True,
        text=True,
    )
    if trim.returncode == 0 and os.path.exists(trimmed_path):
        os.replace(trimmed_path, video_path)
        return True
    if os.path.exists(trimmed_path):
        os.remove(trimmed_path)
    return False


def handle_upload(handler, user: Optional[Dict[str, object]] = None, parsed_path=None) -> bool:
    try:
        filename = handler.headers.get("X-Filename")
        if filename:
            filename = urllib.parse.unquote(filename)
        if not filename:
            handler.send_json(400, {"error": "missing_x_filename_header"})
            return True
        filename = os.path.basename(filename)
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_UPLOAD_EXTS:
            logger.warning("上传被拒绝（类型不允许）: filename=%s", filename)
            handler.send_json(400, {"error": "invalid_file_type", "allowed_exts": sorted(ALLOWED_UPLOAD_EXTS)})
            return True
        content_length_header = handler.headers.get("Content-Length")
        if not content_length_header:
            handler.send_json(400, {"error": "missing_content_length"})
            return True
        content_length = int(content_length_header)
        if content_length <= 0:
            handler.send_json(400, {"error": "empty_body"})
            return True
        if content_length > MAX_UPLOAD_BYTES:
            logger.warning(
                "上传被拒绝（超过大小限制）: filename=%s, size=%d, limit=%d",
                filename,
                content_length,
                MAX_UPLOAD_BYTES,
            )
            handler.send_json(413, {"error": "file_too_large", "max_mb": MAX_UPLOAD_BYTES // (1024 * 1024)})
            return True
        # 先校验工位归属，避免非法绑定落盘产生孤儿文件
        scope = _resolve_scope(parsed_path)
        station_id = scope.get("station_id")
        if station_id:
            station = get_station(int(station_id))
            if not station or (
                scope.get("line_id")
                and int(station.get("line_id") or 0) != int(scope["line_id"])
            ):
                handler.send_json(
                    400,
                    {"error": "invalid_station", "details": "所选工位不属于当前产线"},
                )
                return True
        save_path = os.path.join("data", filename)
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "wb") as f:
            bytes_read = 0
            while bytes_read < content_length:
                chunk_size = min(65536, content_length - bytes_read)
                chunk = handler.rfile.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                bytes_read += len(chunk)
        if not _trim_video_to_180(save_path):
            logger.warning("上传后裁剪失败: path=%s", save_path)
            handler.send_json(500, {"error": "trim_failed"})
            return True
        # 视频资产登记入库（幂等：同名覆盖上传时更新元数据）
        try:
            register_video(
                project_id=int(scope["project_id"]),
                filename=filename,
                stored_path=save_path,
                line_id=int(scope["line_id"]) if scope.get("line_id") else None,
                duration_sec=_get_video_duration(save_path),
                size_bytes=os.path.getsize(save_path) if os.path.exists(save_path) else None,
                uploaded_by=str((user or {}).get("username") or "") or None,
                station_id=int(station_id) if station_id else None,
            )
        except Exception:
            logger.warning("视频登记入库失败: path=%s", save_path, exc_info=True)
        logger.info("上传成功: filename=%s, size=%d", filename, bytes_read)
        handler.send_json(200, {"status": "success", "path": save_path})
        return True
    except Exception as e:
        logger.exception("上传处理异常")
        handler.send_json(500, {"error": "upload_failed", "details": str(e)})
        return True


def handle_extract_frames(handler, user: dict) -> bool:
    try:
        content_length = int(handler.headers.get("Content-Length", "0") or "0")
        post_data = handler.rfile.read(content_length)
        try:
            data = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            data = {}
        video_path = str(data.get("video_path") or "").strip()
        fps = 3.0
        if not video_path:
            handler.send_json(400, {"error": "missing_video_path"})
            return True
        if not video_path.startswith("data/"):
            video_path = os.path.join("data", os.path.basename(video_path))
        if not os.path.exists(video_path):
            handler.send_json(404, {"error": "video_not_found", "path": video_path})
            return True

        if not _trim_video_to_180(video_path):
            handler.send_json(500, {"error": "trim_failed"})
            return True

        ensure_720p(video_path)

        try:
            import cv2  # type: ignore
        except Exception:
            handler.send_json(500, {"error": "missing_opencv"})
            return True
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            handler.send_json(500, {"error": "open_video_failed", "path": video_path})
            return True
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        if video_fps <= 0:
            video_fps = fps
        max_seconds = 180.0
        step = max(1, int(round(video_fps / fps)))
        base_name = os.path.splitext(os.path.basename(video_path))[0] or "frames"
        out_dir = os.path.join("data", base_name)
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(out_dir, exist_ok=True)
        frame_index = 0
        saved = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if video_fps > 0 and (frame_index / video_fps) >= max_seconds:
                break
            if frame_index % step == 0:
                h, w = frame.shape[:2]
                new_w = max(1, w // 2)
                new_h = max(1, h // 2)
                resized = cv2.resize(frame, (new_w, new_h))
                t = frame_index / video_fps if video_fps > 0 else 0.0
                name = f"frame_{saved + 1:05d}_{t:.2f}.jpg"
                cv2.imwrite(
                    os.path.join(out_dir, name),
                    resized,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 90],
                )
                saved += 1
            frame_index += 1
        cap.release()
        handler.send_json(
            200,
            {
                "status": "success",
                "video_path": video_path,
                "frames_dir": out_dir,
                "frame_count": saved,
                "fps_used": fps,
                "video_fps": video_fps,
                "frame_step": step,
            },
        )
        return True
    except Exception as e:
        handler.send_json(500, {"error": "internal_error", "details": str(e)})
        return True


def handle_list_videos(handler, user: Optional[Dict[str, object]] = None, parsed_path=None) -> bool:
    """视频列表：优先走 videos 表（按用户可见项目过滤），DB 无记录时回退目录扫描。

    query 支持 project_id / line_id 进一步过滤（作用域选择器传参）。
    """
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
                rows = list_videos_for_user(username, role, project_id, line_id)
            except Exception:
                logger.warning("视频列表查库失败，回退目录扫描", exc_info=True)
                rows = []
        files: List[str] = []
        for r in rows:
            filename = str(r.get("filename") or "")
            if not filename:
                continue
            if os.path.exists(os.path.join("data", filename)):
                files.append(filename)
        if files:
            handler.send_json(200, {"files": files})
            return True
        legacy: List[str] = []
        if os.path.exists("data"):
            legacy = [f for f in os.listdir("data") if f.endswith(_VIDEO_EXTS)]
        if legacy:
            logger.warning("videos 表为空，视频列表回退目录扫描；建议运行 scripts/migrate_phase1.py")
        handler.send_json(200, {"files": legacy})
        return True
    except Exception as e:
        handler.send_json(500, {"error": str(e)})
        return True


def handle_video_info(handler, parsed_path) -> bool:
    try:
        params = urllib.parse.parse_qs(parsed_path.query)
        rel_path = (params.get("path") or [""])[0]
        rel_path = rel_path.lstrip("/")
        rel_path = os.path.normpath(rel_path)
        if not rel_path or rel_path.startswith("..") or rel_path.startswith("/"):
            handler.send_response(400)
            handler.send_header("Content-type", "application/json")
            handler.end_headers()
            handler.wfile.write(json.dumps({"error": "invalid path"}).encode("utf-8"))
            return True
        if not (rel_path.startswith("data/") or rel_path.startswith("result/")):
            handler.send_response(403)
            handler.send_header("Content-type", "application/json")
            handler.end_headers()
            handler.wfile.write(json.dumps({"error": "forbidden path"}).encode("utf-8"))
            return True
        abs_path = os.path.join(os.getcwd(), rel_path)
        if not (os.path.exists(abs_path) and os.path.isfile(abs_path)):
            handler.send_response(404)
            handler.send_header("Content-type", "application/json")
            handler.end_headers()
            handler.wfile.write(json.dumps({"error": "file not found"}).encode("utf-8"))
            return True
        duration = None
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                abs_path,
            ],
            capture_output=True,
            text=True,
        )
        if probe.returncode == 0:
            out = (probe.stdout or "").strip()
            if out:
                duration = float(out)
        if duration is None:
            try:
                import cv2  # type: ignore

                cap = cv2.VideoCapture(abs_path)
                fps = cap.get(cv2.CAP_PROP_FPS) or 0
                frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
                cap.release()
                if fps > 0 and frames > 0:
                    duration = float(frames) / float(fps)
            except Exception:
                duration = None
        if duration is None:
            handler.send_response(500)
            handler.send_header("Content-type", "application/json")
            handler.end_headers()
            handler.wfile.write(json.dumps({"error": "failed to read duration"}).encode("utf-8"))
            return True
        handler.send_response(200)
        handler.send_header("Content-type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"path": rel_path, "duration": duration}).encode("utf-8"))
        return True
    except Exception as e:
        handler.send_response(500)
        handler.send_header("Content-type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        return True
