#!/usr/bin/env python3
"""HTTP runtime gate for user_preferences with PostgreSQL enabled in one test process."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import sqlite3
import statistics
import subprocess
import sys
import time
import uuid
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app  # noqa: E402

BASE = "http://127.0.0.1:8877"
DATABASE = Path(r"C:\server data\server2.db")
USERS = tuple(f"codexload{index:03d}" for index in range(1, 101))


def server_process() -> psutil.Process | None:
    for connection in psutil.net_connections(kind="tcp"):
        if connection.laddr and connection.laddr.port == 8877 and connection.status == psutil.CONN_LISTEN and connection.pid:
            return psutil.Process(connection.pid)
    return None


def wait_health(expected_flag: str | None = None, old_pid: int = 0, timeout: float = 60.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            payload = requests.get(f"{BASE}/health", timeout=3).json()
            pid = int(payload.get("pid", 0) or 0)
            if payload.get("ok") and pid and pid != old_pid:
                if expected_flag is None or os.environ.get("FUTURE_DB_USER_PREFERENCES_BACKEND", "") == expected_flag:
                    return payload
        except Exception:
            pass
        time.sleep(0.4)
    raise RuntimeError("Server 2 did not become healthy")


def stop_server() -> int:
    process = server_process()
    if not process:
        return 0
    pid = int(process.pid)
    process.kill()
    process.wait(timeout=20)
    return pid


def start_server(postgres_preferences: bool) -> subprocess.Popen:
    env = dict(os.environ)
    if postgres_preferences:
        env["FUTURE_DB_USER_PREFERENCES_BACKEND"] = "postgres"
    else:
        env.pop("FUTURE_DB_USER_PREFERENCES_BACKEND", None)
    return subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--replace-old"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def sqlite_snapshot(usernames: tuple[str, ...]) -> dict[str, tuple | None]:
    placeholders = ",".join("?" for _ in usernames)
    connection = sqlite3.connect(DATABASE)
    try:
        rows = connection.execute(
            f"SELECT username,preferences_json,server_revision,updated_at_utc,updated_epoch FROM user_preferences WHERE lower(username) IN ({placeholders})",
            tuple(username.lower() for username in usernames),
        ).fetchall()
        found = {str(row[0]).lower(): row[1:] for row in rows}
        return {username.lower(): found.get(username.lower()) for username in usernames}
    finally:
        connection.close()


def restore_sqlite(snapshot: dict[str, tuple | None]) -> None:
    connection = sqlite3.connect(DATABASE)
    try:
        connection.execute("BEGIN IMMEDIATE")
        for username, row in snapshot.items():
            if row is None:
                connection.execute("DELETE FROM user_preferences WHERE lower(username)=lower(?)", (username,))
            else:
                connection.execute(
                    "INSERT INTO user_preferences(username,preferences_json,server_revision,updated_at_utc,updated_epoch) VALUES(?,?,?,?,?) "
                    "ON CONFLICT(username) DO UPDATE SET preferences_json=excluded.preferences_json,server_revision=excluded.server_revision,"
                    "updated_at_utc=excluded.updated_at_utc,updated_epoch=excluded.updated_epoch",
                    (username, *row),
                )
        connection.commit()
    finally:
        connection.close()


def postgres_snapshot(usernames: tuple[str, ...]) -> dict[str, tuple | None]:
    keys = tuple(username.lower() for username in usernames)

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT username,preferences_json,server_revision,updated_at_utc,updated_epoch FROM future_server2.user_preferences WHERE lower(username)=ANY(%s)",
                (list(keys),),
            )
            rows = cursor.fetchall()
        found = {str(row[0]).lower(): row[1:] for row in rows}
        return {username.lower(): found.get(username.lower()) for username in usernames}

    return app.postgres_execute(_read)


def restore_postgres(snapshot: dict[str, tuple | None]) -> None:
    def _write(connection):
        with connection.cursor() as cursor:
            for username, row in snapshot.items():
                if row is None:
                    cursor.execute("DELETE FROM future_server2.user_preferences WHERE lower(username)=lower(%s)", (username,))
                else:
                    raw = json.dumps(row[0] if isinstance(row[0], dict) else {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
                    cursor.execute(
                        """
                        INSERT INTO future_server2.user_preferences(username,preferences_json,server_revision,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                        VALUES (%s,%s::jsonb,%s,%s,%s,%s,%s)
                        ON CONFLICT(username) DO UPDATE SET
                            preferences_json=excluded.preferences_json,
                            server_revision=excluded.server_revision,
                            updated_at_utc=excluded.updated_at_utc,
                            updated_epoch=excluded.updated_epoch,
                            migrated_at_utc=excluded.migrated_at_utc,
                            source_sha256=excluded.source_sha256
                        """,
                        (username, raw, row[1], row[2], row[3], app.utc_timestamp(), hashlib.sha256(raw.encode("utf-8")).hexdigest()),
                    )

    app.postgres_execute(_write)


def pg_stat() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT xact_commit,xact_rollback,blks_read,blks_hit,tup_returned,tup_fetched,tup_inserted,tup_updated,tup_deleted,conflicts,deadlocks,temp_bytes
                FROM pg_stat_database WHERE datname=current_database()
                """
            )
            row = cursor.fetchone()
            cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND usename=current_user")
            sessions = int(cursor.fetchone()[0] or 0)
        keys = ("xact_commit", "xact_rollback", "blks_read", "blks_hit", "tup_returned", "tup_fetched", "tup_inserted", "tup_updated", "tup_deleted", "conflicts", "deadlocks", "temp_bytes")
        return {key: int(value or 0) for key, value in zip(keys, row)} | {"sessions": sessions}

    return app.postgres_execute(_read)


