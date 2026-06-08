# Exyst — Behavioral Interview Prep (STAR Method)

> **What is this document?**
> This is your interview-ready reference for discussing the **Exyst** project using the STAR method. Each answer demonstrates **Ownership**, **Impact**, **Collaboration**, **Judgment**, and **Self-awareness** — the five signals behavioral interviewers score on.

---

## 🎯 Project Overview

**Exyst** is an AI-powered exam intelligence platform that analyzes university syllabi and historical question papers to predict future exam questions with confidence scoring. It uses a multi-stage AI pipeline — PDF extraction, LLM-powered page classification, syllabus analysis, pattern detection, RAG-enhanced retrieval via ChromaDB, and structured LLM prediction — backed by a FastAPI backend, Neon PostgreSQL database, and Next.js 15 frontend.

### Architecture at a Glance

```
PDF Upload → PDF Extraction (pdfminer + PyMuPDF)
                │
                ▼
        Page Classifier (LLM-powered)
                │
          ┌─────┴─────┐
          ▼           ▼
   Syllabus        Question Paper
   Analyzer        Pattern Analyzer
   (topics)        (frequency + trends)
          │           │
          └─────┬─────┘
                ▼
        ChromaDB RAG Layer
        (semantic retrieval)
                │
                ▼
           Predictor
        (structured LLM)
                │
                ▼
           Evaluator
        (confidence scoring)
```

### Key Metrics

| Metric | Value |
| :--- | :--- |
| **API Routes** | 17 endpoints across 6 modules |
| **AI Pipeline Stages** | 6 (extraction → classification → syllabus → patterns → RAG → prediction) |
| **Test Suite** | 16 tests (API + AI pipelines + RAG) |
| **Backend Architecture** | FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| **LLM Provider** | LiteLLM (Groq/gemma2-9b-it) with structured JSON outputs |
| **Vector Store** | ChromaDB for semantic similarity search |
| **Database** | Neon PostgreSQL (serverless) |
| **Auth** | JWT with refresh token rotation + bcrypt |
| **Frontend Pages** | 8 (Landing, Login, Register, Dashboard, Upload, Documents, Detail, Analytics) |
| **Confidence Scoring** | 4-factor composite (topic coverage, historical alignment, question quality, weighted) |
| **Logging** | structlog (JSON structured logging with request tracing) |
| **DevOps** | Docker Compose + GitHub Actions CI/CD |
| **PDF Extraction** | Multi-strategy (pdfminer primary + PyMuPDF fallback) |

---

## Prompt A — "Tell me about a time you disagreed with a teammate."

> **Situation:** While building Exyst — a platform that predicts university exam questions from historical papers — I was designing the document processing pipeline. The system receives a single combined PDF containing both syllabus pages and question paper pages. A contributor argued that the user should manually tag which pages are syllabus and which are question papers during upload, because "it's simpler and more reliable than trying to classify automatically."
>
> **Task:** I owned the AI pipeline architecture and had to decide whether to require manual page tagging or build LLM-powered automatic classification, knowing this would define the user experience for every upload and the accuracy of downstream analysis.
>
> **Action:** I agreed that manual tagging would be more *accurate* on a per-page basis, but I mapped the user experience implications. I timed myself tagging a real 40-page combined PDF (syllabus + 3 years of question papers): it took 8 minutes of tedious page-by-page labeling. Then I built the automatic classifier — a prompt-engineered LLM call that receives each page's text and classifies it as "syllabus" or "question_paper" based on structural cues (presence of marks, question numbering, unit headers, course outcomes). I tested it on 5 sample PDFs and measured: the classifier agreed with manual labels on 95% of pages, and the 5% it got wrong were ambiguous pages (like a syllabus with embedded sample questions) that even humans would disagree on. I presented both options: "Manual tagging is 100% accurate but takes 8 minutes per upload. Automatic classification is 95% accurate with zero user effort, and the downstream pipeline is robust to a few misclassified pages because the pattern analyzer cross-validates against the syllabus structure."
>
> **Result:** We shipped automatic LLM-powered classification. The upload flow now takes under 30 seconds of user time (drag-and-drop, then wait for the pipeline). The classifier runs as part of a 6-stage pipeline: extraction → classification → syllabus analysis → pattern analysis → RAG retrieval → prediction. User testing showed that the 5% classification error rate had negligible impact on prediction quality because the pattern analyzer validates topics against the extracted syllabus, catching most misclassifications. The contributor later acknowledged that the zero-effort upload was critical for user adoption.

**Why this answer works:**
- High stakes: user experience for every upload, pipeline accuracy for every prediction.
- "I mapped... I timed... I built... I tested... I presented" — clear ownership.
- Resolved with *user experience data* (8 min vs 30 sec) and *accuracy measurement* (95%), not opinion.
- Quantified result (30-second uploads, 95% accuracy, 6-stage pipeline, negligible downstream impact).
- Respectful collaboration: acknowledged the accuracy concern, showed the robustness argument.

---

## Prompt B — "Tell me about a time you failed."

