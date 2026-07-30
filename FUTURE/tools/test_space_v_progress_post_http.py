"""HTTP retry regression for durable Space_V operation IDs."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


BASE = "http://127.0.0.1:8877"
DATABASE = Path(r"C:\server data\server2.db")
USERNAME = "codexload001"
LEGACY_WAL = Path(r"C:\QMLearn\users\codexload001\_future_space_v_progress.json.wal.jsonl")


def database_row() -> tuple[int, dict]:
    connection = sqlite3.connect(DATABASE)
    try:
        row = connection.execute(
            "SELECT server_revision,record_json FROM lesson_progress "
            "WHERE username=? AND space='Space_V' ORDER BY updated_at_utc DESC LIMIT 1",
            (USERNAME,),
        ).fetchone()
    finally:
        connection.close()
    if not row:
        raise RuntimeError("Run benchmark_space_v_progress_post_hot_path.py first")
    return int(row[0] or 0), json.loads(row[1])


# Added 2026-07-21: an ACK-lost Space_V retry remains a zero-write compact ACK.
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
        raise RuntimeError("The seeded Space_V row has no durable operation ID")
    writer_before = requests.get(f"{BASE}/health", timeout=15).json().get("postgres_writer", {})
    legacy_before = LEGACY_WAL.stat().st_size if LEGACY_WAL.exists() else 0
    response = requests.post(
        f"{BASE}/space-v/progress?client_source=codex_retry_http&response=compact-v1",
        headers={"Authorization": f"Bearer {token}"},
        json={**record, "action": "autosave"},
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    writer_after = requests.get(f"{BASE}/health", timeout=15).json().get("postgres_writer", {})
    revision_after, stored = database_row()
    legacy_after = LEGACY_WAL.stat().st_size if LEGACY_WAL.exists() else 0
    if payload.get("response_schema") != "space-v-progress-compact-v1":
        raise RuntimeError("Duplicate Space_V retry did not receive compact ACK")
    if revision_after != revision_before:
        raise RuntimeError("Duplicate Space_V retry increased durable revision")
    if int(writer_after.get("tasks", 0) or 0) != int(writer_before.get("tasks", 0) or 0):
        raise RuntimeError("Duplicate Space_V retry created a SQLite writer task")
    if legacy_after != legacy_before:
        raise RuntimeError("Duplicate Space_V retry wrote retired JSONL WAL")
    if str(stored.get("syncOperationId") or "") != operation_id:
        raise RuntimeError("Stored Space_V operation ID changed during retry")
    fresh_open = json.loads(json.dumps(record))
    fresh_stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    fresh_open.update({
        "savedAt": fresh_stamp,
        "updatedAt": fresh_stamp,
        "syncOperationId": f"space-v-fresh-open-{time.time_ns()}",
        "action": "autosave",
    })
    fresh_state = fresh_open.get("state") if isinstance(fresh_open.get("state"), dict) else {}
    fresh_state.update({
        "savedAt": fresh_stamp,
        "syncOperationId": fresh_open["syncOperationId"],
        "effective_path": "",
        "lessonSource": {"study": {"users": 2}},
    })
    fresh_open["state"] = fresh_state
    fresh_writer_before = requests.get(f"{BASE}/health", timeout=15).json().get("postgres_writer", {})
    fresh_response = requests.post(
        f"{BASE}/space-v/progress?client_source=codex_fresh_open_http&response=compact-v1",
        headers={"Authorization": f"Bearer {token}"},
        json=fresh_open,
        timeout=45,
    )
    fresh_response.raise_for_status()
    fresh_writer_after = requests.get(f"{BASE}/health", timeout=15).json().get("postgres_writer", {})
    fresh_revision, fresh_stored = database_row()
    if fresh_revision != revision_after:
        raise RuntimeError("Fresh Space_V open increased durable revision")
    if int(fresh_writer_after.get("tasks", 0) or 0) != int(fresh_writer_before.get("tasks", 0) or 0):
        raise RuntimeError("Fresh Space_V open created a SQLite writer task")
    if fresh_stored != stored:
        raise RuntimeError("Fresh Space_V open replaced server-enriched progress context")
    print(f"space_v_progress_post_http=ok revision={revision_after} retry_writes=0 fresh_open_writes=0 legacy_wal_growth=0 compact_bytes={len(response.content)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

