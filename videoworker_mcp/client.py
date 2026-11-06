"""Fixed-origin HTTP and explicitly opted-in, flat local media directories."""

import json
import os
import re
import stat
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote, urlsplit
from uuid import UUID

import httpx

MEDIA_NAME = re.compile(
    r"[A-Za-z0-9_-]{1,64}\.(mp4|mp3|wav|webm|gif|png|jpg|mkv|mov|ogg|flac)"
)
DOWNLOAD_LIMIT = 50 * 1024**2


class ConnectorError(ValueError):
    def __init__(self, code, *, status=None, retry_after=None, uncertain=False):
        self.detail = {"code": code}
        if status is not None:
            self.detail["status"] = status
        if retry_after is not None:
            self.detail["retry_after_seconds"] = retry_after
        if uncertain:
            self.detail["outcome_unknown"] = True
        super().__init__(json.dumps(self.detail))


@dataclass(frozen=True)
class Settings:
    origin: str
    api_key: str = field(repr=False)
    upload_root: Path
    download_root: Path

    def validate(self):
        url = urlsplit(self.origin)
        if (
            (
                url.scheme != "https"
                and not (
                    url.scheme == "http"
                    and url.hostname in {"localhost", "127.0.0.1", "::1"}
                )
            )
            or not url.hostname
            or url.username
            or url.password
            or url.path not in {"", "/"}
            or url.query
            or url.fragment
        ):
            raise ValueError(
                "Configure one HTTPS service origin, or explicit loopback HTTP."
            )
        if (
            not self.api_key.startswith("fk_")
            or not 10 <= len(self.api_key) <= 512
            or any(c.isspace() for c in self.api_key)
        ):
            raise ValueError("Configure a personal API key privately.")
        for root in (self.upload_root, self.download_root):
            if (
                not root.is_absolute()
                or not root.is_dir()
                or root.is_symlink()
                or root.is_junction()
            ):
                raise ValueError(
                    "Configure existing absolute media directories without links."
                )
        return self

    @classmethod
    def from_env(cls):
        key = os.environ.get("VIDEO_WORKER_API_KEY", "")
        key_file = os.environ.get("VIDEO_WORKER_API_KEY_FILE")
        if not key and key_file:
            path = Path(key_file)
            if not path.is_file() or path.is_symlink() or path.stat().st_size > 1024:
                raise ValueError("API key file is unavailable.")
            if os.name != "nt" and path.stat().st_mode & 0o077:
                raise ValueError("API key file must be private (mode 600).")
            key = path.read_text().strip()
        return cls(
            os.environ.get("VIDEO_WORKER_API_URL", "https://videoworker.dev"),
            key,
            Path(os.environ.get("VIDEO_WORKER_UPLOAD_ROOT", "")),
            Path(os.environ.get("VIDEO_WORKER_DOWNLOAD_ROOT", "")),
        ).validate()


def local_name(value):
    reserved = {"CON", "PRN", "AUX", "NUL"} | {
        prefix + str(number) for prefix in ("COM", "LPT") for number in range(1, 10)
    }
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 128
        or value.startswith(".")
        or value != value.rstrip(" .")
        or any(c in '/\\:<>"|?*' or not c.isprintable() for c in value)
        or value.split(".")[0].upper() in reserved
        or Path(value).suffix.lower()
        not in {
            ".mp4",
            ".mp3",
            ".wav",
            ".webm",
            ".gif",
            ".png",
            ".jpg",
            ".jpeg",
            ".mkv",
            ".mov",
            ".ogg",
            ".flac",
        }
    ):
        raise ConnectorError("invalid_media_filename")
    return value


def job_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{32}", value):
        raise ConnectorError("invalid_job_id")
    return value


