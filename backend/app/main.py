"""FastAPI service for the AlphaEarth Foundations explorer.

Endpoints
---------

* `GET  /api/health`                                     — service & dataset health
* `GET  /api/debug/paths`                                — path resolution snapshot
* `GET  /api/aef/tiles?split=train|test`                 — tile + year listing
* `GET  /api/aef/tiles/{tile}/{year}/summary`            — bbox + label counts
* `GET  /api/aef/tiles/{tile}/{year}/stats`              — 64-band statistics
* `GET  /api/aef/tiles/{tile}/{year}/preview.png`        — PCA-3 false-colour PNG
* `GET  /api/aef/tiles/{tile}/{year}/bands.png?r=&g=&b=` — custom band composite
* `GET  /api/aef/scatter`                                — PCA/UMAP 2D scatter
* `POST /api/aef/classify`                               — train SVM/MLP, evaluate
* `GET  /api/aef/classify/{modelId}`                     — cached run metrics
* `GET  /api/aef/classify/{modelId}/prediction.png`      — full-tile prediction
* `GET  /api/aef/classify/{modelId}/probability.png`     — probability heatmap
* `GET  /api/aef/classify/{modelId}/mislabels`           — top disagreement regions
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .config import (
    REPO_ROOT,
    describe_data_dir_resolution,
    get_cache_dir,
    get_data_dir,
)
from . import aef_service

# alphaearth lives under model-training/ and is on sys.path via config import.
from alphaearth.paths import LABEL_SOURCES, Paths, TileYear

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AlphaEarth Explorer API",
    version="1.0.0",
    description=(
        "Serves AEF embedding previews, PCA/UMAP scatter, SVM/MLP classifiers, "
        "and disagreement-based mislabel regions over the Makeathon dataset."
    ),
)

_DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]
_env_origins = [
    o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()
]
_allow_all = "*" in _env_origins
_allowed_origins = ["*"] if _allow_all else [*_DEFAULT_ORIGINS, *_env_origins]
_origin_regex = os.environ.get("CORS_ORIGIN_REGEX", r"https://.*\.vercel\.app")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=None if _allow_all else _origin_regex,
    allow_credentials=not _allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_paths() -> Paths:
    data_dir = get_data_dir()
    if data_dir is None:
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
    return Paths(data_dir=data_dir)


def _parse_tile_year(value: str, *, default_split: str = "train") -> TileYear:
    parts = value.split(":")
    try:
        if len(parts) == 2:
            tile, year = parts
            split = default_split
        elif len(parts) == 3:
            tile, year, split = parts
        else:
            raise ValueError
        if split not in ("train", "test"):
            raise ValueError
        return TileYear(tile=tile, year=int(year), split=split)
    except ValueError as exc:
        raise HTTPException(
            400, detail=f"Invalid tile spec {value!r}, expected 'tile:year[:split]'."
        ) from exc


def _validate_label_source(source: str) -> str:
    if source not in LABEL_SOURCES:
        raise HTTPException(
            400,
            detail=f"label_source must be one of {LABEL_SOURCES}, got {source!r}.",
        )
    return source


def _validate_split(split: str) -> str:
    if split not in ("train", "test"):
        raise HTTPException(400, detail="split must be 'train' or 'test'")
    return split


@app.on_event("startup")
def _log_resolved_paths() -> None:
    info = describe_data_dir_resolution()
    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    banner = [
        "=" * 72,
        " AlphaEarth Explorer API — path resolution",
        f"   cwd               : {info['cwd']}",
        f"   repoRoot          : {info['repoRoot']}",
        f"   modelTrainingDir  : {info['modelTrainingDir']}",
        f"   env source        : {info['envVar']['source']}",
        f"   env raw value     : {info['envVar']['rawValue']}",
        f"   env is relative   : {info['envVar']['isRelative']}",
        f"   env anchored to   : {info['envVar']['anchoredTo']}",
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
            f"   aefDir            : {info['aefDir']['path']}  exists={info['aefDir']['exists']}",
            f"   labelsDir         : {info['labelsDir']['path']}  exists={info['labelsDir']['exists']}",
            f"   cacheDir          : {info['cacheDir']['path']}  exists={info['cacheDir']['exists']}",
            "=" * 72,
        ]
    )
    for line in banner:
        logger.info(line)


@app.get("/")
def root() -> dict:
    return {
        "service": "alphaearth-explorer-api",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
def health() -> dict:
    info = describe_data_dir_resolution()
    cache_dir = get_cache_dir()
    return {
        "status": "ok" if info["resolvedExists"] and info["aefDir"]["exists"] else "degraded",
        "dataDir": info["resolved"],
        "datasetPresent": info["resolvedExists"],
        "aefDirPresent": info["aefDir"]["exists"],
        "labelsDirPresent": info["labelsDir"]["exists"],
        "cacheDir": str(cache_dir),
        "cacheDirPresent": cache_dir.exists(),
        "labelSources": list(LABEL_SOURCES),
    }


@app.get("/api/debug/paths")
def debug_paths() -> dict:
    return {
        "cwd": str(Path.cwd()),
        "envVars": {
            "MAKEATHON_DATA_DIR": os.environ.get("MAKEATHON_DATA_DIR"),
            "DATA_DIR": os.environ.get("DATA_DIR"),
            "AEF_CACHE_DIR": os.environ.get("AEF_CACHE_DIR"),
        },
        "dataset": describe_data_dir_resolution(),
    }


@app.get("/api/aef/tiles")
def list_tiles(split: str = Query("train")) -> dict:
    _validate_split(split)
    paths = _require_paths()
    tiles = aef_service.list_tiles(paths, split=split)
    return {"split": split, "count": len(tiles), "tiles": tiles}


@app.get("/api/aef/tiles/{tile}/{year}/summary")
def tile_summary(tile: str, year: int, split: str = Query("train")) -> dict:
    _validate_split(split)
    paths = _require_paths()
    try:
        return aef_service.tile_summary(paths, tile, year, split)
    except FileNotFoundError as exc:
        raise HTTPException(404, detail=str(exc)) from exc


@app.get("/api/aef/tiles/{tile}/{year}/stats")
def tile_stats(tile: str, year: int, split: str = Query("train")) -> dict:
    _validate_split(split)
    paths = _require_paths()
    try:
        stats = aef_service.channel_stats(paths, tile, year, split)
    except FileNotFoundError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    return {"tileId": tile, "year": year, "split": split, "channels": stats}


@app.get("/api/aef/tiles/{tile}/{year}/preview.png")
def tile_preview(
    tile: str,
    year: int,
    split: str = Query("train"),
    refresh: bool = Query(False),
):
    _validate_split(split)
    paths = _require_paths()
    cache_dir = get_cache_dir()
    try:
        png = aef_service.pca_preview_path(paths, cache_dir, tile, year, split, refresh=refresh)
    except FileNotFoundError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    return FileResponse(png, media_type="image/png")


@app.get("/api/aef/tiles/{tile}/{year}/bands.png")
def tile_bands(
    tile: str,
    year: int,
    split: str = Query("train"),
    r: int = Query(0, ge=0, le=63),
    g: int = Query(21, ge=0, le=63),
    b: int = Query(42, ge=0, le=63),
    mode: Literal["rgb", "gray"] = Query("rgb"),
    refresh: bool = Query(False),
):
    _validate_split(split)
    paths = _require_paths()
    cache_dir = get_cache_dir()
    bands = (r,) if mode == "gray" else (r, g, b)
    try:
        png = aef_service.band_composite_path(
            paths, cache_dir, tile, year, split, bands, mode, refresh=refresh
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    return FileResponse(png, media_type="image/png")


@app.get("/api/aef/scatter")
def scatter(
    method: Literal["pca", "umap"] = Query("pca"),
    tiles: str = Query(..., description="Comma-separated tile:year[:split] specs"),
    label_source: str = Query("gladl"),
    sample_per_tile: int = Query(2000, ge=100, le=10000),
    refresh: bool = Query(False),
) -> dict:
    _validate_label_source(label_source)
    paths = _require_paths()
    parsed = [_parse_tile_year(s.strip()) for s in tiles.split(",") if s.strip()]
    if not parsed:
        raise HTTPException(400, detail="Provide at least one tile.")
    cache_dir = get_cache_dir()
    try:
        return aef_service.scatter_payload(
            paths,
            cache_dir,
            method=method,
            tiles=parsed,
            label_source=label_source,
            sample_per_tile=sample_per_tile,
            refresh=refresh,
        )
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc


class ClassifyBody(BaseModel):
    model: Literal["svm", "mlp"] = Field(..., description="Estimator family")
    train_tiles: list[str] = Field(..., min_length=1, description="tile:year[:split] specs")
    val_tile: Optional[str] = Field(None, description="tile:year[:split] spec, optional")
    test_tile: str = Field(..., description="tile:year[:split] spec")
    label_source: str = Field("gladl")
    sample_per_tile: int = Field(4000, ge=100, le=20000)
    refresh: bool = Field(False)


@app.post("/api/aef/classify")
def classify(body: ClassifyBody) -> dict:
    _validate_label_source(body.label_source)
    paths = _require_paths()
    train_tiles = [_parse_tile_year(s) for s in body.train_tiles]
    val_tile = _parse_tile_year(body.val_tile) if body.val_tile else None
    test_tile = _parse_tile_year(body.test_tile, default_split="train")
    cache_dir = get_cache_dir()
    try:
        return aef_service.classify_run(
            paths,
            cache_dir,
            model=body.model,
            train_tiles=train_tiles,
            val_tile=val_tile,
            test_tile=test_tile,
            label_source=body.label_source,
            sample_per_tile=body.sample_per_tile,
            refresh=body.refresh,
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(400, detail=str(exc)) from exc


@app.get("/api/aef/classify/{model_id}")
def classify_lookup(model_id: str) -> dict:
    cache_dir = get_cache_dir()
    payload = aef_service.classify_payload(cache_dir, model_id)
    if payload is None:
        raise HTTPException(404, detail=f"Run {model_id} not found")
    payload = dict(payload)
    payload["fromCache"] = True
    return payload


@app.get("/api/aef/classify/{model_id}/prediction.png")
def classify_prediction_png(model_id: str):
    cache_dir = get_cache_dir()
    try:
        path = aef_service.classify_artifact(cache_dir, model_id, "prediction.png")
    except FileNotFoundError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    return FileResponse(path, media_type="image/png")


@app.get("/api/aef/classify/{model_id}/probability.png")
def classify_probability_png(model_id: str):
    cache_dir = get_cache_dir()
    try:
        path = aef_service.classify_artifact(cache_dir, model_id, "probability.png")
    except FileNotFoundError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    return FileResponse(path, media_type="image/png")


@app.get("/api/aef/classify/{model_id}/mislabels")
def classify_mislabels(
    model_id: str,
    top: int = Query(20, ge=1, le=200),
    refresh: bool = Query(False),
) -> dict:
    paths = _require_paths()
    cache_dir = get_cache_dir()
    try:
        return aef_service.mislabel_payload(
            paths, cache_dir, model_id, top=top, refresh=refresh
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
