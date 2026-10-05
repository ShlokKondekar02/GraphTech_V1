"""
Sprint 4 Test Suite -- Output Validation & Bounded Repair Loop.

Tests:
  1. OutputValidatorService: Valid SVG passes XML integrity & semantic reconciliation.
  2. OutputValidatorService: Malformed XML fails with XML parse error.
  3. OutputValidatorService: Kroki embedded error text detected and rejected.
  4. OutputValidatorService: Empty SVG without graphical elements rejected.
  5. OutputValidatorService: Semantic reconciliation detects missing AST node labels.
  6. RenderingService: Fallback renderer chain activates when primary engine fails.
  7. GenerationService: Clean run sets attempt_count=1 and status='validated'.
  8. GenerationService: Auto-repair loop recovers after failure, setting status='auto_repaired' and attempt_count=2.
  9. GenerationService: Exhausted retries return status='failed_validation' without false success.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from app.services.output_validator_service import (
    OutputValidationResult,
    output_validator_service,
)
from app.services.rendering_service import RenderingService, RenderResult
from app.services.generation_service import GenerationService, GenerationResult
from app.services.groq_service import GroqValidationError
from app.services.validation_service import ValidationResult, GroqDiagramResponse
from app.services.kroki_client import KrokiRenderError


# ------------------------------------------------------------------------------
# 1. OutputValidatorService Unit Tests
# ------------------------------------------------------------------------------


def test_validator_valid_svg_and_reconciliation():
    """Valid SVG with matching AST node labels passes validation."""
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200">
      <rect width="100" height="50" fill="blue"/>
      <text x="10" y="20">User Service</text>
      <text x="10" y="80">Database Cluster</text>
    </svg>"""

    structured_json = {
        "nodes": [
            {"id": "n1", "label": "User Service", "type": "service"},
            {"id": "n2", "label": "Database Cluster", "type": "database"},
        ]
    }

    res: OutputValidationResult = output_validator_service.validate_svg(svg, structured_json)
    assert res.is_valid is True
    assert res.xml_integrity is True
    assert res.kroki_error_detected is False
    assert res.semantic_reconciliation is True
    assert res.reconciled_labels_count == 2


def test_validator_malformed_xml():
    """Malformed SVG XML fails XML integrity check."""
    malformed_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="300">
      <rect width="100" height="50">
      <text>Missing closing tags
    </svg>"""

    res = output_validator_service.validate_svg(malformed_svg)
    assert res.is_valid is False
    assert res.xml_integrity is False
    assert "xml parse error" in res.error_message.lower()


def test_validator_embedded_kroki_error():
    """SVG containing Kroki error text is detected and rejected."""
    kroki_error_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="500" height="300">
      <text x="10" y="20" fill="red">Syntax error in PlantUML script at line 3</text>
    </svg>"""

    res = output_validator_service.validate_svg(kroki_error_svg)
    assert res.is_valid is False
    assert res.kroki_error_detected is True
    assert "syntax error" in res.error_message.lower()


def test_validator_empty_structure():
    """SVG without renderable graphical elements is rejected."""
    empty_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"></svg>"""

    res = output_validator_service.validate_svg(empty_svg)
    assert res.is_valid is False
    assert "no renderable graphical elements" in res.error_message.lower()


