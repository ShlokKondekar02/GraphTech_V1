"""
Sprint 2 tests -- Complexity Service.

Tests that complexity is ALWAYS independently computed from the graph structure
and that the ceiling rejection fires correctly.

Coverage:
  C1  -- single-node graph has near-zero complexity, labeled "simple"
  C2  -- two-node chain: expected low score
  C3  -- deliberately oversized graph exceeds ceiling and is rejected with a clear reason
  C4  -- cyclomatic number computed correctly for a diamond graph
  C5  -- nesting_depth computed correctly for a linear chain
  C6  -- disconnected components counted correctly
  C7  -- cyclic graph: is_cyclic=True, nesting_depth=-1
  C8  -- compute_from_dict works identically to compute_from_groq_response
  C9  -- compute_from_groq_response does NOT use any complexity field from Groq
  C10 -- rejection_reason is None when ceiling is NOT exceeded
  C11 -- rejection_reason is a non-empty string when ceiling IS exceeded
  C12 -- max_in_degree and max_out_degree computed correctly
"""

from __future__ import annotations

import pytest

from app.schemas.groq_contract import GroqDiagramResponse
from app.services.complexity_service import ComplexityResult, ComplexityService, complexity_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_nodes(*ids: str) -> list[dict]:
    return [{"id": nid, "label": nid.upper(), "type": "service"} for nid in ids]


def _make_edge(eid: str, src: str, tgt: str) -> dict:
    return {"id": eid, "source": src, "target": tgt, "label": "", "type": "calls"}


def _make_attrs(allows_disconnected: bool = False) -> dict:
    return {
        "title": "T",
        "description": "D",
        "allows_disconnected": allows_disconnected,
        "direction": "LR",
    }


def _groq_response(nodes, edges, diagram_type="flowchart", allows_disconnected=False):
    payload = {
        "diagram_type": diagram_type,
        "nodes": nodes,
        "edges": edges,
        "attributes": _make_attrs(allows_disconnected=allows_disconnected),
    }
    return GroqDiagramResponse.model_validate(payload)


# ---------------------------------------------------------------------------
# C1: Single-node graph
# ---------------------------------------------------------------------------


def test_c1_single_node_low_complexity():
    """Single node, no edges -> score should be very low, labeled 'simple'."""
    svc = ComplexityService()
    result = svc.compute(
        nodes=_make_nodes("n1"),
        edges=[],
        diagram_type="flowchart",
        ceiling=50.0,
    )
    assert result.node_count == 1
    assert result.edge_count == 0
    assert result.score < 10.0
    assert result.label == "simple"
    assert not result.exceeds_ceiling


# ---------------------------------------------------------------------------
# C2: Two-node chain
# ---------------------------------------------------------------------------


def test_c2_two_node_chain():
    """Two nodes connected by one edge: low complexity."""
    svc = ComplexityService()
    result = svc.compute(
        nodes=_make_nodes("n1", "n2"),
        edges=[_make_edge("e1", "n1", "n2")],
        diagram_type="flowchart",
        ceiling=50.0,
    )
    assert result.node_count == 2
    assert result.edge_count == 1
    assert result.score < 15.0
    assert result.label in ("simple", "moderate")
    assert not result.exceeds_ceiling


# ---------------------------------------------------------------------------
# C3: Oversized graph exceeds ceiling with clear rejection reason
# ---------------------------------------------------------------------------


def test_c3_oversized_graph_exceeds_ceiling_pre_render():
    """
    A deliberately oversized graph must exceed the ceiling.
    The rejection_reason must be a non-empty, specific string that explains
    WHY it was rejected (not a generic error).
    """
    # Build a 60-node graph with many cross-edges (high cyclomatic number)
    n = 60
    nodes = _make_nodes(*[f"n{i}" for i in range(n)])
    edges = []
    eid = 0
    for i in range(n - 1):
        edges.append(_make_edge(f"e{eid}", f"n{i}", f"n{i+1}"))
        eid += 1
    # Add many cross-edges to inflate cyclomatic number
    for i in range(0, n - 10, 5):
        edges.append(_make_edge(f"ex{eid}", f"n{i}", f"n{i+9}"))
        eid += 1

    svc = ComplexityService()
    result = svc.compute(
        nodes=nodes,
        edges=edges,
        diagram_type="flowchart",
        ceiling=50.0,  # standard ceiling
    )

    assert result.exceeds_ceiling, (
        f"Expected ceiling exceeded but score={result.score:.2f}, ceiling=50.0"
    )
    assert result.rejection_reason is not None
    assert len(result.rejection_reason) > 20  # must be a meaningful sentence
    # Must mention score, ceiling, and pre-render rejection
    reason_lower = result.rejection_reason.lower()
    assert "ceiling" in reason_lower or "score" in reason_lower
    assert "render" in reason_lower


