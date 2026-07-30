#!/usr/bin/env python3
"""Grouped HTTP gate for notice/announcement/speak-skip PostgreSQL slices."""

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
from FUTURE.postgres.repositories import announcements as pg_announcements  # noqa: E402
from FUTURE.postgres.repositories import lesson_task_notices as pg_task_notices  # noqa: E402
from FUTURE.postgres.repositories import space_w_speak_skip as pg_speak_skip  # noqa: E402

DATABASE = Path(os.environ.get("FUTURE_SERVER2_SQLITE_DB", "")) if os.environ.get("FUTURE_SERVER2_SQLITE_DB") else Path(os.environ.get("FUTURE_SERVER_DATA_ROOT", r"C:\server data")) / "server2.db"
BASE = "http://127.0.0.1:18877"
PRODUCTION_BASE = "http://127.0.0.1:8877"
PREFIX = "codexpgnote"
USERS = tuple(f"{PREFIX}{index:03d}" for index in range(1, 101))
ADMIN = f"{PREFIX}admin"


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
        pass


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
    raise RuntimeError("Test Server 2 did not become healthy")


def start_test_server() -> subprocess.Popen:
    env = dict(os.environ)
    env["FUTURE_DB_ANNOUNCEMENTS_BACKEND"] = "postgres"
    env["FUTURE_DB_LESSON_TASK_NOTICES_BACKEND"] = "postgres"
    env["FUTURE_DB_SPACE_W_SPEAK_SKIP_BACKEND"] = "postgres"
    return subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--host", "127.0.0.1", "--port", "18877", "--no-browser", "--no-tunnel"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def provision_users(password: str) -> None:
    now = app.utc_timestamp()
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        con.execute("BEGIN IMMEDIATE")
        for username in (ADMIN, *USERS):
            profile = json.dumps({"full_name": username, "load_test": True}, separators=(",", ":"))
            is_admin = 1 if username == ADMIN else 0
            con.execute(
                "INSERT INTO users(username,is_admin,is_test,profile_json,updated_at_utc) VALUES(?,?,?,?,?) "
                "ON CONFLICT(username) DO UPDATE SET is_admin=excluded.is_admin,is_test=1,profile_json=excluded.profile_json,updated_at_utc=excluded.updated_at_utc",
                (username, is_admin, 1, profile, now),
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
    with app.ADMIN_LOCK:
        admins = app.read_admins_locked()
        admins.add(ADMIN)
        app.write_admins_locked(admins)


def cleanup_sqlite() -> dict:
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        con.execute("BEGIN IMMEDIATE")
        out = {}
        for table in ("auth_sessions", "server_load_test_credentials", "users"):
            cursor = con.execute(f"DELETE FROM {table} WHERE lower(username) LIKE ?", (f"{PREFIX}%",))
            out[table] = int(cursor.rowcount or 0)
        con.commit()
        return out
    finally:
        con.close()


def cleanup_postgres_test_rows() -> None:
    for username in USERS:
        pg_task_notices.delete_user(username)
    pg_task_notices.delete_user(ADMIN)
    payload = pg_speak_skip.load_payload()
    rows = {
        key: value
        for key, value in payload.get("requests", {}).items()
        if not app.normalize_username(value.get("username", "")).lower().startswith(PREFIX)
    }
    pg_speak_skip.save_payload({"version": 1, "updated_at": payload.get("updated_at", ""), "requests": rows})


def restore_snapshots(ann: dict, notices: dict, speak: dict) -> None:
    pg_announcements.save_items(list(ann.get("items", [])), app.clean(ann.get("updated_at", "")) or app.utc_timestamp())
    pg_task_notices.save_payload(notices)
    pg_speak_skip.save_payload(speak)


def admin_snapshot() -> dict:
    payload = app.server_database_read_document_json(app.ADMINS_FILE, {})
    return payload if isinstance(payload, dict) else {"admins": []}


def restore_admin_snapshot(payload: dict) -> None:
    app.server_database_store_document_now(app.ADMINS_FILE, json.dumps(payload if isinstance(payload, dict) else {"admins": []}, ensure_ascii=False, indent=2), authoritative=True)


def login(username: str, password: str) -> requests.Session:
    session = requests.Session()
    deadline = time.monotonic() + 45
    last = ""
    while time.monotonic() < deadline:
        try:
            response = session.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=10)
            last = f"{response.status_code} {response.text[:160]}"
            if response.status_code == 200:
                token = response.json().get("token")
                if token:
                    session.headers.update({"Authorization": f"Bearer {token}"})
                    return session
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(0.4)
    raise RuntimeError(f"Login failed for {username}: {last}")


