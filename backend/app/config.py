"""Backend configuration (paths relative to repository root).

The backend is intentionally a thin shell around the `alphaearth` Python
package that ships under `model-training/alphaearth/`. We add the package's
parent directory to `sys.path` once, then forward path resolution to the
helpers there so the API and the CLI agree on which dataset is loaded.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_TRAINING = REPO_ROOT / "model-training"

if str(MODEL_TRAINING) not in sys.path:
    sys.path.insert(0, str(MODEL_TRAINING))

# Load backend/.env if present so MAKEATHON_DATA_DIR / AEF_CACHE_DIR can live
# in one place. Imported lazily to keep python-dotenv optional.
try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / "backend" / ".env", override=False)
except ImportError:  # pragma: no cover
    pass


DEFAULT_DATA_CANDIDATES = (
    MODEL_TRAINING / "data" / "abdul-testrun" / "makeathon-challenge",
    MODEL_TRAINING / "data" / "makeathon-challenge",
    REPO_ROOT / "data" / "makeathon-challenge",
)
DEFAULT_CACHE_DIR = MODEL_TRAINING / "runs" / "aef"


def _resolve_env_data_dir(raw: str) -> Path:
    """Resolve a user-supplied path, anchoring relative paths to REPO_ROOT.

    Anchoring to REPO_ROOT (not `os.getcwd()`) is important because uvicorn is
    typically launched from inside `backend/`, which would turn a sensible
    value like `model-training/data/...` into `backend/model-training/data/...`.
    """

    expanded = Path(raw).expanduser()
    if not expanded.is_absolute():
        expanded = REPO_ROOT / expanded
    return expanded.resolve()


def get_data_dir() -> Path | None:
    """Dataset root containing `aef-embeddings/` and `labels/`.

    Precedence:
      1. `MAKEATHON_DATA_DIR` / `DATA_DIR` if set AND the path exists.
      2. Built-in default candidates (first existing wins).
    """

    raw = os.environ.get("MAKEATHON_DATA_DIR") or os.environ.get("DATA_DIR")
    if raw:
        env_path = _resolve_env_data_dir(raw)
        if env_path.exists():
            return env_path
        logger.warning(
            "Env-configured data dir %r resolved to %s, but that path does "
            "not exist. Falling back to built-in defaults.",
            raw,
            env_path,
        )
    for candidate in DEFAULT_DATA_CANDIDATES:
        if candidate.exists():
            return candidate.resolve()
    return None


def get_cache_dir() -> Path:
    """Where AEF previews/scatter/classifier runs are persisted."""

    raw = os.environ.get("AEF_CACHE_DIR")
    if raw:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = REPO_ROOT / path
        return path.resolve()
    return DEFAULT_CACHE_DIR.resolve()


def describe_data_dir_resolution() -> dict:
    """Structured snapshot of how `get_data_dir()` resolves right now."""

    raw_env = os.environ.get("MAKEATHON_DATA_DIR") or os.environ.get("DATA_DIR")
    env_source = (
        "MAKEATHON_DATA_DIR"
        if os.environ.get("MAKEATHON_DATA_DIR")
        else ("DATA_DIR" if os.environ.get("DATA_DIR") else None)
    )
    resolved_from_env: Path | None = None
    env_is_relative: bool | None = None
    if raw_env:
        env_is_relative = not Path(raw_env).expanduser().is_absolute()
        resolved_from_env = _resolve_env_data_dir(raw_env)

    def _probe(path: Path) -> dict:
        p = path.expanduser().resolve()
        exists = p.exists()
        details: dict = {"path": str(p), "exists": exists, "isDir": False}
        if exists:
            details["isDir"] = p.is_dir()
            if p.is_dir():
                try:
                    details["topLevelEntries"] = sorted(
                        [child.name for child in p.iterdir()][:12]
                    )
                except PermissionError:
                    details["topLevelEntries"] = "permission-denied"
        return details

    candidates = [_probe(c) for c in DEFAULT_DATA_CANDIDATES]
    resolved = get_data_dir()
    cache_dir = get_cache_dir()
    aef_dir = (resolved / "aef-embeddings") if resolved else None
    labels_dir = (resolved / "labels" / "train") if resolved else None
    return {
        "repoRoot": str(REPO_ROOT),
        "modelTrainingDir": str(MODEL_TRAINING),
        "cwd": str(Path.cwd()),
        "envVar": {
            "source": env_source,
            "rawValue": raw_env,
            "isRelative": env_is_relative,
            "resolvedAbsolute": str(resolved_from_env) if resolved_from_env else None,
            "resolvedExists": resolved_from_env.exists() if resolved_from_env else None,
            "anchoredTo": "REPO_ROOT" if env_is_relative else ("ABSOLUTE" if raw_env else None),
        },
        "defaultCandidates": candidates,
        "resolved": str(resolved) if resolved else None,
        "resolvedExists": resolved.exists() if resolved else False,
        "aefDir": {
            "path": str(aef_dir) if aef_dir else None,
            "exists": bool(aef_dir and aef_dir.exists()),
        },
        "labelsDir": {
            "path": str(labels_dir) if labels_dir else None,
            "exists": bool(labels_dir and labels_dir.exists()),
        },
        "cacheDir": {
            "path": str(cache_dir),
            "exists": cache_dir.exists(),
        },
    }
