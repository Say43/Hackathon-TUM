# Baseline Solution — Deforestation Detection

A runnable, end-to-end baseline for the osapiens Makeathon 2026 deforestation
challenge. It fuses the three weak-label sources (RADD, GLAD-L, GLAD-S2),
builds per-pixel features from Sentinel-1, Sentinel-2 and AlphaEarth
Foundations embeddings, trains a gradient-boosted classifier, and writes a
leaderboard-ready `submission.geojson`.

> This is intentionally a **strong baseline**, not a state-of-the-art
> solution. It's optimised for clarity, reproducibility and CPU-only runtime.
> Hook your own deep model into `solution/model.py` when you're ready.

## 1. Point the code at your data

If your data is not in `./data/makeathon-challenge`, set one of:

```bash
# option A – environment variable (persists in the shell)
export MAKEATHON_DATA_DIR=/abs/path/to/makeathon-challenge

# option B – pass --data-dir explicitly on every command
python run_solution.py train --data-dir /abs/path/to/makeathon-challenge ...
```

The folder you point to must contain `sentinel-1/`, `sentinel-2/`,
`aef-embeddings/`, `labels/`, `metadata/` (exactly as produced by
`make download_data_from_s3`).

## 2. Install dependencies

```bash
make install
source .venv/bin/activate
```

(`scikit-learn` and `joblib` were added to `requirements.txt` for this
solution.)

## 3. Run the full pipeline

```bash
python run_solution.py all \
    --data-dir /abs/path/to/makeathon-challenge \
    --run-dir runs/baseline
```

Output structure:

```text
runs/baseline/
├── model.joblib              # trained classifier + feature schema
├── predictions/              # one binary GeoTIFF per test tile
│   └── pred_<tile_id>.tif
├── geojson/                  # one GeoJSON per tile (EPSG:4326)
│   └── <tile_id>.geojson
└── submission.geojson        # merged FeatureCollection – upload this
```

### Run the steps individually

```bash
python run_solution.py train   --data-dir ... --model-out runs/baseline/model.joblib
python run_solution.py predict --data-dir ... --model  runs/baseline/model.joblib \
                               --pred-dir runs/baseline/predictions
python run_solution.py submit  --pred-dir   runs/baseline/predictions \
                               --geojson-dir runs/baseline/geojson \
                               --out runs/baseline/submission.geojson
```

Useful flags:

* `--max-tiles N` (on `train` / `all`) — only use the first N labelled tiles
  while you iterate.
* `--threshold 0.4` (on `predict` / `all`) — lower values produce more
  positive pixels (higher recall, lower precision).
* `--min-area-ha 0.5` (on `submit` / `all`) — polygons smaller than this
  are dropped; the challenge brief mentions 0.5 ha as a reasonable floor.

## 4. How it works

```mermaid
flowchart LR
    A[Sentinel-2 stack<br/>T×12×H×W] --> F[Per-pixel features]
    B[Sentinel-1 stack<br/>T×1×H×W] --> F
    C[AEF embedding<br/>64×H×W] --> F
    D[GLAD-L + GLAD-S2 + RADD] --> L[Fused label<br/>(≥2 sources vote)]
    F --> M[HistGradientBoosting]
    L --> M
    M --> P[Probability raster]
    P --> BIN[Threshold → binary GeoTIFF]
    BIN --> GJ[raster_to_geojson → submission]
```

### Design choices

* **Per-pixel temporal summaries.** We collapse the time axis with
  nan-aware mean / std / min / max / early-vs-late trend. Indices:
  NDVI, NBR, NDMI. AEF embeddings are averaged across years. This gives
  ~100 features per pixel and lets a tabular model exploit the signal
  without expensive sequence modelling.
* **Robust to missing data.** Sentinel-2 `0` values and Sentinel-1 `≤0`
  values are treated as NaN. `HistGradientBoostingClassifier` consumes
  NaNs directly, so we never impute artificial values.
* **Label fusion.** A pixel is *positive* when at least two of the three
  weak-label sources flag it (falls back to one if only one source is
  available for the tile). Confident negatives are pixels no source
  flagged. Everything in between is excluded from training.
* **Class-balanced sampling.** Up to 40k pixels per tile are drawn with
  a configurable positive fraction (default 50%). This keeps the training
  matrix small (~tens of millions of rows scale is avoided) while giving
  the model enough positives to learn from.
* **Submission on the S2 grid.** Every raster read is reprojected to the
  target tile's Sentinel-2 grid via `rasterio.vrt.WarpedVRT`. The final
  prediction GeoTIFF shares that grid, which `submission_utils.raster_to_geojson`
  then converts to EPSG:4326 polygons with a hectare filter.

### Knobs to tune

Everything sits in `solution/config.py`:

| Setting | Default | Meaning |
| --- | --- | --- |
| `PIXELS_PER_TILE` | 40_000 | sampled pixels per train tile |
| `POSITIVE_FRACTION` | 0.5 | class balance when sampling |
| `BINARY_THRESHOLD` | 0.5 | probability cut-off for the submission |
| `MIN_AREA_HA` | 0.5 | polygon size filter in hectares |
| `N_POS_SOURCES` (in `labels.py`) | 2 | how many label sources must agree |

## 5. Extending this baseline

Good next steps, in order of impact-per-effort:

1. **Swap the classifier.** LightGBM / XGBoost usually beat HGB on this
   type of tabular data — change the class in `solution/model.py`.
2. **Patch-based CNN / U-Net.** Replace `build_training_matrix` with a
   dataset that yields ``(32×32)`` patches of the feature cube + fused
   label; train a small PyTorch model.
3. **Temporal models.** Pass the raw `(T, C, H, W)` stack through a 1D
   CNN / Transformer along the time axis instead of collapsing to
   summary statistics.
4. **Label-noise handling.** Replace the voting rule with a soft-label
   estimate (e.g. Dawid–Skene on the three sources) and train with
   sample weights.
5. **Geographic cross-validation.** Hold out whole tiles from specific
   regions to estimate how well the model generalises.

## 6. Troubleshooting

* **`Dataset root not found`** — pass `--data-dir`, set
  `MAKEATHON_DATA_DIR`, or move the dataset to `./data/makeathon-challenge`.
* **`No labelled training tiles discovered`** — your dataset is missing
  `labels/train/{gladl,glads2,radd}/`. Re-run `make download_data_from_s3`.
* **Predictions are all zeros** — try `--threshold 0.3` first; your weak
  labels may have very few positives for that tile.
* **Out of memory on large tiles** — lower `PRED_CHUNK_ROWS` in
  `solution/config.py`.
