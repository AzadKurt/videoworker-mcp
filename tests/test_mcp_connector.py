"""Connector trust boundaries and real SDK tool discovery, without model inference."""

import asyncio
import json
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


def test_job_callback_requires_server_support_and_keeps_request_id(tmp_path):
    from videoworker_mcp.client import Connector, ConnectorError

    seen = []
    supported = True

    def respond(request):
        seen.append(request)
        if request.url.path == "/v1/health":
            return httpx.Response(200, json={"webhooks_enabled": supported})
        return httpx.Response(202, json={"id": "a" * 32, "state": "queued"})

    connector = Connector(settings(tmp_path), transport=httpx.MockTransport(respond))
    key = str(uuid.uuid4())
    connector.create_job(
        ["b" * 32], ["-i", "{{input:0}}", "{{output:0}}"], ["a.mp4"], 5, key, "c" * 32
    )
    assert seen[-1].headers["idempotency-key"] == key
    assert json.loads(seen[-1].content)["webhook_endpoint_id"] == "c" * 32
    supported = False
    seen.clear()
    with pytest.raises(ConnectorError, match="webhooks_unsupported"):
        connector.create_job(
            ["b" * 32],
            ["-i", "{{input:0}}", "{{output:0}}"],
            ["a.mp4"],
            5,
            key,
            "c" * 32,
        )
    assert all(r.method == "GET" for r in seen)


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
                "list_presets",
                "run_preset",
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


def test_run_preset_keeps_uuid_and_ownership(tmp_path):
    from mcp import Client

    from videoworker_mcp.client import Connector
    from videoworker_mcp.server import build_server

    seen = []

    def respond(request):
        seen.append(
            (
                request.method,
                request.url.path,
                request.headers["authorization"],
                request.headers.get("idempotency-key"),
                json.loads(request.content) if request.content else None,
            )
        )
        if request.url.path == "/v1/jobs":
            return httpx.Response(200, json={"jobs": []})
        if request.url.path == "/v1/presets":
            return httpx.Response(
                200, json={"presets": [{"id": "web-mp4", "version": 1}]}
            )
        return httpx.Response(202, json={"id": "a" * 32, "state": "queued"})

    connector = Connector(settings(tmp_path), transport=httpx.MockTransport(respond))
    args = {
        "preset_id": "web-mp4",
        "version": 1,
        "inputs": ["b" * 32],
        "parameters": {"crf": 25},
        "timeout_seconds": 7,
        "request_id": "ABCDEFAB-1234-4321-ABCD-123456789ABC",
    }

    async def exercise():
        async with Client(build_server(connector)) as client:
            tools = {t.name: t for t in (await client.list_tools()).tools}
            assert tools["list_presets"].annotations.read_only_hint
            assert tools["run_preset"].annotations.idempotent_hint
            catalog = await client.call_tool("list_presets", {})
            assert catalog.structured_content == {
                "presets": [{"id": "web-mp4", "version": 1}]
            }
            for _ in range(2):
                result = await client.call_tool("run_preset", args)
                assert result.structured_content["id"] == "a" * 32
            invalid = await client.call_tool(
                "run_preset", {**args, "request_id": "not-a-uuid"}
            )
            assert invalid.is_error

    asyncio.run(exercise())
    assert (
        seen
        == [
            ("GET", "/v1/jobs", "Bearer fk_unit_secret", None, None),
            ("GET", "/v1/presets", "Bearer fk_unit_secret", None, None),
        ]
        + [
            (
                "POST",
                "/v1/jobs/from-preset",
                "Bearer fk_unit_secret",
                "abcdefab-1234-4321-abcd-123456789abc",
                {key: value for key, value in args.items() if key != "request_id"},
            )
        ]
        * 2
    )
    connector.close()


@pytest.mark.parametrize(
    "status,unknown", [(403, False), (409, False), (422, False), (503, True), (0, True)]
)
def test_preset_write_failure_is_not_retried(tmp_path, status, unknown):
    from videoworker_mcp.client import Connector, ConnectorError

    calls = []

    def respond(request):
        calls.append(request)
        if status == 0:
            raise httpx.ReadError("controlled lost reply")
        return httpx.Response(status, text="private service detail fk_unit_secret")

    connector = Connector(settings(tmp_path), transport=httpx.MockTransport(respond))
    with pytest.raises(ConnectorError) as failure:
        connector.run_preset("web-mp4", 1, ["b" * 32], {}, 7, str(uuid.uuid4()))
    assert len(calls) == 1
    assert bool(failure.value.detail.get("outcome_unknown")) == unknown
    assert "fk_unit_secret" not in str(failure.value)
    connector.close()


