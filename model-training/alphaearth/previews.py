"""PCA-3 false-color previews + arbitrary band composites for AEF tiles."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image
from sklearn.decomposition import PCA

from . import cache
from .io import TileRaster, open_aef_tile, valid_pixel_mask
from .paths import Paths


_PREVIEW_MAX_SIZE = 1024


def _downsample(arr: np.ndarray, max_size: int = _PREVIEW_MAX_SIZE) -> np.ndarray:
    """Downsample a (C, H, W) float32 array so max(H, W) <= max_size.

    Uses simple block-mean averaging to avoid pulling in scipy/skimage just
    for this. Preserves NaNs (any block containing NaN stays NaN).
    """

    c, h, w = arr.shape
    scale = max(1, int(np.ceil(max(h, w) / max_size)))
    if scale == 1:
        return arr
    new_h = h // scale
    new_w = w // scale
    if new_h == 0 or new_w == 0:
        return arr
    cropped = arr[:, : new_h * scale, : new_w * scale]
    reshaped = cropped.reshape(c, new_h, scale, new_w, scale)
    # nanmean preserves NaN-only blocks as NaN; suppress the all-NaN warning.
    with np.errstate(invalid="ignore"):
        out = np.nanmean(reshaped, axis=(2, 4))
    return out.astype(np.float32, copy=False)


def _normalise_to_uint8(channel: np.ndarray) -> np.ndarray:
    """Stretch one channel to [0, 255] uint8, mapping NaN to 0."""

    finite_mask = np.isfinite(channel)
    if not finite_mask.any():
        return np.zeros_like(channel, dtype=np.uint8)
    finite_vals = channel[finite_mask]
    lo, hi = float(finite_vals.min()), float(finite_vals.max())
    span = max(hi - lo, 1e-8)
    out = np.where(finite_mask, np.clip((channel - lo) / span, 0.0, 1.0), 0.0)
    return np.clip(np.round(out * 255.0), 0, 255).astype(np.uint8)


def _alpha_from_finite(rgb: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Add an alpha channel: opaque where the source pixel was valid."""

    alpha = np.where(valid, 255, 0).astype(np.uint8)
    rgba = np.dstack([rgb, alpha])
    return rgba


def render_pca_preview(
    tile: TileRaster,
    *,
    max_size: int = _PREVIEW_MAX_SIZE,
) -> np.ndarray:
    """Return an (H, W, 4) uint8 RGBA PNG of the tile in PCA-3 false colour."""

    arr = _downsample(tile.array, max_size=max_size)
    c, h, w = arr.shape
    flat = arr.reshape(c, -1).T.astype(np.float32, copy=False)
    valid_pixels = np.isfinite(flat).all(axis=1)
    rgb = np.zeros((flat.shape[0], 3), dtype=np.uint8)
    if valid_pixels.any():
        components = min(3, c)
        proj = PCA(n_components=components, random_state=42).fit_transform(flat[valid_pixels])
        if components < 3:
            pad = np.zeros((proj.shape[0], 3 - components), dtype=proj.dtype)
            proj = np.concatenate([proj, pad], axis=1)
        lo = proj.min(axis=0, keepdims=True)
        hi = proj.max(axis=0, keepdims=True)
        scaled = (proj - lo) / np.maximum(hi - lo, 1e-8)
        rgb[valid_pixels] = np.clip(np.round(scaled * 255.0), 0, 255).astype(np.uint8)
    rgb = rgb.reshape(h, w, 3)
    return _alpha_from_finite(rgb, valid_pixels.reshape(h, w))


def render_band_composite(
    tile: TileRaster,
    bands: Iterable[int],
    *,
    mode: str = "rgb",
    max_size: int = _PREVIEW_MAX_SIZE,
) -> np.ndarray:
    """Return an (H, W, 4) RGBA composite using the supplied band indices.

    `mode='rgb'` expects three bands; `mode='gray'` expects one (and the same
    grayscale value is written to R, G, B).
    """

    bands = list(bands)
    n = tile.n_bands
    for b in bands:
        if not (0 <= b < n):
            raise ValueError(f"Band {b} out of range [0, {n - 1}]")
    arr = _downsample(tile.array, max_size=max_size)
    valid_pixels = np.isfinite(arr).all(axis=0)
    if mode == "gray":
        if len(bands) != 1:
            raise ValueError("mode='gray' requires exactly one band")
        gray = _normalise_to_uint8(arr[bands[0]])
        rgb = np.dstack([gray, gray, gray])
    elif mode == "rgb":
        if len(bands) != 3:
            raise ValueError("mode='rgb' requires exactly three bands")
        chans = [_normalise_to_uint8(arr[b]) for b in bands]
        rgb = np.dstack(chans)
    else:
        raise ValueError(f"Unknown mode {mode!r}")
    return _alpha_from_finite(rgb, valid_pixels)


def write_png(rgba: np.ndarray, dest: Path) -> Path:
    cache.ensure_dir(dest.parent)
    img = Image.fromarray(rgba, mode="RGBA")
    img.save(dest, format="PNG", optimize=True)
    return dest


def cached_pca_preview(
    paths: Paths,
    cache_root: Path,
    tile: str,
    year: int,
    split: str,
    *,
    max_size: int = _PREVIEW_MAX_SIZE,
    refresh: bool = False,
) -> Path:
    """Get-or-create a cached PCA-3 PNG and return its path."""

    out = cache.previews_dir(cache_root) / f"{tile}_{year}_{split}_max{max_size}.png"
    if out.exists() and not refresh:
        return out
    raster = open_aef_tile(paths, tile, year, split)
    rgba = render_pca_preview(raster, max_size=max_size)
    return write_png(rgba, out)


def cached_band_composite(
    paths: Paths,
    cache_root: Path,
    tile: str,
    year: int,
    split: str,
    bands: tuple[int, ...],
    mode: str,
    *,
    max_size: int = _PREVIEW_MAX_SIZE,
    refresh: bool = False,
) -> Path:
    band_str = "-".join(str(b) for b in bands)
    out = cache.bands_dir(cache_root) / (
        f"{tile}_{year}_{split}_{mode}_{band_str}_max{max_size}.png"
    )
    if out.exists() and not refresh:
        return out
    raster = open_aef_tile(paths, tile, year, split)
    rgba = render_band_composite(raster, bands, mode=mode, max_size=max_size)
    return write_png(rgba, out)


def channel_stats(tile: TileRaster) -> list[dict]:
    """Per-band {min, max, mean, std, validFraction} (length == n_bands)."""

    out: list[dict] = []
    for i in range(tile.n_bands):
        chan = tile.array[i]
        finite_mask = np.isfinite(chan)
        finite = chan[finite_mask]
        valid_fraction = float(finite_mask.mean())
        if finite.size == 0:
            out.append(
                {
                    "dim": i,
                    "min": None,
                    "max": None,
                    "mean": None,
                    "std": None,
                    "validFraction": valid_fraction,
                }
            )
            continue
        out.append(
            {
                "dim": i,
                "min": float(finite.min()),
                "max": float(finite.max()),
                "mean": float(finite.mean()),
                "std": float(finite.std()),
                "validFraction": valid_fraction,
            }
        )
    return out
