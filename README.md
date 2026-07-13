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
│  • Analytics     │     │  │         AI Pipeline Layer           │  │     │ pgvector │
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
                    │   pgvector RAG Layer    │
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

## 🔄 End-to-End Data Flow

A single upload travels through the system as follows. Stages marked **(LLM)** call
Gemini; everything else is deterministic Python.

```
1.  UPLOAD          Browser → POST /documents/upload (multipart)
                    Client-side 50MB guard → backend validates type/size/empty.
                    File written to UPLOAD_DIR/<user_id>/, SHA-256 hashed,
                    Document row created (status=PENDING).

2.  PIPELINE START  Browser opens an SSE stream: POST /pipeline/{id}/run-stream
                    Progress events ("event: stage") are pushed as each stage runs.
                    (REST fallback: POST /analysis/{id}/run schedules a background
                     task + the client polls /analysis/{id}/status — used if the
                     SSE connection drops.)

3.  EXTRACT         pdfminer.six → text per page (PyMuPDF fallback). No LLM.

4.  CLASSIFY (LLM)  One batched call labels every page "syllabus" | "question_paper".
                    Pages are split into syllabus_text and question_paper_text.

5.  SPLIT           question_paper_text is cut into individual papers on exam-header
                    / session boundaries (e.g. "ODD Semester Examination 2021-22").

6.  ANALYZE (LLM)   • Syllabus analyzer → units + topics (if a syllabus is present).
                    • Pattern analyzer → ONE batched call over all papers, returning
                      per-question topics, marks, the subject/course code, max marks,
                      duration, and question-type mix. Frequencies & trends are then
                      computed in plain Python (Counter), not by the LLM.

7.  INDEX (RAG)     Each historical question + syllabus topic is embedded
                    (Gemini text-embedding-004) and upserted into the
                    `vector_chunks` table, tagged with {user_id, document_id,
                    topic, marks, session}. Idempotent (stable chunk_key → no
                    duplicates on re-run).

8.  RETRIEVE (RAG)  For the top frequent topics + the course title, pgvector
                    returns the most semantically-similar historical questions
                    (cosine similarity, HNSW index) — filtered to the requesting
                    user — deduped and ranked → the "retrieved context".

9.  PREDICT (LLM)   The predictor prompt is assembled from: the actual past papers
                    (verbatim, as the format template) + extracted subject/marks +
                    topic frequencies + the RAG-retrieved questions. Gemini writes a
                    NEW paper in the SAME format. A second lite-model pass validates
                    and repairs marks totals / structure.

10. EVALUATE        Confidence is scored in Python across four factors (topic
                    coverage, historical alignment, question quality, marks
                    distribution). Empty/failed papers are auto-zeroed.

11. PERSIST         Analysis + Prediction rows saved (JSONB). SSE emits "complete";
                    the browser redirects to /documents/{id}.
```

Persistence: **Neon PostgreSQL** holds users, documents, analyses, predictions
(JSONB columns for the flexible AI payloads) **and** the question/topic vectors
(`vector_chunks`, pgvector). Uploaded files live on local disk, or in **Vercel Blob** when a
`BLOB_READ_WRITE_TOKEN` is configured (required for reliable serverless uploads).

---

## 🧠 Why Exyst Is a RAG System

RAG = **R**etrieval-**A**ugmented **G**eneration: instead of asking the model to
generate from its parametric memory alone, you _retrieve_ relevant external knowledge
at query time and _augment_ the prompt with it, so _generation_ is grounded in real
data. Exyst implements all three explicitly:

| RAG stage        | Where it happens in Exyst                                                             | Implementation                                                                                                                                                                                           |
| ---------------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Retrieval**    | `app/ai/rag.py` → `retrieve_similar_questions()`                                      | Every historical question is embedded into a vector space (pgvector); at prediction time we run a **cosine-similarity search** — scoped to the requesting user — over the top topics and the course title to pull the most relevant past questions. |
| **Augmentation** | `app/ai/pipelines/predictor.py` → `_format_rag_context()` + `_format_sample_papers()` | The retrieved questions **and** the verbatim past papers are injected into the generation prompt as grounding context.                                                                                   |
| **Generation**   | `predictor.predict()`                                                                 | Gemini generates a new paper _conditioned on_ that retrieved/injected context — not from generic priors.                                                                                                 |

