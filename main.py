import argparse
import datetime
import getpass
import json
import os
import random
import time
from typing import Any, Dict, List, Optional, TypedDict, Tuple, Union

import cv2  # type: ignore
from PIL import Image as PILImage
from google import genai
from google.genai import errors


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
            resp = client.models.generate_content(
                model=used_model,
                contents=contents,
                config=config,
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
    for _ in range(90):
        try:
            last_info = client.files.get(name=file_name)
        except (errors.ClientError, errors.ServerError) as e:
            if _is_retryable_genai_error(e):
                time.sleep(1.0)
                continue
            raise
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
            
        frame_idx += 1
        
    cap.release()
    return content_parts


def analyze_video(
    api_key: str, video_path: str, model: str, sample_fps: float = 0.0
) -> Tuple[Dict[str, Any], List[DetectedAction]]:
    client = genai.Client(api_key=api_key)

    contents: List[Any] = []
    file_info: Any = None
    use_frames = False

    if sample_fps > 0:
        # Client-side frame extraction
        print(f"Extracting frames at {sample_fps} FPS...")
        contents = extract_frames(video_path, sample_fps)
        if not contents:
            raise ValueError("No frames extracted from video.")
        use_frames = True
        print(f"Extracted {len(contents) // 2} frames.")
    else:
        # Standard video file upload
        uploaded_file = None
        max_attempts = _env_int("GENAI_UPLOAD_MAX_ATTEMPTS", 4)
        base_delay = _env_float("GENAI_RETRY_BASE_DELAY_SECONDS", 1.0)
        max_delay = _env_float("GENAI_RETRY_MAX_DELAY_SECONDS", 20.0)
        for attempt in range(1, max_attempts + 1):
            try:
                uploaded_file = client.files.upload(file=video_path)
                break
            except (errors.ClientError, errors.ServerError) as e:
                if attempt >= max_attempts or not _is_retryable_genai_error(e):
                    raise
                code = _get_error_code(e)
                print(f"GenAI 上传失败（{code or 'unknown'}），第 {attempt}/{max_attempts} 次重试中...", flush=True)
                _sleep_backoff(attempt, base_delay, max_delay)
        if uploaded_file is None:
            raise RuntimeError("Upload failed")
        file_info = wait_until_file_active(client, uploaded_file.name or "")
        contents = [uploaded_file]

    prompt = build_prompt(use_frames=use_frames)
    contents.append(prompt)
    
    schema = build_response_json_schema()

    primary_model = model
    fallback_model = "gemini-2.5-flash"
    used_model = primary_model

    response, used_model = _generate_content_with_retry(
        client,
        primary_model,
        contents,
        {
            "response_mime_type": "application/json",
            "response_json_schema": schema,
        },
        fallback_model=fallback_model,
    )

    text = response.text or "{}"
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {}

    model_output: ModelOutput = {}
    if isinstance(data, dict):
        model_output = data  # type: ignore[assignment]
    elif isinstance(data, list):
        model_output = {"actions": data, "stats": compute_stats(parse_actions(data)), "advice": []}

    actions = parse_actions(model_output.get("actions"))
    computed_stats = compute_stats(actions)

    usage = getattr(response, "usage_metadata", None)
    usage_dict: Optional[Dict[str, Any]] = None
    if usage is not None:
        usage_dict = usage.model_dump() if hasattr(usage, "model_dump") else dict(usage)
    else:
        # count_tokens also supports multimodal content list
        count = client.models.count_tokens(model=used_model, contents=contents)
        usage_dict = {
            "prompt_token_count": getattr(count, "total_tokens", None),
            "response_token_count": None,
            "total_token_count": None,
        }

    input_tokens = usage_dict.get("prompt_token_count")
    output_tokens = usage_dict.get("response_token_count", None)
    if output_tokens is None:
        output_tokens = usage_dict.get("candidates_token_count", None)
    total_tokens = usage_dict.get("total_token_count")
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = int(input_tokens) + int(output_tokens)

    result: Dict[str, Any] = {
        "input": {"video_path": video_path},
        "model": {"requested": model, "used": used_model},
        "file": {
            "name": getattr(file_info, "name", None),
            "uri": getattr(file_info, "uri", None),
            "mime_type": getattr(file_info, "mime_type", None),
            "state": str(getattr(file_info, "state", None)),
        },
        "prompt": prompt,
        "token_usage": usage_dict,
        "token_summary": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
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
        default=os.getenv("GEMINI_MODEL", "gemini-3-pro"),
        help="Gemini model name to use, e.g. gemini-3-pro, gemini-2.5-flash.",
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
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        api_key = getpass.getpass("Gemini API key: ").strip()
        if not api_key:
            raise SystemExit(
                "Missing API key. Set GOOGLE_API_KEY (recommended) or GEMINI_API_KEY, or use --api-key."
            )

    if not os.path.exists(args.video):
        raise SystemExit(f"Video file not found: {args.video}")

    payload, actions = analyze_video(
        api_key=api_key,
        video_path=args.video,
        model=args.model,
        sample_fps=args.fps,
    )
    out_path = args.out or default_result_path(args.video)
    write_result(out_path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
