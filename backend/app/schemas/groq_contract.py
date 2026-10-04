"""
Groq Prompt/Response Contract -- Sprint 2.

This module is the authoritative schema definition for the structured JSON
that Groq must return.  It is deliberately separated from the rest of the
codebase so the contract is explicit, versioned, and not buried in prompt text.

===========================================================================
CONTRACT VERSION: 1.0  (bump whenever the Groq prompt shape changes)
===========================================================================

GROQ SYSTEM PROMPT (sent verbatim -- do NOT alter without bumping version)
---------------------------------------------------------------------------
You are a diagram-architecture extractor.  Given a natural-language description,
return ONLY a valid JSON object with the following fields and no extra keys.

Required fields:
  diagram_type  : string -- one of: flowchart | sequence | erd | class |
                            state_machine | mindmap | gantt | network | generic
  nodes         : array  -- at least 1 node object (see below)
  edges         : array  -- may be empty for single-node diagrams
  attributes    : object -- diagram-level metadata (see below)

Node object shape:
  id       : string  -- unique within the response, non-empty, no whitespace
  label    : string  -- human-readable display label (max 200 chars)
  type     : string  -- node semantic type (e.g. "service", "database",
                        "actor", "class", "state"); use "generic" when unsure
  metadata : object  -- optional; free-form key/value pairs for extra context

Edge object shape:
  id     : string  -- unique within the response, non-empty, no whitespace
  source : string  -- must exactly match an id in the nodes array
  target : string  -- must exactly match an id in the nodes array
  label  : string  -- may be empty string; max 200 chars
  type   : string  -- relationship type (e.g. "depends_on", "calls",
                      "inherits", "transitions_to"); use "generic" when unsure

Attributes object shape (required keys):
  title              : string  -- short diagram title (max 120 chars)
  description        : string  -- one-sentence summary (max 500 chars)
  allows_disconnected: boolean -- true only for diagram types where isolated
                                  subgraphs are semantically valid (e.g.
                                  mindmap, gantt, network); false for all others
  direction          : string  -- layout hint: "LR" | "RL" | "TB" | "BT" | "auto"

DO NOT include a "complexity" field.  Complexity is computed independently.
DO NOT add fields beyond those specified.
Return ONLY the JSON object -- no markdown fences, no prose.

===========================================================================
PYTHON CONTRACT (Pydantic v2)
---------------------------------------------------------------------------
Validation of any Groq response MUST go through these models -- never through
ad-hoc JSON key access.
===========================================================================
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Allowed diagram types
# ---------------------------------------------------------------------------

DiagramType = Literal[
    "flowchart",
    "sequence",
    "erd",
    "class",
    "state_machine",
    "mindmap",
    "gantt",
    "network",
    "generic",
]

# Diagram types that explicitly allow disconnected components
DISCONNECTED_ALLOWED_TYPES: frozenset[str] = frozenset({"mindmap", "gantt", "network"})

DirectionType = Literal["LR", "RL", "TB", "BT", "auto"]

_ID_PATTERN = re.compile(r"^\S+$")


def _validate_id(v: str, field_name: str) -> str:
    """Ensure an ID is non-empty and contains no whitespace."""
    if not v or not _ID_PATTERN.match(v):
        raise ValueError(
            f"{field_name!r} must be a non-empty string with no whitespace; got {v!r}"
        )
    return v


# ---------------------------------------------------------------------------
# Sub-schemas
# ---------------------------------------------------------------------------


NODE_TYPE_SYNONYMS: Dict[str, str] = {
    "postgres": "database",
    "postgresql": "database",
    "mysql": "database",
    "sqlite": "database",
    "rdbms": "database",
    "datastore": "database",
    "db": "database",
    "mongodb": "database",
    "dynamodb": "database",
    "sql": "database",
    "redis": "cache",
    "memcached": "cache",
    "kafka": "queue",
    "rabbitmq": "queue",
    "sqs": "queue",
    "event_bus": "queue",
    "pubsub": "queue",
    "stream": "queue",
    "rest_api": "service",
    "microservice": "service",
    "web_app": "service",
    "backend": "service",
    "service_node": "service",
    "api_gateway": "gateway",
    "lb": "gateway",
    "load_balancer": "gateway",
    "proxy": "gateway",
    "ingress": "gateway",
    "user": "actor",
    "end_user": "actor",
    "client_app": "actor",
    "browser": "actor",
    "table": "entity",
    "schema_entity": "entity",
}

EDGE_TYPE_SYNONYMS: Dict[str, str] = {
    "http_post": "calls",
    "http_get": "calls",
    "api_call": "calls",
    "rest_call": "calls",
    "sync_call": "calls",
    "rpc": "calls",
    "has_many": "one_to_many",
    "belongs_to": "one_to_many",
    "1_to_many": "one_to_many",
    "1_n": "one_to_many",
    "many_to_many": "many_to_many",
    "n_m": "many_to_many",
    "m_n": "many_to_many",
    "one_to_one": "one_to_one",
    "1_to_1": "one_to_one",
    "1_1": "one_to_one",
    "next_state": "transitions_to",
    "moves_to": "transitions_to",
    "extends": "inherits",
    "inherits_from": "inherits",
    "is_a": "inherits",
}


class NodeObject(BaseModel):
    """A single node in the diagram."""

    id: str = Field(..., description="Unique node identifier -- no whitespace")
    label: str = Field(..., max_length=200, description="Human-readable display label")
    type: str = Field(..., description="Semantic node type")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional free-form metadata")

    @field_validator("id")
    @classmethod
    def id_no_whitespace(cls, v: str) -> str:
        return _validate_id(v, "node.id")

    @field_validator("label")
    @classmethod
    def label_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("node.label must not be blank")
        return v

    @field_validator("type")
    @classmethod
    def type_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("node.type must not be blank")
        cleaned = v.strip().lower()
        return NODE_TYPE_SYNONYMS.get(cleaned, cleaned)


class EdgeObject(BaseModel):
    """A directed relationship between two nodes."""

    id: str = Field(..., description="Unique edge identifier -- no whitespace")
    source: str = Field(..., description="Must match an existing node id")
    target: str = Field(..., description="Must match an existing node id")
    label: str = Field("", max_length=200, description="Relationship label (may be empty)")
    type: str = Field(..., description="Relationship type")

    @field_validator("id")
    @classmethod
    def id_no_whitespace(cls, v: str) -> str:
        return _validate_id(v, "edge.id")

    @field_validator("source")
    @classmethod
    def source_no_whitespace(cls, v: str) -> str:
        return _validate_id(v, "edge.source")

    @field_validator("target")
    @classmethod
    def target_no_whitespace(cls, v: str) -> str:
        return _validate_id(v, "edge.target")

    @field_validator("type")
    @classmethod
    def type_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("edge.type must not be blank")
        cleaned = v.strip().lower()
        return EDGE_TYPE_SYNONYMS.get(cleaned, cleaned)


class DiagramAttributes(BaseModel):
    """Diagram-level metadata required in every Groq response."""

    title: str = Field(..., max_length=120, description="Short diagram title")
    description: str = Field(..., max_length=500, description="One-sentence summary")
    allows_disconnected: bool = Field(
        ...,
        description=(
            "True only for diagram types where isolated subgraphs are semantically "
            "valid (mindmap, gantt, network). Must be false for all others."
        ),
    )
    direction: DirectionType = Field("auto", description="Layout direction hint")

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("attributes.title must not be blank")
        return v

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("attributes.description must not be blank")
        return v


# ---------------------------------------------------------------------------
# Top-level Groq response schema
# ---------------------------------------------------------------------------


class GroqDiagramResponse(BaseModel):
    """
    The complete, validated structured JSON that Groq must return.

    Validation layers applied here (in order):
      1. Pydantic field-level type and constraint checks on each sub-model.
      2. No duplicate node IDs.
      3. No duplicate edge IDs.
      4. Referential integrity -- every edge.source and edge.target must
         reference a node id that exists in the same response.
      5. Consistency check -- allows_disconnected must be False for diagram
         types that do not support disconnected components.

    Complexity is intentionally NOT a field here.  It is always computed
    independently by ComplexityService and NEVER sourced from this payload.
    """

    diagram_type: DiagramType = Field(..., description="Diagram category")
    nodes: List[NodeObject] = Field(..., min_length=1, description="At least one node")
    edges: List[EdgeObject] = Field(default_factory=list, description="Directed edges")
    attributes: DiagramAttributes = Field(..., description="Diagram-level metadata")

    @model_validator(mode="after")
    def check_no_duplicate_node_ids(self) -> "GroqDiagramResponse":
        ids = [n.id for n in self.nodes]
        seen: set[str] = set()
        duplicates: list[str] = []
        for nid in ids:
            if nid in seen:
                duplicates.append(nid)
            seen.add(nid)
        if duplicates:
            raise ValueError(
                f"Duplicate node IDs detected: {sorted(set(duplicates))}. "
                "Every node must have a unique id."
            )
        return self

    @model_validator(mode="after")
    def check_no_duplicate_edge_ids(self) -> "GroqDiagramResponse":
        ids = [e.id for e in self.edges]
        seen: set[str] = set()
        duplicates: list[str] = []
        for eid in ids:
            if eid in seen:
                duplicates.append(eid)
            seen.add(eid)
        if duplicates:
            raise ValueError(
                f"Duplicate edge IDs detected: {sorted(set(duplicates))}. "
                "Every edge must have a unique id."
            )
        return self

    @model_validator(mode="after")
    def check_referential_integrity(self) -> "GroqDiagramResponse":
        """Every edge.source and edge.target must reference a real node id."""
        node_ids = {n.id for n in self.nodes}
        violations: list[str] = []
        for edge in self.edges:
            if edge.source not in node_ids:
                violations.append(
                    f"Edge '{edge.id}' references unknown source node '{edge.source}'"
                )
            if edge.target not in node_ids:
                violations.append(
                    f"Edge '{edge.id}' references unknown target node '{edge.target}'"
                )
        if violations:
            raise ValueError(
                "Referential integrity violations:\n" + "\n".join(f"  * {v}" for v in violations)
            )
        return self

    @model_validator(mode="after")
    def check_disconnected_flag_consistency(self) -> "GroqDiagramResponse":
        """
        Reject Groq responses that claim allows_disconnected=True for diagram
        types that do not semantically support disconnected components.
        """
        if (
            self.attributes.allows_disconnected
            and self.diagram_type not in DISCONNECTED_ALLOWED_TYPES
        ):
            raise ValueError(
                f"diagram_type '{self.diagram_type}' does not allow disconnected "
                f"components, but attributes.allows_disconnected is True. "
                f"Types that permit disconnected subgraphs: {sorted(DISCONNECTED_ALLOWED_TYPES)}"
            )
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict suitable for JSONB storage."""
        return self.model_dump(mode="json")

    @classmethod
    def parse_payload(cls, raw: Dict[str, Any]) -> GroqDiagramResponse:
        """
        Parse raw dict into the appropriate specialized diagram schema subclass.
        """
        dtype = raw.get("diagram_type", "generic")
        schema_cls = DIAGRAM_SCHEMA_MAP.get(dtype, GenericDiagramResponse)
        return schema_cls.model_validate(raw)


