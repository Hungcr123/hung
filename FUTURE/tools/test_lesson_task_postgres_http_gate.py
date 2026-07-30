#!/usr/bin/env python3
"""HTTP runtime/shadow gate for Space Task with PostgreSQL routing."""

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
import FUTURE.tools.migrate_lesson_task_to_postgres as migrate_task  # noqa: E402

DATABASE = Path(r"C:\server data\server2.db")
BASE = "http://127.0.0.1:18877"
PRODUCTION_BASE = "http://127.0.0.1:8877"
USERS = tuple(f"codexpgtask{index:03d}" for index in range(1, 101))

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
    env["FUTURE_DB_LESSON_TASK_BACKEND"] = "postgres"
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
        for index, username in enumerate(USERS, 1):
            profile = json.dumps({"full_name": f"Codex PG Task {index:03d}", "load_test": True}, separators=(",", ":"))
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
        con.commit()
    finally:
        con.close()

def cleanup_sqlite() -> dict:
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        con.execute("BEGIN IMMEDIATE")
        out = {}
        for table in ("lesson_task_state", "auth_sessions", "server_load_test_credentials", "users"):
            cursor = con.execute(f"DELETE FROM {table} WHERE lower(username) LIKE 'codexpgtask%'")
            out[table] = int(cursor.rowcount or 0)
        con.commit()
        return out
    finally:
        con.close()

def cleanup_postgres() -> dict:
    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.lesson_task_state WHERE lower(username) LIKE 'codexpgtask%'")
            deleted = int(cursor.rowcount or 0)
            cursor.execute("SELECT count(*) FROM future_server2.lesson_task_state WHERE lower(username) LIKE 'codexpgtask%'")
            remaining = int(cursor.fetchone()[0] or 0)
            return {"deleted": deleted, "remaining": remaining}
    return app.postgres_execute(_write)

