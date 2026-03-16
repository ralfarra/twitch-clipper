"""
Downloads Twitch VODs using yt-dlp and chat logs using chat-downloader.
"""

import os
import json
import subprocess
from pathlib import Path


DOWNLOADS_DIR = Path("downloads")


def vod_dir(vod_id: str) -> Path:
    d = DOWNLOADS_DIR / vod_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def download_video(vod_id: str, vod_url: str) -> Path:
    """Downloads the VOD video file. Returns path to the downloaded file."""
    out_dir = vod_dir(vod_id)
    out_path = out_dir / "video.mp4"

    if out_path.exists():
        print(f"[downloader] Video already downloaded: {out_path}")
        return out_path

    print(f"[downloader] Downloading video for VOD {vod_id}...")
    subprocess.run(
        [
            "yt-dlp",
            "--output", str(out_path),
            "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            vod_url,
        ],
        check=True,
    )
    return out_path


def download_chat(vod_id: str) -> Path:
    """
    Downloads chat for a VOD using chat-downloader.
    Returns path to the JSON chat file.
    """
    out_dir = vod_dir(vod_id)
    out_path = out_dir / "chat.json"

    if out_path.exists():
        print(f"[downloader] Chat already downloaded: {out_path}")
        return out_path

    print(f"[downloader] Downloading chat for VOD {vod_id}...")

    from chat_downloader import ChatDownloader
    url = f"https://www.twitch.tv/videos/{vod_id}"
    downloader = ChatDownloader()
    chat = downloader.get_chat(url)

    messages = []
    for msg in chat:
        messages.append({
            "time_in_seconds": msg.get("time_in_seconds", 0),
            "message": msg.get("message", ""),
            "author": msg.get("author", {}).get("name", ""),
        })

    with open(out_path, "w") as f:
        json.dump(messages, f)

    print(f"[downloader] Saved {len(messages)} chat messages.")
    return out_path
