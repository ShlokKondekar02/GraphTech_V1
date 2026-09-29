"""
Complexity Service -- Sprint 2.

Independently computes diagram complexity from the structured JSON graph.
Groq's self-reported complexity (if it ever returns one) is NEVER used here.

Complexity Metrics (all computed deterministically from the graph structure):
    node_count      -- total nodes
    edge_count      -- total edges
    cyclomatic_number -- edges - nodes + connected_components  (McCabe-style)
    max_in_degree   -- highest number of incoming edges for any single node
    max_out_degree  -- highest number of outgoing edges for any single node
    nesting_depth   -- longest chain (longest path in the DAG via BFS/DFS);
                       set to -1 for cyclic graphs (cycles detected via DFS)
    component_count -- number of weakly connected components

Score calculation:
    Weighted combination of the metrics above; each metric is clamped
    before weighting so a single pathological value cannot dominate.
    The final score is a float in [0, infinity).

Thresholds (configurable in settings):
    COMPLEXITY_CEILING -- if computed score >= ceiling, the request is REJECTED
                          before any rendering is attempted.  The rejection
                          reason and computed metrics are always persisted.
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ComplexityResult:
    """
    The independently computed complexity verdict for a diagram.

    Attributes
    ----------
    node_count          -- total nodes in the graph
    edge_count          -- total edges in the graph
    cyclomatic_number   -- McCabe-style: edges - nodes + components
    max_in_degree       -- max incoming edges for any node
    max_out_degree      -- max outgoing edges for any node
    nesting_depth       -- longest directed path length (-1 if cyclic)
    component_count     -- number of weakly connected components
    is_cyclic           -- True if the directed graph contains a cycle
    score               -- weighted composite score (0..inf)
    label               -- human-readable bucket ("simple", "moderate", "complex", "oversized")
    exceeds_ceiling     -- True when score >= configured ceiling
    ceiling_used        -- the ceiling value used for the verdict
    rejection_reason    -- non-None when exceeds_ceiling is True
    """

    node_count: int
    edge_count: int
    cyclomatic_number: int
    max_in_degree: int
    max_out_degree: int
    nesting_depth: int          # -1 signals cyclic graph
    component_count: int
    is_cyclic: bool
    score: float
    label: str
    exceeds_ceiling: bool
    ceiling_used: float
    rejection_reason: Optional[str] = field(default=None)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "cyclomatic_number": self.cyclomatic_number,
            "max_in_degree": self.max_in_degree,
            "max_out_degree": self.max_out_degree,
            "nesting_depth": self.nesting_depth,
            "component_count": self.component_count,
            "is_cyclic": self.is_cyclic,
            "score": self.score,
            "label": self.label,
            "exceeds_ceiling": self.exceeds_ceiling,
            "ceiling_used": self.ceiling_used,
            "rejection_reason": self.rejection_reason,
        }


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------


def _build_adjacency(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
) -> Tuple[Dict[str, List[str]], Dict[str, List[str]], Dict[str, int], Dict[str, int]]:
    """
    Build directed adjacency lists and degree maps.

    Returns (out_adj, in_adj, out_degree, in_degree).
    """
    out_adj: Dict[str, List[str]] = defaultdict(list)
    in_adj: Dict[str, List[str]] = defaultdict(list)
    out_degree: Dict[str, int] = {n["id"]: 0 for n in nodes}
    in_degree: Dict[str, int] = {n["id"]: 0 for n in nodes}

    for edge in edges:
        src = edge.get("source", "")
        tgt = edge.get("target", "")
        if src in out_degree and tgt in in_degree:
            out_adj[src].append(tgt)
            in_adj[tgt].append(src)
            out_degree[src] += 1
            in_degree[tgt] += 1

    return out_adj, in_adj, out_degree, in_degree


def _weakly_connected_components(
    node_ids: Set[str],
    out_adj: Dict[str, List[str]],
    in_adj: Dict[str, List[str]],
) -> int:
    """Count weakly connected components (treating edges as undirected)."""
    visited: Set[str] = set()
    components = 0
    for start in node_ids:
        if start in visited:
            continue
        components += 1
        queue: deque[str] = deque([start])
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            for neighbor in out_adj.get(node, []):
                if neighbor not in visited:
                    queue.append(neighbor)
            for neighbor in in_adj.get(node, []):
                if neighbor not in visited:
                    queue.append(neighbor)
    return components


def _detect_cycle(
    node_ids: Set[str],
    out_adj: Dict[str, List[str]],
) -> bool:
    """Return True if the directed graph has at least one cycle (DFS coloring)."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: Dict[str, int] = {n: WHITE for n in node_ids}

    def dfs(u: str) -> bool:
        color[u] = GRAY
        for v in out_adj.get(u, []):
            if v not in color:
                continue
            if color[v] == GRAY:
                return True  # back edge -> cycle
            if color[v] == WHITE and dfs(v):
                return True
        color[u] = BLACK
        return False

    return any(color[n] == WHITE and dfs(n) for n in node_ids)


