"""Crawl policies (roadmap Phase 22).

Hard limits and controls for the research agent:

- bounded page/image/request budgets
- robots.txt where applicable (stdlib robotparser)
- per-domain rate limiting
- SSRF guard: never request localhost/private/metadata endpoints

No bypass mechanisms are implemented or intended.
"""

from __future__ import annotations

import asyncio
import ipaddress
import time
import urllib.robotparser
from dataclasses import dataclass, field
from urllib.parse import urlparse

from app.agents.web_research.state import ResearchState

_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "::1",
        "169.254.169.254",
        "0.0.0.0",
        "metadata.google.internal",
        "metadata.google.internal.",
    }
)


class CrawlPolicyError(RuntimeError):
    """A crawl limit/guard blocked an action."""


@dataclass(frozen=True)
class CrawlPolicies:
    """Immutable limits enforced by the research agent."""

    max_pages: int = 20
    max_depth: int = 3
    max_images: int = 50
    max_runtime_seconds: float = 120.0
    max_requests_per_domain: int = 30
    per_domain_min_interval: float = 1.0
    timeout_seconds: float = 10.0
    respect_robots: bool = True
    user_agent: str = "FaceSearchOSINT/1.0 (+research)"
    allow_domains: tuple[str, ...] = ()

    def within_budget(self, state: ResearchState, now: float | None = None) -> bool:
        """False when page count or runtime budget is exhausted."""
        if state.page_count() >= self.max_pages:
            return False
        started = state.started_at.timestamp()
        elapsed = (now or time.time()) - started
        return elapsed <= self.max_runtime_seconds


class UrlGuard:
    """SSRF protection for outbound requests."""

    def __init__(self, blocked_hosts: frozenset[str] = _BLOCKED_HOSTS, allow_domains: tuple[str, ...] = ()) -> None:
        self._blocked = blocked_hosts
        self._allow = tuple(d.lower().lstrip(".") for d in allow_domains)

    def check(self, url: str) -> tuple[bool, str]:
        """Return (allowed, reason). Reason is empty when allowed."""
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False, f"scheme not allowed: {parsed.scheme or 'none'}"
        host = (parsed.hostname or "").lower().rstrip(".")
        if not host:
            return False, "no host"
        if self._allow:
            if any(host == d or host.endswith(f".{d}") for d in self._allow):
                return True, ""
            return False, f"host not in allowlist: {host}"
        if host in self._blocked:
            return False, f"blocked host: {host}"
        if host.startswith("metadata"):
            return False, f"blocked host: {host}"
        # Literal IPs: reject loopback/private/link-local/unspecified ranges.
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            return True, ""  # hostname; DNS resolution happens at fetch time
        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_unspecified:
            return False, f"blocked IP range: {host}"
        return True, ""


class RateLimiter:
    """Per-domain min-interval spacing with a hard request cap."""

    def __init__(self, policies: CrawlPolicies) -> None:
        self._policies = policies
        self._last: dict[str, float] = {}
        self._counts: dict[str, int] = {}

    async def acquire(self, domain: str) -> None:
        """Wait out the min interval and enforce the per-domain cap."""
        now = time.monotonic()
        last = self._last.get(domain, 0.0)
        wait = self._policies.per_domain_min_interval - (now - last)
        count = self._counts.get(domain, 0)
        if count >= self._policies.max_requests_per_domain:
            raise CrawlPolicyError(f"per-domain request limit reached for {domain}")
        if wait > 0:
            await asyncio.sleep(wait)
        self._last[domain] = time.monotonic()
        self._counts[domain] = count + 1


class RobotsTxt:
    """Lazy per-domain robots.txt checker (stdlib robotparser)."""

    def __init__(self, policies: CrawlPolicies) -> None:
        self._policies = policies
        self._cache: dict[str, urllib.robotparser.RobotFileParser] = {}

    async def can_fetch(self, client, url: str) -> bool:
        """Allow fetching `url` under robots.txt rules.

        Robots is advisory: if it cannot be fetched we allow the request
        (and never block legitimate research on robots-server outages).
        """
        if not self._policies.respect_robots:
            return True
        parsed = urlparse(url)
        domain = (parsed.hostname or "").lower()
        if domain in self._cache:
            return self._cache[domain].can_fetch(self._policies.user_agent, url)
        parser = urllib.robotparser.RobotFileParser()
        try:
            response = await client.get(
                f"{parsed.scheme}://{parsed.netloc}/robots.txt",
                timeout=self._policies.timeout_seconds,
                follow_redirects=True,
            )
            response.raise_for_status()
            parser.parse(response.text.splitlines())
        except Exception:
            self._cache[domain] = parser  # permissive on robots outage
            return True
        self._cache[domain] = parser
        return parser.can_fetch(self._policies.user_agent, url)