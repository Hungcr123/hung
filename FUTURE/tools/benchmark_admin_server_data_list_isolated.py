#!/usr/bin/env python3
"""Fresh-snapshot HTTP benchmark for admin Lesson Vault list/task/file paths."""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import statistics
import sys
import time
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "FUTURE" / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "FUTURE" / "tools"))

import test_lesson_complete_isolated_harness as isolated

RUN_ROOT = ROOT / "programe_cache" / "admin_server_data_list_isolated_18877"
OUTPUT = Path(os.environ.get(
    "FUTURE_ADMIN_LIST_BENCH_OUTPUT",
    r"C:\Users\Admin\.codex\plans\admin_server_data_list_isolated_20260730.json",
))
ADMIN_USER = "codexadminlistperf"
TARGET_USER = "hung"
TARGET_FOLDER = "hung"
COMMON_FOLDER = "common/Study/Empower A1/Space_W/Unit 04"
SYNTHETIC_USERS = 1000


def configure_isolated() -> None:
    isolated.RUN_ROOT = RUN_ROOT
    isolated.PG_ROOT = RUN_ROOT / "postgres"
    isolated.SERVER_DATA_ROOT = RUN_ROOT / "server-data"
    isolated.RUNTIME_ROOT = RUN_ROOT / "runtime"
    isolated.QMLEARN_ROOT = RUN_ROOT / "qml"
    isolated.SERVER_LOG = RUN_ROOT / "server.log"
    isolated.PG_LOG = RUN_ROOT / "postgres.log"
    isolated.OUTPUT_PATH = OUTPUT


def prepare_server_data() -> None:
    for source, relative in (
        (Path(r"C:\server data\hung"), Path("hung")),
        (Path(r"C:\server data\common\Study\Empower A1\Space_W\Unit 04"), Path("common/Study/Empower A1/Space_W/Unit 04")),
    ):
        if not source.is_dir():
            raise RuntimeError(f"missing production fixture: {source}")
        shutil.copytree(source, isolated.SERVER_DATA_ROOT / relative, dirs_exist_ok=True)
    for directory in ("Sound", "Picture", "NPC_TOP"):
        (isolated.SERVER_DATA_ROOT / directory).mkdir(parents=True, exist_ok=True)


