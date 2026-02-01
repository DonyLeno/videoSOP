import argparse
import base64
import json
import os
import datetime

import cv2  # type: ignore
from openai import OpenAI


def load_api_key_from_file(path: str) -> str:
    if not os.path.exists(path):
        raise RuntimeError(f"API key file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            key = line.strip()
            if key:
                return key
    raise RuntimeError(f"API key file is empty: {path}")


def build_video_data_url(video_path: str) -> str:
    if not os.path.exists(video_path):
        raise RuntimeError(f"Video file not found: {video_path}")
    ext = os.path.splitext(video_path)[1].lstrip(".") or "mp4"
    with open(video_path, "rb") as f:
        video_data = f.read()
    b64 = base64.b64encode(video_data).decode("utf-8")
    return f"data:video/{ext};base64,{b64}"


def extract_and_save_frames(
    video_path: str,
    output_dir: str,
    target_fps: float = 2.0,
    max_frames: int = 100,
) -> list:
    if not os.path.exists(video_path):
        raise RuntimeError(f"Video file not found: {video_path}")
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    if video_fps <= 0:
        video_fps = 30.0
    if target_fps <= 0:
        target_fps = 2.0
    step = max(1, int(round(video_fps / target_fps)))
    frames = []
    idx = 0
    frames_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % step == 0:
            if frames_count >= max_frames:
                break
            ts = idx / video_fps
            h, w = frame.shape[:2]
            if w > 0 and h > 0:
                new_w = max(1, w // 2)
                new_h = max(1, h // 2)
                frame = cv2.resize(frame, (new_w, new_h))
            filename = f"frame_{idx:05d}_{ts:.2f}.jpg"
            path = os.path.join(output_dir, filename)
            ok = cv2.imwrite(path, frame)
            if not ok:
                idx += 1
                continue
            frames.append({"image_path": path, "timestamp": ts})
            frames_count += 1
        idx += 1
    cap.release()
    return frames


def run_inference(video_path: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    api_key_path = os.path.join(base_dir, "apikey.md")
    api_key = load_api_key_from_file(api_key_path)

    client = OpenAI(api_key=api_key, base_url="https://api.moonshot.cn/v1")

    prompt_json_path = os.path.join(
        os.path.dirname(base_dir),
        "result",
        "motor2_12.15.13.12.json",
    )
    with open(prompt_json_path, "r", encoding="utf-8") as f:
        prompt_payload = json.load(f)
    prompt_text = prompt_payload.get("prompt", "")

    images_root = os.path.join(base_dir, "images")
    video_name = os.path.splitext(os.path.basename(video_path))[0] or "video"
    frame_dir = os.path.join(images_root, video_name)
    print("Extracting frames...", flush=True)
    frames = extract_and_save_frames(video_path, frame_dir)
    print(f"Total frames to process: {len(frames)}", flush=True)

    merged_frames = []

    for idx, frame in enumerate(frames, start=1):
        img_path = frame["image_path"]
        ts = frame["timestamp"]
        print(f"[{idx}/{len(frames)}] Sending frame {os.path.basename(img_path)} at {ts:.2f}s", flush=True)
        with open(img_path, "rb") as f:
            img_data = f.read()
        b64 = base64.b64encode(img_data).decode("utf-8")

        try:
            completion = client.chat.completions.create(
                model="kimi-k2.5",
                messages=[
                    {"role": "system", "content": "你是 Kimi。"},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                            },
                        ],
                    },
                ],
                timeout=60.0,
            )

            content = completion.choices[0].message.content
            try:
                payload = json.loads(content)
            except Exception:
                payload = {"raw_content": content}
        except Exception as e:
            payload = {"error": str(e)}
            print(f"Error processing frame {os.path.basename(img_path)}: {e}", flush=True)

        frame_base = os.path.splitext(os.path.basename(img_path))[0]
        per_frame_name = f"{frame_base}_kimi2_5.json"
        per_frame_path = os.path.join(frame_dir, per_frame_name)
        with open(per_frame_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        merged_frames.append(
            {
                "image": img_path,
                "timestamp": ts,
                "result": payload,
            }
        )

    ts_run = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    merged_name = f"{video_name}_kimi2_5_frames_merged_{ts_run}.json"
    merged_path = os.path.join(base_dir, merged_name)

    merged_payload = {
        "input": {"video_path": video_path},
        "model": {"requested": "kimi-k2.5", "used": "kimi-k2.5"},
        "prompt": prompt_text,
        "frames": merged_frames,
        "created_at": datetime.datetime.now().isoformat(),
    }

    with open(merged_path, "w", encoding="utf-8") as f:
        json.dump(merged_payload, f, ensure_ascii=False, indent=2)

    print(f"Frames written to: {frame_dir}")
    print(f"Merged JSON written to: {merged_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="GenieviewK2.5 视频模型测试程序")
    parser.add_argument(
        "video",
        nargs="?",
        default="kimi.mp4",
        help="要识别的视频文件路径，默认当前目录下的 kimi.mp4",
    )
    args = parser.parse_args()
    run_inference(args.video)


if __name__ == "__main__":
    main()
