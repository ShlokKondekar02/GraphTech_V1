"""
Compilers package: AST -> DSL deterministic compilers (Sprint 3).
"""

from typing import Dict
from app.services.compilers.base import BaseCompiler
from app.services.compilers.mermaid_compiler import MermaidCompiler
from app.services.compilers.plantuml_compiler import PlantUMLCompiler
from app.services.compilers.graphviz_compiler import GraphvizCompiler
from app.services.compilers.erd_compiler import ErdCompiler
from app.services.compilers.nwdiag_compiler import NwdiagCompiler

COMPILER_REGISTRY: Dict[str, BaseCompiler] = {
    "mermaid": MermaidCompiler(),
    "plantuml": PlantUMLCompiler(),
    "graphviz": GraphvizCompiler(),
    "erd": ErdCompiler(),
    "nwdiag": NwdiagCompiler(),
}


def get_compiler(renderer: str) -> BaseCompiler:
    """Retrieve compiler instance by renderer name."""
    renderer_key = str(renderer).lower().strip()
    if renderer_key in COMPILER_REGISTRY:
        return COMPILER_REGISTRY[renderer_key]
    # Default to Graphviz for unknown renderers
    return COMPILER_REGISTRY["graphviz"]


__all__ = [
    "BaseCompiler",
    "MermaidCompiler",
    "PlantUMLCompiler",
    "GraphvizCompiler",
    "ErdCompiler",
    "NwdiagCompiler",
    "COMPILER_REGISTRY",
    "get_compiler",
]
