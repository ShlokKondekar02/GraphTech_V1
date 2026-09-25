"""
Diagrams API router — Sprint 1.

Endpoints
---------
GET  /api/diagrams/          — placeholder list (Sprint 0 stub, kept for compatibility)
POST /api/diagrams/prepare   — internal/dev endpoint: preprocess → embed → similarity search
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.schemas.diagrams import (
    CandidateResult,
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
from app.services.preprocessing_service import build_preprocessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diagrams", tags=["Diagrams"])


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/diagrams/
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/")
async def list_diagrams_placeholder():
    """Placeholder for listing user diagram requests."""
    return {"diagrams": []}


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/diagrams/prepare
# ──────────────────────────────────────────────────────────────────────────────


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
    Sprint 1 pipeline (left half only — no generation):

    1. Optional spaCy preprocessing (toggled by ENABLE_SPACY_PREPROCESSING)
    2. Voyage AI embedding generation (with timeout + retry handling)
    3. pgvector top-k cosine similarity search against ``diagram_requests``
    4. Return ranked candidates + debug metadata
    """
    original_prompt = body.prompt

    # ── Stage 1: optional spaCy preprocessing ─────────────────────────────
    preprocessor = build_preprocessor()
    try:
        preprocessed_prompt = preprocessor.process(original_prompt)
    except RuntimeError as exc:
        # spaCy model not downloaded — surface a clear 503
        logger.error("spaCy model unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"spaCy preprocessing failed: {exc}",
        ) from exc

    # ── Stage 2: Voyage AI embedding ───────────────────────────────────────
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

    # ── Stage 3: pgvector similarity search ────────────────────────────────
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
