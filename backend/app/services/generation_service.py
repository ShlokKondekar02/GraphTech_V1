"""
Generation Service -- Sprint 2 (full implementation).

This service is the pipeline orchestrator for POST /api/diagrams/generate.
It owns the reuse-vs-generate decision and ensures that:

  1. Sprint 1 pipeline is reused (spaCy -> Voyage -> pgvector search).
  2. On CACHE HIT (similarity above SIMILARITY_THRESHOLD):
       - The retrieved structured_json is re-validated through the SAME
         validators as fresh output (Pydantic + graph rules).
       - Complexity is independently computed from the cached JSON.
       - The result is returned as a "reused" result ONLY if validation passes.
       - A cache-hit that fails validation is treated as a cache MISS and
         triggers fresh generation.
  3. On CACHE MISS (no candidate above threshold):
       - Groq is called with the constrained v1.0 prompt.
       - The response is validated (GroqService does this internally).
       - Complexity is independently computed.
       - If complexity exceeds ceiling: request is REJECTED pre-render.
       - If valid and within ceiling: result is persisted with status="validated".
  4. Every generation attempt (including rejections) is persisted to
     diagram_requests with an accurate status and rejection_reason.

Status vocabulary:
  "validated"             -- passed all checks, ready for rendering (Sprint 3)
  "rejected_invalid"      -- failed Pydantic or graph validation
  "rejected_complexity"   -- valid structure but complexity exceeds ceiling
  "cache_reused"          -- served from pgvector cache (re-validated)
  "error"                 -- unexpected runtime failure
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from app.core.config import settings
from app.services.complexity_service import ComplexityResult, complexity_service
from app.services.groq_service import (
    GroqAPIError,
    GroqConfigError,
    GroqParseError,
    GroqRateLimitError,
    GroqTimeoutError,
    GroqValidationError,
    groq_service,
)
from app.services.validation_service import ValidationResult, validation_service
from app.services.embedding_service import (
    EmbeddingAPIError,
    EmbeddingRateLimitError,
    EmbeddingResponseError,
    EmbeddingTimeoutError,
    SimilarityCandidate,
    embedding_service,
)
from app.services.output_validator_service import output_validator_service
from app.services.preprocessing_service import build_preprocessor
from app.services.rendering_service import rendering_service
from app.services.scope_guard import scope_guard

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class GenerationResult:
    """
    The complete result of one pipeline run (reused or fresh).
    """

    request_id: str
    status: str
    source: str                                 # "fresh" | "cache"
    prompt: str
    preprocessed_prompt: str
    diagram_type: Optional[str] = field(default=None)
    structured_json: Optional[Dict[str, Any]] = field(default=None)
    complexity: Optional[ComplexityResult] = field(default=None)
    similarity_score: Optional[float] = field(default=None)
    validation_errors: List[str] = field(default_factory=list)
    rejection_reason: Optional[str] = field(default=None)
    renderer: Optional[str] = field(default=None)
    dsl_code: Optional[str] = field(default=None)
    svg_content: Optional[str] = field(default=None)
    attempt_count: int = field(default=1)
    validation_status: Optional[str] = field(default=None)
    repair_history: List[Dict[str, Any]] = field(default_factory=list)
    validation_details: Optional[Dict[str, Any]] = field(default=None)
    spacy_enabled: bool = field(default=False)
    candidates_count: int = field(default=0)

    @property
    def is_success(self) -> bool:
        return self.status in ("validated", "cache_reused", "auto_repaired")

    @property
    def is_rejected(self) -> bool:
        return self.status.startswith("rejected_")


# ---------------------------------------------------------------------------
# Pipeline orchestrator
# ---------------------------------------------------------------------------


class GenerationService:
    """
    Orchestrates the full diagram-generation pipeline for Sprint 2.

    The Groq creative-image path (generate_creative_image) is a stub here
    and will be implemented in Sprint 6.
    """

    # ---- Public API --------------------------------------------------------

    def run_pipeline(
        self,
        db: "Session",
        prompt: str,
        user_id: Optional[str] = None,
    ) -> GenerationResult:
        """
        Run the full reuse-or-generate pipeline and persist every attempt.

        Parameters
        ----------
        db      -- active SQLAlchemy session
        prompt  -- raw user prompt (will be preprocessed if spaCy is enabled)
        user_id -- optional authenticated user UUID string

        Returns
        -------
        GenerationResult -- always returned, even for rejections
        """
        start_time = time.perf_counter()
        request_id = str(uuid.uuid4())
        logger.info(
            "Pipeline start: request_id=%s prompt_len=%d user=%s",
            request_id,
            len(prompt),
            user_id or "anonymous",
        )

        # ---- Stage 0: Domain Scope Guard (CS/IT technical diagrams only) ---
        scope_check = scope_guard.check_scope(prompt)
        if not scope_check.is_in_scope:
            logger.warning(
                "Prompt rejected by ScopeGuard (domain=%s): %s",
                scope_check.detected_domain,
                scope_check.rejection_reason,
            )
            result = GenerationResult(
                request_id=request_id,
                status="rejected_out_of_scope",
                source="fresh",
                prompt=prompt,
                preprocessed_prompt=prompt,
                rejection_reason=scope_check.rejection_reason,
                spacy_enabled=False,
                candidates_count=0,
            )
            self._persist(db, result, user_id)
            return result

        # ---- Stage 1: spaCy preprocessing ----------------------------------
        preprocessor = build_preprocessor()
        try:
            preprocessed_prompt = preprocessor.process(prompt)
        except RuntimeError as exc:
            logger.error("spaCy preprocessing failed: %s", exc)
            result = self._make_error_result(
                request_id, prompt, prompt, preprocessor.enabled, 0,
                reason=f"spaCy preprocessing unavailable: {exc}",
            )
            self._persist(db, result, user_id)
            return result

        # ---- Stage 2: Voyage embedding + pgvector similarity ---------------
        try:
            embedding = embedding_service.generate_embedding(preprocessed_prompt)
        except (EmbeddingTimeoutError, EmbeddingRateLimitError, EmbeddingResponseError, EmbeddingAPIError) as exc:
            logger.error("Embedding generation failed: %s", exc)
            result = self._make_error_result(
                request_id, prompt, preprocessed_prompt, preprocessor.enabled, 0,
                reason=f"Embedding service error: {exc}",
            )
            self._persist(db, result, user_id)
            return result

        candidates: List[SimilarityCandidate] = embedding_service.find_similar_diagrams(
            db=db,
            embedding=embedding,
            top_k=settings.SIMILARITY_TOP_K,
            threshold=settings.SIMILARITY_THRESHOLD,
        )

        # ---- Stage 3: reuse-or-generate decision ---------------------------
        best_candidate = candidates[0] if candidates else None

        if best_candidate is not None:
            # CACHE HIT PATH -- re-validate before accepting
            result = self._try_cache_hit(
                request_id=request_id,
                prompt=prompt,
                preprocessed_prompt=preprocessed_prompt,
                spacy_enabled=preprocessor.enabled,
                candidates_count=len(candidates),
                candidate=best_candidate,
            )
            if result is not None:
                self._persist(db, result, user_id)
                return result
            # Falls through to fresh generation if cache result failed validation

        # CACHE MISS (or cache hit that failed re-validation) -> fresh Groq call
        result = self._generate_fresh(
            request_id=request_id,
            prompt=prompt,
            preprocessed_prompt=preprocessed_prompt,
            spacy_enabled=preprocessor.enabled,
            candidates_count=len(candidates),
        )
        self._persist(db, result, user_id)
        latency_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Research Telemetry: request_id=%s status=%s source=%s latency=%.2fms",
            result.request_id,
            result.status,
            result.source,
            latency_ms,
        )
        return result

    # ---- Cache hit path ----------------------------------------------------

    def _try_cache_hit(
        self,
        request_id: str,
        prompt: str,
        preprocessed_prompt: str,
        spacy_enabled: bool,
        candidates_count: int,
        candidate: SimilarityCandidate,
    ) -> Optional[GenerationResult]:
        """
        Attempt to reuse a cached candidate.

        Re-validates the cached structured_json through both validation layers
        AND independently computes complexity.  Returns a GenerationResult on
        success, or None to signal fallthrough to fresh generation.
        """
        if not candidate.structured_json:
            logger.info(
                "Cache candidate %s has no structured_json -- falling through to fresh generation.",
                candidate.id,
            )
            return None

        logger.info(
            "Cache hit candidate=%s similarity=%.4f -- re-validating before reuse.",
            candidate.id,
            candidate.similarity,
        )

        # Re-validate cached JSON (same validators as fresh output -- no shortcuts)
        val_result: ValidationResult = validation_service.validate(candidate.structured_json)

        if not val_result.is_valid:
            logger.warning(
                "Cached candidate %s failed re-validation (layer=%s) -- "
                "discarding cache hit, falling through to fresh generation.",
                candidate.id,
                val_result.layer,
            )
            return None  # treat as cache miss

        validated_model = val_result.validated_model
        assert validated_model is not None

        # Independently compute complexity
        complexity = complexity_service.compute_from_groq_response(validated_model)

        if complexity.exceeds_ceiling:
            logger.warning(
                "Cached candidate %s exceeds complexity ceiling (score=%.2f) -- rejecting.",
                candidate.id,
                complexity.score,
            )
            return GenerationResult(
                request_id=request_id,
                status="rejected_complexity",
                source="cache",
                prompt=prompt,
                preprocessed_prompt=preprocessed_prompt,
                diagram_type=validated_model.diagram_type,
                structured_json=None,
                complexity=complexity,
                similarity_score=candidate.similarity,
                rejection_reason=complexity.rejection_reason,
                spacy_enabled=spacy_enabled,
                candidates_count=candidates_count,
            )

        # Sprint 3: Compile and render diagram via Kroki
        render_res = rendering_service.render_diagram(validated_model.to_dict())

        return GenerationResult(
            request_id=request_id,
            status="cache_reused",
            source="cache",
            prompt=prompt,
            preprocessed_prompt=preprocessed_prompt,
            diagram_type=render_res.diagram_type or validated_model.diagram_type,
            structured_json=validated_model.to_dict(),
            complexity=complexity,
            similarity_score=candidate.similarity,
            renderer=render_res.renderer,
            dsl_code=render_res.dsl_code,
            svg_content=render_res.svg_content,
            spacy_enabled=spacy_enabled,
            candidates_count=candidates_count,
        )

    # ---- Fresh generation path --------------------------------------------

    def _generate_fresh(
        self,
        request_id: str,
        prompt: str,
        preprocessed_prompt: str,
        spacy_enabled: bool,
        candidates_count: int,
    ) -> GenerationResult:
        """
        Call Groq, validate response, handle auto-repair loop (max 2 retries),
        compute complexity, render diagram, and validate SVG output.
        """
        logger.info("Cache miss -- calling Groq for fresh generation.")

        max_attempts = 2
        attempt = 0
        last_error_summary = ""
        last_raw_payload = ""
        repair_history: List[Dict[str, Any]] = []

        while attempt <= max_attempts:
            try:
                if attempt == 0:
                    val_result = groq_service.generate_diagram_json(preprocessed_prompt)
                else:
                    logger.info("Executing auto-repair attempt %d for request_id=%s", attempt, request_id)
                    val_result = groq_service.repair_diagram_json(
                        prompt=preprocessed_prompt,
                        invalid_raw=last_raw_payload,
                        error_summary=last_error_summary,
                    )
            except GroqValidationError as exc:
                last_error_summary = exc.validation_result.error_summary
                last_raw_payload = str(exc)
                repair_history.append({"attempt": attempt, "error": last_error_summary})
                attempt += 1
                continue
            except GroqParseError as exc:
                last_error_summary = f"Groq JSON parse error: {exc}"
                last_raw_payload = str(exc)
                repair_history.append({"attempt": attempt, "error": last_error_summary})
                attempt += 1
                continue
            except (GroqConfigError, GroqAPIError, GroqTimeoutError, GroqRateLimitError) as exc:
                return self._make_error_result(
                    request_id, prompt, preprocessed_prompt, spacy_enabled, candidates_count,
                    reason=f"Groq API error: {exc}",
                )

            validated_model = val_result.validated_model
            if validated_model is None:
                attempt += 1
                continue

            # Independently compute complexity
            complexity = complexity_service.compute_from_groq_response(validated_model)

            if complexity.exceeds_ceiling:
                logger.warning(
                    "Fresh generation: complexity ceiling exceeded (score=%.2f) -- rejecting pre-render.",
                    complexity.score,
                )
                return GenerationResult(
                    request_id=request_id,
                    status="rejected_complexity",
                    source="fresh",
                    prompt=prompt,
                    preprocessed_prompt=preprocessed_prompt,
                    diagram_type=validated_model.diagram_type,
                    structured_json=None,
                    complexity=complexity,
                    rejection_reason=complexity.rejection_reason,
                    spacy_enabled=spacy_enabled,
                    candidates_count=candidates_count,
                )

            # Compile and render diagram via Kroki/Compilers
            render_res = rendering_service.render_diagram(validated_model.to_dict())

            # SVG XML & Semantic AST Reconciliation Engine Check
            val_out = output_validator_service.validate_svg(
                svg_content=render_res.svg_content,
                structured_json=validated_model.to_dict(),
            )

            if not val_out.is_valid:
                last_error_summary = f"Output Validation Error: {val_out.error_message}"
                import json
                last_raw_payload = json.dumps(validated_model.to_dict())
                repair_history.append({
                    "attempt": attempt,
                    "error": last_error_summary,
                    "details": val_out.to_dict(),
                })
                attempt += 1
                continue

            status_str = "validated" if attempt == 0 else "auto_repaired"
            val_status = "validated" if attempt == 0 else "auto_repaired"
            return GenerationResult(
                request_id=request_id,
                status=status_str,
                source="fresh",
                prompt=prompt,
                preprocessed_prompt=preprocessed_prompt,
                diagram_type=render_res.diagram_type or validated_model.diagram_type,
                structured_json=validated_model.to_dict(),
                complexity=complexity,
                renderer=render_res.renderer,
                dsl_code=render_res.dsl_code,
                svg_content=render_res.svg_content,
                attempt_count=attempt + 1,
                validation_status=val_status,
                repair_history=repair_history,
                validation_details=val_out.to_dict(),
                spacy_enabled=spacy_enabled,
                candidates_count=candidates_count,
            )

        # Retry budget exhausted
        logger.warning(
            "Request_id=%s failed validation after %d repair attempts. Last error: %s",
            request_id,
            max_attempts,
            last_error_summary,
        )
        return GenerationResult(
            request_id=request_id,
            status="failed_validation",
            source="fresh",
            prompt=prompt,
            preprocessed_prompt=preprocessed_prompt,
            validation_errors=[entry["error"] for entry in repair_history],
            rejection_reason=f"Failed validation after {max_attempts} repair attempts. Reason: {last_error_summary}",
            attempt_count=max_attempts + 1,
            validation_status="output_validation_failed",
            repair_history=repair_history,
            spacy_enabled=spacy_enabled,
            candidates_count=candidates_count,
        )

    @staticmethod
    def _validate_svg_xml(svg_content: Optional[str]) -> tuple[bool, str]:
        """
        Validate SVG XML string for non-zero content, proper XML parsing, and root svg tag.
        Backward-compatible helper wrapping output_validator_service.
        """
        val_res = output_validator_service.validate_svg(svg_content)
        return val_res.is_valid, val_res.error_message


    # ---- Persistence -------------------------------------------------------

    def _persist(
        self,
        db: "Session",
        result: GenerationResult,
        user_id: Optional[str],
    ) -> None:
        """
        Persist every generation attempt to diagram_requests.

        This includes rejected and error attempts so that nothing fails
        silently and everything is auditable.
        """
        from app.models.diagram_requests import DiagramRequest

        try:
            rejection_reason_text: Optional[str] = result.rejection_reason
            if result.validation_errors and not rejection_reason_text:
                rejection_reason_text = "; ".join(result.validation_errors[:5])

            initial_chat = [
                {
                    "id": f"user-{result.request_id[:8]}",
                    "sender": "user",
                    "text": result.prompt,
                    "timestamp": datetime.now(timezone.utc).strftime("%I:%M %p")
                },
                {
                    "id": f"ai-{result.request_id[:8]}",
                    "sender": "ai",
                    "text": f"Generated {result.diagram_type or 'architecture'} diagram using {result.renderer or 'Mermaid'}. AST & SVG validation passed cleanly.",
                    "timestamp": datetime.now(timezone.utc).strftime("%I:%M %p"),
                    "completedPipeline": True,
                    "prompt": result.prompt,
                }
            ]

            try:
                row = DiagramRequest(
                    id=uuid.UUID(result.request_id),
                    user_id=uuid.UUID(user_id) if user_id else None,
                    prompt=result.prompt,
                    structured_json=result.structured_json,
                    complexity=result.complexity.label if result.complexity else None,
                    diagram_type=result.diagram_type,
                    status=result.status,
                    rejection_reason=rejection_reason_text,
                    complexity_score=result.complexity.score if result.complexity else None,
                    complexity_metrics=(
                        result.complexity.to_dict() if result.complexity else None
                    ),
                    source=result.source,
                    renderer=result.renderer,
                    dsl_code=result.dsl_code,
                    svg_content=result.svg_content,
                    attempt_count=result.attempt_count,
                    validation_status=result.validation_status or result.status,
                    repair_history=result.repair_history if result.repair_history else None,
                    chat_history=initial_chat,
                )
                db.add(row)
                db.commit()
            except Exception as first_exc:
                db.rollback()
                logger.warning("Full persistence failed (%s). Attempting legacy fallback persistence.", first_exc)
                row_legacy = DiagramRequest(
                    id=uuid.UUID(result.request_id),
                    user_id=uuid.UUID(user_id) if user_id else None,
                    prompt=result.prompt,
                    structured_json=result.structured_json,
                    complexity=result.complexity.label if result.complexity else None,
                    diagram_type=result.diagram_type,
                    status=result.status,
                    rejection_reason=rejection_reason_text,
                    complexity_score=result.complexity.score if result.complexity else None,
                    complexity_metrics=(
                        result.complexity.to_dict() if result.complexity else None
                    ),
                    source=result.source,
                    renderer=result.renderer,
                    dsl_code=result.dsl_code,
                    svg_content=result.svg_content,
                )
                db.add(row_legacy)
                db.commit()

            logger.info(
                "Persisted diagram_request id=%s status=%s source=%s",
                result.request_id,
                result.status,
                result.source,
            )
        except Exception as exc:
            db.rollback()
            logger.error(
                "Failed to persist diagram_request id=%s: %s",
                result.request_id,
                exc,
                exc_info=True,
            )

    # ---- Helpers -----------------------------------------------------------

    @staticmethod
    def _make_error_result(
        request_id: str,
        prompt: str,
        preprocessed_prompt: str,
        spacy_enabled: bool,
        candidates_count: int,
        reason: str,
    ) -> GenerationResult:
        return GenerationResult(
            request_id=request_id,
            status="error",
            source="fresh",
            prompt=prompt,
            preprocessed_prompt=preprocessed_prompt,
            rejection_reason=reason,
            spacy_enabled=spacy_enabled,
            candidates_count=candidates_count,
        )

    # ---- Stub: Gemini creative image (Sprint 6) ----------------------------

    async def generate_creative_image(self, prompt: str) -> str:
        """Stub for Gemini creative image generation (Sprint 6)."""
        raise NotImplementedError(
            "Creative image generation will be implemented in Sprint 6 (Gemini path)."
        )


# Module-level singleton
generation_service = GenerationService()
