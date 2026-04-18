"""Command-line entrypoint for the baseline deforestation solution.

Typical usage (assuming ``data/makeathon-challenge`` is where the dataset
lives – if not, pass ``--data-dir /path/to/makeathon-challenge``)::

    # 1. Train the model on weak-label fused training tiles
    python run_solution.py train --data-dir /path/to/makeathon-challenge \
        --model-out runs/run1/model.joblib

    # 2. Predict every test tile → per-tile binary rasters
    python run_solution.py predict --data-dir /path/to/makeathon-challenge \
        --model runs/run1/model.joblib --pred-dir runs/run1/predictions

    # 3. Vectorise predictions → per-tile GeoJSONs + a merged submission file
    python run_solution.py submit --pred-dir runs/run1/predictions \
        --geojson-dir runs/run1/geojson --out runs/run1/submission.geojson

    # Or run all three steps at once:
    python run_solution.py all --data-dir /path/to/makeathon-challenge \
        --run-dir runs/run1
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from solution.config import BINARY_THRESHOLD, MIN_AREA_HA, Paths, resolve_data_dir
from solution.model import TrainedModel, train_model
from solution.predict import predict_all_test_tiles
from solution.submit import merge_geojsons, rasters_to_geojsons


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _paths(args: argparse.Namespace) -> Paths:
    p = Paths(resolve_data_dir(getattr(args, "data_dir", None)))
    p.assert_exists()
    logging.info("Using dataset root: %s", p.data_dir)
    return p


def cmd_train(args: argparse.Namespace) -> None:
    paths = _paths(args)
    model = train_model(paths, max_tiles=args.max_tiles)
    out = Path(args.model_out)
    model.save(out)
    logging.info("Saved model → %s | %s", out, model.metadata)


def cmd_predict(args: argparse.Namespace) -> None:
    paths = _paths(args)
    model = TrainedModel.load(args.model)
    rasters = predict_all_test_tiles(
        paths, model, Path(args.pred_dir), threshold=args.threshold,
    )
    logging.info("Wrote %d prediction rasters → %s", len(rasters), args.pred_dir)


def cmd_submit(args: argparse.Namespace) -> None:
    pred_dir = Path(args.pred_dir)
    rasters = sorted(pred_dir.glob("pred_*.tif"))
    if not rasters:
        raise SystemExit(f"No prediction rasters found in {pred_dir}")

    per_tile = rasters_to_geojsons(rasters, Path(args.geojson_dir), min_area_ha=args.min_area_ha)
    if not per_tile:
        raise SystemExit(
            "No GeoJSONs produced — every prediction raster was empty or "
            "filtered out by min_area_ha. Lower the threshold or min_area_ha."
        )
    merged = merge_geojsons(per_tile, Path(args.out))
    logging.info("Submission ready: %s", merged)


def cmd_all(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    model_path = run_dir / "model.joblib"
    pred_dir = run_dir / "predictions"
    geojson_dir = run_dir / "geojson"
    submission_path = run_dir / "submission.geojson"

    cmd_train(argparse.Namespace(
        data_dir=args.data_dir, max_tiles=args.max_tiles, model_out=model_path,
    ))
    cmd_predict(argparse.Namespace(
        data_dir=args.data_dir, model=model_path, pred_dir=pred_dir,
        threshold=args.threshold,
    ))
    cmd_submit(argparse.Namespace(
        pred_dir=pred_dir, geojson_dir=geojson_dir, out=submission_path,
        min_area_ha=args.min_area_ha,
    ))


def _add_data_dir(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--data-dir",
        default=None,
        help="Dataset root (folder containing sentinel-1/ sentinel-2/ aef-embeddings/ labels/ metadata/). "
             "Defaults to $MAKEATHON_DATA_DIR or ./data/makeathon-challenge.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deforestation baseline")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p_train = sub.add_parser("train", help="Train the per-pixel classifier")
    _add_data_dir(p_train)
    p_train.add_argument("--model-out", required=True)
    p_train.add_argument("--max-tiles", type=int, default=None,
                         help="Limit number of training tiles (for fast iteration)")
    p_train.set_defaults(func=cmd_train)

    p_pred = sub.add_parser("predict", help="Predict all test tiles")
    _add_data_dir(p_pred)
    p_pred.add_argument("--model", required=True)
    p_pred.add_argument("--pred-dir", required=True)
    p_pred.add_argument("--threshold", type=float, default=BINARY_THRESHOLD)
    p_pred.set_defaults(func=cmd_predict)

    p_sub = sub.add_parser("submit", help="Vectorise predictions and build a submission file")
    p_sub.add_argument("--pred-dir", required=True)
    p_sub.add_argument("--geojson-dir", required=True)
    p_sub.add_argument("--out", required=True)
    p_sub.add_argument("--min-area-ha", type=float, default=MIN_AREA_HA)
    p_sub.set_defaults(func=cmd_submit)

    p_all = sub.add_parser("all", help="Train, predict and build the submission in one go")
    _add_data_dir(p_all)
    p_all.add_argument("--run-dir", required=True)
    p_all.add_argument("--max-tiles", type=int, default=None)
    p_all.add_argument("--threshold", type=float, default=BINARY_THRESHOLD)
    p_all.add_argument("--min-area-ha", type=float, default=MIN_AREA_HA)
    p_all.set_defaults(func=cmd_all)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    _configure_logging(args.verbose)
    args.func(args)


if __name__ == "__main__":
    main()
