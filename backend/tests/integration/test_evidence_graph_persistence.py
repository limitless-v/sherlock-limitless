"""Integration tests for evidence graph persistence (roadmap Phase 24)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.evidence.graph import EvidenceGraph
from app.models.entities import EvidenceNode, EvidenceEdge, SearchHistory
from app.repositories.evidence_graph import EvidenceGraphRepository
from app.services.evidence_graph_service import EvidenceGraphService


@pytest.mark.asyncio
async def test_evidence_graph_repository_persist(db_session: AsyncSession) -> None:
    """Test persisting an evidence graph to database."""
    repo = EvidenceGraphRepository(db_session)

    # Create a search history entry first
    search = SearchHistory(
        user_id=1,
        uploaded_image="uploads/test.jpg",
    )
    db_session.add(search)
    await db_session.flush()
    await db_session.refresh(search)

    # Create graph with nodes and edges
    graph = EvidenceGraph(search_id=search.id)

    url_id = graph.add_node(
        node_type="url",
        entity_id="https://example.com/page",
        entity_value="https://example.com/page",
        attributes={"title": "Test Page"},
        source_url="https://example.com/page",
        source_evidence_id=1,
    )

    domain_id = graph.add_node(
        node_type="domain",
        entity_id="example.com",
        entity_value="example.com",
        source_url="https://example.com/page",
    )

    image_id = graph.add_node(
        node_type="image",
        entity_id="https://example.com/img.jpg",
        entity_value="https://example.com/img.jpg",
        source_url="https://example.com/page",
    )

    graph.add_edge(
        source_node_id=url_id,
        target_node_id=domain_id,
        edge_type="links_to",
        source_url="https://example.com/page",
        source_evidence_id=1,
        confidence=0.9,
    )

    graph.add_edge(
        source_node_id=image_id,
        target_node_id=url_id,
        edge_type="image_found_on",
        source_url="https://example.com/page",
        source_evidence_id=1,
        confidence=0.8,
    )

    # Persist graph
    await repo.persist_graph(graph)

    # Verify nodes persisted
    nodes = await repo.get_nodes_by_search(search.id)
    assert len(nodes) == 3

    node_types = {n.node_type for n in nodes}
    assert node_types == {"url", "domain", "image"}

    url_node = next(n for n in nodes if n.node_type == "url")
    assert url_node.entity_id == "https://example.com/page"
    assert url_node.attributes == {"title": "Test Page"}

    # Verify edges persisted
    edges = await repo.get_edges_by_search(search.id)
    assert len(edges) == 2

    edge_types = {e.edge_type for e in edges}
    assert edge_types == {"links_to", "image_found_on"}

    links_to_edge = next(e for e in edges if e.edge_type == "links_to")
    assert links_to_edge.confidence == 0.9


@pytest.mark.asyncio
async def test_evidence_graph_repository_load(db_session: AsyncSession) -> None:
    """Test loading an evidence graph from database."""
    repo = EvidenceGraphRepository(db_session)

    search = SearchHistory(user_id=1, uploaded_image="uploads/test2.jpg")
    db_session.add(search)
    await db_session.flush()
    await db_session.refresh(search)

    # Create and persist graph
    graph = EvidenceGraph(search_id=search.id)

    url_id = graph.add_node("url", "https://example.com", "https://example.com")
    domain_id = graph.add_node("domain", "example.com", "example.com")
    graph.add_edge(url_id, domain_id, "links_to", "https://example.com")

    await repo.persist_graph(graph)

    # Load graph
    node_dicts, edge_dicts = await repo.get_graph_for_search(search.id)
    loaded_graph = EvidenceGraph.from_database(search.id, node_dicts, edge_dicts)

    assert loaded_graph.node_count == 2
    assert loaded_graph.edge_count == 1
    assert loaded_graph.search_id == search.id

    # Verify node data
    loaded_url = loaded_graph.get_node_by_entity("url", "https://example.com")
    loaded_domain = loaded_graph.get_node_by_entity("domain", "example.com")
    assert loaded_url is not None
    assert loaded_domain is not None


@pytest.mark.asyncio
async def test_evidence_graph_service(db_session: AsyncSession) -> None:
    """Test EvidenceGraphService."""
    service = EvidenceGraphService(db_session)

    search = SearchHistory(user_id=1, uploaded_image="uploads/test3.jpg")
    db_session.add(search)
    await db_session.flush()
    await db_session.refresh(search)

    # Create graph via service
    graph = service.create_graph(search.id)
    graph.add_node("url", "https://example.com", "https://example.com")
    graph.add_node("domain", "example.com", "example.com")
    graph.add_edge(1, 2, "links_to", "https://example.com")

    # Persist via service
    await service.persist_graph(graph)

    # Load via service
    loaded_data = await service.get_graph_data(search.id)

    assert len(loaded_data["nodes"]) == 2
    assert len(loaded_data["edges"]) == 1
    assert len(loaded_data["nodes"]) == 2
    assert len(loaded_data["edges"]) == 1


@pytest.mark.asyncio
async def test_evidence_graph_counts(db_session: AsyncSession) -> None:
    """Test node and edge count methods."""
    repo = EvidenceGraphRepository(db_session)

    search = SearchHistory(user_id=1, uploaded_image="uploads/test4.jpg")
    db_session.add(search)
    await db_session.flush()
    await db_session.refresh(search)

    graph = EvidenceGraph(search_id=search.id)
    graph.add_node("url", "https://example.com/1", "https://example.com/1")
    graph.add_node("url", "https://example.com/2", "https://example.com/2")
    graph.add_node("domain", "example.com", "example.com")
    graph.add_edge(1, 3, "links_to", "https://example.com/1")
    graph.add_edge(2, 3, "links_to", "https://example.com/2")

    await repo.persist_graph(graph)

    node_count = await repo.get_node_count_by_search(search.id)
    edge_count = await repo.get_edge_count_by_search(search.id)

    assert node_count == 3
    assert edge_count == 2


@pytest.mark.asyncio
async def test_evidence_graph_delete(db_session: AsyncSession) -> None:
    """Test deleting graph data for a search."""
    repo = EvidenceGraphRepository(db_session)

    search = SearchHistory(user_id=1, uploaded_image="uploads/test5.jpg")
    db_session.add(search)
    await db_session.flush()
    await db_session.refresh(search)

    graph = EvidenceGraph(search_id=search.id)
    graph.add_node("url", "https://example.com", "https://example.com")
    graph.add_node("domain", "example.com", "example.com")
    graph.add_edge(1, 2, "links_to", "https://example.com")

    await repo.persist_graph(graph)

    # Verify exists
    nodes_before = await repo.get_nodes_by_search(search.id)
    edges_before = await repo.get_edges_by_search(search.id)
    assert len(nodes_before) == 2
    assert len(edges_before) == 1

    # Delete
    node_count, edge_count = await repo.delete_graph_by_search(search.id)
    assert node_count == 2
    assert edge_count == 1

    # Verify deleted
    nodes_after = await repo.get_nodes_by_search(search.id)
    edges_after = await repo.get_edges_by_search(search.id)
    assert len(nodes_after) == 0
    assert len(edges_after) == 0


@pytest.mark.asyncio
async def test_evidence_graph_get_by_entity(db_session: AsyncSession) -> None:
    """Test getting node by type and entity ID."""
    repo = EvidenceGraphRepository(db_session)

    search = SearchHistory(user_id=1, uploaded_image="uploads/test6.jpg")
    db_session.add(search)
    await db_session.flush()
    await db_session.refresh(search)

    graph = EvidenceGraph(search_id=search.id)
    graph.add_node("url", "https://example.com/page", "https://example.com/page")
    graph.add_node("domain", "example.com", "example.com")

    await repo.persist_graph(graph)

    url_node = await repo.get_node_by_entity(search.id, "url", "https://example.com/page")
    domain_node = await repo.get_node_by_entity(search.id, "domain", "example.com")
    none_node = await repo.get_node_by_entity(search.id, "url", "https://nonexistent.com")

    assert url_node is not None
    assert url_node.entity_id == "https://example.com/page"
    assert domain_node is not None
    assert domain_node.entity_id == "example.com"
    assert none_node is None


@pytest.mark.asyncio
async def test_evidence_graph_edges_by_node(db_session: AsyncSession) -> None:
    """Test getting edges connected to a node."""
    repo = EvidenceGraphRepository(db_session)

    search = SearchHistory(user_id=1, uploaded_image="uploads/test7.jpg")
    db_session.add(search)
    await db_session.flush()
    await db_session.refresh(search)

    graph = EvidenceGraph(search_id=search.id)
    url_id = graph.add_node("url", "https://example.com", "https://example.com")
    domain_id = graph.add_node("domain", "example.com", "example.com")
    image_id = graph.add_node("image", "https://example.com/img.jpg", "https://example.com/img.jpg")

    graph.add_edge(url_id, domain_id, "links_to", "https://example.com")
    graph.add_edge(image_id, url_id, "image_found_on", "https://example.com")

    await repo.persist_graph(graph)

    # Get outgoing edges from URL
    out_edges = await repo.get_edges_by_node(url_id, "out")
    assert len(out_edges) == 1
    assert out_edges[0].edge_type == "links_to"
    assert out_edges[0].target_node_id == domain_id

    # Get incoming edges to URL
    in_edges = await repo.get_edges_by_node(url_id, "in")
    assert len(in_edges) == 1
    assert in_edges[0].edge_type == "image_found_on"
    assert in_edges[0].source_node_id == image_id

    # Get both directions
    both_edges = await repo.get_edges_by_node(url_id, "both")
    assert len(both_edges) == 2