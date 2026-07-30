"""Focused runtime probe for /server-data/tree-preload.

Added 2026-07-26 for the PostgreSQL full-audit checkpoints. It uses real HTTP
auth and records ETag/304, CPU, payload, and PostgreSQL health deltas without
printing credentials or tokens.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil
import requests

BASE = "http://127.0.0.1:8877"
OUTPUT_DIR = Path(r"C:\Users\Admin\.codex\plans\server2_postgres_full_audit")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def server_process(port: int = 8877) -> psutil.Process:
    for connection in psutil.net_connections(kind="tcp"):
        if connection.laddr and connection.laddr.port == port and connection.status == psutil.CONN_LISTEN and connection.pid:
            return psutil.Process(connection.pid)
    raise RuntimeError(f"Server 2 listener not found on port {port}")


def cpu_seconds(process: psutil.Process) -> float:
    row = process.cpu_times()
    return float(row.user + row.system)


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, max(0, int(len(ordered) * ratio) - 1))], 3)


def summarize(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "min_ms": round(min(values), 3),
        "mean_ms": round(statistics.fmean(values), 3),
        "p50_ms": round(statistics.median(values), 3),
        "p95_ms": percentile(values, 0.95),
        "p99_ms": percentile(values, 0.99),
        "max_ms": round(max(values), 3),
    }


def health(base: str) -> dict[str, Any]:
    response = requests.get(base + "/health?view=dashboard-v1", timeout=10)
    response.raise_for_status()
    return response.json()


def pg_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    left = before.get("postgres") if isinstance(before, dict) else {}
    right = after.get("postgres") if isinstance(after, dict) else {}
    if not isinstance(left, dict) or not isinstance(right, dict):
        return {"available": False}
    result = {"available": True}
    for key in sorted(set(left) | set(right)):
        try:
            result[key] = round(float(right.get(key, 0) or 0) - float(left.get(key, 0) or 0), 6)
        except Exception:
            result[key] = right.get(key)
    return result


def login(base: str, username: str, password: str) -> tuple[requests.Session, str]:
    session = requests.Session()
    response = session.post(base + "/auth/login", json={"username": username, "password": password}, timeout=30)
    response.raise_for_status()
    token = str(response.json().get("token") or "")
    if not token:
        raise RuntimeError("Login returned no token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session, token


def get_tree(session: requests.Session, base: str, etag: str = "") -> dict[str, Any]:
    headers = {"Accept-Encoding": "gzip"}
    if etag:
        headers["If-None-Match"] = etag
    started = time.perf_counter()
    response = session.get(base + "/server-data/tree-preload", headers=headers, timeout=45)
    elapsed = (time.perf_counter() - started) * 1000
    content_length = int(response.headers.get("Content-Length") or 0)
    decoded = len(response.content)
    payload = {}
    if response.status_code != 304:
        payload = response.json()
    return {
        "status": response.status_code,
        "duration_ms": round(elapsed, 3),
        "decoded_bytes": decoded,
        "wire_bytes": content_length,
        "etag": str(response.headers.get("ETag") or ""),
        "content_encoding": str(response.headers.get("Content-Encoding") or ""),
        "cache_hit": str(response.headers.get("X-Future-Cache-Hit") or ""),
        "server_timing": str(response.headers.get("Server-Timing") or ""),
        "row_count": int(payload.get("row_count", 0) or 0) if isinstance(payload, dict) else 0,
        "entry_columns": len(payload.get("entry_columns") or []) if isinstance(payload, dict) else 0,
        "payload_sha256": hashlib.sha256(response.content).hexdigest() if response.content else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=BASE)
    parser.add_argument("--prefix", default="checkpoint_002_tree_preload_baseline")
    parser.add_argument("--username", default=os.environ.get("FUTURE_TREE_PROBE_USER", "hung"))
    parser.add_argument("--password-env", default="FUTURE_TREE_PROBE_PASSWORD")
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    args = parser.parse_args()
    password = os.environ.get(args.password_env, "")
    if not password:
        raise RuntimeError(f"Set {args.password_env} for this probe only")

    process = server_process(8877)
    before_health = health(args.base)
    before_cpu = cpu_seconds(process)
    before_rss = int(process.memory_info().rss)
    session, _token = login(args.base, args.username, password)
    cold = get_tree(session, args.base)
    etag = cold.get("etag", "")
    repeated = [get_tree(session, args.base) for _ in range(max(0, args.count))]
    revalidated = [get_tree(session, args.base, etag) for _ in range(max(0, args.count))]
    after_health = health(args.base)
    after_rss = int(process.memory_info().rss)
    total_cpu_ms = round(max(0.0, (cpu_seconds(process) - before_cpu) * 1000), 3)

    raw = {
        "timestamp_utc": utc_now(),
        "prefix": args.prefix,
        "username": args.username,
        "server_pid": process.pid,
        "postgres_only": (before_health.get("postgres_writer") or {}).get("postgres_only") is True,
        "postgres_writer_enabled": (before_health.get("postgres_writer") or {}).get("enabled"),
        "cpu_ms": total_cpu_ms,
        "rss_delta_bytes": after_rss - before_rss,
        "postgres_delta": pg_delta(before_health, after_health),
        "cold": cold,
        "repeated": repeated,
        "revalidated": revalidated,
        "summary": {
            "repeated_duration": summarize([float(row["duration_ms"]) for row in repeated]),
            "revalidated_duration": summarize([float(row["duration_ms"]) for row in revalidated]),
            "repeated_decoded_bytes": sum(int(row["decoded_bytes"]) for row in repeated),
            "revalidated_decoded_bytes": sum(int(row["decoded_bytes"]) for row in revalidated),
            "repeated_wire_bytes": sum(int(row["wire_bytes"]) for row in repeated),
            "revalidated_wire_bytes": sum(int(row["wire_bytes"]) for row in revalidated),
            "revalidated_304": sum(1 for row in revalidated if int(row["status"]) == 304),
        },
    }
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{args.prefix}_raw.json"
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "output": str(path),
        "cold_status": cold.get("status"),
        "cold_decoded_bytes": cold.get("decoded_bytes"),
        "cold_wire_bytes": cold.get("wire_bytes"),
        "repeated_p95_ms": raw["summary"]["repeated_duration"].get("p95_ms"),
        "revalidated_p95_ms": raw["summary"]["revalidated_duration"].get("p95_ms"),
        "revalidated_304": raw["summary"]["revalidated_304"],
        "cpu_ms": total_cpu_ms,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