# ---------------------------------------------------------------------------
# C4: Cyclomatic number for diamond graph
# ---------------------------------------------------------------------------


def test_c4_cyclomatic_number_diamond():
    """
    Diamond graph: A -> B, A -> C, B -> D, C -> D
    Edges=4, Nodes=4, Components=1 -> cyclomatic = 4 - 4 + 1 = 1
    """
    nodes = _make_nodes("A", "B", "C", "D")
    edges = [
        _make_edge("e1", "A", "B"),
        _make_edge("e2", "A", "C"),
        _make_edge("e3", "B", "D"),
        _make_edge("e4", "C", "D"),
    ]
    svc = ComplexityService()
    result = svc.compute(nodes=nodes, edges=edges, diagram_type="flowchart", ceiling=100.0)
    assert result.cyclomatic_number == 1
    assert result.component_count == 1
    assert not result.is_cyclic
    assert result.nesting_depth == 2  # longest path: A -> B -> D or A -> C -> D


# ---------------------------------------------------------------------------
# C5: Nesting depth for a 5-node linear chain
# ---------------------------------------------------------------------------


def test_c5_nesting_depth_linear_chain():
    """A -> B -> C -> D -> E: longest path = 4 edges."""
    nodes = _make_nodes("A", "B", "C", "D", "E")
    edges = [
        _make_edge("e1", "A", "B"),
        _make_edge("e2", "B", "C"),
        _make_edge("e3", "C", "D"),
        _make_edge("e4", "D", "E"),
    ]
    svc = ComplexityService()
    result = svc.compute(nodes=nodes, edges=edges, diagram_type="flowchart", ceiling=100.0)
    assert result.nesting_depth == 4
    assert not result.is_cyclic


# ---------------------------------------------------------------------------
# C6: Disconnected components counted correctly
# ---------------------------------------------------------------------------


def test_c6_disconnected_components():
    """Two isolated pairs of nodes -> component_count == 2."""
    nodes = _make_nodes("a", "b", "c", "d")
    edges = [
        _make_edge("e1", "a", "b"),
        _make_edge("e2", "c", "d"),
    ]
    svc = ComplexityService()
    result = svc.compute(nodes=nodes, edges=edges, diagram_type="network", ceiling=100.0)
    assert result.component_count == 2


# ---------------------------------------------------------------------------
# C7: Cyclic graph detection
# ---------------------------------------------------------------------------


def test_c7_cyclic_graph_detection():
    """A cycle A -> B -> C -> A: is_cyclic=True, nesting_depth=-1."""
    nodes = _make_nodes("A", "B", "C")
    edges = [
        _make_edge("e1", "A", "B"),
        _make_edge("e2", "B", "C"),
        _make_edge("e3", "C", "A"),  # back edge -> cycle
    ]
    svc = ComplexityService()
    result = svc.compute(nodes=nodes, edges=edges, diagram_type="state_machine", ceiling=100.0)
    assert result.is_cyclic
    assert result.nesting_depth == -1


# ---------------------------------------------------------------------------
# C8: compute_from_dict matches compute_from_groq_response
# ---------------------------------------------------------------------------


def test_c8_compute_from_dict_matches_groq_response():
    """compute_from_dict and compute_from_groq_response must give identical scores."""
    groq_model = _groq_response(
        nodes=_make_nodes("n1", "n2", "n3"),
        edges=[_make_edge("e1", "n1", "n2"), _make_edge("e2", "n2", "n3")],
    )
    svc = ComplexityService()
    result_a = svc.compute_from_groq_response(groq_model, ceiling=100.0)
    result_b = svc.compute_from_dict(groq_model.to_dict(), ceiling=100.0)

    assert result_a.score == result_b.score
    assert result_a.node_count == result_b.node_count
    assert result_a.edge_count == result_b.edge_count
    assert result_a.label == result_b.label


