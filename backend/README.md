# Exyst Backend

> FastAPI backend for the Exyst AI-Powered Exam Intelligence Platform.

## Tech Stack

- **Framework**: FastAPI 0.115+
- **Language**: Python 3.11+
- **ORM**: SQLAlchemy 2.0 (async)
- **Database**: PostgreSQL 16
- **Migrations**: Alembic
- **AI/LLM**: LiteLLM (Groq), ChromaDB (RAG)
- **Auth**: JWT (PyJWT + bcrypt)
- **Logging**: structlog (JSON)
- **Testing**: pytest + pytest-asyncio

## Architecture

```
app/
├── main.py              # Entry point (~50 lines)
├── config.py            # Pydantic Settings
├── dependencies.py      # FastAPI dependency injection
│
├── api/v1/              # HTTP route layer
│   ├── auth.py          # Register, login, refresh, me
│   ├── documents.py     # Upload, list, get
│   ├── analysis.py      # Run, status, result
│   ├── predictions.py   # Generate, get, confidence
│   ├── analytics.py     # Overview, topic frequency, breakdown
│   └── health.py        # Health check with dependency status
│
├── services/            # Business logic (no HTTP concerns)
│   ├── auth_service.py
│   ├── document_service.py
│   ├── analysis_service.py
│   └── prediction_service.py
│
├── ai/                  # AI pipeline
│   ├── llm_client.py    # Centralized LLM client (retry, structured output)
│   ├── rag.py           # ChromaDB vector store (index, retrieve)
│   ├── evaluation.py    # Multi-factor confidence scoring
│   └── pipelines/
│       ├── document_processor.py  # PDF extraction + metadata
│       ├── classifier.py          # Syllabus vs QP classification
│       ├── syllabus_analyzer.py   # Topic extraction
│       ├── pattern_analyzer.py    # Frequency + trends
│       └── predictor.py           # Paper generation
│
├── models/              # SQLAlchemy ORM (4 models)
│   └── __init__.py      # User, Document, Analysis, Prediction
│
├── schemas/             # Pydantic request/response models
│   ├── auth.py
│   ├── document.py
│   ├── analysis.py
│   └── prediction.py
│
├── core/                # Cross-cutting concerns
│   ├── exceptions.py    # Custom exception hierarchy
│   ├── logging.py       # structlog configuration
│   ├── middleware.py     # Request ID, timing, error handler
│   └── security.py      # JWT encode/decode utilities
│
└── db/
    └── session.py       # Async SQLAlchemy session factory
```

## API Endpoints (17 routes)

### Auth

| Method | Path                    | Description              |
| ------ | ----------------------- | ------------------------ |
| POST   | `/api/v1/auth/register` | Create new user          |
| POST   | `/api/v1/auth/login`    | Get access + refresh JWT |
| POST   | `/api/v1/auth/refresh`  | Rotate refresh token     |
| GET    | `/api/v1/auth/me`       | Get current user profile |

### Documents

| Method | Path                              | Description         |
| ------ | --------------------------------- | ------------------- |
| POST   | `/api/v1/documents/upload`        | Upload PDF          |
| GET    | `/api/v1/documents/`              | List user documents |
| GET    | `/api/v1/documents/{document_id}` | Get document detail |

### Analysis

| Method | Path                                    | Description             |
| ------ | --------------------------------------- | ----------------------- |
| POST   | `/api/v1/analysis/{document_id}/run`    | Start analysis pipeline |
| GET    | `/api/v1/analysis/{document_id}/status` | Check processing status |
| GET    | `/api/v1/analysis/{document_id}/result` | Get analysis results    |

### Predictions

| Method | Path                                           | Description           |
| ------ | ---------------------------------------------- | --------------------- |
| POST   | `/api/v1/predictions/{document_id}/generate`   | Generate prediction   |
| GET    | `/api/v1/predictions/{document_id}`            | Get predicted paper   |
| GET    | `/api/v1/predictions/{document_id}/confidence` | Get confidence scores |

### Analytics

| Method | Path                                                   | Description            |
| ------ | ------------------------------------------------------ | ---------------------- |
| GET    | `/api/v1/analytics/overview`                           | Aggregate stats        |
| GET    | `/api/v1/analytics/topic-frequency/{document_id}`      | Topic frequency charts |
| GET    | `/api/v1/analytics/confidence-breakdown/{document_id}` | Confidence breakdown   |

### Health

| Method | Path             | Description           |
| ------ | ---------------- | --------------------- |
| GET    | `/api/v1/health` | Health + dependencies |

## Getting Started

### With Docker (recommended)

```bash
# From the project root
docker compose up --build
# API at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Local development

```bash
# Create virtual environment
python -m venv venv && source venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Run dev server
uvicorn app.main:app --reload

# Open API docs
open http://localhost:8000/docs
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

| Variable         | Required | Description                  |
| ---------------- | -------- | ---------------------------- |
| `GROQ_API_KEY`   | ✅       | Groq API key for LLM calls   |
| `DATABASE_URL`   | ✅       | PostgreSQL connection string |
| `JWT_SECRET_KEY` | ✅       | Random 64-char hex string    |
| `HF_TOKEN`       |          | HuggingFace token (optional) |
| `REDIS_URL`      |          | Redis URL (default: local)   |
| `DEBUG`          |          | Enable debug mode            |

## Testing

```bash
# Run all 16 tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=app --cov-report=term-missing

# Just API tests
pytest tests/test_api/ -v

# Just AI tests
pytest tests/test_ai/ -v

# Lint
ruff check app/

# Type check
mypy app/ --ignore-missing-imports
```

### Test Suites

| Suite                    | Tests | What it covers                             |
| ------------------------ | ----- | ------------------------------------------ |
| `test_api/test_health`   | 2     | Health endpoint, OpenAPI docs availability |
| `test_ai/test_pipelines` | 8     | PDF metadata extraction, evaluator scoring |
| `test_ai/test_rag`       | 6     | ChromaDB indexing, retrieval, idempotency  |

## Database Migrations

```bash
# Generate a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```