@contextmanager
def media_file(root, filename, *, write=False):
    """Pin POSIX directories without following links; verify Windows handles."""
    directory = None
    handle = None
    guards = []
    close_guard = None
    identity = None
    try:
        flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL) if write else os.O_RDONLY
        if os.name != "nt":
            directory = os.open(root.anchor, os.O_RDONLY | os.O_DIRECTORY)
            for part in root.parts[1:]:
                child = os.open(
                    part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
                )
                os.close(directory)
                directory = child
            handle = os.open(
                filename, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=directory
            )
        else:
            import ctypes
            import msvcrt
            from ctypes import wintypes

            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            create_directory = kernel.CreateFileW
            create_directory.argtypes = [
                wintypes.LPCWSTR,
                wintypes.DWORD,
                wintypes.DWORD,
                ctypes.c_void_p,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.HANDLE,
            ]
            create_directory.restype = wintypes.HANDLE
            close_guard = kernel.CloseHandle
            close_guard.argtypes = [wintypes.HANDLE]
            close_guard.restype = wintypes.BOOL
            attributes = kernel.GetFileInformationByHandleEx
            attributes.argtypes = [
                wintypes.HANDLE,
                ctypes.c_int,
                ctypes.c_void_p,
                wintypes.DWORD,
            ]
            attributes.restype = wintypes.BOOL
            final_path = kernel.GetFinalPathNameByHandleW
            final_path.argtypes = [
                wintypes.HANDLE,
                wintypes.LPWSTR,
                wintypes.DWORD,
                wintypes.DWORD,
            ]
            final_path.restype = wintypes.DWORD
            # Hold every ancestor without FILE_SHARE_DELETE before creating a
            # child. OPEN_REPARSE_POINT plus attribute checks reject junctions.
            # This closes the pre-creation root swap, not just post-open reads.
            current = Path(root.anchor)
            for part in root.parts[1:]:
                current /= part
                guard = create_directory(
                    str(current),
                    0x80000000,
                    0x1 | 0x2,
                    None,
                    3,
                    0x02000000 | 0x00200000,
                    None,
                )
                if guard == ctypes.c_void_p(-1).value:
                    raise OSError("Media directory cannot be pinned")
                guards.append(guard)
                info = (wintypes.DWORD * 2)()
                if (
                    not attributes(guard, 9, ctypes.byref(info), ctypes.sizeof(info))
                    or info[0] & 0x400
                    or not info[0] & 0x10
                ):
                    raise ConnectorError("media_link_rejected")
            handle = os.open(root / filename, flags | os.O_BINARY, 0o600)
            buffer = ctypes.create_unicode_buffer(32768)
            length = final_path(msvcrt.get_osfhandle(handle), buffer, len(buffer), 0)
            if not 0 < length < len(buffer) or os.path.normcase(
                buffer.value.removeprefix("\\\\?\\")
            ) != os.path.normcase(str(root / filename)):
                raise ConnectorError("media_link_rejected")
        identity = os.fstat(handle)
        if not stat.S_ISREG(identity.st_mode):
            raise ConnectorError("regular_media_file_required")
        with os.fdopen(handle, "wb" if write else "rb") as stream:
            handle = None
            yield stream
    except BaseException:
        if write and identity is not None:
            # Directory handles stay pinned until cleanup finishes. Refuse to
            # remove another file if a concurrent actor replaced the filename.
            try:
                observed = os.stat(
                    root / filename if directory is None else filename,
                    dir_fd=directory,
                    follow_symlinks=False,
                )
                if (observed.st_dev, observed.st_ino) == (
                    identity.st_dev,
                    identity.st_ino,
                ):
                    os.unlink(
                        root / filename if directory is None else filename,
                        dir_fd=directory,
                    )
            except OSError:
                pass
        raise
    finally:
        if handle is not None:
            os.close(handle)
        if directory is not None:
            os.close(directory)
        for guard in reversed(guards):
            close_guard(guard)


