"""Generation service for LLM-based diagram architecture extraction (Sprint 3+)."""

from typing import Dict, Any


class GenerationService:
    def __init__(self):
        pass

    async def generate_architecture_json(self, prompt: str) -> Dict[str, Any]:
        """Stub for Groq LLM structured architecture generation."""
        raise NotImplementedError("Groq architecture generation will be implemented in the Generation sprint.")

    async def generate_creative_image(self, prompt: str) -> str:
        """Stub for Gemini creative image generation."""
        raise NotImplementedError("Creative image generation will be implemented in the Gemini sprint.")


generation_service = GenerationService()
