"""
Rendering Service -- Sprint 3 (full implementation).

Orchestrates diagram compilation and rendering:
  1. Detects diagram type & selects optimal Kroki renderer
  2. Compiles validated structured JSON AST into clean, deterministic DSL
  3. Dispatches DSL to Kroki API to produce SVG markup
  4. Returns complete RenderResult (renderer, diagram_type, dsl_code, svg_content)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.services.compilers import get_compiler
from app.services.kroki_client import (
    KrokiClient,
    KrokiConnectionError,
    KrokiError,
    KrokiRenderError,
    KrokiTimeoutError,
    kroki_client,
)
from app.services.renderer_detector import renderer_detector

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result Dataclass
# ---------------------------------------------------------------------------


@dataclass
class RenderResult:
    """The result of diagram compilation and SVG rendering."""

    renderer: str
    diagram_type: str
    dsl_code: str
    svg_content: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "renderer": self.renderer,
            "diagram_type": self.diagram_type,
            "dsl_code": self.dsl_code,
            "svg_content": self.svg_content,
        }


# ---------------------------------------------------------------------------
# Rendering Service
# ---------------------------------------------------------------------------


class RenderingService:
    """
    Coordinates diagram compilation and rendering via Kroki.
    """

    def __init__(self, client: Optional[KrokiClient] = None):
        self.client = client or kroki_client

    def compile_dsl(self, structured_json: Dict[str, Any], renderer: str) -> str:
        """
        Compile structured JSON to DSL for a specific renderer.
        """
        compiler = get_compiler(renderer)
        return compiler.compile(structured_json)

    def render_diagram(
        self,
        structured_json: Dict[str, Any],
        preferred_renderer: Optional[str] = None,
    ) -> RenderResult:
        """
        Synchronously compile and render a diagram from structured JSON.

        Parameters
        ----------
        structured_json : Dict[str, Any]
            Validated GroqDiagramResponse dictionary.
        preferred_renderer : Optional[str]
            Override renderer selection if provided (mermaid | plantuml | graphviz).

        Returns
        -------
        RenderResult
        """
        detected_type, default_renderer = renderer_detector.select_renderer(structured_json)
        renderer = preferred_renderer or default_renderer

        # 1. Deterministic compilation AST -> DSL
        dsl_code = self.compile_dsl(structured_json, renderer)
        logger.info(
            "Compiled DSL for type=%s renderer=%s (dsl_len=%d)",
            detected_type,
            renderer,
            len(dsl_code),
        )

        # 2. Render via Kroki
        try:
            svg_content = self.client.render_sync(renderer=renderer, dsl_code=dsl_code)
        except (KrokiConnectionError, KrokiTimeoutError) as exc:
            logger.warning(
                "Kroki connection/timeout failure (%s). Generating fallback SVG.",
                exc,
            )
            svg_content = self._generate_fallback_svg(structured_json, renderer, str(exc))
        except KrokiRenderError as exc:
            logger.error("Kroki failed to render DSL: %s", exc)
            # Try fallback to graphviz or mermaid if plantuml failed, or generate fallback SVG
            svg_content = self._generate_fallback_svg(structured_json, renderer, str(exc))

        return RenderResult(
            renderer=renderer,
            diagram_type=detected_type,
            dsl_code=dsl_code,
            svg_content=svg_content,
        )

    async def render_diagram_async(
        self,
        structured_json: Dict[str, Any],
        preferred_renderer: Optional[str] = None,
    ) -> RenderResult:
        """
        Asynchronously compile and render a diagram from structured JSON.
        """
        detected_type, default_renderer = renderer_detector.select_renderer(structured_json)
        renderer = preferred_renderer or default_renderer

        dsl_code = self.compile_dsl(structured_json, renderer)

        try:
            svg_content = await self.client.render_async(renderer=renderer, dsl_code=dsl_code)
        except (KrokiConnectionError, KrokiTimeoutError) as exc:
            logger.warning("Kroki async failure (%s). Using fallback SVG.", exc)
            svg_content = self._generate_fallback_svg(structured_json, renderer, str(exc))
        except KrokiRenderError as exc:
            logger.error("Kroki async failed to render DSL: %s", exc)
            svg_content = self._generate_fallback_svg(structured_json, renderer, str(exc))

        return RenderResult(
            renderer=renderer,
            diagram_type=detected_type,
            dsl_code=dsl_code,
            svg_content=svg_content,
        )

    @staticmethod
    def _generate_fallback_svg(
        data: Dict[str, Any],
        renderer: str,
        reason: str,
    ) -> str:
        """
        Generate a clean, self-contained SVG representation when remote Kroki
        is unreachable or throws an error. Ensures the frontend never receives null SVG.
        """
        title = data.get("attributes", {}).get("title", "Architecture Diagram")
        nodes = data.get("nodes", [])
        node_count = len(nodes)
        node_items = "\n".join(
            f'<text x="40" y="{80 + i * 28}" font-family="sans-serif" font-size="13" fill="#334155">• {n.get("label", n.get("id"))} ({n.get("type", "node")})</text>'
            for i, n in enumerate(nodes[:12])
        )

        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 450" width="100%" height="100%">
  <rect width="100%" height="100%" fill="#F8FAFC" rx="10" stroke="#E2E8F0" stroke-width="2"/>
  <text x="30" y="45" font-family="sans-serif" font-size="18" font-weight="bold" fill="#0F172A">{title}</text>
  <rect x="30" y="55" width="640" height="1" fill="#E2E8F0"/>
  {node_items}
  <text x="30" y="430" font-family="sans-serif" font-size="11" fill="#64748B">Renderer: {renderer} | Total Nodes: {node_count} | Mode: Local Safe Preview</text>
</svg>"""


rendering_service = RenderingService()
