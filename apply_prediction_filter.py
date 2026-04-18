import argparse
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from scipy import ndimage


def remove_small_components(mask: np.ndarray, min_size: int) -> np.ndarray:
    labeled, num_features = ndimage.label(mask)
    if num_features == 0:
        return mask

    component_sizes = np.bincount(labeled.ravel())
    keep = component_sizes >= min_size
    keep[0] = False
    return keep[labeled]


def extract_tile_id(prediction_path: Path) -> str:
    stem = prediction_path.stem
    if stem.startswith("pred_"):
        return stem[len("pred_") :]
    return stem


def find_latest_s2_scene(data_dir: Path, tile_id: str, split: str = "test") -> Path | None:
    s2_dir = data_dir / "sentinel-2" / split / f"{tile_id}__s2_l2a"
    if not s2_dir.exists():
        return None
    scenes = sorted(s2_dir.glob("*.tif"))
    return scenes[-1] if scenes else None


def list_s2_scenes(data_dir: Path, tile_id: str, split: str = "test") -> list[Path]:
    s2_dir = data_dir / "sentinel-2" / split / f"{tile_id}__s2_l2a"
    if not s2_dir.exists():
        return []
    return sorted(s2_dir.glob("*.tif"))


def _normalize_band(band: np.ndarray) -> np.ndarray:
    band = band.astype(np.float32)
    valid = np.isfinite(band) & (band > 0)
    if not np.any(valid):
        return np.zeros_like(band, dtype=np.float32)
    lo, hi = np.percentile(band[valid], [2, 98])
    if hi <= lo:
        return np.zeros_like(band, dtype=np.float32)
    return np.clip((band - lo) / (hi - lo + 1e-6), 0, 1)


def derive_cloud_mask_from_s2(
    s2_path: Path,
    target_shape: tuple[int, int] | None = None,
) -> np.ndarray:
    with rasterio.open(s2_path) as src:
        read_kwargs = {}
        if target_shape is not None:
            read_kwargs = {
                "out_shape": (target_shape[0], target_shape[1]),
                "resampling": Resampling.bilinear,
            }

        blue = src.read(2, **read_kwargs)
        green = src.read(3, **read_kwargs)
        red = src.read(4, **read_kwargs)
        nir = src.read(8, **read_kwargs)
        cirrus = src.read(10, **read_kwargs)
        swir1 = src.read(11, **read_kwargs)
        aerosol = src.read(1, **read_kwargs)

    blue_n = _normalize_band(blue)
    green_n = _normalize_band(green)
    red_n = _normalize_band(red)
    nir_n = _normalize_band(nir)
    cirrus_n = _normalize_band(cirrus)
    swir_n = _normalize_band(swir1)
    aerosol_n = _normalize_band(aerosol)

    vis_mean = (blue_n + green_n + red_n) / 3.0
    whiteness = 1.0 - (
        (np.abs(blue_n - green_n) + np.abs(green_n - red_n) + np.abs(blue_n - red_n)) / 3.0
    )
    ndvi = (nir_n - red_n) / (nir_n + red_n + 1e-6)

    cloud_core = (cirrus_n > 0.35) & (vis_mean > 0.45) & (whiteness > 0.72)
    bright_haze = (aerosol_n > 0.35) & (blue_n > 0.45) & (ndvi < 0.25)
    cold_bright = (swir_n > 0.25) & (vis_mean > 0.55) & (whiteness > 0.68) & (ndvi < 0.35)

    cloud_mask = cloud_core | bright_haze | cold_bright
    cloud_mask = ndimage.binary_opening(cloud_mask, structure=np.ones((2, 2), dtype=bool))
    cloud_mask = ndimage.binary_closing(cloud_mask, structure=np.ones((3, 3), dtype=bool))
    return cloud_mask.astype(bool)


