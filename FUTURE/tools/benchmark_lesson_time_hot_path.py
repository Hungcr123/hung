"""Benchmark rapid /lesson/time spam rejection and restore exact SQLite rows afterward."""

from __future__ import annotations

import argparse
import concurrent.futures
import os
import sqlite3
import statistics
import time
import uuid

import psutil
import requests


DATABASE = r"C:\server data\server2.db"


def server_process() -> psutil.Process:
    for connection in psutil.net_connections(kind="tcp"):
        if connection.laddr and connection.laddr.port == 8877 and connection.status == psutil.CONN_LISTEN and connection.pid:
            return psutil.Process(connection.pid)
    raise RuntimeError("Server 2 process not found")


def read_lesson_time_rows() -> tuple[list[str], list[tuple], list[str], list[tuple]]:
    connection = sqlite3.connect(DATABASE)
    columns = [item[1] for item in connection.execute("PRAGMA table_info(lesson_time)").fetchall()]
    rows = connection.execute("SELECT * FROM lesson_time WHERE username=?", ("hung",)).fetchall()
    credit_columns = [item[1] for item in connection.execute("PRAGMA table_info(lesson_time_credit_state)").fetchall()]
    credit_rows = connection.execute("SELECT * FROM lesson_time_credit_state WHERE username=?", ("hung",)).fetchall() if credit_columns else []
    connection.close()
    if not rows:
        raise RuntimeError("hung lesson-time rows not found")
    return columns, rows, credit_columns, credit_rows


def restore_lesson_time_rows(columns: list[str], rows: list[tuple], credit_columns: list[str], credit_rows: list[tuple]) -> None:
    connection = sqlite3.connect(DATABASE, timeout=30)
    placeholders = ",".join("?" for _column in columns)
    connection.execute("BEGIN IMMEDIATE")
    connection.execute("DELETE FROM lesson_time WHERE username=?", ("hung",))
    if credit_columns:
        connection.execute("DELETE FROM lesson_time_credit_state WHERE username=?", ("hung",))
    connection.executemany(f"INSERT INTO lesson_time ({','.join(columns)}) VALUES ({placeholders})", rows)
    if credit_columns and credit_rows:
        credit_placeholders = ",".join("?" for _column in credit_columns)
        connection.executemany(
            f"INSERT INTO lesson_time_credit_state ({','.join(credit_columns)}) VALUES ({credit_placeholders})",
            credit_rows,
        )
    connection.commit()
    connection.close()


def lesson_time_totals() -> tuple[int, int]:
    connection = sqlite3.connect(DATABASE)
    row = connection.execute("SELECT COALESCE(SUM(seconds),0),COALESCE(SUM(ticks),0) FROM lesson_time WHERE username=?", ("hung",)).fetchone()
    connection.close()
    return int(row[0] or 0), int(row[1] or 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8877")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--workers", type=int, default=20)
    args = parser.parse_args()
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active benchmark only")

    columns, original_rows, credit_columns, original_credit_rows = read_lesson_time_rows()
    original_seconds, original_ticks = lesson_time_totals()
    login = requests.post(
        f"{args.base}/auth/login",
        json={"username": "hung", "password": password},
        timeout=15,
    )
    login.raise_for_status()
    token = login.json().get("token", "")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    session_id = f"lesson-benchmark-{uuid.uuid4().hex}"
    payload = {
        "path": "common/File 02 - {7}.Space_V",
        "title": "Codex lesson-time benchmark",
        "space": "Space_V",
        "seconds": 0,
        "protocol": "server-time-v1",
        "session_id": session_id,
        "sequence": 0,
    }
    start = requests.post(f"{args.base}/lesson/time", headers=headers, json=payload, timeout=15)
    start.raise_for_status()
    process = server_process()
    rows = []
    try:
        before = sum(process.cpu_times()[:2])
        started = time.perf_counter()

        def request_once(index: int):
            request_started = time.perf_counter()
            response = requests.post(
                f"{args.base}/lesson/time",
                headers=headers,
                json={**payload, "seconds": 1, "sequence": index + 1},
                timeout=60,
            )
            if response.status_code not in {200, 429}:
                response.raise_for_status()
            return response.status_code, len(response.content), (time.perf_counter() - request_started) * 1000, int(response.json().get("time", {}).get("acceptedSeconds", 0) or 0)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            rows = list(pool.map(request_once, range(max(1, args.requests))))
        wall_ms = (time.perf_counter() - started) * 1000
        cpu_ms = max(0.0, (sum(process.cpu_times()[:2]) - before) * 1000)
        final_seconds, final_ticks = lesson_time_totals()
        assert final_seconds == original_seconds, (original_seconds, final_seconds)
        assert final_ticks == original_ticks, (original_ticks, final_ticks)
        assert sum(row[3] for row in rows) == 0
    finally:
        restore_lesson_time_rows(columns, original_rows, credit_columns, original_credit_rows)

    latencies = sorted(row[2] for row in rows)
    print(
        {
            "requests": len(rows),
            "workers": args.workers,
            "server_cpu_ms": round(cpu_ms, 3),
            "cpu_ms_per_request": round(cpu_ms / len(rows), 3),
            "wall_ms": round(wall_ms, 3),
            "p50_ms": round(statistics.median(latencies), 3),
            "p95_ms": round(latencies[max(0, int(len(latencies) * 0.95) - 1)], 3),
            "response_bytes": sum(row[1] for row in rows),
            "statuses": {status: sum(1 for row in rows if row[0] == status) for status in sorted({row[0] for row in rows})},
            "seconds_delta": 0,
            "ticks_delta": 0,
            "accepted_seconds": sum(row[3] for row in rows),
            "sqlite_rows_restored": True,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
