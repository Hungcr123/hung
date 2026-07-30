#!/usr/bin/env python3
"""HTTP runtime gate for chat SQLite vs PostgreSQL backends."""

from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
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
USERS = tuple(f"codexpgchat{index:03d}" for index in range(1, 101))


def password_hash(value: str) -> str:
    salt = secrets.token_urlsafe(18)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode(), salt.encode(), 2)
    return "pbkdf2_sha256$2$%s$%s" % (salt, base64.urlsafe_b64encode(digest).decode().rstrip("="))


def password_hash_matches(value: str, encoded: str) -> bool:
    parts = str(encoded or "").split("$")
    if len(parts) != 4:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", value.encode(), parts[2].encode(), int(parts[1]))
    return hmac.compare_digest(base64.urlsafe_b64encode(digest).decode().rstrip("="), parts[3])


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
        pass


def wait_health(timeout: float = 90.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            response = requests.get(f"{BASE}/health", timeout=3)
            if response.status_code == 200 and response.json().get("ok"):
                return response.json()
        except Exception:
            pass
        time.sleep(0.35)
    raise RuntimeError("test server did not become healthy")


def start_server(backend: str) -> subprocess.Popen:
    env = dict(os.environ)
    if backend == "postgres":
        env["FUTURE_DB_CHAT_BACKEND"] = "postgres"
    else:
        env.pop("FUTURE_DB_CHAT_BACKEND", None)
    return subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--host", "127.0.0.1", "--port", "18877", "--no-browser", "--no-tunnel"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def cleanup_sqlite() -> dict:
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        con.execute("BEGIN IMMEDIATE")
        out = {}
        for table in ("chat_read_state", "chat_messages", "auth_sessions", "server_load_test_credentials", "users"):
            cur = con.execute(f"DELETE FROM {table} WHERE lower(username) LIKE 'codexpgchat%'")
            out[table] = int(cur.rowcount or 0)
        con.commit()
        return out
    finally:
        con.close()


def cleanup_postgres() -> dict:
    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.chat_read_state WHERE lower(username) LIKE 'codexpgchat%'")
            read_state = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.chat_messages WHERE lower(username) LIKE 'codexpgchat%' OR id>=920000000")
            messages = int(cursor.rowcount or 0)
        return {"chat_messages": messages, "chat_read_state": read_state}

    return app.postgres_execute(_write)


def provision_users(password: str) -> None:
    now = app.utc_timestamp()
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        con.execute("BEGIN IMMEDIATE")
        for username in USERS:
            con.execute(
                "INSERT INTO users(username,is_admin,is_test,profile_json,updated_at_utc) VALUES(?,0,1,'{}',?) "
                "ON CONFLICT(username) DO UPDATE SET is_test=1,updated_at_utc=excluded.updated_at_utc",
                (username, now),
            )
            existing = con.execute("SELECT password_hash FROM server_load_test_credentials WHERE username=?", (username,)).fetchone()
            encoded = existing[0] if existing and password_hash_matches(password, existing[0]) else password_hash(password)
            con.execute(
                "INSERT INTO server_load_test_credentials(username,password_hash,updated_at_utc) VALUES(?,?,?) "
                "ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash,updated_at_utc=excluded.updated_at_utc",
                (username, encoded, now),
            )
        con.commit()
    finally:
        con.close()


def login(username: str, password: str) -> requests.Session:
    session = requests.Session()
    response = session.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
    response.raise_for_status()
    token = response.json().get("token", "")
    session.headers.update({"Authorization": "Bearer " + token})
    return session


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(len(ordered) * pct / 100.0))], 3)


def post_user_message(session: requests.Session, text: str, operation_id: str) -> tuple[int, dict, float]:
    started = time.perf_counter()
    response = session.post(
        f"{BASE}/chat/send",
        json={"text": text, "language": "en", "audio_enabled": False, "operation_id": operation_id},
        timeout=60,
    )
    elapsed = (time.perf_counter() - started) * 1000
    try:
        body = response.json()
    except Exception:
        body = {"raw": response.text[:200]}
    return response.status_code, body, elapsed


def post_admin_message(username: str, text: str, operation_id: str) -> tuple[int, dict, float]:
    started = time.perf_counter()
    response = requests.post(
        f"{BASE}/chat/admin/send",
        json={"username": username, "text": text, "audio_enabled": False, "operation_id": operation_id},
        timeout=60,
    )
    elapsed = (time.perf_counter() - started) * 1000
    try:
        body = response.json()
    except Exception:
        body = {"raw": response.text[:200]}
    return response.status_code, body, elapsed


def poll(session: requests.Session, mark_read: bool = False) -> tuple[int, dict]:
    response = session.get(
        f"{BASE}/chat/poll",
        params={"since": "0", "open": "1" if mark_read else "0", "notice_after": "2147483647"},
        timeout=60,
    )
    try:
        body = response.json()
    except Exception:
        body = {"raw": response.text[:200]}
    return response.status_code, body


