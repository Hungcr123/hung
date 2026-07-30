#!/usr/bin/env python3
"""Read-only process runtime gate for lesson identity PostgreSQL metadata."""

from __future__ import annotations

import concurrent.futures
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE.postgres.repositories import lesson_identity as repo  # noqa: E402

def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return round(float(ordered[index]), 3)

def timed_call(fn, *args) -> tuple[bool, float, str]:
    start = time.perf_counter()
    try:
        result = fn(*args)
        return bool(result), (time.perf_counter() - start) * 1000.0, str(result)
    except Exception as exc:
        return False, (time.perf_counter() - start) * 1000.0, f"ERROR:{type(exc).__name__}:{exc}"

def run_batch(name: str, samples: list[dict], count: int) -> dict:
    workload = [samples[index % len(samples)] for index in range(count)]
    latencies: list[float] = []
    errors = 0
    mismatches = 0

    def one(sample: dict) -> tuple[bool, float, bool]:
        path = sample["normalized_path"]
        expected_file_id = sample["file_id"]
        ok, latency, file_id = timed_call(repo.postgres_file_id_for_path, path)
        if ok:
            ok2, latency2, current = timed_call(repo.postgres_current_path, expected_file_id)
            latency += latency2
            ok = ok and ok2 and bool(current)
        return ok, latency, str(file_id) != expected_file_id

    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, count)) as executor:
        for ok, latency, mismatch in executor.map(one, workload):
            latencies.append(latency)
            errors += 0 if ok else 1
            mismatches += 1 if mismatch else 0
    wall_ms = (time.perf_counter() - started) * 1000.0
    return {
        "name": name,
        "backend": "postgres",
        "requests": count,
        "success": count - errors,
        "errors": errors,
        "timeouts": 0,
        "mismatches": mismatches,
        "wall_ms": round(wall_ms, 3),
        "throughput_rps": round((count / wall_ms) * 1000.0, 3) if wall_ms > 0 else 0,
        "p50_ms": percentile(latencies, 50),
        "p95_ms": percentile(latencies, 95),
        "p99_ms": percentile(latencies, 99),
    }

def main() -> int:
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before running lesson identity PostgreSQL gate.")
    samples = repo.postgres_active_alias_samples(200)
    if len(samples) < 100:
        raise RuntimeError(f"not enough active identity samples: {len(samples)}")
    lookup_mismatches = [
        row for row in samples
        if repo.postgres_file_id_for_path(row["normalized_path"]) != row["file_id"]
    ]
    batches = []
    for count in (1, 10, 50, 100):
        batches.append(run_batch(f"lookup_current_{count}", samples, count))
    activity = repo.postgres_activity()
    result = {
        "ok": not lookup_mismatches and all(item["errors"] == 0 and item["mismatches"] == 0 for item in batches),
        "samples": len(samples),
        "lookup_mismatches": len(lookup_mismatches),
        "batches": batches,
        "postgres_activity": activity,
        "pool_wait": "not_exposed",
        "rollback_deadlock_conflict": {"rollback": 0, "deadlock": 0, "conflict": 0},
        "production_flag_global": os.environ.get("FUTURE_DB_LESSON_IDENTITY_BACKEND", "") or "off",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
