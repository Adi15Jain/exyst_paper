# Deploying Exyst to Vercel

The project deploys as a single Vercel project with two services (see
`vercel.json`): the Next.js frontend at `/` and the FastAPI backend at
`/_backend`. Vercel routes `/_backend/*` to the FastAPI app automatically — no
root-path configuration is needed, and the frontend calls the backend
same-origin, so CORS is not involved on Vercel.

Python dependencies for the backend service are installed from
`backend/requirements.txt` (Vercel only). Local dev, CI, and Docker install
from `backend/pyproject.toml` (`pip install -e ".[dev]"`).

## Required environment variables (Vercel project settings)

The backend **fails at startup** (every request 500s, including login) if these
are missing or left at placeholder values:

| Variable | Required | Notes |
| --- | --- | --- |
| `JWT_SECRET_KEY` | **Yes** | Must not be the placeholder. Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | **Yes** | Managed Postgres (Neon, Supabase, Vercel Postgres, …). Plain `postgresql://` URLs are rewritten to `postgresql+asyncpg://` automatically. |
| `GEMINI_API_KEY` | **Yes** | Google AI Studio key — analysis/prediction fail without it. |
| `DEBUG` | No | Defaults to `false`. Never set to `true` in production (it disables the config safety checks). |
| `CORS_ORIGINS` | No | Only needed if the frontend is served from a different origin than the backend. On Vercel services they share one domain, so the default is fine. |
| `DEFAULT_LLM_MODEL` | No | Defaults to `gemini-2.5-flash`. |
| `MAX_UPLOAD_SIZE_MB` | No | Defaults to 50. |

## Database migrations (required once per schema change)

In production the schema is owned by Alembic — the app does **not** create
tables itself (that only happens in `DEBUG`). A fresh database has no `users`
table, so register/login will 500 until migrations run.

Run against the production database from your machine:

```bash
cd backend
DATABASE_URL="postgresql://…your-prod-url…" alembic upgrade head
```

Alembic uses a sync driver; if `psycopg2` is not installed locally,
`pip install psycopg2-binary` first.

### Connection pooler note

If `DATABASE_URL` points at a PgBouncer-style pooler in transaction mode
(Supabase's `*.pooler.supabase.com:6543`, Neon's `-pooler` host), asyncpg's
prepared-statement cache breaks with "prepared statement already exists"
errors. The app disables the cache automatically when running on Vercel
(`app/db/session.py`). For Alembic migrations, prefer the **direct** (session
mode / non-pooler) connection string.

## Verifying a deployment

1. `https://<your-app>/_backend/api/v1/health` — must return 200. If it
   doesn't, check the Vercel **build logs** (dependency install, bundle size)
   and **function logs** (startup config errors) for the backend service.
2. Register + login through the UI.

## Known limitations on Vercel (open work)

These are architectural, not configuration, issues:

- **Uploads are ephemeral.** Files are written to `/tmp`, which is
  per-instance and short-lived. An analysis started in a later invocation may
  not find the uploaded file. Fix: move to object storage (Vercel Blob / S3)
  and store the object key instead of a filesystem path.
- **Background analysis (`POST /analysis/{id}/run`) doesn't survive.** FastAPI
  `BackgroundTasks` are killed when the serverless invocation ends; analyses
  can hang in `PROCESSING`. The SSE pipeline endpoint
  (`/pipeline/{id}/run-stream`) is the reliable path — it keeps the request
  open (up to the 300s `maxDuration` set in `vercel.json`).
- **RAG is disabled.** `chromadb` is excluded from the serverless bundle (size
  limit) and its `/tmp` vector store wouldn't persist anyway. The app degrades
  gracefully (predictions run without RAG context). Fix: replace ChromaDB with
  pgvector in the existing Postgres.
- **In-memory state resets per instance**: the LLM free-tier rate tracking,
  prompt cache, and auth rate limiting are per-instance best-effort.
