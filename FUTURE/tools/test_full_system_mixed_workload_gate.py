#!/usr/bin/env python3
"""Run the mixed 100-user benchmark against an isolated PostgreSQL readiness server."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import base64
import hashlib
import secrets
import subprocess
import sys
import time
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).resolve().parents[2]
BASE = "http://127.0.0.1:18877"
SNAPSHOT_ROOT = Path(r"E:\FutureServer2PostgresMigrationBackups\20260726_snapshot_baseline_20260726_032052")

APPROVED_FLAGS = (
    "FUTURE_DB_AUTH_BACKEND",
    "FUTURE_DB_USER_AUTH_DOCS_BACKEND",
    "FUTURE_DB_USER_PREFERENCES_BACKEND",
    "FUTURE_DB_LESSON_LAST_FILE_BACKEND",
    "FUTURE_DB_LESSON_PROGRESS_BACKEND",
    "FUTURE_DB_APPEND_EVENTS_BACKEND",
    "FUTURE_DB_VOCABULARY_BACKEND",
    "FUTURE_DB_LEADERBOARD_DOCUMENTS_BACKEND",
    "FUTURE_DB_INVENTORY_BACKEND",
    "FUTURE_DB_LESSON_TIME_BACKEND",
    "FUTURE_DB_PDF_DRAWINGS_BACKEND",
    "FUTURE_DB_LESSON_TASK_BACKEND",
    "FUTURE_DB_LESSON_IDENTITY_BACKEND",
    "FUTURE_DB_VAULT_METADATA_BACKEND",
    "FUTURE_DB_LESSON_FOLDER_LINKS_BACKEND",
    "FUTURE_DB_CHAT_BACKEND",
    "FUTURE_DB_LEARNING_SUMMARY_DOCUMENTS_BACKEND",
    "FUTURE_DB_AI_HISTORY_DOCUMENTS_BACKEND",
    "FUTURE_DB_VIEWER_TOOL_DOCUMENTS_BACKEND",
    "FUTURE_DB_QM_CITY_DOCUMENTS_BACKEND",
    "FUTURE_DB_ANNOUNCEMENTS_BACKEND",
    "FUTURE_DB_LESSON_TASK_NOTICES_BACKEND",
    "FUTURE_DB_SPACE_W_SPEAK_SKIP_BACKEND",
    "FUTURE_DB_SPACE_PDF_AI_DOCUMENTS_BACKEND",
    "FUTURE_DB_VOCAB_IMAGE_CACHE_BACKEND",
)
SPACE_SUFFIXES = (".space_v", ".space_w", ".space_q", ".space_p", ".space_l", ".space_s")


def readiness_dsn() -> str:
    dsn = os.environ.get("FUTURE_PG_DSN", "")
    if not dsn:
        raise RuntimeError("FUTURE_PG_DSN is required")
    query = ""
    base = dsn
    if "?" in dsn:
        base, query = dsn.split("?", 1)
        query = "?" + query
    at_index = base.rfind("@")
    slash_index = base.find("/", at_index + 1 if at_index >= 0 else base.find("://") + 3)
    if slash_index < 0:
        raise RuntimeError("FUTURE_PG_DSN must include a database path")
    return base[:slash_index] + "/future_server2_readiness_20260726" + query


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
    raise RuntimeError(f"Server 18877 did not become healthy: {last}")


def cleanup_workload_state(env: dict) -> dict:
    tables = [
        "auth_sessions",
        "inventory_events",
        "inventory_items",
        "pdf_drawings",
        "lesson_time",
        "lesson_progress",
        "user_preferences",
        "lesson_last_file",
        "lesson_task_state",
        "vocabulary_events",
        "vocabulary_registry",
    ]
    code = r"""
import json, os, sqlite3, sys
from pathlib import Path
sys.path.insert(0, r'C:\programe\write_html')
import FUTURE.server_app as app
app.postgres_initialize_schema()
tables = %r
def cleanup_pg(con):
    deleted = {}
    with con.cursor() as c:
        for table in tables:
            c.execute(f"DELETE FROM future_server2.{table} WHERE lower(username) LIKE 'codexload%%'")
            deleted[table] = int(c.rowcount or 0)
    return deleted
