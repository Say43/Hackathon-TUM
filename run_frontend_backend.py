import argparse
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_PRED_DIR = PROJECT_ROOT / "model-training" / "runs" / "abdul-testrun" / "predictions"
DEFAULT_DATA_DIR = PROJECT_ROOT / "model-training" / "data" / "abdul-testrun" / "makeathon-challenge"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the backend API against the current Abdul test-run artifacts for the frontend."
    )
    parser.add_argument("--pred-dir", default=str(DEFAULT_PRED_DIR))
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default="8000")
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    env = os.environ.copy()
    env["PRED_DIR"] = str(Path(args.pred_dir).expanduser().resolve())
    env["MAKEATHON_DATA_DIR"] = str(Path(args.data_dir).expanduser().resolve())

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        args.host,
        "--port",
        args.port,
    ]
    if args.reload:
        cmd.append("--reload")

    subprocess.run(cmd, cwd=str(PROJECT_ROOT / "backend"), env=env, check=True)


if __name__ == "__main__":
    main()
