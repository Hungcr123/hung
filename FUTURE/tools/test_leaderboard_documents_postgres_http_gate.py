#!/usr/bin/env python3
"""HTTP runtime/shadow gate for selected leaderboard documents."""

from __future__ import annotations

import hashlib
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
import FUTURE.tools.migrate_leaderboard_documents_to_postgres as migrate_docs  # noqa: E402

DATABASE = Path(r"C:\server data\server2.db")
BASE = "http://127.0.0.1:18877"
PRODUCTION_BASE = "http://127.0.0.1:8877"
USER_PREFIX = "codexpgdocs"
USERNAME = f"{USER_PREFIX}{secrets.token_hex(3)}"


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


def compact_health(base: str = BASE, timeout: float = 5.0) -> dict:
    payload = health(base, timeout)
    writer = payload.get("sqlite_writer") if isinstance(payload.get("sqlite_writer"), dict) else {}
    return {
        "ok": bool(payload.get("ok")),
        "pid": int(payload.get("pid", 0) or 0),
        "writer_queue": int(writer.get("queue_depth", 0) or 0),
        "server_time": str(payload.get("server_time", "")),
    }


def wait_health(pid: int = 0, timeout: float = 90.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            payload = health(BASE, 3)
            if payload.get("ok") and (not pid or int(payload.get("pid", 0) or 0) == pid):
                return
        except Exception:
            pass
        time.sleep(0.4)
    raise RuntimeError("Test Server 2 process did not become healthy")


def start_test_server() -> subprocess.Popen:
    env = dict(os.environ)
    env["FUTURE_DB_LEADERBOARD_DOCUMENTS_BACKEND"] = "postgres"
    env["FUTURE_DB_VOCABULARY_BACKEND"] = "postgres"
    env["FUTURE_DB_APPEND_EVENTS_BACKEND"] = "postgres"
    env["FUTURE_DB_LESSON_PROGRESS_BACKEND"] = "postgres"
    return subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--host", "127.0.0.1", "--port", "18877", "--no-browser", "--no-tunnel"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def sqlite_snapshot() -> list[dict]:
    return migrate_docs.sqlite_rows()


def restore_sqlite(rows: list[dict]) -> None:
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        con.execute("BEGIN IMMEDIATE")
        keys = [row["path_key"] for row in rows]
        con.executemany("DELETE FROM documents WHERE path_key=?", [(key,) for key in keys])
        for row in rows:
            con.execute(
                "INSERT INTO documents(path_key,path,content,encoding,sha256,file_size,file_mtime_ns,updated_at_utc) VALUES(?,?,?,?,?,?,?,?)",
                (
                    row["path_key"],
                    row["path"],
                    bytes(row["content"] or b""),
                    row["encoding"],
                    row["sha256"],
                    row["file_size"],
                    row["file_mtime_ns"],
                    row["updated_at_utc"],
                ),
            )
        con.execute("DELETE FROM users WHERE lower(username) LIKE ?", (f"{USER_PREFIX}%",))
        con.execute("DELETE FROM documents WHERE lower(path) LIKE ?", (f"%{USER_PREFIX}%",))
        con.commit()
    finally:
        con.close()
    try:
        for path in app.USER_ROOT.glob(f"{USER_PREFIX}*.txt"):
            path.unlink(missing_ok=True)
    except Exception:
        pass


def restore_postgres(rows: list[dict]) -> None:
    migrate_docs.cleanup_test_rows()
    for row in rows:
        app.postgres_upsert_document_row(row)


def provision_user(password: str) -> None:
    now = app.utc_timestamp()
    app.write_user_lines(USERNAME, [f"{USERNAME}:{app.password_hash(password)}"])
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute("DELETE FROM users WHERE lower(username) LIKE ?", (f"{USER_PREFIX}%",))
        con.execute(
            "INSERT INTO users(username,is_admin,is_test,profile_json,updated_at_utc) VALUES(?,?,?,?,?)",
            (USERNAME, 1, 0, "{}", now),
        )
        con.commit()
    finally:
        con.close()


def login(password: str) -> str:
    deadline = time.monotonic() + 45
    last = ""
    while time.monotonic() < deadline:
        try:
            response = requests.post(f"{BASE}/auth/login", json={"username": USERNAME, "password": password}, timeout=10)
            last = f"{response.status_code} {response.text[:160]}"
            if response.status_code == 200:
                token = response.json().get("token")
                if token:
                    return token
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(0.5)
    raise RuntimeError(f"Login did not return token: {last}")


def request_json(method: str, path: str, token: str, **kwargs) -> dict:
    started = time.perf_counter()
    response = requests.request(method, f"{BASE}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=60, **kwargs)
    elapsed = (time.perf_counter() - started) * 1000
    payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else json.loads(response.text or "{}")
    return {"status": response.status_code, "ms": round(elapsed, 3), "ok": bool(payload.get("ok")), "keys": sorted(payload.keys())[:12]}


def shadow_compare() -> dict:
    sqlite_rows = sqlite_snapshot()
    pg_rows = migrate_docs.pg_rows()
    keys = {row["path_key"] for row in sqlite_rows}
    pg_subset = [row for row in pg_rows if row["path_key"] in keys]
    return {
        "sqlite_rows": len(sqlite_rows),
        "postgres_total": len(pg_rows),
        "postgres_matching": len(pg_subset),
        "sqlite_fingerprint": migrate_docs.fingerprint(sqlite_rows),
        "postgres_fingerprint": migrate_docs.fingerprint(pg_subset),
        "ok": len(sqlite_rows) == len(pg_subset) and migrate_docs.fingerprint(sqlite_rows) == migrate_docs.fingerprint(pg_subset),
    }


def main() -> int:
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("FUTURE_PG_DSN is required")
    if server_pid_on_port(18877):
        raise RuntimeError("Port 18877 already has a listener")
    app.postgres_initialize_schema()
    original_rows = sqlite_snapshot()
    original_pid_file = app.SERVER_PID_FILE.read_text(encoding="utf-8") if app.SERVER_PID_FILE.is_file() else None
    process: subprocess.Popen | None = None
    result: dict = {}
    password = secrets.token_urlsafe(32)
    try:
        restore_postgres(original_rows)
        provision_user(password)
        process = start_test_server()
        wait_health(pid=int(process.pid))
        token = login(password)
        calls = [
            request_json("GET", "/vocab/leaderboard?limit=10&scope=total&type=space_v", token),
            request_json("GET", "/vocab/leaderboard?limit=10&scope=month&type=space_w", token),
            request_json("GET", "/vocab/leaderboard/chat?limit=10", token),
            request_json("POST", "/vocab/leaderboard/status", token, json={"scope": "total", "status": "codexpgdocs-shadow"}),
        ]
        time.sleep(3.0)
        before_restart = shadow_compare()
        stop_pid(int(process.pid))
        process = start_test_server()
        wait_health(pid=int(process.pid))
        token = login(password)
        restart_call = request_json("GET", "/vocab/leaderboard?limit=10&scope=total&type=space_v", token)
        time.sleep(3.0)
        after_restart = shadow_compare()
        result = {
            "leaderboard_documents_postgres_http_gate": "ok",
            "feature_flag": "FUTURE_DB_LEADERBOARD_DOCUMENTS_BACKEND",
            "calls": calls,
            "shadow_before_restart": before_restart,
            "restart_call": restart_call,
            "shadow_after_restart": after_restart,
            "production_health": compact_health(PRODUCTION_BASE, 10),
            "production_flag": os.environ.get("FUTURE_DB_LEADERBOARD_DOCUMENTS_BACKEND", "off") or "off",
        }
        if any(call["status"] != 200 or not call["ok"] for call in calls + [restart_call]):
            raise RuntimeError({"reason": "HTTP call failed", **result})
        if not before_restart.get("ok") or not after_restart.get("ok"):
            raise RuntimeError({"reason": "shadow mismatch", **result})
        print(json.dumps(result, ensure_ascii=True, indent=2, default=str))
        return 0
    finally:
        if process is not None:
            stop_pid(int(process.pid))
        restore_sqlite(original_rows)
        restore_postgres(original_rows)
        if original_pid_file is None:
            app.SERVER_PID_FILE.unlink(missing_ok=True)
        else:
            app.SERVER_PID_FILE.write_text(original_pid_file, encoding="utf-8")
        cleanup = {
            "shadow": shadow_compare(),
            "port_18877_busy": bool(server_pid_on_port(18877)),
        }
        print(json.dumps({"cleanup": cleanup}, ensure_ascii=True, indent=2, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
