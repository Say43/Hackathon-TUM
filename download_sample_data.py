import argparse
import logging
from pathlib import Path

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DEFAULT_BUCKET_NAME = "osapiens-terra-challenge"
DEFAULT_FOLDER_NAME = "makeathon-challenge"
DEFAULT_LOCAL_DIR = "example data"


def download_s3_folder(
    bucket_name: str, folder_name: str, local_dir: str = DEFAULT_LOCAL_DIR
) -> None:
    """Download a public S3 folder into a local directory."""
    s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
    prefix = folder_name.strip("/")
    if prefix:
        prefix = f"{prefix}/"

    local_path = Path(local_dir)
    local_path.mkdir(parents=True, exist_ok=True)

    try:
        paginator = s3.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            if "Contents" not in page:
                logger.warning(
                    "No objects found in folder '%s' in bucket '%s'",
                    folder_name,
                    bucket_name,
                )
                return

            for obj in page["Contents"]:
                key = obj["Key"]

                if key.endswith("/") or key == prefix:
                    logger.debug("Skipping directory placeholder: %s", key)
                    continue

                relative_key = key[len(prefix) :] if prefix and key.startswith(prefix) else key
                target = local_path / relative_key
                target.parent.mkdir(parents=True, exist_ok=True)

                logger.info("Downloading %s -> %s", key, target)
                s3.download_file(bucket_name, key, str(target))

        logger.info(
            "Successfully downloaded folder '%s' from bucket '%s' to '%s'",
            folder_name,
            bucket_name,
            local_dir,
        )

    except NoCredentialsError:
        logger.error("AWS credentials not found.")
        raise
    except ClientError as exc:
        logger.error("AWS client error: %s", exc)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download a folder from a public S3 bucket into example data."
    )
    parser.add_argument(
        "--bucket_name",
        default=DEFAULT_BUCKET_NAME,
        help=f"Name of the S3 bucket. Default: {DEFAULT_BUCKET_NAME}",
    )
    parser.add_argument(
        "--folder_name",
        default=DEFAULT_FOLDER_NAME,
        help=f"Name of the folder inside the S3 bucket. Default: {DEFAULT_FOLDER_NAME}",
    )
    parser.add_argument(
        "--local_dir",
        default=DEFAULT_LOCAL_DIR,
        help=f"Local directory to save files. Default: {DEFAULT_LOCAL_DIR}",
    )
    args = parser.parse_args()

    download_s3_folder(args.bucket_name, args.folder_name, args.local_dir)


if __name__ == "__main__":
    main()
