"""Prefect tasks for extracting audio tracks from stored video assets."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from typing import Optional

from prefect import get_run_logger, task
from prefect.artifacts import create_markdown_artifact
from prefect.utilities.asyncutils import run_sync_in_worker_thread

from stevedore.blocks import MinIOBucket


class AudioExtractionError(RuntimeError):
    """Raised when FFmpeg fails to extract audio."""


def _derive_storage_key(
    *,
    source_object_path: str,
    task_id: str,
    bucket_prefix: Optional[str],
    object_name: Optional[str],
) -> tuple[PurePosixPath, str]:
    """Derive the S3 key for the extracted audio artifact.

    Returns the relative key (without task prefix) and the full storage key.
    """

    source_key = PurePosixPath(source_object_path)
    parts = list(source_key.parts)

    if parts and parts[0] == task_id:
        parts = parts[1:]
    if parts and parts[0] == "download":
        parts = parts[1:]

    relative_key = PurePosixPath(*parts) if parts else PurePosixPath(source_key.name)

    source_name = Path(relative_key.name)
    inferred_name = f"{source_name.stem}.audio.mka"
    audio_name = object_name or inferred_name

    audio_relative = PurePosixPath("extract-audio")
    parent = relative_key.parent
    if str(parent) not in {".", ""}:
        audio_relative /= parent
    audio_relative /= audio_name

    if bucket_prefix:
        prefix_path = PurePosixPath(bucket_prefix.strip("/"))
        audio_relative = prefix_path / audio_relative

    storage_key = PurePosixPath(task_id) / audio_relative
    return audio_relative, storage_key.as_posix()


@task(name="Extract audio via FFmpeg", persist_result=True, tags={"audio-processing"})
async def extract_audio_asset(
    *,
    source_object_path: str,
    task_id: str,
    minio_bucket_block: str,
    object_name: Optional[str] = None,
) -> str:
    """Extract the primary audio track from a downloaded video.

    The task remuxes the first audio stream without re-encoding (``-c:a copy``),
    ensuring the audio characteristics remain identical to the source.

    Args:
        source_object_path: Fully-qualified MinIO key of the video object.
        task_id: Identifier used to namespace the output artifact.
        minio_bucket_block: Name of the ``MinIOBucket`` Prefect block to load.
        object_name: Optional override for the audio filename within the task
            namespace.

    Returns:
        The S3/MinIO key of the uploaded audio artifact.

    Raises:
        AudioExtractionError: If FFmpeg fails or produces no output.
    """

    logger = get_run_logger()

    bucket_config = await MinIOBucket.load(minio_bucket_block)
    s3_bucket = await bucket_config.load_bucket()

    _, storage_key = _derive_storage_key(
        source_object_path=source_object_path,
        task_id=task_id,
        bucket_prefix=bucket_config.bucket_path_prefix,
        object_name=object_name,
    )

    working_dir = Path(tempfile.mkdtemp(prefix="audio-extract-"))
    source_path = working_dir / Path(source_object_path).name
    audio_filename = Path(storage_key).name
    audio_path = working_dir / audio_filename

    try:
        logger.info("Downloading source video '%s'", source_object_path)
        await s3_bucket.adownload_object_to_path(
            from_path=source_object_path,
            to_path=source_path,
        )

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(source_path),
            "-map",
            "0:a:0",
            "-c:a",
            "copy",
            str(audio_path),
        ]

        logger.info("Running FFmpeg to extract audio: %s", " ".join(command))

        try:
            result = await run_sync_in_worker_thread(
                subprocess.run,
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise AudioExtractionError("FFmpeg binary not found in PATH") from exc

        if result.returncode != 0:
            stderr = result.stderr or "Unknown FFmpeg error"
            raise AudioExtractionError(
                f"FFmpeg failed with exit code {result.returncode}: {stderr}"
            )

        if not audio_path.exists() or audio_path.stat().st_size == 0:
            raise AudioExtractionError("FFmpeg did not produce an audio artifact")

        logger.info("Uploading audio artifact to '%s'", storage_key)
        storage_path = await s3_bucket.aupload_from_path(
            from_path=audio_path,
            to_path=storage_key,
        )

        head_metadata = await bucket_config.head_object(storage_key, bucket=s3_bucket)

        await create_markdown_artifact(
            key=f"audio-{task_id}",
            markdown=_render_artifact_markdown(
                task_id=task_id,
                source_object_path=source_object_path,
                audio_object_path=storage_path,
                head_metadata=head_metadata,
            ),
            description="Metadata for extracted audio artifact.",
        )

        logger.info("Audio extraction succeeded; stored object: %s", storage_path)
        return storage_path
    finally:
        for temp_path in (source_path, audio_path):
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass

        try:
            working_dir.rmdir()
        except OSError:
            pass


def _render_artifact_markdown(
    *,
    task_id: str,
    source_object_path: str,
    audio_object_path: str,
    head_metadata: dict,
) -> str:
    rows = [
        ("Task ID", task_id),
        ("Source Object", source_object_path),
        ("Audio Object", audio_object_path),
    ]

    size_bytes = head_metadata.get("ContentLength")
    if size_bytes is not None:
        rows.append(("Audio Size", f"{size_bytes} bytes"))

    etag = head_metadata.get("ETag")
    if etag:
        rows.append(("ETag", etag))

    last_modified = head_metadata.get("LastModified")
    if last_modified:
        rows.append(("Last Modified", str(last_modified)))

    header = "| Field | Value |"
    separator = "| --- | --- |"
    body = "\n".join(f"| {field} | {value} |" for field, value in rows)

    return f"## Audio Extraction\n{header}\n{separator}\n{body}"


__all__ = ["AudioExtractionError", "extract_audio_asset"]