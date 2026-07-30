"""Verify one direct IPv4 Gemini call does not serialize normal Server 2 routes."""

from __future__ import annotations

import concurrent.futures
import json
import os
import sqlite3
import threading
import time
import uuid

import requests

from benchmark_server2_100_users import BASE, DATABASE, USERS, lesson_paths


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this benchmark only")
    paths = lesson_paths()
    connection = sqlite3.connect(DATABASE)
    aliases = {str(row[0]).lower(): str(row[1] or "") for row in connection.execute(
        "SELECT normalized_path,file_id FROM lesson_file_aliases WHERE active=1"
    )}
    connection.close()

    selected = USERS[:31]

    def login(username: str) -> str:
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        return str(response.json().get("token") or "")

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        tokens = dict(zip(selected, pool.map(login, selected)))

    time_users = USERS[21:31]
    time_sessions = {username: f"gemini-concurrency-{uuid.uuid4().hex}" for username in time_users}
    leases: dict[str, str] = {}
    for offset, username in enumerate(time_users, 21):
        response = requests.post(
            f"{BASE}/lesson/time",
            headers={"Authorization": f"Bearer {tokens[username]}"},
            json={
                "path": paths[offset],
                "lesson_id": aliases.get(paths[offset].lower(), ""),
                "space": "Space_V",
                "seconds": 0,
                "protocol": "server-time-v1",
                "session_id": time_sessions[username],
                "sequence": 0,
            },
            timeout=30,
        )
        response.raise_for_status()
        leases[username] = str(response.json().get("time", {}).get("offlineLease") or "")
    if not all(leases.values()):
        raise RuntimeError("Concurrent time sessions did not receive leases")
    time.sleep(1.15)

    stop_sample = threading.Event()
    samples: list[dict] = []

    def sample_writer() -> None:
        while not stop_sample.wait(0.02):
            try:
                writer = requests.get(f"{BASE}/health?view=dashboard-v1", timeout=3).json().get("sqlite_writer", {})
                samples.append({
                    "depth": int(writer.get("queue_depth", 0) or 0),
                    "active": str(writer.get("active_source") or ""),
                })
            except Exception:
                pass

    def gemini_request() -> tuple[int, float, str]:
        started = time.perf_counter()
        response = requests.post(
            f"{BASE}/pdf/agent-explain",
            headers={"Authorization": f"Bearer {tokens[USERS[0]]}"},
            json={
                "question": f"Explain the main idea briefly. Probe {uuid.uuid4().hex}.",
                "text": "Learning remains reliable when independent services do not block each other.",
                "title": "Gemini IPv4 concurrency probe",
                "path": "common/concurrency-probe.pdf",
                "page": 1,
            },
            timeout=90,
        )
        elapsed = (time.perf_counter() - started) * 1000
        model = ""
        try:
            model = str(response.json().get("model") or "")
        except Exception:
            pass
        return response.status_code, elapsed, model

    def route_request(index: int) -> tuple[str, int, float, int]:
        started = time.perf_counter()
        if index < 5:
            username = USERS[1 + index]
            response = requests.get(
                f"{BASE}/server-data/tree-preload",
                headers={"Authorization": f"Bearer {tokens[username]}"},
                timeout=30,
            )
            kind = "tree"
            accepted = 0
        elif index < 10:
            username = USERS[6 + index - 5]
            path = paths[6 + index - 5]
            response = requests.get(
                f"{BASE}/space-v/progress",
                headers={"Authorization": f"Bearer {tokens[username]}"},
                params={"path": path, "identity": aliases.get(path.lower(), "")},
                timeout=30,
            )
            kind = "progress"
            accepted = 0
        else:
            offset = 21 + index - 10
            username = USERS[offset]
            path = paths[offset]
            response = requests.post(
                f"{BASE}/lesson/time",
                headers={"Authorization": f"Bearer {tokens[username]}"},
                json={
                    "path": path,
                    "lesson_id": aliases.get(path.lower(), ""),
                    "space": "Space_V",
                    "seconds": 1,
                    "protocol": "server-time-v1",
                    "session_id": time_sessions[username],
                    "sequence": 1,
                    "offline_lease": leases[username],
                },
                timeout=30,
            )
            kind = "time"
            accepted = int(response.json().get("time", {}).get("acceptedSeconds", 0) or 0)
        return kind, response.status_code, (time.perf_counter() - started) * 1000, accepted

    sampler = threading.Thread(target=sample_writer, daemon=True)
    sampler.start()
    with concurrent.futures.ThreadPoolExecutor(max_workers=21) as pool:
        gemini_future = pool.submit(gemini_request)
        time.sleep(0.05)
        route_rows = list(pool.map(route_request, range(20)))
        gemini_row = gemini_future.result()
    stop_sample.set()
    sampler.join(timeout=2)

    grouped = {}
    for kind in ("tree", "progress", "time"):
        values = [row[2] for row in route_rows if row[0] == kind]
        grouped[kind] = {
            "requests": len(values),
            "max_ms": round(max(values, default=0), 3),
            "status_200": sum(1 for row in route_rows if row[0] == kind and row[1] == 200),
            "accepted_seconds": sum(row[3] for row in route_rows if row[0] == kind),
        }
    result = {
        "gemini": {"status": gemini_row[0], "latency_ms": round(gemini_row[1], 3), "model": gemini_row[2]},
        "routes": grouped,
        "writer": {
            "max_depth": max((row["depth"] for row in samples), default=0),
            "gemini_active_source_seen": any("gemini" in row["active"].lower() for row in samples),
            "samples": len(samples),
        },
    }
    assert gemini_row[0] == 200, result
    assert all(grouped[kind]["status_200"] == grouped[kind]["requests"] for kind in grouped), result
    assert grouped["time"]["accepted_seconds"] == 10, result
    assert result["writer"]["gemini_active_source_seen"] is False, result
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
