import json
import os
import shutil
import subprocess
import urllib.parse
from typing import Dict, List, Optional

from backend.app_config import ALLOWED_UPLOAD_EXTS, MAX_UPLOAD_BYTES
from backend.app_db_org import (
    can_manage_project,
    clear_all_content,
    delete_video,
    ensure_default_scope,
    get_station,
    get_video,
    list_videos_for_user,
    register_video,
)
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


TARGET_VIDEO_BYTES = 100 * 1024 * 1024
MAX_VIDEO_SECONDS = 180
MAX_VIDEO_HEIGHT = 720


def _probe_video(video_path: str) -> Dict[str, object]:
    """返回视频基础信息（时长/宽高/编码），探测失败返回空字典。"""
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type,codec_name,width,height:format=duration",
                "-of",
                "json",
                video_path,
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return {}
        payload = json.loads(proc.stdout or "{}")
    except Exception:
        return {}
    info: Dict[str, object] = {}
    for stream in payload.get("streams") or []:
        codec_type = str(stream.get("codec_type") or "")
        if codec_type == "video" and "width" not in info:
            info["width"] = int(stream.get("width") or 0)
            info["height"] = int(stream.get("height") or 0)
            info["video_codec"] = str(stream.get("codec_name") or "")
        elif codec_type == "audio" and "audio_codec" not in info:
            info["audio_codec"] = str(stream.get("codec_name") or "")
    duration = (payload.get("format") or {}).get("duration")
    if duration:
        try:
            info["duration"] = float(duration)
        except Exception:
            pass
    return info


def normalize_video(
    video_path: str,
    max_seconds: int = MAX_VIDEO_SECONDS,
    max_height: int = MAX_VIDEO_HEIGHT,
    target_bytes: int = TARGET_VIDEO_BYTES,
) -> bool:
    """统一转码一次：≤180s、高度≤720p、H.264/AAC、faststart，目标 ≤100MB。

    已是合规视频时直接返回；转码失败返回 False（保留原文件）。
    """
    info = _probe_video(video_path)
    try:
        size = os.path.getsize(video_path)
    except Exception:
        return False
    duration = info.get("duration")
    height = int(info.get("height") or 0)
    need_trim = isinstance(duration, (int, float)) and float(duration) > float(max_seconds)
    need_scale = height > max_height
    need_codec = str(info.get("video_codec") or "").lower() not in ("", "h264")
    need_audio = str(info.get("audio_codec") or "").lower() not in ("", "aac")
    need_size = size > target_bytes
    if not (need_trim or need_scale or need_codec or need_audio or need_size):
        return True

    base, ext = os.path.splitext(video_path)
    temp_path = f"{base}_norm{ext or '.mp4'}"
    crf_values = [26, 30] if need_size else [23]
    for attempt, crf in enumerate(crf_values):
        cmd = ["ffmpeg", "-y", "-i", video_path, "-t", str(max_seconds)]
        if need_scale:
            cmd.extend(["-vf", f"scale=-2:{max_height}"])
        cmd.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                str(crf),
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                temp_path,
            ]
        )
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 or not os.path.exists(temp_path) or os.path.getsize(temp_path) <= 0:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            continue
        os.replace(temp_path, video_path)
        final_info = _probe_video(video_path)
        final_size = os.path.getsize(video_path)
        final_duration = final_info.get("duration")
        final_height = int(final_info.get("height") or 0)
        if isinstance(final_duration, (int, float)) and float(final_duration) > max_seconds + 1:
            logger.warning("视频标准化后仍超过 %ss: path=%s", max_seconds, video_path)
        if final_height > max_height:
            logger.warning("视频标准化后高度仍超过 %sp: path=%s", max_height, video_path)
        if final_size > target_bytes:
            logger.warning(
                "视频标准化后体积仍超过目标: path=%s, size=%d, target=%d",
                video_path,
                final_size,
                target_bytes,
            )
            if attempt + 1 < len(crf_values):
                continue
        else:
            logger.info("视频标准化完成: path=%s, size=%d", video_path, final_size)
        return True
    logger.warning("视频标准化失败: path=%s", video_path)
    return False


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
        if not normalize_video(save_path):
            logger.warning("上传后视频标准化失败: path=%s", save_path)
            handler.send_json(500, {"error": "normalize_failed"})
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

        if not normalize_video(video_path):
            handler.send_json(500, {"error": "normalize_failed"})
            return True

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


