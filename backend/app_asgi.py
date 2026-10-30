"""阶段 4.2 批次 I：FastAPI(ASGI) 应用层。

设计要点：
- 业务路由（backend/app_routes.py 路由表）保持 handler 旧接口不变，通过
  ASGIHandlerAdapter 适配：headers（大小写不敏感）→ starlette Request.headers，
  rfile → 请求体 BytesIO，send_json / send_response+wfile 双通道响应缓存。
- 同步业务函数统一经 run_in_threadpool 执行，语义等价原 ThreadingTCPServer。
- SSE /api/task_events：EventSource 无法携带 Authorization 头，支持 ?token=。
- 媒体 /data/** /result/**：Bearer 或 ?token= 鉴权，normpath 防穿越，
  FileResponse 原生支持 Range（视频拖动按需拉流）。
- 静态资源全部映射到 web/ 子树（同原 http.server 行为），Cache-Control: no-store。
"""
import io
import json
import mimetypes
import os
import urllib.parse
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from starlette.concurrency import iterate_in_threadpool, run_in_threadpool

from backend.app_auth import get_token_info
from backend.app_config import PORT
from backend.app_db import ensure_database
from backend.app_logging import get_logger, setup_logging
from backend.app_routes import _AUTH_EXEMPT, GET_ROUTES, POST_ROUTES
from backend.service_analyze import recover_interrupted_tasks
from backend.service_events import iter_task_events

logger = get_logger("asgi")

WEB_DIR = os.path.join(os.getcwd(), "web")

mimetypes.init()
mimetypes.add_type("video/mp4", ".mp4")


# ---------------------------------------------------------------------------
# 启动钩子（等价原 server.py __main__ 段）
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    ensure_database()
    # 任务持久化：重启后把遗留的 pending/running 任务标记为 failed(interrupted)
    recover_interrupted_tasks()
    # Token 持久化建表 + 清理过期会话（旧 Token 在 TTL 内重启后仍有效）
    try:
        from backend.app_db_auth import ensure_auth_tables, purge_expired_tokens

        ensure_auth_tables()
        purged = purge_expired_tokens()
        if purged:
            logger.info("启动清理过期会话 %d 个", purged)
    except Exception:
        logger.warning("会话表初始化失败（鉴权降级为纯内存模式）", exc_info=True)
    with open(".port", "w") as f:
        f.write(str(PORT))
    logger.info("服务已启动，端口 %s", PORT)
    yield


app = FastAPI(title="Geniview", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-Filename", "Range", "X-UI-Lang"],
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length"],
)


# ---------------------------------------------------------------------------
# handler 适配器：把 ASGI 请求包装成业务路由期望的旧 handler 接口
# ---------------------------------------------------------------------------

class ASGIHandlerAdapter:
    """旧 handler 接口的最小实现（headers/rfile/send_json/send_response/wfile）。"""

    def __init__(self, request: Request, body: bytes):
        self.headers = request.headers  # starlette Headers：大小写不敏感
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.json_response: Optional[tuple] = None  # (status, payload)
        self.raw_status: Optional[int] = None
        self.raw_headers: list = []

    def send_json(self, status: int, payload: dict) -> None:
        self.json_response = (status, payload)

    def send_response(self, code: int) -> None:
        self.raw_status = code
        self.raw_headers = []

    def send_header(self, key: str, value: str) -> None:
        self.raw_headers.append((key, value))

    def end_headers(self) -> None:
        pass

    def to_response(self) -> Response:
        if self.json_response is not None:
            status, payload = self.json_response
            # default=str：MySQL 返回的 datetime/date 等对象自动转字符串，避免序列化异常
            body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
            return Response(content=body, status_code=status, media_type="application/json; charset=utf-8")
        if self.raw_status is not None:
            content_type = "application/json"
            for key, value in self.raw_headers:
                if key.lower() == "content-type":
                    content_type = value
            return Response(
                content=self.wfile.getvalue(),
                status_code=self.raw_status,
                media_type=content_type,
            )
        return JSONResponse({"error": "internal_error"}, status_code=500)


def _bearer_user(request: Request) -> Optional[dict]:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    if not token:
        return None
    return get_token_info(token)


def _media_auth_user(request: Request) -> Optional[dict]:
    """媒体/SSE 鉴权：优先 Authorization 头，其次 ?token= 查询参数（<video>/<img>/EventSource）。"""
    user = _bearer_user(request)
    if user:
        return user
    token = request.query_params.get("token") or ""
    if not token:
        return None
    return get_token_info(token)


# ---------------------------------------------------------------------------
# API 路由：把路由表注册为 FastAPI 端点（OpenAPI 可见）
# ---------------------------------------------------------------------------

