"""
Pattern analyzer — detects topic frequency, trends, and recurring patterns
across multiple question papers.

This is the analytical engine that powers prediction confidence.
Uses code-based analysis (not LLM) for frequency calculations,
and LLM for semantic topic matching.
"""

from collections import Counter, defaultdict
from typing import Any

from app.ai.llm_client import LLMClient
from app.core.logging import get_logger

logger = get_logger(__name__)

TOPIC_EXTRACTION_PROMPT = """Analyze this question paper text and extract the topics covered, questions details, and overall exam metadata.

Return a JSON object with:
- "max_marks": integer or null (maximum marks of the exam paper, e.g. 60 or 100)
- "duration": string or null (duration of the exam, e.g. "3 Hours", "2 Hours")
- "instructions": array of strings (exam instructions list, e.g. ["Attempt all questions", "Scientific calculators allowed"])
- "questions": array of objects, each with:
    - "question_number": integer
    - "question_text": string (brief summary)
    - "topic": string (the main topic/concept)
    - "sub_topics": array of strings
    - "marks": integer
    - "question_type": "short" | "medium" | "long"

---

Question paper text:
{paper_text}
"""


class PatternAnalyzer:
    """
    Analyzes patterns across multiple question papers.
    """

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or LLMClient()

    async def extract_topics_from_paper(self, paper_text: str) -> dict[str, Any]:
        """
        Extract topics and metadata from a single question paper using LLM.

        Returns:
            Dict containing questions list, max_marks, duration, instructions.
        """
        if not paper_text.strip():
            return {"questions": []}

        prompt = TOPIC_EXTRACTION_PROMPT.format(
            paper_text=paper_text[:6000]
        )

        try:
            result = await self.llm.complete_json(
                prompt=prompt,
                system_prompt=(
                    "You are an academic content analyzer. "
                    "Extract question topics and exam metadata precisely. Return valid JSON only."
                ),
                temperature=0.1,
            )
            return result
        except Exception as e:
            logger.warning("topic_extraction_failed", error=str(e))
            return {"questions": []}

    async def analyze_frequency(
        self,
        papers: list[dict[str, str]],
    ) -> dict[str, Any]:
        """
        Analyze topic frequency across multiple papers.

        Args:
            papers: List of dicts with 'session' and 'text' keys.

        Returns:
            Dict with frequency data, trends, and patterns.
        """
        all_topics: list[str] = []
        topic_by_session: dict[str, list[str]] = defaultdict(list)
        questions_by_paper: list[list[dict]] = []
        max_marks_list: list[int] = []
        durations_list: list[str] = []

        for paper in papers:
            session = paper.get("session", "Unknown")
            paper_data = await self.extract_topics_from_paper(paper["text"])
            questions = paper_data.get("questions", [])
            questions_by_paper.append(questions)

            # Retrieve paper-level metadata
            max_marks = paper_data.get("max_marks")
            if max_marks is not None:
                try:
                    max_marks_list.append(int(max_marks))
                except (ValueError, TypeError):
                    pass
            duration = paper_data.get("duration")
            if duration:
                durations_list.append(str(duration).strip())

            for q in questions:
                topic = q.get("topic", "")
                if topic:
                    all_topics.append(topic)
                    topic_by_session[session].append(topic)

        # Calculate frequency
        topic_counts = Counter(all_topics)
        total_questions = len(all_topics)

        frequency_data: list[dict[str, Any]] = []
        for topic, count in topic_counts.most_common():
            frequency_data.append({
                "topic": topic,
                "count": count,
                "percentage": round(count / total_questions * 100, 1) if total_questions > 0 else 0,
                "trend": self._calculate_trend(topic, topic_by_session),
            })

        # Aggregate typical metadata
        most_common_max_marks = Counter(max_marks_list).most_common(1)
        most_common_duration = Counter(durations_list).most_common(1)

        typical_max_marks = most_common_max_marks[0][0] if most_common_max_marks else 100
        typical_duration = most_common_duration[0][0] if most_common_duration else "3 Hours"

        # Calculate typical question types and marks
        question_types_counts = defaultdict(int)
        question_types_marks = defaultdict(list)
        for paper_qs in questions_by_paper:
            for q in paper_qs:
                q_type = q.get("question_type", "medium")
                q_marks = q.get("marks")
                if q_marks is not None:
                    try:
                        q_marks = int(q_marks)
                        question_types_marks[q_type].append(q_marks)
                        question_types_counts[q_type] += 1
                    except (ValueError, TypeError):
                        pass

        format_summary = []
        num_papers = max(len(papers), 1)
        for q_type in ["short", "medium", "long"]:
            count = question_types_counts[q_type]
            marks_list = question_types_marks[q_type]
            if count > 0:
                avg_count_per_paper = round(count / num_papers, 1)
                typical_marks = Counter(marks_list).most_common(1)[0][0] if marks_list else 0
                format_summary.append(
                    f"- {q_type.capitalize()} questions: typical marks = {typical_marks}, average count per paper = {avg_count_per_paper}"
                )
        typical_format_str = "\n".join(format_summary) if format_summary else "No typical format patterns detected."

        # Detect patterns
        patterns = {
            "total_papers_analyzed": len(papers),
            "total_questions_found": total_questions,
            "unique_topics": len(topic_counts),
            "top_5_topics": [t["topic"] for t in frequency_data[:5]],
            "rising_topics": [t["topic"] for t in frequency_data if t["trend"] == "rising"],
            "falling_topics": [t["topic"] for t in frequency_data if t["trend"] == "falling"],
            "consistent_topics": [
                t["topic"] for t in frequency_data
                if t["trend"] == "stable" and t["count"] >= 2
            ],
            "max_marks": typical_max_marks,
            "duration": typical_duration,
            "typical_question_format": typical_format_str,
        }

        logger.info(
            "frequency_analysis_complete",
            total_papers=len(papers),
            total_questions=total_questions,
            unique_topics=len(topic_counts),
            max_marks=typical_max_marks,
            duration=typical_duration,
        )

        return {
            "frequency": frequency_data,
            "patterns": patterns,
            "topic_by_session": dict(topic_by_session),
            "questions_by_paper": questions_by_paper,
        }

    def _calculate_trend(
        self,
        topic: str,
        topic_by_session: dict[str, list[str]],
    ) -> str:
        """
        Determine if a topic is rising, falling, or stable.

        Simple heuristic: compare presence in recent vs older sessions.
        """
        sessions = sorted(topic_by_session.keys())

        if len(sessions) < 2:
            return "stable"

        # Split sessions into first half and second half
        mid = len(sessions) // 2
        older_sessions = sessions[:mid]
        newer_sessions = sessions[mid:]

        older_count = sum(1 for s in older_sessions if topic in topic_by_session[s])
        newer_count = sum(1 for s in newer_sessions if topic in topic_by_session[s])

        if newer_count > older_count:
            return "rising"
        elif newer_count < older_count:
            return "falling"
        else:
            return "stable"
