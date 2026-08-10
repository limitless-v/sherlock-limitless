"""Discovery Engine (roadmap Phase 16).

Generates discovery tasks from a SearchContext, runs only available
providers, normalizes their output, deduplicates candidates, and returns a
bounded candidate list for later research phases.

    DiscoveryEngine
       |-- ImageSearch providers (image, context)
       |-- WebSearch providers   (query, context)
       |-- AgentReach            (Phase 18)
       `-- LocalSearch           (local FAISS results)

Agent Reach and LocalSearch are integrated in later phases; the engine
itself is provider-agnostic and works from the provider lists it is given.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path

from app.discovery.context.models import SearchContext
from app.discovery.providers.base import ImageSearchProvider, ProviderStatus, WebSearchProvider
from app.discovery.schemas import Candidate, DiscoveryTask, canonical_url, derive_domain

_WEB_QUERY_SLOTS = 5  # number of top keywords turned into web queries


class DiscoveryEngine:
    """Route search context through available providers into candidates."""

    def __init__(
        self,
        image_providers: Sequence[ImageSearchProvider] = (),
        web_providers: Sequence[WebSearchProvider] = (),
        max_candidates: int = 20,
    ) -> None:
        self._image_providers = tuple(image_providers)
        self._web_providers = tuple(web_providers)
        self._max_candidates = max_candidates

    # --- capabilities ------------------------------------------------------

    def available_providers(self) -> list[str]:
        """Names of providers currently safe to invoke."""
        names = [p.name for p in self._image_providers if p.available]
        names += [p.name for p in self._web_providers if p.available]
        return names

    def provider_statuses(self) -> list[ProviderStatus]:
        """Health of every registered provider, available or not."""
        return [p.status() for p in (*self._image_providers, *self._web_providers)]

    # --- task generation ----------------------------------------------------

    def _generate_tasks(
        self,
        context: SearchContext,
        image: Path | None,
    ) -> list[DiscoveryTask]:
        tasks: list[DiscoveryTask] = []
        for provider in self._image_providers:
            if provider.available:
                tasks.append(DiscoveryTask(provider.name, "image", image=image, context=context))
        for query in self._build_queries(context):
            for provider in self._web_providers:
                if provider.available:
                    tasks.append(DiscoveryTask(provider.name, "web", query=query, context=context))
        return tasks

    @staticmethod
    def _build_queries(context: SearchContext) -> list[str]:
        """Turn context signals into web queries (top keywords + location)."""
        queries: list[str] = []
        for keyword in context.keywords[:_WEB_QUERY_SLOTS]:
            if keyword and keyword not in queries:
                queries.append(keyword)
        if context.location:
            top = queries[0] if queries else ""
            combined = f"{top} {context.location}".strip() if top else context.location
            if combined not in queries:
                queries.append(combined)
        return queries

    # --- execution ----------------------------------------------------------

    async def discover(
        self,
        context: SearchContext,
        image: Path | None = None,
        max_candidates: int | None = None,
    ) -> list[Candidate]:
        """Run all available providers and return deduplicated candidates."""
        tasks = self._generate_tasks(context, image)
        if not tasks:
            return []

        by_name = {p.name: p for p in (*self._image_providers, *self._web_providers)}
        coros = []
        for task in tasks:
            provider = by_name.get(task.provider_name)
            if provider is None:
                continue
            if task.kind == "image":
                coros.append(provider.search(task.image, task.context))
            else:
                coros.append(provider.search(task.query, task.context))

        results = await asyncio.gather(*coros, return_exceptions=True)
        flat: list[Candidate] = []
        for result in results:
            if isinstance(result, BaseException):
                continue  # a failing provider must not block other providers
            if result:
                flat.extend(result)

        normalized = [self._normalize(candidate) for candidate in flat]
        deduped = self._dedupe(normalized)
        limit = max_candidates if max_candidates is not None else self._max_candidates
        return deduped[:limit]

    @staticmethod
    def _normalize(candidate: Candidate) -> Candidate:
        candidate.domain = candidate.domain or derive_domain(candidate.url)
        candidate.kind = candidate.kind or "web"
        candidate.reason = candidate.reason or f"discovered by {candidate.source or 'provider'}"
        return candidate

    @staticmethod
    def _dedupe(candidates: list[Candidate]) -> list[Candidate]:
        seen: set[str] = set()
        out: list[Candidate] = []
        for candidate in candidates:
            key = canonical_url(candidate.url)
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(candidate)
        return out