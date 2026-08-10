"""Local language detection (roadmap Phase 12/15).

Script-based heuristic over Unicode ranges — no external model. Returns an
ISO 639-1-ish code when one script clearly dominates, else None.
"""

from __future__ import annotations

import re

_ANSI = re.compile(r"[\u0041-\u007a]")  # basic latin

_SCRIPTS: list[tuple[str, re.Pattern]] = [
    ("zh", re.compile(r"[\u4e00-\u9fff]")),
    ("ja", re.compile(r"[\u3040-\u30ff]")),
    ("ko", re.compile(r"[\uac00-\ud7af]")),
    ("ru", re.compile(r"[\u0400-\u04ff]")),
    ("ar", re.compile(r"[\u0600-\u06ff]")),
    ("el", re.compile(r"[\u0370-\u03ff]")),
    ("he", re.compile(r"[\u0590-\u05ff]")),
    ("hi", re.compile(r"[\u0900-\u097f]")),
    ("th", re.compile(r"[\u0e00-\u0e7f]")),
]


def detect_language(text: str | None) -> str | None:
    """Return the dominant language code, or None when ambiguous/empty."""
    if not text:
        return None
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return None
    total = len(letters)

    latin = sum(1 for ch in letters if _ANSI.match(ch))
    best: tuple[str, int] | None = None
    for code, pattern in _SCRIPTS:
        count = sum(1 for ch in letters if pattern.match(ch))
        if best is None or count > best[1]:
            best = (code, count)

    if best is None or best[1] < 3:
        return "en" if latin / total >= 0.5 else None
    # non-latin script must clearly dominate; otherwise fall back to latin
    if best[1] >= total * 0.35:
        return best[0]
    return "en" if latin / total >= 0.5 else None