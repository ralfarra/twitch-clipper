"""
Downloads Twitch VODs using yt-dlp and chat logs using the Twitch v5 API.
"""

import os
import json
import subprocess
import requests
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


def download_chat(vod_id: str, client_id: str = None) -> Path:
    """
    Downloads Twitch chat replay using the Twitch GQL API (paginated).
    Returns path to the normalized JSON chat file.
    """
    out_dir = vod_dir(vod_id)
    out_path = out_dir / "chat.json"

    if out_path.exists():
        print(f"[downloader] Chat already downloaded: {out_path}")
        return out_path

    print(f"[downloader] Downloading chat for VOD {vod_id}...")

    GQL_URL = "https://gql.twitch.tv/gql"
    # Public Twitch web client ID — used by browsers, required for GQL chat API
    GQL_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"
    GQL_QUERY = """
    query VideoCommentsByOffset($videoID: ID!, $contentOffsetSeconds: Int) {
      video(id: $videoID) {
        comments(contentOffsetSeconds: $contentOffsetSeconds) {
          edges {
            node {
              contentOffsetSeconds
              message { fragments { text } }
              commenter { displayName }
            }
          }
          pageInfo { hasNextPage }
        }
      }
    }
    """

    # Twitch blocks cursor-based pagination with an integrity challenge,
    # so we walk through the VOD by advancing the time offset after each batch.
    messages = []
    seen_ids = set()
    offset = 0
    page = 0

    while True:
        resp = requests.post(
            GQL_URL,
            json={"query": GQL_QUERY, "variables": {"videoID": vod_id, "contentOffsetSeconds": offset}},
            headers={"Client-ID": GQL_CLIENT_ID},
        )
        resp.raise_for_status()
        data = resp.json()

        comments_block = (
            (data.get("data") or {})
            .get("video") or {}
        ).get("comments") or {}

        edges = comments_block.get("edges") or []

        new_messages = 0
        last_ts = offset
        for edge in edges:
            node = edge.get("node") or {}
            ts = float(node.get("contentOffsetSeconds", 0))
            fragments = (node.get("message") or {}).get("fragments") or []
            text = " ".join(f.get("text", "") for f in fragments)
            author = (node.get("commenter") or {}).get("displayName", "")
            key = (ts, author, text)
            if key not in seen_ids:
                seen_ids.add(key)
                messages.append({"time_in_seconds": ts, "message": text, "author": author})
                new_messages += 1
            last_ts = max(last_ts, ts)

        has_next = (comments_block.get("pageInfo") or {}).get("hasNextPage", False)

        page += 1
        if page % 50 == 0:
            print(f"[downloader] ...{len(messages)} messages fetched (t={last_ts:.0f}s)")

        # Stop if no more pages or no new messages (end of VOD)
        if not has_next or new_messages == 0 or last_ts <= offset:
            break

        offset = int(last_ts)

    with open(out_path, "w") as f:
        json.dump(messages, f)

    print(f"[downloader] Saved {len(messages)} chat messages.")
    return out_path
