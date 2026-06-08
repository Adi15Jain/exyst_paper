# 🎯 Exyst — AI-Powered Exam Intelligence Platform

> Analyzes university syllabi and historical question papers to predict future exam questions with confidence scoring.

[![CI/CD](https://github.com/Adi15Jain/exyst_paper/actions/workflows/ci.yml/badge.svg)](https://github.com/Adi15Jain/exyst_paper/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## ✨ What It Does

- **📄 Document Intelligence** — Upload a combined PDF containing a syllabus and previous year question papers. The system automatically partitions pages and classifies them using an optimized LLM-powered batch page classifier.
- **🧠 Advanced Pattern & Trend Analysis** — Extracts syllabus topics, structures, and course outcomes, while mapping typical historical question formats (marks distribution, question counts, and structure).
- **🔮 Dynamic Exam Prediction** — Generates a complete predicted question paper using Gemini 2.5 Flash. The structure dynamically aligns with historical formatting (e.g., matching the exact sections, question counts, and total marks like 60 or 100).
- **📊 Robust Confidence Scoring** — Every prediction includes a multi-factor confidence score (topic coverage, historical alignment, question quality). Failed or empty predictions are auto-detected and zero-scored to prevent misleading results.
- **🔄 Interactive UI & Recovery** — Includes a high-fidelity document analytics dashboard. Features interactive **Generate / Regenerate Prediction** triggers and robust rate-limit handling with exponential backoffs.

---

## 🏗 System Architecture

```
┌──────────────────┐     ┌───────────────────────────────────────────┐     ┌──────────┐
│  Next.js 15      │     │             FastAPI Backend               │     │Neon      │
│  Frontend        │────▶│                                           │────▶│PostgreSQL│
│                  │     │  ┌─────────┐  ┌──────────┐  ┌─────────┐  │     │  Users   │
│  • Landing Page  │     │  │ Auth    │  │ Document │  │Analysis │  │     │  Docs    │
│  • Login/Signup  │     │  │ Service │  │ Service  │  │Service  │  │     │  Results │
│  • Dashboard     │     │  └─────────┘  └──────────┘  └─────────┘  │     └──────────┘
│  • Upload Flow   │     │       │            │             │         │
│  • Doc Results   │     │  ┌────▼────────────▼─────────────▼─────┐  │     ┌──────────┐
│  • Analytics     │     │  │         AI Pipeline Layer           │  │     │ ChromaDB │
│  • Interactive   │     │  │                                     │  │────▶│ Vectors  │
│    Regeneration  │     │  │  PDF Parser → Batch Classifier →    │  │     └──────────┘
│                  │     │  │  Syllabus Analyzer →                 │  │
└──────────────────┘     │  │  Pattern Analyzer → RAG Retrieval →  │  │
                         │  │  Predictor → Evaluator               │  │
                         │  └─────────────────────────────────────┘  │
                         └───────────────────────────────────────────┘
```

## 🧠 AI Pipeline

```
PDF Upload
    │
    ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  PDF Extraction  │────▶│ Batch Classifier │────▶│  Split Documents│
│  (pdfminer +    │     │ (Single LLM Call │     │  Syllabus vs QP │
│   PyMuPDF)      │     │  for all pages)  │     │                 │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                    ┌─────────────────────────────────────┤
                    │                                     │
                    ▼                                     ▼
          ┌─────────────────┐                   ┌─────────────────┐
          │ Syllabus        │                   │ Question Paper  │
          │ Analyzer        │                   │ Pattern Analyzer│
          │ (extract topics)│                   │ (extract layout,│
          │                 │                   │  marks, counts) │
          └────────┬────────┘                   └────────┬────────┘
                   │                                     │
                   └──────────────┬──────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   ChromaDB RAG Layer    │
                    │  (semantic retrieval    │
                    │   of similar questions) │
                    └────────────┬────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   Predictor     │
                        │ (align layout & │
                        │  dynamic marks) │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   Evaluator     │
                        │ (multi-factor   │
                        │  scoring/fallback)│
                        └─────────────────┘
```

---

## 🛠 Tech Stack

| Layer        | Technology                                                   |
| ------------ | ------------------------------------------------------------ |
| **Frontend** | Next.js 15, React 19, TypeScript, TailwindCSS v4             |
| **Backend**  | FastAPI, Python 3.11+, Pydantic v2, SQLAlchemy 2.0           |
| **AI/LLM**   | Google AI Studio / Gemini 2.5 Flash, structured JSON outputs |
| **RAG**      | ChromaDB (vector embeddings, semantic search)                |
| **Database** | Neon PostgreSQL (serverless, cloud-hosted)                   |
| **Auth**     | JWT (access + refresh tokens), bcrypt (direct)               |
| **Logging**  | structlog (JSON structured logging)                          |
| **DevOps**   | Docker Compose, GitHub Actions CI/CD                         |
| **Testing**  | pytest (16 tests), pytest-asyncio, pytest-cov                |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+ and Node.js 20+
- A Google AI Studio API key ([get one here](https://aistudio.google.com/)) or Groq API key

### 1. Clone & configure

```bash
git clone https://github.com/Adi15Jain/exyst_paper.git
cd exyst_paper

# Set up your environment
cp backend/.env.example backend/.env
# Edit backend/.env and add your GEMINI_API_KEY (or GROQ_API_KEY) and DATABASE_URL
```

### 2. Run locally

```bash
# Backend (terminal 1)
cd backend
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload

# Frontend (terminal 2)
cd frontend
npm install && npm run dev
```

### 3. Run with Docker Compose (alternative)

```bash
docker compose up --build
```

### 4. Access the app

| Service                | URL                                 |
| ---------------------- | ----------------------------------- |
| **Frontend**           | http://localhost:3000               |
| **API Docs (Swagger)** | http://localhost:8000/docs          |
| **Health Check**       | http://localhost:8000/api/v1/health |

> **Note:** The backend automatically creates all database tables on startup — no manual migration needed for initial setup. Tables are created via SQLAlchemy's `create_all` in the app lifespan handler.

---

## 📊 Key Features

### Document Intelligence

- Multi-strategy PDF extraction (pdfminer + PyMuPDF fallback).
- **Batch Page Classification** — Groups page content and classifies pages concurrently in a single LLM request to avoid rate limits and minimize latency.
- Automatic metadata extraction (university, course code, duration, session).

### Analysis Engine

- Structured syllabus extraction (units, topics, course outcomes).
- **Exam Layout Discovery** — Analyzes historical question papers to determine typical question counts, section structures, and question-type weightings.
- Topic-to-question frequency mapping and trend detection (rising/falling/consistent).

### RAG Pipeline (ChromaDB)

- Historical questions indexed as vector embeddings.
- Semantic similarity search retrieves relevant past questions to guide predicted questions.
- Topic clustering and trend analysis.

### Dynamic Prediction Pipeline

- Generates section-wise exam predictions using Gemini 2.5 Flash.
- **Dynamic Layout Alignment** — Coerces predictions to match the typical exam layout discovered during pattern analysis (total questions, sections, and exact target marks like 60 or 100).
- Robust JSON-object output validation via Pydantic.
- Centralized `LLMClient` features rate-limit detection with a 15-second delay to safely use Gemini's free tier.

### Confidence Scoring

- **Topic Coverage** — % of syllabus topics represented.
- **Historical Alignment** — match with historical frequency patterns.
- **Question Quality** — syntax, structure, and clarity validation.
- **Zero-Scoring Fallback** — In case of unexpected extraction errors, the evaluator generates a clean fallback state with all confidence indicators marked at 0% instead of misleading placeholders.

### Frontend Dashboard

- **Landing Page** — Modern landing with glassmorphic cards and interactive features.
- **Upload Flow** — Real-time progress trackers for batch processing.
- **Interactive Document Results** — Displays predicted paper structure, sections, questions with topic tags, and question-level confidence. Includes a **Generate/Regenerate Prediction** action to run predictions on demand.
- **Analytics** — Aggregated dashboards featuring confidence breakdowns and metric trends.

---

## 🔌 API Endpoints (17 routes)

```
Auth:
  POST   /api/v1/auth/register
  POST   /api/v1/auth/login
  POST   /api/v1/auth/refresh
  GET    /api/v1/auth/me

Documents:
  POST   /api/v1/documents/upload
  GET    /api/v1/documents/
  GET    /api/v1/documents/{document_id}

Analysis:
  POST   /api/v1/analysis/{document_id}/run
  GET    /api/v1/analysis/{document_id}/status
  GET    /api/v1/analysis/{document_id}/result

Predictions:
  POST   /api/v1/predictions/{document_id}/generate
  GET    /api/v1/predictions/{document_id}
  GET    /api/v1/predictions/{document_id}/confidence

Analytics:
  GET    /api/v1/analytics/overview
  GET    /api/v1/analytics/topic-frequency/{document_id}
  GET    /api/v1/analytics/confidence-breakdown/{document_id}

Health:
  GET    /api/v1/health
```

---

## 📁 Project Structure

```
exyst/
├── docker-compose.yml              # Multi-service orchestration
├── pyrefly.toml                    # Python type checker config (venv)
├── .github/workflows/ci.yml        # CI/CD pipeline
├── README.md                       # ← You are here
│
├── backend/
│   ├── app/
│   │   ├── main.py                 # Entry point (lifespan handler)
│   │   ├── config.py               # Pydantic Settings (Gemini defaults)
│   │   ├── dependencies.py         # FastAPI DI
│   │   ├── api/v1/                 # Route layer (6 modules)
│   │   │   ├── auth.py
│   │   │   ├── documents.py
│   │   │   ├── analysis.py
│   │   │   ├── predictions.py      # Generate and fetch predictions
│   │   │   ├── analytics.py        # Aggregate stats & charts
│   │   │   └── health.py
│   │   ├── core/                   # Cross-cutting concerns
│   │   │   ├── exceptions.py       # Custom exception hierarchy
│   │   │   ├── logging.py          # structlog setup
│   │   │   ├── middleware.py       # Request ID, timing, errors
│   │   │   └── security.py         # JWT + bcrypt utilities
│   │   ├── models/                 # SQLAlchemy ORM (4 models)
│   │   ├── schemas/                # Pydantic request/response (PredictedPaper schema)
│   │   ├── services/               # Business logic layer
│   │   └── ai/                     # AI pipeline
│   │       ├── llm_client.py       # Gemini-ready client with retry and rate-limiting retry
│   │       ├── rag.py              # ChromaDB vector store
│   │       ├── evaluation.py       # Confidence scoring (zero-score fallback logic)
│   │       └── pipelines/          # Processing stages
│   │           ├── document_processor.py
│   │           ├── classifier.py   # Batch page classifier
│   │           ├── syllabus_analyzer.py
│   │           ├── pattern_analyzer.py # Exam layout and marks pattern analyzer
│   │           └── predictor.py    # Pattern-aligned predicted paper generator
│   ├── tests/                      # 16 tests (API + AI + RAG)
│   ├── alembic/                    # DB migrations
│   ├── pyproject.toml              # Modern Python packaging
│   ├── Dockerfile
│   └── .dockerignore
│
└── frontend/
    ├── pages/                      # 8 pages
    │   ├── index.tsx               # Landing page (hero)
    │   ├── login.tsx               # Auth (login/register)
    │   ├── dashboard.tsx           # Overview + stats
    │   ├── upload.tsx              # Upload + pipeline progress
    │   ├── analytics.tsx           # Aggregate analytics
    │   └── documents/
    │       ├── index.tsx           # Document list
    │       └── [id].tsx            # Detail (results/confidence/regeneration UI)
    ├── components/
    │   ├── layout/AppLayout.tsx    # Sidebar + top bar
    │   └── ui/                     # Shared UI components
    ├── lib/
    │   ├── api.ts                  # Typed API client (auto-refresh)
    │   └── auth-context.tsx        # React auth context
    ├── styles/globals.css          # Design system (glassmorphism)
    ├── Dockerfile
    └── .dockerignore
```

---

## 🧪 Testing

```bash
cd backend
source venv/bin/activate

# Run all 16 tests
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=app --cov-report=term-missing

# Lint
ruff check app/

# Type check
mypy app/ --ignore-missing-imports
```

Test suites:

- `test_api/` — Health endpoint, docs availability
- `test_ai/test_pipelines.py` — Document processor, evaluator scoring
- `test_ai/test_rag.py` — ChromaDB indexing, retrieval, idempotency

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit using conventional commits (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Built with ❤️ by <a href="https://github.com/Adi15Jain">Adi Jain</a>
</p>
