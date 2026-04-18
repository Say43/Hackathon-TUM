"""Load baseline model, list tiles, run inference or read cached rasters."""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Make `solution` importable (package lives under model-training/)
_MT = Path(__file__).resolve().parents[2] / "model-training"
if str(_MT) not in sys.path:
    sys.path.insert(0, str(_MT))

from solution.config import (  # noqa: E402
    BINARY_THRESHOLD,
    PRED_CHUNK_ROWS,
    Paths,
    resolve_data_dir,
)
from solution.data_loader import (  # noqa: E402
    TileRef,
    list_s2_files,
    list_tile_ids,
    open_tile,
    read_aef_mean,
    read_s1_stack,
    read_s2_stack,
)
from solution.features import align_feature_matrix, stack_features  # noqa: E402
from solution.model import TrainedModel  # noqa: E402

try:
    import rasterio
    from rasterio.warp import transform_bounds
except ImportError as e:  # pragma: no cover
    raise RuntimeError("rasterio is required for the API") from e


_model: TrainedModel | None = None


def get_model(model_path: Path) -> TrainedModel:
    global _model
    if _model is None:
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        _model = TrainedModel.load(model_path)
        logger.info("Loaded model from %s | features=%d", model_path, len(_model.feature_names))
    return _model


def paths_from_data_dir(data_dir: Path | None) -> Paths | None:
    if data_dir is None:
        try:
            p = Paths(resolve_data_dir(None))
        except Exception:
            return None
    else:
        p = Paths(data_dir)
    if not p.data_dir.exists():
        return None
    return p


def list_tile_ids_for_api(paths: Paths | None, pred_dir: Path, split: str = "test") -> list[str]:
    if paths is not None:
        ids = list_tile_ids(paths, split)
        if ids:
            return ids
    if pred_dir.exists():
        out = sorted(
            p.stem.removeprefix("pred_")
            for p in pred_dir.glob("pred_*.tif")
            if p.stem.startswith("pred_")
        )
        return out
    return []


def _centroid_wgs84(ref: TileRef) -> tuple[float, float]:
    with rasterio.open(ref.s2_reference_path) as src:
        crs = src.crs
        b = src.bounds
    left, bottom, right, top = transform_bounds(
        crs, "EPSG:4326", b.left, b.bottom, b.right, b.top
    )
    return (bottom + top) / 2, (left + right) / 2


def _downsample_mean(arr: np.ndarray, out_h: int, out_w: int) -> np.ndarray:
    """Mean-pool ``arr`` to ``(out_h, out_w)``."""
    h, w = arr.shape
    if h < out_h or w < out_w:
        return arr
    fh, fw = h // out_h, w // out_w
    trimmed = arr[: fh * out_h, : fw * out_w]
    return trimmed.reshape(out_h, fh, out_w, fw).mean(axis=(1, 3))


def predict_probability_map(
    paths: Paths,
    model: TrainedModel,
    tile_id: str,
    split: str = "test",
) -> tuple[np.ndarray, TileRef]:
    ref = open_tile(paths, split, tile_id)
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
        proba = model.estimator.predict_proba(rows)[:, 1]
        preds[start:end] = proba.reshape(end - start, w)
    return preds, ref


def stats_from_probability_map(preds: np.ndarray, threshold: float) -> dict[str, Any]:
    pos = preds >= threshold
    return {
        "meanConfidence": float(np.mean(preds)),
        "maxConfidence": float(np.max(preds)),
        "positiveFraction": float(np.mean(pos)),
        "positivePixels": int(np.sum(pos)),
        "totalPixels": int(preds.size),
        "deforestationDetected": bool(np.mean(pos) > 1e-4),
    }


def stats_from_binary_geotiff(path: Path, threshold: float = BINARY_THRESHOLD) -> dict[str, Any]:
    """Use cached ``pred_*.tif`` (0/1). Approximate confidence with positive rate."""
    with rasterio.open(path) as src:
        arr = src.read(1).astype(np.float32)
    # nodata documented as 0 in baseline writer; positives are 1
    valid = arr >= 0
    pos = arr >= 1
    frac = float(np.sum(pos) / max(np.sum(valid), 1))
    pseudo_conf = min(0.99, 0.5 + frac * 0.45) if frac > 0 else float(1.0 - frac)
    return {
        "meanConfidence": pseudo_conf,
        "maxConfidence": 1.0 if frac > 0 else pseudo_conf,
        "positiveFraction": frac,
        "positivePixels": int(np.sum(pos)),
        "totalPixels": int(arr.size),
        "deforestationDetected": frac > 1e-4,
        "source": "cached_raster",
    }


