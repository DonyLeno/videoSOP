import os


VERSION = "v2.3"

PORT = int(os.environ.get("PORT", "8000"))

try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass

APP_VERSION = os.environ.get("APP_VERSION", "").strip()

MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "123456")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "geniview")
MYSQL_CONNECT_TIMEOUT = int(os.environ.get("MYSQL_CONNECT_TIMEOUT", "5"))

TOKEN_TTL_SECONDS = int(os.environ.get("TOKEN_TTL_SECONDS", str(8 * 60 * 60)))
ANALYZE_CONCURRENCY = int(os.environ.get("ANALYZE_CONCURRENCY", "1") or "1")
if ANALYZE_CONCURRENCY < 1:
    ANALYZE_CONCURRENCY = 1

LOGIN_MAX_FAILURES = int(os.environ.get("LOGIN_MAX_FAILURES", "5") or "5")
LOGIN_LOCKOUT_SECONDS = int(os.environ.get("LOGIN_LOCKOUT_SECONDS", "900") or "900")
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "1024") or "1024")
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
ALLOWED_UPLOAD_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
