import base64
import hmac
import importlib.util
import sqlite3
from pathlib import Path


def test_receiver_verifies_raw_bytes_and_deduplicates_durably(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "receiver", Path(__file__).parents[1] / "examples/webhook_receiver.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    key = b"k" * 32
    secret = "whsec_" + base64.b64encode(key).decode()
    body = b'{"id":"event"}'
    digest = base64.b64encode(
        hmac.digest(key, b"event.1000." + body, "sha256")
    ).decode()
    headers = {
        "webhook-id": "event",
        "webhook-timestamp": "1000",
        "webhook-signature": "v1," + digest,
    }
    assert module.verified(secret, headers, body, now=1000)
    assert not module.verified(secret, headers, body + b" ", now=1000)
    assert not module.verified(secret, headers, body, now=1301)
    path = tmp_path / "events.sqlite3"
    module.store_event(path, "event", body)
    module.store_event(path, "event", body)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT id,payload,state FROM events").fetchall() == [
            ("event", body, "pending")
        ]
