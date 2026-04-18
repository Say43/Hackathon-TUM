# osapiens Deforestation Monitor — API

FastAPI service that loads **`model-training/runs/baseline/model.joblib`** and serves:

- **`GET /api/health`** — model path, whether the dataset is present, cached `pred_*.tif` availability  
- **`GET /api/tiles`** — list test tile IDs (from Sentinel-2 folders if `MAKEATHON_DATA_DIR` is set, otherwise from `pred_*.tif` names)  
- **`GET /api/plots`** — full list of plot objects for the React dashboard (inference per tile)  
- **`GET /api/tiles/{tile_id}`** — single plot payload  
- **`GET /api/tiles/{tile_id}/timeseries`** — monthly NDVI / VV from Sentinel stacks (**requires** local challenge data)

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r ../model-training/requirements.txt
pip install -r requirements.txt
```

> If joblib warns about **scikit-learn version mismatch**, install the same sklearn major as used to train the model (e.g. `pip install "scikit-learn~=1.7.1"`).

## Run

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://127.0.0.1:8000/docs** for Swagger UI.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `MODEL_PATH` | Override path to `model.joblib` (default: `model-training/runs/baseline/model.joblib`) |
| `PRED_DIR` | Directory with `pred_{tileId}.tif` for stats when rasters exist but raw stacks do not (default: `model-training/runs/baseline/predictions`) |
| `MAKEATHON_DATA_DIR` or `DATA_DIR` | Root of the challenge dataset (`sentinel-1/`, `sentinel-2/`, `aef-embeddings/`, …) for **live** `predict_proba` and **timeseries** |

## Frontend

From repo root, start Vite (it proxies `/api` → `http://127.0.0.1:8000`):

```bash
cd frontend && npm run dev
```

Optional: `VITE_API_BASE_URL=http://localhost:8000` if you serve the UI from another origin without the proxy.
