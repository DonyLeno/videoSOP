import logging
import os
from logging.handlers import RotatingFileHandler

_LOG_DIR = os.environ.get("LOG_DIR") or os.path.join(os.getcwd(), "logs")
_LOG_LEVEL = (os.environ.get("LOG_LEVEL") or "INFO").upper()
_LOG_MAX_BYTES = int(os.environ.get("LOG_MAX_BYTES") or str(10 * 1024 * 1024))
_LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT") or "5")

_configured = False


def setup_logging() -> logging.Logger:
    global _configured
    logger = logging.getLogger("geniview")
    if _configured or logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s"
    )
    logger.setLevel(getattr(logging, _LOG_LEVEL, logging.INFO))

    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join(_LOG_DIR, "geniview.log"),
            maxBytes=_LOG_MAX_BYTES,
            backupCount=_LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception:
        pass  # 文件日志不可用时退化为仅控制台输出

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
    logger.propagate = False
    _configured = True
    return logger


def get_logger(name: str = "") -> logging.Logger:
    setup_logging()
    if name:
        return logging.getLogger(f"geniview.{name}")
    return logging.getLogger("geniview")
