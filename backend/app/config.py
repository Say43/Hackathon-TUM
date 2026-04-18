"""Backend configuration (paths relative to repository root)."""

from __future__ import annotations

import os
from pathlib import Path

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


def get_data_dir() -> Path | None:
    """Dataset root (sentinel-1/, sentinel-2/, …). Optional for live inference."""
    raw = os.environ.get("MAKEATHON_DATA_DIR") or os.environ.get("DATA_DIR")
    if raw:
        return Path(raw).expanduser().resolve()

    # Probed in order — first existing path wins.
    candidates = [
        MODEL_TRAINING / "data" / "abdul-testrun" / "makeathon-challenge",
        MODEL_TRAINING / "data" / "makeathon-challenge",
        REPO_ROOT / "data" / "makeathon-challenge",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None
