# Source preview: optional job notifications

This source checkout adds optional `webhook_endpoint_id` to `create_job` and
`run_preset`. It requires a deployment whose `/v1/health` explicitly reports
`webhooks_enabled: true`. Otherwise the connector refuses the callback
submission; it never silently submits a job without your requested notification.
The previously published v0.2.0 wheel does not include this addition. No new
package release or public service activation is implied by these source changes.

Register your own public HTTPS receiver in the VideoWorker dashboard and save
its one-time signing secret there. Agent tools can select the ID but cannot
register destinations or retrieve secrets. Normal job scopes, processing quota,
idempotency, result authentication and file expiry continue to apply.

Once enabled, a call can include:

```json
{
  "preset_id": "web-mp4",
  "version": 1,
  "inputs": ["YOUR_OWNED_UPLOADED_FILE_ID"],
  "parameters": { "max_width": 640 },
  "timeout_seconds": 10,
  "request_id": "GENERATE_A_UUID_ONCE_AND_KEEP_FOR_RETRIES",
  "webhook_endpoint_id": "YOUR_REGISTERED_ENDPOINT_ID"
}
```

Events are `job.succeeded`, `job.failed` or `job.cancelled`, signed using
[Standard Webhooks](https://github.com/standard-webhooks/standard-webhooks/blob/main/spec/standard-webhooks.md).
Use raw request bytes, verify the five-minute timestamp window and deduplicate
the event ID. Queue work durably before returning 2xx; fetch results separately
with your ordinary workload credential. Retries/redelivery never run a new job.

[webhook_receiver.py](../examples/webhook_receiver.py) is a small standard-library
example with signature checks and a durable SQLite inbox. It binds loopback;
place it behind your own HTTPS ingress. Set `WEBHOOK_SIGNING_SECRET` privately
to your endpoint secret, not your API key. The example stores verified pending
events only; your application consumes that inbox as a separate idempotent step.

Do not register a webhook merely to keep an interactive agent waiting: the
agent needs an actual supported receiver/integration. Ordinary `get_job`
polling remains appropriate when no receiver exists.
