"""Unit tests for candidate extraction (roadmap Phase 23)."""

from datetime import datetime, timezone

from app.agents.web_research.schemas import Evidence, ResearchOutput
from app.evidence.extraction import CandidateExtractor, ExtractedCandidate
from app.evidence.schemas import CandidateExtraction


def test_candidate_extractor_basic() -> None:
    """Test basic extraction from ResearchOutput."""
    extractor = CandidateExtractor()

    evidence = [
        Evidence(
            url="https://example.com/profile",
            kind="page_text",
            text="John Doe works at Acme Corp. Contact: @johndoe",
        ),
        Evidence(
            url="https://example.com/profile",
            kind="metadata",
            text="",
            metadata={"title": "John Doe - Profile", "og:title": "John Doe"},
        ),
        Evidence(
            url="https://example.com/profile",
            kind="profile_link",
            text="https://github.com/johndoe",
        ),
        Evidence(
            url="https://example.com/profile",
            kind="image",
            text="https://example.com/avatar.jpg",
        ),
    ]

    output = ResearchOutput(
        candidates_seen=1,
        status="completed",
        evidence=evidence,
        profiles=["https://github.com/johndoe"],
        images=["https://example.com/avatar.jpg"],
        links=[],
        source_metadata=[],
        errors=[],
    )

    extracted = extractor.extract_from_research(output)

    assert len(extracted) == 1
    ec = extracted[0]
    assert isinstance(ec, ExtractedCandidate)
    assert ec.extraction.url == "https://example.com/profile"
    assert ec.extraction.domain == "example.com"
    assert ec.extraction.title == "John Doe - Profile"
    assert "johndoe" in ec.extraction.public_identifiers
    assert len(ec.extraction.public_profile_links) == 1
    assert ec.extraction.public_profile_links[0].profile_url == "https://github.com/johndoe"
    assert ec.extraction.public_profile_links[0].platform == "github"
    assert len(ec.extraction.images) == 1
    assert ec.extraction.images[0].image_url == "https://example.com/avatar.jpg"


def test_candidate_extractor_multiple_candidates() -> None:
    """Test extraction groups by URL."""
    extractor = CandidateExtractor()

    evidence = [
        Evidence(url="https://site1.com/a", kind="page_text", text="Page A @user1"),
        Evidence(url="https://site1.com/a", kind="metadata", text="", metadata={"title": "Site 1"}),
        Evidence(url="https://site2.com/b", kind="page_text", text="Page B @user2"),
    ]

    output = ResearchOutput(
        candidates_seen=2,
        status="completed",
        evidence=evidence,
        profiles=[],
        images=[],
        links=[],
        source_metadata=[],
        errors=[],
    )

    extracted = extractor.extract_from_research(output)

    assert len(extracted) == 2
    urls = {ec.extraction.url for ec in extracted}
    assert urls == {"https://site1.com/a", "https://site2.com/b"}


def test_candidate_extractor_links_and_profiles() -> None:
    """Test link and profile link extraction."""
    extractor = CandidateExtractor()

    evidence = [
        Evidence(
            url="https://example.com/page",
            kind="page_text",
            text="Check out @alice on https://twitter.com/alice and https://linkedin.com/in/alice",
        ),
        Evidence(
            url="https://example.com/page",
            kind="link",
            text="https://twitter.com/alice",
        ),
        Evidence(
            url="https://example.com/page",
            kind="link",
            text="https://linkedin.com/in/alice",
        ),
        Evidence(
            url="https://example.com/page",
            kind="profile_link",
            text="https://github.com/alice",
        ),
    ]

    output = ResearchOutput(
        candidates_seen=1,
        status="completed",
        evidence=evidence,
        profiles=["https://github.com/alice"],
        images=[],
        links=[],
        source_metadata=[],
        errors=[],
    )

    extracted = extractor.extract_from_research(output)

    assert len(extracted) == 1
    ec = extracted[0]

    # Should have public identifiers from text
    assert "alice" in ec.extraction.public_identifiers

    # Should have profile links from both profile_link evidence and detected links
    profile_urls = {p.profile_url for p in ec.extraction.public_profile_links}
    assert "https://github.com/alice" in profile_urls
    assert "https://twitter.com/alice" in profile_urls
    # linkedin.com/in/ matches /in/ pattern
    assert "https://linkedin.com/in/alice" in profile_urls


