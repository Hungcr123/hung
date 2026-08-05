"""Fresh-snapshot isolated HTTP gate for the persistent Space_Q vocabulary index."""

from __future__ import annotations

import json
import os
import shutil
import stat
import sys
import time
from pathlib import Path

import psutil
import requests


ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "FUTURE" / "tools"))

import test_lesson_complete_isolated_harness as isolated


RUN_ROOT = ROOT / "programe_cache" / "space_q_vocab_index_isolated_18877"
OUTPUT = Path(r"C:\Users\Admin\.codex\plans\space_q_vocab_index_isolated_20260801.json")
TEST_USER = "codexspaceqindex"
SOURCE = Path(r"C:\server data\hung\Thi_qua_khu_don_50_cau.Space_Q")
RELATIVE = f"{TEST_USER}/Thi_qua_khu_don_50_cau.Space_Q"


def configure() -> None:
    isolated.RUN_ROOT = RUN_ROOT
    isolated.PG_ROOT = RUN_ROOT / "postgres"
    isolated.SERVER_DATA_ROOT = RUN_ROOT / "server-data"
    isolated.RUNTIME_ROOT = RUN_ROOT / "runtime"
    isolated.QMLEARN_ROOT = RUN_ROOT / "qml"
    isolated.SERVER_LOG = RUN_ROOT / "server.log"
    isolated.PG_LOG = RUN_ROOT / "postgres.log"
    isolated.OUTPUT_PATH = OUTPUT
    isolated.TEST_USER = TEST_USER


