"""Unit tests for evidence graph (roadmap Phase 24)."""

from app.evidence.graph import EvidenceGraph
from app.evidence.schemas import EvidenceNodeData, EvidenceEdgeData


def test_evidence_graph_basic() -> None:
    """Test basic graph creation and node/edge addition."""
    graph = EvidenceGraph(search_id=1)

    # Add nodes
    url_id = graph.add_node(
        node_type="url",
        entity_id="https://example.com/page",
        entity_value="https://example.com/page",
        source_url="https://example.com/page",
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

    assert graph.node_count == 3
    assert url_id == 1
    assert domain_id == 2
    assert image_id == 3

    # Add edges
    edge1 = graph.add_edge(
        source_node_id=url_id,
        target_node_id=domain_id,
        edge_type="links_to",
        source_url="https://example.com/page",
    )
    edge2 = graph.add_edge(
        source_node_id=image_id,
        target_node_id=url_id,
        edge_type="image_found_on",
        source_url="https://example.com/page",
    )

    assert graph.edge_count == 2
    assert edge1 == 1
    assert edge2 == 2


def test_evidence_graph_node_deduplication() -> None:
    """Test that nodes with same type and entity_id are deduplicated."""
    graph = EvidenceGraph(search_id=1)

    id1 = graph.add_node("url", "https://example.com", "https://example.com")
    id2 = graph.add_node("url", "https://example.com", "https://example.com")

    assert id1 == id2
    assert graph.node_count == 1


def test_evidence_graph_edge_deduplication() -> None:
    """Test that edges with same source, target, type are deduplicated."""
    graph = EvidenceGraph(search_id=1)

    url_id = graph.add_node("url", "https://example.com", "https://example.com")
    domain_id = graph.add_node("domain", "example.com", "example.com")

    edge1 = graph.add_edge(url_id, domain_id, "links_to", "https://example.com")
    edge2 = graph.add_edge(url_id, domain_id, "links_to", "https://example.com")

    assert edge1 == edge2
    assert graph.edge_count == 1


def test_evidence_graph_invalid_node_type() -> None:
    """Test that invalid node type raises ValueError."""
    graph = EvidenceGraph(search_id=1)

    try:
        graph.add_node("invalid_type", "entity1", "Entity 1")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid node_type" in str(e)


def test_evidence_graph_invalid_edge_type() -> None:
    """Test that invalid edge type raises ValueError."""
    graph = EvidenceGraph(search_id=1)

    id1 = graph.add_node("url", "https://example.com", "https://example.com")
    id2 = graph.add_node("domain", "example.com", "example.com")

    try:
        graph.add_edge(id1, id2, "invalid_type", "https://example.com")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid edge_type" in str(e)


def test_evidence_graph_get_node() -> None:
    """Test getting node data by ID."""
    graph = EvidenceGraph(search_id=1)

    node_id = graph.add_node("url", "https://example.com", "https://example.com")
    node = graph.get_node(node_id)

    assert node is not None
    assert node.node_type == "url"
    assert node.entity_id == "https://example.com"
    assert node.entity_value == "https://example.com"

    # Non-existent node
    assert graph.get_node(999) is None


def test_evidence_graph_get_node_by_entity() -> None:
    """Test getting node ID by type and entity ID."""
    graph = EvidenceGraph(search_id=1)

    node_id = graph.add_node("url", "https://example.com", "https://example.com")
    found_id = graph.get_node_by_entity("url", "https://example.com")

    assert found_id == node_id

    # Non-existent
    assert graph.get_node_by_entity("url", "https://nonexistent.com") is None


def test_evidence_graph_get_nodes_by_type() -> None:
    """Test getting all nodes of a specific type."""
    graph = EvidenceGraph(search_id=1)

    graph.add_node("url", "https://example.com/1", "https://example.com/1")
    graph.add_node("url", "https://example.com/2", "https://example.com/2")
    graph.add_node("domain", "example.com", "example.com")
    graph.add_node("image", "https://example.com/img.jpg", "https://example.com/img.jpg")

    urls = graph.get_nodes_by_type("url")
    domains = graph.get_nodes_by_type("domain")
    images = graph.get_nodes_by_type("image")

    assert len(urls) == 2
    assert len(domains) == 1
    assert len(images) == 1


def test_evidence_graph_adjacency() -> None:
    """Test adjacency list operations."""
    graph = EvidenceGraph(search_id=1)

    url_id = graph.add_node("url", "https://example.com", "https://example.com")
    domain_id = graph.add_node("domain", "example.com", "example.com")
    image_id = graph.add_node("image", "https://example.com/img.jpg", "https://example.com/img.jpg")

    graph.add_edge(url_id, domain_id, "links_to", "https://example.com")
    graph.add_edge(image_id, url_id, "image_found_on", "https://example.com")

    # Outgoing edges
    out_url = graph.get_neighbors(url_id, "out")
    out_domain = graph.get_neighbors(domain_id, "out")
    out_image = graph.get_neighbors(image_id, "out")

    assert out_url == [domain_id]
    assert out_domain == []
    assert out_image == [url_id]

    # Incoming edges
    in_url = graph.get_neighbors(url_id, "in")
    in_domain = graph.get_neighbors(domain_id, "in")
    in_image = graph.get_neighbors(image_id, "in")

    assert in_url == [image_id]
    assert in_domain == [url_id]
    assert in_image == []


def test_evidence_graph_get_edges() -> None:
    """Test getting edges by type."""
    graph = EvidenceGraph(search_id=1)

    url_id = graph.add_node("url", "https://example.com", "https://example.com")
    domain_id = graph.add_node("domain", "example.com", "example.com")
    image_id = graph.add_node("image", "https://example.com/img.jpg", "https://example.com/img.jpg")

    graph.add_edge(url_id, domain_id, "links_to", "https://example.com")
    graph.add_edge(image_id, url_id, "image_found_on", "https://example.com")
    graph.add_edge(url_id, image_id, "links_to", "https://example.com")

    links_to = graph.get_edges_by_type("links_to")
    image_found_on = graph.get_edges_by_type("image_found_on")

    assert len(links_to) == 2
    assert len(image_found_on) == 1
    assert image_found_on[0].edge_type == "image_found_on"


def test_evidence_graph_serialization() -> None:
    """Test graph serialization for API response."""
    graph = EvidenceGraph(search_id=1)

    url_id = graph.add_node("url", "https://example.com", "https://example.com")
    domain_id = graph.add_node("domain", "example.com", "example.com")

    graph.add_edge(url_id, domain_id, "links_to", "https://example.com")

    data = graph.to_dict()

    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1

    # Check node structure
    node = data["nodes"][0]
    assert "id" in node
    assert "node_type" in node
    assert "entity_id" in node
    assert "entity_value" in node

    # Check edge structure
    edge = data["edges"][0]
    assert "id" in edge
    assert "source_node_id" in edge
    assert "target_node_id" in edge
    assert "edge_type" in edge
    assert "source_url" in edge


def test_evidence_graph_subgraph() -> None:
    """Test subgraph extraction."""
    graph = EvidenceGraph(search_id=1)

    url_id = graph.add_node("url", "https://example.com", "https://example.com")
    domain_id = graph.add_node("domain", "example.com", "example.com")
    image_id = graph.add_node("image", "https://example.com/img.jpg", "https://example.com/img.jpg")
    profile_id = graph.add_node("profile", "https://github.com/user", "https://github.com/user")

    graph.add_edge(url_id, domain_id, "links_to", "https://example.com")
    graph.add_edge(image_id, url_id, "image_found_on", "https://example.com")
    graph.add_edge(profile_id, url_id, "image_found_on", "https://example.com")

    # Get subgraph centered on URL with depth 1
    subgraph = graph.get_subgraph(url_id, depth=1)

    assert subgraph.node_count == 4  # url, domain, image, profile (all at depth 1)
    assert subgraph.edge_count >= 2


def test_evidence_graph_persistence_format() -> None:
    """Test getting nodes/edges formatted for database persistence."""
    graph = EvidenceGraph(search_id=1)

    url_id = graph.add_node(
        node_type="url",
        entity_id="https://example.com",
        entity_value="https://example.com",
        attributes={"title": "Example"},
        source_url="https://example.com",
        source_evidence_id=1,
    )

    domain_id = graph.add_node(
        node_type="domain",
        entity_id="example.com",
        entity_value="example.com",
        source_url="https://example.com",
    )

    graph.add_edge(
        source_node_id=url_id,
        target_node_id=domain_id,
        edge_type="links_to",
        source_url="https://example.com",
        source_evidence_id=1,
        confidence=0.9,
        metadata={"source": "research"},
    )

    nodes = graph.get_nodes_for_persistence()
    edges = graph.get_edges_for_persistence()

    assert len(nodes) == 2
    assert nodes[0]["node_type"] == "url"
    assert nodes[0]["attributes"] == {"title": "Example"}
    assert nodes[0]["source_evidence_id"] == 1

    assert len(edges) == 1
    assert edges[0]["edge_type"] == "links_to"
    assert edges[0]["confidence"] == 0.9
    assert edges[0]["metadata"] == {"source": "research"}


def test_evidence_graph_from_database() -> None:
    """Test reconstructing graph from database records."""
    # Create original graph
    original = EvidenceGraph(search_id=1)

    url_id = original.add_node("url", "https://example.com", "https://example.com")
    domain_id = original.add_node("domain", "example.com", "example.com")
    original.add_edge(url_id, domain_id, "links_to", "https://example.com")

    # Get persistence format
    nodes = original.get_nodes_for_persistence()
    edges = original.get_edges_for_persistence()

    # Reconstruct
    reconstructed = EvidenceGraph.from_database(1, nodes, edges)

    assert reconstructed.node_count == 2
    assert reconstructed.edge_count == 1
    assert reconstructed.search_id == 1

    # Check nodes preserved
    reconstructed_url = reconstructed.get_node_by_entity("url", "https://example.com")
    reconstructed_domain = reconstructed.get_node_by_entity("domain", "example.com")
    assert reconstructed_url is not None
    assert reconstructed_domain is not None

    # Check edge preserved
    assert reconstructed.edge_count == 1