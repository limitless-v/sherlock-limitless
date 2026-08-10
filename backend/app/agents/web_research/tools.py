"""Agent tools (roadmap Phase 20).

Controlled Python tools (+ a registry for optional LLM dispatch in Phase 26).
All network access is guarded by CrawlPolicies (SSRF, robots.txt, rate
limits, timeouts). The LLM, when wired later, chooses tool *names*; the
Python functions below always perform the actual operations.
"""

from __future__ import annotations

import html as html_module
import inspect
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.agents.web_research.policies import CrawlPolicies, RateLimiter, RobotsTxt, UrlGuard

_PROFILE_HOSTS = {
    "twitter.com",
    "x.com",
    "github.com",
    "instagram.com",
    "linkedin.com",
    "facebook.com",
    "youtube.com",
    "t.me",
    "reddit.com",
    "medium.com",
    "tiktok.com",
}

_PROFILE_PATH_PATTERNS = (
    "/profile/",
    "/user/",
    "/users/",
    "/u/",
    "/@",
)


class ToolError(RuntimeError):
    """A tool failed (network, parsing, or policy)."""


@dataclass
class ToolSpec:
    """One registered tool available to the (current or LLM) planner."""

    name: str
    description: str
    func: object

    def __post_init__(self) -> None:
        if not callable(self.func):
            raise TypeError("tool func must be callable")


class ToolRegistry:
    """Name -> callable registry; the interface an LLM planner would use."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, name: str, func, description: str) -> None:
        self._tools[name] = ToolSpec(name=name, description=description, func=func)

    def has(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> list[str]:
        return sorted(self._tools)

    async def execute(self, name: str, **kwargs):
        spec = self._tools[name]
        result = spec.func(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result


def _absolute_url(href: str, base_url: str) -> str:
    candidate = urljoin(base_url, href.strip())
    parsed = urlparse(candidate)
    return candidate if parsed.scheme in {"http", "https"} else ""


class WebToolbox:
    """Tools bound to an httpx client + crawl policies (Phase 22 enforced)."""

    def __init__(
        self,
        client,
        policies: CrawlPolicies,
        guard: UrlGuard | None = None,
        rate_limiter: RateLimiter | None = None,
        robots: RobotsTxt | None = None,
        web_searcher=None,
    ) -> None:
        self._client = client
        self._policies = policies
        self._guard = guard or UrlGuard(allow_domains=policies.allow_domains)
        self._rate_limiter = rate_limiter or RateLimiter(policies)
        self._robots = robots or RobotsTxt(policies)
        self._web_searcher = web_searcher

    # --- network tools -------------------------------------------------------

    async def fetch_page(self, url: str) -> str:
        """Fetch a public page (respecting SSRF, robots, rate limits)."""
        allowed, reason = self._guard.check(url)
        if not allowed:
            raise ToolError(f"fetch blocked: {reason}")
        domain = urlparse(url).hostname or ""
        await self._rate_limiter.acquire(domain)
        if not await self._robots.can_fetch(self._client, url):
            raise ToolError("fetch blocked by robots.txt")
        try:
            response = await self._client.get(
                url,
                timeout=self._policies.timeout_seconds,
                follow_redirects=False,
                headers={"User-Agent": self._policies.user_agent},
            )
            response.raise_for_status()
        except Exception as exc:
            raise ToolError(f"fetch failed: {exc}") from exc
        return response.text

    async def search_web(self, query: str) -> list[str]:
        """Web search via an injected searcher (returns result URLs)."""
        if self._web_searcher is None:
            raise ToolError("no web searcher configured")
        return await self._web_searcher(query)

    # --- parsing tools -------------------------------------------------------

    def extract_text(self, html_text: str, limit: int = 4000) -> str:
        soup = BeautifulSoup(html_text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = re.sub(r"[ \t]+", " ", soup.get_text("\n"))
        text = html_module.unescape(text)
        return "\n".join(line.strip() for line in text.splitlines() if line.strip())[:limit]

    def extract_links(self, html_text: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html_text, "html.parser")
        links = []
        for tag in soup.find_all("a", href=True):
            absolute = _absolute_url(tag["href"], base_url)
            if absolute and absolute not in links:
                links.append(absolute)
        return links

    def extract_images(self, html_text: str, base_url: str) -> list[str]:
        soup = BeautifulSoup(html_text, "html.parser")
        images: list[str] = []
        for tag in soup.find_all("img"):
            for attr in ("src", "data-src", "srcset"):
                value = tag.get(attr)
                if not value:
                    continue
                for candidate in re.split(r"\s*,\s*|\s+", value):
                    candidate = candidate.strip().split(" ")[0]
                    absolute = _absolute_url(candidate, base_url)
                    if absolute and absolute not in images:
                        images.append(absolute)
                break
        return images[: self._policies.max_images]

    def extract_metadata(self, html_text: str) -> dict:
        soup = BeautifulSoup(html_text, "html.parser")
        metadata: dict[str, str] = {}
        for tag in soup.find_all("meta"):
            name = tag.get("name") or tag.get("property")
            content = tag.get("content")
            if name and content and name not in metadata:
                metadata[name] = content.strip()
        if "title" not in metadata and soup.title:
            metadata["title"] = soup.title.get_text(strip=True)
        return metadata

    def find_public_profile_links(self, links: list[str]) -> list[str]:
        """Links that look like public profile pages (domain/path patterns)."""
        profiles = []
        for link in links:
            parsed = urlparse(link)
            host = (parsed.hostname or "").lower()
            domain = ".".join(host.split(".")[-2:]) if host.count(".") >= 1 else host
            path = parsed.path.lower()
            if any(p in path for p in _PROFILE_PATH_PATTERNS) or domain in _PROFILE_HOSTS:
                if link not in profiles:
                    profiles.append(link)
        return profiles

    def find_external_profiles(self, text: str) -> list[str]:
        """Guess external profile URLs from @handles found in text."""
        handles = set(re.findall(r"(?<![\w@])@([A-Za-z0-9_.]{2,30})\b", text))
        profiles = []
        for handle in sorted(handles):
            candidates = (f"https://twitter.com/{handle}", f"https://github.com/{handle}")
            profiles.extend(c for c in candidates if c not in profiles)
        return profiles


def build_tool_registry(toolbox: WebToolbox) -> ToolRegistry:
    """Expose toolbox methods as named tools (for current & LLM planners)."""
    registry = ToolRegistry()
    registry.register("fetch_page", toolbox.fetch_page, "Fetch a public page's HTML.")
    registry.register("search_web", toolbox.search_web, "Run a public web search for a query.")
    registry.register("extract_text", toolbox.extract_text, "Extract visible text from HTML.")
    registry.register("extract_links", toolbox.extract_links, "Extract absolute links from HTML.")
    registry.register("extract_images", toolbox.extract_images, "Extract image URLs from HTML.")
    registry.register("extract_metadata", toolbox.extract_metadata, "Extract page metadata (title/OG).")
    registry.register("find_public_profile_links", toolbox.find_public_profile_links, "Find public profile links.")
    registry.register("find_external_profiles", toolbox.find_external_profiles, "Guess external profiles from handles.")
    return registry