#!/usr/bin/env python3
"""HTTP runtime gate for append_events with PostgreSQL in a test process."""

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
import time
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
USERS = tuple(f"codexpgappend{index:03d}" for index in range(1, 101))


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


def start_test_server() -> subprocess.Popen:
    env = dict(os.environ)
    env["FUTURE_DB_APPEND_EVENTS_BACKEND"] = "postgres"
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
            profile = json.dumps({"full_name": f"Codex PG Append {index:03d}", "load_test": True}, separators=(",", ":"))
            is_admin = 1 if index == 1 else 0
            connection.execute(
                "INSERT INTO users(username,is_admin,is_test,profile_json,updated_at_utc) VALUES(?,?,1,?,?) "
                "ON CONFLICT(username) DO UPDATE SET is_admin=excluded.is_admin,is_test=1,profile_json=excluded.profile_json,updated_at_utc=excluded.updated_at_utc",
                (username, is_admin, profile, now),
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


def snapshot_sqlite() -> dict:
    placeholders = ",".join("?" for _ in USERS)
    connection = sqlite3.connect(DATABASE, timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        tables = {}
        for table in ("users", "server_load_test_credentials", "auth_sessions", "append_events"):
            columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
            if table == "append_events":
                rows = [dict(row) for row in connection.execute("SELECT * FROM append_events WHERE lower(username) LIKE 'codexpgappend%'")]
            else:
                rows = [dict(row) for row in connection.execute(f'SELECT * FROM "{table}" WHERE username IN ({placeholders})', USERS)]
            tables[table] = {"columns": columns, "rows": rows}
        return {"tables": tables}
    finally:
        connection.close()


def restore_sqlite(snapshot: dict) -> None:
    placeholders = ",".join("?" for _ in USERS)
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM append_events WHERE lower(username) LIKE 'codexpgappend%'")
        for table in ("auth_sessions", "server_load_test_credentials", "users"):
            connection.execute(f'DELETE FROM "{table}" WHERE username IN ({placeholders})', USERS)
        for table in ("users", "server_load_test_credentials", "auth_sessions", "append_events"):
            rows = snapshot.get("tables", {}).get(table, {}).get("rows", [])
            columns = snapshot.get("tables", {}).get(table, {}).get("columns", [])
            if rows:
                sql = f'INSERT INTO "{table}" ({",".join(columns)}) VALUES ({",".join("?" for _ in columns)})'
                connection.executemany(sql, [[row.get(column) for column in columns] for row in rows])
        connection.commit()
    finally:
        connection.close()


def snapshot_postgres() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id,stream,username,event_at_utc,event_epoch,event_json,event_key,migrated_at_utc,source_sha256
                FROM future_server2.append_events WHERE lower(username) LIKE 'codexpgappend%'
                """
            )
            return {"events": [tuple(row) for row in cursor.fetchall()]}

    return app.postgres_execute(_read)


def restore_postgres(snapshot: dict) -> None:
    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.append_events WHERE lower(username) LIKE 'codexpgappend%' OR lower(event_key) LIKE 'codex-pg-append-http-%'")
            for row in snapshot.get("events", []):
                cursor.execute(
                    """
                    INSERT INTO future_server2.append_events
                        (id,stream,username,event_at_utc,event_epoch,event_json,event_key,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s)
                    """,
                    row,
                )
        return True

    app.postgres_execute(_write)


def login(username: str, password: str) -> tuple[float, int, str]:
    started = time.perf_counter()
    response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=45)
    latency = (time.perf_counter() - started) * 1000
    if response.status_code >= 400:
        return latency, response.status_code, ""
    payload = response.json()
    if (payload.get("server_data") or {}).get("load_test") is not True:
        raise RuntimeError(f"{username} did not login as isolated test user")
    return latency, response.status_code, str(payload.get("token") or "")


def pg_test_event_counts() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*),count(DISTINCT username) FROM future_server2.append_events WHERE stream='screen_transport' AND lower(username) LIKE 'codexpgappend%'")
            row = cursor.fetchone()
            cursor.execute("SELECT count(*) FROM future_server2.append_events WHERE lower(username) LIKE 'codexpgappend%' AND stream<>'screen_transport'")
            other = int(cursor.fetchone()[0] or 0)
        return {"transport_rows": int(row[0] or 0), "transport_users": int(row[1] or 0), "other_stream_rows": other}

    return app.postgres_execute(_read)


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


def post_transport(token: str, username: str, index: int) -> tuple[float, int, bool]:
    payload = {
        "username": username,
        "event": "codex-pg-append-http",
        "mode": "postgres-gate",
        "session": f"codex-pg-append-http-{index:03d}",
        "transport": "test",
        "has_turn": True,
    }
    started = time.perf_counter()
    response = requests.post(f"{BASE}/screen/auth-admin/transport-log", headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=45)
    latency = (time.perf_counter() - started) * 1000
    log = response.json().get("log") if response.status_code == 200 else {}
    mismatch = response.status_code != 200 or (log if isinstance(log, dict) else {}).get("username") != username
    return latency, response.status_code, mismatch


def concurrency_phase(name: str, users: tuple[str, ...], admin_token: str) -> dict:
    before = pg_stat()
    process = psutil.Process(server_pid_on_port(18877))
    cpu_before = sum(process.cpu_times()[:2])

    def one(item: tuple[int, str]) -> tuple[float, int, bool]:
        index, username = item
        return post_transport(admin_token, username, index)

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


def assert_no_test_rows() -> dict:
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        sqlite_events = int(connection.execute("SELECT count(*) FROM append_events WHERE lower(username) LIKE 'codexpgappend%'").fetchone()[0] or 0)
        sqlite_users = int(connection.execute("SELECT count(*) FROM users WHERE lower(username) LIKE 'codexpgappend%'").fetchone()[0] or 0)
    finally:
        connection.close()
    pg_counts = pg_test_event_counts()
    return {"sqlite_events": sqlite_events, "sqlite_users": sqlite_users, **pg_counts}


def main() -> int:
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("FUTURE_PG_DSN is required")
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this gate only")
    if server_pid_on_port(18877):
        raise RuntimeError("Port 18877 already has a listener")

    pre = parity()
    if pre["append_events"]["sqlite_fingerprint"] != pre["append_events"]["postgres_fingerprint"]:
        raise RuntimeError(f"Pre-test append_events parity failed: {pre}")
    if pre["completion_events"]["sqlite_fingerprint"] != pre["completion_events"]["postgres_fingerprint"]:
        raise RuntimeError(f"Pre-test completion parity failed: {pre}")

    original_pid_file = app.SERVER_PID_FILE.read_text(encoding="utf-8") if app.SERVER_PID_FILE.is_file() else None
    sqlite_before = snapshot_sqlite()
    postgres_before = snapshot_postgres()
    process: subprocess.Popen | None = None
    result: dict = {}
    try:
        provision_users(password)
        process = start_test_server()
        wait_health(pid=int(process.pid))
        invalid = requests.post(f"{BASE}/auth/login", json={"username": USERS[0], "password": "wrong"}, timeout=30)
        _login_ms, single_status, admin_token = login(USERS[0], password)
        single_transport = post_transport(admin_token, USERS[0], 0)
        forbidden = requests.post(f"{BASE}/screen/auth-admin/transport-log", json={"username": USERS[0]}, timeout=30)
        phases = [
            concurrency_phase("transport_append_distinct_10", USERS[:10], admin_token),
            concurrency_phase("transport_append_distinct_50", USERS[:50], admin_token),
            concurrency_phase("transport_append_distinct_100", USERS, admin_token),
        ]
        if any(phase["mismatched_response"] or phase["deadlock"] or phase["serialization_conflict"] for phase in phases):
            raise RuntimeError(f"Concurrency phase failed: {phases}")
        before_restart = pg_test_event_counts()
        if before_restart["transport_users"] < 100:
            raise RuntimeError(f"append_events HTTP gate did not create all expected PG transport rows: {before_restart}")
        stop_pid(int(process.pid))
        process = start_test_server()
        wait_health(pid=int(process.pid))
        _login_ms, _status, admin_token = login(USERS[0], password)
        post_transport(admin_token, USERS[0], 999)
        after_restart = pg_test_event_counts()
        if after_restart["transport_users"] < before_restart["transport_users"] or after_restart["transport_rows"] < before_restart["transport_rows"]:
            raise RuntimeError({"reason": "append_events restart readback regressed", "before": before_restart, "after": after_restart})
        final = parity()
        result = {
            "append_events_postgres_http_gate": "ok",
            "feature_flag": "FUTURE_DB_APPEND_EVENTS_BACKEND",
            "pre": pre,
            "single_login_status": single_status,
            "single_transport_status": single_transport[1],
            "invalid_login_status": invalid.status_code,
            "unauthorized_transport_status": forbidden.status_code,
            "concurrency": phases,
            "restart": {"before": before_restart, "after": after_restart},
            "shadow_read": final,
            "production_health": health(PRODUCTION_BASE, 10),
            "production_flags": {"FUTURE_DB_APPEND_EVENTS_BACKEND": os.environ.get("FUTURE_DB_APPEND_EVENTS_BACKEND", "off") or "off"},
        }
        print(json.dumps(result, ensure_ascii=True, indent=2, default=str))
        return 0
    finally:
        if process is not None:
            stop_pid(int(process.pid))
        restore_sqlite(sqlite_before)
        restore_postgres(postgres_before)
        restore_pid_file(original_pid_file)
        cleanup = assert_no_test_rows()
        if result:
            print(json.dumps({"cleanup": cleanup, "port_18877_busy": bool(server_pid_on_port(18877))}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
