"""
Tests for the pgvector RAG store.

Embeddings are faked (see conftest.FakeEmbedder) so these exercise the storage
and retrieval plumbing — user scoping, idempotency, cosine ranking, cascade —
not the quality of real embeddings.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.ai.rag import RAGStore
from app.models import ChunkKind, Document, ProcessingStatus, User, VectorChunk
from tests.conftest import FakeEmbedder

QUESTIONS = [
    {"question_text": "Explain the concept of genetic algorithms", "topic": "GA", "marks": 10},
    {"question_text": "Describe crossover and mutation operators", "topic": "GA", "marks": 10},
    {"question_text": "What is backpropagation in neural networks?", "topic": "NN", "marks": 10},
]


async def _make_user_with_document(db_session) -> tuple[User, Document]:
    """Persist a user + document so the vector_chunks FKs resolve."""
    user = User(
        email=f"rag_{uuid.uuid4().hex[:10]}@example.com",
        hashed_password="x",
        name="RAG Tester",
    )
    db_session.add(user)
    await db_session.flush()

    document = Document(
        user_id=user.id,
        filename="exam.pdf",
        original_filename="exam.pdf",
        file_path="/tmp/exam.pdf",
        file_size_bytes=10,
        status=ProcessingStatus.PENDING,
    )
    db_session.add(document)
    await db_session.flush()

    return user, document


@pytest.fixture
def rag() -> RAGStore:
    return RAGStore(embedder=FakeEmbedder())


@pytest_asyncio.fixture
async def owner(db_session):
    return await _make_user_with_document(db_session)


@pytest.mark.asyncio
async def test_index_and_retrieve_questions(rag, db_session, owner):
    user, document = owner

    count = await rag.index_questions(
        db_session, user.id, document.id, QUESTIONS, session="2023-24"
    )
    assert count == 3

    results = await rag.retrieve_similar_questions(
        db_session, user.id, "genetic algorithms crossover"
    )
    assert len(results) > 0
    assert results[0]["similarity_score"] > 0
    # The genetic-algorithm questions must outrank the neural-network one.
    assert "genetic" in results[0]["text"].lower() or "crossover" in results[0]["text"].lower()


@pytest.mark.asyncio
async def test_results_are_ranked_by_similarity(rag, db_session, owner):
    user, document = owner
    await rag.index_questions(db_session, user.id, document.id, QUESTIONS)

    results = await rag.retrieve_similar_questions(
        db_session, user.id, "backpropagation neural networks"
    )
    assert results
    assert "backpropagation" in results[0]["text"].lower()
    # Descending similarity.
    scores = [r["similarity_score"] for r in results]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_retrieval_is_scoped_to_the_owner(rag, db_session):
    """A user must never retrieve another user's questions (cross-user leak)."""
    user_a, doc_a = await _make_user_with_document(db_session)
    user_b, _doc_b = await _make_user_with_document(db_session)

    await rag.index_questions(db_session, user_a.id, doc_a.id, QUESTIONS)

    # User A sees their own chunks...
    mine = await rag.retrieve_similar_questions(db_session, user_a.id, "genetic algorithms")
    assert len(mine) > 0

    # ...user B sees nothing, despite querying the same text.
    theirs = await rag.retrieve_similar_questions(db_session, user_b.id, "genetic algorithms")
    assert theirs == []
    assert await rag.count(db_session, user_b.id) == 0


@pytest.mark.asyncio
async def test_retrieval_can_be_scoped_to_one_document(rag, db_session, owner):
    user, doc_one = owner

    doc_two = Document(
        user_id=user.id,
        filename="other.pdf",
        original_filename="other.pdf",
        file_path="/tmp/other.pdf",
        file_size_bytes=10,
        status=ProcessingStatus.PENDING,
    )
    db_session.add(doc_two)
    await db_session.flush()

    await rag.index_questions(db_session, user.id, doc_one.id, QUESTIONS[:2])
    await rag.index_questions(db_session, user.id, doc_two.id, QUESTIONS[2:])

    scoped = await rag.retrieve_similar_questions(
        db_session, user.id, "genetic algorithms", document_id=doc_two.id
    )
    # doc_two only holds the neural-network question.
    assert all("genetic" not in r["text"].lower() for r in scoped)


@pytest.mark.asyncio
async def test_index_and_retrieve_topics(rag, db_session, owner):
    user, document = owner
    topics = [
        "Introduction to Genetic Algorithms",
        "Neural Network Architectures",
        "Deep Learning Fundamentals",
    ]

    count = await rag.index_topics(db_session, user.id, document.id, topics, unit="Unit 1")
    assert count == 3

    results = await rag.retrieve_related_topics(db_session, user.id, "genetic algorithms")
    assert len(results) > 0
    assert results[0]["unit"] == "Unit 1"


@pytest.mark.asyncio
async def test_questions_and_topics_do_not_cross_contaminate(rag, db_session, owner):
    """A question search must not return topics, and vice versa."""
    user, document = owner
    await rag.index_questions(db_session, user.id, document.id, QUESTIONS)
    await rag.index_topics(
        db_session, user.id, document.id, ["Genetic Algorithms"], unit="Unit 1"
    )

    questions = await rag.retrieve_similar_questions(db_session, user.id, "genetic algorithms")
    assert all(q["text"] != "Genetic Algorithms" for q in questions)

    assert await rag.count(db_session, user.id, kind=ChunkKind.TOPIC) == 1
    assert await rag.count(db_session, user.id, kind=ChunkKind.QUESTION) == 3


@pytest.mark.asyncio
async def test_empty_input(rag, db_session, owner):
    user, document = owner
    assert await rag.index_questions(db_session, user.id, document.id, []) == 0
    assert await rag.index_topics(db_session, user.id, document.id, []) == 0
    assert await rag.retrieve_similar_questions(db_session, user.id, "test") == []


@pytest.mark.asyncio
async def test_index_questions_filters_short_text(rag, db_session, owner):
    user, document = owner
    questions = [
        {"question_text": "Q", "topic": "GA", "marks": 10},
        {"question_text": "", "topic": "NN", "marks": 5},
        {"question_text": "Explain genetic algorithms in detail", "topic": "GA", "marks": 10},
    ]

    count = await rag.index_questions(db_session, user.id, document.id, questions)
    assert count == 1  # only the third is long enough


@pytest.mark.asyncio
async def test_reindexing_is_idempotent(rag, db_session, owner):
    """Re-running the pipeline on a document must not duplicate its chunks."""
    user, document = owner

    await rag.index_questions(db_session, user.id, document.id, QUESTIONS, session="2023-24")
    await rag.index_questions(db_session, user.id, document.id, QUESTIONS, session="2023-24")

    assert await rag.count(db_session, user.id, kind=ChunkKind.QUESTION) == 3


@pytest.mark.asyncio
async def test_chunks_are_deleted_with_their_document(rag, db_session, owner):
    """The FK cascade must clear vectors when a document is deleted."""
    user, document = owner
    await rag.index_questions(db_session, user.id, document.id, QUESTIONS)
    assert await rag.count(db_session, user.id) == 3

    await db_session.delete(document)
    await db_session.flush()

    remaining = await db_session.execute(
        select(VectorChunk).where(VectorChunk.document_id == document.id)
    )
    assert remaining.scalars().all() == []
