"""Tasks responsible for retrieving assets via the Cobalt service."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

import httpx
from prefect import task

from stevedore.blocks import CobaltSettings, MinIOBucket


class CobaltDownloadError(RuntimeError):
    """Raised when the Cobalt service fails to provide a downloadable asset."""


@task(name="Download video via Cobalt")
async def download_video_asset(
    source_url: str,
    task_id: str,
    cobalt_settings_block: str,
    minio_bucket_block: str,
    object_name: Optional[str] = None,
) -> str:
    """Download a video using Cobalt and upload it to MinIO.

    Args:
        source_url: Original media URL to be downloaded via Cobalt.
        task_id: Identifier used to namespace the uploaded object path.
        cobalt_settings_block: Name of the `CobaltSettings` block to load.
        minio_bucket_block: Name of the `MinIOBucket` block to load.
        object_name: Optional object key to use for the uploaded asset. If omitted,
            a task_id-based filename is generated.

    Returns:
        The fully-qualified MinIO object path returned by the storage client.

    Raises:
        CobaltDownloadError: If the Cobalt service responds with an error.
        httpx.HTTPError: On network-level failures when communicating with Cobalt.
    """

    cobalt_settings = CobaltSettings.load(cobalt_settings_block)
    bucket_config = MinIOBucket.load(minio_bucket_block)
    s3_bucket = bucket_config.load_bucket()

    async with httpx.AsyncClient(timeout=cobalt_settings.request_timeout_seconds) as client:
        response = await client.post(
            cobalt_settings.base_url,
            json={"url": source_url},
            headers=cobalt_settings.headers(),
        )
        response.raise_for_status()

        payload = response.json()

    status = payload.get("status")
    if status not in {"tunnel", "redirect"}:
        if status == "picker":
            raise CobaltDownloadError(
                "Cobalt requires user selection of media variant; cannot auto-download."
            )

        raise CobaltDownloadError(
            payload.get("error", f"Unexpected Cobalt status '{status}'.")
        )

    download_url = payload.get("url")
    if not download_url:
        raise CobaltDownloadError("Cobalt response missing download URL.")

    file_name = object_name or f"video_{task_id}.mp4"
    temp_dir = tempfile.mkdtemp(prefix="cobalt-download-")
    temp_file_path = Path(temp_dir) / file_name

    async with httpx.AsyncClient(timeout=cobalt_settings.download_timeout_seconds) as client:
        async with client.stream("GET", download_url) as stream:
            stream.raise_for_status()

            with temp_file_path.open("wb") as file_buffer:
                async for chunk in stream.aiter_bytes():
                    file_buffer.write(chunk)

    prefix = bucket_config.bucket_path_prefix
    object_key = f"{prefix.rstrip('/')}/{file_name}" if prefix else file_name
    storage_path = await s3_bucket.write_path(
        path=temp_file_path,
        key="/".join(filter(None, [task_id, "download", object_key])),
    )

    try:
        temp_file_path.unlink()
        Path(temp_dir).rmdir()
    except OSError:
        pass

    return storage_path


__all__ = ["download_video_asset", "CobaltDownloadError"]

