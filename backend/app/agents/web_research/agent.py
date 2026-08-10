"""Web research agent (roadmap Phase 19).

Investigates candidate pages with the heuristic planner + controlled tools,
recording traceable evidence into a `ResearchState`. Page counts, runtime,
per-domain request limits, robots.txt, and the SSRF guard (all Phase 22)
are enforced per candidate.
"""

from __future__ import annotations

from app.agents.web_research.policies import CrawlPolicies, RateLimiter, RobotsTxt, UrlGuard
from app.agents.web_research.planner import ToolPlanner
from app.agents.web_research.schemas import Evidence, ResearchOutput
from app.agents.web_research.state import ResearchState
from app.agents.web_research.tools import ToolError, WebToolbox, build_tool_registry
from app.discovery.context.models import SearchContext
from app.discovery.schemas import Candidate


class ResearchAgent:
    """Run the bounded investigation loop over candidate pages."""

    def __init__(
        self,
        planner: ToolPlanner | None = None,
        policies: CrawlPolicies | None = None,
        toolbox: WebToolbox | None = None,
    ) -> None:
        self._planner = planner or ToolPlanner()
        self._policies = policies or CrawlPolicies()
        self._toolbox = toolbox
        self._registry = None

    @property
    def registry(self):
        if self._registry is None and self._toolbox is not None:
            self._registry = build_tool_registry(self._toolbox)
        return self._registry

    async def research(
        self,
        candidates: list[Candidate],
        context: SearchContext | None = None,
    ) -> ResearchOutput:
        context = context or SearchContext()
        state = ResearchState(seed_urls=[c.url for c in candidates])

        for candidate in candidates:
            if not self._policies.within_budget(state):
                state.errors.append("research budget exhausted")
                break
            if not state.add_visit(candidate.url):
                continue

            links: list[str] = []
            html: str | None = None
            for step in self._planner.plan(candidate, context):
                tool = step.tool
                if self._toolbox is None or not self.registry.has(tool):
                    continue
                state.tool_calls += 1
                try:
                    if tool == "fetch_page":
                        html = await self.registry.execute(tool, url=candidate.url)
                    elif html is None:
                        state.errors.append(f"{candidate.url}: {tool}: skipped (page not fetched)")
                    elif tool == "extract_metadata":
                        metadata = await self.registry.execute(tool, html_text=html)
                        state.record_evidence(Evidence(url=candidate.url, kind="metadata", text="", metadata=metadata))
                    elif tool == "extract_text":
                        text = await self.registry.execute(tool, html_text=html)
                        state.record_evidence(Evidence(url=candidate.url, kind="page_text", text=text))
                    elif tool == "extract_links":
                        links = await self.registry.execute(tool, html_text=html, base_url=candidate.url)
                        for link in links:
                            state.add_discovered(link)
                    elif tool == "extract_images":
                        images = await self.registry.execute(tool, html_text=html, base_url=candidate.url)
                        for image in images:
                            if len(state.images) >= self._policies.max_images:
                                break
                            state.images.add(image)
                            state.record_evidence(Evidence(url=candidate.url, kind="image", text=image))
                    elif tool == "find_public_profile_links":
                        profiles = await self.registry.execute(tool, links=links)
                        for profile in profiles:
                            state.profiles.add(profile)
                            state.record_evidence(Evidence(url=candidate.url, kind="profile_link", text=profile))
                    elif tool == "find_external_profiles":
                        for profile in await self.registry.execute(tool, text=html):
                            state.profiles.add(profile)
                            state.record_evidence(Evidence(url=candidate.url, kind="profile_link", text=profile))
                except ToolError as exc:
                    state.errors.append(f"{candidate.url}: {tool}: {exc}")
                except Exception as exc:
                    state.errors.append(f"{candidate.url}: {tool}: unexpected {exc!r}")

        state.mark_finished()
        return self._to_output(state)

    def _to_output(self, state: ResearchState) -> ResearchOutput:
        return ResearchOutput(
            candidates_seen=state.page_count(),
            status="completed",
            evidence=state.evidence,
            profiles=sorted(state.profiles),
            images=sorted(state.images),
            links=sorted(state.discovered_urls),
            source_metadata=[
                {"url": url, "source": "agent_reach"}
                for url in sorted(state.visited_urls)
            ],
            errors=state.errors,
        )