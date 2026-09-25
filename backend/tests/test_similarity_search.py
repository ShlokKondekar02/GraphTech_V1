"""
Sprint 1 — Integration tests for the similarity search pipeline.

These tests use the REAL PostgreSQL database (not SQLite).  They:
  1. Insert a known seeded diagram with a known embedding into a temporary
     test schema / table, or directly into the real diagram_requests table
     under a temporary row that is cleaned up after the test.
  2. Assert that a semantically close prompt (after embedding through Voyage)
     returns that diagram as the top candidate with score >= threshold.
  3. Assert that a completely unrelated prompt returns nothing above threshold.

IMPORTANT: These tests call the REAL Voyage AI API.  They are skipped
automatically when VOYAGE_API_KEY is not set, so Sprint 0 CI passes without
needing the key.

Run with:
  pytest tests/test_similarity_search.py -v -m similarity
"""

from __future__ import annotations

import uuid
import os
import pytest

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# ── skip guard ─────────────────────────────────────────────────────────────────
VOYAGE_KEY_AVAILABLE = bool(settings.VOYAGE_API_KEY)

pytestmark = pytest.mark.similarity


# ── Real Postgres session fixture (separate from the SQLite test session) ──────

@pytest.fixture(scope="module")
def pg_engine():
    """Create a real Postgres engine for similarity search tests."""
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def pg_session(pg_engine):
    """Yield a session against the real Postgres DB."""
    Session = sessionmaker(bind=pg_engine, autocommit=False, autoflush=False)
    session = Session()
    yield session
    session.close()


# ── Helper: insert a DiagramRequest row with a known embedding ─────────────────

def _insert_seeded_row(session, prompt: str, embedding: list[float], dtype: str = "system") -> str:
    """
    Insert a row directly into diagram_requests (bypassing the ORM so we can
    cast the vector correctly) and return its UUID string.
    """
    row_id = str(uuid.uuid4())
    vec_str = "[" + ",".join(str(v) for v in embedding) + "]"
    session.execute(
        text(
            """
            INSERT INTO diagram_requests
                (id, prompt, embedding, diagram_type, complexity, renderer, status)
            VALUES
                (:id, :prompt, CAST(:vec AS vector), :dtype, 'moderate', 'mermaid', 'seeded')
            """
        ),
        {"id": row_id, "prompt": prompt, "vec": vec_str, "dtype": dtype},
    )
    session.commit()
    return row_id


def _delete_row(session, row_id: str) -> None:
    session.execute(text("DELETE FROM diagram_requests WHERE id = :id"), {"id": row_id})
    session.commit()


# ── Tests ──────────────────────────────────────────────────────────────────────


@pytest.mark.skipif(not VOYAGE_KEY_AVAILABLE, reason="VOYAGE_API_KEY not configured")
class TestSimilaritySearchNearMatch:
    """
    DoD item 1: A known prompt near a seeded diagram returns it as the top
    match with score >= threshold.
    DoD item 3: Returns multiple ranked candidates with real scores.
    """

    SEEDED_PROMPT = (
        "Design a microservices architecture for an e-commerce platform "
        "with user, product, order, payment, and notification services"
    )
    QUERY_PROMPT = (
        "Microservices e-commerce system with user service, product catalog, "
        "order management, payments, and notifications"
    )

    def test_near_prompt_returns_seeded_as_top_match(self, pg_session):
        """
        Embed the SEEDED_PROMPT, store it, then embed the QUERY_PROMPT and
        run similarity search.  The seeded row must be the top result with
        similarity >= threshold.
        """
        from app.services.embedding_service import EmbeddingService

        svc = EmbeddingService()

        # Embed the reference (seeded) prompt
        seed_embedding = svc.generate_embedding(self.SEEDED_PROMPT)
        assert len(seed_embedding) == 1024

        # Insert as a known row
        row_id = _insert_seeded_row(pg_session, self.SEEDED_PROMPT, seed_embedding)

        try:
            # Embed the semantically close query
            query_embedding = svc.generate_embedding(self.QUERY_PROMPT)
            assert len(query_embedding) == 1024

            # Run similarity search
            candidates = svc.find_similar_diagrams(
                db=pg_session,
                embedding=query_embedding,
                top_k=5,
                threshold=settings.SIMILARITY_THRESHOLD,
            )

            assert len(candidates) >= 1, (
                f"Expected at least one candidate above threshold {settings.SIMILARITY_THRESHOLD}, "
                f"got none."
            )

            # Top candidate must be our seeded row
            top = candidates[0]
            assert top.id == row_id, (
                f"Expected top match to be the seeded row ({row_id}), "
                f"got {top.id} (prompt: {top.prompt[:60]})"
            )
            assert top.similarity >= settings.SIMILARITY_THRESHOLD, (
                f"Expected similarity >= {settings.SIMILARITY_THRESHOLD}, got {top.similarity:.4f}"
            )

        finally:
            _delete_row(pg_session, row_id)

    def test_results_are_ranked_by_similarity_descending(self, pg_session):
        """
        DoD item 3: multiple candidates are returned with real scores, sorted
        descending by similarity.
        """
        from app.services.embedding_service import EmbeddingService

        svc = EmbeddingService()

        # Insert two related rows
        prompt_a = "Microservices architecture with API gateway and multiple backend services"
        prompt_b = "Service mesh architecture with sidecar proxies and inter-service communication"

        emb_a = svc.generate_embedding(prompt_a)
        emb_b = svc.generate_embedding(prompt_b)
        id_a = _insert_seeded_row(pg_session, prompt_a, emb_a)
        id_b = _insert_seeded_row(pg_session, prompt_b, emb_b)

        try:
            query_emb = svc.generate_embedding(
                "Build a microservices system with an API gateway routing to multiple services"
            )

            candidates = svc.find_similar_diagrams(
                db=pg_session,
                embedding=query_emb,
                top_k=10,
                threshold=0.0,  # threshold=0 so we see all candidates
            )

            scores = [c.similarity for c in candidates]
            assert scores == sorted(scores, reverse=True), (
                f"Candidates are not sorted descending by similarity: {scores}"
            )

            # Each score must be a real float in [0, 1]
            for c in candidates:
                assert 0.0 <= c.similarity <= 1.0, f"Score out of range: {c.similarity}"

        finally:
            _delete_row(pg_session, id_a)
            _delete_row(pg_session, id_b)


