"""
SpaCy preprocessing service — Sprint 1.

Provides tokenization, lemmatization, stopword removal, and named-entity
extraction.  The whole stage is feature-flagged via
settings.ENABLE_SPACY_PREPROCESSING; when disabled, the raw prompt passes
through unchanged so the rest of the pipeline is unaffected.

Model loading is lazy (only on first call) and cached in a module-level
variable to avoid reloading the model on every request.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Module-level singleton — populated lazily the first time preprocessing runs.
_nlp = None
_NLP_MODEL = "en_core_web_sm"  # small model; fast, no need for vectors here


def _load_model():
    """Load (and cache) the spaCy model on first use."""
    global _nlp
    if _nlp is not None:
        return _nlp
    try:
        import spacy  # noqa: PLC0415
        _nlp = spacy.load(_NLP_MODEL)
        logger.info("spaCy model '%s' loaded successfully.", _NLP_MODEL)
    except OSError:
        # Model not downloaded yet — give a clear error message.
        raise RuntimeError(
            f"spaCy model '{_NLP_MODEL}' not found.  "
            f"Run: python -m spacy download {_NLP_MODEL}"
        )
    return _nlp


def preprocess_prompt(prompt: str) -> str:
    """
    Run a spaCy NLP pipeline on *prompt* and return a normalised string.

    Steps applied:
    1. Tokenise with the en_core_web_sm pipeline
    2. Drop punctuation, whitespace, and stop-words
    3. Lemmatise each remaining token (lowercase)
    4. Append extracted entity labels in the form ``ENTITY_TYPE:text``
       so that domain-specific nouns survive stop-word removal

    The result is a single whitespace-joined string that is semantically
    richer than the raw prompt for embedding purposes.
    """
    nlp = _load_model()
    doc = nlp(prompt)

    # Core tokens: lemmatised, no stop-words, no punct/space
    tokens = [
        token.lemma_.lower()
        for token in doc
        if not token.is_stop and not token.is_punct and not token.is_space
    ]

    # Append named entities so they're never lost to stop-word filtering
    entities = [
        f"{ent.label_}:{ent.text.lower().replace(' ', '_')}"
        for ent in doc.ents
    ]

    result = " ".join(tokens + entities)
    logger.debug(
        "spaCy preprocessing: %r -> %r  (entities: %s)",
        prompt,
        result,
        entities or "none",
    )
    return result


class SpacyPreprocessor:
    """Thin class wrapper so the service follows the same pattern as others."""

    def __init__(self, enabled: bool):
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    def process(self, prompt: str) -> str:
        """Return preprocessed prompt when enabled, raw prompt when disabled."""
        if not self._enabled:
            logger.debug("spaCy preprocessing disabled — passing prompt through unchanged.")
            return prompt
        return preprocess_prompt(prompt)


def build_preprocessor(enabled: Optional[bool] = None) -> SpacyPreprocessor:
    """Factory that reads the feature flag from settings when *enabled* is None."""
    if enabled is None:
        from app.core.config import settings  # local import to avoid circular deps
        enabled = settings.ENABLE_SPACY_PREPROCESSING
    return SpacyPreprocessor(enabled=enabled)
