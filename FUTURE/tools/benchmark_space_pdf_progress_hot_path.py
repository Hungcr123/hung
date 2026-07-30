"""Benchmark distributed Space_PDF progress create/update/retry/pin behavior."""

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
MANIFEST = Path(r"C:\server data\_future_server_data_manifest.json")
USERS = tuple(f"codexload{index:03d}" for index in range(1, 101))
IDENTITY_PREFIX = "pdf-progress-hot-v1-"


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


def database_state() -> dict:
    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute(
            "SELECT COUNT(*),COALESCE(SUM(server_revision),0) FROM lesson_progress "
            "WHERE space='Space_PDF' AND username LIKE 'codexload%' AND identity LIKE ?",
            (f"{IDENTITY_PREFIX}%",),
        ).fetchone()
    return {"rows": int(row[0]), "revision_sum": int(row[1])}


def writer_metrics() -> dict:
    return requests.get(f"{BASE}/health", timeout=15).json().get("postgres_writer", {})


def metric_delta(before: dict, after: dict) -> dict:
    return {
        key: round(float(after.get(key, 0) or 0) - float(before.get(key, 0) or 0), 3)
        for key in ("batches", "tasks", "queue_wait_ms", "begin_wait_ms", "commit_ms", "busy_errors")
    }


def payload_for(index: int, path: str, phase: str) -> dict:
    base_page = 2 + index % 30
    stamp_by_phase = {
        "create": "2026-07-21T01:00:00Z",
        "retry": "2026-07-21T01:00:00Z",
        "update": "2026-07-21T01:10:00Z",
        "pin": "2026-07-21T01:20:00Z",
        "reconnect_retry": "2026-07-21T01:20:00Z",
        "stale": "2026-07-21T01:05:00Z",
    }
    page = base_page + (1 if phase in {"update", "pin", "reconnect_retry"} else 0)
    payload = {
        "path": path,
        "identity": f"{IDENTITY_PREFIX}{index:03d}",
        "title": f"PDF progress hot path {index:03d}",
        "mode": "pdf",
        "page": page,
        "pages": 120,
        "savedAt": stamp_by_phase[phase],
        "recentPages": [page, base_page],
        "state": {"page": page, "pages": 120, "recentPages": [page, base_page]},
    }
    if phase in {"pin", "reconnect_retry"}:
        payload.update({
            "pinOnly": True,
            "pinnedPages": [base_page, page],
            "pinnedPagesUpdatedAt": stamp_by_phase[phase],
        })
        payload["state"].update({
            "pinnedPages": payload["pinnedPages"],
            "pinnedPagesUpdatedAt": stamp_by_phase[phase],
        })
    return payload


def main() -> int:
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

    results = {}
    for phase in ("create", "retry", "update", "pin", "reconnect_retry", "stale"):
        before_state = database_state()
        before_writer = writer_metrics()
        before_cpu = sum(process.cpu_times()[:2])
        before_io = process.io_counters()
        wal_path = Path(str(DATABASE) + "-wal")
        before_wal = wal_path.stat().st_size if wal_path.exists() else 0

        def request(index: int) -> dict:
            payload = payload_for(index, pdfs[index], phase)
            source = "pdf_pin_save" if phase in {"pin", "reconnect_retry"} else f"pdf_progress_hot_{phase}"
            started = time.perf_counter()
            response = sessions[index].post(
                f"{BASE}/space-pdf/progress?client_source={source}", json=payload, timeout=45,
            )
            return {
                "status": response.status_code,
                "latency_ms": (time.perf_counter() - started) * 1000,
                "request_bytes": len(response.request.body or b""),
                "response_bytes": len(response.content),
            }

        started = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            rows = list(pool.map(request, range(100)))
        wall = time.perf_counter() - started
        after_cpu = sum(process.cpu_times()[:2])
        after_io = process.io_counters()
        after_writer = writer_metrics()
        after_state = database_state()
        after_wal = wal_path.stat().st_size if wal_path.exists() else 0
        latencies = [row["latency_ms"] for row in rows]
        results[phase] = {
            "requests": len(rows),
            "statuses": {str(status): sum(1 for row in rows if row["status"] == status) for status in sorted({row["status"] for row in rows})},
            "wall_ms": round(wall * 1000, 3),
            "requests_per_second": round(len(rows) / max(wall, 0.001), 3),
            "server_cpu_ms_per_request": round((after_cpu - before_cpu) * 1000 / len(rows), 3),
            "p50_ms": round(statistics.median(latencies), 3),
            "p95_ms": round(percentile(latencies, 0.95), 3),
            "p99_ms": round(percentile(latencies, 0.99), 3),
            "request_bytes": sum(row["request_bytes"] for row in rows),
            "response_bytes": sum(row["response_bytes"] for row in rows),
            "process_read_bytes": max(0, after_io.read_bytes - before_io.read_bytes),
            "process_write_bytes": max(0, after_io.write_bytes - before_io.write_bytes),
            "wal_size_delta": after_wal - before_wal,
            "writer": metric_delta(before_writer, after_writer),
            "row_delta": after_state["rows"] - before_state["rows"],
            "revision_delta": after_state["revision_sum"] - before_state["revision_sum"],
        }
        time.sleep(0.5)

    print(json.dumps({"users": 100, "identities": 100, "results": results, "cleanup_required": True}, separators=(",", ":")))
    return 0 if all(phase["statuses"] == {"200": 100} for phase in results.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())

