"""
Tests for the ChromaDB RAG pipeline.
"""

import os
import shutil
import tempfile

import pytest

from app.ai.rag import RAGPipeline


@pytest.fixture
def rag_pipeline(monkeypatch):
    """Create a RAG pipeline with a temp directory for isolation."""
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr("app.ai.rag.get_settings", lambda: type("S", (), {
        "OUTPUTS_DIR": tmpdir
    })())
    pipeline = RAGPipeline()
    yield pipeline
    shutil.rmtree(tmpdir, ignore_errors=True)


class TestRAGPipeline:
    """Tests for vector-based retrieval."""

    def test_index_and_retrieve_questions(self, rag_pipeline):
        """Should index questions and retrieve similar ones."""
        questions = [
            {"question_text": "Explain the concept of genetic algorithms", "topic": "GA", "marks": 10},
            {"question_text": "Describe crossover and mutation operators", "topic": "GA", "marks": 10},
            {"question_text": "What is backpropagation in neural networks?", "topic": "NN", "marks": 10},
        ]

        count = rag_pipeline.index_questions(questions, document_id="doc1", session="2023-24")
        assert count == 3

        results = rag_pipeline.retrieve_similar_questions("genetic algorithm optimization")
        assert len(results) > 0
        assert results[0]["similarity_score"] > 0

    def test_index_and_retrieve_topics(self, rag_pipeline):
        """Should index syllabus topics and retrieve related ones."""
        topics = [
            "Introduction to Genetic Algorithms",
            "Neural Network Architectures",
            "Deep Learning Fundamentals",
            "Reinforcement Learning",
        ]

        count = rag_pipeline.index_topics(topics, document_id="doc1", unit="Unit 1")
        assert count == 4

        results = rag_pipeline.retrieve_related_topics("machine learning models")
        assert len(results) > 0

    def test_empty_input(self, rag_pipeline):
        """Should handle empty input gracefully."""
        assert rag_pipeline.index_questions([], document_id="doc1") == 0
        assert rag_pipeline.index_topics([], document_id="doc1") == 0
        assert rag_pipeline.retrieve_similar_questions("test") == []

    def test_collection_stats(self, rag_pipeline):
        """Should report collection statistics."""
        stats = rag_pipeline.get_collection_stats()
        assert "total_questions" in stats
        assert "total_topics" in stats
        assert stats["total_questions"] == 0

    def test_index_questions_filters_short_text(self, rag_pipeline):
        """Should skip questions with very short text."""
        questions = [
            {"question_text": "Q", "topic": "GA", "marks": 10},
            {"question_text": "", "topic": "NN", "marks": 5},
            {"question_text": "Explain genetic algorithms in detail", "topic": "GA", "marks": 10},
        ]

        count = rag_pipeline.index_questions(questions, document_id="doc1")
        assert count == 1  # Only the third question is long enough

    def test_upsert_idempotent(self, rag_pipeline):
        """Indexing same data twice should not duplicate."""
        questions = [
            {"question_text": "What is artificial intelligence?", "topic": "AI", "marks": 10},
        ]

        rag_pipeline.index_questions(questions, document_id="doc1", session="2023-24")
        rag_pipeline.index_questions(questions, document_id="doc1", session="2023-24")

        stats = rag_pipeline.get_collection_stats()
        assert stats["total_questions"] == 1
