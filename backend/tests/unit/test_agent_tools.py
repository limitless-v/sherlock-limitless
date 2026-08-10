"""Research agent tool tests (roadmap Phase 20)."""

import pytest

from app.agents.web_research.policies import CrawlPolicies
from app.agents.web_research.tools import WebToolbox, build_tool_registry

SAMPLE_HTML = """
<html>
  <head>
    <meta name="description" content="hello world">
    <title>Sample Page</title>
  </head>
  <body>
    <a href="/profile/alice">alice</a>
    <a href="https://public.example/about">about</a>
    <img src="/photo.jpg" data-src="/photo2.jpg">
    <p>Contact @alice_doe and @bob on twitter.</p>
    <script>var x = 1;</script>
  </body>
</html>
"""


def _toolbox():
    return WebToolbox(client=None, policies=CrawlPolicies())


def test_extract_text_strips_scripts_and_whitespace():
    text = _toolbox().extract_text(SAMPLE_HTML)
    assert "Contact" in text
    assert "var x" not in text


def test_extract_links_makes_absolute():
    links = _toolbox().extract_links(SAMPLE_HTML, "https://host.example/base")
    assert "https://host.example/profile/alice" in links
    assert "https://public.example/about" in links


def test_extract_images_prefers_first_attr():
    images = _toolbox().extract_images(SAMPLE_HTML, "https://host.example/base")
    assert images[0] == "https://host.example/photo.jpg"


def test_extract_metadata_captures_meta_and_title():
    metadata = _toolbox().extract_metadata(SAMPLE_HTML)
    assert metadata["description"] == "hello world"
    assert metadata["title"] == "Sample Page"


def test_find_public_profile_links_matches_path_and_domain():
    links = [
        "https://host.example/profile/alice",
        "https://github.com/someone",
        "https://host.example/about",
    ]
    profiles = _toolbox().find_public_profile_links(links)
    assert "https://host.example/profile/alice" in profiles
    assert "https://github.com/someone" in profiles
    assert "https://host.example/about" not in profiles


def test_find_external_profiles_from_handles():
    profiles = _toolbox().find_external_profiles("Contact @alice_doe today")
    assert "https://twitter.com/alice_doe" in profiles


async def test_registry_execute_dispatches():
    toolbox = _toolbox()
    registry = build_tool_registry(toolbox)
    assert registry.has("extract_metadata")
    assert set(registry.names()) >= {"extract_metadata", "extract_text", "fetch_page"}
    metadata = await registry.execute("extract_metadata", html_text=SAMPLE_HTML)
    assert metadata["title"] == "Sample Page"


async def test_registry_unknown_tool_raises_keyerror():
    from app.agents.web_research.tools import ToolRegistry

    with pytest.raises(KeyError):
        await ToolRegistry().execute("nope")