**What specifically makes it RAG (not just "an LLM call"):**

1. **A vector store is the knowledge base.** Questions are stored as embeddings in
   Postgres/pgvector, not as plain rows. Retrieval is _semantic_ — "rank correlation" matches
   "Spearman's coefficient" even with no shared keywords.
2. **Retrieval is query-time and selective.** We don't dump every past question into
   the prompt; we retrieve the top-N most similar ones per topic and dedupe, keeping
   the prompt small and on-topic.
3. **Generation is grounded and attributable.** Each predicted question carries a
   topic and a confidence score derived from how strongly the historical corpus
   supports it. The evaluator's "historical alignment" factor measures exactly this.

> Exyst is a **hybrid-grounded** generator: classic vector RAG (pgvector retrieval)
> **plus** in-context grounding (the actual papers as a format template). The vector
> layer generalizes _across_ papers (semantically similar questions from different
> sessions); the in-context layer locks the _exact output format_. Together they fix
> the two failure modes of a naive LLM: wrong content and wrong format.

---

## ⚡ Performance & Optimization (what's already done)

The pipeline is deliberately **LLM-frugal** — only 3–4 model calls per full run:

| Optimization                            | Effect                                                                                                                              |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **Batched classification & extraction** | All pages classified in _one_ call; all papers' topics extracted in _one_ call — not N calls.                                       |
| **Tiered model routing**                | Heavy generation uses `gemini-2.5-flash`; cheap structured tasks (classification, validation) use `flash-lite`/`gemma`.             |
| **Model fallback + rotation**           | On 503/429/timeout the client rotates `flash → flash-lite → gemma` instead of hammering one model — resilient to provider overload. |
| **Adaptive rate-limit tracking**        | Per-model RPM windows (shared across instances) pick the least-loaded model first, preserving free-tier quotas.                     |
| **Prompt-level response cache**         | Identical prompts (TTL 1h) skip the API entirely — cached in Postgres, so a hit on any instance serves all of them.                 |
| **Deterministic where possible**        | Frequencies, trends, marks math, and confidence are computed in Python — the LLM is used only where it adds value.                  |
| **Async + background + SSE**            | FastAPI is fully async; long runs execute as background tasks with live SSE progress and a polling fallback.                        |
| **Serverless-aware DB pooling**         | `NullPool` on Vercel/serverless avoids stale Neon connections; a real pool is used on long-lived hosts.                             |
| **Content hashing**                     | Every upload is SHA-256 hashed — the hook for dedup/result-reuse is already in place.                                               |

---

## 📈 Scaling to 100,000 Users

The codebase is **stateless at the API layer** and **schema-migrated** (Alembic), so
horizontal scaling is mostly an infrastructure exercise. Honest bottlenecks first, then
the path.

### Current bottlenecks (single-instance assumptions)

- **LLM provider quota** is the hard ceiling — free/standard Gemini tiers cap at a few
  requests/minute. This, not CPU, limits throughput.
- **`BackgroundTasks`** run in the web process; they don't survive a restart, can't
  retry, and don't load-balance.
- **Local file storage** (`/tmp` on Vercel) is ephemeral and per-instance.

### The path to 100k users

| Concern                     | Change                                                                                                                                                                                                                              |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Throughput / LLM limits** | Move to a paid Gemini tier (or provisioned throughput) + a small key pool; queue generation so bursts smooth out. This is the #1 lever.                                                                                             |
| **Compute**                 | Run the FastAPI app as N stateless replicas behind a load balancer / autoscaler (it already holds no local session state).                                                                                                          |
| **Vector store**            | ✅ Done — vectors live in Postgres (pgvector), shared by all replicas. Next: index **per course, once**, and reuse across every student of that course (huge win — see below). |
| **Jobs**                    | Replace `BackgroundTasks` with a real queue (**Celery/RQ/Cloud Tasks**) + workers: durable, retryable, independently autoscaled, decoupled from the web tier.                                                                       |
| **Shared state**            | ✅ Done — the prompt cache, per-model RPM pacing, and rate limiters live in Postgres, so all replicas share quota accounting and cache hits.                                                                                          |
| **Database**                | Neon scales reads via replicas; front it with **PgBouncer** for connection pooling at high concurrency.                                                                                                                             |
| **File storage**            | Use **S3 / GCS** (object storage) instead of local disk for uploads.                                                                                                                                                                |
| **Frontend**                | Already CDN-served on Vercel; static + edge-cached.                                                                                                                                                                                 |
| **Result reuse**            | Cache analyses/predictions by **file hash** → identical/known papers return instantly with zero LLM cost.                                                                                                                           |

