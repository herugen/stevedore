"""Prefect flow responsible for extracting audio from stored media assets."""

from __future__ import annotations

from typing import Optional

from prefect import flow, get_run_logger

from stevedore.tasks.audio import extract_audio_asset


@flow(name="Audio Extraction")
async def audio_extraction_flow(
    *,
    source_object_path: str,
    task_id: str,
    minio_bucket_block: str = "local-minio-assets",
    object_name: Optional[str] = None,
) -> str:
    """Extract the primary audio track from a previously downloaded video."""

    logger = get_run_logger()
    logger.info("Starting audio extraction for task '%s'", task_id)

    audio_path = await extract_audio_asset(
        source_object_path=source_object_path,
        task_id=task_id,
        minio_bucket_block=minio_bucket_block,
        object_name=object_name,
    )

    logger.info("Audio extraction completed for task '%s'", task_id)
    return audio_path


__all__ = ["audio_extraction_flow"]