def test_old_server_reports_presets_unsupported_without_raw_fallback(tmp_path):
    from videoworker_mcp.client import Connector, ConnectorError

    seen = []

    def respond(request):
        seen.append(request.url.path)
        return (
            httpx.Response(200, json={"jobs": []})
            if request.url.path == "/v1/jobs"
            else httpx.Response(404, json={"detail": "Not Found"})
        )

    connector = Connector(settings(tmp_path), transport=httpx.MockTransport(respond))
    with pytest.raises(ConnectorError, match="presets_unsupported"):
        connector.presets()
    with pytest.raises(ConnectorError, match="presets_unsupported"):
        connector.run_preset("web-mp4", 1, ["b" * 32], {}, 7, str(uuid.uuid4()))
    assert seen == ["/v1/jobs", "/v1/presets", "/v1/jobs/from-preset"]
    connector.close()


@pytest.mark.parametrize(
    "changes",
    [
        {"version": True},
        {"version": "1"},
        {"version": 1.5},
        {"timeout_seconds": True},
        {"timeout_seconds": "7"},
    ],
)
def test_preset_sdk_rejects_coerced_numbers_before_post(tmp_path, changes):
    from mcp import Client

    from videoworker_mcp.client import Connector
    from videoworker_mcp.server import build_server

    seen = []

    def respond(request):
        seen.append(request.url.path)
        return httpx.Response(202, json={"id": "a" * 32})

    connector = Connector(settings(tmp_path), transport=httpx.MockTransport(respond))

    async def check():
        async with Client(build_server(connector)) as client:
            result = await client.call_tool(
                "run_preset",
                {
                    "preset_id": "web-mp4",
                    "version": 1,
                    "inputs": ["b" * 32],
                    "parameters": {},
                    "timeout_seconds": 7,
                    "request_id": str(uuid.uuid4()),
                    **changes,
                },
            )
            assert result.is_error

    try:
        asyncio.run(check())
        assert seen == []
    finally:
        connector.close()


@pytest.mark.parametrize("body", [{}, {"id": "bad"}])
def test_preset_bad_success_is_an_unknown_write(tmp_path, body):
    from videoworker_mcp.client import Connector, ConnectorError

    connector = Connector(
        settings(tmp_path),
        transport=httpx.MockTransport(lambda r: httpx.Response(202, json=body)),
    )
    try:
        with pytest.raises(ConnectorError) as failure:
            connector.run_preset("web-mp4", 1, ["b" * 32], {}, 7, str(uuid.uuid4()))
        assert failure.value.detail["outcome_unknown"]
    finally:
        connector.close()


@pytest.mark.parametrize(
    "detail,code",
    [
        ("Not Found", "presets_unsupported"),
        ("An input file is missing or expired. Upload it again.", "input_unavailable"),
        ({"code": "preset_not_found"}, "preset_not_found"),
    ],
)
def test_preset_missing_input_is_distinct_from_missing_server(tmp_path, detail, code):
    from videoworker_mcp.client import Connector, ConnectorError

    connector = Connector(
        settings(tmp_path),
        transport=httpx.MockTransport(
            lambda r: httpx.Response(404, json={"detail": detail})
        ),
    )
    try:
        with pytest.raises(ConnectorError) as failure:
            connector.run_preset("web-mp4", 1, ["b" * 32], {}, 7, str(uuid.uuid4()))
        assert failure.value.detail["code"] == code
    finally:
        connector.close()


@pytest.mark.parametrize("status", [401, 403])
def test_preset_catalog_checks_jobs_read_before_public_metadata(tmp_path, status):
    from videoworker_mcp.client import Connector, ConnectorError

    seen = []

    def respond(request):
        seen.append(request.url.path)
        return httpx.Response(
            status if request.url.path == "/v1/jobs" else 200, json={"presets": []}
        )

    connector = Connector(settings(tmp_path), transport=httpx.MockTransport(respond))
    try:
        with pytest.raises(ConnectorError) as failure:
            connector.presets()
        assert failure.value.detail["status"] == status
        assert seen == ["/v1/jobs"]
    finally:
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
