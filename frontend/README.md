# AlphaEarth Explorer — Frontend

React + TypeScript + Vite + Tailwind dashboard for exploring AlphaEarth
Foundations (AEF) embeddings over the Makeathon 2026 deforestation dataset.

The UI is **strict API-only**: every call goes to the URL in
`VITE_API_BASE_URL`. There is no Vite proxy, no localhost fallback, and no
mock data. If the backend isn't reachable the app shows a clear configuration
error instead of pretending data exists.

## Pages

| Page | What you can do |
|------|----------------|
| Overview | Sanity stats + jump-off cards. |
| Embedding Map | PCA-3 false-colour preview of one tile-year, plus per-source label coverage. |
| Channel Explorer | Pick any 3 of 64 AEF bands (or one for grayscale), view per-channel min/max/mean. |
| Low-dim Analysis | PCA-2D + UMAP-2D scatter of labelled pixels across selected tile-years. |
| Classifier Lab | Train SVM or MLP on selected tiles, evaluate on a held-out tile, inspect confusion matrix, prediction overlay, and the top disagreement ("mislabel") regions. |

## Run

```bash
cd frontend
npm install
npm run dev
```

The dev server prints its URL (default `http://localhost:5173`).

### Configure the backend URL

Copy `.env.example` to `.env` and set the URL of the FastAPI backend:

```bash
cp .env.example .env
# .env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Restart the dev server after editing `.env`.

To boot the backend locally:

```bash
cd ../backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Build

```bash
npm run build      # tsc -b + vite build
npm run preview    # serve the build locally
```

The build emits to `dist/` and contains zero references to localhost — the
generated bundle reads `VITE_API_BASE_URL` at build time.

## Deploy

Set `VITE_API_BASE_URL` in your hosting provider (e.g. Vercel project
settings) to a URL that:

1. Serves the FastAPI app.
2. Has the frontend's origin in its `CORS_ORIGINS` env var (or matches the
   default `https://.*\.vercel\.app` regex).

See [`../backend/README.md`](../backend/README.md) for the full list of
backend env vars.
