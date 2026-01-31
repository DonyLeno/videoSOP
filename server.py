import http.server
import socketserver
import json
import os
import re
import datetime
import subprocess
import urllib.parse
from typing import Dict, List, Optional
import base64
import hashlib
import hmac
import secrets
import time
import threading

import sys
import mysql.connector
import random

# Global task state
USER_TASKS = {}
USER_TASKS_LOCK = threading.Lock()

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


def _extract_last_json_dict(text: str) -> Optional[Dict[str, object]]:
    idx = text.rfind("{")
    attempts = 0
    while idx != -1 and attempts < 20:
        candidate = text[idx:].strip()
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        attempts += 1
        idx = text.rfind("{", 0, idx)
    return None

def _extract_last_result_payload(text: str) -> Optional[Dict[str, object]]:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    for ln in reversed(lines[-500:]):
        if not (ln.startswith("{") and ln.endswith("}")):
            continue
        try:
            parsed = json.loads(ln)
        except Exception:
            continue
        if not isinstance(parsed, dict):
            continue
        if ("actions" in parsed) and ("model_output" in parsed or "computed_stats" in parsed):
            return parsed
    return None


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

def ensure_720p(video_path: str) -> None:
    """
    Checks if video resolution exceeds 720p (min dimension > 720).
    If so, compresses/resizes it to 720p in-place.
    """
    try:
        # 1. Probe resolution
        cmd_probe = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0",
            video_path
        ]
        # Use subprocess.run for safety
        proc = subprocess.run(cmd_probe, capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"[WARN] ensure_720p: probe failed for {video_path}")
            return
            
        out = proc.stdout.strip()
        parts = out.split('x')
        if len(parts) != 2:
            return
        w, h = int(parts[0]), int(parts[1])
        
        # 2. Check if resize needed (min dimension > 720)
        if min(w, h) <= 720:
            return
            
        print(f"[INFO] Video {video_path} is {w}x{h}, resizing to 720p...")
        
        # 3. Construct scale filter
        # If landscape (w >= h), scale height to 720 (scale=-2:720)
        # If portrait (h > w), scale width to 720 (scale=720:-2)
        # Note: -2 ensures even dimensions (required by some codecs)
        scale_filter = "scale=-2:720" if w >= h else "scale=720:-2"
        
        dir_name = os.path.dirname(video_path)
        base_name = os.path.basename(video_path)
        name, ext = os.path.splitext(base_name)
        compressed_path = os.path.join(dir_name, f"{name}_720p{ext}")
        
        cmd_ffmpeg = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", scale_filter,
            "-c:v", "libx264", 
            "-preset", "fast", 
            "-crf", "23",
            "-c:a", "copy",
            compressed_path
        ]
        
        # Run ffmpeg
        res = subprocess.run(cmd_ffmpeg, capture_output=True, text=True)
        if res.returncode == 0:
            # Replace original with compressed
            os.replace(compressed_path, video_path)
            print(f"[INFO] Successfully resized {video_path} to 720p")
        else:
            print(f"[ERR] ffmpeg failed: {res.stderr}")
            if os.path.exists(compressed_path):
                os.remove(compressed_path)
                
    except Exception as e:
        print(f"[ERR] ensure_720p exception: {e}")