def baseline_pg(con):
    with con.cursor() as c:
        c.execute("SELECT count(*) FROM future_server2.users WHERE lower(username) LIKE 'codexload%%'")
        users = int(c.fetchone()[0] or 0)
        c.execute("SELECT count(*) FROM future_server2.user_auth_credentials WHERE lower(username) LIKE 'codexload%%'")
        creds = int(c.fetchone()[0] or 0)
    return {"users": users, "credentials": creds}
def counts_pg(con):
    remaining = {}
    with con.cursor() as c:
        for table in tables:
            c.execute(f"SELECT count(*) FROM future_server2.{table} WHERE lower(username) LIKE 'codexload%%'")
            remaining[table] = int(c.fetchone()[0] or 0)
    return remaining
pg_before = app.postgres_execute(baseline_pg)
pg_deleted = app.postgres_execute(cleanup_pg)
pg_remaining = app.postgres_execute(counts_pg)
sqlite_path = os.environ.get('FUTURE_SERVER2_SQLITE_DB')
sqlite_deleted = {}
sqlite_remaining = {}
con = sqlite3.connect(sqlite_path, timeout=30)
try:
    sqlite_before = {
        "users": int(con.execute("SELECT count(*) FROM users WHERE is_test=1 AND lower(username) LIKE 'codexload%%'").fetchone()[0] or 0),
        "credentials": int(con.execute("SELECT count(*) FROM server_load_test_credentials WHERE lower(username) LIKE 'codexload%%'").fetchone()[0] or 0),
    }
    con.execute('BEGIN IMMEDIATE')
    for table in tables:
        try:
            cur = con.execute(f"DELETE FROM {table} WHERE lower(username) LIKE 'codexload%%'")
            sqlite_deleted[table] = int(cur.rowcount or 0)
        except Exception as exc:
            sqlite_deleted[table] = str(exc)
    con.commit()
    for table in tables:
        try:
            sqlite_remaining[table] = int(con.execute(f"SELECT count(*) FROM {table} WHERE lower(username) LIKE 'codexload%%'").fetchone()[0] or 0)
        except Exception as exc:
            sqlite_remaining[table] = str(exc)
    sqlite_remaining["users"] = int(con.execute("SELECT count(*) FROM users WHERE is_test=1 AND lower(username) LIKE 'codexload%%'").fetchone()[0] or 0)
    sqlite_remaining["credentials"] = int(con.execute("SELECT count(*) FROM server_load_test_credentials WHERE lower(username) LIKE 'codexload%%'").fetchone()[0] or 0)
finally:
    con.close()
local_login_files = []
user_root = Path(os.environ.get('FUTURE_QMLEARN_ROOT', r'C:\QMLearn')) / 'users'
if user_root.exists():
    local_login_files = [str(path) for path in user_root.glob('codexload*.txt')]
