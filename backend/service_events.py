"""阶段 4.2 批次 F：SSE 任务事件流。

- `_task_status_payload`：从 handle_task_status 抽取的任务状态构造逻辑
  （内存优先 + DB 兜底 + 中断任务修复），供轮询接口与 SSE 事件流共用。
- `iter_task_events`：SSE 事件生成器，状态变化时才产出最新 payload，
  终态（completed/failed/none）或超时后结束。
"""
import json
import time
from typing import Dict, Iterator

from backend.app_db_org import (
    TASK_STATUS_FAILED,
    TASK_STATUS_PENDING,
    TASK_STATUS_RUNNING,
    finish_task,
    get_latest_task_for_user,
)
from backend.app_logging import get_logger

logger = get_logger("events")

# SSE 事件流的终态：流到此结束
_TERMINAL_STATUSES = frozenset({"completed", "failed", "none"})


def _task_status_payload(username: str) -> Dict[str, object]:
    """构造任务状态响应（与 /api/task_status 语义完全一致）。

    延迟导入 service_analyze 以避免循环依赖（service_analyze 顶层导入本模块）。
    USER_TASKS / INTERRUPTED_TASKS 均为原地变更的模块级容器，引用绑定安全。
    """
    from backend.service_analyze import INTERRUPTED_TASKS, USER_TASKS, USER_TASKS_LOCK, _task_row_to_response

    task = USER_TASKS.get(username)
    if task:
        with USER_TASKS_LOCK:
            response = {
                "status": task.get("status", "unknown"),
                "logs": list(task.get("logs", [])),
                "result": task.get("result"),
                "error_msg": task.get("error_msg"),
                "phase": task.get("phase"),
                "progress": task.get("progress"),
                "kind": task.get("kind"),
                "model": task.get("model"),
                "progress_unit": task.get("progress_unit"),
                "task_id": task.get("task_id"),
            }
            decoded_logs = []
            for log in response["logs"]:
                if isinstance(log, bytes):
                    decoded_logs.append(log.decode("utf-8", errors="replace"))
                else:
                    decoded_logs.append(str(log))
            response["logs"] = decoded_logs
        return response

    # 内存无任务：查 DB 兜底（覆盖服务重启后仍在轮询的前端连接）
    row = None
    try:
        row = get_latest_task_for_user(username)
    except Exception:
        logger.warning("查询任务状态失败: username=%s", username, exc_info=True)
    if row:
        try:
            row_id = int(row.get("id"))
        except Exception:
            row_id = None
        st = str(row.get("status") or "")
        if st in (TASK_STATUS_PENDING, TASK_STATUS_RUNNING):
            # 防御兜底：正常启动时 recover_interrupted_tasks 已修复，这里处理漏网情况
            try:
                finish_task(row_id, TASK_STATUS_FAILED, error="interrupted_by_restart")
            except Exception:
                logger.warning("中断任务修复写库失败: task_id=%s", row_id, exc_info=True)
            if row_id is not None:
                INTERRUPTED_TASKS.add((username, row_id))
            row = dict(row)
            row["status"] = TASK_STATUS_FAILED
            row["error"] = "interrupted_by_restart"
            row["phase"] = "failed"
        if row_id is not None and (username, row_id) in INTERRUPTED_TASKS:
            return _task_row_to_response(row)
    return {"status": "none"}


def iter_task_events(
    username: str,
    poll_interval: float = 1.0,
    max_seconds: float = 7200.0,
) -> Iterator[Dict[str, object]]:
    """SSE 任务事件生成器。

    - 每次轮询构造完整 payload，与上次做 JSON 规范化签名对比，变化才 yield；
    - 终态（completed/failed/none）yield 后结束流；
    - 超过 max_seconds 强制结束（客户端可自动重连重建流）。
    """
    deadline = time.monotonic() + max_seconds
    last_sig: str = ""
    while time.monotonic() < deadline:
        payload = _task_status_payload(username)
        sig = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        if sig != last_sig:
            last_sig = sig
            yield payload
        status = str(payload.get("status") or "")
        if status in _TERMINAL_STATUSES:
            return
        time.sleep(poll_interval)
