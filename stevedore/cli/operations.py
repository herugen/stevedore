"""Reusable operations for the stevedore CLI commands."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from stevedore.blocks import CobaltSettings, MinIOBucket
from stevedore.deployments.local_download_worker import deploy as deploy_local_downloads

from prefect_aws.credentials import AwsCredentials
from prefect_aws.s3 import S3Bucket
from dotenv import load_dotenv


def load_env_file(path: Path) -> None:
    """Load environment variables from a ``.env`` file into ``os.environ``."""

    if not path.exists():
        raise FileNotFoundError(f"Environment file not found: {path}")

    load_dotenv(path, override=True)


def ensure_work_pool(name: str, pool_type: str, overwrite: bool = False) -> None:
    """Ensure a Prefect work pool with the given configuration exists."""

    command = [
        "prefect",
        "work-pool",
        "create",
        name,
        "--type",
        pool_type,
    ]

    if overwrite:
        command.append("--overwrite")

    result = subprocess.run(command, check=False, capture_output=True, text=True)

    if result.returncode == 0:
        if result.stdout:
            print(result.stdout.strip())
        return

    stderr = result.stderr.strip()
    if "already exists" in stderr and not overwrite:
        print(f"Work pool '{name}' already exists. Use --overwrite to update.")
        return

    raise subprocess.CalledProcessError(
        result.returncode,
        command,
        output=result.stdout,
        stderr=result.stderr,
    )


def register_blocks() -> None:
    """Persist local development Prefect blocks."""

    cobalt_base_url = os.environ["COBALT_BASE_URL"]

    minio_endpoint = os.environ["MINIO_ENDPOINT"]
    minio_bucket_name = os.environ["MINIO_BUCKET"]
    minio_access_key = os.environ["MINIO_ACCESS_KEY"]
    minio_secret_key = os.environ["MINIO_SECRET_KEY"]
    minio_path_prefix = os.getenv("MINIO_PATH_PREFIX")

    cobalt_settings = CobaltSettings(
        base_url=cobalt_base_url,
        request_timeout_seconds=30,
        download_timeout_seconds=1800,
    )
    cobalt_settings.save("local-cobalt", overwrite=True)

    aws_credentials = AwsCredentials(
        aws_access_key_id=minio_access_key,
        aws_secret_access_key=minio_secret_key,
        region_name="us-east-1",
    )
    aws_credentials.save("minio-local-creds", overwrite=True)

    s3_bucket = S3Bucket(
        bucket_name=minio_bucket_name,
        credentials=aws_credentials,
        endpoint_url=minio_endpoint,
        aws_region="us-east-1",
    )
    s3_bucket.save("minio-local-bucket", overwrite=True)

    minio_bucket = MinIOBucket(
        bucket_block_name="minio-local-bucket",
        bucket_path_prefix=minio_path_prefix,
    )
    minio_bucket.save("local-minio-assets", overwrite=True)

    print("Registered Prefect blocks:")
    print("  - CobaltSettings: local-cobalt")
    print("  - AwsCredentials: minio-local-creds")
    print("  - S3Bucket: minio-local-bucket")
    print("  - MinIOBucket: local-minio-assets")


def apply_deployments() -> None:
    """Apply all local deployments defined in the repository."""

    deploy_local_downloads()





