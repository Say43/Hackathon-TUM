import argparse
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
COLLEAGUE_ROOT = PROJECT_ROOT / "model-training"
COLLEAGUE_SCRIPT = COLLEAGUE_ROOT / "run_solution.py"
DEFAULT_DATA_DIR = COLLEAGUE_ROOT / "data" / "makeathon-challenge"
DEFAULT_RUN_DIR = COLLEAGUE_ROOT / "runs" / "baseline"


def _resolve_user_path(value: str) -> str:
    path = Path(value)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return str(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Wrapper that runs Abdul Moeez's existing model-training pipeline."
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="all",
        choices=("train", "predict", "submit", "all"),
        help="Which existing command from model-training/run_solution.py to run.",
    )
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help="Dataset root for the colleague pipeline.",
    )
    parser.add_argument(
        "--run-dir",
        default=str(DEFAULT_RUN_DIR),
        help="Run output directory used for the 'all' command.",
    )
    parser.add_argument(
        "--model",
        default=str(DEFAULT_RUN_DIR / "model.joblib"),
        help="Existing trained model path used for 'predict'.",
    )
    parser.add_argument(
        "--pred-dir",
        default=str(DEFAULT_RUN_DIR / "predictions"),
        help="Prediction output directory used for 'predict' and 'submit'.",
    )
    parser.add_argument(
        "--geojson-dir",
        default=str(DEFAULT_RUN_DIR / "geojson"),
        help="GeoJSON output directory used for 'submit'.",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_RUN_DIR / "submission.geojson"),
        help="Merged submission output path used for 'submit'.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Optional threshold forwarded to the colleague script.",
    )
    parser.add_argument(
        "--min-area-ha",
        type=float,
        default=None,
        help="Optional polygon filter forwarded to the colleague script.",
    )
    parser.add_argument(
        "--max-tiles",
        type=int,
        default=None,
        help="Optional training limit forwarded to the colleague script.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging in the colleague script.",
    )
    return parser


def build_command(args: argparse.Namespace) -> list[str]:
    if not COLLEAGUE_SCRIPT.exists():
        raise FileNotFoundError(f"Colleague script not found: {COLLEAGUE_SCRIPT}")

    cmd = [sys.executable, str(COLLEAGUE_SCRIPT)]
    if args.verbose:
        cmd.append("--verbose")

    cmd.append(args.command)
    data_dir = _resolve_user_path(args.data_dir)
    run_dir = _resolve_user_path(args.run_dir)
    model = _resolve_user_path(args.model)
    pred_dir = _resolve_user_path(args.pred_dir)
    geojson_dir = _resolve_user_path(args.geojson_dir)
    out = _resolve_user_path(args.out)

    if args.command == "train":
        cmd.extend(["--data-dir", data_dir, "--model-out", str(Path(run_dir) / "model.joblib")])
        if args.max_tiles is not None:
            cmd.extend(["--max-tiles", str(args.max_tiles)])
        return cmd

    if args.command == "predict":
        cmd.extend(["--data-dir", data_dir, "--model", model, "--pred-dir", pred_dir])
        if args.threshold is not None:
            cmd.extend(["--threshold", str(args.threshold)])
        return cmd

    if args.command == "submit":
        cmd.extend(["--pred-dir", pred_dir, "--geojson-dir", geojson_dir, "--out", out])
        if args.min_area_ha is not None:
            cmd.extend(["--min-area-ha", str(args.min_area_ha)])
        return cmd

    cmd.extend(["--data-dir", data_dir, "--run-dir", run_dir])
    if args.max_tiles is not None:
        cmd.extend(["--max-tiles", str(args.max_tiles)])
    if args.threshold is not None:
        cmd.extend(["--threshold", str(args.threshold)])
    if args.min_area_ha is not None:
        cmd.extend(["--min-area-ha", str(args.min_area_ha)])
    return cmd


def main() -> None:
    args = build_parser().parse_args()
    cmd = build_command(args)

    env = os.environ.copy()
    env.setdefault("MAKEATHON_DATA_DIR", _resolve_user_path(args.data_dir))

    subprocess.run(cmd, cwd=str(COLLEAGUE_ROOT), env=env, check=True)


if __name__ == "__main__":
    main()