def lesson_rows(limit: int = 300) -> list[dict]:
    con = sqlite3.connect(DATABASE)
    try:
        rows = con.execute(
            """
            SELECT a.normalized_path,a.file_id
            FROM lesson_file_aliases a
            JOIN lesson_files f ON f.file_id=a.file_id
            WHERE a.active=1 AND f.status='active'
              AND lower(a.normalized_path) LIKE 'common/%'
              AND (lower(a.normalized_path) LIKE '%.space_v' OR lower(a.normalized_path) LIKE '%.space_w' OR lower(a.normalized_path) LIKE '%.space_q')
            ORDER BY a.normalized_path
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        con.close()
    if len(rows) < limit:
        raise RuntimeError(f"Need {limit} lessons, found {len(rows)}")
    return [{"path": row[0], "lesson_id": row[1]} for row in rows]

def distributed_lessons() -> dict[str, list[dict]]:
    rows = lesson_rows(300)
    return {username: [rows[index], rows[index + 100], rows[index + 200]] for index, username in enumerate(USERS)}

def login(username: str, password: str) -> requests.Session:
    session = requests.Session()
    response = session.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
    response.raise_for_status()
    session.headers.update({"Authorization": f"Bearer {response.json()['token']}"})
    return session

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
        "errors": sum(1 for status, _payload, _elapsed in rows if status >= 400),
        "wall_ms": round(wall, 3),
        "throughput_rps": round(len(rows) / max(0.001, wall / 1000), 3),
        "p50_ms": round(statistics.median(latencies), 3) if latencies else 0,
        "p95_ms": round(latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))], 3) if latencies else 0,
        "p99_ms": round(latencies[min(len(latencies) - 1, int(len(latencies) * 0.99))], 3) if latencies else 0,
    }

def run_phase(name: str, users: tuple[str, ...], sessions: dict[str, requests.Session], worker) -> dict:
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(users)) as executor:
        rows = list(executor.map(lambda user: worker(user, sessions[user]), users))
    flat_rows = [item for row in rows for item in (row if isinstance(row, list) else [row])]
    return metrics(name, flat_rows, started)

def wait_settled(username: str, session: requests.Session) -> tuple[int, dict, float]:
    last = (0, {}, 0.0)
    for _attempt in range(24):
        last = request_json(session, "GET", "/lesson-tasks/status", params={"user": username})
        payload = last[1]
        if last[0] == 200 and payload.get("ready"):
            return request_json(session, "GET", "/lesson-tasks", params={"user": username})
        time.sleep(0.5)
    return last

def single_flow(username: str, session: requests.Session, lessons: list[dict]) -> dict:
    first = lessons[0]
    folder = first["path"].rsplit("/", 1)[0]
    stale_folder = lessons[1]["path"].rsplit("/", 1)[0]
    add1 = request_json(session, "POST", "/lesson-tasks", json={"action": "add", "user": username, "path": first["path"], "severity": "normal"})
    add_retry = request_json(session, "POST", "/lesson-tasks", json={"action": "add", "user": username, "path": first["path"], "severity": "normal"})
    folders = request_json(session, "POST", "/lesson-tasks", json={"action": "space-folders", "user": username, "folders": [folder], "baseRevision": ""})
    rev = str(((folders[1].get("space_task") or {}).get("updated_rev")) or "")
    stale = request_json(session, "POST", "/lesson-tasks", json={"action": "space-folders", "user": username, "folders": [stale_folder], "baseRevision": "stale-revision"})
    settled = wait_settled(username, session)
    task = (settled[1].get("tasks") or [add1[1].get("task") or {}])[0]
    remove = request_json(session, "POST", "/lesson-tasks", json={"action": "remove", "user": username, "path": task.get("path") or first["path"], "id": task.get("id", ""), "baseRevision": rev})
    read_after = request_json(session, "GET", "/lesson-tasks", params={"user": username})
    return {
        "add_status": add1[0],
        "retry_changed": (add_retry[1].get("result") or add_retry[1]).get("changed"),
        "folders_status": folders[0],
        "stale_status": stale[0],
        "stale_error": str(stale[1].get("error", ""))[:80],
        "remove_status": remove[0],
        "read_status": read_after[0],
        "final_tasks": len(read_after[1].get("tasks") or []),
        "ok": add1[0] == 200 and add_retry[0] == 200 and folders[0] == 200 and stale[0] == 400 and remove[0] == 200 and read_after[0] == 200,
    }

def count_test_rows() -> dict:
    sqlite_count = sum(1 for row in migrate_task.sqlite_rows() if row["username"].lower().startswith("codexpgtask"))
    pg_count = sum(1 for row in migrate_task.postgres_rows() if row["username"].lower().startswith("codexpgtask"))
    return {"sqlite": sqlite_count, "postgres": pg_count}

def production_health() -> dict:
    try:
        response = requests.get(f"{PRODUCTION_BASE}/health", timeout=5)
        payload = response.json()
        return {"status": response.status_code, "ok": bool(payload.get("ok")), "writer_queue": (payload.get("sqlite_writer") or {}).get("queue_depth")}
    except Exception as exc:
        return {"status": 0, "ok": False, "error": type(exc).__name__}

def main() -> int:
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before running the Space Task PostgreSQL HTTP gate.")
    password = secrets.token_urlsafe(24)
    original_pid_text = app.SERVER_PID_FILE.read_text(encoding="utf-8") if app.SERVER_PID_FILE.exists() else None
    proc: subprocess.Popen | None = None
    result: dict = {"ok": False}
    try:
        cleanup_sqlite()
        cleanup_postgres()
        provision_users(password)
        migrate_task.main()
        lessons = distributed_lessons()
        existing = server_pid_on_port(18877)
        if existing:
            stop_pid(existing)
        proc = start_test_server()
        wait_health(proc.pid)
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
            sessions = dict(zip(USERS, executor.map(lambda user: login(user, password), USERS)))
        single = single_flow(USERS[0], sessions[USERS[0]], lessons[USERS[0]])
        if not single["ok"]:
            raise RuntimeError(f"single flow failed: {single}")
        phases = []
        for count in (10, 50, 100):
            users = USERS[:count]
            phases.append(run_phase(f"{count}_add", users, sessions, lambda user, session: [
                request_json(session, "POST", "/lesson-tasks", json={"action": "add", "user": user, "path": lessons[user][0]["path"], "severity": "normal"})
            ]))
            phases.append(run_phase(f"{count}_retry_add", users, sessions, lambda user, session: [
                request_json(session, "POST", "/lesson-tasks", json={"action": "add", "user": user, "path": lessons[user][0]["path"], "severity": "normal"})
            ]))
            phases.append(run_phase(f"{count}_folders", users, sessions, lambda user, session: [
                request_json(session, "POST", "/lesson-tasks", json={
                    "action": "space-folders",
                    "user": user,
                    "folders": [item["path"].rsplit("/", 1)[0] for item in lessons[user]],
                })
            ]))
            phases.append(run_phase(f"{count}_read", users, sessions, lambda user, session: [
                request_json(session, "GET", "/lesson-tasks", params={"user": user})
            ]))
        if any(phase["errors"] for phase in phases):
            raise RuntimeError(f"concurrency phase failed: {phases}")
        same_user = run_phase("same_user_50_add_retry", tuple(USERS[1] for _ in range(50)), sessions, lambda user, session: [
            request_json(session, "POST", "/lesson-tasks", json={"action": "add", "user": user, "path": lessons[user][1]["path"], "severity": "normal"})
        ])
        if same_user["errors"]:
            raise RuntimeError(f"same-user contention failed: {same_user}")
        stop_pid(proc.pid)
        proc = None
        proc = start_test_server()
        wait_health(proc.pid)
        restart_session = login(USERS[2], password)
        restart_read = request_json(restart_session, "GET", "/lesson-tasks", params={"user": USERS[2]})
        if restart_read[0] != 200 or not (restart_read[1].get("tasks") or restart_read[1].get("space_task")):
            raise RuntimeError(f"restart readback failed: {restart_read[0]} {restart_read[1]}")
        verify = json.loads(subprocess.check_output([sys.executable, str(ROOT / "FUTURE/tools/migrate_lesson_task_to_postgres.py"), "--verify-only"], cwd=ROOT, text=True))
        if not verify.get("parity"):
            raise RuntimeError(f"verify-only failed: {verify}")
        result = {
            "ok": True,
            "single_flow": single,
            "phases": phases,
            "same_user": same_user,
            "restart_read_status": restart_read[0],
            "verify_only": verify,
        }
    finally:
        if proc is not None:
            stop_pid(proc.pid)
        cleanup_pg = cleanup_postgres()
        cleanup_sq = cleanup_sqlite()
        final_verify = None
        try:
            final_verify = json.loads(subprocess.check_output([sys.executable, str(ROOT / "FUTURE/tools/migrate_lesson_task_to_postgres.py"), "--verify-only"], cwd=ROOT, text=True))
        except Exception as exc:
            final_verify = {"ok": False, "error": str(exc)}
        result["cleanup"] = {"postgres": cleanup_pg, "sqlite": cleanup_sq, "remaining_test_rows": count_test_rows()}
        result["final_verify_only"] = final_verify
        result["production_health"] = production_health()
        result["port_18877_pid"] = server_pid_on_port(18877)
        if original_pid_text is None:
            app.SERVER_PID_FILE.unlink(missing_ok=True)
        else:
            app.SERVER_PID_FILE.write_text(original_pid_text, encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") and result.get("final_verify_only", {}).get("parity") and not result.get("cleanup", {}).get("remaining_test_rows", {}).get("postgres") else 1

if __name__ == "__main__":
    raise SystemExit(main())
