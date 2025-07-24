from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import PlainTextResponse
import os
import time
import json

from agents.classifier import split_pdf_by_classification
from agents.syllabus_analyzer import extract_syllabus_with_llm
from agents.ques_paper_analyzer import predict_next_paper_structure

app = FastAPI(title="Exyst Predictor")

UPLOAD_DIR = "uploads"
OUTPUTS_DIR = "outputs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

@app.post("/predict-question-paper/", response_class=PlainTextResponse)
async def predict_question_paper(file: UploadFile = File(...)):
    # 1. Save uploaded PDF
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    timestamp = int(time.time())
    safe_name = file.filename.replace(" ", "_")
    pdf_path = os.path.join(UPLOAD_DIR, f"{timestamp}_{safe_name}")
    with open(pdf_path, "wb") as f:
        f.write(await file.read())
    
    # 2. Split into syllabus and question paper text
    try:
        classified = split_pdf_by_classification(pdf_path)
        syllabus_text = classified["syllabus"]
        question_paper_text = classified["question_papers"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF classification failed: {str(e)}")
    
    # 3. (Optional) Split question_paper_text into separate past papers (can be refined)
    import re
    papers = re.split(r"(20\d{2}-\d{2}|20\d{2}|May \d{4})", question_paper_text)
    merged_papers = []
    i = 0
    while i < len(papers) - 1:
        year = papers[i + 1].strip()
        content = papers[i + 2].strip() if i + 2 < len(papers) else ''
        merged_papers.append(f"{year}\n{content}")
        i += 2
    if not merged_papers:
        merged_papers = [question_paper_text]
    
    # 4. Run syllabus analyzer (can be omitted if not used by predictor)
    try:
        syllabus_struct = extract_syllabus_with_llm(syllabus_text)
    except Exception as e:
        syllabus_struct = None  # fallback if extraction fails
    
    # 5. Predict next year's question paper (LLM-based synthesis)
    try:
        prediction = predict_next_paper_structure(
            merged_papers,
            syllabus_text=syllabus_text
        )
        if isinstance(prediction, dict) and prediction.get("predicted_question_paper"):
            pred_text = prediction["predicted_question_paper"]
        else:
            pred_text = str(prediction)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

    # 6. Save as JSON
    json_filename = f"predicted_{timestamp}.json"
    json_path = os.path.join(OUTPUTS_DIR, json_filename)
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(prediction, f, indent=2, ensure_ascii=False)
        print(f"Prediction saved to {json_path}")
    except Exception as e:
        print(f"Error saving prediction JSON: {e}")
    
    # 7. Return only the predicted question paper as plain text
    return pred_text
