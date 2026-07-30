"""Isolate 100-user Space Task folder, unique-add, and retry mutation costs."""

from __future__ import annotations

import concurrent.futures
import json
import os
import sqlite3
import threading
import time

import requests

import benchmark_space_task_click_100_users as common


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active benchmark only")
    lessons = common.distributed_lessons()
    proc = common.server_process()

    def login(username: str) -> tuple[str, requests.Session]:
        session = requests.Session()
        response = session.post(
            f"{common.BASE}/auth/login",
            json={"username": username, "password": password},
            timeout=60,
        )
        response.raise_for_status()
        session.headers.update({"Authorization": f"Bearer {response.json()['token']}"})
        return username, session

    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        sessions = dict(pool.map(login, common.USERS))

    def request(username: str, body: dict | None = None) -> dict:
        started = time.perf_counter()
        if body is None:
            response = sessions[username].get(
                f"{common.BASE}/lesson-tasks",
                params={"user": username},
                timeout=90,
            )
        else:
            response = sessions[username].post(
                f"{common.BASE}/lesson-tasks",
                json=body,
                timeout=90,
            )
        payload = response.json() if response.content else {}
        raw = json.dumps(body, ensure_ascii=True, separators=(",", ":")).encode("utf-8") if body else b""
        return {
            "route": "/lesson-tasks",
            "status": response.status_code,
            "latency_ms": (time.perf_counter() - started) * 1000,
            "request_bytes": len(raw),
            "response_bytes": len(response.content),
            "payload": payload,
        }

    def request_status(username: str) -> dict:
        started = time.perf_counter()
        response = sessions[username].get(
            f"{common.BASE}/lesson-tasks/status",
            params={"user": username},
            timeout=30,
        )
        payload = response.json() if response.content else {}
        return {
            "route": "/lesson-tasks/status",
            "status": response.status_code,
            "latency_ms": (time.perf_counter() - started) * 1000,
            "request_bytes": 0,
            "response_bytes": len(response.content),
            "payload": payload,
        }

    def run_all_users(worker) -> list[dict]:
        barrier = threading.Barrier(len(common.USERS))

        def synchronized(username: str) -> list[dict]:
            barrier.wait(timeout=30)
            return worker(username)

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(common.USERS)) as pool:
            return [row for rows in pool.map(synchronized, common.USERS) for row in rows]

    progress_before = common.progress_fingerprint()

    def save_folders(username: str) -> list[dict]:
        paths = lessons[username]
        return [request(username, {
            "action": "space-folders",
            "user": username,
            "folders": [path.rsplit("/", 1)[0] for path in paths],
            "baseRevision": "",
        })]

    folder_rows, folder_metrics = common.measured(proc, lambda: run_all_users(save_folders))
    folder_pending = sum(bool((row.get("payload", {}).get("space_task") or {}).get("pending")) for row in folder_rows)
    folder_task_counts = [len((row.get("payload", {}).get("space_task") or {}).get("tasks") or []) for row in folder_rows]

    settle_rows = []
    settle_metrics = {"requests": 0, "server_cpu_ms": 0, "errors": 0}
    if folder_pending:
        def wait_for_folder_build(username: str) -> list[dict]:
            rows = []
            time.sleep(0.9)
            for attempt in range(24):
                status_row = request_status(username)
                rows.append(status_row)
                if bool((status_row.get("payload") or {}).get("ready")):
                    rows.append(request(username))
                    return rows
                time.sleep(min(5.0, max(1.2, 0.9 * (1.35 ** max(1, attempt + 1)))))
            return rows

        settle_rows, settle_metrics = common.measured(proc, lambda: run_all_users(wait_for_folder_build))
        final_by_user = {}
        for row in settle_rows:
            owner = str((row.get("payload") or {}).get("task_owner", ""))
            if owner:
                final_by_user[owner] = row
        if len(final_by_user) != len(common.USERS) or any(
            bool(((row.get("payload") or {}).get("space_task") or {}).get("pending"))
            for row in final_by_user.values()
        ):
            raise RuntimeError("One or more Space Task folder payloads did not settle")

    folder_retry_rows, folder_retry_metrics = common.measured(proc, lambda: run_all_users(save_folders))

    def add_cards(username: str) -> list[dict]:
        return [request(username, {
            "action": "add",
            "user": username,
            "path": path,
            "severity": "normal",
        }) for path in lessons[username]]

    unique_rows, unique_metrics = common.measured(proc, lambda: run_all_users(add_cards))
    retry_rows, retry_metrics = common.measured(proc, lambda: run_all_users(add_cards))

    def read_tasks(username: str) -> list[dict]:
        return [request(username)]

    read_rows, read_metrics = common.measured(proc, lambda: run_all_users(read_tasks))
    progress_after = common.progress_fingerprint()
    if progress_after != progress_before:
        raise RuntimeError("Space Task mutations changed learning progress")
    measured_rows = folder_rows + settle_rows + folder_retry_rows + unique_rows + retry_rows + read_rows
    if any(row["status"] != 200 for row in measured_rows):
        raise RuntimeError("One or more Space Task mutation requests failed")

    task_counts = []
    preferred_counts = []
    pending_counts = []
    for row in read_rows:
        payload = row.get("payload") or {}
        space_task = payload.get("space_task") if isinstance(payload.get("space_task"), dict) else {}
        task_counts.append(len(payload.get("tasks") or []))
        preferred_counts.append(len(space_task.get("preferred_folders") or []))
        pending_counts.append(bool(space_task.get("pending")))
    placeholders = ",".join("?" for _ in common.USERS)
    with sqlite3.connect(common.DATABASE) as connection:
        storage = connection.execute(
            f"SELECT COUNT(*),COALESCE(SUM(length(record_json)),0),COALESCE(SUM(server_revision),0) "
            f"FROM lesson_task_state WHERE username IN ({placeholders})",
            common.USERS,
        ).fetchone()

    print(json.dumps({
        "users": len(common.USERS),
        "folders_per_user": 3,
        "cards_per_user": 3,
        "space_folders": {
            **folder_metrics,
            "pending_responses": folder_pending,
            "response_task_count_min_max": [min(folder_task_counts), max(folder_task_counts)],
        },
        "folder_settle": settle_metrics,
        "folder_total_cpu_ms": round(float(folder_metrics.get("server_cpu_ms", 0)) + float(settle_metrics.get("server_cpu_ms", 0)), 3),
        "folder_exact_retry": folder_retry_metrics,
        "unique_add": unique_metrics,
        "exact_retry": retry_metrics,
        "settled_read": {
            **read_metrics,
            "explicit_task_count_min_max": [min(task_counts), max(task_counts)],
            "preferred_folder_count_min_max": [min(preferred_counts), max(preferred_counts)],
            "pending_responses": sum(pending_counts),
        },
        "storage_rows_bytes_revision": storage,
        "progress_unchanged": True,
        "cleanup_required": True,
    }, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
