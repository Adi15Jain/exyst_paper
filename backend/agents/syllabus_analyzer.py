"""Legacy standalone syllabus analyzer — uses Google AI Studio (Gemini) directly."""

from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import re
import json

load_dotenv()

# Initialize Gemini client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


def extract_syllabus_with_llm(syllabus_text: str) -> dict:
    prompt = f"""
    You are an academic document analyzer.
    Given the following syllabus text, extract the structured syllabus details in JSON format with the following keys:
    - course_title: (string)
    - units, chapters, or the actual content included in the course
    Syllabus:
    {syllabus_text}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
        ),
    )

    extracted = (response.text or "").strip()

    # Remove markdown-style triple backticks if present
    if extracted.startswith("```json"):
        extracted = re.sub(r"^```json\s*|```$", "", extracted.strip(), flags=re.IGNORECASE)

    try:
        return json.loads(extracted)
    except Exception as e:
        print("⚠️ Still failed to parse JSON:", e)
        print("Raw cleaned output:\n", extracted)
        return {}
