# videoworker MCP

**Give your AI agent FFmpeg: upload local media, run a remote job, and save the result.**

An MIT-licensed, local stdio MCP connector for the [videoworker](https://videoworker.dev)
video, audio and image processing API. Bring standard FFmpeg arguments; our workers
run them. No local FFmpeg installation required.

[Get started free](https://videoworker.dev/pricing) ·
[Hosted MCP](https://videoworker.dev/mcp) ·
[REST API](https://videoworker.dev/docs) ·
[Releases](https://github.com/AzadKurt/videoworker-mcp/releases) ·
[Listed on Glama](https://glama.ai/mcp/servers/AzadKurt/videoworker-mcp)

## Choose your connection

|                   | Local connector — this repo          | Hosted MCP                                        |
| ----------------- | ------------------------------------ | ------------------------------------------------- |
| Best for          | Local file uploads and downloads     | Connecting without installing Python              |
| Transport         | stdio                                | Streamable HTTP                                   |
| Sign in           | Scoped API key in a private file     | Browser login and OAuth consent                   |
| Local file access | Named media in your selected folders | None; upload via web or REST first                |
| Setup             | Quick start below                    | [Hosted setup guide](https://videoworker.dev/mcp) |

Both use the same account and allowance. The connector is free software; hosted
processing follows the [current plans and limits](https://videoworker.dev/pricing).
Free accounts receive a small monthly allowance. Check pricing for the Starter
launch offer and its availability; a trial is not required to use Free.

## Quick start

### 1. Install — no checkout or Git needed

Requires **Python 3.12 or newer**. Install the versioned release wheel:

```sh
python -m pip install "https://github.com/AzadKurt/videoworker-mcp/releases/download/v0.1.0/videoworker_mcp-0.1.0-py3-none-any.whl"
python -m videoworker_mcp --version
```

On Windows, use `py -3.12` instead of `python` if needed. On macOS/Linux, your
command may be `python3`. Use that same Python installation in your MCP config.
Print its full path with:

```sh
python -c "import sys; print(sys.executable)"
```

Alternative with Git installed:

```sh
python -m pip install "git+https://github.com/AzadKurt/videoworker-mcp.git@v0.1.0"
```

This package is not on PyPI yet. `pip install videoworker-mcp` is not the command
for this release.

### 2. Create your workspace and private key file

Sign in to [your workspace](https://videoworker.dev/dashboard). Under API keys,
create a key with `usage:read`, `files:write`, `jobs:read`, `jobs:write` and
`outputs:read` for all ten tools. Save it as plain text in a file accessible
only to your user. On macOS/Linux: `chmod 600 /absolute/path/to/key`. On Windows,
keep it in your user profile and restrict its file permissions to you.

Create **uploads** and **downloads** folders. Both must exist and use absolute
paths. Keep only authorized media in uploads; keep the key file elsewhere.
Never paste the key into a chat or a shared client config.

### 3. Add your client config

Replace the Python and file/folder paths with your own. **Merge the entry into an
existing config**, preserving other servers. The values are paths, not secrets.
Restart or reload your client after saving.

#### Codex

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.videoworker]
command = "/absolute/path/to/python"
args = ["-m", "videoworker_mcp"]
startup_timeout_sec = 30
tool_timeout_sec = 960

[mcp_servers.videoworker.env]
VIDEO_WORKER_API_KEY_FILE = "/absolute/path/to/videoworker.key"
VIDEO_WORKER_UPLOAD_ROOT = "/absolute/path/to/uploads"
VIDEO_WORKER_DOWNLOAD_ROOT = "/absolute/path/to/downloads"
```

Windows forward-slash paths work, e.g. `C:/Users/YOU/media/uploads`. Ready-to-edit:
[Windows](examples/codex.windows.toml) / [macOS and Linux](examples/codex.posix.toml).
Keep the hosted connection named `videoworker_remote` if you also use it.

#### Claude Desktop

Open **Settings → Developer → Edit Config** and merge:

```json
{
  "mcpServers": {
    "videoworker": {
      "command": "/absolute/path/to/python",
      "args": ["-m", "videoworker_mcp"],
      "env": {
        "VIDEO_WORKER_API_KEY_FILE": "/absolute/path/to/videoworker.key",
        "VIDEO_WORKER_UPLOAD_ROOT": "/absolute/path/to/uploads",
        "VIDEO_WORKER_DOWNLOAD_ROOT": "/absolute/path/to/downloads"
      }
    }
  }
}
```

Ready-to-edit: [Windows](examples/claude-desktop.windows.json) /
[macOS and Linux](examples/claude-desktop.posix.json).

#### Cursor

Use the same JSON structure in `~/.cursor/mcp.json` (global), or
`.cursor/mcp.json` (project). Enable the server in Cursor's MCP settings.
Ready-to-edit: [Windows](examples/cursor.windows.json) /
[macOS and Linux](examples/cursor.posix.json).

Examples follow documented stdio config formats. Real MCP SDK discovery is
tested; this does not claim every desktop app/version was manually tested.

### 4. Try a small job

Put a small `clip.mp4` in uploads and ask your agent:

> Check my videoworker allowance first. I authorize uploading clip.mp4 from my
> configured uploads folder. Trim it to its first second and compress it as MP4.
> Create one job with a 10-second runtime limit. Keep its request_id for any retry,
> wait at least one second between status checks, and save the successful result
> as clip-small.mp4 in my downloads folder. Do not delete anything.

Flow: `get_usage` → `upload_file` → `create_job` → `get_job` → `download_result`.
See [example job arguments](examples/trim-and-compress.json): replace the input
file ID and generate a new UUID for each intended job.

### More than one input

[Workflow recipes](docs/workflows.md) cover joining clips, adding an image/logo,
and replacing a soundtrack. Each includes input order, behavior notes and a
ready-to-edit MCP JSON file. The same recipes are
[displayed on the website](https://videoworker.dev/docs#workflows) with copy buttons
for REST and MCP.

### Versioned presets

On a server that supports `GET /v1/presets`, use `list_presets` to discover
validated parameters, pinned versions and output filenames. Then call
`run_preset` with an uploaded file ID, explicit version, parameters, processing
maximum and a chosen UUID. [Example MCP arguments](examples/web-mp4.preset.mcp.json)
trim and resize video into H.264/AAC MP4. Other catalog entries extract MP3,
produce a JPEG thumbnail or render a short GIF.

The same ordinary job quota, ownership and storage rules apply. The timeout
reserves a processing maximum, not the clip duration. Poll `get_job` at most
once per second and download before expiry. Use the identical request and UUID
for retries within 48 hours; never automatically resubmit a lost reply. Defaults
and encoding behavior are pinned by version. Smaller output size is not guaranteed.

These new tools are staged locally and require the corresponding service
release. `presets_unsupported` means the server has no catalog;
`presets_unsupported` also identifies a missing execution route;
`preset_not_found` identifies an unknown ID/version and `input_unavailable`
means the owned upload is missing or expired. Unknown 404 shapes remain
`preset_unavailable`. No case silently falls back to another job. Listing
presets first checks the same key against the owned jobs-read endpoint, since
the REST metadata catalog itself is intentionally public.

## Tools

| Tool                 | Purpose                                   | API-key scope               |
| -------------------- | ----------------------------------------- | --------------------------- |
| `get_usage`          | Allowance, reservations and storage       | `usage:read`                |
| `list_jobs`          | Recent owned jobs                         | `jobs:read`                 |
| `list_presets`       | Versioned tasks, parameters and defaults  | `jobs:read`                 |
| `run_preset`         | One preset job with a stable retry UUID   | `jobs:write`                |
| `upload_file`        | Upload authorized local media             | `files:write`               |
| `create_job`         | FFmpeg job with a stable retry UUID       | `jobs:write`                |
| `get_job`            | Job state and output metadata             | `jobs:read`                 |
| `download_result`    | Save output to a new local file           | `jobs:read`, `outputs:read` |
| `cancel_job`         | Request cancellation; confirm termination | `jobs:write`                |
| `delete_job_outputs` | Delete results when requested             | `jobs:write`                |

## Configuration and troubleshooting

| Environment variable         | Value                                           |
| ---------------------------- | ----------------------------------------------- |
| `VIDEO_WORKER_API_KEY_FILE`  | Absolute path to a private plaintext key file   |
| `VIDEO_WORKER_UPLOAD_ROOT`   | Existing absolute folder of authorized media    |
| `VIDEO_WORKER_DOWNLOAD_ROOT` | Existing absolute destination folder            |
| `VIDEO_WORKER_API_URL`       | Optional; defaults to `https://videoworker.dev` |

`VIDEO_WORKER_API_KEY` is supported in private process environments and takes
precedence over the file. Never put it in a shared config or command line.
Custom origins require HTTPS, except explicit loopback HTTP for development.

- **ENOENT / server not found:** use the full Python path printed above, not a
  shell alias. GUI applications can have a different PATH.
- **Configuration error:** set the same variables in a terminal and run
  `python -m videoworker_mcp --check`. It validates local setup only, without API
  calls or credential/allowance verification. Help/version need no key.
- **Unauthorized / forbidden:** check your key, scopes and account in the
  dashboard. Never send credentials in a support message.
- **File rejected:** pass a flat name, not a path or URL. Local extensions:
  mp4, mp3, wav, webm, gif, png, jpg, jpeg, mkv, mov, ogg, flac. Linked folders
  and symlinks/junctions are rejected.
- **Slow transfer:** uploads/downloads can take up to 15 minutes per network
  operation. Configure suitable tool-call timeouts where supported. Closing a
  tool call does not cancel an accepted processing job.

## Data and retries

The service enforces account ownership, allowance, file limits and expiry.
The local process runs as your OS user; folder restrictions are application
guards, not an operating-system sandbox. No local FFmpeg is bundled or needed.

Downloads never overwrite files or follow agent-supplied output URLs. Declared
output sizes are bounded to 1 GiB; legacy metadata without a size has a 50-MiB
fallback cap. Transfers stream instead of loading a full video into memory.

Keep one UUID `request_id` and identical arguments for job retries (48 hours).
An uncertain response can still mean success. Uploads are not idempotent. Poll
no faster than once per second and download before expiry. Cancellation/deletion
are complete only after server confirmation. No billing/admin permissions needed.

## Development

```sh
python -m pip install '.[dev]'
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

Tests use tiny controlled HTTP fixtures and actual MCP SDK discovery. See
[release checks](RELEASE.md), [dependency licenses](DEPENDENCIES.md) and
[security reporting](SECURITY.md).

## License and support

[MIT](LICENSE) for the connector; hosted processing and the private backend are
separate. [GitHub issues](https://github.com/AzadKurt/videoworker-mcp/issues) or
[info@videoworker.dev](mailto:info@videoworker.dev).

Config references: [Codex](https://learn.chatgpt.com/docs/extend/mcp?surface=cli),
[Claude Desktop](https://modelcontextprotocol.io/docs/develop/connect-local-servers),
[Cursor](https://cursor.com/docs/mcp).
