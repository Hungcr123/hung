"""HTTP stale-device regression for Space_Q progress ETags."""

from __future__ import annotations

import copy
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import requests


BASE = "http://127.0.0.1:8877"
DATABASE = Path(r"C:\server data\server2.db")
USERNAME = "codexload001"


# Added 2026-07-21: prove an old Space_Q ETag cannot hide a newer durable checkpoint.
def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this test only")
    login = requests.post(f"{BASE}/auth/login", json={"username": USERNAME, "password": password}, timeout=30)
    login.raise_for_status()
    token = str(login.json().get("token") or "").strip()
    headers = {"Authorization": f"Bearer {token}"}
    connection = sqlite3.connect(DATABASE)
    try:
        row = connection.execute(
            "SELECT path,identity,record_json FROM lesson_progress WHERE username=? AND space='Space_Q' ORDER BY updated_at_utc DESC LIMIT 1",
            (USERNAME,),
        ).fetchone()
    finally:
        connection.close()
    if not row:
        raise RuntimeError("Run benchmark_space_q_progress_get_hot_path.py first")
    path, identity, record_json = row
    params = {"path": path, "identity": identity}

    first = requests.get(f"{BASE}/space-q/progress", headers=headers, params=params, timeout=30)
    first.raise_for_status()
    etag_a = str(first.headers.get("ETag") or "").strip()
    unchanged = requests.get(f"{BASE}/space-q/progress", headers={**headers, "If-None-Match": etag_a}, params=params, timeout=30)
    if unchanged.status_code != 304 or unchanged.content:
        raise RuntimeError("Unchanged Space_Q checkpoint did not return empty 304")

    record = copy.deepcopy(json.loads(record_json))
    state = record.get("state") if isinstance(record.get("state"), dict) else {}
    changed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    previous_done = int(state.get("questionDone") or state.get("completedQuestions") or 0)
    total = max(previous_done + 2, int(state.get("questionTotal") or state.get("totalQuestions") or 2))
    changed_done = (previous_done + 1) % total
    state.update({"savedAt": changed_at, "updatedAt": changed_at, "questionDone": changed_done, "questionTotal": total})
    record.update({"action": "autosave", "path": path, "identity": identity, "savedAt": changed_at, "updatedAt": changed_at, "state": state})
    posted = requests.post(
        f"{BASE}/space-q/progress?client_source=codex_etag_stale_device",
        headers=headers,
        json=record,
        timeout=45,
    )
    posted.raise_for_status()

    stale = requests.get(f"{BASE}/space-q/progress", headers={**headers, "If-None-Match": etag_a}, params=params, timeout=30)
    stale.raise_for_status()
    etag_b = str(stale.headers.get("ETag") or "").strip()
    progress_b = stale.json().get("progress") or {}
    state_b = progress_b.get("state") if isinstance(progress_b.get("state"), dict) else {}
    if stale.status_code != 200 or not etag_b or etag_b == etag_a:
        raise RuntimeError("Old Space_Q ETag hid the newer checkpoint")
    if int(state_b.get("questionDone") or -1) != changed_done:
        raise RuntimeError("New Space_Q checkpoint was not returned")
    latest = requests.get(f"{BASE}/space-q/progress", headers={**headers, "If-None-Match": etag_b}, params=params, timeout=30)
    if latest.status_code != 304 or latest.content:
        raise RuntimeError("Latest Space_Q ETag did not return empty 304")
    print(f"space_q_progress_etag_http=ok old_etag_200=true latest_etag_304=true question_done={changed_done}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
