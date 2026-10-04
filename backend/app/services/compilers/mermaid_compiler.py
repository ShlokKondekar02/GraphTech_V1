"""
Mermaid AST -> DSL Compiler (Sprint 3).

Compiles structured JSON into valid Mermaid diagram syntax:
- Flowcharts (flowchart LR / flowchart TB)
- Sequence Diagrams (sequenceDiagram)
"""

from typing import Any, Dict, List
from app.services.compilers.base import BaseCompiler


class MermaidCompiler(BaseCompiler):
    """Deterministic compiler targeting Mermaid syntax."""

    def compile(self, structured_json: Dict[str, Any]) -> str:
        diagram_type = str(structured_json.get("diagram_type", "flowchart")).lower()
        if diagram_type == "sequence":
            return self._compile_sequence(structured_json)
        return self._compile_flowchart(structured_json)

    def _compile_flowchart(self, data: Dict[str, Any]) -> str:
        attributes = data.get("attributes", {})
        direction = self.get_direction(attributes, default="LR")

        lines: List[str] = [f"flowchart {direction}"]

        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        # Nodes
        for node in nodes:
            raw_id = node.get("id", "")
            node_id = self.clean_id(raw_id)
            label = self.clean_label(node.get("label", raw_id))
            # Escape characters that break Mermaid labels
            safe_label = label.replace('"', '#quot;').replace("[", "(").replace("]", ")")
            node_type = str(node.get("type", "generic")).lower()

            if node_type in ("database", "datastore", "db", "storage"):
                lines.append(f'    {node_id}[("{safe_label}")]')
            elif node_type in ("decision", "condition", "gateway"):
                lines.append(f'    {node_id}{{"{safe_label}"}}')
            elif node_type in ("queue", "topic", "stream", "message_broker"):
                lines.append(f'    {node_id}[/"{safe_label}"/]')
            elif node_type in ("actor", "user", "client"):
                lines.append(f'    {node_id}(["{safe_label}"])')
            else:
                lines.append(f'    {node_id}["{safe_label}"]')

        # Edges
        for edge in edges:
            source = self.clean_id(edge.get("source", ""))
            target = self.clean_id(edge.get("target", ""))
            label = self.clean_label(edge.get("label", ""))
            edge_type = str(edge.get("type", "calls")).lower()

            arrow = "-->"
            if "async" in edge_type or "event" in edge_type or "pubsub" in edge_type or "dotted" in edge_type:
                arrow = "-.->"
            elif "thick" in edge_type or "sync" in edge_type:
                arrow = "==>"

            if label:
                safe_label = label.replace('"', '#quot;').replace("|", " ")
                lines.append(f'    {source} {arrow}|"{safe_label}"| {target}')
            else:
                lines.append(f"    {source} {arrow} {target}")

        return "\n".join(lines)

    def _compile_sequence(self, data: Dict[str, Any]) -> str:
        lines: List[str] = ["sequenceDiagram", "    autonumber"]

        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        # Participants
        for node in nodes:
            raw_id = node.get("id", "")
            node_id = self.clean_id(raw_id)
            label = self.clean_label(node.get("label", raw_id)).replace('"', "")
            node_type = str(node.get("type", "generic")).lower()

            keyword = "actor" if node_type in ("actor", "user", "client") else "participant"
            lines.append(f'    {keyword} {node_id} as {label}')

        # Messages (edges)
        for edge in edges:
            source = self.clean_id(edge.get("source", ""))
            target = self.clean_id(edge.get("target", ""))
            label = self.clean_label(edge.get("label", "")) or "call"
            edge_type = str(edge.get("type", "calls")).lower()

            safe_label = label.replace("\n", " ").replace(":", "-")

            if "reply" in edge_type or "response" in edge_type or "return" in edge_type:
                lines.append(f"    {source}-->>{target}: {safe_label}")
            else:
                lines.append(f"    {source}->>{target}: {safe_label}")

        return "\n".join(lines)
