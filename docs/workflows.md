# Multi-file workflows

[Browse the recipe cards](https://videoworker.dev/docs#workflows) for input order,
behavior notes, agent requests and copyable REST/MCP arguments. These workflows
use the ordinary API and processing allowance; no extra service is required.

| Workflow                                                 | Input 0     | Input 1           | Result                                                                                |
| -------------------------------------------------------- | ----------- | ----------------- | ------------------------------------------------------------------------------------- |
| [Join two clips](../examples/join-clips.mcp.json)        | First video | Second video      | Video-only 640 × 360 MP4 with black padding as needed                                 |
| [Image overlay](../examples/image-overlay.mcp.json)      | Video       | PNG/JPG image     | Image 48 px wide, bottom-right with 8 px inset; existing audio retained where present |
| [Replace soundtrack](../examples/replace-audio.mcp.json) | Video       | Replacement audio | Original soundtrack removed; short audio padded with silence, long audio cut to video |

The JSON files contain **MCP `create_job` arguments**. Replace both uploaded
file-ID placeholders and generate a fresh UUID once per intended job. Retain
that UUID and identical arguments for retries. The examples reserve at most ten
seconds; increase runtime for larger work within your account limits.

For REST, remove `request_id` from the JSON body and send the chosen UUID in the
`Idempotency-Key` header on `POST /v1/jobs`. All file IDs must belong to your
account. Check allowance first, poll at most once per second, and download before
the expiry returned by the service.

For local stdio, put authorized source files in your configured uploads folder
and let the agent call `upload_file`. For hosted OAuth MCP, upload on the website
or through REST first; it cannot read local paths. These JSON examples require
no update to the released 0.1.0 connector.

The readable catalog with prompts/notes is in [examples/workflows.json](../examples/workflows.json).
Three real tiny hosted jobs were verified using one-second 160 × 90 video
fixtures, a 64 × 16 PNG and a quarter-second WAV. This is basic functional
acceptance, not a claim that all codecs, damaged files or large workloads were tested.
