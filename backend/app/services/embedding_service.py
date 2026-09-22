"""Embedding service for generating Voyage embeddings and pgvector similarity search (Sprint 2+)."""

from typing import List


class EmbeddingService:
    def __init__(self):
        pass

    async def generate_embedding(self, text: str) -> List[float]:
        """Stub for Voyage API embedding generation (1024-dimension)."""
        raise NotImplementedError("Embedding generation will be implemented in the Retrieval sprint.")

    async def find_similar_diagram(self, embedding: List[float], threshold: float = 0.85):
        """Stub for pgvector similarity search."""
        raise NotImplementedError("pgvector similarity search will be implemented in the Retrieval sprint.")


embedding_service = EmbeddingService()
