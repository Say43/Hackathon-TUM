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


def filter_mask(
    mask: np.ndarray,
    opening_size: int = 2,
    closing_size: int = 2,
    min_component_size: int = 64,
) -> np.ndarray:
    binary = mask > 0
    structure = np.ones((opening_size, opening_size), dtype=bool)
    opened = ndimage.binary_opening(binary, structure=structure)

    structure = np.ones((closing_size, closing_size), dtype=bool)
    closed = ndimage.binary_closing(opened, structure=structure)

    filtered = remove_small_components(closed, min_component_size)
    return filtered.astype(np.uint8)


def filter_raster(
    input_path: Path,
    output_path: Path,
    opening_size: int = 2,
    closing_size: int = 2,
    min_component_size: int = 64,
) -> Path:
    with rasterio.open(input_path) as src:
        arr = src.read(1, out_dtype=np.uint8, resampling=Resampling.nearest)
        profile = src.profile.copy()

    filtered = filter_mask(
        arr,
        opening_size=opening_size,
        closing_size=closing_size,
        min_component_size=min_component_size,
    )

    profile.update(count=1, dtype=rasterio.uint8, compress="lzw")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(filtered, 1)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply a simple morphological filter to a prediction GeoTIFF.")
    parser.add_argument("--input", required=True, help="Input prediction GeoTIFF")
    parser.add_argument("--output", required=True, help="Output filtered GeoTIFF")
    parser.add_argument("--opening-size", type=int, default=2)
    parser.add_argument("--closing-size", type=int, default=2)
    parser.add_argument("--min-component-size", type=int, default=64)
    args = parser.parse_args()

    filter_raster(
        Path(args.input),
        Path(args.output),
        opening_size=args.opening_size,
        closing_size=args.closing_size,
        min_component_size=args.min_component_size,
    )


if __name__ == "__main__":
    main()
