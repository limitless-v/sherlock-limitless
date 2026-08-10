"""Search context models (roadmap Phase 15).

Plain dataclasses; the builder (builder.py) populates them from the local
analysis modules. Fields stay non-sensitive and evidence-backed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.discovery.fingerprinting import ImageFingerprint


@dataclass
class SearchContext:
    """Non-sensitive signal bundle feeding the Discovery Engine."""

    keywords: list[str] = field(default_factory=list)
    text: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    usernames: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)
    location: str | None = None
    timestamp: datetime | None = None
    language: str | None = None
    image_hash: ImageFingerprint | None = None
    user_filters: dict = field(default_factory=dict)
    sources: set[str] = field(default_factory=set)

    def to_dict(self) -> dict:
        return {
            "keywords": self.keywords,
            "text": self.text,
            "urls": self.urls,
            "usernames": self.usernames,
            "hashtags": self.hashtags,
            "location": self.location,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "language": self.language,
            "image_hash": self.image_hash.sha256 if self.image_hash else None,
            "sources": sorted(self.sources),
        }