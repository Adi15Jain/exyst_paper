"""
Document classifier — determines whether a page is from a syllabus or question paper.

Uses LLM classification with few-shot prompting for accuracy.
"""

from typing import Literal

from app.ai.llm_client import LLMClient
from app.core.logging import get_logger

logger = get_logger(__name__)

CLASSIFIER_SYSTEM_PROMPT = """You are a strict academic document classifier.
You classify individual pages of text into exactly one category.
You MUST return ONLY a valid JSON object with a single key "classification".
Do not include any other text, explanation, or markdown formatting."""

CLASSIFIER_USER_PROMPT = """Classify this page into one of these categories:

1. "question_paper" — if the content contains:
   - Exam-style questions (Q1, Q2, etc.)
   - Time/marks indicators (e.g., "Time: 3 Hours", "Max. Marks: 60")
   - Instructions like "Attempt all questions"
   - Academic sessions (e.g., "2023-24", "May 2024")

2. "syllabus" — if the content contains:
   - Unit/module structure (e.g., "Unit I", "Module 2")
   - Course content or learning objectives
   - Textbooks or reference books
   - Course outcomes

Return a JSON object: {{"classification": "question_paper"}} or {{"classification": "syllabus"}}

---

Page text:
{page_text}
"""


class Classifier:
    """
    Classifies document pages as 'syllabus' or 'question_paper'.
    """

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or LLMClient()

    async def classify_page(self, page_text: str) -> Literal["question_paper", "syllabus"]:
        """
        Classify a single page of text.

        Returns:
            "question_paper" or "syllabus"
        """
        if not page_text.strip():
            return "question_paper"  # Default for empty pages

        # Truncate for token limits
        prompt = CLASSIFIER_USER_PROMPT.format(page_text=page_text[:3000])

        try:
            result = await self.llm.complete_json(
                prompt=prompt,
                system_prompt=CLASSIFIER_SYSTEM_PROMPT,
                temperature=0.0,
            )

            classification = result.get("classification", "question_paper").lower().strip()

            if classification not in ("question_paper", "syllabus"):
                logger.warning(
                    "unexpected_classification",
                    raw_value=classification,
                    defaulting_to="question_paper",
                )
                classification = "question_paper"

            return classification  # type: ignore

        except Exception as e:
            logger.warning(
                "classification_failed",
                error=str(e),
                defaulting_to="question_paper",
            )
            return "question_paper"

    async def classify_document(
        self, pages: list[dict]
    ) -> dict:
        """
        Classify all pages of a document and split into syllabus vs question paper text.

        Args:
            pages: List of dicts with 'page_number' and 'text' keys.

        Returns:
            Dict with 'syllabus_text', 'question_paper_text', and 'page_classifications'.
        """
        syllabus_pages: list[str] = []
        question_pages: list[str] = []
        page_classifications: list[dict] = []

        for page in pages:
            page_num = page["page_number"]
            text = page["text"]

            classification = await self.classify_page(text)

            logger.info(
                "page_classified",
                page=page_num,
                classification=classification,
                text_length=len(text),
            )

            page_classifications.append({
                "page_number": page_num,
                "classification": classification,
            })

            if classification == "syllabus":
                syllabus_pages.append(text)
            else:
                question_pages.append(text)

        result = {
            "syllabus_text": "\n\n".join(syllabus_pages),
            "question_paper_text": "\n\n".join(question_pages),
            "page_classifications": page_classifications,
            "syllabus_page_count": len(syllabus_pages),
            "question_paper_page_count": len(question_pages),
        }

        logger.info(
            "document_classified",
            syllabus_pages=len(syllabus_pages),
            question_paper_pages=len(question_pages),
        )

        return result