def test_validator_semantic_reconciliation_failure():
    """SVG missing expected AST node labels fails semantic reconciliation."""
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200">
      <rect width="100" height="50"/>
      <text x="10" y="20">Unrelated Node</text>
    </svg>"""

    structured_json = {
        "nodes": [
            {"id": "n1", "label": "Payment Gateway API", "type": "service"},
            {"id": "n2", "label": "PostgreSQL Analytics DB", "type": "database"},
        ]
    }

    res = output_validator_service.validate_svg(svg, structured_json)
    assert res.is_valid is False
    assert res.xml_integrity is True
    assert res.semantic_reconciliation is False
    assert len(res.missing_labels) > 0


# ------------------------------------------------------------------------------
# 2. RenderingService Fallback Chain Unit Tests
# ------------------------------------------------------------------------------


def test_rendering_service_fallback_chain():
    """When primary renderer throws KrokiRenderError, fallback renderer is attempted."""
    mock_client = MagicMock()
    # First call (e.g. mermaid) raises error, second call (graphviz) succeeds
    mock_client.render_sync.side_effect = [
        KrokiRenderError(400, "Mermaid syntax error"),
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect/><text>Auth Service</text></svg>',
    ]

    service = RenderingService(client=mock_client)

    ast = {
        "diagram_type": "architecture",
        "nodes": [{"id": "n1", "label": "Auth Service", "type": "service"}],
        "edges": [],
        "attributes": {"title": "Test", "description": "Test description", "allows_disconnected": True}
    }

    result: RenderResult = service.render_diagram(ast, preferred_renderer="mermaid")
    assert result.renderer == "graphviz"
    assert "<svg" in result.svg_content
    assert mock_client.render_sync.call_count == 2


# ------------------------------------------------------------------------------
# 3. GenerationService Repair Loop Integration Tests
# ------------------------------------------------------------------------------


def test_generation_pipeline_bounded_repair_success():
    """Attempt 0 fails, Attempt 1 succeeds via repair prompt -> status='auto_repaired'."""
    service = GenerationService()

    valid_ast_dict = {
        "diagram_type": "flowchart",
        "nodes": [{"id": "n1", "label": "Ingest", "type": "generic"}, {"id": "n2", "label": "Process", "type": "generic"}],
        "edges": [{"id": "e1", "source": "n1", "target": "n2", "label": "", "type": "generic"}],
        "attributes": {"title": "Repaired Pipeline", "description": "Repaired description", "allows_disconnected": False}
    }
    repaired_model = GroqDiagramResponse.model_validate(valid_ast_dict)
    valid_val_result = ValidationResult(is_valid=True, validated_model=repaired_model)
    failed_val_result = ValidationResult(is_valid=False, errors=["[Pydantic] missing node label"], layer="pydantic")

    with patch("app.services.generation_service.groq_service") as mock_groq, \
         patch("app.services.generation_service.rendering_service") as mock_render, \
         patch("app.services.generation_service.complexity_service") as mock_comp:

        mock_groq.generate_diagram_json.side_effect = GroqValidationError("Invalid JSON", failed_val_result)
        mock_groq.repair_diagram_json.return_value = valid_val_result

        mock_comp.compute_from_groq_response.return_value = MagicMock(exceeds_ceiling=False, score=1.2, rejection_reason=None)
        mock_render.render_diagram.return_value = MagicMock(
            diagram_type="flowchart",
            renderer="mermaid",
            dsl_code="graph TD; n1[Ingest]-->n2[Process];",
            svg_content='<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect/><text>Ingest</text><text>Process</text></svg>'
        )

        res: GenerationResult = service._generate_fresh(
            request_id="req-test-repair",
            prompt="create pipeline diagram",
            preprocessed_prompt="create pipeline diagram",
            spacy_enabled=False,
            candidates_count=0
        )

        assert res.status == "auto_repaired"
        assert res.attempt_count == 2
        assert res.validation_status == "auto_repaired"
        assert res.is_success is True
        assert len(res.repair_history) == 1


def test_generation_pipeline_exhausted_retries_failure():
    """All repair attempts fail -> returns status='failed_validation' and attempt_count=3."""
    service = GenerationService()
    failed_val_result = ValidationResult(is_valid=False, errors=["Unresolvable graph cycle"], layer="graph")

    with patch("app.services.generation_service.groq_service") as mock_groq:
        mock_groq.generate_diagram_json.side_effect = GroqValidationError("Failed graph validation", failed_val_result)
        mock_groq.repair_diagram_json.side_effect = GroqValidationError("Failed graph repair", failed_val_result)

        res: GenerationResult = service._generate_fresh(
            request_id="req-test-fail",
            prompt="create broken diagram",
            preprocessed_prompt="create broken diagram",
            spacy_enabled=False,
            candidates_count=0
        )

        assert res.status == "failed_validation"
        assert res.attempt_count == 3
        assert res.validation_status == "output_validation_failed"
        assert res.is_success is False
        assert "after 2 repair attempts" in res.rejection_reason
