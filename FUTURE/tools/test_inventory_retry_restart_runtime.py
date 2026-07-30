"""Verify inventory event idempotency across Server 2 restart and same-process retries."""

from __future__ import annotations

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
USER = "codexload002"


def health() -> dict:
    return requests.get(f"{BASE}/health", timeout=5).json()


def wait_health(different_from: int, timeout: float = 45.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            payload = health()
            if payload.get("ok") and int(payload.get("pid", 0) or 0) != different_from:
                return payload
        except requests.RequestException:
            pass
        time.sleep(0.4)
    raise RuntimeError("Server 2 did not recover after inventory retry restart test")


def login(password: str) -> dict[str, str]:
    response = requests.post(f"{BASE}/auth/login", json={"username": USER, "password": password}, timeout=20)
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['token']}"}


def award(headers: dict[str, str], payload: dict) -> dict:
    response = requests.post(f"{BASE}/inventory/award?response=delta-v1", headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def stable_writer_tasks(timeout: float = 5.0) -> int:
    deadline = time.monotonic() + timeout
    previous = None
    stable = 0
    while time.monotonic() < deadline:
        current = int((health().get("sqlite_writer") or {}).get("tasks", 0) or 0)
        if current == previous:
            stable += 1
            if stable >= 3:
                return current
        else:
            previous = current
            stable = 0
        time.sleep(0.3)
    raise RuntimeError("SQLite writer did not stabilize during inventory restart test")


def start_server() -> None:
    subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--replace-old"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this runtime test only")
    event_id = f"inventory-restart:{uuid.uuid4().hex}"
    item_id = f"retry_restart_{uuid.uuid4().hex[:12]}"
    payload = {
        "event_id": event_id,
        "quantity": 1,
        "item": {"id": item_id, "name": "Retry Restart Probe", "use": "Inventory restart idempotency test"},
    }
    headers = login(password)
    first = award(headers, payload)
    if first.get("awarded") is not True:
        raise RuntimeError("Initial inventory award was not committed")
    old_pid = int(health().get("pid", 0) or 0)
    psutil.Process(old_pid).kill()
    psutil.Process(old_pid).wait(timeout=15)
    start_server()
    restarted = wait_health(old_pid)
    fresh_headers = login(password)
    writer_before = stable_writer_tasks()
    retry_after_restart = award(fresh_headers, payload)
    writer_middle = stable_writer_tasks()
    retry_from_ram = award(fresh_headers, payload)
    writer_after = stable_writer_tasks()
    connection = sqlite3.connect(DATABASE)
    event_rows = connection.execute(
        "SELECT COUNT(*) FROM inventory_events WHERE username=? AND event_id=?", (USER, event_id)
    ).fetchone()[0]
    quantity = connection.execute(
        "SELECT quantity FROM inventory_items WHERE username=? AND item_id=?", (USER, item_id)
    ).fetchone()[0]
    connection.close()
    restart_retry_tasks = int(writer_middle) - int(writer_before)
    ram_retry_tasks = int(writer_after) - int(writer_middle)
    assert retry_after_restart.get("awarded") is False
    assert retry_from_ram.get("awarded") is False
    assert restart_retry_tasks == 1, (writer_before, writer_middle, writer_after)
    assert ram_retry_tasks == 0, (writer_before, writer_middle, writer_after)
    assert int(event_rows) == 1 and int(quantity) == 1
    print({
        "inventory_retry_restart": "ok",
        "old_pid": old_pid,
        "new_pid": int(restarted.get("pid", 0) or 0),
        "restart_retry_tasks": restart_retry_tasks,
        "ram_retry_tasks": ram_retry_tasks,
        "event_rows": int(event_rows),
        "quantity": int(quantity),
        "cleanup_required": True,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
