"""Geniview 服务入口：FastAPI(ASGI) + uvicorn。

阶段 4.2 批次 I：由标准库 http.server 迁移至 ASGI。
- 路由/鉴权/SSE/媒体/静态实现见 backend/app_asgi.py
- 路由表见 backend/app_routes.py
- 启动钩子（建库、中断任务恢复、会话清理）在 lifespan 中执行
- 保持 `python3 server.py` 兼容启动
"""

import uvicorn

from backend.app_asgi import app
from backend.app_config import PORT

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_config=None)
