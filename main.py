import argparse
import datetime
import getpass
import json
import os
import random
import re
import time
import base64
import io
from typing import Any, Dict, List, Optional, TypedDict, Tuple, Union, Callable

import cv2  # type: ignore
from PIL import Image as PILImage
from google import genai
from google.genai import errors

try:
    import openai
except ImportError:
    openai = None


def _truncate_text(value: Any, limit: int = 2000) -> str:
    text = "" if value is None else str(value)
    if len(text) <= limit:
        return text
    return text[:limit] + f"...(truncated,len={len(text)})"


def _redact_headers(headers: Any) -> Dict[str, str]:
    out: Dict[str, str] = {}
    try:
        items = list(getattr(headers, "items")())
    except Exception:
        try:
            items = list(dict(headers).items())
        except Exception:
            items = []
    for k, v in items:
        key = str(k)
        lower = key.lower()
        if lower in ("authorization", "proxy-authorization", "x-api-key", "api-key"):
            out[key] = "***"
        else:
            out[key] = _truncate_text(v, 200)
    return out


def _contents_summary(contents: List[Any]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {"count": len(contents), "types": []}
    types: List[str] = []
    for item in contents[:20]:
        if isinstance(item, str):
            types.append("text")
        elif isinstance(item, PILImage.Image):
            types.append("image")
        else:
            types.append(type(item).__name__)
    if len(contents) > 20:
        types.append(f"...(+{len(contents) - 20} more)")
    summary["types"] = types
    return summary


def _extract_section(content: str, section_header: str) -> str:
    pattern = re.escape(section_header) + r"(.*?)(?=\n##|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def _parse_table(table_text: str) -> Tuple[Optional[str], Optional[str], List[str]]:
    lines = table_text.strip().split('\n')
    lines = [line.strip() for line in lines if line.strip()]
    if not lines:
        return None, None, []
    table_lines = [line for line in lines if line.startswith('|')]
    if len(table_lines) < 2:
        return None, None, []
    return table_lines[0], table_lines[1], table_lines[2:]


def _clean_section_content(content: str) -> str:
    """
    Removes leading/trailing whitespace and `---` separators.
    """
    content = content.strip()
    # Remove trailing --- if present
    if content.endswith("---"):
        content = content[:-3].strip()
    # Remove leading --- if present
    if content.startswith("---"):
        content = content[3:].strip()
    return content


def _parse_deep_dive_section(content: str) -> Dict[str, List[str]]:
    """
    Parses the Deep Dive Findings section into categories.
    """
    findings: Dict[str, List[str]] = {
        "Stability": [],
        "Ergonomics": [],
        "Cognitive Load": [],
        "Material/Environment": []
    }
    
    # Split content by lines starting with * **
    # Pattern: ^\* \*\*(.*?)\:\*\*(.*?)(?=(?:^\*\s+\*\*)|$)
    # Note: Using re.MULTILINE to match start of lines
    
    matches = re.finditer(r"(?m)^\*\s+\*\*(.*?)\:\*\*(.*?)(?=(?:^\*\s+\*\*)|$)", content, re.DOTALL)
    
    for match in matches:
        header = match.group(1).strip() # e.g. "稳定性 (Stability)"
        body = match.group(2).strip()
        
        # Determine category
        if "Stability" in header or "稳定性" in header:
            findings["Stability"].append(body)
        elif "Ergonomics" in header or "人机工程" in header:
            findings["Ergonomics"].append(body)
        elif "Cognitive" in header or "认知" in header:
            findings["Cognitive Load"].append(body)
        elif "Material" in header or "Environment" in header or "物料" in header or "环境" in header:
            findings["Material/Environment"].append(body)
            
    return findings


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except Exception:
        return default
    return value if value > 0 else default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except Exception:
        return default
    return value if value > 0 else default


def _get_error_code(err: BaseException) -> Optional[int]:
    code = getattr(err, "code", None)
    if isinstance(code, int):
        return code
    status = getattr(err, "status", None)
    if isinstance(status, int):
        return status
    return None


def _is_retryable_genai_error(err: BaseException) -> bool:
    code = _get_error_code(err)
    if code in (408, 429, 500, 502, 503, 504):
        return True
    text = str(err).lower()
    if "overloaded" in text or "unavailable" in text or "timeout" in text:
        return True
    return False


def _sleep_backoff(attempt: int, base_delay: float, max_delay: float) -> None:
    delay = min(max_delay, base_delay * (2 ** max(0, attempt - 1)))
    delay *= random.uniform(0.6, 1.4)
    time.sleep(delay)


def _generate_content_with_retry(
    client: genai.Client,
    model: str,
    contents: List[Any],
    config: Dict[str, Any],
    *,
    fallback_model: Optional[str] = None,
) -> Tuple[Any, str]:
    max_attempts = _env_int("GENAI_MAX_ATTEMPTS", 6)
    base_delay = _env_float("GENAI_RETRY_BASE_DELAY_SECONDS", 1.0)
    max_delay = _env_float("GENAI_RETRY_MAX_DELAY_SECONDS", 20.0)
    switch_after = _env_int("GENAI_SWITCH_TO_FALLBACK_AFTER_ATTEMPTS", 3)

    used_model = model
    last_err: Optional[BaseException] = None

    for attempt in range(1, max_attempts + 1):
        try:
            print(
                json.dumps(
                    {
                        "event": "genai.generate_content.request",
                        "attempt": attempt,
                        "max_attempts": max_attempts,
                        "model": used_model,
                        "config_keys": sorted(list(config.keys())),
                        "contents": _contents_summary(contents),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            resp = client.models.generate_content(
                model=used_model,
                contents=contents,
                config=config,
            )
            print(
                json.dumps(
                    {
                        "event": "genai.generate_content.response",
                        "model": used_model,
                        "text_preview": _truncate_text(getattr(resp, "text", None), 2000),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            return resp, used_model
        except (errors.ClientError, errors.ServerError) as e:
            last_err = e
            code = _get_error_code(e)
            if code == 404 and fallback_model and used_model != fallback_model:
                used_model = fallback_model
                continue
            if (
                fallback_model
                and used_model != fallback_model
                and attempt >= switch_after
                and code in (429, 503)
            ):
                used_model = fallback_model
                continue
            if attempt >= max_attempts or not _is_retryable_genai_error(e):
                raise
            print(f"GenAI 请求失败（{code or 'unknown'}），第 {attempt}/{max_attempts} 次重试中...", flush=True)
            _sleep_backoff(attempt, base_delay, max_delay)

    raise last_err if last_err is not None else RuntimeError("GenAI request failed")


def _normalize_model_name(model: str) -> str:
    text = str(model or "").strip()
    if text in ("kimi-2.5", "GenieviewK2.5", "genieviewk2.5", "genieview-k2.5"):
        return "kimi-k2.5"
    if text == "gemini2.5flash":
        return "gemini-1.5-flash"
    if text == "gemini3flash":
        return "gemini-2.0-flash"
    return text or model


class DetectedAction(TypedDict):
    label: str
    start_time: float
    end_time: float
    confidence: float


class ActionTypeStat(TypedDict):
    label: str
    count: int
    avg_duration: float


class ActionStats(TypedDict):
    total_actions: int
    unique_action_type_count: int
    avg_action_duration: float
    action_types: List[ActionTypeStat]


class ModelOutput(TypedDict, total=False):
    actions: List[DetectedAction]
    stats: ActionStats
    advice: List[str]


def build_prompt(use_frames: bool = False) -> str:
    base = "你是一个视频动作检测与统计助手。\n"
    if use_frames:
        base += (
            "我提供了一系列按固定帧率采样的高清图片（带有时间戳）。\n"
            "请仔细观察每一帧的细节，重建动作序列。\n"
        )
    else:
        base += "请基于视频内容提取动作序列，并输出结构化 JSON。\n"
    
    return base + (
        "要求：\n"
        "- actions: 动作列表，按时间顺序。\n"
        "- 每个动作包含：label（简短中文动词短语）、start_time（秒）、end_time（秒）、confidence（0-1）。\n"
        "- 合并规则：如果相邻采样帧（或相邻时间段）识别出的 action 的 label 相同，则合并为一个动作，延长 end_time，不要输出重复相邻动作。\n"
        "- stats: 统计信息，包含：\n"
        "  - total_actions: 动作总数\n"
        "  - unique_action_type_count: 动作种类数\n"
        "  - avg_action_duration: 整体平均持续时间（秒）\n"
        "  - action_types: 每种动作的统计列表，每个包含 label, count, avg_duration\n"
        "- advice: 工艺流程改进建议，给出 3-8 条具体的改进意见（偏向流程优化、操作规范、效率提升等）。\n"
        "只输出 JSON，不要输出任何额外文字。"
    )


def load_prompt_from_file(path: str) -> Optional[str]:
    raw = str(path or "").strip()
    if not raw or not os.path.exists(raw):
        return None
    try:
        with open(raw, "r", encoding="utf-8") as f:
            content = f.read().strip()
            
        # Try to parse as JSON first
        if content.startswith("{"):
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    prompt = data.get("prompt")
                    if isinstance(prompt, str):
                        return prompt.strip() or None
            except json.JSONDecodeError:
                pass
                
        # If not JSON or no prompt field, return raw content
        return content or None
    except Exception:
        return None


def build_response_json_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "required": ["actions", "stats", "advice"],
        "properties": {
            "actions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["label", "start_time", "end_time", "confidence"],
                    "properties": {
                        "label": {"type": "string"},
                        "start_time": {"type": "number", "minimum": 0},
                        "end_time": {"type": "number", "minimum": 0},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            },
            "stats": {
                "type": "object",
                "required": [
                    "total_actions",
                    "unique_action_type_count",
                    "avg_action_duration",
                    "action_types",
                ],
                "properties": {
                    "total_actions": {"type": "integer", "minimum": 0},
                    "unique_action_type_count": {"type": "integer", "minimum": 0},
                    "avg_action_duration": {"type": "number", "minimum": 0},
                    "action_types": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["label", "count", "avg_duration"],
                            "properties": {
                                "label": {"type": "string"},
                                "count": {"type": "integer", "minimum": 0},
                                "avg_duration": {"type": "number", "minimum": 0},
                            },
                        },
                    },
                },
            },
            "advice": {"type": "array", "items": {"type": "string"}},
        },
    }


def _is_file_state(value: Any, name: str) -> bool:
    if value is None:
        return False
    text = str(value)
    return text == name or text.endswith(f".{name}")


def wait_until_file_active(client: genai.Client, file_name: str) -> Any:
    if not file_name:
        raise SystemExit("Upload returned empty file name.")
    last_info = None
    last_state = None
    for _ in range(90):
        try:
            last_info = client.files.get(name=file_name)
        except (errors.ClientError, errors.ServerError) as e:
            if _is_retryable_genai_error(e):
                time.sleep(1.0)
                continue
            raise
        state = str(getattr(last_info, "state", None))
        if state != last_state:
            last_state = state
            print(
                json.dumps(
                    {"event": "genai.files.get", "file_name": file_name, "state": state},
                    ensure_ascii=False,
                ),
                flush=True,
            )
        if _is_file_state(last_info.state, "ACTIVE"):
            return last_info
        if _is_file_state(last_info.state, "FAILED"):
            raise SystemExit(f"File processing failed: {last_info.error}")
        time.sleep(1.0)
    raise SystemExit(f"File not ACTIVE after waiting: {last_info}")


def parse_actions(value: Any) -> List[DetectedAction]:
    actions: List[DetectedAction] = []
    if not isinstance(value, list):
        return actions
    for item in value:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip()
        if not label:
            continue
        try:
            start = float(item.get("start_time", 0.0))
            end = float(item.get("end_time", start))
            conf = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            continue
        if start < 0:
            start = 0.0
        if end < start:
            end = start
        if conf < 0:
            conf = 0.0
        if conf > 1:
            conf = 1.0
        actions.append(
            DetectedAction(
                label=label,
                start_time=start,
                end_time=end,
                confidence=conf,
            )
        )
    return actions


def compute_stats(actions: List[DetectedAction]) -> ActionStats:
    by_label: Dict[str, List[float]] = {}
    durations: List[float] = []
    for a in actions:
        duration = max(0.0, float(a["end_time"]) - float(a["start_time"]))
        durations.append(duration)
        by_label.setdefault(a["label"], []).append(duration)

    action_types: List[ActionTypeStat] = []
    for label, ds in sorted(by_label.items(), key=lambda x: (-len(x[1]), x[0])):
        avg = sum(ds) / len(ds) if ds else 0.0
        action_types.append(ActionTypeStat(label=label, count=len(ds), avg_duration=avg))

    overall_avg = sum(durations) / len(durations) if durations else 0.0
    return ActionStats(
        total_actions=len(actions),
        unique_action_type_count=len(by_label),
        avg_action_duration=overall_avg,
        action_types=action_types,
    )


def extract_frames(video_path: str, fps: float) -> List[Any]:
    """
    Extracts frames from video at a target FPS.
    Returns a list of alternating [timestamp_text, PILImage, ...].
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    if video_fps <= 0:
        # Fallback if FPS is not detected
        video_fps = 30.0

    # Calculate frame interval (e.g. if video is 30fps and target is 3fps, take every 10th frame)
    step = max(1, int(round(video_fps / fps)))
    
    content_parts: List[Any] = []
    frame_idx = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_idx % step == 0:
            # Timestamp in seconds
            current_time = frame_idx / video_fps
            timestamp_label = f"{current_time:.2f}s"
            
            # Convert BGR (OpenCV) to RGB (PIL)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = PILImage.fromarray(rgb_frame)
            
            # Interleave timestamp text and image
            content_parts.append(timestamp_label)
            content_parts.append(pil_img)
            content_parts.append(f"frame_{frame_idx}_{timestamp_label}.jpg")
            
        frame_idx += 1
        
    cap.release()
    return content_parts


def encode_image(image: PILImage.Image) -> str:
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def _iter_image_files(root: str) -> List[str]:
    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    files: List[str] = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext in exts:
                files.append(os.path.join(dirpath, name))
    files.sort()
    return files


def _timestamp_label_from_filename(path: str) -> Optional[str]:
    name = os.path.basename(path)
    m = re.search(r"_([0-9]+(?:\.[0-9]+)?)\.(?:jpg|jpeg|png|webp|bmp)$", name, flags=re.IGNORECASE)
    if not m:
        return None
    try:
        ts = float(m.group(1))
    except Exception:
        return None
    if not (ts == ts) or ts < 0:
        return None
    return f"{ts:.2f}s"


def load_frames_from_dir(frames_dir: str, max_frames: int = 1000) -> List[Any]:
    frames_dir = os.path.abspath(frames_dir)
    if not os.path.isdir(frames_dir):
        raise ValueError(f"Frames directory not found: {frames_dir}")
    paths = _iter_image_files(frames_dir)
    if len(paths) > max_frames:
        raise ValueError("too_many_frames")
    content_parts: List[Any] = []
    for path in paths:
        ts = _timestamp_label_from_filename(path) or "0.00s"
        try:
            img = PILImage.open(path)
            img = img.convert("RGB")
        except Exception as e:
            raise ValueError(f"Failed to read image: {path}: {e}")
        content_parts.append(ts)
        content_parts.append(img)
        content_parts.append(os.path.basename(path))
    return content_parts


def _clear_kimi_files(client: Any) -> None:
    try:
        # Attempt to list files. The return type depends on the SDK version,
        # but typically has a .data property or is iterable.
        resp = client.files.list()
        files = getattr(resp, "data", [])
        if not files and isinstance(resp, list):
            files = resp

        count = 0
        for f in files:
            fid = getattr(f, "id", None)
            if fid:
                try:
                    client.files.delete(fid)
                    count += 1
                except Exception:
                    pass
        if count > 0:
            print(
                json.dumps(
                    {"event": "kimi.files.cleared", "count": count},
                    ensure_ascii=False,
                ),
                flush=True,
            )
    except Exception:
        # Ignore errors during cleanup (e.g. network issues, empty list)
        pass


def _parse_timestamp_to_seconds(ts_str: str) -> float:
    ts_str = ts_str.strip()
    try:
        # 1. Try HH:MM:SS.mmm format
        if ':' in ts_str:
            parts = ts_str.split(':')
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                 return int(parts[0]) * 60 + float(parts[1])
        
        # 2. Try seconds format (e.g. "60.00s", "60.00", "60s")
        # Remove 's' suffix if present
        lower_ts = ts_str.lower()
        if lower_ts.endswith('s'):
            ts_str = ts_str[:-1].strip()
        
        return float(ts_str)
    except Exception:
        pass
    return 0.0


def _seconds_to_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    # 2FPS means 0.5s precision. Let's use 3 decimal places to be safe and match prompt example.
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def _merge_batches_python(result_dir: str, video_name: str, batch_count: int) -> str:
    final_lines = []
    global_seq = 1
    
    # Standard columns as per prompt.md
    STANDARD_HEADERS = [
        "序号", "动作描述", "SOP 操作步骤", "左手状态", "右手状态", 
        "预估耗时(s)", "增值/非增值", "时间段"
    ]
    
    # Keywords to identify columns in source files (fuzzy match)
    COL_KEYWORDS = {
        "序号": ["序号", "No", "Seq"],
        "动作描述": ["动作描述", "动作", "Element", "Description"],
        "SOP 操作步骤": ["SOP", "步骤", "Step"],
        "左手状态": ["左手", "Left"],
        "右手状态": ["右手", "Right"],
        "预估耗时(s)": ["耗时", "Time", "Duration"],
        "增值/非增值": ["增值", "VA", "NVA", "Value"],
        "时间段": ["时间段", "Range", "Timestamp"]
    }

    # 1. Scan and Sort Files
    all_files = [f for f in os.listdir(result_dir) if f.endswith(".md") and not f.startswith(".")]
    
    def get_sort_key_and_offset(fname):
        # Try to match "batch_N.md"
        m_batch = re.match(r"batch_(\d+)\.md", fname)
        if m_batch:
            idx = int(m_batch.group(1))
            # Assuming 60 frames per batch.
            # If 2FPS, duration is 30s. If 1FPS, duration is 60s.
            # User said "Reference now each action is sampled at 2FPS".
            # So we default to 30s offset for batch_N files.
            return idx, (idx - 1) * 30.0
            
        # Try to match "start_end.md" e.g. "0.00.jpg_59.00.jpg.md"
        # Extract first float
        m_float = re.match(r"^(\d+(?:\.\d+)?)", fname)
        if m_float:
            val = float(m_float.group(1))
            return val, val
            
        return 999999, 0.0

    # Sort files
    files_with_offset = []
    for f in all_files:
        key, offset = get_sort_key_and_offset(f)
        files_with_offset.append((f, offset))
    
    # Sort by key (which is effectively the offset or batch index)
    files_with_offset.sort(key=lambda x: get_sort_key_and_offset(x[0])[0])
    
    print(f"Found {len(files_with_offset)} batch files to merge:")
    for f, off in files_with_offset:
        print(f"  - {f} (offset={off})")

    for i, (fname, offset) in enumerate(files_with_offset):
        batch_path = os.path.join(result_dir, fname)
            
        with open(batch_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        # State: 0=Searching Header, 1=Header Found, 2=Separator Found, 3=Rows, 4=Finished
        state = 0
        
        # Accumulator for time within this batch
        # Start at the batch offset (e.g. 0.0, 60.0, etc.)
        current_batch_time = offset

        # Mapping from Standard Index -> Source Index
        col_map = {} 
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
                
            is_pipe = stripped.startswith("|")
            is_sep = "---" in stripped and is_pipe
            
            if state == 0: # Searching for header
                if is_pipe and not is_sep:
                    # Check if it looks like a header (contains "序号" or "动作")
                    if "序号" in line or "动作" in line:
                        state = 1
                        
                        # Parse source headers
                        raw_parts = [p.strip() for p in stripped.split("|")]
                        src_headers = []
                        src_indices = []
                        
                        for idx, p in enumerate(raw_parts):
                            if p: # Keep non-empty parts
                                src_headers.append(p)
                                src_indices.append(idx)
                        
                        # Build column map
                        col_map = {}
                        used_src_indices = set()
                        
                        for std_idx, std_name in enumerate(STANDARD_HEADERS):
                            keywords = COL_KEYWORDS.get(std_name, [])
                            found_idx = -1
                            
                            # Try to find a matching source column
                            for h_idx, src_name in enumerate(src_headers):
                                real_idx = src_indices[h_idx]
                                if real_idx in used_src_indices:
                                    continue
                                for kw in keywords:
                                    if kw in src_name:
                                        found_idx = real_idx
                                        break
                                if found_idx != -1:
                                    break
                            
                            if found_idx != -1:
                                col_map[std_idx] = found_idx
                                used_src_indices.add(found_idx)
                            else:
                                pass

                        # If this is the first batch, write the STANDARD header
                        if i == 0:
                            header_line = "| " + " | ".join(STANDARD_HEADERS) + " |\n"
                            final_lines.append(header_line)
            
            elif state == 1: # Header found, looking for separator
                if is_sep:
                    state = 2
                    if i == 0:
                        # Write standard separator
                        sep_line = "| " + " | ".join([":---"] * len(STANDARD_HEADERS)) + " |\n"
                        final_lines.append(sep_line)
                elif is_pipe: 
                    # Missing separator, this is a row!
                    if i == 0:
                        # Write standard separator since we missed it
                        sep_line = "| " + " | ".join([":---"] * len(STANDARD_HEADERS)) + " |\n"
                        final_lines.append(sep_line)
                    state = 3
                    # Fall through to process this row
            
            elif state == 2: # Separator found, expect rows
                state = 3
                # Fall through to process this row
            
            if state == 3: # Processing rows
                if is_pipe and not is_sep:
                    parts = [p.strip() for p in stripped.split("|")]
                    
                    if len(parts) < 3: 
                        continue

                    # Reconstruct row based on col_map
                    new_parts = [""] * len(STANDARD_HEADERS)
                    for std_idx in range(len(STANDARD_HEADERS)):
                        src_idx = col_map.get(std_idx)
                        if src_idx is not None and src_idx < len(parts):
                            new_parts[std_idx] = parts[src_idx]
                        else:
                            new_parts[std_idx] = "-" # Default value
                    
                    # Now apply logic (Sequence, Time, SOP) on the STANDARDIZED row
                    
                    # 1. Update Sequence Number (Index 0: 序号)
                    new_parts[0] = str(global_seq)
                    global_seq += 1
                    
                    # 2. Update Time (Index 7: 时间段)
                    # Recalculate based on Duration and Batch Offset
                    time_idx = 7
                    duration_idx = 5
                    
                    parsed_times = False
                    start_t = 0.0
                    end_t = 0.0

                    # Try to parse time column first
                    src_time_idx = col_map.get(time_idx)
                    if src_time_idx is not None and src_time_idx < len(parts):
                        time_str = parts[src_time_idx].strip()
                        if "-" in time_str:
                             t_parts = time_str.split("-")
                             if len(t_parts) >= 2:
                                 try:
                                     s_local = _parse_timestamp_to_seconds(t_parts[0])
                                     e_local = _parse_timestamp_to_seconds(t_parts[1])
                                     
                                     # Heuristic: If parsed time is greater than offset, assume absolute time
                                     # (or if offset is 0, it doesn't matter)
                                     # This handles cases where LLM outputs absolute timestamps
                                     if s_local >= offset:
                                         start_t = s_local
                                         end_t = e_local
                                     else:
                                         start_t = s_local + offset
                                         end_t = e_local + offset
                                     
                                     current_batch_time = end_t
                                     parsed_times = True
                                 except:
                                     pass

                    if not parsed_times:
                        try:
                            duration_str = new_parts[duration_idx].strip()
                            match_dur = re.search(r"([\d\.]+)", duration_str)
                            if match_dur:
                                duration_val = float(match_dur.group(1))
                            else:
                                duration_val = 0.5
                        except Exception:
                            duration_val = 0.5
                        
                        # Quantize duration to nearest 2FPS frame (0.5s)
                        frames = round(duration_val * 2.0)
                        if frames < 1: frames = 1 
                        duration_val = frames / 2.0
                        
                        start_t = current_batch_time
                        end_t = start_t + duration_val
                        current_batch_time = end_t
                    
                    new_parts[time_idx] = f"{_seconds_to_timestamp(start_t)} - {_seconds_to_timestamp(end_t)}"

                    # 3. Normalize SOP Column (Index 2: SOP 操作步骤)
                    sop_idx = 2
                    sop_content = new_parts[sop_idx]
                    match = re.search(r'(?i)(?:SOP\s*step|中文步骤|SOP|步骤|step)\s*(\d+)', sop_content)
                    if match:
                        new_parts[sop_idx] = f"SOP {match.group(1)}"
                            
                    # Construct line
                    final_lines.append("| " + " | ".join(new_parts) + " |\n")
                    
                else:
                    state = 4
            
            elif state == 4: # Finished table, ignore rest
                continue

    return "".join(final_lines)


def analyze_video_openai(
    api_key: str,
    video_path: str,
    model: str,
    sample_fps: float = 0.0,
    frames_dir: Optional[str] = None,
    prompt_override: Optional[str] = None,
    output_stem: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Tuple[Dict[str, Any], List[DetectedAction]]:
    if not openai:
        raise ImportError("openai module not installed. Please install 'openai'.")

    if sample_fps <= 0:
        sample_fps = 2.0
    
    if frames_dir:
        print(f"Loading frames from directory: {frames_dir}", flush=True)
        frames_data = load_frames_from_dir(frames_dir, max_frames=1000)
    else:
        print(f"Extracting frames for {model} at {sample_fps} FPS...")
        frames_data = extract_frames(video_path, sample_fps)
    if not frames_data:
        raise ValueError("No frames extracted from video.")
    
    print(f"Extracted {len(frames_data) // 2} frames.")

    prompt_text = (prompt_override or "").strip() or build_prompt(use_frames=True)
    
    # Inject SOP content into prompt if provided (redundant check if already added in setup, but safe)
    # prompt_text logic handled in main() where sop_content is merged into prompt_override
        
    frames: List[Tuple[str, PILImage.Image, str]] = []
    for i in range(0, len(frames_data), 3):
        ts = str(frames_data[i])
        img = frames_data[i + 1]
        fname = str(frames_data[i + 2])
        if isinstance(img, PILImage.Image):
            frames.append((ts, img, fname))

    used_model = _normalize_model_name(model)
    base_url = "https://api.moonshot.cn/v1"
    print(
        json.dumps(
            {
                "event": "moonshot.chat_completions.request",
                "model": used_model,
                "requested_model": model,
                "base_url": base_url,
                "timeout_seconds": 60.0,
                "frame_count": len(frames),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    http_client = None
    try:
        import httpx  # type: ignore

        def _on_request(request: Any) -> None:
            try:
                content_length = request.headers.get("content-length")
                if not content_length:
                    try:
                        content_length = str(len(request.content or b""))
                    except Exception:
                        content_length = None
                print(
                    json.dumps(
                        {
                            "event": "http.request",
                            "method": getattr(request, "method", None),
                            "url": str(getattr(request, "url", "")),
                            "headers": _redact_headers(getattr(request, "headers", {})),
                            "content_length": content_length,
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
            except Exception:
                return

        def _on_response(response: Any) -> None:
            try:
                print(
                    json.dumps(
                        {
                            "event": "http.response",
                            "status_code": getattr(response, "status_code", None),
                            "url": str(getattr(getattr(response, "request", None), "url", "")),
                            "headers": _redact_headers(getattr(response, "headers", {})),
                            "body_preview": _truncate_text(getattr(response, "text", None), 2000),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
            except Exception:
                return

        http_client = httpx.Client(event_hooks={"request": [_on_request], "response": [_on_response]})
    except Exception:
        http_client = None

    client = openai.OpenAI(api_key=api_key, base_url=base_url, http_client=http_client)
    
    # Clean up existing files in Kimi storage before starting new analysis
    _clear_kimi_files(client)

    try:
        def _extract_json_content(content: str) -> Any:
            text = content or "{}"
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].strip()
            try:
                return json.loads(text)
            except Exception:
                return {}

        def _merge_adjacent_actions(items: List[DetectedAction], gap_seconds: float = 0.15) -> List[DetectedAction]:
            if not items:
                return []
            sorted_items = sorted(items, key=lambda x: (float(x["start_time"]), float(x["end_time"])))
            merged: List[DetectedAction] = [
                DetectedAction(
                    label=str(sorted_items[0]["label"]),
                    start_time=float(sorted_items[0]["start_time"]),
                    end_time=float(sorted_items[0]["end_time"]),
                    confidence=float(sorted_items[0]["confidence"]),
                )
            ]
            for item in sorted_items[1:]:
                last = merged[-1]
                if (
                    str(item["label"]) == str(last["label"])
                    and float(item["start_time"]) <= float(last["end_time"]) + gap_seconds
                ):
                    last["end_time"] = max(float(last["end_time"]), float(item["end_time"]))
                    last["confidence"] = max(float(last["confidence"]), float(item["confidence"]))
                    continue
                merged.append(
                    DetectedAction(
                        label=str(item["label"]),
                        start_time=float(item["start_time"]),
                        end_time=float(item["end_time"]),
                        confidence=float(item["confidence"]),
                    )
                )
            return merged

        prompt_tokens_total: Optional[int] = 0
        completion_tokens_total: Optional[int] = 0
        total_tokens_total: Optional[int] = 0

        all_actions: List[DetectedAction] = []
        batch_size = 60 # User requested batch size 60
        
        # Create result directory for this video
        video_name = output_stem or os.path.splitext(os.path.basename(video_path))[0]
        result_dir = os.path.join("result", video_name)
        os.makedirs(result_dir, exist_ok=True)

        idx = 0
        batch_index = 0
        while idx < len(frames):
            if progress_callback:
                progress_callback(idx, len(frames))
            batch_index += 1
            current_size = min(batch_size, len(frames) - idx)
            while True:
                batch = frames[idx : idx + current_size]
                messages_content: List[Dict[str, Any]] = [{"type": "text", "text": prompt_text}]
                for ts, img, _ in batch:
                    messages_content.append({"type": "text", "text": f"Timestamp: {ts}"})
                    b64 = encode_image(img)
                    messages_content.append(
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    )
                try:
                    print(
                        json.dumps(
                            {
                                "event": "moonshot.chat_completions.request.batch",
                                "model": used_model,
                                "requested_model": model,
                                "batch_index": batch_index,
                                "batch_frame_count": len(batch),
                                "batch_start": idx,
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                    response = client.chat.completions.create(
                        model=used_model,
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": messages_content},
                        ],
                        temperature=1,
                        timeout=300.0,
                    )
                    content = response.choices[0].message.content or "{}"

                    # Save batch result to MD file
                    # Naming rule: batch start image suffix + batch end image suffix
                    start_fname = batch[0][2]
                    end_fname = batch[-1][2]
                    
                    def _get_suffix(s: str) -> str:
                        if "_" in s:
                            return s.rsplit("_", 1)[1]
                        return s

                    s_suffix = _get_suffix(start_fname)
                    e_suffix = _get_suffix(end_fname)
                    
                    # Ensure .md extension is appended to the combined suffixes
                    # Example: 0.00.jpg_2.00.jpg.md (if suffix includes extension)
                    # Or if user meant just the value, they might want to strip extension.
                    # But "图片名最后面的_后缀" usually includes extension in this context.
                    # I'll keep it as is to be safe and strict to instruction.
                    
                    batch_md_name = f"{s_suffix}_{e_suffix}.md"
                    batch_md_path = os.path.join(result_dir, batch_md_name)
                    
                    with open(batch_md_path, "w", encoding="utf-8") as f:
                        f.write(content)

                    print(
                        json.dumps(
                            {
                                "event": "moonshot.chat_completions.content.batch",
                                "model": used_model,
                                "requested_model": model,
                                "batch_index": batch_index,
                                "batch_frame_count": len(batch),
                                "batch_start": idx,
                                "content_preview": _truncate_text(content, 2000),
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                    usage = response.usage
                    if usage:
                        prompt_tokens_total = (
                            None
                            if prompt_tokens_total is None
                            else int(prompt_tokens_total) + int(getattr(usage, "prompt_tokens", 0) or 0)
                        )
                        completion_tokens_total = (
                            None
                            if completion_tokens_total is None
                            else int(completion_tokens_total)
                            + int(getattr(usage, "completion_tokens", 0) or 0)
                        )
                        total_tokens_total = (
                            None
                            if total_tokens_total is None
                            else int(total_tokens_total) + int(getattr(usage, "total_tokens", 0) or 0)
                        )
                    if not prompt_override:
                        data = _extract_json_content(content)
                        model_output: ModelOutput = {}
                        if isinstance(data, dict):
                            model_output = data  # type: ignore[assignment]
                        elif isinstance(data, list):
                            model_output = {"actions": data, "stats": compute_stats(parse_actions(data)), "advice": []}
                        batch_actions = parse_actions(model_output.get("actions"))
                        # Apply offset as per user requirement for batches
                        time_offset = (batch_index - 1) * 60.0
                        if time_offset > 0:
                            threshold = time_offset - 5.0
                            for act in batch_actions:
                                start_t = float(act.get("start_time", 0))
                                end_t = float(act.get("end_time", 0))
                                if start_t < threshold:
                                    act["start_time"] = start_t + time_offset
                                    act["end_time"] = end_t + time_offset
                        all_actions.extend(batch_actions)
                    break
                except Exception as e:
                    # Fallback Logic for Genie 3 Flash -> Genie 2.5 Flash
                    if used_model == "gemini-2.0-flash":
                         print(f"[WARNING] Model {used_model} failed with error: {e}. Falling back to gemini-1.5-flash (Genie 2.5).")
                         used_model = "gemini-1.5-flash"
                         continue

                    msg = str(e).lower()
                    if "timed out" in msg or "timeout" in msg:
                        if current_size > 4:
                            current_size = max(4, current_size // 2)
                            continue
                        _sleep_backoff(1, 1.0, 5.0)
                        continue
                    if current_size > 4 and (
                        "context" in msg
                        or "too large" in msg
                        or "413" in msg
                        or "maximum" in msg
                        or "payload" in msg
                    ):
                        current_size = max(4, current_size // 2)
                        continue
                    raise
            idx += current_size

        # Python Merge Strategy (Manual Merge with Time Offset)
        print("Starting Python merge of batch files...", flush=True)
        try:
            # Ensure result directory exists
            if not os.path.exists(result_dir):
                print(f"[WARNING] Result directory {result_dir} does not exist. Creating empty result.", flush=True)
                final_content = "| 序号 | 动作描述 | SOP 操作步骤 | 左手状态 | 右手状态 | 预估耗时(s) | 增值/非增值 | 时间段 |\n| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
            else:
                final_content = _merge_batches_python(result_dir, video_name, batch_index)
            
            final_md_path = os.path.join("result", f"{video_name}.md")
            with open(final_md_path, "w", encoding="utf-8") as f:
                f.write(final_content)
            print(f"Successfully merged {batch_index} batches into {final_md_path} using Python merge", flush=True)
        except Exception as e:
             print(f"[ERROR] Python Merge failed: {e}", flush=True)
             raise RuntimeError(f"Python Merge failed: {e}")
        actions = _merge_adjacent_actions(all_actions)
        computed_stats = compute_stats(actions)

        advice_list: List[str] = []
        try:
            if prompt_override:
                raise ValueError("Skip advice")
            advice_req = (
                "基于下面的动作序列（actions）与统计信息（stats），给出 3-8 条工艺流程改进建议。\n"
                "只输出 JSON：{\"advice\": [\"...\"]}\n"
                f"actions={json.dumps(actions, ensure_ascii=False)}\n"
                f"stats={json.dumps(computed_stats, ensure_ascii=False)}\n"
            )
            advice_resp = client.chat.completions.create(
                model=used_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": advice_req},
                ],
                temperature=1,
                timeout=300.0,
            )
            advice_content = advice_resp.choices[0].message.content or "{}"
            print(
                json.dumps(
                    {
                        "event": "moonshot.chat_completions.content.advice",
                        "model": used_model,
                        "requested_model": model,
                        "content_preview": _truncate_text(advice_content, 2000),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            advice_data = _extract_json_content(advice_content)
            if isinstance(advice_data, dict):
                adv = advice_data.get("advice")
                if isinstance(adv, list):
                    advice_list = [str(x).strip() for x in adv if str(x).strip()]
            usage = advice_resp.usage
            if usage:
                prompt_tokens_total = (
                    None
                    if prompt_tokens_total is None
                    else int(prompt_tokens_total) + int(getattr(usage, "prompt_tokens", 0) or 0)
                )
                completion_tokens_total = (
                    None
                    if completion_tokens_total is None
                    else int(completion_tokens_total) + int(getattr(usage, "completion_tokens", 0) or 0)
                )
                total_tokens_total = (
                    None
                    if total_tokens_total is None
                    else int(total_tokens_total) + int(getattr(usage, "total_tokens", 0) or 0)
                )
        except Exception:
            advice_list = []

        model_output: ModelOutput = {
            "actions": actions,
            "stats": computed_stats,
            "advice": advice_list,
        }

        usage_dict = {
            "prompt_token_count": prompt_tokens_total,
            "response_token_count": completion_tokens_total,
            "total_token_count": total_tokens_total,
        }

        result = {
            "input": {"video_path": video_path},
            "model": {"requested": model, "used": used_model},
            "file": {"name": "frames", "uri": None, "mime_type": "image/jpeg", "state": "processed"},
            "prompt": prompt_text,
            "token_usage": usage_dict,
            "token_summary": {
                "input_tokens": usage_dict.get("prompt_token_count"),
                "output_tokens": usage_dict.get("response_token_count"),
                "total_tokens": usage_dict.get("total_token_count"),
            },
            "model_output": model_output,
            "computed_stats": computed_stats,
            "actions": actions,
            "created_at": time.time(),
        }
        return result, actions

    except Exception as e:
        print(
            json.dumps(
                {
                    "event": "moonshot.chat_completions.error",
                    "model": used_model,
                    "error": _truncate_text(str(e), 2000),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        raise RuntimeError(f"Kimi API request failed: {str(e)}")
    finally:
        try:
            if http_client is not None:
                http_client.close()
        except Exception:
            pass


def analyze_video(
    api_key: str,
    video_path: str,
    model: str,
    sample_fps: float = 0.0,
    frames_dir: Optional[str] = None,
    prompt_override: Optional[str] = None,
    output_stem: Optional[str] = None,
) -> Tuple[Dict[str, Any], List[DetectedAction]]:
    normalized = _normalize_model_name(model)
    if normalized.startswith("kimi") or normalized.startswith("moonshot"):
        return analyze_video_openai(
            api_key,
            video_path,
            model,
            sample_fps,
            frames_dir=frames_dir,
            prompt_override=prompt_override,
            output_stem=output_stem,
        )

    client = genai.Client(api_key=api_key)

    # --- Batch Processing Logic (Parity with Kimi 2.5) ---
    # The user requested "do the kimi 2.5's job", which implies:
    # 1. Frame extraction (default 1 FPS)
    # 2. Batch processing (60 frames/batch)
    # 3. MD output and merging
    
    if sample_fps <= 0:
        sample_fps = 2.0
    
    frames_data: List[Any] = []
    if frames_dir:
        print(f"Loading frames from directory: {frames_dir}", flush=True)
        frames_data = load_frames_from_dir(frames_dir, max_frames=1000)
    else:
        print(f"Extracting frames for {model} at {sample_fps} FPS...", flush=True)
        frames_data = extract_frames(video_path, sample_fps)
    
    if not frames_data:
        raise ValueError("No frames extracted from video.")
    
    print(f"Extracted {len(frames_data) // 2} frames.")

    frames: List[Tuple[str, PILImage.Image, str]] = []
    for i in range(0, len(frames_data), 3):
        ts = str(frames_data[i])
        img = frames_data[i + 1]
        fname = str(frames_data[i + 2])
        if isinstance(img, PILImage.Image):
            frames.append((ts, img, fname))

    prompt_text = (prompt_override or "").strip() or build_prompt(use_frames=True)
    
    # Create result directory
    video_name = output_stem or os.path.splitext(os.path.basename(video_path))[0]
    result_dir = os.path.join("result", video_name)
    os.makedirs(result_dir, exist_ok=True)

    batch_size = 60
    idx = 0
    batch_index = 0
    
    used_model = normalized
    # Fallback setup
    fallback_model = "gemini-1.5-flash"
    
    prompt_tokens_total = 0
    completion_tokens_total = 0
    total_tokens_total = 0

    while idx < len(frames):
        batch_index += 1
        current_size = min(batch_size, len(frames) - idx)
        batch = frames[idx : idx + current_size]
        
        # Build contents for Gemini
        # Interleave text and images
        contents: List[Any] = [prompt_text]
        for ts, img, _ in batch:
            contents.append(f"Timestamp: {ts}")
            contents.append(img)
            
        print(
            json.dumps(
                {
                    "event": "gemini.generate_content.request.batch",
                    "model": used_model,
                    "batch_index": batch_index,
                    "batch_frame_count": len(batch),
                    "batch_start": idx,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

        try:
            # Config
            config = {} # Default config
            
            resp, actual_model = _generate_content_with_retry(
                client,
                used_model,
                contents,
                config,
                fallback_model=fallback_model
            )
            
            content = getattr(resp, "text", "") or ""
            
            # Save batch result to MD file
            start_fname = batch[0][2]
            end_fname = batch[-1][2]
            
            def _get_suffix(s: str) -> str:
                if "_" in s:
                    return s.rsplit("_", 1)[1]
                return s

            s_suffix = _get_suffix(start_fname)
            e_suffix = _get_suffix(end_fname)
            batch_md_name = f"{s_suffix}_{e_suffix}.md"
            batch_md_path = os.path.join(result_dir, batch_md_name)
            
            with open(batch_md_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            # Usage tracking
            usage = getattr(resp, "usage_metadata", None)
            if usage:
                prompt_tokens_total += getattr(usage, "prompt_token_count", 0) or 0
                completion_tokens_total += getattr(usage, "candidates_token_count", 0) or 0
                total_tokens_total += getattr(usage, "total_token_count", 0) or 0

        except Exception as e:
            print(f"[ERROR] Batch {batch_index} failed: {e}", flush=True)
            # Depending on requirements, we might want to continue or raise.
            # Kimi implementation raises or continues depending on error.
            # Here we raise to ensure visibility, or we could skip.
            raise e

        idx += current_size

    # Merge Batches
    print("Starting Python merge of batch files...", flush=True)
    try:
        final_content = _merge_batches_python(result_dir, video_name, batch_index)
        final_md_path = os.path.join("result", f"{video_name}.md")
        with open(final_md_path, "w", encoding="utf-8") as f:
            f.write(final_content)
        print(f"Successfully merged {batch_index} batches into {final_md_path}", flush=True)
    except Exception as e:
        print(f"[ERROR] Python Merge failed: {e}", flush=True)
        final_content = ""

    # Construct result object
    # Since we are using prompt_override (SOP mode), actions/stats are empty as per Kimi parity
    actions: List[DetectedAction] = []
    computed_stats = compute_stats([])
    
    usage_dict = {
        "prompt_token_count": prompt_tokens_total,
        "response_token_count": completion_tokens_total,
        "total_token_count": total_tokens_total,
    }

    model_output: ModelOutput = {
        "raw_content": final_content,
        "actions": actions,
        "stats": computed_stats,
        "advice": [],
    }

    result: Dict[str, Any] = {
        "input": {"video_path": video_path},
        "model": {"requested": model, "used": used_model},
        "file": {"name": "frames_batch", "uri": None, "mime_type": "image/jpeg", "state": "processed"},
        "prompt": prompt_text,
        "token_usage": usage_dict,
        "token_summary": {
            "input_tokens": prompt_tokens_total,
            "output_tokens": completion_tokens_total,
            "total_tokens": total_tokens_total,
        },
        "model_output": model_output,
        "computed_stats": computed_stats,
        "actions": actions,
        "created_at": time.time(),
    }
    
    return result, actions


def default_result_path(video_path: str) -> str:
    base = os.path.splitext(os.path.basename(video_path))[0] or "result"
    timestamp = datetime.datetime.now().strftime("%d.%H.%M.%S")
    return os.path.join("result", f"{base}_{timestamp}.json")


def write_result(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Use Gemini 3 Pro API to detect actions in a video file."
    )
    parser.add_argument("video", help="Path to the input video file.")
    parser.add_argument(
        "--model",
        default=os.getenv("GEMINI_MODEL", "kimi-2.5"),
        help="Model name to use. Default: kimi-2.5 (GenieviewK2.5)。",
    )
    parser.add_argument(
        "--api-key",
        help="Gemini API key. If omitted, reads from GOOGLE_API_KEY or GEMINI_API_KEY env vars.",
    )
    parser.add_argument(
        "--out",
        help="Write full result JSON to this path. Default: result/<video>.json",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=0.0,
        help="If > 0, extract frames at this FPS (client-side) instead of uploading video file.",
    )
    parser.add_argument(
        "--frames-dir",
        default="",
        help="如果指定，则直接使用该目录内图片作为输入（优先于 --fps 拆帧）。",
    )
    parser.add_argument(
        "--prompt-file",
        default="",
        help="从指定文件读取 prompt（支持 .json 或纯文本）。",
    )
    parser.add_argument(
        "--sop-content",
        default="",
        help="SOP content string to inject into the prompt.",
    )
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("MOONSHOT_API_KEY")
    if not api_key:
        api_key = getpass.getpass("API key (Gemini/Kimi): ").strip()
        if not api_key:
            raise SystemExit(
                "Missing API key. Set GOOGLE_API_KEY/MOONSHOT_API_KEY, or use --api-key."
            )

    if not os.path.exists(args.video):
        raise SystemExit(f"Video file not found: {args.video}")

    if not args.model or not args.model.strip():
        args.model = os.getenv("GEMINI_MODEL", "kimi-2.5")

    frames_dir = str(args.frames_dir or "").strip() or None
    prompt_override = load_prompt_from_file(str(args.prompt_file or "data/prompt.md").strip())
    
    sop_override = args.sop_content or load_prompt_from_file("data/SOP.md")
    if sop_override:
        if "## 预设 SOP Steps" not in sop_override:
             sop_override = f"\n\n## 预设 SOP Steps\n请参考以下标准作业程序(SOP)步骤进行分析：\n{sop_override}\n"
        if prompt_override:
            prompt_override += "\n\n" + sop_override
        else:
            prompt_override = sop_override
    
    out_path = args.out or default_result_path(args.video)
    if not args.out and prompt_override:
        # If using custom prompt (likely markdown), change extension to .md
        out_path = os.path.splitext(out_path)[0] + ".md"

    output_stem = os.path.splitext(os.path.basename(out_path))[0]
    
    payload, actions = analyze_video(
        api_key=api_key,
        video_path=args.video,
        model=args.model,
        sample_fps=float(args.fps),
        frames_dir=frames_dir,
        prompt_override=prompt_override,
        output_stem=output_stem,
    )
    if prompt_override and "model_output" in payload and "raw_content" in payload["model_output"]:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(payload["model_output"]["raw_content"])
    else:
        # User requested to NOT generate JSON files anymore.
        # write_result(out_path, payload)
        # print(json.dumps(payload, ensure_ascii=False, indent=2))
        pass

    # Check if MD file exists (likely created by manual merge or raw content write)
    # and update out_path for the log message if needed.
    md_path_check = os.path.splitext(out_path)[0] + ".md"
    if os.path.exists(md_path_check):
        out_path = md_path_check

    print(f"Analysis complete. Result saved to {out_path}")


if __name__ == "__main__":
    main()
