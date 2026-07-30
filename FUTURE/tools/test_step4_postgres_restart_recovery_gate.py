#!/usr/bin/env python3
"""Step 4 isolated PostgreSQL restart/recovery gate for Server 2 readiness."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE.tools import benchmark_server2_mixed_100_users as mixed  # noqa: E402
from FUTURE.tools import test_full_system_mixed_workload_gate as full_gate  # noqa: E402

BASE = full_gate.BASE


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def request_json(method: str, path: str, token: str = "", **kwargs) -> tuple[int, dict]:
    headers = dict(kwargs.pop("headers", {}) or {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.request(method, f"{BASE}{path}", headers=headers, timeout=kwargs.pop("timeout", 45), **kwargs)
    payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
    return int(response.status_code), payload


def start_server(env: dict, log_path: Path) -> subprocess.Popen:
    handle = log_path.open("ab")
    return subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--host", "127.0.0.1", "--port", "18877", "--no-browser", "--no-tunnel", "--no-preload"],
        cwd=ROOT,
        env=env,
        stdout=handle,
        stderr=handle,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def stop_server(process: subprocess.Popen | None) -> None:
    if process and process.poll() is None:
        full_gate.stop_pid(process.pid)


def restart_postgres_service() -> dict:
    script = r"""
$svc = Get-Service -Name postgresql-x64-17 -ErrorAction SilentlyContinue
if (-not $svc) { $svc = Get-Service | Where-Object { $_.Name -like 'postgresql*' } | Select-Object -First 1 }
if (-not $svc) { @{ok=$false; reason='service_not_found'} | ConvertTo-Json -Compress; exit 0 }
$name = $svc.Name
$before = $svc.Status.ToString()
Restart-Service -Name $name -Force -ErrorAction Stop
$svc.WaitForStatus('Running', [TimeSpan]::FromSeconds(60))
@{ok=$true; service=$name; before=$before; after=(Get-Service -Name $name).Status.ToString()} | ConvertTo-Json -Compress
"""
    started = time.perf_counter()
    run = subprocess.run(["powershell", "-NoProfile", "-Command", script], text=True, capture_output=True, timeout=90)
    payload = {}
    try:
        payload = json.loads(run.stdout.strip() or "{}")
    except Exception:
        payload = {"ok": False, "parse_error": run.stdout[-300:]}
    payload["exit_code"] = int(run.returncode)
    payload["duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
    if run.stderr:
        payload["stderr_tail"] = run.stderr[-500:]
    return payload


def login(username: str, password: str) -> str:
    status, payload = request_json("POST", "/auth/login", json={"username": username, "password": password})
    if status != 200 or not payload.get("token") or (payload.get("server_data") or {}).get("load_test") is not True:
        raise RuntimeError({"reason": "login_failed", "username": username, "status": status, "payload": payload})
    return str(payload["token"])


def make_users(password: str) -> tuple[mixed.MixedUser, mixed.MixedUser, str, str]:
    mixed.BASE = BASE
    mixed.legacy.BASE = BASE
    mixed.DATABASE = full_gate.SNAPSHOT_ROOT / "server data" / "server2.db"
    mixed.legacy.DATABASE = mixed.DATABASE
    mixed.MANIFEST = full_gate.SNAPSHOT_ROOT / "server data" / "_future_server_data_manifest.json"
    mixed.legacy.MANIFEST = mixed.MANIFEST
    spaces, pdfs, raw_pdfs, lesson_ids, _identity_audit = mixed.load_paths_by_space()
    lesson = spaces["space_v"][0]
    pdf = pdfs[0]
    token1 = login(mixed.USERS[0], password)
    token2 = login(mixed.USERS[1], password)
    user1 = mixed.MixedUser(
        0,
        mixed.USERS[0],
        token1,
        lesson,
        pdf,
        20260726,
        role="space_v",
        password=password,
        lesson_id=lesson_ids[lesson],
        pdf_lesson_id=lesson_ids[pdf],
        raw_pdf_path=raw_pdfs[0] if raw_pdfs else pdf,
    )
    user2 = mixed.MixedUser(
        1,
        mixed.USERS[1],
        token2,
        lesson,
        pdf,
        20260726,
        role="mixed",
        password=password,
        lesson_id=lesson_ids[lesson],
        pdf_lesson_id=lesson_ids[pdf],
        raw_pdf_path=raw_pdfs[0] if raw_pdfs else pdf,
    )
    return user1, user2, token1, token2


def assert_ok_rows(label: str, rows: list[dict], allowed=(200, 304, 429)) -> None:
    bad = [row for row in rows if row.get("error") or int(row.get("status", 0) or 0) not in allowed]
    if bad:
        raise RuntimeError({"reason": f"{label}_failed", "bad": bad[:5]})


def run_gate(output: Path) -> dict:
    env = full_gate.make_env()
    fixture = full_gate.prepare_asset_fixture()
    password = str(fixture.pop("password"))
    env["FUTURE_TEST_PASSWORD"] = password
    if fixture.get("raw_pdf_paths"):
        raw_pdf_env = ";".join(str(item) for item in fixture["raw_pdf_paths"])
        env["FUTURE_BENCHMARK_RAW_PDF_PATHS"] = raw_pdf_env
        os.environ["FUTURE_BENCHMARK_RAW_PDF_PATHS"] = raw_pdf_env
    log_path = Path.home() / ".codex" / "plans" / "server2_postgres_step4_restart_recovery_18877.log"
    cleanup_before = full_gate.cleanup_workload_state(env)
    process: subprocess.Popen | None = None
    evidence: dict = {
        "started_at_utc": utc_now(),
        "port": 18877,
        "database": "future_server2_readiness_20260726",
        "fixture": fixture,
        "production_8877_touched": False,
    }
    try:
        process = start_server(env, log_path)
        health1 = full_gate.wait_health(process.pid)
        user1, user2, token1, token2 = make_users(password)

        committed_rows = [
            user1.request("progress_write"),
            user1.request("progress_retry"),
            user1.request("lesson_time_write"),
            user2.request("inventory_write"),
            user1.request("pdf_progress_write"),
            user1.request("drawing_write"),
            user1.request("leaderboard_read"),
            user1.request("tree_read"),
            user1.request("tasks_read"),
        ]
        assert_ok_rows("initial_commit", committed_rows)

        run_id = f"step4-complete-{uuid.uuid4().hex}"
        stamp = utc_now()
        complete_body = {
            "path": user1.lesson_path,
            "lesson_id": user1.lesson_id,
            "file_id": user1.lesson_id,
            "title": "Codex Step4 Completion",
            "nodes": 1,
            "completed_at": stamp,
            "completion_run_id": run_id,
            "source": "Space_V",
        }
        complete1 = request_json("POST", "/lesson/complete", token1, json=complete_body, timeout=60)
        complete_retry = request_json("POST", "/lesson/complete", token1, json=complete_body, timeout=60)
        if complete1[0] != 200 or complete_retry[0] != 200:
            raise RuntimeError({"reason": "completion_retry_failed", "first": complete1, "retry": complete_retry})

        before_restart_reads = [
            user1.request("progress_read"),
            user1.request("lesson_time_write", replay=True),
            user2.request("inventory_read"),
            user1.request("pdf_progress_read"),
            user1.request("drawing_read"),
            user1.request("leaderboard_read"),
        ]
        assert_ok_rows("before_restart_readback", before_restart_reads)

        old_pid = process.pid
        stop_server(process)
        process = start_server(env, log_path)
        health2 = full_gate.wait_health(process.pid)
        user1b, user2b, token1b, _token2b = make_users(password)
        after_server_restart = [
            user1b.request("progress_read"),
            user1b.request("progress_retry"),
            user1b.request("lesson_time_write", replay=True),
            user2b.request("inventory_read"),
            user1b.request("pdf_progress_read"),
            user1b.request("drawing_read"),
            user1b.request("leaderboard_read"),
        ]
        assert_ok_rows("server_restart_readback", after_server_restart)
        complete_after_restart = request_json("POST", "/lesson/complete", token1b, json=complete_body, timeout=60)
        if complete_after_restart[0] != 200 or not complete_after_restart[1].get("ok"):
            raise RuntimeError({"reason": "completion_after_restart_failed", "response": complete_after_restart})

        pg_restart = restart_postgres_service()
        time.sleep(2.0)
        health3 = full_gate.wait_health(process.pid, timeout=120)
        token_after_pg = login(mixed.USERS[0], password)
        user1c = mixed.MixedUser(
            0,
            mixed.USERS[0],
            token_after_pg,
            user1.lesson_path,
            user1.pdf_path,
            20260726,
            role="space_v",
            password=password,
            lesson_id=user1.lesson_id,
            pdf_lesson_id=user1.pdf_lesson_id,
            raw_pdf_path=user1.raw_pdf_path,
        )
        after_pg_restart = [
            user1c.request("progress_read"),
            user1c.request("progress_retry"),
            user1c.request("lesson_time_write"),
            user1c.request("pdf_progress_read"),
            user1c.request("drawing_read"),
            user1c.request("leaderboard_read"),
        ]
        assert_ok_rows("postgres_restart_readback", after_pg_restart)

        invalid_progress = request_json("POST", "/lesson/time", token_after_pg, json={"path": "", "seconds": -999, "sequence": -1}, timeout=45)
        unauthorized = request_json("GET", "/inventory", token="", timeout=30)
        if invalid_progress[0] not in {400, 422} or invalid_progress[1].get("ok") is not False:
            raise RuntimeError({"reason": "invalid_payload_not_rejected", "response": invalid_progress})
        if unauthorized[0] != 401:
            raise RuntimeError({"reason": "unauthorized_read_not_rejected", "response": unauthorized})

        evidence.update({
            "ok": True,
            "server_restart": {"old_pid": old_pid, "new_pid": process.pid, "health_before": health1.get("postgres_probe", {}), "health_after": health2.get("postgres_probe", {})},
            "postgres_restart": pg_restart,
            "health_after_postgres_restart": health3.get("postgres_probe", {}),
            "initial_commit": committed_rows,
            "before_restart_readback": before_restart_reads,
            "after_server_restart": after_server_restart,
            "after_postgres_restart": after_pg_restart,
            "completion_retry": {"first_status": complete1[0], "retry_status": complete_retry[0], "after_restart_status": complete_after_restart[0], "deduplicated": bool(complete_retry[1].get("deduplicated") or complete_after_restart[1].get("deduplicated"))},
            "invalid_payload": {"status": invalid_progress[0], "ok": bool(invalid_progress[1].get("ok"))},
            "unauthorized_read": {"status": unauthorized[0]},
        })
    finally:
        stop_server(process)
        cleanup = full_gate.cleanup_workload_state(env)
        evidence["cleanup_before"] = cleanup_before
        evidence["cleanup"] = cleanup
        evidence["cleanup_summary"] = {
            "temporary_workload_rows": sum(full_gate._count_value(value) for key, value in (cleanup.get("sqlite_remaining", {}) or {}).items() if key not in {"users", "credentials"})
            + sum(full_gate._count_value(value) for value in (cleanup.get("pg_remaining", {}) or {}).values())
            + full_gate._count_value(cleanup.get("local_login_fixture_files_remaining", 0)),
            "unexpected_test_rows": sum(full_gate._count_value(value) for key, value in (cleanup.get("sqlite_remaining", {}) or {}).items() if key not in {"users", "credentials"})
            + sum(full_gate._count_value(value) for value in (cleanup.get("pg_remaining", {}) or {}).values())
            + full_gate._count_value(cleanup.get("local_login_fixture_files_remaining", 0)),
        }
        evidence["port_18877_pid_after_shutdown"] = full_gate.port_pid(18877)
        evidence["finished_at_utc"] = utc_now()
        output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    return evidence


def main() -> int:
    output = Path.home() / ".codex" / "plans" / "server2_postgres_step4_restart_recovery_2026-07-26.json"
    try:
        evidence = run_gate(output)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc), "output": str(output)}, ensure_ascii=True, indent=2))
        return 2
    ok = bool(evidence.get("ok")) and evidence.get("cleanup_summary", {}).get("unexpected_test_rows") == 0 and evidence.get("port_18877_pid_after_shutdown") == 0
    print(json.dumps({"ok": ok, "output": str(output), "summary": evidence.get("cleanup_summary"), "port_18877_pid_after_shutdown": evidence.get("port_18877_pid_after_shutdown")}, ensure_ascii=True, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
