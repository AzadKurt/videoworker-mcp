# videoworker MCP

Standalone stdio connector for the [videoworker](https://videoworker.dev) FFmpeg
processing API. Agents can inspect allowance, upload explicitly authorized media,
create jobs, check progress, download results and request cancellation/deletion.

Local release candidate: not yet published to GitHub or PyPI. License selection
and dependency-license review remain release checks; see [release status](RELEASE.md).

## Install and run

Requires Python 3.12+. From this checkout:

```sh
python -m pip install .
python -m videoworker_mcp
```

The installed `videoworker-mcp` command is an equivalent entry point. Use either
entry point as the command of an MCP-capable client, including Codex. Client
configuration syntax varies; no API key should appear in a shared configuration.

Configure these environment variables privately in the client process:

| Variable                     | Value                                                    |
| ---------------------------- | -------------------------------------------------------- |
| `VIDEO_WORKER_API_URL`       | `https://videoworker.dev`                                |
| `VIDEO_WORKER_API_KEY_FILE`  | Absolute path to your private API-key file               |
| `VIDEO_WORKER_UPLOAD_ROOT`   | Existing absolute folder of media authorized for uploads |
| `VIDEO_WORKER_DOWNLOAD_ROOT` | Existing absolute destination folder                     |

The key needs the scopes for the tools you use: `usage:read`, `files:write`,
`jobs:read`, `jobs:write`, `outputs:read`. The dashboard issues scoped keys.
Keep the key file private (mode 600 on POSIX, your user only on Windows).
`VIDEO_WORKER_API_KEY` is also supported, but a private file avoids putting the
key into copied client configuration. Never pass it as a command-line argument.

## What runs where?

The connector runs locally; FFmpeg runs on the configured service. This does not
bundle or provide a free self-hosted processing backend. API allowance, ownership,
retention and cost limits apply equally to MCP jobs. Hosted remote MCP/OAuth is a
separate connection method and is not part of this package.

Filenames are flat, validated media names. Arbitrary paths, remote URLs and
symlink/junction folders are rejected. Uploads require the user's authorization.
The current connector independently caps downloads at 50 MiB even when a service
plan permits larger outputs; review this before distributing to large-file users.

Use one UUID `request_id` per job and retain it with identical arguments for
retries. A lost response may still have created a job. Check allowance first,
poll no faster than once per second, and download before result expiry.
Cancellation is complete only when the server confirms it. Deletion requires
the user's explicit request and server-confirmed removal.

## Development

```sh
python -m pip install '.[dev]'
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

The connector tests use controlled HTTP transports and MCP discovery. They do not
claim acceptance against every model/client, the production backend or real
large-media transfers.