def derive_temporal_consistency_mask(
    s2_paths: list[Path],
    target_shape: tuple[int, int],
    min_support: int = 2,
) -> np.ndarray | None:
    if len(s2_paths) < 2:
        return None

    ndvi_series: list[np.ndarray] = []
    valid_series: list[np.ndarray] = []

    for s2_path in s2_paths:
        with rasterio.open(s2_path) as src:
            read_kwargs = {
                "out_shape": (target_shape[0], target_shape[1]),
                "resampling": Resampling.bilinear,
            }
            red = src.read(4, **read_kwargs).astype(np.float32)
            nir = src.read(8, **read_kwargs).astype(np.float32)

        valid = np.isfinite(red) & np.isfinite(nir) & (red > 0) & (nir > 0)
        ndvi = np.full(target_shape, np.nan, dtype=np.float32)
        ndvi[valid] = (nir[valid] - red[valid]) / (nir[valid] + red[valid] + 1e-6)
        ndvi_series.append(ndvi)
        valid_series.append(valid)

    ndvi_stack = np.stack(ndvi_series, axis=0)
    valid_stack = np.stack(valid_series, axis=0)

    low_vegetation = np.where(valid_stack, ndvi_stack < 0.42, False)

    running_max = np.maximum.accumulate(np.where(np.isfinite(ndvi_stack), ndvi_stack, -1.0), axis=0)
    drop_from_best = np.where(np.isfinite(ndvi_stack), running_max - ndvi_stack, 0.0)
    sudden_drop = np.where(valid_stack, drop_from_best > 0.18, False)

    month_to_month_drop = np.zeros_like(ndvi_stack, dtype=bool)
    if ndvi_stack.shape[0] >= 2:
        delta = ndvi_stack[:-1] - ndvi_stack[1:]
        valid_delta = valid_stack[:-1] & valid_stack[1:]
        month_to_month_drop[1:] = np.where(valid_delta, delta > 0.12, False)

    support_count = (
        low_vegetation.astype(np.uint8)
        + sudden_drop.astype(np.uint8)
        + month_to_month_drop.astype(np.uint8)
    )
    support_count = np.sum(support_count > 0, axis=0)

    temporal_mask = support_count >= min_support
    temporal_mask = ndimage.binary_opening(temporal_mask, structure=np.ones((2, 2), dtype=bool))
    temporal_mask = ndimage.binary_closing(temporal_mask, structure=np.ones((3, 3), dtype=bool))
    return temporal_mask.astype(bool)


def derive_proxy_confidence(
    mask: np.ndarray,
    cloud_mask: np.ndarray | None = None,
    temporal_mask: np.ndarray | None = None,
    probability_map: np.ndarray | None = None,
) -> np.ndarray:
    if probability_map is not None:
        return np.clip(probability_map.astype(np.float32), 0.0, 1.0)

    binary = (mask > 0).astype(np.float32)
    local_density = ndimage.uniform_filter(binary, size=9, mode="nearest")
    confidence = 0.55 * binary + 0.45 * np.clip(local_density * 1.8, 0.0, 1.0)

    if temporal_mask is not None:
        confidence += 0.2 * temporal_mask.astype(np.float32)
    if cloud_mask is not None:
        confidence -= 0.35 * cloud_mask.astype(np.float32)

    confidence *= binary
    return np.clip(confidence, 0.0, 1.0)


def filter_mask(
    mask: np.ndarray,
    cloud_mask: np.ndarray | None = None,
    temporal_mask: np.ndarray | None = None,
    confidence_map: np.ndarray | None = None,
    confidence_threshold: float = 0.55,
    opening_size: int = 2,
    closing_size: int = 2,
    min_component_size: int = 64,
) -> np.ndarray:
    binary = mask > 0
    if cloud_mask is not None:
        binary = binary & ~cloud_mask
    if temporal_mask is not None:
        binary = binary & temporal_mask
    if confidence_map is not None:
        binary = binary & (confidence_map >= confidence_threshold)

    structure = np.ones((opening_size, opening_size), dtype=bool)
    opened = ndimage.binary_opening(binary, structure=structure)

    structure = np.ones((closing_size, closing_size), dtype=bool)
    closed = ndimage.binary_closing(opened, structure=structure)

    filtered = remove_small_components(closed, min_component_size)
    return filtered.astype(np.uint8)


