"""
Diagrams API router -- Sprint 1 + Sprint 2.

Endpoints
---------
GET  /api/diagrams/          -- placeholder list (Sprint 0 stub, kept for compatibility)
POST /api/diagrams/prepare   -- internal/dev: preprocess -> embed -> similarity search
POST /api/diagrams/generate  -- Sprint 2: full pipeline (reuse or fresh Groq generation)
                                with independent validation and complexity gating
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.schemas.diagrams import (
    CandidateResult,
    GenerateRequest,
    GenerateResponse,
    PrepareRequest,
    PrepareResponse,
)
from app.services.embedding_service import (
    EmbeddingAPIError,
    EmbeddingResponseError,
    EmbeddingRateLimitError,
    EmbeddingTimeoutError,
    embedding_service,
)
from app.services.generation_service import generation_service
from app.services.preprocessing_service import build_preprocessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diagrams", tags=["Diagrams"])


# ------------------------------------------------------------------------------
# GET /api/diagrams/
# ------------------------------------------------------------------------------


@router.get("/")
async def list_diagrams_placeholder():
    """Placeholder for listing user diagram requests."""
    return {"diagrams": []}


# ------------------------------------------------------------------------------
# POST /api/diagrams/prepare
# ------------------------------------------------------------------------------


@router.post(
    "/prepare",
    response_model=PrepareResponse,
    summary="[Dev] Preprocess prompt, embed, and run similarity search",
    description=(
        "Internal/dev-only endpoint (not exposed in any user-facing UI). "
        "Runs the prompt through the optional spaCy stage, generates a Voyage "
        "embedding, then performs a pgvector top-k cosine similarity search "
        "and returns ranked candidates with their scores."
    ),
    status_code=status.HTTP_200_OK,
)
async def prepare_diagram(
    body: PrepareRequest,
    db: Session = Depends(get_db),
) -> PrepareResponse:
    """
    Sprint 1 pipeline (left half only -- no generation):

    1. Optional spaCy preprocessing (toggled by ENABLE_SPACY_PREPROCESSING)
    2. Voyage AI embedding generation (with timeout + retry handling)
    3. pgvector top-k cosine similarity search against ``diagram_requests``
    4. Return ranked candidates + debug metadata
    """
    original_prompt = body.prompt

    # -- Stage 1: optional spaCy preprocessing --------------------------------
    preprocessor = build_preprocessor()
    try:
        preprocessed_prompt = preprocessor.process(original_prompt)
    except RuntimeError as exc:
        logger.error("spaCy model unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"spaCy preprocessing failed: {exc}",
        ) from exc

    # -- Stage 2: Voyage AI embedding -----------------------------------------
    try:
        embedding = embedding_service.generate_embedding(preprocessed_prompt)
    except EmbeddingTimeoutError as exc:
        logger.error("Voyage timeout: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Embedding service timed out: {exc}",
        ) from exc
    except EmbeddingRateLimitError as exc:
        logger.error("Voyage rate-limit exhausted: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Embedding rate limit: {exc}",
        ) from exc
    except EmbeddingResponseError as exc:
        logger.error("Voyage bad response: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Embedding service returned malformed response: {exc}",
        ) from exc
    except EmbeddingAPIError as exc:
        logger.error("Voyage API error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Embedding service error: {exc}",
        ) from exc

    # -- Stage 3: pgvector similarity search ----------------------------------
    raw_candidates = embedding_service.find_similar_diagrams(
        db=db,
        embedding=embedding,
        top_k=settings.SIMILARITY_TOP_K,
        threshold=settings.SIMILARITY_THRESHOLD,
    )

    candidates = [
        CandidateResult(
            id=c.id,
            prompt=c.prompt,
            similarity=c.similarity,
            diagram_type=c.diagram_type,
            complexity=c.complexity,
            renderer=c.renderer,
            structured_json=c.structured_json,
        )
        for c in raw_candidates
    ]

    logger.info(
        "prepare_diagram: prompt=%r  spacy=%s  candidates=%d  above_threshold=%s",
        original_prompt[:60],
        preprocessor.enabled,
        len(candidates),
        bool(candidates),
    )

    return PrepareResponse(
        original_prompt=original_prompt,
        preprocessed_prompt=preprocessed_prompt,
        spacy_enabled=preprocessor.enabled,
        embedding_dimension=len(embedding),
        similarity_threshold=settings.SIMILARITY_THRESHOLD,
        candidates=candidates,
        above_threshold=bool(candidates),
    )


# ------------------------------------------------------------------------------
# POST /api/diagrams/generate  (Sprint 2)
# ------------------------------------------------------------------------------


@router.post(
    "/generate",
    response_model=GenerateResponse,
    summary="Generate or reuse a validated diagram structure",
    description=(
        "Full pipeline: spaCy (optional) -> Voyage embedding -> pgvector search -> "
        "reuse-or-generate decision -> Groq structured JSON (on cache miss) -> "
        "independent Pydantic + graph validation -> independent complexity computation "
        "and ceiling check -> persist every attempt (including rejections) -> response.\n\n"
        "On cache hit: the cached JSON is re-validated through the SAME layers before "
        "being returned -- no shortcuts for reused results.\n\n"
        "Complexity is ALWAYS computed independently from the graph structure. "
        "Any complexity value Groq may self-report is ignored entirely."
    ),
    status_code=status.HTTP_200_OK,
)
async def generate_diagram(
    body: GenerateRequest,
    db: Session = Depends(get_db),
) -> GenerateResponse:
    """
    Sprint 2 pipeline:

    1. spaCy preprocessing (optional)
    2. Voyage embedding + pgvector similarity search
    3. Cache hit -> re-validate + complexity check -> return (or fall through)
    4. Cache miss -> Groq call -> validate -> complexity check -> persist
    5. Return structured result (never render -- that is Sprint 3)
    """
    result = generation_service.run_pipeline(
        db=db,
        prompt=body.prompt,
        user_id=None,  # auth wiring deferred to Sprint 5
    )

    # Map GenerationResult to HTTP response
    complexity_dict = result.complexity.to_dict() if result.complexity else None

    return GenerateResponse(
        request_id=result.request_id,
        status=result.status,
        source=result.source,
        prompt=result.prompt,
        preprocessed_prompt=result.preprocessed_prompt,
        diagram_type=result.diagram_type,
        structured_json=result.structured_json,
        complexity=complexity_dict,
        similarity_score=result.similarity_score,
        validation_errors=result.validation_errors if not result.is_success else [],
        rejection_reason=result.rejection_reason,
        spacy_enabled=result.spacy_enabled,
        candidates_count=result.candidates_count,
        success=result.is_success,
    )
