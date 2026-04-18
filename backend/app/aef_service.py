"""Adapter between FastAPI and the `alphaearth` package.

Keep this module thin: it converts incoming HTTP query parameters into the
dataclasses the package expects, runs the call, and shapes the JSON response.
All heavy lifting (rasterio, sklearn, umap) lives in `alphaearth/`.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

from alphaearth import classifiers, mislabels, previews, scatter
from alphaearth.io import (
    find_available_label_sources,
    label_pixel_counts,
    metadata_lookup,
    open_aef_tile,
    tile_geographic_bounds,
)
from alphaearth.paths import (
    LABEL_SOURCES,
    Paths,
    TileYear,
    discover_tiles,
)

logger = logging.getLogger(__name__)


def list_tiles(paths: Paths, *, split: str) -> list[dict]:
    """Tile listing enriched with metadata + label availability."""

    discovered = discover_tiles(paths, split)
    metadata = metadata_lookup(paths, split)
    out: list[dict] = []
    for tile, years in discovered.items():
        feat = metadata.get(tile)
        bounds = None
        centroid = None
        if years:
            try:
                lon_min, lat_min, lon_max, lat_max = tile_geographic_bounds(
                    paths, tile, years[0], split
                )
                bounds = {
                    "minLon": lon_min,
                    "minLat": lat_min,
                    "maxLon": lon_max,
                    "maxLat": lat_max,
                }
                centroid = {
                    "lon": (lon_min + lon_max) / 2,
                    "lat": (lat_min + lat_max) / 2,
                }
            except Exception as exc:  # pragma: no cover
                logger.warning("Could not derive bounds for %s: %s", tile, exc)
        label_sources = find_available_label_sources(paths, tile) if split == "train" else []
        meta_origin = (feat or {}).get("properties", {}).get("origin")
        out.append(
            {
                "tileId": tile,
                "split": split,
                "years": years,
                "hasLabels": bool(label_sources),
                "labelSources": label_sources,
                "bbox": bounds,
                "centroid": centroid,
                "originSrid": meta_origin,
            }
        )
    out.sort(key=lambda t: t["tileId"])
    return out


def tile_summary(
    paths: Paths,
    tile: str,
    year: int,
    split: str,
) -> dict:
    raster = open_aef_tile(paths, tile, year, split)
    bounds = tile_geographic_bounds(paths, tile, year, split)
    counts: dict[str, dict] = {}
    if split == "train":
        for source in LABEL_SOURCES:
            try:
                pc = label_pixel_counts(paths, tile, year, split, source)
                if pc is not None:
                    counts[source] = pc
            except Exception as exc:  # pragma: no cover
                logger.warning("counts(%s/%s/%s/%s) failed: %s", tile, year, split, source, exc)
    return {
        "tileId": tile,
        "year": year,
        "split": split,
        "bands": raster.n_bands,
        "height": int(raster.height),
        "width": int(raster.width),
        "bbox": {
            "minLon": bounds[0],
            "minLat": bounds[1],
            "maxLon": bounds[2],
            "maxLat": bounds[3],
        },
        "labelCounts": counts,
    }


def channel_stats(paths: Paths, tile: str, year: int, split: str) -> list[dict]:
    raster = open_aef_tile(paths, tile, year, split)
    return previews.channel_stats(raster)


def pca_preview_path(
    paths: Paths,
    cache_dir: Path,
    tile: str,
    year: int,
    split: str,
    *,
    refresh: bool = False,
) -> Path:
    return previews.cached_pca_preview(
        paths, cache_dir, tile, year, split, refresh=refresh
    )


def band_composite_path(
    paths: Paths,
    cache_dir: Path,
    tile: str,
    year: int,
    split: str,
    bands: tuple[int, ...],
    mode: str,
    *,
    refresh: bool = False,
) -> Path:
    return previews.cached_band_composite(
        paths, cache_dir, tile, year, split, bands, mode, refresh=refresh
    )


def scatter_payload(
    paths: Paths,
    cache_dir: Path,
    *,
    method: str,
    tiles: Iterable[TileYear],
    label_source: str,
    sample_per_tile: int,
    refresh: bool = False,
) -> dict:
    request = scatter.ScatterRequest(
        method=method,
        tiles=tuple(tiles),
        label_source=label_source,
        sample_per_tile=sample_per_tile,
    )
    return scatter.cached_scatter(paths, cache_dir, request, refresh=refresh)


def classify_run(
    paths: Paths,
    cache_dir: Path,
    *,
    model: str,
    train_tiles: Iterable[TileYear],
    val_tile: TileYear | None,
    test_tile: TileYear,
    label_source: str,
    sample_per_tile: int,
    refresh: bool = False,
) -> dict:
    request = classifiers.ClassifyRequest(
        model=model,
        train_tiles=tuple(train_tiles),
        val_tile=val_tile,
        test_tile=test_tile,
        label_source=label_source,
        sample_per_tile=sample_per_tile,
    )
    return classifiers.run_classifier(paths, cache_dir, request, refresh=refresh)


def classify_artifact(cache_dir: Path, model_id: str, name: str) -> Path:
    path = classifiers.run_artifact_path(cache_dir, model_id, name)
    if not path.exists():
        raise FileNotFoundError(f"Run artifact missing: {path}")
    return path


def classify_payload(cache_dir: Path, model_id: str) -> dict | None:
    return classifiers.load_run(cache_dir, model_id)


def mislabel_payload(
    paths: Paths,
    cache_dir: Path,
    model_id: str,
    *,
    top: int,
    refresh: bool = False,
) -> dict:
    return mislabels.cached_mislabels(
        paths, cache_dir, model_id, top=top, refresh=refresh
    )
