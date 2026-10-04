"""
Sprint 4 tests -- Auto-Repair Loop & SVG XML Reconciliation Engine.

Coverage:
  1. SVG XML Reconciliation: Valid SVG string passes.
  2. SVG XML Reconciliation: Malformed or truncated SVG fails.
  3. Auto-Repair Loop: Attempt 0 succeeds directly (status: "validated").
  4. Auto-Repair Loop: Attempt 0 fails validation, Attempt 1 succeeds via repair prompt (status: "auto_repaired").
  5. Auto-Repair Loop: All 2 repair attempts fail (status: "failed_validation").
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from app.services.generation_service import GenerationService, GenerationResult
from app.services.groq_service import GroqValidationError, GroqParseError
from app.services.validation_service import ValidationResult, GroqDiagramResponse


def test_svg_xml_reconciliation_valid():
    """Valid SVG XML passes reconciliation."""
    valid_svg = '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100"/></svg>'
    ok, err = GenerationService._validate_svg_xml(valid_svg)
    assert ok is True
    assert err == ""


def test_svg_xml_reconciliation_invalid_xml():
    """Malformed SVG XML fails reconciliation."""
    invalid_svg = '<svg xmlns="http://www.w3.org/2000/svg" width="100"><unclosed_tag>some text content</svg>'
    ok, err = GenerationService._validate_svg_xml(invalid_svg)
    assert ok is False
    assert "parse error" in err.lower()


def test_svg_xml_reconciliation_empty():
    """Empty or tiny string fails reconciliation threshold."""
    ok, err = GenerationService._validate_svg_xml("   ")
    assert ok is False
    assert "threshold" in err.lower()


def test_auto_repair_loop_successful_on_attempt_1():
    """Simulate Attempt 0 failing validation, but Attempt 1 repair succeeding."""
    service = GenerationService()

    valid_dict = {
        "diagram_type": "flowchart",
        "nodes": [{"id": "n1", "label": "Start", "type": "generic"}, {"id": "n2", "label": "End", "type": "generic"}],
        "edges": [{"id": "e1", "source": "n1", "target": "n2", "label": "", "type": "generic"}],
        "attributes": {"title": "Fixed Flowchart", "description": "Auto repaired", "allows_disconnected": False, "direction": "auto"}
    }
    repaired_model = GroqDiagramResponse.model_validate(valid_dict)
    valid_val_result = ValidationResult(is_valid=True, validated_model=repaired_model)

    failed_val_result = ValidationResult(is_valid=False, errors=["[Pydantic] edge 'e1': missing source"], layer="pydantic")

    with patch("app.services.generation_service.groq_service") as mock_groq, \
         patch("app.services.generation_service.rendering_service") as mock_render, \
         patch("app.services.generation_service.complexity_service") as mock_comp:

        # Attempt 0 raises GroqValidationError, Attempt 1 returns valid_val_result
        mock_groq.generate_diagram_json.side_effect = GroqValidationError("Failed layer 1", failed_val_result)
        mock_groq.repair_diagram_json.return_value = valid_val_result

        # Mock complexity & rendering
        mock_comp.compute_from_groq_response.return_value = MagicMock(exceeds_ceiling=False, score=1.5, rejection_reason=None)
        mock_render.render_diagram.return_value = MagicMock(
            diagram_type="flowchart",
            renderer="kroki",
            dsl_code="graph TD; n1-->n2;",
            svg_content='<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect/></svg>'
        )

        res = service._generate_fresh(
            request_id="req-123",
            prompt="draw a flowchart",
            preprocessed_prompt="draw a flowchart",
            spacy_enabled=False,
            candidates_count=0
        )

        assert res.status == "auto_repaired"
        assert res.is_success is True
        assert mock_groq.repair_diagram_json.call_count == 1


def test_auto_repair_loop_budget_exhausted():
    """Simulate all 2 repair attempts failing, resulting in status='failed_validation'."""
    service = GenerationService()
    failed_val_result = ValidationResult(is_valid=False, errors=["Orphan edge detected"], layer="graph")

    with patch("app.services.generation_service.groq_service") as mock_groq:
        mock_groq.generate_diagram_json.side_effect = GroqValidationError("Failed graph layer", failed_val_result)
        mock_groq.repair_diagram_json.side_effect = GroqValidationError("Failed graph layer repair", failed_val_result)

        res = service._generate_fresh(
            request_id="req-456",
            prompt="draw broken architecture",
            preprocessed_prompt="draw broken architecture",
            spacy_enabled=False,
            candidates_count=0
        )

        assert res.status == "failed_validation"
        assert res.is_success is False
        assert "after 2 repair attempts" in res.rejection_reason
        assert mock_groq.repair_diagram_json.call_count == 2
