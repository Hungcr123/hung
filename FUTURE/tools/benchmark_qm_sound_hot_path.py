"""Benchmark `/server-data/qm-sound` with 100 distinct authenticated users."""

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
QMLEARN_DATA = Path(r"C:\QMLearn\Data")
USERS = tuple(f"codexload{index:03d}" for index in range(1, 101))


# Added 2026-07-20: measure the real shared audio route without mutating lesson state.
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


def audio_paths() -> list[str]:
    rows = []
    for path in QMLEARN_DATA.rglob("*.mp3"):
        try:
            size = int(path.stat().st_size)
        except OSError:
            continue
        if size < 2_048 or size > 512 * 1_024:
            continue
        rows.append(path.relative_to(QMLEARN_DATA).as_posix())
        if len(rows) >= len(USERS):
            return rows
    raise RuntimeError(f"Only {len(rows)} usable QMLearn audio files were found")


def audio_words() -> list[str]:
    rows = []
    for path in sorted(QMLEARN_DATA.glob("*_en-GB.mp3"), key=lambda item: item.name.lower())[1_000:]:
        word = path.name[: -len("_en-GB.mp3")]
        if word:
            rows.append(word)
        if len(rows) >= len(USERS):
            return rows
    raise RuntimeError(f"Only {len(rows)} usable QMLearn word-audio files were found")


def response_sizes(response: requests.Response) -> tuple[int, int]:
    decoded = len(response.content)
    return decoded, int(response.headers.get("Content-Length") or decoded)


def percentile(rows: list[float], fraction: float) -> float:
    ordered = sorted(rows)
    return ordered[max(0, int(len(ordered) * fraction) - 1)]


# Added 2026-07-20: isolate audio reads from delayed auth/session group commits.
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
    raise RuntimeError("SQLite writer did not become quiescent before qm-sound measurement")


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
        "decoded_response_bytes": sum(int(row[2]) for row in rows),
        "wire_response_bytes": sum(int(row[3]) for row in rows),
        "statuses": {str(status): sum(1 for row in rows if row[1] == status) for status in sorted({row[1] for row in rows})},
        "etag_responses": sum(1 for row in rows if clean(row[4])),
        "cache_controls": sorted({clean(row[5]) for row in rows if clean(row[5])}),
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
    paths = audio_paths()
    words = audio_words()

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

    def request_one(index: int, *, shared: bool = False, range_request: bool = False, word_request: bool = False) -> tuple:
        path = paths[0] if shared else paths[index]
        headers = {"Authorization": f"Bearer {tokens[USERS[index]]}"}
        if range_request:
            headers["Range"] = "bytes=0-4095"
        if word_request:
            target_url = f"{BASE}/server-data/qm-sound?word={quote(words[index], safe='')}&voice=sot%3Aen-GB"
        else:
            target_url = f"{BASE}/server-data/qm-sound?path={quote(path, safe='')}"
        started = time.perf_counter()
        response = requests.get(
            target_url,
            headers=headers,
            timeout=30,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        decoded, wire = response_sizes(response)
        return (
            latency_ms,
            response.status_code,
            decoded,
            wire,
            clean(response.headers.get("ETag")),
            clean(response.headers.get("Cache-Control")),
        )

    phases = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        _, phases["word_first"] = measured(process, lambda: list(pool.map(lambda index: request_one(index, word_request=True), range(100))))
        _, phases["word_warm"] = measured(process, lambda: list(pool.map(lambda index: request_one(index, word_request=True), range(100))))
        _, phases["distributed_first"] = measured(process, lambda: list(pool.map(request_one, range(100))))
        _, phases["distributed_warm"] = measured(process, lambda: list(pool.map(request_one, range(100))))
        _, phases["shared_warm"] = measured(process, lambda: list(pool.map(lambda index: request_one(index, shared=True), range(100))))
        range_rows, phases["distributed_range"] = measured(
            process,
            lambda: list(pool.map(lambda index: request_one(index, range_request=True), range(100))),
        )
    if any(row[1] != 206 for row in range_rows):
        raise RuntimeError("One or more qm-sound range requests did not return HTTP 206")
    print(json.dumps({"qm_sound_hot_path": phases}, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

