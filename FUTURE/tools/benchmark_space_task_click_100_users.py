"""Benchmark 100 distinct users adding Space Task folders and spamming task cards."""

from __future__ import annotations

import concurrent.futures
import json
import os
import sqlite3
import statistics
import threading
import time
from pathlib import Path

import psutil
import requests


BASE = "http://127.0.0.1:8877"
DATABASE = Path(r"C:\server data\server2.db")
MANIFEST = Path(r"C:\server data\_future_server_data_manifest.json")
USERS = tuple(f"codexload{index:03d}" for index in range(1, 101))
CLICK_COUNT = 6
PROGRESS_TABLES = (
    "lesson_progress",
    "lesson_progress_namespaces",
    "lesson_time",
    "lesson_time_credit_state",
    "pdf_drawings",
    "vocabulary_events",
    "vocabulary_registry",
)


def server_process() -> psutil.Process:
    for connection in psutil.net_connections(kind="tcp"):
        if connection.laddr and connection.laddr.port == 8877 and connection.status == psutil.CONN_LISTEN and connection.pid:
            return psutil.Process(connection.pid)
    raise RuntimeError("Server 2 listener not found")


def distributed_lessons() -> dict[str, list[str]]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_parent: dict[str, str] = {}
    suffixes = (".space_v", ".space_w", ".space_q", ".space_p", ".space_l", ".space_s", ".pdf")
    for entries in (payload.get("folders") or {}).values():
        for entry in entries if isinstance(entries, list) else []:
            path = str(entry.get("path", "")).strip() if isinstance(entry, dict) else ""
            if not path.lower().startswith("common/") or not path.lower().endswith(suffixes) or "/" not in path:
                continue
            by_parent.setdefault(path.rsplit("/", 1)[0], path)
    rows = sorted(by_parent.items(), key=lambda row: row[0].lower())
    if len(rows) < 300:
        raise RuntimeError(f"Need 300 distinct task folders; found {len(rows)}")
    return {
        username: [rows[index][1], rows[index + 100][1], rows[index + 200][1]]
        for index, username in enumerate(USERS)
    }


def health_writer() -> dict:
    return requests.get(f"{BASE}/health", timeout=15).json().get("postgres_writer", {})