def _longest_path_dag(
    node_ids: Set[str],
    out_adj: Dict[str, List[str]],
    in_degree: Dict[str, int],
) -> int:
    """
    Compute the longest directed path length (number of edges) in a DAG.
    Uses Kahn's topological sort with distance tracking.
    Returns -1 if a cycle is detected (should not happen if _detect_cycle ran first).
    """
    in_deg = dict(in_degree)
    dist: Dict[str, int] = {n: 0 for n in node_ids}
    queue: deque[str] = deque(n for n in node_ids if in_deg.get(n, 0) == 0)
    processed = 0

    while queue:
        u = queue.popleft()
        processed += 1
        for v in out_adj.get(u, []):
            if v not in dist:
                continue
            if dist[u] + 1 > dist[v]:
                dist[v] = dist[u] + 1
            in_deg[v] -= 1
            if in_deg[v] == 0:
                queue.append(v)

    if processed < len(node_ids):
        return -1  # cycle detected
    return max(dist.values()) if dist else 0


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------


# Weights for the composite score (tuned for diagram complexity)
_WEIGHTS = {
    "node_count": 1.0,
    "edge_count": 0.8,
    "cyclomatic_number": 2.0,  # heavily penalises tightly meshed graphs
    "max_in_degree": 0.5,
    "max_out_degree": 0.5,
    "nesting_depth": 1.5,       # long chains are cognitively demanding
    "component_count": 0.3,     # additional components add a small penalty
}

# Label bucket boundaries (score thresholds)
_LABEL_THRESHOLDS = [
    (10.0, "simple"),
    (25.0, "moderate"),
    (50.0, "complex"),
]
_LABEL_OVERSIZED = "oversized"


