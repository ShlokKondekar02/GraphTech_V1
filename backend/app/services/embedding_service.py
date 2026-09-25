"""
Voyage AI embedding client — Sprint 1.

Responsibilities
----------------
1. Generate a 1024-dimension embedding for an input text via Voyage AI's
   ``voyage-3-large`` model (configurable via settings.VOYAGE_MODEL).
2. Run a pgvector cosine-similarity search against the ``diagram_requests``
   table and return the top-k ranked candidates with their real scores.
3. Handle errors explicitly:
   - Network timeout  → EmbeddingTimeoutError
   - Malformed/empty response → EmbeddingResponseError
   - Rate-limit (429) → retried with exponential back-off via tenacity
   - Any other API error → EmbeddingAPIError
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Custom exception hierarchy
# ──────────────────────────────────────────────────────────────────────────────


class EmbeddingError(Exception):
    """Base class for all embedding-related errors."""


class EmbeddingTimeoutError(EmbeddingError):
    """Raised when the Voyage API call times out."""


class EmbeddingResponseError(EmbeddingError):
    """Raised when the Voyage response is malformed or empty."""


class EmbeddingAPIError(EmbeddingError):
    """Raised for non-retryable Voyage API errors (4xx other than 429, 5xx)."""


class EmbeddingRateLimitError(EmbeddingError):
    """Raised when the Voyage API returns 429 (only after all retries exhausted)."""


# ──────────────────────────────────────────────────────────────────────────────
# Result dataclasses
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class SimilarityCandidate:
    """A single ranked result from the similarity search."""

    id: str                          # UUID of the DiagramRequest row (as string)
    prompt: str                      # Original prompt stored in the DB
    similarity: float                # Cosine similarity score (0–1 range)
    structured_json: Optional[dict] = field(default=None)
    diagram_type: Optional[str] = field(default=None)
    complexity: Optional[str] = field(default=None)
    renderer: Optional[str] = field(default=None)


# ──────────────────────────────────────────────────────────────────────────────
# Internal retry helper — only retries on rate-limit (429) errors
# ──────────────────────────────────────────────────────────────────────────────


def _is_rate_limit_error(exc: BaseException) -> bool:
    """Return True if *exc* represents an HTTP 429 rate-limit response."""
    msg = str(exc).lower()
    return "429" in msg or "rate limit" in msg or "rate_limit" in msg


@retry(
    retry=retry_if_exception_type(EmbeddingRateLimitError),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(settings.VOYAGE_MAX_RETRIES),
    reraise=True,
)
def _call_voyage_with_retry(client, texts: list[str], model: str) -> list:
    """
    Call the Voyage embed endpoint and return the raw result object.

    Wrapped by tenacity so 429 errors are automatically retried with
    exponential back-off up to settings.VOYAGE_MAX_RETRIES attempts.
    """
    try:
        result = client.embed(texts, model=model, input_type="query")
    except Exception as exc:
        if _is_rate_limit_error(exc):
            logger.warning("Voyage rate-limit hit, will retry: %s", exc)
            raise EmbeddingRateLimitError(str(exc)) from exc
        raise  # let the caller classify other errors
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Main service class
# ──────────────────────────────────────────────────────────────────────────────


class EmbeddingService:
    """
    Wraps the Voyage AI client with proper error handling, timeouts, and
    pgvector similarity search.

    The Voyage client is instantiated lazily on first use so that the service
    can be imported even when VOYAGE_API_KEY is not configured (e.g. during
    unit tests that mock this class).
    """

    def __init__(self):
        self._client = None

    # ── Lazy Voyage client ──────────────────────────────────────────────────

    def _get_client(self):
        """Return a cached Voyage client, creating it if needed."""
        if self._client is not None:
            return self._client
        try:
            import voyageai  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "voyageai package is not installed.  "
                "Run: pip install voyageai"
            ) from exc

        if not settings.VOYAGE_API_KEY:
            raise EmbeddingAPIError(
                "VOYAGE_API_KEY is not configured.  "
                "Set it in .env before using the embedding service."
            )

        self._client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
        return self._client

    # ── Embedding generation ────────────────────────────────────────────────

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a 1024-dimension embedding for *text* via Voyage AI.

        Raises
        ------
        EmbeddingTimeoutError
            The Voyage API did not respond within settings.VOYAGE_TIMEOUT_SECONDS.
        EmbeddingResponseError
            The response was empty or did not contain a valid embedding.
        EmbeddingRateLimitError
            All retry attempts were exhausted due to rate-limiting.
        EmbeddingAPIError
            Any other non-retryable Voyage API error.
        """
        import signal as _signal  # local import — not available on Windows threads
        import threading

        client = self._get_client()
        model = settings.VOYAGE_MODEL
        timeout = settings.VOYAGE_TIMEOUT_SECONDS

        logger.debug("Requesting Voyage embedding for %d chars of text.", len(text))

        # ── Timeout via threading.Timer (Windows-compatible) ────────────────
        result_holder: dict = {}

        def _do_call():
            try:
                raw = _call_voyage_with_retry(client, [text], model)
                result_holder["result"] = raw
            except Exception as exc:
                result_holder["error"] = exc

        thread = threading.Thread(target=_do_call, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            # Thread is still blocked — we can't kill it, but we raise immediately.
            logger.error(
                "Voyage embedding call timed out after %.1f seconds.", timeout
            )
            raise EmbeddingTimeoutError(
                f"Voyage API did not respond within {timeout:.0f} seconds."
            )

        if "error" in result_holder:
            exc = result_holder["error"]
            if isinstance(exc, (EmbeddingRateLimitError, RetryError)):
                raise EmbeddingRateLimitError(
                    f"Voyage rate-limit: all {settings.VOYAGE_MAX_RETRIES} retries exhausted."
                ) from exc
            logger.error("Voyage API error: %s", exc)
            raise EmbeddingAPIError(str(exc)) from exc

        raw = result_holder.get("result")

        # ── Validate response ───────────────────────────────────────────────
        if raw is None:
            raise EmbeddingResponseError("Voyage returned a None result object.")

        embeddings = getattr(raw, "embeddings", None)
        if not embeddings:
            raise EmbeddingResponseError(
                "Voyage response missing 'embeddings' list or it is empty."
            )

        embedding = embeddings[0]
        if not isinstance(embedding, list) or len(embedding) == 0:
            raise EmbeddingResponseError(
                f"Voyage embedding[0] is not a non-empty list; got: {type(embedding)}"
            )

        logger.debug(
            "Voyage embedding generated successfully (%d dimensions).", len(embedding)
        )
        return embedding

    # ── pgvector similarity search ──────────────────────────────────────────

    def find_similar_diagrams(
        self,
        db: "Session",
        embedding: List[float],
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> List[SimilarityCandidate]:
        """
        Run a cosine-similarity search against the ``diagram_requests`` table.

        Parameters
        ----------
        db:
            Active SQLAlchemy session pointing at the real Postgres database.
        embedding:
            1024-dimension query vector (output of ``generate_embedding``).
        top_k:
            Maximum number of candidates to return.  Defaults to
            ``settings.SIMILARITY_TOP_K``.
        threshold:
            Minimum cosine similarity to include.  Defaults to
            ``settings.SIMILARITY_THRESHOLD``.

        Returns
        -------
        List[SimilarityCandidate]
            Sorted descending by similarity score.  May be empty.
        """
        if top_k is None:
            top_k = settings.SIMILARITY_TOP_K
        if threshold is None:
            threshold = settings.SIMILARITY_THRESHOLD

        # pgvector's cosine *distance* = 1 - cosine_similarity, so:
        #   similarity = 1 - distance
        #   distance   = 1 - threshold  → upper bound for the WHERE clause
        max_distance = 1.0 - threshold

        from sqlalchemy import text  # local import to keep module-level clean

        sql = text(
            """
            SELECT
                id,
                prompt,
                structured_json,
                diagram_type,
                complexity,
                renderer,
                1 - (embedding <=> CAST(:vec AS vector)) AS similarity
            FROM diagram_requests
            WHERE embedding IS NOT NULL
              AND (embedding <=> CAST(:vec AS vector)) <= :max_dist
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT :k
            """
        )

        vec_str = "[" + ",".join(str(v) for v in embedding) + "]"

        rows = db.execute(
            sql,
            {"vec": vec_str, "max_dist": max_distance, "k": top_k},
        ).fetchall()

        candidates = [
            SimilarityCandidate(
                id=str(row.id),
                prompt=row.prompt,
                similarity=float(row.similarity),
                structured_json=row.structured_json,
                diagram_type=row.diagram_type,
                complexity=row.complexity,
                renderer=row.renderer,
            )
            for row in rows
        ]

        logger.info(
            "Similarity search returned %d candidate(s) above threshold %.2f.",
            len(candidates),
            threshold,
        )
        return candidates


# Module-level singleton — used by the API router
embedding_service = EmbeddingService()
