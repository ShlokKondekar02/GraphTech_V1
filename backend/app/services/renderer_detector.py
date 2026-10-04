"""
Diagram-Type Detection and Renderer Selection (Sprint 3).

Maps validated structured JSON to:
  1. Refined diagram type
  2. Optimal Kroki renderer (erd, nwdiag, mermaid, plantuml, graphviz)
"""

from typing import Any, Dict, Tuple


# Explicit mapping from diagram type to optimal Kroki renderer format
DIAGRAM_TYPE_TO_RENDERER: Dict[str, str] = {
    # Kroki native ERD engine
    "erd": "erd",
    # Kroki native nwdiag network engine
    "network": "nwdiag",
    # Mermaid
    "flowchart": "mermaid",
    "sequence": "mermaid",
    "mindmap": "mermaid",
    "gantt": "mermaid",
    # PlantUML
    "class": "plantuml",
    # Graphviz
    "architecture": "graphviz",
    "state_machine": "graphviz",
    "generic": "graphviz",
}


class RendererDetector:
    """Detects/refines diagram type and maps it to the target Kroki renderer."""

    @staticmethod
    def detect_diagram_type(structured_json: Dict[str, Any]) -> str:
        """
        Inspect structured JSON to detect or refine diagram type.
        Uses structural heuristic rules when diagram_type is 'generic' or missing.
        """
        raw_type = str(structured_json.get("diagram_type", "")).strip().lower()
        if raw_type and raw_type != "generic":
            return raw_type

        nodes = structured_json.get("nodes", [])
        edges = structured_json.get("edges", [])

        node_types = {str(n.get("type", "")).lower() for n in nodes}
        edge_types = {str(e.get("type", "")).lower() for e in edges}

        # Rule 1: Entity-Relationship
        if any(t in node_types for t in ("entity", "table", "schema")) or any(
            t in edge_types for t in ("has_many", "belongs_to", "one_to_many", "one_to_one", "many_to_many")
        ):
            return "erd"

        # Rule 2: Network Topologies
        if any(t in node_types for t in ("subnet", "router", "firewall", "switch", "ip")) or any(
            t in edge_types for t in ("subnet_of", "routes_to", "firewall_rule")
        ):
            return "network"

        # Rule 3: Sequence / Interaction
        if any(t in node_types for t in ("actor", "lifeline")) or any(
            t in edge_types for t in ("calls", "reply", "response", "message", "sync_call")
        ):
            return "sequence"

        # Rule 4: State Machine
        if any(t in node_types for t in ("state", "initial_state", "terminal_state")) or any(
            t in edge_types for t in ("transitions_to", "transition", "event")
        ):
            return "state_machine"

        # Rule 5: Class / OOP
        if any(t in node_types for t in ("class", "interface")) or any(
            t in edge_types for t in ("inherits", "implements", "extends")
        ):
            return "class"

        # Rule 6: Architecture / Cloud / Services
        if any(t in node_types for t in ("service", "database", "queue", "gateway", "cache")):
            return "architecture"

        # Default fallback
        return raw_type or "flowchart"

    @classmethod
    def get_renderer_for_type(cls, diagram_type: str) -> str:
        """Get optimal Kroki renderer format for a given diagram type."""
        normalized = str(diagram_type).lower().strip()
        return DIAGRAM_TYPE_TO_RENDERER.get(normalized, "graphviz")

    @classmethod
    def select_renderer(cls, structured_json: Dict[str, Any]) -> Tuple[str, str]:
        """
        Returns (detected_diagram_type, target_renderer).
        """
        dtype = cls.detect_diagram_type(structured_json)
        renderer = cls.get_renderer_for_type(dtype)
        return dtype, renderer


renderer_detector = RendererDetector()