class ComplexityService:
    """
    Independently compute graph-structural complexity from a validated
    GroqDiagramResponse (or from its raw dict equivalent).

    This service has NO dependency on Groq -- it operates purely on the
    node/edge structure of the diagram.
    """

    def compute(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        diagram_type: str,
        ceiling: Optional[float] = None,
    ) -> ComplexityResult:
        """
        Compute the complexity of a diagram from its node and edge lists.

        Parameters
        ----------
        nodes       -- list of node dicts (each must have an "id" key)
        edges       -- list of edge dicts (each must have "id", "source", "target")
        diagram_type -- the diagram type string (used to interpret component count)
        ceiling     -- complexity score ceiling; defaults to settings value

        Returns
        -------
        ComplexityResult with all metrics filled in.
        """
        if ceiling is None:
            from app.core.config import settings  # local to avoid circular
            ceiling = settings.COMPLEXITY_CEILING

        node_count = len(nodes)
        edge_count = len(edges)
        node_ids: Set[str] = {n["id"] for n in nodes}

        out_adj, in_adj, out_degree, in_degree = _build_adjacency(nodes, edges)

        # Degree metrics
        max_out = max(out_degree.values(), default=0)
        max_in = max(in_degree.values(), default=0)

        # Connectivity
        component_count = _weakly_connected_components(node_ids, out_adj, in_adj)

        # Cyclomatic number (McCabe-style): E - N + C
        cyclomatic_number = max(0, edge_count - node_count + component_count)

        # Cycle detection
        is_cyclic = _detect_cycle(node_ids, out_adj)

        # Nesting depth (longest path -- only meaningful for DAGs)
        if is_cyclic:
            nesting_depth = -1
        else:
            nesting_depth = _longest_path_dag(node_ids, out_adj, dict(in_degree))

        # Composite score
        nd_clamped = min(node_count, 100)
        ed_clamped = min(edge_count, 200)
        cyc_clamped = min(cyclomatic_number, 50)
        maxin_clamped = min(max_in, 20)
        maxout_clamped = min(max_out, 20)
        nest_clamped = min(max(nesting_depth, 0), 30)  # -1 -> 0 for scoring
        comp_clamped = min(component_count, 20)

        score = (
            nd_clamped * _WEIGHTS["node_count"]
            + ed_clamped * _WEIGHTS["edge_count"]
            + cyc_clamped * _WEIGHTS["cyclomatic_number"]
            + maxin_clamped * _WEIGHTS["max_in_degree"]
            + maxout_clamped * _WEIGHTS["max_out_degree"]
            + nest_clamped * _WEIGHTS["nesting_depth"]
            + comp_clamped * _WEIGHTS["component_count"]
        )

        # Label bucket
        label = _LABEL_OVERSIZED
        for threshold, bucket_label in _LABEL_THRESHOLDS:
            if score < threshold:
                label = bucket_label
                break

        exceeds_ceiling = score >= ceiling
        rejection_reason: Optional[str] = None
        if exceeds_ceiling:
            rejection_reason = (
                f"Independently computed complexity score {score:.2f} exceeds the "
                f"configured ceiling of {ceiling:.2f}. "
                f"Metrics: nodes={node_count}, edges={edge_count}, "
                f"cyclomatic={cyclomatic_number}, nesting_depth={nesting_depth}, "
                f"components={component_count}. "
                "Rendering rejected pre-render to avoid resource exhaustion."
            )

        result = ComplexityResult(
            node_count=node_count,
            edge_count=edge_count,
            cyclomatic_number=cyclomatic_number,
            max_in_degree=max_in,
            max_out_degree=max_out,
            nesting_depth=nesting_depth,
            component_count=component_count,
            is_cyclic=is_cyclic,
            score=score,
            label=label,
            exceeds_ceiling=exceeds_ceiling,
            ceiling_used=ceiling,
            rejection_reason=rejection_reason,
        )

        logger.info(
            "Complexity computed: nodes=%d edges=%d cyclomatic=%d "
            "nesting=%d components=%d score=%.2f label=%s exceeds_ceiling=%s",
            node_count,
            edge_count,
            cyclomatic_number,
            nesting_depth,
            component_count,
            score,
            label,
            exceeds_ceiling,
        )

        return result

    def compute_from_groq_response(
        self,
        groq_response: Any,
        ceiling: Optional[float] = None,
    ) -> ComplexityResult:
        """
        Convenience wrapper that accepts a GroqDiagramResponse object
        (from app.schemas.groq_contract) directly.
        """
        nodes = [n.model_dump(mode="json") for n in groq_response.nodes]
        edges = [e.model_dump(mode="json") for e in groq_response.edges]
        return self.compute(
            nodes=nodes,
            edges=edges,
            diagram_type=groq_response.diagram_type,
            ceiling=ceiling,
        )

    def compute_from_dict(
        self,
        structured_json: Dict[str, Any],
        ceiling: Optional[float] = None,
    ) -> ComplexityResult:
        """
        Compute complexity from a raw dict (e.g. retrieved from DB JSONB).
        The dict must contain 'nodes', 'edges', and 'diagram_type' keys.
        """
        nodes = structured_json.get("nodes", [])
        edges = structured_json.get("edges", [])
        diagram_type = structured_json.get("diagram_type", "generic")
        return self.compute(
            nodes=nodes,
            edges=edges,
            diagram_type=diagram_type,
            ceiling=ceiling,
        )


# Module-level singleton
complexity_service = ComplexityService()
