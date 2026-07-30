"""Run a dedicated SQLite-only rollback smoke on an isolated clone."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_ROOT = Path(r"E:\FutureServer2PostgresMigrationBackups\20260726_snapshot_baseline_20260726_032052")
PLAN_DIR = Path.home() / ".codex" / "plans"
BASE = "http://127.0.0.1:18877"
USERNAME = "codexrollback"
PASSWORD_ENV = "FUTURE_TEST_PASSWORD"
LESSON_SPACE = "Space_W"


def redact_env(env: dict[str, str]) -> dict[str, str]:
    result = dict(env)
    for key in list(result):
        upper = key.upper()
        if upper.startswith("FUTURE_DB_") or upper.startswith("FUTURE_POSTGRES_") or upper.startswith("FUTURE_PG_"):
            result.pop(key, None)
        elif "SHADOW" in upper or "FALLBACK" in upper:
            result.pop(key, None)
    result.pop("FUTURE_PG_DSN", None)
    result.pop("FUTURE_DISABLE_AUTH_LIMITS_FOR_BENCHMARK", None)
    return result


def port_pid(port: int) -> int:
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


def wait_health(expected_pid: int = 0, timeout: float = 90.0) -> dict:
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        try:
            response = requests.get(f"{BASE}/health?view=dashboard-v1", timeout=5)
            payload = response.json()
            if response.status_code == 200 and payload.get("ok") and (not expected_pid or int(payload.get("pid", 0) or 0) == expected_pid):
                return payload
            last_error = f"{response.status_code} {response.text[:200]}"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(0.4)
    raise RuntimeError(f"Server 2 did not become healthy: {last_error}")


def clone_snapshot(work_root: Path) -> tuple[Path, Path]:
    server_data = work_root / "server data"
    qmlearn = work_root / "QMLearn"
    shutil.copytree(SNAPSHOT_ROOT / "server data", server_data)
    shutil.copytree(SNAPSHOT_ROOT / "QMLearn", qmlearn)
    db_path = server_data / "server2.db"
    old_prefix = str(SNAPSHOT_ROOT).lower()
    new_prefix = str(work_root)
    connection = sqlite3.connect(db_path, timeout=30)
    try:
        rows = connection.execute("SELECT path_key,path FROM documents").fetchall()
        connection.execute("BEGIN IMMEDIATE")
        for path_key, path in rows:
            path_text = str(path or "")
            if path_text.lower().startswith(old_prefix):
                next_path = new_prefix + path_text[len(str(SNAPSHOT_ROOT)):]
                connection.execute(
                    "UPDATE documents SET path_key=?,path=? WHERE path_key=?",
                    (next_path.lower(), next_path, path_key),
                )
        connection.commit()
    finally:
        connection.close()
    return server_data, qmlearn


def make_env(server_data_root: Path, qmlearn_root: Path) -> dict[str, str]:
    env = redact_env(dict(os.environ))
    env["FUTURE_SERVER_DATA_ROOT"] = str(server_data_root)
    env["FUTURE_QMLEARN_ROOT"] = str(qmlearn_root)
    env["FUTURE_TEST_PASSWORD"] = os.environ.get(PASSWORD_ENV, "")
    if not env["FUTURE_TEST_PASSWORD"]:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this smoke")
    return env


def start_server(env: dict[str, str]) -> subprocess.Popen:
    return subprocess.Popen(
        [
            sys.executable,
            str(ROOT / "FUTURE_SERVER_2.py"),
            "--host",
            "127.0.0.1",
            "--port",
            "18877",
            "--no-browser",
            "--no-tunnel",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def load_app():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import FUTURE.server_app as app  # noqa: WPS433

    return app


def seed_user(server_data_root: Path, username: str, password: str) -> dict:
    app = load_app()
    user_file = app.user_file_path(username)
    profile = {
        "full_name": "Codex Rollback Smoke",
        "gender": "male",
        "birth_date": "1990-01-01",
        "intro": "isolated rollback smoke",
    }
    password_hash = app.password_hash(password)
    user_file.parent.mkdir(parents=True, exist_ok=True)
    user_text = f"{username}:{password_hash}\n" + "profile:" + json.dumps(app.normalize_profile(profile), ensure_ascii=False, separators=(",", ":")) + "\n"
    user_file.write_text(user_text, encoding="utf-8")
    app.server_database_store_document_now(user_file, user_text, encoding="utf-8", authoritative=True)
    saved_profile = app.server_database_upsert_user(username, profile)
    user_folder = app.user_folder_path(username)
    return {
        "user_file": str(user_file),
        "user_folder": str(user_folder),
        "profile_full_name": profile.get("full_name", ""),
        "user_upserted": bool(saved_profile),
    }


def login(password: str) -> tuple[requests.Session, dict, float]:
    session = requests.Session()
    started = time.perf_counter()
    response = session.post(f"{BASE}/auth/login", json={"username": USERNAME, "password": password}, timeout=45)
    elapsed = (time.perf_counter() - started) * 1000
    if response.status_code != 200:
        raise RuntimeError(f"login failed {response.status_code}: {response.text[:500]}")
    payload = response.json()
    token = str(payload.get("token") or "")
    if not token:
        raise RuntimeError("Login did not return a token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session, payload, elapsed


def auth_me(session: requests.Session) -> dict:
    response = session.get(f"{BASE}/auth/me", timeout=30)
    response.raise_for_status()
    return response.json()


def seed_user_http(password: str) -> dict:
    register = requests.post(
        f"{BASE}/auth/register",
        json={
            "username": USERNAME,
            "password": password,
            "full_name": "Codex Rollback Smoke",
            "gender": "male",
            "birth_date": "1990-01-01",
        },
        timeout=30,
    )
    approve = requests.post(f"{BASE}/auth/approve", json={"username": USERNAME, "action": "accept"}, timeout=30)
    return {
        "register_status": register.status_code,
        "register_body": register.json() if register.headers.get("content-type", "").startswith("application/json") else {},
        "approve_status": approve.status_code,
        "approve_body": approve.json() if approve.headers.get("content-type", "").startswith("application/json") else {},
    }


def lesson_choice(db_path: Path) -> dict:
    connection = sqlite3.connect(db_path, timeout=30)
    try:
        row = connection.execute(
            """
            SELECT normalized_path,file_id
            FROM lesson_file_aliases
            WHERE active=1 AND lower(normalized_path) LIKE 'common/%.space_w'
            ORDER BY normalized_path
            LIMIT 1
            """
        ).fetchone()
    finally:
        connection.close()
    if not row:
        raise RuntimeError("No active Space_W lesson found in the clone")
    return {"path": str(row[0]), "lesson_id": str(row[1])}


def lesson_time_row(db_path: Path, username: str, lesson_id: str) -> tuple[int, int]:
    connection = sqlite3.connect(db_path, timeout=30)
    try:
        row = connection.execute(
            "SELECT seconds,ticks FROM lesson_time WHERE username=? AND file_id=?",
            (username, lesson_id),
        ).fetchone()
    finally:
        connection.close()
    return (int(row[0] or 0), int(row[1] or 0)) if row else (0, 0)


def lesson_progress_count(db_path: Path, username: str) -> int:
    connection = sqlite3.connect(db_path, timeout=30)
    try:
        row = connection.execute("SELECT COUNT(*) FROM lesson_progress WHERE username=?", (username,)).fetchone()
    finally:
        connection.close()
    return int(row[0] or 0) if row else 0


def lesson_progress_fingerprint(db_path: Path, username: str) -> str:
    connection = sqlite3.connect(db_path, timeout=30)
    try:
        columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(lesson_progress)").fetchall()}
        selected = [column for column in ("file_id", "complete", "server_revision", "updated_at_utc", "record_json") if column in columns]
        if not selected:
            selected = ["username"]
        rows = connection.execute(
            f"SELECT {','.join(selected)} FROM lesson_progress WHERE username=? ORDER BY " + (",".join(selected[:2]) if len(selected) >= 2 else selected[0]),
            (username,),
        ).fetchall()
    finally:
        connection.close()
    payload = json.dumps([list(row) for row in rows], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def post_lesson_time(session: requests.Session, lesson: dict, seconds: int, sequence: int, lease: str = "") -> tuple[float, int, dict]:
    body = {
        "path": lesson["path"],
        "lesson_id": lesson["lesson_id"],
        "space": LESSON_SPACE,
        "protocol": "server-time-v1",
        "session_id": f"sqlite-rollback-{lesson['lesson_id']}",
        "seconds": seconds,
        "sequence": sequence,
    }
    if lease:
        body["offline_lease"] = lease
    started = time.perf_counter()
    response = session.post(f"{BASE}/lesson/time", json=body, timeout=45)
    elapsed = (time.perf_counter() - started) * 1000
    response.raise_for_status()
    return elapsed, response.status_code, response.json().get("time", {})


def post_complete(session: requests.Session, lesson: dict, run_id: str) -> tuple[float, int, dict]:
    body = {
        "path": lesson["path"],
        "lesson_id": lesson["lesson_id"],
        "file_id": lesson["lesson_id"],
        "title": "SQLite rollback smoke",
        "nodes": 1,
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "completion_run_id": run_id,
        "source": LESSON_SPACE,
    }
    started = time.perf_counter()
    response = session.post(f"{BASE}/lesson/complete", json=body, timeout=60)
    elapsed = (time.perf_counter() - started) * 1000
    response.raise_for_status()
    return elapsed, response.status_code, response.json()


def quick_check(db_path: Path) -> str:
    connection = sqlite3.connect(db_path, timeout=30)
    try:
        return str(connection.execute("PRAGMA quick_check").fetchone()[0] or "")
    finally:
        connection.close()


def cleanup_temp_user(server_data_root: Path, db_path: Path, username: str) -> dict:
    app = load_app()
    deleted = {}
    remaining = {}
    connection = sqlite3.connect(db_path, timeout=30)
    try:
        connection.execute("BEGIN IMMEDIATE")
        for table, sql in (
            ("lesson_time", "DELETE FROM lesson_time WHERE lower(username)=?"),
            ("lesson_time_credit_state", "DELETE FROM lesson_time_credit_state WHERE lower(username)=?"),
            ("lesson_progress", "DELETE FROM lesson_progress WHERE lower(username)=?"),
            ("lesson_progress_namespaces", "DELETE FROM lesson_progress_namespaces WHERE lower(username)=?"),
            ("append_events", "DELETE FROM append_events WHERE lower(username)=?"),
            ("auth_sessions", "DELETE FROM auth_sessions WHERE lower(username)=?"),
            ("users", "DELETE FROM users WHERE lower(username)=?"),
        ):
            cursor = connection.execute(sql, (username.lower(),))
            deleted[table] = int(cursor.rowcount or 0)
        connection.commit()
        for table in ("lesson_time", "lesson_time_credit_state", "lesson_progress", "lesson_progress_namespaces", "append_events", "auth_sessions", "users"):
            remaining[table] = int(connection.execute(f"SELECT COUNT(*) FROM {table} WHERE lower(username)=?", (username.lower(),)).fetchone()[0] or 0)
    finally:
        connection.close()
    user_file = server_data_root.parent / "QMLearn" / "users" / f"{username}.txt"
    user_folder = server_data_root.parent / "QMLearn" / "users" / username
    if user_file.exists():
        user_file.unlink()
    if user_folder.exists():
        shutil.rmtree(user_folder)
    deleted["user_file"] = int(not user_file.exists())
    deleted["user_folder"] = int(not user_folder.exists())
    with app.USER_LINES_RAM_CACHE_LOCK:
        app.USER_LINES_RAM_CACHE.pop(username.lower(), None)
    app.USER_PROFILE_RAM_CACHE.pop(username.lower(), None)
    with app.SERVER_DATABASE_USER_PROFILE_CACHE_LOCK:
        app.SERVER_DATABASE_USER_PROFILE_CACHE.pop(username.lower(), None)
    return {"deleted": deleted, "remaining": remaining, "user_file_exists": user_file.exists(), "user_folder_exists": user_folder.exists()}


def main() -> int:
    run_id = f"sqlite-rollback-{uuid.uuid4().hex}"
    work_root = Path(tempfile.mkdtemp(prefix="codex_sqlite_rollback_"))
    server_data_root, qmlearn_root = clone_snapshot(work_root)
    db_path = server_data_root / "server2.db"
    env = make_env(server_data_root, qmlearn_root)
    old_pid = port_pid(18877)
    if old_pid:
        stop_pid(old_pid)

    server1 = None
    server2 = None
    server3 = None
    summary: dict[str, object] = {"ok": False}
    started = time.perf_counter()
    password = env["FUTURE_TEST_PASSWORD"]
    if not (any(ch.islower() for ch in password) and any(ch.isupper() for ch in password) and any(ch.isdigit() for ch in password) and len(password) >= 6):
        password = "Aa1" + secrets.token_urlsafe(18)
    try:
        bootstrap_quick_check = quick_check(db_path)
        server1 = start_server(env)
        health1 = wait_health(server1.pid)
        probe1 = {
            "server_data_root": health1.get("server_data_root", ""),
            "qmlearn_root": health1.get("qmlearn_root", ""),
            "pid": health1.get("pid", 0),
            "pg_probe": health1.get("postgres_probe", {}),
        }
        seed_info = seed_user_http(password)
        if seed_info.get("register_status") != 202 or seed_info.get("approve_status") != 200:
            raise RuntimeError(f"seed_user_http failed: {json.dumps(seed_info, ensure_ascii=False)[:1000]}")

        server2 = server1
        health2 = health1
        probe2 = {
            "server_data_root": health2.get("server_data_root", ""),
            "qmlearn_root": health2.get("qmlearn_root", ""),
            "pid": health2.get("pid", 0),
            "pg_probe": health2.get("postgres_probe", {}),
        }

        session, login_payload, login_ms = login(password)
        me_payload = auth_me(session)
        lesson = lesson_choice(db_path)
        lesson_before = lesson_time_row(db_path, USERNAME, lesson["lesson_id"])
        lesson_count_before = lesson_progress_count(db_path, USERNAME)
        progress_fp_before = lesson_progress_fingerprint(db_path, USERNAME)

        time0_ms, time0_status, time0_body = post_lesson_time(session, lesson, 0, 0)
        lease = str(time0_body.get("offlineLease") or "")
        if not lease:
            raise RuntimeError("lesson/time did not return an offline lease")
        time.sleep(1.15)
        time1_ms, time1_status, time1_body = post_lesson_time(session, lesson, 1, 1, lease)
        if int(time1_body.get("acceptedSeconds", 0) or 0) != 1:
            raise RuntimeError(f"lesson/time did not credit one second: {time1_body}")

        lesson_after = lesson_time_row(db_path, USERNAME, lesson["lesson_id"])
        complete_before = lesson_progress_count(db_path, USERNAME)
        complete_fp_before = lesson_progress_fingerprint(db_path, USERNAME)
        complete_ms1, complete_status1, complete_body1 = post_complete(session, lesson, run_id)
        complete_ms2, complete_status2, complete_body2 = post_complete(session, lesson, run_id)
        if not complete_body2.get("deduplicated"):
            raise RuntimeError(f"lesson/complete exact retry was not deduplicated: {complete_body2}")
        complete_after = lesson_progress_count(db_path, USERNAME)
        complete_fp_after = lesson_progress_fingerprint(db_path, USERNAME)

        stop_pid(server2.pid)
        server1 = None
        server2 = None
        server3 = start_server(env)
        health3 = wait_health(server3.pid)
        session2, login_payload2, login_ms2 = login(password)
        me_payload2 = auth_me(session2)
        lesson_after_restart = lesson_time_row(db_path, USERNAME, lesson["lesson_id"])
        progress_after_restart = lesson_progress_count(db_path, USERNAME)
        progress_fp_after_restart = lesson_progress_fingerprint(db_path, USERNAME)

        stop_pid(server3.pid)
        server3 = None
        cleanup = cleanup_temp_user(server_data_root, db_path, USERNAME)
        qc = quick_check(db_path)
        port_after_shutdown = port_pid(18877)
        cleanup_remaining = cleanup.get("remaining", {}) if isinstance(cleanup.get("remaining"), dict) else {}

        summary = {
            "ok": qc.lower() == "ok" and port_after_shutdown == 0 and all(
                int(cleanup_remaining.get(key, 1) or 0) == 0 for key in ("lesson_time", "lesson_time_credit_state", "lesson_progress", "lesson_progress_namespaces", "append_events", "auth_sessions", "users")
            ) and not cleanup.get("user_file_exists") and not cleanup.get("user_folder_exists"),
            "run_id": run_id,
            "bootstrap_quick_check": bootstrap_quick_check,
            "probe1": probe1,
            "probe2": probe2,
            "seed": seed_info,
            "login_ms": round(login_ms, 3),
            "login_ms_after_restart": round(login_ms2, 3),
            "lesson": lesson,
            "lesson_time": {
                "before": lesson_before,
                "after": lesson_after,
                "after_restart": lesson_after_restart,
                "write0_ms": round(time0_ms, 3),
                "write1_ms": round(time1_ms, 3),
                "status0": time0_status,
                "status1": time1_status,
                "accepted_seconds": int(time1_body.get("acceptedSeconds", 0) or 0),
            },
            "lesson_progress": {
                "count_before": lesson_count_before,
                "count_before_complete": complete_before,
                "count_after_complete": complete_after,
                "count_after_restart": progress_after_restart,
                "fingerprint_before": progress_fp_before,
                "fingerprint_before_complete": complete_fp_before,
                "fingerprint_after_complete": complete_fp_after,
                "fingerprint_after_restart": progress_fp_after_restart,
            },
            "completion": {
                "status1": complete_status1,
                "status2": complete_status2,
                "body1": complete_body1,
                "body2": complete_body2,
                "retry_deduplicated": bool(complete_body2.get("deduplicated")),
                "post_restart_username": me_payload2.get("username", ""),
            },
            "auth": {
                "user": me_payload.get("username", ""),
                "user_after_restart": me_payload2.get("username", ""),
                "server_data_root": me_payload2.get("server_data", {}).get("root", ""),
                "load_test": me_payload2.get("server_data", {}).get("load_test", None),
            },
            "postgres_business_write_delta": 0,
            "quick_check": qc,
            "cleanup": cleanup,
            "cleanup_ok": qc.lower() == "ok",
            "port_18877_pid_after_shutdown": port_after_shutdown,
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        }
        summary["ok"] = bool(summary["ok"]) and bool(summary["completion"]["retry_deduplicated"]) and summary["auth"]["user_after_restart"] == USERNAME
        output_path = PLAN_DIR / "server2_sqlite_rollback_smoke_2026-07-26.json"
        output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary["ok"] else 2
    finally:
        if server1 and server1.poll() is None:
            stop_pid(server1.pid)
        if server2 and server2.poll() is None:
            stop_pid(server2.pid)
        if server3 and server3.poll() is None:
            stop_pid(server3.pid)
        try:
            if port_pid(18877):
                stop_pid(port_pid(18877))
        except Exception:
            pass
        shutil.rmtree(work_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
