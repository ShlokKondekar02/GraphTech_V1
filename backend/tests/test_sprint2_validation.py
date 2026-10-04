"""
Sprint 2 tests -- Validation layer (schema + graph rules).

Tests deterministic validation of GroqDiagramResponse without any
Groq API calls.  All payloads are hand-crafted to simulate the kinds
of hallucinated or malformed responses Groq might produce.

Coverage:
  T1  -- valid minimal payload passes both layers
  T2  -- valid full payload passes both layers
  T3  -- missing required field (nodes) fails Pydantic (layer 1)
  T4  -- wrong type for nodes (string instead of list) fails Pydantic
  T5  -- edge references nonexistent source node (referential integrity)
  T6  -- edge references nonexistent target node (referential integrity)
  T7  -- duplicate node IDs are rejected
  T8  -- duplicate edge IDs are rejected
  T9  -- node with blank label is rejected
  T10 -- node ID with whitespace is rejected
  T11 -- disconnected graph (isolated nodes) rejected for flowchart
  T12 -- disconnected graph ALLOWED for mindmap type
  T13 -- allows_disconnected=True for flowchart is rejected (flag mismatch)
  T14 -- missing attributes field fails Pydantic
  T15 -- attributes.title blank is rejected
  T16 -- invalid diagram_type literal fails Pydantic
  T17 -- non-dict input fails gracefully (no crash)
  T18 -- edge with whitespace source ID fails
  T19 -- ValidationResult.error_summary is non-empty on failure
  T20 -- ValidationResult.validated_model is None on failure
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.groq_contract import GroqDiagramResponse, DISCONNECTED_ALLOWED_TYPES
from app.services.validation_service import ValidationResult, validation_service


# ---------------------------------------------------------------------------
# Fixtures -- reusable valid sub-structures
# ---------------------------------------------------------------------------


def _valid_node(node_id: str, label: str = "Node", ntype: str = "service") -> dict:
    return {"id": node_id, "label": label, "type": ntype}


def _valid_edge(edge_id: str, source: str, target: str) -> dict:
    return {"id": edge_id, "source": source, "target": target, "label": "", "type": "calls"}


def _valid_attributes(allows_disconnected: bool = False) -> dict:
    return {
        "title": "Test Diagram",
        "description": "A test diagram for validation.",
        "allows_disconnected": allows_disconnected,
        "direction": "LR",
    }


def _minimal_valid_payload() -> dict:
    """The simplest possible valid payload: one node, no edges."""
    return {
        "diagram_type": "flowchart",
        "nodes": [_valid_node("n1", "Start")],
        "edges": [],
        "attributes": _valid_attributes(allows_disconnected=False),
    }


def _two_node_payload() -> dict:
    """Two connected nodes."""
    return {
        "diagram_type": "flowchart",
        "nodes": [_valid_node("n1", "A"), _valid_node("n2", "B")],
        "edges": [_valid_edge("e1", "n1", "n2")],
        "attributes": _valid_attributes(allows_disconnected=False),
    }


# ---------------------------------------------------------------------------
# T1: Valid minimal payload
# ---------------------------------------------------------------------------


def test_t1_valid_minimal_payload_passes():
    """A single-node diagram with no edges must pass both validation layers."""
    payload = _minimal_valid_payload()
    result = validation_service.validate(payload)
    assert result.is_valid, f"Expected valid, got errors: {result.errors}"
    assert result.validated_model is not None
    assert result.layer is None
    assert result.errors == []


# ---------------------------------------------------------------------------
# T2: Valid full payload
# ---------------------------------------------------------------------------


def test_t2_valid_full_payload_passes():
    """A well-formed two-node connected diagram must pass."""
    payload = _two_node_payload()
    result = validation_service.validate(payload)
    assert result.is_valid, f"Expected valid, got errors: {result.errors}"
    assert result.validated_model is not None
    assert result.validated_model.diagram_type == "flowchart"
    assert len(result.validated_model.nodes) == 2
    assert len(result.validated_model.edges) == 1


# ---------------------------------------------------------------------------
# T3: Missing required field (nodes)
# ---------------------------------------------------------------------------


def test_t3_missing_nodes_fails_pydantic():
    """Payload without 'nodes' must fail layer 1 (Pydantic)."""
    payload = {
        "diagram_type": "flowchart",
        # "nodes" intentionally omitted
        "edges": [],
        "attributes": _valid_attributes(),
    }
    result = validation_service.validate(payload)
    assert not result.is_valid
    assert result.layer == "pydantic"
    assert len(result.errors) > 0


# ---------------------------------------------------------------------------
# T4: Wrong type for nodes (string instead of list)
# ---------------------------------------------------------------------------


def test_t4_nodes_wrong_type_fails_pydantic():
    """'nodes' must be a list; a string value must fail Pydantic."""
    payload = {
        "diagram_type": "flowchart",
        "nodes": "not-a-list",
        "edges": [],
        "attributes": _valid_attributes(),
    }
    result = validation_service.validate(payload)
    assert not result.is_valid
    assert result.layer == "pydantic"


# ---------------------------------------------------------------------------
# T5: Edge references nonexistent source node
# ---------------------------------------------------------------------------


def test_t5_edge_references_nonexistent_source():
    """An edge whose source does not exist in nodes must be rejected."""
    payload = {
        "diagram_type": "flowchart",
        "nodes": [_valid_node("n1", "A")],
        "edges": [{"id": "e1", "source": "GHOST_NODE", "target": "n1", "label": "", "type": "calls"}],
        "attributes": _valid_attributes(),
    }
    result = validation_service.validate(payload)
    assert not result.is_valid
    # Referential integrity violation caught in Pydantic layer (model_validator)
    assert "GHOST_NODE" in " ".join(result.errors)


# ---------------------------------------------------------------------------
# T6: Edge references nonexistent target node
# ---------------------------------------------------------------------------


def test_t6_edge_references_nonexistent_target():
    """An edge whose target does not exist in nodes must be rejected."""
    payload = {
        "diagram_type": "flowchart",
        "nodes": [_valid_node("n1", "A")],
        "edges": [{"id": "e1", "source": "n1", "target": "MISSING_TARGET", "label": "", "type": "calls"}],
        "attributes": _valid_attributes(),
    }
    result = validation_service.validate(payload)
    assert not result.is_valid
    assert "MISSING_TARGET" in " ".join(result.errors)


# ---------------------------------------------------------------------------
# T7: Duplicate node IDs
# ---------------------------------------------------------------------------


def test_t7_duplicate_node_ids_rejected():
    """Two nodes with the same id must be rejected as a hallucination."""
    payload = {
        "diagram_type": "flowchart",
        "nodes": [
            _valid_node("n1", "First"),
            _valid_node("n1", "Duplicate -- same ID as first"),  # duplicate
        ],
        "edges": [],
        "attributes": _valid_attributes(),
    }
    result = validation_service.validate(payload)
    assert not result.is_valid
    assert result.layer == "pydantic"
    # Error message must call out the duplicate
    assert "n1" in " ".join(result.errors)


# ---------------------------------------------------------------------------
# T8: Duplicate edge IDs
# ---------------------------------------------------------------------------


def test_t8_duplicate_edge_ids_rejected():
    """Two edges with the same id must be rejected."""
    payload = {
        "diagram_type": "flowchart",
        "nodes": [_valid_node("n1", "A"), _valid_node("n2", "B"), _valid_node("n3", "C")],
        "edges": [
            _valid_edge("e1", "n1", "n2"),
            _valid_edge("e1", "n2", "n3"),  # duplicate edge id
        ],
        "attributes": _valid_attributes(),
    }
    result = validation_service.validate(payload)
    assert not result.is_valid
    assert result.layer == "pydantic"
    assert "e1" in " ".join(result.errors)


# ---------------------------------------------------------------------------
# T9: Node with blank label
# ---------------------------------------------------------------------------


def test_t9_blank_node_label_rejected():
    """A node with a whitespace-only label must be rejected."""
    payload = {
        "diagram_type": "flowchart",
        "nodes": [{"id": "n1", "label": "   ", "type": "service"}],
        "edges": [],
        "attributes": _valid_attributes(),
    }
    result = validation_service.validate(payload)
    assert not result.is_valid
    assert result.layer == "pydantic"


# ---------------------------------------------------------------------------
# T10: Node ID with whitespace
# ---------------------------------------------------------------------------


def test_t10_node_id_with_whitespace_rejected():
    """A node ID containing a space must be rejected."""
    payload = {
        "diagram_type": "flowchart",
        "nodes": [{"id": "node 1", "label": "A Node", "type": "service"}],
        "edges": [],
        "attributes": _valid_attributes(),
    }
    result = validation_service.validate(payload)
    assert not result.is_valid
    assert result.layer == "pydantic"


# ---------------------------------------------------------------------------
# T11: Disconnected graph rejected for flowchart
# ---------------------------------------------------------------------------


def test_t11_disconnected_graph_rejected_for_flowchart():
    """
    A flowchart with isolated nodes (no edges at all, two+ nodes) must be
    rejected by layer 2 (graph rules).
    """
    payload = {
        "diagram_type": "flowchart",
        "nodes": [_valid_node("n1", "A"), _valid_node("n2", "B")],  # no edges -> disconnected
        "edges": [],
        "attributes": _valid_attributes(allows_disconnected=False),
    }
    result = validation_service.validate(payload)
    assert not result.is_valid
    assert result.layer == "graph"
    # Error must mention isolated/disconnected
    combined = " ".join(result.errors).lower()
    assert "isolated" in combined or "connected" in combined or "disconnected" in combined


# ---------------------------------------------------------------------------
# T12: Disconnected graph ALLOWED for mindmap
# ---------------------------------------------------------------------------


def test_t12_disconnected_graph_allowed_for_mindmap():
    """Mindmap with isolated nodes must PASS -- disconnected is semantically valid."""
    payload = {
        "diagram_type": "mindmap",
        "nodes": [_valid_node("n1", "Topic A"), _valid_node("n2", "Topic B")],
        "edges": [],  # no edges -- isolated nodes, but that's OK for mindmap
        "attributes": _valid_attributes(allows_disconnected=True),
    }
    result = validation_service.validate(payload)
    assert result.is_valid, f"Expected valid mindmap, got errors: {result.errors}"


# ---------------------------------------------------------------------------
# T13: allows_disconnected=True for flowchart -- flag mismatch
# ---------------------------------------------------------------------------


def test_t13_disconnected_flag_mismatch_rejected():
    """
    Groq claims allows_disconnected=True for a flowchart -- this must be
    rejected because flowchart is not in DISCONNECTED_ALLOWED_TYPES.
    """
    payload = {
        "diagram_type": "flowchart",
        "nodes": [_valid_node("n1", "A"), _valid_node("n2", "B")],
        "edges": [_valid_edge("e1", "n1", "n2")],
        "attributes": {
            "title": "Bad Flag",
            "description": "Flowchart claiming disconnected is allowed.",
            "allows_disconnected": True,  # WRONG for flowchart
            "direction": "LR",
        },
    }
    result = validation_service.validate(payload)
    assert not result.is_valid
    assert result.layer == "pydantic"
    # Message must mention flowchart and/or allowed types
    combined = " ".join(result.errors).lower()
    assert "flowchart" in combined or "disconnected" in combined


# ---------------------------------------------------------------------------
# T14: Missing attributes field
# ---------------------------------------------------------------------------


def test_t14_missing_attributes_fails_pydantic():
    """A payload without 'attributes' must fail Pydantic."""
    payload = {
        "diagram_type": "flowchart",
        "nodes": [_valid_node("n1", "A")],
        "edges": [],
        # "attributes" omitted
    }
    result = validation_service.validate(payload)
    assert not result.is_valid
    assert result.layer == "pydantic"


# ---------------------------------------------------------------------------
# T15: Blank attributes.title
# ---------------------------------------------------------------------------


def test_t15_blank_attributes_title_rejected():
    """attributes.title must not be blank."""
    payload = {
        "diagram_type": "flowchart",
        "nodes": [_valid_node("n1", "A")],
        "edges": [],
        "attributes": {
            "title": "",
            "description": "Valid description.",
            "allows_disconnected": False,
            "direction": "LR",
        },
    }
    result = validation_service.validate(payload)
    assert not result.is_valid
    assert result.layer == "pydantic"


# ---------------------------------------------------------------------------
# T16: Invalid diagram_type literal
# ---------------------------------------------------------------------------


def test_t16_invalid_diagram_type_rejected():
    """A diagram_type not in the allowed literals must fail Pydantic."""
    payload = {
        "diagram_type": "spaghetti_chart",  # not a valid type
        "nodes": [_valid_node("n1", "A")],
        "edges": [],
        "attributes": _valid_attributes(),
    }
    result = validation_service.validate(payload)
    assert not result.is_valid
    assert result.layer == "pydantic"


# ---------------------------------------------------------------------------
# T17: Non-dict input fails gracefully
# ---------------------------------------------------------------------------


def test_t17_non_dict_input_fails_gracefully():
    """Passing a string (or None) instead of a dict must not crash -- return ValidationResult."""
    for bad_input in ["not a dict", None, 42, [], True]:
        result = validation_service.validate(bad_input)
        assert not result.is_valid, f"Expected invalid for input {bad_input!r}"
        assert result.layer == "pydantic"
        assert len(result.errors) > 0


# ---------------------------------------------------------------------------
# T18: Edge with whitespace in source ID
# ---------------------------------------------------------------------------


def test_t18_edge_source_with_whitespace_rejected():
    """An edge source containing whitespace must fail Pydantic."""
    payload = {
        "diagram_type": "flowchart",
        "nodes": [_valid_node("n1", "A")],
        "edges": [
            {"id": "e1", "source": "n 1", "target": "n1", "label": "", "type": "calls"}
        ],
        "attributes": _valid_attributes(),
    }
    result = validation_service.validate(payload)
    assert not result.is_valid
    assert result.layer == "pydantic"


# ---------------------------------------------------------------------------
# T19: error_summary is non-empty on failure
# ---------------------------------------------------------------------------


def test_t19_error_summary_non_empty_on_failure():
    """ValidationResult.error_summary must be a non-empty string on failure."""
    payload = {"diagram_type": "flowchart", "nodes": [], "edges": [], "attributes": _valid_attributes()}
    result = validation_service.validate(payload)
    assert not result.is_valid
    assert result.error_summary != ""
    assert result.layer is not None


# ---------------------------------------------------------------------------
# T20: validated_model is None on failure
# ---------------------------------------------------------------------------


def test_t20_validated_model_is_none_on_failure():
    """On validation failure, validated_model must always be None."""
    payload = {"this": "is", "totally": "wrong"}
    result = validation_service.validate(payload)
    assert not result.is_valid
    assert result.validated_model is None


# ---------------------------------------------------------------------------
# T21: GroqDiagramResponse.to_dict() roundtrip
# ---------------------------------------------------------------------------


def test_t21_to_dict_roundtrip():
    """A valid GroqDiagramResponse must serialize and re-validate cleanly."""
    model = GroqDiagramResponse.model_validate(_two_node_payload())
    serialized = model.to_dict()
    result = validation_service.validate(serialized)
    assert result.is_valid, f"Roundtrip failed: {result.errors}"


# ---------------------------------------------------------------------------
# T22: Hallucinated extra field on node is accepted (extra fields ignored)
# ---------------------------------------------------------------------------


def test_t22_extra_fields_on_node_accepted():
    """
    Groq may hallucinate extra fields.  Pydantic should ignore them silently
    (model_config defaults to ignore extra fields in BaseModel).
    The payload should still pass validation.
    """
    payload = {
        "diagram_type": "flowchart",
        "nodes": [
            {
                "id": "n1",
                "label": "A",
                "type": "service",
                "hallucinated_field": "this should be ignored",
                "complexity": "high",  # Groq self-reporting -- must be ignored
            }
        ],
        "edges": [],
        "attributes": _valid_attributes(),
    }
    result = validation_service.validate(payload)
    # Extra fields should NOT cause rejection -- Pydantic ignores them by default
    # The real guard is that complexity is computed by ComplexityService, not read from here
    assert result.is_valid, f"Extra fields caused unexpected rejection: {result.errors}"


# ---------------------------------------------------------------------------
# Phase 2: Specialized Discriminated Diagram Schemas (T23 - T27)
# ---------------------------------------------------------------------------


def test_t23_erd_specialized_schema():
    """ERD payload gets instantiated as ErdDiagramResponse and normalizes edge types."""
    payload = {
        "diagram_type": "erd",
        "nodes": [_valid_node("n1", "Users", "service"), _valid_node("n2", "Orders", "generic")],
        "edges": [_valid_edge("e1", "n1", "n2")],
        "attributes": _valid_attributes(),
    }
    result = validation_service.validate(payload)
    assert result.is_valid
    model = result.validated_model
    assert model.diagram_type == "erd"
    assert model.nodes[0].type == "entity"
    assert model.edges[0].type in {"one_to_many", "calls"}


def test_t24_sequence_specialized_schema():
    """Sequence payload gets instantiated as SequenceDiagramResponse."""
    payload = {
        "diagram_type": "sequence",
        "nodes": [_valid_node("n1", "Client", "actor"), _valid_node("n2", "Server", "service")],
        "edges": [{"id": "e1", "source": "n1", "target": "n2", "label": "Login", "type": "sync_call"}],
        "attributes": _valid_attributes(),
    }
    result = validation_service.validate(payload)
    assert result.is_valid
    model = result.validated_model
    assert model.diagram_type == "sequence"
    assert model.edges[0].type == "calls"


def test_t25_class_specialized_schema():
    """Class diagram payload gets instantiated as ClassDiagramResponse."""
    payload = {
        "diagram_type": "class",
        "nodes": [_valid_node("n1", "Animal", "generic"), _valid_node("n2", "Dog", "generic")],
        "edges": [{"id": "e1", "source": "n2", "target": "n1", "label": "extends", "type": "extends"}],
        "attributes": _valid_attributes(),
    }
    result = validation_service.validate(payload)
    assert result.is_valid
    model = result.validated_model
    assert model.diagram_type == "class"
    assert model.nodes[0].type == "class"
    assert model.edges[0].type == "inherits"


def test_t26_state_machine_specialized_schema():
    """State machine payload allows self-loops and state node normalization."""
    payload = {
        "diagram_type": "state_machine",
        "nodes": [_valid_node("n1", "Idle", "generic")],
        "edges": [{"id": "e1", "source": "n1", "target": "n1", "label": "Ping", "type": "transitions_to"}],
        "attributes": _valid_attributes(),
    }
    result = validation_service.validate(payload)
    assert result.is_valid
    model = result.validated_model
    assert model.diagram_type == "state_machine"
    assert model.nodes[0].type == "state"
    assert len(model.edges) == 1  # Self-loop preserved for state_machine


def test_t27_network_specialized_schema():
    """Network diagram payload gets instantiated as NetworkDiagramResponse."""
    payload = {
        "diagram_type": "network",
        "nodes": [_valid_node("n1", "Router1", "generic")],
        "edges": [],
        "attributes": {
            "title": "Network Topology",
            "description": "Lab setup",
            "allows_disconnected": True,
            "direction": "auto",
        },
    }
    result = validation_service.validate(payload)
    assert result.is_valid
    model = result.validated_model
    assert model.diagram_type == "network"
    assert model.nodes[0].type == "server"

