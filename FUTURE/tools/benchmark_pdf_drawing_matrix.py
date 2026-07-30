"""Benchmark isolated PDF drawing create/update/retry/contention/clear/load paths."""

from __future__ import annotations

import concurrent.futures
import json
import os
import sqlite3
import statistics
import time
from datetime import datetime, timedelta, timezone
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


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, int(len(ordered) * fraction) - 1))] if ordered else 0.0


def measured(process: psutil.Process, callback) -> tuple[list[dict], dict]:
    writer_before = requests.get(f"{BASE}/health", timeout=10).json().get("sqlite_writer", {})
    before_cpu = sum(process.cpu_times()[:2])
    before_io = process.io_counters()
    wal_path = Path(str(DATABASE) + "-wal")
    before_wal = wal_path.stat().st_size if wal_path.exists() else 0
    started = time.perf_counter()
    rows = callback()
    wall_ms = (time.perf_counter() - started) * 1000
    after_cpu = sum(process.cpu_times()[:2])
    after_io = process.io_counters()
    writer_after = requests.get(f"{BASE}/health", timeout=10).json().get("sqlite_writer", {})
    after_wal = wal_path.stat().st_size if wal_path.exists() else 0
    latencies = [float(row.get("latency_ms", 0.0)) for row in rows]
    cpu_ms = max(0.0, (after_cpu - before_cpu) * 1000)
    count = max(1, len(rows))
    return rows, {
        "requests": len(rows),
        "server_cpu_ms": round(cpu_ms, 3),
        "cpu_ms_per_request": round(cpu_ms / count, 3),
        "wall_ms": round(wall_ms, 3),
        "requests_per_second": round(len(rows) / max(0.001, wall_ms / 1000), 3),
        "p50_ms": round(statistics.median(latencies), 3) if latencies else 0,
        "p95_ms": round(percentile(latencies, 0.95), 3),
        "p99_ms": round(percentile(latencies, 0.99), 3),
        "request_body_bytes": sum(int(row.get("request_bytes", 0)) for row in rows),
        "response_bytes": sum(int(row.get("response_bytes", 0)) for row in rows),
        "wal_size_delta": after_wal - before_wal,
        "sqlite_busy_or_lock_errors": sum(1 for row in rows if row.get("status") in {409, 423, 429, 500, 503} or "lock" in str(row.get("error", "")).lower()),
        "sqlite_writer": {
            key: round(float(writer_after.get(key, 0) or 0) - float(writer_before.get(key, 0) or 0), 3)
            for key in ("batches", "tasks", "queue_wait_ms", "begin_wait_ms", "commit_ms", "busy_errors")
        },
        "process_io": {
            "read_ops": max(0, after_io.read_count - before_io.read_count),
            "write_ops": max(0, after_io.write_count - before_io.write_count),
            "read_bytes": max(0, after_io.read_bytes - before_io.read_bytes),
            "write_bytes": max(0, after_io.write_bytes - before_io.write_bytes),
        },
    }


def vector(index: int, item_count: int, version: int = 1) -> dict:
    return {
        "version": 2,
        "width": 10000,
        "height": 10000,
        "items": [
            {
                "kind": "pen",
                "color": f"#{(index * 7919 + item * 97) % 0xFFFFFF:06x}",
                "width": 8 + (item % 24),
                "points": [
                    {"x": 100 + index + item * 3, "y": 200 + version * 7},
                    {"x": 300 + index + item * 5, "y": 420 + version * 11},
                ],
            }
            for item in range(item_count)
        ],
    }


