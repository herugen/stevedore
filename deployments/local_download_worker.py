"""Deployment configuration for the Cobalt download flow."""

from __future__ import annotations

from pathlib import Path

from prefect.deployments import load_deployments_from_yaml


def deploy() -> None:
    yaml_path = Path(__file__).with_suffix(".yaml")
    deployments = load_deployments_from_yaml(str(yaml_path))

    for deployment in deployments:
        deployment.apply()


if __name__ == "__main__":
    deploy()
    print("Deployment(s) applied from local_download_worker.yaml")

