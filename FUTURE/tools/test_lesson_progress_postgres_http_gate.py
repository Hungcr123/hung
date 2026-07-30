#!/usr/bin/env python3
"""HTTP runtime gate for canonical lesson_progress with PostgreSQL in a test process."""

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

DATABASE = Path(r"C:\server data\server2.db")
BASE = "http://127.0.0.1:18877"
PRODUCTION_BASE = "http://127.0.0.1:8877"
USERS = tuple(f"codexpgprogress{index:03d}" for index in range(1, 101))


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
    env["FUTURE_DB_LESSON_PROGRESS_BACKEND"] = "postgres"
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


def canonical_sqlite_rows() -> list[dict]:
    import FUTURE.tools.migrate_lesson_progress_to_postgres as migrate

    return migrate.sqlite_rows()


def canonical_pg_rows() -> list[dict]:
    import FUTURE.tools.migrate_lesson_progress_to_postgres as migrate

    return migrate.postgres_rows()


def canonical_fingerprint(rows: list[dict]) -> str:
    import FUTURE.tools.migrate_lesson_progress_to_postgres as migrate

    return migrate.fingerprint(rows)


def lesson_progress_parity_rows(rows: list[dict]) -> list[dict]:
    return [
        row
        for row in rows
        if row.get("space") not in {"Space_PDF", "Space_Picture"}
        and not str(row.get("path") or "").lower().endswith((".space_pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"))
    ]


def canonical_parity() -> dict:
    import FUTURE.tools.migrate_lesson_progress_to_postgres as migrate

    sqlite_rows = lesson_progress_parity_rows(canonical_sqlite_rows())
    pg_rows = lesson_progress_parity_rows(canonical_pg_rows())
    sqlite_keys = {(row["username"].lower(), row["file_id"].lower()) for row in sqlite_rows}
    pg_subset = [row for row in pg_rows if (row["username"].lower(), row["file_id"].lower()) in sqlite_keys]
    return {
        "sqlite_counts": migrate.sqlite_counts(),
        "sqlite_canonical_rows": len(sqlite_rows),
        "postgres_rows_total": len(pg_rows),
        "postgres_rows_matching_sqlite_canonical": len(pg_subset),
        "sqlite_fingerprint": canonical_fingerprint(sqlite_rows),
        "postgres_fingerprint_for_sqlite_canonical": canonical_fingerprint(pg_subset),
        "shadow_read": migrate.shadow_read_check(sqlite_rows, pg_subset),
    }


