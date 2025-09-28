"""Tests for the Cobalt download Prefect task."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from pathlib import Path

import pytest

from stevedore.tasks.downloads import (
    CobaltDownloadError,
    download_video_asset,
)
from botocore.exceptions import ClientError


class DummyS3Bucket:
    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.bucket_name = "bucket"

    def _resolve_path(self, key):
        return key

    def _get_s3_client(self):
        return SimpleNamespace(head_object=self._head_object)

    async def aread_path(self, key):
        return self.objects[key]

    async def aupload_from_path(self, from_path, to_path=None, **kwargs):
        to_path = to_path or Path(from_path).name
        self.objects[to_path] = Path(from_path).read_bytes()
        return to_path

    def _head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")

        return {
            "ContentLength": len(self.objects[Key]),
            "ETag": "\"dummy-etag\"",
            "LastModified": "2024-01-01T00:00:00Z",
        }


async def _object_exists(dummy_bucket, key, bucket=None):
    return key in dummy_bucket.objects


async def _head_object(dummy_bucket, key, bucket=None):
    active_bucket = bucket or dummy_bucket
    return active_bucket._head_object(active_bucket.bucket_name, key)


@pytest.mark.asyncio
async def test_download_video_asset_skips_when_object_exists(monkeypatch, tmp_path):
    dummy_bucket = DummyS3Bucket()
    dummy_bucket.objects["task-123/download/videos/video.mp4"] = b"dummy"
    dummy_cobalt_response = {"status": "redirect", "url": "http://download.test/video"}

    class DummyCobaltClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: dummy_cobalt_response,
            )

        def stream(self, method, url):
            assert method == "GET"
            assert url == dummy_cobalt_response["url"]

            class DummyStream:
                async def __aenter__(self):
                    return self

                async def __aexit__(self, exc_type, exc, tb):
                    return False

                def raise_for_status(self):
                    return None

                async def aiter_bytes(self):
                    yield b"dummy"

            return DummyStream()

    monkeypatch.setattr(
        "stevedore.tasks.downloads.httpx.AsyncClient",
        DummyCobaltClient,
    )

    monkeypatch.setattr(
        "stevedore.tasks.downloads.CobaltSettings.load",
        classmethod(
            lambda cls, name: SimpleNamespace(
                base_url="http://cobalt.test",
                request_timeout_seconds=5,
                download_timeout_seconds=5,
                headers=lambda: {"Content-Type": "application/json"},
            )
        ),
    )

    gather_mock = AsyncMock(return_value={"resolution": "1920x1080"})
    artifact_mock = AsyncMock()

    monkeypatch.setattr("stevedore.tasks.downloads._gather_media_metadata", gather_mock)
    monkeypatch.setattr("stevedore.tasks.downloads.create_markdown_artifact", artifact_mock)
    monkeypatch.setattr(
        "stevedore.tasks.downloads.MinIOBucket.load",
        classmethod(
            lambda cls, name: SimpleNamespace(
                bucket_path_prefix="videos",
                load_bucket=AsyncMock(return_value=dummy_bucket),
                object_exists=lambda key, bucket=None: _object_exists(dummy_bucket, key, bucket),
                head_object=lambda key, bucket=None: _head_object(dummy_bucket, key, bucket),
            )
        ),
    )

    monkeypatch.setattr(
        "stevedore.tasks.downloads.tempfile.mkdtemp",
        lambda prefix: str(tmp_path),
    )

    result = await download_video_asset.fn(
        source_url="http://example.com/video",
        task_id="task-123",
        cobalt_settings_block="cobalt",
        minio_bucket_block="minio",
        object_name="video.mp4",
    )

    assert result == "task-123/download/videos/video.mp4"
    gather_mock.assert_awaited()
    artifact_mock.assert_awaited()


@pytest.mark.asyncio
async def test_download_video_asset_success(monkeypatch, tmp_path):
    dummy_bucket = DummyS3Bucket()
    dummy_cobalt_response = {"status": "redirect", "url": "http://download.test/video"}

    class DummyCobaltClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: dummy_cobalt_response,
            )

    monkeypatch.setattr(
        "stevedore.tasks.downloads.httpx.AsyncClient",
        DummyCobaltClient,
    )

    monkeypatch.setattr(
        "stevedore.tasks.downloads.CobaltSettings.load",
        classmethod(
            lambda cls, name: SimpleNamespace(
                base_url="http://cobalt.test",
                request_timeout_seconds=5,
                download_timeout_seconds=5,
                headers=lambda: {"Content-Type": "application/json"},
            )
        ),
    )

    gather_mock = AsyncMock(return_value={"resolution": "1920x1080"})
    artifact_mock = AsyncMock()

    monkeypatch.setattr("stevedore.tasks.downloads._gather_media_metadata", gather_mock)
    monkeypatch.setattr("stevedore.tasks.downloads.create_markdown_artifact", artifact_mock)
    monkeypatch.setattr(
        "stevedore.tasks.downloads.MinIOBucket.load",
        classmethod(
            lambda cls, name: SimpleNamespace(
                bucket_path_prefix=None,
                load_bucket=lambda: dummy_bucket,
                object_exists=lambda key, bucket=None: _object_exists(dummy_bucket, key, bucket),
                head_object=lambda key, bucket=None: _head_object(dummy_bucket, key, bucket),
            )
        ),
    )

    with pytest.raises(CobaltDownloadError):
        await download_video_asset.fn(
            source_url="http://example.com/video",
            task_id="task-123",
            cobalt_settings_block="cobalt",
            minio_bucket_block="minio",
        )

