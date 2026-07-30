#!/usr/bin/env python3
"""HTTP runtime gate for users/auth_sessions PostgreSQL process backend."""

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
USERS = tuple(f"codexpgauth{index:03d}" for index in range(1, 101))


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
    env["FUTURE_DISABLE_AUTH_LIMITS_FOR_BENCHMARK"] = "1"
    if backend == "postgres":
        env["FUTURE_DB_AUTH_BACKEND"] = "postgres"
    else:
        env.pop("FUTURE_DB_AUTH_BACKEND", None)
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
        for table in ("auth_sessions", "server_load_test_credentials", "users"):
            cur = con.execute(f"DELETE FROM {table} WHERE lower(username) LIKE 'codexpgauth%'")
            out[table] = int(cur.rowcount or 0)
        con.commit()
        return out
    finally:
        con.close()


def cleanup_postgres() -> dict:
    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.auth_sessions WHERE lower(username) LIKE 'codexpgauth%'")
            sessions = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.users WHERE lower(username) LIKE 'codexpgauth%'")
            users = int(cursor.rowcount or 0)
        return {"users": users, "auth_sessions": sessions}

    return app.postgres_execute(_write)


def provision_users(password: str) -> None:
    now = app.utc_timestamp()
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        con.execute("BEGIN IMMEDIATE")
        for username in USERS:
            profile = json.dumps({"full_name": f"Codex Auth {username[-3:]}", "load_test": True}, separators=(",", ":"))
            con.execute(
                "INSERT INTO users(username,is_admin,is_test,profile_json,updated_at_utc) VALUES(?,0,1,?,?) "
                "ON CONFLICT(username) DO UPDATE SET is_test=1,profile_json=excluded.profile_json,updated_at_utc=excluded.updated_at_utc",
                (username, profile, now),
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


def copy_test_users_to_postgres() -> None:
    con = sqlite3.connect(DATABASE)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT username,is_admin,is_test,profile_json,updated_at_utc FROM users WHERE lower(username) LIKE 'codexpgauth%'"
        ).fetchall()
    finally:
        con.close()
    for row in rows:
        app.postgres_upsert_user_row({
            "username": row["username"],
            "is_admin": bool(row["is_admin"]),
            "is_test": bool(row["is_test"]),
            "profile_json": row["profile_json"],
            "updated_at_utc": row["updated_at_utc"],
        })


def login(username: str, password: str) -> tuple[requests.Session, float]:
    session = requests.Session()
    started = time.perf_counter()
    response = session.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=60)
    elapsed = (time.perf_counter() - started) * 1000
    if response.status_code != 200:
        raise RuntimeError(f"login failed {response.status_code}: {response.text[:500]}")
    token = response.json().get("token", "")
    if not token:
        raise RuntimeError("login did not return token")
    session.headers.update({"Authorization": "Bearer " + token})
    return session, elapsed


def auth_me(session: requests.Session) -> tuple[int, dict, float]:
    started = time.perf_counter()
    response = session.get(f"{BASE}/auth/me", timeout=60)
    elapsed = (time.perf_counter() - started) * 1000
    try:
        body = response.json()
    except Exception:
        body = {"raw": response.text[:200]}
    return response.status_code, body, elapsed


def backend_session_count(backend: str) -> int:
    if backend == "sqlite":
        con = sqlite3.connect(DATABASE)
        try:
            return int(con.execute("SELECT COUNT(*) FROM auth_sessions WHERE lower(username) LIKE 'codexpgauth%'").fetchone()[0] or 0)
        finally:
            con.close()

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM future_server2.auth_sessions WHERE lower(username) LIKE 'codexpgauth%'")
            return int(cursor.fetchone()[0] or 0)

    return app.postgres_execute(_read)


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(len(ordered) * pct / 100.0))], 3)


def phase(name: str, backend: str, users: tuple[str, ...], password: str) -> dict:
    latencies = []
    me_latencies = []
    errors = 0
    mismatches = 0
    sample_errors = []
    sessions: dict[str, requests.Session] = {}
    started = time.perf_counter()

    def one(username: str):
        try:
            session, login_ms = login(username, password)
            status, body, me_ms = auth_me(session)
            return username, session, login_ms, status, body, me_ms, None
        except Exception as exc:
            return username, None, 0.0, 0, {}, 0.0, str(exc)

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, len(users))) as executor:
        rows = list(executor.map(one, users))
    for username, session, login_ms, status, body, me_ms, error in rows:
        latencies.append(float(login_ms))
        me_latencies.append(float(me_ms))
        if error or status != 200:
            errors += 1
            if len(sample_errors) < 3:
                sample_errors.append({"username": username, "status": status, "error": error, "body": body})
            continue
        if app.normalize_username((body.get("user") or {}).get("username", body.get("username", ""))) != username:
            mismatches += 1
        if session is not None:
            sessions[username] = session
    wall = (time.perf_counter() - started) * 1000
    session_count = backend_session_count(backend)
    if session_count < len(set(users)):
        mismatches += 1
    return {
        "name": name,
        "requests": len(users),
        "status_200": len(users) - errors,
        "errors": errors,
        "mismatches": mismatches,
        "session_count": session_count,
        "wall_ms": round(wall, 3),
        "p50_ms": percentile(latencies, 50),
        "p95_ms": percentile(latencies, 95),
        "p99_ms": percentile(latencies, 99),
        "me_p95_ms": percentile(me_latencies, 95),
        "throughput_rps": round((len(users) / wall) * 1000, 3) if wall else 0,
        "sample_errors": sample_errors,
        "sessions": sessions,
    }


