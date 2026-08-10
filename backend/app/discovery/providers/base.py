"""Search provider interfaces (roadmap Phase 17).

Replaceable discovery backends. Contracts mirror the roadmap:

    ImageSearchProvider.search(image, context) -> candidates
    WebSearchProvider.search(query, context)    -> candidates

Providers must only use permitted/public interfaces and never bypass
search-engine protections (rate limits, robots.txt, CAPTCHAs, auth).

Providers also report availability and capabilities so callers can show
explicit provider status instead of silently returning zero results.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from app.discovery.context.models import SearchContext
from app.discovery.schemas import Candidate


@dataclass(frozen=True)
class ProviderStatus:
    """Machine-readable provider health for UIs / search responses."""

    name: str
    available: bool
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "available": self.available,
            "capabilities": list(self.capabilities),
            "reason": self.reason,
        }


class ImageSearchProvider(ABC):
    """Reverse-image search over public sources."""

    name: str = "image-provider"
    kind: str = "image"

    @property
    def available(self) -> bool:
        return True

    @property
    def availability_reason(self) -> str:
        return "" if self.available else "provider unavailable"

    def capabilities(self) -> list[str]:
        return [self.kind]

    def status(self) -> ProviderStatus:
        try:
            available = bool(self.available)
        except NotImplementedError:
            available, reason = False, "availability probe not implemented"
        else:
            reason = "" if available else self.availability_reason
        return ProviderStatus(self.name, available, tuple(self.capabilities()), reason)

    @abstractmethod
    async def search(self, image: Path | None, context: SearchContext) -> list[Candidate]:
        """Find public pages that contain (a match of) the image."""


class WebSearchProvider(ABC):
    """Keyword web search over public sources."""

    name: str = "web-provider"
    kind: str = "web"

    @property
    def available(self) -> bool:
        return True

    @property
    def availability_reason(self) -> str:
        return "" if self.available else "provider unavailable"

    def capabilities(self) -> list[str]:
        return [self.kind]

    def status(self) -> ProviderStatus:
        try:
            available = bool(self.available)
        except NotImplementedError:
            available, reason = False, "availability probe not implemented"
        else:
            reason = "" if available else self.availability_reason
        return ProviderStatus(self.name, available, tuple(self.capabilities()), reason)

    @abstractmethod
    async def search(self, query: str, context: SearchContext) -> list[Candidate]:
        """Find public pages relevant to `query`."""


class ProviderRegistry:
    """Annotate/manage registered providers (registration is optional)."""

    def __init__(self) -> None:
        self._image: dict[str, ImageSearchProvider] = {}
        self._web: dict[str, WebSearchProvider] = {}

    def register_image(self, provider: ImageSearchProvider) -> None:
        self._image[provider.name] = provider

    def register_web(self, provider: WebSearchProvider) -> None:
        self._web[provider.name] = provider

    def image_providers(self, available_only: bool = True) -> list[ImageSearchProvider]:
        items = [p for p in self._image.values() if not available_only or p.available]
        return items

    def web_providers(self, available_only: bool = True) -> list[WebSearchProvider]:
        return [p for p in self._web.values() if not available_only or p.available]

    def statuses(self) -> list[ProviderStatus]:
        return [p.status() for p in (*self._image.values(), *self._web.values())]