def request_json(session: requests.Session, method: str, path: str, **kwargs) -> tuple[int, dict, float]:
    started = time.perf_counter()
    response = session.request(method, f"{BASE}{path}", timeout=90, **kwargs)
    elapsed = (time.perf_counter() - started) * 1000
    try:
        payload = response.json()
    except Exception:
        payload = {"raw": response.text[:200]}
    return response.status_code, payload, elapsed


def metrics(name: str, rows: list[tuple[int, dict, float]], started: float) -> dict:
    latencies = sorted(float(row[2]) for row in rows)
    statuses: dict[str, int] = {}
    for status, _payload, _elapsed in rows:
        statuses[str(status)] = statuses.get(str(status), 0) + 1
    wall = (time.perf_counter() - started) * 1000
    return {
        "name": name,
        "requests": len(rows),
        "statuses": statuses,
        "errors": sum(1 for status, payload, _elapsed in rows if status >= 400 or not payload.get("ok", status == 200)),
        "wall_ms": round(wall, 3),
        "throughput_rps": round(len(rows) / max(0.001, wall / 1000), 3),
        "p50_ms": round(statistics.median(latencies), 3) if latencies else 0,
        "p95_ms": round(latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))], 3) if latencies else 0,
        "p99_ms": round(latencies[min(len(latencies) - 1, int(len(latencies) * 0.99))], 3) if latencies else 0,
    }


def run_phase(name: str, users: tuple[str, ...], sessions: dict[str, requests.Session], worker) -> dict:
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(users)) as executor:
        results = list(executor.map(lambda user: worker(user, sessions[user]), users))
    rows: list[tuple[int, dict, float]] = []
    for result in results:
        rows.extend(result if isinstance(result, list) else [result])
    return metrics(name, rows, started)


