"""Per-pixel feature engineering.

Each feature is a **temporal summary** over the stacked Sentinel-1 / Sentinel-2
observations for a tile, concatenated with the mean AEF embedding. Keeping
this simple (summary statistics rather than sequence modelling) makes the
baseline trainable in minutes on a laptop while still exploiting every
modality the challenge provides.

The same feature construction must be applied at train-time and at inference
time, so this module is the single source of truth.
"""

from __future__ import annotations

import numpy as np

from .config import AEF_BANDS, S2_BANDS


# Sentinel-2 band indices inside the 12-band GeoTIFF (1-based in the notebook,
# 0-based here). See challenge.ipynb §3 for the band table.
S2_B04_RED = 3
S2_B08_NIR = 7
S2_B11_SWIR1 = 10
S2_B12_SWIR2 = 11


def _safe_stats(arr: np.ndarray, axis: int = 0) -> tuple[np.ndarray, ...]:
    """NaN-aware mean/std/min/max across ``axis``."""
    with np.errstate(invalid="ignore", all="ignore"):
        mean = np.nanmean(arr, axis=axis)
        std = np.nanstd(arr, axis=axis)
        mn = np.nanmin(arr, axis=axis)
        mx = np.nanmax(arr, axis=axis)
    for a in (mean, std, mn, mx):
        a[~np.isfinite(a)] = 0.0
    return mean, std, mn, mx


def _temporal_trend(arr: np.ndarray) -> np.ndarray:
    """Late-minus-early mean across the time axis; captures directional change.

    Expects shape ``(T, ..., H, W)``. Returns ``(..., H, W)``.
    """
    if arr.shape[0] < 2:
        return np.zeros(arr.shape[1:], dtype=np.float32)
    half = arr.shape[0] // 2
    with np.errstate(invalid="ignore", all="ignore"):
        early = np.nanmean(arr[:half], axis=0)
        late = np.nanmean(arr[half:], axis=0)
    diff = late - early
    diff[~np.isfinite(diff)] = 0.0
    return diff.astype(np.float32)


def compute_s2_features(s2_stack: np.ndarray, h: int, w: int) -> np.ndarray:
    """Compute per-pixel Sentinel-2 features → ``(H, W, F_s2)``."""
    if s2_stack.size == 0:
        return np.zeros((h, w, 0), dtype=np.float32)

    # Aggregate each band over time with mean/std (reduce memory vs min/max too).
    mean, std, _, _ = _safe_stats(s2_stack, axis=0)  # (B, H, W)

    # Vegetation & moisture indices, nan-aware.
    with np.errstate(invalid="ignore", divide="ignore", all="ignore"):
        red = s2_stack[:, S2_B04_RED]
        nir = s2_stack[:, S2_B08_NIR]
        swir1 = s2_stack[:, S2_B11_SWIR1]
        swir2 = s2_stack[:, S2_B12_SWIR2]

        ndvi = (nir - red) / (nir + red + 1e-6)
        nbr = (nir - swir2) / (nir + swir2 + 1e-6)
        ndmi = (nir - swir1) / (nir + swir1 + 1e-6)

    ndvi_mean, ndvi_std, ndvi_min, ndvi_max = _safe_stats(ndvi, axis=0)
    ndvi_trend = _temporal_trend(ndvi)

    nbr_mean, nbr_std, _, _ = _safe_stats(nbr, axis=0)
    nbr_trend = _temporal_trend(nbr)

    ndmi_mean, _, _, _ = _safe_stats(ndmi, axis=0)

    parts = [
        mean,                                                  # (12, H, W)
        std,                                                   # (12, H, W)
        ndvi_mean[None], ndvi_std[None], ndvi_min[None],
        ndvi_max[None], ndvi_trend[None],
        nbr_mean[None], nbr_std[None], nbr_trend[None],
        ndmi_mean[None],
    ]
    feats = np.concatenate(parts, axis=0)  # (F_s2, H, W)
    return np.moveaxis(feats, 0, -1).astype(np.float32)  # (H, W, F_s2)


def compute_s1_features(s1_stack: np.ndarray, h: int, w: int) -> np.ndarray:
    """Per-pixel Sentinel-1 features → ``(H, W, F_s1)``."""
    if s1_stack.size == 0:
        return np.zeros((h, w, 0), dtype=np.float32)

    # s1_stack: (T, 1, H, W) — squeeze the single VV band.
    arr = s1_stack[:, 0]  # (T, H, W)
    mean, std, mn, mx = _safe_stats(arr, axis=0)
    trend = _temporal_trend(arr)
    feats = np.stack([mean, std, mn, mx, trend], axis=0)  # (5, H, W)
    return np.moveaxis(feats, 0, -1).astype(np.float32)


def compute_aef_features(aef_mean: np.ndarray, h: int, w: int) -> np.ndarray:
    """Temporal-mean AEF embedding as feature plane → ``(H, W, F_aef)``."""
    if aef_mean.size == 0:
        return np.zeros((h, w, 0), dtype=np.float32)
    return np.moveaxis(aef_mean, 0, -1).astype(np.float32)


def stack_features(
    s2_stack: np.ndarray,
    s1_stack: np.ndarray,
    aef_mean: np.ndarray,
    h: int,
    w: int,
) -> tuple[np.ndarray, list[str]]:
    """Build the final (H, W, F) feature cube and the feature-name list."""
    s2_feats = compute_s2_features(s2_stack, h, w)
    s1_feats = compute_s1_features(s1_stack, h, w)
    aef_feats = compute_aef_features(aef_mean, h, w)

    s2_names = (
        [f"s2_b{b+1:02d}_mean" for b in range(S2_BANDS)]
        + [f"s2_b{b+1:02d}_std" for b in range(S2_BANDS)]
        + [
            "ndvi_mean", "ndvi_std", "ndvi_min", "ndvi_max", "ndvi_trend",
            "nbr_mean", "nbr_std", "nbr_trend",
            "ndmi_mean",
        ]
    )
    s1_names = ["s1_vv_mean", "s1_vv_std", "s1_vv_min", "s1_vv_max", "s1_vv_trend"]
    aef_names = [f"aef_{b:02d}" for b in range(aef_mean.shape[0] if aef_mean.size else 0)]

    s2_names = s2_names if s2_feats.shape[-1] > 0 else []
    s1_names = s1_names if s1_feats.shape[-1] > 0 else []
    aef_names = aef_names if aef_feats.shape[-1] > 0 else []

    cube = np.concatenate([s2_feats, s1_feats, aef_feats], axis=-1)
    names = s2_names + s1_names + aef_names
    assert cube.shape[-1] == len(names), (cube.shape, len(names))
    return cube, names


def align_feature_matrix(cube: np.ndarray, names: list[str], target_names: list[str]) -> np.ndarray:
    """Reorder/pad ``cube`` so columns match ``target_names`` exactly.

    Missing columns (e.g. a tile has no AEF embedding but the model was
    trained with one) are filled with zero. Extra columns are dropped.
    Input: ``(H, W, F)``. Output: ``(H, W, len(target_names))``.
    """
    h, w, _ = cube.shape
    idx = {n: i for i, n in enumerate(names)}
    out = np.zeros((h, w, len(target_names)), dtype=np.float32)
    for j, tn in enumerate(target_names):
        i = idx.get(tn)
        if i is not None:
            out[..., j] = cube[..., i]
    return out
