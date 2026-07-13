# 🗺 Exyst — Platform Improvement Plan & Roadmap

> A comprehensive, prioritized plan for evolving Exyst from a working prototype into a
> complete, production-grade exam-intelligence platform. Based on a full audit of the
> backend, frontend, AI pipeline, deployment setup, and security posture (July 2026).

**How to read this document:** items are grouped into phases ordered by dependency and
impact. Each item carries an **Impact** rating (🔴 critical / 🟠 high / 🟡 medium / 🟢 nice-to-have)
and an **Effort** estimate (S = hours, M = days, L = a week+). Within a phase, do the
🔴/S items first.

---

## Where the platform stands today

**What works well:** a clean, layered, fully-async FastAPI backend; an LLM-frugal
pipeline (3–5 Gemini calls per run) with model fallback and rate-limit awareness;
hybrid RAG grounding (vector retrieval + verbatim past papers as format template);
transparent multi-factor confidence scoring; SSE progress streaming with a polling
fallback; a visually polished dark-glassmorphism frontend with good loading/error/empty
states; ownership correctly scoped by `user_id` on every query.

**The honest gaps, in one paragraph:** the product is a *single-shot pipeline demo* —
upload one PDF, get one prediction. There is no account lifecycle (no password reset,
email verification, profile editing, or token revocation), no document management
(no delete/rename), no way to act on a prediction (no export, no study tools), and no
course-level organization. Operationally, uploads sit on ephemeral `/tmp`, background
jobs die with the serverless invocation, RAG is disabled on Vercel entirely, and
rate-limiting/cache state is per-process. The frontend is one giant page per route with
inline styles, no shared component library, no mobile support, and no data-fetching
layer. Several security items from the audit remain open.

---

## Phase 0 — Security & hygiene (do first, mostly small)

These unblock everything else and remove standing risk.

| # | Item | Impact | Effort | Status |
|---|------|--------|--------|--------|
| 0.1 | **Rotate leaked secrets** (Neon password, Groq keys, HF token exposed in git history of the now-public repo), then purge `.env` from history with `git filter-repo`/BFG. **Step-by-step: [OWNER-SETUP.md](OWNER-SETUP.md)** | 🔴 | S | ⏳ owner-only, **still open** |
| 0.2 | **Revocable refresh tokens** — `users.token_version` + `ver` claim in refresh JWTs; `POST /auth/logout` bumps the version, revoking every outstanding refresh token (migration `0002`) | 🔴 | M | ✅ 2026-07-13 |
| 0.3 | **Move refresh token out of `localStorage`** into an `httpOnly Secure SameSite=Lax` cookie; access token kept in memory only, session restored via cookie refresh on page load | 🔴 | M | ✅ 2026-07-13 |
| 0.4 | **Rate-limit expensive endpoints** — per-IP limits on upload (20/10 min), analysis run, prediction generate, and SSE pipeline (10/10 min each) | 🟠 | S | ✅ 2026-07-13 |
| 0.5 | **Delete legacy code** — `backend/agents/`, `backend/utils/`, `backend/outputs/predicted_*.json`, stray STAR docs removed (`backend/main.py` kept — it is the Vercel entrypoint) | 🟡 | S | ✅ 2026-07-13 |
| 0.6 | **Cap `per_page`** on list endpoints (now `le=100`) | 🟡 | S | ✅ 2026-07-13 |
| 0.7 | **Clean `MODEL_LIMITS`** — nonexistent models removed; fallback is `gemini-2.5-flash → flash-lite → gemma-3-27b-it` | 🟡 | S | ✅ 2026-07-13 |

---

## Phase 1 — Production-grade infrastructure

The three architectural fixes that make the hosted (Vercel) product actually reliable,
plus the state that must move out of process memory.