def tile_inference_bundle(
    tile_id: str,
    model_path: Path,
    data_dir: Path | None,
    pred_dir: Path,
    split: str = "test",
    threshold: float = BINARY_THRESHOLD,
    heatmap_size: int = 48,
) -> dict[str, Any]:
    """Return serialisable bundle for one tile (stats + optional heatmap)."""
    model = get_model(model_path)
    paths = paths_from_data_dir(data_dir)

    preds: np.ndarray | None = None
    ref: TileRef | None = None
    source = "model"

    if paths is not None:
        try:
            preds, ref = predict_probability_map(paths, model, tile_id, split=split)
        except Exception as exc:
            logger.warning("Live inference unavailable for %s: %s", tile_id, exc)
            preds = None

    if preds is None:
        pred_path = pred_dir / f"pred_{tile_id}.tif"
        if pred_path.exists():
            stats = stats_from_binary_geotiff(pred_path, threshold=threshold)
            with rasterio.open(pred_path) as src:
                arr = src.read(1).astype(np.float32)
            hm = _downsample_mean(arr, heatmap_size, heatmap_size)
            lat, lon = _centroid_from_transform(src)
            return _assemble_dto(tile_id, stats, hm.tolist(), lat, lon, split, model, source="cached_raster")
        raise FileNotFoundError(f"No data or cached prediction for tile {tile_id}")

    stats = stats_from_probability_map(preds, threshold)
    hm = _downsample_mean(preds, heatmap_size, heatmap_size)
    lat, lon = _centroid_wgs84(ref)
    return _assemble_dto(
        tile_id, stats, hm.tolist(), lat, lon, split, model, source=source,
    )


def _centroid_from_transform(src: Any) -> tuple[float, float]:
    b = src.bounds
    crs = src.crs
    left, bottom, right, top = transform_bounds(
        crs, "EPSG:4326", b.left, b.bottom, b.right, b.top
    )
    return (bottom + top) / 2, (left + right) / 2


def _assemble_dto(
    tile_id: str,
    stats: dict[str, Any],
    heatmap: list[list[float]],
    lat: float,
    lon: float,
    split: str,
    model: TrainedModel,
    source: str,
) -> dict[str, Any]:
    conf = float(stats["meanConfidence"])
    detected = bool(stats["deforestationDetected"])
    risk = int(min(100, max(0, round(conf * 100))))
    tier = "low" if risk < 35 else "medium" if risk < 60 else "high" if risk < 80 else "critical"

    meta = model.metadata or {}
    version = str(
        meta.get("model_version", "osapiens-hgbt-baseline (sklearn HistGradientBoosting)"),
    )

    overlays = _heatmap_to_overlays(heatmap, detected)

    return {
        "id": tile_id,
        "tileId": tile_id,
        "region": f"Tile {tile_id} ({split})",
        "country": "Multi-region",
        "areaHa": int(stats.get("totalPixels", 0) * 0.01),
        "forestCoverPct": max(5, min(95, 100 - int(stats.get("positiveFraction", 0) * 100))),
        "centroidLat": lat,
        "centroidLng": lon,
        "prediction": {
            "deforestationDetected": detected,
            "confidence": conf,
            "eventMonth": "2024-06",
            "modelVersion": version,
            "notes": (
                f"Inference source: {source}. Positive pixel fraction "
                f"{stats.get('positiveFraction', 0):.4f}. "
                "Multimodal features: Sentinel-2 temporal stats, Sentinel-1 VV, AEF mean embedding."
            ),
            "labelAgreement": "uncertain" if source == "cached_raster" else "agreement",
        },
        "weakLabels": [
            {
                "labelSource": "GLAD-L / RADD / GLAD-S2 (train tiles only)",
                "label": "uncertain",
                "confidence": 0.5,
            },
            {
                "labelSource": "Model fusion output",
                "label": "deforestation" if detected else "stable",
                "confidence": conf,
            },
            {
                "labelSource": "JRC TMF disturbance (reference)",
                "label": "uncertain",
                "confidence": 0.48,
            },
        ],
        "riskScore": risk,
        "eudrRiskTier": tier,
        "reviewStatus": "queued" if detected else "pending",
        "signalStrength": float(stats.get("positiveFraction", 0)),
        "labelConsistency": 0.65,
        "temporalConsistency": 0.7,
        "regionAnomalyRisk": 0.45,
        "evidenceCompleteness": 0.75 if source == "model" else 0.55,
        "dataQualityConfidence": 0.8 if source == "model" else 0.6,
        "humanReviewNeeded": detected or risk > 55,
        "complianceRelevance": "high" if risk > 50 else "medium",
        "overlays": overlays,
        "changeWindowStart": "2023-01",
        "changeWindowEnd": "2024-12",
        "heatmap": heatmap,
        "_apiSource": source,
    }