@pytest.mark.skipif(not VOYAGE_KEY_AVAILABLE, reason="VOYAGE_API_KEY not configured")
class TestSimilaritySearchUnrelatedPrompt:
    """
    DoD item 2: An unrelated prompt returns nothing above threshold.
    """

    UNRELATED_PROMPT = (
        "Write a haiku about autumn leaves falling in the mountain breeze"
    )

    def test_unrelated_prompt_returns_no_results_above_threshold(self, pg_session):
        """
        A prompt about poetry/nature should not match any architecture diagram
        above the configured similarity threshold.
        """
        from app.services.embedding_service import EmbeddingService

        svc = EmbeddingService()
        query_embedding = svc.generate_embedding(self.UNRELATED_PROMPT)

        candidates = svc.find_similar_diagrams(
            db=pg_session,
            embedding=query_embedding,
            top_k=settings.SIMILARITY_TOP_K,
            threshold=settings.SIMILARITY_THRESHOLD,
        )

        # No diagram about poetry/haiku should be seeded, so we expect 0
        # (or all scores are below threshold — the WHERE clause handles this)
        for c in candidates:
            assert c.similarity < settings.SIMILARITY_THRESHOLD, (
                f"Unexpected high-similarity match for unrelated prompt: "
                f"prompt={c.prompt[:60]!r}  score={c.similarity:.4f}"
            )


@pytest.mark.skipif(not VOYAGE_KEY_AVAILABLE, reason="VOYAGE_API_KEY not configured")
class TestSimilaritySearchReturnStructure:
    """Verify that candidates include all expected fields."""

    def test_candidate_fields_are_populated(self, pg_session):
        from app.services.embedding_service import EmbeddingService, SimilarityCandidate

        svc = EmbeddingService()

        prompt = "Three-tier web application with load balancer, application server, and database"
        embedding = svc.generate_embedding(prompt)
        row_id = _insert_seeded_row(pg_session, prompt, embedding, dtype="infrastructure")

        try:
            candidates = svc.find_similar_diagrams(
                db=pg_session,
                embedding=embedding,  # exact same embedding → similarity ~1.0
                top_k=5,
                threshold=0.0,
            )

            matching = [c for c in candidates if c.id == row_id]
            assert matching, f"Inserted row {row_id} not found in results"

            c = matching[0]
            assert isinstance(c, SimilarityCandidate)
            assert c.id == row_id
            assert isinstance(c.prompt, str) and len(c.prompt) > 0
            assert isinstance(c.similarity, float)
            assert c.similarity > 0.99, f"Self-similarity should be ~1.0, got {c.similarity}"

        finally:
            _delete_row(pg_session, row_id)
