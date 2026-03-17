"""
Analyzes chat messages to find the funniest/most exciting moments in a VOD.

Key behaviors:
  - Always skips the first 15 minutes (waiting screen before stream starts)
  - Scores windows heavily on laugh emotes, "clip it" signals, and caps bursts
  - Returns the top N funniest moments spread across the FULL stream,
    each at least 2 minutes apart
"""

import json
import math
from collections import defaultdict
from pathlib import Path


# Strongest signal: chat is laughing at something
LAUGH_EMOTES = {
    "kekw", "lul", "lulw", "omegalul", "omegalmao", "lmao", "lmfao",
    "😂", "💀", "pepelaugh", "peepolaughing", "kekleo",
    "bahahaha", "hahaa", "rofll",
}

# Chat explicitly flagging the moment as clip-worthy
CLIP_SIGNALS = {
    "clip it", "clip that", "clipable", "clippable", "someone clip",
    "clip this", "lmaooo", "lmaoo", "omg", "bro what", "bro no",
    "no way", "no wayyy", "i cant", "i can't", "WHAT",
}

# General hype/excitement
HYPE_EMOTES = {
    "pogchamp", "pog", "poggers", "hype", "monkas", "catjam",
    "pepehands", "copium", "sadge", "pepega", "peepogg", "ez",
}

HYPE_KEYWORDS = {
    "lets go", "let's go", "letsgo", "gg", "wtf", "holy",
    "insane", "crazy", "goat", "sheesh", "bro", "dude",
}

WINDOW_SIZE = 10        # seconds per scoring bucket
SMOOTHING_RADIUS = 3    # rolling average radius in buckets
MIN_PEAK_SPACING = 120  # seconds between clips (2 min buffer)
MIN_SCORE = 30.0        # minimum score to produce a clip

SKIP_FIRST_SECONDS = 15 * 60  # always skip first 15 minutes (waiting screen)


def score_message(msg: str) -> float:
    """Returns a funny/excitement score for a single message."""
    text = msg.strip()
    if not text:
        return 0.0

    score = 1.0  # base: message exists
    lower = text.lower()

    # Laugh emotes — strongest signal (3x)
    for emote in LAUGH_EMOTES:
        if emote in lower:
            score += 3.0

    # "Clip it" signals — chat explicitly flagging the moment (2.5x)
    for signal in CLIP_SIGNALS:
        if signal in lower:
            score += 2.5

    # General hype emotes (1.5x)
    for emote in HYPE_EMOTES:
        if emote in lower:
            score += 1.5

    # Hype keywords (1x)
    for kw in HYPE_KEYWORDS:
        if kw in lower:
            score += 1.0

    # ALL CAPS — shouting = strong reaction (2x)
    letters = [c for c in text if c.isalpha()]
    if letters:
        caps_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        score += caps_ratio * 2.0

    # Punctuation
    score += min(text.count("!"), 5) * 0.4
    score += min(text.count("?"), 3) * 0.2

    return score


def bucket_scores(messages: list[dict], skip_before: float) -> dict[int, float]:
    """Groups messages into time buckets, ignoring anything before skip_before."""
    buckets: dict[int, float] = defaultdict(float)
    for msg in messages:
        t = msg.get("time_in_seconds", 0)
        if t < skip_before:
            continue
        bucket = int(t // WINDOW_SIZE)
        buckets[bucket] += score_message(msg.get("message", ""))
    return buckets


def smooth(buckets: dict[int, float], max_bucket: int) -> list[float]:
    """Applies a rolling average over the bucket scores."""
    raw = [buckets.get(i, 0.0) for i in range(max_bucket + 1)]
    smoothed = []
    for i in range(len(raw)):
        lo = max(0, i - SMOOTHING_RADIUS)
        hi = min(len(raw), i + SMOOTHING_RADIUS + 1)
        smoothed.append(sum(raw[lo:hi]) / (hi - lo))
    return smoothed


def find_peaks(smoothed: list[float], n: int, skip_before_bucket: int) -> list[int]:
    """
    Returns indices of top N peaks above MIN_SCORE with minimum spacing.
    Only considers buckets at or after skip_before_bucket.
    """
    min_bucket_gap = math.ceil(MIN_PEAK_SPACING / WINDOW_SIZE)
    peaks = []
    remaining = [(i, s) for i, s in enumerate(smoothed) if i >= skip_before_bucket]

    while len(peaks) < n and remaining:
        best_idx, best_score = max(remaining, key=lambda x: x[1])
        if best_score < MIN_SCORE:
            break
        peaks.append(best_idx)
        remaining = [
            (i, s) for i, s in remaining
            if abs(i - best_idx) > min_bucket_gap
        ]

    return sorted(peaks)


def analyze(chat_path: Path, top_n: int = 15) -> list[dict]:
    """
    Analyzes a chat JSON file and returns the top funny/exciting moments.
    Automatically skips the pre-stream waiting screen.

    Returns list of dicts:
      { "rank": int, "timestamp": float (seconds), "score": float }
    """
    with open(chat_path) as f:
        messages = json.load(f)

    if not messages:
        return []

    print(f"[analyzer] Skipping first {SKIP_FIRST_SECONDS // 60} minutes (waiting screen)")
    buckets = bucket_scores(messages, skip_before=SKIP_FIRST_SECONDS)
    if not buckets:
        return []

    max_bucket = max(buckets.keys(), default=0)
    smoothed = smooth(buckets, max_bucket)
    skip_before_bucket = int(SKIP_FIRST_SECONDS // WINDOW_SIZE)
    peak_buckets = find_peaks(smoothed, top_n, skip_before_bucket)

    results = []
    for rank, bucket in enumerate(peak_buckets, start=1):
        timestamp = bucket * WINDOW_SIZE
        results.append({
            "rank": rank,
            "timestamp": timestamp,
            "score": round(smoothed[bucket], 2),
        })

    print(f"[analyzer] Found {len(results)} clip-worthy moments")
    return results