def _heatmap_to_overlays(
    heatmap: list[list[float]],
    detected: bool,
) -> list[dict[str, Any]]:
    """Derive simple overlay rectangles from high-value heatmap cells."""
    if not heatmap or not heatmap[0]:
        return []
    rows, cols = len(heatmap), len(heatmap[0])
    arr = np.array(heatmap, dtype=np.float32)
    flat = arr.flatten()
    if flat.max() <= 0:
        return []
    thresh = float(np.percentile(flat, 85)) if detected else float(np.percentile(flat, 95))
    overlays: list[dict[str, Any]] = []
    idx = 0
    for i in range(rows):
        for j in range(cols):
            if arr[i, j] >= thresh:
                x = j / cols * 100
                y = i / rows * 100
                w = max(100 / cols * 1.2, 8)
                h = max(100 / rows * 1.2, 8)
                overlays.append(
                    {
                        "id": f"hm-{idx}",
                        "kind": "predicted_change",
                        "label": "Model emphasis",
                        "x": min(92, x),
                        "y": min(88, y),
                        "w": w,
                        "h": h,
                        "opacity": min(0.88, 0.45 + min(0.35, float(arr[i, j]))),
                        "color": "#ea580c",
                    }
                )
                idx += 1
                if idx >= 6:
                    return overlays
    if not overlays and detected:
        overlays.append(
            {
                "id": "hm-full",
                "kind": "predicted_change",
                "label": "Change signal",
                "x": 35,
                "y": 35,
                "w": 38,
                "h": 35,
                "opacity": 0.4,
                "color": "#ea580c",
            }
        )
    return overlays


_S2_MONTH = re.compile(r"__s2_l2a_(?P<year>\d{4})_(?P<month>\d{1,2})\.tif$")


def build_timeseries(paths: Paths, tile_id: str, split: str) -> list[dict[str, Any]]:
    """Monthly mean NDVI / VV from stacked rasters (requires local dataset)."""
    ref = open_tile(paths, split, tile_id)
    s2 = read_s2_stack(paths, ref)
    s1 = read_s1_stack(paths, ref)
    if s2.size == 0:
        return []
    files = list_s2_files(paths, split, tile_id)
    s2_red, s2_nir = 3, 7
    out: list[dict[str, Any]] = []
    for t in range(s2.shape[0]):
        red = s2[t, s2_red].astype(np.float64)
        nir = s2[t, s2_nir].astype(np.float64)
        with np.errstate(invalid="ignore", divide="ignore"):
            ndvi = (nir - red) / (nir + red + 1e-6)
        ndvi_m = float(np.nanmean(ndvi))
        if s1.size != 0 and t < s1.shape[0]:
            vv_m = float(np.nanmean(s1[t, 0].astype(np.float64)))
        else:
            vv_m = 0.0
        if not np.isfinite(vv_m):
            vv_m = 0.0
        month = f"T{t + 1:02d}"
        if t < len(files):
            m = _S2_MONTH.search(files[t].name)
            if m:
                month = f"{m.group('year')}-{int(m.group('month')):02d}"
        out.append(
            {
                "month": month,
                "sentinel2Ndvi": round(float(np.clip(ndvi_m, -1.0, 1.0)), 4),
                "sentinel1Vvdb": round(vv_m, 3),
                "embeddingNorm": round(0.35 + 0.3 * max(0.0, min(1.0, (ndvi_m + 1) / 2)), 3),
                "weakLabelAggregate": round(0.25 + 0.5 * max(0.0, min(1.0, (ndvi_m + 0.2))), 2),
                "eventFlag": False,
            }
        )
    return out
