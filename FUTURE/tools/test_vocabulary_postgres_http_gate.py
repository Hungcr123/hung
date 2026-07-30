#!/usr/bin/env python3
"""HTTP runtime gate for vocabulary registry/events/earn PostgreSQL backend."""

from __future__ import annotations

import base64
import argparse
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
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app  # noqa: E402
import FUTURE.tools.migrate_vocabulary_earn_to_postgres as migrate_earn  # noqa: E402
import FUTURE.tools.migrate_vocabulary_to_postgres as migrate_vocab  # noqa: E402

DATABASE = Path(r"C:\server data\server2.db")
BASE = "http://127.0.0.1:18877"
PRODUCTION_BASE = "http://127.0.0.1:8877"
USERS = tuple(f"codexpgvocab{index:03d}" for index in range(1, 101))
BACKEND = "postgres"

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

def compact_health(base: str = BASE, timeout: float = 5.0) -> dict:
    payload = health(base, timeout)
    writer = payload.get("postgres_writer") if isinstance(payload.get("postgres_writer"), dict) else {}
    return {
        "ok": bool(payload.get("ok")),
        "pid": int(payload.get("pid", 0) or 0),
        "writer_queue": int(writer.get("queue_depth", 0) or 0),
        "server_time": str(payload.get("server_time", "")),
    }

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

def start_test_server() -> subprocess.Popen:
    env = dict(os.environ)
    if BACKEND == "postgres":
        env["FUTURE_DB_VOCABULARY_BACKEND"] = "postgres"
        env["FUTURE_DB_APPEND_EVENTS_BACKEND"] = "postgres"
        env["FUTURE_DB_LESSON_PROGRESS_BACKEND"] = "postgres"
    else:
        env.pop("FUTURE_DB_VOCABULARY_BACKEND", None)
        env.pop("FUTURE_DB_APPEND_EVENTS_BACKEND", None)
        env.pop("FUTURE_DB_LESSON_PROGRESS_BACKEND", None)
    return subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--host", "127.0.0.1", "--port", "18877", "--no-browser", "--no-tunnel"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
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
            profile = json.dumps({"full_name": f"Codex PG Vocab {index:03d}", "load_test": True}, separators=(",", ":"))
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

