#!/usr/bin/env python3
"""HTTP runtime gate for Space_PDF progress and pdf_drawings with PostgreSQL."""

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
from datetime import datetime, timedelta, timezone
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
USERS = tuple(f"codexpgpdf{index:03d}" for index in range(1, 101))


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
    env["FUTURE_DB_PDF_DRAWINGS_BACKEND"] = "postgres"
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


def pdf_drawings_parity() -> dict:
    import FUTURE.tools.migrate_pdf_drawings_to_postgres as migrate

    sqlite_rows = migrate.sqlite_rows()
    pg_rows = migrate.postgres_rows()
    sqlite_keys = {(row["username"].lower(), row["document_key"], int(row["page"])) for row in sqlite_rows}
    pg_subset = [row for row in pg_rows if (row["username"].lower(), row["document_key"], int(row["page"])) in sqlite_keys]
    sqlite_fp = migrate.fingerprint(sqlite_rows)
    pg_fp = migrate.fingerprint(pg_subset)
    return {
        "sqlite_rows": len(sqlite_rows),
        "postgres_rows_total": len(pg_rows),
        "postgres_rows_matching_sqlite": len(pg_subset),
        "sqlite_fingerprint": sqlite_fp,
        "postgres_fingerprint_for_sqlite": pg_fp,
        "missing_count": len(sqlite_rows) - len(pg_subset),
        "mismatch_count": 0 if sqlite_fp == pg_fp else 1,
        "ok": sqlite_fp == pg_fp and len(sqlite_rows) == len(pg_subset),
    }


def lesson_progress_parity() -> dict:
    import FUTURE.tools.migrate_lesson_progress_to_postgres as migrate

    sqlite_rows = migrate.sqlite_rows()
    pg_rows = migrate.postgres_rows()
    sqlite_keys = {(row["username"].lower(), row["file_id"].lower()) for row in sqlite_rows}
    pg_subset = [row for row in pg_rows if (row["username"].lower(), row["file_id"].lower()) in sqlite_keys]
    return migrate.shadow_read_check(sqlite_rows, pg_subset)


