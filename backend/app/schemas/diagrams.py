"""
Diagram API Pydantic schemas -- Sprint 1 + Sprint 2.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
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


# ---- Sprint 1: /api/diagrams/prepare ----------------------------------------


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

    This is an internal/dev endpoint -- the response deliberately exposes
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


# ---- Sprint 2: /api/diagrams/generate ---------------------------------------


class GenerateRequest(BaseModel):
    """
    Input for POST /api/diagrams/generate.

    The prompt is the only required field.  A max_length of 8192 is enforced
    at the API boundary (before any external call) as a first-line size guard.
    """

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=8192,
        description=(
            "Natural language description of the diagram to generate. "
            "Max 8192 characters enforced at the API boundary."
        ),
    )


class GenerateResponse(BaseModel):
    """
    Response from POST /api/diagrams/generate.

    Key design decisions:
    - success=True only when status is "validated" or "cache_reused".
    - structured_json is None for rejected or error results.
    - complexity contains the INDEPENDENTLY COMPUTED metrics (never Groq's
      self-reported value).
    - rejection_reason is always populated when success=False.
    - This response has no rendering fields (svgContent, dslCode, renderer) --
      those are Sprint 3.
    """

    request_id: str                                  = Field(..., description="UUID of the persisted diagram_requests row")
    status: str                                      = Field(..., description="Pipeline status: validated | cache_reused | rejected_invalid | rejected_complexity | error")
    source: str                                      = Field(..., description="Origin of the result: fresh | cache")
    prompt: str                                      = Field(..., description="Original user prompt")
    preprocessed_prompt: str                         = Field(..., description="Prompt after optional spaCy stage")
    success: bool                                    = Field(..., description="True only when status is validated or cache_reused")

    diagram_type: Optional[str]                      = Field(None, description="Diagram category from validated JSON")
    structured_json: Optional[Dict[str, Any]]        = Field(None, description="Validated graph structure (None on rejection)")
    complexity: Optional[Dict[str, Any]]             = Field(None, description="Independently computed complexity metrics")

    similarity_score: Optional[float]                = Field(None, description="Cosine similarity score (only on cache hits)")
    validation_errors: List[str]                     = Field(default_factory=list, description="Validation error details (on rejection)")
    rejection_reason: Optional[str]                  = Field(None, description="Human-readable rejection reason")

    spacy_enabled: bool                              = Field(..., description="Whether spaCy preprocessing ran")
    candidates_count: int                            = Field(..., description="Number of similarity candidates found above threshold")