def pg_stat_delta(before: dict, after: dict) -> dict:
    return {key: int(after.get(key, 0) or 0) - int(before.get(key, 0) or 0) for key in after.keys()}


def login(username: str, password: str) -> tuple[str, dict]:
    response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    token = str(payload.get("token") or "")
    if not token:
        raise RuntimeError(f"Missing login token for {username}")
    return token, payload


def get_me(token: str) -> dict:
    response = requests.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    response.raise_for_status()
    return response.json()


def save_preferences(token: str, payload: dict) -> tuple[float, int, int, dict]:
    started = time.perf_counter()
    response = requests.post(
        f"{BASE}/auth/preferences",
        headers={"Authorization": f"Bearer {token}", "X-Future-Response-Mode": "preferences-compact-v1"},
        json=payload,
        timeout=30,
    )
    latency = (time.perf_counter() - started) * 1000
    decoded = len(response.content)
    response.raise_for_status()
    return latency, response.status_code, decoded, response.json()


def phase(name: str, usernames: tuple[str, ...], tokens: dict[str, str], marker: str) -> dict:
    payloads = {
        username: {
            "chat_voice": {"enabled": True, "voice": "male-us", "label": f"PG Gate {marker} {index:03d}"},
            "question_animation": {"paused": bool(index % 2)},
            "pdf_settings": {"ui": {"aiNoticeVoice": f"pg-gate-{marker}-{index:03d}", "aiNoticeSpeakMode": "off"}},
        }
        for index, username in enumerate(usernames, 1)
    }
    before = pg_stat()

    def one(username: str):
        latency, status, decoded, payload = save_preferences(tokens[username], payloads[username])
        return latency, status, decoded, payload

    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(40, len(usernames))) as pool:
        rows = list(pool.map(one, usernames))
    wall_ms = (time.perf_counter() - started) * 1000
    after = pg_stat()
    latencies = sorted(row[0] for row in rows)
    return {
        "name": name,
        "users": len(usernames),
        "statuses": {str(status): sum(1 for row in rows if row[1] == status) for status in sorted({row[1] for row in rows})},
        "wall_ms": round(wall_ms, 3),
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(latencies[max(0, int(len(latencies) * 0.95) - 1)], 3),
        "p99_ms": round(latencies[max(0, int(len(latencies) * 0.99) - 1)], 3),
        "decoded_response_bytes": sum(row[2] for row in rows),
        "revision_values": sorted({int((row[3] or {}).get("server_revision", 0) or 0) for row in rows})[:10],
        "pg_stat_delta": pg_stat_delta(before, after),
    }


