"""
Prompt Sanitization & Adversarial Injection Defense Service -- Sprint 6.

Responsibilities:
  1. Detect adversarial prompt injection patterns (jailbreaks, rule bypasses,
     developer mode activations, ignore instructions directives).
  2. Sanitize and neutralize detected malicious directives so they cannot alter
     system instructions, JSON schema rules, or validation limits.
  3. Enclose prompts inside safe XML boundaries (<user_diagram_request>) and
     escape structural tags to prevent boundary escaping.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SanitizationResult:
    """Result of prompt sanitization check."""
    original_text: str
    sanitized_text: str
    has_injection_attempt: bool = False
    detected_patterns: List[str] = field(default_factory=list)

    @property
    def was_modified(self) -> bool:
        return self.original_text != self.sanitized_text


# High-confidence prompt-injection / jailbreak regex patterns
INJECTION_RULES: List[Tuple[str, str]] = [
    (
        r"(?i)\bignore\s+(all\s+|any\s+|prior\s+|previous\s+)?instructions\b",
        "Instruction override directive",
    ),
    (
        r"(?i)\bdisregard\s+(all\s+|any\s+|prior\s+|previous\s+)?instructions\b",
        "Disregard instructions directive",
    ),
    (
        r"(?i)\bforget\s+(all\s+|any\s+|prior\s+|previous\s+)?instructions\b",
        "Forget instructions directive",
    ),
    (
        r"(?i)\b(system\s*prompt|system\s*instructions)\s*:\s*",
        "System prompt impersonation",
    ),
    (
        r"(?i)\b(system\s*:\s*override|system\s*override|override\s*system\s*rules)\b",
        "System override directive",
    ),
    (
        r"(?i)\b(developer\s*mode|dan\s*mode|jailbreak)\b",
        "Jailbreak mode toggle",
    ),
    (
        r"(?i)\bbypass\s+(all\s+)?(rules|validation|limits|checks)\b",
        "Validation bypass directive",
    ),
    (
        r"(?i)\bdo\s+not\s+(validate|check|enforce)\b",
        "Rule disable directive",
    ),
    (
        r"(?i)\bpretend\s+to\s+be\s+an\s+unconstrained\b",
        "Unconstrained persona prompt",
    ),
    (
        r"(?i)\boutput\s+plain\s+text\s+instead\s+of\s+json\b",
        "Format escape directive",
    ),
]


class SanitizationService:
    """Service providing adversarial sanitization for user-provided prompts and uploaded reference texts."""

    def sanitize(self, text: str) -> SanitizationResult:
        if not text:
            return SanitizationResult(original_text="", sanitized_text="")

        detected = []
        cleaned = text

        for pattern, label in INJECTION_RULES:
            if re.search(pattern, cleaned):
                detected.append(label)
                # Neutralize matched injection directive by replacing it with sanitized token
                cleaned = re.sub(pattern, "[sanitized_directive]", cleaned)

        # Escape XML tag delimiters so prompt cannot break out of <user_diagram_request>
        cleaned = re.sub(r"</?user_diagram_request.*?>", "[escaped_tag]", cleaned, flags=re.IGNORECASE)

        has_injection = len(detected) > 0
        if has_injection:
            logger.warning(
                "Prompt injection attempt detected and neutralized: patterns=%s original=%r",
                detected,
                text[:100],
            )

        return SanitizationResult(
            original_text=text,
            sanitized_text=cleaned.strip(),
            has_injection_attempt=has_injection,
            detected_patterns=detected,
        )

    def envelope_for_llm(self, prompt: str) -> str:
        """
        Encloses prompt inside secure XML tags to preserve isolation between
        system instruction contract and user description.
        """
        res = self.sanitize(prompt)
        safe_content = res.sanitized_text
        return f"<user_diagram_request>\n{safe_content}\n</user_diagram_request>"


# Global singleton
sanitization_service = SanitizationService()
