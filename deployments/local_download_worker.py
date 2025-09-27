"""Deployment configuration for the Cobalt download flow."""

from __future__ import annotations

from prefect.infrastructure.docker import DockerContainer
from prefect.server.schemas.core import WorkPool

from stevedore.flows.download_video_flow import cobalt_video_download_flow


def deploy() -> WorkPool:
    infrastructure = DockerContainer(
        image="stevedore-download-worker:latest",
        image_pull_policy="IF_NOT_PRESENT",
        env={
            "PREFECT_LOGGING_LEVEL": "INFO",
        },
    )

    deployment = cobalt_video_download_flow.to_deployment(
        name="cobalt-download-worker",
        version="1.0.0",
        work_pool_name="cobalt-downloads",
        infrastructure=infrastructure,
        tags=["cobalt", "downloads"],
        parameters={
            "source_url": "https://example.com/video.mp4",
            "task_id": "example-task",
        },
    )

    deployment.apply()
    return deployment.work_pool


if __name__ == "__main__":
    work_pool = deploy()
    print(f"Deployment applied to work pool '{work_pool.name}'.")

