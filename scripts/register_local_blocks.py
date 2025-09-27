"""Utility script to register local Prefect blocks for Cobalt and MinIO.

Usage:
    uv run python scripts/register_local_blocks.py
    # or: poetry run python scripts/register_local_blocks.py

Environment variables (with sensible defaults for local development):
    COBALT_BASE_URL=http://localhost:9100
    MINIO_ENDPOINT=http://127.0.0.1:9100
    MINIO_BUCKET=stevedore
    MINIO_ACCESS_KEY=admin
    MINIO_SECRET_KEY=admin123
    MINIO_PATH_PREFIX=None
"""

from __future__ import annotations

import os

os.environ.setdefault("PREFECT_API_URL", "http://127.0.0.1:4200/api")

from prefect_aws.credentials import AwsCredentials
from prefect_aws.s3 import S3Bucket

from stevedore.blocks import CobaltSettings, MinIOBucket


def main() -> None:
    cobalt_base_url = os.getenv("COBALT_BASE_URL", "http://localhost:9100")

    minio_endpoint = os.getenv("MINIO_ENDPOINT", "http://127.0.0.1:9100")
    minio_bucket_name = os.getenv("MINIO_BUCKET", "stevedore")
    minio_access_key = os.getenv("MINIO_ACCESS_KEY", "admin")
    minio_secret_key = os.getenv("MINIO_SECRET_KEY", "admin123")
    minio_path_prefix = os.getenv("MINIO_PATH_PREFIX", None)

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


if __name__ == "__main__":
    main()

