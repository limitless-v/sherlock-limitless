"""Integration tests for candidate persistence (roadmap Phase 23)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.web_research.schemas import Evidence, ResearchOutput
from app.evidence.extraction import CandidateExtractor
from app.models.entities import Candidate, CandidateExtractedImage, CandidateProfile, CandidateLocation, CandidateDate, SearchHistory
from app.repositories.candidates import CandidateRepository
from app.services.candidate_service import CandidateService


@pytest.mark.asyncio
async def test_candidate_repository_create(db_session: AsyncSession) -> None:
    """Test creating a candidate with all related entities."""
    repo = CandidateRepository(db_session)

    # Create a search history entry first
    search = SearchHistory(
        user_id=1,
        uploaded_image="uploads/test.jpg",
    )
    db_session.add(search)
    await db_session.flush()
    await db_session.refresh(search)

    extractor = CandidateExtractor()
    evidence = [
        Evidence(
            url="https://example.com/profile",
            kind="page_text",
            text="John Doe @johndoe",
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

    candidates = await repo.create_candidates_bulk(search.id, [ec.extraction for ec in extracted])

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.search_id == search.id
    assert candidate.url == "https://example.com/profile"
    assert candidate.domain == "example.com"
    assert candidate.title == ""
    assert candidate.source == "web_research"

    # Check related entities
    await db_session.refresh(candidate, attribute_names=["images", "profiles", "locations", "dates"])
    assert len(candidate.images) == 1
    assert candidate.images[0].image_url == "https://example.com/avatar.jpg"
    assert len(candidate.profiles) == 1
    assert candidate.profiles[0].profile_url == "https://github.com/johndoe"
    assert candidate.profiles[0].platform == "github"
    assert candidate.profiles[0].username == "johndoe"


@pytest.mark.asyncio
async def test_candidate_repository_get_by_search(db_session: AsyncSession) -> None:
    """Test retrieving candidates for a search."""
    repo = CandidateRepository(db_session)

    search = SearchHistory(user_id=1, uploaded_image="uploads/test2.jpg")
    db_session.add(search)
    await db_session.flush()
    await db_session.refresh(search)

    extractor = CandidateExtractor()
    evidence1 = [Evidence(url="https://site1.com/a", kind="page_text", text="Page A")]
    evidence2 = [Evidence(url="https://site2.com/b", kind="page_text", text="Page B")]

    output1 = ResearchOutput(candidates_seen=1, status="completed", evidence=evidence1, profiles=[], images=[], links=[], source_metadata=[], errors=[])
    output2 = ResearchOutput(candidates_seen=1, status="completed", evidence=evidence2, profiles=[], images=[], links=[], source_metadata=[], errors=[])

    extracted1 = extractor.extract_from_research(output1)
    extracted2 = extractor.extract_from_research(output2)

    await repo.create_candidates_bulk(search.id, [extracted1[0].extraction, extracted2[0].extraction])

    candidates = await repo.get_candidates_by_search(search.id)
    assert len(candidates) == 2
    urls = {c.url for c in candidates}
    assert urls == {"https://site1.com/a", "https://site2.com/b"}


@pytest.mark.asyncio
async def test_candidate_repository_count(db_session: AsyncSession) -> None:
    """Test candidate count."""
    repo = CandidateRepository(db_session)

    search = SearchHistory(user_id=1, uploaded_image="uploads/test3.jpg")
    db_session.add(search)
    await db_session.flush()
    await db_session.refresh(search)

    extractor = CandidateExtractor()
    evidence = [Evidence(url="https://example.com/page", kind="page_text", text="Test")]
    output = ResearchOutput(candidates_seen=1, status="completed", evidence=evidence, profiles=[], images=[], links=[], source_metadata=[], errors=[])
    extracted = extractor.extract_from_research(output)

    count_before = await repo.get_candidate_count_by_search(search.id)
    assert count_before == 0

    await repo.create_candidates_bulk(search.id, [extracted[0].extraction])

    count_after = await repo.get_candidate_count_by_search(search.id)
    assert count_after == 1


@pytest.mark.asyncio
async def test_candidate_repository_update_images(db_session: AsyncSession) -> None:
    """Test updating candidate images after download."""
    repo = CandidateRepository(db_session)

    search = SearchHistory(user_id=1, uploaded_image="uploads/test4.jpg")
    db_session.add(search)
    await db_session.flush()
    await db_session.refresh(search)

    extractor = CandidateExtractor()
    evidence = [
        Evidence(url="https://example.com/page", kind="image", text="https://example.com/img1.jpg"),
        Evidence(url="https://example.com/page", kind="image", text="https://example.com/img2.jpg"),
    ]
    output = ResearchOutput(candidates_seen=1, status="completed", evidence=evidence, profiles=[], images=[], links=[], source_metadata=[], errors=[])
    extracted = extractor.extract_from_research(output)

    await repo.create_candidates_bulk(search.id, [extracted[0].extraction])
    candidate = extracted[0].extraction

    # Get the created candidate
    candidates = await repo.get_candidates_by_search(search.id)
    assert len(candidates) == 1
    created = candidates[0]

    # Update images with local paths and hashes
    from app.evidence.schemas import CandidateImageData
    new_images = [
        CandidateImageData(
            image_url="https://example.com/img1.jpg",
            local_path="cache/faces/img1.jpg",
            sha256="abc123",
            a_hash="1234",
            d_hash="5678",
            p_hash="9abc",
            width=200,
            height=200,
            content_type="image/jpeg",
            file_size=10240,
        ),
        CandidateImageData(
            image_url="https://example.com/img2.jpg",
            local_path="cache/faces/img2.jpg",
            sha256="def456",
            a_hash="abcd",
            d_hash="ef12",
            p_hash="3456",
            width=300,
            height=300,
            content_type="image/png",
            file_size=20480,
        ),
    ]

    await repo.update_candidate_images(created.id, new_images)

    await db_session.refresh(created, attribute_names=["images"])
    assert len(created.images) == 2
    assert created.images[0].local_path == "cache/faces/img1.jpg"
    assert created.images[0].sha256 == "abc123"
    assert created.images[1].sha256 == "def456"


@pytest.mark.asyncio
async def test_candidate_service_integration(db_session: AsyncSession) -> None:
    """Test CandidateService integration."""
    service = CandidateService(db_session)

    search = SearchHistory(user_id=1, uploaded_image="uploads/test5.jpg")
    db_session.add(search)
    await db_session.flush()
    await db_session.refresh(search)

    extractor = CandidateExtractor()
    evidence = [
        Evidence(url="https://example.com/profile", kind="page_text", text="Test @user"),
        Evidence(url="https://example.com/profile", kind="profile_link", text="https://twitter.com/user"),
    ]
    output = ResearchOutput(candidates_seen=1, status="completed", evidence=evidence, profiles=["https://twitter.com/user"], images=[], links=[], source_metadata=[], errors=[])
    extracted = extractor.extract_from_research(output)

    candidates = await service.persist_candidates(search.id, extracted)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.url == "https://example.com/profile"

    # Test retrieval
    retrieved = await service.get_candidates(search.id)
    assert len(retrieved) == 1

    count = await service.get_candidate_count(search.id)
    assert count == 1