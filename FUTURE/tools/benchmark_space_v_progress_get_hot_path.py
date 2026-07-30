"""Benchmark Space_V progress reads for 100 users and realistic `hung` state."""

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
SERVER_DATA = Path(r"C:\server data")
USERS = tuple(f"codexload{index:03d}" for index in range(1, 101))


# Added 2026-07-20: separate multi-user scalability from one realistic large progress namespace.
def clean(value: object = "") -> str:
    return str(value or "").strip()


def server_process() -> psutil.Process:
    for connection in psutil.net_connections(kind="tcp"):
        if connection.laddr and connection.laddr.port == 8877 and connection.status == psutil.CONN_LISTEN and connection.pid:
            return psutil.Process(connection.pid)
    raise RuntimeError("Server 2 listener not found")


def cpu_seconds(process: psutil.Process) -> float:
    row = process.cpu_times()
    return float(row.user + row.system)


def lesson_paths() -> list[str]:
    rows = []
    for path in (SERVER_DATA / "common").rglob("*.Space_V"):
        try:
            if int(path.stat().st_size) < 128:
                continue
        except OSError:
            continue
        rows.append(path.relative_to(SERVER_DATA).as_posix())
        if len(rows) >= len(USERS):
            return rows
    raise RuntimeError(f"Only {len(rows)} Space_V files were found")


def hung_rows() -> list[tuple[str, str]]:
    connection = sqlite3.connect(DATABASE)
    try:
        rows = connection.execute(
            "SELECT path,identity FROM lesson_progress WHERE username='hung' AND space='Space_V' ORDER BY updated_at_utc DESC"
        ).fetchall()
    finally:
        connection.close()
    if not rows:
        raise RuntimeError("Real user hung has no Space_V progress rows")
    return [(clean(path), clean(identity)) for path, identity in rows if clean(path)]


def seed_record() -> dict:
    connection = sqlite3.connect(DATABASE)
    try:
        row = connection.execute(
            "SELECT record_json FROM lesson_progress WHERE username='hung' AND space='Space_V' ORDER BY updated_at_utc DESC LIMIT 1"
        ).fetchone()
    finally:
        connection.close()
    if not row:
        raise RuntimeError("No seed Space_V record exists")
    return json.loads(row[0])


