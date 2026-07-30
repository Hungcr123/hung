"""Run an isolated SQLite rollback drill with PostgreSQL flags disabled."""

from __future__ import annotations

import json
import os
import base64
import hashlib
import secrets
import subprocess
import sys
import time
import sqlite3
import shutil
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).resolve().parents[2]
BASE = "http://127.0.0.1:18877"
SNAPSHOT_ROOT = Path(r"E:\FutureServer2PostgresMigrationBackups\20260726_snapshot_baseline_20260726_032052")


def port_pid(port: int) -> int:
    for connection in psutil.net_connections(kind="tcp"):
        if connection.laddr and connection.laddr.port == port and connection.status == psutil.CONN_LISTEN and connection.pid:
            return int(connection.pid)
    return 0


def stop_pid(pid: int) -> None:
    if not pid:
        return
    try:
        process = psutil.Process(pid)
        process.kill()
        process.wait(timeout=20)
    except psutil.NoSuchProcess:
        pass


def wait_health(pid: int, timeout: float = 120.0) -> dict:
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        try:
            response = requests.get(f"{BASE}/health", timeout=5)
            last = f"{response.status_code} {response.text[:160]}"
            payload = response.json()
            if response.status_code == 200 and payload.get("ok") and int(payload.get("pid", 0) or 0) == pid:
                return payload
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(0.5)
    raise RuntimeError(f"Server 2 did not become healthy: {last}")


def make_env() -> dict:
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("FUTURE_DB_") or key.startswith("FUTURE_POSTGRES_"):
            env.pop(key, None)
    env.pop("FUTURE_PG_DSN", None)
    env["FUTURE_SERVER_DATA_ROOT"] = str(SNAPSHOT_ROOT / "server data")
    env["FUTURE_QMLEARN_ROOT"] = str(SNAPSHOT_ROOT / "QMLearn")
    env["FUTURE_SERVER2_SQLITE_DB"] = str(SNAPSHOT_ROOT / "server data" / "server2.db")
    env.pop("FUTURE_BENCHMARK_LOCAL_LOGIN", None)
    env["FUTURE_DISABLE_AUTH_LIMITS_FOR_BENCHMARK"] = "1"
    env["FUTURE_BENCHMARK_RAW_PDF_PATHS"] = "common/benchmark_fixtures/codex_cold_ocr_fixture.pdf"
    env["FUTURE_TEST_PASSWORD"] = "sqlite-rollback-drill-only"
    return env


def seed_test_password(db_path: Path) -> str:
    sys.path.insert(0, str(ROOT))
    import FUTURE.server_app as app
    password = secrets.token_urlsafe(18)
    password_hash = app.password_hash(password)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    con = sqlite3.connect(str(db_path), timeout=30)
    try:
        con.execute("BEGIN IMMEDIATE")
        for index in range(1, 101):
            username = f"codexload{index:03d}"
            profile = json.dumps(
                {"full_name": f"Server Load Test {index:03d}", "intro": "SQLite-only Server 2 load-test identity.", "load_test": True},
                ensure_ascii=True,
                separators=(",", ":"),
            )
            con.execute(
                "INSERT INTO users(username,is_admin,is_test,profile_json,updated_at_utc) VALUES(?,0,1,?,?) "
                "ON CONFLICT(username) DO UPDATE SET is_admin=0,is_test=1,profile_json=excluded.profile_json,updated_at_utc=excluded.updated_at_utc",
                (username, profile, now),
            )
            con.execute(
                "INSERT INTO server_load_test_credentials(username,password_hash,updated_at_utc) VALUES(?,?,?) "
                "ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash,updated_at_utc=excluded.updated_at_utc",
                (username, password_hash, now),
            )
        con.commit()
    finally:
        con.close()
    return password


def verify_seeded_password(db_path: Path, password: str) -> dict:
    sys.path.insert(0, str(ROOT))
    import FUTURE.server_app as app
    con = sqlite3.connect(str(db_path), timeout=30)
    try:
        row = con.execute(
            "SELECT password_hash FROM server_load_test_credentials WHERE username='codexload001'"
        ).fetchone()
    finally:
        con.close()
    stored = str(row[0] or "") if row else ""
    return {
        "row_present": bool(row),
        "hash_prefix": stored.split("$", 1)[0] if stored else "",
        "matches": bool(stored and app.password_hash_matches(password, stored)),
    }


