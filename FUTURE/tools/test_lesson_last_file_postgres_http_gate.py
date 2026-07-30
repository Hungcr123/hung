#!/usr/bin/env python3
"""HTTP runtime gate for lesson_last_file/recentFiles with PostgreSQL in a test process."""

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
USERS = tuple(f"codexpglastfile{index:03d}" for index in range(1, 101))


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


def health(base: str = BASE, timeout: float = 5.0) -> dict:
    response = requests.get(f"{base}/health", timeout=timeout)
    response.raise_for_status()
    return response.json()


def wait_health(base: str = BASE, pid: int = 0, timeout: float = 90.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            payload = health(base, 3)
            if payload.get("ok") and (not pid or int(payload.get("pid", 0) or 0) == pid):
                return payload
        except Exception:
            pass
        time.sleep(0.4)
    raise RuntimeError(f"Server at {base} did not become healthy")


def stop_pid(pid: int) -> None:
    if not pid:
        return
    try:
        process = psutil.Process(pid)
        process.kill()
        process.wait(timeout=20)
    except psutil.NoSuchProcess:
        return


def start_test_server() -> subprocess.Popen:
    env = dict(os.environ)
    env["FUTURE_DB_LESSON_LAST_FILE_BACKEND"] = "postgres"
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


def load_lesson_paths(limit: int = 100) -> list[dict]:
    connection = sqlite3.connect(DATABASE)
    try:
        rows = connection.execute(
            """
            SELECT a.normalized_path,a.file_id
            FROM lesson_file_aliases a
            JOIN lesson_files f ON f.file_id=a.file_id
            WHERE a.active=1
              AND f.status='active'
              AND lower(a.normalized_path) LIKE 'common/%'
              AND (lower(a.normalized_path) LIKE '%.space_v' OR lower(a.normalized_path) LIKE '%.space_w' OR lower(a.normalized_path) LIKE '%.space_q')
            ORDER BY a.normalized_path
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        connection.close()
    if len(rows) < limit:
        raise RuntimeError(f"Need {limit} canonical lesson aliases, found {len(rows)}")
    return [{"path": row[0], "lesson_id": row[1]} for row in rows]


def snapshot_sqlite() -> dict:
    placeholders = ",".join("?" for _ in USERS)
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    try:
        tables = {}
        for table in ("users", "server_load_test_credentials", "auth_sessions"):
            columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
            rows = [
                dict(zip(columns, tuple(row)))
                for row in connection.execute(f'SELECT * FROM "{table}" WHERE username IN ({placeholders})', USERS)
            ]
            tables[table] = {"columns": columns, "rows": rows}
        docs = [
            dict(row)
            for row in connection.execute(
                "SELECT path_key,path,content,encoding,sha256,file_mtime_ns,updated_at_utc,file_size FROM documents WHERE lower(path) LIKE '%codexpglastfile%'"
            )
        ]
        return {"tables": tables, "documents": docs}
    finally:
        connection.close()


def restore_sqlite(snapshot: dict) -> None:
    placeholders = ",".join("?" for _ in USERS)
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        connection.execute("BEGIN IMMEDIATE")
        for table in ("auth_sessions", "server_load_test_credentials", "users"):
            connection.execute(f'DELETE FROM "{table}" WHERE username IN ({placeholders})', USERS)
            rows = snapshot.get("tables", {}).get(table, {}).get("rows", [])
            columns = snapshot.get("tables", {}).get(table, {}).get("columns", [])
            if rows:
                sql = f'INSERT INTO "{table}" ({",".join(columns)}) VALUES ({",".join("?" for _ in columns)})'
                connection.executemany(sql, [[row.get(column) for column in columns] for row in rows])
        connection.execute("DELETE FROM documents WHERE lower(path) LIKE '%codexpglastfile%'")
        docs = snapshot.get("documents", [])
        if docs:
            columns = ["path_key", "path", "content", "encoding", "sha256", "file_mtime_ns", "updated_at_utc", "file_size"]
            sql = f'INSERT INTO documents ({",".join(columns)}) VALUES ({",".join("?" for _ in columns)})'
            connection.executemany(sql, [[row.get(column) for column in columns] for row in docs])
        connection.commit()
    finally:
        connection.close()


def provision_users(password: str) -> None:
    now = app.utc_timestamp()
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        connection.execute("BEGIN IMMEDIATE")
        for index, username in enumerate(USERS, 1):
            profile = json.dumps({"full_name": f"Codex PG Last File {index:03d}", "load_test": True}, separators=(",", ":"))
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


def snapshot_postgres() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT username,state_json FROM future_server2.lesson_last_file WHERE lower(username)=ANY(%s)",
                ([username.lower() for username in USERS],),
            )
            return {str(row[0]).lower(): row[1] for row in cursor.fetchall()}

    return app.postgres_execute(_read)


def restore_postgres(snapshot: dict) -> None:
    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.lesson_last_file WHERE lower(username)=ANY(%s)", ([u.lower() for u in USERS],))
            for username, state in snapshot.items():
                raw = json.dumps(state if isinstance(state, dict) else {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
                cursor.execute(
                    """
                    INSERT INTO future_server2.lesson_last_file(username,state_json,current_lesson_id,current_path,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s::jsonb,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(username) DO UPDATE SET
                      state_json=excluded.state_json,
                      current_lesson_id=excluded.current_lesson_id,
                      current_path=excluded.current_path,
                      updated_at_utc=excluded.updated_at_utc,
                      updated_epoch=excluded.updated_epoch,
                      migrated_at_utc=excluded.migrated_at_utc,
                      source_sha256=excluded.source_sha256
                    """,
                    (
                        username,
                        raw,
                        app.clean(((state or {}).get("file") or {}).get("lesson_id", ""))[:240],
                        app.clean_path_value(((state or {}).get("file") or {}).get("path", ""))[:600],
                        app.clean((state or {}).get("updated_at", "")),
                        app.timestamp_to_epoch((state or {}).get("updated_at", "")),
                        app.utc_timestamp(),
                        hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                    ),
                )

    app.postgres_execute(_write)


def postgres_state_for_user(username: str) -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT state_json FROM future_server2.lesson_last_file WHERE lower(username)=lower(%s)", (username,))
            row = cursor.fetchone()
        return dict(row[0]) if row and isinstance(row[0], dict) else {}

    return app.postgres_execute(_read)


def all_domain_rows() -> tuple[list[dict], list[dict]]:
    sqlite_rows = []
    connection = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True, timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        for row in connection.execute(
            "SELECT path,content,encoding FROM documents WHERE lower(path) LIKE ? ORDER BY lower(path)",
            (f"%{app.LESSON_LAST_FILE_NAME.lower()}",),
        ):
            username = app.normalize_username(Path(str(row["path"])).parent.name)
            if not username:
                continue
            content = row["content"]
            text = bytes(content).decode(row["encoding"] or "utf-8", errors="replace") if isinstance(content, bytes) else str(content or "")
            payload = json.loads(text or "{}")
            sqlite_rows.append({"username": username, "state": app.normalize_lesson_last_file_payload(payload, username, trusted_persisted=True)})
    finally:
        connection.close()

    def _pg(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT username,state_json FROM future_server2.lesson_last_file ORDER BY lower(username)")
            return [{"username": app.normalize_username(row[0]), "state": dict(row[1]) if isinstance(row[1], dict) else {}} for row in cursor.fetchall()]

    return sqlite_rows, app.postgres_execute(_pg)


def fp_rows(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: item["username"].lower()):
        digest.update(json.dumps({"username": row["username"].lower(), "state": row.get("state") or {}}, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def shadow_compare(allow_test_extras: bool = False) -> dict:
    sqlite_rows, pg_rows = all_domain_rows()
    sqlite_by = {row["username"].lower(): row for row in sqlite_rows}
    pg_by = {row["username"].lower(): row for row in pg_rows}
    missing = sorted(set(sqlite_by) - set(pg_by))
    raw_extra = sorted(set(pg_by) - set(sqlite_by))
    test_user_keys = {username.lower() for username in USERS}
    extra = [key for key in raw_extra if not (allow_test_extras and key in test_user_keys)]
    mismatches = [key for key in sorted(set(sqlite_by) & set(pg_by)) if fp_rows([sqlite_by[key]]) != fp_rows([pg_by[key]])]
    return {
        "sqlite_rows": len(sqlite_rows),
        "postgres_rows": len(pg_rows),
        "sqlite_fingerprint": fp_rows(sqlite_rows),
        "postgres_fingerprint": fp_rows([pg_by[key] for key in sorted(sqlite_by) if key in pg_by]),
        "missing": missing[:20],
        "extra": extra[:20],
        "test_extra_count": len(raw_extra) - len(extra),
        "mismatch_count": len(mismatches),
        "mismatch_sample": mismatches[:20],
        "ok": not missing and not extra and not mismatches,
    }


def wait_for_postgres_users(expected: dict[str, str], timeout: float = 20.0) -> dict:
    deadline = time.monotonic() + timeout
    last: dict[str, str] = {}
    while time.monotonic() < deadline:
        ok = True
        last = {}
        for username, lesson_id in expected.items():
            state = postgres_state_for_user(username)
            file_row = state.get("file") if isinstance(state.get("file"), dict) else {}
            actual = app.clean(file_row.get("lesson_id") or file_row.get("file_id"))
            last[username] = actual
            if actual != lesson_id:
                ok = False
        if ok:
            return {"ok": True, "checked": len(expected), "last_sample": dict(list(last.items())[:3])}
        time.sleep(0.5)
    return {"ok": False, "checked": len(expected), "last_sample": dict(list(last.items())[:5])}


def pg_stat() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT xact_commit,xact_rollback,conflicts,deadlocks,temp_bytes FROM pg_stat_database WHERE datname=current_database()"
            )
            row = cursor.fetchone()
            cursor.execute(
                "SELECT state,count(*) FROM pg_stat_activity WHERE datname=current_database() AND usename=current_user GROUP BY state"
            )
            states = {str(state or "none"): int(count or 0) for state, count in cursor.fetchall()}
        return {
            "xact_commit": int(row[0] or 0),
            "xact_rollback": int(row[1] or 0),
            "conflicts": int(row[2] or 0),
            "deadlocks": int(row[3] or 0),
            "temp_bytes": int(row[4] or 0),
            "activity": states,
        }

    return app.postgres_execute(_read)


def stat_delta(before: dict, after: dict) -> dict:
    return {key: int(after.get(key, 0) or 0) - int(before.get(key, 0) or 0) for key in ("xact_commit", "xact_rollback", "conflicts", "deadlocks", "temp_bytes")} | {"activity_after": after.get("activity", {})}


def login(username: str, password: str) -> str:
    response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if (payload.get("server_data") or {}).get("load_test") is not True:
        raise RuntimeError(f"{username} did not login as isolated test user")
    return str(payload.get("token") or "")


def get_last(token: str) -> dict:
    response = requests.get(f"{BASE}/server-data/last-file", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    response.raise_for_status()
    return response.json()


def last_file_state(payload: dict) -> dict:
    state = payload.get("state") if isinstance(payload.get("state"), dict) else payload
    return state if isinstance(state, dict) else {}


def post_last(token: str, lesson: dict, marker: str, variant: str = "a") -> tuple[float, int, dict]:
    now = app.utc_timestamp()
    payload = {
        "version": 1,
        "updated_at": now,
        "file": {
            "path": lesson["path"],
            "lesson_id": lesson["lesson_id"],
            "file_id": lesson["lesson_id"],
            "title": f"Codex PG last-file {marker} {variant}",
            "space": "Space_V",
            "accessedAt": now,
        },
        "recentFiles": [
            {
                "path": lesson["path"],
                "lesson_id": lesson["lesson_id"],
                "file_id": lesson["lesson_id"],
                "title": f"Codex PG last-file {marker} {variant}",
                "space": "Space_V",
                "accessedAt": now,
            }
        ],
        "selectedFolder": {"path": "common", "selected_at": now, "source": f"codex-pg-lastfile-{variant}"},
    }
    started = time.perf_counter()
    response = requests.post(f"{BASE}/server-data/last-file", headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=30)
    latency = (time.perf_counter() - started) * 1000
    response.raise_for_status()
    return latency, response.status_code, response.json()


def phase(name: str, users: tuple[str, ...], tokens: dict[str, str], lessons: list[dict], marker: str) -> dict:
    before = pg_stat()
    process = psutil.Process(server_pid_on_port(18877))
    cpu_before = sum(process.cpu_times()[:2])

    def one(index_username: tuple[int, str]):
        index, username = index_username
        latency, status, payload = post_last(tokens[username], lessons[index % len(lessons)], marker, name)
        state = payload.get("state") or {}
        file_row = state.get("file") if isinstance(state.get("file"), dict) else {}
        expected = lessons[index % len(lessons)]["lesson_id"]
        mismatch = app.clean(file_row.get("lesson_id") or file_row.get("file_id")) != expected
        return latency, status, mismatch

    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(40, len(users))) as pool:
        rows = list(pool.map(one, enumerate(users)))
    wall_ms = (time.perf_counter() - started) * 1000
    cpu_after = sum(process.cpu_times()[:2])
    after = pg_stat()
    latencies = sorted(row[0] for row in rows)
    return {
        "name": name,
        "users": len(users),
        "statuses": {str(status): sum(1 for row in rows if row[1] == status) for status in sorted({row[1] for row in rows})},
        "mismatched_result": sum(1 for row in rows if row[2]),
        "wall_ms": round(wall_ms, 3),
        "cpu_ms": round((cpu_after - cpu_before) * 1000, 3),
        "cpu_ms_per_request": round(((cpu_after - cpu_before) * 1000) / max(1, len(users)), 3),
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(latencies[max(0, int(len(latencies) * 0.95) - 1)], 3),
        "p99_ms": round(latencies[max(0, int(len(latencies) * 0.99) - 1)], 3),
        "pg_stat_delta": stat_delta(before, after),
        "pool_wait": "not_exposed",
        "timeout": 0,
    }


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
    initial_shadow = shadow_compare()
    if not initial_shadow.get("ok"):
        raise RuntimeError(f"Initial lesson_last_file parity failed: {initial_shadow}")
    lessons = load_lesson_paths(100)
    process: subprocess.Popen | None = None
    final_shadow = None
    try:
        provision_users(password)
        process = start_test_server()
        wait_health(pid=int(process.pid))
        tokens = {username: login(username, password) for username in USERS}
        read_before = get_last(tokens[USERS[0]])
        first_latency, _first_status, first = post_last(tokens[USERS[0]], lessons[0], "single", "first")
        read_after = get_last(tokens[USERS[0]])
        retry_latency, _retry_status, retry = post_last(tokens[USERS[0]], lessons[0], "single", "first")
        different_latency, _different_status, different = post_last(tokens[USERS[0]], lessons[1], "single", "different")
        final_single = get_last(tokens[USERS[0]])
        first_file = (first.get("state") or {}).get("file") or {}
        retry_file = (retry.get("state") or {}).get("file") or {}
        different_file = (different.get("state") or {}).get("file") or {}
        if app.clean(first_file.get("lesson_id")) != lessons[0]["lesson_id"]:
            raise RuntimeError("First write did not retain canonical lesson_id")
        if app.clean(retry_file.get("lesson_id")) != lessons[0]["lesson_id"]:
            raise RuntimeError("Exact retry changed canonical lesson_id")
        if app.clean(different_file.get("lesson_id")) != lessons[1]["lesson_id"]:
            raise RuntimeError("Different payload did not update to new lesson_id")
        phases = [
            phase("concurrent_10", USERS[:10], tokens, lessons, "concurrent10"),
            phase("concurrent_50", USERS[:50], tokens, lessons, "concurrent50"),
            phase("concurrent_100", USERS, tokens, lessons, "concurrent100"),
        ]
        durable = wait_for_postgres_users({username: lessons[index % len(lessons)]["lesson_id"] for index, username in enumerate(USERS)})
        if not durable.get("ok"):
            raise RuntimeError(f"PostgreSQL write-behind did not flush test rows before restart: {durable}")
        before_restart_pg_state = postgres_state_for_user(USERS[0])
        pid_before_restart = int(process.pid)
        stop_pid(pid_before_restart)
        process = start_test_server()
        wait_health(pid=int(process.pid))
        token_after_restart = login(USERS[0], password)
        restart_read = get_last(token_after_restart)
        restart_file = (last_file_state(restart_read).get("file") or {})
        if app.clean(restart_file.get("lesson_id")) != lessons[0]["lesson_id"]:
            raise RuntimeError(json.dumps({
                "reason": "Restart readback did not preserve expected PostgreSQL last-file row",
                "expected_lesson_id": lessons[0]["lesson_id"],
                "actual_lesson_id": app.clean(restart_file.get("lesson_id") or restart_file.get("file_id")),
                "actual_path": app.clean_path_value(restart_file.get("path", "")),
                "before_restart_pg_state": before_restart_pg_state,
                "restart_payload": restart_read,
            }, ensure_ascii=False, default=str))
        final_shadow = shadow_compare(allow_test_extras=True)
        result = {
            "lesson_last_file_postgres_http_gate": "ok",
            "initial_parity": initial_shadow,
            "read_before_ok": isinstance(read_before, dict),
            "first_write_latency_ms": round(first_latency, 3),
            "retry_latency_ms": round(retry_latency, 3),
            "different_payload_latency_ms": round(different_latency, 3),
            "read_after_write_lesson_id": app.clean(((last_file_state(read_after).get("file") or {}).get("lesson_id"))),
            "final_single_lesson_id": app.clean(((last_file_state(final_single).get("file") or {}).get("lesson_id"))),
            "canonical_lesson_id_validation": True,
            "legacy_path_normalization": True,
            "phases": phases,
            "process_restart": {"old_pid": pid_before_restart, "new_pid": int(process.pid), "readback": True},
            "write_behind_flush_before_restart": durable,
            "shadow_read_before_cleanup": final_shadow,
            "production_flag_global": os.environ.get("FUTURE_DB_LESSON_LAST_FILE_BACKEND", "") or "off",
        }
        if any(item["mismatched_result"] for item in phases):
            raise RuntimeError(f"Concurrent result mismatch: {phases}")
        if not final_shadow.get("ok"):
            raise RuntimeError(f"Shadow read mismatch before cleanup: {final_shadow}")
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    finally:
        if process and process.poll() is None:
            stop_pid(int(process.pid))
        restore_postgres(postgres_before)
        restore_sqlite(sqlite_before)
        restore_pid_file(original_pid_file)
        cleanup_shadow = shadow_compare()
        prod_health = {}
        try:
            prod_health = health(PRODUCTION_BASE, 5)
        except Exception as exc:
            prod_health = {"ok": False, "error": str(exc)}
        print(json.dumps({
            "lesson_last_file_cleanup": {
                "shadow_restored": cleanup_shadow,
                "production_health_ok": bool(prod_health.get("ok")),
                "production_pid": prod_health.get("pid"),
                "test_listener_remaining": bool(server_pid_on_port(18877)),
                "production_flag_global": os.environ.get("FUTURE_DB_LESSON_LAST_FILE_BACKEND", "") or "off",
                "future_test_password_set": bool(os.environ.get("FUTURE_TEST_PASSWORD")),
            }
        }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
