# 🎯 Exyst — AI-Powered Exam Intelligence Platform

> Analyzes university syllabi and historical question papers to predict future exam questions with confidence scoring.

[![CI/CD](https://github.com/Adi15Jain/exyst_paper/actions/workflows/ci.yml/badge.svg)](https://github.com/Adi15Jain/exyst_paper/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## ✨ What It Does

- **📄 Document Intelligence** — Upload a combined PDF containing syllabus and previous year question papers. The system automatically classifies each page using LLM-powered document classification.
- **🧠 AI-Powered Prediction** — Analyzes topic frequency, detects rising/falling trends, and generates a complete predicted question paper using RAG + LLM reasoning.
- **📊 Confidence Scoring** — Every prediction comes with a multi-factor confidence score (topic coverage, historical alignment, question quality) so you know how much to trust it.
- **🔍 RAG-Enhanced Context** — Historical questions are vectorized via ChromaDB for semantic retrieval, improving prediction accuracy across sessions.

---

## 🏗 System Architecture

```
┌──────────────────┐     ┌───────────────────────────────────────────┐     ┌──────────┐
│  Next.js 15      │     │             FastAPI Backend               │     │PostgreSQL│
│  Frontend        │────▶│                                           │────▶│  16      │
│                  │     │  ┌─────────┐  ┌──────────┐  ┌─────────┐  │     │  Users   │
│  • Landing Page  │     │  │ Auth    │  │ Document │  │Analysis │  │     │  Docs    │
│  • Login/Signup  │     │  │ Service │  │ Service  │  │Service  │  │     │  Results │
│  • Dashboard     │     │  └─────────┘  └──────────┘  └─────────┘  │     └──────────┘
│  • Upload Flow   │     │       │            │             │         │
│  • Doc Results   │     │  ┌────▼────────────▼─────────────▼─────┐  │     ┌──────────┐
│  • Analytics     │     │  │         AI Pipeline Layer           │  │     │ ChromaDB │
└──────────────────┘     │  │                                     │  │────▶│ Vectors  │
                         │  │  PDF Parser → Classifier →          │  │     └──────────┘
                         │  │  Syllabus Analyzer →                 │  │
                         │  │  Pattern Analyzer → RAG Retrieval →  │  │     ┌──────────┐
                         │  │  Predictor → Evaluator               │  │     │  Redis   │
                         │  └─────────────────────────────────────┘  │────▶│  Cache   │
                         └───────────────────────────────────────────┘     └──────────┘
```

## 🧠 AI Pipeline

```
PDF Upload
    │
    ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  PDF Extraction  │────▶│  Page Classifier │────▶│  Split Documents│
│  (pdfminer +    │     │  (LLM-powered)   │     │  Syllabus vs QP │
│   PyMuPDF)      │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                    ┌─────────────────────────────────────┤
                    │                                     │
                    ▼                                     ▼
          ┌─────────────────┐                   ┌─────────────────┐
          │ Syllabus        │                   │ Question Paper  │
          │ Analyzer        │                   │ Pattern Analyzer│
          │ (extract topics)│                   │ (frequency +    │
          │                 │                   │  trends)        │
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
                        │  (structured    │
                        │   LLM output)   │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   Evaluator     │
                        │  (confidence    │
                        │   scoring)      │
                        └─────────────────┘
```

---

## 🛠 Tech Stack

| Layer        | Technology                                           |
| ------------ | ---------------------------------------------------- |
| **Frontend** | Next.js 15, React 19, TypeScript, TailwindCSS v4     |
| **Backend**  | FastAPI, Python 3.11+, Pydantic v2, SQLAlchemy 2.0   |
| **AI/LLM**   | LiteLLM (Groq/gemma2-9b-it), structured JSON outputs |
| **RAG**      | ChromaDB (vector embeddings, semantic search)        |
| **Database** | PostgreSQL 16, Alembic migrations                    |
| **Cache**    | Redis 7                                              |
| **Auth**     | JWT (access + refresh tokens), bcrypt                |
| **Logging**  | structlog (JSON structured logging)                  |
| **DevOps**   | Docker Compose, GitHub Actions CI/CD                 |
| **Testing**  | pytest (16 tests), pytest-asyncio, pytest-cov        |

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- A Groq API key ([get one free](https://console.groq.com))

### 1. Clone & configure

```bash
git clone https://github.com/Adi15Jain/exyst_paper.git
cd exyst_paper

# Set up your environment
cp backend/.env.example backend/.env
# Edit backend/.env and add your GROQ_API_KEY
```

### 2. Run with Docker Compose

```bash
docker compose up --build
```

### 3. Access the app

| Service                | URL                                 |
| ---------------------- | ----------------------------------- |
| **Frontend**           | http://localhost:3000               |
| **API Docs (Swagger)** | http://localhost:8000/docs          |
| **Health Check**       | http://localhost:8000/api/v1/health |

### Local Development (without Docker)

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install && npm run dev
```

---

## 📊 Key Features

### Document Intelligence

- Multi-strategy PDF extraction (pdfminer + PyMuPDF fallback)
- LLM-powered page classification (syllabus vs question paper)
- Automatic metadata extraction (university, course code, marks, session)

### Analysis Engine

- Structured syllabus extraction (units, topics, course outcomes)
- Topic-to-question mapping across multiple papers
- Frequency analysis with trend detection (rising/falling/stable topics)

### RAG Pipeline (ChromaDB)

- Historical questions stored as vector embeddings
- Semantic similarity search across past question papers
- Context retrieval to augment LLM prediction prompts
- Topic clustering and trend analysis

### Prediction Pipeline

- Context-aware prediction using syllabus + frequency + RAG retrieval
- Structured LLM output (Pydantic-validated, no JSON parse failures)
- Multi-section paper generation with marks distribution

### Confidence Scoring

- **Topic Coverage** — % of syllabus topics represented
- **Historical Alignment** — match with historical frequency patterns
- **Question Quality** — well-formedness and completeness checks
- **Weighted Composite** — single 0-1 confidence score

### Frontend (8 Pages)

- **Landing Page** — hero section with animated background, feature cards
- **Login / Register** — glassmorphism card with form validation
- **Dashboard** — stat cards, quick actions, recent documents
- **Upload** — drag & drop, multi-stage pipeline progress indicator
- **Documents** — paginated list with status badges
- **Document Detail** — tabbed view (predicted paper, analysis, confidence)
- **Analytics** — aggregate stats, confidence breakdown, performance metrics

### Production Features

- JWT authentication with refresh token rotation
- Per-user document isolation
- Structured JSON logging with request tracing
- Background task support for long-running analysis
- Health check endpoint with dependency status
- CORS configuration for frontend-backend communication

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
├── .github/workflows/ci.yml        # CI/CD pipeline
├── README.md                       # ← You are here
│
├── backend/
│   ├── app/
│   │   ├── main.py                 # Slim entry point (~50 lines)
│   │   ├── config.py               # Pydantic Settings
│   │   ├── dependencies.py         # FastAPI DI
│   │   ├── api/v1/                 # Route layer (6 modules)
│   │   │   ├── auth.py
│   │   │   ├── documents.py
│   │   │   ├── analysis.py
│   │   │   ├── predictions.py
│   │   │   ├── analytics.py        # Aggregate stats & charts
│   │   │   └── health.py
│   │   ├── core/                   # Cross-cutting concerns
│   │   │   ├── exceptions.py       # Custom exception hierarchy
│   │   │   ├── logging.py          # structlog setup
│   │   │   ├── middleware.py       # Request ID, timing, errors
│   │   │   └── security.py        # JWT utilities
│   │   ├── models/                 # SQLAlchemy ORM (4 models)
│   │   ├── schemas/                # Pydantic request/response
│   │   ├── services/               # Business logic layer
│   │   └── ai/                     # AI pipeline
│   │       ├── llm_client.py       # Centralized LLM with retry
│   │       ├── rag.py              # ChromaDB vector store
│   │       ├── evaluation.py       # Confidence scoring
│   │       └── pipelines/          # Processing stages
│   │           ├── document_processor.py
│   │           ├── classifier.py
│   │           ├── syllabus_analyzer.py
│   │           ├── pattern_analyzer.py
│   │           └── predictor.py
│   ├── tests/                      # 16 tests (API + AI + RAG)
│   ├── alembic/                    # DB migrations
│   ├── pyproject.toml              # Modern Python packaging
│   └── Dockerfile
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
    │       └── [id].tsx            # Detail (results/confidence)
    ├── components/
    │   ├── layout/AppLayout.tsx    # Sidebar + top bar
    │   └── ui/                     # Shared UI components
    ├── lib/
    │   ├── api.ts                  # Typed API client (auto-refresh)
    │   └── auth-context.tsx        # React auth context
    ├── styles/globals.css          # Design system (glassmorphism)
    └── Dockerfile
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
