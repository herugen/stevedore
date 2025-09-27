"""Command-line interface definitions for the stevedore tooling package."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import typer

from stevedore.cli.operations import (
    apply_deployments,
    ensure_work_pool,
    load_env_file,
    register_blocks,
)

app = typer.Typer(help="Stevedore maintenance CLI")


@app.command("create-work-pool")
def create_work_pool(
    name: str = typer.Argument("cobalt-downloads", help="Name of the Prefect work pool."),
    pool_type: str = typer.Option("docker", "--type", help="Work pool type."),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Overwrite existing configuration if possible.",
    ),
) -> None:
    """Ensure that a Prefect work pool exists with the requested configuration."""

    ensure_work_pool(name, pool_type, overwrite=overwrite)


@app.command("register-blocks")
def register_blocks_command(
    env_file: Path | None = typer.Option(
        None,
        "--env-file",
        help="Optional .env file to load before registering blocks.",
    ),
) -> None:
    """Persist the local Prefect blocks needed for development."""

    if env_file:
        load_env_file(env_file)
    register_blocks()


@app.command("apply-deployments")
def apply_deployments_command(
    env_file: Path | None = typer.Option(
        None,
        "--env-file",
        help="Optional .env file to load before applying deployments.",
    ),
) -> None:
    """Register Prefect deployments defined within the repository."""

    if env_file:
        load_env_file(env_file)
    apply_deployments()


def main(argv: Iterable[str] | None = None) -> int:
    """Typer-compatible entrypoint used by the package console script."""

    args = list(argv) if argv is not None else None
    return app(args=args)


__all__ = ["app", "main"]


if __name__ == "__main__":
    raise SystemExit(main())