def cleanup_seeded_users(db_path: Path) -> dict:
    tables = [
        "auth_sessions",
        "inventory_events",
        "inventory_items",
        "pdf_drawings",
        "lesson_time",
        "lesson_progress",
        "lesson_progress_namespaces",
        "user_preferences",
        "lesson_last_file",
        "lesson_task_state",
        "vocabulary_events",
        "vocabulary_registry",
        "server_load_test_credentials",
        "users",
    ]
    deleted: dict[str, int | str] = {}
    remaining: dict[str, int | str] = {}
    con = sqlite3.connect(str(db_path), timeout=30)
    try:
        con.execute("BEGIN IMMEDIATE")
        for table in tables:
            try:
                if table == "users":
                    cursor = con.execute("DELETE FROM users WHERE is_test=1 AND lower(username) LIKE 'codexload%'")
                else:
                    cursor = con.execute(f"DELETE FROM {table} WHERE lower(username) LIKE 'codexload%'")
                deleted[table] = int(cursor.rowcount or 0)
            except Exception as exc:
                deleted[table] = type(exc).__name__
        con.commit()
        for table in tables:
            try:
                if table == "users":
                    remaining[table] = int(con.execute("SELECT COUNT(*) FROM users WHERE is_test=1 AND lower(username) LIKE 'codexload%'").fetchone()[0] or 0)
                else:
                    remaining[table] = int(con.execute(f"SELECT COUNT(*) FROM {table} WHERE lower(username) LIKE 'codexload%'").fetchone()[0] or 0)
            except Exception as exc:
                remaining[table] = type(exc).__name__
    finally:
        con.close()
    user_root = SNAPSHOT_ROOT / "QMLearn" / "users"
    files_deleted = 0
    folders_deleted = 0
    if user_root.exists():
        for index in range(1, 101):
            username = f"codexload{index:03d}"
            user_file = user_root / f"{username}.txt"
            if user_file.exists():
                user_file.unlink()
                files_deleted += 1
            user_folder = user_root / username
            if user_folder.exists():
                shutil.rmtree(user_folder)
                folders_deleted += 1
    return {
        "sqlite_deleted": deleted,
        "sqlite_remaining": remaining,
        "local_login_files_deleted": files_deleted,
        "local_login_folders_deleted": folders_deleted,
        "remaining_seed_rows": sum(value for value in remaining.values() if isinstance(value, int)),
    }


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from FUTURE.tools import test_full_system_mixed_workload_gate as full_gate  # noqa: E402
    env = make_env()
    os.environ.update(env)
    old_pid = port_pid(18877)
    if old_pid:
        stop_pid(old_pid)
    started = time.perf_counter()
    log_path = Path.home() / ".codex" / "plans" / "server2_sqlite_rollback_drill_18877.log"
    output_path = Path.home() / ".codex" / "plans" / "server2_sqlite_rollback_drill_2026-07-26.json"
    log_handle = log_path.open("w", encoding="utf-8")
    process = None
    try:
        fixture = full_gate.prepare_asset_fixture()
        password = str(fixture.pop("password"))
        env["FUTURE_TEST_PASSWORD"] = password
        os.environ["FUTURE_TEST_PASSWORD"] = password
        if fixture.get("raw_pdf_paths"):
            raw_pdf_env = ";".join(str(item) for item in fixture["raw_pdf_paths"])
            env["FUTURE_BENCHMARK_RAW_PDF_PATHS"] = raw_pdf_env
            os.environ["FUTURE_BENCHMARK_RAW_PDF_PATHS"] = raw_pdf_env
        process = subprocess.Popen(
            [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--host", "127.0.0.1", "--port", "18877", "--no-browser", "--no-tunnel", "--no-preload"],
            cwd=ROOT,
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        health = wait_health(process.pid)
        smoke_cmd = [
            sys.executable,
            str(ROOT / "FUTURE" / "tools" / "benchmark_server2_mixed_100_users.py"),
            "--profile",
            "smoke",
            "--disable-ocr",
            "--skip-idle-gate",
            "--output",
            str(output_path),
        ]
        run = subprocess.run(smoke_cmd, cwd=ROOT, env=env, text=True, capture_output=True, timeout=3600)
        benchmark_payload = {}
        try:
            benchmark_payload = json.loads(output_path.read_text(encoding="utf-8"))
        except Exception:
            benchmark_payload = {}
        phases = benchmark_payload.get("phases") if isinstance(benchmark_payload.get("phases"), list) else []
        total_requests = sum(int(phase.get("requests", 0) or 0) for phase in phases if isinstance(phase, dict))
        total_errors = sum(int(phase.get("errors", 0) or 0) for phase in phases if isinstance(phase, dict))
        total_timeouts = sum(int(phase.get("timeouts", 0) or 0) for phase in phases if isinstance(phase, dict))
        cleanup = cleanup_seeded_users(SNAPSHOT_ROOT / "server data" / "server2.db")
        server_pid = process.pid
        stop_pid(server_pid)
        process = None
        port_after_shutdown = port_pid(18877)
        summary = {
            "ok": run.returncode == 0 and bool(health.get("ok")) and not health.get("postgres_probe") and port_after_shutdown == 0,
            "server_pid": server_pid,
            "health_ok": bool(health.get("ok")),
            "postgres_probe": health.get("postgres_probe", {}),
            "server_data_root": health.get("server_data_root", ""),
            "qmlearn_root": health.get("qmlearn_root", ""),
            "postgres_flags_disabled": True,
            "postgres_dsn_present": False,
            "fixture": fixture,
            "benchmark": {
                "profile": "smoke",
                "requests": total_requests,
                "errors": total_errors,
                "timeouts": total_timeouts,
                "exit_code": run.returncode,
            },
            "cleanup": cleanup,
            "port_18877_pid_after_shutdown": port_after_shutdown,
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            "output": str(output_path),
            "exit_code": run.returncode,
            "stdout_tail": run.stdout[-6000:],
            "stderr_tail": run.stderr[-4000:],
        }
        output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary["ok"] else 2
    finally:
        if process and process.poll() is None:
            stop_pid(process.pid)
        if log_handle:
            log_handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
