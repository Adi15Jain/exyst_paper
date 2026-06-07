"""
Tests for AI pipeline components.
"""

import pytest

from app.ai.pipelines.document_processor import DocumentProcessor
from app.ai.evaluation import Evaluator
from app.ai.pipelines.syllabus_analyzer import SyllabusStructure
from app.schemas.prediction import PredictedPaper, PredictedQuestion, PredictedSection


class TestDocumentProcessor:
    """Tests for PDF processing pipeline."""

    def test_extract_metadata_university(self):
        """Should extract university name from text."""
        processor = DocumentProcessor()
        text = "TEERTHANKER MAHAVEER UNIVERSITY – MORADABAD\nB.Tech Examination"
        metadata = processor.extract_metadata(text)
        assert metadata["university"] is not None
        assert "UNIVERSITY" in metadata["university"]

    def test_extract_metadata_course_code(self):
        """Should extract course code."""
        processor = DocumentProcessor()
        text = "Course Code: EAI602\nMax. Marks: 60"
        metadata = processor.extract_metadata(text)
        assert metadata["course_code"] == "EAI602"

    def test_extract_metadata_max_marks(self):
        """Should extract max marks."""
        processor = DocumentProcessor()
        text = "Max. Marks: 60\nTime: 3 Hours"
        metadata = processor.extract_metadata(text)
        assert metadata["max_marks"] == "60"

    def test_split_papers_by_session(self):
        """Should split text by academic session markers."""
        processor = DocumentProcessor()
        text = "Header\n2023-24\nQ1. What is AI?\n2024-25\nQ1. Define ML?"
        papers = processor.split_papers_by_session(text)
        assert len(papers) >= 1

    def test_split_papers_no_sessions(self):
        """Should return single paper when no sessions found."""
        processor = DocumentProcessor()
        text = "Q1. What is AI?\nQ2. Define ML?"
        papers = processor.split_papers_by_session(text)
        assert len(papers) == 1


class TestEvaluator:
    """Tests for confidence scoring."""

    def _make_paper(self, questions: list[dict]) -> PredictedPaper:
        """Helper to create a PredictedPaper."""
        pred_questions = [
            PredictedQuestion(
                question_number=q.get("num", 1),
                question_text=q.get("text", "Sample question"),
                topic=q.get("topic", ""),
                marks=q.get("marks", 10),
                confidence=q.get("confidence", 0.5),
            )
            for q in questions
        ]
        return PredictedPaper(
            sections=[
                PredictedSection(
                    section_name="A",
                    title="Test",
                    questions=pred_questions,
                )
            ],
            total_questions=len(pred_questions),
        )

    def test_quality_score_good_questions(self):
        """Well-formed questions should score high."""
        evaluator = Evaluator()
        paper = self._make_paper([
            {"text": "Explain the concept of fitness function in genetic algorithms.", "marks": 10, "topic": "GA"},
            {"text": "Compare crossover and mutation operators with examples.", "marks": 10, "topic": "GA"},
        ])
        syllabus = SyllabusStructure()
        report = evaluator.evaluate(paper, syllabus, {"frequency": []})
        assert report.question_quality_score > 0.5

    def test_quality_score_bad_questions(self):
        """Placeholder questions should score low."""
        evaluator = Evaluator()
        paper = self._make_paper([
            {"text": "Q", "marks": 1, "topic": ""},
            {"text": "", "marks": 1, "topic": ""},
        ])
        syllabus = SyllabusStructure()
        report = evaluator.evaluate(paper, syllabus, {"frequency": []})
        assert report.question_quality_score < 0.3

    def test_topic_coverage_full(self):
        """Should score high when all syllabus topics are covered."""
        evaluator = Evaluator()
        paper = self._make_paper([
            {"text": "Explain genetic algorithms", "marks": 10, "topic": "Genetic Algorithms"},
            {"text": "Describe neural networks", "marks": 10, "topic": "Neural Networks"},
        ])
        syllabus = SyllabusStructure(
            units=[
                {"unit_number": 1, "title": "GA", "topics": ["Genetic Algorithms"]},
                {"unit_number": 2, "title": "NN", "topics": ["Neural Networks"]},
            ]
        )
        report = evaluator.evaluate(paper, syllabus, {"frequency": []})
        assert report.topic_coverage_score > 0.5
