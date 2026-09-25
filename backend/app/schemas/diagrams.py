from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class DiagramGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Natural language prompt describing the diagram")
    renderer_preference: Optional[str] = Field(None, description="Optional preferred renderer (e.g. mermaid, plantuml, graphviz)")


class DiagramResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    prompt: str
    structured_json: Optional[Dict[str, Any]] = None
    complexity: Optional[str] = None
    renderer: Optional[str] = None
    diagram_type: Optional[str] = None
    status: str
    output_path: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Sprint 1: /api/diagrams/prepare ──────────────────────────────────────────


class PrepareRequest(BaseModel):
    """Input for the prompt-prepare endpoint."""

    prompt: str = Field(..., min_length=1, max_length=4096, description="Natural language diagram prompt")


class CandidateResult(BaseModel):
    """A single similarity search result returned by /prepare."""

    id: str                                          = Field(..., description="DiagramRequest UUID")
    prompt: str                                      = Field(..., description="Stored prompt that matched")
    similarity: float                                = Field(..., ge=0.0, le=1.0, description="Cosine similarity score")
    diagram_type: Optional[str]                      = Field(None)
    complexity: Optional[str]                        = Field(None)
    renderer: Optional[str]                          = Field(None)
    structured_json: Optional[Dict[str, Any]]        = Field(None)


class PrepareResponse(BaseModel):
    """
    Full response from POST /api/diagrams/prepare.

    This is an internal/dev endpoint — the response deliberately exposes
    debug metadata (preprocessed prompt, similarity threshold, embedding
    dimension) so the retrieval stage can be inspected in isolation.
    """

    original_prompt: str                    = Field(..., description="Raw input prompt")
    preprocessed_prompt: str               = Field(..., description="Prompt after optional spaCy stage")
    spacy_enabled: bool                    = Field(..., description="Whether spaCy preprocessing ran")
    embedding_dimension: int               = Field(..., description="Dimension of the generated embedding")
    similarity_threshold: float            = Field(..., description="Configured threshold used for filtering")
    candidates: List[CandidateResult]      = Field(..., description="Top-k similarity results above threshold")
    above_threshold: bool                  = Field(..., description="True if any candidate exceeds threshold")