def provision_admin_and_scale_users() -> None:
    import psycopg
    from psycopg.types.json import Jsonb

    now = "2026-07-30T00:00:00Z"
    with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO future_server2.users
               (username,is_admin,is_test,profile_json,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
               VALUES (%s,true,true,%s,%s,0,'','')
               ON CONFLICT (username) DO UPDATE SET is_admin=true,is_test=true,profile_json=excluded.profile_json""",
            (ADMIN_USER, Jsonb({"source": "isolated-admin-list-benchmark"}), now),
        )
        cursor.execute(
            """INSERT INTO future_server2.user_auth_credentials
               (username,password_hash,source_path,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
               VALUES (%s,%s,'isolated-admin-list-benchmark',%s,0,'','')
               ON CONFLICT (username) DO UPDATE SET password_hash=excluded.password_hash""",
            (ADMIN_USER, isolated.password_hash(isolated.PASSWORD), now),
        )
        cursor.execute(
            """INSERT INTO future_server2.admin_users
               (username,enabled,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
               VALUES (%s,true,%s,0,'','')
               ON CONFLICT (username) DO UPDATE SET enabled=true""",
            (ADMIN_USER, now),
        )
        rows = [
            (f"codexscale{i:04d}", False, True, Jsonb({"scale_fixture": True}), now, 0.0, "", "")
            for i in range(SYNTHETIC_USERS)
        ]
        cursor.executemany(
            """INSERT INTO future_server2.users
               (username,is_admin,is_test,profile_json,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (username) DO NOTHING""",
            rows,
        )
        connection.commit()


def auth_headers(token: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    if extra:
        headers.update(extra)
    return headers


def request_measure(process: psutil.Process, method: str, url: str, **kwargs) -> dict:
    server_before = sum(process.cpu_times()[:2]) * 1000
    pg_before = isolated.postgres_cpu()
    started = time.perf_counter()
    response = requests.request(method, url, timeout=60, **kwargs)
    wall_ms = (time.perf_counter() - started) * 1000
    server_after = sum(process.cpu_times()[:2]) * 1000
    pg_after = isolated.postgres_cpu()
    return {
        "status": response.status_code,
        "wall_ms": round(wall_ms, 3),
        "server_cpu_ms": round(server_after - server_before, 3),
        "postgres_cpu_ms": round(pg_after - pg_before, 3),
        "bytes": len(response.content),
        "etag": response.headers.get("ETag", ""),
        "cache": response.headers.get("X-Future-Cache-Hit", ""),
        "server_timing": response.headers.get("Server-Timing", ""),
        "json": response.json() if response.content and "json" in response.headers.get("Content-Type", "") else None,
    }


def timing_value(header: str, name: str) -> float:
    match = re.search(rf"(?:^|,\s*){re.escape(name)};dur=([0-9.]+)", header or "")
    return float(match.group(1)) if match else 0.0


def batch(process: psutil.Process, token: str, path: str, count: int, *, fresh: bool = False, etag: str = "") -> dict:
    params = {"path": path, "task_owner": TARGET_USER, "defer_task_board": "1"}
    if fresh:
        params["fresh"] = "1"
    headers = auth_headers(token, {"If-None-Match": etag} if etag else None)
    server_before = sum(process.cpu_times()[:2]) * 1000
    pg_before = isolated.postgres_cpu()
    rows = []
    for _ in range(count):
        started = time.perf_counter()
        response = requests.get(f"{isolated.BASE}/server-data/list", params=params, headers=headers, timeout=60)
        rows.append({
            "status": response.status_code,
            "wall_ms": (time.perf_counter() - started) * 1000,
            "bytes": len(response.content),
            "cache": response.headers.get("X-Future-Cache-Hit", ""),
            "etag": response.headers.get("ETag", ""),
            "server_timing": response.headers.get("Server-Timing", ""),
        })
    server_after = sum(process.cpu_times()[:2]) * 1000
    pg_after = isolated.postgres_cpu()
    walls = sorted(row["wall_ms"] for row in rows)
    return {
        "count": count,
        "status_counts": {str(code): sum(1 for row in rows if row["status"] == code) for code in sorted({row["status"] for row in rows})},
        "p50_ms": round(statistics.median(walls), 3),
        "p95_ms": round(walls[min(len(walls) - 1, int(len(walls) * 0.95))], 3),
        "max_ms": round(max(walls), 3),
        "server_cpu_total_ms": round(server_after - server_before, 3),
        "server_cpu_per_request_ms": round((server_after - server_before) / count, 3),
        "postgres_cpu_total_ms": round(pg_after - pg_before, 3),
        "response_bytes": sorted({row["bytes"] for row in rows}),
        "cache_values": sorted({row["cache"] for row in rows}),
        "last_etag": rows[-1].get("etag", "") if rows else "",
    }


def main() -> int:
    configure_isolated()
    if RUN_ROOT.resolve() == ROOT.resolve() or ROOT.resolve() not in RUN_ROOT.resolve().parents:
        raise RuntimeError(f"unsafe isolated root: {RUN_ROOT}")
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
        provision_admin_and_scale_users()
        prepare_server_data()
        server = isolated.start_server(no_preload=True, extra_env={"FUTURE_WARMUP_MAX_USERS": "50"})
        health = isolated.wait_health(server)
        process = psutil.Process(server.pid)

        login_started = time.perf_counter()
        token = isolated.login(ADMIN_USER)
        login_ms = (time.perf_counter() - login_started) * 1000
        headers = auth_headers(token)

        cold = request_measure(process, "GET", f"{isolated.BASE}/server-data/list", headers=headers, params={
            "path": TARGET_FOLDER, "task_owner": TARGET_USER, "defer_task_board": "1", "fresh": "1",
        })
        cold["entry_file_study_ms"] = timing_value(cold["server_timing"], "list_entry_file_study")
        cold["entry_file_meta_ms"] = timing_value(cold["server_timing"], "list_entry_file_meta")
        ram_fresh = batch(process, token, TARGET_FOLDER, 20, fresh=True)
        normal_cached = batch(process, token, TARGET_FOLDER, 50)
        etag_304_probe = batch(process, token, TARGET_FOLDER, 1)
        etag_304 = batch(process, token, TARGET_FOLDER, 50, etag=etag_304_probe.get("last_etag", ""))

        common_fresh = request_measure(process, "GET", f"{isolated.BASE}/server-data/list", headers=headers, params={
            "path": COMMON_FOLDER, "task_owner": "quynh", "defer_task_board": "1", "fresh": "1",
        })
        common_fresh["entry_file_study_ms"] = timing_value(common_fresh["server_timing"], "list_entry_file_study")
        common_fresh["entry_file_meta_ms"] = timing_value(common_fresh["server_timing"], "list_entry_file_meta")

        lesson_file = next((path for path in (isolated.SERVER_DATA_ROOT / TARGET_FOLDER).rglob("*") if path.is_file() and path.suffix.lower().startswith(".space_")), None)
        if lesson_file is None:
            raise RuntimeError("no target lesson file")
        lesson_rel = lesson_file.relative_to(isolated.SERVER_DATA_ROOT).as_posix()
        file_first = request_measure(process, "GET", f"{isolated.BASE}/server-data/file", headers=headers, params={"path": lesson_rel})
        file_repeat = request_measure(process, "GET", f"{isolated.BASE}/server-data/file", headers=headers, params={"path": lesson_rel})

        task_add = request_measure(process, "POST", f"{isolated.BASE}/lesson-tasks", headers={**headers, "Content-Type": "application/json"}, json={
            "action": "add", "user": TARGET_USER, "path": lesson_rel, "title": lesson_file.stem,
        })
        folder_task_add = request_measure(process, "POST", f"{isolated.BASE}/lesson-tasks", headers={**headers, "Content-Type": "application/json"}, json={
            "action": "space-folders", "user": TARGET_USER, "folders": [COMMON_FOLDER],
        })
        folder_task_retry = request_measure(process, "POST", f"{isolated.BASE}/lesson-tasks", headers={**headers, "Content-Type": "application/json"}, json={
            "action": "space-folders", "user": TARGET_USER, "folders": [COMMON_FOLDER],
            "baseRevision": ((folder_task_add.get("json") or {}).get("space_task") or {}).get("revision"),
        })
        task_read = request_measure(process, "GET", f"{isolated.BASE}/lesson-tasks", headers=headers, params={"user": TARGET_USER})

        index_path = isolated.RUNTIME_ROOT / "vocab_file_meta_index_v1.json"
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not index_path.is_file():
            time.sleep(0.1)
        index_bytes = index_path.stat().st_size if index_path.is_file() else 0

        isolated.stop_server(server)
        server = isolated.start_server(no_preload=True, extra_env={"FUTURE_WARMUP_MAX_USERS": "50"})
        restart_health = isolated.wait_health(server)
        process = psutil.Process(server.pid)
        token = isolated.login(ADMIN_USER)
        persistent_fresh = request_measure(process, "GET", f"{isolated.BASE}/server-data/list", headers=auth_headers(token), params={
            "path": TARGET_FOLDER, "task_owner": TARGET_USER, "defer_task_board": "1", "fresh": "1",
        })
        persistent_fresh["entry_file_study_ms"] = timing_value(persistent_fresh["server_timing"], "list_entry_file_study")
        persistent_fresh["entry_file_meta_ms"] = timing_value(persistent_fresh["server_timing"], "list_entry_file_meta")
        tasks_after_restart = request_measure(process, "GET", f"{isolated.BASE}/lesson-tasks", headers=auth_headers(token), params={"user": TARGET_USER})

        result = {
            "ok": True,
            "database_sync": {
                "enabled": True,
                "source": isolated.PRODUCTION_DSN,
                "method": "fresh pg_dump + pg_restore before run",
                "dump_bytes": dump_path.stat().st_size,
            },
            "resources": {"http": isolated.BASE, "postgres_port": isolated.PG_PORT, "production_mutated": False},
            "scale": {"synthetic_users": SYNTHETIC_USERS, "warmup_max_users": 50},
            "health": {"pid": health.get("pid"), "ready": health.get("ready"), "warm_ready": health.get("warm_ready")},
            "login_ms": round(login_ms, 3),
            "admin_hung_cold_fresh": cold,
            "admin_hung_ram_fresh_20": ram_fresh,
            "admin_hung_cached_50": normal_cached,
            "admin_hung_etag_304_50": etag_304,
            "admin_quynh_common_fresh": common_fresh,
            "admin_file_open_first": file_first,
            "admin_file_open_repeat": file_repeat,
            "admin_add_file_task": task_add,
            "admin_add_folder_task": folder_task_add,
            "admin_add_folder_task_retry": folder_task_retry,
            "admin_read_tasks": task_read,
            "persistent_index_bytes": index_bytes,
            "restart": {"pid": restart_health.get("pid"), "ready": restart_health.get("ready"), "warm_ready": restart_health.get("warm_ready")},
            "admin_hung_persistent_fresh_after_restart": persistent_fresh,
            "admin_tasks_after_restart": tasks_after_restart,
            "production_log_baseline_ms": {"hung_min": 2471, "hung_max": 3382, "quynh_min": 635, "quynh_max": 670},
        }
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"ok": True, "output": str(OUTPUT), "pid": server.pid}, ensure_ascii=False))
        return 0
    finally:
        isolated.stop_server(server)
        isolated.stop_postgres()


if __name__ == "__main__":
    raise SystemExit(main())