# ---------------------------------------------------------------------------
# Specialized Diagram Schemas (Phase 2)
# ---------------------------------------------------------------------------


class ErdDiagramResponse(GroqDiagramResponse):
    """Specialized schema for Entity Relationship Diagrams (ERD)."""

    diagram_type: Literal["erd"] = "erd"

    @model_validator(mode="after")
    def validate_erd_relationships(self) -> "ErdDiagramResponse":
        allowed = {"one_to_many", "many_to_many", "one_to_one", "calls", "generic", "depends_on", "inherits"}
        for edge in self.edges:
            if edge.type not in allowed:
                edge.type = "one_to_many"
        for node in self.nodes:
            if node.type in {"generic", "service", "actor"}:
                node.type = "entity"
        return self


class SequenceDiagramResponse(GroqDiagramResponse):
    """Specialized schema for Sequence Diagrams."""

    diagram_type: Literal["sequence"] = "sequence"

    @model_validator(mode="after")
    def validate_sequence_interactions(self) -> "SequenceDiagramResponse":
        allowed_edges = {"calls", "sync", "async", "reply", "returns", "depends_on", "generic"}
        for edge in self.edges:
            if edge.type not in allowed_edges:
                edge.type = "calls"
        return self


class ClassDiagramResponse(GroqDiagramResponse):
    """Specialized schema for UML Class Diagrams."""

    diagram_type: Literal["class"] = "class"

    @model_validator(mode="after")
    def validate_class_relationships(self) -> "ClassDiagramResponse":
        allowed_edges = {"inherits", "implements", "associates", "aggregates", "composes", "calls", "one_to_many", "one_to_one", "generic"}
        for edge in self.edges:
            if edge.type not in allowed_edges:
                edge.type = "inherits"
        for node in self.nodes:
            if node.type in {"generic", "service"}:
                node.type = "class"
        return self


