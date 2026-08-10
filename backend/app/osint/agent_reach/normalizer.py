"""Agent Reach record normalizer (roadmap Phase 18).

Maps raw records returned by `agent-reach get --json` into the app-wide
`discovery.schemas.Candidate`. Only URL-bearing records survive — those
without a usable URL are dropped, and exact duplicate URLs collapse.
"""

from __future__ import annotations

from app.discovery.schemas import Candidate


def _first_url(record: dict) -> str:
    for key in ("url", "link", "page", "profile_url", "href", "permalink"):
        value = record.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
    return ""


def _title(record: dict) -> str:
    for key in ("title", "name", "label", "snippet"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _images(record: dict) -> list[str]:
    raw = record.get("images", record.get("image_urls", record.get("image", [])))
    if isinstance(raw, str):
        raw = [raw]
    return [u for u in raw if isinstance(u, str) and u.startswith(("http://", "https://"))]


def normalize_record(record: dict, source: str = "agent_reach") -> Candidate | None:
    """Normalize one raw record; None when it carries no usable URL."""
    url = _first_url(record)
    if not url:
        return None
    return Candidate(
        url=url,
        source=source,
        title=_title(record),
        kind="web",
        reason=record.get("reason") or f"discovered by {source}",
        images=_images(record),
        metadata={"raw": record},
    )


def normalize_records(records: list[dict], source: str = "agent_reach") -> list[Candidate]:
    """Normalize and deduplicate raw records by canonical URL."""
    seen: set[str] = set()
    out: list[Candidate] = []
    for record in records:
        candidate = normalize_record(record, source=source)
        if candidate is None:
            continue
        key = candidate.url.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(candidate)
    return out