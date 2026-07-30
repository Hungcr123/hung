"""Stop Server 2, remove isolated load-test state, restart, and verify production chat."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import psutil
import requests


BASE = "http://127.0.0.1:8877"
ROOT = Path(__file__).parents[2]
DATABASE = Path(r"C:\server data\server2.db")


def health(timeout: float = 2.0) -> dict:
    return requests.get(f"{BASE}/health", timeout=timeout).json()


def wait_health(old_pid: int, timeout: float = 50.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            payload = health()
            if payload.get("ok") and int(payload.get("pid", 0) or 0) != old_pid:
                return payload
        except requests.RequestException:
            pass
        time.sleep(0.5)
    raise RuntimeError("Server 2 did not become healthy after cleanup")


def main() -> int:
    if not os.environ.get("FUTURE_TEST_PASSWORD", ""):
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for cleanup provisioning only")
    old_pid = int(health().get("pid", 0) or 0)
    psutil.Process(old_pid).kill()
    psutil.Process(old_pid).wait(timeout=15)
    subprocess.run(
        [sys.executable, str(ROOT / "FUTURE" / "tools" / "provision_server2_load_test_users.py"), "--reset-state"],
        cwd=ROOT,
        check=True,
    )
    subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--replace-old"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    restarted = wait_health(old_pid)

    connection = sqlite3.connect(DATABASE)
    try:
        chat_total = int(connection.execute("SELECT COUNT(*) FROM chat_messages").fetchone()[0])
        chat_test = int(connection.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE lower(username) LIKE 'codexload%'"
        ).fetchone()[0])
        read_test = int(connection.execute(
            "SELECT COUNT(*) FROM chat_read_state WHERE lower(username) LIKE 'codexload%'"
        ).fetchone()[0])
        auth_test = int(connection.execute(
            "SELECT COUNT(*) FROM auth_sessions WHERE lower(username) LIKE 'codexload%'"
        ).fetchone()[0]) if connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='auth_sessions'").fetchone() else 0
        session_doc = connection.execute(
            "SELECT content FROM documents WHERE lower(path) LIKE '%_future_auth_sessions.json' LIMIT 1"
        ).fetchone()
        session_text = bytes(session_doc[0]).decode("utf-8") if session_doc else ""
        legacy_chat = int(connection.execute(
            "SELECT COUNT(*) FROM documents WHERE lower(path) LIKE '%_future_chat_messages.json'"
        ).fetchone()[0])
        quick_check = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0])
        synchronous = int(connection.execute("PRAGMA synchronous").fetchone()[0])
    finally:
        connection.close()
    if chat_test or read_test or auth_test or "codexload" in session_text.lower():
        raise RuntimeError("Load-test chat/session state remains after cleanup")
    if chat_total != 87 or legacy_chat != 0 or quick_check.lower() != "ok":
        raise RuntimeError("Production chat/database invariant changed during cleanup")
    print(json.dumps({
        "chat_cleanup": "ok",
        "old_pid": old_pid,
        "new_pid": int(restarted.get("pid", 0) or 0),
        "production_chat_rows": chat_total,
        "test_chat_rows": chat_test,
        "test_read_rows": read_test,
        "test_auth_sessions": auth_test,
        "test_sessions": 0,
        "legacy_chat_document": legacy_chat,
        "quick_check": quick_check,
        "journal_mode": journal_mode,
        "synchronous": synchronous,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
