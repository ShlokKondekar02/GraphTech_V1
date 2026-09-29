"""
Sprint 2 tests -- Generation pipeline (mocked Groq + DB).

Tests the full pipeline in generation_service.run_pipeline with:
  - Groq mocked (no real API calls)
  - DB using the test SQLite session from conftest.py

Required test cases from the Definition of Done:
  G1  -- structurally invalid Groq output is rejected (never returned as success)
  G2  -- oversized/overcomplex prompt is rejected pre-render with a clear reason
  G3  -- cache-hit path still runs full re-validation (not a bypass)
  G3b -- valid cache hit is returned as cache_reused (Groq is not called)
  G4  -- fresh valid Groq response is persisted with status="validated"
  G5  -- rejected_invalid is persisted for bad Groq JSON
  G6  -- rejected_complexity is persisted for oversized result
  G9  -- Groq returning non-JSON is rejected with rejected_invalid
  G10 -- every persisted row has an accurate status (nothing silent)
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from app.services.generation_service import GenerationResult, GenerationService
from app.services.validation_service import validation_service
from app.services.complexity_service import complexity_service


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _valid_groq_payload(n_nodes: int = 2) -> dict:
    """Build a valid Groq-style payload with n_nodes connected in a chain."""
    nodes = [{"id": f"n{i}", "label": f"Node {i}", "type": "service"} for i in range(n_nodes)]
    edges = [
        {"id": f"e{i}", "source": f"n{i}", "target": f"n{i+1}", "label": "", "type": "calls"}
        for i in range(n_nodes - 1)
    ]
    return {
        "diagram_type": "flowchart",
        "nodes": nodes,
        "edges": edges,
        "attributes": {
            "title": "Test Diagram",
            "description": "Generated for testing.",
            "allows_disconnected": False,
            "direction": "LR",
        },
    }


def _oversized_groq_payload() -> dict:
    """Build a payload large enough to exceed the default ceiling of 50.0."""
    n = 60
    nodes = [{"id": f"n{i}", "label": f"Node {i}", "type": "service"} for i in range(n)]
    edges = []
    eid = 0
    for i in range(n - 1):
        edges.append({"id": f"e{eid}", "source": f"n{i}", "target": f"n{i+1}", "label": "", "type": "calls"})
        eid += 1
    # Extra cross-edges to inflate cyclomatic number
    for i in range(0, n - 10, 5):
        edges.append({"id": f"ex{eid}", "source": f"n{i}", "target": f"n{i+9}", "label": "", "type": "calls"})
        eid += 1
    return {
        "diagram_type": "flowchart",
        "nodes": nodes,
        "edges": edges,
        "attributes": {
            "title": "Oversized Diagram",
            "description": "Intentionally oversized for testing ceiling rejection.",
            "allows_disconnected": False,
            "direction": "LR",
        },
    }


def _invalid_groq_payload_missing_nodes() -> dict:
    return {
        "diagram_type": "flowchart",
        # "nodes" intentionally missing
        "edges": [],
        "attributes": {
            "title": "Bad",
            "description": "Missing nodes.",
            "allows_disconnected": False,
            "direction": "LR",
        },
    }


def _invalid_groq_payload_dangling_edge() -> dict:
    return {
        "diagram_type": "flowchart",
        "nodes": [{"id": "n1", "label": "A", "type": "service"}],
        "edges": [
            {"id": "e1", "source": "n1", "target": "GHOST", "label": "", "type": "calls"}
        ],
        "attributes": {
            "title": "Dangling Edge",
            "description": "Edge points to nonexistent node.",
            "allows_disconnected": False,
            "direction": "LR",
        },
    }


# ---------------------------------------------------------------------------
# Helper: build a GenerationService with mocked embedding + groq
# ---------------------------------------------------------------------------

def _make_svc_with_mocks(groq_payload, candidates=None):
    """
    Return (svc, mock_emb, mock_groq) with the Groq client returning groq_payload.
    groq_payload may be a dict (valid JSON) or a raw string (for bad-JSON tests).
    """
    from app.services.groq_service import GroqService

    svc = GenerationService()
    real_groq = GroqService()

    if isinstance(groq_payload, dict):
        content = json.dumps(groq_payload)
    else:
        content = groq_payload  # raw string (e.g. prose, not JSON)

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=content))]
    )

    return svc, real_groq, mock_client, candidates or []


# ---------------------------------------------------------------------------
# G1: Structurally invalid Groq output is rejected
# ---------------------------------------------------------------------------


def test_g1_invalid_groq_output_rejected_not_success(db_session):
    """
    When Groq returns a payload with missing 'nodes', the pipeline must
    return is_success=False and status='rejected_invalid'.
    It must NEVER return is_success=True.
    """
    svc, real_groq, mock_client, _ = _make_svc_with_mocks(_invalid_groq_payload_missing_nodes())

    with patch.object(real_groq, "_get_client", return_value=mock_client), \
         patch("app.services.generation_service.embedding_service") as mock_emb, \
         patch("app.services.generation_service.groq_service", real_groq):

        mock_emb.generate_embedding.return_value = [0.0] * 1024
        mock_emb.find_similar_diagrams.return_value = []

        result = svc.run_pipeline(db=db_session, prompt="draw me something")

    assert not result.is_success, "Invalid Groq output must not be returned as success"
    assert result.status == "rejected_invalid", f"Expected rejected_invalid, got: {result.status}"
    assert result.rejection_reason is not None


# ---------------------------------------------------------------------------
# G2: Oversized prompt rejected pre-render with a clear specific reason
# ---------------------------------------------------------------------------


def test_g2_oversized_prompt_rejected_pre_render(db_session):
    """
    An intentionally oversized payload must be rejected BEFORE rendering
    (Sprint 3 doesn't exist yet, but the rejection logic must exist now).
    The rejection_reason must be a specific, informative string.
    """
    svc, real_groq, mock_client, _ = _make_svc_with_mocks(_oversized_groq_payload())

    with patch.object(real_groq, "_get_client", return_value=mock_client), \
         patch("app.services.generation_service.embedding_service") as mock_emb, \
         patch("app.services.generation_service.groq_service", real_groq):

        mock_emb.generate_embedding.return_value = [0.0] * 1024
        mock_emb.find_similar_diagrams.return_value = []

        result = svc.run_pipeline(db=db_session, prompt="generate an oversized complex diagram")

    assert not result.is_success, "Oversized diagram must be rejected"
    assert result.status == "rejected_complexity", (
        f"Expected 'rejected_complexity', got '{result.status}'"
    )
    assert result.rejection_reason is not None
    assert len(result.rejection_reason) > 20, "rejection_reason must be substantive"

    # The reason must be specific: mention complexity metrics and pre-render intent
    reason_lower = result.rejection_reason.lower()
    assert "ceiling" in reason_lower or "score" in reason_lower or "complexity" in reason_lower, (
        f"rejection_reason not specific enough: {result.rejection_reason}"
    )
    assert "render" in reason_lower, (
        "rejection_reason must clarify this is a pre-render rejection"
    )


# ---------------------------------------------------------------------------
# G3: Cache-hit path runs full re-validation (invalid cached JSON is discarded)
# ---------------------------------------------------------------------------


def test_g3_cache_hit_runs_full_revalidation(db_session):
    """
    When a cache candidate is found with an invalid structured_json, the
    generation service must re-validate it, detect the failure, discard it,
    and fall through to fresh generation (not return the invalid data).
    """
    from app.services.embedding_service import SimilarityCandidate

    invalid_cached_json = _invalid_groq_payload_dangling_edge()
    bad_candidate = SimilarityCandidate(
        id=str(uuid.uuid4()),
        prompt="draw something",
        similarity=0.95,  # high confidence -- would be a cache hit
        structured_json=invalid_cached_json,
        diagram_type="flowchart",
        complexity="simple",
        renderer=None,
    )

    # Fresh generation returns a valid result
    valid_fresh_payload = _valid_groq_payload(2)
    svc, real_groq, mock_client, _ = _make_svc_with_mocks(valid_fresh_payload)

    with patch.object(real_groq, "_get_client", return_value=mock_client), \
         patch("app.services.generation_service.embedding_service") as mock_emb, \
         patch("app.services.generation_service.groq_service", real_groq):

        mock_emb.generate_embedding.return_value = [0.0] * 1024
        mock_emb.find_similar_diagrams.return_value = [bad_candidate]

        result = svc.run_pipeline(db=db_session, prompt="draw something")

    # The invalid cache hit must NOT have been returned as a cache hit
    # It failed re-validation -> fell through to fresh generation -> success
    assert result.is_success, (
        f"Expected fresh generation success after cache miss, "
        f"got status={result.status}, reason={result.rejection_reason}"
    )
    assert result.source == "fresh", "Must have fallen through to fresh generation"
    # Groq WAS called (fresh generation happened)
    assert mock_client.chat.completions.create.called


# ---------------------------------------------------------------------------
# G3b: Valid cache hit returned as cache_reused without calling Groq
# ---------------------------------------------------------------------------


def test_g3b_valid_cache_hit_returned_as_cache_reused(db_session):
    """
    A cache candidate with VALID structured_json must be returned as
    'cache_reused' after passing re-validation -- Groq must NOT be called.
    """
    from app.services.embedding_service import SimilarityCandidate

    valid_cached_json = _valid_groq_payload(2)
    good_candidate = SimilarityCandidate(
        id=str(uuid.uuid4()),
        prompt="similar prompt",
        similarity=0.92,
        structured_json=valid_cached_json,
        diagram_type="flowchart",
        complexity="simple",
        renderer=None,
    )

    svc = GenerationService()
    mock_groq = MagicMock()
    mock_groq.generate_diagram_json.side_effect = AssertionError(
        "groq_service must NOT be called on a valid cache hit"
    )

    with patch("app.services.generation_service.embedding_service") as mock_emb, \
         patch("app.services.generation_service.groq_service", mock_groq):

        mock_emb.generate_embedding.return_value = [0.0] * 1024
        mock_emb.find_similar_diagrams.return_value = [good_candidate]

        result = svc.run_pipeline(db=db_session, prompt="draw something similar")

    assert result.is_success
    assert result.status == "cache_reused"
    assert result.source == "cache"
    assert result.similarity_score == pytest.approx(0.92)
    mock_groq.generate_diagram_json.assert_not_called()


# ---------------------------------------------------------------------------
# G4: Fresh valid result persisted with status="validated"
# ---------------------------------------------------------------------------


def test_g4_valid_fresh_result_persisted_as_validated(db_session):
    """
    A successful fresh generation must be persisted to diagram_requests
    with status='validated'.
    """
    svc, real_groq, mock_client, _ = _make_svc_with_mocks(_valid_groq_payload(2))

    with patch.object(real_groq, "_get_client", return_value=mock_client), \
         patch("app.services.generation_service.embedding_service") as mock_emb, \
         patch("app.services.generation_service.groq_service", real_groq):

        mock_emb.generate_embedding.return_value = [0.0] * 1024
        mock_emb.find_similar_diagrams.return_value = []

        result = svc.run_pipeline(db=db_session, prompt="design a simple flowchart")

    assert result.is_success
    assert result.status == "validated"
    assert result.structured_json is not None

    # Verify DB persistence by querying for the row by status
    from app.models.diagram_requests import DiagramRequest
    rows = db_session.query(DiagramRequest).filter_by(status="validated").all()
    assert len(rows) >= 1
    matching = [r for r in rows if str(r.id) == result.request_id]
    assert len(matching) == 1
    assert matching[0].status == "validated"


# ---------------------------------------------------------------------------
# G5: Rejected invalid result persisted with status="rejected_invalid"
# ---------------------------------------------------------------------------


def test_g5_rejected_invalid_persisted(db_session):
    """
    A Groq response that fails validation must be persisted as 'rejected_invalid'.
    """
    svc, real_groq, mock_client, _ = _make_svc_with_mocks(_invalid_groq_payload_missing_nodes())

    with patch.object(real_groq, "_get_client", return_value=mock_client), \
         patch("app.services.generation_service.embedding_service") as mock_emb, \
         patch("app.services.generation_service.groq_service", real_groq):

        mock_emb.generate_embedding.return_value = [0.0] * 1024
        mock_emb.find_similar_diagrams.return_value = []

        result = svc.run_pipeline(db=db_session, prompt="give me a broken diagram")

    assert result.status == "rejected_invalid"

    from app.models.diagram_requests import DiagramRequest
    rows = db_session.query(DiagramRequest).filter_by(status="rejected_invalid").all()
    matching = [r for r in rows if str(r.id) == result.request_id]
    assert len(matching) == 1
    assert matching[0].rejection_reason is not None


# ---------------------------------------------------------------------------
# G6: Rejected complexity persisted with status="rejected_complexity"
# ---------------------------------------------------------------------------


def test_g6_rejected_complexity_persisted(db_session):
    """
    An oversized Groq response must be persisted as 'rejected_complexity'.
    """
    svc, real_groq, mock_client, _ = _make_svc_with_mocks(_oversized_groq_payload())

    with patch.object(real_groq, "_get_client", return_value=mock_client), \
         patch("app.services.generation_service.embedding_service") as mock_emb, \
         patch("app.services.generation_service.groq_service", real_groq):

        mock_emb.generate_embedding.return_value = [0.0] * 1024
        mock_emb.find_similar_diagrams.return_value = []

        result = svc.run_pipeline(db=db_session, prompt="generate an oversized system")

    assert result.status == "rejected_complexity"

    from app.models.diagram_requests import DiagramRequest
    rows = db_session.query(DiagramRequest).filter_by(status="rejected_complexity").all()
    matching = [r for r in rows if str(r.id) == result.request_id]
    assert len(matching) == 1
    assert matching[0].rejection_reason is not None


# ---------------------------------------------------------------------------
# G9: Non-JSON Groq response rejected as rejected_invalid
# ---------------------------------------------------------------------------


def test_g9_non_json_groq_response_rejected(db_session):
    """
    Groq returning plain text (not JSON) must result in rejected_invalid,
    not a server crash.
    """
    # Raw prose response, not JSON
    svc, real_groq, mock_client, _ = _make_svc_with_mocks(
        "Here is your diagram! Nodes: A, B, C. Hope that helps!"
    )

    with patch.object(real_groq, "_get_client", return_value=mock_client), \
         patch("app.services.generation_service.embedding_service") as mock_emb, \
         patch("app.services.generation_service.groq_service", real_groq):

        mock_emb.generate_embedding.return_value = [0.0] * 1024
        mock_emb.find_similar_diagrams.return_value = []

        result = svc.run_pipeline(db=db_session, prompt="something")

    assert not result.is_success
    assert result.status == "rejected_invalid"
    assert result.rejection_reason is not None


# ---------------------------------------------------------------------------
# G10: Every persisted row has accurate status (nothing silent)
# ---------------------------------------------------------------------------


def test_g10_all_statuses_auditable(db_session):
    """
    Run several pipeline scenarios and confirm every resulting DB row has
    a non-null, non-empty, meaningful status -- nothing silently fails.
    """
    from app.services.groq_service import GroqService
    from app.models.diagram_requests import DiagramRequest

    scenarios = [
        ("valid", _valid_groq_payload(2), "validated"),
        ("invalid", _invalid_groq_payload_missing_nodes(), "rejected_invalid"),
        ("oversized", _oversized_groq_payload(), "rejected_complexity"),
    ]

    for scenario_name, payload, expected_status in scenarios:
        svc, real_groq, mock_client, _ = _make_svc_with_mocks(payload)

        with patch.object(real_groq, "_get_client", return_value=mock_client), \
             patch("app.services.generation_service.embedding_service") as mock_emb, \
             patch("app.services.generation_service.groq_service", real_groq):

            mock_emb.generate_embedding.return_value = [0.0] * 1024
            mock_emb.find_similar_diagrams.return_value = []

            result = svc.run_pipeline(db=db_session, prompt=f"scenario: {scenario_name}")

        assert result.status == expected_status, (
            f"Scenario '{scenario_name}': expected status='{expected_status}', "
            f"got='{result.status}'"
        )

        # Verify DB persistence
        rows = db_session.query(DiagramRequest).filter_by(status=expected_status).all()
        matching = [r for r in rows if str(r.id) == result.request_id]
        assert len(matching) == 1, (
            f"Scenario '{scenario_name}': no DB row persisted with id={result.request_id}"
        )
        assert matching[0].status == expected_status, (
            f"Scenario '{scenario_name}': DB status mismatch"
        )
