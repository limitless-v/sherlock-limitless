"""Keyword extraction (roadmap Phase 15).

Turns recognized text into short, de-duplicated search keywords. Purely
morphological — no external NLP dependency.
"""

from __future__ import annotations

import re
from collections import Counter

_TOKEN = re.compile(r"[\w][\w'_-]{2,}")


DEFAULT_STOPWORDS = frozenset(
    {
        "the", "and", "for", "with", "this", "that", "from", "you", "not",
        "are", "was", "were", "have", "has", "had", "but", "not", "all",
        "can", "any", "will", "would", "could", "should", "your", "its",
        "our", "their", "his", "her", "about", "into", "over", "after",
        "up", "off", "out", "be", "by", "on", "at", "in", "to", "of", "a",
    }
)


def extract_keywords(
    texts,
    stopwords: frozenset | None = None,
    max_keywords: int = 20,
) -> list[str]:
    """Return the most frequent meaningful tokens across `texts`."""
    sw = stopwords if stopwords is not None else DEFAULT_STOPWORDS
    counts: Counter = Counter()
    for text in texts:
        if not text:
            continue
        for token in _TOKEN.findall(str(text)):
            low = token.lower()
            if low in sw or low.isdigit():
                continue
            counts[low] += 1
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [token for token, _ in top[:max_keywords]]