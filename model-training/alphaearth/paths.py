"""Filesystem layout for the Makeathon AEF dataset.

Replaces `solution/config.py`. The dataset root is resolved exactly the same
way as the FastAPI backend does (CLI argument > `MAKEATHON_DATA_DIR` env var >
sensible defaults under `model-training/`), so the CLI and the API agree on
which tiles exist.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_TRAINING = REPO_ROOT / "model-training"

# In order; first existing wins. Must mirror backend/app/config.py.
DEFAULT_DATA_CANDIDATES = (
    MODEL_TRAINING / "data" / "abdul-testrun" / "makeathon-challenge",
    MODEL_TRAINING / "data" / "makeathon-challenge",
    REPO_ROOT / "data" / "makeathon-challenge",
)

# AEF filenames look like  "18NWG_6_6_2020.tiff"  -> tile=18NWG_6_6, year=2020.
_AEF_NAME_RE = re.compile(r"^(?P<tile>[A-Z0-9_]+?)_(?P<year>\d{4})\.tiff?$")

# Weak label sources expected under labels/train/{source}.
LABEL_SOURCES = ("gladl", "glads2", "radd")


def resolve_data_dir(cli_value: str | None = None) -> Path:
    """Resolve the dataset root, with the same precedence as the API."""

    if cli_value:
        return Path(cli_value).expanduser().resolve()
    raw = os.environ.get("MAKEATHON_DATA_DIR") or os.environ.get("DATA_DIR")
    if raw:
        env = Path(raw).expanduser()
        if not env.is_absolute():
            env = REPO_ROOT / env
        env = env.resolve()
        if env.exists():
            return env
    for candidate in DEFAULT_DATA_CANDIDATES:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(
        "Dataset root not found. Pass --data-dir, set MAKEATHON_DATA_DIR, "
        "or place the challenge data under model-training/data/."
    )


def resolve_cache_dir(cli_value: str | None = None) -> Path:
    """Where on-disk caches (PCA PNGs, UMAP JSON, classifier joblibs) live."""

    if cli_value:
        return Path(cli_value).expanduser().resolve()
    raw = os.environ.get("AEF_CACHE_DIR")
    if raw:
        env = Path(raw).expanduser()
        if not env.is_absolute():
            env = REPO_ROOT / env
        return env.resolve()
    return (MODEL_TRAINING / "runs" / "aef").resolve()


@dataclass(frozen=True)
class Paths:
    data_dir: Path

    @property
    def aef_dir(self) -> Path:
        return self.data_dir / "aef-embeddings"

    @property
    def labels_root(self) -> Path:
        return self.data_dir / "labels" / "train"

    @property
    def metadata_dir(self) -> Path:
        return self.data_dir / "metadata"

    def aef_split_dir(self, split: str) -> Path:
        if split not in ("train", "test"):
            raise ValueError(f"split must be train|test, got {split!r}")
        return self.aef_dir / split

    def aef_tile_path(self, tile: str, year: int, split: str) -> Path:
        return self.aef_split_dir(split) / f"{tile}_{year}.tiff"

    def metadata_geojson(self, split: str) -> Path:
        if split not in ("train", "test"):
            raise ValueError(f"split must be train|test, got {split!r}")
        return self.metadata_dir / f"{split}_tiles.geojson"

    def label_dir(self, source: str) -> Path:
        if source not in LABEL_SOURCES:
            raise ValueError(
                f"label source must be one of {LABEL_SOURCES}, got {source!r}"
            )
        return self.labels_root / source

    def list_aef_files(self, split: str) -> list[Path]:
        d = self.aef_split_dir(split)
        if not d.exists():
            return []
        return sorted(p for p in d.iterdir() if _AEF_NAME_RE.match(p.name))


@dataclass(frozen=True)
class TileYear:
    """One concrete (tile, year, split) AEF observation."""

    tile: str
    year: int
    split: str

    @property
    def key(self) -> str:
        return f"{self.tile}_{self.year}_{self.split}"


def parse_aef_name(name: str) -> tuple[str, int]:
    """`'18NWG_6_6_2020.tiff'` -> `('18NWG_6_6', 2020)`. Raises if invalid."""

    m = _AEF_NAME_RE.match(Path(name).name)
    if not m:
        raise ValueError(f"Not an AEF tile filename: {name!r}")
    return m.group("tile"), int(m.group("year"))


def discover_tiles(paths: Paths, split: str) -> dict[str, list[int]]:
    """Map tile id -> sorted list of years available for that tile."""

    out: dict[str, list[int]] = {}
    for p in paths.list_aef_files(split):
        tile, year = parse_aef_name(p.name)
        out.setdefault(tile, []).append(year)
    for tile in out:
        out[tile].sort()
    return out


def discover_label_files(paths: Paths, source: str, tile: str) -> list[Path]:
    """All weak-label rasters for a tile under a given source (any year)."""

    d = paths.label_dir(source)
    if not d.exists():
        return []
    needle = f"_{tile}_"
    return sorted(p for p in d.iterdir() if needle in p.name and p.suffix == ".tif")