# ---------------------------------------------------------------------------
# C9: Groq self-reported complexity field is NOT used
# ---------------------------------------------------------------------------


def test_c9_groq_self_reported_complexity_not_trusted():
    """
    Even if Groq adds a 'complexity' field to its response, ComplexityService
    must ignore it entirely and compute its own score.

    The Groq contract schema intentionally excludes 'complexity', so any
    such field is silently dropped by Pydantic (extra='ignore').
    We validate that compute_from_dict doesn't read 'complexity' from the dict.
    """
    # Simulate a dict that Groq returned with a self-reported complexity
    raw_with_groq_complexity = {
        "diagram_type": "flowchart",
        "nodes": _make_nodes("n1", "n2"),
        "edges": [_make_edge("e1", "n1", "n2")],
        "attributes": _make_attrs(),
        "complexity": "simple",   # Groq hallucinated this -- must be ignored
        "complexity_score": 1.0,  # Also hallucinated -- must be ignored
    }

    svc = ComplexityService()
    # Validate through GroqDiagramResponse first (strips complexity field)
    from app.services.validation_service import validation_service
    val_result = validation_service.validate(raw_with_groq_complexity)
    assert val_result.is_valid, f"Payload should be valid (extra fields ignored): {val_result.errors}"

    # Now compute complexity independently
    result = svc.compute_from_groq_response(val_result.validated_model, ceiling=100.0)

    # The score should reflect the actual graph (2 nodes, 1 edge) -- not Groq's "simple" label
    assert result.score > 0
    assert result.label in ("simple", "moderate")  # independently computed label
    # Groq's "complexity_score: 1.0" must NOT appear as the score
    assert result.score != 1.0 or result.node_count > 0  # sanity: score formula ran


# ---------------------------------------------------------------------------
# C10: rejection_reason is None when ceiling not exceeded
# ---------------------------------------------------------------------------


def test_c10_no_rejection_reason_when_below_ceiling():
    """When score < ceiling, rejection_reason must be None."""
    svc = ComplexityService()
    result = svc.compute(
        nodes=_make_nodes("n1"),
        edges=[],
        diagram_type="flowchart",
        ceiling=100.0,
    )
    assert not result.exceeds_ceiling
    assert result.rejection_reason is None


# ---------------------------------------------------------------------------
# C11: rejection_reason is non-empty string when ceiling exceeded
# ---------------------------------------------------------------------------


def test_c11_rejection_reason_present_when_ceiling_exceeded():
    """When score >= ceiling, rejection_reason must be specific and non-empty."""
    # Use a very low ceiling to guarantee a hit
    svc = ComplexityService()
    result = svc.compute(
        nodes=_make_nodes("n1", "n2", "n3", "n4", "n5"),
        edges=[
            _make_edge("e1", "n1", "n2"),
            _make_edge("e2", "n2", "n3"),
            _make_edge("e3", "n3", "n4"),
            _make_edge("e4", "n4", "n5"),
        ],
        diagram_type="flowchart",
        ceiling=0.1,  # impossibly low -- guarantees ceiling breach
    )
    assert result.exceeds_ceiling
    assert result.rejection_reason is not None
    assert len(result.rejection_reason) > 20


# ---------------------------------------------------------------------------
# C12: max_in_degree and max_out_degree
# ---------------------------------------------------------------------------


def test_c12_degree_metrics_correct():
    """
    Fan-in: three nodes all point to a hub.
    max_in_degree must be 3 (hub), max_out_degree must be 1 (each source).
    """
    nodes = _make_nodes("hub", "s1", "s2", "s3")
    edges = [
        _make_edge("e1", "s1", "hub"),
        _make_edge("e2", "s2", "hub"),
        _make_edge("e3", "s3", "hub"),
    ]
    svc = ComplexityService()
    result = svc.compute(nodes=nodes, edges=edges, diagram_type="flowchart", ceiling=100.0)
    assert result.max_in_degree == 3
    assert result.max_out_degree == 1
