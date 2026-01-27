import argparse
import os
import subprocess
import sys


def resolve_input_path(video_name: str) -> str:
    if os.path.isabs(video_name) and os.path.exists(video_name):
        return video_name

    candidates = [
        video_name,
        os.path.join("result", video_name),
        os.path.join("data", video_name),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p

    raise FileNotFoundError(f"Video not found: {video_name}")


def build_output_path(input_path: str, factor_str: str) -> str:
    base = os.path.basename(input_path)
    stem, ext = os.path.splitext(base)
    out_name = f"{stem}_{factor_str}{ext or '.mp4'}"
    return os.path.join("result", out_name)


def downscale_video(input_path: str, factor: float, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    vf = (
        f"scale=trunc(iw*{factor}/2)*2:trunc(ih*{factor}/2)*2"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        msg = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(msg or "ffmpeg failed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", help="视频文件名或路径（支持 data/、result/ 下的文件名）")
    parser.add_argument("factor", help="0~1 之间的小数，代表缩放倍数，例如 0.4")
    args = parser.parse_args()

    try:
        factor = float(args.factor)
    except ValueError as e:
        raise SystemExit(f"Invalid factor: {args.factor}") from e

    if not (0 < factor <= 1):
        raise SystemExit(f"factor must be in (0, 1], got {factor}")

    input_path = resolve_input_path(args.video)
    output_path = build_output_path(input_path, args.factor)
    downscale_video(input_path, factor, output_path)
    print(output_path)


if __name__ == "__main__":
    main()