def _clear_uploaded_videos(target_dir: str) -> tuple:
    """删除 data/ 下的视频文件与同名抽帧目录，保留数据库与其他文件。

    返回 (视频数, 抽帧目录数, 释放字节数)。
    """
    deleted_files = 0
    deleted_dirs = 0
    freed_bytes = 0
    video_bases: List[str] = []
    if not os.path.isdir(target_dir):
        return deleted_files, deleted_dirs, freed_bytes
    for name in os.listdir(target_dir):
        path = os.path.join(target_dir, name)
        if not (os.path.isfile(path) and name.lower().endswith(_VIDEO_EXTS)):
            continue
        try:
            freed_bytes += os.path.getsize(path)
            os.remove(path)
            deleted_files += 1
            video_bases.append(os.path.splitext(name)[0])
        except OSError:
            logger.warning("删除视频文件失败: path=%s", path, exc_info=True)
    for base_name in video_bases:
        frames_dir = os.path.join(target_dir, base_name)
        if not os.path.isdir(frames_dir):
            continue
        for dirpath, _, filenames in os.walk(frames_dir):
            for fname in filenames:
                try:
                    freed_bytes += os.path.getsize(os.path.join(dirpath, fname))
                except OSError:
                    pass
        shutil.rmtree(frames_dir, ignore_errors=True)
        deleted_dirs += 1
    return deleted_files, deleted_dirs, freed_bytes


def _clear_directory_contents(target_dir: str) -> tuple:
    """删除目录下的全部内容（保留目录本身），返回 (文件数, 子目录数, 释放字节数)。"""
    deleted_files = 0
    deleted_dirs = 0
    freed_bytes = 0
    if not os.path.isdir(target_dir):
        return deleted_files, deleted_dirs, freed_bytes
    for name in os.listdir(target_dir):
        path = os.path.join(target_dir, name)
        try:
            if os.path.isdir(path):
                for dirpath, _, filenames in os.walk(path):
                    for fname in filenames:
                        try:
                            freed_bytes += os.path.getsize(os.path.join(dirpath, fname))
                        except OSError:
                            pass
                shutil.rmtree(path, ignore_errors=True)
                deleted_dirs += 1
            else:
                freed_bytes += os.path.getsize(path)
                os.remove(path)
                deleted_files += 1
        except OSError:
            logger.warning("清理目录内容失败: path=%s", path, exc_info=True)
    return deleted_files, deleted_dirs, freed_bytes


def handle_clear_all_content(handler, user: Optional[Dict[str, object]] = None) -> bool:
    """一键清空所有内容：上传视频、抽帧缓存、检测结果文件与相关数据表记录。

    仅管理员可调用；项目/产线/工位/用户等配置数据不受影响。
    """
    try:
        role = str((user or {}).get("role") or "")
        if role != "admin":
            handler.send_json(403, {"error": "forbidden", "details": "仅管理员可清空内容"})
            return True

        video_files, frame_dirs, video_bytes = _clear_uploaded_videos("data")
        result_files, result_dirs, result_bytes = _clear_directory_contents("result")

        table_counts: Dict[str, int] = {}
        try:
            table_counts = clear_all_content()
        except Exception:
            logger.warning("清空内容数据表失败", exc_info=True)

        logger.info(
            "已清空所有内容: videos=%d, frames=%d, results=%d, tables=%s, freed_bytes=%d",
            video_files,
            frame_dirs,
            result_files + result_dirs,
            table_counts,
            video_bytes + result_bytes,
        )
        handler.send_json(
            200,
            {
                "status": "success",
                "deleted_videos": video_files,
                "deleted_frame_dirs": frame_dirs,
                "deleted_result_files": result_files,
                "deleted_result_dirs": result_dirs,
                "deleted_records": table_counts,
                "freed_bytes": video_bytes + result_bytes,
            },
        )
        return True
    except Exception as e:
        logger.exception("清空内容处理异常")
        handler.send_json(500, {"error": "clear_content_failed", "details": str(e)})
        return True


_BROWSER_CONTAINER_EXTS = (".mp4", ".webm")


