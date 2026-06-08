from litellm import completion
import os
from dotenv import load_dotenv
import re
import json
from typing import Dict, List, Any, Optional

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY")


def _clean_llm_json(extracted: str) -> str:
    if not extracted:
        return ""
    # Remove starting ```
    extracted = re.sub(r"^\s*```json\s*", "", extracted.strip(), flags=re.IGNORECASE)
    # Remove leading/trailing ```
    extracted = re.sub(r"^\s*```\s*", "", extracted)
    # extracted = re.sub(r"\s*```\s*$")
    return extracted.strip()


def analyze_question_paper(question_paper_text: str) -> Dict[str, Any]:
    """Analyze question paper text using LLM to extract structured information."""
    if not question_paper_text.strip():
        return {"error": "Empty question paper text provided"}
    
    prompt = f"""
    You are an academic question paper analyzer. Analyze the following question paper text and extract structured information in JSON format.

    Extract the following information:
    - academic_session: (string) e.g., "2024-25", "May 2023"
    - subject: (string) subject name if mentioned
    - duration: (string) exam duration if mentioned
    - max_marks: (integer) maximum marks for the paper
    - sections: (array) list of sections with their details
    - question_types: (object) count of different question types (MCQ, descriptive, etc.)
    - topics_covered: (array) list of topics/subjects covered
    - marks_distribution: (object) marks allocated to different sections/question types
    - total_questions: (integer) total number of questions
    - difficulty_analysis: (object) estimated difficulty breakdown

    Question Paper Text:
    {question_paper_text}

    Return ONLY valid JSON without any markdown formatting or explanations.
    """

    try:
        response = completion(
            model="gemini/gemini-2.5-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            stream=False,
        )

        # Safe chain to avoid attribute errors
        extracted = getattr(response.choices[0].message, "content", "")     #type: ignore
        if extracted is None:
            return {"error": "No response from LLM"}
        extracted = extracted.strip()
        extracted = _clean_llm_json(extracted)

        return json.loads(extracted)
    except json.JSONDecodeError as e:
        return {
            "error": "Failed to parse JSON",
            "raw_output": extracted,        #type: ignore
            "exception": str(e),
            "analysis_status": "failed"
        }
    except Exception as e:
        return {
            "error": f"Analysis failed: {str(e)}",
            "analysis_status": "failed"
        }


def extract_question_patterns(question_paper_text: str) -> Dict[str, Any]:
    """Extract specific question patterns and formats from the question paper."""
    if not question_paper_text.strip():
        return {"error": "Empty question paper text provided"}
    
    prompt = f"""
    Analyze this question paper and identify recurring patterns. Extract:

    1. Question numbering patterns (Q1, Q2, 1., a), etc.)
    2. Instruction patterns ("Attempt all questions", "Choose any 5", etc.)
    3. Marks indication patterns ("[5 marks]", "(10)", etc.)
    4. Section headers and their characteristics
    5. Question formats (Multiple choice, Fill in blanks, Short answer, etc.)

    Question Paper Text:
    {question_paper_text}

    Return analysis in JSON format focusing on structural patterns that repeat across questions.
    """

    try:
        response = completion(
            model="gemini/gemini-2.5-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            stream=False,
        )

        extracted = getattr(response.choices[0].message, "content", "")     #type: ignore
        if extracted is None:
            return {"error": "No response from LLM"}
        extracted = extracted.strip()
        extracted = _clean_llm_json(extracted)

        return json.loads(extracted)
    except json.JSONDecodeError as e:
        return {"patterns": "Could not extract patterns", "raw_output": extracted, "exception": str(e)}     #type: ignore
    except Exception as e:
        return {"error": f"Pattern extraction failed: {str(e)}"}


def compare_question_papers(papers: List[str]) -> Dict[str, Any]:
    """Compare multiple question papers to identify trends and patterns."""
    if len(papers) < 2:
        return {"error": "At least 2 question papers required for comparison"}

    combined_text = "\n\n--- PAPER SEPARATOR ---\n\n".join(papers)
    
    prompt = f"""
    Compare these multiple question papers and identify:

    1. Common topics that appear across papers
    2. Question format trends over time
    3. Marks distribution patterns
    4. Difficulty progression
    5. Topics that are frequently repeated
    6. New topics that have been introduced
    7. Topics that have been discontinued

    Papers to compare:
    {combined_text}

    Provide analysis in JSON format with insights about trends and patterns.
    """

    try:
        response = completion(
            model="gemini/gemini-2.5-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            stream=False,
        )

        extracted = getattr(response.choices[0].message, "content", "")     #type: ignore
        if extracted is None:
            return {"error": "No response from LLM"}
        extracted = extracted.strip()
        extracted = _clean_llm_json(extracted)

        return json.loads(extracted)
    except json.JSONDecodeError as e:
        return {"comparison": "Could not analyze papers", "raw_output": extracted, "exception": str(e)}     #type: ignore
    except Exception as e:
        return {"error": f"Comparison failed: {str(e)}", "paper_count": len(papers)}


def predict_next_paper_structure(question_papers: List[str], syllabus_text: Optional[str] = None) -> dict:
    """
    Predict the likely structure and content of the next question paper based on historical data.
    """
    if not question_papers:
        return {"error": "No question papers provided for prediction"}
    
    papers_text = "\n\n--- PAPER SEPARATOR ---\n\n".join(question_papers)
    
    context = f"Historical Question Papers:\n{papers_text}"
    if syllabus_text:
        context += f"\n\nCurrent Syllabus:\n{syllabus_text}"

    prompt = f"""
    Based on the historical question papers provided{' and current syllabus' if syllabus_text else ''}, predict the structure and likely content of the next question paper.

    Provide predictions for:
    1. Likely question types and their distribution
    2. Topics that are most likely to appear
    3. Estimated marks distribution
    4. Sections structure
    5. Difficulty level expectations
    6. New topics that might be introduced
    7. Pattern analysis and recommendations

    {context}

    Return detailed predictions in JSON format including a "predicted_question_paper" key, where possible, with the expected text of the next exam paper.
    """

    try:
        response = completion(
            model="gemini/gemini-2.5-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            stream=False,
        )

        extracted = getattr(response.choices[0].message, "content", "")     #type: ignore
        if extracted is None:
            return {"error": "No response from LLM"}
        extracted = extracted.strip()
        extracted = _clean_llm_json(extracted)

        return json.loads(extracted)
    except json.JSONDecodeError as e:
        return {
            "prediction": "Could not generate prediction",
            "raw_output": extracted,        #type: ignore
            "exception": str(e),
            "input_papers": len(question_papers),
            "has_syllabus": syllabus_text is not None
        }
    except Exception as e:
        return {
            "error": f"Prediction failed: {str(e)}",
            "input_papers": len(question_papers),
            "has_syllabus": syllabus_text is not None
        }


def comprehensive_question_paper_analysis(question_paper_text: str) -> Dict[str, Any]:
    """
    Perform comprehensive analysis combining all the above functions.
    """
    if not question_paper_text.strip():
        return {"error": "Empty question paper text provided"}
    
    basic_analysis = analyze_question_paper(question_paper_text)
    pattern_analysis = extract_question_patterns(question_paper_text)
    
    return {
        "basic_analysis": basic_analysis,
        "pattern_analysis": pattern_analysis,
        "analyzer_version": "1.0"
    }
