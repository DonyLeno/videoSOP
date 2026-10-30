#!/usr/bin/env python3
"""阶段 1 存量数据迁移脚本：把 data/ 与 result/ 的既有文件登记入库。

行为（全部幂等，可重复执行）：
1. 创建「默认项目 / 默认产线」
2. 所有用户加入默认项目成员（admin → owner，其他 → editor）
3. data/ 下存量视频登记 videos 表（uploaded_by 依据 detection_history 推断，推断不出用 admin）
4. result/ 下存量分析结果登记 analysis_results 表（归属/模型/token 依据 detection_history 关联）
5. detection_history 中 project_id 为空的行回填默认归属

用法：在项目根目录执行 `python3 scripts/migrate_phase1.py`
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from backend.app_db import ensure_database, list_detection_history_for_migration, list_users  # noqa: E402
from backend.app_db_org import (  # noqa: E402
    add_project_member,
    backfill_detection_history_scope,
    ensure_default_scope,
    get_line_sop,
    get_video_by_path,
    register_analysis_result,
    register_video,
    update_production_line,
)
from backend.app_logging import get_logger, setup_logging  # noqa: E402

logger = get_logger("migrate_phase1")

VIDEO_EXTS = (".mp4", ".mov", ".avi", ".mkv", ".webm")


def _load_detection_history() -> list:
    """读取检测历史并按 result_path / video_name 建索引。"""
    try:
        return list_detection_history_for_migration(limit=2000)
    except Exception:
        logger.warning("读取 detection_history 失败，归属推断将退化为 admin", exc_info=True)
        return []


def _match_history_owner(md_name: str, history: list) -> dict:
    """根据结果文件名在检测历史中找归属（md 文件名 = result_path 的 basename）。"""
    for h in history:
        rp = str(h.get("result_path") or "")
        if rp and os.path.basename(rp) == md_name:
            return h
    return {}


def _infer_uploader_by_history(video_name: str, history: list) -> str:
    for h in history:
        vn = str(h.get("video_name") or "")
        if vn and os.path.basename(vn) == os.path.basename(video_name):
            return str(h.get("username") or "admin")
    return "admin"


def _extract_stats_json(json_path: str):
    if not json_path or not os.path.exists(json_path):
        return None
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        stats = (data or {}).get("stats")
        return json.dumps(stats, ensure_ascii=False) if stats is not None else None
    except Exception:
        return None


def _find_video_id_for_result(md_name: str, videos_by_stem: dict):
    """结果文件名形如 {video_base}_{timestamp}.md，取 videos 中 stem 为其前缀的最长匹配。"""
    stem = md_name[:-3] if md_name.endswith(".md") else md_name
    best = None
    best_len = 0
    for vstem, vid in videos_by_stem.items():
        if stem.startswith(vstem) and len(vstem) > best_len:
            best = vid
            best_len = len(vstem)
    return best


def main() -> int:
    setup_logging()
    ensure_database()

    stats = {"members": 0, "videos": 0, "results": 0, "history_backfilled": 0}
    history = _load_detection_history()

    # 1. 默认项目 / 产线
    scope = ensure_default_scope()
    project_id = scope["project_id"]
    line_id = scope["line_id"]
    logger.info("默认项目就绪: project_id=%s, line_id=%s", project_id, line_id)

    # 2. 全员加入默认项目
    try:
        users = list_users()
    except Exception:
        logger.exception("读取用户列表失败")
        users = []
    for u in users:
        username = str(u.get("username") or "")
        if not username:
            continue
        role = "owner" if str(u.get("role") or "") == "admin" else "editor"
        if add_project_member(project_id, username, role):
            stats["members"] += 1

    # 3. 存量视频登记
    if os.path.isdir("data"):
        for name in sorted(os.listdir("data")):
            if not name.lower().endswith(VIDEO_EXTS):
                continue
            stored_path = os.path.join("data", name)
            if not os.path.isfile(stored_path):
                continue
            try:
                size_bytes = os.path.getsize(stored_path)
            except OSError:
                size_bytes = None
            uploaded_by = _infer_uploader_by_history(name, history)
            vid = register_video(
                project_id=project_id,
                filename=name,
                stored_path=stored_path,
                line_id=line_id,
                size_bytes=size_bytes,
                uploaded_by=uploaded_by,
            )
            if vid:
                stats["videos"] += 1

    # videos stem 索引（供结果关联 video_id）
    videos_by_stem = {}
    for name in sorted(os.listdir("data")) if os.path.isdir("data") else []:
        if name.lower().endswith(VIDEO_EXTS):
            row = get_video_by_path(os.path.join("data", name))
            if row:
                videos_by_stem[os.path.splitext(name)[0]] = int(row["id"])

    # 4. 存量结果登记
    if os.path.isdir("result"):
        for name in sorted(os.listdir("result")):
            if not name.endswith(".md") or name.startswith("en_"):
                continue
            md_path = os.path.join("result", name)
            if not os.path.isfile(md_path):
                continue
            h = _match_history_owner(name, history)
            json_path = md_path[:-3] + ".json"
            if not os.path.exists(json_path):
                json_path = None
            video_copy_path = md_path[:-3] + ".mp4"
            if not os.path.exists(video_copy_path):
                video_copy_path = None
            en_md_path = os.path.join("result", f"en_{name}")
            if not os.path.exists(en_md_path):
                en_md_path = None
            video_id = _find_video_id_for_result(name, videos_by_stem)
            created_by = str(h.get("username") or "admin") if h else "admin"
            rid = register_analysis_result(
                project_id=project_id,
                md_path=md_path,
                line_id=line_id,
                video_id=video_id,
                json_path=json_path,
                video_copy_path=video_copy_path,
                en_md_path=en_md_path,
                stats_json=_extract_stats_json(json_path),
                created_by=created_by,
            )
            if rid:
                stats["results"] += 1

    # 5. 检测历史回填归属
    stats["history_backfilled"] = backfill_detection_history_scope(project_id, line_id)

    # 6. SOP 迁移：全局 data/SOP.md 首次灌入默认产线（产线级 SOP 优先；已配置则不覆盖）
    sop_file = os.path.join("data", "SOP.md")
    if os.path.isfile(sop_file):
        try:
            existing = get_line_sop(line_id)
            if existing is None or not str(existing).strip():
                with open(sop_file, "r", encoding="utf-8") as f:
                    sop_text = f.read()
                if sop_text.strip():
                    update_production_line(line_id, sop_content=sop_text)
                    stats["sop_migrated"] = 1
                    logger.info("已把 data/SOP.md 迁入默认产线 sop_content (line_id=%s)", line_id)
        except Exception:
            logger.warning("SOP 迁移默认产线失败", exc_info=True)
    stats.setdefault("sop_migrated", 0)

    logger.info(
        "迁移完成: members=%d, videos=%d, results=%d, history_backfilled=%d, sop_migrated=%d",
        stats["members"],
        stats["videos"],
        stats["results"],
        stats["history_backfilled"],
        stats["sop_migrated"],
    )
    print(json.dumps({"status": "success", "project_id": project_id, "line_id": line_id, "stats": stats}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
