"""
Groq Generation Service -- Sprint 2.

Responsibilities:
  1. Build the constrained system prompt from the Groq contract (v1.0).
  2. Call the Groq API with JSON mode / structured output.
  3. Parse the raw response into a dict and pass it to ValidationService.
  4. Return the validated GroqDiagramResponse or raise a typed exception.

The Groq client is instantiated lazily so that the service can be imported
even when GROQ_API_KEY is not configured (e.g. during unit tests that mock
this class).

Error hierarchy:
  GroqServiceError       -- base
  GroqConfigError        -- API key not set
  GroqAPIError           -- non-retryable Groq API error
  GroqTimeoutError       -- call exceeded GROQ_TIMEOUT_SECONDS
  GroqRateLimitError     -- 429, all retries exhausted
  GroqParseError         -- response was not valid JSON
  GroqValidationError    -- response failed schema/graph validation
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any, Dict, Optional

from tenacity import RetryError, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.services.validation_service import ValidationResult, validation_service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class GroqServiceError(Exception):
    """Base class for all Groq service errors."""


class GroqConfigError(GroqServiceError):
    """Raised when GROQ_API_KEY is not configured."""


class GroqAPIError(GroqServiceError):
    """Raised for non-retryable Groq API errors."""


class GroqTimeoutError(GroqServiceError):
    """Raised when the Groq API call exceeds the configured timeout."""


class GroqRateLimitError(GroqServiceError):
    """Raised when Groq rate-limits the request and all retries are exhausted."""


class GroqParseError(GroqServiceError):
    """Raised when the Groq response cannot be parsed as JSON."""


class GroqValidationError(GroqServiceError):
    """
    Raised when the Groq response parses as JSON but fails schema or graph
    validation.  The ValidationResult is attached as .validation_result.
    """

    def __init__(self, message: str, validation_result: ValidationResult):
        super().__init__(message)
        self.validation_result = validation_result


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

# This is the verbatim system prompt that corresponds to CONTRACT VERSION 1.0.
# If you change the schema in groq_contract.py, you MUST update this prompt
# and bump the contract version.
_SYSTEM_PROMPT_V1 = """You are a diagram-architecture extractor. Given a natural-language description, return ONLY a valid JSON object with the following fields and no extra keys.

Required fields:
  diagram_type  : string -- one of: flowchart | sequence | erd | class | state_machine | mindmap | gantt | network | generic
  nodes         : array  -- at least 1 node object
  edges         : array  -- may be empty for single-node diagrams
  attributes    : object -- diagram-level metadata

Node object shape:
  id       : string  -- unique within the response, non-empty, no whitespace
  label    : string  -- human-readable display label (max 200 chars)
  type     : string  -- node semantic type (e.g. "service", "database", "actor", "class", "state"); use "generic" when unsure
  metadata : object  -- optional; free-form key/value pairs for extra context

Edge object shape:
  id     : string  -- unique within the response, non-empty, no whitespace
  source : string  -- must exactly match an id in the nodes array
  target : string  -- must exactly match an id in the nodes array
  label  : string  -- may be empty string; max 200 chars
  type   : string  -- relationship type (e.g. "depends_on", "calls", "inherits", "transitions_to"); use "generic" when unsure

Attributes object shape (all keys required):
  title              : string  -- short diagram title (max 120 chars)
  description        : string  -- one-sentence summary (max 500 chars)
  allows_disconnected: boolean -- true ONLY for mindmap, gantt, network diagram types; false for all others
  direction          : string  -- layout hint: "LR" | "RL" | "TB" | "BT" | "auto"

