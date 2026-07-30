"""Benchmark 100 unique chat sends and exact operation retries."""

from __future__ import annotations

import concurrent.futures
import json
import os
import sqlite3
import time
import uuid

import requests

from benchmark_server2_100_users import BASE, DATABASE, USERS, measured, response_sizes, server_process, wait_for_writer_quiescence


CHAT_PATH = r"C:\QMLearn\users\_future_chat_messages.json"


def chat_sqlite_active() -> bool:
    connection = sqlite3.connect(DATABASE)
    marker = connection.execute("SELECT value FROM database_meta WHERE key='chat_rows_v1'").fetchone()
    connection.close()
    return marker is not None


def chat_test_rows(run_id: str) -> dict:
    connection = sqlite3.connect(DATABASE)
    marker = connection.execute("SELECT value FROM database_meta WHERE key='chat_rows_v1'").fetchone()
    if marker is not None:
        raw_rows = connection.execute(
            "SELECT message_json,operation_id FROM chat_messages WHERE message_json LIKE ? ORDER BY id",
            (f"%{run_id}%",),
        ).fetchall()
        connection.close()
        rows = [json.loads(str(row[0])) for row in raw_rows]
        raw = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return {
            "rows": len(rows),
            "users": len({str(item.get("username", "")).lower() for item in rows}),
            "operations": len({str(row[1]) for row in raw_rows if row[1]}),
            "sha256": __import__("hashlib").sha256(raw).hexdigest(),
            "bytes": len(raw),
        }
    row = connection.execute("SELECT content,sha256,file_size FROM documents WHERE lower(path)=lower(?)", (CHAT_PATH,)).fetchone()
    connection.close()
    payload = json.loads(bytes(row[0]).decode("utf-8"))
    rows = [item for item in payload.get("messages", []) if isinstance(item, dict) and str(item.get("text", "")).startswith(run_id)]
    return {
        "rows": len(rows),
        "users": len({str(item.get("username", "")).lower() for item in rows}),
        "operations": len({str(item.get("operation_id", "")) for item in rows if item.get("operation_id")}),
        "sha256": str(row[1]),
        "bytes": int(row[2]),
    }


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active benchmark only")
    process = server_process()
    run_id = f"codex-chat-{uuid.uuid4().hex}"

    def login(username: str) -> str:
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if payload.get("server_data", {}).get("load_test") is not True:
            raise RuntimeError(f"Load-test isolation missing for {username}")
        return str(payload.get("token") or "")

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        tokens = dict(zip(USERS, pool.map(login, USERS)))
    operations = {username: f"{run_id}:{username}" for username in USERS}
    wait_for_writer_quiescence()

    def send(index: int):
        username = USERS[index]
        started = time.perf_counter()
        response = requests.post(
            f"{BASE}/chat/send",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            json={
                "text": f"{run_id} message {index:03d}",
                "language": "en",
                "audio_enabled": False,
                # Match the real frontend, which sends the selected voice even while audio is off.
                "voice": "male-us",
                "voice_label": "Male US",
                "operation_id": operations[username],
            },
            timeout=30,
        )
        decoded, wire, request_bytes = response_sizes(response)
        message = response.json().get("message", {})
        return (
            (time.perf_counter() - started) * 1000,
            response.status_code,
            decoded,
            wire,
            request_bytes,
            int(message.get("id", 0) or 0),
            str(message.get("operation_id", "")),
        )

    def phase(name: str):
        wait_for_writer_quiescence()

        def run():
            with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
                rows = list(pool.map(send, range(len(USERS))))
            if not chat_sqlite_active():
                time.sleep(2.6)
            return rows

        rows, metrics = measured(process, run)
        result = {**metrics, "unique_response_ids": len({row[5] for row in rows}), "document": chat_test_rows(run_id)}
        print(name, json.dumps(result, ensure_ascii=True), flush=True)
        return result

    unique = phase("UNIQUE_SEND")
    statuses = unique.get("statuses") or {}
    if int(statuses.get(200, statuses.get("200", 0)) or 0) != 100:
        print(json.dumps({"run_id": run_id, "error": "unique_send_failed", "document": unique["document"]}, ensure_ascii=True))
        return 2
    retry = phase("EXACT_RETRY")
    assert unique["document"]["rows"] >= 100 and unique["document"]["users"] == 100
    if unique["document"]["operations"]:
        assert retry["document"]["rows"] == unique["document"]["rows"] == 100
        assert retry["document"]["operations"] == 100
        assert retry["unique_response_ids"] == unique["unique_response_ids"] == 100
    print(json.dumps({"run_id": run_id, "unique": unique["document"], "retry": retry["document"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
