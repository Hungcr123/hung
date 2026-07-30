"""Measure worst-case staggered session heartbeat persistence for 100 users."""

from __future__ import annotations

import json
import sqlite3
import time

import requests

from benchmark_auth_session_hot_path import AUTH_SESSION_PATH, session_document_state
from benchmark_server2_100_users import BASE, DATABASE, USERS, measured, response_sizes, server_process, wait_for_writer_quiescence


def persisted_sessions() -> dict[str, dict]:
    connection = sqlite3.connect(DATABASE)
    try:
        row = connection.execute(
            "SELECT content FROM documents WHERE lower(path)=lower(?)",
            (AUTH_SESSION_PATH,),
        ).fetchone()
    finally:
        connection.close()
    payload = json.loads(bytes(row[0]).decode("utf-8")) if row else {}
    source = payload.get("sessions") if isinstance(payload, dict) and isinstance(payload.get("sessions"), dict) else {}
    return {
        str(item.get("username", "")).lower(): {"token": token, **item}
        for token, item in source.items()
        if isinstance(item, dict) and str(item.get("username", "")).lower() in USERS
    }


def main() -> int:
    sessions = persisted_sessions()
    if len(sessions) != len(USERS):
        raise RuntimeError(f"Expected 100 persisted load sessions, found {len(sessions)}")
    newest_persisted = max(float(item.get("last_seen_persisted", 0) or 0) for item in sessions.values())
    wait_seconds = max(0.0, 60.5 - (time.time() - newest_persisted))
    if wait_seconds:
        print(f"WAITING {wait_seconds:.1f}s FOR STAGGERED SESSION WINDOW", flush=True)
        time.sleep(wait_seconds)
    process = server_process()
    wait_for_writer_quiescence()

    def run():
        rows = []
        for username in USERS:
            started = time.perf_counter()
            response = requests.get(
                f"{BASE}/auth/me",
                headers={"Authorization": f"Bearer {sessions[username]['token']}"},
                timeout=30,
            )
            decoded, wire, request_bytes = response_sizes(response)
            rows.append(((time.perf_counter() - started) * 1000, response.status_code, decoded, wire, request_bytes))
            time.sleep(0.2)
        return rows

    rows, metrics = measured(process, run)
    time.sleep(0.6)
    wait_for_writer_quiescence()
    print("AUTH_ME_SESSION_STAGGERED", json.dumps({**metrics, "session_document": session_document_state()}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
