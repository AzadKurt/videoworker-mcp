"""Connector trust boundaries and real SDK tool discovery, without model inference."""

import asyncio
import os
import uuid

import httpx
import pytest


def settings(tmp_path):
    from videoworker_mcp.client import Settings

    upload, download = tmp_path / "upload", tmp_path / "download"
    upload.mkdir(exist_ok=True)
    download.mkdir(exist_ok=True)
    return Settings("http://localhost:18887", "fk_unit_secret", upload, download)


def test_origin_and_local_file_boundaries(tmp_path):
    from dataclasses import replace

    from videoworker_mcp.client import Connector, ConnectorError

    config = settings(tmp_path)
    for url in (
        "http://example.test",
        "https://user:pass@example.test",
        "https://example.test/path",
        "https://example.test?x=y",
    ):
        with pytest.raises(ValueError):
            replace(config, origin=url).validate()
    connector = Connector(
        config,
        transport=httpx.MockTransport(
            lambda r: (
                httpx.Response(
                    200, json={"max_upload_bytes": 100, "max_output_bytes": 100}
                )
                if r.url.path == "/v1/limits"
                else httpx.Response(201, json={"id": "a" * 32})
            )
        ),
    )
    for filename in ("../secret.mp4", "/secret.mp4", "nested/clip.mp4", "secret.txt"):
        with pytest.raises(ConnectorError):
            connector.upload(filename)
    clip = config.upload_root / "clip.mp4"
    clip.write_bytes(b"tiny")
    assert connector.upload("clip.mp4")["id"] == "a" * 32
    (config.upload_root / "Mein Clip (1).MP4").write_bytes(b"tiny")
    assert connector.upload("Mein Clip (1).MP4")["id"] == "a" * 32
    connector.close()


def test_service_redirect_and_secret_errors_are_sanitized(tmp_path):
    from videoworker_mcp.client import Connector, ConnectorError

    config = settings(tmp_path)
    seen = []

    def respond(request):
        seen.append(str(request.url))
        assert request.headers["authorization"] == "Bearer fk_unit_secret"
        return httpx.Response(
            302,
            headers={"Location": "https://attacker.example/"},
            text="fk_unit_secret",
        )

    connector = Connector(config, transport=httpx.MockTransport(respond))
    with pytest.raises(ConnectorError) as failure:
        connector.usage()
    assert "fk_unit_secret" not in str(failure.value)
    assert len(seen) == 1 and seen[0].startswith(config.origin)
    assert "fk_unit_secret" not in repr(config)
    connector.close()


def test_download_uses_owned_job_not_untrusted_url_and_never_overwrites(tmp_path):
    from videoworker_mcp.client import Connector, ConnectorError

    config = settings(tmp_path)
    job = uuid.uuid4().hex
    seen = []

    def respond(request):
        seen.append(str(request.url))
        if request.url.path == "/v1/limits":
            return httpx.Response(
                200, json={"max_upload_bytes": 100, "max_output_bytes": 100}
            )
        if request.url.path == "/v1/jobs/" + job:
            return httpx.Response(
                200,
                json={
                    "id": job,
                    "state": "succeeded",
                    "outputs": [
                        {"name": "audio.mp3", "url": "https://evil.example/secret"}
                    ],
                },
            )
        return httpx.Response(200, content=b"result")

    connector = Connector(config, transport=httpx.MockTransport(respond))
    saved = connector.download(job, "audio.mp3", "saved.mp3")
    assert saved["size_bytes"] == 6
    assert (config.download_root / "saved.mp3").read_bytes() == b"result"
    assert all(url.startswith(config.origin + "/") for url in seen)
    with pytest.raises(ConnectorError):
        connector.download(job, "audio.mp3", "saved.mp3")
    connector.close()


def test_real_sdk_tools_have_scopes_annotations_and_structured_results(tmp_path):
    pytest.importorskip("mcp")
    from mcp import Client

    from videoworker_mcp.client import Connector
    from videoworker_mcp.server import build_server

    config = settings(tmp_path)
    connector = Connector(
        config,
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"mode": "preview", "quota": None})
        ),
    )

    async def exercise():
        async with Client(build_server(connector)) as client:
            tools = await client.list_tools()
            assert {t.name for t in tools.tools} == {
                "get_usage",
                "list_jobs",
                "upload_file",
                "create_job",
                "get_job",
                "cancel_job",
                "delete_job_outputs",
                "download_result",
            }
            result = await client.call_tool("get_usage", {})
            assert (
                not result.is_error and result.structured_content["mode"] == "preview"
            )
            invalid = await client.call_tool(
                "upload_file", {"filename": "../secret.mp4"}
            )
            assert invalid.is_error and "fk_unit_secret" not in str(invalid)

    asyncio.run(exercise())
    connector.close()


def test_failed_download_keeps_creation_and_cleanup_in_selected_directory(
    tmp_path, monkeypatch
):
    from videoworker_mcp.client import Connector, ConnectorError

    config = settings(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "saved.mp4").write_bytes(b"keep")
    job = uuid.uuid4().hex
    moved = tmp_path / "moved"
    if os.name == "nt":
        original_open = os.open

        def intercept(path, *args, **kwargs):
            if str(path) == str(config.download_root / "saved.mp4"):
                with pytest.raises(PermissionError):
                    config.download_root.rename(moved)
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(os, "open", intercept)

    def respond(request):
        if request.url.path == "/v1/jobs/" + job:
            return httpx.Response(
                200, json={"state": "succeeded", "outputs": [{"name": "out.mp4"}]}
            )
        if os.name == "nt":
            with pytest.raises(PermissionError):
                config.download_root.rename(moved)
        else:
            config.download_root.rename(moved)
            config.download_root.symlink_to(outside, target_is_directory=True)
        raise httpx.ReadError("controlled interrupted result")

    connector = Connector(config, transport=httpx.MockTransport(respond))
    with pytest.raises(ConnectorError):
        connector.download(job, "out.mp4", "saved.mp4")
    assert (outside / "saved.mp4").read_bytes() == b"keep"
    original = config.download_root if os.name == "nt" else moved
    assert not (original / "saved.mp4").exists()
    connector.close()
