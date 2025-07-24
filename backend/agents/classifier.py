from typing import Literal
from litellm import completion
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer
import os
from dotenv import load_dotenv

load_dotenv()

# ✅ Set your Groq API Key
api_key = os.environ['GROQ_API_KEY']

# ✅ Classify a page of text using Groq LLaMA 3
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

    ### Examples

    **Example 1:**
    Text:
    Q1. Answer the following:  
    a) Define crossover.  
    b) Explain mutation in genetic algorithms.  
    Max. Marks: 60  
    Time: 3 Hours  
    Classification: question_paper

    **Example 2:**
    Text:
    Unit I: Introduction to Genetic Algorithms  
    Course Outcomes:  
    - Understand fitness functions  
    Textbooks: Goldberg D.E.  
    Classification: syllabus

    ---

    ### Classify this page:
    {text}

    Classification:
    """

    response = completion(
        model="groq/gemma2-9b-it",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        stream=False
    )

    output = response.choices[0].message["content"].strip().lower()     #type:ignore
    return output
        
    
def split_pdf_by_classification(pdf_path: str):
    question_pages = []
    syllabus_pages = []

    for i, page_layout in enumerate(extract_pages(pdf_path)):
        # Concatenate text from all containers (blocks) on this page
        text = ""
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                text += element.get_text()
        text = text.strip()

        print(f"\n🔍 Classifying Page {i+1}...")
        tag = classify_chunk_with_llm(text)
        print(f"🧠 LLM says: {tag}")

        if tag == "syllabus":
            syllabus_pages.append(text)
        else:
            question_pages.append(text)

    return {
        "question_papers": "\n\n".join(question_pages),
        "syllabus": "\n\n".join(syllabus_pages)
    }