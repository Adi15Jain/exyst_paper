"""
Text embeddings via Google Gemini.

Used by the pgvector RAG store to embed questions, syllabus topics, and
retrieval queries into the same vector space.

The embedding model and its dimensionality are fixed together: changing
EMBEDDING_MODEL without a matching EMBEDDING_DIM (and a re-index) will make
every stored vector meaningless, so both live here as constants rather than
being configurable at runtime.
"""

import asyncio
from typing import Protocol

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIM = 768

# Gemini caps how many texts one embed call accepts.
_MAX_BATCH = 100


class Embedder(Protocol):
    """Anything that can turn texts into vectors (real or, in tests, fake)."""

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class GeminiEmbedder:
    """Embeds text with Gemini's embedding model."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not configured — embeddings unavailable")

        from google import genai

        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a list of texts, preserving order.

        Raises on API failure — callers decide whether to degrade (RAG is
        always optional; a failed embed disables retrieval, never the request).
        """
        if not texts:
            return []

        vectors: list[list[float]] = []
        for start in range(0, len(texts), _MAX_BATCH):
            batch = texts[start : start + _MAX_BATCH]
            # google-genai's client is sync; keep the event loop free.
            response = await asyncio.to_thread(
                self._client.models.embed_content,
                model=EMBEDDING_MODEL,
                contents=batch,
            )
            if not response.embeddings:
                raise RuntimeError("Embedding provider returned no embeddings")
            vectors.extend([list(e.values or []) for e in response.embeddings])

        if len(vectors) != len(texts):
            raise RuntimeError(
                f"Embedding count mismatch: got {len(vectors)} for {len(texts)} texts"
            )

        return vectors


def get_embedder() -> Embedder:
    """Build the default embedder. Raises if the LLM provider isn't configured."""
    return GeminiEmbedder()
