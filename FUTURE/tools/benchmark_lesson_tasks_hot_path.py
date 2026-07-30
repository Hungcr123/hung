"""Measure 100-user Lesson Task reads/writes and the shared document hot path."""

from __future__ import annotations

import concurrent.futures
import json
import os
import sqlite3
import statistics
import time
from pathlib import Path

import psutil
import requests


BASE = "http://127.0.0.1:8877"
DATABASE = Path(r"C:\server data\server2.db")
MANIFEST = Path(r"C:\server data\_future_server_data_manifest.json")
TASK_DOCUMENT = Path(r"C:\server data\_future_lesson_tasks.json")
USERS = tuple(f"codexload{index:03d}" for index in range(1, 101))


def paths() -> list[str]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    out = []
    for entries in (manifest.get("folders") or {}).values():
        for entry in entries if isinstance(entries, list) else []:
            path = str(entry.get("path", "")).strip() if isinstance(entry, dict) else ""
            if path.lower().startswith("common/") and path.lower().endswith((".space_v", ".space_w", ".space_q", ".space_p", ".space_l", ".space_s")):
                out.append(path)
                if len(out) == len(USERS):
                    return out
    raise RuntimeError(f"Need 100 common lesson files; found {len(out)}")


def process() -> psutil.Process:
    for conn in psutil.net_connections(kind="tcp"):
        if conn.laddr and conn.laddr.port == 8877 and conn.status == psutil.CONN_LISTEN and conn.pid:
            return psutil.Process(conn.pid)
    raise RuntimeError("Server 2 listener not found")


