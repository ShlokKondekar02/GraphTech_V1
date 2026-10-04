"""
Kroki HTTP Client (Sprint 3).

Connects to Kroki open-source diagram rendering engine via HTTP API:
  POST /{renderer}/svg
Supports timeouts, retries, and both synchronous and asynchronous execution.
"""

import logging
import time
from typing import Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class KrokiError(Exception):
    """Base exception for Kroki rendering client."""
    pass


class KrokiConnectionError(KrokiError):
    """Network connection failure communicating with Kroki."""
    pass


class KrokiTimeoutError(KrokiError):
    """Kroki API request timed out."""
    pass


class KrokiRenderError(KrokiError):
    """Kroki returned an error while compiling/rendering diagram syntax."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Kroki render failed (HTTP {status_code}): {message}")


# ---------------------------------------------------------------------------
# Client Implementation
# ---------------------------------------------------------------------------


class KrokiClient:
    """HTTP client for Kroki API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        self.base_url = (base_url or settings.KROKI_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.KROKI_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.KROKI_MAX_RETRIES

    def _build_url(self, renderer: str) -> str:
        clean_renderer = renderer.lower().strip()
        return f"{self.base_url}/{clean_renderer}/svg"

    def render_sync(self, renderer: str, dsl_code: str) -> str:
        """
        Synchronously compile DSL code into an SVG via Kroki.

        Parameters
        ----------
        renderer : str
            One of 'mermaid', 'plantuml', 'graphviz', etc.
        dsl_code : str
            Raw diagram DSL source text.

        Returns
        -------
        str
            SVG markup string.
        """
        url = self._build_url(renderer)
        headers = {"Content-Type": "text/plain; charset=utf-8", "Accept": "image/svg+xml"}
        body = dsl_code.encode("utf-8")

        last_exc: Optional[Exception] = None

        with httpx.Client(timeout=self.timeout) as client:
            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.debug(
                        "Kroki render attempt %d/%d url=%s dsl_len=%d",
                        attempt,
                        self.max_retries,
                        url,
                        len(dsl_code),
                    )
                    resp = client.post(url, content=body, headers=headers)

                    if resp.status_code == 200:
                        return resp.text

                    if resp.status_code in (400, 422):
                        # Client syntax error from diagram code
                        raise KrokiRenderError(resp.status_code, resp.text[:500])

                    # Server side error, retry if attempts remain
                    if attempt < self.max_retries:
                        time.sleep(0.5 * attempt)
                        continue

                    raise KrokiRenderError(resp.status_code, resp.text[:500])

                except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
                    last_exc = exc
                    logger.warning("Kroki timeout on attempt %d: %s", attempt, exc)
                    if attempt < self.max_retries:
                        time.sleep(0.5 * attempt)
                        continue
                    raise KrokiTimeoutError(f"Kroki timed out after {self.max_retries} attempts: {exc}") from exc

                except (httpx.ConnectError, httpx.NetworkError) as exc:
                    last_exc = exc
                    logger.warning("Kroki connection error on attempt %d: %s", attempt, exc)
                    if attempt < self.max_retries:
                        time.sleep(0.5 * attempt)
                        continue
                    raise KrokiConnectionError(f"Could not connect to Kroki at {self.base_url}: {exc}") from exc

        raise KrokiError(f"Kroki render failed: {last_exc}")

    async def render_async(self, renderer: str, dsl_code: str) -> str:
        """
        Asynchronously compile DSL code into an SVG via Kroki.
        """
        import asyncio

        url = self._build_url(renderer)
        headers = {"Content-Type": "text/plain; charset=utf-8", "Accept": "image/svg+xml"}
        body = dsl_code.encode("utf-8")

        last_exc: Optional[Exception] = None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(1, self.max_retries + 1):
                try:
                    resp = await client.post(url, content=body, headers=headers)

                    if resp.status_code == 200:
                        return resp.text

                    if resp.status_code in (400, 422):
                        raise KrokiRenderError(resp.status_code, resp.text[:500])

                    if attempt < self.max_retries:
                        await asyncio.sleep(0.5 * attempt)
                        continue

                    raise KrokiRenderError(resp.status_code, resp.text[:500])

                except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
                    last_exc = exc
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.5 * attempt)
                        continue
                    raise KrokiTimeoutError(f"Kroki timed out after {self.max_retries} attempts: {exc}") from exc

                except (httpx.ConnectError, httpx.NetworkError) as exc:
                    last_exc = exc
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.5 * attempt)
                        continue
                    raise KrokiConnectionError(f"Could not connect to Kroki at {self.base_url}: {exc}") from exc

        raise KrokiError(f"Kroki async render failed: {last_exc}")


kroki_client = KrokiClient()
