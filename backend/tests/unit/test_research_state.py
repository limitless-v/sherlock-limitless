"""ResearchState unit tests (roadmap Phase 21)."""

from app.agents.web_research.schemas import Evidence
from app.agents.web_research.state import ResearchState


def test_add_visit_dedupes():
    state = ResearchState()
    assert state.add_visit("https://a.example") is True
    assert state.add_visit("https://a.example") is False
    assert state.page_count() == 1


def test_add_discovered_dedupes():
    state = ResearchState()
    assert state.add_discovered("https://a.example/x") is True
    assert state.add_discovered("https://a.example/x") is False
    assert len(state.discovered_urls) == 1


def test_record_evidence_keeps_source_url():
    state = ResearchState()
    state.record_evidence(Evidence(url="https://a.example", kind="link", text="x"))
    assert state.evidence[0].url == "https://a.example"


def test_mark_finished_sets_timestamp():
    state = ResearchState()
    assert state.finished_at is None
    state.mark_finished()
    assert state.finished_at is not None


def test_summary_counts():
    state = ResearchState()
    state.add_visit("https://a.example")
    state.add_discovered("https://b.example")
    state.record_evidence(Evidence(url="https://a.example", kind="metadata"))
    summary = state.summary()
    assert summary["pages_visited"] == 1
    assert summary["pages_discovered"] == 1
    assert summary["evidence_items"] == 1