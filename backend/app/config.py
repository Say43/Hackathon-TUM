"""Backend configuration (paths relative to repository root)."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_TRAINING = REPO_ROOT / "model-training"

# Trained classifier from Makeathon baseline run
DEFAULT_MODEL_PATH = MODEL_TRAINING / "runs" / "baseline" / "model.joblib"
# Pre-computed prediction rasters (binary) for demo without full Sentinel stacks
DEFAULT_PRED_DIR = MODEL_TRAINING / "runs" / "baseline" / "predictions"


def get_model_path() -> Path:
    return Path(os.environ.get("MODEL_PATH", DEFAULT_MODEL_PATH)).expanduser().resolve()


def get_pred_dir() -> Path:
    return Path(os.environ.get("PRED_DIR", DEFAULT_PRED_DIR)).expanduser().resolve()


def get_data_dir() -> Path | None:
    """Dataset root (sentinel-1/, sentinel-2/, …). Optional for live inference."""
    raw = os.environ.get("MAKEATHON_DATA_DIR") or os.environ.get("DATA_DIR")
    if raw:
        return Path(raw).expanduser().resolve()
    default = REPO_ROOT / "data" / "makeathon-challenge"
    if default.exists():
        return default.resolve()
    return None
