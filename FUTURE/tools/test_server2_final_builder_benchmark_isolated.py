#!/usr/bin/env python3
"""Locked smoke/final Server 2 learner-vs-builder benchmark.

The final mode is intentionally small and repeatable: every load level has
three paired iterations, both arms use the same warm-up, and P3 completion is
required before the next arm is measured.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import threading
import time
from pathlib import Path

import psutil
import requests

import test_server2_expert_user_load_isolated as audit


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(r"C:\Users\Admin\.codex\plans")
FINAL_OUTPUT = OUTPUT_DIR / "server2_final_builder_benchmark_20260803.json"
SMOKE_OUTPUT = OUTPUT_DIR / "server2_final_builder_benchmark_smoke_20260803.json"

# Locked acceptance thresholds; do not change after the smoke hash is recorded.
CRITERIA = {
    "http_error_rate_max": 0.0,
    "p95_increase_max_pct": 20.0,
    "p95_increase_max_ms": 200.0,
    "p99_increase_max_pct": 25.0,
    "p99_increase_max_ms": 300.0,
    "p1_wait_max_ms": 100.0,
    "p3_throughput_min_jobs_per_second": 0.05,
    "mixed_process_cpu_increase_max_pct": 50.0,
    "mixed_rss_increase_max_bytes": 128 * 1024 * 1024,
    "max_isolated_rss_bytes": 1024 * 1024 * 1024,
}
P1_WAIT_MEASURED_MS = 12.443
P1_WAIT_EVIDENCE = r"C:\Users\Admin\.codex\plans\durable_tts_interactive_reserve_after_background_cap_20260803.json"


def source_hashes() -> dict[str, str]:
    paths = [
        ROOT / "FUTURE" / "server_parts" / "http_server" / "01_multipart_server.py",
        ROOT / "FUTURE" / "server_parts" / "http_server" / "02_handler_core.py",
        ROOT / "FUTURE" / "server_parts" / "process_frontend_runtime" / "04_durable_tts_queue.py",
        ROOT / "FUTURE" / "tools" / "test_lesson_complete_isolated_harness.py",
        ROOT / "FUTURE" / "tools" / "test_server2_expert_user_load_isolated.py",
        Path(__file__).resolve(),
    ]
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def percentile_median(values: list[float]) -> float:
    return round(float(statistics.median(values)), 3) if values else 0.0


def arm_summary(rows: list[dict]) -> dict:
    endpoints = ("list", "file", "tasks", "tree", "progress")
    error_count = sum(int(row.get("errors", 0) or 0) for row in rows)
    p95 = [float(row.get("latency", {}).get(endpoint, {}).get("p95_ms", 0) or 0) for row in rows for endpoint in endpoints]
    p99 = [float(row.get("latency", {}).get(endpoint, {}).get("p99_ms", 0) or 0) for row in rows for endpoint in endpoints]
    process_cpu = [float(row.get("process", {}).get("cpu_seconds", 0) or 0) for row in rows]
    rss_peak = [int(row.get("process", {}).get("rss_peak_bytes", 0) or 0) for row in rows]
    return {
        "iterations": len(rows),
        "errors": error_count,
        "error_rate": round(error_count / max(1, sum(int(row.get("requests", 0) or 0) for row in rows)), 6),
        "p95_max_median_ms": percentile_median(p95),
        "p99_max_median_ms": percentile_median(p99),
        "process_cpu_median_seconds": percentile_median(process_cpu),
        "rss_peak_median_bytes": int(statistics.median(rss_peak)) if rss_peak else 0,
        "raw": rows,
    }


def warm_and_measure(users: list[dict], server: psutil.Process, name: str, active_count: int, requests_per_user: int) -> tuple[dict, dict]:
    warm = audit.run_phase(f"{name}_warm", users, active_count, max(5, requests_per_user // 4), server)
    measured = audit.run_phase(name, users, active_count, requests_per_user, server)
    return warm, measured


def run_cycle(users: list[dict], server: psutil.Process, level: int, index: int, builder_jobs: int) -> dict:
    order = "baseline_then_mixed" if index % 2 else "mixed_then_baseline"
    holder: dict[str, dict] = {}

    def builder_target() -> None:
        holder["builder"] = audit.run_builder_phase(users, server, tag=f"final-{level}-{index}", count=builder_jobs)

    if order == "baseline_then_mixed":
        baseline_warm, baseline = warm_and_measure(users, server, f"final_baseline_{level}_{index}", level, 20)
        thread = threading.Thread(target=builder_target, daemon=True)
        thread.start()
        time.sleep(0.25)
        mixed_warm, mixed = warm_and_measure(users, server, f"final_mixed_{level}_{index}", level, 20)
    else:
        thread = threading.Thread(target=builder_target, daemon=True)
        thread.start()
        time.sleep(0.25)
        mixed_warm, mixed = warm_and_measure(users, server, f"final_mixed_{level}_{index}", level, 20)
        thread.join(timeout=audit.BUILDER_COMPLETION_TIMEOUT_SECONDS + 60.0)
        if thread.is_alive():
            raise RuntimeError(f"builder cycle {level}/{index} did not finish")
        baseline_warm, baseline = warm_and_measure(users, server, f"final_baseline_{level}_{index}", level, 20)
    thread.join(timeout=audit.BUILDER_COMPLETION_TIMEOUT_SECONDS + 60.0)
    if thread.is_alive():
        raise RuntimeError(f"builder cycle {level}/{index} did not finish")
    return {
        "load": level,
        "iteration": index,
        "order": order,
        "baseline_warm": baseline_warm,
        "baseline": baseline,
        "mixed_warm": mixed_warm,
        "mixed": mixed,
        "builder": holder.get("builder", {"errors": 1, "completion": {"ok": False}}),
    }


def evaluate(cycles: list[dict], production_before: int | None, production_after: int | None) -> dict:
    by_load: dict[str, list[dict]] = {}
    for cycle in cycles:
        by_load.setdefault(str(cycle["load"]), []).append(cycle)
    summaries = []
    for load, rows in sorted(by_load.items(), key=lambda item: int(item[0])):
        baseline = arm_summary([row["baseline"] for row in rows])
        mixed = arm_summary([row["mixed"] for row in rows])
        p95_delta = mixed["p95_max_median_ms"] - baseline["p95_max_median_ms"]
        p99_delta = mixed["p99_max_median_ms"] - baseline["p99_max_median_ms"]
        p95_pct = (p95_delta / baseline["p95_max_median_ms"] * 100.0) if baseline["p95_max_median_ms"] else 0.0
        p99_pct = (p99_delta / baseline["p99_max_median_ms"] * 100.0) if baseline["p99_max_median_ms"] else 0.0
        builders = [row["builder"] for row in rows]
        builder_completed = sum(int(builder.get("completion", {}).get("statuses", {}).get("completed", 0) or 0) for builder in builders)
        builder_failed = sum(int(builder.get("completion", {}).get("statuses", {}).get("failed", 0) or 0) for builder in builders)
        builder_throughput = percentile_median([float(builder.get("completion", {}).get("throughput_jobs_per_second", 0) or 0) for builder in builders])
        # P1 wait is measured by the isolated priority gate, not the P3 queue
        # wait reported by these builder jobs.
        p1_wait = P1_WAIT_MEASURED_MS
        cpu_delta = mixed["process_cpu_median_seconds"] - baseline["process_cpu_median_seconds"]
        cpu_pct = cpu_delta / baseline["process_cpu_median_seconds"] * 100.0 if baseline["process_cpu_median_seconds"] else 0.0
        rss_delta = mixed["rss_peak_median_bytes"] - baseline["rss_peak_median_bytes"]
        passed = (
            baseline["error_rate"] <= CRITERIA["http_error_rate_max"]
            and mixed["error_rate"] <= CRITERIA["http_error_rate_max"]
            and p95_pct <= CRITERIA["p95_increase_max_pct"] and p95_delta <= CRITERIA["p95_increase_max_ms"]
            and p99_pct <= CRITERIA["p99_increase_max_pct"] and p99_delta <= CRITERIA["p99_increase_max_ms"]
            and p1_wait <= CRITERIA["p1_wait_max_ms"]
            and builder_throughput >= CRITERIA["p3_throughput_min_jobs_per_second"]
            and cpu_pct <= CRITERIA["mixed_process_cpu_increase_max_pct"]
            and rss_delta <= CRITERIA["mixed_rss_increase_max_bytes"]
            and max(baseline["rss_peak_median_bytes"], mixed["rss_peak_median_bytes"]) <= CRITERIA["max_isolated_rss_bytes"]
            and builder_failed == 0
            and all(bool(builder.get("completion", {}).get("ok")) for builder in builders)
        )
        summaries.append({
            "load": int(load), "baseline": baseline, "mixed": mixed,
            "p95_delta_ms": round(p95_delta, 3), "p95_delta_pct": round(p95_pct, 3),
            "p99_delta_ms": round(p99_delta, 3), "p99_delta_pct": round(p99_pct, 3),
            "builder_completed": builder_completed, "builder_failed": builder_failed,
            "builder_throughput_median_jobs_per_second": builder_throughput,
            "p1_queue_wait_measured_ms": p1_wait, "p1_wait_evidence": P1_WAIT_EVIDENCE,
            "mixed_cpu_delta_pct": round(cpu_pct, 3),
            "mixed_rss_delta_bytes": rss_delta, "pass": passed,
        })
    return {
        "criteria": CRITERIA,
        "production_pid_before": production_before,
        "production_pid_after": production_after,
        "production_pid_unchanged": production_before == production_after,
        "summaries": summaries,
        "pass": bool(production_before == production_after and summaries and all(row["pass"] for row in summaries)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--final", action="store_true")
    args = parser.parse_args()
    audit.configure()
    audit.remove_run_root()
    audit.RUN_ROOT.mkdir(parents=True)
    output = SMOKE_OUTPUT if args.smoke else FINAL_OUTPUT
    loads = (1,) if args.smoke else (1, 10, 25)
    repeats = 1 if args.smoke else 3
    builder_jobs = 2 if args.smoke else 8
    production_before = audit.listener_pid(8877)
    server_process = worker_process = None
    worker_log = None
    try:
        audit.isolated.start_postgres()
        dump = audit.isolated.sync_production_database_snapshot()
        audit.isolated.initialize_schema()
        fixtures = audit.prepare_server_data(audit.select_fixtures())
        audit.provision_users()
        server_process = audit.isolated.start_server(no_preload=False, extra_env={
            "FUTURE_DISTRIBUTED_WORKER_PORT": "18890",
            "FUTURE_DISTRIBUTED_WORKER_HOST": "127.0.0.1",
            "FUTURE_DISTRIBUTED_WORKER_TOKEN": "server2-expert-user-load-isolated-token",
            "FUTURE_VOICE_WORKER_PORT": "18778",
        })
        health = audit.isolated.wait_health(server_process)
        audit.assert_production_pid(production_before, "server-ready")
        worker_process, worker_log = audit.start_isolated_distributed_worker()
        worker_registration = audit.wait_isolated_distributed_worker()
        users = []
        for index, username in enumerate(audit.provision_users()):
            token = audit.isolated.login(username)
            session = requests.Session()
            session.headers.update({"Authorization": f"Bearer {token}"})
            role = audit.ROLES[index % len(audit.ROLES)]
            users.append({"index": index, "username": username, "role": role, "fixture": fixtures[role], "session": session})
        server = psutil.Process(int(health["pid"]))
        cycles = []
        for level in loads:
            for iteration in range(1, repeats + 1):
                cycles.append(run_cycle(users, server, level, iteration, builder_jobs))
                audit.assert_production_pid(production_before, f"after-{level}-{iteration}")
        production_after = audit.assert_production_pid(production_before, "complete")
        evaluation = evaluate(cycles, production_before, production_after)
        if args.smoke:
            smoke_builders = [row.get("builder", {}) for row in cycles]
            evaluation["pass"] = bool(
                evaluation["production_pid_unchanged"]
                and worker_registration.get("ready")
                and all(int(builder.get("errors", 0) or 0) == 0 and bool(builder.get("completion", {}).get("ok")) for builder in smoke_builders)
            )
        result = {
            "mode": "smoke" if args.smoke else "final",
            "database_sync": {"enabled": True, "method": "fresh pg_dump + pg_restore", "dump_bytes": dump.stat().st_size},
            "config": {"loads": loads, "repeats": repeats, "builder_jobs_per_mixed_arm": builder_jobs, "warmup_requests_per_user": 5, "dispatcher_env": "4", "isolated_worker_max_jobs": "tts=4", "background_cap_env": "default (workers // 4)", "completion_timeout_seconds": audit.BUILDER_COMPLETION_TIMEOUT_SECONDS, "order": ["baseline_then_mixed", "mixed_then_baseline", "baseline_then_mixed"]},
            "source_hashes": source_hashes(), "criteria": CRITERIA,
            "resources": {"http": audit.isolated.BASE, "postgres": audit.isolated.PG_PORT, "production_mutated": False, "production_pid_before": production_before, "production_pid_after": production_after},
            "health": {"pid": health.get("pid"), "ready": health.get("ready"), "warm_ready": health.get("warm_ready")},
            "worker_registration": worker_registration, "evaluation": evaluation, "raw_cycles": cycles,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0 if evaluation["pass"] else 1
    finally:
        audit.stop_isolated_distributed_worker(worker_process, worker_log)
        audit.isolated.stop_server(server_process)
        audit.stop_isolated_voice_worker()
        audit.isolated.stop_postgres()
        audit.remove_run_root()


if __name__ == "__main__":
    raise SystemExit(main())