> **Situation:** Exyst's prediction pipeline uses LiteLLM to call Groq's gemma2-9b-it model for generating predicted question papers. The pipeline assembles context from syllabus analysis, frequency data, and RAG-retrieved historical questions, then asks the LLM to produce a complete question paper as structured JSON — validated against a Pydantic schema (`PredictedPaper` with sections, questions, marks, confidence scores).
>
> **Task:** I was responsible for the entire AI prediction pipeline — from context assembly through LLM generation to output validation and confidence scoring.
>
> **Action:** I built the predictor with a detailed system prompt and a structured user prompt that includes syllabus topics, frequency summaries, trend data (rising/falling/consistent topics), and sample questions from past papers. I tested it on 3 courses and it produced well-structured predicted papers. So I shipped it. What I *didn't* do was test the pipeline when the LLM returned malformed JSON — which happens unpredictably with open-weight models, especially under high load or when the prompt context is very long. Two weeks after launch, a user uploaded a dense 60-page PDF. The pipeline ran the full extraction, classification, and analysis (which took ~45 seconds of LLM calls), but then the final prediction step returned JSON with a trailing comma that broke Pydantic validation. The entire pipeline failed, and the user got a generic error after waiting nearly a minute.
>
> **Result:** The user lost a minute of processing time and got no result. I fixed it in two ways: (1) I added a `_create_fallback_paper()` method to the Predictor class that returns a minimal valid `PredictedPaper` with `overall_confidence: 0.0` and a message explaining the generation error — so the user always gets *something* back, even if the LLM fails. (2) I added retry logic to the `LLMClient` with exponential backoff, and I implemented JSON repair (stripping trailing commas, fixing unclosed brackets) before Pydantic validation. The pipeline hasn't had a user-facing failure since, but the real cost was that the first user who hit this edge case churned — they never came back.
>
> **What I learned / changed:** I now treat LLM output as *untrusted external input*, the same way I'd treat user input or a third-party API response. Every LLM call in the pipeline now has: (1) retry logic, (2) JSON repair pre-processing, (3) a fallback return value, and (4) structured logging of the failure with the raw LLM output for debugging. The principle is: *the pipeline must never fail from the user's perspective — it can degrade (lower confidence, fallback output) but never crash.*

**Why this answer works:**
- Real failure with real user impact (user waited a minute, got nothing, churned).
- Owns the root cause: didn't test LLM output validation for malformed JSON.
- Shows the recovery: fallback paper, retry logic, JSON repair, structured logging.
- Concrete behavior change: "treat LLM output as untrusted external input."
- Honest about the cost: acknowledges the user churned, doesn't minimize.

---

## Prompt C — "Tell me about a time you had to learn something quickly."

> **Situation:** Exyst's core differentiator is its RAG (Retrieval-Augmented Generation) pipeline — historical exam questions are vectorized and stored in ChromaDB so that when generating a predicted paper, the LLM has semantically similar past questions as context. I had used LLMs for text generation before, but I'd never built a RAG pipeline — I didn't understand vector embeddings, similarity search, or how to integrate a vector database with an LLM prediction workflow.
>
> **Task:** I had to design, implement, and integrate a ChromaDB-based RAG pipeline into Exyst's prediction workflow — including document vectorization, semantic retrieval, context assembly, and LLM prompting — within 10 days, because the prediction quality without historical context was too low for launch.
>
> **Action:** I broke the learning into three focused steps. (1) **Vector embeddings fundamentals**: I learned how ChromaDB's default embedding function converts text chunks into vectors, and how cosine similarity finds semantically related questions — I didn't need to understand the embedding model internals, just the API contract (text in, vector out, query returns ranked results). (2) **Indexing strategy**: I studied how to chunk exam questions for optimal retrieval — one question per document, with metadata (topic, marks, year, paper) so I could filter by topic during retrieval. I tested different chunking strategies and found that individual questions with metadata produced far better retrieval than full-page embeddings. (3) **RAG integration pattern**: I connected the retrieval step to the prediction prompt — the predictor now queries ChromaDB for the top 10 most similar historical questions for each predicted topic, and includes them in the LLM prompt as "Sample Questions from Past Papers." I validated each step with the test suite: `test_ai/test_rag.py` covers ChromaDB indexing, retrieval accuracy, and idempotency (re-indexing the same document doesn't create duplicates).
>
> **Result:** The RAG pipeline was integrated in 8 days. ChromaDB stores all historical questions as vector embeddings with topic/year metadata. Semantic search retrieves the top 10 relevant past questions per prediction, which are injected into the LLM prompt as context. The prediction quality improved measurably — confidence scores rose from an average of 0.45 (without RAG context) to 0.72 (with RAG context) across test courses, because the LLM now generates questions that match historical style, difficulty, and topic distribution. The RAG test suite (3 tests: indexing, retrieval, idempotency) passes in CI, and the pipeline is documented in the architecture diagram in the README.

**Why this answer works:**
- Specific, high-stakes constraint: learn RAG from scratch, integrate in 10 days, prediction quality depended on it.
- Shows *how* I learn: three focused steps, didn't over-learn (skipped embedding model internals), validated with tests.
- Quantified impact: 8 days, confidence scores 0.45 → 0.72, top-10 retrieval, 3-test RAG suite.
- The test suite shows durable engineering, not just "I got it working."
- Tied to business impact: prediction quality was too low for launch without RAG.

---

## 📝 Practice Notes

> **Target delivery: ~90 seconds to 2 minutes per answer.**
>
> - If you're past 30 seconds and haven't started the **Action**, cut the Situation.
> - Every Action sentence should have **"I"** as the subject.
> - End with: *"Does that answer it, or would you like me to go deeper on any part?"*
>
> These three stories also cover: **AI/ML engineering**, **LLM integration**, **user experience decisions**, and **production resilience**. The Exyst stories are especially strong for "technical tradeoff" (auto-classification), "production incident" (LLM malformed output), "how you handle ambiguity" (RAG design), and "a time you prioritized the user" (zero-effort uploads).

---

*Prepared using the [STAR Method framework](./01-star-method.md) · [Back to Project README](./README.md)*
