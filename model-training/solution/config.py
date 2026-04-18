"""Central configuration for the baseline solution.

The dataset root can be configured in three ways (highest priority first):

1. Explicit ``--data-dir`` CLI argument passed to ``run_solution.py``.
2. Environment variable ``MAKEATHON_DATA_DIR``.
3. The default ``./data/makeathon-challenge`` (standard path produced by
   ``make download_data_from_s3``).

Every module in ``solution/`` reads its paths via :class:`Paths` so you only
set the dataset location once.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DATA_DIR = Path("./data/makeathon-challenge")


def resolve_data_dir(cli_value: str | None = None) -> Path:
    """Return the dataset root, checking CLI > env > default."""
    if cli_value:
        return Path(cli_value).expanduser().resolve()
    env = os.environ.get("MAKEATHON_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return DEFAULT_DATA_DIR.resolve()


@dataclass(frozen=True)
class Paths:
    """Strongly-typed view of the dataset layout documented in the README."""

    data_dir: Path

    @property
    def s1_dir(self) -> Path:
        return self.data_dir / "sentinel-1"

    @property
    def s2_dir(self) -> Path:
        return self.data_dir / "sentinel-2"

    @property
    def aef_dir(self) -> Path:
        return self.data_dir / "aef-embeddings"

    @property
    def labels_dir(self) -> Path:
        return self.data_dir / "labels" / "train"

    @property
    def metadata_dir(self) -> Path:
        return self.data_dir / "metadata"

    @property
    def train_tiles_geojson(self) -> Path:
        return self.metadata_dir / "train_tiles.geojson"

    @property
    def test_tiles_geojson(self) -> Path:
        return self.metadata_dir / "test_tiles.geojson"

    def s2_tile_dir(self, split: str, tile_id: str) -> Path:
        return self.s2_dir / split / f"{tile_id}__s2_l2a"

    def s1_tile_dir(self, split: str, tile_id: str) -> Path:
        return self.s1_dir / split / f"{tile_id}__s1_rtc"

    def aef_split_dir(self, split: str) -> Path:
        return self.aef_dir / split

    def assert_exists(self) -> None:
        if not self.data_dir.exists():
            raise FileNotFoundError(
                f"Dataset root not found: {self.data_dir}. "
                "Pass --data-dir, set MAKEATHON_DATA_DIR, or place data at "
                "./data/makeathon-challenge."
            )


# ---------------------------------------------------------------------------
# Training / feature hyperparameters. Tweak carefully; these defaults are
# chosen to run on a laptop-grade CPU within reasonable time.
# ---------------------------------------------------------------------------

PIXELS_PER_TILE = 40_000          # sampled pixels per train tile
POSITIVE_FRACTION = 0.5           # class balance when sampling
RANDOM_STATE = 42
BINARY_THRESHOLD = 0.5            # probability cut-off for the submission
MIN_AREA_HA = 0.5                 # filter tiny polygons in the GeoJSON
PRED_CHUNK_ROWS = 1024            # rows processed per inference chunk
S2_BANDS = 12                     # documented in challenge.ipynb
AEF_BANDS = 64
