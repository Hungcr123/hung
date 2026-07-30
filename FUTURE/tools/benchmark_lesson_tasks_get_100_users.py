"""Measure cold and warm full Lesson Task GETs for 100 distinct sessions."""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import statistics
import threading
import time

import requests

import benchmark_space_task_click_100_users as common


def parse_server_timing(value: str) -> dict[str, float]:
    rows = {}
    for name, duration in re.findall(r"([A-Za-z0-9_-]+);dur=([0-9.]+)", str(value or "")):
        rows[name] = float(duration)
    return rows


def summarize_stage_timings(rows: list[dict]) -> dict:
    names = sorted({name for row in rows for name in (row.get("server_timing") or {})})
    result = {}
    for name in names:
        values = sorted(float((row.get("server_timing") or {}).get(name, 0.0)) for row in rows if name in (row.get("server_timing") or {}))
        if not values:
            continue
        result[name] = {
            "count": len(values),
            "p50_ms": round(statistics.median(values), 3),
            "p95_ms": round(values[max(0, int(len(values) * 0.95) - 1)], 3),
            "p99_ms": round(values[max(0, int(len(values) * 0.99) - 1)], 3),
            "sum_ms": round(sum(values), 3),
        }
    return result


def summarize_request_latencies(rows: list[dict]) -> dict:
    values = sorted(float(row.get("latency_ms", 0.0) or 0.0) for row in rows)
    if not values:
        return {"count": 0, "p50_ms": 0, "p95_ms": 0, "p99_ms": 0}
    return {
        "count": len(values),
        "p50_ms": round(statistics.median(values), 3),
        "p95_ms": round(values[max(0, int(len(values) * 0.95) - 1)], 3),
        "p99_ms": round(values[max(0, int(len(values) * 0.99) - 1)], 3),
    }


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active benchmark only")
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

    # Keep auth-session touch batching outside the measured read-only phases.
    idle_samples = 0
    deadline = time.time() + 10.0
    while time.time() < deadline and idle_samples < 3:
        writer = requests.get(f"{common.BASE}/health", timeout=10).json().get("sqlite_writer", {})
        if int(writer.get("queue_depth", 0) or 0) == 0:
            idle_samples += 1
        else:
            idle_samples = 0
        time.sleep(0.1)
    if idle_samples < 3:
        raise RuntimeError("SQLite writer did not become idle before Lesson Task GET benchmark")

    def run_phase() -> list[dict]:
        barrier = threading.Barrier(len(common.USERS))

        def request(username: str) -> dict:
            barrier.wait(timeout=30)
            started = time.perf_counter()
            response = sessions[username].get(
                f"{common.BASE}/lesson-tasks",
                params={"user": username},
                timeout=90,
            )
            payload = response.json() if response.content else {}
            space_task = payload.get("space_task") if isinstance(payload.get("space_task"), dict) else {}
            return {
                "route": "/lesson-tasks",
                "status": response.status_code,
                "latency_ms": (time.perf_counter() - started) * 1000,
                "request_bytes": 0,
                "response_bytes": len(response.content),
                "cache_hit": response.headers.get("X-Future-Cache-Hit", ""),
                "server_timing": parse_server_timing(response.headers.get("Server-Timing", "")),
                "pending": bool(space_task.get("pending")),
                "space_task_count": len(space_task.get("tasks") or []),
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(common.USERS)) as pool:
            return list(pool.map(request, common.USERS))

    def run_status_phase() -> list[dict]:
        barrier = threading.Barrier(len(common.USERS))

        def request(username: str) -> dict:
            barrier.wait(timeout=30)
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
                "cache_hit": "status",
                "server_timing": {},
                "pending": not bool(payload.get("ready")),
                "space_task_count": int(payload.get("task_count", 0) or 0),
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(common.USERS)) as pool:
            return list(pool.map(request, common.USERS))

    initial_rows = []
    settle_rows = []
    final_rows = []

    def run_cold_and_settle() -> list[dict]:
        nonlocal initial_rows, settle_rows, final_rows
        initial_rows = run_phase()
        rows = list(initial_rows)
        pending = [row for row in initial_rows if row.get("pending")]
        for attempt in range(60):
            if not pending:
                break
            time.sleep(min(0.6, 0.16 + attempt * 0.02))
            phase_rows = run_status_phase()
            settle_rows.extend(phase_rows)
            rows.extend(phase_rows)
            pending = [row for row in phase_rows if row.get("pending")]
        if pending:
            raise RuntimeError(f"{len(pending)} Lesson Task payloads did not settle")
        if any(row.get("pending") for row in initial_rows):
            final_rows = run_phase()
            rows.extend(final_rows)
        return rows

    cold_rows, cold = common.measured(proc, run_cold_and_settle)
    warm_rows, warm = common.measured(proc, run_phase)
    for rows in (cold_rows, warm_rows):
        if any(row["status"] != 200 for row in rows):
            raise RuntimeError("One or more Lesson Task GET requests failed")
    print(json.dumps({
        "users": len(common.USERS),
        "cold": cold,
        "warm": warm,
        "initial_requests": len(initial_rows),
        "settle_requests": len(settle_rows),
        "initial_pending": sum(bool(row.get("pending")) for row in initial_rows),
        "initial_latency": summarize_request_latencies(initial_rows),
        "final_poll_latency": summarize_request_latencies(final_rows),
        "final_space_task_count_min_max": [
            min(row.get("space_task_count", 0) for row in (final_rows or initial_rows)),
            max(row.get("space_task_count", 0) for row in (final_rows or initial_rows)),
        ],
        "cache_headers": {
            "cold": {value: sum(row["cache_hit"] == value for row in cold_rows) for value in sorted({row["cache_hit"] for row in cold_rows})},
            "warm": {value: sum(row["cache_hit"] == value for row in warm_rows) for value in sorted({row["cache_hit"] for row in warm_rows})},
        },
        "cold_stages": summarize_stage_timings(initial_rows),
        "warm_stages": summarize_stage_timings(warm_rows),
    }, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
