"""测试包初始化：在任何 backend 导入之前设置隔离的 SQLite 测试环境。"""

import os
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_TMPDIR = tempfile.mkdtemp(prefix="geniview_test_")
os.environ["DB_MODE"] = "sqlite"
os.environ["SQLITE_PATH"] = os.path.join(_TMPDIR, "test.sqlite3")
