"""Prefect flow wrapping the Cobalt download task."""

from __future__ import annotations

from typing import Optional

from prefect import flow

from stevedore.tasks import download_video_asset


@flow(name="Cobalt Video Download")
async def cobalt_video_download_flow(
    source_url: str,
    task_id: str,
    cobalt_settings_block: str = "local-cobalt",
    minio_bucket_block: str = "local-minio-assets",
    object_name: Optional[str] = None,
) -> str:
    """Download a video via Cobalt and persist it to MinIO."""

    return await download_video_asset(
        source_url=source_url,
        task_id=task_id,
        cobalt_settings_block=cobalt_settings_block,
        minio_bucket_block=minio_bucket_block,
        object_name=object_name,
    )


__all__ = ["cobalt_video_download_flow"]

