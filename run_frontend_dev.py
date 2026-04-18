import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the existing Vite frontend dev server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default="5173")
    args = parser.parse_args()

    subprocess.run(
        ["npm", "run", "dev", "--", "--host", args.host, "--port", args.port],
        cwd=str(FRONTEND_DIR),
        check=True,
    )


if __name__ == "__main__":
    main()
