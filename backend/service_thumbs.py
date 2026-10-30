"""阶段 3：动作首帧缩略图服务。

设计要点：
- lazy 生成：前端加载结果时请求 /api/result_thumbs，后端首次调用时按动作区间抽帧，
  之后命中缓存直接返回清单。因此存量结果无需迁移即可获得缩略图。
- 缓存位置：result/thumbs/<结果基名>/a001.jpg + meta.json（记录动作区间签名）。
  该目录位于 /result/** 下，天然被阶段 0 的媒体鉴权覆盖。
- 幂等：meta.json 中的动作签名与当前结果一致且图片齐全时直接返回，否则重建。
- 优雅降级：找不到关联视频 / cv2 不可用时返回空清单，前端显示占位符不报错。
- en_ 前缀的英文结果与中文结果共享同一份缩略图（对应同一视频）。
"""

import hashlib
import json
import os
import threading
import urllib.parse
from typing import Dict, List, Optional

from backend.app_logging import get_logger
from backend.app_results_md import parse_md_content

logger = get_logger("thumbs")

THUMB_WIDTH = 160
THUMB_JPEG_QUALITY = 70
_THUMB_SEEK_OFFSET = 0.04  # 抽帧时刻相对动作起点的偏移，避免取到上一动作尾帧

_BUILD_LOCKS: Dict[str, threading.Lock] = {}
_BUILDS_GUARD = threading.Lock()

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover - 环境无 cv2 时优雅降级
    cv2 = None


def _lock_for(key: str) -> threading.Lock:
    with _BUILDS_GUARD:
        lock = _BUILD_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _BUILD_LOCKS[key] = lock
        return lock


def _normalize_result_path(rel_path: str) -> Optional[str]:
    """与 result_details 相同的路径校验：仅允许 result/ 下已存在的文件。"""
    rel_path = (rel_path or "").lstrip("/")
    rel_path = os.path.normpath(rel_path)
    if (
        not rel_path
        or rel_path.startswith("..")
        or rel_path.startswith("/")
        or not rel_path.startswith("result/")
    ):
        return None
    if not os.path.isfile(os.path.join(os.getcwd(), rel_path)):
        return None
    return rel_path


def _thumb_key(result_path: str) -> str:
    """缩略图目录键：去掉扩展名与 en_ 前缀（中英结果共享）。"""
    base = os.path.basename(result_path)
    base = os.path.splitext(base)[0]
    if base.lower().startswith("en_"):
        base = base[3:]
    return base


def _load_actions(result_path: str) -> List[Dict[str, object]]:
    """从 .md 或 .json 结果文件读取动作列表。"""
    lower = result_path.lower()
    try:
        if lower.endswith(".json"):
            with open(result_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            with open(result_path, "r", encoding="utf-8") as f:
                content = f.read()
            data = parse_md_content(content)
        if isinstance(data, dict):
            if isinstance(data.get("actions"), list):
                return data["actions"]
            for section in ("model_output", "output"):
                sec = data.get(section)
                if isinstance(sec, dict) and isinstance(sec.get("actions"), list):
                    return sec["actions"]
        if isinstance(data, list):
            return data
    except Exception:
        logger.warning("读取结果动作失败: %s", result_path, exc_info=True)
    return []


def _actions_signature(actions: List[Dict[str, object]]) -> str:
    pairs = []
    for act in actions or []:
        try:
            s = float(act.get("start_time"))
            e = float(act.get("end_time"))
            pairs.append([round(s, 2), round(e, 2)])
        except Exception:
            continue
    payload = json.dumps(pairs, ensure_ascii=False)
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def _find_video_for(result_path: str, base: str) -> Optional[str]:
    """为结果定位关联视频（绝对路径）：优先 result/ 副本，其次 data/ 原件。"""
    candidates: List[str] = []
    exact = os.path.join("result", base + ".mp4")
    candidates.append(exact)

    # analysis_results 表登记的视频副本（含迁移过的存量数据）
    try:
        from backend.app_db_org import get_analysis_result_by_md

        for key in (result_path, os.path.join("result", f"en_{base}.md")):
            row = get_analysis_result_by_md(key)
            if not row:
                row = get_analysis_result_by_md(os.path.basename(key))
            vid = str((row or {}).get("video_copy_path") or "")
            if vid:
                candidates.append(vid)
    except Exception:
        pass

    # 前缀匹配兜底
    for root in ("result", "data"):
        try:
            for name in sorted(os.listdir(root)):
                if name.startswith(base) and name.lower().endswith(".mp4"):
                    candidates.append(os.path.join(root, name))
        except Exception:
            continue

    for cand in candidates:
        if cand and os.path.isfile(os.path.join(os.getcwd(), cand)):
            return os.path.join(os.getcwd(), cand)
        if cand and os.path.isfile(cand):
            return cand
    return None


def _extract_thumbs(video_abs: str, actions: List[Dict[str, object]], out_dir: str) -> List[Optional[str]]:
    """用 cv2 按动作起点抽帧，返回与 actions 对齐的清单（失败项为 None）。"""
    if cv2 is None:
        return []
    cap = cv2.VideoCapture(video_abs)
    if not cap.isOpened():
        return []
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0:
            fps = 25.0
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        duration = frame_count / fps if frame_count and frame_count > 0 else None

        def clamp_seek(t: float) -> Optional[float]:
            if duration is not None:
                t = max(0.0, min(t, max(0.0, duration - 0.05)))
            return max(0.0, t)

        base_rel = os.path.relpath(out_dir, os.getcwd()).replace(os.sep, "/")
        thumbs: List[Optional[str]] = []
        for idx, act in enumerate(actions, 1):
            name = f"a{idx:03d}.jpg"
            try:
                start = float(act.get("start_time"))
                end = float(act.get("end_time"))
            except Exception:
                thumbs.append(None)
                continue
            t = start + _THUMB_SEEK_OFFSET
            if not (t < end):
                t = start
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(clamp_seek(t) * fps))
            ret, frame = cap.read()
            if not ret or frame is None:
                # 回退到动作中点再试一次
                mid = start + max(0.0, (end - start) / 2.0)
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(clamp_seek(mid) * fps))
                ret, frame = cap.read()
            if not ret or frame is None:
                thumbs.append(None)
                continue
            h, w = frame.shape[:2]
            if w > THUMB_WIDTH:
                nh = max(1, int(h * THUMB_WIDTH / w))
                frame = cv2.resize(frame, (THUMB_WIDTH, nh), interpolation=cv2.INTER_AREA)
            out_path = os.path.join(out_dir, name)
            if cv2.imwrite(out_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), THUMB_JPEG_QUALITY]):
                thumbs.append(f"{base_rel}/{name}")
            else:
                thumbs.append(None)
        return thumbs
    finally:
        cap.release()