def snapshot_sqlite() -> dict:
    placeholders = ",".join("?" for _ in USERS)
    connection = sqlite3.connect(DATABASE, timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        tables = {}
        for table in ("users", "server_load_test_credentials", "auth_sessions", "lesson_progress", "lesson_progress_namespaces", "append_events"):
            columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
            if table == "append_events":
                rows = [dict(row) for row in connection.execute("SELECT * FROM append_events WHERE lower(username) LIKE 'codexpgprogress%'")]
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
        connection.execute("DELETE FROM append_events WHERE lower(username) LIKE 'codexpgprogress%'")
        for table in ("lesson_progress", "lesson_progress_namespaces", "auth_sessions", "server_load_test_credentials", "users"):
            connection.execute(f'DELETE FROM "{table}" WHERE username IN ({placeholders})', USERS)
        for table in ("users", "server_load_test_credentials", "auth_sessions", "lesson_progress_namespaces", "lesson_progress", "append_events"):
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
                SELECT username,space,progress_key,path,identity,file_id,node_index,node_count,
                       learned_count,complete,server_revision,updated_at_utc,updated_epoch,record_json,migrated_at_utc,source_sha256
                FROM future_server2.lesson_progress WHERE lower(username)=ANY(%s)
                """,
                ([username.lower() for username in USERS],),
            )
            progress = [tuple(row) for row in cursor.fetchall()]
            cursor.execute(
                "SELECT username,space,updated_at_utc,updated_epoch FROM future_server2.lesson_progress_namespaces WHERE lower(username)=ANY(%s)",
                ([username.lower() for username in USERS],),
            )
            namespaces = [tuple(row) for row in cursor.fetchall()]
        return {"progress": progress, "namespaces": namespaces}

    return app.postgres_execute(_read)


def restore_postgres(snapshot: dict) -> None:
    def _write(connection):
        with connection.cursor() as cursor:
            users = [username.lower() for username in USERS]
            cursor.execute("DELETE FROM future_server2.lesson_progress WHERE lower(username)=ANY(%s)", (users,))
            cursor.execute("DELETE FROM future_server2.lesson_progress_namespaces WHERE lower(username)=ANY(%s)", (users,))
            for row in snapshot.get("namespaces", []):
                cursor.execute(
                    "INSERT INTO future_server2.lesson_progress_namespaces(username,space,updated_at_utc,updated_epoch) VALUES (%s,%s,%s,%s)",
                    row,
                )
            for row in snapshot.get("progress", []):
                cursor.execute(
                    """
                    INSERT INTO future_server2.lesson_progress
                    (username,space,progress_key,path,identity,file_id,node_index,node_count,learned_count,complete,server_revision,updated_at_utc,updated_epoch,record_json,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                    """,
                    row,
                )
        return True

    app.postgres_execute(_write)


def provision_users(password: str) -> None:
    now = app.utc_timestamp()
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        connection.execute("BEGIN IMMEDIATE")
        for index, username in enumerate(USERS, 1):
            profile = json.dumps({"full_name": f"Codex PG Progress {index:03d}", "load_test": True}, separators=(",", ":"))
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


def load_lesson_paths(limit: int = 100) -> list[dict]:
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        rows = connection.execute(
            """
            SELECT a.normalized_path,a.file_id
            FROM lesson_file_aliases a
            JOIN lesson_files f ON f.file_id=a.file_id
            WHERE a.active=1
              AND f.status='active'
              AND lower(a.normalized_path) LIKE 'common/%'
              AND lower(a.normalized_path) LIKE '%.space_v'
              AND lower(a.file_id) LIKE 'ftg-lesson-%'
            ORDER BY a.normalized_path
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        connection.close()
    if len(rows) < limit:
        raise RuntimeError(f"Need {limit} canonical Space_V lesson aliases, found {len(rows)}")
    return [{"path": row[0], "lesson_id": row[1], "key": f"codex-progress-http-{index:03d}"} for index, row in enumerate(rows, 1)]


def login(username: str, password: str) -> str:
    response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if (payload.get("server_data") or {}).get("load_test") is not True:
        raise RuntimeError(f"{username} did not login as isolated test user")
    return str(payload.get("token") or "")


def login_preload(token: str) -> dict:
    response = requests.get(f"{BASE}/server-data/login-preload", headers={"Authorization": f"Bearer {token}"}, timeout=45)
    response.raise_for_status()
    return response.json()


def lesson(lessons: list[dict], index: int) -> dict:
    return lessons[(index - 1) % len(lessons)]


def post_progress(
    token: str,
    lesson_row: dict,
    node_index: int,
    revision: int,
    operation_id: str,
    *,
    complete: bool = False,
    timestamp: str = "",
) -> tuple[float, int, dict]:
    now = app.clean(timestamp) or app.utc_timestamp()
    payload = {
        "action": "autosave",
        "path": lesson_row["path"],
        "identity": lesson_row["lesson_id"],
        "lesson_id": lesson_row["lesson_id"],
        "file_id": lesson_row["lesson_id"],
        "title": f"Codex PG Progress {lesson_row['key']}",
        "nodeIndex": node_index,
        "nodeCount": 10,
        "learnedCount": 10 if complete else node_index,
        "complete": complete,
        "savedAt": now,
        "updatedAt": now,
        "_serverRevision": revision,
        "syncOperationId": operation_id,
        "runId": "codex-progress-http-run",
        "state": {
            "path": lesson_row["path"],
            "identity": lesson_row["lesson_id"],
            "lesson_id": lesson_row["lesson_id"],
            "nodeIndex": node_index,
            "nodeCount": 10,
            "learnedCount": 10 if complete else node_index,
            "complete": complete,
            "syncOperationId": operation_id,
        },
    }
    started = time.perf_counter()
    response = requests.post(
        f"{BASE}/space-v/progress?client_source=codex_pg_progress_http&response=compact-v1",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=45,
    )
    latency = (time.perf_counter() - started) * 1000
    if response.status_code >= 400:
        raise RuntimeError(f"Progress POST failed status={response.status_code} body={response.text[:1000]}")
    return latency, response.status_code, response.json()


def progress_record(username: str, lesson_id: str) -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT record_json,server_revision,node_index,learned_count,complete FROM future_server2.lesson_progress WHERE username=%s AND file_id=%s",
                (username, lesson_id),
            )
            row = cursor.fetchone()
            if row is None:
                return {}
            return {
                "record": dict(row[0]) if isinstance(row[0], dict) else {},
                "server_revision": int(row[1] or 0),
                "node_index": int(row[2] or 0),
                "learned_count": int(row[3] or 0),
                "complete": bool(row[4]),
            }

    return app.postgres_execute(_read)


def pg_stat() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT xact_commit,xact_rollback,conflicts,deadlocks FROM pg_stat_database WHERE datname=current_database()")
            row = cursor.fetchone()
            cursor.execute("SELECT state,count(*) FROM pg_stat_activity WHERE datname=current_database() AND usename=current_user GROUP BY state")
            activity = {str(state or "none"): int(count or 0) for state, count in cursor.fetchall()}
        return {
            "xact_commit": int(row[0] or 0),
            "xact_rollback": int(row[1] or 0),
            "conflicts": int(row[2] or 0),
            "deadlocks": int(row[3] or 0),
            "activity": activity,
        }

    return app.postgres_execute(_read)


def stat_delta(before: dict, after: dict) -> dict:
    return {key: int(after.get(key, 0) or 0) - int(before.get(key, 0) or 0) for key in ("xact_commit", "xact_rollback", "conflicts", "deadlocks")} | {"activity_after": after.get("activity", {})}


def concurrency_phase(name: str, users: tuple[str, ...], tokens: dict[str, str], lessons: list[dict], *, contended: bool = False) -> dict:
    before = pg_stat()
    process = psutil.Process(server_pid_on_port(18877))
    cpu_before = sum(process.cpu_times()[:2])

    def one(index_username: tuple[int, str]) -> tuple[float, int, bool, str]:
        index, username = index_username
        item = lesson(lessons, 1 if contended else index)
        op = f"{name}-{index}-{time.time_ns()}"
        revision = index if contended else 1
        latency, status, payload = post_progress(tokens[username], item, min(10, index), revision, op, complete=index % 5 == 0)
        progress = payload.get("progress") if isinstance(payload.get("progress"), dict) else {}
        mismatch = app.clean(progress.get("lesson_id") or progress.get("file_id") or progress.get("identity")) != item["lesson_id"]
        return latency, status, mismatch, username

    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(50, len(users))) as pool:
        rows = list(pool.map(one, enumerate(users, start=1)))
    wall_ms = (time.perf_counter() - started) * 1000
    cpu_after = sum(process.cpu_times()[:2])
    after = pg_stat()
    latencies = sorted(row[0] for row in rows)
    return {
        "name": name,
        "users": len(users),
        "statuses": {str(status): sum(1 for row in rows if row[1] == status) for status in sorted({row[1] for row in rows})},
        "mismatched_response": sum(1 for row in rows if row[2]),
        "wall_ms": round(wall_ms, 3),
        "cpu_ms_per_request": round(((cpu_after - cpu_before) * 1000) / max(1, len(users)), 3),
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(latencies[max(0, int(len(latencies) * 0.95) - 1)], 3),
        "p99_ms": round(latencies[max(0, int(len(latencies) * 0.99) - 1)], 3),
        "pg_stat_delta": stat_delta(before, after),
        "pool_wait": "not_exposed",
        "timeout": 0,
        "rollback": stat_delta(before, after).get("xact_rollback", 0),
        "deadlock": stat_delta(before, after).get("deadlocks", 0),
        "serialization_conflict": stat_delta(before, after).get("conflicts", 0),
    }


