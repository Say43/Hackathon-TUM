"""Turn per-tile prediction rasters into leaderboard-ready GeoJSON files.

Uses the repository-provided :func:`submission_utils.raster_to_geojson` so we
stay consistent with the challenge spec (binary raster → EPSG:4326 polygons,
area filter in hectares).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from submission_utils import raster_to_geojson

from .config import MIN_AREA_HA

logger = logging.getLogger(__name__)


def rasters_to_geojsons(
    prediction_rasters: list[Path],
    out_dir: Path,
    min_area_ha: float = MIN_AREA_HA,
) -> list[Path]:
    """Convert every prediction raster into its own GeoJSON file."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for raster_path in prediction_rasters:
        tile_id = raster_path.stem.replace("pred_", "")
        out_path = out_dir / f"{tile_id}.geojson"
        try:
            raster_to_geojson(raster_path, output_path=out_path, min_area_ha=min_area_ha)
            written.append(out_path)
        except ValueError as exc:
            # No positive pixels or everything filtered out – skip but keep going.
            logger.warning("Skipping %s: %s", raster_path, exc)
    return written


def merge_geojsons(
    tile_geojsons: list[Path],
    output_path: Path,
) -> Path:
    """Concatenate per-tile FeatureCollections into a single submission file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    features: list[dict] = []
    for fp in tile_geojsons:
        with open(fp) as f:
            gj = json.load(f)
        tile_id = fp.stem
        for feat in gj.get("features", []):
            props = feat.setdefault("properties", {})
            props.setdefault("tile_id", tile_id)
            features.append(feat)

    merged = {"type": "FeatureCollection", "features": features}
    with open(output_path, "w") as f:
        json.dump(merged, f)
    logger.info("Wrote merged submission with %d features → %s", len(features), output_path)
    return output_path
