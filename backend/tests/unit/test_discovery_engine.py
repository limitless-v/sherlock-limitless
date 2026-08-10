"""Discovery Engine unit tests (roadmap Phase 16)."""

from pathlib import Path

from app.discovery.context.models import SearchContext
from app.discovery.engine import DiscoveryEngine
from app.discovery.providers.base import ImageSearchProvider, WebSearchProvider
from app.discovery.schemas import Candidate, canonical_url, derive_domain


class FakeWeb(WebSearchProvider):
    name = "fw"

    async def search(self, query, context):
        return [Candidate(url=f"https://fw.example/result?q={query}", source=self.name, title=f"R {query}")]


class FakeDuplicateWeb(WebSearchProvider):
    name = "fw2"

    async def search(self, query, context):
        return [Candidate(url=f"https://fw.example/result?q={query}", source=self.name)]


class UnavailableWeb(WebSearchProvider):
    name = "never-runs"

    @property
    def available(self) -> bool:
        return False

    async def search(self, query, context):
        raise AssertionError("unavailable provider must not be invoked")


class FakeImage(ImageSearchProvider):
    name = "fi"

    async def search(self, image, context):
        return [Candidate(url="https://img.example/one", source=self.name, kind="image")]


def _context() -> SearchContext:
    return SearchContext(keywords=["kochi", "marine"], location="9.58, 76.25 (approx)")


def test_available_providers_filters_unavailable():
    engine = DiscoveryEngine(image_providers=[FakeImage()], web_providers=[FakeWeb(), UnavailableWeb()])
    assert engine.available_providers() == ["fi", "fw"]


async def test_discover_runs_available_providers_and_deduplicates():
    engine = DiscoveryEngine(
        image_providers=[FakeImage()],
        web_providers=[FakeWeb(), FakeDuplicateWeb(), UnavailableWeb()],
        max_candidates=100,
    )
    results = await engine.discover(_context(), image=Path("x.png"), max_candidates=10)

    urls = {c.url for c in results}
    # 1 image + 3 unique web queries; fw2's duplicates of fw collapsed
    assert len(results) == 4
    assert "https://img.example/one" in urls
    assert all(c.domain in {"fw.example", "img.example"} for c in results)
    assert all(c.kind in {"image", "web"} for c in results)


async def test_discover_respects_max_candidates():
    engine = DiscoveryEngine(image_providers=[FakeImage()], web_providers=[FakeWeb()], max_candidates=100)
    results = await engine.discover(_context(), max_candidates=2)
    assert len(results) == 2


async def test_discover_no_providers_returns_empty():
    engine = DiscoveryEngine()
    assert await engine.discover(_context()) == []
    assert engine.available_providers() == []


def test_candidate_derives_domain_and_canonical_url():
    candidate = Candidate(url="HTTP://Sub.Example.COM:8080/a")
    assert candidate.domain == "sub.example.com:8080"
    # scheme + host are lowercased; the path stays case-sensitive
    assert canonical_url("HTTPS://Ex.COM/A") == "https://ex.com/A"
    assert derive_domain("example.com") == "example.com"