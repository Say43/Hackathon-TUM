"""CLI entrypoint for the AlphaEarth Foundations explorer.

Examples
--------

# Pre-render PCA preview PNGs for every available train tile / year:
python run_aef.py previews --split train

# Pre-compute UMAP scatter for two train tiles, gladl labels, 2k pixels each:
python run_aef.py scatter --method umap \\
    --tile 18NWG_6_6:2022 --tile 18NWG_6_6:2023 \\
    --label-source gladl --sample 2000

# Train an MLP on three years, evaluate on a held-out year:
python run_aef.py classify --model mlp \\
    --train 18NWG_6_6:2021 --train 18NWG_6_6:2022 --train 18NWG_6_6:2023 \\
    --val 18NWG_6_6:2024 --test 18NWG_6_6:2025 \\
    --label-source gladl --sample 4000

# Inspect mislabels from the most recent run:
python run_aef.py mislabels --model-id <id-printed-by-classify>
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from alphaearth import cache as aef_cache
from alphaearth import classifiers, mislabels, paths, previews, scatter
from alphaearth.io import open_aef_tile
from alphaearth.paths import Paths, TileYear, discover_tiles, resolve_cache_dir, resolve_data_dir
from alphaearth.scatter import (
    ScatterRequest,
    cached_scatter,
    parse_tile_year_list,
    parse_tile_year_string,
)
from alphaearth.classifiers import ClassifyRequest, run_classifier


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _common_paths(args: argparse.Namespace) -> tuple[Paths, Path]:
    data_dir = resolve_data_dir(getattr(args, "data_dir", None))
    cache_dir = resolve_cache_dir(getattr(args, "cache_dir", None))
    aef_cache.ensure_dir(cache_dir)
    logging.info("data_dir = %s", data_dir)
    logging.info("cache_dir = %s", cache_dir)
    return Paths(data_dir=data_dir), cache_dir


def cmd_tiles(args: argparse.Namespace) -> int:
    p, _ = _common_paths(args)
    out = {split: discover_tiles(p, split) for split in ("train", "test")}
    json.dump(out, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")
    return 0


def cmd_previews(args: argparse.Namespace) -> int:
    p, cache_dir = _common_paths(args)
    splits = ["train", "test"] if args.split == "all" else [args.split]
    rendered = []
    for split in splits:
        for tile, years in discover_tiles(p, split).items():
            for year in years:
                out = previews.cached_pca_preview(
                    p, cache_dir, tile, year, split, refresh=args.refresh
                )
                rendered.append(str(out))
                logging.info("preview ready: %s", out)
    print(f"rendered {len(rendered)} PCA preview PNG(s)")
    return 0


def cmd_scatter(args: argparse.Namespace) -> int:
    p, cache_dir = _common_paths(args)
    tiles = parse_tile_year_list(args.tile, default_split="train")
    request = ScatterRequest(
        method=args.method,
        tiles=tiles,
        label_source=args.label_source,
        sample_per_tile=args.sample,
        seed=args.seed,
    )
    payload = cached_scatter(p, cache_dir, request, refresh=args.refresh)
    print(json.dumps({k: v for k, v in payload.items() if k != "points"} | {"points": len(payload["points"])}, indent=2))
    return 0


def cmd_classify(args: argparse.Namespace) -> int:
    p, cache_dir = _common_paths(args)
    train_tiles = parse_tile_year_list(args.train, default_split="train")
    val_tile = parse_tile_year_string(args.val, default_split="train") if args.val else None
    test_tile = parse_tile_year_string(args.test, default_split=args.test_split)
    request = ClassifyRequest(
        model=args.model,
        train_tiles=train_tiles,
        val_tile=val_tile,
        test_tile=test_tile,
        label_source=args.label_source,
        sample_per_tile=args.sample,
        seed=args.seed,
    )
    payload = run_classifier(p, cache_dir, request, refresh=args.refresh)
    print(json.dumps(payload, indent=2))
    return 0


def cmd_mislabels(args: argparse.Namespace) -> int:
    p, cache_dir = _common_paths(args)
    payload = mislabels.cached_mislabels(
        p, cache_dir, args.model_id, top=args.top, refresh=args.refresh
    )
    print(json.dumps(payload, indent=2))
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    p, _ = _common_paths(args)
    raster = open_aef_tile(p, args.tile, args.year, args.split)
    print(json.dumps(previews.channel_stats(raster), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="run_aef.py", description="AlphaEarth explorer CLI")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--data-dir", default=None, help="Override the dataset root.")
    parser.add_argument("--cache-dir", default=None, help="Override AEF_CACHE_DIR.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_tiles = sub.add_parser("tiles", help="List discovered AEF tiles per split.")
    p_tiles.set_defaults(func=cmd_tiles)

    p_prev = sub.add_parser("previews", help="Pre-render PCA-3 preview PNGs.")
    p_prev.add_argument("--split", choices=("train", "test", "all"), default="all")
    p_prev.add_argument("--refresh", action="store_true")
    p_prev.set_defaults(func=cmd_previews)

    p_sc = sub.add_parser("scatter", help="Compute and cache a PCA/UMAP scatter.")
    p_sc.add_argument("--method", choices=("pca", "umap"), required=True)
    p_sc.add_argument("--tile", action="append", required=True, help="tile:year[:split]")
    p_sc.add_argument("--label-source", required=True, choices=("gladl", "glads2", "radd"))
    p_sc.add_argument("--sample", type=int, default=2000)
    p_sc.add_argument("--seed", type=int, default=42)
    p_sc.add_argument("--refresh", action="store_true")
    p_sc.set_defaults(func=cmd_scatter)

    p_cl = sub.add_parser("classify", help="Train a classifier and dump artifacts.")
    p_cl.add_argument("--model", choices=("svm", "mlp"), required=True)
    p_cl.add_argument("--train", action="append", required=True, help="tile:year[:split]")
    p_cl.add_argument("--val", default=None, help="tile:year[:split]")
    p_cl.add_argument("--test", required=True, help="tile:year[:split]")
    p_cl.add_argument("--test-split", default="train", choices=("train", "test"))
    p_cl.add_argument("--label-source", required=True, choices=("gladl", "glads2", "radd"))
    p_cl.add_argument("--sample", type=int, default=4000)
    p_cl.add_argument("--seed", type=int, default=42)
    p_cl.add_argument("--refresh", action="store_true")
    p_cl.set_defaults(func=cmd_classify)

    p_ml = sub.add_parser("mislabels", help="Compute mislabel regions for a run.")
    p_ml.add_argument("--model-id", required=True)
    p_ml.add_argument("--top", type=int, default=20)
    p_ml.add_argument("--refresh", action="store_true")
    p_ml.set_defaults(func=cmd_mislabels)

    p_st = sub.add_parser("stats", help="Per-band statistics for one tile/year.")
    p_st.add_argument("--tile", required=True)
    p_st.add_argument("--year", type=int, required=True)
    p_st.add_argument("--split", default="train", choices=("train", "test"))
    p_st.set_defaults(func=cmd_stats)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    _configure_logging(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