CRITICAL RULES:
- DO NOT include a "complexity" field. Complexity is computed independently.
- DO NOT add any fields not listed above.
- Return ONLY the JSON object -- no markdown code fences, no prose, no explanation.
- Every edge.source and edge.target MUST match an id in the nodes array exactly.
- All node ids and edge ids must be unique within the response.
- Node ids and edge ids must contain no whitespace characters."""


def _build_user_message(prompt: str) -> str:
    """Wrap the user prompt in a clear instruction."""
    return (
        f"Generate a diagram structure for the following description:\n\n{prompt}\n\n"
        "Return ONLY the JSON object as specified. No markdown fences."
    )


# ---------------------------------------------------------------------------
# Retry decorator (rate-limit only)
# ---------------------------------------------------------------------------


def _is_rate_limit(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "429" in msg or "rate_limit" in msg or "rate limit" in msg


@retry(
    retry=retry_if_exception_type(GroqRateLimitError),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(settings.GROQ_MAX_RETRIES),
    reraise=True,
)
def _call_groq_with_retry(client: Any, model: str, messages: list, timeout: float) -> str:
    """
    Call the Groq chat completions API and return the raw content string.
    Wrapped by tenacity for 429 retries only.
    """
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.0,        # deterministic output
            max_tokens=4096,
            response_format={"type": "json_object"},
            timeout=timeout,
        )
    except Exception as exc:
        if _is_rate_limit(exc):
            logger.warning("Groq rate-limit hit, will retry: %s", exc)
            raise GroqRateLimitError(str(exc)) from exc
        raise

    content = completion.choices[0].message.content
    if not content:
        raise GroqAPIError("Groq returned an empty content field.")
    return content


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------


class GroqService:
    """
    Wraps the Groq API client with structured-output enforcement, timeouts,
    retry logic, and mandatory schema validation.

    Every successful call returns a ValidationResult whose validated_model
    is a fully-checked GroqDiagramResponse.  If validation fails, a
    GroqValidationError is raised -- the invalid payload never reaches the caller.
    """

    def __init__(self) -> None:
        self._client: Optional[Any] = None

    # ---- Lazy client -------------------------------------------------------

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            from groq import Groq  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "groq package is not installed. Run: pip install groq"
            ) from exc

        if not settings.GROQ_API_KEY:
            raise GroqConfigError(
                "GROQ_API_KEY is not configured. Set it in .env before using Groq."
            )

        self._client = Groq(api_key=settings.GROQ_API_KEY)
        return self._client

    # ---- Core generation ---------------------------------------------------

    def generate_diagram_json(
        self,
        prompt: str,
        timeout: Optional[float] = None,
    ) -> ValidationResult:
        """
        Call Groq with the constrained prompt and return a validated result.

        Parameters
        ----------
        prompt  -- the (optionally preprocessed) user prompt
        timeout -- override for GROQ_TIMEOUT_SECONDS (mainly for tests)

        Returns
        -------
        ValidationResult with is_valid=True and a populated validated_model.

        Raises
        ------
        GroqConfigError       -- API key not set
        GroqTimeoutError      -- call timed out
        GroqRateLimitError    -- 429 exhausted
        GroqAPIError          -- other API errors
        GroqParseError        -- response not valid JSON
        GroqValidationError   -- schema/graph validation failed
        """
        if timeout is None:
            timeout = settings.GROQ_TIMEOUT_SECONDS

        client = self._get_client()
        model = settings.GROQ_MODEL
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT_V1},
            {"role": "user", "content": _build_user_message(prompt)},
        ]

        logger.info(
            "Calling Groq model=%s for prompt (len=%d chars).", model, len(prompt)
        )

        # ---- Timeout wrapper (threading, Windows-compatible) ---------------
        result_holder: Dict[str, Any] = {}

        def _do_call() -> None:
            try:
                raw_content = _call_groq_with_retry(client, model, messages, timeout)
                result_holder["content"] = raw_content
            except Exception as exc:
                result_holder["error"] = exc

        thread = threading.Thread(target=_do_call, daemon=True)
        thread.start()
        thread.join(timeout=timeout + 5)  # extra 5s grace for HTTP overhead

        if thread.is_alive():
            logger.error("Groq call timed out after %.1f seconds.", timeout)
            raise GroqTimeoutError(
                f"Groq API did not respond within {timeout:.0f} seconds."
            )

        if "error" in result_holder:
            exc = result_holder["error"]
            if isinstance(exc, (GroqRateLimitError, RetryError)):
                raise GroqRateLimitError(
                    f"Groq rate-limit: all {settings.GROQ_MAX_RETRIES} retries exhausted."
                ) from exc
            if isinstance(exc, GroqAPIError):
                raise
            raise GroqAPIError(str(exc)) from exc

        raw_content: str = result_holder.get("content", "")

        # ---- JSON parsing --------------------------------------------------
        try:
            raw_dict = json.loads(raw_content)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error(
                "Groq response is not valid JSON: %s ... (first 200 chars)",
                raw_content[:200],
            )
            raise GroqParseError(
                f"Groq response could not be parsed as JSON: {exc}. "
                f"First 200 chars of response: {raw_content[:200]!r}"
            ) from exc

        # ---- Validation (both layers) --------------------------------------
        validation_result = validation_service.validate(raw_dict)
        if not validation_result.is_valid:
            logger.warning(
                "Groq response failed validation (layer=%s): %s",
                validation_result.layer,
                validation_result.error_summary,
            )
            raise GroqValidationError(
                f"Groq response failed {validation_result.layer} validation: "
                f"{validation_result.error_summary}",
                validation_result=validation_result,
            )

        logger.info(
            "Groq response validated successfully: diagram_type=%s nodes=%d edges=%d",
            validation_result.validated_model.diagram_type,  # type: ignore[union-attr]
            len(validation_result.validated_model.nodes),    # type: ignore[union-attr]
            len(validation_result.validated_model.edges),    # type: ignore[union-attr]
        )
        return validation_result


# Module-level singleton
groq_service = GroqService()
