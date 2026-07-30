"""Benchmark 100 isolated lesson completions with path as locator and optional canonical lesson_id."""

from __future__ import annotations

import argparse
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
SPACE_SUFFIXES = {
    "space_v": ".space_v",
    "space_w": ".space_w",
    "space_q": ".space_q",
    "space_p": ".space_p",
    "space_l": ".space_l",
    "space_s": ".space_s",
}


def percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, int(len(ordered) * ratio) - 1)] if ordered else 0.0


def server_process() -> psutil.Process:
    for connection in psutil.net_connections(kind="tcp"):
        if connection.status == psutil.CONN_LISTEN and connection.laddr and connection.laddr.port == 8877 and connection.pid:
            return psutil.Process(connection.pid)
    raise RuntimeError("Server 2 listener not found")


def load_lessons(space: str = "space_w") -> list[dict]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    manifest_rows = sorted(
        (
            {"path": str(entry.get("path", "")).strip(), "lesson_id": str(entry.get("lesson_id", "")).strip()}
            for entries in (payload.get("folders") or {}).values()
            for entry in (entries if isinstance(entries, list) else [])
            if isinstance(entry, dict)
            and str(entry.get("type", "")).lower() == "file"
            and str(entry.get("path", "")).lower().startswith("common/")
            and any(str(entry.get("path", "")).lower().endswith(suffix) for suffix in SPACE_SUFFIXES.values())
            and str(entry.get("lesson_id", "")).lower().startswith("ftg-lesson-")
        ),
        key=lambda row: row["path"].lower(),
    )
    connection = sqlite3.connect(DATABASE)
    try:
        registry_ids = {
            str(row[0]).strip().lower(): str(row[1]).strip()
            for row in connection.execute("SELECT normalized_path,file_id FROM lesson_file_aliases WHERE active=1")
        }
    finally:
        connection.close()
    rows = [
        {
            **row,
            "space": next((name for name, suffix in SPACE_SUFFIXES.items() if row["path"].lower().endswith(suffix)), ""),
            "manifest_lesson_id": row["lesson_id"],
            "lesson_id": registry_ids.get(row["path"].lower(), ""),
        }
        for row in manifest_rows
    ]
    rows = [row for row in rows if row["lesson_id"].lower().startswith("ftg-lesson-")]
    if space != "mixed":
        rows = [row for row in rows if row["space"] == space]
        if len(rows) < 100:
            raise RuntimeError(f"Need 100 registry-backed {space} lessons, found {len(rows)}")
        return rows[:100]
    quotas = {"space_v": 17, "space_w": 17, "space_q": 17, "space_p": 17, "space_l": 16, "space_s": 16}
    selected = []
    for name, count in quotas.items():
        pool = [row for row in rows if row["space"] == name]
        if len(pool) < count:
            raise RuntimeError(f"Need {count} registry-backed {name} lessons, found {len(pool)}")
        selected.extend(pool[:count])
    return selected


def writer_state() -> dict:
    return requests.get(f"{BASE}/health", timeout=15).json().get("sqlite_writer", {})


def source_delta(before: dict, after: dict, key: str) -> dict:
    left = before.get(key) if isinstance(before.get(key), dict) else {}
    right = after.get(key) if isinstance(after.get(key), dict) else {}
    return {
        source: round(float(right.get(source, 0) or 0) - float(left.get(source, 0) or 0), 3)
        for source in sorted(set(left) | set(right))
        if float(right.get(source, 0) or 0) - float(left.get(source, 0) or 0)
    }


