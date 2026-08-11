"""Candidate extraction (roadmap Phase 23).

Converts ResearchAgent output into structured CandidateExtractions
and provides persistence helpers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.agents.web_research.schemas import Evidence, ResearchOutput
from app.discovery.schemas import Candidate as DiscoveryCandidate
from app.evidence.schemas import (
    CandidateExtraction,
    CandidateImageData,
    CandidateProfileData,
    CandidateLocationData,
    CandidateDateData,
)


_URL_RE = re.compile(r"https?://[^\s<>\"']+")
_USERNAME_RE = re.compile(r"(?<![\w@])@([A-Za-z0-9_.]{2,30})\b")
_HASHTAG_RE = re.compile(r"(?<![\w#])#([\w]{1,50})\b")
_PROFILE_HOSTS = frozenset({
    "twitter.com", "x.com", "github.com", "instagram.com",
    "linkedin.com", "facebook.com", "youtube.com", "t.me",
    "reddit.com", "medium.com", "tiktok.com",
})
_PROFILE_PATH_PATTERNS = ("/profile/", "/user/", "/users/", "/u/", "/@")


@dataclass
class ExtractedCandidate:
    """Intermediate representation before ORM persistence."""

    extraction: CandidateExtraction
    source_evidence: list[Evidence]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _derive_domain(url: str) -> str:
    try:
        parsed = urlparse(url.strip())
        return parsed.netloc.lower()
    except ValueError:
        return ""


def _extract_urls(text: str) -> list[str]:
    urls = []
    for raw in _URL_RE.findall(text):
        clean = raw.rstrip(".,;:!?)]}>\"'")
        if clean and clean not in urls:
            urls.append(clean)
    return urls


def _extract_usernames(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for m in _USERNAME_RE.finditer(text):
        handle = m.group(1)
        if handle not in seen:
            seen.add(handle)
            out.append(handle)
    return out


def _is_profile_link(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        domain = ".".join(host.split(".")[-2:]) if host.count(".") >= 1 else host
        path = parsed.path.lower()
        if domain in _PROFILE_HOSTS:
            return True
        if any(p in path for p in _PROFILE_PATH_PATTERNS):
            return True
    except ValueError:
        pass
    return False


def _guess_platform(url: str) -> str:
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if "twitter.com" in host or "x.com" in host:
            return "twitter"
        if "github.com" in host:
            return "github"
        if "instagram.com" in host:
            return "instagram"
        if "linkedin.com" in host:
            return "linkedin"
        if "facebook.com" in host:
            return "facebook"
        if "youtube.com" in host:
            return "youtube"
        if "t.me" in host:
            return "telegram"
        if "reddit.com" in host:
            return "reddit"
        if "medium.com" in host:
            return "medium"
        if "tiktok.com" in host:
            return "tiktok"
    except ValueError:
        pass
    return "unknown"


def _extract_username_from_profile_url(url: str, platform: str) -> str | None:
    """Extract username from a profile URL based on platform."""
    try:
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if not path:
            return None

        if platform == "github":
            # github.com/username
            return path.split("/")[0] if path else None
        elif platform == "twitter":
            # twitter.com/username or x.com/username
            return path.split("/")[0] if path else None
        elif platform == "instagram":
            # instagram.com/username
            return path.split("/")[0] if path else None
        elif platform == "linkedin":
            # linkedin.com/in/username or linkedin.com/profile/username
            parts = path.split("/")
            if "in" in parts:
                idx = parts.index("in")
                if idx + 1 < len(parts):
                    return parts[idx + 1]
            elif "profile" in parts:
                idx = parts.index("profile")
                if idx + 1 < len(parts):
                    return parts[idx + 1]
        elif platform == "medium":
            # medium.com/@username
            if path.startswith("@"):
                return path[1:]
        elif platform == "telegram":
            # t.me/username
            return path
    except Exception:
        pass
    return None


def _extract_locations(text: str) -> list[CandidateLocationData]:
    """Extract location-like strings (heuristic, not NER)."""
    locations: list[CandidateLocationData] = []
    # Look for capitalized phrases that might be locations
    # This is a simple heuristic - production would use NER
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Simple pattern: capitalized words, possibly with comma
        words = line.split()
        if len(words) >= 2 and words[0][0].isupper():
            # Could be a location
            locations.append(CandidateLocationData(
                location=line[:200],
                location_type="extracted_text",
                source_text=line[:500],
                confidence=0.3,
            ))
    return locations[:10]  # Limit


def _extract_dates(text: str) -> list[CandidateDateData]:
    """Extract date-like strings (heuristic)."""
    dates: list[CandidateDateData] = []
    # ISO-like dates
    iso_re = re.compile(r"\b(\d{4}-\d{2}-\d{2}[T\s]?\d{2}:\d{2}:\d{2}?)\b")
    for m in iso_re.finditer(text):
        try:
            dt = datetime.fromisoformat(m.group(1).replace(" ", "T"))
            dates.append(CandidateDateData(
                date_value=dt,
                date_type="iso",
                source_text=m.group(0),
                confidence=0.8,
            ))
        except ValueError:
            pass
    # Common formats: Jan 1, 2024
    month_re = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b", re.IGNORECASE)
    for m in month_re.finditer(text):
        try:
            dt = datetime.strptime(m.group(0), "%b %d, %Y")
            dates.append(CandidateDateData(
                date_value=dt,
                date_type="month_day_year",
                source_text=m.group(0),
                confidence=0.7,
            ))
        except ValueError:
            pass
    return dates[:10]


class CandidateExtractor:
    """Extract structured candidates from ResearchAgent output."""

    def __init__(self, max_images_per_candidate: int = 5, max_profiles_per_candidate: int = 10) -> None:
        self._max_images = max_images_per_candidate
        self._max_profiles = max_profiles_per_candidate

    def extract_from_research(self, research_output: ResearchOutput) -> list[ExtractedCandidate]:
        """Extract candidates from ResearchOutput.

        Groups evidence by source URL to build candidate records.
        """
        # Group evidence by URL
        by_url: dict[str, list[Evidence]] = {}
        for ev in research_output.evidence:
            by_url.setdefault(ev.url, []).append(ev)

        candidates: list[ExtractedCandidate] = []

        for url, evidence_list in by_url.items():
            # Build combined text from page_text evidence
            combined_text = "\n".join(
                ev.text for ev in evidence_list if ev.kind == "page_text" and ev.text
            )

            # Get metadata from metadata evidence
            metadata: dict = {}
            for ev in evidence_list:
                if ev.kind == "metadata" and ev.metadata:
                    metadata.update(ev.metadata)

            title = metadata.get("title") or metadata.get("og:title") or ""

            extraction = CandidateExtraction(
                url=url,
                domain=_derive_domain(url),
                title=title,
                source="web_research",
                kind="web",
                reason=f"Analyzed via research agent ({len(evidence_list)} evidence items)",
                metadata=metadata,
                discovered_at=_utcnow(),
            )

            # Extract images from evidence
            for ev in evidence_list:
                if ev.kind == "image" and ev.text:
                    if len(extraction.images) >= self._max_images:
                        break
                    extraction.images.append(CandidateImageData(image_url=ev.text))

            # Extract links from evidence
            for ev in evidence_list:
                if ev.kind == "link" and ev.text:
                    if ev.text not in extraction.links:
                        extraction.links.append(ev.text)

            # Extract public identifiers (usernames) from page text
            if combined_text:
                extraction.public_identifiers = _extract_usernames(combined_text)

            # Extract profile links
            profile_urls_seen: set[str] = set()
            for ev in evidence_list:
                if ev.kind == "profile_link" and ev.text:
                    if ev.text not in profile_urls_seen and len(extraction.public_profile_links) < self._max_profiles:
                        profile_urls_seen.add(ev.text)
                        platform = _guess_platform(ev.text)
                        extraction.public_profile_links.append(CandidateProfileData(
                            profile_url=ev.text,
                            platform=platform,
                            username=_extract_username_from_profile_url(ev.text, platform),
                            source_url=url,
                        ))

            # Also check links for profile patterns
            for link in extraction.links:
                if _is_profile_link(link) and link not in profile_urls_seen:
                    if len(extraction.public_profile_links) >= self._max_profiles:
                        break
                    profile_urls_seen.add(link)
                    platform = _guess_platform(link)
                    extraction.public_profile_links.append(CandidateProfileData(
                        profile_url=link,
                        platform=platform,
                        username=_extract_username_from_profile_url(link, platform),
                        source_url=url,
                    ))

            # Extract locations and dates from combined text
            if combined_text:
                extraction.locations = _extract_locations(combined_text)
                extraction.dates = _extract_dates(combined_text)

            candidates.append(ExtractedCandidate(
                extraction=extraction,
                source_evidence=evidence_list,
            ))

        return candidates

    def extract_from_discovery(self, candidates: list[DiscoveryCandidate]) -> list[ExtractedCandidate]:
        """Extract from DiscoveryEngine candidates (before research)."""
        result: list[ExtractedCandidate] = []
        for c in candidates:
            extraction = CandidateExtraction(
                url=c.url,
                domain=c.domain,
                title=c.title,
                source=c.source,
                kind=c.kind,
                reason=c.reason,
                metadata=c.metadata,
                discovered_at=c.discovered_at,
            )
            result.append(ExtractedCandidate(extraction=extraction, source_evidence=[]))
        return result