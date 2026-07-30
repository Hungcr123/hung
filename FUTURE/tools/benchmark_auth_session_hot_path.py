"""Benchmark 100-user login, auth-me cache, and periodic session persistence."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import sqlite3
import time

import requests

from benchmark_server2_100_users import BASE, DATABASE, USERS, measured, response_sizes, server_process, wait_for_writer_quiescence


AUTH_SESSION_PATH = r"C:\QMLearn\users\_future_auth_sessions.json"


def session_document_state() -> dict:
    connection = sqlite3.connect(DATABASE)
    try:
        table = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='auth_sessions'").fetchone()
        marker = connection.execute("SELECT value FROM database_meta WHERE key='auth_session_rows_v1'").fetchone() if table else None
        if marker is not None:
            rows = connection.execute(
                "SELECT token_hash,username,created_epoch,last_seen_epoch,last_persisted_epoch,expires_epoch FROM auth_sessions ORDER BY username"
            ).fetchall()
            raw_rows = json.dumps(rows, separators=(",", ":")).encode("utf-8")
            connection.close()
            return {
                "authority": "auth_sessions",
                "sessions": len(rows),
                "test_sessions": sum(1 for row in rows if str(row[1]).lower().startswith("codexload")),
                "bytes": len(raw_rows),
                "sha256": hashlib.sha256(raw_rows).hexdigest(),
                "updated_at": "sqlite-rows",
            }
        row = connection.execute(
            "SELECT content,file_size,sha256,updated_at_utc FROM documents WHERE lower(path)=lower(?)",
            (AUTH_SESSION_PATH,),
        ).fetchone()
    finally:
        try:
            connection.close()
        except Exception:
            pass
    if row is None:
        return {"authority": "document", "sessions": 0, "bytes": 0, "sha256": "", "updated_at": ""}
    raw = bytes(row[0])
    payload = json.loads(raw.decode("utf-8"))
    sessions = payload.get("sessions") if isinstance(payload, dict) and isinstance(payload.get("sessions"), dict) else {}
    return {
        "authority": "document",
        "sessions": len(sessions),
        "test_sessions": sum(1 for item in sessions.values() if isinstance(item, dict) and str(item.get("username", "")).lower().startswith("codexload")),
        "bytes": int(row[1] or len(raw)),
        "sha256": str(row[2] or hashlib.sha256(raw).hexdigest()),
        "updated_at": str(row[3] or ""),
    }


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this benchmark only")
    process = server_process()
    tokens: dict[str, str] = {}

    def login(index: int):
        username = USERS[index]
        body = json.dumps({"username": username, "password": password}, separators=(",", ":")).encode("utf-8")
        started = time.perf_counter()
        response = requests.post(f"{BASE}/auth/login", data=body, headers={"Content-Type": "application/json"}, timeout=30)
        decoded, wire, request_bytes = response_sizes(response)
        payload = response.json()
        token = str(payload.get("token") or "")
        if response.ok and token:
            tokens[username] = token
        return ((time.perf_counter() - started) * 1000, response.status_code, decoded, wire, request_bytes, token)

    def auth_me(index: int):
        username = USERS[index]
        started = time.perf_counter()
        response = requests.get(
            f"{BASE}/auth/me",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            timeout=30,
        )
        decoded, wire, request_bytes = response_sizes(response)
        payload = response.json()
        return (
            (time.perf_counter() - started) * 1000,
            response.status_code,
            decoded,
            wire,
            request_bytes,
            str(payload.get("username") or ""),
        )

    def phase(name: str, callback, settle: float = 0.0):
        wait_for_writer_quiescence()

        def run():
            with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
                return list(pool.map(callback, range(len(USERS))))

        rows, metrics = measured(process, run)
        background_settle = None
        if settle:
            writer_before = requests.get(f"{BASE}/health", timeout=10).json().get("postgres_writer", {})
            cpu_before = sum(process.cpu_times()[:2])
            io_before = process.io_counters()
            time.sleep(settle)
            wait_for_writer_quiescence()
            writer_after = requests.get(f"{BASE}/health", timeout=10).json().get("postgres_writer", {})
            io_after = process.io_counters()
            background_settle = {
                "server_cpu_ms": round(max(0.0, sum(process.cpu_times()[:2]) - cpu_before) * 1000, 3),
                "postgres_writer": {
                    key: round(float(writer_after.get(key, 0) or 0) - float(writer_before.get(key, 0) or 0), 3)
                    for key in ("batches", "tasks", "queue_wait_ms", "begin_wait_ms", "commit_ms", "busy_errors")
                },
                "process_io": {
                    "read_ops": max(0, int(io_after.read_count - io_before.read_count)),
                    "write_ops": max(0, int(io_after.write_count - io_before.write_count)),
                    "read_bytes": max(0, int(io_after.read_bytes - io_before.read_bytes)),
                    "write_bytes": max(0, int(io_after.write_bytes - io_before.write_bytes)),
                },
            }
        result = {**metrics, "background_settle": background_settle, "session_document": session_document_state()}
        print(name, json.dumps(result, ensure_ascii=True), flush=True)
        return result

    login_result = phase("LOGIN", login, settle=0.6)
    if len(tokens) != len(USERS):
        raise RuntimeError(f"Only {len(tokens)} load users logged in")
    if os.environ.get("AUTH_SESSION_LOGIN_ONLY") == "1":
        print(json.dumps({"login": login_result["session_document"]}, ensure_ascii=True))
        return 0
    if os.environ.get("AUTH_SESSION_SIMULTANEOUS_ONLY") == "1":
        print("WAITING_FOR_SESSION_PERSIST_INTERVAL", flush=True)
        time.sleep(60.5)
        refresh = phase("AUTH_ME_SESSION_REFRESH", auth_me, settle=5.4)
        print(json.dumps({"refresh": refresh["session_document"]}, ensure_ascii=True))
        return 0
    first = phase("AUTH_ME_FIRST", auth_me)
    repeat = phase("AUTH_ME_REPEAT", auth_me)
    print("WAITING_FOR_SESSION_PERSIST_INTERVAL", flush=True)
    time.sleep(60.5)
    refresh = phase("AUTH_ME_SESSION_REFRESH", auth_me, settle=5.4)
    staggered = None
    if os.environ.get("AUTH_SESSION_INCLUDE_STAGGERED") == "1":
        print("WAITING_FOR_STAGGERED_SESSION_PERSIST_INTERVAL", flush=True)
        time.sleep(60.5)
        wait_for_writer_quiescence()

        def run_staggered():
            rows = []
            for index in range(len(USERS)):
                rows.append(auth_me(index))
                time.sleep(0.2)
            return rows

        rows, metrics = measured(process, run_staggered)
        time.sleep(5.4)
        wait_for_writer_quiescence()
        staggered = {**metrics, "session_document": session_document_state()}
        print("AUTH_ME_SESSION_STAGGERED", json.dumps(staggered, ensure_ascii=True), flush=True)
    print(json.dumps({
        "login": login_result["session_document"],
        "first": first["session_document"],
        "repeat": repeat["session_document"],
        "refresh": refresh["session_document"],
        "staggered": staggered["session_document"] if staggered else None,
    }, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

