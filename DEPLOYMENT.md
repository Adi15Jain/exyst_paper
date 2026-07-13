# Deploying Exyst to Vercel

> **First time, or picking this up after a break?** [OWNER-SETUP.md](OWNER-SETUP.md)
> is the click-by-click checklist: secret rotation, migrations, the Blob store,
> and the accounts that unlock pending features. This file is the reference for
> what each variable does.

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
| `BLOB_READ_WRITE_TOKEN` | **Strongly recommended** | Enables Vercel Blob for uploads. Without it files go to `/tmp` and may vanish before analysis runs. Created automatically when you add a Blob store to the project (Vercel dashboard → Storage → Create Database → Blob). |
| `RESEND_API_KEY` | For password reset | Without it, reset emails are **not sent** — the link is only logged (an error outside `DEBUG`). Get one at resend.com and verify a sending domain. |
| `EMAIL_FROM` | No | Sender address, e.g. `Exyst <noreply@yourdomain.com>`. Defaults to Resend's shared test sender. |
| `APP_BASE_URL` | For password reset | Public URL of the frontend (e.g. `https://your-app.vercel.app`) — used to build the reset link. Defaults to `http://localhost:3000`, which would email unusable links in production. |
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
source ../.venv/bin/activate    # the repo-root venv
alembic upgrade head            # reads DATABASE_URL from backend/.env
```

Alembic runs on the **async (asyncpg) driver** — the same one the app uses. You
do **not** need `psycopg2`. Prefer letting it read `DATABASE_URL` from
`backend/.env` rather than pasting a connection string on the command line
(shell history is a great place to leak a password).

Both the pooled (`-pooler`) and direct Neon URLs work: `alembic/env.py` disables
asyncpg's prepared-statement cache, which is what otherwise breaks against
transaction-mode poolers ("prepared statement already exists").

### Adopting a database that pre-dates Alembic

If a database was first created by the old `DEBUG=true` `create_all` bootstrap,
its tables exist but it has no `alembic_version` row. Alembic therefore thinks
it is empty and previously failed with:

```
asyncpg.exceptions.DuplicateTableError: relation "users" already exists
```

The migrations are now **idempotent** — each one skips objects that already
exist — so `alembic upgrade head` simply adopts such a database, applies only
what is genuinely missing, and stamps it at head. Existing rows are untouched.
No manual `alembic stamp` is needed.

## Verifying a deployment

1. `https://<your-app>/_backend/api/v1/health` — must return 200. If it
   doesn't, check the Vercel **build logs** (dependency install, bundle size)
   and **function logs** (startup config errors) for the backend service.
2. Register + login through the UI.

## Known limitations on Vercel (open work)

These are architectural, not configuration, issues:

- **Uploads are ephemeral — unless Blob is configured.** With
  `BLOB_READ_WRITE_TOKEN` set, uploads go to Vercel Blob and survive across
  invocations (fixed). Without it files are written to `/tmp`, which is
  per-instance and short-lived, and an analysis started in a later invocation
  may not find the uploaded file. Note: blob objects are public-but-unguessable
  URLs (random suffix); don't share `Document.file_path` values.
- **Background analysis (`POST /analysis/{id}/run`) doesn't survive.** FastAPI
  `BackgroundTasks` are killed when the serverless invocation ends. The SSE
  pipeline endpoint (`/pipeline/{id}/run-stream`) is the reliable path — it
  keeps the request open (up to the 300s `maxDuration` set in `vercel.json`).
  A killed run no longer hangs forever: an analysis still `PROCESSING` after
  `ANALYSIS_TIMEOUT_SECONDS` (default 600) is reported as `FAILED` so the user
  can retry. A durable job queue is the real fix (ROADMAP 1.3).
- **RAG now works on Vercel (fixed).** Vectors live in the `vector_chunks`
  table via **pgvector**, so they survive cold starts and are shared across
  instances. Requires the `vector` extension in your database — `alembic
  upgrade head` runs `CREATE EXTENSION IF NOT EXISTS vector`, which Neon,
  Supabase, and Vercel Postgres all permit. If embeddings fail (missing
  `GEMINI_API_KEY`, provider error) RAG degrades gracefully and predictions
  run without retrieved context.
- **Shared state now survives across instances (fixed).** The LLM prompt cache,
  the per-model Gemini RPM pacing, and the per-IP auth/upload rate limits live
  in Postgres (`llm_cache`, `rate_limit_counters`), so N instances share one
  cache and enforce one limit instead of each keeping a private copy. All of it
  fails open: if the database is unreachable, requests are allowed through and
  the cache simply misses — shared state is never a reason to 500.