def normalized_sqlite_after_patch(username: str, patch: dict) -> dict:
    current = app.read_user_preferences(username)
    return app.normalize_user_preferences(patch, current)


def main() -> int:
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("FUTURE_PG_DSN is required")
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this runtime gate only")
    app.postgres_initialize_schema()
    users = USERS
    sqlite_before = sqlite_snapshot(users)
    postgres_before = postgres_snapshot(users)
    original_pid = int(server_process().pid) if server_process() else 0
    marker = uuid.uuid4().hex[:12]
    final_pid = 0
    try:
        stop_server()
        start_server(postgres_preferences=True)
        health = wait_health(old_pid=original_pid)
        final_pid = int(health.get("pid", 0) or 0)
        tokens = {}
        login_payloads = {}
        for username in users:
            token, payload = login(username, password)
            tokens[username] = token
            login_payloads[username] = payload
        if not all((payload.get("server_data") or {}).get("load_test") is True for payload in login_payloads.values()):
            raise RuntimeError("One or more load-test logins were not isolated")
        single_user = users[0]
        before_me = get_me(tokens[single_user])
        patch = {"chat_voice": {"enabled": True, "voice": "female-us", "label": f"PG Gate Single {marker}"}}
        first = save_preferences(tokens[single_user], patch)[3]
        after_me = get_me(tokens[single_user])
        retry = save_preferences(tokens[single_user], patch)[3]
        if int(retry.get("server_revision", 0) or 0) != int(first.get("server_revision", 0) or 0):
            raise RuntimeError("Exact retry changed server_revision")
        sqlite_expected = normalized_sqlite_after_patch(single_user, patch)
        pg_read = ((after_me.get("preferences") or {}).get("chat_voice") or {}).get("label")
        if pg_read != sqlite_expected.get("chat_voice", {}).get("label"):
            raise RuntimeError("PostgreSQL HTTP read-after-write does not match SQLite normalization")
        phases = [
            phase("concurrent_10", users[:10], tokens, marker),
            phase("concurrent_50", users[:50], tokens, marker),
            phase("concurrent_100", users, tokens, marker),
        ]
        old_pid = stop_server()
        start_server(postgres_preferences=True)
        restarted = wait_health(old_pid=old_pid)
        final_pid = int(restarted.get("pid", 0) or 0)
        token, login_after_restart = login(single_user, password)
        restored_label = (((login_after_restart.get("preferences") or {}).get("chat_voice") or {}).get("label"))
        if restored_label != f"PG Gate {marker} 001":
            raise RuntimeError(f"Preference did not restore after Server 2 restart: {restored_label}")
        sqlite_after = sqlite_snapshot(users)
        sqlite_unchanged = sqlite_after == sqlite_before
        result = {
            "user_preferences_postgres_http_gate": "ok",
            "test_pid": final_pid,
            "login_users": len(tokens),
            "read_before": bool(before_me.get("ok")),
            "single_update_revision": int(first.get("server_revision", 0) or 0),
            "exact_retry_revision": int(retry.get("server_revision", 0) or 0),
            "read_after_write_label": pg_read,
            "response_parity_with_sqlite_normalizer": True,
            "phases": phases,
            "server_restart_readback": True,
            "postgres_deadlock_deltas": [item["pg_stat_delta"].get("deadlocks", 0) for item in phases],
            "postgres_rollback_deltas": [item["pg_stat_delta"].get("xact_rollback", 0) for item in phases],
            "sqlite_authoritative_unchanged": sqlite_unchanged,
            "production_flag_global": os.environ.get("FUTURE_DB_USER_PREFERENCES_BACKEND", "") or "off",
        }
        if not sqlite_unchanged:
            raise RuntimeError("SQLite user_preferences changed during PostgreSQL-only runtime gate")
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    finally:
        try:
            stop_server()
        except Exception:
            pass
        try:
            restore_postgres(postgres_before)
            restore_sqlite(sqlite_before)
        finally:
            start_server(postgres_preferences=False)
            wait_health(old_pid=final_pid)


if __name__ == "__main__":
    raise SystemExit(main())
