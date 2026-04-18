"""Run inference on test tiles and write binary GeoTIFF rasters.

The output rasters share the Sentinel-2 grid of each test tile so that
``submission_utils.raster_to_geojson`` can vectorise them and reproject to
EPSG:4326 for the leaderboard.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import rasterio
from tqdm import tqdm

from .config import BINARY_THRESHOLD, PRED_CHUNK_ROWS, Paths
from .data_loader import (
    TileRef,
    list_tile_ids,
    open_tile,
    read_aef_mean,
    read_s1_stack,
    read_s2_stack,
)
from .features import align_feature_matrix, stack_features
from .model import TrainedModel

logger = logging.getLogger(__name__)


def predict_tile(
    paths: Paths,
    tile_id: str,
    model: TrainedModel,
    split: str = "test",
    threshold: float = BINARY_THRESHOLD,
) -> tuple[np.ndarray, TileRef]:
    """Return ``(binary_raster, tile_ref)`` for a single tile."""
    ref: TileRef = open_tile(paths, split, tile_id)
    s2 = read_s2_stack(paths, ref)
    s1 = read_s1_stack(paths, ref)
    aef = read_aef_mean(paths, ref)
    cube, names = stack_features(s2, s1, aef, ref.height, ref.width)
    cube = align_feature_matrix(cube, names, model.feature_names)

    h, w, f = cube.shape
    preds = np.zeros((h, w), dtype=np.float32)

    for start in range(0, h, PRED_CHUNK_ROWS):
        end = min(start + PRED_CHUNK_ROWS, h)
        rows = cube[start:end].reshape(-1, f)
        # HistGradientBoosting accepts NaNs directly.
        proba = model.estimator.predict_proba(rows)[:, 1]
        preds[start:end] = proba.reshape(end - start, w)

    binary = (preds >= threshold).astype(np.uint8)
    return binary, ref


def write_prediction_geotiff(
    binary: np.ndarray,
    ref: TileRef,
    output_path: Path,
) -> Path:
    """Write ``binary`` as a single-band GeoTIFF aligned to ``ref``."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(ref.s2_reference_path) as src:
        profile = src.profile.copy()
    profile.update(
        driver="GTiff",
        dtype="uint8",
        count=1,
        nodata=0,
        compress="lzw",
    )
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(binary, 1)
    return output_path


def predict_all_test_tiles(
    paths: Paths,
    model: TrainedModel,
    out_dir: Path,
    threshold: float = BINARY_THRESHOLD,
) -> list[Path]:
    """Predict every test tile and write per-tile GeoTIFFs. Returns the paths."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tile_ids = list_tile_ids(paths, "test")
    if not tile_ids:
        raise RuntimeError(
            f"No test tiles found under {paths.s2_dir / 'test'}. "
            "Run `make download_data_from_s3` or point --data-dir at your dataset."
        )

    written: list[Path] = []
    for tid in tqdm(tile_ids, desc="Predicting test tiles"):
        binary, ref = predict_tile(paths, tid, model, split="test", threshold=threshold)
        if binary.sum() == 0:
            logger.warning("Tile %s produced 0 positive pixels at threshold %.2f", tid, threshold)
        out_path = out_dir / f"pred_{tid}.tif"
        write_prediction_geotiff(binary, ref, out_path)
        written.append(out_path)
    return written
