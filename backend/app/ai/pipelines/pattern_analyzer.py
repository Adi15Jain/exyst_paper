"""
Pattern analyzer — detects topic frequency, trends, and recurring patterns
across multiple question papers.

This is the analytical engine that powers prediction confidence.
Uses a SINGLE batched LLM call for all papers (quota-efficient),
and code-based analysis for frequency calculations.
"""

from collections import Counter, defaultdict
from typing import Any

from app.ai.llm_client import LLMClient
from app.core.logging import get_logger

logger = get_logger(__name__)

# Batched prompt — analyzes ALL papers in one LLM call instead of N separate calls
BATCH_TOPIC_EXTRACTION_PROMPT = """You are given the verbatim text of {num_papers} university question paper(s).
Extract the course metadata and the topic of every question, reading ONLY what is actually written.

STRICT RULES:
- The `topic` of each question MUST be the specific concept that question is about, taken
  from the question's own words. Do NOT invent generic or unrelated topics. For example, a
  question "Find the mean value of the following data" has topic "Mean / Measures of Central
  Tendency" — NOT "Mathematics" or some unrelated subject.
- `subject` is the course name printed in the paper header (e.g. "Fundamentals of Statistics").
- If a value is not present in the text, use null. Never guess a subject or topic from outside
  the paper's content.

Return a JSON object with this structure:
{{
    "papers": [
        {{
            "session": "paper_0",
            "subject": "Course name from the header, or null",
            "course_code": "Course code from the header, or null",
            "max_marks": 60,
            "duration": "3 Hours",
            "instructions": ["Attempt all questions"],
            "questions": [
                {{
                    "question_number": 1,
                    "question_text": "Brief summary of the question",
                    "topic": "Specific concept this question tests",
                    "sub_topics": ["sub-topic1"],
                    "marks": 5,
                    "question_type": "short"
                }}
            ]
        }}
    ]
}}

question_type MUST be one of: "short", "medium", "long"

---

{papers_text}
"""


class PatternAnalyzer:
    """
    Analyzes patterns across multiple question papers.
    Uses lite-tier models and batched calls for quota efficiency.
    """

    def __init__(self, llm_client: LLMClient | None = None):
        # Use the default (stronger) tier: topic grounding is the foundation of the whole
        # prediction, and weaker models hallucinate unrelated topics here.
        self.llm = llm_client or LLMClient()

    async def analyze_frequency(
        self,
        papers: list[dict[str, str]],
    ) -> dict[str, Any]:
        """
        Analyze topic frequency across multiple papers using a SINGLE batched LLM call.

        Args:
            papers: List of dicts with 'session' and 'text' keys.

        Returns:
            Dict with frequency data, trends, and patterns.
        """
        if not papers:
            return {
                "frequency": [],
                "patterns": {},
                "topic_by_session": {},
                "questions_by_paper": [],
            }

        # --- BATCHED extraction: one LLM call for ALL papers ---
        papers_text_parts = []
        for i, paper in enumerate(papers):
            session = paper.get("session", f"paper_{i}")
            # Truncate each paper to keep within token limits
            text = paper["text"][:4000]
            papers_text_parts.append(f"=== PAPER {i} (Session: {session}) ===\n{text}")

        combined_text = "\n\n".join(papers_text_parts)

        prompt = BATCH_TOPIC_EXTRACTION_PROMPT.format(
            num_papers=len(papers),
            papers_text=combined_text,
        )

        try:
            result = await self.llm.complete_json(
                prompt=prompt,
                system_prompt=(
                    "You are an academic content analyzer. "
                    "Extract question topics and exam metadata from ALL papers. Return valid JSON only."
                ),
                temperature=0.1,
            )
            papers_data = result.get("papers", [])
        except Exception as e:
            logger.warning("batch_topic_extraction_failed", error=str(e))
            papers_data = []

        # --- Process results ---
        all_topics: list[str] = []
        topic_by_session: dict[str, list[str]] = defaultdict(list)
        questions_by_paper: list[list[dict]] = []
        max_marks_list: list[int] = []
        durations_list: list[str] = []
        subjects_list: list[str] = []
        course_codes_list: list[str] = []

        for i, paper in enumerate(papers):
            session = paper.get("session", f"paper_{i}")

            # Match paper data from LLM response
            paper_data = papers_data[i] if i < len(papers_data) else {}
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
            subject = paper_data.get("subject")
            if subject and str(subject).strip().lower() not in ("", "null", "none", "unknown"):
                subjects_list.append(str(subject).strip())
            course_code = paper_data.get("course_code")
            if course_code and str(course_code).strip().lower() not in ("", "null", "none"):
                course_codes_list.append(str(course_code).strip())

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

        most_common_subject = Counter(subjects_list).most_common(1)
        most_common_code = Counter(course_codes_list).most_common(1)
        subject = most_common_subject[0][0] if most_common_subject else None
        course_code = most_common_code[0][0] if most_common_code else None

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
            "subject": subject,
            "course_code": course_code,
            "typical_question_format": typical_format_str,
        }

        logger.info(
            "frequency_analysis_complete",
            total_papers=len(papers),
            total_questions=total_questions,
            unique_topics=len(topic_counts),
            max_marks=typical_max_marks,
            duration=typical_duration,
            llm_calls_used=1,  # Just 1 batched call!
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
