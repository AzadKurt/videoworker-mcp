"""Minimal durable Standard Webhooks receiver; expose through your HTTPS proxy.

Set WEBHOOK_SIGNING_SECRET to your endpoint secret, then run this file. It binds
only 127.0.0.1:9005 and queues verified events in webhook-events.sqlite3. Process
pending records separately with your own idempotent workflow. No API key needed
for receipt; retrieve job/results later with your ordinary scoped credential.
"""

import base64
import hashlib
import hmac
import json
import os
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def signing_key(secret):
    key = base64.b64decode(secret.removeprefix("whsec_"), validate=True)
    if len(key) < 32:
        raise ValueError("Signing secrets must contain at least 32 random bytes.")
    return key


def verified(secret, headers, body, *, now=None):
    try:
        stamp = int(headers["webhook-timestamp"])
        if abs((time.time() if now is None else now) - stamp) > 300:
            return False
        key = signing_key(secret)
        message = (
            headers["webhook-id"].encode() + b"." + str(stamp).encode() + b"." + body
        )
        expected = (
            "v1," + base64.b64encode(hmac.digest(key, message, hashlib.sha256)).decode()
        )
        return any(
            hmac.compare_digest(expected, part)
            for part in headers["webhook-signature"].split()
        )
    except (ValueError, KeyError, TypeError):
        return False


def store_event(path, event_id, body):
    with sqlite3.connect(path, timeout=5) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.execute(
            "CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,payload BLOB NOT NULL,state TEXT NOT NULL DEFAULT 'pending')"
        )
        db.execute(
            "INSERT OR IGNORE INTO events(id,payload) VALUES (?,?)", (event_id, body)
        )
        # The context commits before the HTTP acknowledgement. An application
        # worker consumes this durable queue; duplicate receipts do not enqueue twice.


class Receiver(BaseHTTPRequestHandler):
    def do_POST(self):
        length = self.headers.get("Content-Length", "")
        if (
            self.path != "/webhooks/videoworker"
            or self.headers.get("Transfer-Encoding")
            or not length.isdecimal()
            or not 0 < int(length) <= 4096
        ):
            self.send_error(400)
            return
        self.connection.settimeout(10)
        body = self.rfile.read(int(length))
        headers = {k.lower(): v for k, v in self.headers.items()}
        if not verified(os.environ["WEBHOOK_SIGNING_SECRET"], headers, body):
            self.send_error(401)
            return
        try:
            event = json.loads(body)
            if not isinstance(event, dict) or event.get("id") != headers["webhook-id"]:
                raise ValueError()
        except (ValueError, TypeError):
            self.send_error(400)
            return
        store_event("webhook-events.sqlite3", headers["webhook-id"], body)
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):
        pass  # Never print payloads, endpoint query tokens or signing secrets.


if __name__ == "__main__":
    try:
        signing_key(os.environ.get("WEBHOOK_SIGNING_SECRET", ""))
    except ValueError:
        raise SystemExit(
            "Set a valid WEBHOOK_SIGNING_SECRET privately before starting "
            "(base64 of at least 32 random bytes)."
        ) from None
    ThreadingHTTPServer(("127.0.0.1", 9005), Receiver).serve_forever()
