"""Trace one production /lesson/complete call with an isolated temporary user."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import time
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import psutil
import psycopg
from psycopg import sql
import requests


BASE_URL = "http://127.0.0.1:8877"
DEBUG_LOG = Path(r"C:\server data\server_log\future_whisper_stt_debug.log")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def password_hash(password: str) -> str:
    salt = secrets.token_urlsafe(18)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 2)
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"pbkdf2_sha256$2${salt}${encoded}"


def server_process() -> psutil.Process:
    for connection in psutil.net_connections(kind="tcp"):
        if connection.status == psutil.CONN_LISTEN and connection.laddr and connection.laddr.port == 8877 and connection.pid:
            return psutil.Process(connection.pid)
    raise RuntimeError("Server 2 listener not found")


def provision_user(username: str, password: str, template_user: str, is_test: bool) -> int:
    now = utc_now()
    with psycopg.connect(os.environ["FUTURE_PG_DSN"]) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM future_server2.users WHERE username=%s", (username,))
            if int(cursor.fetchone()[0] or 0):
                raise RuntimeError(f"Temporary user already exists: {username}")
            cursor.execute(
                "INSERT INTO future_server2.users"
                "(username,is_admin,is_test,profile_json,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256) "
                "VALUES (%s,false,%s,'{}'::jsonb,%s,%s,%s,'')",
                (username, bool(is_test), now, time.time(), now),
            )
            cursor.execute(
                "INSERT INTO future_server2.user_auth_credentials"
                "(username,password_hash,source_path,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256) "
                "VALUES (%s,%s,'',%s,%s,%s,'')",
                (username, password_hash(password), now, time.time(), now),
            )
            cursor.execute(
                "INSERT INTO future_server2.vocabulary_registry"
                "(username,word_key,word,meaning,pron,word_type,learn_count,first_at_utc,last_at_utc,last_epoch,"
                "sources_json,qmdict_missing,migrated_at_utc,source_sha256) "
                "SELECT %s,word_key,word,meaning,pron,word_type,learn_count,first_at_utc,last_at_utc,last_epoch,"
                "sources_json,qmdict_missing,%s,'' FROM future_server2.vocabulary_registry WHERE username=%s",
                (username, now, template_user),
            )
            return max(0, int(cursor.rowcount or 0))


def cleanup_user(username: str) -> dict:
    deleted = {}
    with psycopg.connect(os.environ["FUTURE_PG_DSN"]) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.columns "
                "WHERE table_schema='future_server2' AND column_name='username' ORDER BY table_name"
            )
            tables = [str(row[0]) for row in cursor.fetchall()]
            for table in [value for value in tables if value != "users"] + ["users"]:
                cursor.execute(
                    sql.SQL("DELETE FROM {}.{} WHERE username=%s").format(
                        sql.Identifier("future_server2"),
                        sql.Identifier(table),
                    ),
                    (username,),
                )
                if int(cursor.rowcount or 0) > 0:
                    deleted[table] = int(cursor.rowcount)
            cursor.execute("SELECT COUNT(*) FROM future_server2.users WHERE username=%s", (username,))
            remaining = int(cursor.fetchone()[0] or 0)
    return {"deleted": deleted, "user_rows_remaining": remaining}


def user_mutation_counts(username: str) -> dict:
    with psycopg.connect(os.environ["FUTURE_PG_DSN"]) as connection:
        with connection.cursor() as cursor:
            counts = {}
            for table in ("append_events", "vocabulary_events", "daily_earn", "weekly_earn", "monthly_earn", "vocabulary_registry"):
                cursor.execute(f"SELECT COUNT(*) FROM future_server2.{table} WHERE username=%s", (username,))
                counts[table] = int(cursor.fetchone()[0] or 0)
            return counts


def trace_log_rows(trace_id: str) -> list[dict]:
    if not DEBUG_LOG.is_file():
        return []
    rows = []
    for line in DEBUG_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        if trace_id not in line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def wait_for_warm_server(previous_pid: int = 0) -> dict:
    deadline = time.time() + 120
    last = {}
    while time.time() < deadline:
        try:
            last = requests.get(f"{BASE_URL}/health", timeout=3).json()
        except Exception:
            last = {}
        if last.get("warm_ready") and int(last.get("pid", 0) or 0) != int(previous_pid or 0):
            return last
        time.sleep(0.5)
    raise RuntimeError(f"Server 2 did not become warm after restart: {last}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    parser.add_argument("--lesson-id", required=True)
    parser.add_argument("--nodes", type=int, required=True)
    parser.add_argument("--template-user", default="quynh")
    parser.add_argument("--output", required=True)
    parser.add_argument("--verify-retry", action="store_true")
    parser.add_argument("--verify-restart", action="store_true")
    args = parser.parse_args()

    relative_path = str(args.path).replace("\\", "/").lstrip("/")
    lesson_file = Path(r"C:\server data") / Path(relative_path)
    original_bytes = lesson_file.read_bytes()
    original_sha256 = hashlib.sha256(original_bytes).hexdigest()
    username = f"codexcomplete{int(time.time())}"
    password = secrets.token_urlsafe(18)
    trace_id = f"{username}-{int(time.time() * 1000)}"
    evidence: dict = {"trace_id": trace_id, "test_user": username, "path": relative_path}

    try:
        evidence["cloned_registry_rows"] = provision_user(username, password, args.template_user, is_test=not args.verify_restart)
        login = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password}, timeout=30)
        login.raise_for_status()
        token = str(login.json().get("token", ""))
        if not token:
            raise RuntimeError("Temporary user login did not return a token")

        process = server_process()
        time.sleep(5)
        cpu_before = sum(process.cpu_times()[:2])
        started = time.perf_counter()
        completion_body = {
            "path": relative_path,
            "lesson_id": args.lesson_id,
            "name": lesson_file.name,
            "title": lesson_file.stem,
            "nodes": max(0, args.nodes),
            "completed_at": utc_now(),
            "completion_run_id": trace_id,
            "completion_trace_id": trace_id,
            "source": "Space_V",
        }
        response = requests.post(
            f"{BASE_URL}/lesson/complete",
            headers={"Authorization": f"Bearer {token}", "X-Future-Completion-Trace": trace_id},
            json=completion_body,
            timeout=120,
        )
        request_wall_ms = (time.perf_counter() - started) * 1000
        cpu_response = sum(process.cpu_times()[:2])
        cpu_samples = {}
        previous_wait = 0
        for wait_seconds in (1, 5, 10):
            time.sleep(wait_seconds - previous_wait)
            previous_wait = wait_seconds
            cpu_samples[f"after_{wait_seconds}s_ms"] = round((sum(process.cpu_times()[:2]) - cpu_before) * 1000, 3)
        payload = response.json() if response.content else {}
        evidence.update({
            "status": response.status_code,
            "response_bytes": len(response.content),
            "client_wall_ms": round(request_wall_ms, 3),
            "process_cpu_until_response_ms": round((cpu_response - cpu_before) * 1000, 3),
            "process_cpu_samples": cpu_samples,
            "timing_ms": payload.get("timing_ms", {}),
            "postgres_delta": payload.get("postgres_delta", {}),
            "event_key": payload.get("event_key", ""),
            "recorded": payload.get("recorded"),
            "duplicate": payload.get("duplicate"),
            "vocabulary": {
                key: value for key, value in (payload.get("vocabulary") or {}).items()
                if key not in {"registry", "words"}
            },
            "learning_stats": payload.get("learning_stats", {}),
            "error": payload.get("error", ""),
            "trace_log": trace_log_rows(trace_id),
        })
        if args.verify_retry and response.status_code == 200:
            counts_before_retry = user_mutation_counts(username)
            retry_trace_id = trace_id + "-retry"
            retry_response = requests.post(
                f"{BASE_URL}/lesson/complete",
                headers={"Authorization": f"Bearer {token}", "X-Future-Completion-Trace": retry_trace_id},
                json={**completion_body, "completion_trace_id": retry_trace_id},
                timeout=120,
            )
            counts_after_retry = user_mutation_counts(username)
            retry_payload = retry_response.json() if retry_response.content else {}
            evidence["retry"] = {
                "status": retry_response.status_code,
                "response_bytes": len(retry_response.content),
                "duplicate": retry_payload.get("duplicate"),
                "deduplicated": retry_payload.get("deduplicated"),
                "timing_ms": retry_payload.get("timing_ms", {}),
                "postgres_delta": retry_payload.get("postgres_delta", {}),
                "counts_before": counts_before_retry,
                "counts_after": counts_after_retry,
                "counts_unchanged": counts_before_retry == counts_after_retry,
                "trace_log": trace_log_rows(retry_trace_id),
            }
        if args.verify_restart and response.status_code == 200:
            old_pid = server_process().pid
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            subprocess.Popen(
                [sys.executable, "FUTURE_SERVER_2.py", "--replace-old"],
                cwd=str(Path(__file__).resolve().parents[2]),
                creationflags=creation_flags,
                close_fds=True,
            )
            restarted_health = wait_for_warm_server(old_pid)
            relogin = requests.post(
                f"{BASE_URL}/auth/login",
                json={"username": username, "password": password},
                timeout=30,
            )
            relogin.raise_for_status()
            token_after_restart = str(relogin.json().get("token", ""))
            registry_after_restart = requests.get(
                f"{BASE_URL}/vocab/registry",
                headers={"Authorization": f"Bearer {token_after_restart}"},
                timeout=30,
            )
            leaderboard_after_restart = requests.get(
                f"{BASE_URL}/vocab/leaderboard?limit=100",
                headers={"Authorization": f"Bearer {token_after_restart}"},
                timeout=60,
            )
            counts_after_restart = user_mutation_counts(username)
            restart_retry_trace = trace_id + "-restart-retry"
            restart_retry = requests.post(
                f"{BASE_URL}/lesson/complete",
                headers={"Authorization": f"Bearer {token_after_restart}", "X-Future-Completion-Trace": restart_retry_trace},
                json={**completion_body, "completion_trace_id": restart_retry_trace},
                timeout=120,
            )
            restart_retry_payload = restart_retry.json() if restart_retry.content else {}
            evidence["restart"] = {
                "health": {key: restarted_health.get(key) for key in ("ok", "warm_ready", "pid", "started_at")},
                "relogin_status": relogin.status_code,
                "registry_status": registry_after_restart.status_code,
                "registry_total_words": len((registry_after_restart.json().get("registry") or registry_after_restart.json()).get("words", {})),
                "leaderboard_status": leaderboard_after_restart.status_code,
                "leaderboard_contains_user": username.lower() in leaderboard_after_restart.text.lower(),
                "counts_after_restart": counts_after_restart,
                "retry_status": restart_retry.status_code,
                "retry_duplicate": restart_retry_payload.get("duplicate"),
                "retry_deduplicated": restart_retry_payload.get("deduplicated"),
                "trace_log": trace_log_rows(restart_retry_trace),
            }
    finally:
        lesson_file.write_bytes(original_bytes)
        evidence["lesson_restored_sha256"] = hashlib.sha256(lesson_file.read_bytes()).hexdigest()
        evidence["lesson_restore_matches"] = evidence["lesson_restored_sha256"] == original_sha256
        try:
            evidence["cleanup"] = cleanup_user(username)
        except Exception as exc:
            evidence["cleanup_error"] = str(exc)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "trace_id": evidence.get("trace_id"),
        "status": evidence.get("status"),
        "client_wall_ms": evidence.get("client_wall_ms"),
        "process_cpu_until_response_ms": evidence.get("process_cpu_until_response_ms"),
        "postgres_delta": evidence.get("postgres_delta"),
        "trace_rows": len(evidence.get("trace_log", [])),
        "lesson_restore_matches": evidence.get("lesson_restore_matches"),
        "cleanup": evidence.get("cleanup"),
        "cleanup_error": evidence.get("cleanup_error", ""),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
