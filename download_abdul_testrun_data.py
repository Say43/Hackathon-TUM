import argparse
import logging
import math
from collections import defaultdict
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


def _extract_tile_id(key: str, root_prefix: str) -> str | None:
    rel = key[len(root_prefix) :] if key.startswith(root_prefix) else key
    parts = rel.split("/")
    if len(parts) < 3:
        return None

    top = parts[0]
    split = parts[1]
    item = parts[2]

    if top == "metadata":
        return None
    if top == "aef-embeddings":
        stem = Path(item).stem
        return "_".join(stem.split("_")[:3])
    if top in {"sentinel-1", "sentinel-2"}:
        return item.split("__")[0]
    if top == "labels" and split == "train":
        stem = Path(item).stem
        pieces = stem.split("_")
        return "_".join(pieces[1:4]) if len(pieces) >= 4 else None
    return None


def _choose_tile_ids(keys: list[str], prefix: str, sample_ratio: float) -> set[str]:
    grouped: dict[str, set[str]] = defaultdict(set)

    for key in keys:
        tile_id = _extract_tile_id(key, prefix)
        if tile_id:
            grouped["all"].add(tile_id)

    all_tile_ids = sorted(grouped["all"])
    if not all_tile_ids:
        raise RuntimeError("No tile ids found while building the 2% sample.")

    sample_count = max(1, math.ceil(len(all_tile_ids) * sample_ratio))
    selected = set(all_tile_ids[:sample_count])
    logger.info("Selected %d/%d tile ids for Abdul test run.", len(selected), len(all_tile_ids))
    return selected


def _filter_keys_for_sample(keys: list[str], prefix: str, selected_tile_ids: set[str]) -> list[str]:
    selected_keys: list[str] = []

    for key in keys:
        rel = key[len(prefix) :] if key.startswith(prefix) else key
        if rel.startswith("metadata/"):
            selected_keys.append(key)
            continue

        tile_id = _extract_tile_id(key, prefix)
        if tile_id in selected_tile_ids:
            selected_keys.append(key)

    return selected_keys


def download_s3_folder(
    bucket_name: str,
    folder_name: str,
    local_dir: str = DEFAULT_LOCAL_DIR,
    sample_ratio: float = DEFAULT_SAMPLE_RATIO,
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

        selected_tile_ids = _choose_tile_ids(keys, prefix, sample_ratio)
        selected_keys = _filter_keys_for_sample(keys, prefix, selected_tile_ids)

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
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Downloaded Abdul test run is incomplete. Missing: {missing}")

    tif_count = sum(1 for _ in dataset_root.rglob("*.tif"))
    tiff_count = sum(1 for _ in dataset_root.rglob("*.tiff"))
    geojson_count = sum(1 for _ in dataset_root.rglob("*.geojson"))

    logger.info("Verification successful for %s", dataset_root)
    logger.info("Found %d .tif files", tif_count)
    logger.info("Found %d .tiff files", tiff_count)
    logger.info("Found %d .geojson files", geojson_count)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download a 2%% Makeathon subset for Abdul's test run and verify it."
    )
    parser.add_argument("--bucket_name", default=DEFAULT_BUCKET_NAME, help="Name of the S3 bucket")
    parser.add_argument("--folder_name", default=DEFAULT_FOLDER_NAME, help="Name of the folder inside the S3 bucket")
    parser.add_argument("--local_dir", default=DEFAULT_LOCAL_DIR, help="Local directory to save files")
    parser.add_argument("--sample_ratio", type=float, default=DEFAULT_SAMPLE_RATIO, help="Fraction of tile ids to keep")
    args = parser.parse_args()

    download_s3_folder(
        bucket_name=args.bucket_name,
        folder_name=args.folder_name,
        local_dir=args.local_dir,
        sample_ratio=args.sample_ratio,
    )
    verify_download(local_dir=args.local_dir, folder_name=args.folder_name)