def run_backend(backend: str, password: str) -> dict:
    process = start_server(backend)
    try:
        health_before = wait_health()
        single_session, single_ms = login(USERS[0], password)
        status, body, me_ms = auth_me(single_session)
        if status != 200:
            raise RuntimeError(f"{backend} /auth/me failed: {status} {body}")
        wrong = requests.post(f"{BASE}/auth/login", json={"username": USERS[0], "password": "wrong"}, timeout=30)
        if wrong.status_code == 200:
            raise RuntimeError(f"{backend} wrong password was accepted")
        distinct10 = phase(f"{backend}-login10", backend, USERS[:10], password)
        distinct50 = phase(f"{backend}-login50", backend, USERS[:50], password)
        distinct100 = phase(f"{backend}-login100", backend, USERS, password)
        health_after = requests.get(f"{BASE}/health", timeout=5).json()
        kept = distinct100["sessions"][USERS[0]]
        token_header = kept.headers.get("Authorization", "")
        return {
            "backend": backend,
            "health_before": {"pid": health_before.get("pid"), "postgres": health_before.get("postgres") or health_before.get("postgresql")},
            "health_after": {"pid": health_after.get("pid"), "postgres": health_after.get("postgres") or health_after.get("postgresql")},
            "single": {"login_ms": round(single_ms, 3), "me_ms": round(me_ms, 3), "wrong_password_status": wrong.status_code},
            "phases": [{k: v for k, v in row.items() if k != "sessions"} for row in (distinct10, distinct50, distinct100)],
            "restart_token": token_header,
        }
    finally:
        stop_pid(process.pid)


def restart_readback(password: str, token_header: str) -> dict:
    process = start_server("postgres")
    try:
        health = wait_health()
        session = requests.Session()
        session.headers.update({"Authorization": token_header})
        status, body, _ = auth_me(session)
        if status != 200:
            raise RuntimeError(f"restart token readback failed: {status} {body}")
        fresh, _ = login(USERS[1], password)
        fresh_status, fresh_body, _ = auth_me(fresh)
        if fresh_status != 200:
            raise RuntimeError(f"fresh login after restart failed: {fresh_status} {fresh_body}")
        return {"pid": health.get("pid"), "token_status": status, "fresh_status": fresh_status, "session_count": backend_session_count("postgres")}
    finally:
        stop_pid(process.pid)


def assert_ok(result: dict) -> None:
    for row in result.get("phases", []):
        if row["errors"] or row["mismatches"]:
            raise RuntimeError(f"{result['backend']} phase failed: {row}")


def main() -> int:
    if server_pid_on_port(18877):
        raise RuntimeError("test port 18877 is already in use")
    password = "codex-" + secrets.token_urlsafe(18)
    cleanup = {"sqlite_before": cleanup_sqlite(), "postgres_before": cleanup_postgres()}
    try:
        app.postgres_initialize_schema()
        provision_users(password)
        copy_test_users_to_postgres()
        sqlite_result = run_backend("sqlite", password)
        assert_ok(sqlite_result)
        postgres_result = run_backend("postgres", password)
        assert_ok(postgres_result)
        readback = restart_readback(password, postgres_result["restart_token"])
        cleanup["sqlite_after"] = cleanup_sqlite()
        cleanup["postgres_after"] = cleanup_postgres()
        refresh = subprocess.run(
            [sys.executable, str(ROOT / "FUTURE" / "tools" / "migrate_auth_users_to_postgres.py"), "--cleanup-test-rows"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=120,
        )
        if refresh.returncode != 0:
            raise RuntimeError(f"post-cleanup parity refresh failed: {refresh.stdout[-800:]} {refresh.stderr[-400:]}")
        verify = subprocess.run(
            [sys.executable, str(ROOT / "FUTURE" / "tools" / "migrate_auth_users_to_postgres.py"), "--verify-only"],
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
            "parity_refresh_exit": refresh.returncode,
            "parity_refresh": json.loads(refresh.stdout or "{}") if refresh.stdout.strip().startswith("{") else refresh.stdout[-500:],
            "verify_only_exit": verify.returncode,
            "verify_only": json.loads(verify.stdout or "{}") if verify.stdout.strip().startswith("{") else verify.stdout[-500:],
            "production_flag": os.environ.get("FUTURE_DB_AUTH_BACKEND", "off"),
            "test_port_busy": bool(server_pid_on_port(18877)),
        }
        if verify.returncode != 0:
            raise RuntimeError(f"verify-only failed: {verify.stdout[-800:]} {verify.stderr[-400:]}")
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    finally:
        stop_pid(server_pid_on_port(18877))
        cleanup_sqlite()
        cleanup_postgres()


if __name__ == "__main__":
    raise SystemExit(main())
