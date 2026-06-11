"""
Tests for AI pipeline components.
"""

import pytest

from app.ai.evaluation import Evaluator
from app.ai.llm_client import LLMResponse
from app.ai.pipelines.classifier import Classifier
from app.ai.pipelines.document_processor import DocumentProcessor
from app.ai.pipelines.syllabus_analyzer import SyllabusStructure
from app.core.exceptions import LLMOutputParsingError
from app.schemas.prediction import PredictedPaper, PredictedQuestion, PredictedSection


class _FakeLLM:
    """Minimal stand-in for LLMClient used to drive pipeline logic offline."""

    def __init__(self, json_result=None, raise_exc: Exception | None = None):
        self._json_result = json_result or {}
        self._raise = raise_exc

    async def complete_json(self, *args, **kwargs):
        if self._raise:
            raise self._raise
        return self._json_result


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


class TestClassifier:
    """Tests for the page classifier with a mocked LLM."""

    _PAGES = [
        {"page_number": 1, "text": "Course structure, units, reference books and outcomes."},
        {"page_number": 2, "text": "Q1. Define AI. Q2. Explain ML. Max Marks 60. 2023-24."},
    ]

    @pytest.mark.asyncio
    async def test_splits_pages_by_classification(self):
        fake = _FakeLLM(json_result={
            "classifications": [
                {"page_number": 1, "classification": "syllabus"},
                {"page_number": 2, "classification": "question_paper"},
            ]
        })
        classifier = Classifier(llm_client=fake)
        result = await classifier.classify_document(self._PAGES)

        assert result["syllabus_page_count"] == 1
        assert result["question_paper_page_count"] == 1
        assert "reference books" in result["syllabus_text"]
        assert "Define AI" in result["question_paper_text"]

    @pytest.mark.asyncio
    async def test_empty_pages_returns_empty(self):
        classifier = Classifier(llm_client=_FakeLLM())
        result = await classifier.classify_document([])
        assert result["syllabus_text"] == ""
        assert result["question_paper_text"] == ""
        assert result["page_classifications"] == []

    @pytest.mark.asyncio
    async def test_llm_failure_defaults_to_question_paper(self):
        """If the LLM call fails, every page falls back to question_paper."""
        classifier = Classifier(llm_client=_FakeLLM(raise_exc=RuntimeError("boom")))
        result = await classifier.classify_document(self._PAGES)
        assert result["question_paper_page_count"] == 2
        assert result["syllabus_page_count"] == 0

    @pytest.mark.asyncio
    async def test_unknown_label_defaults_to_question_paper(self):
        fake = _FakeLLM(json_result={
            "classifications": [
                {"page_number": 1, "classification": "nonsense"},
                {"page_number": 2, "classification": "question_paper"},
            ]
        })
        classifier = Classifier(llm_client=fake)
        result = await classifier.classify_document(self._PAGES)
        assert result["question_paper_page_count"] == 2


class TestLLMResponseParsing:
    """Tests for JSON parsing/cleaning on LLM responses."""

    def test_parse_plain_json(self):
        resp = LLMResponse(content='{"a": 1, "b": "x"}', model="test")
        assert resp.parse_json() == {"a": 1, "b": "x"}

    def test_parse_json_with_markdown_fences(self):
        resp = LLMResponse(content='```json\n{"a": 1}\n```', model="test")
        assert resp.parse_json() == {"a": 1}

    def test_parse_json_with_bare_fences(self):
        resp = LLMResponse(content='```\n{"a": 2}\n```', model="test")
        assert resp.parse_json() == {"a": 2}

    def test_malformed_json_raises(self):
        resp = LLMResponse(content="not json at all {", model="test")
        with pytest.raises(LLMOutputParsingError):
            resp.parse_json()
