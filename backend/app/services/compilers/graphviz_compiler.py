"""
Graphviz DOT AST -> DSL Compiler (Sprint 3).

Compiles structured JSON into valid Graphviz DOT diagram syntax:
- Architecture Diagrams
- Network Topologies
- State Machines
- Generic Graph Visualizations
"""

from typing import Any, Dict, List
from app.services.compilers.base import BaseCompiler


class GraphvizCompiler(BaseCompiler):
    """Deterministic compiler targeting Graphviz DOT syntax."""

    def compile(self, structured_json: Dict[str, Any]) -> str:
        diagram_type = str(structured_json.get("diagram_type", "architecture")).lower()
        if diagram_type == "state_machine":
            return self._compile_state_machine(structured_json)
        return self._compile_architecture(structured_json)

    def _compile_architecture(self, data: Dict[str, Any]) -> str:
        attributes = data.get("attributes", {})
        direction = self.get_direction(attributes, default="LR")

        lines: List[str] = [
            "digraph Architecture {",
            f'  graph [rankdir="{direction}", bgcolor="transparent", fontname="Helvetica, Arial, sans-serif", compound=true, pad="0.3", nodesep="0.5", ranksep="0.6"];',
            '  node [shape="box", style="rounded,filled", fillcolor="#F8FAFC", color="#94A3B8", fontname="Helvetica, Arial, sans-serif", fontsize="11", fontcolor="#0F172A", margin="0.2,0.12", penwidth=1.2];',
            '  edge [fontname="Helvetica, Arial, sans-serif", fontsize="10", color="#64748B", fontcolor="#475569", arrowsize=0.8, penwidth=1.1];',
            "",
        ]

        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        # Nodes
        for node in nodes:
            raw_id = node.get("id", "")
            node_id = self.clean_id(raw_id)
            label = self.clean_label(node.get("label", raw_id))
            node_type = str(node.get("type", "service")).lower()

            safe_label = label.replace('\\', '\\\\').replace('"', '\\"')

            # Styling variants based on node semantics
            if node_type in ("database", "datastore", "db", "storage"):
                lines.append(f'  {node_id} [label="{safe_label}\\n[Database]", shape="cylinder", fillcolor="#EFF6FF", color="#3B82F6"];')
            elif node_type in ("cache", "redis", "memcached"):
                lines.append(f'  {node_id} [label="{safe_label}\\n[Cache]", shape="cylinder", fillcolor="#FEF2F2", color="#EF4444"];')
            elif node_type in ("queue", "topic", "kafka", "rabbitmq"):
                lines.append(f'  {node_id} [label="{safe_label}\\n[Queue]", shape="cds", fillcolor="#FFFBEB", color="#F59E0B"];')
            elif node_type in ("gateway", "lb", "load_balancer", "proxy"):
                lines.append(f'  {node_id} [label="{safe_label}\\n[Gateway]", shape="hexagon", fillcolor="#F0FDF4", color="#10B981"];')
            elif node_type in ("actor", "user", "client"):
                lines.append(f'  {node_id} [label="{safe_label}", shape="ellipse", fillcolor="#F1F5F9", color="#64748B"];')
            else:
                lines.append(f'  {node_id} [label="{safe_label}"];')

        lines.append("")

        # Edges
        for edge in edges:
            source = self.clean_id(edge.get("source", ""))
            target = self.clean_id(edge.get("target", ""))
            label = self.clean_label(edge.get("label", ""))
            edge_type = str(edge.get("type", "calls")).lower()

            edge_attrs = []
            if label:
                safe_label = label.replace('\\', '\\\\').replace('"', '\\"')
                edge_attrs.append(f'label="{safe_label}"')

            if "async" in edge_type or "event" in edge_type or "pubsub" in edge_type:
                edge_attrs.append('style="dashed"')
            elif "bidirectional" in edge_type or "two_way" in edge_type:
                edge_attrs.append('dir="both"')

            attr_str = f" [{', '.join(edge_attrs)}]" if edge_attrs else ""
            lines.append(f"  {source} -> {target}{attr_str};")

        lines.append("}")
        return "\n".join(lines)

    def _compile_state_machine(self, data: Dict[str, Any]) -> str:
        attributes = data.get("attributes", {})
        direction = self.get_direction(attributes, default="LR")

        lines: List[str] = [
            "digraph StateMachine {",
            f'  graph [rankdir="{direction}", bgcolor="transparent", fontname="Helvetica, Arial, sans-serif"];',
            '  node [shape="circle", style="rounded,filled", fillcolor="#F8FAFC", color="#475569", fontname="Helvetica, Arial, sans-serif", fontsize="10", fontcolor="#0F172A", penwidth=1.2];',
            '  edge [fontname="Helvetica, Arial, sans-serif", fontsize="9", color="#64748B", fontcolor="#334155", arrowsize=0.8];',
            "",
        ]

        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        for node in nodes:
            raw_id = node.get("id", "")
            node_id = self.clean_id(raw_id)
            label = self.clean_label(node.get("label", raw_id))
            node_type = str(node.get("type", "state")).lower()
            safe_label = label.replace('\\', '\\\\').replace('"', '\\"')

            if "initial" in node_type or "start" in node_type or "begin" in safe_label.lower():
                lines.append(f'  {node_id} [label="{safe_label}", shape="circle", fillcolor="#D1FAE5", color="#059669"];')
            elif "terminal" in node_type or "final" in node_type or "end" in safe_label.lower():
                lines.append(f'  {node_id} [label="{safe_label}", shape="doublecircle", fillcolor="#FEE2E2", color="#DC2626"];')
            else:
                lines.append(f'  {node_id} [label="{safe_label}", shape="rect", style="rounded,filled", fillcolor="#F1F5F9"];')

        lines.append("")

        for edge in edges:
            source = self.clean_id(edge.get("source", ""))
            target = self.clean_id(edge.get("target", ""))
            label = self.clean_label(edge.get("label", ""))

            if label:
                safe_label = label.replace('\\', '\\\\').replace('"', '\\"')
                lines.append(f'  {source} -> {target} [label="{safe_label}"];')
            else:
                lines.append(f"  {source} -> {target};")

        lines.append("}")
        return "\n".join(lines)
