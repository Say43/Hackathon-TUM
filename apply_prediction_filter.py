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


def filter_mask(
    mask: np.ndarray,
    cloud_mask: np.ndarray | None = None,
    opening_size: int = 2,
    closing_size: int = 2,
    min_component_size: int = 64,
) -> np.ndarray:
    binary = mask > 0
    if cloud_mask is not None:
        binary = binary & ~cloud_mask

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
    if data_dir is not None:
        s2_path = find_latest_s2_scene(data_dir, tile_id, split=split)
        if s2_path is not None:
            cloud_mask = derive_cloud_mask_from_s2(s2_path, target_shape=arr.shape)

    filtered = filter_mask(
        arr,
        cloud_mask=cloud_mask,
        opening_size=opening_size,
        closing_size=closing_size,
        min_component_size=min_component_size,
    )

    profile.update(count=1, dtype=rasterio.uint8, compress="lzw")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(filtered, 1)
    diagnostics = {
        "tile_id": tile_id,
        "s2_scene": str(s2_path) if s2_path is not None else None,
        "positive_before": int((arr > 0).sum()),
        "positive_after_cloud": int(((arr > 0) & ~cloud_mask).sum()) if cloud_mask is not None else int((arr > 0).sum()),
        "positive_after_filter": int((filtered > 0).sum()),
        "cloud_pixels": int(cloud_mask.sum()) if cloud_mask is not None else 0,
        "cloud_suppressed_positive_pixels": int(((arr > 0) & cloud_mask).sum()) if cloud_mask is not None else 0,
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
