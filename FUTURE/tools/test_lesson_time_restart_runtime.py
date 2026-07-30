"""Verify acknowledged and signed-offline lesson time across a hard Server 2 restart."""

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
USER = "codexload100"
PATH = "common/File 02 - {7}.Space_V"


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
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--replace-old"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )


def reset_test_state() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "FUTURE" / "tools" / "provision_server2_load_test_users.py"), "--reset-state"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )


def login(password: str) -> dict[str, str]:
    response = requests.post(f"{BASE}/auth/login", json={"username": USER, "password": password}, timeout=20)
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json().get('token', '')}"}


def post_time(headers: dict[str, str], payload: dict) -> dict:
    response = requests.post(f"{BASE}/lesson/time", headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json().get("time", {})


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this runtime test only")
    reset_test_state()
    old_pid = 0
    new_pid = 0
    retry_pid = 0
    try:
        headers = login(password)
        session_id = f"lesson-restart-{uuid.uuid4().hex}"
        connection = sqlite3.connect(DATABASE)
        lesson_id_row = connection.execute(
            "SELECT file_id FROM lesson_file_aliases WHERE normalized_path=? COLLATE NOCASE AND active=1",
            (PATH,),
        ).fetchone()
        connection.close()
        lesson_id = str(lesson_id_row[0] or "") if lesson_id_row is not None else ""
        if not lesson_id.lower().startswith("ftg-lesson-"):
            raise RuntimeError("Restart test lesson has no active canonical ID")
        common = {
            "path": PATH,
            "lesson_id": lesson_id,
            "space": "Space_V",
            "protocol": "server-time-v1",
            "session_id": session_id,
        }
        started = post_time(headers, {**common, "seconds": 0, "sequence": 0})
        lease = str(started.get("offlineLease") or "")
        if not lease:
            raise RuntimeError("Session start did not return a signed offline lease")
        time.sleep(1.15)
        acknowledged = post_time(headers, {**common, "seconds": 1, "sequence": 1, "offline_lease": lease})
        if int(acknowledged.get("acceptedSeconds", 0) or 0) != 1:
            raise RuntimeError("Pre-kill write was not acknowledged as credited")

        old_pid = int(health().get("pid", 0) or 0)
        psutil.Process(old_pid).kill()
        psutil.Process(old_pid).wait(timeout=15)
        start_server()
        restarted = wait_health(different_from=old_pid)
        new_pid = int(restarted.get("pid", 0) or 0)

        fresh_headers = login(password)
        recovered = post_time(fresh_headers, {
            **common,
            "seconds": 0,
            "sequence": 2,
            "offline_lease": lease,
            "offline_claims": [{"sequence": 2, "seconds": 1}],
        })
        if recovered.get("heartbeatReason") != "offline_credited" or int(recovered.get("acceptedSeconds", 0) or 0) != 1:
            raise RuntimeError(f"Offline claim did not recover after restart: {recovered.get('heartbeatReason')}")

        connection = sqlite3.connect(DATABASE)
        row = connection.execute(
            "SELECT seconds,ticks FROM lesson_time WHERE username=?",
            (USER,),
        ).fetchone()
        connection.close()
        if tuple(map(int, row or ())) != (2, 2):
            raise RuntimeError(f"Durable lesson-time row mismatch after restart: {row}")

        psutil.Process(new_pid).kill()
        psutil.Process(new_pid).wait(timeout=15)
        start_server()
        retry_restart = wait_health(different_from=new_pid)
        retry_pid = int(retry_restart.get("pid", 0) or 0)
        retry_headers = login(password)
        retried = post_time(retry_headers, {
            **common,
            "seconds": 0,
            "sequence": 2,
            "offline_lease": lease,
            "offline_claims": [{"sequence": 2, "seconds": 1}],
        })
        if retried.get("heartbeatReason") != "replay" or int(retried.get("acceptedSeconds", 0) or 0) != 0:
            raise RuntimeError(f"Post-restart duplicate was not rejected durably: {retried.get('heartbeatReason')}")
        print({
            "lesson_time_restart_runtime": "ok",
            "old_pid": old_pid,
            "new_pid": new_pid,
            "retry_pid": retry_pid,
            "pre_kill_ack": 1,
            "post_restart_offline": 1,
            "post_second_restart_retry": 0,
            "durable_seconds": 2,
            "durable_ticks": 2,
        })
        return 0
    finally:
        reset_test_state()
        try:
            current_pid = int(health().get("pid", 0) or 0)
        except requests.RequestException:
            current_pid = 0
        start_server()
        wait_health(different_from=current_pid)


if __name__ == "__main__":
    raise SystemExit(main())
