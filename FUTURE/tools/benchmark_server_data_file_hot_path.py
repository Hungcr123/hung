"""Benchmark authenticated `/server-data/file` delivery for 100 distinct learners."""

from __future__ import annotations

import concurrent.futures
import json
import os
import statistics
import time
from pathlib import Path
from urllib.parse import quote

import psutil
import requests


BASE = "http://127.0.0.1:8877"
SERVER_DATA = Path(r"C:\server data")
USERS = tuple(f"codexload{index:03d}" for index in range(1, 101))
EXTENSIONS = (".Space_V", ".Space_W", ".Space_Q", ".Space_P", ".Space_S", ".Space_L")


# Added 2026-07-20: measure full-byte and conditional lesson loads without changing progress.
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


def lesson_paths() -> tuple[list[str], str]:
    grouped: dict[str, list[Path]] = {extension.lower(): [] for extension in EXTENSIONS}
    for path in (SERVER_DATA / "common").rglob("*"):
        suffix = path.suffix.lower()
        if suffix not in grouped:
            continue
        try:
            size = int(path.stat().st_size)
        except OSError:
            continue
        if 128 <= size <= 2 * 1024 * 1024:
            grouped[suffix].append(path)
    rows = []
    offsets = {key: 0 for key in grouped}
    keys = tuple(grouped)
    while len(rows) < len(USERS):
        changed = False
        for key in keys:
            index = offsets[key]
            if index >= len(grouped[key]):
                continue
            path = grouped[key][index]
            offsets[key] += 1
            rows.append(path.relative_to(SERVER_DATA).as_posix())
            changed = True
            if len(rows) >= len(USERS):
                used = {value.lower() for value in rows}
                shared_cold = next(
                    (item.relative_to(SERVER_DATA).as_posix() for item in grouped[".space_v"] if item.relative_to(SERVER_DATA).as_posix().lower() not in used),
                    "",
                )
                if not shared_cold:
                    raise RuntimeError("No reserved cold Space_V path was found")
                return rows, shared_cold
        if not changed:
            break
    raise RuntimeError(f"Only {len(rows)} suitable lesson files were found")


def wait_for_writer_quiescence(timeout: float = 8.0) -> None:
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
    raise RuntimeError("SQLite writer did not become quiescent before file-route measurement")


def percentile(rows: list[float], fraction: float) -> float:
    ordered = sorted(rows)
    return ordered[max(0, int(len(ordered) * fraction) - 1)]


