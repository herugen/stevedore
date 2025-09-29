"""Orchestrator flow coordinating video download and audio extraction deployments."""

from __future__ import annotations

from typing import Optional

from prefect import flow
from prefect.deployments import run_deployment
from prefect.flow_runs import wait_for_flow_run


@flow(name="Video to Audio Pipeline")
async def video_pipeline_flow(
    *,
    source_url: str,
    task_id: str,
    cobalt_settings_block: str = "local-cobalt",
    minio_bucket_block: str = "local-minio-assets",
    object_name: Optional[str] = None,
) -> dict[str, str]:
    """Download a video then trigger audio extraction as a downstream deployment."""

    download_flow_run = await run_deployment(
        "cobalt-video-download/cobalt-download-worker",
        parameters={
            "source_url": source_url,
            "task_id": task_id,
            "cobalt_settings_block": cobalt_settings_block,
            "minio_bucket_block": minio_bucket_block,
            "object_name": object_name,
        },
        flow_run_name=f"download-{task_id}",
        timeout=0,
    )

    download_flow_run = await wait_for_flow_run(download_flow_run.id)
    download_state = download_flow_run.state
    download_result = await download_state.aresult()

    audio_flow_run = await run_deployment(
        "audio-extraction/audio-processing",
        parameters={
            "source_object_path": download_result["video"],
            "task_id": task_id,
            "minio_bucket_block": minio_bucket_block,
        },
        flow_run_name=f"audio-{task_id}",
        timeout=0,
    )

    return {
        "download_flow_run_id": str(download_flow_run.id),
        "download_state": download_state.type.value,
        "audio_flow_run_id": str(audio_flow_run.id),
    }


__all__ = ["video_pipeline_flow"]


