"""Tasks responsible for retrieving assets via the Cobalt service."""

from __future__ import annotations

import json
import subprocess
import tempfile
from datetime import timedelta
from pathlib import Path
from typing import Optional

import httpx
from prefect import task
from prefect.artifacts import create_markdown_artifact
from prefect.tasks import task_input_hash

from stevedore.blocks import CobaltSettings, MinIOBucket


class CobaltDownloadError(RuntimeError):
    """Raised when the Cobalt service fails to provide a downloadable asset."""


@task(
    name="Download video via Cobalt",
    persist_result=True,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=24),
)
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

    cobalt_settings = await CobaltSettings.load(cobalt_settings_block)
    bucket_config = await MinIOBucket.load(minio_bucket_block)
    s3_bucket = await bucket_config.load_bucket()

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

    prefix = bucket_config.bucket_path_prefix
    file_name = object_name or f"video_{task_id}.mp4"
    object_key = f"{prefix.rstrip('/')}/{file_name}" if prefix else file_name
    storage_key = "/".join(filter(None, [task_id, "download", object_key]))
    resolved_storage_path = s3_bucket._resolve_path(storage_key)

    if await bucket_config.object_exists(storage_key, bucket=s3_bucket):
        head_data = await bucket_config.head_object(storage_key, bucket=s3_bucket)
        media_metadata = await _gather_media_metadata(
            bucket=s3_bucket,
            key=storage_key,
            head_metadata=head_data,
        )
        await _emit_download_artifact(
            task_id=task_id,
            storage_uri=f"s3://{s3_bucket.bucket_name}/{resolved_storage_path}",
            endpoint_url=_resolve_bucket_endpoint(s3_bucket),
            media_metadata=media_metadata,
            head_metadata=head_data,
            reused=True,
            source_url=source_url,
        )
        return resolved_storage_path

    temp_dir = tempfile.mkdtemp(prefix="cobalt-download-")
    temp_file_path = Path(temp_dir) / file_name

    async with httpx.AsyncClient(timeout=cobalt_settings.download_timeout_seconds) as client:
        async with client.stream("GET", download_url) as stream:
            stream.raise_for_status()

            with temp_file_path.open("wb") as file_buffer:
                async for chunk in stream.aiter_bytes():
                    file_buffer.write(chunk)

    storage_path = await s3_bucket.aupload_from_path(
        from_path=temp_file_path,
        to_path=storage_key,
    )

    head_data = await bucket_config.head_object(storage_key, bucket=s3_bucket)
    media_metadata = await _gather_media_metadata(
        bucket=s3_bucket,
        key=storage_key,
        head_metadata=head_data,
        local_path=temp_file_path,
    )
    await _emit_download_artifact(
        task_id=task_id,
        storage_uri=f"s3://{s3_bucket.bucket_name}/{storage_path}",
        endpoint_url=_resolve_bucket_endpoint(s3_bucket),
        media_metadata=media_metadata,
        head_metadata=head_data,
        reused=False,
        source_url=source_url,
    )

    try:
        temp_file_path.unlink()
        Path(temp_dir).rmdir()
    except OSError:
        pass

    return storage_path


def _probe_media_metadata(path: Path | str) -> dict[str, Optional[str]]:
    """Extract media metadata using ffprobe; falls back gracefully."""

    file_path = Path(path)
    if not file_path.exists():
        return {}

    ffprobe_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,codec_name,avg_frame_rate,bit_rate",
        "-show_entries",
        "format=duration,size,bit_rate",
        "-of",
        "json",
        str(file_path),
    ]

    try:
        proc = subprocess.run(
            ffprobe_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            encoding="utf-8",
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {}

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {}

    result: dict[str, Optional[str]] = {}

    fmt = data.get("format", {})
    if "duration" in fmt:
        result["duration_seconds"] = fmt["duration"]
    if "size" in fmt:
        result["size_bytes"] = fmt["size"]
    if "bit_rate" in fmt:
        result["bitrate"] = fmt["bit_rate"]

    streams = data.get("streams", [])
    if streams:
        stream = streams[0]
        result["codec"] = stream.get("codec_name")
        if stream.get("width") and stream.get("height"):
            result["resolution"] = f"{stream['width']}x{stream['height']}"
        if stream.get("avg_frame_rate") and stream["avg_frame_rate"] != "0/0":
            result["frame_rate"] = stream["avg_frame_rate"]
        if stream.get("bit_rate"):
            result["video_bitrate"] = stream["bit_rate"]

    return result


async def _gather_media_metadata(
    *,
    bucket,
    key: str,
    head_metadata: dict,
    local_path: Optional[Path] = None,
) -> dict[str, Optional[str]]:
    """Gather media metadata using ffprobe and S3 headers."""

    metadata: dict[str, Optional[str]] = {}

    size_bytes = head_metadata.get("ContentLength")
    if size_bytes is not None:
        metadata["size_bytes"] = str(size_bytes)

    target_path = local_path
    cleanup_temp = False

    if target_path is None:
        temp_dir = tempfile.mkdtemp(prefix="cobalt-head-probe-")
        target_path = Path(temp_dir) / Path(key).name
        cleanup_temp = True

        try:
            content = await bucket.aread_path(key)
            target_path.write_bytes(content)
        except Exception:
            if cleanup_temp:
                _safe_cleanup_tempfile(target_path)
            return metadata

    metadata.update(_probe_media_metadata(target_path))

    if cleanup_temp:
        _safe_cleanup_tempfile(target_path)

    return metadata


def _safe_cleanup_tempfile(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
        if path.parent.exists():
            path.parent.rmdir()
    except OSError:
        pass


async def _emit_download_artifact(
    *,
    task_id: str,
    storage_uri: str,
    endpoint_url: Optional[str],
    media_metadata: dict[str, Optional[str]],
    head_metadata: dict,
    reused: bool,
    source_url: str,
) -> None:
    """Emit a Prefect markdown artifact summarizing the download."""

    headers = ["Field", "Value"]

    if endpoint_url:
        object_path = storage_uri.split("//", 1)[-1]
        storage_link = f"[{storage_uri}]({endpoint_url.rstrip('/')}/{object_path})"
    else:
        storage_link = storage_uri

    rows = [
        ("Status", "Reused existing object" if reused else "Uploaded new object"),
        ("Storage URI", storage_link),
        ("Task ID", task_id),
        ("Source URL", source_url),
    ]

    size_bytes = head_metadata.get("ContentLength")
    if size_bytes is not None:
        rows.append(("S3 Object Size", f"{size_bytes} bytes"))

    etag = head_metadata.get("ETag")
    if etag:
        rows.append(("ETag", etag))

    last_modified = head_metadata.get("LastModified")
    if last_modified:
        rows.append(("Last Modified", str(last_modified)))

    for key, value in media_metadata.items():
        rows.append((key.replace("_", " ").title(), value or "-"))

    markdown_rows = "\n".join(f"| {field} | {value} |" for field, value in rows)
    markdown_table = f"| {' | '.join(headers)} |\n| --- | --- |\n{markdown_rows}"

    await create_markdown_artifact(
        key=f"download-{task_id}",
        markdown=f"## Cobalt Download\n{markdown_table}",
        description="Metadata for downloaded video asset.",
    )


def _resolve_bucket_endpoint(bucket) -> Optional[str]:
    try:
        params = bucket.credentials.aws_client_parameters.get_params_override()
        return params.get("endpoint_url")
    except AttributeError:
        return None


__all__ = ["download_video_asset", "CobaltDownloadError"]

