"""Train a classical per-pixel classifier on fused weak labels.

We use a scikit-learn :class:`HistGradientBoostingClassifier` because:

* It handles NaN inputs natively (robust to cloudy / missing observations).
* It scales to millions of rows on a laptop in minutes.
* It needs no feature scaling — S1 dB, S2 reflectance and AEF embeddings can
  be concatenated as-is.

The model + the ordered feature-name list + a couple of metadata fields are
serialised together so inference is reproducible.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from .config import (
    PIXELS_PER_TILE,
    POSITIVE_FRACTION,
    RANDOM_STATE,
    Paths,
)
from .data_loader import (
    TileRef,
    iter_labels_for_split,
    open_tile,
    read_aef_mean,
    read_label_rasters,
    read_s1_stack,
    read_s2_stack,
)
from .features import stack_features
from .labels import fuse

logger = logging.getLogger(__name__)


@dataclass
class TrainedModel:
    estimator: HistGradientBoostingClassifier
    feature_names: list[str]
    metadata: dict

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "estimator": self.estimator,
                "feature_names": self.feature_names,
                "metadata": self.metadata,
            },
            path,
        )

    @classmethod
    def load(cls, path: Path) -> "TrainedModel":
        blob = joblib.load(Path(path))
        return cls(
            estimator=blob["estimator"],
            feature_names=blob["feature_names"],
            metadata=blob.get("metadata", {}),
        )


def _sample_pixels(
    cube: np.ndarray,
    positive: np.ndarray,
    confident_negative: np.ndarray,
    rng: np.random.Generator,
    max_pixels: int,
    pos_fraction: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Balanced sampling of pixels within a single tile."""
    h, w, _ = cube.shape
    flat = cube.reshape(h * w, -1)
    pos_idx = np.flatnonzero(positive.reshape(-1))
    neg_idx = np.flatnonzero(confident_negative.reshape(-1))

    if pos_idx.size == 0 or neg_idx.size == 0:
        return np.empty((0, flat.shape[1]), dtype=np.float32), np.empty((0,), dtype=np.uint8)

    n_pos_target = int(max_pixels * pos_fraction)
    n_neg_target = max_pixels - n_pos_target
    n_pos = min(n_pos_target, pos_idx.size)
    n_neg = min(n_neg_target, neg_idx.size)

    pos_pick = rng.choice(pos_idx, size=n_pos, replace=False)
    neg_pick = rng.choice(neg_idx, size=n_neg, replace=False)
    idx = np.concatenate([pos_pick, neg_pick])
    y = np.concatenate([np.ones(n_pos, dtype=np.uint8), np.zeros(n_neg, dtype=np.uint8)])
    return flat[idx], y


def build_training_matrix(
    paths: Paths,
    max_tiles: int | None = None,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Iterate train tiles and assemble the (X, y) matrix for training."""
    rng = np.random.default_rng(RANDOM_STATE)
    tile_ids = list(iter_labels_for_split(paths, "train"))
    if max_tiles is not None:
        tile_ids = tile_ids[:max_tiles]
    if not tile_ids:
        raise RuntimeError(
            "No labelled training tiles discovered. "
            "Check that labels/train/{gladl,glads2,radd}/ exist under the data dir."
        )

    X_parts: list[np.ndarray] = []
    y_parts: list[np.ndarray] = []
    feature_names: list[str] | None = None

    for i, tid in enumerate(tile_ids, 1):
        logger.info("[%d/%d] Building features for train tile %s", i, len(tile_ids), tid)
        ref: TileRef = open_tile(paths, "train", tid)
        s2 = read_s2_stack(paths, ref)
        s1 = read_s1_stack(paths, ref)
        aef = read_aef_mean(paths, ref)
        cube, names = stack_features(s2, s1, aef, ref.height, ref.width)
        if feature_names is None:
            feature_names = names
        elif names != feature_names:
            # Align to the canonical order discovered from the first tile.
            from .features import align_feature_matrix

            cube = align_feature_matrix(cube, names, feature_names)

        labels = read_label_rasters(paths, ref)
        if not labels:
            logger.warning("Tile %s has no label rasters; skipping", tid)
            continue
        fused = fuse(labels)

        X_i, y_i = _sample_pixels(
            cube, fused.positive, fused.confident_negative,
            rng, PIXELS_PER_TILE, POSITIVE_FRACTION,
        )
        if X_i.size == 0:
            logger.warning("Tile %s produced zero usable samples; skipping", tid)
            continue
        X_parts.append(X_i)
        y_parts.append(y_i)

    if not X_parts:
        raise RuntimeError("No training samples produced. Check label fusion and data availability.")

    X = np.concatenate(X_parts, axis=0)
    y = np.concatenate(y_parts, axis=0)
    logger.info("Training matrix: X=%s y=%s positives=%d", X.shape, y.shape, int(y.sum()))
    return X, y, feature_names or []


def train_model(
    paths: Paths,
    max_tiles: int | None = None,
) -> TrainedModel:
    """Full training loop: build (X, y), fit model, return the TrainedModel."""
    X, y, feature_names = build_training_matrix(paths, max_tiles=max_tiles)

    estimator = HistGradientBoostingClassifier(
        max_iter=400,
        learning_rate=0.05,
        max_depth=None,
        max_leaf_nodes=63,
        l2_regularization=1.0,
        early_stopping=True,
        validation_fraction=0.1,
        random_state=RANDOM_STATE,
    )
    estimator.fit(X, y)

    return TrainedModel(
        estimator=estimator,
        feature_names=feature_names,
        metadata={
            "n_train_samples": int(X.shape[0]),
            "n_positive": int(y.sum()),
            "n_features": int(X.shape[1]),
        },
    )
