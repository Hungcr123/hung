#!/usr/bin/env python3
"""HTTP runtime gate for lesson_complete append_events with PostgreSQL."""

from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app  # noqa: E402
import FUTURE.tools.migrate_append_events_to_postgres as migrate_append  # noqa: E402
import FUTURE.tools.migrate_completion_events_to_postgres as migrate_completion  # noqa: E402

DATABASE = Path(r"C:\server data\server2.db")
BASE = "http://127.0.0.1:18877"
PRODUCTION_BASE = "http://127.0.0.1:8877"
USERS = tuple(f"codexpgcomplete{index:03d}" for index in range(1, 101))
SERVER_LOG = Path(tempfile.gettempdir()) / "codex_completion_postgres_gate_server.log"


def password_hash(value: str) -> str:
    rounds = 2
    salt = secrets.token_urlsafe(18)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode("utf-8"), salt.encode("utf-8"), rounds)
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"pbkdf2_sha256${rounds}${salt}${encoded}"


def password_hash_matches(value: str, encoded: str) -> bool:
    parts = str(encoded or "").split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", value.encode("utf-8"), parts[2].encode("utf-8"), int(parts[1]))
    return hmac.compare_digest(base64.urlsafe_b64encode(digest).decode("ascii").rstrip("="), parts[3])


def server_pid_on_port(port: int) -> int:
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
        return


def health(base: str = BASE, timeout: float = 5.0) -> dict:
    response = requests.get(f"{base}/health", timeout=timeout)
    response.raise_for_status()
    return response.json()


