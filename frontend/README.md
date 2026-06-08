# Exyst Frontend

> Next.js 15 dashboard for the Exyst AI-Powered Exam Intelligence Platform.

## Tech Stack

- **Framework**: Next.js 15 (Pages Router)
- **Language**: TypeScript
- **Styling**: TailwindCSS v4 + Custom premium CSS design system
- **State**: React Context (Auth)
- **HTTP**: Custom typed API client with JWT auto-refresh

## Pages

| Route             | Description                                       |
| ----------------- | ------------------------------------------------- |
| `/`               | Landing page — premium hero section, features, CTA|
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
│   └── globals.css             # Premium design system styling (colors, glassmorphism, animations)
│
├── package.json
├── tsconfig.json
├── next.config.ts
├── postcss.config.mjs
├── .dockerignore               # Optimizes Docker builds by ignoring local node_modules/.next
└── Dockerfile                  # Production-ready Docker container configuration
```

## Design System

The design system in `styles/globals.css` provides:

- **CSS Variables** — custom dark mode palette, accent colors, gradients, borders, shadows
- **Glassmorphism** — `.glass`, `.glass-card` (backdrop-blur + subtle borders)
- **Gradient Text** — `.text-gradient`, `.text-gradient-accent`
- **Buttons** — `.btn-primary` (gradient), `.btn-secondary` (outline)
- **Badges** — `.badge-success`, `.badge-warning`, `.badge-error`, `.badge-info`
- **Stat Cards** — `.stat-card`, `.stat-value`, `.stat-label`
- **Inputs** — `.input-field` with focus glow
- **Animations** — `animate-fade-in`, `animate-scale-in`, `animate-float`, `animate-pulse-glow`
- **Stagger** — `.stagger-1` through `.stagger-5` for cascade effects
- **Charts** — `.bar-chart-bar`, `.confidence-ring` for data visualization

## Getting Started

### Standalone Development (Recommended)

1. **Install Dependencies**:
   ```bash
   # From the frontend directory
   npm install
   ```

2. **Run Dev Server**:
   ```bash
   npm run dev
   ```
   The application will be available at http://localhost:3000.

3. **Build & Lint**:
   ```bash
   # Production build
   npm run build

   # Code linting
   npm run lint
   ```

### Containerized Execution

To run the frontend together with the backend under Docker Compose:
```bash
# From the project root
docker compose up --build
```

## Environment Variables

| Variable              | Default                 | Description          |
| --------------------- | ----------------------- | -------------------- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |
