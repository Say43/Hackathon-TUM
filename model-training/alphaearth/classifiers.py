"""SVM and MLP classifiers over AEF embeddings + metrics + prediction maps.

The classifier "lab" workflow:

1. Caller supplies one or more train (tile, year), one optional val (tile, year),
   one test (tile, year), and a label source.
2. We sample labelled pixels from each tile, fit `LinearSVC` or `MLPClassifier`,
   and evaluate on the test tile (if it has labels).
3. We run a full-tile prediction pass on the test tile, write a binary
   prediction PNG (RGBA — opaque on positive predictions, transparent on
   negative), and persist everything in the cache.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import joblib
import numpy as np
from PIL import Image
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

from . import cache
from .io import (
    all_pixels_matrix,
    label_array_for,
    open_aef_tile,
    sample_labelled_pixels,
    valid_pixel_mask,
)
from .paths import Paths, TileYear

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClassifyRequest:
    model: str  # "svm" | "mlp"
    train_tiles: tuple[TileYear, ...]
    val_tile: TileYear | None
    test_tile: TileYear
    label_source: str
    sample_per_tile: int = 4000
    seed: int = 42

    def cache_key(self) -> dict:
        return {
            "model": self.model,
            "trainTiles": [t.key for t in self.train_tiles],
            "valTile": self.val_tile.key if self.val_tile else None,
            "testTile": self.test_tile.key,
            "labelSource": self.label_source,
            "samplePerTile": self.sample_per_tile,
            "seed": self.seed,
            "version": 2,
        }


def _build_estimator(model: str, *, seed: int):
    if model == "svm":
        return Pipeline(
            [
                ("scale", StandardScaler(with_mean=True, with_std=True)),
                (
                    "clf",
                    LinearSVC(
                        C=1.0,
                        class_weight="balanced",
                        dual="auto",
                        max_iter=5000,
                        random_state=seed,
                    ),
                ),
            ]
        )
    if model == "mlp":
        return Pipeline(
            [
                ("scale", StandardScaler(with_mean=True, with_std=True)),
                (
                    "clf",
                    MLPClassifier(
                        hidden_layer_sizes=(128, 64, 32),
                        activation="relu",
                        solver="adam",
                        max_iter=200,
                        early_stopping=True,
                        validation_fraction=0.1,
                        n_iter_no_change=10,
                        random_state=seed,
                    ),
                ),
            ]
        )
    raise ValueError(f"Unknown model {model!r}")


def _decision_scores(estimator, X: np.ndarray) -> np.ndarray:
    """Return (N,) float scores for the positive class.

    LinearSVC has no `predict_proba`; we use `decision_function` and pass it
    through a logistic squash so the scale matches the MLP output.
    """

    if hasattr(estimator, "predict_proba"):
        return estimator.predict_proba(X)[:, 1]
    raw = estimator.decision_function(X)
    return 1.0 / (1.0 + np.exp(-raw))


def _gather_train(
    paths: Paths,
    tiles: Sequence[TileYear],
    label_source: str,
    sample_per_tile: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    Xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    for ty in tiles:
        if ty.split != "train":
            logger.warning("Skipping %s — only train split has labels", ty.key)
            continue
        tile = open_aef_tile(paths, ty.tile, ty.year, ty.split)
        label = label_array_for(paths, tile, label_source)
        if label is None:
            logger.warning("Skipping %s — no %s label", ty.key, label_source)
            continue
        X, y, _ = sample_labelled_pixels(
            tile, label, sample=sample_per_tile, rng=rng, balance=True
        )
        if X.size == 0:
            continue
        Xs.append(X)
        ys.append(y)
    if not Xs:
        raise RuntimeError(
            f"No labelled training samples could be drawn for label source {label_source!r}. "
            "Check that the tiles exist in the train split and that the labels are present."
        )
    return np.concatenate(Xs, axis=0), np.concatenate(ys, axis=0)


def _evaluate(
    estimator, X: np.ndarray, y: np.ndarray
) -> dict:
    if X.size == 0:
        return {
            "supported": False,
            "reason": "no_test_samples",
        }
    preds = estimator.predict(X)
    scores = _decision_scores(estimator, X)
    cm = confusion_matrix(y, preds, labels=[0, 1])
    metrics = {
        "supported": True,
        "samples": int(X.shape[0]),
        "precision": float(precision_score(y, preds, pos_label=1, zero_division=0)),
        "recall": float(recall_score(y, preds, pos_label=1, zero_division=0)),
        "f1": float(f1_score(y, preds, pos_label=1, zero_division=0)),
        "confusion": {
            "tn": int(cm[0, 0]),
            "fp": int(cm[0, 1]),
            "fn": int(cm[1, 0]),
            "tp": int(cm[1, 1]),
        },
    }
    if len(np.unique(y)) > 1:
        try:
            metrics["rocAuc"] = float(roc_auc_score(y, scores))
        except ValueError:
            pass
    return metrics


def _render_prediction_png(
    pred: np.ndarray, valid: np.ndarray
) -> np.ndarray:
    """Map (H, W) binary prediction + valid mask to (H, W, 4) RGBA uint8.

    Negative predictions render as transparent navy; positive as opaque
    crimson; invalid pixels stay fully transparent.
    """

    h, w = pred.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    if not valid.any():
        return rgba
    pos = (pred == 1) & valid
    neg = (pred == 0) & valid
    rgba[neg] = [21, 32, 64, 110]
    rgba[pos] = [220, 38, 38, 220]
    return rgba


def _render_probability_png(
    proba: np.ndarray, valid: np.ndarray
) -> np.ndarray:
    """Continuous probability ramp from cold (0) to hot (1)."""

    h, w = proba.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    if not valid.any():
        return rgba
    p = np.clip(proba, 0.0, 1.0)
    r = (255 * p).astype(np.uint8)
    g = (255 * (1.0 - np.abs(p - 0.5) * 2)).astype(np.uint8)
    b = (255 * (1.0 - p)).astype(np.uint8)
    a = np.where(valid, 230, 0).astype(np.uint8)
    rgba[..., 0] = r
    rgba[..., 1] = g
    rgba[..., 2] = b
    rgba[..., 3] = a
    return rgba


def run_classifier(
    paths: Paths, cache_root: Path, request: ClassifyRequest, *, refresh: bool = False
) -> dict:
    """Train, evaluate, persist artifacts. Returns the payload sent to the API."""

    key = cache.hash_request(request.cache_key())
    run_dir = cache.runs_dir(cache_root) / key
    metrics_path = run_dir / "metrics.json"
    if metrics_path.exists() and not refresh:
        cached = cache.read_json(metrics_path)
        if cached is not None:
            cached["modelId"] = key
            cached["fromCache"] = True
            return cached

    cache.ensure_dir(run_dir)
    X_train, y_train = _gather_train(
        paths,
        request.train_tiles,
        request.label_source,
        request.sample_per_tile,
        request.seed,
    )
    estimator = _build_estimator(request.model, seed=request.seed)
    estimator.fit(X_train, y_train)
    joblib.dump(estimator, run_dir / "model.joblib")

    val_metrics = None
    if request.val_tile:
        try:
            val_tile = open_aef_tile(
                paths, request.val_tile.tile, request.val_tile.year, request.val_tile.split
            )
            val_label = label_array_for(paths, val_tile, request.label_source)
            if val_label is not None:
                X_val, y_val, _ = sample_labelled_pixels(
                    val_tile,
                    val_label,
                    sample=request.sample_per_tile,
                    rng=np.random.default_rng(request.seed + 1),
                    balance=False,
                )
                val_metrics = _evaluate(estimator, X_val, y_val)
        except FileNotFoundError as exc:
            logger.warning("Validation tile unavailable: %s", exc)

    test_tile = open_aef_tile(
        paths, request.test_tile.tile, request.test_tile.year, request.test_tile.split
    )
    test_label = (
        label_array_for(paths, test_tile, request.label_source)
        if request.test_tile.split == "train"
        else None
    )

    flat, valid = all_pixels_matrix(test_tile)
    full_pred = np.zeros((test_tile.height, test_tile.width), dtype=np.uint8)
    full_proba = np.zeros((test_tile.height, test_tile.width), dtype=np.float32)
    if flat.size > 0:
        preds = estimator.predict(flat)
        scores = _decision_scores(estimator, flat)
        full_pred[valid] = preds.astype(np.uint8)
        full_proba[valid] = scores.astype(np.float32)

    test_metrics: dict
    if test_label is not None:
        rng = np.random.default_rng(request.seed + 2)
        X_test, y_test, _ = sample_labelled_pixels(
            test_tile, test_label, sample=request.sample_per_tile, rng=rng, balance=False
        )
        test_metrics = _evaluate(estimator, X_test, y_test)
    else:
        test_metrics = {"supported": False, "reason": "test_tile_has_no_labels"}

    pred_png = _render_prediction_png(full_pred, valid)
    Image.fromarray(pred_png, mode="RGBA").save(run_dir / "prediction.png", optimize=True)
    proba_png = _render_probability_png(full_proba, valid)
    Image.fromarray(proba_png, mode="RGBA").save(run_dir / "probability.png", optimize=True)

    np.save(run_dir / "prediction.npy", full_pred)
    np.save(run_dir / "probability.npy", full_proba)
    np.save(run_dir / "valid.npy", valid)
    if test_label is not None:
        np.save(run_dir / "test_label.npy", test_label)

    payload = {
        "modelId": key,
        "request": request.cache_key(),
        "trainSamples": int(X_train.shape[0]),
        "trainPositive": int((y_train == 1).sum()),
        "valMetrics": val_metrics,
        "testMetrics": test_metrics,
        "tile": {
            "id": request.test_tile.tile,
            "year": request.test_tile.year,
            "split": request.test_tile.split,
            "height": int(test_tile.height),
            "width": int(test_tile.width),
        },
        "fromCache": False,
    }
    cache.write_json(metrics_path, payload)
    return payload


def load_run(cache_root: Path, model_id: str) -> dict | None:
    run_dir = cache.runs_dir(cache_root) / model_id
    return cache.read_json(run_dir / "metrics.json")


def run_artifact_path(cache_root: Path, model_id: str, name: str) -> Path:
    return cache.runs_dir(cache_root) / model_id / name
