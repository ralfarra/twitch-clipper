"""
Full pipeline: detect new VODs → download video + chat → analyze → clip.
Run this file directly or via the scheduler.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from twitch_auth import TwitchAuth
from vod_poller import init_db, get_new_vods, mark_processed
from downloader import download_video, download_chat
from chat_analyzer import analyze
from clipper import generate_clips


load_dotenv()


def run():
    client_id = os.environ["TWITCH_CLIENT_ID"]
    client_secret = os.environ["TWITCH_CLIENT_SECRET"]
    channel = os.environ["TWITCH_CHANNEL"]

    auth = TwitchAuth(client_id, client_secret)
    init_db()

    print(f"[pipeline] Checking for new VODs on channel: {channel}")
    new_vods = get_new_vods(auth, channel)

    if not new_vods:
        print("[pipeline] No new VODs found.")
        return

    for vod in new_vods:
        vod_id = vod["id"]
        print(f"\n[pipeline] Processing VOD: {vod['title']} (id={vod_id})")

        try:
            video_path = download_video(vod_id, vod["url"])
            chat_path = download_chat(vod_id, client_id)

            peaks = analyze(chat_path, top_n=15)
            if not peaks:
                print(f"[pipeline] No chat data to analyze for VOD {vod_id}, skipping clips.")
            else:
                clips_dir = Path("downloads") / vod_id / "clips"
                clips = generate_clips(video_path, peaks, clips_dir)
                print(f"[pipeline] Generated {len(clips)} clips in {clips_dir}")

            mark_processed(vod_id, vod["title"], vod["created_at"])

        except Exception as e:
            print(f"[pipeline] ERROR processing VOD {vod_id}: {e}")


if __name__ == "__main__":
    run()
