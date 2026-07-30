"""Benchmark 100 distributed authenticated Space_PDF progress reads."""

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
DATABASE = Path(r"C:\server data\server2.db")
MANIFEST = Path(r"C:\server data\_future_server_data_manifest.json")
USERS = tuple(f"codexload{index:03d}" for index in range(1, 101))
IDENTITY_PREFIX = "pdf-progress-get-hot-v1-"


def percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, int(len(ordered) * ratio) - 1)] if ordered else 0.0


def server_process() -> psutil.Process:
    for connection in psutil.net_connections(kind="tcp"):
        if connection.laddr and connection.laddr.port == 8877 and connection.status == psutil.CONN_LISTEN and connection.pid:
            return psutil.Process(connection.pid)
    raise RuntimeError("Server 2 listener not found")


def load_pdfs() -> list[str]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files = sorted({
        str(entry.get("path", "")).strip()
        for entries in (payload.get("folders") or {}).values()
        for entry in entries if isinstance(entries, list) and isinstance(entry, dict)
        if str(entry.get("type", "")).lower() == "file"
        and str(entry.get("path", "")).lower().startswith("common/")
        and str(entry.get("path", "")).lower().endswith(".pdf")
    }, key=str.lower)
    if len(files) < 100:
        raise RuntimeError(f"Need 100 distributed PDFs, found {len(files)}")
    return files[:100]


def writer_metrics() -> dict:
    return requests.get(f"{BASE}/health", timeout=15).json().get("sqlite_writer", {})


def metric_delta(before: dict, after: dict) -> dict:
    return {
        key: round(float(after.get(key, 0) or 0) - float(before.get(key, 0) or 0), 3)
        for key in ("batches", "tasks", "queue_wait_ms", "begin_wait_ms", "commit_ms", "busy_errors")
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-only", action="store_true")
    parser.add_argument("--label", default="space_pdf_progress_get")
    args = parser.parse_args()
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active benchmark only")
    pdfs = load_pdfs()
    process = server_process()

    def login(index: int) -> tuple[int, requests.Session]:
        session = requests.Session()
        response = session.post(f"{BASE}/auth/login", json={"username": USERS[index], "password": password}, timeout=30)
        response.raise_for_status()
        session.headers.update({"Authorization": f"Bearer {response.json()['token']}"})
        return index, session

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        sessions = dict(pool.map(login, range(100)))

    if args.seed_only:
        def seed(index: int) -> int:
            page = 2 + index % 30
            response = sessions[index].post(
                f"{BASE}/space-pdf/progress?client_source=pdf_progress_get_seed",
                json={
                    "path": pdfs[index],
                    "identity": f"{IDENTITY_PREFIX}{index:03d}",
                    "title": f"PDF progress GET {index:03d}",
                    "page": page,
                    "pages": 120,
                    "savedAt": "2026-07-21T02:00:00Z",
                    "state": {"page": page, "pages": 120},
                },
                timeout=45,
            )
            return response.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            statuses = list(pool.map(seed, range(100)))
        print(json.dumps({"seeded": len(statuses), "statuses": {str(code): statuses.count(code) for code in sorted(set(statuses))}}))
        return 0 if statuses == [200] * 100 else 2

    results = {}
    for phase in ("cold", "warm", "settled"):
        before_writer = writer_metrics()
        before_cpu = sum(process.cpu_times()[:2])
        before_io = process.io_counters()

        def read(index: int) -> dict:
            started = time.perf_counter()
            response = sessions[index].get(
                f"{BASE}/space-pdf/progress",
                params={"path": pdfs[index], "identity": f"{IDENTITY_PREFIX}{index:03d}"},
                timeout=45,
            )
            payload = response.json() if response.content else {}
            progress = payload.get("progress") if isinstance(payload, dict) else None
            return {
                "status": response.status_code,
                "latency_ms": (time.perf_counter() - started) * 1000,
                "response_bytes": len(response.content),
                "found": isinstance(progress, dict),
            }

        started = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            rows = list(pool.map(read, range(100)))
        wall = time.perf_counter() - started
        after_cpu = sum(process.cpu_times()[:2])
        after_io = process.io_counters()
        after_writer = writer_metrics()
        latencies = [row["latency_ms"] for row in rows]
        results[phase] = {
            "requests": len(rows),
            "statuses": {str(code): sum(1 for row in rows if row["status"] == code) for code in sorted({row["status"] for row in rows})},
            "found": sum(1 for row in rows if row["found"]),
            "wall_ms": round(wall * 1000, 3),
            "requests_per_second": round(len(rows) / max(wall, 0.001), 3),
            "server_cpu_ms_per_request": round((after_cpu - before_cpu) * 1000 / len(rows), 3),
            "p50_ms": round(statistics.median(latencies), 3),
            "p95_ms": round(percentile(latencies, 0.95), 3),
            "p99_ms": round(percentile(latencies, 0.99), 3),
            "response_bytes": sum(row["response_bytes"] for row in rows),
            "process_read_bytes": max(0, after_io.read_bytes - before_io.read_bytes),
            "process_write_bytes": max(0, after_io.write_bytes - before_io.write_bytes),
            "writer": metric_delta(before_writer, after_writer),
        }
        time.sleep(0.4)

    print(json.dumps({"label": args.label, "users": 100, "identities": 100, "results": results, "cleanup_required": True}, separators=(",", ":")))
    return 0 if all(row["statuses"] == {"200": 100} and row["found"] == 100 for row in results.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
