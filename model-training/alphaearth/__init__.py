"""AlphaEarth Foundations (AEF) explorer toolkit.

This package replaces the original `solution/` baseline. It provides:

* `paths`        — dataset path helpers for AEF tiles + weak labels.
* `io`           — read AEF rasters, reproject weak labels onto the AEF grid,
                   and sample labeled pixels.
* `previews`     — render PCA-3 false-color PNGs from 64-band AEF tiles.
* `scatter`      — PCA-2D and UMAP-2D projections of labeled pixel samples.
* `classifiers`  — train SVM (LinearSVC) and MLP classifiers on AEF embeddings.
* `mislabels`    — find regions where a model strongly disagrees with the weak
                   label (a proxy for likely mislabelled / mis-aligned data).
* `cache`        — content-addressable on-disk cache used by both the CLI and
                   the FastAPI backend.

The code is intentionally backend-agnostic: nothing imports FastAPI. The
`backend/app/aef_service.py` module is a thin adapter on top of this package.
"""

from . import cache, classifiers, io, mislabels, paths, previews, scatter

__all__ = [
    "cache",
    "classifiers",
    "io",
    "mislabels",
    "paths",
    "previews",
    "scatter",
]
