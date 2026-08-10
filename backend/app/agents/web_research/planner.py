"""Tool planner (roadmap Phase 20).

Deterministic, heuristic planner — no LLM required. Produces an ordered
list of tool steps for a candidate URL. An optional LLM may replace this
planner in Phase 26 without touching the tools themselves.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.discovery.context.models import SearchContext
from app.discovery.schemas import Candidate


@dataclass
class PlanStep:
    """One planned tool call."""

    tool: str
    kwargs: dict = field(default_factory=dict)


class ToolPlanner:
    """Heuristic plan: fetch first, then extract signals, then find profiles."""

    def plan(self, candidate: Candidate, context: SearchContext) -> list[PlanStep]:
        steps = [
            PlanStep("fetch_page", {"url": candidate.url}),
            PlanStep("extract_metadata"),
            PlanStep("extract_text"),
            PlanStep("extract_links"),
            PlanStep("extract_images"),
            PlanStep("find_public_profile_links"),
            PlanStep("find_external_profiles"),
        ]
        return steps