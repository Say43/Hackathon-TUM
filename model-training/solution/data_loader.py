"""Locate and read per-tile Sentinel-1, Sentinel-2, AEF and label rasters.

All readers align the output to the **Sentinel-2 grid** of the target tile,
because S2 is the finest / most complete reference in this challenge and the
submission raster is expected on that grid.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT

from .config import Paths

logger = logging.getLogger(__name__)


# Regexes for the filenames documented in the challenge notebook / README.
_S2_RE = re.compile(r"^(?P<tile>.+)__s2_l2a_(?P<year>\d{4})_(?P<month>\d{1,2})\.tif$")
_S1_RE = re.compile(
    r"^(?P<tile>.+)__s1_rtc_(?P<year>\d{4})_(?P<month>\d{1,2})_(?P<orbit>ascending|descending)\.tif$"
)
_AEF_RE = re.compile(r"^(?P<tile>.+)_(?P<year>\d{4})\.tiff?$")


@dataclass(frozen=True)
class TileRef:
    """Minimal reference to the S2 raster grid for a tile."""

    tile_id: str
    split: str
    s2_reference_path: Path
    height: int
    width: int
    crs: str
    transform: object  # rasterio Affine, kept loose to avoid import churn


def list_tile_ids(paths: Paths, split: str) -> list[str]:
    """Return tile ids discovered from the S2 folder of ``split``."""
    root = paths.s2_dir / split
    if not root.exists():
        return []
    ids = []
    for p in sorted(root.iterdir()):
        if p.is_dir() and p.name.endswith("__s2_l2a"):
            ids.append(p.name[: -len("__s2_l2a")])
    return ids


def pick_reference_s2(paths: Paths, split: str, tile_id: str) -> Path:
    """Pick a reference S2 file used to define the target grid (shape/CRS)."""
    tile_dir = paths.s2_tile_dir(split, tile_id)
    if not tile_dir.exists():
        raise FileNotFoundError(f"No S2 directory for tile {tile_id} in split {split}")
    candidates = sorted(tile_dir.glob("*.tif"))
    if not candidates:
        raise FileNotFoundError(f"No S2 tiff in {tile_dir}")
    return candidates[0]


def open_tile(paths: Paths, split: str, tile_id: str) -> TileRef:
    ref = pick_reference_s2(paths, split, tile_id)
    with rasterio.open(ref) as src:
        return TileRef(
            tile_id=tile_id,
            split=split,
            s2_reference_path=ref,
            height=src.height,
            width=src.width,
            crs=src.crs.to_string() if src.crs else "",
            transform=src.transform,
        )


def _read_aligned(path: Path, ref: TileRef, resampling: Resampling = Resampling.bilinear) -> np.ndarray:
    """Read ``path`` and warp it onto the reference S2 grid. Shape: (bands, H, W)."""
    with rasterio.open(path) as src:
        with WarpedVRT(
            src,
            crs=ref.crs,
            transform=ref.transform,
            width=ref.width,
            height=ref.height,
            resampling=resampling,
        ) as vrt:
            return vrt.read().astype(np.float32)


def _read_aligned_nearest(path: Path, ref: TileRef) -> np.ndarray:
    return _read_aligned(path, ref, resampling=Resampling.nearest)


# ---------------------------------------------------------------------------
# Sentinel-2
# ---------------------------------------------------------------------------

def list_s2_files(paths: Paths, split: str, tile_id: str) -> list[Path]:
    tile_dir = paths.s2_tile_dir(split, tile_id)
    return sorted(p for p in tile_dir.glob("*.tif") if _S2_RE.match(p.name))


def read_s2_stack(paths: Paths, ref: TileRef) -> np.ndarray:
    """Return stacked Sentinel-2 observations as ``(T, 12, H, W)`` float32.

    Missing bands / months are skipped. Cloud handling is left to downstream
    feature aggregation (we use nan-aware statistics).
    """
    files = list_s2_files(paths, ref.split, ref.tile_id)
    if not files:
        return np.empty((0, 0, ref.height, ref.width), dtype=np.float32)
    arrays = []
    for fp in files:
        try:
            arr = _read_aligned(fp, ref)
        except Exception as exc:  # pragma: no cover - defensive IO
            logger.warning("Skipping unreadable S2 file %s: %s", fp, exc)
            continue
        # 0 is the documented nodata for S2 reflectance; treat as NaN for stats.
        arr[arr == 0] = np.nan
        arrays.append(arr)
    if not arrays:
        return np.empty((0, 0, ref.height, ref.width), dtype=np.float32)
    return np.stack(arrays, axis=0)  # (T, B, H, W)


# ---------------------------------------------------------------------------
# Sentinel-1
# ---------------------------------------------------------------------------

def list_s1_files(paths: Paths, split: str, tile_id: str) -> list[Path]:
    tile_dir = paths.s1_tile_dir(split, tile_id)
    if not tile_dir.exists():
        return []
    return sorted(p for p in tile_dir.glob("*.tif") if _S1_RE.match(p.name))


def read_s1_stack(paths: Paths, ref: TileRef) -> np.ndarray:
    """Return stacked Sentinel-1 VV observations as ``(T, 1, H, W)`` float32."""
    files = list_s1_files(paths, ref.split, ref.tile_id)
    if not files:
        return np.empty((0, 1, ref.height, ref.width), dtype=np.float32)
    arrays = []
    for fp in files:
        try:
            arr = _read_aligned(fp, ref)
        except Exception as exc:  # pragma: no cover
            logger.warning("Skipping unreadable S1 file %s: %s", fp, exc)
            continue
        arr[arr <= 0] = np.nan  # linear-scale radar backscatter; 0 is nodata
        arrays.append(arr[:1])  # keep VV only (first band)
    if not arrays:
        return np.empty((0, 1, ref.height, ref.width), dtype=np.float32)
    return np.stack(arrays, axis=0)


# ---------------------------------------------------------------------------
# AEF embeddings
# ---------------------------------------------------------------------------

def list_aef_files(paths: Paths, split: str, tile_id: str) -> list[Path]:
    root = paths.aef_split_dir(split)
    if not root.exists():
        return []
    out = []
    for p in sorted(root.glob(f"{tile_id}_*.tif*")):
        if _AEF_RE.match(p.name):
            out.append(p)
    return out


def read_aef_mean(paths: Paths, ref: TileRef) -> np.ndarray:
    """Average the AEF embeddings across available years → ``(64, H, W)``.

    Using the temporal mean keeps the feature count manageable for a baseline.
    """
    files = list_aef_files(paths, ref.split, ref.tile_id)
    if not files:
        return np.zeros((0, ref.height, ref.width), dtype=np.float32)
    stack = []
    for fp in files:
        try:
            arr = _read_aligned(fp, ref)
        except Exception as exc:  # pragma: no cover
            logger.warning("Skipping unreadable AEF file %s: %s", fp, exc)
            continue
        stack.append(arr)
    if not stack:
        return np.zeros((0, ref.height, ref.width), dtype=np.float32)
    return np.nanmean(np.stack(stack, axis=0), axis=0).astype(np.float32)


# ---------------------------------------------------------------------------
# Labels (train only)
# ---------------------------------------------------------------------------

def list_label_files(paths: Paths, tile_id: str) -> dict[str, list[Path]]:
    """Locate all weak-label rasters for a tile, grouped by source."""
    out: dict[str, list[Path]] = {"gladl": [], "glads2": [], "radd": []}
    root = paths.labels_dir
    if not root.exists():
        return out
    for src in out.keys():
        src_dir = root / src
        if not src_dir.exists():
            continue
        for p in sorted(src_dir.glob(f"{src}_{tile_id}_*")):
            # Skip the alertDate rasters; we only need the binary/severity alerts.
            if "alertDate" in p.name:
                continue
            out[src].append(p)
    return out


def read_label_rasters(paths: Paths, ref: TileRef) -> dict[str, np.ndarray]:
    """Return each source's alert raster resampled (nearest) to the S2 grid.

    Shape per entry: (H, W) uint8 where >0 indicates an alert of any kind.
    """
    out: dict[str, np.ndarray] = {}
    files_by_src = list_label_files(paths, ref.tile_id)
    for src, files in files_by_src.items():
        if not files:
            continue
        merged = np.zeros((ref.height, ref.width), dtype=np.uint8)
        for fp in files:
            try:
                arr = _read_aligned_nearest(fp, ref)
            except Exception as exc:  # pragma: no cover
                logger.warning("Skipping unreadable label %s: %s", fp, exc)
                continue
            merged |= (arr[0] > 0).astype(np.uint8)
        out[src] = merged
    return out


def iter_labels_for_split(paths: Paths, split: str) -> Iterable[str]:
    """Yield tile ids that actually have labels available (train split only)."""
    if split != "train":
        return []
    for tid in list_tile_ids(paths, split):
        files = list_label_files(paths, tid)
        if any(files.values()):
            yield tid
