"""Tests for the Cobalt download Prefect task."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from stevedore.tasks.downloads import (
    CobaltDownloadError,
    download_video_asset,
)


class DummyS3Bucket:
    async def write_path(self, path, key):  # noqa: D401 - simple async stub
        assert path.exists()
        return f"s3://bucket/{key}"


@pytest.mark.asyncio
async def test_download_video_asset_success(monkeypatch, tmp_path):
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

    monkeypatch.setattr(
        "stevedore.tasks.downloads.MinIOBucket.load",
        classmethod(
            lambda cls, name: SimpleNamespace(
                bucket_path_prefix="videos",
                load_bucket=lambda: DummyS3Bucket(),
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

    assert result == "s3://bucket/task-123/download/videos/video.mp4"


@pytest.mark.asyncio
async def test_download_video_asset_picker_error(monkeypatch):
    dummy_response = {"status": "picker"}

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: dummy_response,
            )

    monkeypatch.setattr(
        "stevedore.tasks.downloads.httpx.AsyncClient",
        DummyClient,
    )

    monkeypatch.setattr(
        "stevedore.tasks.downloads.CobaltSettings.load",
        classmethod(
            lambda cls, name: SimpleNamespace(
                base_url="http://cobalt.test",
                request_timeout_seconds=5,
                download_timeout_seconds=5,
                headers=lambda: {},
            )
        ),
    )

    monkeypatch.setattr(
        "stevedore.tasks.downloads.MinIOBucket.load",
        classmethod(
            lambda cls, name: SimpleNamespace(
                bucket_path_prefix=None,
                load_bucket=lambda: DummyS3Bucket(),
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

