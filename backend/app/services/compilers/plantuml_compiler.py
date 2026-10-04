"""
PlantUML AST -> DSL Compiler (Sprint 3).

Compiles structured JSON into valid PlantUML diagram syntax:
- Entity-Relationship Diagrams (ERD)
- Class Diagrams
"""

from typing import Any, Dict, List
from app.services.compilers.base import BaseCompiler


class PlantUMLCompiler(BaseCompiler):
    """Deterministic compiler targeting PlantUML syntax."""

    def compile(self, structured_json: Dict[str, Any]) -> str:
        diagram_type = str(structured_json.get("diagram_type", "erd")).lower()
        if diagram_type == "class":
            return self._compile_class(structured_json)
        return self._compile_erd(structured_json)

    def _compile_erd(self, data: Dict[str, Any]) -> str:
        lines: List[str] = [
            "@startuml",
            "!theme plain",
            "hide circle",
            "skinparam roundcorner 4",
            "skinparam linetype ortho",
        ]

        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        # Entities
        for node in nodes:
            raw_id = node.get("id", "")
            node_id = self.clean_id(raw_id)
            label = self.clean_label(node.get("label", raw_id))
            safe_label = label.replace('"', "").replace("\n", " ")

            lines.append(f"entity {node_id} {{")
            lines.append("  * id : identifier")
            lines.append("  --")
            lines.append(f"  title : {safe_label}")
            lines.append("}")

        # Relationships
        for edge in edges:
            source = self.clean_id(edge.get("source", ""))
            target = self.clean_id(edge.get("target", ""))
            label = self.clean_label(edge.get("label", ""))
            edge_type = str(edge.get("type", "rel")).lower()

            rel_operator = "}o--||"
            if "one_to_many" in edge_type or "has_many" in edge_type or "places" in edge_type or "contains" in edge_type:
                rel_operator = "||--o{"
            elif "many_to_many" in edge_type:
                rel_operator = "}o--o{"
            elif "one_to_one" in edge_type:
                rel_operator = "||--||"

            if label:
                safe_label = label.replace('"', "")
                lines.append(f'{source} {rel_operator} {target} : "{safe_label}"')
            else:
                lines.append(f"{source} {rel_operator} {target}")

        lines.append("@enduml")
        return "\n".join(lines)

    def _compile_class(self, data: Dict[str, Any]) -> str:
        lines: List[str] = [
            "@startuml",
            "!theme plain",
            "skinparam classAttributeIconSize 0",
        ]

        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        # Classes
        for node in nodes:
            raw_id = node.get("id", "")
            node_id = self.clean_id(raw_id)
            label = self.clean_label(node.get("label", raw_id))
            safe_label = label.replace('"', "").replace("\n", " ")

            lines.append(f"class {node_id} {{")
            lines.append(f"  + name: {safe_label}")
            lines.append("}")

        # Relationships
        for edge in edges:
            source = self.clean_id(edge.get("source", ""))
            target = self.clean_id(edge.get("target", ""))
            label = self.clean_label(edge.get("label", ""))
            edge_type = str(edge.get("type", "associates")).lower()

            arrow = "-->"
            if "inherit" in edge_type or "extends" in edge_type:
                arrow = "--|>"
            elif "implements" in edge_type:
                arrow = "..|>"
            elif "composition" in edge_type:
                arrow = "*--"
            elif "aggregation" in edge_type:
                arrow = "o--"

            if label:
                safe_label = label.replace('"', "")
                lines.append(f'{source} {arrow} {target} : "{safe_label}"')
            else:
                lines.append(f"{source} {arrow} {target}")

        lines.append("@enduml")
        return "\n".join(lines)
