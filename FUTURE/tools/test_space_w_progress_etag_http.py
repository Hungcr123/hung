"""HTTP stale-device regression for Space_W progress ETags."""

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


# Added 2026-07-20: prove an old ETag cannot hide a newer durable Space_W checkpoint.
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
            "SELECT path,identity,record_json FROM lesson_progress WHERE username=? AND space='Space_W' ORDER BY updated_at_utc DESC LIMIT 1",
            (USERNAME,),
        ).fetchone()
    finally:
        connection.close()
    if not row:
        raise RuntimeError("Run benchmark_space_w_progress_get_hot_path.py first")
    path, identity, record_json = row
    params = {"path": path, "identity": identity}

    first = requests.get(f"{BASE}/space-w/progress", headers=headers, params=params, timeout=30)
    first.raise_for_status()
    etag_a = str(first.headers.get("ETag") or "").strip()
    if not etag_a or not isinstance(first.json().get("progress"), dict):
        raise RuntimeError("Initial Space_W payload/ETag missing")
    unchanged = requests.get(
        f"{BASE}/space-w/progress",
        headers={**headers, "If-None-Match": etag_a},
        params=params,
        timeout=30,
    )
    if unchanged.status_code != 304 or unchanged.content:
        raise RuntimeError(f"Unchanged ETag did not return empty 304: {unchanged.status_code}")

    record = copy.deepcopy(json.loads(record_json))
    state = record.get("state") if isinstance(record.get("state"), dict) else {}
    previous_done = int(state.get("progressDone") or record.get("progressDone") or 0)
    total = max(previous_done + 2, int(state.get("progressTotal") or record.get("progressTotal") or 2))
    changed_done = (previous_done + 1) % total
    changed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    state.update({
        "savedAt": changed_at,
        "updatedAt": changed_at,
        "progressDone": changed_done,
        "progressTotal": total,
        "trainEnabled": not bool(state.get("trainEnabled")),
    })
    record.update({
        "action": "autosave",
        "path": path,
        "identity": identity,
        "savedAt": changed_at,
        "updatedAt": changed_at,
        "progressDone": changed_done,
        "progressTotal": total,
        "state": state,
    })
    posted = requests.post(
        f"{BASE}/space-w/progress?client_source=codex_etag_stale_device",
        headers=headers,
        json=record,
        timeout=45,
    )
    posted.raise_for_status()

    stale = requests.get(
        f"{BASE}/space-w/progress",
        headers={**headers, "If-None-Match": etag_a},
        params=params,
        timeout=30,
    )
    stale.raise_for_status()
    etag_b = str(stale.headers.get("ETag") or "").strip()
    payload_b = stale.json()
    if stale.status_code != 200 or not etag_b or etag_b == etag_a:
        raise RuntimeError("Old Space_W ETag hid the newer checkpoint")
    progress_b = payload_b.get("progress") if isinstance(payload_b.get("progress"), dict) else {}
    state_b = progress_b.get("state") if isinstance(progress_b.get("state"), dict) else {}
    if int(state_b.get("progressDone") or progress_b.get("progressDone") or -1) != changed_done:
        raise RuntimeError("New Space_W checkpoint was not returned")
    latest = requests.get(
        f"{BASE}/space-w/progress",
        headers={**headers, "If-None-Match": etag_b},
        params=params,
        timeout=30,
    )
    if latest.status_code != 304 or latest.content:
        raise RuntimeError("Latest Space_W ETag did not return empty 304")
    print(f"space_w_progress_etag_http=ok old_etag_200=true latest_etag_304=true progress_done={changed_done}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
