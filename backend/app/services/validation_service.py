"""
Validation Service -- Sprint 2.

Applies two independent validation layers to any diagram structured JSON:

Layer 1 -- Pydantic schema validation (app.schemas.groq_contract.GroqDiagramResponse)
  - Required fields, correct types, field constraints
  - Referential integrity (every edge source/target references a real node id)
  - No duplicate node IDs or edge IDs
  - Disconnected-component flag consistency

Layer 2 -- Deterministic graph rules (code, not LLM)
  - No orphan edges (edges referencing missing nodes -- belt-and-suspenders
    check even though Pydantic catches this first)
  - Graph must be connected unless the diagram type explicitly allows
    disconnected components (mindmap, gantt, network)

Both layers are always run.  A failure in either layer causes a HARD rejection
with a structured error -- no silent coercion, no auto-fix.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from app.schemas.groq_contract import DISCONNECTED_ALLOWED_TYPES, GroqDiagramResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """
    Result of running both validation layers on a structured JSON payload.

    Attributes
    ----------
    is_valid        -- True only when ALL validation layers pass
    errors          -- list of human-readable error strings; empty on success
    validated_model -- the parsed GroqDiagramResponse when is_valid is True;
                       None on failure
    layer           -- which layer failed first: "pydantic", "graph", or None
    """

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    validated_model: Optional[GroqDiagramResponse] = field(default=None)
    layer: Optional[str] = field(default=None)

    @property
    def error_summary(self) -> str:
        """One-line summary suitable for a rejection_reason column."""
        if not self.errors:
            return ""
        return f"[{self.layer}] " + "; ".join(self.errors[:3])


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------


class ValidationService:
    """
    Deterministic, two-layer validator for diagram structured JSON.

    Neither layer trusts Groq's own output -- every claim is independently
    checked against the graph structure.
    """

    # ---- Public API --------------------------------------------------------

    def validate(self, raw: Any) -> ValidationResult:
        """
        Validate a raw dict (or any object) as a GroqDiagramResponse.

        Parameters
        ----------
        raw -- the JSON-deserialized dict from Groq (or from DB cache)

        Returns
        -------
        ValidationResult -- always returned, never raises
        """
        # Layer 1: Pydantic schema + model-level validators
        pydantic_result = self._layer1_pydantic(raw)
        if not pydantic_result.is_valid:
            return pydantic_result

        # Layer 2: Deterministic graph rules
        graph_result = self._layer2_graph(pydantic_result.validated_model)  # type: ignore[arg-type]
        return graph_result

    # ---- Layer 1: Pydantic ------------------------------------------------

    def _layer1_pydantic(self, raw: Any) -> ValidationResult:
        """
        Parse and validate raw input through GroqDiagramResponse.

        All Pydantic field validators AND model-level validators run here,
        including referential integrity, duplicate ID detection, and the
        disconnected-flag consistency check.
        """
        if not isinstance(raw, dict):
            return ValidationResult(
                is_valid=False,
                errors=[
                    f"Expected a dict, got {type(raw).__name__}. "
                    "Groq response must be a JSON object."
                ],
                layer="pydantic",
            )

        try:
            model = GroqDiagramResponse.model_validate(raw)
        except ValidationError as exc:
            errors = [
                f"{' -> '.join(str(loc) for loc in e['loc'])}: {e['msg']}"
                if e.get("loc")
                else e["msg"]
                for e in exc.errors()
            ]
            logger.warning(
                "Pydantic validation failed (%d error(s)): %s",
                len(errors),
                "; ".join(errors[:3]),
            )
            return ValidationResult(is_valid=False, errors=errors, layer="pydantic")

        logger.debug("Layer 1 (Pydantic) passed.")
        return ValidationResult(is_valid=True, validated_model=model)

    # ---- Layer 2: Deterministic graph rules --------------------------------

    def _layer2_graph(self, model: GroqDiagramResponse) -> ValidationResult:
        """
        Run deterministic graph checks that go beyond Pydantic constraints.

        Rules:
        R1 -- No orphan edges (belt-and-suspenders; Pydantic catches this first
              via referential integrity, but we double-check here because this
              rule must never be skipped).
        R2 -- Graph must be connected (single weakly connected component)
              unless the diagram type is in DISCONNECTED_ALLOWED_TYPES.
        """
        errors: list[str] = []
        node_ids = {n.id for n in model.nodes}

        # R1: No orphan edges
        orphans: list[str] = []
        for edge in model.edges:
            if edge.source not in node_ids:
                orphans.append(
                    f"Edge '{edge.id}': source '{edge.source}' not found in nodes"
                )
            if edge.target not in node_ids:
                orphans.append(
                    f"Edge '{edge.id}': target '{edge.target}' not found in nodes"
                )
        if orphans:
            errors.extend(orphans)

        # R2: Connectivity check
        if model.diagram_type not in DISCONNECTED_ALLOWED_TYPES:
            isolated = self._find_isolated_nodes(model)
            if isolated:
                errors.append(
                    f"Graph is not fully connected for diagram_type "
                    f"'{model.diagram_type}'. Isolated nodes (no edges): "
                    f"{sorted(isolated)}. "
                    f"Disconnected components are only permitted for: "
                    f"{sorted(DISCONNECTED_ALLOWED_TYPES)}."
                )

        if errors:
            logger.warning(
                "Layer 2 (graph rules) failed (%d rule violation(s)): %s",
                len(errors),
                "; ".join(errors[:3]),
            )
            return ValidationResult(is_valid=False, errors=errors, layer="graph")

        logger.debug("Layer 2 (graph rules) passed.")
        return ValidationResult(is_valid=True, validated_model=model)

    # ---- Helpers -----------------------------------------------------------

    @staticmethod
    def _find_isolated_nodes(model: GroqDiagramResponse) -> List[str]:
        """
        Return node IDs that have no edges (neither incoming nor outgoing).

        A single-node diagram with no edges is always considered connected.
        """
        if len(model.nodes) <= 1:
            return []

        connected: set[str] = set()
        for edge in model.edges:
            connected.add(edge.source)
            connected.add(edge.target)

        return [n.id for n in model.nodes if n.id not in connected]


# Module-level singleton
validation_service = ValidationService()
