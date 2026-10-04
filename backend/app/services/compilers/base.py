"""
Base compiler interface and shared utilities for AST -> DSL compilers.
"""

from abc import ABC, abstractmethod
import re
from typing import Any, Dict, List, Optional


class BaseCompiler(ABC):
    """Abstract base class for all deterministic diagram DSL compilers."""

    @abstractmethod
    def compile(self, structured_json: Dict[str, Any]) -> str:
        """
        Compile structured JSON (Pydantic GroqDiagramResponse shape) into a clean,
        syntactically guaranteed DSL string.
        """
        pass

    @staticmethod
    def clean_id(raw_id: str) -> str:
        """Ensure node/edge identifier is safe and contains only valid characters."""
        if not raw_id:
            return "node"
        # Replace non-alphanumeric/underscore characters with underscore
        cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", str(raw_id).strip())
        if not cleaned:
            return "node"
        if cleaned[0].isdigit():
            cleaned = f"n_{cleaned}"
        return cleaned

    @staticmethod
    def clean_label(label: Optional[str], default: str = "") -> str:
        """Clean human-readable label string by stripping excess whitespace and quotes."""
        if not label:
            return default
        # Replace newlines with space, strip leading/trailing quotes
        text = str(label).strip()
        text = text.replace("\r\n", " ").replace("\n", " ")
        return text

    @staticmethod
    def get_direction(attributes: Optional[Dict[str, Any]], default: str = "LR") -> str:
        """Extract and normalize layout direction hint (LR, RL, TB, BT)."""
        if not attributes or not isinstance(attributes, dict):
            return default
        direction = attributes.get("direction", default)
        if direction in ("LR", "RL", "TB", "BT"):
            return direction
        if direction == "auto":
            return default
        return default
