"""ResearchAgent loop tests (roadmap Phase 19) with a fake toolbox (no network)."""

import pytest

from app.agents.web_research.agent import ResearchAgent
from app.agents.web_research.policies import CrawlPolicies
from app.agents.web_research.tools import WebToolbox
from app.discovery.context.models import SearchContext
from app.discovery.schemas import Candidate

SAMPLE_HTML = """
<html>
  <head><title>Alice</title></head>
  <body>
    <a href="https://twitter.com/alice_page">profile</a>
    <img src="/pic.jpg">
    <p>reach me @alice_official</p>
  </body>
</html>
"""


class FakeToolbox(WebToolbox):
    """A WebToolbox whose fetch_page returns canned HTML (no network)."""

    async def fetch_page(self, url: str) -> str:
        return SAMPLE_HTML

    async def search_web(self, query: str) -> list[str]:
        return ["https://search.example/0"]


@pytest.fixture
def agent():
    policies = CrawlPolicies(max_pages=5, max_images=10)
    toolbox = FakeToolbox(client=None, policies=policies)
    return ResearchAgent(policies=policies, toolbox=toolbox)


async def test_research_returns_evidence_and_signals(agent):
    candidates = [
        Candidate(url="https://host.example/alice", source="agent_reach"),
        Candidate(url="https://host2.example/bob", source="agent_reach"),
    ]
    output = await agent.research(candidates)

    assert output.status == "completed"
    assert output.candidates_seen == 2
    assert output.profiles  # twitter/github links found via extraction
    assert output.images  # absolute image URLs
    assert output.links  # discovered links
    assert output.evidence
    assert all(e.url for e in output.evidence)


async def test_research_respects_budget(agent):
    candidates = [Candidate(url=f"https://p{i}.example", source="x") for i in range(10)]
    policies = CrawlPolicies(max_pages=2)
    toolbox = FakeToolbox(client=None, policies=policies)
    agent = ResearchAgent(policies=policies, toolbox=toolbox)

    output = await agent.research(candidates)
    assert output.candidates_seen == 2


async def test_research_without_toolbox_returns_empty_state():
    agent = ResearchAgent(policies=CrawlPolicies())
    output = await agent.research([Candidate(url="https://host.example/x")])
    assert output.status == "completed"
    assert output.candidates_seen == 1
    assert output.evidence == []