def server_timing_values(value: str) -> dict[str, float]:
    out = {}
    for item in clean(value).split(","):
        parts = [part.strip() for part in item.split(";") if part.strip()]
        if not parts:
            continue
        duration = next((part[4:] for part in parts[1:] if part.startswith("dur=")), "")
        try:
            out[parts[0]] = float(duration)
        except (TypeError, ValueError):
            continue
    return out


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
    ttfb_latencies = [float(row[6]) for row in rows]
    timing_rows = [server_timing_values(row[7]) for row in rows if len(row) > 7 and row[7]]
    # Added 2026-07-21: attribute cold/warm tails to the lesson format instead of averaging unlike routes.
    by_extension = {}
    for extension in sorted({Path(str(row[5])).suffix.lower() for row in rows if len(row) > 5 and row[5]}):
        subset = [row for row in rows if Path(str(row[5])).suffix.lower() == extension]
        subset_latencies = [float(row[0]) for row in subset]
        by_extension[extension] = {
            "requests": len(subset),
            "p50_ms": round(statistics.median(subset_latencies), 3),
            "p95_ms": round(percentile(subset_latencies, 0.95), 3),
            "p99_ms": round(percentile(subset_latencies, 0.99), 3),
            "ttfb_p50_ms": round(statistics.median(float(row[6]) for row in subset), 3),
            "download_gap_p95_ms": round(percentile([max(0.0, float(row[0]) - float(row[6])) for row in subset], 0.95), 3),
            "decoded_response_bytes": sum(int(row[2]) for row in subset),
            "wire_response_bytes": sum(int(row[3]) for row in subset),
        }
    return rows, {
        "requests": len(rows),
        "server_cpu_ms": round(cpu_ms, 3),
        "cpu_ms_per_request": round(cpu_ms / max(1, len(rows)), 3),
        "wall_ms": round(wall_ms, 3),
        "requests_per_second": round(len(rows) / max(0.001, wall_ms / 1000), 3),
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(percentile(latencies, 0.95), 3),
        "p99_ms": round(percentile(latencies, 0.99), 3),
        "ttfb_p50_ms": round(statistics.median(ttfb_latencies), 3),
        "ttfb_p95_ms": round(percentile(ttfb_latencies, 0.95), 3),
        "download_gap_p95_ms": round(percentile([max(0.0, float(row[0]) - float(row[6])) for row in rows], 0.95), 3),
        "decoded_response_bytes": sum(int(row[2]) for row in rows),
        "wire_response_bytes": sum(int(row[3]) for row in rows),
        "statuses": {str(status): sum(1 for row in rows if row[1] == status) for status in sorted({row[1] for row in rows})},
        "etags": sum(1 for row in rows if clean(row[4])),
        "cache_hits": {value: sum(1 for row in rows if clean(row[8]) == value) for value in sorted({clean(row[8]) for row in rows if len(row) > 8 and clean(row[8])})},
        "server_timing_avg_ms": {
            name: round(statistics.mean(row[name] for row in timing_rows if name in row), 3)
            for name in sorted({name for row in timing_rows for name in row})
        },
        "by_extension": by_extension,
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
    paths, shared_cold_path = lesson_paths()

    def login(username: str) -> str:
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if payload.get("server_data", {}).get("load_test") is not True:
            raise RuntimeError(f"Load-test isolation missing for {username}")
        token = clean(payload.get("token"))
        if not token:
            raise RuntimeError(f"Missing token for {username}")
        return token

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        tokens = dict(zip(USERS, pool.map(login, USERS)))
    wait_for_writer_quiescence()

    def request_one(index: int, *, shared: bool = False, etag: str = "", override_path: str = "", slow_read: bool = False) -> tuple:
        path = override_path or (paths[0] if shared else paths[index])
        headers = {"Authorization": f"Bearer {tokens[USERS[index]]}"}
        if etag:
            headers["If-None-Match"] = etag
        started = time.perf_counter()
        response = requests.get(
            f"{BASE}/server-data/file?path={quote(path, safe='')}",
            headers=headers,
            timeout=45,
            stream=True,
        )
        ttfb_ms = (time.perf_counter() - started) * 1000
        if slow_read:
            decoded = 0
            for chunk in response.iter_content(chunk_size=128):
                decoded += len(chunk)
                time.sleep(0.002)
        else:
            decoded = len(response.content)
        latency_ms = (time.perf_counter() - started) * 1000
        wire = int(response.headers.get("Content-Length") or decoded)
        return (
            latency_ms,
            response.status_code,
            decoded,
            wire,
            clean(response.headers.get("ETag")),
            path,
            ttfb_ms,
            clean(response.headers.get("Server-Timing")),
            clean(response.headers.get("X-Future-Cache-Hit")),
        )

    phases = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        _, phases["shared_cold_space_v"] = measured(
            process,
            lambda: list(pool.map(lambda index: request_one(index, override_path=shared_cold_path), range(100))),
        )
        first_rows, phases["distributed_first"] = measured(process, lambda: list(pool.map(request_one, range(100))))
        warm_rows, phases["distributed_warm"] = measured(process, lambda: list(pool.map(request_one, range(100))))
        etags = [clean(row[4]) for row in warm_rows]
        conditional_rows, phases["distributed_conditional"] = measured(
            process,
            lambda: list(pool.map(lambda index: request_one(index, etag=etags[index]), range(100))),
        )
        _, phases["shared_warm"] = measured(process, lambda: list(pool.map(lambda index: request_one(index, shared=True), range(100))))
        _, phases["shared_slow_client"] = measured(
            process,
            lambda: list(pool.map(lambda index: request_one(index, shared=True, slow_read=True), range(20))),
        )
    if any(row[1] != 200 for row in first_rows + warm_rows):
        raise RuntimeError("One or more full lesson requests failed")
    if any(row[1] != 304 for row in conditional_rows):
        raise RuntimeError("One or more conditional lesson requests did not return HTTP 304")
    print(json.dumps({"server_data_file_hot_path": phases}, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