def _playable_path(stored_path: str) -> Optional[str]:
    """返回浏览器可直接播放的文件路径，必要时转封装为 mp4（带缓存）。

    Chrome 不支持 QuickTime 容器（.mov / major_brand=qt），需用 ffmpeg
    无损转封装为 H.264/AAC 的 MP4；失败时回退重编码。
    """
    if not stored_path or not os.path.isfile(stored_path):
        return None
    base, ext = os.path.splitext(stored_path)
    if ext.lower() in _BROWSER_CONTAINER_EXTS:
        return stored_path
    play_path = f"{base}_play.mp4"
    if os.path.isfile(play_path) and os.path.getsize(play_path) > 0:
        return play_path
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        stored_path,
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        play_path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not os.path.isfile(play_path) or os.path.getsize(play_path) <= 0:
        if os.path.exists(play_path):
            os.remove(play_path)
        reencode = [
            "ffmpeg",
            "-y",
            "-i",
            stored_path,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "26",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            play_path,
        ]
        res = subprocess.run(reencode, capture_output=True, text=True)
        if res.returncode != 0 or not os.path.isfile(play_path) or os.path.getsize(play_path) <= 0:
            if os.path.exists(play_path):
                os.remove(play_path)
            logger.warning("视频转封装失败: path=%s", stored_path)
            return None
    logger.info("视频已转封装为可播放格式: src=%s, out=%s", stored_path, play_path)
    return play_path


def handle_ensure_playable(handler, user: Optional[Dict[str, object]] = None) -> bool:
    """返回视频的可播放地址（必要时在服务端转封装为 mp4）。"""
    try:
        payload: Dict[str, object] = {}
        try:
            length = int(handler.headers.get("Content-Length") or 0)
            if length > 0:
                raw = handler.rfile.read(length)
                payload = json.loads(raw or b"{}")
        except Exception:
            payload = {}
        try:
            video_id = int(payload.get("video_id") or payload.get("id") or 0)
        except Exception:
            video_id = 0
        if not video_id:
            handler.send_json(400, {"error": "missing_video_id"})
            return True
        video = get_video(video_id)
        if not video:
            handler.send_json(404, {"error": "video_not_found"})
            return True
        stored_path = str(video.get("stored_path") or "").strip()
        playable = _playable_path(stored_path)
        if not playable:
            handler.send_json(404, {"error": "video_file_not_found"})
            return True
        handler.send_json(
            200,
            {
                "status": "success",
                "video_id": video_id,
                "path": playable.replace(os.sep, "/"),
                "converted": os.path.normpath(playable) != os.path.normpath(stored_path),
            },
        )
        return True
    except Exception as e:
        logger.exception("获取可播放视频失败")
        handler.send_json(500, {"error": "ensure_playable_failed", "details": str(e)})
        return True


def handle_delete_video(handler, user: Optional[Dict[str, object]] = None) -> bool:
    """删除单个视频：磁盘文件、抽帧目录与 videos 表记录。"""
    try:
        payload: Dict[str, object] = {}
        try:
            length = int(handler.headers.get("Content-Length") or 0)
            if length > 0:
                raw = handler.rfile.read(length)
                payload = json.loads(raw or b"{}")
        except Exception:
            payload = {}
        try:
            video_id = int(payload.get("video_id") or payload.get("id") or 0)
        except Exception:
            video_id = 0
        if not video_id:
            handler.send_json(400, {"error": "missing_video_id"})
            return True
        video = get_video(video_id)
        if not video:
            handler.send_json(404, {"error": "video_not_found"})
            return True
        try:
            project_id = int(video.get("project_id") or 0)
        except Exception:
            project_id = 0
        if not can_manage_project(user or {}, project_id):
            handler.send_json(403, {"error": "forbidden", "details": "仅管理员或项目 owner 可删除视频"})
            return True

        stored_path = str(video.get("stored_path") or "").strip()
        deleted_file = False
        if stored_path and os.path.isfile(stored_path):
            try:
                os.remove(stored_path)
                deleted_file = True
            except OSError:
                logger.warning("删除视频文件失败: path=%s", stored_path, exc_info=True)
        if stored_path:
            play_path = f"{os.path.splitext(stored_path)[0]}_play.mp4"
            if os.path.isfile(play_path):
                try:
                    os.remove(play_path)
                except OSError:
                    logger.warning("删除转封装文件失败: path=%s", play_path, exc_info=True)
            frames_dir = os.path.join(
                os.path.dirname(stored_path) or "data",
                os.path.splitext(os.path.basename(stored_path))[0],
            )
            if os.path.isdir(frames_dir):
                shutil.rmtree(frames_dir, ignore_errors=True)

        delete_video(video_id)
        logger.info(
            "已删除视频: id=%s, filename=%s, file=%s",
            video_id,
            video.get("filename"),
            deleted_file,
        )
        handler.send_json(
            200,
            {
                "status": "success",
                "video_id": video_id,
                "filename": video.get("filename"),
                "deleted_file": deleted_file,
            },
        )
        return True
    except Exception as e:
        logger.exception("删除视频处理异常")
        handler.send_json(500, {"error": "delete_video_failed", "details": str(e)})
        return True
