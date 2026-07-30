#!/usr/bin/env python3
"""HTTP read-runtime gate for lesson_time with PostgreSQL routing."""

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
USERS = tuple(f"codextimeread{index:03d}" for index in range(1, 101))

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

def wait_health(pid: int = 0, timeout: float = 90.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            response = requests.get(f"{BASE}/health", timeout=3)
            if response.status_code == 200:
                payload = response.json()
                if payload.get("ok") and (not pid or int(payload.get("pid", 0) or 0) == pid):
                    return payload
        except Exception:
            pass
        time.sleep(0.4)
    raise RuntimeError("Test Server 2 did not become healthy")

def start_test_server() -> subprocess.Popen:
    env = dict(os.environ)
    env["FUTURE_DB_LESSON_TIME_BACKEND"] = "postgres"
    return subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--host", "127.0.0.1", "--port", "18877", "--no-browser", "--no-tunnel"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

def lesson_paths(limit: int = 100) -> list[dict]:
    con = sqlite3.connect(DATABASE)
    try:
        rows = con.execute(
            """
            SELECT a.normalized_path,a.file_id
            FROM lesson_file_aliases a
            JOIN lesson_files f ON f.file_id=a.file_id
            WHERE a.active=1 AND f.status='active'
              AND lower(a.normalized_path) LIKE 'common/%'
              AND lower(a.normalized_path) LIKE '%.space_v'
            ORDER BY a.normalized_path
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        con.close()
    if len(rows) < limit:
        raise RuntimeError(f"Need {limit} active lessons, found {len(rows)}")
    return [{"path": row[0], "lesson_id": row[1]} for row in rows]

def cleanup_sqlite() -> dict:
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        con.execute("BEGIN IMMEDIATE")
        out = {}
        for table in ("lesson_time_credit_state", "lesson_time", "auth_sessions", "server_load_test_credentials", "users"):
            cursor = con.execute(f"DELETE FROM {table} WHERE lower(username) LIKE 'codextimeread%'")
            out[table] = int(cursor.rowcount or 0)
        con.commit()
        return out
    finally:
        con.close()

def cleanup_postgres() -> dict:
    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.lesson_time_credit_state WHERE lower(username) LIKE 'codextimeread%'")
            deleted_credit = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.lesson_time WHERE lower(username) LIKE 'codextimeread%'")
            deleted_time = int(cursor.rowcount or 0)
            return {"deleted_time": deleted_time, "deleted_credit": deleted_credit}
    return app.postgres_execute(_write)

def provision_users_and_time(password: str, paths: list[dict]) -> None:
    now = app.utc_timestamp()
    epoch = app.timestamp_to_epoch(now)
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        con.execute("BEGIN IMMEDIATE")
        for index, username in enumerate(USERS, 1):
            profile = json.dumps({"full_name": f"Codex Time Read {index:03d}", "load_test": True}, separators=(",", ":"))
            con.execute(
                "INSERT INTO users(username,is_admin,is_test,profile_json,updated_at_utc) VALUES(?,0,1,?,?) "
                "ON CONFLICT(username) DO UPDATE SET is_admin=0,is_test=1,profile_json=excluded.profile_json,updated_at_utc=excluded.updated_at_utc",
                (username, profile, now),
            )
            existing = con.execute("SELECT password_hash FROM server_load_test_credentials WHERE username=?", (username,)).fetchone()
            encoded = existing[0] if existing and password_hash_matches(password, existing[0]) else password_hash(password)
            con.execute(
                "INSERT INTO server_load_test_credentials(username,password_hash,updated_at_utc) VALUES(?,?,?) "
                "ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash,updated_at_utc=excluded.updated_at_utc",
                (username, encoded, now),
            )
            lesson = paths[index - 1]
            lesson_key = app.lesson_time_key(f"file_id:{lesson['lesson_id']}")
            con.execute(
                "INSERT INTO lesson_time(username,lesson_key,file_id,path,title,space,seconds,ticks,updated_at_utc,updated_epoch) "
                "VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(username,lesson_key) DO UPDATE SET "
                "file_id=excluded.file_id,path=excluded.path,title=excluded.title,space=excluded.space,"
                "seconds=excluded.seconds,ticks=excluded.ticks,updated_at_utc=excluded.updated_at_utc,updated_epoch=excluded.updated_epoch",
                (username, lesson_key, lesson["lesson_id"], lesson["path"], f"Codex Time {index:03d}", "Space_V", index + 30, index, now, epoch + index),
            )
            con.execute(
                "INSERT INTO lesson_time_credit_state(username,lesson_key,file_id,session_id,last_sequence,last_seen_epoch,boot_id,lease_issued_epoch,offline_credited_seconds,updated_at_utc) "
                "VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(username,lesson_key) DO UPDATE SET "
                "file_id=excluded.file_id,session_id=excluded.session_id,last_sequence=excluded.last_sequence,last_seen_epoch=excluded.last_seen_epoch,"
                "boot_id=excluded.boot_id,lease_issued_epoch=excluded.lease_issued_epoch,offline_credited_seconds=excluded.offline_credited_seconds,updated_at_utc=excluded.updated_at_utc",
                (username, lesson_key, lesson["lesson_id"], f"codexpg-session-{index}", index, epoch + index, "codexpg-boot", epoch, index % 5, now),
            )
        con.commit()
    finally:
        con.close()

def migrate_copy() -> dict:
    raw = subprocess.check_output([sys.executable, str(ROOT / "FUTURE/tools/migrate_lesson_time_to_postgres.py")], cwd=ROOT, text=True)
    return json.loads(raw)

def migrate_verify() -> dict:
    raw = subprocess.check_output([sys.executable, str(ROOT / "FUTURE/tools/migrate_lesson_time_to_postgres.py"), "--verify-only"], cwd=ROOT, text=True)
    return json.loads(raw)

def login(username: str, password: str) -> requests.Session:
    session = requests.Session()
    response = session.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
    response.raise_for_status()
    session.headers.update({"Authorization": f"Bearer {response.json()['token']}"})
    return session

def request_list(session: requests.Session, username: str, path: str) -> tuple[int, dict, float]:
    started = time.perf_counter()
    response = session.get(
        f"{BASE}/server-data/list",
        params={"path": path.rsplit("/", 1)[0], "task_owner": username, "fresh": "1"},
        timeout=90,
    )
    elapsed = (time.perf_counter() - started) * 1000
    try:
        payload = response.json()
    except Exception:
        payload = {"raw": response.text[:200]}
    return response.status_code, payload, elapsed

def extract_seconds(payload: dict, path: str) -> int:
    entries = payload.get("entries") if isinstance(payload.get("entries"), list) else []
    wanted = path.lower()
    for entry in entries:
        if not isinstance(entry, dict) or str(entry.get("path", "")).lower() != wanted:
            continue
        study = entry.get("study") if isinstance(entry.get("study"), dict) else {}
        study_time = study.get("time") if isinstance(study.get("time"), dict) else {}
        return int(study_time.get("seconds", study.get("time_seconds", 0)) or 0)
    return -1

def phase(name: str, users: tuple[str, ...], sessions: dict[str, requests.Session], paths: dict[str, dict]) -> dict:
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(users)) as executor:
        rows = list(executor.map(lambda user: request_list(sessions[user], user, paths[user]["path"]), users))
    latencies = sorted(row[2] for row in rows)
    statuses: dict[str, int] = {}
    bad_seconds = 0
    for user, row in zip(users, rows):
        statuses[str(row[0])] = statuses.get(str(row[0]), 0) + 1
        expected = USERS.index(user) + 31
        if row[0] != 200 or extract_seconds(row[1], paths[user]["path"]) != expected:
            bad_seconds += 1
    wall = (time.perf_counter() - started) * 1000
    return {
        "name": name,
        "requests": len(users),
        "statuses": statuses,
        "errors": sum(1 for row in rows if row[0] >= 400),
        "bad_seconds": bad_seconds,
        "wall_ms": round(wall, 3),
        "throughput_rps": round(len(users) / max(0.001, wall / 1000), 3),
        "p50_ms": round(statistics.median(latencies), 3) if latencies else 0,
        "p95_ms": round(latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))], 3) if latencies else 0,
        "p99_ms": round(latencies[min(len(latencies) - 1, int(len(latencies) * 0.99))], 3) if latencies else 0,
    }

def production_health() -> dict:
    try:
        response = requests.get(f"{PRODUCTION_BASE}/health", timeout=5)
        payload = response.json()
        return {"status": response.status_code, "ok": bool(payload.get("ok")), "writer_queue": (payload.get("sqlite_writer") or {}).get("queue_depth")}
    except Exception as exc:
        return {"status": 0, "ok": False, "error": type(exc).__name__}

def main() -> int:
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before running the lesson_time PostgreSQL HTTP gate.")
    password = secrets.token_urlsafe(24)
    lessons = lesson_paths(len(USERS))
    paths_by_user = {username: lessons[index] for index, username in enumerate(USERS)}
    original_pid_text = app.SERVER_PID_FILE.read_text(encoding="utf-8") if app.SERVER_PID_FILE.exists() else None
    proc: subprocess.Popen | None = None
    result: dict = {"ok": False}
    try:
        cleanup_sqlite()
        cleanup_postgres()
        provision_users_and_time(password, lessons)
        copy_result = migrate_copy()
        if not copy_result.get("parity"):
            raise RuntimeError(f"copy parity failed: {copy_result}")
        existing = server_pid_on_port(18877)
        if existing:
            stop_pid(existing)
        proc = start_test_server()
        wait_health(proc.pid)
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
            sessions = dict(zip(USERS, executor.map(lambda user: login(user, password), USERS)))
        phases = [phase(f"{count}_list_read", USERS[:count], sessions, paths_by_user) for count in (1, 10, 50, 100)]
        if any(item["errors"] or item["bad_seconds"] for item in phases):
            raise RuntimeError(f"read phase failed: {phases}")
        stop_pid(proc.pid)
        proc = None
        proc = start_test_server()
        wait_health(proc.pid)
        restart_session = login(USERS[0], password)
        restart_read = request_list(restart_session, USERS[0], paths_by_user[USERS[0]]["path"])
        if restart_read[0] != 200 or extract_seconds(restart_read[1], paths_by_user[USERS[0]]["path"]) != 31:
            raise RuntimeError("restart readback failed")
        verify = migrate_verify()
        if not verify.get("parity"):
            raise RuntimeError(f"verify-only failed: {verify}")
        result = {"ok": True, "copy": copy_result, "phases": phases, "restart_read_status": restart_read[0], "verify_only": verify}
    finally:
        if proc is not None:
            stop_pid(proc.pid)
        cleanup_pg = cleanup_postgres()
        cleanup_sq = cleanup_sqlite()
        final_verify = None
        try:
            final_verify = migrate_verify()
        except Exception as exc:
            final_verify = {"ok": False, "error": str(exc)}
        result["cleanup"] = {"postgres": cleanup_pg, "sqlite": cleanup_sq}
        result["final_verify_only"] = final_verify
        result["production_health"] = production_health()
        result["port_18877_pid"] = server_pid_on_port(18877)
        if original_pid_text is None:
            app.SERVER_PID_FILE.unlink(missing_ok=True)
        else:
            app.SERVER_PID_FILE.write_text(original_pid_text, encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") and result.get("final_verify_only", {}).get("parity") and result.get("port_18877_pid") == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
