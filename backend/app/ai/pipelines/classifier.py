"""
Document classifier — determines whether a page is from a syllabus or question paper.

Uses LLM classification with batch processing for speed and quota efficiency.
"""

from typing import Literal

from app.ai.llm_client import LLMClient
from app.core.logging import get_logger

logger = get_logger(__name__)

CLASSIFIER_BATCH_SYSTEM_PROMPT = """You are a strict academic document classifier.
You classify a list of document pages into categories: "question_paper" or "syllabus".
You MUST return ONLY a valid JSON object matching the requested schema.
Do not include any other text, explanation, or markdown formatting."""

CLASSIFIER_BATCH_USER_PROMPT = """Classify each of the following pages into "question_paper" or "syllabus".

Categories definition:
- "question_paper": exam papers, questions (Q1, Q2), marks, duration, year/session (e.g. "2023-24").
- "syllabus": course structures, syllabus units, textbooks, reference books, course outcomes.

Pages list:
{pages_data}

Return a JSON object with this structure:
{{
    "classifications": [
        {{"page_number": 1, "classification": "syllabus"}},
        {{"page_number": 2, "classification": "question_paper"}}
    ]
}}
"""


class Classifier:
    """
    Classifies document pages as 'syllabus' or 'question_paper'.
    """

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or LLMClient()

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
        if not pages:
            return {
                "syllabus_text": "",
                "question_paper_text": "",
                "page_classifications": [],
                "syllabus_page_count": 0,
                "question_paper_page_count": 0,
            }

        # Build batch pages data context
        pages_data = ""
        for page in pages:
            page_num = page["page_number"]
            # Extract first 1500 chars of page text for classification
            snippet = page["text"][:1500].replace("{", "{{").replace("}", "}}")
            pages_data += f"--- Page {page_num} ---\n{snippet}\n\n"

        prompt = CLASSIFIER_BATCH_USER_PROMPT.format(pages_data=pages_data)

        try:
            result = await self.llm.complete_json(
                prompt=prompt,
                system_prompt=CLASSIFIER_BATCH_SYSTEM_PROMPT,
                temperature=0.0,
            )

            classifications_list = result.get("classifications", [])
            classifications_map = {
                item.get("page_number"): item.get("classification", "question_paper").lower().strip()
                for item in classifications_list
                if "page_number" in item
            }
        except Exception as e:
            logger.warning("batch_classification_failed", error=str(e))
            classifications_map = {}

        syllabus_pages: list[str] = []
        question_pages: list[str] = []
        page_classifications: list[dict] = []

        for page in pages:
            page_num = page["page_number"]
            text = page["text"]

            classification = classifications_map.get(page_num, "question_paper")
            if classification not in ("question_paper", "syllabus"):
                classification = "question_paper"

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
