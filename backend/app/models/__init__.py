"""
SQLAlchemy ORM models for Exyst.

All models use UUID primary keys and include audit timestamps.
"""

import enum
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship

from app.ai.embeddings import EMBEDDING_DIM


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class ProcessingStatus(enum.StrEnum):
    """Status of a processing job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# --- User Model ---


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    # Bumped on logout to invalidate all outstanding refresh tokens.
    token_version = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    courses = relationship("Course", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.email}>"


# --- Course Model ---


class Course(Base):
    """
    A subject a student is studying — the organizing unit of the platform.

    Documents belong to a course, so past papers accumulate into a growing
    corpus instead of each upload being an isolated one-shot. That corpus is
    what RAG retrieval is scoped to: a prediction for a Physics paper is
    grounded on the Physics papers, not on everything the user has ever
    uploaded.

    `course_id` is nullable on Document — documents uploaded before courses
    existed (or deliberately left unfiled) keep working.
    """

    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True)          # e.g. "EAI602"
    university = Column(String(255), nullable=True)
    semester = Column(String(50), nullable=True)      # e.g. "6th", "2024-25 ODD"
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user = relationship("User", back_populates="courses")
    # Deleting a course does NOT delete its documents — they're just unfiled
    # (course_id set to NULL). Losing a semester of uploads because you renamed
    # a course wrong would be unforgivable.
    documents = relationship("Document", back_populates="course")

    def __repr__(self) -> str:
        return f"<Course {self.name}>"


# --- Document Model ---


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    # Nullable: documents can be unfiled (and every document uploaded before
    # courses existed is). Deleting a course nulls this rather than cascading.
    course_id = Column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_hash = Column(String(64), nullable=True)  # SHA-256
    file_size_bytes = Column(Integer, nullable=False)
    status = Column(
        Enum(ProcessingStatus),
        default=ProcessingStatus.PENDING,
        nullable=False,
    )
    error_message = Column(Text, nullable=True)
    uploaded_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="documents")
    course = relationship("Course", back_populates="documents")
    analyses = relationship("Analysis", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Document {self.original_filename}>"


# --- Analysis Model ---


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id"),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(ProcessingStatus),
        default=ProcessingStatus.PENDING,
        nullable=False,
    )

    # Extracted data (stored as JSONB for flexible schema)
    syllabus_structure = Column(JSONB, nullable=True)
    question_papers = Column(JSONB, nullable=True)  # Array of parsed papers
    topic_frequency = Column(JSONB, nullable=True)  # {topic: count}
    pattern_analysis = Column(JSONB, nullable=True)

    # Metadata
    num_pages_processed = Column(Integer, nullable=True)
    num_papers_found = Column(Integer, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    model_used = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    document = relationship("Document", back_populates="analyses")
    predictions = relationship(
        "Prediction", back_populates="analysis", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Analysis {self.id} status={self.status}>"


# --- Prediction Model ---


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id"),
        nullable=False,
        index=True,
    )

    # The predicted paper (full structure)
    predicted_paper = Column(JSONB, nullable=False)

    # Quality metrics
    confidence_scores = Column(JSONB, nullable=True)  # Per-question confidence
    overall_confidence = Column(Float, nullable=True)
    topic_coverage = Column(JSONB, nullable=True)  # {topic: coverage_pct}

    # Metadata
    model_used = Column(String(100), nullable=True)
    prompt_version = Column(String(50), nullable=True)
    prompt_metadata = Column(JSONB, nullable=True)
    generation_time_seconds = Column(Float, nullable=True)

    generated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    analysis = relationship("Analysis", back_populates="predictions")

    def __repr__(self) -> str:
        return f"<Prediction {self.id} confidence={self.overall_confidence}>"


# --- RAG vector store ---


class ChunkKind(enum.StrEnum):
    """What a stored vector represents."""
    QUESTION = "question"
    TOPIC = "topic"


class VectorChunk(Base):
    """
    A single embedded piece of text (a historical question or a syllabus topic).

    Replaces the former embedded ChromaDB store: keeping vectors in Postgres
    means they survive serverless cold starts, are shared across instances, and
    — critically — can be filtered by user_id so retrieval can never surface
    another user's questions.

    Rows are removed by the ON DELETE CASCADE on document_id (no ORM
    relationship: the pipeline writes these, nothing needs to traverse them).
    """

    __tablename__ = "vector_chunks"
    __table_args__ = (
        # Stable natural key makes re-indexing the same document idempotent.
        UniqueConstraint("chunk_key", name="uq_vector_chunks_chunk_key"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Denormalized from the document so retrieval can filter to a course's whole
    # corpus with an index hit instead of a join. Nullable for unfiled documents.
    course_id = Column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    kind = Column(String(20), nullable=False, index=True)
    chunk_key = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    chunk_metadata = Column(JSONB, nullable=True)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<VectorChunk {self.kind} {self.chunk_key}>"


# --- Cross-instance shared state (see app/core/shared_state.py) ---


class LLMCacheEntry(Base):
    """
    A cached LLM response, keyed by a hash of (system prompt, prompt, temperature).

    Lives in Postgres rather than process memory so a cache hit on one
    serverless instance serves all of them — each hit skips a multi-second
    Gemini call. Rows expire by `expires_at` and are swept opportunistically.
    """

    __tablename__ = "llm_cache"

    cache_key = Column(String(64), primary_key=True)  # sha256 hex
    response = Column(Text, nullable=False)
    model = Column(String(100), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<LLMCacheEntry {self.cache_key[:12]}>"


class RateLimitCounter(Base):
    """
    A hit counter for one (bucket, client, time-window) triple.

    Used for per-IP auth/upload limits and for per-model Gemini RPM pacing.
    Shared across instances so N replicas enforce one limit and share one
    provider quota, instead of each keeping its own private count.
    """

    __tablename__ = "rate_limit_counters"

    bucket = Column(String(64), primary_key=True)       # e.g. "login", "llm_rpm"
    client_key = Column(String(200), primary_key=True)  # e.g. an IP, or a model name
    window_start = Column(DateTime(timezone=True), primary_key=True)
    hits = Column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<RateLimitCounter {self.bucket}:{self.client_key} hits={self.hits}>"
