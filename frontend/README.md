# osapiens Deforestation Monitor (Makeathon 2026)

Hackathon-ready frontend for the **osapiens** challenge: **multimodal satellite monitoring** for deforestation signals (Sentinel-1, Sentinel-2, AEF / foundation embeddings, weak labels) with **EUDR-oriented risk** and a **human validation** workflow.

Stack: **React**, **TypeScript**, **Vite**, **Tailwind CSS**, **lucide-react**, **recharts**. All data is **mock JSON** — no backend.

## Run

```bash
cd frontend
npm install
npm run dev
```

Open the URL shown (default `http://localhost:5173`).

### Connect to the trained model (backend)

1. In another terminal, start the API (see **`../backend/README.md`**):

   ```bash
   cd ../backend
   pip install -r ../model-training/requirements.txt -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```

2. Keep the Vite dev server running. It **proxies** `/api` → `http://127.0.0.1:8000`, so the UI loads **`GET /api/plots`** and switches from mock tiles to **real test tiles** (e.g. `48PWA_0_6`) when the API is up.

3. Top bar shows **Model API** (green) vs **Mock data** if the backend is unreachable.

Optional: set `VITE_API_BASE_URL` if the API is not on localhost during dev.

```bash
npm run build   # typecheck + production bundle
npm run preview
```

## Deploy to Vercel

This folder is a self-contained Vite app and ships with a `vercel.json` so it
can be deployed as-is.

### One-time setup (Vercel dashboard)

1. **Import the repo** on [vercel.com/new](https://vercel.com/new).
2. Set **Root Directory** = `frontend` (important — the repo contains a
   separate Python backend).
3. Framework preset should auto-detect as **Vite**. Leave the defaults
   (install / build / output) — they match `vercel.json`.
4. Under **Settings → Environment Variables**, add (for *Production* and
   *Preview*):

   | Name | Value (example) |
   |------|-----------------|
   | `VITE_API_BASE_URL` | `https://your-backend-host.example.com` |

   See `.env.production.example` for the authoritative list.

### Deploy from the CLI (optional)

```bash
cd frontend
npm i -g vercel
vercel link          # first time only, attaches this dir to a Vercel project
vercel --prod        # production deploy
```

### Backend requirements

The frontend calls `${VITE_API_BASE_URL}/api/*` directly from the browser, so
the **backend must allow the Vercel origin**. On the backend host set:

```bash
# e.g. your production domain, plus wildcard preview URLs are handled via regex
export CORS_ORIGINS="https://your-app.vercel.app"
# or allow every *.vercel.app preview:
export CORS_ORIGIN_REGEX="https://.*\.vercel\.app"
```

The dev-only `/api` proxy in `vite.config.ts` is **not** used in production
builds — Vercel serves static assets and the browser talks to
`VITE_API_BASE_URL` over HTTPS.

## Layout

- **Left sidebar** — Overview, Land Plots, Time Series, Predictions, Risk Analysis, Validation  
- **Top bar** — Title `osapiens Deforestation Monitor`, search, tile selector, monitoring status (click to toggle), profile  
- **Main area** — page content  
- **Right panel (xl+)** — selected tile summary, risk breakdown, monitoring feed shortcuts  

Default route **Overview** is tuned for demo: large **map-style plot panel**, **risk summary**, **temporal preview**, **activity feed**, and **top detections**.

## Key files

| Path | Role |
|------|------|
| `src/data/mock.ts` | 12 land plots, overlays, time series generator, activity feed, validation queue metadata |
| `src/types/index.ts` | `LandPlot`, `TimeSeriesPoint`, `ActivityItem`, layers, nav keys |
| `src/components/PlotMapPanel.tsx` | Synthetic satellite workspace + overlay legend |
| `src/components/TimeSeriesChart.tsx` | Recharts multimodal timeline + change window + event markers |
| `src/components/RiskBreakdownPanel.tsx` | Enterprise-style risk breakdown + EUDR tier |
| `src/components/ValidationPanel.tsx` | HITL actions with mock feedback |
| `src/App.tsx` | Navigation, plot/region/layer state, insights panel |

## Challenge assets (repo root)

Reference notebooks and scripts (`challenge.ipynb`, `download_data.py`, `submission_utils.py`, description markdown) inform the **domain language** used in the UI; the frontend does not load those files at runtime.