| # | Item | Impact | Effort | Status |
|---|------|--------|--------|--------|
| 1.0 | **Semantic topic-coverage scoring** *(new — regression from the pgvector move)*. The evaluator's confidence score now uses deterministic substring matching for topic coverage. Its old "semantic" path went through ChromaDB, so it only ever ran locally (never on Vercel) and re-embedded every syllabus topic per evaluation. Re-add it properly on pgvector: embed predicted + syllabus topics once, score coverage by cosine similarity | 🟡 | S | ⏳ open |
| 1.1 | **Object storage for uploads** — storage layer added (`app/services/storage.py`): local disk by default, Vercel Blob when `BLOB_READ_WRITE_TOKEN` is set; reads/deletes dispatch on the stored path so old rows keep working. Owner must create a Blob store in Vercel (see DEPLOYMENT.md) | 🔴 | M | ✅ 2026-07-13 |
| 1.2 | **Replace ChromaDB with pgvector** — `vector_chunks` table (migration `0003`) with Gemini `text-embedding-004` embeddings, HNSW cosine index. RAG now works on Vercel, survives deploys, is shared across instances, and **retrieval is filtered by `user_id`** (closing the cross-user leak) with true cosine similarity (was `1 - L2`). chromadb dropped entirely | 🔴 | L | ✅ 2026-07-13 |
| 1.3 | **Durable job queue** — replace `BackgroundTasks` with a real queue (Upstash QStash / Inngest fit Vercel; Celery+Redis if self-hosted). Analyses stuck in `PROCESSING` forever after a killed invocation is the worst current failure mode | 🔴 | L | ⏳ **interim done**: stale runs (>`ANALYSIS_TIMEOUT_SECONDS`, default 10 min) are now reaped as FAILED so the UI stops polling. Queue itself still open — needs a provider choice |
| 1.4 | **Shared cache & rate-limit state** — moved out of process memory into **Postgres** (`llm_cache` + `rate_limit_counters`, migration `0004`): prompt cache, per-model Gemini RPM pacing, and per-IP rate limits are now shared across instances. Deliberately *not* Redis: no extra service or credentials, and a ~20 ms query is free next to the 5–90 s LLM call a cache hit avoids. Fails open if the DB hiccups | 🟠 | M | ✅ 2026-07-13 |
| 1.5 | **Dedup by file hash** — re-uploading an identical PDF that already has a COMPLETED analysis returns the existing document (zero LLM cost). Scoped to the same user on purpose; cross-user/global reuse — the *really* big cost lever — needs the shared-corpus design in 3a first | 🟠 | M | ✅ 2026-07-13 |
| 1.6 | **Observability** — Sentry (backend + frontend) for errors; a simple LLM-usage table (model, tokens, latency, cost per call) so quota burn is visible; uptime check on `/health` | 🟠 | M | ⏳ needs a Sentry account/DSN |
| 1.7 | **Populate `prompt_metadata`** and version prompts properly (the column exists but is never written; `prompt_version` is hardcoded `"v3.0"`) — prerequisite for A/B-testing prompt changes | 🟡 | S |

---

## Phase 2 — Complete the core product

Features users expect from any account-based product, plus closing the loop on the
document lifecycle. Almost all are 🟠 because their absence is felt immediately.

### 2a. Account lifecycle

| # | Item | Impact | Effort | Status |
|---|------|--------|--------|--------|
| 2.1 | **Password reset** — `/auth/forgot-password` + `/auth/reset-password`, single-use tokens (bound to the current password hash, so a used link dies), enumeration-safe, revokes all sessions. Sends via Resend; **logs the link instead when `RESEND_API_KEY` is unset**, so it works in dev today | 🟠 | M | ✅ 2026-07-13 — *needs `RESEND_API_KEY` to actually mail* |
| 2.2 | **Email verification** on signup (uses the same Resend sender) | 🟠 | M | ⏳ open |
| 2.3 | **Profile/settings page** — `/settings`: edit name, change password (revokes other sessions), delete account (cascades documents/analyses/predictions/vectors + removes stored files) | 🟠 | M | ✅ 2026-07-13 |
| 2.4 | **OAuth sign-in** (Google) — students overwhelmingly prefer it; removes password-reset support burden | 🟡 | M | ⏳ open |

### 2b. Document & prediction lifecycle

