from litellm import completion
import os
from dotenv import load_dotenv
import re
import json

load_dotenv()

api_key = os.environ["GROQ_API_KEY"] 

def extract_syllabus_with_llm(syllabus_text: str) -> dict:
    prompt = f"""
    You are an academic document analyzer.
    Given the following syllabus text, extract the structured syllabus details in JSON format with the following keys:
    - course_title: (string)
    - units, chapters, or the actual content included in the course
    Syllabus:
    {syllabus_text}
    """

    response = completion(
        model="groq/gemma2-9b-it",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        stream=False,
    )

    extracted = response.choices[0].message["content"].strip()          #type: ignore

    # Remove markdown-style triple backticks if present
    if extracted.startswith("```json"):
        extracted = re.sub(r"^```json\s*|```$", "", extracted.strip(), flags=re.IGNORECASE)

    try:
        return json.loads(extracted)
    except Exception as e:
        print("⚠️ Still failed to parse JSON:", e)
        print("Raw cleaned output:\n", extracted)
        return {}

