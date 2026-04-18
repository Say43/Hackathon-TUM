#!/usr/bin/env python3
"""Print whether PyTorch can see CUDA / MPS (for Prithvi and other torch code)."""

from __future__ import annotations

import sys


def main() -> int:
    try:
        import torch
    except ImportError:
        print("PyTorch is not installed. Install torch (see requirements-gpu.txt).")
        return 1

    print("torch:", torch.__version__)
    cuda = torch.cuda.is_available()
    print("cuda.is_available:", cuda)
    if cuda:
        print("cuda.device_count:", torch.cuda.device_count())
        print("cuda.current_device:", torch.cuda.current_device())
        print("cuda.get_device_name(0):", torch.cuda.get_device_name(0))

    mps_ok = bool(
        getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()
    )
    print("mps.is_available:", mps_ok)

    return 0


if __name__ == "__main__":
    sys.exit(main())
