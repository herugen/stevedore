"""Prefect Block wrapper for uploading artifacts to MinIO via S3 protocol."""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from prefect.blocks.core import Block
from prefect_aws.s3 import S3Bucket


class MinIOBucket(Block):
    """Stores MinIO connectivity info and target bucket details."""

    _block_type_name = "MinIO Bucket"
    _description = "Configuration for interacting with MinIO via S3-compatible APIs."

    bucket_block_name: str = Field(
        ...,
        description=(
            "Name of a Prefect `S3Bucket` block that contains credentials and endpoint "
            "configuration for the target MinIO cluster."
        ),
        example="minio-assets",
    )
    bucket_path_prefix: Optional[str] = Field(
        default=None,
        description="Optional prefix to prepend to uploaded object keys (e.g. folder path).",
        example="/",
    )

    async def load_bucket(self) -> S3Bucket:
        """Load the configured S3Bucket block instance."""

        return await S3Bucket.load(self.bucket_block_name)


__all__ = ["MinIOBucket"]

