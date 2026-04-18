"""Reading AEF tiles, aligning weak labels, sampling labelled pixels."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject, transform_bounds

from .paths import Paths, discover_label_files, parse_aef_name

logger = logging.getLogger(__name__)

# A label value > 0 means "alert" / "deforested" for every weak source we use.
_BINARY_THRESHOLD = 0


@dataclass(frozen=True)
class TileRaster:
    """Raw AEF observation, materialised as float32 (bands, H, W)."""

    tile: str
    year: int
    split: str
    array: np.ndarray  # shape (64, H, W) float32
    transform: rasterio.Affine
    crs: rasterio.crs.CRS
    width: int
    height: int

    @property
    def n_bands(self) -> int:
        return int(self.array.shape[0])


def open_aef_tile(paths: Paths, tile: str, year: int, split: str) -> TileRaster:
    """Read an AEF tile fully into memory as float32."""

    src_path = paths.aef_tile_path(tile, year, split)
    if not src_path.exists():
        raise FileNotFoundError(f"AEF tile not found: {src_path}")
    with rasterio.open(src_path) as src:
        arr = src.read(out_dtype="float32")
        return TileRaster(
            tile=tile,
            year=year,
            split=split,
            array=arr,
            transform=src.transform,
            crs=src.crs,
            width=src.width,
            height=src.height,
        )


def reproject_label_to(
    label_path: Path,
    target: TileRaster,
    *,
    resampling: Resampling = Resampling.nearest,
) -> np.ndarray:
    """Reproject a single-band label raster onto the AEF tile grid.

    Returns an int32 array of shape (target.height, target.width) where each
    pixel is the resampled label value (0 = no alert, >0 = alert). A small
    int dtype is sufficient — none of the weak sources exceed 65535.
    """

    out = np.zeros((target.height, target.width), dtype=np.int32)
    with rasterio.open(label_path) as src:
        reproject(
            source=rasterio.band(src, 1),
            destination=out,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=target.transform,
            dst_crs=target.crs,
            resampling=resampling,
        )
    return out


# Patterns understood inside a label filename, e.g. "alert22" / "alertDate22".
_YEAR_SUFFIX_RE = re.compile(r"alert(?:Date)?(\d{2})", re.IGNORECASE)


def _two_digit_year(filename: str) -> int | None:
    m = _YEAR_SUFFIX_RE.search(filename)
    if not m:
        return None
    yy = int(m.group(1))
    return 2000 + yy


def select_label_file(
    paths: Paths,
    source: str,
    tile: str,
    year: int,
) -> Path | None:
    """Pick the weak-label file that best matches a (tile, year).

    `gladl` files have per-year alerts (`alert20.tif`, `alert21.tif`, ...).
    `glads2` and `radd` have a single accumulated alert raster per tile, which
    we use for any year.
    """

    candidates = discover_label_files(paths, source, tile)
    if not candidates:
        return None

    yearly = []
    accum = []
    for path in candidates:
        if "alertDate" in path.name:
            continue
        if _two_digit_year(path.name) is not None:
            yearly.append(path)
        else:
            accum.append(path)

    for path in yearly:
        if _two_digit_year(path.name) == year:
            return path

    if accum:
        return accum[0]
    if yearly:
        return min(yearly, key=lambda p: abs((_two_digit_year(p.name) or 0) - year))
    return None


def label_array_for(
    paths: Paths,
    target: TileRaster,
    source: str,
) -> np.ndarray | None:
    """Return a binary (0/1) label raster aligned to `target`, or None."""

    p = select_label_file(paths, source, target.tile, target.year)
    if p is None:
        return None
    raw = reproject_label_to(p, target)
    return (raw > _BINARY_THRESHOLD).astype(np.uint8)


def valid_pixel_mask(arr: np.ndarray) -> np.ndarray:
    """A pixel is valid if ALL 64 bands are finite. Shape (H, W) bool."""
    return np.isfinite(arr).all(axis=0)


def sample_labelled_pixels(
    tile: TileRaster,
    label: np.ndarray,
    *,
    sample: int,
    rng: np.random.Generator | None = None,
    balance: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Draw up to `sample` labelled pixel embeddings from one tile.

    Returns
    -------
    X : (N, 64) float32
    y : (N,)    uint8
    coords : (N, 2) int32 — (row, col) of each sample so callers can map
             predictions back onto the tile grid.
    """

    rng = rng if rng is not None else np.random.default_rng(42)
    valid = valid_pixel_mask(tile.array)
    pos_mask = valid & (label == 1)
    neg_mask = valid & (label == 0)

    pos_idx = np.argwhere(pos_mask)
    neg_idx = np.argwhere(neg_mask)

    if balance:
        per_class = max(1, sample // 2)
        if pos_idx.size:
            pos_take = rng.choice(len(pos_idx), size=min(per_class, len(pos_idx)), replace=False)
            pos_sel = pos_idx[pos_take]
        else:
            pos_sel = np.empty((0, 2), dtype=np.int64)
        if neg_idx.size:
            neg_take = rng.choice(len(neg_idx), size=min(per_class, len(neg_idx)), replace=False)
            neg_sel = neg_idx[neg_take]
        else:
            neg_sel = np.empty((0, 2), dtype=np.int64)
        idx = np.concatenate([pos_sel, neg_sel], axis=0)
    else:
        all_idx = np.concatenate([pos_idx, neg_idx], axis=0)
        if len(all_idx) == 0:
            idx = all_idx
        else:
            take = rng.choice(len(all_idx), size=min(sample, len(all_idx)), replace=False)
            idx = all_idx[take]

    if idx.size == 0:
        return (
            np.empty((0, tile.n_bands), dtype=np.float32),
            np.empty((0,), dtype=np.uint8),
            np.empty((0, 2), dtype=np.int32),
        )

    rows = idx[:, 0]
    cols = idx[:, 1]
    X = tile.array[:, rows, cols].T.astype(np.float32, copy=False)
    y = label[rows, cols].astype(np.uint8, copy=False)
    coords = idx.astype(np.int32, copy=False)
    return X, y, coords


def sample_unlabelled_pixels(
    tile: TileRaster,
    *,
    sample: int,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Draw `sample` valid pixels from a tile that has no labels (test split)."""

    rng = rng if rng is not None else np.random.default_rng(42)
    valid = valid_pixel_mask(tile.array)
    idx = np.argwhere(valid)
    if idx.size == 0:
        return (
            np.empty((0, tile.n_bands), dtype=np.float32),
            np.empty((0, 2), dtype=np.int32),
        )
    take = rng.choice(len(idx), size=min(sample, len(idx)), replace=False)
    sel = idx[take]
    rows, cols = sel[:, 0], sel[:, 1]
    X = tile.array[:, rows, cols].T.astype(np.float32, copy=False)
    return X, sel.astype(np.int32, copy=False)


def tile_geographic_bounds(
    paths: Paths, tile: str, year: int, split: str
) -> tuple[float, float, float, float]:
    """Return (lon_min, lat_min, lon_max, lat_max) of a tile in WGS84."""

    path = paths.aef_tile_path(tile, year, split)
    with rasterio.open(path) as src:
        bounds = src.bounds
        return tuple(transform_bounds(src.crs, "EPSG:4326", *bounds))


def tile_centroid_lonlat(
    paths: Paths, tile: str, year: int, split: str
) -> tuple[float, float]:
    lon_min, lat_min, lon_max, lat_max = tile_geographic_bounds(paths, tile, year, split)
    return ((lon_min + lon_max) / 2, (lat_min + lat_max) / 2)


def all_pixels_matrix(tile: TileRaster) -> tuple[np.ndarray, np.ndarray]:
    """Return (N, 64) float32 + (H, W) bool valid mask for a full-tile predict.

    The matrix only contains the valid pixels (so the caller must use the mask
    to scatter predictions back onto the (H, W) grid).
    """

    valid = valid_pixel_mask(tile.array)
    flat = tile.array[:, valid].T.astype(np.float32, copy=False)
    return flat, valid


def metadata_features(paths: Paths, split: str) -> list[dict]:
    """Return the feature list from metadata/{split}_tiles.geojson, or []."""

    f = paths.metadata_geojson(split)
    if not f.exists():
        return []
    try:
        with f.open("r") as fp:
            gj = json.load(fp)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read %s: %s", f, exc)
        return []
    feats = gj.get("features") or []
    if not isinstance(feats, list):
        return []
    return feats


def metadata_lookup(paths: Paths, split: str) -> dict[str, dict]:
    """tile name -> metadata feature dict."""

    out: dict[str, dict] = {}
    for feat in metadata_features(paths, split):
        name = (feat.get("properties") or {}).get("name")
        if name:
            out[name] = feat
    return out


def label_pixel_counts(
    paths: Paths, tile: str, year: int, split: str, source: str
) -> dict[str, int] | None:
    """Quick counts: total valid pixels + positive label pixels for a tile."""

    if split != "train":
        return None
    target = open_aef_tile(paths, tile, year, split)
    label = label_array_for(paths, target, source)
    if label is None:
        return None
    valid = valid_pixel_mask(target.array)
    return {
        "valid": int(valid.sum()),
        "positive": int(((label == 1) & valid).sum()),
        "negative": int(((label == 0) & valid).sum()),
        "height": int(target.height),
        "width": int(target.width),
    }


def find_available_label_sources(paths: Paths, tile: str) -> list[str]:
    """Which weak-label sources actually have files for `tile`."""

    out = []
    for src in ("gladl", "glads2", "radd"):
        if discover_label_files(paths, src, tile):
            out.append(src)
    return out


def iterable_join(items: Iterable[str], sep: str = ",") -> str:
    return sep.join(sorted(set(items)))
