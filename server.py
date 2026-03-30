import http.server
import json
import mimetypes
import os
import re
import shutil
import socketserver
import urllib.parse
from typing import Dict, Optional

from backend.app_auth import get_token_info
from backend.app_config import PORT
from backend.app_db import ensure_database
from backend.service_analyze import handle_analyze, handle_task_status
from backend.service_media import handle_extract_frames, handle_list_videos, handle_upload, handle_video_info
from backend.service_results import (
    get_latest_version,
    handle_list_results,
    handle_result_details,
    handle_update_result,
)
from backend.service_sop import handle_get_sop_content, handle_set_sop_content
from backend.service_users import (
    handle_create_user,
    handle_list_users,
    handle_login,
    handle_me,
    handle_user_history,
    handle_update_user,
)


mimetypes.init()
mimetypes.add_type("video/mp4", ".mp4")


class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def send_json(self, status: int, payload: Dict[str, object]) -> None:
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

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
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization, X-Filename, Range, X-UI-Lang",
        )
        self.send_header("Access-Control-Expose-Headers", "Content-Range, Accept-Ranges, Content-Length")

        request_path = getattr(self, "path", None)
        if request_path:
            parsed_path = urllib.parse.urlparse(request_path)
            clean_path = os.path.normpath(parsed_path.path)
            if clean_path == "/web/index.html" or clean_path.startswith("/web/"):
                self.send_header("Cache-Control", "no-store")
        return super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_HEAD(self):
        parsed_path = urllib.parse.urlparse(self.path)
        decoded_path = parsed_path.path
        try:
            decoded_path = urllib.parse.unquote(decoded_path)
            decoded_path = urllib.parse.unquote(decoded_path)
        except Exception:
            pass
        clean_path = os.path.normpath(decoded_path)
        if clean_path.startswith("/.."):
            self.send_response(403)
            self.end_headers()
            return

        if clean_path.startswith("/data/") or clean_path.startswith("/result/"):
            real_path = os.path.join(os.getcwd(), clean_path.lstrip("/"))
            if not (os.path.exists(real_path) and os.path.isfile(real_path)):
                self.send_error(404, "File not found")
                return

            try:
                f = open(real_path, "rb")
            except OSError:
                self.send_error(404, "File not found")
                return

            try:
                fs = os.fstat(f.fileno())
                size = fs.st_size
                ctype = self.guess_type(real_path)
                range_header = self.headers.get("Range")

                if range_header:
                    m = re.match(r"^bytes=(\d*)-(\d*)$", range_header.strip())
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

        if self.path == "/" or self.path == "/index.html":
            self.path = "/web/index.html"
            return super().do_HEAD()

        if not clean_path.startswith("/web/"):
            if not os.path.exists("." + clean_path):
                self.path = "/web" + clean_path

        return super().do_HEAD()

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)

        if parsed_path.path == "/api/login":
            handle_login(self)
            return

        user = self.require_auth()
        if not user:
            return

        if parsed_path.path == "/api/users":
            handle_create_user(self, user)
            return

        if parsed_path.path == "/api/users/update":
            handle_update_user(self, user)
            return

        if parsed_path.path == "/api/sop_content":
            handle_set_sop_content(self, user)
            return

        if parsed_path.path == "/api/update_result":
            handle_update_result(self)
            return


        if parsed_path.path == "/api/upload":
            handle_upload(self)
            return

        if parsed_path.path == "/api/extract_frames":
            handle_extract_frames(self, user)
            return

        if parsed_path.path == "/api/analyze":
            handle_analyze(self, user)
            return

        self.send_json(404, {"error": "not_found"})

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        if parsed_path.path.startswith("/api/"):
            if parsed_path.path == "/api/version":
                version = get_latest_version()
                self.send_json(200, {"version": version})
                return

            if parsed_path.path == "/api/sop_content":
                user = self.require_auth()
                if not user:
                    return
                handle_get_sop_content(self, user)
                return

            if parsed_path.path == "/api/me":
                user = self.require_auth()
                if not user:
                    return
                handle_me(self, user)
                return

            if parsed_path.path == "/api/users":
                user = self.require_auth()
                if not user:
                    return
                handle_list_users(self, user)
                return

            if parsed_path.path == "/api/user_history":
                user = self.require_auth()
                if not user:
                    return
                handle_user_history(self, user, parsed_path)
                return

            if parsed_path.path == "/api/task_status":
                user = self.require_auth()
                if not user:
                    return
                handle_task_status(self, user)
                return


            user = self.require_auth()
            if not user:
                return

            if parsed_path.path == "/api/list_videos":
                handle_list_videos(self)
                return

            if parsed_path.path == "/api/list_results":
                handle_list_results(self)
                return

            if parsed_path.path == "/api/result_details":
                handle_result_details(self, parsed_path)
                return

            if parsed_path.path == "/api/video_info":
                handle_video_info(self, parsed_path)
                return

            self.send_json(404, {"error": "not_found"})
            return

        if self.path == "/" or self.path == "/index.html":
            self.path = "/web/index.html"
            return super().do_GET()

        decoded_path = parsed_path.path
        try:
            decoded_path = urllib.parse.unquote(decoded_path)
            decoded_path = urllib.parse.unquote(decoded_path)
        except Exception:
            pass
        clean_path = os.path.normpath(decoded_path)
        if clean_path.startswith("/.."):
            self.send_response(403)
            self.end_headers()
            return

        if clean_path.startswith("/data/") or clean_path.startswith("/result/"):
            real_path = os.path.join(os.getcwd(), clean_path.lstrip("/"))
            if not (os.path.exists(real_path) and os.path.isfile(real_path)):
                self.send_error(404, "File not found")
                return

            try:
                f = open(real_path, "rb")
            except OSError:
                self.send_error(404, "File not found")
                return

            try:
                fs = os.fstat(f.fileno())
                size = fs.st_size
                ctype = self.guess_type(real_path)
                range_header = self.headers.get("Range")

                if range_header:
                    m = re.match(r"^bytes=(\d*)-(\d*)$", range_header.strip())
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
                    pass
                return
            finally:
                f.close()

        if not clean_path.startswith("/web/"):
            if not os.path.exists("." + clean_path):
                self.path = "/web" + clean_path

        return super().do_GET()


class ReusableThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    ensure_database()
    with ReusableThreadingTCPServer(("", PORT), CustomHandler) as httpd:
        print(f"Serving at port {PORT}")
        with open(".port", "w") as f:
            f.write(str(PORT))
        httpd.serve_forever()
