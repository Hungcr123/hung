"""Benchmark Space_V progress with hung and restore authoritative SQLite rows afterward."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sqlite3
import statistics
import time

import psutil
import requests


DATABASE = r"C:\server data\server2.db"
TARGET_PATH = "common/File 02 - {7}.Space_V"


def server_process() -> psutil.Process:
    listener_pid = None
    for connection in psutil.net_connections(kind="tcp"):
        if connection.laddr and connection.laddr.port == 8877 and connection.status == psutil.CONN_LISTEN:
            listener_pid = connection.pid
            break
    if listener_pid:
        return psutil.Process(listener_pid)
    raise RuntimeError("Server 2 listener not found")


def snapshot_rows() -> tuple[list[str], list[tuple], list[str], list[tuple], dict]:
    connection = sqlite3.connect(DATABASE)
    progress_columns = [row[1] for row in connection.execute("PRAGMA table_info(lesson_progress)")]
    namespace_columns = [row[1] for row in connection.execute("PRAGMA table_info(lesson_progress_namespaces)")]
    progress_rows = connection.execute(
        "SELECT * FROM lesson_progress WHERE username=? AND space=?",
        ("hung", "Space_V"),
    ).fetchall()
    namespace_rows = connection.execute(
        "SELECT * FROM lesson_progress_namespaces WHERE username=? AND space=?",
        ("hung", "Space_V"),
    ).fetchall()
    record_row = connection.execute(
        "SELECT record_json FROM lesson_progress WHERE username=? AND space=? AND path=? ORDER BY updated_at_utc DESC LIMIT 1",
        ("hung", "Space_V", TARGET_PATH),
    ).fetchone()
    connection.close()
    if not record_row:
        raise RuntimeError("Target Space_V progress row not found")
    return progress_columns, progress_rows, namespace_columns, namespace_rows, json.loads(record_row[0])


def restore_rows(progress_columns, progress_rows, namespace_columns, namespace_rows) -> None:
    connection = sqlite3.connect(DATABASE, timeout=30)
    connection.execute("BEGIN IMMEDIATE")
    connection.execute("DELETE FROM lesson_progress WHERE username=? AND space=?", ("hung", "Space_V"))
    connection.execute("DELETE FROM lesson_progress_namespaces WHERE username=? AND space=?", ("hung", "Space_V"))
    if namespace_rows:
        connection.executemany(
            f"INSERT INTO lesson_progress_namespaces ({','.join(namespace_columns)}) VALUES ({','.join('?' for _ in namespace_columns)})",
            namespace_rows,
        )
    if progress_rows:
        connection.executemany(
            f"INSERT INTO lesson_progress ({','.join(progress_columns)}) VALUES ({','.join('?' for _ in progress_columns)})",
            progress_rows,
        )
    connection.commit()
    connection.close()


def target_revision() -> int:
    connection = sqlite3.connect(DATABASE)
    row = connection.execute(
        "SELECT server_revision FROM lesson_progress WHERE username=? AND space=? AND path=? ORDER BY updated_at_utc DESC LIMIT 1",
        ("hung", "Space_V", TARGET_PATH),
    ).fetchone()
    connection.close()
    return int(row[0] or 0) if row else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8877")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--workers", type=int, default=20)
    args = parser.parse_args()
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active benchmark only")
    progress_columns, progress_rows, namespace_columns, namespace_rows, payload = snapshot_rows()
    original_revision = target_revision()
    payload["action"] = "autosave"
    payload["reason"] = "codex_space_v_benchmark"
    login = requests.post(f"{args.base}/auth/login", json={"username": "hung", "password": password}, timeout=15)
    login.raise_for_status()
    headers = {"Authorization": f"Bearer {login.json()['token']}", "Content-Type": "application/json"}
    process = server_process()
    rows = []
    try:
        before = sum(process.cpu_times()[:2])
        started = time.perf_counter()

        def request_once(_index: int):
            request_started = time.perf_counter()
            response = requests.post(
                f"{args.base}/space-v/progress?client_source=codex_benchmark&response=compact-v1",
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            response_payload = response.json()
            return response.status_code, len(response.content), (time.perf_counter() - request_started) * 1000, response_payload.get("response_schema", "")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            rows = list(pool.map(request_once, range(max(1, args.requests))))
        wall_ms = (time.perf_counter() - started) * 1000
        cpu_ms = max(0.0, (sum(process.cpu_times()[:2]) - before) * 1000)
        final_revision = target_revision()
        assert final_revision - original_revision == len(rows), (original_revision, final_revision, len(rows))
        assert all(row[3] == "space-v-progress-compact-v1" for row in rows)
    finally:
        restore_rows(progress_columns, progress_rows, namespace_columns, namespace_rows)

    latencies = sorted(row[2] for row in rows)
    print({
        "requests": len(rows),
        "workers": args.workers,
        "server_cpu_ms": round(cpu_ms, 3),
        "cpu_ms_per_request": round(cpu_ms / len(rows), 3),
        "wall_ms": round(wall_ms, 3),
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(latencies[max(0, int(len(latencies) * 0.95) - 1)], 3),
        "response_bytes": sum(row[1] for row in rows),
        "server_revision_delta": final_revision - original_revision,
        "statuses": {status: sum(1 for row in rows if row[0] == status) for status in sorted({row[0] for row in rows})},
        "sqlite_rows_restored": True,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
