"""Deployment configuration for the Cobalt download flow."""

from __future__ import annotations

from pathlib import Path

import yaml

from prefect.deployments.runner import RunnerDeployment
from prefect.flows import load_flow_from_entrypoint


def deploy() -> None:
    yaml_path = Path(__file__).with_suffix(".yaml")
    with yaml_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    deployments = data.get("deployments", [])

    for deployment_config in deployments:
        register_deployment(deployment_config)


def register_deployment(config: dict[str, object]) -> None:
    entrypoint = config["entrypoint"]
    flow = load_flow_from_entrypoint(entrypoint)

    deployment = flow.to_deployment(  # type: ignore[arg-type]
        name=config["name"],
        version=config.get("version"),
        tags=config.get("tags", []),
        parameters=config.get("parameters", {}),
        work_pool_name=config.get("work_pool", {}).get("name"),
        work_queue_name=config.get("work_queue"),
        job_variables=config.get("work_pool", {}).get("job_variables", {}),
    )

    if isinstance(deployment, RunnerDeployment):
        deployment.flow_name = config.get("flow_name") or flow.name
        deployment.entrypoint = entrypoint

    deployment.apply()


if __name__ == "__main__":
    deploy()
    print("Deployment(s) applied from local_download_worker.yaml")

