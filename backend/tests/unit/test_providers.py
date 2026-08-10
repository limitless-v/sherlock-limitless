"""Search provider interface tests (roadmap Phase 17)."""

import pytest

from app.discovery.context.models import SearchContext
from app.discovery.providers.base import ImageSearchProvider, ProviderRegistry, WebSearchProvider
from app.discovery.schemas import Candidate


def test_image_provider_is_abstract():
    with pytest.raises(TypeError):
        ImageSearchProvider()


def test_web_provider_is_abstract():
    with pytest.raises(TypeError):
        WebSearchProvider()


class ConcreteWeb(WebSearchProvider):
    name = "concrete-web"

    async def search(self, query, context):
        return [Candidate(url=f"https://example/{query}", source=self.name)]


class ConcreteImage(ImageSearchProvider):
    name = "concrete-image"

    async def search(self, image, context):
        return [Candidate(url="https://example/img", source=self.name, kind="image")]


async def test_concrete_providers_are_replaceable():
    context = SearchContext(keywords=["kochi"])
    web = ConcreteWeb()
    img = ConcreteImage()

    assert {c.url for c in await web.search("kochi", context)} == {"https://example/kochi"}
    assert {c.url for c in await img.search(None, context)} == {"https://example/img"}
    assert web.name == "concrete-web"
    assert img.name == "concrete-image"


def test_registry_tracks_and_filters_providers():
    registry = ProviderRegistry()
    registry.register_web(ConcreteWeb())
    registry.register_image(ConcreteImage())

    assert [p.name for p in registry.web_providers()] == ["concrete-web"]
    assert [p.name for p in registry.image_providers()] == ["concrete-image"]
    assert [p.name for p in registry.web_providers(available_only=False)] == ["concrete-web"]