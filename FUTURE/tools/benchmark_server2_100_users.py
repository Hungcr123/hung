"""Benchmark 100 distinct SQLite-only users across accepted writes and a mixed workload."""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import sqlite3
import statistics
import threading
import time
import uuid
from pathlib import Path

import psutil
import requests


BASE = "http://127.0.0.1:8877"
DATABASE = Path(r"C:\server data\server2.db")
MANIFEST = Path(r"C:\server data\_future_server_data_manifest.json")
USERS = tuple(f"codexload{index:03d}" for index in range(1, 101))


def server_process() -> psutil.Process:
    for connection in psutil.net_connections(kind="tcp"):
        if connection.laddr and connection.laddr.port == 8877 and connection.status == psutil.CONN_LISTEN and connection.pid:
            return psutil.Process(connection.pid)
    raise RuntimeError("Server 2 listener not found")


def cpu_seconds(process: psutil.Process) -> float:
    row = process.cpu_times()
    return float(row.user + row.system)


def lesson_paths() -> list[str]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    for entries in (payload.get("folders") or {}).values():
        for entry in entries if isinstance(entries, list) else []:
            if not isinstance(entry, dict) or clean(entry.get("type")) != "file":
                continue
            path = clean(entry.get("path"))
            if not path.lower().startswith("common/") or not path.lower().endswith((".space_v", ".space_w", ".space_q", ".space_p", ".space_l", ".space_s")):
                continue
            rows.append(path)
            if len(rows) >= len(USERS):
                return rows
    raise RuntimeError(f"Manifest contains only {len(rows)} usable lesson paths")


def clean(value) -> str:
    return str(value or "").strip()


def measured(process: psutil.Process, callback):
    writer_before = requests.get(f"{BASE}/health", timeout=10).json().get("postgres_writer", {})
    before = cpu_seconds(process)
    io_before = process.io_counters()
    rss_before = int(process.memory_info().rss)
    rss_peak = [rss_before]
    stop_sampling = threading.Event()

    def sample_rss() -> None:
        while not stop_sampling.wait(0.01):
            try:
                rss_peak[0] = max(rss_peak[0], int(process.memory_info().rss))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return

    sampler = threading.Thread(target=sample_rss, name="server2-benchmark-rss", daemon=True)
    sampler.start()
    started = time.perf_counter()
    try:
        rows = callback()
    finally:
        stop_sampling.set()
        sampler.join(timeout=1.0)
    wall_ms = (time.perf_counter() - started) * 1000
    cpu_ms = max(0.0, (cpu_seconds(process) - before) * 1000)
    io_after = process.io_counters()
    rss_after = int(process.memory_info().rss)
    writer_after = requests.get(f"{BASE}/health", timeout=10).json().get("postgres_writer", {})
    latencies = [row[0] for row in rows]
    ordered = sorted(latencies)
    return rows, {
        "requests": len(rows),
        "server_cpu_ms": round(cpu_ms, 3),
        "cpu_ms_per_request": round(cpu_ms / max(1, len(rows)), 3),
        "wall_ms": round(wall_ms, 3),
        "requests_per_second": round(len(rows) / max(0.001, wall_ms / 1000), 3),
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(ordered[max(0, int(len(ordered) * 0.95) - 1)], 3),
        "p99_ms": round(ordered[max(0, int(len(ordered) * 0.99) - 1)], 3),
        "decoded_response_bytes": sum(row[2] for row in rows),
        "wire_response_bytes": sum(row[3] for row in rows),
        "request_body_bytes": sum(row[4] for row in rows),
        "rss": {
            "before": rss_before,
            "peak": max(rss_peak[0], rss_after),
            "after": rss_after,
            "delta": rss_after - rss_before,
        },
        "postgres_writer": {
            key: round(float(writer_after.get(key, 0) or 0) - float(writer_before.get(key, 0) or 0), 3)
            for key in ("batches", "tasks", "queue_wait_ms", "begin_wait_ms", "commit_ms", "busy_errors")
        },
        "process_io": {
            "read_ops": max(0, int(io_after.read_count - io_before.read_count)),
            "write_ops": max(0, int(io_after.write_count - io_before.write_count)),
            "read_bytes": max(0, int(io_after.read_bytes - io_before.read_bytes)),
            "write_bytes": max(0, int(io_after.write_bytes - io_before.write_bytes)),
        },
        "statuses": {status: sum(1 for row in rows if row[1] == status) for status in sorted({row[1] for row in rows})},
    }


