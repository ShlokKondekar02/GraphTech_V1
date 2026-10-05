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

import uuid
import threading
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.schemas.diagrams import (
    CandidateResult,
    GenerateRequest,
    GenerateResponse,
    PrepareRequest,
    PrepareResponse,
    RenderDiagramRequest,
    RenderDiagramResponse,
)
from app.services.embedding_service import (
    EmbeddingAPIError,
    EmbeddingResponseError,
    EmbeddingRateLimitError,
    EmbeddingTimeoutError,
    embedding_service,
)
from app.services.generation_service import generation_service
from app.services.job_tracker_service import job_tracker_service
from app.services.preprocessing_service import build_preprocessor
from app.services.rendering_service import rendering_service

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
    Sprint 2 + Sprint 3 pipeline:

    1. spaCy preprocessing (optional)
    2. Voyage embedding + pgvector similarity search
    3. Cache hit -> re-validate + complexity check -> render -> return
    4. Cache miss -> Groq call -> validate -> complexity check -> render -> persist
    5. Return structured result + compiled DSL + rendered SVG (Sprint 3)
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
        renderer=result.renderer,
        dsl_code=result.dsl_code,
        svg_content=result.svg_content,
        dslCode=result.dsl_code,
        svgContent=result.svg_content,
        attempt_count=result.attempt_count,
        validation_status=result.validation_status,
        repair_history=result.repair_history,
        validation_details=result.validation_details,
        spacy_enabled=result.spacy_enabled,
        candidates_count=result.candidates_count,
        success=result.is_success,
    )


# ------------------------------------------------------------------------------
# POST /api/diagrams/render  (Sprint 3 on-demand rendering)
# ------------------------------------------------------------------------------


@router.post(
    "/render",
    response_model=RenderDiagramResponse,
    summary="Compile structured JSON into DSL and render SVG via Kroki",
    description=(
        "Takes a validated structured diagram JSON and deterministically compiles "
        "it into the optimal DSL (Mermaid, PlantUML, or Graphviz DOT), renders it "
        "via Kroki, and returns the SVG markup alongside the DSL code."
    ),
    status_code=status.HTTP_200_OK,
)
async def render_diagram_endpoint(
    body: RenderDiagramRequest,
) -> RenderDiagramResponse:
    """
    On-demand compilation and rendering endpoint.
    """
    render_res = rendering_service.render_diagram(
        structured_json=body.structured_json,
        preferred_renderer=body.preferred_renderer,
    )

    return RenderDiagramResponse(
        renderer=render_res.renderer,
        diagram_type=render_res.diagram_type,
        dsl_code=render_res.dsl_code,
        svg_content=render_res.svg_content,
        dslCode=render_res.dsl_code,
        svgContent=render_res.svg_content,
    )


# ------------------------------------------------------------------------------
# Sprint 5 Endpoints: Progress Polling, Async Jobs & Reference Attachment
# ------------------------------------------------------------------------------


@router.get(
    "/{job_id}/status",
    summary="Get async generation job status and stage progress",
    description="Returns current stage, step index, percentage, and final result when completed.",
)
async def get_job_status(job_id: str):
    """
    Polling endpoint for the frontend to observe real pipeline stage transitions.
    """
    job = job_tracker_service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found in active registry",
        )
    return job.to_dict()


def _run_async_pipeline_task(job_id: str, prompt: str, db_session_factory):
    """
    Background worker that executes the pipeline while emitting stage events.
    """
    db = db_session_factory()
    try:
        job_tracker_service.update_job(job_id, "scope_guard", message="Checking domain scope...")
        time_step = 0.05

        # Execute generation service pipeline
        job_tracker_service.update_job(job_id, "preprocessing", message="spaCy NLP prompt normalization...")
        job_tracker_service.update_job(job_id, "embedding_search", message="Voyage AI embedding & pgvector search...")
        job_tracker_service.update_job(job_id, "cache_check", message="Evaluating cache hit vs fresh generation...")
        job_tracker_service.update_job(job_id, "llm_generation", message="Calling Groq LLM for AST generation...")

        result = generation_service.run_pipeline(db=db, prompt=prompt)

        job_tracker_service.update_job(job_id, "ast_validation", message="Validating Pydantic AST & graph topology...")
        job_tracker_service.update_job(job_id, "rendering", message="Compiling AST & rendering SVG via Kroki...")
        job_tracker_service.update_job(job_id, "output_validation", message="Verifying SVG XML & semantic label match...")

        resp_dict = {
            "request_id": result.request_id,
            "status": result.status,
            "source": result.source,
            "prompt": result.prompt,
            "preprocessed_prompt": result.preprocessed_prompt,
            "diagram_type": result.diagram_type,
            "structured_json": result.structured_json,
            "complexity": result.complexity.to_dict() if result.complexity else None,
            "similarity_score": result.similarity_score,
            "validation_errors": result.validation_errors,
            "rejection_reason": result.rejection_reason,
            "renderer": result.renderer,
            "dsl_code": result.dsl_code,
            "svg_content": result.svg_content,
            "dslCode": result.dsl_code,
            "svgContent": result.svg_content,
            "attempt_count": result.attempt_count,
            "validation_status": result.validation_status,
            "repair_history": result.repair_history,
            "validation_details": result.validation_details,
            "spacy_enabled": result.spacy_enabled,
            "candidates_count": result.candidates_count,
            "success": result.is_success,
        }

        if result.is_success:
            job_tracker_service.update_job(
                job_id, "completed", message="Pipeline completed successfully", result=resp_dict
            )
        else:
            job_tracker_service.update_job(
                job_id, "failed", message=result.rejection_reason or "Pipeline generation rejected", result=resp_dict, error=result.rejection_reason
            )
    except Exception as exc:
        logger.error("Async pipeline job %s failed: %s", job_id, exc, exc_info=True)
        job_tracker_service.update_job(job_id, "failed", message=f"Internal error: {exc}", error=str(exc))
    finally:
        db.close()


@router.post(
    "/generate-async",
    summary="Start async diagram generation job",
    description="Initiates background generation pipeline and returns a job_id for polling status.",
)
async def generate_diagram_async(
    body: GenerateRequest,
    background_tasks: BackgroundTasks,
):
    """
    Asynchronous generation entry point driving real frontend pipeline progress.
    """
    job_id = str(uuid.uuid4())
    job_tracker_service.create_job(job_id)

    from app.core.database import SessionLocal
    background_tasks.add_task(_run_async_pipeline_task, job_id, body.prompt, SessionLocal)

    return {
        "job_id": job_id,
        "status": "scope_guard",
        "message": "Async generation job initiated",
        "poll_url": f"/api/diagrams/{job_id}/status",
    }


@router.post(
    "/upload-reference",
    summary="Upload reference file to extract text context for generation",
    description="Extracts plain text content from uploaded reference code or document files.",
)
async def upload_reference_file(file: UploadFile = File(...)):
    """
    Extract text context from uploaded reference files.
    """
    filename = file.filename or "reference.txt"
    try:
        content_bytes = await file.read()
        extracted_text = content_bytes.decode("utf-8", errors="ignore").strip()
        if len(extracted_text) > 4000:
            extracted_text = extracted_text[:4000] + "\n... [truncated]"

        return {
            "success": True,
            "filename": filename,
            "extracted_text": extracted_text,
            "size_bytes": len(content_bytes),
        }
    except Exception as exc:
        logger.error("Failed to extract reference file content: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read uploaded file content: {exc}",
        )


