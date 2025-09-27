"""Utility script to register local Prefect blocks for Cobalt and MinIO.

Environment variables:
    Read from `profiles/local.env` via docker-compose `env_file` or manual export.
"""

from __future__ import annotations

import os

from prefect_aws.credentials import AwsCredentials
from prefect_aws.s3 import S3Bucket

from stevedore.blocks import CobaltSettings, MinIOBucket


def main() -> None:
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


if __name__ == "__main__":
    main()

