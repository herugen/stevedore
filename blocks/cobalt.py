"""Prefect Block for configuring access to the Cobalt service."""

from __future__ import annotations

from typing import Dict

from pydantic import Field

from prefect.blocks.core import Block


class CobaltSettings(Block):
    """Stores configuration for invoking the Cobalt download service."""

    _block_type_name = "Cobalt Settings"
    _description = "Configuration for Cobalt HTTP API access."

    base_url: str = Field(
        ...,
        description="Base URL of the Cobalt service endpoint that accepts download requests.",
        example="http://cobalt.internal/api/download",
    )
    request_timeout_seconds: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Timeout (in seconds) for the initial Cobalt request.",
    )
    download_timeout_seconds: int = Field(
        default=120,
        ge=30,
        le=1800,
        description="Timeout (in seconds) for streaming the downloadable asset.",
    )

    def headers(self) -> Dict[str, str]:
        """Return default headers for Cobalt requests."""

        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }


__all__ = ["CobaltSettings"]

