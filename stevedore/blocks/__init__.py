"""Prefect block definitions for the stevedore project."""

from .cobalt import CobaltSettings  # noqa: F401
from .minio import MinIOBucket  # noqa: F401

__all__ = [
    "CobaltSettings",
    "MinIOBucket",
]

