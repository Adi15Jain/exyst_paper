"""
SQLAlchemy ORM models for Exyst.

All models use UUID primary keys and include audit timestamps.
"""

import enum
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


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

    def __repr__(self) -> str:
        return f"<User {self.email}>"


# --- Document Model ---


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
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
