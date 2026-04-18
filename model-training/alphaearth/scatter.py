"""PCA-2D and UMAP-2D projections of labelled AEF pixel samples.

These power the "Low-dimensional Analysis" page: each point is one labelled
pixel, projected to 2D, coloured by binary deforestation label.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from . import cache
from .io import (
    label_array_for,
    open_aef_tile,
    sample_labelled_pixels,
)
from .paths import Paths, TileYear

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScatterRequest:
    method: str  # "pca" | "umap"
    tiles: tuple[TileYear, ...]
    label_source: str
    sample_per_tile: int = 2000
    seed: int = 42

    def cache_key(self) -> dict:
        return {
            "method": self.method,
            "tiles": [t.key for t in self.tiles],
            "labelSource": self.label_source,
            "samplePerTile": self.sample_per_tile,
            "seed": self.seed,
            "version": 2,
        }


def _gather_samples(
    paths: Paths,
    request: ScatterRequest,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    rng = np.random.default_rng(request.seed)
    Xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    tile_tags: list[str] = []
    for ty in request.tiles:
        if ty.split != "train":
            logger.info(
                "Skipping %s for scatter (no labels available outside the train split)",
                ty.key,
            )
            continue
        tile = open_aef_tile(paths, ty.tile, ty.year, ty.split)
        label = label_array_for(paths, tile, request.label_source)
        if label is None:
            logger.info(
                "Skipping %s — no %s label available",
                ty.key,
                request.label_source,
            )
            continue
        X, y, _ = sample_labelled_pixels(
            tile,
            label,
            sample=request.sample_per_tile,
            rng=rng,
            balance=True,
        )
        if X.size == 0:
            continue
        Xs.append(X)
        ys.append(y)
        tile_tags.extend([ty.key] * len(y))
    if not Xs:
        return (
            np.empty((0, 64), dtype=np.float32),
            np.empty((0,), dtype=np.uint8),
            [],
        )
    return np.concatenate(Xs, axis=0), np.concatenate(ys, axis=0), tile_tags


def project_pca_2d(X: np.ndarray, *, seed: int = 42) -> np.ndarray:
    if X.shape[0] < 2:
        return np.zeros((X.shape[0], 2), dtype=np.float32)
    pca = PCA(n_components=2, random_state=seed)
    return pca.fit_transform(X).astype(np.float32, copy=False)


def project_umap_2d(X: np.ndarray, *, seed: int = 42) -> np.ndarray:
    if X.shape[0] < 4:
        return np.zeros((X.shape[0], 2), dtype=np.float32)
    try:
        import umap  # noqa: PLC0415  (umap-learn is an optional heavy dep)
    except ImportError as e:
        raise RuntimeError(
            "umap-learn is required for UMAP projection. "
            "Install with `pip install umap-learn`."
        ) from e

    n_neighbors = max(2, min(15, X.shape[0] - 1))
    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=n_neighbors,
        min_dist=0.1,
        random_state=seed,
        n_jobs=1,
    )
    scaler = StandardScaler(with_mean=True, with_std=True)
    X_std = scaler.fit_transform(X)
    return reducer.fit_transform(X_std).astype(np.float32, copy=False)


def build_scatter(paths: Paths, request: ScatterRequest) -> dict:
    X, y, tile_tags = _gather_samples(paths, request)
    if X.shape[0] == 0:
        return {
            "method": request.method,
            "labelSource": request.label_source,
            "points": [],
            "samples": 0,
            "tilesUsed": [],
        }
    if request.method == "pca":
        proj = project_pca_2d(X, seed=request.seed)
    elif request.method == "umap":
        proj = project_umap_2d(X, seed=request.seed)
    else:
        raise ValueError(f"Unknown scatter method {request.method!r}")
    points = [
        {
            "x": float(proj[i, 0]),
            "y": float(proj[i, 1]),
            "label": int(y[i]),
            "tile": tile_tags[i],
        }
        for i in range(proj.shape[0])
    ]
    return {
        "method": request.method,
        "labelSource": request.label_source,
        "points": points,
        "samples": int(proj.shape[0]),
        "tilesUsed": sorted({t.key for t in request.tiles}),
    }


def cached_scatter(
    paths: Paths,
    cache_root: Path,
    request: ScatterRequest,
    *,
    refresh: bool = False,
) -> dict:
    key = cache.hash_request(request.cache_key())
    out_path = cache.scatter_dir(cache_root) / f"{request.method}_{request.label_source}_{key}.json"
    if not refresh:
        cached = cache.read_json(out_path)
        if cached is not None:
            return cached
    payload = build_scatter(paths, request)
    cache.write_json(out_path, payload)
    return payload


def parse_tile_year_string(s: str, default_split: str = "train") -> TileYear:
    """Parse "tile:year[:split]" into a TileYear."""

    parts = s.split(":")
    if len(parts) == 2:
        tile, year = parts
        split = default_split
    elif len(parts) == 3:
        tile, year, split = parts
    else:
        raise ValueError(f"Expected tile:year[:split], got {s!r}")
    return TileYear(tile=tile, year=int(year), split=split)


def parse_tile_year_list(items: Iterable[str], default_split: str = "train") -> tuple[TileYear, ...]:
    return tuple(parse_tile_year_string(s, default_split) for s in items)
