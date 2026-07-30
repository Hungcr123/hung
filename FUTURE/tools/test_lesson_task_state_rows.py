"""Exercise row isolation, idempotency, and concurrent Lesson Task mutations."""

from __future__ import annotations

import concurrent.futures
import json
import os
import sqlite3
from pathlib import Path

import requests


BASE = "http://127.0.0.1:8877"
DATABASE = Path(r"C:\server data\server2.db")
MANIFEST = Path(r"C:\server data\_future_server_data_manifest.json")
USERS = ("codexload001", "codexload002")


def lesson_paths(limit: int = 24) -> list[str]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    paths = []
    for entries in (payload.get("folders") or {}).values():
        for entry in entries if isinstance(entries, list) else []:
            path = str(entry.get("path", "")).strip() if isinstance(entry, dict) else ""
            if path.lower().startswith("common/") and path.lower().endswith((".space_v", ".space_w", ".space_q", ".space_p", ".space_l", ".space_s")):
                paths.append(path)
                if len(paths) >= limit:
                    return paths
    raise RuntimeError(f"Need {limit} lesson paths; found {len(paths)}")


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this active test only")
    paths = lesson_paths()
    tokens = {}
    for username in USERS:
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        tokens[username] = response.json()["token"]

    def add(username: str, path: str) -> int:
        response = requests.post(
            f"{BASE}/lesson-tasks",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            json={"action": "add", "user": username, "path": path},
            timeout=60,
        )
        return response.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        duplicate_statuses = list(pool.map(lambda _index: add(USERS[0], paths[0]), range(20)))
    assert duplicate_statuses == [200] * 20

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        statuses = list(pool.map(lambda index: add(USERS[index % 2], paths[index + 1]), range(20)))
    assert statuses == [200] * 20

    with sqlite3.connect(DATABASE) as connection:
        rows = connection.execute(
            "SELECT username,record_json,server_revision FROM lesson_task_state WHERE username IN (?,?) ORDER BY username",
            USERS,
        ).fetchall()
    assert len(rows) == 2
    decoded = {row[0]: (json.loads(row[1]), int(row[2])) for row in rows}
    tasks_a, revision_a = decoded[USERS[0]]
    tasks_b, revision_b = decoded[USERS[1]]
    paths_a = {str(item.get("path", "")).lower() for item in tasks_a.get("tasks", [])}
    paths_b = {str(item.get("path", "")).lower() for item in tasks_b.get("tasks", [])}
    assert len(paths_a) == 11 and revision_a == 11
    assert len(paths_b) == 10 and revision_b == 10
    assert paths_a.isdisjoint(paths_b)
    print("lesson_task_state_rows=ok duplicate_noop=true same_user_serial=true independent_users=true revisions=11,10")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
