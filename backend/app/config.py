"""Backend configuration (paths relative to repository root)."""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_TRAINING = REPO_ROOT / "model-training"

# Load backend/.env if present so MAKEATHON_DATA_DIR etc. can live in one place.
try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / "backend" / ".env", override=False)
except ImportError:  # python-dotenv is optional
    pass

# Trained classifier from Makeathon baseline run
DEFAULT_MODEL_PATH = MODEL_TRAINING / "runs" / "baseline" / "model.joblib"
# Pre-computed prediction rasters (binary) for demo without full Sentinel stacks
DEFAULT_PRED_DIR = MODEL_TRAINING / "runs" / "baseline" / "predictions"


def get_model_path() -> Path:
    return Path(os.environ.get("MODEL_PATH", DEFAULT_MODEL_PATH)).expanduser().resolve()


def get_pred_dir() -> Path:
    return Path(os.environ.get("PRED_DIR", DEFAULT_PRED_DIR)).expanduser().resolve()


DEFAULT_DATA_CANDIDATES = (
    MODEL_TRAINING / "data" / "abdul-testrun" / "makeathon-challenge",
    MODEL_TRAINING / "data" / "makeathon-challenge",
    REPO_ROOT / "data" / "makeathon-challenge",
)


def _resolve_env_data_dir(raw: str) -> Path:
    """Resolve a user-supplied path, anchoring relative paths to REPO_ROOT.

    Anchoring to REPO_ROOT (not `os.getcwd()`) is important because uvicorn is
    typically launched from inside `backend/`, which turns a perfectly
    sensible-looking value like `model-training/data/...` into
    `backend/model-training/data/...` — a path that does not exist.
    """
    expanded = Path(raw).expanduser()
    if not expanded.is_absolute():
        expanded = REPO_ROOT / expanded
    return expanded.resolve()


def get_data_dir() -> Path | None:
    """Dataset root (sentinel-1/, sentinel-2/, …). Optional for live inference.

    Precedence:
      1. `MAKEATHON_DATA_DIR` / `DATA_DIR` if set AND the path exists.
      2. Built-in default candidates (first existing wins).

    If the env var is set but points to a non-existent path we log a warning and
    fall through to the defaults, rather than returning a dead path that makes
    downstream checks fail mysteriously.
    """
    raw = os.environ.get("MAKEATHON_DATA_DIR") or os.environ.get("DATA_DIR")
    if raw:
        env_path = _resolve_env_data_dir(raw)
        if env_path.exists():
            return env_path
        logger.warning(
            "Env-configured data dir %r resolved to %s, but that path does not exist. "
            "Falling back to built-in defaults.",
            raw,
            env_path,
        )

    for candidate in DEFAULT_DATA_CANDIDATES:
        if candidate.exists():
            return candidate.resolve()
    return None


def describe_data_dir_resolution() -> dict:
    """Structured snapshot of how `get_data_dir()` resolves right now.

    Intended for the /api/debug/paths endpoint so the behaviour on the remote
    server is observable without shell access.
    """
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
    }
