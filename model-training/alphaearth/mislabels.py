"""Detect regions where a trained classifier strongly disagrees with the label.

A high disagreement score is a proxy for likely-mislabelled or mis-aligned
pixels. We aggregate disagreeing pixels into connected regions via
`scipy.ndimage.label`, score each region by area * mean confidence, and
return the top-N as a list of geographic boxes.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform_bounds
from scipy import ndimage

from . import cache
from .paths import Paths


def _affine_to_lonlat(
    rows: np.ndarray,
    cols: np.ndarray,
    transform: rasterio.Affine,
    src_crs: rasterio.crs.CRS,
) -> tuple[np.ndarray, np.ndarray]:
    xs, ys = rasterio.transform.xy(transform, rows.tolist(), cols.tolist(), offset="center")
    xs_arr = np.asarray(xs, dtype=np.float64)
    ys_arr = np.asarray(ys, dtype=np.float64)
    if str(src_crs).upper() in ("EPSG:4326", "EPSG:4326+5773"):
        return xs_arr, ys_arr
    # Treat as 1-point bounding box per coordinate to reuse transform_bounds.
    lon = []
    lat = []
    for x, y in zip(xs_arr, ys_arr):
        l_min, b_min, _, _ = transform_bounds(src_crs, "EPSG:4326", x, y, x, y)
        lon.append(l_min)
        lat.append(b_min)
    return np.asarray(lon), np.asarray(lat)


def find_mislabel_regions(
    paths: Paths,
    cache_root: Path,
    model_id: str,
    *,
    top: int = 20,
    confidence_threshold: float = 0.7,
    min_area_pixels: int = 5,
) -> list[dict]:
    """Look at a cached classifier run, return top-N disagreement regions."""

    run_dir = cache.runs_dir(cache_root) / model_id
    metrics_path = run_dir / "metrics.json"
    payload = cache.read_json(metrics_path)
    if payload is None:
        raise FileNotFoundError(f"Run {model_id} not found at {run_dir}")

    label_path = run_dir / "test_label.npy"
    if not label_path.exists():
        # No labels for the test tile (test split). Mislabels are undefined.
        return []
    label = np.load(label_path).astype(np.int8)
    pred = np.load(run_dir / "prediction.npy").astype(np.int8)
    proba = np.load(run_dir / "probability.npy").astype(np.float32)
    valid = np.load(run_dir / "valid.npy").astype(bool)

    disagree = (label != pred) & valid
    confidence = np.where(label == 1, 1.0 - proba, proba)
    high_conf_disagree = disagree & (confidence >= confidence_threshold)
    if not high_conf_disagree.any():
        return []

    structure = np.ones((3, 3), dtype=np.uint8)
    components, n_components = ndimage.label(high_conf_disagree, structure=structure)
    if n_components == 0:
        return []

    # Need transform/CRS from the source tile to translate row/col to lon/lat.
    tile_info = payload["tile"]
    src_path = paths.aef_tile_path(tile_info["id"], tile_info["year"], tile_info["split"])
    with rasterio.open(src_path) as src:
        transform = src.transform
        crs = src.crs

    out: list[dict] = []
    for cid in range(1, n_components + 1):
        mask = components == cid
        area = int(mask.sum())
        if area < min_area_pixels:
            continue
        rows, cols = np.where(mask)
        avg_conf = float(confidence[rows, cols].mean())
        majority_label = int(round(label[rows, cols].mean()))
        majority_pred = int(round(pred[rows, cols].mean()))
        lons, lats = _affine_to_lonlat(rows, cols, transform, crs)
        bbox = {
            "minLon": float(lons.min()),
            "maxLon": float(lons.max()),
            "minLat": float(lats.min()),
            "maxLat": float(lats.max()),
        }
        centroid = {
            "lon": float(lons.mean()),
            "lat": float(lats.mean()),
        }
        out.append(
            {
                "id": int(cid),
                "areaPixels": area,
                "labelClass": majority_label,
                "predictedClass": majority_pred,
                "meanConfidence": avg_conf,
                "score": float(area * avg_conf),
                "bbox": bbox,
                "centroid": centroid,
            }
        )

    out.sort(key=lambda r: r["score"], reverse=True)
    return out[:top]


def cached_mislabels(
    paths: Paths,
    cache_root: Path,
    model_id: str,
    *,
    top: int = 20,
    refresh: bool = False,
) -> dict:
    out_path = cache.runs_dir(cache_root) / model_id / f"mislabels_top{top}.json"
    if not refresh and out_path.exists():
        cached = cache.read_json(out_path)
        if cached is not None:
            return cached
    regions = find_mislabel_regions(paths, cache_root, model_id, top=top)
    payload = {"modelId": model_id, "regions": regions, "top": top}
    cache.write_json(out_path, payload)
    return payload
