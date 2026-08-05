#!/usr/bin/env python3
"""Measure interactive TTS wait while background builder jobs occupy the queue."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "FUTURE" / "tools"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import test_lesson_complete_isolated_harness as isolated

RUN_ROOT = ROOT / "programe_cache" / "durable_tts_interactive_reserve_18877"


# Added 2026-08-01: isolate the contention benchmark from production data and ports.
def configure() -> None:
    isolated.RUN_ROOT = RUN_ROOT
    isolated.PG_ROOT = RUN_ROOT / "postgres"
    isolated.SERVER_DATA_ROOT = RUN_ROOT / "server-data"
    isolated.RUNTIME_ROOT = RUN_ROOT / "runtime"
    isolated.QMLEARN_ROOT = RUN_ROOT / "qml"
    isolated.SERVER_LOG = RUN_ROOT / "server.log"
    isolated.PG_LOG = RUN_ROOT / "postgres.log"


# Added 2026-08-01: exercise the real coordinator and dispatcher threads with deterministic work time.
def run_child(job_seconds: float) -> dict:
    import FUTURE.server_app as app

    app.postgres_initialize_schema()

    def clear_jobs(connection):
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE future_server2.tts_jobs")

    app.postgres_execute(clear_jobs)
    starts: list[dict] = []
    starts_lock = threading.Lock()
    background_started = threading.Event()
    interactive_started = threading.Event()

    def fake_execute(job: dict) -> None:
        row = {
            "source": str(job.get("source") or ""),
            "priority": int(job.get("priority", 0) or 0),
            "at": time.perf_counter(),
        }
        with starts_lock:
            starts.append(row)
            background_count = sum(1 for item in starts if item["priority"] == 3)
        background_target = max(1, int(app.durable_tts_background_concurrency_limit(4) or 1))
        if background_count >= background_target:
            background_started.set()
        if row["priority"] == 1:
            interactive_started.set()
        time.sleep(job_seconds)

    app.durable_tts_execute_job = fake_execute
    os.environ["FUTURE_DURABLE_TTS_DISPATCHERS"] = "4"
    app.start_durable_tts_dispatcher()
    for index in range(8):
        app.durable_tts_enqueue(
            f"background contention {index}",
            "kokoro:af_jessica",
            priority=3,
            source=f"builder_contention_{index}",
            output_key=f"builder_contention_{index}",
        )
    if not background_started.wait(timeout=10):
        raise RuntimeError(f"Background jobs did not start: {starts}")
    submitted_at = time.perf_counter()
    app.durable_tts_enqueue(
        "interactive contention probe",
        "kokoro:af_jessica",
        priority=1,
        source="interactive_contention_probe",
        output_key="interactive_contention_probe",
    )
    if not interactive_started.wait(timeout=10):
        raise RuntimeError(f"Interactive job did not start: {starts}")
    with starts_lock:
        interactive = next(item for item in starts if item["priority"] == 1)
        before_interactive = [item for item in starts if item["priority"] == 3 and item["at"] <= interactive["at"]]
    app.DURABLE_TTS_QUEUE_STOP.set()
    with app.DURABLE_TTS_QUEUE_CONDITION:
        app.DURABLE_TTS_QUEUE_CONDITION.notify_all()
    app.postgres_close_pool()
    return {
        "dispatchers": 4,
        "background_target": max(1, int(app.durable_tts_background_concurrency_limit(4) or 1)),
        "job_seconds": job_seconds,
        "interactive_wait_ms": round((interactive["at"] - submitted_at) * 1000, 3),
        "background_started_before_interactive": len(before_interactive),
        "start_order": [{"source": item["source"], "priority": item["priority"]} for item in starts[:8]],
    }


def remove_run_root() -> None:
    if not RUN_ROOT.exists():
        return

    def clear_readonly(func, path, _exc):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    shutil.rmtree(RUN_ROOT, onerror=clear_readonly)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--job-seconds", type=float, default=0.8)
    args = parser.parse_args()
    configure()
    remove_run_root()
    RUN_ROOT.mkdir(parents=True)
    try:
        isolated.start_postgres()
        dump = isolated.sync_production_database_snapshot()
        isolated.initialize_schema()
        env = isolated.app_env()
        env["FUTURE_DURABLE_TTS_DISPATCHERS"] = "4"
        completed = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--child", "--job-seconds", str(args.job_seconds)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"contention child failed: {completed.stdout}\n{completed.stderr}")
        measurement = json.loads(completed.stdout.strip().splitlines()[-1])
        result = {
            "ok": True,
            "label": args.label,
            "database_sync": {
                "enabled": True,
                "method": "fresh pg_dump + pg_restore",
                "dump_bytes": dump.stat().st_size,
            },
            "resources": {"postgres": isolated.PG_PORT, "production_mutated": False},
            "measurement": measurement,
        }
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0
    finally:
        isolated.stop_postgres()
        remove_run_root()


if __name__ == "__main__":
    if "--child" in sys.argv:
        child_parser = argparse.ArgumentParser()
        child_parser.add_argument("--child", action="store_true")
        child_parser.add_argument("--job-seconds", type=float, default=0.8)
        child_args = child_parser.parse_args()
        print(json.dumps(run_child(child_args.job_seconds), ensure_ascii=False), flush=True)
        raise SystemExit(0)
    raise SystemExit(main())
