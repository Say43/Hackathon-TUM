# AlphaEarth Explorer — Backend

FastAPI service that exposes the AlphaEarth Foundations (AEF) embedding
explorer over HTTP. All heavy lifting (rasterio, sklearn, PCA/UMAP, mislabel
detection) lives in the `alphaearth` Python package under
[`../model-training/alphaearth/`](../model-training/alphaearth/); this app is
just a thin adapter so the FastAPI surface and the `run_aef.py` CLI agree on
data layout and caching.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET`  | `/api/health` | Service health + dataset / cache presence. |
| `GET`  | `/api/debug/paths` | Resolved paths + env var diagnostics. |
| `GET`  | `/api/aef/tiles?split=train\|test` | Tiles, years, label sources, bbox. |
| `GET`  | `/api/aef/tiles/{tile}/{year}/summary` | Bbox + per-source label counts. |
| `GET`  | `/api/aef/tiles/{tile}/{year}/stats` | 64-band channel statistics. |
| `GET`  | `/api/aef/tiles/{tile}/{year}/preview.png` | PCA-3 false-colour PNG. |
| `GET`  | `/api/aef/tiles/{tile}/{year}/bands.png?r=&g=&b=&mode=` | RGB / gray composite. |
| `GET`  | `/api/aef/scatter?method=pca\|umap&tiles=&label_source=` | Scatter points. |
| `POST` | `/api/aef/classify` | Train SVM/MLP, evaluate on test tile. |
| `GET`  | `/api/aef/classify/{modelId}` | Cached run metrics. |
| `GET`  | `/api/aef/classify/{modelId}/prediction.png` | Binary prediction overlay. |
| `GET`  | `/api/aef/classify/{modelId}/probability.png` | Probability heatmap. |
| `GET`  | `/api/aef/classify/{modelId}/mislabels?top=` | Top disagreement regions. |

The legacy `/api/tiles`, `/api/plots`, `/api/tiles/{id}/timeseries` endpoints
have been **removed** — the project pivoted from raw Sentinel timeseries to
AEF embeddings.

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r ../model-training/requirements.txt
pip install -r requirements.txt
```

The `model-training/requirements.txt` already pins `umap-learn`, `scipy` and
`Pillow`, which the explorer needs. If you have an existing env that was set
up for the old solution, run the install line again to pick those up.

## Run

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open <http://127.0.0.1:8000/docs> for the OpenAPI / Swagger UI.

On startup, the app prints a banner showing exactly where it resolved the
dataset and the cache. Look for lines like:

```
==> resolved      : /…/makeathon-challenge
aefDir            : /…/makeathon-challenge/aef-embeddings  exists=True
labelsDir         : /…/makeathon-challenge/labels/train    exists=True
cacheDir          : /…/model-training/runs/aef              exists=True
```

If `exists=False` for any of these, hit `/api/debug/paths` for the same data
as JSON (handy on remote servers).

## Environment variables

Copy `backend/.env.example` to `backend/.env` and edit. `python-dotenv`
loads it automatically on import.

| Variable | Purpose | Default |
|----------|---------|---------|
| `MAKEATHON_DATA_DIR` (or `DATA_DIR`) | Dataset root with `aef-embeddings/` + `labels/`. Relative paths are anchored to the **repo root**, not `cwd`. | first existing of: `model-training/data/abdul-testrun/makeathon-challenge`, `model-training/data/makeathon-challenge`, `data/makeathon-challenge` |
| `AEF_CACHE_DIR` | Where PCA previews, UMAP JSON and classifier joblibs are cached. Relative paths are anchored to the repo root. | `model-training/runs/aef/` |
| `CORS_ORIGINS` | Comma-separated additional allowed origins. `*` allows all (drops credentials). | localhost:5173/5174/4173 + Vercel preview regex |
| `CORS_ORIGIN_REGEX` | Override the regex used for credential-less wildcard origins. | `https://.*\.vercel\.app` |

## Caching

Every PCA preview / UMAP scatter / classifier run is cached on disk under
`AEF_CACHE_DIR/`:

```
runs/aef/
├── previews/{tile}_{year}_{split}_max1024.png
├── bands/{tile}_{year}_{split}_{mode}_{r-g-b}_max1024.png
├── scatter/{method}_{labelSource}_{requestHash}.json
└── runs/{modelId}/
    ├── metrics.json
    ├── model.joblib
    ├── prediction.png   (binary overlay)
    ├── probability.png  (continuous ramp)
    └── mislabels_top{N}.json
```

`modelId` is a 16-char SHA-1 of the request body. Re-issuing the same
classify request returns the cached payload immediately. Use
`?refresh=true` (or pass `refresh: true` on the POST body) to invalidate.

## Frontend

See [`../frontend/README.md`](../frontend/README.md). The frontend is
strict API-only: it talks directly to `VITE_API_BASE_URL` with no proxy and
no mock data fallback.
