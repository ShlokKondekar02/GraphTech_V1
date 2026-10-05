"""
Output Validator Service -- Sprint 4.

Validates rendered diagram outputs (SVG markup) across two primary dimensions:
  1. XML & Markup Integrity:
     - Ensures valid, well-formed SVG XML.
     - Detects embedded Kroki/engine error strings (e.g., "Syntax error", "Error 404").
     - Confirms non-empty graphical structure (<g>, <path>, <rect>, <text>, etc.).

  2. Semantic Reconciliation (AST vs Rendered SVG):
     - Extracts node labels from the validated Pydantic AST (GroqDiagramResponse).
     - Extracts text elements from the SVG XML tree.
     - Verifies that key AST node labels are present in the rendered output,
       detecting cases where renderer silently dropped elements.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Common Kroki and compiler error signatures rendered inside SVGs or returned as text
ERROR_SIGNATURES = [
    "syntax error",
    "syntaxerror",
    "parse error",
    "parseerror",
    "error 404",
    "cannot compile",
    "compilation failed",
    "unknown diagram type",
    "diagram error",
    "rendering failed",
]


@dataclass
class OutputValidationResult:
    """
    Detailed result of output validation.
    """

    is_valid: bool
    xml_integrity: bool
    kroki_error_detected: bool
    semantic_reconciliation: bool
    total_expected_labels: int = 0
    reconciled_labels_count: int = 0
    missing_labels: List[str] = field(default_factory=list)
    error_message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "xml_integrity": self.xml_integrity,
            "kroki_error_detected": self.kroki_error_detected,
            "semantic_reconciliation": self.semantic_reconciliation,
            "total_expected_labels": self.total_expected_labels,
            "reconciled_labels_count": self.reconciled_labels_count,
            "missing_labels": self.missing_labels,
            "error_message": self.error_message,
        }


class OutputValidatorService:
    """
    Validates SVG rendered artifacts against XML standards and AST semantic models.
    """

    def validate_svg(
        self,
        svg_content: Optional[str],
        structured_json: Optional[Dict[str, Any]] = None,
        min_label_match_ratio: float = 0.5,
    ) -> OutputValidationResult:
        """
        Validate SVG content string for XML integrity, Kroki errors, and semantic AST reconciliation.
        """
        if not svg_content or len(svg_content.strip()) < 50:
            return OutputValidationResult(
                is_valid=False,
                xml_integrity=False,
                kroki_error_detected=False,
                semantic_reconciliation=False,
                error_message="SVG content is empty or below minimum size threshold (50 bytes)",
            )

        # 1. Kroki Embedded Error Detection
        lower_svg = svg_content.lower()
        for err_sig in ERROR_SIGNATURES:
            if err_sig in lower_svg:
                logger.warning("Embedded Kroki error signature found: '%s'", err_sig)
                return OutputValidationResult(
                    is_valid=False,
                    xml_integrity=True,
                    kroki_error_detected=True,
                    semantic_reconciliation=False,
                    error_message=f"Embedded Kroki error detected: contains '{err_sig}'",
                )

        # 2. XML Integrity & Parsing
        try:
            root = ET.fromstring(svg_content)
        except ET.ParseError as exc:
            logger.warning("SVG XML parse error: %s", exc)
            return OutputValidationResult(
                is_valid=False,
                xml_integrity=False,
                kroki_error_detected=False,
                semantic_reconciliation=False,
                error_message=f"SVG XML parse error: {exc}",
            )

        # Confirm top-level SVG tag
        tag_name = root.tag.lower()
        if not tag_name.endswith("svg"):
            return OutputValidationResult(
                is_valid=False,
                xml_integrity=False,
                kroki_error_detected=False,
                semantic_reconciliation=False,
                error_message=f"Root XML element must be <svg>, found <{root.tag}>",
            )

        # Confirm non-empty graphical element structure
        has_elements = False
        for elem in root.iter():
            local_tag = elem.tag.split("}")[-1].lower()
            if local_tag in {"path", "rect", "circle", "ellipse", "polygon", "polyline", "line", "text", "g", "use"}:
                has_elements = True
                break

        if not has_elements:
            return OutputValidationResult(
                is_valid=False,
                xml_integrity=False,
                kroki_error_detected=False,
                semantic_reconciliation=False,
                error_message="SVG XML contains no renderable graphical elements",
            )

        # 3. Semantic Reconciliation (AST Node Label Verification)
        if not structured_json:
            # If no AST provided, XML integrity check is sufficient
            return OutputValidationResult(
                is_valid=True,
                xml_integrity=True,
                kroki_error_detected=False,
                semantic_reconciliation=True,
                error_message="",
            )

        # Extract AST expected node labels
        expected_labels: Set[str] = set()
        nodes = structured_json.get("nodes", [])
        for node in nodes:
            label = str(node.get("label", "") or "").strip()
            if label and len(label) > 1 and label.lower() not in {"node", "start", "end", "process"}:
                expected_labels.add(label)

        if not expected_labels:
            return OutputValidationResult(
                is_valid=True,
                xml_integrity=True,
                kroki_error_detected=False,
                semantic_reconciliation=True,
                error_message="",
            )

        # Extract text content from SVG XML elements
        extracted_texts: Set[str] = set()
        for elem in root.iter():
            if elem.text and elem.text.strip():
                extracted_texts.add(elem.text.strip().lower())
            if elem.tail and elem.tail.strip():
                extracted_texts.add(elem.tail.strip().lower())

        # Also search raw SVG string for label substring presence (handles nested tspan / HTML entity encoding)
        raw_lower_svg = svg_content.lower()

        reconciled_labels: List[str] = []
        missing_labels: List[str] = []

        for expected_lbl in expected_labels:
            lbl_lower = expected_lbl.lower()
            # Direct match in extracted text elements or substring match in SVG body
            found = any(lbl_lower in text for text in extracted_texts) or (lbl_lower in raw_lower_svg)
            if found:
                reconciled_labels.append(expected_lbl)
            else:
                missing_labels.append(expected_lbl)

        total_expected = len(expected_labels)
        reconciled_count = len(reconciled_labels)
        match_ratio = reconciled_count / total_expected if total_expected > 0 else 1.0

        is_reconciled = match_ratio >= min_label_match_ratio

        if not is_reconciled:
            logger.warning(
                "Semantic reconciliation failed: match_ratio=%.2f < threshold=%.2f. Missing labels: %s",
                match_ratio,
                min_label_match_ratio,
                missing_labels,
            )
            return OutputValidationResult(
                is_valid=False,
                xml_integrity=True,
                kroki_error_detected=False,
                semantic_reconciliation=False,
                total_expected_labels=total_expected,
                reconciled_labels_count=reconciled_count,
                missing_labels=missing_labels,
                error_message=f"Semantic reconciliation failed ({reconciled_count}/{total_expected} labels matched). Missing: {missing_labels[:3]}",
                details={
                    "match_ratio": match_ratio,
                    "reconciled": reconciled_labels,
                    "missing": missing_labels,
                },
            )

        return OutputValidationResult(
            is_valid=True,
            xml_integrity=True,
            kroki_error_detected=False,
            semantic_reconciliation=True,
            total_expected_labels=total_expected,
            reconciled_labels_count=reconciled_count,
            missing_labels=[],
            error_message="",
            details={
                "match_ratio": match_ratio,
                "reconciled": reconciled_labels,
            },
        )


# Singleton instance
output_validator_service = OutputValidatorService()
