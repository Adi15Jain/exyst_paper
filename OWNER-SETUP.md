# Owner Setup — things only you can do

Everything here is account/dashboard work, not code. Kept in the repo (not in a
chat log) so it doesn't get lost.

Status legend: 🔴 do now · 🟠 before next deploy · 🟢 unlocks pending work

---

## 🔴 1. Rotate the exposed secrets (~10 minutes)

**Why this can't wait:** the repo has been public since 2026-07-06, and
`backend/.env` is in 11 historical commits. These values are readable by anyone
with `git log -p`, and GitHub is constantly scraped by bots that pattern-match
exactly these key formats. They are not *at risk* of exposure — they *are*
exposed. Rotating is the only thing that makes them harmless. Deleting the file
in a later commit did nothing: git keeps the history.

Exposed values:

| Secret | Value in history | Still live? |
| --- | --- | --- |
| Neon Postgres password | `npg_WoFR2t0fpjir` (user `neondb_owner`) | **Yes — matches current `DATABASE_URL`** |
| Groq API keys | `gsk_1fF4SM…`, `gsk_IoNXqn…` | Probably (app no longer uses Groq) |
| Hugging Face token | `hf_onNRfk…` | Probably (app no longer uses HF) |

### 1a. Neon (the urgent one — it's your production database)

1. https://console.neon.tech → your project → **Roles** (left sidebar).
2. Find `neondb_owner` → **⋯** → **Reset password** → copy the new one.
3. **Branches → main → Connection string** → copy the full new URL.
4. Paste it into `backend/.env` as `DATABASE_URL=…`.
5. Paste it into Vercel → Project → **Settings → Environment Variables** →
   edit `DATABASE_URL` → **Save**, then **redeploy** (env changes don't apply
   to existing deployments).

> Use the **direct** (non-pooler) connection string when running Alembic; the
> pooled one is fine for the app.

### 1b. Groq — revoke

https://console.groq.com/keys → delete both keys. The app doesn't use Groq
anymore (it's on Gemini), so nothing breaks.

### 1c. Hugging Face — revoke

https://huggingface.co/settings/tokens → revoke the token. Also unused now.

### 1d. (Optional, after rotating) purge `.env` from git history

Rotation already defuses the leak; this just cleans up. Requires a force-push,
which rewrites history.

```bash
brew install git-filter-repo          # not currently installed
git filter-repo --path backend/.env --invert-paths
git push --force --all
```

---

## 🟠 2. Before the next deploy

Do these in order or hosted login/RAG/uploads will break.

### 2a. Run the pending database migrations

Four are outstanding: `token_version` (revocable sessions), `vector_chunks`
(pgvector RAG) plus the `CREATE EXTENSION vector` it needs, and `llm_cache` +
`rate_limit_counters` (shared cache / rate limits). Neon permits the extension.

```bash
cd backend
source ../.venv/bin/activate   # `alembic` lives in the venv, not on your PATH
alembic upgrade head         # reads DATABASE_URL from backend/.env
```

**Put the new Neon URL in `backend/.env` first**, rather than pasting it on the
command line — a connection string on the CLI ends up in your shell history.

Notes:
- You do **not** need `psycopg2`. Alembic runs on asyncpg, the same driver as
  the app. (An earlier version of these docs said otherwise — that was wrong.)
- Both the pooled (`-pooler`) and direct URLs work.
- If your database already has tables (it was first created by the old
  `DEBUG=true` bootstrap), that's fine: the migrations are idempotent and will
  adopt it, add only what's missing, and leave existing rows alone.

### 2b. Create a Vercel Blob store

Vercel → your project → **Storage → Create Database → Blob**. This injects
`BLOB_READ_WRITE_TOKEN` automatically. Without it, uploads land on `/tmp` and
can vanish before the analysis reads them.

### 2c. Set / confirm these environment variables in Vercel

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | the **new** Neon URL from step 1a |
| `JWT_SECRET_KEY` | generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey — now powers **embeddings** too, so RAG silently disables without it |
| `APP_BASE_URL` | your public frontend URL, e.g. `https://exyst.vercel.app`. **Defaults to `localhost:3000`, which would email unusable password-reset links.** |
| `BLOB_READ_WRITE_TOKEN` | auto-set by step 2b |

### 2d. Verify

1. `https://<your-app>/_backend/api/v1/health` → must return 200.
2. Register + log in through the UI.
3. Upload a PDF and confirm the prediction completes.

---

## 🟢 3. Accounts that unlock pending work

Create these when you want the feature; hand me the env var and I'll wire the
code. None are required for the app to run today.

### Resend — makes password-reset emails actually send (feature is already built)

Right now the reset flow works but the link is only **logged**, not emailed.

1. https://resend.com → sign up.
2. **Domains → Add Domain** → add the DNS records it gives you.
   (To just test: skip this and use their shared `onboarding@resend.dev` sender.)
3. **API Keys → Create API Key** → copy.
4. Give me: **`RESEND_API_KEY`**. Also set `EMAIL_FROM` (e.g.
   `Exyst <noreply@yourdomain.com>`).

### Upstash QStash — durable job queue (ROADMAP 1.3)

Fixes the worst remaining failure mode: analyses die when a serverless
invocation is killed. (There's an interim guard, but this is the real fix.)

1. https://console.upstash.com → **QStash**.
2. Copy the token and the two signing keys.
3. Give me: **`QSTASH_TOKEN`**, **`QSTASH_CURRENT_SIGNING_KEY`**,
   **`QSTASH_NEXT_SIGNING_KEY`**.

### ~~Upstash Redis — shared cache + rate limits~~ ✅ Done, no account needed

**Nothing to do.** The prompt cache, the per-model Gemini RPM pacing, and the
per-IP rate limits now live in the Postgres you already have (`llm_cache` and
`rate_limit_counters`, added by migration `0004`), shared across all instances.

Redis was the obvious choice but the wrong one here: Upstash's free tier allows
only one database and yours is in use by another project, and the latency Redis
buys is irrelevant when a cache hit's job is to skip a 5–90 second Gemini call.
A ~20 ms Postgres query does that just as well, with no extra service, no
credentials, and no bill.

### Sentry — error tracking (ROADMAP 1.6)

1. https://sentry.io → new project → pick **Python (FastAPI)**; add a second
   for **Next.js** if you want frontend errors too.
2. Copy the DSN from **Settings → Client Keys (DSN)**.
3. Give me: **`SENTRY_DSN`** (and the frontend DSN if separate).

---

## Quick reference — where each variable is needed

| Variable | Local `.env` | Vercel | Needed for |
| --- | --- | --- | --- |
| `DATABASE_URL` | ✅ | ✅ | everything |
| `JWT_SECRET_KEY` | ✅ | ✅ | auth (app refuses to boot on the placeholder) |
| `GEMINI_API_KEY` | ✅ | ✅ | analysis, prediction, embeddings/RAG |
| `BLOB_READ_WRITE_TOKEN` | — | ✅ | durable uploads on serverless |
| `APP_BASE_URL` | ✅ | ✅ | links in emails |
| `RESEND_API_KEY` | optional | ✅ | actually sending reset emails |
| `QSTASH_*` / `SENTRY_DSN` | optional | ✅ | pending roadmap items (durable queue, error tracking) |
