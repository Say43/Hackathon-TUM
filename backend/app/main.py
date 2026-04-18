"""FastAPI service: trained baseline model + tile predictions for the dashboard."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import get_data_dir, get_model_path, get_pred_dir
from .ml_service import (
    build_timeseries,
    get_model,
    list_tile_ids_for_api,
    paths_from_data_dir,
    tile_inference_bundle,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="osapiens Deforestation Monitor API",
    version="0.1.0",
    description="Serves inference from the Makeathon baseline model (joblib) and cached GeoTIFFs.",
)

_DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

_env_origins = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "").split(",")
    if o.strip()
]
_allow_all = "*" in _env_origins
_allowed_origins = ["*"] if _allow_all else [*_DEFAULT_ORIGINS, *_env_origins]

# Support Vercel preview URLs (e.g. `project-git-branch-team.vercel.app`)
# without having to enumerate them one by one.
_origin_regex = os.environ.get(
    "CORS_ORIGIN_REGEX",
    r"https://.*\.vercel\.app",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=None if _allow_all else _origin_regex,
    allow_credentials=not _allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    model_path = get_model_path()
    data_dir = get_data_dir()
    pred_dir = get_pred_dir()
    paths = paths_from_data_dir(data_dir)
    ok_model = model_path.exists()
    ok_data = paths is not None and paths.data_dir.exists()
    ok_pred = pred_dir.exists() and any(pred_dir.glob("pred_*.tif"))
    try:
        if ok_model:
            get_model(model_path)
        model_ready = ok_model
    except Exception as exc:  # pragma: no cover
        logger.exception("Model load failed")
        model_ready = False
        err = str(exc)
    else:
        err = None
    tiles = list_tile_ids_for_api(paths, pred_dir, split="test")
    return {
        "status": "ok" if model_ready and (ok_data or ok_pred) else "degraded",
        "modelPath": str(model_path),
        "modelLoaded": model_ready,
        "dataDir": str(data_dir) if data_dir else None,
        "datasetPresent": ok_data,
        "predDir": str(pred_dir),
        "cachedPredictionsPresent": ok_pred,
        "testTiles": len(tiles),
        "error": err,
    }


@app.get("/api/tiles")
def list_tiles(split: str = Query("test")) -> dict:
    model_path = get_model_path()
    if not model_path.exists():
        raise HTTPException(500, detail=f"Model not found: {model_path}")
    get_model(model_path)
    paths = paths_from_data_dir(get_data_dir())
    pred_dir = get_pred_dir()
    if split not in ("train", "test"):
        raise HTTPException(400, detail="split must be train or test")
    ids = list_tile_ids_for_api(paths, pred_dir, split=split)
    return {"split": split, "tileIds": ids, "count": len(ids)}


@app.get("/api/tiles/{tile_id}")
def get_tile(
    tile_id: str,
    split: str = Query("test"),
    threshold: float = Query(0.5, ge=0.0, le=1.0),
) -> dict:
    if split not in ("train", "test"):
        raise HTTPException(400, detail="split must be train or test")
    try:
        return tile_inference_bundle(
            tile_id,
            get_model_path(),
            get_data_dir(),
            get_pred_dir(),
            split=split,
            threshold=threshold,
        )
    except FileNotFoundError as e:
        raise HTTPException(404, detail=str(e)) from e
    except Exception as e:  # pragma: no cover
        logger.exception("Inference failed for %s", tile_id)
        raise HTTPException(500, detail=str(e)) from e


@app.get("/api/plots")
def list_plots(
    split: str = Query("test"),
    threshold: float = Query(0.5, ge=0.0, le=1.0),
) -> dict:
    """Full list of `LandPlot`-shaped objects for the frontend."""
    if split not in ("train", "test"):
        raise HTTPException(400, detail="split must be train or test")
    model_path = get_model_path()
    if not model_path.exists():
        raise HTTPException(500, detail=f"Model not found: {model_path}")
    get_model(model_path)
    paths = paths_from_data_dir(get_data_dir())
    pred_dir = get_pred_dir()
    ids = list_tile_ids_for_api(paths, pred_dir, split=split)
    plots: list[dict] = []
    errors: list[str] = []
    for tid in ids:
        try:
            plots.append(
                tile_inference_bundle(
                    tid,
                    model_path,
                    get_data_dir(),
                    pred_dir,
                    split=split,
                    threshold=threshold,
                )
            )
        except Exception as exc:  # pragma: no cover
            errors.append(f"{tid}: {exc}")
    return {"split": split, "plots": plots, "errors": errors}


@app.get("/api/tiles/{tile_id}/timeseries")
def tile_timeseries(tile_id: str, split: str = Query("test")) -> dict:
    if split not in ("train", "test"):
        raise HTTPException(400, detail="split must be train or test")
    paths = paths_from_data_dir(get_data_dir())
    if paths is None:
        raise HTTPException(
            503,
            detail="Dataset root not found. Set MAKEATHON_DATA_DIR or place data under data/makeathon-challenge.",
        )
    try:
        points = build_timeseries(paths, tile_id, split)
    except Exception as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    if not points:
        raise HTTPException(
            404,
            detail="No Sentinel-2 time series available for this tile.",
        )
    return {"tileId": tile_id, "split": split, "points": points}


@app.get("/")
def root() -> dict:
    return {"service": "osapiens-deforestation-monitor-api", "docs": "/docs"}
