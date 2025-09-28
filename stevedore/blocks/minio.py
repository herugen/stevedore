"""Prefect Block wrapper for uploading artifacts to MinIO via S3 protocol."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import Field

from prefect.blocks.core import Block
from prefect_aws.s3 import S3Bucket
from botocore.exceptions import ClientError
from prefect.utilities.asyncutils import run_sync_in_worker_thread


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

    async def head_object(
        self,
        key: str,
        *,
        bucket: Optional[S3Bucket] = None,
    ) -> dict[str, Any]:
        """Return HEAD metadata for the given object key."""

        bucket = bucket or await self.load_bucket()
        resolved_key = bucket._resolve_path(key)
        client = bucket._get_s3_client()

        return await run_sync_in_worker_thread(
            client.head_object,
            Bucket=bucket.bucket_name,
            Key=resolved_key,
        )

    async def object_exists(self, key: str, *, bucket: Optional[S3Bucket] = None) -> bool:
        """Return True if the object exists in the configured bucket."""

        try:
            await self.head_object(key, bucket=bucket)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code") if hasattr(exc, "response") else None
            if error_code in {"404", "NoSuchKey"}:
                return False
            raise

        return True


__all__ = ["MinIOBucket"]

