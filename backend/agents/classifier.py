"""Legacy standalone classifier — uses Google AI Studio (Gemini) directly."""

from typing import Literal

from google import genai
from google.genai import types
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


def classify_chunk_with_llm(text: str) -> Literal["question_paper", "syllabus"]:
    prompt = f"""
    You are a strict academic document classifier.

    Your job is to classify a single page of text into exactly one of these categories:

    1. "question_paper" → If the content contains:
    - Exam format
    - Time/marks (e.g., "Time: 3 Hours", "Max. Marks: 60")
    - Question numbers (e.g., "Q1.", "Q2.", etc.)
    - Instructions like "Attempt all questions"
    - Sessions like "2023-24", "2022-23"

    2. "syllabus" → If the content contains:
    - Units (e.g., "Unit I", "Unit II")
    - Course content or learning objectives
    - Textbooks or reference books
    - Module structure or course outcomes

    ⚠️ You must return ONLY one of these exact values:
    → "question_paper"
    → "syllabus"

    Do not explain your answer. Do not add any extra text.
    ---

    ### Classify this page:
    {text}

    Classification:
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.0),
    )

    output = (response.text or "").strip().lower()
    if output in ("question_paper", "syllabus"):
        return output  # type: ignore[return-value]
    return "question_paper"


def split_pdf_by_classification(pdf_path: str):
    question_pages = []
    syllabus_pages = []

    for i, page_layout in enumerate(extract_pages(pdf_path)):
        text = ""
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                text += element.get_text()
        text = text.strip()

        print(f"\n🔍 Classifying Page {i+1}...")
        tag = classify_chunk_with_llm(text)
        print(f"🧠 Gemini says: {tag}")

        if tag == "syllabus":
            syllabus_pages.append(text)
        else:
            question_pages.append(text)

    return {
        "question_papers": "\n\n".join(question_pages),
        "syllabus": "\n\n".join(syllabus_pages)
    }