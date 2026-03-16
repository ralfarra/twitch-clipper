"""
Analyzes chat messages to find the most exciting moments in a VOD.

Scoring per time window:
  - Message volume (weighted highest)
  - ALL CAPS ratio
  - Exclamation/question mark density
  - Known hype emote count (PogChamp, KEKW, LUL, etc.)
  - Hype keyword count (lets go, gg, omg, etc.)

Returns top N peak timestamps with minimum spacing between them.
"""

import json
import math
from collections import defaultdict
from pathlib import Path


HYPE_EMOTES = {
    "pogchamp", "pog", "poggers", "kekw", "lul", "omegalul",
    "hype", "monkas", "pepelaugh", "peepolaughing", "pepehands",
    "widepeeposad", "catjam", "peepogg", "copium", "ez",
}

HYPE_KEYWORDS = {
    "lets go", "let's go", "letsgo", "gg", "omg", "wtf", "holy",
    "insane", "crazy", "clip it", "clip that", "no way", "goat",
    "actually", "bro", "sheesh",
}

WINDOW_SIZE = 10      # seconds per scoring bucket
SMOOTHING_RADIUS = 3  # buckets to smooth over (rolling average)
MIN_PEAK_SPACING = 90 # seconds minimum gap between clips


def score_message(msg: str) -> float:
    """Returns an excitement score for a single message."""
    score = 1.0  # base point for existing

    text = msg.strip()
    if not text:
        return 0.0

    # Caps ratio bonus
    letters = [c for c in text if c.isalpha()]
    if letters:
        caps_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        score += caps_ratio * 1.5

    # Punctuation excitement
    score += text.count("!") * 0.3
    score += text.count("?") * 0.2

    lower = text.lower()

    # Hype emotes
    for emote in HYPE_EMOTES:
        if emote in lower:
            score += 1.0

    # Hype keywords
    for kw in HYPE_KEYWORDS:
        if kw in lower:
            score += 0.8

    return score


def bucket_scores(messages: list[dict]) -> dict[int, float]:
    """Groups messages into time buckets and sums their scores."""
    buckets: dict[int, float] = defaultdict(float)
    for msg in messages:
        t = msg.get("time_in_seconds", 0)
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


def find_peaks(smoothed: list[float], n: int) -> list[int]:
    """
    Returns indices of top N peaks with minimum spacing between them.
    Each index is a bucket number (multiply by WINDOW_SIZE to get seconds).
    """
    min_bucket_gap = math.ceil(MIN_PEAK_SPACING / WINDOW_SIZE)
    peaks = []
    remaining = list(enumerate(smoothed))

    while len(peaks) < n and remaining:
        best_idx, best_score = max(remaining, key=lambda x: x[1])
        if best_score == 0:
            break
        peaks.append(best_idx)
        # Suppress buckets within min spacing
        remaining = [
            (i, s) for i, s in remaining
            if abs(i - best_idx) > min_bucket_gap
        ]

    return sorted(peaks)


def analyze(chat_path: Path, top_n: int = 10) -> list[dict]:
    """
    Analyzes a chat JSON file and returns top N peak moments.

    Returns list of dicts:
      { "timestamp": float (seconds), "score": float, "rank": int }
    """
    with open(chat_path) as f:
        messages = json.load(f)

    if not messages:
        return []

    buckets = bucket_scores(messages)
    max_bucket = max(buckets.keys(), default=0)
    smoothed = smooth(buckets, max_bucket)
    peak_buckets = find_peaks(smoothed, top_n)

    results = []
    for rank, bucket in enumerate(peak_buckets, start=1):
        timestamp = bucket * WINDOW_SIZE
        results.append({
            "rank": rank,
            "timestamp": timestamp,
            "score": round(smoothed[bucket], 2),
        })

    return results
