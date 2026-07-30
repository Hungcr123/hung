"""Benchmark cold/warm Task Board reads for 100 users that only have lesson-time state."""

from __future__ import annotations

import concurrent.futures
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE.tools.benchmark_server2_100_users import (  # noqa: E402
    BASE,
    DATABASE,
    USERS,
    measured,
    response_sizes,
    server_process,
    wait_for_writer_quiescence,
)


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active benchmark only")
    with sqlite3.connect(DATABASE) as connection:
        placeholders = ",".join("?" for _ in USERS)
        time_users = int(connection.execute(
            f"SELECT COUNT(DISTINCT username) FROM lesson_time WHERE username IN ({placeholders})",
            USERS,
        ).fetchone()[0])
        summaries = int(connection.execute(
            "SELECT COUNT(*) FROM documents WHERE lower(path) LIKE '%_future_learning_summary.json' "
            "AND lower(path) LIKE '%codexload%'"
        ).fetchone()[0])
    if time_users != 100 or summaries != 0:
        raise RuntimeError(f"Expected 100 time-only users and zero cached summaries, got time={time_users}, summaries={summaries}")

    def login(username: str) -> tuple[str, str]:
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        return username, str(response.json().get("token") or "")

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        tokens = dict(pool.map(login, USERS))
    # Login/session state has a shared delayed flush; let it commit before attributing Task GET writes.
    time.sleep(3.5)
    wait_for_writer_quiescence()
    process = server_process()

    def task_request(index: int):
        username = USERS[index]
        started = time.perf_counter()
        response = requests.get(
            f"{BASE}/lesson-tasks",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            params={"user": username},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        stats = payload.get("learning_stats") if isinstance(payload.get("learning_stats"), dict) else {}
        if payload.get("tasks") or int(stats.get("total_files", 0) or 0) != 0:
            raise RuntimeError(f"Unexpected Task Board payload for time-only user {username}")
        decoded, wire, request_bytes = response_sizes(response)
        return (time.perf_counter() - started) * 1000, response.status_code, decoded, wire, request_bytes

    def phase(count: int):
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(50, count)) as pool:
            return list(pool.map(task_request, range(count)))

    cold_rows, cold = measured(process, lambda: phase(100))
    wait_for_writer_quiescence()
    warm_rows, warm = measured(process, lambda: phase(100))
    wait_for_writer_quiescence()
    rows_50, warm_50 = measured(process, lambda: phase(50))
    wait_for_writer_quiescence()
    rows_35, warm_35 = measured(process, lambda: phase(35))
    assert len(cold_rows) == len(warm_rows) == 100 and len(rows_50) == 50 and len(rows_35) == 35
    for metrics in (cold, warm, warm_50, warm_35):
        if metrics["postgres_writer"]["tasks"] != 0:
            raise RuntimeError(f"Task GET unexpectedly wrote state: {metrics}")
    print(json.dumps({"cold_100": cold, "warm_100": warm, "warm_50": warm_50, "warm_35": warm_35}, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

