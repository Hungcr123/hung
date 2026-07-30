"""Benchmark 100 isolated /auth/login calls for a configured test-hash round count."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import statistics
import time
from pathlib import Path

import psutil
import requests


BASE = "http://127.0.0.1:8877"
USERS = tuple(f"codexload{index:03d}" for index in range(1, 101))


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = max(0.0, min(len(ordered) - 1, (len(ordered) - 1) * fraction))
    lower = int(position)
    upper = min(len(ordered) - 1, lower + 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def health() -> dict:
    response = requests.get(f"{BASE}/health", timeout=15)
    response.raise_for_status()
    return response.json()


def wait_ready(timeout: float = 90.0) -> dict:
    deadline = time.monotonic() + timeout
    latest = {}
    while time.monotonic() < deadline:
        try:
            latest = health()
            writer = latest.get("postgres_writer", {}) if isinstance(latest, dict) else {}
            if latest.get("ok") and latest.get("warm_ready") and int(writer.get("queue_depth", 0) or 0) == 0:
                return latest
        except requests.RequestException:
            pass
        time.sleep(0.25)
    raise RuntimeError(f"Server 2 did not become warm/idle: {latest}")


def wait_writer_idle(timeout: float = 30.0) -> dict:
    deadline = time.monotonic() + timeout
    latest = {}
    while time.monotonic() < deadline:
        latest = health()
        writer = latest.get("postgres_writer", {}) if isinstance(latest, dict) else {}
        if int(writer.get("queue_depth", 0) or 0) == 0 and not str(writer.get("active_source", "") or ""):
            return writer
        time.sleep(0.05)
    raise RuntimeError(f"SQLite writer did not become idle: {latest}")


def cpu_seconds(process: psutil.Process) -> float:
    times = process.cpu_times()
    return float(times.user + times.system)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, required=True)
    parser.add_argument("--workers", type=int, default=25)
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this benchmark only")

    state = wait_ready()
    process = psutil.Process(int(state.get("pid", 0) or 0))
    writer_before = wait_writer_idle()
    cpu_before = cpu_seconds(process)
    rss_before = int(process.memory_info().rss)
    io_before = process.io_counters()

    def login(username: str) -> dict:
        started = time.perf_counter()
        response = requests.post(
            f"{BASE}/auth/login",
            json={"username": username, "password": password},
            timeout=60,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        return {
            "username": username,
            "status": response.status_code,
            "elapsed_ms": elapsed_ms,
            "ok": bool(response.status_code == 200 and payload.get("token")),
        }

    wall_started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = list(pool.map(login, USERS))
    wall_seconds = time.perf_counter() - wall_started
    writer_after = wait_writer_idle()
    cpu_after = cpu_seconds(process)
    rss_after = int(process.memory_info().rss)
    io_after = process.io_counters()

    latencies = [float(row["elapsed_ms"]) for row in rows]
    successes = sum(bool(row["ok"]) for row in rows)
    cpu_ms = max(0.0, (cpu_after - cpu_before) * 1000.0)
    result = {
        "benchmark": "auth_login_pbkdf2_rounds_v1",
        "rounds": int(args.rounds),
        "users": len(USERS),
        "workers": int(args.workers),
        "successes": successes,
        "errors": len(USERS) - successes,
        "wall_ms": round(wall_seconds * 1000.0, 3),
        "throughput_users_s": round(len(USERS) / wall_seconds, 3),
        "server_cpu_ms": round(cpu_ms, 3),
        "server_cpu_ms_per_login": round(cpu_ms / len(USERS), 3),
        "latency_ms": {
            "min": round(min(latencies), 3),
            "p50": round(statistics.median(latencies), 3),
            "p95": round(percentile(latencies, 0.95), 3),
            "p99": round(percentile(latencies, 0.99), 3),
            "max": round(max(latencies), 3),
        },
        "rss_bytes": {"before": rss_before, "after": rss_after, "delta": rss_after - rss_before},
        "io": {
            "read_count": int(io_after.read_count - io_before.read_count),
            "read_bytes": int(io_after.read_bytes - io_before.read_bytes),
            "write_count": int(io_after.write_count - io_before.write_count),
            "write_bytes": int(io_after.write_bytes - io_before.write_bytes),
        },
        "writer": {
            "tasks": int(writer_after.get("tasks", 0) or 0) - int(writer_before.get("tasks", 0) or 0),
            "batches": int(writer_after.get("batches", 0) or 0) - int(writer_before.get("batches", 0) or 0),
            "busy_errors": int(writer_after.get("busy_errors", 0) or 0) - int(writer_before.get("busy_errors", 0) or 0),
            "queue_depth": int(writer_after.get("queue_depth", 0) or 0),
        },
    }
    if successes != len(USERS):
        result["failed_statuses"] = [row["status"] for row in rows if not row["ok"]][:10]
    encoded = json.dumps(result, indent=2, sort_keys=True)
    print(encoded)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
    return 0 if successes == len(USERS) else 1


if __name__ == "__main__":
    raise SystemExit(main())

