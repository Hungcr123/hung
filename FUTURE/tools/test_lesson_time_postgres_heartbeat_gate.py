#!/usr/bin/env python3
"""HTTP heartbeat write gate for lesson_time SQLite vs PostgreSQL backends."""

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
USERS = tuple(f"codextimewrite{index:03d}" for index in range(1, 101))

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
        env["FUTURE_DB_LESSON_TIME_BACKEND"] = "postgres"
    else:
        env.pop("FUTURE_DB_LESSON_TIME_BACKEND", None)
    return subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--host", "127.0.0.1", "--port", "18877", "--no-browser", "--no-tunnel"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

def lesson_paths() -> list[dict]:
    con = sqlite3.connect(DATABASE)
    try:
        rows = con.execute(
            """
            SELECT a.normalized_path,a.file_id
            FROM lesson_file_aliases a JOIN lesson_files f ON f.file_id=a.file_id
            WHERE a.active=1 AND f.status='active' AND lower(a.normalized_path) LIKE 'common/%'
            ORDER BY lower(a.normalized_path) LIMIT 100
            """
        ).fetchall()
    finally:
        con.close()
    if len(rows) < 100:
        raise RuntimeError(f"need 100 lessons, found {len(rows)}")
    return [{"path": row[0], "lesson_id": row[1], "key": app.lesson_time_key("file_id:" + row[1])} for row in rows]

def cleanup_sqlite() -> dict:
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        con.execute("BEGIN IMMEDIATE")
        out = {}
        for table in ("lesson_time_credit_state", "lesson_time", "auth_sessions", "server_load_test_credentials", "users"):
            cur = con.execute(f"DELETE FROM {table} WHERE lower(username) LIKE 'codextimewrite%'")
            out[table] = int(cur.rowcount or 0)
        con.commit()
        return out
    finally:
        con.close()

def cleanup_postgres() -> dict:
    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.lesson_time_credit_state WHERE lower(username) LIKE 'codextimewrite%'")
            credit = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.lesson_time WHERE lower(username) LIKE 'codextimewrite%'")
            total = int(cursor.rowcount or 0)
        return {"lesson_time": total, "lesson_time_credit_state": credit}
    return app.postgres_execute(_write)

def provision_auth(password: str) -> None:
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
    session.headers.update({"Authorization": "Bearer " + response.json()["token"]})
    return session

def post_heartbeat(session: requests.Session, lesson: dict, sequence: int, session_id: str, seconds: int = 5) -> tuple[int, dict, float]:
    payload = {
        "path": lesson["path"],
        "lesson_id": lesson["lesson_id"],
        "title": "Codex Time Write",
        "space": "Space_V",
        "seconds": seconds,
        "sessionId": session_id,
        "sequence": sequence,
        "protocol": app.LESSON_TIME_PROTOCOL,
    }
    started = time.perf_counter()
    response = session.post(f"{BASE}/lesson/time", json=payload, timeout=60)
    elapsed = (time.perf_counter() - started) * 1000
    try:
        body = response.json()
    except Exception:
        body = {"raw": response.text[:200]}
    return response.status_code, body, elapsed

def read_backend_seconds(backend: str, username: str, key: str) -> int:
    if backend == "sqlite":
        con = sqlite3.connect(DATABASE)
        try:
            row = con.execute("SELECT seconds FROM lesson_time WHERE username=? AND lesson_key=?", (username, key)).fetchone()
            return int(row[0] or 0) if row else 0
        finally:
            con.close()
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT seconds FROM future_server2.lesson_time WHERE username=%s AND lesson_key=%s", (username, key))
            row = cursor.fetchone()
        return int(row[0] or 0) if row else 0
    return app.postgres_execute(_read)

def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(len(ordered) * pct / 100.0))], 3)

