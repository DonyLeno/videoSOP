import argparse
import json
import os
import time


def load_raw_payload(path: str) -> dict:
    if not os.path.exists(path):
        raise RuntimeError(f"Input JSON file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def extract_inner_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        if text.lower().startswith("```json"):
            text = text.split("\n", 1)[1] if "\n" in text else ""
        if "```" in text:
            text = text.split("```", 1)[0]
    text = text.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception as e:
        raise RuntimeError(f"Failed to parse inner JSON: {e}")


def build_pretty_result(inner: dict, video_path: str) -> dict:
    actions = inner.get("actions") or []
    stats = inner.get("stats") or {}
    advice = inner.get("advice") or []

    result = {
        "input": {"video_path": video_path},
        "model": {"requested": "kimi-k2.5", "used": "kimi-k2.5"},
        "file": {
            "name": None,
            "uri": None,
            "mime_type": None,
            "state": "None",
        },
        "prompt": None,
        "token_usage": None,
        "token_summary": None,
        "model_output": inner,
        "computed_stats": stats,
        "actions": actions,
        "advice": advice,
        "created_at": time.time(),
    }
    return result


def format_kimi_json(input_path: str, output_path: str, video_path: str) -> None:
    payload = load_raw_payload(input_path)
    raw = payload.get("raw_content")
    if not isinstance(raw, str):
        raise RuntimeError("Input JSON does not contain 'raw_content' string")
    inner = extract_inner_json(raw)
    pretty = build_pretty_result(inner, video_path)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(pretty, f, ensure_ascii=False, indent=2)


def main() -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(
        base_dir, "kimi_kimi2_5_20260129_144105.json"
    )
    parser = argparse.ArgumentParser(
        description="Format GenieviewK2.5 原始 JSON 为更可读的结构"
    )
    parser.add_argument(
        "--input",
        default=default_input,
        help="原始 Kimi JSON 文件路径",
    )
    parser.add_argument(
        "--output",
        default="",
        help="输出 JSON 文件路径（默认为在 test 目录中加 _pretty 后缀）",
    )
    parser.add_argument(
        "--video-path",
        default="kimi.mp4",
        help="对应的视频文件路径，仅用于 metadata 展示",
    )
    args = parser.parse_args()

    input_path = args.input
    if args.output:
        output_path = args.output
    else:
        root, ext = os.path.splitext(os.path.basename(input_path))
        pretty_name = f"{root}_pretty{ext or '.json'}"
        output_path = os.path.join(base_dir, pretty_name)

    format_kimi_json(input_path, output_path, args.video_path)
    print(f"Formatted JSON written to: {output_path}")


if __name__ == "__main__":
    main()
