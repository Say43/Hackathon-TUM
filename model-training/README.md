# osapiens Challenge Makeathon 2026 — AlphaEarth Explorer

![Deforestation event example](content/deforestation.png)

This repository contains the materials for the osapiens Makeathon 2026
challenge. The original brief asked for deforestation detection from raw
multimodal satellite data (Sentinel-1, Sentinel-2, weak labels). We pivoted
the in-repo demo to the **AlphaEarth Foundations (AEF) embeddings** so we
can showcase the kind of "embedding viewer + scatter + classifier"
workflow demonstrated in the AlphaEarth workshop, while still using the
weak deforestation labels as the supervised signal.

## Start here

1. [osapiens-challenge-full-description.md](./osapiens-challenge-full-description.md)
   — written challenge brief and context.
2. [challenge.ipynb](./challenge.ipynb) — original walkthrough of the dataset
   structure, label encodings and visualisations.
3. [download_data.py](./download_data.py) — dataset download entrypoint.
4. **[alphaearth/](./alphaearth/)** — new Python package powering the AEF
   explorer (paths, IO, PCA previews, PCA/UMAP scatter, SVM/MLP classifiers,
   mislabel detection).
5. **[run_aef.py](./run_aef.py)** — CLI wrapping the package.

## Setup

```bash
make install
```

`make install` creates `.venv` and installs `requirements.txt`. The
explorer needs a few extras over the original baseline — `umap-learn`,
`scipy`, `Pillow` — which are already pinned in
[requirements.txt](./requirements.txt).

### GPU note

The AEF explorer is **CPU only** by design (sklearn `LinearSVC` /
`MLPClassifier`, plus PCA/UMAP). For optional PyTorch demos at the repo
root (e.g. `prithvi.py`), install a CUDA build of torch and set
`TORCH_DEVICE=cuda` — see `../requirements-gpu.txt` and the
`install_torch_cuda` Makefile target.

### Download the dataset

```bash
make download_data_from_s3
```

The explorer expects at minimum the `aef-embeddings/` and `labels/`
subtrees. Sentinel-1/2 are still useful for ad-hoc inspection in the
notebook but are *not* required by `run_aef.py` or the FastAPI backend.

## Dataset layout

```text
data/makeathon-challenge/
├── aef-embeddings/
│   ├── train/{tile_id}_{year}.tiff       (64-band float32, 1004x998)
│   └── test/{tile_id}_{year}.tiff
├── labels/train/
│   ├── gladl/   per-year GLAD Landsat alerts (gladl_{tile}_alert{YY}.tif)
│   ├── glads2/  GLAD Sentinel-2 alerts (single accumulated raster per tile)
│   └── radd/    RADD alerts (single accumulated raster per tile)
├── metadata/
│   ├── train_tiles.geojson
│   └── test_tiles.geojson
└── sentinel-1/, sentinel-2/   (optional; not used by AEF explorer)
```

## CLI examples

```bash
# Show every (tile, year) discovered on disk:
python run_aef.py tiles

# Pre-render PCA-3 false-colour PNGs (cached under runs/aef/previews/):
python run_aef.py previews --split all
# or:
make previews

# UMAP scatter from labelled pixels of two tile-years (gladl labels, 2k each):
python run_aef.py scatter --method umap \
  --tile 18NWG_6_6:2022 --tile 18NWG_6_6:2023 \
  --label-source gladl --sample 2000

# Train an MLP on three years and evaluate on a fourth:
python run_aef.py classify --model mlp \
  --train 18NWG_6_6:2021 --train 18NWG_6_6:2022 --train 18NWG_6_6:2023 \
  --val 18NWG_6_6:2024 --test 18NWG_6_6:2025 \
  --label-source gladl --sample 4000

# Inspect mislabel regions for the run printed by the previous command:
python run_aef.py mislabels --model-id <id> --top 20
```

All CLI commands honour the same path resolution as the FastAPI backend
(`MAKEATHON_DATA_DIR` env > `./data/...` defaults). Cached artifacts live
under `runs/aef/` (override with `AEF_CACHE_DIR`).

## Migrating from `solution/`

The legacy GLAD/Sentinel `solution/` package and its `runs/baseline/`
artifacts have been removed. The previous CLI (`run_solution.py`) is now a
thin shim that simply forwards to `run_aef.py`. Update any scripts to
invoke `run_aef.py` directly.

## Backend & frontend

- The FastAPI backend is at [`../backend/`](../backend/) and exposes the
  AEF explorer over HTTP (`/api/aef/*`). It re-uses this package
  in-process via `sys.path`, so the CLI and the API always agree on the
  data they see.
- The frontend (Vite/React) is at [`../frontend/`](../frontend/) and talks
  to the backend exclusively over those endpoints.