def test_candidate_extractor_deduplication() -> None:
    """Test that duplicate profile links are deduplicated."""
    extractor = CandidateExtractor()

    evidence = [
        Evidence(url="https://example.com/page", kind="profile_link", text="https://twitter.com/bob"),
        Evidence(url="https://example.com/page", kind="link", text="https://twitter.com/bob"),
        Evidence(url="https://example.com/page", kind="link", text="https://twitter.com/bob"),
    ]

    output = ResearchOutput(
        candidates_seen=1,
        status="completed",
        evidence=evidence,
        profiles=["https://twitter.com/bob"],
        images=[],
        links=["https://twitter.com/bob", "https://twitter.com/bob"],
        source_metadata=[],
        errors=[],
    )

    extracted = extractor.extract_from_research(output)

    assert len(extracted) == 1
    ec = extracted[0]
    # Should only have one entry for the duplicate URL
    profile_urls = [p.profile_url for p in ec.extraction.public_profile_links]
    assert profile_urls.count("https://twitter.com/bob") == 1


def test_candidate_extraction_schema_serialization() -> None:
    """Test CandidateExtraction to_dict serialization."""
    extraction = CandidateExtraction(
        url="https://example.com/test",
        domain="example.com",
        title="Test Page",
        public_identifiers=["@user1", "@user2"],
        images=[
            type("Img", (), {"image_url": "https://example.com/img.jpg", "to_dict": lambda self: {"image_url": self.image_url}})()
        ],
    )

    data = extraction.to_dict()
    assert data["url"] == "https://example.com/test"
    assert data["domain"] == "example.com"
    assert data["title"] == "Test Page"
    assert data["public_identifiers"] == ["@user1", "@user2"]
    assert len(data["images"]) == 1


def test_candidate_extractor_max_limits() -> None:
    """Test max images/profiles limits are enforced."""
    extractor = CandidateExtractor(max_images_per_candidate=2, max_profiles_per_candidate=2)

    evidence = [
        Evidence(url="https://example.com/page", kind="image", text=f"https://example.com/img{i}.jpg")
        for i in range(5)
    ] + [
        Evidence(url="https://example.com/page", kind="profile_link", text=f"https://github.com/user{i}")
        for i in range(5)
    ]

    output = ResearchOutput(
        candidates_seen=1,
        status="completed",
        evidence=evidence,
        profiles=[f"https://github.com/user{i}" for i in range(5)],
        images=[f"https://example.com/img{i}.jpg" for i in range(5)],
        links=[],
        source_metadata=[],
        errors=[],
    )

    extracted = extractor.extract_from_research(output)

    assert len(extracted) == 1
    ec = extracted[0]
    assert len(ec.extraction.images) == 2
    assert len(ec.extraction.public_profile_links) == 2


def test_candidate_extractor_date_extraction() -> None:
    """Test date extraction from text."""
    extractor = CandidateExtractor()

    evidence = [
        Evidence(
            url="https://example.com/page",
            kind="page_text",
            text="Event on 2024-01-15T10:30:00 and Jan 15, 2024",
        ),
    ]

    output = ResearchOutput(
        candidates_seen=1,
        status="completed",
        evidence=evidence,
        profiles=[],
        images=[],
        links=[],
        source_metadata=[],
        errors=[],
    )

    extracted = extractor.extract_from_research(output)

    assert len(extracted) == 1
    ec = extracted[0]
    assert len(ec.extraction.dates) >= 1
    # Should find ISO date
    iso_dates = [d for d in ec.extraction.dates if d.date_type == "iso"]
    assert len(iso_dates) >= 1
    assert iso_dates[0].date_value.year == 2024


def test_candidate_extractor_location_extraction() -> None:
    """Test location extraction heuristic."""
    extractor = CandidateExtractor()

    evidence = [
        Evidence(
            url="https://example.com/page",
            kind="page_text",
            text="San Francisco, CA\nNew York City\n  not a location",
        ),
    ]

    output = ResearchOutput(
        candidates_seen=1,
        status="completed",
        evidence=evidence,
        profiles=[],
        images=[],
        links=[],
        source_metadata=[],
        errors=[],
    )

    extracted = extractor.extract_from_research(output)

    assert len(extracted) == 1
    ec = extracted[0]
    # Should extract capitalized lines as potential locations
    assert len(ec.extraction.locations) >= 1
    loc_texts = [loc.location for loc in ec.extraction.locations]
    assert any("San Francisco" in t for t in loc_texts)
    assert any("New York" in t for t in loc_texts)