def filter_raster(
    input_path: Path,
    output_path: Path,
    data_dir: Path | None = None,
    split: str = "test",
    opening_size: int = 2,
    closing_size: int = 2,
    min_component_size: int = 64,
) -> tuple[Path, dict[str, int | str | None]]:
    with rasterio.open(input_path) as src:
        arr = src.read(1, out_dtype=np.uint8, resampling=Resampling.nearest)
        profile = src.profile.copy()

    tile_id = extract_tile_id(input_path)
    cloud_mask = None
    s2_path = None
    temporal_mask = None
    s2_paths: list[Path] = []
    confidence_map = None
    if data_dir is not None:
        s2_path = find_latest_s2_scene(data_dir, tile_id, split=split)
        s2_paths = list_s2_scenes(data_dir, tile_id, split=split)
        if s2_path is not None:
            cloud_mask = derive_cloud_mask_from_s2(s2_path, target_shape=arr.shape)
        temporal_mask = derive_temporal_consistency_mask(s2_paths, target_shape=arr.shape)
    confidence_map = derive_proxy_confidence(arr, cloud_mask=cloud_mask, temporal_mask=temporal_mask)

    filtered = filter_mask(
        arr,
        cloud_mask=cloud_mask,
        temporal_mask=temporal_mask,
        confidence_map=confidence_map,
        confidence_threshold=0.55,
        opening_size=opening_size,
        closing_size=closing_size,
        min_component_size=min_component_size,
    )

    profile.update(count=1, dtype=rasterio.uint8, compress="lzw")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(filtered, 1)
    positive_before = arr > 0
    positive_after_cloud_mask = positive_before & ~cloud_mask if cloud_mask is not None else positive_before
    positive_after_temporal_mask = (
        positive_after_cloud_mask & temporal_mask if temporal_mask is not None else positive_after_cloud_mask
    )
    positive_after_confidence_mask = positive_after_temporal_mask & (confidence_map >= 0.55)

    diagnostics = {
        "tile_id": tile_id,
        "s2_scene": str(s2_path) if s2_path is not None else None,
        "s2_scene_count": len(s2_paths),
        "positive_before": int(positive_before.sum()),
        "positive_after_cloud": int(positive_after_cloud_mask.sum()),
        "positive_after_temporal": int(positive_after_temporal_mask.sum()),
        "positive_after_confidence": int(positive_after_confidence_mask.sum()),
        "positive_after_filter": int((filtered > 0).sum()),
        "cloud_pixels": int(cloud_mask.sum()) if cloud_mask is not None else 0,
        "temporal_support_pixels": int(temporal_mask.sum()) if temporal_mask is not None else 0,
        "mean_proxy_confidence": float(confidence_map[positive_before].mean()) if np.any(positive_before) else 0.0,
        "cloud_suppressed_positive_pixels": int((positive_before & cloud_mask).sum()) if cloud_mask is not None else 0,
        "temporally_suppressed_positive_pixels": int((positive_after_cloud_mask & ~temporal_mask).sum()) if temporal_mask is not None else 0,
        "confidence_suppressed_positive_pixels": int((positive_after_temporal_mask & ~(confidence_map >= 0.55)).sum()),
    }
    return output_path, diagnostics


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply cloud-aware and morphological filtering to a prediction GeoTIFF.")
    parser.add_argument("--input", required=True, help="Input prediction GeoTIFF")
    parser.add_argument("--output", required=True, help="Output filtered GeoTIFF")
    parser.add_argument("--data-dir", help="Challenge dataset root for locating Sentinel-2 time series")
    parser.add_argument("--split", default="test", choices=["train", "test"])
    parser.add_argument("--opening-size", type=int, default=2)
    parser.add_argument("--closing-size", type=int, default=2)
    parser.add_argument("--min-component-size", type=int, default=64)
    args = parser.parse_args()

    _, diagnostics = filter_raster(
        Path(args.input),
        Path(args.output),
        data_dir=Path(args.data_dir) if args.data_dir else None,
        split=args.split,
        opening_size=args.opening_size,
        closing_size=args.closing_size,
        min_component_size=args.min_component_size,
    )
    print(diagnostics)


if __name__ == "__main__":
    main()
