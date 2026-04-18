import argparse
import logging
import math
from pathlib import Path

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DEFAULT_BUCKET_NAME = "osapiens-terra-challenge"
DEFAULT_FOLDER_NAME = "makeathon-challenge"
DEFAULT_LOCAL_DIR = "./model-training/data/abdul-testrun"
DEFAULT_SAMPLE_RATIO = 0.02
DEFAULT_SAMPLE_OFFSET = 1


def _list_s3_keys(bucket_name: str, prefix: str) -> list[str]:
    s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
    paginator = s3.get_paginator("list_objects_v2")
    keys: list[str] = []

    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        if "Contents" not in page:
            continue
        for obj in page["Contents"]:
            key = obj["Key"]
            if key.endswith("/"):
                continue
            keys.append(key)
    return keys


def _extract_tile_ref(key: str, root_prefix: str) -> tuple[str, str] | None:
    rel = key[len(root_prefix) :] if key.startswith(root_prefix) else key
    parts = rel.split("/")
    if len(parts) < 3:
        return None

    top = parts[0]
    split = parts[1]

    if top == "metadata":
        return None
    if top == "aef-embeddings":
        item = parts[2]
        stem = Path(item).stem
        return split, "_".join(stem.split("_")[:3])
    if top in {"sentinel-1", "sentinel-2"}:
        item = parts[2]
        return split, item.split("__")[0]
    if top == "labels" and split == "train" and len(parts) >= 4:
        source = parts[2]
        item = parts[3]
        if source not in {"gladl", "glads2", "radd"}:
            return None
        stem = Path(item).stem
        pieces = stem.split("_")
        if len(pieces) >= 4:
            return "train", "_".join(pieces[1:4])
        return None
    return None


def _select_window(tile_ids: set[str], sample_ratio: float, sample_offset: int) -> set[str]:
    ordered = sorted(tile_ids)
    sample_count = max(1, math.ceil(len(ordered) * sample_ratio))
    if sample_count >= len(ordered):
        return set(ordered)
    max_start = max(0, len(ordered) - sample_count)
    start = min(max(sample_offset, 0), max_start)
    return set(ordered[start : start + sample_count])


def _choose_tile_ids(
    keys: list[str],
    prefix: str,
    sample_ratio: float,
    sample_offset: int,
) -> tuple[set[str], set[str]]:
    labelled_train_tile_ids: set[str] = set()
    test_tile_ids: set[str] = set()
    for key in keys:
        tile_ref = _extract_tile_ref(key, prefix)
        if not tile_ref:
            continue
        split, tile_id = tile_ref
        rel = key[len(prefix) :] if key.startswith(prefix) else key
        if split == "train" and rel.startswith("labels/train/"):
            labelled_train_tile_ids.add(tile_id)
        elif split == "test":
            test_tile_ids.add(tile_id)

    if not labelled_train_tile_ids:
        raise RuntimeError("No labelled train tile ids found while building the 2% sample.")
    if not test_tile_ids:
        raise RuntimeError("No test tile ids found while building the 2% sample.")

    selected_train = _select_window(labelled_train_tile_ids, sample_ratio, sample_offset)
    selected_test = _select_window(test_tile_ids, sample_ratio, sample_offset)
    logger.info(
        "Selected %d/%d labelled train tile ids and %d/%d test tile ids for Abdul test run (offset=%d).",
        len(selected_train),
        len(labelled_train_tile_ids),
        len(selected_test),
        len(test_tile_ids),
        sample_offset,
    )
    return selected_train, selected_test


def _filter_keys_for_sample(
    keys: list[str],
    prefix: str,
    selected_train_tile_ids: set[str],
    selected_test_tile_ids: set[str],
) -> list[str]:
    selected_keys: list[str] = []

    for key in keys:
        rel = key[len(prefix) :] if key.startswith(prefix) else key
        if rel.startswith("metadata/"):
            selected_keys.append(key)
            continue

        tile_ref = _extract_tile_ref(key, prefix)
        if not tile_ref:
            continue
        split, tile_id = tile_ref
        if split == "train" and tile_id in selected_train_tile_ids:
            selected_keys.append(key)
        if split == "test" and tile_id in selected_test_tile_ids:
            selected_keys.append(key)

    return selected_keys