def get_or_build_thumbs(rel_path: str) -> Dict[str, object]:
    """获取（或首次生成）某结果文件的动作首帧缩略图清单。"""
    rel_path = _normalize_result_path(rel_path or "")
    if not rel_path:
        return {"thumbs": [], "count": 0, "error": "invalid_path"}
    actions = _load_actions(rel_path)
    if not actions:
        return {"thumbs": [], "count": 0}
    base = _thumb_key(rel_path)
    out_dir = os.path.join("result", "thumbs", base)
    sig = _actions_signature(actions)
    meta_path = os.path.join(out_dir, "meta.json")

    # 命中缓存：签名一致且图片齐全
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        if meta.get("signature") == sig:
            thumbs: List[Optional[str]] = meta.get("thumbs") or []
            if len(thumbs) == len(actions) and all(
                (t is None) or os.path.isfile(os.path.join(os.getcwd(), t)) for t in thumbs
            ):
                return {"thumbs": thumbs, "count": len(thumbs)}
    except Exception:
        pass

    with _lock_for(base):
        # 双重检查：拿锁期间可能已被并发请求生成
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if meta.get("signature") == sig:
                thumbs = meta.get("thumbs") or []
                if len(thumbs) == len(actions) and all(
                    (t is None) or os.path.isfile(os.path.join(os.getcwd(), t)) for t in thumbs
                ):
                    return {"thumbs": thumbs, "count": len(thumbs)}
        except Exception:
            pass

        video_abs = _find_video_for(rel_path, base)
        if not video_abs:
            logger.info("结果 %s 未找到关联视频，跳过缩略图", rel_path)
            return {"thumbs": [], "count": len(actions)}
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception:
            logger.warning("创建缩略图目录失败: %s", out_dir, exc_info=True)
            return {"thumbs": [], "count": len(actions)}
        thumbs = _extract_thumbs(video_abs, actions, out_dir)
        if not thumbs:
            return {"thumbs": [], "count": len(actions)}
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"signature": sig, "thumbs": thumbs, "video": os.path.basename(video_abs)},
                    f,
                    ensure_ascii=False,
                )
        except Exception:
            logger.warning("写入缩略图元数据失败: %s", meta_path, exc_info=True)
        return {"thumbs": thumbs, "count": len(thumbs)}


def handle_result_thumbs(handler, user: Optional[Dict[str, object]], parsed_path) -> bool:
    """GET /api/result_thumbs?path=result/xxx.md|json"""
    try:
        params = urllib.parse.parse_qs(parsed_path.query or "")
        rel_path = (params.get("path") or [""])[0]
        data = get_or_build_thumbs(rel_path)
        handler.send_json(200, data)
    except Exception as e:
        logger.exception("生成缩略图失败")
        handler.send_json(500, {"error": str(e), "thumbs": [], "count": 0})
    return True