def wait_health(pid: int = 0, timeout: float = 90.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            payload = health(BASE, 3)
            if payload.get("ok") and (not pid or int(payload.get("pid", 0) or 0) == pid):
                return payload
        except Exception:
            pass
        time.sleep(0.4)
    raise RuntimeError("Test Server 2 process did not become healthy")


def start_test_server(fail_prefix: str = "") -> subprocess.Popen:
    env = dict(os.environ)
    env["FUTURE_DB_APPEND_EVENTS_BACKEND"] = "postgres"
    env["FUTURE_DB_LESSON_PROGRESS_BACKEND"] = "postgres"
    env["FUTURE_DB_VOCABULARY_BACKEND"] = "postgres"
    env["FUTURE_DB_LEADERBOARD_DOCUMENTS_BACKEND"] = "postgres"
    if fail_prefix:
        env["FUTURE_TEST_FAIL_COMPLETION_BEFORE_FINALIZE"] = fail_prefix
    else:
        env.pop("FUTURE_TEST_FAIL_COMPLETION_BEFORE_FINALIZE", None)
    log_handle = SERVER_LOG.open("ab")
    return subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--host", "127.0.0.1", "--port", "18877", "--no-browser", "--no-tunnel"],
        cwd=ROOT,
        env=env,
        stdout=log_handle,
        stderr=log_handle,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def restore_pid_file(original_text: str | None) -> None:
    try:
        if original_text is None:
            app.SERVER_PID_FILE.unlink(missing_ok=True)
        else:
            app.SERVER_PID_FILE.write_text(original_text, encoding="utf-8")
    except Exception:
        pass


def provision_users(password: str) -> None:
    now = app.utc_timestamp()
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        connection.execute("BEGIN IMMEDIATE")
        for index, username in enumerate(USERS, 1):
            profile = json.dumps({"full_name": f"Codex PG Complete {index:03d}", "load_test": True}, separators=(",", ":"))
            connection.execute(
                "INSERT INTO users(username,is_admin,is_test,profile_json,updated_at_utc) VALUES(?,0,1,?,?) "
                "ON CONFLICT(username) DO UPDATE SET is_admin=0,is_test=1,profile_json=excluded.profile_json,updated_at_utc=excluded.updated_at_utc",
                (username, profile, now),
            )
            existing = connection.execute("SELECT password_hash FROM server_load_test_credentials WHERE username=?", (username,)).fetchone()
            encoded = existing[0] if existing and password_hash_matches(password, existing[0]) else password_hash(password)
            connection.execute(
                "INSERT INTO server_load_test_credentials(username,password_hash,updated_at_utc) VALUES(?,?,?) "
                "ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash,updated_at_utc=excluded.updated_at_utc",
                (username, encoded, now),
            )
        connection.commit()
    finally:
        connection.close()


def load_lessons(limit: int = 100) -> list[dict]:
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        rows = connection.execute(
            """
            SELECT normalized_path,file_id FROM lesson_file_aliases
            WHERE active=1 AND file_id<>'' AND lower(normalized_path) LIKE 'common/%.space_w'
            ORDER BY normalized_path LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        connection.close()
    if len(rows) < limit:
        raise RuntimeError(f"Need {limit} Space_W lessons, found {len(rows)}")
    return [{"path": row[0], "lesson_id": row[1]} for row in rows]


def cleanup_sqlite() -> None:
    placeholders = ",".join("?" for _ in USERS)
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        connection.execute("BEGIN IMMEDIATE")
        for table in ("append_events", "lesson_progress", "lesson_progress_namespaces", "auth_sessions", "server_load_test_credentials", "users"):
            if table == "append_events":
                connection.execute("DELETE FROM append_events WHERE lower(username) LIKE 'codexpgcomplete%'")
            else:
                connection.execute(f'DELETE FROM "{table}" WHERE username IN ({placeholders})', USERS)
        for table in ("vocabulary_registry", "vocabulary_events", "daily_earn", "weekly_earn", "monthly_earn", "npc_period_earn", "inventory_items", "inventory_events"):
            try:
                connection.execute(f'DELETE FROM "{table}" WHERE username IN ({placeholders})', USERS)
            except sqlite3.Error:
                pass
        connection.execute("DELETE FROM documents WHERE lower(path) LIKE '%codexpgcomplete%'")
        connection.commit()
    finally:
        connection.close()


def cleanup_postgres() -> None:
    def _write(connection):
        with connection.cursor() as cursor:
            users = [username.lower() for username in USERS]
            cursor.execute("DELETE FROM future_server2.append_events WHERE lower(username)=ANY(%s) OR lower(event_key) LIKE 'codex-pg-completion-http-%%'", (users,))
            cursor.execute("DELETE FROM future_server2.lesson_progress WHERE lower(username)=ANY(%s)", (users,))
            cursor.execute("DELETE FROM future_server2.lesson_progress_namespaces WHERE lower(username)=ANY(%s)", (users,))
            for table in ("vocabulary_registry", "vocabulary_events", "daily_earn", "weekly_earn", "monthly_earn", "npc_period_earn"):
                cursor.execute(f"DELETE FROM future_server2.{table} WHERE lower(username)=ANY(%s)", (users,))
        return True

    app.postgres_execute(_write)


def login(username: str, password: str) -> str:
    response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=45)
    response.raise_for_status()
    payload = response.json()
    if (payload.get("server_data") or {}).get("load_test") is not True:
        raise RuntimeError(f"{username} did not login as isolated test user")
    return str(payload.get("token") or "")


def complete_payload(username: str, lesson: dict, run_id: str, stamp: str) -> dict:
    return {
        "path": lesson["path"],
        "lesson_id": lesson["lesson_id"],
        "file_id": lesson["lesson_id"],
        "title": f"Codex PG Completion {username}",
        "nodes": 1,
        "completed_at": stamp,
        "completion_run_id": run_id,
        "source": "Space_W",
    }


def post_complete(token: str, body: dict) -> tuple[float, int, dict]:
    started = time.perf_counter()
    try:
        response = requests.post(f"{BASE}/lesson/complete", headers={"Authorization": f"Bearer {token}"}, json=body, timeout=60)
        latency = (time.perf_counter() - started) * 1000
        payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        return latency, response.status_code, payload
    except Exception as exc:
        return (time.perf_counter() - started) * 1000, 0, {"error": str(exc), "exception": type(exc).__name__}


def pg_counts() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*),count(DISTINCT username) FROM future_server2.append_events WHERE stream='learning' AND lower(username) LIKE 'codexpgcomplete%'")
            final = cursor.fetchone()
            cursor.execute("SELECT count(*),count(DISTINCT username) FROM future_server2.append_events WHERE stream='learning_intent' AND lower(username) LIKE 'codexpgcomplete%'")
            intent = cursor.fetchone()
            cursor.execute("SELECT count(*),count(DISTINCT username) FROM future_server2.lesson_progress WHERE lower(username)=ANY(%s) AND complete=true", ([u.lower() for u in USERS],))
            progress = cursor.fetchone()
            cursor.execute("SELECT count(*) FROM future_server2.vocabulary_events WHERE lower(username)=ANY(%s)", ([u.lower() for u in USERS],))
            vocab_events = cursor.fetchone()
        return {
            "pg_final_events": int(final[0] or 0),
            "pg_final_users": int(final[1] or 0),
            "pg_intents": int(intent[0] or 0),
            "pg_intent_users": int(intent[1] or 0),
            "pg_complete_progress": int(progress[0] or 0),
            "pg_complete_progress_users": int(progress[1] or 0),
            "pg_vocabulary_events": int(vocab_events[0] or 0),
        }

    return app.postgres_execute(_read)


def sqlite_counts() -> dict:
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        return {
            "sqlite_events": int(connection.execute("SELECT count(*) FROM append_events WHERE lower(username) LIKE 'codexpgcomplete%'").fetchone()[0] or 0),
            "sqlite_progress": int(connection.execute("SELECT count(*) FROM lesson_progress WHERE lower(username) LIKE 'codexpgcomplete%'").fetchone()[0] or 0),
            "sqlite_users": int(connection.execute("SELECT count(*) FROM users WHERE lower(username) LIKE 'codexpgcomplete%'").fetchone()[0] or 0),
            "sqlite_summary_docs": int(connection.execute("SELECT count(*) FROM documents WHERE lower(path) LIKE '%codexpgcomplete%'").fetchone()[0] or 0),
        }
    finally:
        connection.close()


def pg_stat() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT xact_commit,xact_rollback,conflicts,deadlocks FROM pg_stat_database WHERE datname=current_database()")
            row = cursor.fetchone()
            cursor.execute("SELECT state,count(*) FROM pg_stat_activity WHERE datname=current_database() AND usename=current_user GROUP BY state")
            activity = {str(state or "none"): int(count or 0) for state, count in cursor.fetchall()}
        return {"xact_commit": int(row[0] or 0), "xact_rollback": int(row[1] or 0), "conflicts": int(row[2] or 0), "deadlocks": int(row[3] or 0), "activity": activity}

    return app.postgres_execute(_read)


def stat_delta(before: dict, after: dict) -> dict:
    return {key: int(after.get(key, 0) or 0) - int(before.get(key, 0) or 0) for key in ("xact_commit", "xact_rollback", "conflicts", "deadlocks")} | {"activity_after": after.get("activity", {})}


def concurrency_phase(name: str, users: tuple[str, ...], tokens: dict[str, str], lessons: list[dict], *, same_key: bool = False) -> dict:
    before = pg_stat()
    process = psutil.Process(server_pid_on_port(18877))
    cpu_before = sum(process.cpu_times()[:2])
    base = datetime(2026, 7, 25, 8, 0, 0, tzinfo=timezone.utc)

    def one(item: tuple[int, str]) -> tuple[float, int, bool, bool]:
        index, username = item
        lesson = lessons[0 if same_key else (index - 1) % len(lessons)]
        owner = USERS[0] if same_key else username
        token = tokens[owner]
        run_id = f"codex-pg-completion-http-{name}-{index if not same_key else 1}"
        stamp = (base.replace(microsecond=0)).isoformat().replace("+00:00", "Z")
        latency, status, payload = post_complete(token, complete_payload(owner, lesson, run_id, stamp))
        mismatch = status != 200 or not payload.get("ok") or not payload.get("event_key")
        dedupe = bool(payload.get("deduplicated"))
        return latency, status, mismatch, dedupe

    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(50, len(users))) as pool:
        rows = list(pool.map(one, enumerate(users, start=1)))
    wall_ms = (time.perf_counter() - started) * 1000
    cpu_after = sum(process.cpu_times()[:2])
    delta = stat_delta(before, pg_stat())
    latencies = sorted(row[0] for row in rows)
    return {
        "name": name,
        "requests": len(users),
        "statuses": {str(status): sum(1 for row in rows if row[1] == status) for status in sorted({row[1] for row in rows})},
        "mismatched_response": sum(1 for row in rows if row[2]),
        "deduplicated": sum(1 for row in rows if row[3]),
        "wall_ms": round(wall_ms, 3),
        "throughput_rps": round(len(users) / max(0.001, wall_ms / 1000), 3),
        "cpu_ms_per_request": round(((cpu_after - cpu_before) * 1000) / max(1, len(users)), 3),
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(latencies[max(0, int(len(latencies) * 0.95) - 1)], 3),
        "p99_ms": round(latencies[max(0, int(len(latencies) * 0.99) - 1)], 3),
        "pg_stat_delta": delta,
        "pool_wait": "not_exposed",
        "timeout": 0,
        "rollback": delta.get("xact_rollback", 0),
        "deadlock": delta.get("deadlocks", 0),
        "serialization_conflict": delta.get("conflicts", 0),
    }


def parity() -> dict:
    sqlite_rows = migrate_append.sqlite_rows()
    pg_rows = migrate_append.pg_rows()
    ids = {row["id"] for row in sqlite_rows}
    pg_subset = [row for row in pg_rows if row["id"] in ids]
    completion_sqlite = migrate_completion.sqlite_rows()
    completion_pg = migrate_completion.postgres_rows()
    completion_ids = {row["id"] for row in completion_sqlite}
    completion_pg_subset = [row for row in completion_pg if row["id"] in completion_ids]
    return {
        "append_events": {
            "sqlite_rows": len(sqlite_rows),
            "postgres_matching_sqlite": len(pg_subset),
            "sqlite_fingerprint": migrate_append.fingerprint(sqlite_rows),
            "postgres_fingerprint": migrate_append.fingerprint(pg_subset),
        },
        "completion_events": {
            "sqlite_rows": len(completion_sqlite),
            "postgres_matching_sqlite": len(completion_pg_subset),
            "sqlite_fingerprint": migrate_completion.fingerprint(completion_sqlite),
            "postgres_fingerprint": migrate_completion.fingerprint(completion_pg_subset),
        },
    }


def main() -> int:
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("FUTURE_PG_DSN is required")
    password = os.environ.get("FUTURE_TEST_PASSWORD", "") or secrets.token_urlsafe(32)
    if server_pid_on_port(18877):
        raise RuntimeError("Port 18877 already has a listener")
    pre = parity()
    if pre["append_events"]["sqlite_fingerprint"] != pre["append_events"]["postgres_fingerprint"]:
        raise RuntimeError(f"Pre-test append_events parity failed: {pre}")
    if pre["completion_events"]["sqlite_fingerprint"] != pre["completion_events"]["postgres_fingerprint"]:
        raise RuntimeError(f"Pre-test completion parity failed: {pre}")

    original_pid_file = app.SERVER_PID_FILE.read_text(encoding="utf-8") if app.SERVER_PID_FILE.is_file() else None
    process: subprocess.Popen | None = None
    result: dict = {}
    try:
        cleanup_sqlite()
        cleanup_postgres()
        provision_users(password)
        process = start_test_server()
        wait_health(pid=int(process.pid))
        lessons = load_lessons(100)
        tokens = {username: login(username, password) for username in USERS}

        stamp = datetime(2026, 7, 25, 7, 0, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        first_body = complete_payload(USERS[0], lessons[0], "codex-pg-completion-http-single", stamp)
        first = post_complete(tokens[USERS[0]], first_body)
        retry = post_complete(tokens[USERS[0]], first_body)
        invalid = requests.post(f"{BASE}/lesson/complete", json={"path": lessons[0]["path"]}, timeout=30)
        if first[1] != 200 or not first[2].get("event_key") or retry[1] != 200 or not retry[2].get("deduplicated"):
            raise RuntimeError({"reason": "single completion/retry failed", "first": first[2], "retry": retry[2]})

        failure_run_id = "codex-pg-completion-http-fail-before-finalize"
        failure_body = complete_payload(USERS[1], lessons[1], failure_run_id, stamp)
        before_failure = pg_counts()
        stop_pid(int(process.pid))
        process = start_test_server(fail_prefix=failure_run_id)
        wait_health(pid=int(process.pid))
        fail_token = login(USERS[1], password)
        failure = post_complete(fail_token, failure_body)
        failure_mid = pg_counts()
        stop_pid(int(process.pid))
        process = start_test_server()
        wait_health(pid=int(process.pid))
        recovered_after_start = pg_counts()
        retry_token = login(USERS[1], password)
        failure_retry = post_complete(retry_token, failure_body)
        failure_exact_retry = post_complete(retry_token, failure_body)
        failure_after = pg_counts()
        final_delta_at_failure = failure_mid["pg_final_events"] - before_failure["pg_final_events"]
        final_delta_after_retry = failure_after["pg_final_events"] - before_failure["pg_final_events"]
        if (
            failure[1] == 200
            or final_delta_at_failure != 0
            or final_delta_after_retry != 1
            or failure_retry[1] != 200
            or failure_exact_retry[1] != 200
            or not failure_exact_retry[2].get("deduplicated")
        ):
            raise RuntimeError({
                "reason": "failure recovery/compensation check failed",
                "failure_status": failure[1],
                "failure_payload": failure[2],
                "before": before_failure,
                "mid": failure_mid,
                "recovered_after_start": recovered_after_start,
                "retry": failure_retry[2],
                "exact_retry": failure_exact_retry[2],
                "after": failure_after,
            })

        tokens = {username: login(username, password) for username in USERS}
        phases = [
            concurrency_phase("completion_distinct_10", USERS[:10], tokens, lessons),
            concurrency_phase("completion_distinct_50", USERS[:50], tokens, lessons),
            concurrency_phase("completion_distinct_100", USERS, tokens, lessons),
            concurrency_phase("completion_same_key_10", USERS[:10], tokens, lessons, same_key=True),
            concurrency_phase("completion_same_key_50", USERS[:50], tokens, lessons, same_key=True),
            concurrency_phase("completion_same_key_100", USERS, tokens, lessons, same_key=True),
        ]
        if any(phase["mismatched_response"] or phase["deadlock"] or phase["serialization_conflict"] for phase in phases):
            raise RuntimeError(f"Concurrency phase failed: {phases}")

        before_restart = {**pg_counts(), **sqlite_counts()}
        stop_pid(int(process.pid))
        process = start_test_server()
        wait_health(pid=int(process.pid))
        token_after = login(USERS[0], password)
        readback_retry = post_complete(token_after, first_body)
        after_restart = {**pg_counts(), **sqlite_counts()}
        if not readback_retry[2].get("deduplicated") or after_restart["pg_final_users"] < before_restart["pg_final_users"]:
            raise RuntimeError({"reason": "completion restart readback failed", "retry": readback_retry[2], "before": before_restart, "after": after_restart})

        final = parity()
        result = {
            "completion_postgres_http_gate": "ok",
            "feature_flags": ["FUTURE_DB_APPEND_EVENTS_BACKEND", "FUTURE_DB_LESSON_PROGRESS_BACKEND", "FUTURE_DB_VOCABULARY_BACKEND", "FUTURE_DB_LEADERBOARD_DOCUMENTS_BACKEND"],
            "pre": pre,
            "single": {"status": first[1], "retry_deduplicated": bool(retry[2].get("deduplicated")), "invalid_status": invalid.status_code},
            "failure_recovery": {
                "failure_status": failure[1],
                "before_failure": before_failure,
                "pending_intents_after_failure": failure_mid["pg_intents"],
                "final_events_after_failure": failure_mid["pg_final_events"],
                "final_delta_at_failure": final_delta_at_failure,
                "recovered_after_start": recovered_after_start,
                "retry_status": failure_retry[1],
                "exact_retry_status": failure_exact_retry[1],
                "exact_retry_deduplicated": bool(failure_exact_retry[2].get("deduplicated")),
                "final_delta_after_retry": final_delta_after_retry,
                "after_retry": failure_after,
            },
            "concurrency": phases,
            "restart": {"before": before_restart, "after": after_restart, "retry_deduplicated": bool(readback_retry[2].get("deduplicated"))},
            "shadow_read": final,
            "production_health": health(PRODUCTION_BASE, 10),
            "production_flags": {
                "FUTURE_DB_APPEND_EVENTS_BACKEND": os.environ.get("FUTURE_DB_APPEND_EVENTS_BACKEND", "off") or "off",
                "FUTURE_DB_LESSON_PROGRESS_BACKEND": os.environ.get("FUTURE_DB_LESSON_PROGRESS_BACKEND", "off") or "off",
            },
        }
        print(json.dumps(result, ensure_ascii=True, indent=2, default=str))
        return 0
    finally:
        if process is not None:
            stop_pid(int(process.pid))
        cleanup_sqlite()
        cleanup_postgres()
        restore_pid_file(original_pid_file)
        cleanup = {**pg_counts(), **sqlite_counts()}
        if result:
            print(json.dumps({"cleanup": cleanup, "port_18877_busy": bool(server_pid_on_port(18877))}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