class Connector:
    def __init__(self, settings, *, transport=None):
        self.settings = settings.validate()
        self.origin = settings.origin.rstrip("/")
        self.client = httpx.Client(
            headers={"Authorization": "Bearer " + settings.api_key},
            timeout=30,
            trust_env=False,
            follow_redirects=False,
            transport=transport,
        )

    def close(self):
        self.client.close()

    @staticmethod
    def checked(response, *, uncertain=False):
        if 200 <= response.status_code < 300:
            return
        code = {
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            409: "conflict",
            410: "expired",
            429: "rate_limited",
            503: "service_unavailable",
        }.get(response.status_code, "request_rejected")
        retry = response.headers.get("retry-after", "")
        raise ConnectorError(
            code,
            status=response.status_code,
            uncertain=uncertain and response.status_code >= 500,
            retry_after=int(retry)
            if retry.isascii() and retry.isdigit() and len(retry) <= 4
            else None,
        )

    def call(self, method, path, *, uncertain=False, preset=False, **kwargs):
        try:
            with self.client.stream(method, self.origin + path, **kwargs) as response:
                if preset and response.status_code == 404:
                    data = bytearray()
                    for chunk in response.iter_bytes():
                        if len(data) + len(chunk) > 4096:
                            break
                        data.extend(chunk)
                    try:
                        detail = json.loads(data).get("detail")
                    except (ValueError, AttributeError):
                        detail = None
                    code = (
                        "presets_unsupported"
                        if detail == "Not Found"
                        else "input_unavailable"
                        if detail
                        == "An input file is missing or expired. Upload it again."
                        else "preset_not_found"
                        if isinstance(detail, dict)
                        and detail.get("code") == "preset_not_found"
                        else "preset_unavailable"
                    )
                    raise ConnectorError(code, status=404)
                self.checked(response, uncertain=uncertain)
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 1024**2:
                        raise ConnectorError("response_too_large", uncertain=uncertain)
                result = json.loads(body)
                if not isinstance(result, dict):
                    raise ConnectorError(
                        "invalid_service_response", uncertain=uncertain
                    )
                return result
        except httpx.HTTPError:
            raise ConnectorError("network_error", uncertain=uncertain) from None
        except (json.JSONDecodeError, UnicodeError):
            raise ConnectorError(
                "invalid_service_response", uncertain=uncertain
            ) from None

    def usage(self):
        return self.call("GET", "/v1/usage")

    def list_jobs(self):
        return self.call("GET", "/v1/jobs")

    def presets(self):
        # REST metadata is public; this owned read verifies the MCP jobs:read scope.
        self.list_jobs()
        try:
            return self.call("GET", "/v1/presets")
        except ConnectorError as exc:
            if exc.detail.get("status") == 404:
                raise ConnectorError("presets_unsupported", status=404) from None
            raise

    def run_preset(
        self,
        preset_id,
        version,
        inputs,
        parameters,
        timeout_seconds,
        request_id,
        webhook_endpoint_id=None,
    ):
        try:
            key = str(UUID(request_id))
        except (ValueError, TypeError, AttributeError):
            raise ConnectorError("invalid_request_id") from None
        result = self.call(
            "POST",
            "/v1/jobs/from-preset",
            json={
                "preset_id": preset_id,
                "version": version,
                "inputs": inputs,
                "parameters": parameters,
                "timeout_seconds": timeout_seconds,
                **self.webhook_options(webhook_endpoint_id),
            },
            headers={"Idempotency-Key": key},
            uncertain=True,
            preset=True,
        )
        if not isinstance(result.get("id"), str) or not re.fullmatch(
            r"[a-f0-9]{32}", result["id"]
        ):
            raise ConnectorError("invalid_service_response", uncertain=True)
        return result

    def get_job(self, identifier):
        return self.call("GET", "/v1/jobs/" + job_id(identifier))

    def webhook_options(self, endpoint_id):
        if endpoint_id is None:
            return {}
        if not isinstance(endpoint_id, str) or not re.fullmatch(
            r"[a-f0-9]{32}", endpoint_id
        ):
            raise ConnectorError("invalid_webhook_endpoint")
        if self.call("GET", "/v1/health").get("webhooks_enabled") is not True:
            raise ConnectorError("webhooks_unsupported")
        return {"webhook_endpoint_id": endpoint_id}

    def create_job(
        self,
        inputs,
        args,
        outputs,
        timeout_seconds,
        request_id,
        webhook_endpoint_id=None,
    ):
        try:
            key = str(UUID(request_id))
        except (ValueError, TypeError, AttributeError):
            raise ConnectorError("invalid_request_id") from None
        return self.call(
            "POST",
            "/v1/jobs",
            json={
                "inputs": inputs,
                "args": args,
                "outputs": outputs,
                "timeout_seconds": timeout_seconds,
                **self.webhook_options(webhook_endpoint_id),
            },
            headers={"Idempotency-Key": key},
            uncertain=True,
        )

    def delete_job_outputs(self, identifier):
        return self.call(
            "DELETE", "/v1/jobs/" + job_id(identifier) + "/outputs", uncertain=True
        )

    def cancel_job(self, identifier):
        return self.call(
            "POST",
            "/v1/jobs/" + job_id(identifier) + "/cancel",
            headers={"Content-Type": "application/octet-stream"},
            uncertain=True,
        )

    def path(self, root, filename):
        local_name(filename)
        if root.is_symlink() or root.is_junction() or root.resolve() != root:
            raise ConnectorError("media_directory_changed")
        path = root / filename
        if path.is_symlink() or path.is_junction():
            raise ConnectorError("media_link_rejected")
        return path

    def media_limits(self):
        limits = self.call("GET", "/v1/limits")
        for key, ceiling in (
            ("max_upload_bytes", 2 * 1024**3),
            ("max_output_bytes", 1024**3),
        ):
            if type(limits.get(key)) is not int or not 0 < limits[key] <= ceiling:
                raise ConnectorError("invalid_service_limits")
        return limits

    def upload(self, filename):
        path = self.path(self.settings.upload_root, filename)
        maximum = self.media_limits()["max_upload_bytes"]
        try:
            # Links are refused, and callers can name only flat media files in
            # the operator-selected folder. No directory traversal or globbing.
            with media_file(path.parent, path.name) as source:
                size = os.fstat(source.fileno()).st_size
                if not 0 < size <= maximum:
                    raise ConnectorError("upload_size_limit")

                def chunks():
                    remaining = size
                    while remaining:
                        chunk = source.read(min(65536, remaining))
                        if not chunk:
                            raise ConnectorError("local_file_changed", uncertain=True)
                        remaining -= len(chunk)
                        yield chunk

                return self.call(
                    "POST",
                    "/v1/files",
                    content=chunks(),
                    timeout=httpx.Timeout(900, connect=10),
                    headers={
                        "Content-Type": "application/octet-stream",
                        "Content-Length": str(size),
                        "X-Filename": quote(filename, safe=""),
                    },
                    uncertain=True,
                )
        except OSError:
            raise ConnectorError("local_file_unavailable") from None

    def download(self, identifier, output_name, destination):
        identifier, output_name = job_id(identifier), local_name(output_name)
        maximum = DOWNLOAD_LIMIT
        if not MEDIA_NAME.fullmatch(output_name):
            raise ConnectorError("invalid_output_name")
        job = self.get_job(identifier)
        if job.get("state") != "succeeded" or output_name not in {
            item.get("name") for item in job.get("outputs", [])
        }:
            raise ConnectorError("output_not_available")
        declared = next(
            item.get("size_bytes")
            for item in job["outputs"]
            if item.get("name") == output_name
        )
        if declared is not None:
            if type(declared) is not int or not 0 < declared <= 1024**3:
                raise ConnectorError("invalid_service_response")
            maximum = declared
        path = self.path(self.settings.download_root, destination)
        try:
            # Derive the owned API route; never follow a URL from tool
            # arguments or the job response with the bearer credential.
            with (
                media_file(path.parent, path.name, write=True) as target,
                self.client.stream(
                    "GET",
                    self.origin + "/v1/jobs/" + identifier + "/outputs/" + output_name,
                    timeout=httpx.Timeout(900, connect=10),
                ) as response,
            ):
                self.checked(response)
                total = 0
                for chunk in response.iter_bytes(chunk_size=65536):
                    total += len(chunk)
                    if total > maximum:
                        raise ConnectorError("download_size_limit")
                    target.write(chunk)
                if total == 0:
                    raise ConnectorError("empty_output")
            return {"filename": destination, "size_bytes": total}
        except (OSError, httpx.HTTPError, ConnectorError) as exc:
            if isinstance(exc, ConnectorError):
                raise
            raise ConnectorError("download_failed") from None