# Added 2026-07-20: keep delayed write-behind work from contaminating the next route phase.
def wait_for_writer_quiescence(timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    stable = 0
    previous = None
    while time.monotonic() < deadline:
        writer = requests.get(f"{BASE}/health", timeout=10).json().get("postgres_writer", {})
        current = (
            int(writer.get("tasks", 0) or 0),
            int(writer.get("batches", 0) or 0),
        )
        if current == previous:
            stable += 1
            if stable >= 3:
                return
        else:
            stable = 0
            previous = current
        time.sleep(0.2)
    raise RuntimeError("SQLite writer did not become quiescent before the next benchmark phase")


def response_sizes(response: requests.Response) -> tuple[int, int, int]:
    decoded = len(response.content)
    wire = int(response.headers.get("Content-Length") or decoded)
    body = response.request.body
    if body is None:
        request_bytes = 0
    elif isinstance(body, bytes):
        request_bytes = len(body)
    else:
        request_bytes = len(str(body).encode("utf-8"))
    return decoded, wire, request_bytes


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active benchmark only")
    paths = lesson_paths()
    connection = sqlite3.connect(DATABASE)
    aliases = {
        str(row[0]).lower(): str(row[1] or "")
        for row in connection.execute("SELECT normalized_path,file_id FROM lesson_file_aliases WHERE active=1")
    }
    connection.close()
    lesson_ids = [aliases.get(path.lower(), "") for path in paths]
    if not all(value.lower().startswith("ftg-lesson-") for value in lesson_ids):
        raise RuntimeError("Mixed benchmark requires 100 active canonical lesson IDs")
    process = server_process()

    def login_one(username: str):
        started = time.perf_counter()
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        token = clean(response.json().get("token"))
        if not token or response.json().get("server_data", {}).get("load_test") is not True:
            raise RuntimeError(f"Load-test login was not isolated for {username}")
        decoded, wire, request_bytes = response_sizes(response)
        return (time.perf_counter() - started) * 1000, response.status_code, decoded, wire, request_bytes, token

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        login_rows, login_metrics = measured(process, lambda: list(pool.map(login_one, USERS)))
    tokens = {username: row[5] for username, row in zip(USERS, login_rows)}
    sessions = {username: f"lesson-load-{uuid.uuid4().hex}" for username in USERS}

    def heartbeat(index: int, sequence: int, seconds: int, lease: str = ""):
        username = USERS[index]
        started = time.perf_counter()
        response = requests.post(
            f"{BASE}/lesson/time",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            json={
                "path": paths[index],
                "lesson_id": lesson_ids[index],
                "space": "Space_V",
                "seconds": seconds,
                "protocol": "server-time-v1",
                "session_id": sessions[username],
                "sequence": sequence,
                "offline_lease": lease,
            },
            timeout=30,
        )
        response.raise_for_status()
        decoded, wire, request_bytes = response_sizes(response)
        return (time.perf_counter() - started) * 1000, response.status_code, decoded, wire, request_bytes, response.json().get("time", {})

    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        start_rows, start_metrics = measured(process, lambda: list(pool.map(lambda index: heartbeat(index, 0, 0), range(100))))
    leases = [clean(row[5].get("offlineLease")) for row in start_rows]
    if not all(leases):
        raise RuntimeError("One or more load-test sessions did not receive a signed offline lease")

    time.sleep(1.15)
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        write_rows, write_metrics = measured(process, lambda: list(pool.map(lambda index: heartbeat(index, 1, 1, leases[index]), range(100))))
    accepted = sum(int(row[5].get("acceptedSeconds", 0) or 0) for row in write_rows)
    if accepted != 100:
        raise RuntimeError(f"Expected 100 verified seconds across distinct users, got {accepted}")

    run_id = uuid.uuid4().hex
    wait_for_writer_quiescence()

    def tree_request(index: int):
        started = time.perf_counter()
        response = requests.get(
            f"{BASE}/server-data/tree-preload",
            headers={"Authorization": f"Bearer {tokens[USERS[index]]}"},
            timeout=30,
        )
        response.raise_for_status()
        decoded, wire, request_bytes = response_sizes(response)
        return (
            (time.perf_counter() - started) * 1000,
            response.status_code,
            decoded,
            wire,
            request_bytes,
            index,
            0,
            clean(response.headers.get("X-Future-Cache-Hit")),
            clean(response.headers.get("Server-Timing")),
        )

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
        decoded, wire, request_bytes = response_sizes(response)
        return (time.perf_counter() - started) * 1000, response.status_code, decoded, wire, request_bytes, index, 0

    def time_request(index: int, sequence: int):
        row = heartbeat(index, sequence, 1, leases[index])
        return (*row[:5], index, int(row[5].get("acceptedSeconds", 0) or 0))

    def inventory_request(index: int, phase: str):
        username = USERS[index]
        started = time.perf_counter()
        response = requests.post(
            f"{BASE}/inventory/award?response=delta-v1",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            json={
                "event_id": f"load-test:{run_id}:{phase}:{username}", "quantity": 1,
                "item": {"id": "load_test_crystal", "name": "Load Test Crystal", "use": "Synthetic benchmark state"},
            },
            timeout=30,
        )
        response.raise_for_status()
        decoded, wire, request_bytes = response_sizes(response)
        return (time.perf_counter() - started) * 1000, response.status_code, decoded, wire, request_bytes, index, 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=35) as pool:
        tree_rows, tree_metrics = measured(process, lambda: list(pool.map(tree_request, range(35))))
    tree_cache_headers = {value: sum(1 for row in tree_rows if row[7] == value) for value in sorted({row[7] for row in tree_rows})}
    tree_prepare_ms = [float(re.search(r"dur=([0-9.]+)", row[8]).group(1)) for row in tree_rows if re.search(r"dur=([0-9.]+)", row[8])]
    tree_prepare_metrics = {
        "p50_ms": round(statistics.median(tree_prepare_ms), 3) if tree_prepare_ms else 0,
        "p95_ms": round(sorted(tree_prepare_ms)[max(0, int(len(tree_prepare_ms) * 0.95) - 1)], 3) if tree_prepare_ms else 0,
        "max_ms": round(max(tree_prepare_ms), 3) if tree_prepare_ms else 0,
    }
    print("ROUTE_TREE", json.dumps({**tree_metrics, "cache_headers": tree_cache_headers, "prepare": tree_prepare_metrics}, ensure_ascii=True), flush=True)
    wait_for_writer_quiescence()
    with concurrent.futures.ThreadPoolExecutor(max_workers=35) as pool:
        task_rows, task_metrics = measured(process, lambda: list(pool.map(task_request, range(35, 70))))
    print("ROUTE_TASKS", json.dumps(task_metrics, ensure_ascii=True), flush=True)
    wait_for_writer_quiescence()
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        time_rows, time_metrics = measured(process, lambda: list(pool.map(lambda index: time_request(index, 2), range(70, 90))))
    route_time_accepted = sum(row[6] for row in time_rows)
    print("ROUTE_TIME", json.dumps({**time_metrics, "accepted_seconds": route_time_accepted}, ensure_ascii=True), flush=True)
    wait_for_writer_quiescence()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        inventory_probe_rows, inventory_metrics = measured(process, lambda: list(pool.map(lambda index: inventory_request(index, "route"), range(90, 100))))
    print("ROUTE_INVENTORY", json.dumps(inventory_metrics, ensure_ascii=True), flush=True)

    def mixed_request(index: int):
        username = USERS[index]
        headers = {"Authorization": f"Bearer {tokens[username]}"}
        started = time.perf_counter()
        if index < 35:
            response = requests.get(f"{BASE}/server-data/tree-preload", headers=headers, timeout=30)
        elif index < 70:
            response = requests.get(f"{BASE}/lesson-tasks", headers=headers, params={"user": username}, timeout=30)
        elif index < 90:
            response = requests.post(
                f"{BASE}/lesson/time",
                headers=headers,
                json={
                    "path": paths[index], "lesson_id": lesson_ids[index], "space": "Space_V", "seconds": 1, "protocol": "server-time-v1",
                    "session_id": sessions[username], "sequence": 3, "offline_lease": leases[index],
                },
                timeout=30,
            )
        else:
            response = requests.post(
                f"{BASE}/inventory/award?response=delta-v1",
                headers=headers,
                json={
                    "event_id": f"load-test:{run_id}:mixed:{username}", "quantity": 1,
                    "item": {"id": "load_test_crystal", "name": "Load Test Crystal", "use": "Synthetic benchmark state"},
                },
                timeout=30,
            )
        response.raise_for_status()
        accepted_seconds = int(response.json().get("time", {}).get("acceptedSeconds", 0) or 0) if 70 <= index < 90 else 0
        decoded, wire, request_bytes = response_sizes(response)
        return (time.perf_counter() - started) * 1000, response.status_code, decoded, wire, request_bytes, index, accepted_seconds

    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        mixed_rows, mixed_metrics = measured(process, lambda: list(pool.map(mixed_request, range(100))))

    connection = sqlite3.connect(DATABASE)
    placeholders = ",".join("?" for _ in USERS)
    time_state = connection.execute(
        f"SELECT COUNT(*),COALESCE(SUM(seconds),0),COALESCE(SUM(ticks),0) FROM lesson_time WHERE username IN ({placeholders})",
        USERS,
    ).fetchone()
    credit_rows = connection.execute(
        f"SELECT COUNT(*) FROM lesson_time_credit_state WHERE username IN ({placeholders})",
        USERS,
    ).fetchone()[0]
    inventory_rows = connection.execute(
        f"SELECT COUNT(*) FROM inventory_items WHERE username IN ({placeholders})",
        USERS,
    ).fetchone()[0]
    real_users = connection.execute("SELECT COUNT(*) FROM users WHERE is_test=0").fetchone()[0]
    test_users = connection.execute("SELECT COUNT(*) FROM users WHERE is_test=1").fetchone()[0]
    connection.close()
    mixed_accepted = sum(int(row[6]) for row in mixed_rows)
    assert tuple(map(int, time_state)) == (
        100,
        100 + route_time_accepted + mixed_accepted,
        100 + sum(1 for row in time_rows if int(row[6]) > 0) + sum(1 for row in mixed_rows if int(row[6]) > 0),
    ), time_state
    assert int(credit_rows) == 100 and int(inventory_rows) == 10

    leaderboard = requests.get(
        f"{BASE}/vocab/leaderboard",
        headers={"Authorization": f"Bearer {tokens[USERS[0]]}"},
        params={"limit": 500, "scope": "month", "type": "space_v"},
        timeout=30,
    )
    leaderboard.raise_for_status()
    if "codexload" in leaderboard.text.lower():
        raise RuntimeError("Load-test users leaked into the production leaderboard")

    print(json.dumps({
        "users": 100,
        "distinct_paths": len(set(paths)),
        "login": login_metrics,
        "session_start": start_metrics,
        "verified_write": {**write_metrics, "accepted_seconds": accepted},
        "route_probe": {
            "tree_35": {**tree_metrics, "cache_headers": tree_cache_headers, "prepare": tree_prepare_metrics},
            "tasks_35": task_metrics,
            "time_20": {**time_metrics, "accepted_seconds": route_time_accepted},
            "inventory_10": inventory_metrics,
        },
        "mixed_35_tree_35_tasks_20_time_10_inventory": {**mixed_metrics, "accepted_seconds": mixed_accepted},
        "sqlite": {"time_rows": time_state[0], "seconds": time_state[1], "ticks": time_state[2], "credit_rows": credit_rows, "inventory_rows": inventory_rows},
        "isolation": {"real_users": real_users, "test_users": test_users, "leaderboard_hidden": True},
        "cleanup_required": True,
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