def contended_same_key_phase(name: str, username: str, token: str, lessons: list[dict], requests_count: int) -> dict:
    before = pg_stat()
    item = lesson(lessons, 2)
    before_row = progress_record(username, item["lesson_id"])
    process = psutil.Process(server_pid_on_port(18877))
    cpu_before = sum(process.cpu_times()[:2])

    def one(index: int) -> tuple[float, int, bool]:
        revision = index if index % 3 else max(1, index - 2)
        node_index = min(10, revision)
        latency, status, payload = post_progress(
            token,
            item,
            node_index,
            revision,
            f"{name}-same-key-{index}",
            complete=revision >= requests_count - 1,
            timestamp=f"2026-07-25T00:{revision // 60:02d}:{revision % 60:02d}Z",
        )
        progress = payload.get("progress") if isinstance(payload.get("progress"), dict) else {}
        mismatch = app.clean(progress.get("lesson_id") or progress.get("file_id") or progress.get("identity")) != item["lesson_id"]
        return latency, status, mismatch

    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(50, requests_count)) as pool:
        rows = list(pool.map(one, range(1, requests_count + 1)))
    wall_ms = (time.perf_counter() - started) * 1000
    final = progress_record(username, item["lesson_id"])
    cpu_after = sum(process.cpu_times()[:2])
    after = pg_stat()
    latencies = sorted(row[0] for row in rows)
    delta = stat_delta(before, after)
    expected_node_index = 10
    return {
        "name": name,
        "requests": requests_count,
        "same_user": username,
        "same_lesson_id": item["lesson_id"],
        "statuses": {str(status): sum(1 for row in rows if row[1] == status) for status in sorted({row[1] for row in rows})},
        "mismatched_response": sum(1 for row in rows if row[2]),
        "initial_revision": before_row.get("server_revision", 0),
        "final_revision": final.get("server_revision"),
        "final_node_index": final.get("node_index"),
        "expected_node_index": expected_node_index,
        "no_regression": int(final.get("server_revision", 0) or 0) >= int(before_row.get("server_revision", 0) or 0) and int(final.get("node_index", 0) or 0) >= expected_node_index,
        "wall_ms": round(wall_ms, 3),
        "cpu_ms_per_request": round(((cpu_after - cpu_before) * 1000) / max(1, requests_count), 3),
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


def assert_no_test_rows() -> dict:
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        sqlite_progress = int(connection.execute("SELECT count(*) FROM lesson_progress WHERE lower(username) LIKE 'codexpgprogress%'").fetchone()[0] or 0)
        sqlite_users = int(connection.execute("SELECT count(*) FROM users WHERE lower(username) LIKE 'codexpgprogress%'").fetchone()[0] or 0)
    finally:
        connection.close()

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM future_server2.lesson_progress WHERE lower(username) LIKE 'codexpgprogress%'")
            pg_progress = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT count(*) FROM future_server2.lesson_progress_namespaces WHERE lower(username) LIKE 'codexpgprogress%'")
            pg_namespaces = int(cursor.fetchone()[0] or 0)
        return {"postgres_progress": pg_progress, "postgres_namespaces": pg_namespaces}

    return {"sqlite_progress": sqlite_progress, "sqlite_users": sqlite_users, **app.postgres_execute(_read)}


def main() -> int:
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("FUTURE_PG_DSN is required")
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this gate only")
    if server_pid_on_port(18877):
        raise RuntimeError("Port 18877 already has a listener")

    original_pid_file = app.SERVER_PID_FILE.read_text(encoding="utf-8") if app.SERVER_PID_FILE.is_file() else None
    sqlite_before = snapshot_sqlite()
    postgres_before = snapshot_postgres()
    pre_parity = canonical_parity()
    if not pre_parity["shadow_read"].get("ok"):
        raise RuntimeError(f"Initial canonical parity failed: {pre_parity}")
    process: subprocess.Popen | None = None
    result: dict = {}
    try:
        provision_users(password)
        process = start_test_server()
        wait_health(pid=int(process.pid))
        tokens = {username: login(username, password) for username in USERS}
        lessons = load_lesson_paths(100)
        read_missing = progress_record(USERS[0], lesson(lessons, 1)["lesson_id"])
        first_latency, first_status, first = post_progress(tokens[USERS[0]], lesson(lessons, 1), 2, 1, "codex-progress-first")
        after_first = progress_record(USERS[0], lesson(lessons, 1)["lesson_id"])
        retry_latency, retry_status, retry = post_progress(tokens[USERS[0]], lesson(lessons, 1), 2, 1, "codex-progress-first")
        after_retry = progress_record(USERS[0], lesson(lessons, 1)["lesson_id"])
        different_latency, different_status, different = post_progress(tokens[USERS[0]], lesson(lessons, 1), 4, 2, "codex-progress-different")
        stale_latency, stale_status, stale = post_progress(
            tokens[USERS[0]],
            lesson(lessons, 1),
            1,
            1,
            "codex-progress-stale",
            timestamp="2020-01-01T00:00:00Z",
        )
        after_stale = progress_record(USERS[0], lesson(lessons, 1)["lesson_id"])
        complete_latency, complete_status, complete = post_progress(tokens[USERS[0]], lesson(lessons, 1), 10, 3, "codex-progress-complete", complete=True)
        after_complete = progress_record(USERS[0], lesson(lessons, 1)["lesson_id"])
        invalid_response = requests.post(
            f"{BASE}/space-v/progress?client_source=codex_pg_progress_invalid",
            headers={"Authorization": f"Bearer {tokens[USERS[0]]}"},
            json={"path": "common/codex/invalid.Space_V", "identity": "legacy-path-only", "nodeIndex": 1, "nodeCount": 10},
            timeout=30,
        )
        phases = [
            concurrency_phase("distinct_10", USERS[:10], tokens, lessons),
            concurrency_phase("distinct_50", USERS[:50], tokens, lessons),
            concurrency_phase("distinct_100", USERS, tokens, lessons),
            concurrency_phase("contended_10", USERS[:10], tokens, lessons, contended=True),
            concurrency_phase("contended_50", USERS[:50], tokens, lessons, contended=True),
            concurrency_phase("contended_100", USERS, tokens, lessons, contended=True),
            contended_same_key_phase("same_key_10", USERS[0], tokens[USERS[0]], lessons, 10),
            contended_same_key_phase("same_key_50", USERS[0], tokens[USERS[0]], lessons, 50),
            contended_same_key_phase("same_key_100", USERS[0], tokens[USERS[0]], lessons, 100),
        ]
        if any(phase["mismatched_response"] or phase["deadlock"] or phase["serialization_conflict"] or not phase.get("no_regression", True) for phase in phases):
            raise RuntimeError(f"Concurrency phase failed: {phases}")
        if int(after_first.get("node_index", -1)) != 2:
            raise RuntimeError("HTTP create/read-after-write did not persist nodeIndex=2")
        if after_retry != after_first:
            raise RuntimeError("Exact retry changed PostgreSQL progress row")
        if int(after_stale.get("node_index", -1)) != 4:
            raise RuntimeError("Stale revision overwrote newer progress")
        if not after_complete.get("complete"):
            raise RuntimeError("Completion state was not persisted")
        if invalid_response.status_code < 400:
            raise RuntimeError("Invalid non-canonical lesson ID unexpectedly succeeded")
        before_restart = progress_record(USERS[0], lesson(lessons, 1)["lesson_id"])
        stop_pid(int(process.pid))
        process = start_test_server()
        wait_health(pid=int(process.pid))
        token_after_restart = login(USERS[0], password)
        restart_started = time.perf_counter()
        restart_payload = login_preload(token_after_restart)
        restart_latency = (time.perf_counter() - restart_started) * 1000
        restart_status = 200
        after_restart = progress_record(USERS[0], lesson(lessons, 1)["lesson_id"])
        if after_restart != before_restart:
            raise RuntimeError("Restart/readback changed durable PostgreSQL progress state")
        final_parity = canonical_parity()
        result = {
            "lesson_progress_postgres_http_gate": "ok",
            "feature_flag": "FUTURE_DB_LESSON_PROGRESS_BACKEND",
            "pre_parity": pre_parity,
            "legacy_path_only_rows": pre_parity.get("sqlite_counts", {}).get("legacy_path_pending"),
            "read_missing": read_missing,
            "single": {
                "first": {"status": first_status, "latency_ms": round(first_latency, 3), "response_schema": first.get("response_schema")},
                "retry": {"status": retry_status, "latency_ms": round(retry_latency, 3), "unchanged": after_retry == after_first},
                "different_payload": {"status": different_status, "latency_ms": round(different_latency, 3), "node_index": after_stale.get("node_index")},
                "stale_revision": {"status": stale_status, "latency_ms": round(stale_latency, 3), "rejected_by_revision_guard": int(after_stale.get("node_index", -1)) == 4},
                "completion": {"status": complete_status, "latency_ms": round(complete_latency, 3), "complete": after_complete.get("complete")},
                "invalid_lesson_id_status": invalid_response.status_code,
            },
            "concurrency": phases,
            "restart": {"status": restart_status, "latency_ms": round(restart_latency, 3), "stable": after_restart == before_restart, "preload_ok": bool(restart_payload.get("ok"))},
            "shadow_read": final_parity["shadow_read"],
            "production_health": health(PRODUCTION_BASE, 10),
            "production_flag": os.environ.get("FUTURE_DB_LESSON_PROGRESS_BACKEND", "off") or "off",
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
