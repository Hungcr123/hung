"""HTTP retry regression for durable Space_Q operation IDs."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import requests


BASE = "http://127.0.0.1:8877"
DATABASE = Path(r"C:\server data\server2.db")
USERNAME = "codexload001"
LEGACY_WAL = Path(r"C:\QMLearn\users\codexload001\_future_space_q_progress.json.wal.jsonl")


def database_row() -> tuple[int, dict]:
    connection = sqlite3.connect(DATABASE)
    try:
        row = connection.execute(
            "SELECT server_revision,record_json FROM lesson_progress "
            "WHERE username=? AND space='Space_Q' ORDER BY updated_at_utc DESC LIMIT 1",
            (USERNAME,),
        ).fetchone()
    finally:
        connection.close()
    if not row:
        raise RuntimeError("Run benchmark_space_q_progress_post_hot_path.py first")
    return int(row[0] or 0), json.loads(row[1])


# Added 2026-07-21: an ACK-lost Space_Q retry stays a zero-write compact ACK.
def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this test only")
    login = requests.post(f"{BASE}/auth/login", json={"username": USERNAME, "password": password}, timeout=30)
    login.raise_for_status()
    token = str(login.json().get("token") or "").strip()
    revision_before, record = database_row()
    operation_id = str(record.get("syncOperationId") or record.get("sync_operation_id") or "").strip()
    if not operation_id:
        raise RuntimeError("The seeded Space_Q row has no durable operation ID")
    writer_before = requests.get(f"{BASE}/health", timeout=15).json().get("sqlite_writer", {})
    legacy_before = LEGACY_WAL.stat().st_size if LEGACY_WAL.exists() else 0
    response = requests.post(
        f"{BASE}/space-q/progress?client_source=codex_retry_http&response=compact-v1",
        headers={"Authorization": f"Bearer {token}"},
        json={**record, "action": "autosave"},
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    writer_after = requests.get(f"{BASE}/health", timeout=15).json().get("sqlite_writer", {})
    revision_after, stored = database_row()
    legacy_after = LEGACY_WAL.stat().st_size if LEGACY_WAL.exists() else 0
    if payload.get("response_schema") != "space-q-progress-compact-v1":
        raise RuntimeError("Duplicate Space_Q retry did not receive compact ACK")
    if revision_after != revision_before:
        raise RuntimeError("Duplicate Space_Q retry increased the durable revision")
    if int(writer_after.get("tasks", 0) or 0) != int(writer_before.get("tasks", 0) or 0):
        raise RuntimeError("Duplicate Space_Q retry created a SQLite writer task")
    if legacy_after != legacy_before:
        raise RuntimeError("Duplicate Space_Q retry wrote the retired JSONL WAL")
    if str(stored.get("syncOperationId") or "") != operation_id:
        raise RuntimeError("Stored Space_Q operation ID changed during retry")
    print(f"space_q_progress_post_http=ok revision={revision_after} writer_tasks=0 legacy_wal_growth=0 compact_bytes={len(response.content)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
