"""Crawl policies unit tests (roadmap Phase 22): budgets, SSRF, rate limits."""

import pytest

from app.agents.web_research.policies import CrawlPolicies, CrawlPolicyError, RateLimiter, RobotsTxt, UrlGuard
from app.agents.web_research.state import ResearchState


def _state(existing_pages: int = 0) -> ResearchState:
    state = ResearchState()
    for i in range(existing_pages):
        state.add_visit(f"https://p{i}.example")
    return state


def test_within_budget_page_cap():
    policies = CrawlPolicies(max_pages=2)
    assert policies.within_budget(_state(1)) is True
    assert policies.within_budget(_state(2)) is False


def test_within_budget_runtime_cap():
    state = _state()
    expired = state.started_at.timestamp() + 10_000.0
    assert CrawlPolicies(max_runtime_seconds=1.0).within_budget(state, now=expired) is False


# --- SSRF guard ------------------------------------------------------------

@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/x",
        "http://127.0.0.1/x",
        "http://::1/x",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.1/x",
        "http://192.168.1.1/x",
        "http://0.0.0.0/x",
        "http://metadata.google.internal/x",
        "ftp://example.com/x",
        "file:///etc/passwd",
    ],
)
def test_guard_blocks_ssrf_and_bad_schemes(url):
    allowed, reason = UrlGuard().check(url)
    assert allowed is False
    assert reason


def test_guard_allows_public_hostname():
    assert UrlGuard().check("https://example.com/page") == (True, "")


def test_guard_allows_allowlist_host_and_subdomain():
    guard = UrlGuard(allow_domains=("example.com",))
    assert guard.check("https://example.com/x")[0] is True
    assert guard.check("https://sub.example.com/x")[0] is True
    assert guard.check("https://other.com/x")[0] is False


# --- rate limiter ----------------------------------------------------------

async def test_rate_limiter_honors_cap():
    policies = CrawlPolicies(max_requests_per_domain=2, per_domain_min_interval=0.0)
    limiter = RateLimiter(policies)
    await limiter.acquire("example.com")
    await limiter.acquire("example.com")
    with pytest.raises(CrawlPolicyError):
        await limiter.acquire("example.com")


# --- robots -----------------------------------------------------------------

class _NoopClient:
    async def get(self, *args, **kwargs):
        raise AssertionError("robots fetch should not run when disabled")


async def test_robots_skipped_when_disabled():
    policies = CrawlPolicies(respect_robots=False)
    robots = RobotsTxt(policies)
    assert await robots.can_fetch(_NoopClient(), "https://example.com/x") is True


async def test_robots_permissive_on_outage():
    class _FailingClient:
        async def get(self, *args, **kwargs):
            raise OSError("robots.txt unreachable")

    robots = RobotsTxt(CrawlPolicies(respect_robots=True))
    assert await robots.can_fetch(_FailingClient(), "https://example.com/x") is True