"""Search service (thin adapter).

Delegates search routing/execution to the SearchOrchestrator and keeps
persistence/history plumbing separate. No `if mode == ...` logic lives
here — that belongs in backend/app/search/ (roadmap section 5, 7).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, delete, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entities import (
    Search, SearchEvent, SearchHistory, User,
    Candidate, CandidateExtractedImage, CandidateProfile,
    CandidateLocation, CandidateDate,
    EvidenceNode, EvidenceEdge,
    DetectedFace, MatchedProfile
)
from app.search.orchestrator import SearchOrchestrator
from app.search.request_models import SearchRequest
from app.search.result_models import SearchResponse
from app.schemas.search import SearchCreateResponse, SearchDetailRead, SearchHistoryItem, SearchResultRead


class SearchService:
    """Coordinates search execution and persistence."""

    def __init__(
        self,
        orchestrator: SearchOrchestrator,
        session: AsyncSession,
    ) -> None:
        self._orchestrator = orchestrator
        self._session = session

    async def execute_search(self, request: SearchRequest) -> SearchResponse:
        """Delegate to the orchestrator, which routes by search mode."""
        # Create search record first
        search = Search(
            user_id=request.user_id,
            image_id=str(request.image_id),
            mode=request.mode.value if hasattr(request.mode, 'value') else str(request.mode),
            status="running",
            uploaded_image=request.uploaded_image or "",
            started_at=datetime.now(timezone.utc),
        )
        self._session.add(search)
        await self._session.flush()
        await self._session.refresh(search)

        try:
            response = await self._orchestrator.execute(request)
            
            # Update search record with results
            search.status = "completed" if response.status != "degraded" else "degraded"
            search.providers = response.providers
            search.ranked_evidence = getattr(response, 'ranked_evidence', None)
            search.sources_checked = len(response.providers) if response.providers else 0
            search.pages_analyzed = getattr(response, 'pages_analyzed', 0)
            search.total_candidates = len(response.results)
            search.total_evidence = len(getattr(response, 'ranked_evidence', []))
            search.completed_at = datetime.now(timezone.utc)
            
            await self._session.flush()
            
            # Add completed event
            await self._add_event(search.id, "search_completed", {
                "status": search.status,
                "total_candidates": search.total_candidates,
                "total_evidence": search.total_evidence,
            })
            
        except Exception as e:
            search.status = "failed"
            search.error_message = str(e)
            search.completed_at = datetime.now(timezone.utc)
            await self._session.flush()
            await self._add_event(search.id, "search_failed", {"error": str(e)})
            raise

        return response

    async def _add_event(self, search_id: int, event_type: str, payload: dict[str, Any]) -> None:
        """Add an event to the search event stream."""
        # Get next sequence number
        stmt = select(func.max(SearchEvent.sequence)).where(SearchEvent.search_id == search_id)
        result = await self._session.execute(stmt)
        max_seq = result.scalar() or 0
        
        event = SearchEvent(
            search_id=search_id,
            sequence=max_seq + 1,
            event_type=event_type,
            payload=payload,
        )
        self._session.add(event)

    async def get_search(self, search_id: int) -> SearchDetailRead | None:
        """Retrieve search status and ranked results with full detail."""
        stmt = (
            select(Search)
            .where(Search.id == search_id)
            .options(
                selectinload(Search.events),
            )
        )
        result = await self._session.execute(stmt)
        search = result.scalar_one_or_none()
        
        if not search:
            return None

        # Load detected faces from SearchHistory (legacy) or new Search
        # For now, load from the newer Search table's perspective
        # We need to get the SearchHistory record if it exists
        history_stmt = select(SearchHistory).where(SearchHistory.id == search_id)
        history_result = await self._session.execute(history_stmt)
        history = history_result.scalar_one_or_none()
        
        detected_faces = []
        if history:
            # Load faces with matched profiles
            faces_stmt = (
                select(DetectedFace)
                .where(DetectedFace.search_id == history.id)
                .options(selectinload(DetectedFace.matched_profiles))
            )
            faces_result = await self._session.execute(faces_stmt)
            faces = faces_result.scalars().all()
            
            for face in faces:
                matched_profiles = [
                    MatchedProfileRead(
                        id=mp.id,
                        platform=mp.platform,
                        profile_url=mp.profile_url,
                        image_url=mp.image_url,
                        confidence=mp.confidence,
                    )
                    for mp in face.matched_profiles
                ]
                detected_faces.append(DetectedFaceRead(
                    id=face.id,
                    face_image=face.face_image,
                    embedding_path=face.embedding_path,
                    matched_profiles=matched_profiles,
                ))

        # Build ranked evidence from stored JSON or from evidence graph
        ranked_evidence = search.ranked_evidence
        if not ranked_evidence and history:
            # Build from evidence graph
            nodes_stmt = select(EvidenceNode).where(EvidenceNode.search_id == history.id)
            nodes_result = await self._session.execute(nodes_stmt)
            nodes = nodes_result.scalars().all()
            
            edges_stmt = select(EvidenceEdge).where(EvidenceEdge.search_id == history.id)
            edges_result = await self._session.execute(edges_stmt)
            edges = edges_result.scalars().all()
            
            ranked_evidence = {
                "nodes": [
                    {
                        "id": n.id,
                        "type": n.node_type,
                        "entity_id": n.entity_id,
                        "entity_value": n.entity_value,
                        "attributes": n.attributes,
                        "source_url": n.source_url,
                    }
                    for n in nodes
                ],
                "edges": [
                    {
                        "id": e.id,
                        "source": e.source_node_id,
                        "target": e.target_node_id,
                        "type": e.edge_type,
                        "source_url": e.source_url,
                        "confidence": e.confidence,
                        "metadata": e.edge_metadata,
                    }
                    for e in edges
                ],
            }

        return SearchDetailRead(
            id=search.id,
            uploaded_image=search.uploaded_image,
            created_at=search.started_at,
            detected_faces=detected_faces,
            matched_profiles=[],  # Legacy field, kept for compatibility
            mode=search.mode,
            status=search.status,
            providers=search.providers or {},
            ranked_evidence=ranked_evidence,
        )

    async def get_search_results(
        self,
        search_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Get paginated search results from candidates table."""
        # First verify search exists
        search_stmt = select(Search).where(Search.id == search_id)
        search_result = await self._session.execute(search_stmt)
        search = search_result.scalar_one_or_none()
        if not search:
            return {
                "search_id": search_id,
                "page": page,
                "page_size": page_size,
                "total": 0,
                "results": [],
            }

        # Load candidates from SearchHistory (legacy) which has the candidates relationship
        history_stmt = select(SearchHistory).where(SearchHistory.id == search_id)
        history_result = await self._session.execute(history_stmt)
        history = history_result.scalar_one_or_none()
        
        if not history:
            return {
                "search_id": search_id,
                "page": page,
                "page_size": page_size,
                "total": 0,
                "results": [],
            }

        # Count total candidates
        count_stmt = select(func.count(Candidate.id)).where(Candidate.search_id == history.id)
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        # Load paginated candidates with relationships
        candidates_stmt = (
            select(Candidate)
            .where(Candidate.search_id == history.id)
            .options(
                selectinload(Candidate.images),
                selectinload(Candidate.profiles),
                selectinload(Candidate.locations),
                selectinload(Candidate.dates),
            )
            .order_by(Candidate.discovered_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        candidates_result = await self._session.execute(candidates_stmt)
        candidates = candidates_result.scalars().all()

        results = []
        for c in candidates:
            # Get primary image
            primary_image = c.images[0] if c.images else None
            image_urls = [img.image_url for img in c.images]
            
            # Get profiles
            profiles = [
                {
                    "profile_url": p.profile_url,
                    "platform": p.platform,
                    "username": p.username,
                    "display_name": p.display_name,
                }
                for p in c.profiles
            ]
            
            # Get first profile for backward compat
            first_profile = c.profiles[0] if c.profiles else None
            
            # Determine confidence based on correlation
            confidence = "low"
            face_similarity = 0.0
            if primary_image and primary_image.correlation_classification:
                if primary_image.correlation_classification == "exact_duplicate":
                    confidence = "high"
                elif primary_image.correlation_classification == "near_duplicate":
                    confidence = "medium"
                elif primary_image.correlation_classification == "similar":
                    confidence = "low"
                if primary_image.face_similarity:
                    face_similarity = primary_image.face_similarity
            
            # Get location
            location = c.locations[0].location if c.locations else None
            
            # Get date
            date = c.dates[0].date_value.isoformat() if c.dates else None

            results.append(SearchResultRead(
                id=str(c.id),
                source=c.source,
                url=c.url,
                title=c.title or "",
                username=first_profile.username if first_profile else "",
                display_name=first_profile.display_name if first_profile else "",
                image_urls=image_urls,
                text=c.candidate_metadata.get("text", "") if c.candidate_metadata else "",
                discovery_method=c.kind,
                face_similarity=face_similarity,
                confidence=confidence,
                discovered_at=c.discovered_at,
                location=location,
                date=date,
                profiles=profiles,
            ))

        return {
            "search_id": search_id,
            "page": page,
            "page_size": page_size,
            "total": total,
            "results": [r.model_dump() for r in results],
        }

    async def get_search_evidence(self, search_id: int) -> dict[str, Any]:
        """Get full evidence graph for a search."""
        # Verify search exists
        search_stmt = select(Search).where(Search.id == search_id)
        search_result = await self._session.execute(search_stmt)
        search = search_result.scalar_one_or_none()
        if not search:
            return {
                "search_id": search_id,
                "nodes": [],
                "edges": [],
            }

        # Load from SearchHistory which has the evidence graph relationships
        history_stmt = select(SearchHistory).where(SearchHistory.id == search_id)
        history_result = await self._session.execute(history_stmt)
        history = history_result.scalar_one_or_none()
        
        if not history:
            return {
                "search_id": search_id,
                "nodes": [],
                "edges": [],
            }

        # Load nodes
        nodes_stmt = select(EvidenceNode).where(EvidenceNode.search_id == history.id)
        nodes_result = await self._session.execute(nodes_stmt)
        nodes = nodes_result.scalars().all()
        
        # Load edges
        edges_stmt = select(EvidenceEdge).where(EvidenceEdge.search_id == history.id)
        edges_result = await self._session.execute(edges_stmt)
        edges = edges_result.scalars().all()
        
        return {
            "search_id": search_id,
            "nodes": [
                {
                    "id": n.id,
                    "type": n.node_type,
                    "entity_id": n.entity_id,
                    "entity_value": n.entity_value,
                    "attributes": n.attributes,
                    "source_url": n.source_url,
                    "source_evidence_id": n.source_evidence_id,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "source": e.source_node_id,
                    "target": e.target_node_id,
                    "type": e.edge_type,
                    "source_url": e.source_url,
                    "source_evidence_id": e.source_evidence_id,
                    "confidence": e.confidence,
                    "metadata": e.edge_metadata,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in edges
            ],
        }

    async def list_history(
        self,
        user_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        mode: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[SearchHistoryItem], int]:
        """Get paginated search history with filters."""
        stmt = select(Search).where(Search.user_id == user_id if user_id else True)
        
        if status:
            stmt = stmt.where(Search.status == status)
        if mode:
            stmt = stmt.where(Search.mode == mode)
        if created_from:
            stmt = stmt.where(Search.started_at >= created_from)
        if created_to:
            stmt = stmt.where(Search.started_at <= created_to)
        
        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()
        
        # Apply pagination and ordering
        stmt = stmt.order_by(Search.started_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        result = await self._session.execute(stmt)
        searches = result.scalars().all()
        
        items = [
            SearchHistoryItem(
                id=s.id,
                uploaded_image=s.uploaded_image,
                created_at=s.started_at,
            )
            for s in searches
        ]
        
        return items, total

    async def delete_history(self, search_id: int, user_id: int | None = None) -> bool:
        """Delete a search history entry (and cascade to events)."""
        stmt = select(Search).where(Search.id == search_id)
        if user_id is not None:
            stmt = stmt.where(Search.user_id == user_id)
        
        result = await self._session.execute(stmt)
        search = result.scalar_one_or_none()
        
        if not search:
            return False
        
        # Delete events first (FK constraint)
        await self._session.execute(
            delete(SearchEvent).where(SearchEvent.search_id == search_id)
        )
        
        # Delete search
        await self._session.delete(search)
        await self._session.flush()
        
        return True