### Why this scales cleanly

Because the **expensive work is shared, not per-user.** 100k students of the same
course upload the _same_ past papers → one cached analysis + one shared RAG index
serves all of them. The per-user cost collapses to a cache lookup. The only genuinely
per-user LLM cost is a _novel_ paper set, which the queue absorbs and the cache then
remembers.

---

## ✅ Pros & ⚠️ Cons

**Pros**

- Clean, layered, fully-typed, fully-async backend; stateless and migration-ready.
- Quota-frugal AI pipeline (3–4 calls) with provider-failure resilience built in.
- Genuinely format-faithful output (replicates the real paper's structure & marks).
- Hybrid grounding (vector RAG + in-context) → accurate content _and_ format.
- Transparent confidence scoring; graceful degradation (fallback paper, never a crash).

**Cons / current limits**

- Throughput is bounded by the LLM provider's rate limits until you pay for higher tiers.
- `BackgroundTasks` (not a real queue) is fine for moderate load, not for 100k.
- Prediction quality depends on extraction quality for scanned/image-only PDFs (no OCR yet).
- Single LLM provider (Gemini) — no cross-provider failover today.

---

## 🔧 Further Processing Optimizations (roadmap)

> 📌 The full, prioritized platform improvement plan — security, infrastructure,
> product features, frontend engineering, and a 90-day sequencing — lives in
> [ROADMAP.md](ROADMAP.md). The list below covers pipeline-level optimizations only.

- **Dedup by file hash** — skip the whole pipeline when an identical PDF (or a known
  course's papers) was already processed; serve the cached result. _(hash already computed)_
- **Per-course shared RAG index** — build one vector index per course and reuse it
  for every student, instead of re-indexing per upload.
- **Separate text input streams** — let users paste/upload syllabus and past papers
  separately; removes the classification LLM call and its ambiguity entirely.
- **Persistent embedding cache** — cache embeddings keyed by question text so
  re-indexing is free.
- **Parallel stage execution** — syllabus analysis and pattern analysis are
  independent and can run concurrently.
- **Streaming generation** — stream the predicted paper token-by-token to the UI for
  perceived latency wins.
- **OCR fallback** (Tesseract / a vision model) for scanned, image-only PDFs.
- **Cross-provider failover** — add a non-Gemini backend to the fallback chain for
  full provider independence.

---

## 🛠 Tech Stack

| Layer        | Technology                                                   |
| ------------ | ------------------------------------------------------------ |
| **Frontend** | Next.js 15, React 19, TypeScript, TailwindCSS v4             |
| **Backend**  | FastAPI, Python 3.11+, Pydantic v2, SQLAlchemy 2.0           |
| **AI/LLM**   | Google AI Studio / Gemini 2.5 Flash, structured JSON outputs |
| **RAG**      | pgvector in Postgres (Gemini `text-embedding-004`, HNSW cosine index) |
| **Database** | Neon PostgreSQL (serverless, cloud-hosted)                   |
| **Auth**     | JWT (in-memory access token + revocable httpOnly-cookie refresh token), bcrypt |
| **Logging**  | structlog (JSON structured logging)                          |
| **DevOps**   | Docker Compose, GitHub Actions CI/CD                         |
| **Testing**  | pytest (79 backend tests), Vitest + ESLint (frontend)        |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+ and Node.js 20+
- A Google AI Studio API key ([get one here](https://aistudio.google.com/apikey))

### 1. Clone & configure

```bash
git clone https://github.com/Adi15Jain/exyst_paper.git
cd exyst_paper

# Set up your environment
cp backend/.env.example backend/.env
# Edit backend/.env and add your GEMINI_API_KEY and DATABASE_URL
```

### 2. Run locally

```bash
# One virtualenv at the repo root serves the whole project.
python -m venv .venv && source .venv/bin/activate

# Backend (terminal 1)
cd backend
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

> **Note:** With `DEBUG=true` (local dev) the backend automatically creates all database tables on startup. In production the schema is owned by Alembic — run `alembic upgrade head` against the database.

### 5. Deploy to Vercel

See [DEPLOYMENT.md](DEPLOYMENT.md) for the required environment variables, the database migration step, and known serverless limitations.

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

### RAG Pipeline (pgvector)

- Historical questions and syllabus topics indexed as vector embeddings in Postgres.
- Semantic similarity (cosine) search retrieves relevant past questions to guide predicted questions.
- Retrieval is **scoped to the owning user** — one user's questions can never ground another's prediction.
- Vectors live in the same database as everything else: they survive serverless cold starts, are shared across instances, and are removed automatically when a document is deleted.

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

## 🔌 API Endpoints (25 routes)

```
Auth:
  POST   /api/v1/auth/register
  POST   /api/v1/auth/login            (sets httpOnly refresh cookie)
  POST   /api/v1/auth/refresh          (cookie or body)
  POST   /api/v1/auth/logout           (revokes all refresh tokens)
  GET    /api/v1/auth/me
  PATCH  /api/v1/auth/me               (rename)
  DELETE /api/v1/auth/me               (delete account + all data)
  POST   /api/v1/auth/change-password  (requires current password)
  POST   /api/v1/auth/forgot-password  (emails a reset link)
  POST   /api/v1/auth/reset-password   (single-use token)

Documents:
  POST   /api/v1/documents/upload
  GET    /api/v1/documents/
  GET    /api/v1/documents/{document_id}
  PATCH  /api/v1/documents/{document_id}   (rename)
  DELETE /api/v1/documents/{document_id}

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
│   │       ├── rag.py              # pgvector vector store
│   │       ├── evaluation.py       # Confidence scoring (zero-score fallback logic)
│   │       └── pipelines/          # Processing stages
│   │           ├── document_processor.py
│   │           ├── classifier.py   # Batch page classifier
│   │           ├── syllabus_analyzer.py
│   │           ├── pattern_analyzer.py # Exam layout and marks pattern analyzer
│   │           └── predictor.py    # Pattern-aligned predicted paper generator
│   ├── tests/                      # 79 tests (API + AI + RAG)
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
    │   ├── settings.tsx            # Profile, password, delete account
    │   ├── forgot-password.tsx     # Request a reset link
    │   ├── reset-password.tsx      # Set a new password
    │   └── documents/
    │       ├── index.tsx           # Document list (rename/delete)
    │       └── [id].tsx            # Detail (results/confidence/regeneration UI)
    ├── components/
    │   ├── layout/AppLayout.tsx    # Sidebar + top bar (responsive)
    │   └── ui/                     # Banner, Spinner, EmptyState
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
source .venv/bin/activate      # repo-root venv
cd backend

# Run the backend suite (79 tests) — needs Postgres with the pgvector extension
# (e.g. `docker run -p 5432:5432 -e POSTGRES_PASSWORD=… pgvector/pgvector:pg16`)
pytest tests/ -v

# With coverage report
pytest tests/ -v --cov=app --cov-report=term-missing

# Lint
ruff check app/

# Type check
mypy app/ --ignore-missing-imports
```

Backend suites:

- `test_api/test_auth.py` — register, login, refresh rotation (cookie + body), logout revocation, `/me`, invalid/expired tokens, rate-limit
- `test_api/test_documents.py` — upload, list, get, validation, ownership isolation
- `test_api/test_analysis.py` — 202 contract, background success/failure persistence, ownership
- `test_api/test_predictions.py` — generate/get error contracts
- `test_ai/test_pipelines.py` — document processor, classifier (mocked LLM), JSON parsing, evaluator
- `test_ai/test_rag.py` — pgvector indexing, retrieval, ranking, user-scoping, idempotency, cascade

Frontend tests (Vitest + React Testing Library):

```bash
cd frontend
npm test     # API client: token refresh, 401-retry, error normalization
```

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