def snapshot_sqlite() -> dict:
    placeholders = ",".join("?" for _ in USERS)
    connection = sqlite3.connect(DATABASE, timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        tables = {}
        for table in ("users", "server_load_test_credentials", "auth_sessions", "lesson_progress", "lesson_progress_namespaces", "pdf_drawings"):
            columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
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
        for table in ("pdf_drawings", "lesson_progress", "lesson_progress_namespaces", "auth_sessions", "server_load_test_credentials", "users"):
            connection.execute(f'DELETE FROM "{table}" WHERE username IN ({placeholders})', USERS)
        for table in ("users", "server_load_test_credentials", "auth_sessions", "lesson_progress_namespaces", "lesson_progress", "pdf_drawings"):
            rows = snapshot.get("tables", {}).get(table, {}).get("rows", [])
            columns = snapshot.get("tables", {}).get(table, {}).get("columns", [])
            if rows:
                sql = f'INSERT INTO "{table}" ({",".join(columns)}) VALUES ({",".join("?" for _ in columns)})'
                connection.executemany(sql, [[row.get(column) for column in columns] for row in rows])
        connection.commit()
    finally:
        connection.close()


def snapshot_postgres() -> dict:
    users = [username.lower() for username in USERS]

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM future_server2.pdf_drawings WHERE lower(username)=ANY(%s)", (users,))
            drawings = [tuple(row) for row in cursor.fetchall()]
            cursor.execute("SELECT * FROM future_server2.lesson_progress WHERE lower(username)=ANY(%s)", (users,))
            progress = [tuple(row) for row in cursor.fetchall()]
            cursor.execute("SELECT * FROM future_server2.lesson_progress_namespaces WHERE lower(username)=ANY(%s)", (users,))
            namespaces = [tuple(row) for row in cursor.fetchall()]
        return {"drawings": drawings, "progress": progress, "namespaces": namespaces}

    return app.postgres_execute(_read)


def restore_postgres(snapshot: dict) -> None:
    users = [username.lower() for username in USERS]

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.pdf_drawings WHERE lower(username)=ANY(%s)", (users,))
            cursor.execute("DELETE FROM future_server2.lesson_progress WHERE lower(username)=ANY(%s)", (users,))
            cursor.execute("DELETE FROM future_server2.lesson_progress_namespaces WHERE lower(username)=ANY(%s)", (users,))
            for row in snapshot.get("namespaces", []):
                cursor.execute("INSERT INTO future_server2.lesson_progress_namespaces VALUES (%s,%s,%s,%s)", row)
            for row in snapshot.get("progress", []):
                cursor.execute(
                    """
                    INSERT INTO future_server2.lesson_progress
                    (username,space,progress_key,path,identity,file_id,node_index,node_count,learned_count,complete,server_revision,updated_at_utc,updated_epoch,record_json,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                    """,
                    row,
                )
            for row in snapshot.get("drawings", []):
                cursor.execute(
                    """
                    INSERT INTO future_server2.pdf_drawings
                    (username,document_key,page,progress_key,path,identity,title,mode,drawing_json,content_hash,last_operation_id,deleted,server_revision,updated_at_utc,updated_epoch,updated_by,file_id,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
            profile = json.dumps({"full_name": f"Codex PG PDF {index:03d}", "load_test": True}, separators=(",", ":"))
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


def load_pdf_lessons(limit: int = 100) -> list[dict]:
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        rows = connection.execute(
            """
            SELECT a.normalized_path,a.file_id
            FROM lesson_file_aliases a
            JOIN lesson_files f ON f.file_id=a.file_id
            WHERE a.active=1 AND f.status='active'
              AND lower(a.file_id) LIKE 'ftg-lesson-%'
              AND f.space_id IN ('Space_PDF','Space_Picture')
            ORDER BY a.normalized_path
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        connection.close()
    if len(rows) < limit:
        raise RuntimeError(f"Need {limit} canonical PDF/Picture aliases, found {len(rows)}")
    return [{"path": row[0], "lesson_id": row[1]} for row in rows]


def login(username: str, password: str) -> str:
    response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if (payload.get("server_data") or {}).get("load_test") is not True:
        raise RuntimeError(f"{username} did not login as isolated test user")
    return str(payload.get("token") or "")


def vector(offset: int, count: int = 1) -> dict:
    return {
        "version": 2,
        "width": 10000,
        "height": 10000,
        "items": [
            {"kind": "pen", "color": "#123456", "width": 12, "points": [{"x": offset + i * 50, "y": 100}, {"x": offset + i * 50 + 20, "y": 200}]}
            for i in range(count)
        ],
    }


def post_progress(token: str, lesson: dict, page: int, stamp: datetime, *, pins: list[int] | None = None) -> tuple[float, int, dict]:
    timestamp = stamp.isoformat().replace("+00:00", "Z")
    payload = {
        "path": lesson["path"],
        "identity": lesson["lesson_id"],
        "lesson_id": lesson["lesson_id"],
        "title": "Codex PG PDF progress",
        "page": page,
        "pages": 20,
        "savedAt": timestamp,
        "updatedAt": timestamp,
        "pinnedPages": pins if pins is not None else [page],
        "pinnedPagesUpdatedAt": timestamp,
        "recentPages": [page],
    }
    started = time.perf_counter()
    response = requests.post(f"{BASE}/space-pdf/progress?client_source=codex_pg_pdf", headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=45)
    latency = (time.perf_counter() - started) * 1000
    if response.status_code >= 400:
        raise RuntimeError(f"PDF progress POST failed status={response.status_code} body={response.text[:1000]}")
    return latency, response.status_code, response.json()


def get_progress(token: str, lesson: dict) -> dict:
    response = requests.get(
        f"{BASE}/space-pdf/progress",
        headers={"Authorization": f"Bearer {token}"},
        params={"path": lesson["path"], "identity": lesson["lesson_id"], "lesson_id": lesson["lesson_id"]},
        timeout=45,
    )
    response.raise_for_status()
    return response.json().get("progress") or {}


def post_drawing(token: str, lesson: dict, page: int, operation_id: str, stamp: datetime, *, action: str = "", base_revision: int | None = None, item_count: int = 1) -> tuple[float, int, dict]:
    timestamp = stamp.isoformat().replace("+00:00", "Z")
    payload = {
        "path": lesson["path"],
        "identity": lesson["lesson_id"],
        "lesson_id": lesson["lesson_id"],
        "title": "Codex PG PDF drawing",
        "mode": "pdf",
        "page": page,
        "operationId": operation_id,
        "clientUpdatedAt": timestamp,
    }
    if action:
        payload["action"] = action
    else:
        payload["vector"] = vector(page * 100, item_count)
    if base_revision is not None:
        payload["baseRevision"] = base_revision
    started = time.perf_counter()
    response = requests.post(f"{BASE}/space-pdf/drawing", headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=45)
    latency = (time.perf_counter() - started) * 1000
    if response.status_code >= 400:
        raise RuntimeError(f"PDF drawing POST failed status={response.status_code} body={response.text[:1000]}")
    return latency, response.status_code, response.json()["drawing"]


def get_drawing(token: str, lesson: dict, page: int) -> dict:
    response = requests.get(
        f"{BASE}/space-pdf/drawing",
        headers={"Authorization": f"Bearer {token}"},
        params={"path": lesson["path"], "identity": lesson["lesson_id"], "lesson_id": lesson["lesson_id"], "page": page},
        timeout=45,
    )
    response.raise_for_status()
    return response.json()["drawing"]


def stable_progress_state(payload: dict) -> dict:
    state = dict(payload.get("state") or {})
    return {
        "key": payload.get("key"),
        "username": payload.get("username"),
        "path": payload.get("path"),
        "identity": payload.get("identity"),
        "lesson_id": payload.get("lesson_id"),
        "page": int(payload.get("page", 0) or 0),
        "pages": int(payload.get("pages", 0) or 0),
        "currentNode": int(payload.get("currentNode", 0) or 0),
        "nodeIndex": int(payload.get("nodeIndex", 0) or 0),
        "nodeIndexBase": int(payload.get("nodeIndexBase", 0) or 0),
        "nodeCount": int(payload.get("nodeCount", 0) or 0),
        "pinnedPages": payload.get("pinnedPages") or state.get("pinnedPages") or [],
        "recentPages": payload.get("recentPages") or state.get("recentPages") or [],
        "pinnedPagesUpdatedAt": payload.get("pinnedPagesUpdatedAt") or state.get("pinnedPagesUpdatedAt"),
        "savedAt": payload.get("savedAt"),
        "updatedAt": payload.get("updatedAt"),
        "_serverRevision": int(payload.get("_serverRevision", 0) or 0),
    }


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


def concurrency_phase(name: str, users: tuple[str, ...], tokens: dict[str, str], lessons: list[dict], *, drawing: bool, same_key: bool = False) -> dict:
    before = pg_stat()
    process = psutil.Process(server_pid_on_port(18877))
    cpu_before = sum(process.cpu_times()[:2])
    base = datetime(2026, 7, 25, 3, 0, 0, tzinfo=timezone.utc)

    def one(index_username: tuple[int, str]) -> tuple[float, int, bool]:
        index, username = index_username
        lesson = lessons[0 if same_key else (index - 1) % len(lessons)]
        page = 9 if same_key else (index % 20) + 1
        stamp = base + timedelta(seconds=index)
        if drawing:
            latency, status, payload = post_drawing(tokens[username], lesson, page, f"{name}-{index}", stamp, base_revision=0 if not same_key else None)
            mismatch = int(payload.get("page", 0) or 0) != page
        else:
            latency, status, payload = post_progress(tokens[username], lesson, page, stamp)
            progress = payload.get("progress") or {}
            mismatch = int(progress.get("page", 0) or 0) != page
        return latency, status, mismatch

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


def assert_no_test_rows() -> dict:
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        sqlite_progress = int(connection.execute("SELECT count(*) FROM lesson_progress WHERE lower(username) LIKE 'codexpgpdf%'").fetchone()[0] or 0)
        sqlite_drawings = int(connection.execute("SELECT count(*) FROM pdf_drawings WHERE lower(username) LIKE 'codexpgpdf%'").fetchone()[0] or 0)
        sqlite_users = int(connection.execute("SELECT count(*) FROM users WHERE lower(username) LIKE 'codexpgpdf%'").fetchone()[0] or 0)
    finally:
        connection.close()

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM future_server2.lesson_progress WHERE lower(username) LIKE 'codexpgpdf%'")
            pg_progress = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT count(*) FROM future_server2.pdf_drawings WHERE lower(username) LIKE 'codexpgpdf%'")
            pg_drawings = int(cursor.fetchone()[0] or 0)
        return {"postgres_progress": pg_progress, "postgres_drawings": pg_drawings}

    return {"sqlite_progress": sqlite_progress, "sqlite_drawings": sqlite_drawings, "sqlite_users": sqlite_users, **app.postgres_execute(_read)}


def main() -> int:
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("FUTURE_PG_DSN is required")
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this gate only")
    if server_pid_on_port(18877):
        raise RuntimeError("Port 18877 already has a listener")
    pre_drawings = pdf_drawings_parity()
    pre_progress = lesson_progress_parity()
    if not pre_drawings.get("ok") or not pre_progress.get("ok"):
        raise RuntimeError(f"Pre-test parity failed drawings={pre_drawings} progress={pre_progress}")

    original_pid_file = app.SERVER_PID_FILE.read_text(encoding="utf-8") if app.SERVER_PID_FILE.is_file() else None
    sqlite_before = snapshot_sqlite()
    postgres_before = snapshot_postgres()
    process: subprocess.Popen | None = None
    result: dict = {}
    try:
        provision_users(password)
        process = start_test_server()
        wait_health(pid=int(process.pid))
        lessons = load_pdf_lessons(100)
        tokens = {username: login(username, password) for username in USERS}
        base = datetime(2026, 7, 25, 2, 0, 0, tzinfo=timezone.utc)

        progress_missing = get_progress(tokens[USERS[0]], lessons[0])
        progress_first = post_progress(tokens[USERS[0]], lessons[0], 2, base)[2]
        progress_retry = post_progress(tokens[USERS[0]], lessons[0], 2, base)[2]
        progress_newer = post_progress(tokens[USERS[0]], lessons[0], 5, base + timedelta(seconds=5), pins=[2, 5])[2]
        progress_stale = post_progress(tokens[USERS[0]], lessons[0], 1, base - timedelta(days=1), pins=[1])[2]
        progress_after_stale = get_progress(tokens[USERS[0]], lessons[0])
        if int(progress_after_stale.get("page", 0) or 0) != 5:
            raise RuntimeError("Stale PDF progress regressed current page")

        drawing_missing = get_drawing(tokens[USERS[0]], lessons[0], 7)
        draw_first = post_drawing(tokens[USERS[0]], lessons[0], 7, "codex-pg-pdf-draw-first", base, base_revision=0)[2]
        draw_retry = post_drawing(tokens[USERS[0]], lessons[0], 7, "codex-pg-pdf-draw-first", base, base_revision=0)[2]
        draw_stale = post_drawing(tokens[USERS[0]], lessons[0], 7, "codex-pg-pdf-draw-stale", base - timedelta(days=1))[2]
        draw_newer = post_drawing(tokens[USERS[0]], lessons[0], 7, "codex-pg-pdf-draw-newer", base + timedelta(seconds=2), base_revision=draw_first.get("serverRevision", 1), item_count=2)[2]
        draw_clear = post_drawing(tokens[USERS[0]], lessons[0], 7, "codex-pg-pdf-draw-clear", base + timedelta(seconds=3), action="clear", base_revision=draw_newer.get("serverRevision", 1))[2]
        draw_after_clear = get_drawing(tokens[USERS[0]], lessons[0], 7)
        invalid = requests.post(f"{BASE}/space-pdf/drawing", headers={"Authorization": f"Bearer {tokens[USERS[0]]}"}, json={"page": 1, "vector": vector(1)}, timeout=30)
        cross = requests.get(f"{BASE}/space-pdf/drawing", headers={"Authorization": f"Bearer {tokens[USERS[1]]}"}, params={"path": lessons[0]["path"], "identity": lessons[0]["lesson_id"], "page": 7, "user": USERS[0]}, timeout=30)

        if draw_retry.get("serverRevision") != draw_first.get("serverRevision") or not draw_stale.get("stale") or not draw_clear.get("deleted") or not draw_after_clear.get("deleted"):
            raise RuntimeError(json.dumps({
                "reason": "PDF drawing retry/stale/tombstone semantics failed",
                "draw_first": draw_first,
                "draw_retry": draw_retry,
                "draw_stale": draw_stale,
                "draw_newer": draw_newer,
                "draw_clear": draw_clear,
                "draw_after_clear": draw_after_clear,
            }, ensure_ascii=True, default=str))
        if invalid.status_code < 400 or cross.status_code != 403:
            raise RuntimeError(f"PDF drawing validation/auth failed invalid={invalid.status_code} cross={cross.status_code}")

        phases = [
            concurrency_phase("progress_distinct_10", USERS[:10], tokens, lessons, drawing=False),
            concurrency_phase("progress_distinct_50", USERS[:50], tokens, lessons, drawing=False),
            concurrency_phase("progress_distinct_100", USERS, tokens, lessons, drawing=False),
            concurrency_phase("drawing_distinct_10", USERS[:10], tokens, lessons, drawing=True),
            concurrency_phase("drawing_distinct_50", USERS[:50], tokens, lessons, drawing=True),
            concurrency_phase("drawing_distinct_100", USERS, tokens, lessons, drawing=True),
            concurrency_phase("drawing_same_key_10", USERS[:10], tokens, lessons, drawing=True, same_key=True),
            concurrency_phase("drawing_same_key_50", USERS[:50], tokens, lessons, drawing=True, same_key=True),
            concurrency_phase("drawing_same_key_100", USERS, tokens, lessons, drawing=True, same_key=True),
        ]
        if any(phase["mismatched_response"] or phase["deadlock"] or phase["serialization_conflict"] for phase in phases):
            raise RuntimeError(f"Concurrency phase failed: {phases}")

        before_restart_progress = get_progress(tokens[USERS[0]], lessons[0])
        before_restart_drawing = get_drawing(tokens[USERS[0]], lessons[0], 7)
        stop_pid(int(process.pid))
        process = start_test_server()
        wait_health(pid=int(process.pid))
        token_after_restart = login(USERS[0], password)
        restart_progress = get_progress(token_after_restart, lessons[0])
        restart_drawing = get_drawing(token_after_restart, lessons[0], 7)
        if stable_progress_state(restart_progress) != stable_progress_state(before_restart_progress) or restart_drawing != before_restart_drawing:
            raise RuntimeError(json.dumps({
                "reason": "PDF progress/drawing restart readback changed state",
                "before_restart_progress": stable_progress_state(before_restart_progress),
                "restart_progress": stable_progress_state(restart_progress),
                "before_restart_drawing": before_restart_drawing,
                "restart_drawing": restart_drawing,
            }, ensure_ascii=True, default=str))

        final_drawings = pdf_drawings_parity()
        final_progress = lesson_progress_parity()
        result = {
            "pdf_progress_drawings_postgres_http_gate": "ok",
            "feature_flags": ["FUTURE_DB_LESSON_PROGRESS_BACKEND", "FUTURE_DB_PDF_DRAWINGS_BACKEND"],
            "pre_drawings": pre_drawings,
            "pre_progress_shadow": pre_progress,
            "single": {
                "progress_missing": progress_missing,
                "progress_retry_same_page": (progress_retry.get("progress") or {}).get("page") == (progress_first.get("progress") or {}).get("page"),
                "progress_stale_rejected": int(progress_after_stale.get("page", 0) or 0) == 5,
                "drawing_missing": drawing_missing,
                "drawing_retry_revision": draw_retry.get("serverRevision"),
                "drawing_stale": bool(draw_stale.get("stale")),
                "drawing_deleted": bool(draw_after_clear.get("deleted")),
                "invalid_status": invalid.status_code,
                "cross_user_status": cross.status_code,
            },
            "concurrency": phases,
            "restart": {
                "progress_stable": stable_progress_state(restart_progress) == stable_progress_state(before_restart_progress),
                "drawing_stable": restart_drawing == before_restart_drawing,
            },
            "shadow_read": {"pdf_drawings": final_drawings, "lesson_progress": final_progress},
            "production_health": health(PRODUCTION_BASE, 10),
            "production_flags": {
                "FUTURE_DB_LESSON_PROGRESS_BACKEND": os.environ.get("FUTURE_DB_LESSON_PROGRESS_BACKEND", "off") or "off",
                "FUTURE_DB_PDF_DRAWINGS_BACKEND": os.environ.get("FUTURE_DB_PDF_DRAWINGS_BACKEND", "off") or "off",
            },
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
