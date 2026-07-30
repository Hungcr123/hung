"""Benchmark closed/open unchanged chat polling with 100 isolated users."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import sqlite3
import time

import requests

from benchmark_server2_100_users import BASE, DATABASE, USERS, measured, response_sizes, server_process, wait_for_writer_quiescence


CHAT_PATH = r"C:\QMLearn\users\_future_chat_messages.json"


def chat_document() -> dict:
    connection = sqlite3.connect(DATABASE)
    chat_table = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='chat_messages'").fetchone()
    marker = connection.execute("SELECT value FROM database_meta WHERE key='chat_rows_v1'").fetchone() if chat_table else None
    if marker is not None:
        message_rows = connection.execute("SELECT id,message_json FROM chat_messages ORDER BY id").fetchall()
        read_rows = connection.execute("SELECT username,admin_read,user_read FROM chat_read_state ORDER BY username COLLATE NOCASE").fetchall()
        connection.close()
        raw = json.dumps({"messages": message_rows, "read": read_rows}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "updated_at": "sqlite-rows",
            "messages": len(message_rows),
            "admin_read": sum(1 for row in read_rows if int(row[1] or 0) > 0),
            "user_read": sum(1 for row in read_rows if int(row[2] or 0) > 0),
        }
    row = connection.execute(
        "SELECT content,sha256,file_size,updated_at_utc FROM documents WHERE lower(path)=lower(?)",
        (CHAT_PATH,),
    ).fetchone()
    connection.close()
    if row is None:
        raise RuntimeError("Chat document is missing")
    raw = bytes(row[0])
    payload = json.loads(raw.decode("utf-8"))
    return {
        "sha256": str(row[1]),
        "bytes": int(row[2]),
        "updated_at": str(row[3]),
        "messages": len(payload.get("messages") or []),
        "admin_read": len(payload.get("admin_read") or {}),
        "user_read": len(payload.get("user_read") or {}),
    }


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active benchmark only")
    process = server_process()

    def login(username: str) -> str:
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if payload.get("server_data", {}).get("load_test") is not True:
            raise RuntimeError(f"Load-test isolation missing for {username}")
        return str(payload.get("token") or "")

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        tokens = dict(zip(USERS, pool.map(login, USERS)))
    wait_for_writer_quiescence()
    before_document = chat_document()

    def poll(index: int, opened: bool):
        started = time.perf_counter()
        response = requests.get(
            f"{BASE}/chat/poll",
            headers={"Authorization": f"Bearer {tokens[USERS[index]]}"},
            params={"since": 2_147_483_647, "open": "1" if opened else "0", "notice_after": 2_147_483_647},
            timeout=30,
        )
        response.raise_for_status()
        decoded, wire, request_bytes = response_sizes(response)
        payload = response.json()
        return (
            (time.perf_counter() - started) * 1000,
            response.status_code,
            decoded,
            wire,
            request_bytes,
            len(payload.get("messages") or []),
            int(payload.get("unread", 0) or 0),
        )

    def phase(name: str, opened: bool, settle: float = 0.0):
        wait_for_writer_quiescence()

        def run():
            with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
                rows = list(pool.map(lambda index: poll(index, opened), range(len(USERS))))
            return rows

        rows, metrics = measured(process, run)
        if settle > 0:
            time.sleep(settle)
        result = {
            **metrics,
            "messages": sum(row[5] for row in rows),
            "unread": sum(row[6] for row in rows),
            "document": chat_document(),
        }
        print(name, json.dumps(result, ensure_ascii=True), flush=True)
        return result

    closed = phase("CLOSED_UNCHANGED", False)
    open_first = phase("OPEN_FIRST", True, 2.6)
    open_repeat = phase("OPEN_REPEAT_UNCHANGED", True, 2.6)
    assert closed["messages"] == open_first["messages"] == open_repeat["messages"] == 0
    print(json.dumps({"before": before_document, "after": chat_document()}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
