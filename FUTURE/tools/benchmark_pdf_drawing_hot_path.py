"""Benchmark 100 distinct users reading, writing, and retrying PDF drawing rows."""

from __future__ import annotations

import concurrent.futures
import json
import os
import statistics
import time
from datetime import datetime, timezone
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


def pdf_paths() -> list[str]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = sorted({
        str(entry.get("path", "")).strip()
        for entries in (payload.get("folders") or {}).values()
        for entry in entries if isinstance(entries, list) and isinstance(entry, dict)
        if str(entry.get("type", "")).lower() == "file"
        and str(entry.get("path", "")).lower().startswith("common/")
        and str(entry.get("path", "")).lower().endswith(".pdf")
    }, key=str.lower)
    if len(rows) < len(USERS):
        raise RuntimeError(f"Need 100 distinct common PDFs, found {len(rows)}")
    return rows[:len(USERS)]


def response_sizes(response: requests.Response) -> tuple[int, int, int]:
    decoded = len(response.content)
    wire = int(response.headers.get("Content-Length") or decoded)
    body = response.request.body
    request_bytes = len(body) if isinstance(body, bytes) else len(str(body or "").encode("utf-8"))
    return decoded, wire, request_bytes


def measured(process: psutil.Process, callback) -> tuple[list[tuple], dict]:
    before_cpu = sum(process.cpu_times()[:2])
    before_io = process.io_counters()
    before_wal = Path(str(DATABASE) + "-wal").stat().st_size if Path(str(DATABASE) + "-wal").exists() else 0
    started = time.perf_counter()
    rows = callback()
    wall_ms = (time.perf_counter() - started) * 1000
    after_cpu = sum(process.cpu_times()[:2])
    after_io = process.io_counters()
    after_wal = Path(str(DATABASE) + "-wal").stat().st_size if Path(str(DATABASE) + "-wal").exists() else 0
    latencies = sorted(row[0] for row in rows)
    count = max(1, len(rows))
    cpu_ms = max(0.0, (after_cpu - before_cpu) * 1000)
    return rows, {
        "requests": len(rows),
        "server_cpu_ms": round(cpu_ms, 3),
        "cpu_ms_per_request": round(cpu_ms / count, 3),
        "wall_ms": round(wall_ms, 3),
        "requests_per_second": round(len(rows) / max(0.001, wall_ms / 1000), 3),
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(latencies[max(0, int(len(latencies) * 0.95) - 1)], 3),
        "p99_ms": round(latencies[max(0, int(len(latencies) * 0.99) - 1)], 3),
        "decoded_response_bytes": sum(row[2] for row in rows),
        "wire_response_bytes": sum(row[3] for row in rows),
        "request_body_bytes": sum(row[4] for row in rows),
        "process_io": {
            "read_ops": max(0, after_io.read_count - before_io.read_count),
            "write_ops": max(0, after_io.write_count - before_io.write_count),
            "read_bytes": max(0, after_io.read_bytes - before_io.read_bytes),
            "write_bytes": max(0, after_io.write_bytes - before_io.write_bytes),
        },
        "wal_size_delta": after_wal - before_wal,
        "statuses": {status: sum(1 for row in rows if row[1] == status) for status in sorted({row[1] for row in rows})},
    }


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active benchmark only")
    paths = pdf_paths()
    process = server_process()

    def login(username: str) -> tuple:
        started = time.perf_counter()
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        decoded, wire, request_bytes = response_sizes(response)
        return (time.perf_counter() - started) * 1000, response.status_code, decoded, wire, request_bytes, response.json()["token"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        login_rows, login_metrics = measured(process, lambda: list(pool.map(login, USERS)))
    tokens = {username: row[5] for username, row in zip(USERS, login_rows)}
    updated_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    payloads = []
    for index, (username, path) in enumerate(zip(USERS, paths), 1):
        payloads.append({
            "path": path,
            "identity": f"pdf-drawing-load-{index:03d}",
            "title": f"Drawing load {index:03d}",
            "mode": "pdf",
            "page": 1 + (index % 5),
            "clientUpdatedAt": updated_at,
            "vector": {
                "version": 2,
                "width": 10000,
                "height": 10000,
                "items": [{
                    "kind": "pen",
                    "color": "#f25f3a",
                    "width": 18,
                    "points": [{"x": 100 + index, "y": 200}, {"x": 300 + index, "y": 420}],
                }],
            },
        })

    def request_one(index: int, method: str) -> tuple:
        username = USERS[index]
        headers = {"Authorization": f"Bearer {tokens[username]}"}
        started = time.perf_counter()
        if method == "read":
            source = payloads[index]
            response = requests.get(
                f"{BASE}/space-pdf/drawing",
                headers=headers,
                params={"path": source["path"], "identity": source["identity"], "page": source["page"]},
                timeout=60,
            )
        else:
            response = requests.post(f"{BASE}/space-pdf/drawing", headers=headers, json=payloads[index], timeout=120)
        response.raise_for_status()
        decoded, wire, request_bytes = response_sizes(response)
        drawing = response.json().get("drawing") or {}
        return (time.perf_counter() - started) * 1000, response.status_code, decoded, wire, request_bytes, len((drawing.get("vector") or {}).get("items") or [])

    def run_phase(method: str, workers: int = 25):
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            return list(pool.map(lambda index: request_one(index, method), range(len(USERS))))

    cold_rows, cold_metrics = measured(process, lambda: run_phase("read", 30))
    write_rows, write_metrics = measured(process, lambda: run_phase("write", 25))
    retry_rows, retry_metrics = measured(process, lambda: run_phase("write", 25))
    warm_rows, warm_metrics = measured(process, lambda: run_phase("read", 30))
    if any(row[5] != 0 for row in cold_rows):
        raise RuntimeError("Cold drawing reads unexpectedly found synthetic state")
    if any(row[5] != 1 for row in write_rows + retry_rows + warm_rows):
        raise RuntimeError("Drawing write/retry was not idempotent")
    print({
        "users": len(USERS),
        "distinct_pdfs": len(set(paths)),
        "login": login_metrics,
        "cold_read": cold_metrics,
        "write": write_metrics,
        "retry_same_timestamp_payload": retry_metrics,
        "warm_read": warm_metrics,
        "cleanup_required": True,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
