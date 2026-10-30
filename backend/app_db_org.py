"""阶段 1 数据底座：组织层级（项目/产线/成员）、视频、任务、分析结果的数据访问层。

设计要点：
- SQL 统一用 ``?`` 占位符书写，MySQL 执行前自动替换为 ``%s``，避免每个函数双份书写
- 业务键以 username 为中心（与 detection_history 现状一致），不依赖 users.id
- 所有「登记」函数幂等：已存在则返回既有 id 或更新元数据，不重复插入
- auto 模式下 MySQL 执行失败自动降级 SQLite 重试（与 app_db 行为一致）
"""

import json
from typing import Any, Dict, List, Optional

from backend.app_db import (
    MYSQL_DATABASE,
    _DB_MODE,
    _get_sqlite_connection,
    _mysql_available,
    get_db_connection,
)
from backend.app_logging import get_logger

logger = get_logger("db_org")

DEFAULT_PROJECT_CODE = "DEFAULT"
DEFAULT_PROJECT_NAME = "默认项目"
DEFAULT_LINE_CODE = "DEFAULT"
DEFAULT_LINE_NAME = "默认产线"

TASK_STATUS_PENDING = "pending"
TASK_STATUS_RUNNING = "running"
TASK_STATUS_SUCCEEDED = "succeeded"
TASK_STATUS_FAILED = "failed"
TASK_STATUS_CANCELED = "canceled"

_MEMBER_ROLES = ("owner", "editor", "viewer")
MEMBER_ROLES = _MEMBER_ROLES  # 公开别名，供服务层校验


def _use_mysql() -> bool:
    if _DB_MODE == "sqlite":
        return False
    if _DB_MODE == "mysql":
        return True
    return _mysql_available()


# ---------------------------------------------------------------------------
# 建表
# ---------------------------------------------------------------------------