def background_analyze_task(username, video_path, model, fps, api_key):
    task = USER_TASKS.get(username)
    if not task: return
    
    def log(msg):
        with USER_TASKS_LOCK:
            task['logs'].append(msg)
            
    try:
        os.makedirs("result", exist_ok=True)
        base_name = os.path.basename(video_path).rsplit('.', 1)[0]
        frames_dir = os.path.join('data', base_name)
        image_paths = _iter_image_files(frames_dir)
        total_images = len(image_paths)
        if total_images == 0:
            with USER_TASKS_LOCK:
                task['status'] = 'failed'
                task['error_msg'] = 'no_images_found'
            return
        if total_images > 1000:
            with USER_TASKS_LOCK:
                task['status'] = 'failed'
                task['error_msg'] = "超过模型保存文件上限（1000个）。请降低帧率或者分拆视频重新上传，保证视频时长*帧率 < 1000"
            return


        timestamp = datetime.datetime.now().strftime("%d.%H.%M.%S")
        json_filename = f"{base_name}_{timestamp}.json"
        json_path = os.path.join('result', json_filename)
        
        env = os.environ.copy()
        env.pop('GOOGLE_API_KEY', None)
        env.pop('GEMINI_API_KEY', None)
        env.pop('MOONSHOT_API_KEY', None)
        
        normalized_model = _normalize_kimi_cli_model(model)
        if normalized_model.startswith('kimi') or normalized_model.startswith('moonshot'):
            env['MOONSHOT_API_KEY'] = api_key
        else:
            env['GOOGLE_API_KEY'] = api_key

        python_exe = sys.executable
        
        cmd_main = [
            python_exe, 'main.py',
            video_path,
            '--model', normalized_model,
            '--out', json_path,
            '--fps', str(fps),
            '--frames-dir', frames_dir,
            '--prompt-json', os.path.join('result', 'motor_12.15.00.40.json'),
        ]
        output_video_filename = f"{base_name}_{timestamp}.mp4"
        output_video_path = os.path.join('result', output_video_filename)
        
        cmd_handle = [
            python_exe, 'prehandle/handle_video.py',
            video_path,
            '--out', output_video_path,
            '--json', json_path,
            '--no-gui',
            '--threshold', '0.5'
        ]
        
        _set_task_progress(username, "analyze", 0, 0)
        _append_task_log(username, f"[INFO] Starting analysis for {video_path}\n")
        
        proc_main = subprocess.Popen(
            cmd_main,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=env
        )
        proc_handle = subprocess.Popen(
            cmd_handle,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        analysis_stdout = ""
        analysis_stderr = ""
        annotation_stdout = ""
        annotation_stderr = ""
        annotation_actions_ready = False
        
        import select
        fds = [
            proc_main.stdout.fileno(), proc_main.stderr.fileno(),
            proc_handle.stdout.fileno(), proc_handle.stderr.fileno()
        ]
        
        while fds:
            ready, _, _ = select.select(fds, [], [])
            for fd in ready:
                if fd == proc_main.stdout.fileno():
                    line = proc_main.stdout.readline()
                    if line:
                        analysis_stdout += line
                        log(f"[ANALYSIS]{line}".encode('utf-8'))
                        # Try to parse progress from JSON lines
                        try:
                            # line might be just a partial chunk, but readline() should give us a line
                            # Check if line looks like a JSON object
                            stripped = line.strip()
                            if stripped.startswith('{') and stripped.endswith('}'):
                                evt = json.loads(stripped)
                                if isinstance(evt, dict):
                                    evt_type = evt.get("event")
                                    if evt_type == "moonshot.chat_completions.request.batch":
                                        # When request is sent, show 1/3 progress for this batch
                                        current_batch_start = evt.get("batch_start", 0)
                                        batch_count = evt.get("batch_frame_count", 0)
                                        processed = current_batch_start + int(batch_count / 3)
                                        _set_task_progress(username, "analyze", processed, total_images)
                                    elif evt_type == "moonshot.chat_completions.content.batch":
                                        # When content is received, show full progress for this batch
                                        current_batch_start = evt.get("batch_start", 0)
                                        batch_count = evt.get("batch_frame_count", 0)
                                        processed = current_batch_start + batch_count
                                        _set_task_progress(username, "analyze", processed, total_images)
                                    elif evt_type == "kimi.files.cleared":
                                        count = evt.get("count", 0)
                                        log(f"[INFO] 已清理 Kimi 云端历史文件: {count} 个\n".encode('utf-8'))
                                    elif evt_type == "genai.files.upload.request":
                                        # Google Gemini upload
                                        pass
                        except Exception:
                            pass
                    else:
                        fds.remove(fd)
                elif fd == proc_main.stderr.fileno():
                    line = proc_main.stderr.readline()
                    if line:
                        analysis_stderr += line
                        log(f"[ANALYSIS_ERR]{line}".encode('utf-8'))
                    else:
                        fds.remove(fd)
                elif fd == proc_handle.stdout.fileno():
                    line = proc_handle.stdout.readline()
                    if line:
                        annotation_stdout += line
                        if "[ACTIONS_READY]" in line:
                            annotation_actions_ready = True
                        log(line.encode('utf-8'))
                    else:
                        fds.remove(fd)
                elif fd == proc_handle.stderr.fileno():
                    line = proc_handle.stderr.readline()
                    if line:
                        annotation_stderr += line
                        log(f"[ANNOTATION_ERR]{line}".encode('utf-8'))
                    else:
                        fds.remove(fd)
            
            if not fds or ((proc_main.poll() is not None) and (proc_handle.poll() is not None)):
                break
        
        status = 'success'
        error_details = None
        if (proc_main.returncode or 0) != 0 or (proc_handle.returncode or 0) != 0:
            status = 'partial'
            err_parts = []
            if (proc_main.returncode or 0) != 0:
                err_parts.append('Gemini analysis failed')
            if (proc_handle.returncode or 0) != 0:
                err_parts.append('Video annotation failed')
            error_details = '; '.join(err_parts)
        
        if (not annotation_actions_ready) and os.path.exists(json_path) and (proc_handle.returncode or 0) == 0:
            retry = subprocess.run(cmd_handle, capture_output=True, text=True)
            if retry.returncode == 0:
                annotation_stdout = retry.stdout or annotation_stdout
                annotation_stderr = retry.stderr or annotation_stderr
        
        response = {
            'status': status,
            'json_path': json_path,
            'video_path': output_video_path,
            'error': error_details,
            'logs': {
                'analysis': {
                    'command': ' '.join(cmd_main),
                    'stdout': analysis_stdout,
                    'stderr': analysis_stderr
                },
                'annotation': {
                    'command': ' '.join(cmd_handle),
                    'stdout': annotation_stdout,
                    'stderr': annotation_stderr
                }
            }
        }

        if not os.path.exists(json_path):
            recovered = _extract_last_result_payload(analysis_stdout)
            if recovered is not None:
                try:
                    os.makedirs(os.path.dirname(json_path) or ".", exist_ok=True)
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(recovered, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    with USER_TASKS_LOCK:
                        task['status'] = 'failed'
                        task['error_msg'] = f"result_json_write_failed: {e}"
                        task['phase'] = 'failed'
                    return
            else:
                with USER_TASKS_LOCK:
                    task['status'] = 'failed'
                    task['error_msg'] = "result_json_not_generated"
                    task['phase'] = 'failed'
                return

        if (proc_main.returncode or 0) != 0:
            with USER_TASKS_LOCK:
                task["result"] = response
                task["status"] = "failed"
                task["error_msg"] = error_details or "analysis_failed"
                task["phase"] = "failed"
            return
        
        with USER_TASKS_LOCK:
            task['result'] = response
            task['status'] = 'completed'
            task['phase'] = 'completed'
            
    except Exception as e:
        with USER_TASKS_LOCK:
            task['status'] = 'failed'
            task['error_msg'] = str(e)
            task['phase'] = 'failed'
            task['logs'].append(f"\nERROR:{str(e)}\n")
    finally:
        ANALYZE_SEMAPHORE.release()

PORT = int(os.environ.get('PORT', '8000'))

import mimetypes
import shutil

mimetypes.init()
mimetypes.add_type('video/mp4', '.mp4')

# Load .env file if exists
ENV_FILE = '.env'
if os.path.exists(ENV_FILE):
    with open(ENV_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
MYSQL_PORT = int(os.environ.get('MYSQL_PORT', '3306'))
MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '123456')
MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'geniview')
MYSQL_CONNECT_TIMEOUT = int(os.environ.get('MYSQL_CONNECT_TIMEOUT', '5'))
TOKEN_TTL_SECONDS = int(os.environ.get('TOKEN_TTL_SECONDS', str(8 * 60 * 60)))
TOKENS: Dict[str, Dict[str, object]] = {}
ANALYZE_CONCURRENCY = int(os.environ.get("ANALYZE_CONCURRENCY", "1") or "1")
if ANALYZE_CONCURRENCY < 1:
    ANALYZE_CONCURRENCY = 1
ANALYZE_SEMAPHORE = threading.Semaphore(ANALYZE_CONCURRENCY)

def pick_python_executable() -> str:
    env = os.environ.get("VIRTUAL_ENV")
    candidates: List[str] = []
    if env:
        candidates.extend(
            [
                os.path.join(env, "bin", "python3"),
                os.path.join(env, "bin", "python"),
            ]
        )
    root = os.getcwd()
    candidates.extend(
        [
            os.path.join(root, ".venv", "bin", "python3"),
            os.path.join(root, ".venv", "bin", "python"),
            os.path.join(root, "venv", "bin", "python3"),
            os.path.join(root, "venv", "bin", "python"),
        ]
    )
    for path in candidates:
        if path and os.path.exists(path) and os.path.isfile(path):
            return path
    return sys.executable

def get_db_connection(use_database: bool = True):
    config = {
        "host": MYSQL_HOST,
        "port": MYSQL_PORT,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "autocommit": True,
        "connection_timeout": MYSQL_CONNECT_TIMEOUT,
    }
    if use_database:
        config["database"] = MYSQL_DATABASE
    return mysql.connector.connect(**config)

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return f"{base64.b64encode(salt).decode('utf-8')}:{base64.b64encode(digest).decode('utf-8')}"

def verify_password(password: str, stored: str) -> bool:
    if ":" not in stored:
        return False
    salt_b64, digest_b64 = stored.split(":", 1)
    try:
        salt = base64.b64decode(salt_b64.encode("utf-8"))
        expected = base64.b64decode(digest_b64.encode("utf-8"))
    except Exception:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return hmac.compare_digest(digest, expected)

def ensure_database() -> None:
    conn = get_db_connection(use_database=False)
    cursor = conn.cursor()
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cursor.close()
    conn.close()

    conn = get_db_connection(use_database=True)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(64) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(32) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    cursor.execute(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME='users'",
        (MYSQL_DATABASE,),
    )
    existing_cols = {row[0] for row in cursor.fetchall()}
    if "email" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN email VARCHAR(255) DEFAULT NULL")
    if "status" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT 'active'")
    if "data_usage" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN data_usage BIGINT NOT NULL DEFAULT 0")
    if "api_key" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN api_key VARCHAR(255) DEFAULT NULL")
    if "model" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN model VARCHAR(64) DEFAULT NULL")
    cursor.execute("SELECT username FROM users WHERE username IN (%s, %s)", ("admin", "user1"))
    existing = {row[0] for row in cursor.fetchall()}
    seeds = [
        ("admin", "geniviewa", "admin", "admin@example.com"),
        ("user1", "userpass1", "user", "user1@example.com"),
    ]
    for username, password, role, email in seeds:
        if username in existing:
            continue
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, email, status) VALUES (%s, %s, %s, %s, %s)",
            (username, hash_password(password), role, email, "active"),
        )
    cursor.close()
    conn.close()

