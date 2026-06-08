"""
Syllabus analyzer — extracts structured topic/unit information from syllabus text.
"""


from pydantic import BaseModel

from app.ai.llm_client import LLMClient
from app.core.logging import get_logger

logger = get_logger(__name__)

SYLLABUS_SYSTEM_PROMPT = """You are an expert academic syllabus analyzer.
Extract structured information from university syllabi.
Always return valid JSON. Do not include markdown formatting or explanations."""

SYLLABUS_USER_PROMPT = """Analyze this syllabus text and extract structured information.

Return a JSON object with these keys:
- "course_title": string (the name of the course)
- "course_code": string or null
- "total_units": integer
- "units": array of objects, each with:
    - "unit_number": integer
    - "title": string
    - "topics": array of strings (each individual topic/concept)
- "textbooks": array of strings (if mentioned)
- "course_outcomes": array of strings (if mentioned)

---

Syllabus text:
{syllabus_text}
"""


class SyllabusUnit(BaseModel):
    """A single unit/module in the syllabus."""
    unit_number: int = 0
    title: str = ""
    topics: list[str] = []


class SyllabusStructure(BaseModel):
    """Structured representation of a syllabus."""
    course_title: str = ""
    course_code: str | None = None
    total_units: int = 0
    units: list[SyllabusUnit] = []
    textbooks: list[str] = []
    course_outcomes: list[str] = []

    @property
    def all_topics(self) -> list[str]:
        """Flat list of all topics across all units."""
        topics = []
        for unit in self.units:
            topics.extend(unit.topics)
        return topics


class SyllabusAnalyzer:
    """
    Extracts structured syllabus information using LLM.
    """

    def __init__(self, llm_client: LLMClient | None = None):
        # Syllabus extraction is a structured task — use lite tier to save quota
        self.llm = llm_client or LLMClient(tier="lite")

    async def analyze(self, syllabus_text: str) -> SyllabusStructure:
        """
        Analyze syllabus text and return structured data.

        Args:
            syllabus_text: Raw text from syllabus pages.

        Returns:
            SyllabusStructure with course info, units, and topics.
        """
        if not syllabus_text.strip():
            logger.warning("empty_syllabus_text")
            return SyllabusStructure()

        prompt = SYLLABUS_USER_PROMPT.format(
            syllabus_text=syllabus_text[:6000]  # Truncate for token limits
        )

        try:
            result = await self.llm.complete_json(
                prompt=prompt,
                system_prompt=SYLLABUS_SYSTEM_PROMPT,
                temperature=0.2,
            )

            structure = SyllabusStructure.model_validate(result)

            logger.info(
                "syllabus_analyzed",
                course_title=structure.course_title,
                total_units=structure.total_units,
                total_topics=len(structure.all_topics),
            )

            return structure

        except Exception as e:
            logger.error("syllabus_analysis_failed", error=str(e))
            return SyllabusStructure()
