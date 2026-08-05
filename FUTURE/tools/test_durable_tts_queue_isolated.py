#!/usr/bin/env python3
"""Fresh PostgreSQL gate for durable TTS ordering, leases, dedupe, and artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "FUTURE" / "tools"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import test_lesson_complete_isolated_harness as isolated

RUN_ROOT = ROOT / "programe_cache" / "durable_tts_isolated_18877"
OUTPUT = Path(r"C:\Users\Admin\.codex\plans\durable_tts_queue_isolated_20260730.json")


def configure() -> None:
    isolated.RUN_ROOT = RUN_ROOT
    isolated.PG_ROOT = RUN_ROOT / "postgres"
    isolated.SERVER_DATA_ROOT = RUN_ROOT / "server-data"
    isolated.RUNTIME_ROOT = RUN_ROOT / "runtime"
    isolated.QMLEARN_ROOT = RUN_ROOT / "qml"
    isolated.SERVER_LOG = RUN_ROOT / "server.log"
    isolated.PG_LOG = RUN_ROOT / "postgres.log"


def run_validation() -> dict:
    import FUTURE.server_app as server_app
    import psycopg

    server_app.postgres_initialize_schema()
    for text, voice, priority, source in (
        ("background sentence", "kokoro:af_jessica", 3, "builder_space_l"),
        ("interactive sentence", "kokoro:af_jessica", 1, "ai_ghost"),
    ):
        server_app.durable_tts_enqueue(text, voice, priority=priority, source=source, output_key=source)
    first = server_app.durable_tts_claim("gate-worker-1", background_turn=False)
    if not first or first.get("source") != "ai_ghost":
        raise RuntimeError(f"P1 did not precede P3: {first}")
    stale = server_app.durable_tts_heartbeat(first["job_id"], "gate-worker-1", "stale-token")
    current = server_app.durable_tts_heartbeat(first["job_id"], "gate-worker-1", first["lease_token"])
    if stale or not current:
        raise RuntimeError(f"Lease fencing failed: stale={stale}, current={current}")
    with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
        cursor.execute(
            "UPDATE future_server2.tts_jobs SET lease_expires_epoch = %s WHERE job_id = %s",
            (time.time() - 1, first["job_id"]),
        )
    recovered = server_app.durable_tts_recover_expired()
    if recovered < 1:
        raise RuntimeError("Expired lease was not recovered.")
    time.sleep(1.1)
    reclaimed = server_app.durable_tts_claim("gate-worker-2", background_turn=False)
    if not reclaimed or reclaimed.get("job_id") != first.get("job_id") or reclaimed.get("lease_token") == first.get("lease_token"):
        raise RuntimeError("Recovered job did not receive a new fencing token.")
    artifact = b"deterministic-audio-gate"
    checksum = hashlib.sha256(artifact).hexdigest()
    if not server_app.durable_tts_publish(reclaimed, artifact, {"mime": "audio/mpeg", "voice": reclaimed["voice"]}):
        raise RuntimeError("Atomic artifact publication failed.")
    completed = server_app.durable_tts_job(reclaimed["job_id"])
    if not server_app.durable_tts_artifact_valid(completed) or completed.get("artifact_sha256") != checksum:
        raise RuntimeError(f"Published artifact metadata invalid: {completed}")
    duplicate = server_app.durable_tts_enqueue(
        reclaimed["text_payload"], reclaimed["voice"], priority=1, source="ai_ghost", output_key="ai_ghost"
    )
    ready = server_app.durable_tts_result(duplicate)
    if not ready or ready.get("audio_bytes") != artifact:
        raise RuntimeError("Dedupe did not reuse the durable artifact.")
    for index, priority in enumerate((1, 1, 3), start=1):
        server_app.durable_tts_enqueue(
            f"batch sentence {index}",
            "kokoro:af_jessica",
            priority=priority,
            source=f"batch_{priority}_{index}",
            output_key=f"batch_{priority}_{index}",
        )
    batch = server_app.durable_tts_claim_batch("gate-batch", 3, background_turn=False)
    if len(batch) != 3 or len({row.get("lease_token") for row in batch}) != 3:
        raise RuntimeError(f"Batch claim did not fence three jobs independently: {batch}")
    server_app.durable_tts_enqueue(
        "background batch preference",
        "kokoro:af_jessica",
        priority=3,
        source="batch_background_preference",
        output_key="batch_background_preference",
    )
    server_app.durable_tts_enqueue(
        "interactive batch preference",
        "kokoro:af_jessica",
        priority=1,
        source="batch_interactive_preference",
        output_key="batch_interactive_preference",
    )
    background_first = server_app.durable_tts_claim_batch("gate-background", 1, background_turn=True)
    if not background_first or int(background_first[0].get("priority", 0) or 0) != 3:
        raise RuntimeError(f"Background batch turn did not prefer P3: {background_first}")
    for index in range(4):
        server_app.durable_tts_enqueue(
            f"reserve background {index}",
            "kokoro:af_jessica",
            priority=3,
            source=f"reserve_background_{index}",
            output_key=f"reserve_background_{index}",
        )
    server_app.durable_tts_enqueue(
        "reserve interactive",
        "kokoro:af_jessica",
        priority=1,
        source="reserve_interactive",
        output_key="reserve_interactive",
    )
    reserve_batch = server_app.durable_tts_claim_capacity_batch("gate-reserve", 4, 3)
    reserve_priorities = [int(row.get("priority", 0) or 0) for row in reserve_batch]
    if len(reserve_priorities) != 4 or reserve_priorities != sorted(reserve_priorities) or reserve_priorities.count(3) > 3:
        raise RuntimeError(f"Interactive reserve batch was not bounded: {reserve_priorities}")
    with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT priority, source, status, COUNT(*) FROM future_server2.tts_jobs GROUP BY priority, source, status ORDER BY priority, source, status")
        rows = [list(row) for row in cursor.fetchall()]
    result = {
        "priority_first": first.get("source"),
        "lease_recovered": recovered,
        "fencing": {"stale_rejected": True, "current_accepted": True, "token_rotated": True},
        "artifact": {"atomic": True, "checksum": checksum, "dedupe_reused": True},
        "batch_claim": {
            "count": len(batch),
            "unique_fencing_tokens": True,
            "background_preferred": True,
            "interactive_reserve_priorities": reserve_priorities,
        },
        "rows": rows,
    }
    server_app.postgres_close_pool()
    return result


def main() -> int:
    configure()
    if RUN_ROOT.exists():
        def clear_readonly(func, path, _exc):
            os.chmod(path, stat.S_IWRITE)
            func(path)
        shutil.rmtree(RUN_ROOT, onerror=clear_readonly)
    RUN_ROOT.mkdir(parents=True)
    try:
        isolated.start_postgres()
        dump = isolated.sync_production_database_snapshot()
        isolated.initialize_schema()
        completed = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--child"],
            cwd=ROOT,
            env=isolated.app_env(),
            capture_output=True,
            text=True,
            timeout=180,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"durable TTS child failed: {completed.stdout}\n{completed.stderr}")
        child_result = json.loads(completed.stdout.strip().splitlines()[-1])
        result = {
            "ok": True,
            "database_sync": {"enabled": True, "method": "fresh pg_dump + pg_restore", "dump_bytes": dump.stat().st_size},
            "resources": {"postgres": isolated.PG_PORT, "production_mutated": False},
            **child_result,
        }
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0
    finally:
        isolated.stop_postgres()
        if RUN_ROOT.exists():
            def clear_readonly_final(func, path, _exc):
                os.chmod(path, stat.S_IWRITE)
                func(path)
            shutil.rmtree(RUN_ROOT, onerror=clear_readonly_final)


if __name__ == "__main__":
    if "--child" in sys.argv:
        print(json.dumps(run_validation(), ensure_ascii=False), flush=True)
        raise SystemExit(0)
    raise SystemExit(main())