_MYSQL_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS projects (
        id INT AUTO_INCREMENT PRIMARY KEY,
        code VARCHAR(32) NOT NULL UNIQUE,
        name VARCHAR(128) NOT NULL,
        description TEXT,
        status VARCHAR(16) NOT NULL DEFAULT 'active',
        created_by VARCHAR(64) NOT NULL DEFAULT 'admin',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS production_lines (
        id INT AUTO_INCREMENT PRIMARY KEY,
        project_id INT NOT NULL,
        code VARCHAR(32) NOT NULL,
        name VARCHAR(128) NOT NULL,
        process_desc TEXT,
        sop_content MEDIUMTEXT,
        status VARCHAR(16) NOT NULL DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_line (project_id, code),
        INDEX idx_line_project (project_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS line_stations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        line_id INT NOT NULL,
        code VARCHAR(32) NOT NULL,
        name VARCHAR(128) NOT NULL,
        pos_x DOUBLE NOT NULL DEFAULT 0,
        pos_y DOUBLE NOT NULL DEFAULT 0,
        rotation DOUBLE NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_station_line (line_id),
        UNIQUE KEY uq_station (line_id, code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS project_members (
        project_id INT NOT NULL,
        username VARCHAR(64) NOT NULL,
        role VARCHAR(16) NOT NULL DEFAULT 'editor',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (project_id, username)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS videos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        project_id INT NOT NULL,
        line_id INT NULL,
        station_id INT NULL,
        filename VARCHAR(255) NOT NULL,
        stored_path VARCHAR(512) NOT NULL,
        duration_sec DOUBLE NULL,
        size_bytes BIGINT NULL,
        uploaded_by VARCHAR(64) NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_video_scope (project_id, line_id),
        INDEX idx_video_station (line_id, station_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS tasks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(64) NOT NULL,
        video_id INT NULL,
        project_id INT NULL,
        line_id INT NULL,
        model VARCHAR(64) NULL,
        status VARCHAR(16) NOT NULL DEFAULT 'pending',
        phase VARCHAR(32) NULL,
        progress_current INT NOT NULL DEFAULT 0,
        progress_total INT NOT NULL DEFAULT 0,
        progress_unit VARCHAR(16) NULL,
        error TEXT NULL,
        result_md_path VARCHAR(512) NULL,
        result_json_path VARCHAR(512) NULL,
        result_video_path VARCHAR(512) NULL,
        token_input INT NULL,
        token_output INT NULL,
        token_thinking INT NULL,
        token_total INT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP NULL,
        finished_at TIMESTAMP NULL,
        INDEX idx_tasks_user (username, id),
        INDEX idx_tasks_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS analysis_results (
        id INT AUTO_INCREMENT PRIMARY KEY,
        task_id INT NULL,
        video_id INT NULL,
        project_id INT NOT NULL,
        line_id INT NULL,
        md_path VARCHAR(512) NOT NULL,
        json_path VARCHAR(512) NULL,
        video_copy_path VARCHAR(512) NULL,
        en_md_path VARCHAR(512) NULL,
        stats_json TEXT NULL,
        version INT NOT NULL DEFAULT 1,
        created_by VARCHAR(64) NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_results_scope (project_id, line_id),
        INDEX idx_results_task (task_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS result_revisions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        result_path VARCHAR(512) NOT NULL,
        actions_json MEDIUMTEXT NOT NULL,
        action_count INT NOT NULL DEFAULT 0,
        revision_note VARCHAR(255) NULL,
        created_by VARCHAR(64) NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_revisions_path (result_path, id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]

_SQLITE_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_by TEXT NOT NULL DEFAULT 'admin',
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS production_lines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        process_desc TEXT,
        sop_content TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        UNIQUE (project_id, code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS line_stations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        line_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        pos_x REAL NOT NULL DEFAULT 0,
        pos_y REAL NOT NULL DEFAULT 0,
        rotation REAL NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        UNIQUE (line_id, code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS project_members (
        project_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'editor',
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        PRIMARY KEY (project_id, username)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        line_id INTEGER,
        station_id INTEGER,
        filename TEXT NOT NULL,
        stored_path TEXT NOT NULL,
        duration_sec REAL,
        size_bytes INTEGER,
        uploaded_by TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        video_id INTEGER,
        project_id INTEGER,
        line_id INTEGER,
        model TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        phase TEXT,
        progress_current INTEGER NOT NULL DEFAULT 0,
        progress_total INTEGER NOT NULL DEFAULT 0,
        progress_unit TEXT,
        error TEXT,
        result_md_path TEXT,
        result_json_path TEXT,
        result_video_path TEXT,
        token_input INTEGER,
        token_output INTEGER,
        token_thinking INTEGER,
        token_total INTEGER,
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        started_at TEXT,
        finished_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS analysis_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER,
        video_id INTEGER,
        project_id INTEGER NOT NULL,
        line_id INTEGER,
        md_path TEXT NOT NULL,
        json_path TEXT,
        video_copy_path TEXT,
        en_md_path TEXT,
        stats_json TEXT,
        version INTEGER NOT NULL DEFAULT 1,
        created_by TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS result_revisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        result_path TEXT NOT NULL,
        actions_json TEXT NOT NULL,
        action_count INTEGER NOT NULL DEFAULT 0,
        revision_note TEXT,
        created_by TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    )
    """,
]


def _ensure_detection_history_columns(cur, mysql: bool) -> None:
    """为既有 detection_history 表补充 project_id/line_id/task_id（可 NULL，向后兼容）。"""
    if mysql:
        cur.execute(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='detection_history'",
            (MYSQL_DATABASE,),
        )
        existing = {str(row[0]).lower() for row in cur.fetchall()}
        if "project_id" not in existing:
            cur.execute("ALTER TABLE detection_history ADD COLUMN project_id INT NULL")
        if "line_id" not in existing:
            cur.execute("ALTER TABLE detection_history ADD COLUMN line_id INT NULL")
        if "task_id" not in existing:
            cur.execute("ALTER TABLE detection_history ADD COLUMN task_id INT NULL")
    else:
        cur.execute("PRAGMA table_info(detection_history)")
        existing = {str(row[1]).lower() for row in cur.fetchall()}
        if "project_id" not in existing:
            cur.execute("ALTER TABLE detection_history ADD COLUMN project_id INTEGER")
        if "line_id" not in existing:
            cur.execute("ALTER TABLE detection_history ADD COLUMN line_id INTEGER")
        if "task_id" not in existing:
            cur.execute("ALTER TABLE detection_history ADD COLUMN task_id INTEGER")


def _ensure_video_station_column(cur, mysql: bool) -> None:
    """为既有 videos 表补充 station_id（可 NULL，向后兼容）。"""
    if mysql:
        cur.execute(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='videos'",
            (MYSQL_DATABASE,),
        )
        existing = {str(row[0]).lower() for row in cur.fetchall()}
        if "station_id" not in existing:
            cur.execute("ALTER TABLE videos ADD COLUMN station_id INT NULL")
    else:
        cur.execute("PRAGMA table_info(videos)")
        existing = {str(row[1]).lower() for row in cur.fetchall()}
        if "station_id" not in existing:
            cur.execute("ALTER TABLE videos ADD COLUMN station_id INTEGER")


def ensure_org_tables() -> None:
    """创建阶段 1 全部新表；由 app_db.ensure_database() 调用。"""
    if _use_mysql():
        conn = get_db_connection(use_database=True)
        try:
            cur = conn.cursor()
            for ddl in _MYSQL_TABLES:
                cur.execute(ddl)
            _ensure_detection_history_columns(cur, mysql=True)
            _ensure_video_station_column(cur, mysql=True)
            conn.commit()
            cur.close()
        finally:
            conn.close()
        return
    conn = _get_sqlite_connection()
    try:
        cur = conn.cursor()
        for ddl in _SQLITE_TABLES:
            cur.execute(ddl)
        _ensure_detection_history_columns(cur, mysql=False)
        _ensure_video_station_column(cur, mysql=False)
        conn.commit()
        cur.close()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 统一执行器：SQL 用 ? 占位符，MySQL 侧自动替换为 %s
# ---------------------------------------------------------------------------

def _to_mysql_sql(sql: str) -> str:
    # 注意：新写 SQL 时字符串字面量中不得出现 '?'，否则会被误替换
    return sql.replace("?", "%s")


def _exec_mysql(sql: str, params, fetch, commit, want_lastrowid, want_rowcount=False):
    conn = get_db_connection(use_database=True)
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(_to_mysql_sql(sql), tuple(params))
        result: Any = None
        if fetch == "all":
            result = [dict(r) if not isinstance(r, dict) else r for r in (cur.fetchall() or [])]
        elif fetch == "one":
            row = cur.fetchone()
            result = dict(row) if row else None
        if want_lastrowid:
            result = cur.lastrowid
        elif want_rowcount:
            result = cur.rowcount
        if commit:
            conn.commit()
        cur.close()
        return result
    finally:
        conn.close()


def _exec_sqlite(sql: str, params, fetch, commit, want_lastrowid, want_rowcount=False):
    conn = _get_sqlite_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, tuple(params))
        result: Any = None
        if fetch == "all":
            result = [dict(r) for r in (cur.fetchall() or [])]
        elif fetch == "one":
            row = cur.fetchone()
            result = dict(row) if row else None
        if want_lastrowid:
            result = cur.lastrowid
        elif want_rowcount:
            result = cur.rowcount
        if commit:
            conn.commit()
        cur.close()
        return result
    finally:
        conn.close()


def _exec(
    sql: str,
    params=(),
    *,
    fetch: Optional[str] = None,
    commit: bool = False,
    want_lastrowid: bool = False,
    want_rowcount: bool = False,
):
    """统一 SQL 执行器。

    fetch: None（不取结果）/ 'all' / 'one'；want_lastrowid 时返回 lastrowid；
    want_rowcount 时返回受影响行数。auto 模式下 MySQL 失败自动降级 SQLite 重试。
    """
    if _use_mysql():
        try:
            return _exec_mysql(sql, params, fetch, commit, want_lastrowid, want_rowcount)
        except Exception:
            if _DB_MODE == "auto":
                logger.warning("MySQL 执行失败，auto 模式降级 SQLite 重试", exc_info=True)
                return _exec_sqlite(sql, params, fetch, commit, want_lastrowid, want_rowcount)
            raise
    return _exec_sqlite(sql, params, fetch, commit, want_lastrowid, want_rowcount)


def _to_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 项目
# ---------------------------------------------------------------------------

def create_project(code: str, name: str, description: Optional[str] = None, created_by: str = "admin") -> Optional[int]:
    code = (code or "").strip()
    if not code:
        return None
    row = _exec("SELECT id FROM projects WHERE code=?", (code,), fetch="one")
    if row:
        return _to_int(row.get("id"))
    return _to_int(
        _exec(
            "INSERT INTO projects (code, name, description, status, created_by) VALUES (?, ?, ?, 'active', ?)",
            (code, name, description, created_by),
            commit=True,
            want_lastrowid=True,
        )
    )


def get_project(project_id: int) -> Optional[Dict[str, object]]:
    return _exec("SELECT * FROM projects WHERE id=?", (project_id,), fetch="one")


def get_project_by_code(code: str) -> Optional[Dict[str, object]]:
    return _exec("SELECT * FROM projects WHERE code=?", ((code or "").strip(),), fetch="one")


def update_project(
    project_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
) -> bool:
    sets = []
    params: List[object] = []
    if name is not None:
        sets.append("name=?")
        params.append(name)
    if description is not None:
        sets.append("description=?")
        params.append(description)
    if status is not None:
        sets.append("status=?")
        params.append(status)
    if not sets:
        return True
    params.append(project_id)
    _exec(f"UPDATE projects SET {', '.join(sets)} WHERE id=?", tuple(params), commit=True)
    return True


def list_projects(username: Optional[str] = None, role: Optional[str] = None) -> List[Dict[str, object]]:
    """项目列表。admin 或未指定用户 → 全部；普通用户 → 仅成员项目。"""
    if username and (role or "") != "admin":
        return _exec(
            "SELECT p.* FROM projects p JOIN project_members m ON m.project_id = p.id "
            "WHERE m.username=? AND p.status='active' ORDER BY p.id ASC",
            (username,),
            fetch="all",
        )
    return _exec("SELECT * FROM projects ORDER BY id ASC", fetch="all")


# ---------------------------------------------------------------------------
# 产线
# ---------------------------------------------------------------------------

def create_production_line(
    project_id: int,
    code: str,
    name: str,
    process_desc: Optional[str] = None,
    sop_content: Optional[str] = None,
) -> Optional[int]:
    code = (code or "").strip()
    if not project_id or not code:
        return None
    row = _exec(
        "SELECT id FROM production_lines WHERE project_id=? AND code=?",
        (project_id, code),
        fetch="one",
    )
    if row:
        return _to_int(row.get("id"))
    return _to_int(
        _exec(
            "INSERT INTO production_lines (project_id, code, name, process_desc, sop_content, status) "
            "VALUES (?, ?, ?, ?, ?, 'active')",
            (project_id, code, name, process_desc, sop_content),
            commit=True,
            want_lastrowid=True,
        )
    )


def get_production_line(line_id: int) -> Optional[Dict[str, object]]:
    return _exec("SELECT * FROM production_lines WHERE id=?", (line_id,), fetch="one")


def get_line_sop(line_id: int) -> Optional[str]:
    """读取产线级 SOP 内容；产线不存在或未配置时返回 None。"""
    row = _exec("SELECT sop_content FROM production_lines WHERE id=?", (line_id,), fetch="one")
    if not row:
        return None
    content = row.get("sop_content")
    return str(content) if content is not None else None


def list_production_lines(project_id: int) -> List[Dict[str, object]]:
    return _exec(
        "SELECT * FROM production_lines WHERE project_id=? ORDER BY id ASC",
        (project_id,),
        fetch="all",
    )


def update_production_line(
    line_id: int,
    name: Optional[str] = None,
    process_desc: Optional[str] = None,
    sop_content: Optional[str] = None,
    status: Optional[str] = None,
) -> bool:
    sets = []
    params: List[object] = []
    if name is not None:
        sets.append("name=?")
        params.append(name)
    if process_desc is not None:
        sets.append("process_desc=?")
        params.append(process_desc)
    if sop_content is not None:
        sets.append("sop_content=?")
        params.append(sop_content)
    if status is not None:
        sets.append("status=?")
        params.append(status)
    if not sets:
        return True
    params.append(line_id)
    _exec(f"UPDATE production_lines SET {', '.join(sets)} WHERE id=?", tuple(params), commit=True)
    return True


def delete_production_line(line_id: int) -> bool:
    """物理删除产线及其工位；调用方需先确认产线下没有视频/任务/结果。"""
    _exec("DELETE FROM line_stations WHERE line_id=?", (line_id,), commit=True)
    _exec("DELETE FROM production_lines WHERE id=?", (line_id,), commit=True)
    return True


def count_line_references(line_id: int) -> Dict[str, int]:
    """统计产线被引用的数据量，用于删除前的占用校验。"""
    counts: Dict[str, int] = {}
    for key, sql in (
        ("video_count", "SELECT COUNT(*) AS c FROM videos WHERE line_id=?"),
        ("task_count", "SELECT COUNT(*) AS c FROM tasks WHERE line_id=?"),
        ("result_count", "SELECT COUNT(*) AS c FROM analysis_results WHERE line_id=?"),
    ):
        row = _exec(sql, (line_id,), fetch="one") or {}
        counts[key] = _to_int(row.get("c")) or 0
    return counts


# ---------------------------------------------------------------------------
# 工位（产线内的 2.5D 平面布局）
# ---------------------------------------------------------------------------

STATION_STEP_X = 18.0
STATION_ORIGIN_X = 6.0
STATION_LINE_END_X = 78.0
STATION_ORIGIN_Y = 50.0
STATION_MAX_COUNT = 60
FLOOR_MIN = 0.0
FLOOR_MAX = 100.0


def linear_station_positions(count: int) -> List[float]:
    """一条直线上均分工位的 X 坐标（y 固定为 STATION_ORIGIN_Y）。"""
    total = max(1, int(count or 1))
    if total == 1:
        return [42.0]
    step = (STATION_LINE_END_X - STATION_ORIGIN_X) / (total - 1)
    return [STATION_ORIGIN_X + index * step for index in range(total)]


def default_station_position(index: int, total: int = 0) -> tuple:
    """按直线布局给出工位默认坐标（平面坐标 0~100）。"""
    positions = linear_station_positions(max(int(total or 0), index + 1))
    x = positions[min(max(index, 0), len(positions) - 1)]
    return (
        min(max(round(x, 2), FLOOR_MIN), FLOOR_MAX),
        min(max(round(STATION_ORIGIN_Y, 2), FLOOR_MIN), FLOOR_MAX),
    )


def list_stations(line_id: int) -> List[Dict[str, object]]:
    return _exec(
        "SELECT * FROM line_stations WHERE line_id=? ORDER BY id ASC",
        (line_id,),
        fetch="all",
    ) or []


def list_stations_for_project(project_id: int) -> List[Dict[str, object]]:
    return _exec(
        "SELECT s.* FROM line_stations s JOIN production_lines l ON l.id = s.line_id "
        "WHERE l.project_id=? ORDER BY s.line_id ASC, s.id ASC",
        (project_id,),
        fetch="all",
    ) or []


def get_station(station_id: int) -> Optional[Dict[str, object]]:
    return _exec("SELECT * FROM line_stations WHERE id=?", (station_id,), fetch="one")


def create_station(
    line_id: int,
    name: str,
    code: str,
    pos_x: float,
    pos_y: float,
    rotation: float = 0.0,
) -> Optional[int]:
    if not line_id or not code:
        return None
    row = _exec(
        "SELECT id FROM line_stations WHERE line_id=? AND code=?",
        (line_id, code),
        fetch="one",
    )
    if row:
        return _to_int(row.get("id"))
    return _to_int(
        _exec(
            "INSERT INTO line_stations (line_id, code, name, pos_x, pos_y, rotation) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (line_id, code, name, float(pos_x), float(pos_y), float(rotation)),
            commit=True,
            want_lastrowid=True,
        )
    )


def create_default_stations(line_id: int, count: int, start_index: int = 0) -> List[int]:
    """批量创建默认工位；start_index 用于追加时延续编号，布局为一字排开。"""
    created: List[int] = []
    base = max(0, int(start_index))
    total = max(1, base + max(0, int(count)))
    positions = linear_station_positions(total)
    index = base
    for offset in range(max(0, int(count))):
        while True:
            code = f"ST-{index + 1:02d}"
            row = _exec(
                "SELECT id FROM line_stations WHERE line_id=? AND code=?",
                (line_id, code),
                fetch="one",
            )
            if not row:
                break
            index += 1
        x = positions[min(base + offset, len(positions) - 1)]
        sid = create_station(line_id, f"工位{index + 1}", code, x, STATION_ORIGIN_Y)
        if sid:
            created.append(sid)
        index += 1
    return created


def next_station_position(line_id: int) -> float:
    """追加单个工位时的 X 坐标；右侧无空间时把既有工位重新均分到一条直线。"""
    existing = list_stations(line_id)
    if not existing:
        return 42.0
    max_x = max(float(row.get("pos_x") or 0) for row in existing)
    target = min(max_x + STATION_STEP_X, STATION_LINE_END_X)
    if target > max_x:
        return target
    positions = linear_station_positions(len(existing) + 1)
    ordered = sorted(
        existing,
        key=lambda row: (float(row.get("pos_x") or 0), int(row.get("id") or 0)),
    )
    for slot, row in enumerate(ordered):
        update_station(int(row.get("id") or 0), pos_x=positions[slot], pos_y=STATION_ORIGIN_Y)
    return positions[-1]


def update_station(
    station_id: int,
    name: Optional[str] = None,
    pos_x: Optional[float] = None,
    pos_y: Optional[float] = None,
    rotation: Optional[float] = None,
) -> bool:
    sets: List[str] = []
    params: List[object] = []
    if name is not None:
        sets.append("name=?")
        params.append(str(name).strip())
    if pos_x is not None:
        sets.append("pos_x=?")
        params.append(float(pos_x))
    if pos_y is not None:
        sets.append("pos_y=?")
        params.append(float(pos_y))
    if rotation is not None:
        sets.append("rotation=?")
        params.append(float(rotation))
    if not sets:
        return True
    params.append(station_id)
    _exec(f"UPDATE line_stations SET {', '.join(sets)} WHERE id=?", tuple(params), commit=True)
    return True


def delete_station(station_id: int) -> bool:
    _exec("DELETE FROM line_stations WHERE id=?", (station_id,), commit=True)
    return True


def count_station_videos(station_id: int) -> int:
    row = _exec("SELECT COUNT(*) AS c FROM videos WHERE station_id=?", (station_id,), fetch="one") or {}
    return _to_int(row.get("c")) or 0


def list_station_video_counts(line_id: int) -> Dict[int, int]:
    rows = _exec(
        "SELECT station_id, COUNT(*) AS c FROM videos WHERE line_id=? AND station_id IS NOT NULL "
        "GROUP BY station_id",
        (line_id,),
        fetch="all",
    ) or []
    counts: Dict[int, int] = {}
    for row in rows:
        sid = _to_int(row.get("station_id"))
        if sid:
            counts[sid] = _to_int(row.get("c")) or 0
    return counts


# ---------------------------------------------------------------------------
# 项目成员
# ---------------------------------------------------------------------------

def add_project_member(project_id: int, username: str, role: str = "editor") -> bool:
    username = (username or "").strip()
    if not project_id or not username:
        return False
    if role not in _MEMBER_ROLES:
        role = "editor"
    existing = _exec(
        "SELECT role FROM project_members WHERE project_id=? AND username=?",
        (project_id, username),
        fetch="one",
    )
    if existing:
        if existing.get("role") != role:
            _exec(
                "UPDATE project_members SET role=? WHERE project_id=? AND username=?",
                (role, project_id, username),
                commit=True,
            )
        return True
    _exec(
        "INSERT INTO project_members (project_id, username, role) VALUES (?, ?, ?)",
        (project_id, username, role),
        commit=True,
    )
    return True


def remove_project_member(project_id: int, username: str) -> bool:
    _exec("DELETE FROM project_members WHERE project_id=? AND username=?", (project_id, username), commit=True)
    return True


def list_project_members(project_id: int) -> List[Dict[str, object]]:
    return _exec(
        "SELECT * FROM project_members WHERE project_id=? ORDER BY username ASC",
        (project_id,),
        fetch="all",
    )


def get_member_role(project_id: int, username: str) -> Optional[str]:
    """返回用户在指定项目中的成员角色；非成员返回 None。"""
    row = _exec(
        "SELECT role FROM project_members WHERE project_id=? AND username=?",
        (project_id, (username or "").strip()),
        fetch="one",
    )
    return str(row.get("role")) if row else None


def can_manage_project(user: Dict[str, object], project_id: int) -> bool:
    """项目级管理权限（管理成员/产线）：admin 或项目 owner。"""
    if not isinstance(user, dict) or not project_id:
        return False
    if str(user.get("role") or "") == "admin":
        return True
    username = str(user.get("username") or "").strip()
    if not username:
        return False
    return get_member_role(int(project_id), username) == "owner"


def user_visible_project_ids(username: str, role: Optional[str] = None) -> List[int]:
    """用户可见项目 id 列表。admin → 全部；普通用户 → 成员项目；无成员关系 → 默认项目（兼容）。"""
    username = (username or "").strip()
    if (role or "") == "admin":
        rows = _exec("SELECT id FROM projects ORDER BY id ASC", fetch="all")
        return [int(r["id"]) for r in rows]
    if not username:
        return []
    rows = _exec(
        "SELECT p.id AS pid FROM projects p JOIN project_members m ON m.project_id = p.id "
        "WHERE m.username=? AND p.status='active' ORDER BY p.id ASC",
        (username,),
        fetch="all",
    )
    ids = [int(r["pid"]) for r in rows]
    if ids:
        return ids
    default_p = get_project_by_code(DEFAULT_PROJECT_CODE)
    return [int(default_p["id"])] if default_p else []


def ensure_default_scope() -> Dict[str, int]:
    """确保默认项目与默认产线存在，返回 {'project_id': id, 'line_id': id}。"""
    project = get_project_by_code(DEFAULT_PROJECT_CODE)
    if not project:
        create_project(DEFAULT_PROJECT_CODE, DEFAULT_PROJECT_NAME, "迁移脚本自动创建的默认归属", "admin")
        project = get_project_by_code(DEFAULT_PROJECT_CODE)
    line = _exec(
        "SELECT id FROM production_lines WHERE project_id=? AND code=?",
        (project["id"], DEFAULT_LINE_CODE),
        fetch="one",
    )
    if not line:
        create_production_line(int(project["id"]), DEFAULT_LINE_CODE, DEFAULT_LINE_NAME)
        line = _exec(
            "SELECT id FROM production_lines WHERE project_id=? AND code=?",
            (project["id"], DEFAULT_LINE_CODE),
            fetch="one",
        )
    return {"project_id": int(project["id"]), "line_id": int(line["id"])}


# ---------------------------------------------------------------------------
# 视频
# ---------------------------------------------------------------------------

def register_video(
    project_id: int,
    filename: str,
    stored_path: str,
    line_id: Optional[int] = None,
    duration_sec: Optional[float] = None,
    size_bytes: Optional[int] = None,
    uploaded_by: Optional[str] = None,
    station_id: Optional[int] = None,
) -> Optional[int]:
    """登记视频（幂等：stored_path 已存在则更新元数据并返回既有 id）。"""
    if not project_id or not (stored_path or "").strip():
        return None
    row = _exec("SELECT id FROM videos WHERE stored_path=?", (stored_path,), fetch="one")
    if row:
        vid = _to_int(row.get("id"))
        _exec(
            "UPDATE videos SET project_id=?, line_id=?, station_id=?, filename=?, duration_sec=?, "
            "size_bytes=?, uploaded_by=? WHERE id=?",
            (project_id, line_id, station_id, filename, duration_sec, size_bytes, uploaded_by, vid),
            commit=True,
        )
        return vid
    return _to_int(
        _exec(
            "INSERT INTO videos (project_id, line_id, station_id, filename, stored_path, duration_sec, "
            "size_bytes, uploaded_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (project_id, line_id, station_id, filename, stored_path, duration_sec, size_bytes, uploaded_by),
            commit=True,
            want_lastrowid=True,
        )
    )


def get_video_by_path(stored_path: str) -> Optional[Dict[str, object]]:
    return _exec("SELECT * FROM videos WHERE stored_path=?", (stored_path,), fetch="one")


def get_video(video_id: int) -> Optional[Dict[str, object]]:
    return _exec("SELECT * FROM videos WHERE id=?", (video_id,), fetch="one")


def list_videos_for_user(
    username: str,
    role: Optional[str] = None,
    project_id: Optional[int] = None,
    line_id: Optional[int] = None,
) -> List[Dict[str, object]]:
    """按用户可见项目过滤视频；project_id/line_id 提供时进一步过滤。"""
    visible = user_visible_project_ids(username, role)
    if not visible:
        return []
    marks = ",".join("?" for _ in visible)
    sql = f"SELECT * FROM videos WHERE project_id IN ({marks})"
    params: List[object] = list(visible)
    if project_id:
        sql += " AND project_id=?"
        params.append(project_id)
    if line_id:
        sql += " AND line_id=?"
        params.append(line_id)
    sql += " ORDER BY id DESC"
    return _exec(sql, tuple(params), fetch="all")


# ---------------------------------------------------------------------------
# 任务
# ---------------------------------------------------------------------------

def create_task(
    username: str,
    model: Optional[str] = None,
    video_id: Optional[int] = None,
    project_id: Optional[int] = None,
    line_id: Optional[int] = None,
    progress_total: int = 0,
    progress_unit: Optional[str] = None,
) -> Optional[int]:
    username = (username or "").strip()
    if not username:
        return None
    return _to_int(
        _exec(
            "INSERT INTO tasks (username, video_id, project_id, line_id, model, status, phase, "
            "progress_current, progress_total, progress_unit) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
            (username, video_id, project_id, line_id, model, TASK_STATUS_RUNNING, "analyze", progress_total, progress_unit),
            commit=True,
            want_lastrowid=True,
        )
    )


def update_task_progress(task_id: int, phase: Optional[str], current: int, total: int) -> None:
    if not task_id:
        return
    _exec(
        "UPDATE tasks SET phase=?, progress_current=?, progress_total=? WHERE id=?",
        (phase, int(current), int(total), task_id),
        commit=True,
    )


def mark_task_running(task_id: int) -> None:
    """记录 started_at（后台线程真正开始执行时调用）。"""
    if not task_id:
        return
    if _use_mysql():
        _exec("UPDATE tasks SET status=?, started_at=NOW() WHERE id=?", (TASK_STATUS_RUNNING, task_id), commit=True)
    else:
        _exec(
            "UPDATE tasks SET status=?, started_at=datetime('now','localtime') WHERE id=?",
            (TASK_STATUS_RUNNING, task_id),
            commit=True,
        )


def finish_task(
    task_id: int,
    status: str,
    error: Optional[str] = None,
    md_path: Optional[str] = None,
    json_path: Optional[str] = None,
    video_path: Optional[str] = None,
    token_input: Optional[int] = None,
    token_output: Optional[int] = None,
    token_thinking: Optional[int] = None,
    token_total: Optional[int] = None,
) -> None:
    if not task_id:
        return
    if _use_mysql():
        _exec(
            "UPDATE tasks SET status=?, error=?, result_md_path=?, result_json_path=?, result_video_path=?, "
            "token_input=?, token_output=?, token_thinking=?, token_total=?, finished_at=NOW() WHERE id=?",
            (status, error, md_path, json_path, video_path, token_input, token_output, token_thinking, token_total, task_id),
            commit=True,
        )
    else:
        _exec(
            "UPDATE tasks SET status=?, error=?, result_md_path=?, result_json_path=?, result_video_path=?, "
            "token_input=?, token_output=?, token_thinking=?, token_total=?, "
            "finished_at=datetime('now','localtime') WHERE id=?",
            (status, error, md_path, json_path, video_path, token_input, token_output, token_thinking, token_total, task_id),
            commit=True,
        )


def get_task(task_id: int) -> Optional[Dict[str, object]]:
    return _exec("SELECT * FROM tasks WHERE id=?", (task_id,), fetch="one")


def get_latest_task_for_user(username: str) -> Optional[Dict[str, object]]:
    username = (username or "").strip()
    if not username:
        return None
    return _exec("SELECT * FROM tasks WHERE username=? ORDER BY id DESC LIMIT 1", (username,), fetch="one")


def list_tasks_for_project(
    project_id: int,
    line_id: Optional[int] = None,
    limit: int = 200,
) -> List[Dict[str, object]]:
    """项目内任务列表（按项目/产线过滤，最新在前）。"""
    if not project_id:
        return []
    lim = max(1, min(int(limit or 200), 1000))
    sql = "SELECT * FROM tasks WHERE project_id=?"
    params: List[object] = [project_id]
    if line_id:
        sql += " AND line_id=?"
        params.append(line_id)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(lim)
    return _exec(sql, tuple(params), fetch="all")


def fail_stale_tasks() -> List[Dict[str, object]]:
    """服务启动时调用：把遗留的 pending/running 任务标记为 failed(interrupted)。

    返回被中断的任务列表（含 username），供 /api/task_status 兜底响应使用。
    """
    stale = _exec(
        "SELECT id, username FROM tasks WHERE status IN (?, ?)",
        (TASK_STATUS_PENDING, TASK_STATUS_RUNNING),
        fetch="all",
    )
    if not stale:
        return []
    interrupted = "interrupted_by_restart"
    if _use_mysql():
        _exec(
            "UPDATE tasks SET status=?, error=?, phase='failed', finished_at=NOW() "
            "WHERE status IN (?, ?)",
            (TASK_STATUS_FAILED, interrupted, TASK_STATUS_PENDING, TASK_STATUS_RUNNING),
            commit=True,
        )
    else:
        _exec(
            "UPDATE tasks SET status=?, error=?, phase='failed', finished_at=datetime('now','localtime') "
            "WHERE status IN (?, ?)",
            (TASK_STATUS_FAILED, interrupted, TASK_STATUS_PENDING, TASK_STATUS_RUNNING),
            commit=True,
        )
    return stale


# ---------------------------------------------------------------------------
# 分析结果
# ---------------------------------------------------------------------------

def register_analysis_result(
    project_id: int,
    md_path: str,
    line_id: Optional[int] = None,
    task_id: Optional[int] = None,
    video_id: Optional[int] = None,
    json_path: Optional[str] = None,
    video_copy_path: Optional[str] = None,
    en_md_path: Optional[str] = None,
    stats_json: Optional[str] = None,
    created_by: Optional[str] = None,
) -> Optional[int]:
    """登记分析结果（幂等：md_path 已存在则返回既有 id）。"""
    md_path = (md_path or "").strip()
    if not project_id or not md_path:
        return None
    row = _exec("SELECT id FROM analysis_results WHERE md_path=?", (md_path,), fetch="one")
    if row:
        return _to_int(row.get("id"))
    return _to_int(
        _exec(
            "INSERT INTO analysis_results (task_id, video_id, project_id, line_id, md_path, json_path, "
            "video_copy_path, en_md_path, stats_json, version, created_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
            (task_id, video_id, project_id, line_id, md_path, json_path, video_copy_path, en_md_path, stats_json, created_by),
            commit=True,
            want_lastrowid=True,
        )
    )


def get_analysis_result_by_md(md_path: str) -> Optional[Dict[str, object]]:
    return _exec("SELECT * FROM analysis_results WHERE md_path=?", (md_path,), fetch="one")


def list_analysis_results_for_user(
    username: str,
    role: Optional[str] = None,
    project_id: Optional[int] = None,
    line_id: Optional[int] = None,
    limit: int = 500,
    offset: int = 0,
) -> List[Dict[str, object]]:
    """按用户可见项目过滤分析结果；project_id/line_id 提供时进一步过滤；支持分页。"""
    visible = user_visible_project_ids(username, role)
    if not visible:
        return []
    lim = max(1, min(int(limit or 500), 2000))
    off = max(0, int(offset or 0))
    marks = ",".join("?" for _ in visible)
    sql = f"SELECT * FROM analysis_results WHERE project_id IN ({marks})"
    params: List[object] = list(visible)
    if project_id:
        sql += " AND project_id=?"
        params.append(project_id)
    if line_id:
        sql += " AND line_id=?"
        params.append(line_id)
    sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.append(lim)
    params.append(off)
    return _exec(sql, tuple(params), fetch="all")


def backfill_detection_history_scope(project_id: int, line_id: Optional[int] = None) -> int:
    """把 project_id/line_id 为空的检测历史回填为指定归属，返回受影响行数。"""
    rowcount = _exec(
        "UPDATE detection_history SET project_id=?, line_id=? WHERE project_id IS NULL",
        (project_id, line_id),
        commit=True,
        want_rowcount=True,
    )
    return 0 if rowcount is None else int(rowcount)


# ---------------------------------------------------------------------------
# 结果修订留痕（阶段 3：结果查看增强）
# ---------------------------------------------------------------------------

MAX_RESULT_REVISIONS = 20  # 每个结果文件保留的最大修订版本数


def add_result_revision(
    result_path: str,
    actions: List[Dict[str, object]],
    created_by: Optional[str] = None,
    revision_note: Optional[str] = None,
) -> Optional[int]:
    """在修改结果前保存一份修订快照，返回修订 id。"""
    result_path = (result_path or "").strip()
    if not result_path or not isinstance(actions, list):
        return None
    try:
        actions_json = json.dumps(actions, ensure_ascii=False)
    except Exception:
        return None
    rev_id = _exec(
        "INSERT INTO result_revisions (result_path, actions_json, action_count, revision_note, created_by) "
        "VALUES (?, ?, ?, ?, ?)",
        (result_path, actions_json, len(actions), revision_note, created_by),
        commit=True,
        want_lastrowid=True,
    )
    _prune_result_revisions(result_path)
    return _to_int(rev_id)


def _prune_result_revisions(result_path: str) -> None:
    """超出保留上限时删除最旧的修订。"""
    try:
        rows = _exec(
            "SELECT id FROM result_revisions WHERE result_path=? ORDER BY id DESC",
            (result_path,),
            fetch="all",
        )
        for row in (rows or [])[MAX_RESULT_REVISIONS:]:
            _exec(
                "DELETE FROM result_revisions WHERE id=?",
                (row.get("id"),),
                commit=True,
            )
    except Exception:
        pass


def list_result_revisions(result_path: str, limit: int = 20) -> List[Dict[str, object]]:
    """列出某结果文件的修订历史（最新在前）。"""
    result_path = (result_path or "").strip()
    if not result_path:
        return []
    lim = max(1, min(int(limit or 20), MAX_RESULT_REVISIONS))
    return _exec(
        "SELECT id, result_path, action_count, revision_note, created_by, created_at "
        "FROM result_revisions WHERE result_path=? ORDER BY id DESC LIMIT ?",
        (result_path, lim),
        fetch="all",
    )


def get_result_revision(revision_id: int) -> Optional[Dict[str, object]]:
    """读取指定修订快照（含 actions JSON）。"""
    try:
        row = _exec(
            "SELECT * FROM result_revisions WHERE id=?",
            (int(revision_id),),
            fetch="one",
        )
    except Exception:
        return None
    if not row:
        return None
    try:
        row["actions"] = json.loads(row.get("actions_json") or "[]")
    except Exception:
        row["actions"] = []
    return row