print(json.dumps({'pg_before': pg_before, 'pg_deleted': pg_deleted, 'pg_remaining': pg_remaining, 'sqlite_before': sqlite_before, 'sqlite_deleted': sqlite_deleted, 'sqlite_remaining': sqlite_remaining, 'local_login_fixture_files_remaining': len(local_login_files)}, indent=2))
""" % tables
    run = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, text=True, capture_output=True, timeout=60)
    try:
        payload = json.loads(run.stdout)
    except Exception:
        payload = {"stdout": run.stdout[-2000:], "stderr": run.stderr[-2000:]}
    payload["exit_code"] = run.returncode
    return payload

def _count_value(value: object) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def make_env() -> dict:
    env = dict(os.environ)
    env["FUTURE_PG_DSN"] = readiness_dsn()
    env["FUTURE_BENCHMARK_BASE"] = BASE
    env["FUTURE_READINESS_PROBE"] = "1"
    env["FUTURE_SERVER_DATA_ROOT"] = str(SNAPSHOT_ROOT / "server data")
    env["FUTURE_QMLEARN_ROOT"] = str(SNAPSHOT_ROOT / "QMLearn")
    env["FUTURE_SERVER2_SQLITE_DB"] = str(SNAPSHOT_ROOT / "server data" / "server2.db")
    env.pop("FUTURE_BENCHMARK_LOCAL_LOGIN", None)
    env.pop("FUTURE_DB_BACKEND", None)
    env.pop("FUTURE_POSTGRES_BACKEND", None)
    env.pop("FUTURE_DB_SYSTEM_DOCUMENTS_BACKEND", None)
    for flag in APPROVED_FLAGS:
        env[flag] = "postgres"
    return env


def prepare_asset_fixture() -> dict:
    source_root = Path(r"C:\server data")
    target_root = SNAPSHOT_ROOT / "server data"
    user_root = SNAPSHOT_ROOT / "QMLearn" / "users"
    db_path = target_root / "server2.db"
    password = secrets.token_urlsafe(18)
    selected: list[str] = []
    manifest_rows = []
    suffix_hits: dict[str, str] = {}
    pdfs: list[str] = []
    connection = sqlite3.connect(db_path)
    try:
        rows = [
            str(row[0] or "")
            for row in connection.execute(
                "SELECT normalized_path FROM lesson_file_aliases WHERE active=1 AND normalized_path LIKE 'common/%' ORDER BY normalized_path COLLATE NOCASE"
            ).fetchall()
        ]
    finally:
        connection.close()
    for path in rows:
        lower = path.lower()
        if lower.endswith(SPACE_SUFFIXES):
            suffix = next(item for item in SPACE_SUFFIXES if lower.endswith(item))
            if suffix not in suffix_hits and (source_root / path).is_file():
                suffix_hits[suffix] = path
        elif lower.endswith((".pdf", ".space_pdf")) and len(pdfs) < 10 and (source_root / path).is_file():
            pdfs.append(path)
        if len(suffix_hits) == len(SPACE_SUFFIXES) and len(pdfs) >= 10:
            break
    missing = [suffix for suffix in SPACE_SUFFIXES if suffix not in suffix_hits]
    if missing or len(pdfs) < 10:
        raise RuntimeError(f"Missing asset fixture paths: spaces={missing}, pdfs={len(pdfs)}")
    removed_local_login_files = 0
    if user_root.exists():
        for target in user_root.glob("codexload*.txt"):
            target.unlink(missing_ok=True)
            removed_local_login_files += 1
    selected = list(suffix_hits.values()) + pdfs
    copied = 0
    for rel_path in selected:
        source = source_root / rel_path
        target = target_root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file() or target.stat().st_size != source.stat().st_size:
            shutil.copy2(source, target)
            copied += 1
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        lower = rel_path.lower()
        manifest_rows.append({
            "source": str(source),
            "destination": str(target),
            "type": "space_pdf" if lower.endswith(".space_pdf") else "pdf" if lower.endswith(".pdf") else "space",
            "size": int(target.stat().st_size),
            "sha256": digest,
            "copied_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "note": "benchmark asset fixture copied after T0; not evidence of T0 source/destination parity",
        })
    raw_pdf_paths = [path for path in pdfs if path.lower().endswith(".pdf")]
    if not raw_pdf_paths:
        rel_path = "common/benchmark_fixtures/codex_cold_ocr_fixture.pdf"
        target = target_root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            import fitz  # PyMuPDF
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.insert_text((72, 90), "Codex OCR readiness fixture. The cold OCR route should accept raw PDF input.", fontsize=14)
            doc.save(str(target))
            doc.close()
        except Exception:
            target.write_bytes(
                b"%PDF-1.4\n"
                b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n"
                b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n"
                b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n"
                b"4 0 obj<< /Length 88 >>stream\nBT /F1 14 Tf 72 752 Td (Codex OCR readiness fixture raw PDF input.) Tj ET\nendstream endobj\n"
                b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
                b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000239 00000 n \n0000000377 00000 n \ntrailer<< /Size 6 /Root 1 0 R >>\nstartxref\n447\n%%EOF\n"
            )
        raw_pdf_paths.append(rel_path)
        manifest_rows.append({
            "source": "generated isolated fixture",
            "destination": str(target),
            "type": "pdf",
            "size": int(target.stat().st_size),
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "copied_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "note": "generated after T0 for focused /pdf/ocr cold-region validation; not source parity evidence",
        })
    salt = secrets.token_urlsafe(18)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    password_hash = f"pbkdf2_sha256$120000${salt}${encoded}"
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    connection = sqlite3.connect(db_path, timeout=30)
    try:
        connection.execute("BEGIN IMMEDIATE")
        for index in range(1, 101):
            username = f"codexload{index:03d}"
            connection.execute(
                "UPDATE server_load_test_credentials SET password_hash=?, updated_at_utc=? WHERE username=?",
                (password_hash, now, username),
            )
        connection.commit()
    finally:
        connection.close()
    fixture_manifest = Path.home() / ".codex" / "plans" / "server2_postgres_step3_asset_fixture_manifest_2026-07-26.json"
    fixture_manifest.write_text(json.dumps({
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "classification": "benchmark asset fixture set supplemented after T0",
        "atomic_t0_claim": False,
        "t0_parity_claim": False,
        "items": manifest_rows,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"selected": len(selected), "copied": copied, "removed_local_login_files": removed_local_login_files, "fixture_manifest": str(fixture_manifest), "password": password, "spaces": suffix_hits, "pdfs": len(pdfs), "raw_pdf_paths": raw_pdf_paths}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("smoke", "probe", "triad", "bounded", "full"), default="smoke")
    parser.add_argument("--output", default="")
    parser.add_argument("--disable-ocr", action="store_true")
    parser.add_argument("--only-action", default="")
    parser.add_argument("--only-role", default="")
    args = parser.parse_args()
    env = make_env()
    old_pid = port_pid(18877)
    if old_pid:
        stop_pid(old_pid)
    process: subprocess.Popen | None = None
    started = time.perf_counter()
    log_path = Path.home() / ".codex" / "plans" / f"server2_postgres_step3_server_{args.profile}_18877.log"
    log_handle = None
    try:
        log_handle = log_path.open("w", encoding="utf-8")
        fixture = prepare_asset_fixture()
        env["FUTURE_TEST_PASSWORD"] = str(fixture.pop("password"))
        raw_pdf_paths = fixture.get("raw_pdf_paths") or []
        if raw_pdf_paths:
            env["FUTURE_BENCHMARK_RAW_PDF_PATHS"] = ";".join(str(item) for item in raw_pdf_paths)
        cleanup_before = cleanup_workload_state(env)
        process = subprocess.Popen(
            [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--host", "127.0.0.1", "--port", "18877", "--no-browser", "--no-tunnel", "--no-preload"],
            cwd=ROOT,
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            health = wait_health(process.pid)
        except Exception as exc:
            summary = {
                "ok": False,
                "stage": "server_startup",
                "server_pid": process.pid,
                "process_exit_code": process.poll(),
                "log_path": str(log_path),
                "error": str(exc),
                "log_tail": log_path.read_text(encoding="utf-8", errors="replace")[-4000:] if log_path.exists() else "",
            }
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 3
        refresh = requests.post(f"{BASE}/server-data/manifest-refresh", json={"paths": []}, timeout=90)
        refresh.raise_for_status()
        output = args.output or str(Path.home() / ".codex" / "plans" / f"server2_postgres_step3_mixed_{args.profile}_2026-07-26.json")
        command = [
            sys.executable,
            str(ROOT / "FUTURE" / "tools" / "benchmark_server2_mixed_100_users.py"),
            "--profile",
            args.profile,
            "--skip-idle-gate",
            "--output",
            output,
        ]
        if args.disable_ocr:
            command.append("--disable-ocr")
        if args.only_action:
            command.extend(["--only-action", args.only_action])
        if args.only_role:
            command.extend(["--only-role", args.only_role])
        benchmark_stdout_lines = []
        benchmark_stderr = ""
        benchmark_started = time.monotonic()
        benchmark_process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            while True:
                if benchmark_process.stdout is not None:
                    line = benchmark_process.stdout.readline()
                    if line:
                        benchmark_stdout_lines.append(line)
                        print(line, end="", flush=True)
                        continue
                if benchmark_process.poll() is not None:
                    break
                if time.monotonic() - benchmark_started > 3600:
                    benchmark_process.kill()
                    benchmark_stderr = "benchmark timeout after 3600 seconds"
                    break
                time.sleep(0.2)
            if benchmark_process.stdout is not None:
                for line in benchmark_process.stdout.readlines():
                    benchmark_stdout_lines.append(line)
                    print(line, end="", flush=True)
        finally:
            if benchmark_process.poll() is None:
                benchmark_process.kill()
        run = subprocess.CompletedProcess(command, benchmark_process.returncode, "".join(benchmark_stdout_lines), benchmark_stderr)
        cleanup = cleanup_workload_state(env)
        stop_pid(process.pid)
        port_after_shutdown = port_pid(18877)
        cleanup_summary = {
            "baseline_fixture_users_expected": 100,
            "baseline_fixture_users_actual": _count_value(cleanup_before.get("sqlite_before", {}).get("users", 0)),
            "baseline_fixture_credentials_expected": 100,
            "baseline_fixture_credentials_actual": _count_value(cleanup_before.get("sqlite_before", {}).get("credentials", 0)),
            "temporary_workload_rows": _count_value(
                sum(_count_value(value) for key, value in (cleanup.get("sqlite_remaining", {}) or {}).items() if key not in {"users", "credentials"})
                + sum(_count_value(value) for value in (cleanup.get("pg_remaining", {}) or {}).values())
                + _count_value(cleanup.get("local_login_fixture_files_remaining", 0))
            ),
            "unexpected_test_rows": _count_value(
                sum(_count_value(value) for key, value in (cleanup.get("sqlite_remaining", {}) or {}).items() if key not in {"users", "credentials"})
                + sum(_count_value(value) for value in (cleanup.get("pg_remaining", {}) or {}).values())
                + _count_value(cleanup.get("local_login_fixture_files_remaining", 0))
            ),
        }
        benchmark_ok = False
        benchmark_payload = {}
        try:
            benchmark_payload = json.loads(Path(output).read_text(encoding="utf-8"))
            benchmark_ok = all(not phase.get("errors") for phase in benchmark_payload.get("phases", []))
        except Exception:
            benchmark_payload = {}
        postgres_probe = health.get("postgres_probe", {})
        postgres_credentials = cleanup_before.get("pg_before", {}).get("credentials", 0)
        summary = {
            "ok": bool(benchmark_ok and cleanup_summary["unexpected_test_rows"] == 0 and port_after_shutdown == 0),
            "profile": args.profile,
            "server_pid": process.pid,
            "cleanup_before": cleanup_before,
            "health_ok": bool(health.get("ok")),
            "backend_root_probe": {
                "postgres_probe": postgres_probe,
                "server_data_root": health.get("server_data_root", ""),
                "qmlearn_root": health.get("qmlearn_root", ""),
            },
            "runtime_probe": {
                "dsn_set": bool(postgres_probe.get("dsn_set")),
                "current_database": postgres_probe.get("database", ""),
                "current_user": postgres_probe.get("user", ""),
                "pg_auth_credentials_rows": _count_value(postgres_credentials),
            },
            "asset_fixture": fixture,
            "manifest_refresh": refresh.json(),
            "cleanup": cleanup,
            "cleanup_summary": cleanup_summary,
            "port_18877_pid_after_shutdown": port_after_shutdown,
            "output": output,
            "exit_code": run.returncode,
            "benchmark_ok": benchmark_ok,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            "stdout_tail": run.stdout[-6000:],
            "stderr_tail": run.stderr[-4000:],
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary["ok"] else run.returncode
    finally:
        if process and process.poll() is None:
            stop_pid(process.pid)
        if log_handle:
            log_handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