def _make_api_endpoint(route, with_body: bool):
    async def endpoint(request: Request) -> Response:
        body = await request.body() if with_body else b""
        adapter = ASGIHandlerAdapter(request, body)
        path = request.url.path
        user = None
        if path not in _AUTH_EXEMPT:
            user = _bearer_user(request)
            if not user:
                return JSONResponse({"error": "unauthorized"}, status_code=401)
        try:
            parsed_path = urllib.parse.urlparse(str(request.url))
            await run_in_threadpool(route, adapter, user, parsed_path)
        except Exception:
            logger.exception("API 处理异常: path=%s", path)
            return JSONResponse({"error": "internal_error"}, status_code=500)
        return adapter.to_response()

    return endpoint


for _path, _route in GET_ROUTES.items():
    app.add_api_route(
        _path,
        _make_api_endpoint(_route, with_body=False),
        methods=["GET", "HEAD"],
        include_in_schema=False,
    )

for _path, _route in POST_ROUTES.items():
    app.add_api_route(
        _path,
        _make_api_endpoint(_route, with_body=True),
        methods=["POST"],
        include_in_schema=False,
    )


# ---------------------------------------------------------------------------
# SSE 任务事件流
# ---------------------------------------------------------------------------

async def task_events(request: Request) -> Response:
    user = _media_auth_user(request)
    if not user:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    username = str(user.get("username") or "")

    async def event_stream():
        # 生成器函数调用本身不执行任何 IO（首个 next 才会查任务状态），真正迭代在 threadpool 中进行
        async for payload in iterate_in_threadpool(iter_task_events(username)):
            data = json.dumps(payload, ensure_ascii=False, default=str)
            yield f"event: status\ndata: {data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


app.add_api_route(
    "/api/task_events",
    task_events,
    methods=["GET", "HEAD"],
    include_in_schema=False,
)


# ---------------------------------------------------------------------------
# 媒体文件（data/ result/）：Bearer 或 ?token= 鉴权，FileResponse 支持 Range
# ---------------------------------------------------------------------------

async def _serve_media(prefix: str, file_path: str, request: Request) -> Response:
    if not _media_auth_user(request):
        logger.warning("未授权的媒体文件访问: path=%s, client=%s", request.url.path, request.client.host if request.client else "-")
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    # 对齐原实现：URL 解码两次（框架已解一次，这里再解一次）
    decoded = urllib.parse.unquote(file_path)
    clean = os.path.normpath(os.path.join(prefix, decoded))
    if not clean.startswith(prefix + os.sep) or ".." in clean.split(os.sep):
        return JSONResponse({"error": "forbidden"}, status_code=403)

    real_path = os.path.join(os.getcwd(), clean)
    if not os.path.isfile(real_path):
        return JSONResponse({"error": "file not found"}, status_code=404)
    return FileResponse(real_path, headers={"Cache-Control": "no-store"})


async def media_data(file_path: str, request: Request) -> Response:
    return await _serve_media("data", file_path, request)


async def media_result(file_path: str, request: Request) -> Response:
    return await _serve_media("result", file_path, request)


app.add_api_route(
    "/data/{file_path:path}", media_data, methods=["GET", "HEAD"], include_in_schema=False
)
app.add_api_route(
    "/result/{file_path:path}", media_result, methods=["GET", "HEAD"], include_in_schema=False
)


# ---------------------------------------------------------------------------
# 静态资源：/ → web/index.html；其余路径映射到 web/ 子树（no-store，同原实现）
# ---------------------------------------------------------------------------

async def favicon() -> Response:
    # 浏览器自动请求 /favicon.ico：返回 204 避免控制台出现无意义的 404
    return Response(status_code=204)


app.add_api_route("/favicon.ico", favicon, methods=["GET", "HEAD"], include_in_schema=False)


async def static_files(full_path: str) -> Response:
    if full_path in ("", "index.html"):
        index_path = os.path.join(WEB_DIR, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path, headers={"Cache-Control": "no-store"})
        return JSONResponse({"error": "not_found"}, status_code=404)

    decoded = urllib.parse.unquote(full_path)
    clean = os.path.normpath(decoded)
    if clean.startswith("..") or os.path.isabs(clean):
        return JSONResponse({"error": "not_found"}, status_code=404)

    # 允许 /web/xxx 与 /xxx 双写法（等价映射到 web/ 子树）
    if clean.startswith("web/"):
        clean = clean[len("web/"):]
    target = os.path.join(WEB_DIR, clean)
    if os.path.isfile(target):
        return FileResponse(target, headers={"Cache-Control": "no-store"})
    return JSONResponse({"error": "not_found"}, status_code=404)


app.add_api_route(
    "/{full_path:path}", static_files, methods=["GET", "HEAD"], include_in_schema=False
)
