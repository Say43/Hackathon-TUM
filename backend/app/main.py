"""FastAPI service: trained baseline model + tile predictions for the dashboard."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import (
    describe_data_dir_resolution,
    get_data_dir,
    get_model_path,
    get_pred_dir,
)
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


@app.on_event("startup")
def _log_resolved_paths() -> None:
    """Prints where the API is looking for the dataset on boot.

    Makes path-misconfiguration obvious in the server console (or Jupyter
    terminal) without having to hit /api/debug/paths.
    """
    info = describe_data_dir_resolution()
    banner = [
        "=" * 72,
        " Dataset path resolution",
        f"   repoRoot          : {info['repoRoot']}",
        f"   modelTrainingDir  : {info['modelTrainingDir']}",
        f"   env source        : {info['envVar']['source']}",
        f"   env raw value     : {info['envVar']['rawValue']}",
        f"   env resolved abs  : {info['envVar']['resolvedAbsolute']}",
        f"   env resolved ok   : {info['envVar']['resolvedExists']}",
        "   default candidates:",
    ]
    for c in info["defaultCandidates"]:
        banner.append(f"     - exists={c['exists']!s:<5} {c['path']}")
    banner.extend(
        [
            f"   ==> resolved      : {info['resolved']}",
            f"   ==> exists        : {info['resolvedExists']}",
            "=" * 72,
        ]
    )
    for line in banner:
        logger.info(line)


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


@app.get("/api/debug/paths")
def debug_paths() -> dict:
    """Show every path the API is aware of + whether it exists on disk.

    Hit this when you see a 503 from /api/tiles/.../timeseries so you can see
    which candidate paths were probed on THIS server.
    """
    model_path = get_model_path()
    pred_dir = get_pred_dir()
    resolution = describe_data_dir_resolution()
    paths = paths_from_data_dir(get_data_dir())
    sample_s1_dir: str | None = None
    sample_s2_dir: str | None = None
    if paths is not None and paths.data_dir.exists():
        s1 = paths.data_dir / "sentinel-1" / "test"
        s2 = paths.data_dir / "sentinel-2" / "test"
        sample_s1_dir = str(s1) if s1.exists() else f"MISSING: {s1}"
        sample_s2_dir = str(s2) if s2.exists() else f"MISSING: {s2}"
    return {
        "cwd": str(Path.cwd()),
        "envVars": {
            "MAKEATHON_DATA_DIR": os.environ.get("MAKEATHON_DATA_DIR"),
            "DATA_DIR": os.environ.get("DATA_DIR"),
            "MODEL_PATH": os.environ.get("MODEL_PATH"),
            "PRED_DIR": os.environ.get("PRED_DIR"),
        },
        "model": {
            "path": str(model_path),
            "exists": model_path.exists(),
        },
        "predictions": {
            "dir": str(pred_dir),
            "exists": pred_dir.exists(),
            "predTifs": sorted(p.name for p in pred_dir.glob("pred_*.tif"))
            if pred_dir.exists()
            else [],
        },
        "dataset": resolution,
        "sentinelProbe": {
            "s1TestDir": sample_s1_dir,
            "s2TestDir": sample_s2_dir,
        },
    }


@app.get("/api/tiles/{tile_id}/timeseries")
def tile_timeseries(tile_id: str, split: str = Query("test")) -> dict:
    if split not in ("train", "test"):
        raise HTTPException(400, detail="split must be train or test")
    paths = paths_from_data_dir(get_data_dir())
    if paths is None:
        info = describe_data_dir_resolution()
        probed = [c["path"] for c in info["defaultCandidates"]]
        raise HTTPException(
            503,
            detail=(
                "Dataset root not found. "
                f"MAKEATHON_DATA_DIR={info['envVar']['rawValue']!r}. "
                f"Probed defaults: {probed}. "
                "Call /api/debug/paths for a full breakdown."
            ),
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