def load_space_v_lessons(limit: int = 100) -> list[dict]:
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        rows = connection.execute(
            """
            SELECT normalized_path,file_id FROM lesson_file_aliases
            WHERE active=1 AND file_id<>'' AND lower(normalized_path) LIKE 'common/%.space_v'
            ORDER BY normalized_path LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        connection.close()
    if len(rows) < limit:
        raise RuntimeError(f"Need {limit} Space_V lessons, found {len(rows)}")
    return [{"path": row[0], "lesson_id": row[1]} for row in rows]

def cleanup_sqlite() -> None:
    placeholders = ",".join("?" for _ in USERS)
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        connection.execute("BEGIN IMMEDIATE")
        for table in ("append_events", "lesson_progress", "lesson_progress_namespaces", "auth_sessions", "server_load_test_credentials", "users"):
            if table == "append_events":
                connection.execute("DELETE FROM append_events WHERE lower(username) LIKE 'codexpgvocab%'")
            else:
                connection.execute(f'DELETE FROM "{table}" WHERE username IN ({placeholders})', USERS)
        for table in ("vocabulary_registry", "vocabulary_events", "daily_earn", "weekly_earn", "monthly_earn", "npc_period_earn"):
            connection.execute(f'DELETE FROM "{table}" WHERE username IN ({placeholders})', USERS)
        connection.execute("DELETE FROM documents WHERE lower(path) LIKE '%codexpgvocab%'")
        connection.commit()
    finally:
        connection.close()

def cleanup_postgres() -> None:
    def _write(connection):
        with connection.cursor() as cursor:
            users = [username.lower() for username in USERS]
            for table in ("daily_earn", "weekly_earn", "monthly_earn", "npc_period_earn", "vocabulary_events", "vocabulary_registry"):
                cursor.execute(f"DELETE FROM future_server2.{table} WHERE lower(username)=ANY(%s)", (users,))
            cursor.execute("DELETE FROM future_server2.append_events WHERE lower(username)=ANY(%s) OR lower(event_key) LIKE 'codex-pg-vocab-http-%%'", (users,))
            cursor.execute("DELETE FROM future_server2.lesson_progress WHERE lower(username)=ANY(%s)", (users,))
            cursor.execute("DELETE FROM future_server2.lesson_progress_namespaces WHERE lower(username)=ANY(%s)", (users,))
            cursor.execute("DELETE FROM future_server2.users WHERE lower(username)=ANY(%s)", (users,))
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
        "title": f"Codex PG Vocab {username}",
        "nodes": 1,
        "completed_at": stamp,
        "completion_run_id": run_id,
        "source": "Space_V",
    }

def post_complete(token: str, body: dict) -> tuple[float, int, dict]:
    started = time.perf_counter()
    try:
        response = requests.post(f"{BASE}/lesson/complete", headers={"Authorization": f"Bearer {token}"}, json=body, timeout=240)
        latency = (time.perf_counter() - started) * 1000
        payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        return latency, response.status_code, payload
    except requests.exceptions.Timeout:
        return (time.perf_counter() - started) * 1000, 0, {"timeout": True}

def pg_counts() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            users = [username.lower() for username in USERS]
            result = {}
            for table in ("vocabulary_registry", "vocabulary_events", "daily_earn", "weekly_earn", "monthly_earn"):
                cursor.execute(f"SELECT count(*),count(DISTINCT username) FROM future_server2.{table} WHERE lower(username)=ANY(%s)", (users,))
                row = cursor.fetchone()
                result[f"pg_{table}"] = int(row[0] or 0)
                result[f"pg_{table}_users"] = int(row[1] or 0)
        return result
    return app.postgres_execute(_read)

def sqlite_counts() -> dict:
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        result = {}
        for table in ("vocabulary_registry", "vocabulary_events", "daily_earn", "weekly_earn", "monthly_earn"):
            row = connection.execute(f"SELECT count(*),count(DISTINCT username) FROM {table} WHERE lower(username) LIKE 'codexpgvocab%'").fetchone()
            result[f"sqlite_{table}"] = int(row[0] or 0)
            result[f"sqlite_{table}_users"] = int(row[1] or 0)
        result["sqlite_users"] = int(connection.execute("SELECT count(*) FROM users WHERE lower(username) LIKE 'codexpgvocab%'").fetchone()[0] or 0)
        return result
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

def postgres_health_metrics() -> dict:
    try:
        payload = health(BASE, 5)
    except Exception:
        return {}
    metrics = payload.get("postgres") if isinstance(payload.get("postgres"), dict) else {}
    return dict(metrics) if isinstance(metrics, dict) else {}

def metrics_delta(before: dict, after: dict, requests_count: int) -> dict:
    keys = ("transactions", "commits", "rollbacks", "sql_execute", "sql_executemany", "sql_round_trips", "pool_wait_count", "pool_wait_ms_total")
    delta = {key: float(after.get(key, 0) or 0) - float(before.get(key, 0) or 0) for key in keys}
    round_trips = int(delta.get("sql_round_trips", 0) or 0)
    transactions = int(delta.get("transactions", 0) or 0)
    pool_wait_total = float(delta.get("pool_wait_ms_total", 0.0) or 0.0)
    return {
        "transactions": transactions,
        "transactions_per_request": round(transactions / max(1, requests_count), 3),
        "sql_execute": int(delta.get("sql_execute", 0) or 0),
        "sql_executemany": int(delta.get("sql_executemany", 0) or 0),
        "sql_round_trips": round_trips,
        "sql_round_trips_per_request": round(round_trips / max(1, requests_count), 3),
        "pool_wait_count": int(delta.get("pool_wait_count", 0) or 0),
        "pool_wait_ms_total": round(pool_wait_total, 3),
        "pool_wait_ms_per_request": round(pool_wait_total / max(1, requests_count), 3),
        "pool_wait_ms_max": round(
            float(after.get("pool_wait_ms_max", 0.0) or 0.0)
            if float(after.get("pool_wait_ms_max", 0.0) or 0.0) > float(before.get("pool_wait_ms_max", 0.0) or 0.0)
            else 0.0,
            3,
        ),
        "pool_size": int(after.get("pool_size", 0) or 0),
        "pool_active": int(after.get("pool_active", 0) or 0),
        "pool_idle": int(after.get("pool_idle", 0) or 0),
    }

def concurrency_phase(name: str, users: tuple[str, ...], tokens: dict[str, str], lessons: list[dict], *, same_key: bool = False) -> dict:
    before = pg_stat()
    metrics_before = postgres_health_metrics()
    process = psutil.Process(server_pid_on_port(18877))
    cpu_before = sum(process.cpu_times()[:2])
    base = datetime(2026, 7, 25, 9, 0, 0, tzinfo=timezone.utc)

    def one(item: tuple[int, str]) -> tuple[float, int, bool, bool, int, dict]:
        index, username = item
        lesson = lessons[0 if same_key else (index - 1) % len(lessons)]
        owner = USERS[0] if same_key else username
        token = tokens[owner]
        run_id = f"codex-pg-vocab-http-{name}-{index if not same_key else 1}"
        stamp = base.isoformat().replace("+00:00", "Z")
        latency, status, payload = post_complete(token, complete_payload(owner, lesson, run_id, stamp))
        vocabulary = payload.get("vocabulary") if isinstance(payload.get("vocabulary"), dict) else {}
        deduplicated = bool(payload.get("deduplicated"))
        if same_key and deduplicated:
            mismatch = status != 200 or not payload.get("ok")
        else:
            mismatch = status != 200 or not payload.get("ok") or int(vocabulary.get("learned_words", 0) or 0) <= 0
        timing = payload.get("timing_ms") if isinstance(payload.get("timing_ms"), dict) else {}
        return latency, status, mismatch, deduplicated, int(vocabulary.get("learned_words", 0) or 0), timing

    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(50, len(users))) as pool:
        rows = list(pool.map(one, enumerate(users, start=1)))
    wall_ms = (time.perf_counter() - started) * 1000
    cpu_after = sum(process.cpu_times()[:2])
    delta = stat_delta(before, pg_stat())
    pg_metrics = metrics_delta(metrics_before, postgres_health_metrics(), len(users))
    latencies = sorted(row[0] for row in rows)
    timing_keys = sorted({key for row in rows for key in row[5].keys()})
    timing_p95 = {}
    for key in timing_keys:
        values = sorted(int(row[5].get(key, 0) or 0) for row in rows)
        timing_p95[key] = values[max(0, int(len(values) * 0.95) - 1)] if values else 0
    return {
        "name": name,
        "requests": len(users),
        "statuses": {str(status): sum(1 for row in rows if row[1] == status) for status in sorted({row[1] for row in rows})},
        "mismatched_response": sum(1 for row in rows if row[2]),
        "timeout": sum(1 for row in rows if row[1] == 0),
        "deduplicated": sum(1 for row in rows if row[3]),
        "learned_words_total": sum(row[4] for row in rows),
        "wall_ms": round(wall_ms, 3),
        "throughput_rps": round(len(users) / max(0.001, wall_ms / 1000), 3),
        "cpu_ms_per_request": round(((cpu_after - cpu_before) * 1000) / max(1, len(users)), 3),
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(latencies[max(0, int(len(latencies) * 0.95) - 1)], 3),
        "p99_ms": round(latencies[max(0, int(len(latencies) * 0.99) - 1)], 3),
        "pg_stat_delta": delta,
        "postgres_metrics": pg_metrics,
        "pool_wait": {
            "count": pg_metrics.get("pool_wait_count", 0),
            "ms_total": pg_metrics.get("pool_wait_ms_total", 0),
            "ms_per_request": pg_metrics.get("pool_wait_ms_per_request", 0),
            "ms_max": pg_metrics.get("pool_wait_ms_max", 0),
        },
        "timing_p95_ms": timing_p95,
        "rollback": delta.get("xact_rollback", 0),
        "deadlock": delta.get("deadlocks", 0),
        "serialization_conflict": delta.get("conflicts", 0),
    }

def parity() -> dict:
    test_users = {u.lower() for u in USERS}
    vocab_sqlite = migrate_vocab.sqlite_registry_rows()
    vocab_pg = [row for row in migrate_vocab.pg_registry_rows() if row["username"] not in test_users]
    events_sqlite = migrate_vocab.sqlite_event_rows()
    events_pg = [row for row in migrate_vocab.pg_event_rows() if row["username"] not in test_users]
    earn = {}
    for scope in ("day", "week", "month", "npc"):
        sqlite_rows = migrate_earn.sqlite_rows(scope)
        pg_rows = [row for row in migrate_earn.pg_rows(scope) if row["username"] not in test_users]
        earn[scope] = {
            "sqlite": len(sqlite_rows),
            "pg_matching": len(pg_rows),
            "sqlite_fingerprint": migrate_earn.fingerprint(sqlite_rows),
            "pg_fingerprint": migrate_earn.fingerprint(pg_rows),
            "parity": len(sqlite_rows) == len(pg_rows) and migrate_earn.fingerprint(sqlite_rows) == migrate_earn.fingerprint(pg_rows),
        }
    return {
        "registry": {
            "sqlite": len(vocab_sqlite),
            "pg_matching": len(vocab_pg),
            "sqlite_fingerprint": migrate_vocab.fingerprint(vocab_sqlite, ("username", "word_key")),
            "pg_fingerprint": migrate_vocab.fingerprint(vocab_pg, ("username", "word_key")),
        },
        "events": {
            "sqlite": len(events_sqlite),
            "pg_matching": len(events_pg),
            "sqlite_fingerprint": migrate_vocab.fingerprint(events_sqlite, ("id",)),
            "pg_fingerprint": migrate_vocab.fingerprint(events_pg, ("id",)),
        },
        "earn": earn,
    }

def main() -> int:
    global BACKEND
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=("postgres", "sqlite"), default="postgres")
    args = parser.parse_args()
    BACKEND = args.backend
    if BACKEND == "postgres" and not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("FUTURE_PG_DSN is required")
    password = os.environ.get("FUTURE_TEST_PASSWORD", "") or secrets.token_urlsafe(32)
    if server_pid_on_port(18877):
        raise RuntimeError("Port 18877 already has a listener")
    app.postgres_initialize_schema()
    original_pid_file = app.SERVER_PID_FILE.read_text(encoding="utf-8") if app.SERVER_PID_FILE.is_file() else None
    process: subprocess.Popen | None = None
    result: dict = {}
    try:
        cleanup_sqlite()
        cleanup_postgres()
        pre = parity()
        provision_users(password)
        process = start_test_server()
        wait_health(pid=int(process.pid))
        lessons = load_space_v_lessons(100)
        tokens = {username: login(username, password) for username in USERS}

        stamp = datetime(2026, 7, 25, 8, 30, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        body = complete_payload(USERS[0], lessons[0], "codex-pg-vocab-http-single", stamp)
        first = post_complete(tokens[USERS[0]], body)
        retry = post_complete(tokens[USERS[0]], body)
        invalid = requests.post(f"{BASE}/lesson/complete", json={"path": lessons[0]["path"]}, timeout=30)
        first_vocab = first[2].get("vocabulary") if isinstance(first[2].get("vocabulary"), dict) else {}
        if first[1] != 200 or int(first_vocab.get("learned_words", 0) or 0) <= 0 or retry[1] != 200:
            raise RuntimeError({"reason": "single vocabulary completion failed", "first": first[2], "retry": retry[2]})

        phases = [
            concurrency_phase("vocab_distinct_10", USERS[:10], tokens, lessons),
            concurrency_phase("vocab_distinct_50", USERS[:50], tokens, lessons),
            concurrency_phase("vocab_distinct_100", USERS, tokens, lessons),
            concurrency_phase("vocab_same_key_10", USERS[:10], tokens, lessons, same_key=True),
            concurrency_phase("vocab_same_key_50", USERS[:50], tokens, lessons, same_key=True),
            concurrency_phase("vocab_same_key_100", USERS, tokens, lessons, same_key=True),
        ]
        if any(phase["mismatched_response"] or phase["deadlock"] or phase["serialization_conflict"] for phase in phases):
            raise RuntimeError(f"Vocabulary concurrency failed: {phases}")

        before_restart = {**pg_counts(), **sqlite_counts()}
        stop_pid(int(process.pid))
        process = start_test_server()
        wait_health(pid=int(process.pid))
        token_after = login(USERS[0], password)
        retry_after = post_complete(token_after, body)
        after_restart = {**pg_counts(), **sqlite_counts()}
        if retry_after[1] != 200 or after_restart.get("pg_vocabulary_registry_users", 0) < before_restart.get("pg_vocabulary_registry_users", 0):
            raise RuntimeError({"reason": "restart readback failed", "retry": retry_after[2], "before": before_restart, "after": after_restart})

        result = {
            "vocabulary_http_gate": "ok",
            "backend": BACKEND,
            "feature_flags": ["FUTURE_DB_VOCABULARY_BACKEND", "FUTURE_DB_APPEND_EVENTS_BACKEND", "FUTURE_DB_LESSON_PROGRESS_BACKEND"],
            "pre": pre,
            "single": {"status": first[1], "retry_status": retry[1], "invalid_status": invalid.status_code, "learned_words": first_vocab.get("learned_words")},
            "concurrency": phases,
            "restart": {"before": before_restart, "after": after_restart, "retry_status": retry_after[1]},
            "production_health": compact_health(PRODUCTION_BASE, 10),
            "production_flags": {
                "FUTURE_DB_VOCABULARY_BACKEND": os.environ.get("FUTURE_DB_VOCABULARY_BACKEND", "off") or "off",
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
        print(json.dumps({"cleanup": {**pg_counts(), **sqlite_counts()}, "port_18877_busy": bool(server_pid_on_port(18877))}, ensure_ascii=True, indent=2))

if __name__ == "__main__":
    raise SystemExit(main())

