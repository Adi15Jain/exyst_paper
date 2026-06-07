# Exyst Frontend

> Next.js 15 dashboard for the Exyst AI-Powered Exam Intelligence Platform.

## Tech Stack

- **Framework**: Next.js 15 (Pages Router)
- **Language**: TypeScript
- **Styling**: TailwindCSS v4 + custom CSS design system
- **State**: React Context (Auth)
- **HTTP**: Custom typed API client with JWT auto-refresh

## Pages

| Route             | Description                                       |
| ----------------- | ------------------------------------------------- |
| `/`               | Landing page — hero section, features, CTA        |
| `/login`          | Login / Register — glassmorphism card, validation |
| `/dashboard`      | Overview — stat cards, quick actions, recent docs |
| `/upload`         | Upload — drag & drop, pipeline progress stages    |
| `/documents`      | Document list — paginated, status badges          |
| `/documents/[id]` | Document detail — predicted paper, analysis tabs  |
| `/analytics`      | Analytics — aggregate stats, confidence breakdown |

## Project Structure

```
frontend/
├── pages/                      # Route pages
│   ├── _app.tsx                # App wrapper (AuthProvider, fonts)
│   ├── _document.tsx           # HTML document
│   ├── index.tsx               # Landing page
│   ├── login.tsx               # Auth page
│   ├── dashboard.tsx           # Dashboard
│   ├── upload.tsx              # Upload + pipeline flow
│   ├── analytics.tsx           # Aggregate analytics
│   └── documents/
│       ├── index.tsx           # Document list
│       └── [id].tsx            # Document detail (tabs)
│
├── components/
│   ├── layout/
│   │   ├── AppLayout.tsx       # Sidebar + top bar (auth pages)
│   │   └── MainCard.tsx        # Content card wrapper
│   └── ui/                     # Shared UI components
│       ├── AnimatedBackground.tsx
│       ├── FileUpload.tsx
│       ├── Header.tsx
│       ├── Footer.tsx
│       ├── ErrorMessage.tsx
│       ├── SubmitButton.tsx
│       └── QuestionPaper.tsx
│
├── lib/
│   ├── api.ts                  # Typed API client
│   │                           #   - JWT token management
│   │                           #   - Automatic 401 → refresh
│   │                           #   - Typed interfaces for all endpoints
│   └── auth-context.tsx        # React Context for auth state
│
├── types/
│   └── prediction.ts           # Shared TypeScript interfaces
│
├── styles/
│   └── globals.css             # Design system
│                               #   - CSS variables (colors, gradients)
│                               #   - Glassmorphism utilities
│                               #   - Animation keyframes
│                               #   - Component styles (buttons, badges, cards)
│
├── package.json
├── tsconfig.json
├── next.config.ts
├── postcss.config.mjs
└── Dockerfile
```

## Design System

The design system in `styles/globals.css` provides:

- **CSS Variables** — dark mode palette, accent colors, gradients, borders, shadows
- **Glassmorphism** — `.glass`, `.glass-card` (backdrop-blur + subtle borders)
- **Gradient Text** — `.text-gradient`, `.text-gradient-accent`
- **Buttons** — `.btn-primary` (gradient), `.btn-secondary` (outline)
- **Badges** — `.badge-success`, `.badge-warning`, `.badge-error`, `.badge-info`
- **Stat Cards** — `.stat-card`, `.stat-value`, `.stat-label`
- **Inputs** — `.input-field` with focus glow
- **Animations** — `animate-fade-in`, `animate-scale-in`, `animate-float`, `animate-pulse-glow`
- **Stagger** — `.stagger-1` through `.stagger-5` for cascade effects
- **Charts** — `.bar-chart-bar`, `.confidence-ring` for data visualization

## API Client (`lib/api.ts`)

Centralized HTTP client that handles:

- **Token Management** — stores JWT access + refresh tokens in localStorage
- **Auto-Refresh** — on 401, transparently refreshes and retries the request
- **Typed Responses** — all endpoints return typed TypeScript interfaces
- **FormData** — handles file uploads with correct Content-Type

```typescript
import { auth, documents, analysis, predictions, analytics } from "@/lib/api";

// Auth
await auth.login("user@example.com", "password");
const user = await auth.me();

// Upload & analyze
const doc = await documents.upload(file);
await analysis.run(doc.id);
const prediction = await predictions.generate(doc.id);

// Analytics
const stats = await analytics.overview();
const topics = await analytics.topicFrequency(doc.id);
```

## Getting Started

### With the full stack (recommended)

```bash
# From the project root
docker compose up --build
# Frontend at http://localhost:3000
```

### Standalone development

```bash
# Install dependencies
npm install

# Run dev server
npm run dev

# Build for production
npm run build

# Lint
npm run lint
```

### Environment Variables

| Variable              | Default                 | Description          |
| --------------------- | ----------------------- | -------------------- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |

## Dependencies

| Package       | Version | Purpose         |
| ------------- | ------- | --------------- |
| `next`        | 15.4    | React framework |
| `react`       | 19.1    | UI library      |
| `typescript`  | ^5      | Type safety     |
| `tailwindcss` | ^4      | Utility CSS     |
