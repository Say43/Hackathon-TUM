"""Compatibility shim — the project pivoted to AlphaEarth Foundations.

This file used to drive the GLAD/Sentinel deforestation baseline. That
solution has been retired in favour of the AEF-first explorer; please use
`python run_aef.py --help` instead. Running this script forwards any
arguments to `run_aef.py` so existing scripts/CI calling
``python run_solution.py …`` keep working.
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(here, "run_aef.py")
    sys.stderr.write(
        "[run_solution.py] DEPRECATED — forwarding to run_aef.py. "
        "Update your call sites to invoke run_aef.py directly.\n"
    )
    args = [sys.executable, target, *sys.argv[1:]]
    os.execv(sys.executable, args)


if __name__ == "__main__":
    raise SystemExit(main())
