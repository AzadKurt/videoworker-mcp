"""Startup diagnostics must never consume allowance or leak credentials."""

import pytest

from videoworker_mcp.__main__ import main


@pytest.fixture
def configured(tmp_path, monkeypatch):
    for name in ("VIDEO_WORKER_API_KEY", "VIDEO_WORKER_API_URL"):
        monkeypatch.delenv(name, raising=False)
    key = tmp_path / "key"
    key.write_text("fk_test_private_key")
    key.chmod(0o600)
    monkeypatch.setenv("VIDEO_WORKER_API_KEY_FILE", str(key))
    for name in ("VIDEO_WORKER_UPLOAD_ROOT", "VIDEO_WORKER_DOWNLOAD_ROOT"):
        monkeypatch.setenv(name, str(tmp_path))


def test_check_is_local_and_redacted(configured, monkeypatch, capsys):
    def no_connector(*args, **kwargs):
        pytest.fail("--check must not open an HTTP client")

    monkeypatch.setattr("videoworker_mcp.__main__.Connector", no_connector)
    assert main(["--check"]) == 0
    output = capsys.readouterr()
    assert "have not been checked" in output.out
    assert "fk_test_private_key" not in output.out + output.err


def test_default_host_is_public_service(configured):
    from videoworker_mcp.client import Settings

    assert Settings.from_env().origin == "https://videoworker.dev"


def test_invalid_configuration_points_to_setup_without_leaking(
    configured, monkeypatch, capsys
):
    monkeypatch.setenv("VIDEO_WORKER_API_KEY", "invalid-secret-do-not-log")
    assert main(["--check"]) == 2
    output = capsys.readouterr()
    assert "VIDEO_WORKER_API_KEY_FILE" in output.err
    assert "#quick-start" in output.err
    assert "invalid-secret-do-not-log" not in output.out + output.err


@pytest.mark.parametrize("flag", ["--help", "--version"])
def test_help_and_version_do_not_require_configuration(monkeypatch, flag):
    def no_settings():
        pytest.fail("diagnostic flag must not read credentials")

    monkeypatch.setattr("videoworker_mcp.__main__.Settings.from_env", no_settings)
    with pytest.raises(SystemExit) as result:
        main([flag])
    assert result.value.code == 0