def create_token(username: str, role: str) -> str:
    token = secrets.token_urlsafe(32)
    TOKENS[token] = {
        "username": username,
        "role": role,
        "expires_at": time.time() + TOKEN_TTL_SECONDS,
    }
    return token

def get_token_info(token: str) -> Optional[Dict[str, object]]:
    info = TOKENS.get(token)
    if not info:
        return None
    expires_at = info.get("expires_at")
    if isinstance(expires_at, (int, float)) and expires_at < time.time():
        TOKENS.pop(token, None)
        return None
    return info

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def send_json(self, status: int, payload: Dict[str, object]) -> None:
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))

    def get_auth_user(self) -> Optional[Dict[str, object]]:
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth.split(" ", 1)[1].strip()
        if not token:
            return None
        return get_token_info(token)

    def require_auth(self) -> Optional[Dict[str, object]]:
        user = self.get_auth_user()
        if not user:
            self.send_json(401, {"error": "unauthorized"})
            return None
        return user
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Filename, Range')
        self.send_header('Access-Control-Expose-Headers', 'Content-Range, Accept-Ranges, Content-Length')
        
        request_path = getattr(self, "path", None)
        if request_path:
            parsed_path = urllib.parse.urlparse(request_path)
            clean_path = os.path.normpath(parsed_path.path)
            if clean_path == '/web/index.html' or clean_path.startswith('/web/'):
                self.send_header('Cache-Control', 'no-store')
        return super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_HEAD(self):
        parsed_path = urllib.parse.urlparse(self.path)
        clean_path = os.path.normpath(parsed_path.path)
        if clean_path.startswith('/..'):
            self.send_response(403)
            self.end_headers()
            return

        if clean_path.startswith('/data/') or clean_path.startswith('/result/'):
            real_path = os.path.join(os.getcwd(), clean_path.lstrip('/'))
            if not (os.path.exists(real_path) and os.path.isfile(real_path)):
                self.send_error(404, "File not found")
                return

            try:
                f = open(real_path, 'rb')
            except OSError:
                self.send_error(404, "File not found")
                return

            try:
                fs = os.fstat(f.fileno())
                size = fs.st_size
                ctype = self.guess_type(real_path)
                range_header = self.headers.get('Range')

                if range_header:
                    m = re.match(r'^bytes=(\d*)-(\d*)$', range_header.strip())
                    if not m:
                        self.send_response(416)
                        self.send_header("Content-Range", f"bytes */{size}")
                        self.end_headers()
                        return

                    start_str, end_str = m.group(1), m.group(2)
                    if start_str == "" and end_str == "":
                        self.send_response(416)
                        self.send_header("Content-Range", f"bytes */{size}")
                        self.end_headers()
                        return

                    if start_str == "":
                        suffix = int(end_str)
                        if suffix <= 0:
                            start, end = 0, size - 1
                        else:
                            start = max(size - suffix, 0)
                            end = size - 1
                    else:
                        start = int(start_str)
                        end = int(end_str) if end_str != "" else size - 1

                    if start >= size:
                        self.send_response(416)
                        self.send_header("Content-Range", f"bytes */{size}")
                        self.end_headers()
                        return

                    end = min(end, size - 1)
                    if end < start:
                        self.send_response(416)
                        self.send_header("Content-Range", f"bytes */{size}")
                        self.end_headers()
                        return

                    length = end - start + 1
                    self.send_response(206)
                    self.send_header("Content-type", ctype)
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                    self.send_header("Content-Length", str(length))
                    self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    return

                self.send_response(200)
                self.send_header("Content-type", ctype)
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Length", str(size))
                self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return
            finally:
                f.close()

        if self.path == '/' or self.path == '/index.html':
            self.path = '/web/index.html'
            return super().do_HEAD()

        if not clean_path.startswith('/web/'):
            if not os.path.exists('.' + clean_path):
                self.path = '/web' + clean_path

        return super().do_HEAD()

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)
        
        if parsed_path.path == '/api/login':
            content_length = int(self.headers.get('Content-Length', '0') or '0')
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8')) if post_data else {}
            except Exception:
                data = {}
            username = (data.get('username') or '').strip()
            password = data.get('password') or ''
            if not username or not password:
                self.send_json(400, {"error": "missing_credentials"})
                return
            try:
                conn = get_db_connection(use_database=True)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT username, password_hash, role FROM users WHERE username = %s",
                    (username,),
                )
                row = cursor.fetchone()
                cursor.close()
                conn.close()
            except Exception as e:
                self.send_json(500, {"error": "db_error", "details": str(e)})
                return
            if not row:
                self.send_json(401, {"error": "invalid_credentials"})
                return
            stored_hash = row[1]
            role = row[2]
            if not verify_password(password, stored_hash):
                self.send_json(401, {"error": "invalid_credentials"})
                return
            token = create_token(username, role)
            self.send_json(200, {"token": token, "user": {"username": username, "role": role}})
            return

        user = self.require_auth()
        if not user:
            return

        if parsed_path.path == '/api/users':
            if user.get("role") != "admin":
                self.send_json(403, {"error": "forbidden"})
                return
            content_length = int(self.headers.get('Content-Length', '0') or '0')
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8')) if post_data else {}
            except Exception:
                data = {}
            username = (data.get('username') or '').strip()
            password = data.get('password') or ''
            role = (data.get('role') or 'user').strip() or 'user'
            email = (data.get('email') or '').strip() or None
            status = (data.get('status') or 'active').strip() or 'active'
            api_key = (data.get('api_key') or '').strip() or None
            model = 'kimi-2.5'
            if not username or not password:
                self.send_json(400, {"error": "missing_username_or_password"})
                return
            if role not in ('admin', 'user'):
                self.send_json(400, {"error": "invalid_role"})
                return
            if status not in ('active', 'inactive'):
                self.send_json(400, {"error": "invalid_status"})
                return
            try:
                conn = get_db_connection(use_database=True)
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
                if cursor.fetchone():
                    cursor.close()
                    conn.close()
                    self.send_json(409, {"error": "username_exists"})
                    return
                cursor.execute(
                    "INSERT INTO users (username, password_hash, role, email, status, api_key, model) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (username, hash_password(password), role, email, status, api_key, model),
                )
                cursor.close()
                conn.close()
            except Exception as e:
                self.send_json(500, {"error": "db_error", "details": str(e)})
                return
            self.send_json(200, {"status": "success"})
            return

        if parsed_path.path == '/api/users/update':
            if user.get("role") != "admin":
                self.send_json(403, {"error": "forbidden"})
                return
            content_length = int(self.headers.get('Content-Length', '0') or '0')
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8')) if post_data else {}
            except Exception:
                data = {}
            username = (data.get('username') or '').strip()
            if not username:
                self.send_json(400, {"error": "missing_username"})
                return
            role = data.get('role')
            email = data.get('email')
            status = data.get('status')
            new_password = data.get('new_password')
            api_key = data.get('api_key')
            model = data.get('model')
            try:
                conn = get_db_connection(use_database=True)
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    conn.close()
                    self.send_json(404, {"error": "user_not_found"})
                    return
                sets = []
                params: List[object] = []
                if email is not None:
                    sets.append("email=%s")
                    params.append(email)
                if role is not None:
                    if role not in ('admin', 'user'):
                        self.send_json(400, {"error": "invalid_role"})
                        cursor.close()
                        conn.close()
                        return
                    sets.append("role=%s")
                    params.append(role)
                if status is not None:
                    if status not in ('active', 'inactive'):
                        self.send_json(400, {"error": "invalid_status"})
                        cursor.close()
                        conn.close()
                        return
                    sets.append("status=%s")
                    params.append(status)
                if api_key is not None:
                    normalized_key = str(api_key).strip()
                    sets.append("api_key=%s")
                    params.append(normalized_key or None)
                if model is not None:
                    sets.append("model=%s")
                    params.append("kimi-2.5")
                if new_password:
                    sets.append("password_hash=%s")
                    params.append(hash_password(new_password))
                if sets:
                    params.append(username)
                    cursor.execute(f"UPDATE users SET {', '.join(sets)} WHERE username=%s", tuple(params))
                cursor.close()
                conn.close()
            except Exception as e:
                self.send_json(500, {"error": "db_error", "details": str(e)})
                return
            self.send_json(200, {"status": "success"})
            return

        if parsed_path.path == '/api/update_result':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                json_path = data.get('json_path') or data.get('filename') or data.get('path')
                new_actions = data.get('actions')
                
                if not json_path or new_actions is None:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Missing json_path or actions'}).encode('utf-8'))
                    return
                
                # Normalize path
                if json_path.startswith('/'):
                    json_path = json_path[1:]
                
                real_path = os.path.join(os.getcwd(), json_path)
                if not os.path.exists(real_path):
                    self.send_response(404)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'File not found'}).encode('utf-8'))
                    return

                # Read existing file
                with open(real_path, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                
                # Helper to calculate stats
                def calculate_stats(actions):
                    total_actions = len(actions)
                    if total_actions == 0:
                        return {
                            "total_actions": 0,
                            "unique_action_type_count": 0,
                            "avg_action_duration": 0.0,
                            "action_types": []
                        }

                    by_label = {}
                    total_duration = 0.0

                    for act in actions:
                        label = act.get('label', 'Unknown')
                        try:
                            start = float(act.get('start_time', 0))
                            end = float(act.get('end_time', 0))
                            duration = max(0, end - start)
                        except:
                            duration = 0
                        
                        total_duration += duration
                        
                        if label not in by_label:
                            by_label[label] = {'count': 0, 'total_duration': 0.0}
                        
                        by_label[label]['count'] += 1
                        by_label[label]['total_duration'] += duration

                    avg_action_duration = total_duration / total_actions if total_actions > 0 else 0
                    
                    action_types = []
                    for label, data in by_label.items():
                        avg = data['total_duration'] / data['count'] if data['count'] > 0 else 0
                        action_types.append({
                            "label": label,
                            "count": data['count'],
                            "avg_duration": round(avg, 2)
                        })

                    # Sort by count desc
                    action_types.sort(key=lambda x: x['count'], reverse=True)

                    return {
                        "total_actions": total_actions,
                        "unique_action_type_count": len(by_label),
                        "avg_action_duration": round(avg_action_duration, 2),
                        "action_types": action_types
                    }

                # Update logic preserving structure
                new_stats = calculate_stats(new_actions)
                
                if isinstance(file_data, dict):
                    file_data['actions'] = new_actions
                    file_data['stats'] = new_stats

                    if 'model_output' in file_data and isinstance(file_data['model_output'], dict):
                        file_data['model_output']['actions'] = new_actions
                        file_data['model_output']['stats'] = new_stats

                    if 'output' in file_data and isinstance(file_data['output'], dict):
                        file_data['output']['actions'] = new_actions
                        file_data['output']['stats'] = new_stats

                    file_data['computed_stats'] = new_stats
                else:
                    # If file_data is just a list or something else, wrap it?
                    # Assuming standard dict structure based on existing code
                    pass

                # Write back
                with open(real_path, 'w', encoding='utf-8') as f:
                    json.dump(file_data, f, indent=2, ensure_ascii=False)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'success', 'json_path': json_path, 'stats': new_stats, 'data': file_data}).encode('utf-8'))

            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))

        elif parsed_path.path == '/api/upload':
            try:
                filename = self.headers.get('X-Filename')
                if not filename:
                    self.send_json(400, {"error": "missing_x_filename_header"})
                    return
                filename = os.path.basename(filename)
                content_length = int(self.headers['Content-Length'])
                save_path = os.path.join('data', filename)
                os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
                with open(save_path, 'wb') as f:
                    bytes_read = 0
                    while bytes_read < content_length:
                        chunk_size = min(65536, content_length - bytes_read)
                        chunk = self.rfile.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        bytes_read += len(chunk)
                
                # Compress/Resize if needed
                ensure_720p(save_path)

                self.send_json(200, {"status": "success", "path": save_path})
            except Exception as e:
                self.send_json(500, {"error": "upload_failed", "details": str(e)})
        elif parsed_path.path == '/api/extract_frames':
            user = self.require_auth()
            if not user:
                return
            try:
                content_length = int(self.headers.get('Content-Length', '0') or '0')
                post_data = self.rfile.read(content_length)
                try:
                    data = json.loads(post_data.decode('utf-8')) if post_data else {}
                except Exception:
                    data = {}
                video_path = str(data.get('video_path') or '').strip()
                fps_raw = data.get('fps', 1.0)
                try:
                    fps = float(fps_raw)
                    if fps <= 0:
                        fps = 1.0
                except Exception:
                    fps = 1.0
                if not video_path:
                    self.send_json(400, {"error": "missing_video_path"})
                    return
                if not video_path.startswith('data/'):
                    video_path = os.path.join('data', os.path.basename(video_path))
                if not os.path.exists(video_path):
                    self.send_json(404, {"error": "video_not_found", "path": video_path})
                    return
                try:
                    import cv2  # type: ignore
                except Exception:
                    self.send_json(500, {"error": "missing_opencv"})
                    return
                cap = cv2.VideoCapture(video_path)
                if not cap.isOpened():
                    self.send_json(500, {"error": "open_video_failed", "path": video_path})
                    return
                video_fps = cap.get(cv2.CAP_PROP_FPS)
                if video_fps <= 0:
                    video_fps = fps
                step = max(1, int(round(video_fps / fps)))
                base_name = os.path.splitext(os.path.basename(video_path))[0] or "frames"
                out_dir = os.path.join('data', base_name)
                # Clean up existing frames if re-processing
                if os.path.exists(out_dir):
                    import shutil
                    shutil.rmtree(out_dir)
                os.makedirs(out_dir, exist_ok=True)
                frame_index = 0
                saved = 0
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    if frame_index % step == 0:
                        h, w = frame.shape[:2]
                        new_w = max(1, w // 2)
                        new_h = max(1, h // 2)
                        resized = cv2.resize(frame, (new_w, new_h))
                        t = frame_index / video_fps if video_fps > 0 else 0.0
                        name = f"frame_{saved + 1:05d}_{t:.2f}.jpg"
                        cv2.imwrite(os.path.join(out_dir, name), resized, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
                        saved += 1
                    frame_index += 1
                cap.release()
                self.send_json(
                    200,
                    {
                        "status": "success",
                        "video_path": video_path,
                        "frames_dir": out_dir,
                        "frame_count": saved,
                    },
                )
            except Exception as e:
                self.send_json(500, {"error": "internal_error", "details": str(e)})
        elif parsed_path.path == '/api/analyze':
            acquired = ANALYZE_SEMAPHORE.acquire(blocking=False)
            if not acquired:
                self.send_json(429, {"error": "server_busy", "details": "服务器正在处理其他检测任务，请稍后重试"})
                return
            started = False
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                try:
                    data = json.loads(post_data.decode('utf-8'))
                except Exception:
                    data = {}
                
                video_path = data.get('video_path')
                raw_model = data.get('model')
                text_model = str(raw_model).strip() if raw_model is not None else ""
                model = 'kimi-2.5'
                
                fps_raw = data.get('fps', 1.0)
                api_key = None
                username = user.get("username") if isinstance(user, dict) else None
                if username:
                    try:
                        conn = get_db_connection(use_database=True)
                        cursor = conn.cursor()
                        cursor.execute("SELECT api_key FROM users WHERE username=%s", (username,))
                        row = cursor.fetchone()
                        cursor.close()
                        conn.close()
                        if row and row[0]:
                            api_key = str(row[0]).strip() or None
                    except Exception as e:
                        self.send_json(500, {"error": "db_error", "details": str(e)})
                        return

                try:
                    fps = float(fps_raw)
                    if fps != fps or fps < 0:
                        fps = 0.0
                except Exception:
                    fps = 0.0
                
                if not video_path:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Missing video_path'}).encode('utf-8'))
                    return
                if not api_key:
                    self.send_json(400, {"error": "missing_user_api_key", "details": "当前用户未配置 API Key"})
                    return

                base_name = os.path.basename(str(video_path)).rsplit('.', 1)[0]
                frames_dir = os.path.join('data', base_name)
                if not os.path.isdir(frames_dir):
                    self.send_json(400, {"error": "missing_frames_dir", "details": "请先上传视频并完成图片拆分后再开始检测"})
                    return
                image_count = len(_iter_image_files(frames_dir))
                if image_count == 0:
                    self.send_json(400, {"error": "missing_frames", "details": "未找到拆分后的图片，请先完成图片拆分"})
                    return
                if image_count > 1000:
                    self.send_json(400, {"error": "too_many_frames", "details": "超过模型保存文件上限（1000个）。请降低帧率或者分拆视频重新上传，保证视频时长*帧率 < 1000"})
                    return

                prompt_json_path = os.path.join('result', 'motor_12.15.00.40.json')
                if not os.path.exists(prompt_json_path):
                    self.send_json(500, {"error": "missing_prompt_template", "details": f"未找到 prompt 模板文件: {prompt_json_path}"})
                    return

                try:
                    # Check if task already running
                    with USER_TASKS_LOCK:
                        if username in USER_TASKS and USER_TASKS[username]['status'] == 'running':
                            self.send_json(409, {"error": "task_already_running", "details": "当前已有正在进行的任务，请等待其完成"})
                            return
                        
                        # Initialize new task
                        USER_TASKS[username] = {
                            'status': 'running',
                            'logs': [],
                            'result': None,
                            'error_msg': None,
                            'created_at': time.time(),
                            'phase': 'analyze',
                            'progress': {"current": 0, "total": image_count},
                            'kind': 'analyze',
                        }
                    
                    # Start background thread
                    t = threading.Thread(
                        target=background_analyze_task,
                        args=(username, video_path, model, fps, api_key),
                        daemon=True
                    )
                    t.start()
                    
                    self.send_json(200, {"status": "started", "message": "任务已在后台启动"})
                    started = True

                except Exception as e:
                    self.send_json(500, {"error": "internal_error", "details": str(e)})
                    return
            finally:
                if not started:
                    ANALYZE_SEMAPHORE.release()
            return


                
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        if parsed_path.path.startswith('/api/'):
            if parsed_path.path == '/api/me':
                user = self.require_auth()
                if not user:
                    return
                try:
                    conn = get_db_connection(use_database=True)
                    cursor = conn.cursor()
                    cursor.execute("SELECT username, role, email, status, created_at, data_usage, api_key, model FROM users WHERE username = %s", (user.get("username"),))
                    r = cursor.fetchone()
                    cursor.close()
                    conn.close()
                except Exception as e:
                     self.send_json(500, {"error": "db_error", "details": str(e)})
                     return
                
                if not r:
                    self.send_json(404, {"error": "user_not_found"})
                    return

                user_data = {
                    "username": r[0],
                    "role": r[1],
                    "email": r[2],
                    "status": r[3],
                    "created_at": r[4].isoformat() if hasattr(r[4], "isoformat") else str(r[4]),
                    "data_usage": int(r[5] or 0),
                    "api_key": r[6],
                    "model": r[7],
                }
                self.send_json(200, {"user": user_data})
                return
            if parsed_path.path == '/api/users':
                user = self.require_auth()
                if not user:
                    return
                if user.get("role") != "admin":
                    self.send_json(403, {"error": "forbidden"})
                    return
                try:
                    conn = get_db_connection(use_database=True)
                    cursor = conn.cursor()
                    cursor.execute("SELECT username, role, email, status, created_at, data_usage, api_key, model FROM users ORDER BY id ASC")
                    rows = cursor.fetchall()
                    cursor.close()
                    conn.close()
                except Exception as e:
                    self.send_json(500, {"error": "db_error", "details": str(e)})
                    return
                items = []
                for r in rows:
                    items.append({
                        "username": r[0],
                        "role": r[1],
                        "email": r[2],
                        "status": r[3],
                        "created_at": r[4].isoformat() if hasattr(r[4], "isoformat") else str(r[4]),
                        "data_usage": int(r[5] or 0),
                        "api_key": r[6],
                        "model": r[7],
                    })
                self.send_json(200, {"users": items})
                return
            if parsed_path.path == '/api/task_status':
                user = self.require_auth()
                if not user:
                    return
                
                username = user.get("username")
                task = USER_TASKS.get(username)
                
                if not task:
                    self.send_json(200, {"status": "none"})
                    return
                
                with USER_TASKS_LOCK:
                    # Return copy to avoid race conditions
                    response = {
                        "status": task.get("status", "unknown"),
                        "logs": list(task.get("logs", [])),
                        "result": task.get("result"),
                        "error_msg": task.get("error_msg"),
                        "phase": task.get("phase"),
                        "progress": task.get("progress"),
                        "kind": task.get("kind"),
                    }
                    # Decode bytes logs
                    decoded_logs = []
                    for log in response["logs"]:
                        if isinstance(log, bytes):
                            decoded_logs.append(log.decode('utf-8', errors='replace'))
                        else:
                            decoded_logs.append(str(log))
                    response["logs"] = decoded_logs
                    
                self.send_json(200, response)
                return

            user = self.require_auth()
            if not user:
                return

        if parsed_path.path == '/api/list_videos':
            # List videos in data/ folder
            try:
                files = [f for f in os.listdir('data') if f.endswith(('.mp4', '.mov', '.avi'))]
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'files': files}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
                
        elif parsed_path.path == '/api/list_results':
             # List files in result/ folder
            try:
                files = []
                if os.path.exists('result'):
                    files = [f for f in os.listdir('result') if f.endswith(('.json', '.mp4'))]
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'files': files}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
        elif parsed_path.path == '/api/video_info':
            try:
                params = urllib.parse.parse_qs(parsed_path.query)
                rel_path = (params.get('path') or [''])[0]
                rel_path = rel_path.lstrip('/')
                rel_path = os.path.normpath(rel_path)

                if not rel_path or rel_path.startswith('..') or rel_path.startswith('/'):
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'invalid path'}).encode('utf-8'))
                    return

                if not (rel_path.startswith('data/') or rel_path.startswith('result/')):
                    self.send_response(403)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'forbidden path'}).encode('utf-8'))
                    return

                abs_path = os.path.join(os.getcwd(), rel_path)
                if not (os.path.exists(abs_path) and os.path.isfile(abs_path)):
                    self.send_response(404)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'file not found'}).encode('utf-8'))
                    return

                duration = None
                probe = subprocess.run(
                    [
                        'ffprobe',
                        '-v',
                        'error',
                        '-show_entries',
                        'format=duration',
                        '-of',
                        'default=noprint_wrappers=1:nokey=1',
                        abs_path,
                    ],
                    capture_output=True,
                    text=True,
                )
                if probe.returncode == 0:
                    out = (probe.stdout or '').strip()
                    if out:
                        duration = float(out)

                if duration is None:
                    try:
                        import cv2

                        cap = cv2.VideoCapture(abs_path)
                        fps = cap.get(cv2.CAP_PROP_FPS) or 0
                        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
                        cap.release()
                        if fps > 0 and frames > 0:
                            duration = float(frames) / float(fps)
                    except Exception:
                        duration = None

                if duration is None:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'failed to read duration'}).encode('utf-8'))
                    return

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'path': rel_path, 'duration': duration}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
        else:
            if self.path == '/' or self.path == '/index.html':
                self.path = '/web/index.html'
                return super().do_GET()
            
            clean_path = os.path.normpath(parsed_path.path)
            if clean_path.startswith('/..'):
                self.send_response(403)
                self.end_headers()
                return

            if clean_path.startswith('/data/') or clean_path.startswith('/result/'):
                real_path = os.path.join(os.getcwd(), clean_path.lstrip('/'))
                if not (os.path.exists(real_path) and os.path.isfile(real_path)):
                    self.send_error(404, "File not found")
                    return

                try:
                    f = open(real_path, 'rb')
                except OSError:
                    self.send_error(404, "File not found")
                    return

                try:
                    fs = os.fstat(f.fileno())
                    size = fs.st_size
                    ctype = self.guess_type(real_path)
                    range_header = self.headers.get('Range')

                    if range_header:
                        m = re.match(r'^bytes=(\d*)-(\d*)$', range_header.strip())
                        if not m:
                            self.send_response(416)
                            self.send_header("Content-Range", f"bytes */{size}")
                            self.end_headers()
                            return

                        start_str, end_str = m.group(1), m.group(2)
                        if start_str == "" and end_str == "":
                            self.send_response(416)
                            self.send_header("Content-Range", f"bytes */{size}")
                            self.end_headers()
                            return

                        if start_str == "":
                            suffix = int(end_str)
                            if suffix <= 0:
                                start, end = 0, size - 1
                            else:
                                start = max(size - suffix, 0)
                                end = size - 1
                        else:
                            start = int(start_str)
                            end = int(end_str) if end_str != "" else size - 1

                        if start >= size:
                            self.send_response(416)
                            self.send_header("Content-Range", f"bytes */{size}")
                            self.end_headers()
                            return

                        end = min(end, size - 1)
                        if end < start:
                            self.send_response(416)
                            self.send_header("Content-Range", f"bytes */{size}")
                            self.end_headers()
                            return

                        length = end - start + 1
                        self.send_response(206)
                        self.send_header("Content-type", ctype)
                        self.send_header("Accept-Ranges", "bytes")
                        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                        self.send_header("Content-Length", str(length))
                        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
                        self.send_header("Cache-Control", "no-store")
                        self.end_headers()
                        f.seek(start)
                        remaining = length
                        try:
                            while remaining > 0:
                                chunk = f.read(min(1024 * 1024, remaining))
                                if not chunk:
                                    break
                                self.wfile.write(chunk)
                                remaining -= len(chunk)
                        except (BrokenPipeError, ConnectionResetError):
                            # Client disconnected, stop sending
                            pass
                        return

                    self.send_response(200)
                    self.send_header("Content-type", ctype)
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Content-Length", str(size))
                    self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    try:
                        shutil.copyfileobj(f, self.wfile)
                    except (BrokenPipeError, ConnectionResetError):
                        # Client disconnected, stop sending
                        pass
                    return
                finally:
                    f.close()

            elif not clean_path.startswith('/web/'):
                 if not os.path.exists('.' + clean_path):
                     self.path = '/web' + clean_path
            
            return super().do_GET()

class ReusableThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    ensure_database()
    with ReusableThreadingTCPServer(("", PORT), CustomHandler) as httpd:
        print(f"Serving at port {PORT}")
        with open('.port', 'w') as f:
            f.write(str(PORT))
        httpd.serve_forever()
