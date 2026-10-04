"""
Kroki Native nwdiag AST -> DSL Compiler (Sprint 3).

Compiles structured JSON into nwdiag network topology syntax for Kroki's native /nwdiag/svg renderer:
  nwdiag {
    network network_name {
      node1;
      node2;
    }
  }
"""

from typing import Any, Dict, List
from app.services.compilers.base import BaseCompiler


class NwdiagCompiler(BaseCompiler):
    """Deterministic compiler targeting Kroki's native nwdiag network topology format."""

    def compile(self, structured_json: Dict[str, Any]) -> str:
        nodes = structured_json.get("nodes", [])
        edges = structured_json.get("edges", [])

        lines: List[str] = ["nwdiag {"]

        # Group nodes into network tiers based on type or metadata
        dmz_nodes: List[str] = []
        app_nodes: List[str] = []
        data_nodes: List[str] = []

        for node in nodes:
            raw_id = node.get("id", "")
            node_id = self.clean_id(raw_id)
            node_type = str(node.get("type", "")).lower()

            if node_type in ("gateway", "lb", "load_balancer", "proxy", "firewall", "router", "client"):
                dmz_nodes.append(node_id)
            elif node_type in ("database", "datastore", "db", "storage", "cache", "redis"):
                data_nodes.append(node_id)
            else:
                app_nodes.append(node_id)

        # Fallback if unassigned
        if not dmz_nodes and not data_nodes:
            app_nodes = [self.clean_id(n.get("id", "")) for n in nodes]

        if dmz_nodes:
            lines.append("  network external_dmz {")
            lines.append('    address = "10.0.1.x/24"')
            for nid in dmz_nodes:
                lines.append(f"    {nid};")
            lines.append("  }")

        if app_nodes:
            lines.append("  network application_subnet {")
            lines.append('    address = "10.0.2.x/24"')
            for nid in app_nodes:
                lines.append(f"    {nid};")
            lines.append("  }")

        if data_nodes:
            lines.append("  network database_subnet {")
            lines.append('    address = "10.0.3.x/24"')
            for nid in data_nodes:
                lines.append(f"    {nid};")
            lines.append("  }")

        lines.append("}")
        return "\n".join(lines)
