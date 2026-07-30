"""Live API regression for V/W/Q/L/S folder-group removal using codexload098."""

from __future__ import annotations

import collections
import json
import os
from pathlib import Path

import requests


BASE = "http://127.0.0.1:8877"
USERNAME = "codexload098"
SERVER_DATA = Path(r"C:\server data")
MANIFEST = SERVER_DATA / "_future_server_data_manifest.json"
SPACES = {
    "Space_V": ".space_v",
    "Space_W": ".space_w",
    "Space_Q": ".space_q",
    "Space_L": ".space_l",
    "Space_S": ".space_s",
}


def login(password: str) -> str:
    response = requests.post(f"{BASE}/auth/login", json={"username": USERNAME, "password": password}, timeout=30)
    response.raise_for_status()
    return response.json()["token"]


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def task_paths() -> dict[str, tuple[list[str], str]]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    all_paths = []
    seen = set()
    for entries in (payload.get("folders") or {}).values():
        for entry in entries if isinstance(entries, list) else []:
            path = str(entry.get("path", "")).replace("\\", "/") if isinstance(entry, dict) else ""
            key = path.lower()
            if path and key not in seen:
                seen.add(key)
                all_paths.append(path)
    selected = {}
    for space, suffix in SPACES.items():
        by_folder = collections.defaultdict(list)
        for path in all_paths:
            if path.lower().endswith(suffix):
                by_folder[path.rsplit("/", 1)[0] if "/" in path else ""].append(path)
        folder_a, rows_a = max(by_folder.items(), key=lambda item: len(item[1]))
        if len(rows_a) < 3:
            raise RuntimeError(f"Need 3 {space} files in one folder")
        other = next(path for folder, rows in by_folder.items() if folder != folder_a for path in rows)
        selected[space] = (sorted(rows_a)[:3], other)
    return selected


def get_tasks(token: str) -> list[dict]:
    response = requests.get(f"{BASE}/lesson-tasks?user={USERNAME}", headers=headers(token), timeout=60)
    response.raise_for_status()
    return response.json().get("tasks", [])


def remove_task(token: str, task: dict) -> dict:
    response = requests.post(
        f"{BASE}/lesson-tasks",
        headers=headers(token),
        json={
            "action": "remove",
            "user": USERNAME,
            "id": task.get("id", ""),
            "path": task.get("path", ""),
            "folder_group_key": task.get("folder_group_key", ""),
            "folder_path": task.get("folder_path", ""),
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this active test only")
    selected = task_paths()
    results = {}
    token = login(password)
    try:
        if get_tasks(token):
            raise RuntimeError(f"{USERNAME} must start with an empty task row")
        for space, (group_paths, other_path) in selected.items():
            source_paths = [*group_paths, other_path]
            signatures = {
                path: (SERVER_DATA / Path(path)).stat().st_size
                for path in source_paths
            }
            for path in source_paths:
                response = requests.post(
                    f"{BASE}/lesson-tasks",
                    headers=headers(token),
                    json={"action": "add", "user": USERNAME, "path": path},
                    timeout=60,
                )
                response.raise_for_status()
            tasks = get_tasks(token)
            target = next(task for task in tasks if task.get("path") == group_paths[0])
            group_key = target.get("folder_group_key", "")
            assert group_key and sum(task.get("folder_group_key") == group_key for task in tasks) == 3
            removed = remove_task(token, target)
            assert removed.get("removed_count") == 3
            token = login(password)
            remaining = get_tasks(token)
            assert len(remaining) == 1 and remaining[0].get("path") == other_path
            assert all((SERVER_DATA / Path(path)).is_file() and (SERVER_DATA / Path(path)).stat().st_size == signatures[path] for path in source_paths)
            remove_task(token, remaining[0])
            assert get_tasks(token) == []
            results[space] = {"removed": 3, "other_preserved": 1, "files_preserved": 4}
    finally:
        try:
            token = login(password)
            for task in list(get_tasks(token)):
                remove_task(token, task)
        except Exception:
            pass
    print("space_task_folder_group_live=ok " + json.dumps(results, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