def backend_counts(backend: str, username: str) -> dict:
    if backend == "sqlite":
        con = sqlite3.connect(DATABASE)
        try:
            messages = con.execute("SELECT COUNT(*) FROM chat_messages WHERE username=?", (username,)).fetchone()[0]
            read = con.execute("SELECT admin_read,user_read FROM chat_read_state WHERE username=?", (username,)).fetchone()
            return {
                "messages": int(messages or 0),
                "admin_read": int(read[0] or 0) if read else 0,
                "user_read": int(read[1] or 0) if read else 0,
            }
        finally:
            con.close()

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM future_server2.chat_messages WHERE username=%s", (username,))
            messages = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT admin_read,user_read FROM future_server2.chat_read_state WHERE username=%s", (username,))
            read = cursor.fetchone()
        return {
            "messages": messages,
            "admin_read": int(read[0] or 0) if read else 0,
            "user_read": int(read[1] or 0) if read else 0,
        }

    return app.postgres_execute(_read)


def backend_operation_rows(backend: str, username: str, operation_id: str) -> int:
    if backend == "sqlite":
        con = sqlite3.connect(DATABASE)
        try:
            return int(con.execute(
                "SELECT COUNT(*) FROM chat_messages WHERE username=? AND operation_id=?",
                (username, operation_id),
            ).fetchone()[0] or 0)
        finally:
            con.close()

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM future_server2.chat_messages WHERE username=%s AND operation_id=%s",
                (username, operation_id),
            )
            return int(cursor.fetchone()[0] or 0)

    return app.postgres_execute(_read)


def phase(name: str, backend: str, users: tuple[str, ...], sessions: dict[str, requests.Session], same_operation: bool = False) -> dict:
    latencies = []
    errors = 0
    mismatches = 0
    duplicates = 0
    sample_errors = []
    started = time.perf_counter()

    def one(pair):
        index, username = pair
        operation = f"codex-chat-{name}-same" if same_operation else f"codex-chat-{name}-{index:03d}"
        return username, operation, post_user_message(sessions[username], f"{name} hello {index}", operation)

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, len(users))) as executor:
        rows = list(executor.map(one, enumerate(users, 1)))
    for username, operation, (status, body, elapsed) in rows:
        latencies.append(elapsed)
        errors += 0 if status == 200 else 1
        if status != 200 and len(sample_errors) < 3:
            sample_errors.append({"status": status, "body": body})
        message = body.get("message") if isinstance(body.get("message"), dict) else {}
        if int(message.get("id", 0) or 0) <= 0:
            mismatches += 1
        if same_operation and backend_operation_rows(backend, username, operation) != 1:
            mismatches += 1
        if bool(body.get("duplicate")):
            duplicates += 1
    wall = (time.perf_counter() - started) * 1000
    return {
        "name": name,
        "requests": len(users),
        "status_200": len(users) - errors,
        "errors": errors,
        "mismatches": mismatches,
        "duplicates": duplicates,
        "wall_ms": round(wall, 3),
        "p50_ms": percentile(latencies, 50),
        "p95_ms": percentile(latencies, 95),
        "p99_ms": percentile(latencies, 99),
        "throughput_rps": round((len(users) / wall) * 1000, 3) if wall else 0,
        "sample_errors": sample_errors,
    }