| # | Item | Impact | Effort | Status |
|---|------|--------|--------|--------|
| 2.5 | **Delete & rename documents** — `DELETE /documents/{id}` (cascades analyses/predictions + removes stored file) and `PATCH /documents/{id}` rename; both wired into the documents list UI | 🟠 | S | ✅ 2026-07-13 |
| 2.6 | **Export predicted paper as PDF** — "⬇ Download PDF" prints the paper via the browser's native Save-as-PDF (a `@media print` stylesheet strips the app chrome and flattens the dark theme to black-on-white), plus "📋 Copy text" for pasting into Word/Docs. No new dependency, no server-side renderer | 🟠 | M | ✅ 2026-07-13 |
| 2.7 | **Separate syllabus / past-paper upload streams** — optional two-slot upload removes the page-classification LLM call and its ambiguity entirely (already on the old roadmap) | 🟠 | M |
| 2.8 | **Multiple uploads per course** (see Courses, #3.1) — add papers over time to one corpus instead of re-uploading a combined PDF | 🟠 | L |
| 2.9 | **OCR fallback** for scanned/image-only PDFs — Gemini is multimodal, so pages with no extractable text can be sent as images to the same model; today they produce empty analyses | 🟠 | M |
| 2.10 | **Prediction history** — keep and list all generated predictions per document (schema already supports it; UI shows only the latest) with a diff/compare view | 🟡 | M |

---

## Phase 3 — New capabilities (what to *add* to the system)

This is where Exyst stops being "a prediction generator" and becomes a study platform.
Ordered by how directly each builds on what already exists.

### 3a. Courses as the organizing unit ✅ 2026-07-13

The structural change everything else in Phase 3 sits on. A `Course`
(`user_id, name, code, university, semester`, migration `0005`) is the unit
papers are filed under.

**Done:**
- `Course` CRUD (`/api/v1/courses`), a `/courses` page, a course picker on
  upload, and a course filter on the documents list.
- `documents.course_id` and `vector_chunks.course_id` (both nullable — existing
  and deliberately-unfiled papers keep working).
- **RAG retrieval is now course-scoped.** A prediction for a paper in a course
  is grounded on that course's *entire corpus* — every paper ever filed under
  it. The corpus grows with each upload, which is the whole point.
- **Fixed a real relevance bug in the process:** retrieval was scoped to the
  whole *user*, so a Physics prediction could be grounded on questions from
  their Chemistry papers. Unfiled documents now scope to themselves.
- Deleting a course does **not** delete its papers — they're unfiled
  (`ON DELETE SET NULL`). Losing a semester of uploads to a tidy-up would be
  unforgivable.

**Still open (the follow-ons this unlocks):**
- Cross-paper trend analysis over the course corpus (today's
  first-half/second-half heuristic still only sees one upload's papers).
- Dashboard reorganized around courses.
- Shared/global corpus per course across users (see 1.5 — the big cost lever).

### 3b. Study tools on top of the analysis (the retention features)

Each of these reuses the already-extracted topics/questions — marginal LLM cost is low:

| Feature | What it is | Impact | Effort |
|---------|-----------|--------|--------|
| **Answer/model-solution generation** | "Show answer" on any predicted question, grounded in syllabus topics | 🟠 | M |
| **Topic study guide** | Per-topic explainer generated from syllabus + the historical questions that hit that topic | 🟠 | M |
| **Practice/quiz mode** | Turn predicted + historical questions into an interactive self-test with self-grading (LLM evaluates the student's typed answer) | 🟠 | L |
| **Flashcards** | Auto-generated from topics; spaced-repetition scheduling (SM-2 is a weekend of code) | 🟡 | M |
| **Study planner** | Given exam date + topic frequencies, produce a prioritized day-by-day plan ("these 6 topics cover 80% of historical marks") | 🟡 | M |
| **Chat with your documents** | RAG chat over the course corpus ("what usually comes from unit 3?") — the retrieval layer already exists | 🟡 | L |
| **Question bank browser** | Searchable, filterable view of every extracted historical question (topic/marks/session/type) — the data is already in `analyses.question_papers` | 🟡 | M |

### 3c. Prediction quality improvements

| Item | Why | Impact | Effort |
|------|-----|--------|--------|
| **Difficulty estimation** per question (LLM-tagged, shown as a badge) | Adds a dimension students care about | 🟡 | S |
| **"Why this question?" explanations** | Surface the evidence (frequency, trend, similar past questions) behind each predicted question — turns the confidence score into something inspectable and trustworthy | 🟠 | M |
| **Generalize paper splitting** | Session/paper detection regexes are hardcoded to one university's header format; make splitting LLM-assisted or configurable so other universities work | 🟠 | M |
| **Chunking instead of truncation** | Text is silently truncated at 4000–6000 chars everywhere; large syllabi/papers lose content. Chunk + merge instead | 🟡 | M |
| **Backtesting mode** | Hold out the most recent paper, predict it from the older ones, score the overlap — an *actual accuracy metric* for the marketing page and for prompt iteration (pairs with #1.7) | 🟠 | M |
| **Cross-provider failover** | Add one non-Gemini provider (e.g. an OpenAI-compatible endpoint) behind the existing `LLMClient` abstraction | 🟡 | M |

### 3d. Growth & platform (later)

- **Shareable prediction links** (public read-only URL per prediction) — the organic growth loop; students share with classmates. 🟠/M
- **Course marketplace / community corpus** — opt-in sharing of anonymized course corpora so the second student of a course gets instant results. Big win, needs moderation thought. 🟡/L
- **Institution/org accounts** — roles, shared workspaces for coaching centers. Only when there's pull. 🟢/L
- **Billing** (Stripe: free tier with N predictions/month, paid unlimited + priority queue) — gate on LLM cost telemetry from #1.6. 🟡/L
- **i18n** — Hindi first, given the current user base. 🟢/M

---

## Phase 4 — Frontend engineering (parallel track)

The frontend's visual design is good; its structure won't survive more features.
Do these incrementally alongside Phases 1–3, not as a big-bang rewrite.

| # | Item | Impact | Effort | Status |
|---|------|--------|--------|--------|
| 4.1 | **Mobile responsiveness** — sidebar now slides in behind a hamburger below 900px (with overlay + auto-close on navigation), content padding adapts, the analytics `1fr 1fr` grid stacks (`.grid-2`), fake "Connected" badge removed | 🔴 | M | ✅ 2026-07-13 |
| 4.2 | **Extract a shared component library** — `components/ui/`: `Banner` (replaced 10 hand-rolled copies of the same red box), `Spinner`, `EmptyState`. Still local per-page: StatCard/BigStatCard/MiniStat (3 variants), ConfidenceRing, BarChart, and the auth-page shell | 🟠 | M | 🟡 partial |
| 4.3 | **Adopt TanStack Query** for data fetching — hand-rolled `fetch`+`useEffect` per page means no caching, retry, or background refetch; every navigation refetches everything | 🟠 | M |
| 4.4 | **Actually use Tailwind** (it's installed) instead of inline `style={{}}` objects — inline styles are why there are no responsive variants; migrate page-by-page | 🟠 | L |
| 4.5 | **Accessibility pass** — real `<button>`/`<a>` for clickable rows, `aria-label`s replacing bare emoji icons, `role="tab"`+`aria-selected` on tabs, focus-visible styles. *(Fake "● Connected" badge already removed; new `ui/` primitives carry correct `role`/`aria`.)* | 🟠 | M |
| 4.6 | **Type the API payloads** — all 15 `any`s gone; `PredictedPaper`, `ConfidenceReport`, `AnalysisResult` etc. now mirror the backend Pydantic schemas. (Typing them surfaced two latent null-safety bugs the `any` was hiding.) Generating from OpenAPI (5.4) would remove the hand-sync burden | 🟡 | M | ✅ 2026-07-13 |
| 4.7 | **Surface partial-failure states** — dashboard/detail `.catch(() => null)` silently renders "—"; show which panel failed and offer retry per-panel | 🟡 | S |
| 4.8 | **Icon library** (lucide-react) to replace emoji-as-icons; **toast system** for action feedback | 🟡 | S |
| 4.9 | **Light theme** + `prefers-color-scheme` (tokens are already centralized in `:root`, so this is mostly mechanical) | 🟢 | M |
| 4.10 | **Route protection via middleware/HOC** instead of copy-pasted `useEffect` redirects in every page | 🟡 | S |

---

## Phase 5 — Quality & developer experience

| # | Item | Impact | Effort |
|---|------|--------|--------|
| 5.1 | **E2E smoke test** (Playwright): register → upload fixture PDF (mocked LLM) → see prediction. CI currently can't catch integration breaks like the Vercel boot failure | 🟠 | M |
| 5.2 | **Prediction-quality regression suite** — golden fixture PDFs with expected topic sets; run on prompt changes (pairs with backtesting #3c) | 🟠 | M |
| 5.3 | **Frontend component/page tests** — only `lib/api.ts` is tested today; add `@testing-library/react` and cover the critical flows | 🟡 | M |
| 5.4 | **OpenAPI-generated TS client** — deletes the hand-maintained `lib/api.ts` type drift problem permanently | 🟡 | M |
| 5.5 | **Preview-deploy checks** — a CI step that hits `/health` on the Vercel preview URL before merge | 🟡 | S |

---

## Suggested sequencing (90-day view)

```
Weeks 1–2   Phase 0 complete (secrets, revocable tokens, cookie auth, rate limits, cleanup)
Weeks 2–4   Blob storage (1.1) + document delete (2.5) + mobile responsiveness (4.1)
Weeks 4–7   pgvector RAG (1.2) + durable jobs (1.3) + hash dedup (1.5) + observability (1.6)
Weeks 7–10  Courses (3a) — the big product bet — with component extraction (4.2/4.3) alongside
Weeks 10–13 Account lifecycle (2.1–2.3), PDF export (2.6), OCR (2.9),
            then the first study tool (answers or study planner) + shareable links
```

**Guiding principle for what to build next:** every analysis already extracts far more
value (topics, frequencies, trends, per-question metadata) than the UI exposes. Prefer
features that *re-use existing extractions* (study guides, question bank, planner,
"why this question?") over features requiring new pipeline stages — they're cheaper,
faster to ship, and deepen the moat of the data you already have.

## Success metrics to instrument from day one

- **Activation:** % of signups that complete a first prediction.
- **Prediction accuracy:** backtest overlap score (#3c) — the number that sells the product.
- **Retention:** weekly returning users per course (study tools are what move this).
- **Unit cost:** LLM spend per prediction (should *fall* as hash-dedup and per-course
  indexes land).
- **Reliability:** % of pipeline runs completing without manual retry.

---

## Cleanup log — 2026-07-13

A dead-code + hygiene sweep. Three of the "dead code" findings were live bugs:

- **`typical_format` was computed and thrown away.** The pattern analyzer derived
  the paper's typical layout, the prediction service passed it to the predictor —
  and the prompt template had no placeholder for it, so the model never saw it.
  Now wired into the prompt. *(Expect slightly more format-faithful predictions.)*
- **`AnalysisResponse.question_papers` declared a shape the data never had**
  (`academic_session`/`total_questions`/… vs the stored `{session, text}`), so every
  paper serialized to all-defaults and the real content was silently dropped from
  the API response. Schema now matches what the pipeline writes (`QuestionPaperExcerpt`).
- **`marks_distribution_score` was computed, stored, and then omitted** from
  `/analytics/confidence-breakdown` — the UI only ever saw 3 of the 4 factors.

Removed: `DocumentProcessor.extract_metadata` + its 6 helpers (no caller — metadata
comes from the LLM pattern analyzer), `RAGStore.delete_document_chunks` (FK cascade
does it), the `app/schemas/__init__` re-export facade, unused `DocumentError`/`AIError`
base classes, `Settings.database_url_sync` + `OUTPUTS_DIR`, unused params
(`run_analysis_background(user_id)` — kept, still used for lookups; `_score_marks_distribution(frequency_data)`),
126 lines of dead CSS (unused classes, orphaned `@keyframes`, unreferenced custom
properties), the `localStorage` token-migration shim, and the stale Pyrefly docs
(the tool was dropped in an earlier commit but both READMEs still configured it).

Fixed: the frontend **`npm run lint` never linted anything** — it ran `next lint`
with no ESLint config or dependency, so it hung on an interactive setup prompt and
the CI "Lint" step was a no-op. ESLint is now installed and configured, CI lints
`tests/` as well as `app/`, and all 15 `any`s it found are typed.
