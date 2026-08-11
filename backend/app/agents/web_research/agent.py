"""Web research agent (roadmap Phase 19).

Investigates candidate pages with the heuristic planner + controlled tools,
recording traceable evidence into a `ResearchState`. Page counts, runtime,
per-domain request limits, robots.txt, and the SSRF guard (all Phase 22)
are enforced per candidate.

Phase 23: Integrates CandidateExtractor for incremental candidate persistence.
Phase 24: Integrates EvidenceGraph for building evidence connections.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.web_research.policies import CrawlPolicies, RateLimiter, RobotsTxt, UrlGuard
from app.agents.web_research.planner import ToolPlanner
from app.agents.web_research.schemas import Evidence, ResearchOutput
from app.agents.web_research.state import ResearchState
from app.agents.web_research.tools import ToolError, WebToolbox, build_tool_registry
from app.discovery.context.models import SearchContext
from app.discovery.schemas import Candidate
from app.evidence.extraction import ExtractedCandidate
from app.evidence.graph import EvidenceGraph
from app.evidence.schemas import EvidenceEdgeData, EvidenceNodeData
from app.services.candidate_service import CandidateService
from app.services.evidence_graph_service import EvidenceGraphService


@dataclass
class ResearchResult:
    """Research output plus extracted candidates for persistence."""
    output: ResearchOutput
    extracted_candidates: list[ExtractedCandidate]
    evidence_graph: EvidenceGraph | None = None


class ResearchAgent:
    """Run the bounded investigation loop over candidate pages."""

    def __init__(
        self,
        planner: ToolPlanner | None = None,
        policies: CrawlPolicies | None = None,
        toolbox: WebToolbox | None = None,
        candidate_service: CandidateService | None = None,
        evidence_graph_service: EvidenceGraphService | None = None,
    ) -> None:
        self._planner = planner or ToolPlanner()
        self._policies = policies or CrawlPolicies()
        self._toolbox = toolbox
        self._registry = None
        self._candidate_service = candidate_service
        self._evidence_graph_service = evidence_graph_service

    @property
    def registry(self):
        if self._registry is None and self._toolbox is not None:
            self._registry = build_tool_registry(self._toolbox)
        return self._registry

    async def research(
        self,
        candidates: list[Candidate],
        context: SearchContext | None = None,
        search_id: int | None = None,
    ) -> ResearchResult:
        context = context or SearchContext()
        state = ResearchState(seed_urls=[c.url for c in candidates])
        all_extracted: list[ExtractedCandidate] = []

        # Phase 24: Initialize evidence graph
        evidence_graph: EvidenceGraph | None = None
        if self._evidence_graph_service is not None and search_id is not None:
            evidence_graph = self._evidence_graph_service.create_graph(search_id)

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

            # Phase 23: Extract candidate after processing each URL
            if self._candidate_service is not None:
                try:
                    candidate_evidence = [ev for ev in state.evidence if ev.url == candidate.url]
                    if candidate_evidence:
                        temp_output = ResearchOutput(
                            candidates_seen=1,
                            status="completed",
                            evidence=candidate_evidence,
                            profiles=sorted(state.profiles),
                            images=sorted(state.images),
                            links=sorted(state.discovered_urls),
                            source_metadata=[
                                {"url": url, "source": "agent_reach"}
                                for url in sorted(state.visited_urls)
                            ],
                            errors=[e for e in state.errors if candidate.url in e],
                        )
                        extracted = self._candidate_service.extract_from_research(temp_output)
                        if extracted:
                            all_extracted.extend(extracted)
                except Exception as exc:
                    state.errors.append(f"{candidate.url}: candidate_extraction: {exc!r}")

            # Phase 24: Build evidence graph from this candidate's evidence
            if evidence_graph is not None and candidate_evidence:
                self._build_evidence_graph(evidence_graph, candidate.url, candidate_evidence, state)

        state.mark_finished()
        return ResearchResult(
            output=self._to_output(state),
            extracted_candidates=all_extracted,
            evidence_graph=evidence_graph,
        )

    def _build_evidence_graph(
        self,
        graph: EvidenceGraph,
        candidate_url: str,
        evidence: list[Evidence],
        state: ResearchState,
    ) -> None:
        """Build evidence graph nodes and edges from candidate evidence."""
        # Create URL node for the candidate page
        url_node_id = graph.add_node(
            node_type="url",
            entity_id=candidate_url,
            entity_value=candidate_url,
            source_url=candidate_url,
        )

        # Create domain node
        from urllib.parse import urlparse
        parsed = urlparse(candidate_url)
        domain = parsed.netloc.lower()
        if domain:
            domain_node_id = graph.add_node(
                node_type="domain",
                entity_id=domain,
                entity_value=domain,
                source_url=candidate_url,
            )
            # URL belongs to domain
            graph.add_edge(
                source_node_id=url_node_id,
                target_node_id=domain_node_id,
                edge_type="links_to",
                source_url=candidate_url,
            )

        # Process evidence to create nodes and edges
        for ev in evidence:
            if ev.kind == "image" and ev.text:
                # Image node
                image_node_id = graph.add_node(
                    node_type="image",
                    entity_id=ev.text,
                    entity_value=ev.text,
                    source_url=candidate_url,
                )
                # Image found on URL
                graph.add_edge(
                    source_node_id=image_node_id,
                    target_node_id=url_node_id,
                    edge_type="image_found_on",
                    source_url=candidate_url,
                )

            elif ev.kind == "profile_link" and ev.text:
                # Profile node
                profile_node_id = graph.add_node(
                    node_type="profile",
                    entity_id=ev.text,
                    entity_value=ev.text,
                    source_url=candidate_url,
                )
                # Profile found on URL
                graph.add_edge(
                    source_node_id=profile_node_id,
                    target_node_id=url_node_id,
                    edge_type="image_found_on",  # Using image_found_on for "found on"
                    source_url=candidate_url,
                )

                # Extract username from profile URL if possible
                from app.evidence.extraction import _guess_platform, _extract_username_from_profile_url
                platform = _guess_platform(ev.text)
                username = _extract_username_from_profile_url(ev.text, platform)
                if username:
                    username_node_id = graph.add_node(
                        node_type="username",
                        entity_id=f"{platform}:{username}",
                        entity_value=username,
                        attributes={"platform": platform},
                        source_url=candidate_url,
                    )
                    # Username same as profile
                    graph.add_edge(
                        source_node_id=profile_node_id,
                        target_node_id=username_node_id,
                        edge_type="same_public_identifier",
                        source_url=candidate_url,
                    )

            elif ev.kind == "link" and ev.text:
                # Linked URL node
                link_url = ev.text
                link_node_id = graph.add_node(
                    node_type="url",
                    entity_id=link_url,
                    entity_value=link_url,
                    source_url=candidate_url,
                )
                # URL links to URL
                graph.add_edge(
                    source_node_id=url_node_id,
                    target_node_id=link_node_id,
                    edge_type="links_to",
                    source_url=candidate_url,
                )

        # Add usernames from public identifiers (already extracted in candidate service)
        for ev in evidence:
            if ev.kind == "page_text" and ev.text:
                from app.evidence.extraction import _extract_usernames
                usernames = _extract_usernames(ev.text)
                for username in usernames:
                    username_node_id = graph.add_node(
                        node_type="username",
                        entity_id=f"extracted:{username}",
                        entity_value=username,
                        source_url=candidate_url,
                    )
                    # Username mentioned on URL
                    graph.add_edge(
                        source_node_id=username_node_id,
                        target_node_id=url_node_id,
                        edge_type="mentions",
                        source_url=candidate_url,
                    )

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