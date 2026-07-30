"""Verify chat idempotency, server time, and acknowledged writes across a hard restart."""

from __future__ import annotations

import concurrent.futures
import json
import os
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path

import psutil
import requests


BASE = "http://127.0.0.1:8877"
ROOT = Path(__file__).parents[2]
DATABASE = Path(r"C:\server data\server2.db")
USER = "codexload100"


def health(timeout: float = 2.0) -> dict:
    return requests.get(f"{BASE}/health", timeout=timeout).json()


def wait_health(*, different_from: int = 0, timeout: float = 45.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            payload = health()
            if payload.get("ok") and int(payload.get("pid", 0) or 0) != int(different_from or 0):
                return payload
        except requests.RequestException:
            pass
        time.sleep(0.4)
    raise RuntimeError("Server 2 did not become healthy after restart")


def start_server() -> None:
    subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--replace-old"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def login(password: str) -> dict[str, str]:
    response = requests.post(f"{BASE}/auth/login", json={"username": USER, "password": password}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if payload.get("server_data", {}).get("load_test") is not True:
        raise RuntimeError("Runtime test user is not isolated as load-test data")
    return {"Authorization": f"Bearer {payload.get('token', '')}"}


def send(headers: dict[str, str], text: str, operation_id: str) -> dict:
    response = requests.post(
        f"{BASE}/chat/send",
        headers=headers,
        json={
            "text": text,
            "language": "en",
            "audio_enabled": False,
            "operation_id": operation_id,
            # Client time must never influence authoritative chat ordering.
            "at": "2099-01-01T00:00:00Z",
            "ts": 4_070_908_800,
        },
        timeout=30,
    )
    response.raise_for_status()
    return dict(response.json().get("message") or {})


def rows(prefix: str) -> list[sqlite3.Row]:
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    try:
        return connection.execute(
            "SELECT id,operation_id,message_json,created_at_utc,created_epoch FROM chat_messages "
            "WHERE username=? AND message_json LIKE ? ORDER BY id",
            (USER, f"%{prefix}%"),
        ).fetchall()
    finally:
        connection.close()


def cleanup(prefix: str) -> None:
    connection = sqlite3.connect(DATABASE)
    try:
        connection.execute(
            "DELETE FROM chat_messages WHERE username=? AND message_json LIKE ?",
            (USER, f"%{prefix}%"),
        )
        connection.commit()
    finally:
        connection.close()


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this runtime test only")
    prefix = f"codex-chat-restart-{uuid.uuid4().hex}"
    old_pid = 0
    restarted_pid = 0
    try:
        headers = login(password)
        concurrent_operation = f"{prefix}:concurrent"
        before_epoch = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            results = list(pool.map(
                lambda _index: send(headers, f"{prefix} concurrent", concurrent_operation),
                range(20),
            ))
        after_epoch = time.time()
        if len({int(item.get("id", 0) or 0) for item in results}) != 1:
            raise RuntimeError("Concurrent duplicate operation returned multiple message IDs")
        concurrent_rows = rows(prefix)
        if len(concurrent_rows) != 1:
            raise RuntimeError(f"Concurrent duplicate operation created {len(concurrent_rows)} rows")
        created_epoch = float(concurrent_rows[0]["created_epoch"] or 0)
        if not before_epoch - 1 <= created_epoch <= after_epoch + 1:
            raise RuntimeError("Client-supplied future time influenced chat ordering")

        durable_operation = f"{prefix}:durable"
        acknowledged = send(headers, f"{prefix} durable", durable_operation)
        acknowledged_id = int(acknowledged.get("id", 0) or 0)
        if acknowledged_id <= 0 or len(rows(prefix)) != 2:
            raise RuntimeError("Durable chat message was not committed before ACK")

        old_pid = int(health().get("pid", 0) or 0)
        psutil.Process(old_pid).kill()
        psutil.Process(old_pid).wait(timeout=15)
        start_server()
        restarted = wait_health(different_from=old_pid)
        restarted_pid = int(restarted.get("pid", 0) or 0)

        fresh_headers = login(password)
        poll = requests.get(
            f"{BASE}/chat/poll",
            headers=fresh_headers,
            params={"since": 0, "open": "0", "notice_after": 2_147_483_647},
            timeout=30,
        )
        poll.raise_for_status()
        restored = [item for item in poll.json().get("messages", []) if str(item.get("text", "")).startswith(prefix)]
        if len(restored) != 2 or acknowledged_id not in {int(item.get("id", 0) or 0) for item in restored}:
            raise RuntimeError("Fresh-session poll did not restore acknowledged chat rows")
        retried = send(fresh_headers, f"{prefix} durable", durable_operation)
        if int(retried.get("id", 0) or 0) != acknowledged_id or len(rows(prefix)) != 2:
            raise RuntimeError("Post-restart retry was not idempotent")

        print(json.dumps({
            "chat_restart_runtime": "ok",
            "old_pid": old_pid,
            "restarted_pid": restarted_pid,
            "concurrent_requests": 20,
            "concurrent_rows": 1,
            "acknowledged_rows": 2,
            "fresh_poll_rows": 2,
            "post_restart_retry_rows": 2,
            "server_time_authoritative": True,
        }, sort_keys=True))
        return 0
    finally:
        try:
            current_pid = int(health().get("pid", 0) or 0)
        except requests.RequestException:
            current_pid = 0
        if current_pid:
            psutil.Process(current_pid).kill()
            psutil.Process(current_pid).wait(timeout=15)
        cleanup(prefix)
        start_server()
        wait_health(different_from=current_pid)


if __name__ == "__main__":
    raise SystemExit(main())