class StateMachineResponse(GroqDiagramResponse):
    """Specialized schema for State Machine Diagrams."""

    diagram_type: Literal["state_machine"] = "state_machine"

    @model_validator(mode="after")
    def validate_state_machine_nodes(self) -> "StateMachineResponse":
        for node in self.nodes:
            if node.type in {"generic", "service"}:
                node.type = "state"
        return self


class NetworkDiagramResponse(GroqDiagramResponse):
    """Specialized schema for Network & Infrastructure Diagrams (nwdiag)."""

    diagram_type: Literal["network"] = "network"

    @model_validator(mode="after")
    def validate_network_nodes(self) -> "NetworkDiagramResponse":
        for node in self.nodes:
            if node.type in {"generic"}:
                node.type = "server"
        return self


class GenericDiagramResponse(GroqDiagramResponse):
    """Generic schema for flowcharts, architecture, mindmaps, gantt, etc."""

    diagram_type: DiagramType = "generic"


DIAGRAM_SCHEMA_MAP: Dict[str, type[GroqDiagramResponse]] = {
    "erd": ErdDiagramResponse,
    "sequence": SequenceDiagramResponse,
    "class": ClassDiagramResponse,
    "state_machine": StateMachineResponse,
    "network": NetworkDiagramResponse,
    "flowchart": GenericDiagramResponse,
    "architecture": GenericDiagramResponse,
    "mindmap": GenericDiagramResponse,
    "gantt": GenericDiagramResponse,
    "generic": GenericDiagramResponse,
}

