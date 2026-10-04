"""
Kroki Native ERD AST -> DSL Compiler (Sprint 3).

Compiles structured JSON into BurntSushi ERD syntax for Kroki's native /erd/svg renderer:
  [Entity]
  *primary_key
  +foreign_key
  column_name

  Entity1 1--* Entity2
"""

from typing import Any, Dict, List
from app.services.compilers.base import BaseCompiler


class ErdCompiler(BaseCompiler):
    """Deterministic compiler targeting Kroki's native ERD format."""

    def compile(self, structured_json: Dict[str, Any]) -> str:
        lines: List[str] = []

        nodes = structured_json.get("nodes", [])
        edges = structured_json.get("edges", [])

        # Entities
        for node in nodes:
            raw_id = node.get("id", "")
            node_id = self.clean_id(raw_id)
            label = self.clean_label(node.get("label", raw_id))
            metadata = node.get("metadata") or {}

            lines.append(f"[{node_id}]")

            # Check if explicit attributes list is present in metadata
            attributes_list = metadata.get("attributes") or metadata.get("fields")
            if attributes_list and isinstance(attributes_list, list):
                for attr in attributes_list:
                    attr_str = str(attr).strip()
                    if "(pk)" in attr_str.lower() or "pk" in attr_str.lower() or attr_str == "id":
                        clean_attr = attr_str.split("(")[0].strip()
                        lines.append(f"  *{clean_attr}")
                    elif "(fk)" in attr_str.lower() or "fk" in attr_str.lower() or "_id" in attr_str.lower():
                        clean_attr = attr_str.split("(")[0].strip()
                        lines.append(f"  +{clean_attr}")
                    else:
                        clean_attr = attr_str.split("(")[0].strip()
                        lines.append(f"  {clean_attr}")
            else:
                # Intelligently infer default primary key and attributes
                lines.append("  *id")
                safe_name = label.lower().replace(" ", "_")
                if safe_name != node_id and safe_name != "id":
                    lines.append(f"  {safe_name}_name")
                lines.append("  created_at")

            lines.append("")

        # Relationships
        for edge in edges:
            source = self.clean_id(edge.get("source", ""))
            target = self.clean_id(edge.get("target", ""))
            edge_type = str(edge.get("type", "rel")).lower()

            cardinality = "1--*"
            if "one_to_one" in edge_type or "has_one" in edge_type:
                cardinality = "1--1"
            elif "many_to_many" in edge_type:
                cardinality = "*--*"
            elif "one_to_many" in edge_type or "has_many" in edge_type or "places" in edge_type or "contains" in edge_type:
                cardinality = "1--*"
            elif "optional" in edge_type or "zero_to_many" in edge_type:
                cardinality = "?--*"

            lines.append(f"{source} {cardinality} {target}")

        return "\n".join(lines).strip()
