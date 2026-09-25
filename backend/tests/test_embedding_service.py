"""
Sprint 1 — Unit tests for the Voyage AI embedding client.

These tests do NOT call the real Voyage API.  Instead they mock the
voyageai.Client to exercise:
  1. Normal successful call → returns a 1024-dim embedding
  2. Timeout → raises EmbeddingTimeoutError
  3. Malformed response (embeddings = []) → raises EmbeddingResponseError
  4. Malformed response (embeddings = None attr) → raises EmbeddingResponseError
  5. Rate-limit error (429) after retries → raises EmbeddingRateLimitError
  6. Generic API error → raises EmbeddingAPIError

Run with:
  pytest tests/test_embedding_service.py -v
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.embedding_service import (
    EmbeddingAPIError,
    EmbeddingResponseError,
    EmbeddingRateLimitError,
    EmbeddingTimeoutError,
    EmbeddingService,
)


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_voyage_result(dim: int = 1024) -> SimpleNamespace:
    """Return a fake Voyage result object that looks like the real one."""
    return SimpleNamespace(embeddings=[[float(i % 100) / 100.0 for i in range(dim)]])


def _make_service_with_mock_client(mock_client) -> EmbeddingService:
    """Create an EmbeddingService and inject a pre-built mock client."""
    svc = EmbeddingService()
    svc._client = mock_client
    return svc


# ── Test 1: successful call ────────────────────────────────────────────────────


class TestEmbeddingSuccess:
    def test_returns_1024_dim_list(self):
        """Normal call returns a list of 1024 floats."""
        fake_result = _make_voyage_result(1024)
        mock_client = MagicMock()
        mock_client.embed.return_value = fake_result

        svc = _make_service_with_mock_client(mock_client)
        embedding = svc.generate_embedding("Design a microservices system")

        assert isinstance(embedding, list)
        assert len(embedding) == 1024
        assert all(isinstance(v, float) for v in embedding)

    def test_calls_voyage_with_correct_model(self):
        """The Voyage client is called with the configured model name."""
        from app.core.config import settings

        fake_result = _make_voyage_result(1024)
        mock_client = MagicMock()
        mock_client.embed.return_value = fake_result

        svc = _make_service_with_mock_client(mock_client)
        svc.generate_embedding("some prompt")

        mock_client.embed.assert_called_once()
        call_kwargs = mock_client.embed.call_args
        # second positional arg or keyword 'model'
        called_model = call_kwargs[1].get("model") or call_kwargs[0][1]
        assert called_model == settings.VOYAGE_MODEL


# ── Test 2: timeout ────────────────────────────────────────────────────────────


class TestEmbeddingTimeout:
    def test_raises_timeout_error(self):
        """When the Voyage call hangs longer than the timeout, EmbeddingTimeoutError is raised."""

        def _slow_embed(*args, **kwargs):
            time.sleep(60)  # simulate a hung request

        mock_client = MagicMock()
        mock_client.embed.side_effect = _slow_embed

        svc = _make_service_with_mock_client(mock_client)

        # Patch the timeout to 0.2 s so the test runs fast
        with patch("app.services.embedding_service.settings") as mock_settings:
            mock_settings.VOYAGE_TIMEOUT_SECONDS = 0.2
            mock_settings.VOYAGE_MODEL = "voyage-3-large"
            mock_settings.VOYAGE_MAX_RETRIES = 1

            with pytest.raises(EmbeddingTimeoutError):
                svc.generate_embedding("slow prompt")


# ── Test 3: malformed / empty response ────────────────────────────────────────


class TestEmbeddingMalformedResponse:
    def test_empty_embeddings_list_raises_response_error(self):
        """When embeddings list is empty, EmbeddingResponseError is raised."""
        fake_result = SimpleNamespace(embeddings=[])
        mock_client = MagicMock()
        mock_client.embed.return_value = fake_result

        svc = _make_service_with_mock_client(mock_client)

        with pytest.raises(EmbeddingResponseError, match="empty"):
            svc.generate_embedding("test prompt")

    def test_none_embeddings_attr_raises_response_error(self):
        """When the result has no embeddings attribute, EmbeddingResponseError is raised."""
        fake_result = SimpleNamespace(embeddings=None)
        mock_client = MagicMock()
        mock_client.embed.return_value = fake_result

        svc = _make_service_with_mock_client(mock_client)

        with pytest.raises(EmbeddingResponseError):
            svc.generate_embedding("test prompt")

    def test_none_result_raises_response_error(self):
        """When the Voyage client returns None, EmbeddingResponseError is raised."""
        mock_client = MagicMock()
        mock_client.embed.return_value = None

        svc = _make_service_with_mock_client(mock_client)

        with pytest.raises(EmbeddingResponseError, match="None"):
            svc.generate_embedding("test prompt")

    def test_empty_inner_vector_raises_response_error(self):
        """When embeddings[0] is an empty list, EmbeddingResponseError is raised."""
        fake_result = SimpleNamespace(embeddings=[[]])
        mock_client = MagicMock()
        mock_client.embed.return_value = fake_result

        svc = _make_service_with_mock_client(mock_client)

        with pytest.raises(EmbeddingResponseError):
            svc.generate_embedding("test prompt")


# ── Test 4: rate-limit error ───────────────────────────────────────────────────


class TestEmbeddingRateLimit:
    def test_rate_limit_raises_rate_limit_error(self):
        """When Voyage returns 429, EmbeddingRateLimitError is raised after retries."""
        mock_client = MagicMock()
        mock_client.embed.side_effect = Exception("HTTP 429 Too Many Requests: rate limit exceeded")

        svc = _make_service_with_mock_client(mock_client)

        with patch("app.services.embedding_service.settings") as mock_settings:
            mock_settings.VOYAGE_TIMEOUT_SECONDS = 5.0
            mock_settings.VOYAGE_MODEL = "voyage-3-large"
            mock_settings.VOYAGE_MAX_RETRIES = 2

            with pytest.raises(EmbeddingRateLimitError):
                svc.generate_embedding("rate-limited prompt")


# ── Test 5: generic API error ─────────────────────────────────────────────────


class TestEmbeddingAPIError:
    def test_generic_exception_raises_api_error(self):
        """Non-rate-limit exceptions from Voyage are wrapped as EmbeddingAPIError."""
        mock_client = MagicMock()
        mock_client.embed.side_effect = Exception("Internal server error 500")

        svc = _make_service_with_mock_client(mock_client)

        with pytest.raises(EmbeddingAPIError):
            svc.generate_embedding("error prompt")