def provision_user() -> None:
    import psycopg
    from psycopg.types.json import Jsonb

    now = "2026-08-01T00:00:00Z"
    with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO future_server2.users
               (username,is_admin,is_test,profile_json,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
               VALUES (%s,false,true,%s,%s,0,'','')
               ON CONFLICT (username) DO UPDATE SET is_test=true,profile_json=excluded.profile_json""",
            (TEST_USER, Jsonb({"source": "space-q-vocab-index-isolated"}), now),
        )
        cursor.execute(
            """INSERT INTO future_server2.user_auth_credentials
               (username,password_hash,source_path,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
               VALUES (%s,%s,'space-q-vocab-index-isolated',%s,0,'','')
               ON CONFLICT (username) DO UPDATE SET password_hash=excluded.password_hash""",
            (TEST_USER, isolated.password_hash(isolated.PASSWORD), now),
        )
        connection.commit()


def prepare_server_data() -> str:
    if not SOURCE.is_file():
        raise RuntimeError(f"missing fixture: {SOURCE}")
    target = isolated.SERVER_DATA_ROOT / RELATIVE.replace("/", os.sep)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE, target)
    for name in ("Sound", "Picture", "NPC_TOP"):
        (isolated.SERVER_DATA_ROOT / name).mkdir(parents=True, exist_ok=True)
    wrapper = json.loads(target.read_text(encoding="utf-8-sig"))
    lesson_id = str(wrapper.get("lesson_id") or wrapper.get("lessonId") or "").strip()
    if not lesson_id:
        raise RuntimeError("fixture has no lesson_id")
    return lesson_id


def scan(token: str, lesson_id: str, process: psutil.Process) -> dict:
    server_before = sum(process.cpu_times()[:2]) * 1000
    pg_before = isolated.postgres_cpu()
    started = time.perf_counter()
    response = requests.post(
        f"{isolated.BASE}/vocab/scan-space-w?response=compact-v1",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"path": RELATIVE, "lesson_id": lesson_id},
        timeout=15,
    )
    wall_ms = (time.perf_counter() - started) * 1000
    server_after = sum(process.cpu_times()[:2]) * 1000
    pg_after = isolated.postgres_cpu()
    payload = response.json() if response.content else {}
    return {
        "status": response.status_code,
        "wall_ms": round(wall_ms, 3),
        "server_cpu_ms": round(server_after - server_before, 3),
        "postgres_cpu_ms": round(pg_after - pg_before, 3),
        "payload": payload,
    }


def wait_health(process, timeout_seconds: float = 300.0) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last = {}
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"isolated Server 2 exited with {process.returncode}")
        try:
            last = requests.get(f"{isolated.BASE}/health", timeout=5).json()
            if int(last.get("pid", 0) or 0) == process.pid and last.get("ready") and last.get("warm_ready"):
                return last
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"isolated Server 2 not warm after {timeout_seconds}s: {last}")


def main() -> int:
    configure()
    if RUN_ROOT.exists():
        def clear_readonly(func, path, _exc):
            os.chmod(path, stat.S_IWRITE)
            func(path)
        shutil.rmtree(RUN_ROOT, onerror=clear_readonly)
    RUN_ROOT.mkdir(parents=True)
    server = None
    try:
        isolated.start_postgres()
        dump_path = isolated.sync_production_database_snapshot()
        provision_user()
        lesson_id = prepare_server_data()
        server = isolated.start_server(no_preload=True, extra_env={"FUTURE_DISTRIBUTED_WORKER_PORT": "18890"})
        health = wait_health(server)
        process = psutil.Process(server.pid)
        token = isolated.login(TEST_USER)

        first = scan(token, lesson_id, process)
        deadline = time.monotonic() + 20
        current = first
        while current["payload"].get("index_pending") and time.monotonic() < deadline:
            time.sleep(0.2)
            current = scan(token, lesson_id, process)
        indexed = current
        canonical_lesson_id = str(indexed["payload"].get("lesson_id") or lesson_id).strip()
        warm_rows = [scan(token, lesson_id, process) for _ in range(10)]

        index_path = isolated.RUNTIME_ROOT / "vocab_file_meta_index_v1.json"
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not index_path.is_file():
            time.sleep(0.1)
        if not index_path.is_file():
            raise RuntimeError("persistent vocabulary index was not written")
        persisted = json.loads(index_path.read_text(encoding="utf-8"))
        index_mtime_before = index_path.stat().st_mtime_ns
        lesson_record = (persisted.get("lessons") or {}).get(canonical_lesson_id) or {}

        isolated.stop_server(server)
        server = isolated.start_server(no_preload=True, extra_env={"FUTURE_DISTRIBUTED_WORKER_PORT": "18890"})
        restart_health = wait_health(server)
        process = psutil.Process(server.pid)
        token = isolated.login(TEST_USER)
        restart_first = scan(token, canonical_lesson_id, process)
        index_mtime_after = index_path.stat().st_mtime_ns

        warm_wall = sorted(row["wall_ms"] for row in warm_rows)
        result = {
            "ok": True,
            "database_sync": {
                "enabled": True,
                "source": isolated.PRODUCTION_DSN,
                "method": "fresh pg_dump + pg_restore before run",
                "dump_bytes": dump_path.stat().st_size,
            },
            "resources": {"http": isolated.BASE, "postgres_port": isolated.PG_PORT, "production_mutated": False},
            "lesson_id": lesson_id,
            "canonical_lesson_id": canonical_lesson_id,
            "first": first,
            "indexed": indexed,
            "warm_10": {
                "p50_ms": warm_wall[len(warm_wall) // 2],
                "max_ms": max(warm_wall),
                "server_cpu_total_ms": round(sum(row["server_cpu_ms"] for row in warm_rows), 3),
                "postgres_cpu_total_ms": round(sum(row["postgres_cpu_ms"] for row in warm_rows), 3),
                "statuses": sorted({row["status"] for row in warm_rows}),
            },
            "persistent": {
                "version": persisted.get("version"),
                "extractor_version": persisted.get("extractor_version"),
                "lesson_rows": len(persisted.get("lessons") or {}),
                "valid_keys": len(lesson_record.get("valid_keys") or []),
                "bytes": index_path.stat().st_size,
                "mtime_unchanged_after_restart": index_mtime_before == index_mtime_after,
            },
            "restart": {"health": restart_health, "first_scan": restart_first},
            "startup": {"ready": health.get("ready"), "warm_ready": health.get("warm_ready")},
        }
        gates = {
            "fresh_snapshot": result["database_sync"]["enabled"],
            "indexed_response": indexed["status"] == 200 and not indexed["payload"].get("index_pending") and int(indexed["payload"].get("new_count", 0) or 0) > 0,
            "warm_responses": result["warm_10"]["statuses"] == [200],
            "persisted_by_lesson_id": bool(lesson_record.get("valid_keys")),
            "restart_reused_index": restart_first["status"] == 200 and not restart_first["payload"].get("index_pending"),
            "restart_did_not_rewrite": index_mtime_before == index_mtime_after,
        }
        result["gates"] = gates
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(json.dumps({"ok": all(gates.values()), "output": str(OUTPUT), "gates": gates}, ensure_ascii=True))
        if not all(gates.values()):
            raise RuntimeError(f"Space_Q vocabulary index isolated gate failed: {gates}")
        return 0
    finally:
        isolated.stop_server(server)
        isolated.stop_postgres()
        shutil.rmtree(RUN_ROOT, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