def postgres_counts() -> dict:
    def _run(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM future_server2.lesson_task_notices WHERE lower(username) LIKE %s", (f"{PREFIX}%",))
            task_notices = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT count(*) FROM future_server2.lesson_task_notice_state WHERE lower(username) LIKE %s", (f"{PREFIX}%",))
            task_state = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT count(*) FROM future_server2.space_w_speak_skip_requests WHERE lower(username) LIKE %s", (f"{PREFIX}%",))
            speak = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT state, count(*) FROM pg_stat_activity WHERE datname=current_database() GROUP BY state")
            activity = {str(row[0] or "unknown"): int(row[1] or 0) for row in cursor.fetchall()}
        return {"task_notices": task_notices, "task_state": task_state, "speak_skip": speak, "pg_activity": activity}

    return app.postgres_execute(_run)


def main() -> int:
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("FUTURE_PG_DSN is required")
    if server_pid_on_port(8877) and not health(PRODUCTION_BASE, 3).get("ok"):
        raise RuntimeError("Production port 8877 is occupied but not healthy")
    old_18877 = server_pid_on_port(18877)
    if old_18877:
        stop_pid(old_18877)
    password = secrets.token_urlsafe(18)
    ann_before = pg_announcements.load()
    notices_before = pg_task_notices.load_payload()
    speak_before = pg_speak_skip.load_payload()
    admins_before = admin_snapshot()
    process: subprocess.Popen | None = None
    started_total = time.perf_counter()
    try:
        cleanup_postgres_test_rows()
        cleanup_sqlite()
        provision_users(password)
        process = start_test_server()
        wait_health(process.pid)
        sessions = {username: login(username, password) for username in USERS}
        admin_session = login(ADMIN, password)

        ann_get = request_json(admin_session, "GET", "/announcements")
        ann_post = request_json(admin_session, "POST", "/announcements", json={"text": "Codex notice gate"})
        ann_retry = request_json(admin_session, "POST", "/announcements", json={"text": "Codex notice gate"})
        ann_read = request_json(admin_session, "GET", "/announcements")

        def task_notice_worker(username: str, session: requests.Session):
            notice_id = f"{PREFIX}-{username}"
            save = request_json(admin_session, "POST", "/lesson-task-notices", json={
                "user": username,
                "id": notice_id,
                "text": f"Notice for {username}",
                "language": "en",
                "translation_en": f"Notice for {username}",
                "translation_vi": f"Thong bao cho {username}",
                "mode": "always",
                "audio_enabled": False,
            })
            read_admin = request_json(admin_session, "GET", "/lesson-task-notices", params={"user": username})
            read_user = request_json(session, "GET", "/lesson-task-notices")
            seen = request_json(session, "POST", "/lesson-task-notices", json={"action": "seen", "id": notice_id})
            ack = request_json(session, "POST", "/lesson-task-notices", json={"action": "read", "id": notice_id})
            retry_seen = request_json(session, "POST", "/lesson-task-notices", json={"action": "seen", "id": notice_id})
            return [save, read_admin, read_user, seen, ack, retry_seen]

        def speak_worker(username: str, session: requests.Session):
            payload = {"path": f"common/{PREFIX}.Space_W", "lesson_id": f"ftg-lesson-{PREFIX}", "nodeIndex": 1, "nodeCount": 3, "sessionId": f"{PREFIX}-session-{username}", "title": "Codex speak skip", "expected": "hello", "reason": "gate"}
            req = request_json(session, "POST", "/space-w/speak-skip/request", json=payload)
            retry = request_json(session, "POST", "/space-w/speak-skip/request", json=payload)
            state = request_json(session, "GET", "/space-w/speak-skip/state", params=payload)
            request_id = ((req[1].get("request") or {}) if isinstance(req[1], dict) else {}).get("id", "")
            listed = request_json(admin_session, "GET", "/space-w/speak-skip/list", params={"status": "pending", "username": username})
            respond = request_json(admin_session, "POST", "/space-w/speak-skip/respond", json={"username": username, "id": request_id, "action": "accept"})
            state2 = request_json(session, "GET", "/space-w/speak-skip/state", params=payload)
            return [req, retry, state, listed, respond, state2]

        phases = []
        for n in (10, 50, 100):
            subset = USERS[:n]
            phases.append(run_phase(f"task_notices_{n}", subset, sessions, task_notice_worker))
            phases.append(run_phase(f"speak_skip_{n}", subset, sessions, speak_worker))

        counts_after_write = postgres_counts()
        health_after = health(BASE, 10)
        pg_metrics = health_after.get("postgres", {}) if isinstance(health_after.get("postgres"), dict) else {}

        cleanup_postgres_test_rows()
        cleanup_counts = postgres_counts()
        restore_snapshots(ann_before, notices_before, speak_before)
        verify = {
            "announcements": pg_announcements.load().get("items", []) == ann_before.get("items", []),
            "lesson_task_notices": pg_task_notices.load_payload() == notices_before,
            "space_w_speak_skip": pg_speak_skip.fingerprint(pg_speak_skip.load_payload()) == pg_speak_skip.fingerprint(speak_before),
        }
        cleanup_sqlite_result = cleanup_sqlite()
        restore_admin_snapshot(admins_before)

        output = {
            "ok": True,
            "announcements": {
                "get_status": ann_get[0],
                "post_status": ann_post[0],
                "retry_status": ann_retry[0],
                "read_status": ann_read[0],
                "read_contains_test": "Codex notice gate" in json.dumps(ann_read[1], ensure_ascii=False),
            },
            "phases": phases,
            "postgres_metrics": pg_metrics,
            "counts_after_write": counts_after_write,
            "cleanup_counts": cleanup_counts,
            "cleanup_sqlite": cleanup_sqlite_result,
            "restore_verify": verify,
            "total_ms": round((time.perf_counter() - started_total) * 1000, 3),
        }
        output["ok"] = (
            all(phase.get("errors") == 0 for phase in phases)
            and all(value in {200, 204} for value in (ann_get[0], ann_post[0], ann_retry[0], ann_read[0]))
            and output["announcements"]["read_contains_test"]
            and all(verify.values())
            and cleanup_counts.get("task_notices") == 0
            and cleanup_counts.get("task_state") == 0
            and cleanup_counts.get("speak_skip") == 0
            and int(pg_metrics.get("rollbacks", 0) or 0) == 0
        )
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0 if output["ok"] else 1
    finally:
        try:
            cleanup_postgres_test_rows()
            restore_snapshots(ann_before, notices_before, speak_before)
            restore_admin_snapshot(admins_before)
        except Exception:
            pass
        try:
            cleanup_sqlite()
        except Exception:
            pass
        if process and process.poll() is None:
            stop_pid(process.pid)


if __name__ == "__main__":
    raise SystemExit(main())
