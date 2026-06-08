# Exyst Backend

> FastAPI backend for the Exyst AI-Powered Exam Intelligence Platform.

## Tech Stack

- **Framework**: FastAPI 0.115+
- **Language**: Python 3.11+
- **ORM**: SQLAlchemy 2.0 (async)
- **Database**: Neon PostgreSQL (Serverless Cloud)
- **Migrations**: Alembic
- **AI/LLM**: LiteLLM (Groq), ChromaDB (RAG)
- **Auth**: JWT (PyJWT) + Direct bcrypt hashing (Python 3.14 compatible)
- **Logging**: structlog (JSON)
- **Testing**: pytest + pytest-asyncio

## Architecture

```
app/
├── main.py              # Entry point (~80 lines, includes lifespan logic)
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
│   └── security.py      # JWT encode/decode and direct bcrypt hashing utilities
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

### Local Development (Recommended)

1. **Activate the Virtual Environment**:

    ```bash
    # From the backend directory
    python -m venv venv && source venv/bin/activate
    ```

2. **Install Dependencies**:

    ```bash
    pip install -e ".[dev]"
    ```

3. **Configure the Environment**:
   Create a `.env` file based on `.env.example`:

    ```bash
    cp .env.example .env
    ```

4. **Run the Dev Server**:

    ```bash
    uvicorn app.main:app --reload
    ```

    _Note: Tables are automatically created/migrated in the Neon PostgreSQL database on application startup via the lifespan handler._

5. **Access API Documentation**:
    - Swagger UI: http://localhost:8000/docs
    - ReDoc: http://localhost:8000/redoc

### With Docker

You can also run the backend containerized:

```bash
# From the project root
docker compose up --build
```

## Environment Variables

Configure these in `backend/.env`:

| Variable         | Required | Description                       |
| ---------------- | -------- | --------------------------------- |
| `GROQ_API_KEY`   | ✅       | Groq API key for LLM calls        |
| `DATABASE_URL`   | ✅       | Neon PostgreSQL connection string |
| `JWT_SECRET_KEY` | ✅       | Random 64-char hex string         |
| `DEBUG`          |          | Enable debug mode                 |

## Testing & Linting

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=app --cov-report=term-missing

# Lint & Type Check
ruff check app/
mypy app/ --ignore-missing-imports
```

## IDE / Type Checker Setup (Pyrefly)

If you are using the **Pyrefly** type checker extension in your IDE and see false-positive missing import warnings, ensure the type checker points to your local virtual environment:

1. Ensure `pyrefly.toml` exists at the root of the workspace.
2. In `backend/pyproject.toml`, the config section `[tool.pyrefly]` is already set up to point to the local `venv`:
    ```toml
    [tool.pyrefly]
    python_interpreter = "venv/bin/python"
    python-interpreter-path = "venv/bin/python"
    search_path = ["."]
    ```
3. If errors persist, reload your IDE window (e.g. `⌘ + Shift + P` -> `Developer: Reload Window` in VS Code) to clear the in-memory cache.
