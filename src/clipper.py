"""
Cuts 90-second clips from a VOD using ffmpeg.

Timing: chat reacts AFTER the funny moment, so we start 60s before the
chat peak to capture the actual moment, and end 30s after to capture the
reaction. This gives better context vs. centering on the peak.
"""

import subprocess
from pathlib import Path


CLIP_DURATION = 90     # seconds total
LEAD_IN = 60           # seconds before chat peak (capture the moment)
LEAD_OUT = 30          # seconds after chat peak (capture the reaction)


def clip_video(video_path: Path, timestamp: float, rank: int, out_dir: Path) -> Path:
    """
    Cuts a 90-second clip starting 60s before `timestamp` from `video_path`.
    Returns path to the output clip file.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    start = max(0, timestamp - LEAD_IN)
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
