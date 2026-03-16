"""
Cuts 90-second clips from a VOD using ffmpeg, centered on peak timestamps.
"""

import subprocess
from pathlib import Path


CLIP_DURATION = 90   # seconds
HALF = CLIP_DURATION // 2


def clip_video(video_path: Path, timestamp: float, rank: int, out_dir: Path) -> Path:
    """
    Cuts a 90-second clip centered on `timestamp` from `video_path`.
    Returns path to the output clip file.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    start = max(0, timestamp - HALF)
    out_path = out_dir / f"clip_{rank:02d}_t{int(timestamp)}s.mp4"

    if out_path.exists():
        print(f"[clipper] Clip already exists: {out_path}")
        return out_path

    print(f"[clipper] Cutting clip #{rank} at t={timestamp}s -> {out_path}")
    subprocess.run(
        [
            "ffmpeg",
            "-ss", str(start),
            "-i", str(video_path),
            "-t", str(CLIP_DURATION),
            "-c", "copy",          # fast: no re-encode
            "-avoid_negative_ts", "make_zero",
            str(out_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return out_path


def generate_clips(video_path: Path, peaks: list[dict], out_dir: Path) -> list[Path]:
    """
    Generates clips for all peak moments.
    `peaks` is the output of chat_analyzer.analyze().
    """
    clips = []
    for peak in peaks:
        clip = clip_video(video_path, peak["timestamp"], peak["rank"], out_dir)
        clips.append(clip)
    return clips