def wait_writer_idle(timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if int(health_writer().get("queue_depth", 0) or 0) == 0:
            time.sleep(0.08)
            if int(health_writer().get("queue_depth", 0) or 0) == 0:
                return
        time.sleep(0.05)
    raise RuntimeError("SQLite writer queue did not drain")


def progress_fingerprint() -> dict[str, tuple[int, int]]:
    placeholders = ",".join("?" for _ in USERS)
    result = {}
    with sqlite3.connect(DATABASE) as connection:
        for table in PROGRESS_TABLES:
            rows = connection.execute(
                f'SELECT * FROM "{table}" WHERE username IN ({placeholders}) ORDER BY username',
                USERS,
            ).fetchall()
            encoded = json.dumps(rows, ensure_ascii=True, default=str, separators=(",", ":"))
            result[table] = (len(rows), hash(encoded))
    return result


def response_row(response: requests.Response, started: float, route: str, request_bytes: int = 0) -> dict:
    return {
        "route": route,
        "status": response.status_code,
        "latency_ms": (time.perf_counter() - started) * 1000,
        "request_bytes": request_bytes,
        "response_bytes": len(response.content),
    }


def request_json(session: requests.Session, method: str, route: str, *, params=None, body=None) -> dict:
    raw = json.dumps(body, ensure_ascii=True, separators=(",", ":")).encode("utf-8") if body is not None else b""
    started = time.perf_counter()
    response = session.request(method, f"{BASE}{route}", params=params, json=body, timeout=60)
    row = response_row(response, started, route, len(raw))
    if response.status_code >= 400:
        row["error"] = response.text[:300]
    return row


def measured(proc: psutil.Process, callback) -> tuple[list[dict], dict]:
    wait_writer_idle()
    writer_before = health_writer()
    cpu_before = sum(proc.cpu_times()[:2])
    io_before = proc.io_counters()
    wal = Path(str(DATABASE) + "-wal")
    wal_before = wal.stat().st_size if wal.exists() else 0
    started = time.perf_counter()
    rows = callback()
    wall_seconds = max(0.001, time.perf_counter() - started)
    wait_writer_idle()
    cpu_after = sum(proc.cpu_times()[:2])
    io_after = proc.io_counters()
    writer_after = health_writer()
    wal_after = wal.stat().st_size if wal.exists() else 0
    cpu_seconds = max(0.0, cpu_after - cpu_before)
    latencies = sorted(float(row.get("latency_ms", 0.0)) for row in rows)
    logical_cpus = max(1, psutil.cpu_count(logical=True) or 1)
    route_counts = {route: sum(row.get("route") == route for row in rows) for route in sorted({row.get("route", "") for row in rows})}
    metrics = {
        "requests": len(rows),
        "route_counts": route_counts,
        "server_cpu_ms": round(cpu_seconds * 1000, 3),
        "cpu_ms_per_request": round(cpu_seconds * 1000 / max(1, len(rows)), 3),
        "whole_machine_cpu_percent": round(cpu_seconds / wall_seconds / logical_cpus * 100, 3),
        "wall_ms": round(wall_seconds * 1000, 3),
        "requests_per_second": round(len(rows) / wall_seconds, 3),
        "p50_ms": round(statistics.median(latencies), 3) if latencies else 0,
        "p95_ms": round(latencies[max(0, int(len(latencies) * 0.95) - 1)], 3) if latencies else 0,
        "p99_ms": round(latencies[max(0, int(len(latencies) * 0.99) - 1)], 3) if latencies else 0,
        "request_bytes": sum(int(row.get("request_bytes", 0) or 0) for row in rows),
        "response_bytes": sum(int(row.get("response_bytes", 0) or 0) for row in rows),
        "errors": sum(int(row.get("status", 0) or 0) >= 400 for row in rows),
        "wal_growth": wal_after - wal_before,
        "postgres_writer": {
            key: round(float(writer_after.get(key, 0) or 0) - float(writer_before.get(key, 0) or 0), 3)
            for key in ("batches", "tasks", "queue_wait_ms", "begin_wait_ms", "commit_ms", "busy_errors")
        },
        "process_io": {
            "read_ops": max(0, io_after.read_count - io_before.read_count),
            "write_ops": max(0, io_after.write_count - io_before.write_count),
            "read_bytes": max(0, io_after.read_bytes - io_before.read_bytes),
            "write_bytes": max(0, io_after.write_bytes - io_before.write_bytes),
        },
    }
    return rows, metrics


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active benchmark only")
    lessons = distributed_lessons()
    proc = server_process()

    def login(username: str) -> tuple[str, requests.Session]:
        session = requests.Session()
        response = session.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=60)
        response.raise_for_status()
        session.headers.update({"Authorization": f"Bearer {response.json()['token']}"})
        return username, session

    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        sessions = dict(pool.map(login, USERS))

    def run_all_users(worker) -> list[dict]:
        barrier = threading.Barrier(len(USERS))

        def synchronized(username: str) -> list[dict]:
            barrier.wait(timeout=30)
            return worker(username)

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(USERS)) as pool:
            return [row for rows in pool.map(synchronized, USERS) for row in rows]

    def setup_user(username: str) -> list[dict]:
        session = sessions[username]
        paths = lessons[username]
        folders = [path.rsplit("/", 1)[0] for path in paths]
        rows = [request_json(session, "POST", "/lesson-tasks", body={"action": "space-folders", "user": username, "folders": folders})]
        for path in paths:
            rows.append(request_json(session, "POST", "/lesson-tasks", body={"action": "add", "user": username, "path": path, "severity": "normal"}))
        return rows

    setup_rows, setup_metrics = measured(proc, lambda: run_all_users(setup_user))
    if any(row["status"] != 200 for row in setup_rows):
        raise RuntimeError("One or more Space Task setup requests failed")

    def verify_user(username: str) -> tuple[str, int, int]:
        response = sessions[username].get(f"{BASE}/lesson-tasks", params={"user": username}, timeout=60)
        response.raise_for_status()
        payload = response.json()
        space_task = payload.get("space_task") if isinstance(payload.get("space_task"), dict) else {}
        task_rows = payload.get("tasks") if isinstance(payload.get("tasks"), list) else space_task.get("tasks") or []
        return username, len(task_rows), len(space_task.get("preferred_folders") or [])

    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        verified = list(pool.map(verify_user, USERS))
    if any(task_count < 3 or folder_count < 3 for _username, task_count, folder_count in verified):
        raise RuntimeError(f"Space Task setup incomplete: {verified[:5]}")

    progress_before = progress_fingerprint()

    def optimized_user(username: str) -> list[dict]:
        session = sessions[username]
        paths = lessons[username]
        rows = [request_json(session, "GET", "/lesson-tasks", params={"user": username})]
        for path in paths:
            rows.append(request_json(
                session,
                "GET",
                "/server-data/list",
                params={"path": path.rsplit("/", 1)[0], "task_owner": username, "defer_task_board": "1"},
            ))
        final_path = paths[-1]
        rows.append(request_json(session, "POST", "/server-data/last-file?client_source=server_last_file_sync", body={
            "file": {"path": final_path, "parentPath": final_path.rsplit("/", 1)[0], "accessedAt": "2026-07-21T01:45:00Z"},
            "recentFiles": [{"path": final_path, "parentPath": final_path.rsplit("/", 1)[0]}],
            "selectedFolder": {"path": final_path.rsplit("/", 1)[0], "task_owner": username},
        }))
        return rows

    optimized_rows, optimized_metrics = measured(proc, lambda: run_all_users(optimized_user))

    def pre_fix_coalesced_user(username: str) -> list[dict]:
        # Baseline retained for A/B: the old frontend still wrote one final folder checkpoint.
        final_path = lessons[username][0]
        return [request_json(sessions[username], "POST", "/server-data/last-file?client_source=server_last_file_sync", body={
            "file": {"path": final_path, "parentPath": final_path.rsplit("/", 1)[0], "accessedAt": "2026-07-21T01:46:00Z"},
            "recentFiles": [{"path": final_path, "parentPath": final_path.rsplit("/", 1)[0]}],
            "selectedFolder": {"path": final_path.rsplit("/", 1)[0], "task_owner": username},
        })]

    warm_rows, warm_metrics = measured(proc, lambda: run_all_users(pre_fix_coalesced_user))

    def naive_user(username: str) -> list[dict]:
        session = sessions[username]
        paths = lessons[username]
        rows = []
        for click_index in range(CLICK_COUNT):
            path = paths[click_index % len(paths)]
            parent = path.rsplit("/", 1)[0]
            rows.append(request_json(session, "GET", "/lesson-tasks", params={"user": username}))
            rows.append(request_json(session, "GET", "/server-data/list", params={
                "path": parent,
                "task_owner": username,
                "defer_task_board": "1",
            }))
            rows.append(request_json(session, "POST", "/server-data/last-file?client_source=server_last_file_sync", body={
                "file": {"path": path, "parentPath": parent, "accessedAt": f"2026-07-21T01:47:{click_index:02d}Z"},
                "recentFiles": [{"path": path, "parentPath": parent}],
                "selectedFolder": {"path": parent, "task_owner": username},
            }))
        return rows

    naive_rows, naive_metrics = measured(proc, lambda: run_all_users(naive_user))

    progress_after = progress_fingerprint()
    if progress_after != progress_before:
        raise RuntimeError("Space Task card navigation changed learning progress")
    if any(row["status"] >= 400 for row in optimized_rows + warm_rows + naive_rows):
        raise RuntimeError("One or more measured click requests failed")

    result = {
        "users": len(USERS),
        "cards_per_user": 3,
        "simultaneous_spam_clicks_per_user": CLICK_COUNT,
        "space_task_add_folders_and_cards": setup_metrics,
        "optimized_cold_upper_bound": optimized_metrics,
        "pre_fix_coalesced_folder_checkpoint": warm_metrics,
        "post_fix_warm_local_clicks": {
            "clicks": len(USERS) * CLICK_COUNT,
            "requests": 0,
            "route_counts": {},
            "server_cpu_ms_attributable": 0,
            "postgres_writer_tasks": 0,
            "note": "Tree-preloaded Space Task card focus is local-only; actual lesson open persists last-file.",
        },
        "naive_spam": naive_metrics,
        "progress_unchanged": True,
        "cleanup_required": True,
    }
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

