"""Tiny content-addressable on-disk cache shared by the CLI and the API."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def hash_request(payload: dict[str, Any]) -> str:
    """Stable short hash of a JSON-serialisable dict (sorted keys)."""

    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha1(blob).hexdigest()[:16]


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def previews_dir(cache_root: Path) -> Path:
    return ensure_dir(cache_root / "previews")


def bands_dir(cache_root: Path) -> Path:
    return ensure_dir(cache_root / "bands")


def stats_dir(cache_root: Path) -> Path:
    return ensure_dir(cache_root / "stats")


def scatter_dir(cache_root: Path) -> Path:
    return ensure_dir(cache_root / "scatter")


def runs_dir(cache_root: Path) -> Path:
    return ensure_dir(cache_root / "runs")


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, separators=(",", ":")))


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
