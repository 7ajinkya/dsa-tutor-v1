# DSA Tutor — frontend (Slice 1C, milestone C1)

Vue 3 + Vite + TypeScript + Pinia + Vue Router scaffold implementing milestone C1 of
`../plans/V1_SLICE_1C_PLAN.md` (v0.2.0, approved). API client (C2), stores (C3) and views
(C4/C5) build on this skeleton — the stub views are intentionally empty.

## Commands

```bash
npm install
npm run dev        # Vite dev server (default http://localhost:5173)
npm run build      # type-check + production build
npm run lint       # eslint (flat config)
npm run preview    # preview the production build
```

## Environment

- `VITE_API_BASE` — base URL of the 1B API (default `http://127.0.0.1:8000`), see `.env.example`.
- Server-side CORS must include the Vite dev origin (default `http://localhost:5173`),
  configurable via `API_CORS_ORIGINS` on the API server.

## Layout

- `src/router/index.ts` — route map (`/`, `/session/:id`, `/progress`, 404)
- `src/api/`, `src/stores/`, `src/composables/` — empty skeletons for C2/C3
- `src/views/` — stub views (content in C4/C5)
