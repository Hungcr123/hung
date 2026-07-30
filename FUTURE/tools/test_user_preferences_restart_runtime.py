"""Verify preference retry, server-time ordering, and ACK durability across hard restart."""

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


def wait_health(old_pid: int, timeout: float = 45.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            payload = health()
            if payload.get("ok") and int(payload.get("pid", 0) or 0) != old_pid:
                return payload
        except requests.RequestException:
            pass
        time.sleep(0.4)
    raise RuntimeError("Server 2 did not become healthy after preference restart")


def start_server() -> None:
    subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--replace-old"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def login(password: str) -> tuple[dict[str, str], dict]:
    response = requests.post(f"{BASE}/auth/login", json={"username": USER, "password": password}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    return {"Authorization": f"Bearer {payload.get('token', '')}"}, payload


def save(headers: dict[str, str], payload: dict) -> dict:
    response = requests.post(
        f"{BASE}/auth/preferences",
        headers={**headers, "X-Future-Response-Mode": "preferences-compact-v1"},
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def row() -> tuple | None:
    connection = sqlite3.connect(DATABASE)
    try:
        return connection.execute(
            "SELECT preferences_json,server_revision,updated_at_utc,updated_epoch FROM user_preferences WHERE username=?",
            (USER,),
        ).fetchone()
    finally:
        connection.close()


def restore_row(previous: tuple | None) -> None:
    connection = sqlite3.connect(DATABASE)
    try:
        if previous is None:
            connection.execute("DELETE FROM user_preferences WHERE username=?", (USER,))
        else:
            connection.execute(
                "INSERT INTO user_preferences(username,preferences_json,server_revision,updated_at_utc,updated_epoch) VALUES(?,?,?,?,?) "
                "ON CONFLICT(username) DO UPDATE SET preferences_json=excluded.preferences_json,server_revision=excluded.server_revision,"
                "updated_at_utc=excluded.updated_at_utc,updated_epoch=excluded.updated_epoch",
                (USER, *previous),
            )
        connection.commit()
    finally:
        connection.close()


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this runtime test only")
    previous = row()
    old_pid = 0
    restarted_pid = 0
    marker = f"runtime-{uuid.uuid4().hex[:16]}"
    try:
        headers, _login_payload = login(password)
        before = row()
        before_revision = int(before[1] or 0) if before else 0
        patch = {
            "ghost_en_voice": {"voice": marker, "rate": 1.1},
            "updated_at": "2099-01-01T00:00:00Z",
        }
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            responses = list(pool.map(lambda _index: save(headers, patch), range(20)))
        revisions = {int(item.get("server_revision", 0) or 0) for item in responses}
        if revisions != {before_revision + 1}:
            raise RuntimeError(f"Concurrent identical patch revisions were not coalesced semantically: {revisions}")
        acknowledged = row()
        if acknowledged is None or int(acknowledged[1] or 0) != before_revision + 1:
            raise RuntimeError("Preference ACK did not match the durable row")
        stored = json.loads(str(acknowledged[0]))
        if stored.get("ghost_en_voice", {}).get("voice") != marker or "2099" in str(acknowledged[2]):
            raise RuntimeError("Client time or payload ordering corrupted the durable preference")

        old_pid = int(health().get("pid", 0) or 0)
        psutil.Process(old_pid).kill()
        psutil.Process(old_pid).wait(timeout=15)
        start_server()
        restarted = wait_health(old_pid)
        restarted_pid = int(restarted.get("pid", 0) or 0)
        fresh_headers, fresh_login = login(password)
        restored = fresh_login.get("preferences") or {}
        if restored.get("ghost_en_voice", {}).get("voice") != marker:
            durable_after_restart = row()
            raise RuntimeError(
                "Fresh login did not restore the ACKed preference: "
                f"login={restored.get('ghost_en_voice')} durable={durable_after_restart}"
            )
        retried = save(fresh_headers, patch)
        if int(retried.get("server_revision", 0) or 0) != before_revision + 1:
            raise RuntimeError("Post-restart exact retry incremented preference revision")
        if int(row()[1] or 0) != before_revision + 1:
            raise RuntimeError("Post-restart retry changed the durable row")
        print(json.dumps({
            "user_preferences_restart_runtime": "ok",
            "old_pid": old_pid,
            "restarted_pid": restarted_pid,
            "concurrent_requests": 20,
            "revision_delta": 1,
            "hard_kill_restore": True,
            "post_restart_retry": "noop",
            "client_time_ignored": True,
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
        restore_row(previous)
        start_server()
        wait_health(current_pid)


if __name__ == "__main__":
    raise SystemExit(main())