def run_backend(backend: str, password: str) -> dict:
    process = None
    try:
        process = start_server(backend)
        health_before = wait_health()
        sessions = {username: login(username, password) for username in USERS}
        single_user = USERS[0]
        single = sessions[single_user]

        status, body, _elapsed = post_user_message(single, f"{backend} single user", f"codex-chat-{backend}-single")
        if status != 200:
            raise RuntimeError(f"{backend} single send failed: {status} {body}")
        first_id = int((body.get("message") or {}).get("id", 0) or 0)
        retry_status, retry_body, _ = post_user_message(single, f"{backend} single user", f"codex-chat-{backend}-single")
        retry_id = int((retry_body.get("message") or {}).get("id", 0) or 0)
        if retry_status != 200 or retry_id != first_id or backend_operation_rows(backend, single_user, f"codex-chat-{backend}-single") != 1:
            raise RuntimeError(f"{backend} exact retry was not idempotent")

        admin_status, admin_body, _ = post_admin_message(single_user, f"{backend} admin reply", f"codex-chat-{backend}-admin")
        if admin_status != 200 or int(((admin_body.get("message") or {}).get("id", 0) or 0)) <= 0:
            raise RuntimeError(f"{backend} admin send failed: {admin_status} {admin_body}")
        poll_status, poll_body = poll(single, mark_read=True)
        if poll_status != 200 or len(poll_body.get("messages", [])) < 2:
            raise RuntimeError(f"{backend} poll/readback failed: {poll_status} {poll_body}")
        read_counts = backend_counts(backend, single_user)
        if read_counts["messages"] < 2 or read_counts["user_read"] <= 0:
            raise RuntimeError(f"{backend} read marker was not persisted: {read_counts}")

        invalid_status, invalid_body, _ = post_user_message(single, "", f"codex-chat-{backend}-invalid")
        invalid_ok = invalid_status == 400 and backend_operation_rows(backend, single_user, f"codex-chat-{backend}-invalid") == 0
        if not invalid_ok:
            raise RuntimeError(f"{backend} invalid payload did not rollback: {invalid_status} {invalid_body}")

        distinct10 = phase(f"{backend}-distinct10", backend, USERS[:10], sessions)
        distinct50 = phase(f"{backend}-distinct50", backend, USERS[:50], sessions)
        distinct100 = phase(f"{backend}-distinct100", backend, USERS, sessions)
        same_user_sessions = {single_user: single}
        same10 = phase(f"{backend}-same10", backend, (single_user,) * 10, same_user_sessions, same_operation=True)
        same50 = phase(f"{backend}-same50", backend, (single_user,) * 50, same_user_sessions, same_operation=True)
        same100 = phase(f"{backend}-same100", backend, (single_user,) * 100, same_user_sessions, same_operation=True)

        health_after = requests.get(f"{BASE}/health", timeout=5).json()
        return {
            "backend": backend,
            "health_before": {
                "pid": health_before.get("pid"),
                "postgres": health_before.get("postgres") or health_before.get("postgresql"),
                "writer_queue": health_before.get("writer_queue"),
            },
            "health_after": {
                "pid": health_after.get("pid"),
                "postgres": health_after.get("postgres") or health_after.get("postgresql"),
                "writer_queue": health_after.get("writer_queue"),
            },
            "single": {"message_id": first_id, "retry_id": retry_id, "admin_message_id": int((admin_body.get("message") or {}).get("id", 0) or 0), "read": read_counts},
            "invalid_rollback": invalid_ok,
            "phases": [distinct10, distinct50, distinct100, same10, same50, same100],
        }
    finally:
        if process is not None:
            stop_pid(process.pid)


def restart_readback(password: str) -> dict:
    process = start_server("postgres")
    try:
        first = wait_health()
        username = USERS[0]
        session = login(username, password)
        status, body = poll(session, mark_read=False)
        if status != 200 or len(body.get("messages", [])) < 2:
            raise RuntimeError(f"postgres restart readback failed: {status} {body}")
        retry_status, retry_body, _ = post_user_message(session, "postgres single user", "codex-chat-postgres-single")
        retry_id = int((retry_body.get("message") or {}).get("id", 0) or 0)
        if retry_status != 200 or backend_operation_rows("postgres", username, "codex-chat-postgres-single") != 1:
            raise RuntimeError("postgres post-restart retry was not idempotent")
        return {"pid": first.get("pid"), "poll_messages": len(body.get("messages", [])), "retry_id": retry_id}
    finally:
        stop_pid(process.pid)


def assert_phase_ok(result: dict) -> None:
    for phase_result in result.get("phases", []):
        if phase_result["errors"] or phase_result["mismatches"]:
            raise RuntimeError(f"{result['backend']} phase failed: {phase_result}")


def main() -> int:
    if server_pid_on_port(18877):
        raise RuntimeError("test port 18877 is already in use")
    password = "codex-" + secrets.token_urlsafe(18)
    os.environ["FUTURE_TEST_PASSWORD"] = password
    cleanup = {"sqlite_before": cleanup_sqlite(), "postgres_before": cleanup_postgres()}
    try:
        app.postgres_initialize_schema()
        provision_users(password)
        sqlite_result = run_backend("sqlite", password)
        assert_phase_ok(sqlite_result)
        postgres_result = run_backend("postgres", password)
        assert_phase_ok(postgres_result)
        readback = restart_readback(password)
        cleanup["sqlite_after"] = cleanup_sqlite()
        cleanup["postgres_after"] = cleanup_postgres()
        verify = subprocess.run(
            [sys.executable, str(ROOT / "FUTURE" / "tools" / "migrate_chat_to_postgres.py"), "--verify-only"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=120,
        )
        result = {
            "ok": True,
            "sqlite": sqlite_result,
            "postgres": postgres_result,
            "restart_readback": readback,
            "cleanup": cleanup,
            "verify_only_exit": verify.returncode,
            "verify_only": json.loads(verify.stdout or "{}") if verify.stdout.strip().startswith("{") else verify.stdout[-500:],
            "test_port_busy": bool(server_pid_on_port(18877)),
            "production_flag": os.environ.get("FUTURE_DB_CHAT_BACKEND", "off"),
        }
        if verify.returncode != 0:
            raise RuntimeError(f"post-cleanup verify-only failed: {verify.stdout[-800:]} {verify.stderr[-400:]}")
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    finally:
        stop_pid(server_pid_on_port(18877))
        cleanup_sqlite()
        cleanup_postgres()
        os.environ.pop("FUTURE_TEST_PASSWORD", None)


if __name__ == "__main__":
    raise SystemExit(main())
