"""
Analyzes chat messages to find the funniest/most exciting moments in a VOD.

Scoring per time window:
  - Message volume (base score — chat going fast = something happening)
  - Laugh emotes: KEKW, LUL, OMEGALUL, etc. (strongest signal for funny)
  - "clip it" / "clip that" (chat explicitly asking to clip)
  - Hype emotes: Pog, PogChamp, etc.
  - ALL CAPS ratio
  - Exclamation/question mark density

Only peaks above a minimum score threshold are returned — if chat was
quiet, no clip is produced for that moment.
"""

import json
import math
from collections import defaultdict
from pathlib import Path


# Strongest signal: chat is laughing
LAUGH_EMOTES = {
    "kekw", "lul", "lulw", "omegalul", "omegalmao", "lmao", "lmfao",
    "😂", "💀", "pepelaugh", "peepolaughing", "kekleo", "gigachad",
    "rofll", "hahaa", "bahahaha",
}

# Chat explicitly saying this is clip-worthy
CLIP_SIGNALS = {
    "clip it", "clip that", "clipable", "clippable", "someone clip",
    "clip this", "highlight", "lmaooo", "lmaoo", "omg", "bro what",
    "bro no", "no way", "no wayyy", "i cant", "i can't",
}

# General hype/excitement
HYPE_EMOTES = {
    "pogchamp", "pog", "poggers", "pogg", "hype", "monkas",
    "pepehands", "widepeeposad", "catjam", "peepogg", "ez",
    "copium", "sadge", "aware", "pepega",
}

HYPE_KEYWORDS = {
    "lets go", "let's go", "letsgo", "gg", "wtf", "holy",
    "insane", "crazy", "goat", "sheesh", "actually", "real",
    "bro", "dude", "cmon",
}

WINDOW_SIZE = 10       # seconds per scoring bucket
SMOOTHING_RADIUS = 3   # buckets on each side for rolling average
MIN_PEAK_SPACING = 120 # seconds minimum between clips (2 min buffer)
MIN_SCORE = 30.0       # minimum score to produce a clip at all


def score_message(msg: str) -> float:
    """Returns a funny/excitement score for a single message."""
    text = msg.strip()
    if not text:
        return 0.0

    score = 1.0  # base: message exists
    lower = text.lower()

    # Laugh emotes — strongest signal (3x weight)
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

    # ALL CAPS bonus — caps = shouting = excited
    letters = [c for c in text if c.isalpha()]
    if letters:
        caps_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        score += caps_ratio * 2.0

    # Punctuation excitement
    score += min(text.count("!"), 5) * 0.4
    score += min(text.count("?"), 3) * 0.2

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
    Only includes peaks above MIN_SCORE threshold.
    """
    min_bucket_gap = math.ceil(MIN_PEAK_SPACING / WINDOW_SIZE)
    peaks = []
    remaining = list(enumerate(smoothed))

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

    Returns list of dicts:
      { "rank": int, "timestamp": float (seconds), "score": float }
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
