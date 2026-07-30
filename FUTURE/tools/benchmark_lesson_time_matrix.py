"""Benchmark /lesson/time protocol phases with 100 isolated users and paths."""

from __future__ import annotations

import concurrent.futures
import json
import os
import sqlite3
import time
import uuid

import requests

from benchmark_server2_100_users import (
    BASE,
    DATABASE,
    USERS,
    lesson_paths,
    measured,
    response_sizes,
    server_process,
    wait_for_writer_quiescence,
)


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active benchmark only")
    paths = lesson_paths()
    process = server_process()
    connection = sqlite3.connect(DATABASE)
    aliases = {
        str(row[0]).lower(): str(row[1] or "")
        for row in connection.execute("SELECT normalized_path,file_id FROM lesson_file_aliases WHERE active=1")
    }
    connection.close()
    lesson_ids = [aliases.get(path.lower(), "") for path in paths]
    if not all(value.lower().startswith("ftg-lesson-") for value in lesson_ids):
        raise RuntimeError("Lesson-time benchmark requires 100 active canonical lesson IDs")

    def login(username: str) -> str:
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if payload.get("server_data", {}).get("load_test") is not True:
            raise RuntimeError(f"Load-test isolation missing for {username}")
        return str(payload.get("token") or "")

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        tokens = dict(zip(USERS, pool.map(login, USERS)))
    sessions = {username: f"lesson-matrix-{uuid.uuid4().hex}" for username in USERS}
    wait_for_writer_quiescence()

    def request(index: int, sequence: int, seconds: int, lease: str = "", offline: bool = False):
        username = USERS[index]
        payload = {
            "path": paths[index],
            "lesson_id": lesson_ids[index],
            "space": "Space_V",
            "seconds": seconds,
            "protocol": "server-time-v1",
            "session_id": sessions[username],
            "sequence": sequence,
            "offline_lease": lease,
        }
        if offline:
            payload["offline_claims"] = [{"sequence": sequence, "seconds": seconds}]
            payload["seconds"] = 0
        started = time.perf_counter()
        response = requests.post(
            f"{BASE}/lesson/time",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        decoded, wire, request_bytes = response_sizes(response)
        row = response.json().get("time", {})
        return (
            (time.perf_counter() - started) * 1000,
            response.status_code,
            decoded,
            wire,
            request_bytes,
            str(row.get("heartbeatReason") or ""),
            int(row.get("acceptedSeconds", 0) or 0),
            str(row.get("offlineLease") or ""),
        )

    def phase(name: str, callback):
        wait_for_writer_quiescence()
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
            rows, metrics = measured(process, lambda: list(pool.map(callback, range(len(USERS)))))
        reasons = {reason: sum(1 for row in rows if row[5] == reason) for reason in sorted({row[5] for row in rows})}
        result = {**metrics, "accepted_seconds": sum(row[6] for row in rows), "reasons": reasons}
        print(name, json.dumps(result, ensure_ascii=True), flush=True)
        return rows, result

    start_rows, start_metrics = phase("START", lambda index: request(index, 0, 0))
    leases = [row[7] for row in start_rows]
    if not all(leases) or start_metrics["reasons"] != {"session_started": 100}:
        raise RuntimeError("Session start did not return 100 signed leases")

    _, replay_start_metrics = phase("REPLAY_START_RAM", lambda index: request(index, 0, 0, leases[index]))
    time.sleep(1.15)
    _, accepted_metrics = phase("ACCEPTED", lambda index: request(index, 1, 1, leases[index]))
    _, replay_metrics = phase("REPLAY_RAM", lambda index: request(index, 1, 1, leases[index]))
    _, stale_metrics = phase("STALE_RAM", lambda index: request(index, 0, 1, leases[index]))
    time.sleep(1.15)
    _, offline_metrics = phase("OFFLINE_UNIQUE", lambda index: request(index, 2, 1, leases[index], True))
    _, offline_retry_metrics = phase("OFFLINE_RETRY_DB", lambda index: request(index, 2, 1, leases[index], True))

    connection = sqlite3.connect(DATABASE)
    placeholders = ",".join("?" for _ in USERS)
    time_rows = connection.execute(
        f"SELECT COUNT(*),COALESCE(SUM(seconds),0),COALESCE(SUM(ticks),0) FROM lesson_time WHERE username IN ({placeholders})",
        USERS,
    ).fetchone()
    credit_rows = connection.execute(
        f"SELECT COUNT(*) FROM lesson_time_credit_state WHERE username IN ({placeholders})",
        USERS,
    ).fetchone()[0]
    connection.close()
    expected_accepted = accepted_metrics["accepted_seconds"] + offline_metrics["accepted_seconds"]
    assert tuple(map(int, time_rows)) == (100, expected_accepted, expected_accepted), time_rows
    assert int(credit_rows) == 100, credit_rows
    assert accepted_metrics["accepted_seconds"] == 100
    assert offline_metrics["accepted_seconds"] == 100
    for metrics in (replay_start_metrics, replay_metrics, stale_metrics, offline_retry_metrics):
        assert metrics["accepted_seconds"] == 0, metrics
    assert int(offline_retry_metrics["postgres_writer"]["tasks"]) == 0, offline_retry_metrics
    print(json.dumps({"rows": tuple(map(int, time_rows)), "credit_rows": int(credit_rows), "isolated_users": 100}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

