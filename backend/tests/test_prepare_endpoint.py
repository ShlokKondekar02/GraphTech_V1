"""
Sprint 1 — Tests for POST /api/diagrams/prepare endpoint.

Covers:
  - Happy path: mocked embedding + seeded DB row → 200 with candidates
  - spaCy toggle on/off: endpoint behaves correctly in both cases
  - Timeout from Voyage → 504
  - Rate-limit from Voyage → 429
  - Malformed Voyage response → 502
  - Missing Voyage key → 502

All tests use the SQLite test DB from conftest.py (so they run without Postgres)
and mock the embedding_service to avoid real Voyage calls.

Run with:
  pytest tests/test_prepare_endpoint.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from types import SimpleNamespace

import pytest

from app.services.embedding_service import (
    EmbeddingTimeoutError,
    EmbeddingRateLimitError,
    EmbeddingResponseError,
    EmbeddingAPIError,
    SimilarityCandidate,
)


# ── Fake embedding used across tests ──────────────────────────────────────────

FAKE_EMBEDDING = [0.01] * 1024


def _fake_candidate(score: float = 0.92) -> SimilarityCandidate:
    return SimilarityCandidate(
        id="00000000-0000-0000-0000-000000000001",
        prompt="Microservices e-commerce platform",
        similarity=score,
        diagram_type="system",
        complexity="high",
        renderer="mermaid",
        structured_json={"nodes": []},
    )


# ── Helper to patch both embedding methods on the module-level singleton ───────

def _patch_embedding(
    generate_return=None,
    generate_side_effect=None,
    search_return=None,
):
    """
    Return a context manager that patches embedding_service on the diagrams module.
    """
    from app.api import diagrams as diagrams_mod

    mock_svc = MagicMock()

    if generate_side_effect is not None:
        mock_svc.generate_embedding.side_effect = generate_side_effect
    else:
        mock_svc.generate_embedding.return_value = (
            generate_return if generate_return is not None else FAKE_EMBEDDING
        )

    mock_svc.find_similar_diagrams.return_value = (
        search_return if search_return is not None else []
    )

    return patch.object(diagrams_mod, "embedding_service", mock_svc)


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestPrepareEndpointHappyPath:
    def test_returns_200_with_candidate(self, client):
        """Full happy path: mock embedding returns a match, endpoint returns 200."""
        candidate = _fake_candidate(score=0.93)

        with _patch_embedding(search_return=[candidate]):
            resp = client.post(
                "/api/diagrams/prepare",
                json={"prompt": "Microservices architecture for an e-commerce platform"},
            )

        assert resp.status_code == 200
        body = resp.json()

        assert body["original_prompt"] == "Microservices architecture for an e-commerce platform"
        assert isinstance(body["preprocessed_prompt"], str)
        assert body["embedding_dimension"] == 1024
        assert isinstance(body["similarity_threshold"], float)
        assert body["above_threshold"] is True
        assert len(body["candidates"]) == 1
        assert body["candidates"][0]["id"] == "00000000-0000-0000-0000-000000000001"
        assert body["candidates"][0]["similarity"] == pytest.approx(0.93, abs=1e-6)

    def test_returns_200_no_candidates(self, client):
        """When no candidates exceed threshold, above_threshold=False."""
        with _patch_embedding(search_return=[]):
            resp = client.post(
                "/api/diagrams/prepare",
                json={"prompt": "Something with no match in the database"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["above_threshold"] is False
        assert body["candidates"] == []

    def test_multiple_candidates_are_returned(self, client):
        """DoD item 3: multiple ranked candidates with scores are returned."""
        candidates = [
            _fake_candidate(0.95),
            _fake_candidate(0.87),
            _fake_candidate(0.81),
        ]
        # Give them distinct IDs
        candidates[1].id = "00000000-0000-0000-0000-000000000002"
        candidates[2].id = "00000000-0000-0000-0000-000000000003"

        with _patch_embedding(search_return=candidates):
            resp = client.post(
                "/api/diagrams/prepare",
                json={"prompt": "Complex microservices with multiple services"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["candidates"]) == 3
        scores = [c["similarity"] for c in body["candidates"]]
        assert scores == sorted(scores, reverse=True), "Candidates must be sorted descending"


class TestPrepareEndpointSpacyToggle:
    """DoD item 4: spaCy preprocessing can be toggled on/off without breaking the endpoint."""

    def test_spacy_disabled_passes_prompt_unchanged(self, client):
        """When ENABLE_SPACY_PREPROCESSING=False, preprocessed_prompt == original_prompt."""
        original = "Raw prompt with stop words and punctuation!"

        with _patch_embedding():
            with patch("app.api.diagrams.settings") as mock_settings:
                mock_settings.ENABLE_SPACY_PREPROCESSING = False
                mock_settings.SIMILARITY_THRESHOLD = 0.75
                mock_settings.SIMILARITY_TOP_K = 5
                mock_settings.VOYAGE_MODEL = "voyage-3-large"
                mock_settings.VOYAGE_TIMEOUT_SECONDS = 15.0
                mock_settings.VOYAGE_MAX_RETRIES = 3

                resp = client.post(
                    "/api/diagrams/prepare",
                    json={"prompt": original},
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["spacy_enabled"] is False
        assert body["preprocessed_prompt"] == original

    def test_spacy_enabled_transforms_prompt(self, client):
        """When ENABLE_SPACY_PREPROCESSING=True, preprocessed_prompt is transformed."""
        original = "Design a microservices architecture"

        with _patch_embedding():
            with patch("app.api.diagrams.build_preprocessor") as mock_build:
                mock_preprocessor = MagicMock()
                mock_preprocessor.enabled = True
                mock_preprocessor.process.return_value = "design microservices architecture"
                mock_build.return_value = mock_preprocessor

                resp = client.post(
                    "/api/diagrams/prepare",
                    json={"prompt": original},
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["spacy_enabled"] is True
        assert body["preprocessed_prompt"] == "design microservices architecture"
        assert body["original_prompt"] == original  # original is preserved separately


class TestPrepareEndpointErrorHandling:
    def test_voyage_timeout_returns_504(self, client):
        """When Voyage times out, the endpoint returns 504."""
        with _patch_embedding(generate_side_effect=EmbeddingTimeoutError("timed out")):
            resp = client.post(
                "/api/diagrams/prepare",
                json={"prompt": "Will trigger a timeout"},
            )
        assert resp.status_code == 504
        assert "timed out" in resp.json()["detail"].lower()

    def test_voyage_rate_limit_returns_429(self, client):
        """When Voyage rate-limits, the endpoint returns 429."""
        with _patch_embedding(generate_side_effect=EmbeddingRateLimitError("rate limit")):
            resp = client.post(
                "/api/diagrams/prepare",
                json={"prompt": "Will trigger rate limit"},
            )
        assert resp.status_code == 429

    def test_voyage_malformed_response_returns_502(self, client):
        """When Voyage returns a malformed response, the endpoint returns 502."""
        with _patch_embedding(generate_side_effect=EmbeddingResponseError("empty embeddings")):
            resp = client.post(
                "/api/diagrams/prepare",
                json={"prompt": "Will trigger bad response"},
            )
        assert resp.status_code == 502

    def test_voyage_api_error_returns_502(self, client):
        """When Voyage returns a generic API error, the endpoint returns 502."""
        with _patch_embedding(generate_side_effect=EmbeddingAPIError("key not configured")):
            resp = client.post(
                "/api/diagrams/prepare",
                json={"prompt": "Will trigger API error"},
            )
        assert resp.status_code == 502

    def test_empty_prompt_returns_422(self, client):
        """An empty prompt is rejected by the Pydantic schema with 422."""
        resp = client.post("/api/diagrams/prepare", json={"prompt": ""})
        assert resp.status_code == 422

    def test_missing_prompt_returns_422(self, client):
        """A missing prompt field is rejected with 422."""
        resp = client.post("/api/diagrams/prepare", json={})
        assert resp.status_code == 422
