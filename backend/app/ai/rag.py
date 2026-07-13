"""
pgvector-backed RAG (Retrieval-Augmented Generation) store.

Stores historical questions and syllabus topics as embeddings in Postgres
(`vector_chunks`), enabling semantic retrieval of relevant past questions to
ground prediction prompts.

Replaces the previous embedded-ChromaDB store, which could not work on
serverless (its on-disk index vanished between invocations, and the package
blew the bundle size limit). Keeping vectors in the existing database also
means:

  * retrieval is filtered by ``user_id`` — one user's questions can never be
    retrieved into another user's prediction prompt;
  * similarity is a true cosine similarity (``1 - cosine_distance``), not the
    ``1 - L2`` approximation the old store used;
  * chunks are removed automatically when their document is deleted.

RAG is always optional: if embeddings are unavailable (no API key, provider
error), indexing and retrieval degrade to no-ops and prediction proceeds
without retrieved context.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import Embedder, get_embedder
from app.core.logging import get_logger
from app.models import ChunkKind, VectorChunk

logger = get_logger(__name__)

# Retrieval below this cosine similarity is noise, not context.
MIN_SIMILARITY = 0.3


class RAGStore:
    """Semantic index over a user's historical questions and syllabus topics."""

    def __init__(self, embedder: Embedder | None = None) -> None:
        # Injectable so tests can supply a deterministic embedder.
        self._embedder = embedder or get_embedder()

    # --- Indexing ---

    async def index_questions(
        self,
        db: AsyncSession,
        user_id: UUID,
        document_id: UUID,
        questions: list[dict[str, Any]],
        session: str = "unknown",
        course_id: UUID | None = None,
    ) -> int:
        """
        Embed and store extracted questions. Returns the number indexed.

        Idempotent: re-indexing the same document overwrites the same rows
        (stable chunk_key), so a re-run never duplicates context.
        """
        texts: list[str] = []
        rows: list[dict[str, Any]] = []

        for i, q in enumerate(questions):
            text = q.get("question_text", q.get("text", ""))
            if not text or len(text.strip()) < 5:
                continue

            topic = q.get("topic", "unknown")
            # Prefixing with the topic mirrors the retrieval query shape
            # (topic names), which measurably improves matching.
            texts.append(f"{topic} | {text}")
            rows.append({
                "user_id": user_id,
                "document_id": document_id,
                "course_id": course_id,
                "kind": ChunkKind.QUESTION.value,
                "chunk_key": f"{document_id}:question:{session}:{i}",
                "content": text,
                "chunk_metadata": {
                    "topic": topic,
                    "session": session,
                    "marks": str(q.get("marks", 0)),
                    "question_type": q.get("question_type", "medium"),
                    "question_number": str(q.get("question_number", i + 1)),
                },
            })

        return await self._embed_and_upsert(db, texts, rows)

    async def index_topics(
        self,
        db: AsyncSession,
        user_id: UUID,
        document_id: UUID,
        topics: list[str],
        unit: str = "unknown",
        course_id: UUID | None = None,
    ) -> int:
        """Embed and store syllabus topics. Returns the number indexed."""
        texts: list[str] = []
        rows: list[dict[str, Any]] = []

        for i, topic in enumerate(topics):
            if not topic or not topic.strip():
                continue
            texts.append(topic)
            rows.append({
                "user_id": user_id,
                "document_id": document_id,
                "course_id": course_id,
                "kind": ChunkKind.TOPIC.value,
                "chunk_key": f"{document_id}:topic:{unit}:{i}",
                "content": topic,
                "chunk_metadata": {"unit": unit},
            })

        return await self._embed_and_upsert(db, texts, rows)

    async def _embed_and_upsert(
        self,
        db: AsyncSession,
        texts: list[str],
        rows: list[dict[str, Any]],
    ) -> int:
        if not rows:
            return 0

        embeddings = await self._embedder.embed(texts)

        for row, embedding in zip(rows, embeddings, strict=True):
            row["embedding"] = embedding

        stmt = insert(VectorChunk).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_vector_chunks_chunk_key",
            set_={
                "content": stmt.excluded.content,
                "chunk_metadata": stmt.excluded.chunk_metadata,
                "embedding": stmt.excluded.embedding,
                "course_id": stmt.excluded.course_id,
            },
        )
        await db.execute(stmt)

        logger.info("chunks_indexed", count=len(rows), kind=rows[0]["kind"])
        return len(rows)

    # --- Retrieval ---

    async def retrieve_similar_questions(
        self,
        db: AsyncSession,
        user_id: UUID,
        query: str,
        n_results: int = 10,
        document_id: UUID | None = None,
        course_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """
        Semantically retrieve a user's historical questions matching ``query``.

        Always scoped to ``user_id``, and narrowed further to a course (its
        whole corpus) or a single document when given.
        """
        chunks = await self._search(
            db,
            user_id=user_id,
            kind=ChunkKind.QUESTION,
            query=query,
            n_results=n_results,
            document_id=document_id,
            course_id=course_id,
        )
        return [
            {
                "text": content,
                "topic": (metadata or {}).get("topic", ""),
                "session": (metadata or {}).get("session", ""),
                "marks": (metadata or {}).get("marks", ""),
                "similarity_score": similarity,
            }
            for content, metadata, similarity in chunks
        ]

    async def retrieve_related_topics(
        self,
        db: AsyncSession,
        user_id: UUID,
        query: str,
        n_results: int = 5,
        document_id: UUID | None = None,
        course_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Semantically retrieve a user's syllabus topics related to ``query``."""
        chunks = await self._search(
            db,
            user_id=user_id,
            kind=ChunkKind.TOPIC,
            query=query,
            n_results=n_results,
            document_id=document_id,
            course_id=course_id,
        )
        return [
            {
                "topic": content,
                "unit": (metadata or {}).get("unit", ""),
                "similarity_score": similarity,
            }
            for content, metadata, similarity in chunks
        ]

    async def _search(
        self,
        db: AsyncSession,
        user_id: UUID,
        kind: ChunkKind,
        query: str,
        n_results: int,
        document_id: UUID | None = None,
        course_id: UUID | None = None,
    ) -> list[tuple[str, dict[str, Any] | None, float]]:
        if not query or not query.strip():
            return []

        embeddings = await self._embedder.embed([query])
        if not embeddings:
            return []
        query_vector = embeddings[0]

        # cosine_distance is in [0, 2]; similarity = 1 - distance.
        distance = VectorChunk.embedding.cosine_distance(query_vector)
        stmt = (
            select(VectorChunk.content, VectorChunk.chunk_metadata, distance.label("distance"))
            .where(
                VectorChunk.user_id == user_id,
                VectorChunk.kind == kind.value,
            )
            .order_by(distance)
            .limit(n_results)
        )
        # A course scopes retrieval to that subject's whole corpus (every paper
        # filed under it); a document scopes it to just that upload.
        if course_id is not None:
            stmt = stmt.where(VectorChunk.course_id == course_id)
        elif document_id is not None:
            stmt = stmt.where(VectorChunk.document_id == document_id)

        result = await db.execute(stmt)

        hits = []
        for content, metadata, dist in result.all():
            similarity = round(1.0 - float(dist), 3)
            if similarity >= MIN_SIMILARITY:
                hits.append((content, metadata, similarity))

        logger.info(
            "chunks_retrieved",
            kind=kind.value,
            query_length=len(query),
            results_count=len(hits),
        )
        return hits

    # --- Maintenance ---

    async def count(
        self,
        db: AsyncSession,
        user_id: UUID,
        kind: ChunkKind | None = None,
        course_id: UUID | None = None,
        document_id: UUID | None = None,
    ) -> int:
        """How many chunks are indexed in a given scope."""
        stmt = (
            select(func.count())
            .select_from(VectorChunk)
            .where(VectorChunk.user_id == user_id)
        )
        if kind is not None:
            stmt = stmt.where(VectorChunk.kind == kind.value)
        if course_id is not None:
            stmt = stmt.where(VectorChunk.course_id == course_id)
        if document_id is not None:
            stmt = stmt.where(VectorChunk.document_id == document_id)
        result = await db.execute(stmt)
        return result.scalar() or 0