def database_counts() -> dict:
    connection = sqlite3.connect(DATABASE)
    try:
        return {
            "progress": int(connection.execute("SELECT COUNT(*) FROM lesson_progress WHERE username LIKE 'codexload%'").fetchone()[0]),
            "learning_events": int(connection.execute("SELECT COUNT(*) FROM append_events WHERE username LIKE 'codexload%' AND stream IN ('learning','learning_intent')").fetchone()[0]),
            "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
            "journal_mode": connection.execute("PRAGMA journal_mode").fetchone()[0],
            "synchronous": int(connection.execute("PRAGMA synchronous").fetchone()[0]),
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--send-id", action="store_true")
    parser.add_argument("--space", choices=("mixed",) + tuple(SPACE_SUFFIXES), default="space_w")
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this benchmark only")

    lessons = load_lessons(args.space)

    def login(username: str) -> str:
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if not (payload.get("server_data") or {}).get("load_test"):
            raise RuntimeError(f"Load-test isolation missing for {username}")
        return str(payload.get("token", ""))

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        tokens = list(pool.map(login, USERS))

    process = server_process()
    writer_before = writer_state()
    counts_before = database_counts()
    cpu_before = sum(process.cpu_times()[:2])
    io_before = process.io_counters()
    base_stamp = datetime.now(timezone.utc) - timedelta(minutes=1)

    def complete(index: int) -> dict:
        lesson = lessons[index]
        stamp = (base_stamp + timedelta(milliseconds=index)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        body = {
            "path": lesson["path"],
            "name": Path(lesson["path"]).name,
            "title": Path(lesson["path"]).stem,
            "nodes": 1,
            "completed_at": stamp,
            "source": lesson["space"].replace("space_", "Space_").upper().replace("SPACE_", "Space_"),
        }
        if args.send_id:
            body["lesson_id"] = lesson["lesson_id"]
        started = time.perf_counter()
        response = requests.post(
            f"{BASE}/lesson/complete",
            headers={"Authorization": f"Bearer {tokens[index]}"},
            json=body,
            timeout=60,
        )
        latency = (time.perf_counter() - started) * 1000
        payload = response.json() if response.content else {}
        return {
            "status": response.status_code,
            "latency_ms": latency,
            "bytes": len(response.content),
            "event_key": str(payload.get("event_key", "")),
            "timing": payload.get("timing_ms") if isinstance(payload.get("timing_ms"), dict) else {},
            "lock_scope": str(payload.get("lock_scope", "")),
            "error": "" if response.status_code == 200 else str(payload.get("error", response.text[:200])),
        }

    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        rows = list(pool.map(complete, range(100)))
    wall = time.perf_counter() - started
    cpu_after = sum(process.cpu_times()[:2])
    io_after = process.io_counters()
    counts_after = database_counts()
    writer_after = writer_state()
    latencies = [float(row["latency_ms"]) for row in rows]
    stage_names = sorted({key for row in rows for key in row["timing"]})
    result = {
        "send_id": args.send_id,
        "space": args.space,
        "space_counts": {name: sum(row["space"] == name for row in lessons) for name in sorted({row["space"] for row in lessons})},
        "users": 100,
        "canonical_ids": sum(1 for row in lessons if row["lesson_id"]),
        "manifest_registry_mismatches": sum(row["manifest_lesson_id"] != row["lesson_id"] for row in lessons),
        "requests": len(rows),
        "errors": sum(bool(row["error"]) for row in rows),
        "error_samples": [row for row in rows if row["error"]][:5],
        "rps": round(len(rows) / max(0.001, wall), 3),
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(percentile(latencies, 0.95), 3),
        "p99_ms": round(percentile(latencies, 0.99), 3),
        "server_cpu_ms": round((cpu_after - cpu_before) * 1000, 3),
        "server_cpu_ms_per_request": round((cpu_after - cpu_before) * 10, 3),
        "server_read_bytes": max(0, io_after.read_bytes - io_before.read_bytes),
        "server_write_bytes": max(0, io_after.write_bytes - io_before.write_bytes),
        "response_bytes": sum(int(row["bytes"]) for row in rows),
        "unique_event_keys": len({row["event_key"] for row in rows if row["event_key"]}),
        "lock_scopes": {scope: sum(row["lock_scope"] == scope for row in rows) for scope in sorted({row["lock_scope"] for row in rows})},
        "stages": {
            name: {
                "p50_ms": round(statistics.median([float(row["timing"].get(name, 0)) for row in rows]), 3),
                "p95_ms": round(percentile([float(row["timing"].get(name, 0)) for row in rows], 0.95), 3),
            }
            for name in stage_names
        },
        "writer_delta": {
            key: round(float(writer_after.get(key, 0) or 0) - float(writer_before.get(key, 0) or 0), 3)
            for key in ("tasks", "batches", "queue_wait_ms", "begin_wait_ms", "commit_ms", "busy_errors")
        },
        "writer_sources": {
            "tasks": source_delta(writer_before, writer_after, "source_tasks"),
            "callback_ms": source_delta(writer_before, writer_after, "source_callback_ms"),
        },
        "database_before": counts_before,
        "database_after": counts_after,
    }
    encoded = json.dumps(result, ensure_ascii=True, indent=2)
    print(encoded)
    if args.output:
        Path(args.output).write_text(encoded, encoding="utf-8")
    return 0 if not result["errors"] and result["unique_event_keys"] == 100 else 2


if __name__ == "__main__":
    raise SystemExit(main())