def wait_for_writer_quiescence(timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    previous = None
    stable = 0
    while time.monotonic() < deadline:
        writer = requests.get(f"{BASE}/health", timeout=10).json().get("postgres_writer", {})
        current = (int(writer.get("tasks", 0) or 0), int(writer.get("batches", 0) or 0))
        if current == previous:
            stable += 1
            if stable >= 3:
                return
        else:
            previous = current
            stable = 0
        time.sleep(0.2)
    raise RuntimeError("SQLite writer did not become quiescent before Space_V GET measurement")


def percentile(rows: list[float], fraction: float) -> float:
    ordered = sorted(rows)
    return ordered[max(0, int(len(ordered) * fraction) - 1)]


def measured(process: psutil.Process, callback) -> tuple[list[tuple], dict]:
    writer_before = requests.get(f"{BASE}/health", timeout=10).json().get("postgres_writer", {})
    cpu_before = cpu_seconds(process)
    io_before = process.io_counters()
    started = time.perf_counter()
    rows = callback()
    wall_ms = (time.perf_counter() - started) * 1000
    cpu_ms = max(0.0, (cpu_seconds(process) - cpu_before) * 1000)
    io_after = process.io_counters()
    writer_after = requests.get(f"{BASE}/health", timeout=10).json().get("postgres_writer", {})
    latencies = [float(row[0]) for row in rows]
    return rows, {
        "requests": len(rows),
        "server_cpu_ms": round(cpu_ms, 3),
        "cpu_ms_per_request": round(cpu_ms / max(1, len(rows)), 3),
        "wall_ms": round(wall_ms, 3),
        "requests_per_second": round(len(rows) / max(0.001, wall_ms / 1000), 3),
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(percentile(latencies, 0.95), 3),
        "p99_ms": round(percentile(latencies, 0.99), 3),
        "response_bytes": sum(int(row[2]) for row in rows),
        "statuses": {str(status): sum(1 for row in rows if row[1] == status) for status in sorted({row[1] for row in rows})},
        "progress_rows": sum(1 for row in rows if row[3]),
        "process_io": {
            "read_ops": max(0, int(io_after.read_count - io_before.read_count)),
            "write_ops": max(0, int(io_after.write_count - io_before.write_count)),
            "read_bytes": max(0, int(io_after.read_bytes - io_before.read_bytes)),
            "write_bytes": max(0, int(io_after.write_bytes - io_before.write_bytes)),
        },
        "postgres_writer": {
            key: round(float(writer_after.get(key, 0) or 0) - float(writer_before.get(key, 0) or 0), 3)
            for key in ("batches", "tasks", "queue_wait_ms", "begin_wait_ms", "commit_ms", "busy_errors")
        },
    }


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this benchmark only")
    process = server_process()
    paths = lesson_paths()
    real_rows = hung_rows()
    template = seed_record()

    def login(username: str) -> str:
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        return clean(response.json().get("token"))

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        tokens = dict(zip(USERS, pool.map(login, USERS)))
    hung_token = login("hung")

    def seed(index: int) -> None:
        path = paths[index]
        record = json.loads(json.dumps(template))
        record.update({
            "action": "autosave",
            "path": path,
            "identity": f"codex-progress-get-{index:03d}",
            "title": Path(path).stem,
            "runId": f"codex-progress-get-run-{index:03d}",
            "activeRun": True,
            "savedAt": "2026-07-20T02:50:00Z",
        })
        state = record.get("state") if isinstance(record.get("state"), dict) else {}
        state.update({"savedAt": "2026-07-20T02:50:00Z", "runId": record["runId"], "activeRun": True})
        record["state"] = state
        response = requests.post(
            f"{BASE}/space-v/progress?client_source=codex_get_seed&response=compact-v1",
            headers={"Authorization": f"Bearer {tokens[USERS[index]]}"},
            json=record,
            timeout=45,
        )
        response.raise_for_status()

    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        list(pool.map(seed, range(100)))
    wait_for_writer_quiescence()

    def get_one(index: int, etag: str = "") -> tuple:
        headers = {"Authorization": f"Bearer {tokens[USERS[index]]}"}
        if etag:
            headers["If-None-Match"] = etag
        started = time.perf_counter()
        response = requests.get(
            f"{BASE}/space-v/progress",
            headers=headers,
            params={"path": paths[index], "identity": f"codex-progress-get-{index:03d}"},
            timeout=30,
        )
        latency = (time.perf_counter() - started) * 1000
        payload = response.json() if response.content else {}
        return latency, response.status_code, len(response.content), isinstance(payload.get("progress"), dict), clean(response.headers.get("ETag"))

    def get_hung(index: int, etag: str = "") -> tuple:
        path, identity = real_rows[index % len(real_rows)]
        headers = {"Authorization": f"Bearer {hung_token}"}
        if etag:
            headers["If-None-Match"] = etag
        started = time.perf_counter()
        response = requests.get(
            f"{BASE}/space-v/progress",
            headers=headers,
            params={"path": path, "identity": identity},
            timeout=30,
        )
        latency = (time.perf_counter() - started) * 1000
        payload = response.json() if response.content else {}
        return latency, response.status_code, len(response.content), isinstance(payload.get("progress"), dict), clean(response.headers.get("ETag"))

    phases = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        _, phases["distinct_users_first"] = measured(process, lambda: list(pool.map(get_one, range(100))))
        distinct_warm_rows, phases["distinct_users_warm"] = measured(process, lambda: list(pool.map(get_one, range(100))))
        distinct_etags = [row[4] for row in distinct_warm_rows]
        _, phases["distinct_users_conditional"] = measured(
            process,
            lambda: list(pool.map(lambda index: get_one(index, distinct_etags[index]), range(100))),
        )
        hung_rows_result, phases["hung_realistic"] = measured(process, lambda: list(pool.map(get_hung, range(100))))
        hung_etags = [row[4] for row in hung_rows_result]
        hung_conditional, phases["hung_conditional"] = measured(
            process,
            lambda: list(pool.map(lambda index: get_hung(index, hung_etags[index]), range(100))),
        )
    if any(row[1] != 304 for row in hung_conditional):
        raise RuntimeError("One or more real hung conditional progress reads did not return 304")
    print(json.dumps({"space_v_progress_get_hot_path": phases}, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

