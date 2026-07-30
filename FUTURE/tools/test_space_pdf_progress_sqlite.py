"""Verify Space_PDF progress uses SQLite rows, semantic retries, and clear tombstones."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

import requests


BASE = "http://127.0.0.1:8877"
DATABASE = Path(r"C:\server data\server2.db")
USER = "codexload001"


def first_pdf() -> str:
    manifest = json.loads(Path(r"C:\server data\_future_server_data_manifest.json").read_text(encoding="utf-8"))
    for entries in (manifest.get("folders") or {}).values():
        for entry in entries if isinstance(entries, list) else []:
            path = str(entry.get("path", "")).strip() if isinstance(entry, dict) else ""
            if path.lower().startswith("common/") and path.lower().endswith(".pdf"):
                return path
    raise RuntimeError("No common PDF found")


def progress_row() -> tuple[int, dict]:
    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            "SELECT server_revision,record_json FROM lesson_progress "
            "WHERE username=? AND space='Space_PDF' ORDER BY server_revision DESC LIMIT 1",
            (USER,),
        ).fetchone()
    if not row:
        raise AssertionError("Space_PDF row was not written to SQLite")
    return int(row[0]), json.loads(row[1])


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active test only")
    session = requests.Session()
    login = session.post(f"{BASE}/auth/login", json={"username": USER, "password": password}, timeout=30)
    login.raise_for_status()
    token = login.json()["token"]
    session.headers.update({"Authorization": f"Bearer {token}"})
    path = first_pdf()
    base = {
        "path": path,
        "identity": "sqlite-progress-regression",
        "title": "SQLite progress regression",
        "page": 2,
        "pages": 12,
        "pinnedPages": [2],
        "pinnedPagesUpdatedAt": "2026-07-20T14:30:00Z",
        "recentPages": [2],
        "savedAt": "2026-07-20T14:30:00Z",
        "state": {"page": 2, "pages": 12, "pinnedPages": [2], "pinnedPagesUpdatedAt": "2026-07-20T14:30:00Z"},
    }
    if "--verify-restart" in sys.argv:
        before_revision, before_record = progress_row()
        assert before_record.get("_deleted") is True, before_record
        stale = {**base, "savedAt": "2026-07-20T14:30:30Z", "state": {**base["state"], "savedAt": "2026-07-20T14:30:30Z"}}
        session.post(f"{BASE}/space-pdf/progress?client_source=sqlite_progress_restart_stale", json=stale, timeout=30).raise_for_status()
        after_revision, after_record = progress_row()
        assert after_revision == before_revision and after_record.get("_deleted") is True, (before_revision, after_revision, after_record)
        print(json.dumps({"restart_revision": after_revision, "tombstone_retained": True, "post_restart_stale_rejected": True}, ensure_ascii=True))
        return 0
    first = session.post(f"{BASE}/space-pdf/progress?client_source=sqlite_progress_test", json=base, timeout=30)
    first.raise_for_status()
    revision, record = progress_row()
    assert revision >= 1 and not record.get("_deleted"), (revision, record)
    retry = {**base, "savedAt": "2026-07-20T14:30:01Z", "state": {**base["state"], "savedAt": "2026-07-20T14:30:01Z"}}
    session.post(f"{BASE}/space-pdf/progress?client_source=sqlite_progress_test_retry", json=retry, timeout=30).raise_for_status()
    retry_revision, _ = progress_row()
    assert retry_revision == revision, (revision, retry_revision)
    clear = {"path": path, "identity": base["identity"], "savedAt": "2026-07-20T14:31:00Z", "action": "clear"}
    session.post(f"{BASE}/space-pdf/progress?client_source=sqlite_progress_test_clear", json=clear, timeout=30).raise_for_status()
    clear_revision, clear_record = progress_row()
    assert clear_revision > revision and clear_record.get("_deleted") is True, (clear_revision, clear_record)
    stale = {**base, "savedAt": "2026-07-20T14:30:30Z", "state": {**base["state"], "savedAt": "2026-07-20T14:30:30Z"}}
    session.post(f"{BASE}/space-pdf/progress?client_source=sqlite_progress_test_stale", json=stale, timeout=30).raise_for_status()
    stale_revision, stale_record = progress_row()
    assert stale_revision == clear_revision and stale_record.get("_deleted") is True, (clear_revision, stale_revision, stale_record)
    query = requests.Request("GET", f"{BASE}/space-pdf/progress", params={"path": path, "identity": base["identity"]}).prepare().url
    remote = session.get(query, timeout=30).json()
    assert remote.get("progress") in (None, {}), remote
    print(json.dumps({"path": path, "revision": clear_revision, "sqlite_tombstone": True, "stale_rejected": True, "read_hidden": True}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