def phase(name: str, backend: str, users: tuple[str, ...], sessions: dict[str, requests.Session], lessons_by_user: dict[str, dict], base_sequence: int) -> dict:
    latencies = []
    errors = 0
    accepted = 0
    mismatches = 0
    sample_errors = []
    started = time.perf_counter()
    def one(pair):
        idx, username = pair
        lesson = lessons_by_user[username]
        return username, lesson, post_heartbeat(sessions[username], lesson, base_sequence + idx, f"codex-session-{USERS.index(username)}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, len(users))) as executor:
        rows = list(executor.map(one, enumerate(users, 1)))
    for username, lesson, (status, body, elapsed) in rows:
        latencies.append(elapsed)
        time_row = body.get("time") if isinstance(body.get("time"), dict) else {}
        errors += 0 if status == 200 else 1
        if status != 200 and len(sample_errors) < 3:
            sample_errors.append({"status": status, "body": body})
        accepted += max(0, int(time_row.get("acceptedSeconds", 0) or 0))
        if status != 200 or read_backend_seconds(backend, username, lesson["key"]) <= 0:
            mismatches += 1
    wall = (time.perf_counter() - started) * 1000
    return {
        "name": name,
        "backend": backend,
        "requests": len(users),
        "success": len(users) - errors,
        "errors": errors,
        "timeouts": 0,
        "accepted_seconds": accepted,
        "mismatches": mismatches,
        "sample_errors": sample_errors,
        "wall_ms": round(wall, 3),
        "throughput_rps": round(len(users) / max(0.001, wall / 1000), 3),
        "p50_ms": percentile(latencies, 50),
        "p95_ms": percentile(latencies, 95),
        "p99_ms": percentile(latencies, 99),
    }

def warm_sessions(sessions: dict[str, requests.Session], lessons_by_user: dict[str, dict]) -> dict:
    users = tuple(USERS)
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
        rows = list(executor.map(
            lambda user: post_heartbeat(sessions[user], lessons_by_user[user], 1, f"codex-session-{USERS.index(user)}"),
            users,
        ))
    statuses = {}
    for status, _body, _elapsed in rows:
        statuses[str(status)] = statuses.get(str(status), 0) + 1
    time.sleep(1.15)
    return {"statuses": statuses}

def run_backend(backend: str, password: str, lessons: list[dict]) -> dict:
    stop_pid(server_pid_on_port(18877))
    cleanup_sqlite()
    cleanup_postgres()
    provision_auth(password)
    proc = start_server(backend)
    try:
        health = wait_health()
        sessions = {username: login(username, password) for username in USERS}
        lessons_by_user = {username: lessons[idx] for idx, username in enumerate(USERS)}
        warm = warm_sessions(sessions, lessons_by_user)
        single = phase("single", backend, USERS[:1], sessions, lessons_by_user, 10)
        retry_status, retry_body, retry_latency = post_heartbeat(sessions[USERS[0]], lessons_by_user[USERS[0]], 11, "codex-session-0")
        same_user = phase("same_user_contention", backend, tuple([USERS[-1]] * 10), sessions, lessons_by_user, 1000)
        distinct10 = phase("distinct10", backend, USERS[:10], sessions, lessons_by_user, 100)
        distinct50 = phase("distinct50", backend, USERS[:50], sessions, lessons_by_user, 200)
        distinct100 = phase("distinct100", backend, USERS, sessions, lessons_by_user, 300)
        return {
            "backend": backend,
            "health_pid": health.get("pid"),
            "warm": warm,
            "phases": [single, distinct10, distinct50, distinct100, same_user],
            "exact_retry": {
                "status": retry_status,
                "acceptedSeconds": ((retry_body.get("time") or {}).get("acceptedSeconds") if isinstance(retry_body, dict) else None),
                "heartbeatReason": ((retry_body.get("time") or {}).get("heartbeatReason") if isinstance(retry_body, dict) else None),
                "latency_ms": round(retry_latency, 3),
            },
        }
    finally:
        stop_pid(proc.pid if proc else 0)

def main() -> int:
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before running lesson_time heartbeat gate.")
    password = secrets.token_urlsafe(24)
    lessons = lesson_paths()
    result = {"ok": False}
    try:
        sqlite = run_backend("sqlite", password, lessons)
        postgres = run_backend("postgres", password, lessons)
        cleanup = {"sqlite": cleanup_sqlite(), "postgres": cleanup_postgres()}
        ok = all(phase["errors"] == 0 and phase["mismatches"] == 0 for item in (sqlite, postgres) for phase in item["phases"])
        ok = ok and sqlite["exact_retry"]["acceptedSeconds"] == 0 and postgres["exact_retry"]["acceptedSeconds"] == 0
        result = {
            "ok": ok,
            "sqlite": sqlite,
            "postgres": postgres,
            "cleanup": cleanup,
            "production_enabled": os.environ.get("FUTURE_DB_LESSON_TIME_BACKEND", "") or "off",
        }
    finally:
        stop_pid(server_pid_on_port(18877))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1

if __name__ == "__main__":
    raise SystemExit(main())