def download_s3_folder(
    bucket_name: str,
    folder_name: str,
    local_dir: str = DEFAULT_LOCAL_DIR,
    sample_ratio: float = DEFAULT_SAMPLE_RATIO,
    sample_offset: int = DEFAULT_SAMPLE_OFFSET,
) -> None:
    """Download a small, coherent subset of the Makeathon dataset for Abdul's test run."""
    if not 0 < sample_ratio <= 1:
        raise ValueError("sample_ratio must be in the range (0, 1].")

    s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
    prefix = folder_name.strip("/")
    if prefix:
        prefix = f"{prefix}/"

    local_path = Path(local_dir)
    local_path.mkdir(parents=True, exist_ok=True)

    try:
        keys = _list_s3_keys(bucket_name, prefix)
        if not keys:
            logger.warning(
                "No objects found in folder '%s' in bucket '%s'",
                folder_name,
                bucket_name,
            )
            return

        selected_train_tile_ids, selected_test_tile_ids = _choose_tile_ids(
            keys,
            prefix,
            sample_ratio,
            sample_offset,
        )
        selected_keys = _filter_keys_for_sample(
            keys,
            prefix,
            selected_train_tile_ids,
            selected_test_tile_ids,
        )

        for key in selected_keys:
            target = local_path / key
            target.parent.mkdir(parents=True, exist_ok=True)
            logger.info("Downloading %s -> %s", key, target)
            s3.download_file(bucket_name, key, str(target))

        logger.info(
            "Successfully downloaded %d files for Abdul test run into '%s'",
            len(selected_keys),
            local_dir,
        )

    except NoCredentialsError:
        logger.error("AWS credentials not found.")
        raise
    except ClientError as exc:
        logger.error("AWS client error: %s", exc)
        raise


def verify_download(local_dir: str = DEFAULT_LOCAL_DIR, folder_name: str = DEFAULT_FOLDER_NAME) -> None:
    dataset_root = Path(local_dir) / folder_name
    required = [
        dataset_root / "metadata",
        dataset_root / "sentinel-1",
        dataset_root / "sentinel-2",
        dataset_root / "aef-embeddings",
        dataset_root / "labels" / "train" / "gladl",
        dataset_root / "labels" / "train" / "glads2",
        dataset_root / "labels" / "train" / "radd",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Downloaded Abdul test run is incomplete. Missing: {missing}")

    tif_count = sum(1 for _ in dataset_root.rglob("*.tif"))
    tiff_count = sum(1 for _ in dataset_root.rglob("*.tiff"))
    geojson_count = sum(1 for _ in dataset_root.rglob("*.geojson"))
    train_label_count = sum(1 for _ in (dataset_root / "labels" / "train").rglob("*.tif"))

    if train_label_count == 0:
        raise FileNotFoundError(f"No weak-label rasters found below {dataset_root / 'labels' / 'train'}")

    logger.info("Verification successful for %s", dataset_root)
    logger.info("Found %d .tif files", tif_count)
    logger.info("Found %d .tiff files", tiff_count)
    logger.info("Found %d .geojson files", geojson_count)
    logger.info("Found %d weak-label rasters", train_label_count)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download a 2%% Makeathon subset for Abdul's test run and verify it."
    )
    parser.add_argument("--bucket_name", default=DEFAULT_BUCKET_NAME, help="Name of the S3 bucket")
    parser.add_argument("--folder_name", default=DEFAULT_FOLDER_NAME, help="Name of the folder inside the S3 bucket")
    parser.add_argument("--local_dir", default=DEFAULT_LOCAL_DIR, help="Local directory to save files")
    parser.add_argument("--sample_ratio", type=float, default=DEFAULT_SAMPLE_RATIO, help="Fraction of tile ids to keep")
    parser.add_argument(
        "--sample_offset",
        type=int,
        default=DEFAULT_SAMPLE_OFFSET,
        help="Start offset into the sorted tile-id list, to select a different but equally sized sample",
    )
    args = parser.parse_args()

    download_s3_folder(
        bucket_name=args.bucket_name,
        folder_name=args.folder_name,
        local_dir=args.local_dir,
        sample_ratio=args.sample_ratio,
        sample_offset=args.sample_offset,
    )
    verify_download(local_dir=args.local_dir, folder_name=args.folder_name)