def metrics(proc: psutil.Process, callback) -> tuple[list[dict], dict]:
    writer_before = requests.get(f"{BASE}/health", timeout=10).json().get("sqlite_writer", {})
    before_cpu = sum(proc.cpu_times()[:2])
    before_io = proc.io_counters()
    wal = Path(str(DATABASE) + "-wal")
    before_wal = wal.stat().st_size if wal.exists() else 0
    started = time.perf_counter()
    rows = callback()
    wall_ms = (time.perf_counter() - started) * 1000
    after_cpu = sum(proc.cpu_times()[:2])
    after_io = proc.io_counters()
    writer_after = requests.get(f"{BASE}/health", timeout=10).json().get("sqlite_writer", {})
    after_wal = wal.stat().st_size if wal.exists() else 0
    latencies = sorted(float(row["latency_ms"]) for row in rows)
    return rows, {
        "requests": len(rows),
        "server_cpu_ms": round(max(0, after_cpu - before_cpu) * 1000, 3),
        "cpu_ms_per_request": round(max(0, after_cpu - before_cpu) * 1000 / max(1, len(rows)), 3),
        "wall_ms": round(wall_ms, 3),
        "requests_per_second": round(len(rows) / max(0.001, wall_ms / 1000), 3),
        "p50_ms": round(statistics.median(latencies), 3) if latencies else 0,
        "p95_ms": round(latencies[max(0, int(len(latencies) * 0.95) - 1)], 3) if latencies else 0,
        "p99_ms": round(latencies[max(0, int(len(latencies) * 0.99) - 1)], 3) if latencies else 0,
        "request_bytes": sum(row["request_bytes"] for row in rows),
        "response_bytes": sum(row["response_bytes"] for row in rows),
        "wal_size_delta": after_wal - before_wal,
        "sqlite_writer": {
            key: round(float(writer_after.get(key, 0) or 0) - float(writer_before.get(key, 0) or 0), 3)
            for key in ("batches", "tasks", "queue_wait_ms", "begin_wait_ms", "commit_ms", "busy_errors")
        },
        "process_io": {
            "read_ops": max(0, after_io.read_count - before_io.read_count),
            "write_ops": max(0, after_io.write_count - before_io.write_count),
            "read_bytes": max(0, after_io.read_bytes - before_io.read_bytes),
            "write_bytes": max(0, after_io.write_bytes - before_io.write_bytes),
        },
        "errors": sum(1 for row in rows if row["status"] >= 400),
    }


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active benchmark only")
    lesson_paths = paths()
    proc = process()

    def login(username: str) -> tuple[str, str]:
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        return username, response.json()["token"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        tokens = dict(pool.map(login, USERS))

    def request(index: int, method: str, action: str = "add", path_override: str = "") -> dict:
        username = USERS[index]
        headers = {"Authorization": f"Bearer {tokens[username]}", "Content-Type": "application/json"}
        if method == "GET":
            url = f"{BASE}/lesson-tasks"
            body = None
            params = {"user": username}
        else:
            url = f"{BASE}/lesson-tasks"
            body = {"action": action, "path": path_override or lesson_paths[index], "user": username, "severity": "normal"}
            params = None
        started = time.perf_counter()
        response = requests.request(method, url, headers=headers, params=params, json=body, timeout=60)
        return {
            "latency_ms": (time.perf_counter() - started) * 1000,
            "status": response.status_code,
            "request_bytes": len(json.dumps(body, separators=(",", ":")).encode("utf-8")) if body else 0,
            "response_bytes": len(response.content),
            "cache_hit": response.headers.get("X-Future-Cache-Hit", ""),
            "body": response.json() if response.content else {},
        }

    def parallel(method: str, action: str = "add") -> list[dict]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
            return list(pool.map(lambda index: request(index, method, action), range(100)))

    unique_rows, unique_metrics = metrics(proc, lambda: parallel("POST", "add"))
    duplicate_rows, duplicate_metrics = metrics(proc, lambda: parallel("POST", "add"))
    read_rows, read_metrics = metrics(proc, lambda: parallel("GET"))
    warm_rows, warm_metrics = metrics(proc, lambda: parallel("GET"))
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        second_unique_rows, second_unique_metrics = metrics(
            proc,
            lambda: list(pool.map(lambda index: request(index, "POST", "add", lesson_paths[(index + 1) % len(lesson_paths)]), range(100))),
        )
    second_read_rows, second_read_metrics = metrics(proc, lambda: parallel("GET"))
    single_user_write, single_user_write_metrics = metrics(proc, lambda: [request(0, "POST", "add", lesson_paths[2 % len(lesson_paths)])])
    invalidation_rows, invalidation_metrics = metrics(proc, lambda: parallel("GET"))
    time.sleep(3.2)
    document_bytes = TASK_DOCUMENT.stat().st_size if TASK_DOCUMENT.exists() else 0
    with sqlite3.connect(DATABASE) as connection:
        document_row = connection.execute(
            "SELECT COUNT(*),COALESCE(SUM(length(record_json)),0),COALESCE(SUM(server_revision),0) FROM lesson_task_state WHERE username LIKE 'codexload%'"
        ).fetchone()
        namespaces = connection.execute("SELECT COUNT(*) FROM documents WHERE path LIKE '%_future_lesson_tasks.json'").fetchone()[0]
    result = {
        "users": 100,
        "unique_add": unique_metrics,
        "duplicate_add": duplicate_metrics,
        "second_unique_add": second_unique_metrics,
        "read": read_metrics,
        "second_read": second_read_metrics,
        "success": {
            "unique": sum(row["status"] == 200 for row in unique_rows),
            "duplicate": sum(row["status"] == 200 for row in duplicate_rows),
            "second_unique": sum(row["status"] == 200 for row in second_unique_rows),
            "read": sum(row["status"] == 200 for row in read_rows),
            "warm_read": sum(row["status"] == 200 for row in warm_rows),
            "second_read": sum(row["status"] == 200 for row in second_read_rows),
        },
        "warm_read": warm_metrics,
        "single_user_write": single_user_write_metrics,
        "after_one_user_write": invalidation_metrics,
        "cache_headers": {
            "read": {value: sum(row["cache_hit"] == value for row in read_rows) for value in sorted({row["cache_hit"] for row in read_rows})},
            "warm": {value: sum(row["cache_hit"] == value for row in warm_rows) for value in sorted({row["cache_hit"] for row in warm_rows})},
            "after_one_user_write": {value: sum(row["cache_hit"] == value for row in invalidation_rows) for value in sorted({row["cache_hit"] for row in invalidation_rows})},
        },
        "task_storage": {"legacy_filesystem_bytes": document_bytes, "legacy_document_rows": namespaces, "sqlite_test_rows_bytes_revision": document_row},
        "cleanup_required": True,
    }
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