def row_counts() -> dict:
    with sqlite3.connect(DATABASE) as connection:
        row_count, revision_sum, deleted = connection.execute(
            "SELECT COUNT(*),COALESCE(SUM(server_revision),0),COALESCE(SUM(deleted),0) FROM pdf_drawings WHERE username LIKE 'codexload%'"
        ).fetchone()
    return {"rows": int(row_count), "revision_sum": int(revision_sum), "deleted_rows": int(deleted)}


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active benchmark only")
    paths = pdf_paths()
    process = server_process()

    def login(username: str) -> tuple[str, str]:
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        return username, response.json()["token"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        tokens = dict(pool.map(login, USERS))
    base_time = datetime.now(timezone.utc).replace(microsecond=0)
    size_labels = tuple("small" if index < 34 else "medium" if index < 67 else "large" for index in range(100))
    size_items = {"small": 1, "medium": 12, "large": 60}

    def payload(index: int, phase: str, stamp: datetime, *, action: str = "", operation_id: str = "") -> dict:
        label = size_labels[index]
        source = {
            "path": paths[index],
            "identity": f"drawing-matrix-{index:03d}",
            "title": f"Drawing matrix {index:03d}",
            "mode": "pdf",
            "page": 1 + (index % 7),
            "clientUpdatedAt": stamp.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "operationId": operation_id or f"matrix-{phase}-{index:03d}",
        }
        if action:
            source["action"] = action
        else:
            source["vector"] = vector(index, size_items[label], 2 if phase == "update" else 1)
        return source

    def request(index: int, method: str, source: dict | None = None, token: str = "") -> dict:
        headers = {"Authorization": f"Bearer {token or tokens[USERS[index]]}", "Content-Type": "application/json"}
        started = time.perf_counter()
        try:
            if method == "GET":
                body = source or {}
                response = requests.get(
                    f"{BASE}/space-pdf/drawing",
                    headers=headers,
                    params={"path": body["path"], "identity": body["identity"], "page": body["page"]},
                    timeout=120,
                )
                request_bytes = 0
            else:
                body = source or {}
                encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                request_bytes = len(encoded)
                response = requests.post(f"{BASE}/space-pdf/drawing", headers=headers, data=encoded, timeout=120)
            result = response.json() if response.content else {}
            drawing = result.get("drawing") or {}
            return {
                "latency_ms": (time.perf_counter() - started) * 1000,
                "status": response.status_code,
                "request_bytes": request_bytes,
                "response_bytes": len(response.content),
                "revision": int(drawing.get("serverRevision", 0) or 0),
                "items": len((drawing.get("vector") or {}).get("items") or []),
                "deleted": bool(drawing.get("deleted")),
                "stale": bool(drawing.get("stale")),
                "conflict": bool(drawing.get("conflict")),
                "operation_id": str(drawing.get("operationId", "")),
                "error": str(result.get("error", "")),
                "size": size_labels[index],
            }
        except Exception as exc:
            return {"latency_ms": (time.perf_counter() - started) * 1000, "status": 0, "error": str(exc), "request_bytes": 0, "response_bytes": 0, "size": size_labels[index]}

    def parallel(rows, workers: int = 25):
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            return list(pool.map(lambda args: request(*args), rows))

    creates = [payload(index, "create", base_time, operation_id=f"matrix-create-{index:03d}") for index in range(100)]
    for source in creates:
        source["baseRevision"] = 0
    create_rows, create_metrics = measured(process, lambda: parallel([(index, "POST", creates[index], "") for index in range(100)], 25))
    create_state = row_counts()
    assert all(row.get("status") == 200 and row.get("revision") == 1 for row in create_rows), create_rows[:5]
    assert create_state["rows"] == 100 and create_state["revision_sum"] == 100, create_state

    retry_rows, retry_metrics = measured(process, lambda: parallel([(index, "POST", creates[index], "") for index in range(100)], 25))
    retry_state = row_counts()
    assert retry_state == create_state and all(row.get("revision") == 1 for row in retry_rows), (create_state, retry_state)

    updates = [payload(index, "update", base_time + timedelta(seconds=1), operation_id=f"matrix-update-{index:03d}") for index in range(100)]
    for source in updates:
        source["baseRevision"] = 1
    update_rows, update_metrics = measured(process, lambda: parallel([(index, "POST", updates[index], "") for index in range(100)], 25))
    update_state = row_counts()
    assert update_state["rows"] == 100 and update_state["revision_sum"] == 200, update_state

    load_rows, load_metrics = measured(process, lambda: parallel([(index, "GET", updates[index], "") for index in range(100)], 30))
    assert all(row.get("status") == 200 and row.get("revision") == 2 for row in load_rows), load_rows[:5]

    contention_index = 0
    contention_payloads = []
    for offset in range(10):
        source = payload(contention_index, "contention", base_time + timedelta(seconds=2), operation_id=f"matrix-contention-{offset:02d}")
        source["baseRevision"] = 2
        source["vector"] = vector(500 + offset, 1, offset + 3)
        contention_payloads.append(source)
    contention_rows, contention_metrics = measured(
        process,
        lambda: parallel([(contention_index, "POST", source, tokens[USERS[contention_index]]) for source in contention_payloads], 10),
    )
    final_contention = request(contention_index, "GET", contention_payloads[-1])
    assert all(row.get("status") == 200 for row in contention_rows), contention_rows
    assert final_contention["revision"] == 12 and final_contention["items"] >= 10, final_contention

    stale_clear = payload(contention_index, "stale-clear", base_time + timedelta(days=1), action="clear", operation_id="matrix-stale-clear")
    stale_clear["baseRevision"] = 2
    stale_clear_rows, stale_clear_metrics = measured(process, lambda: [request(contention_index, "POST", stale_clear)])
    assert stale_clear_rows[0].get("stale") and stale_clear_rows[0].get("conflict") and stale_clear_rows[0].get("revision") == 12

    clears = [payload(index, "clear", base_time + timedelta(seconds=3), action="clear", operation_id=f"matrix-clear-{index:03d}") for index in range(100)]
    for index, source in enumerate(clears):
        source["baseRevision"] = 12 if index == contention_index else 2
    clear_rows, clear_metrics = measured(process, lambda: parallel([(index, "POST", clears[index], "") for index in range(100)], 25))
    clear_state = row_counts()
    assert clear_state["rows"] == 100 and clear_state["deleted_rows"] == 100, clear_state

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        reconnect_tokens = dict(pool.map(login, USERS))
    reconnect_rows, reconnect_metrics = measured(
        process,
        lambda: parallel([(index, "GET", clears[index], reconnect_tokens[USERS[index]]) for index in range(100)], 30),
    )
    assert all(row.get("status") == 200 and row.get("deleted") for row in reconnect_rows), reconnect_rows[:5]

    payload_size_metrics = {}
    for label in ("small", "medium", "large"):
        selected = [row for row in create_rows if row.get("size") == label]
        payload_size_metrics[label] = {
            "requests": len(selected),
            "request_body_bytes": sum(row.get("request_bytes", 0) for row in selected),
            "p50_ms": round(statistics.median(row["latency_ms"] for row in selected), 3),
            "p95_ms": round(percentile([row["latency_ms"] for row in selected], 0.95), 3),
        }

    result = {
        "users": 100,
        "distinct_pdfs": len(set(paths)),
        "distinct_pages": len({(paths[index], creates[index]["page"]) for index in range(100)}),
        "unique_operation_ids": len({row["operationId"] for row in creates}),
        "create_unique_independent_rows": create_metrics,
        "duplicate_retry_same_operation": retry_metrics,
        "update_unique_independent_rows": update_metrics,
        "load": load_metrics,
        "same_row_contention": {**contention_metrics, "final_revision": final_contention["revision"], "final_items": final_contention["items"]},
        "same_row_stale_clear": stale_clear_metrics,
        "same_row_device_model": "10 concurrent requests sharing the user's current valid session token; a newer login invalidates older tokens",
        "clear": clear_metrics,
        "reconnect_load": reconnect_metrics,
        "payload_sizes": payload_size_metrics,
        "states": {"create": create_state, "retry": retry_state, "update": update_state, "clear": clear_state},
        "isolation_key": "username + document_key(path|identity) + page",
        "cleanup_required": True,
    }
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
