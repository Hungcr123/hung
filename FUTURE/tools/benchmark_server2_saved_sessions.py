"""Measure a hot Server 2 route with distinct already-authenticated users without exposing tokens."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sqlite3
import statistics
import time

import psutil
import requests


ROUTES = {
    "tree_preload": ("/server-data/tree-preload", lambda username: {}),
    "login_preload": ("/server-data/login-preload", lambda username: {"username": username}),
    "lesson_tasks": ("/lesson-tasks", lambda username: {"user": username}),
    "last_file": ("/server-data/last-file", lambda username: {}),
    "vocab_registry": ("/vocab/registry", lambda username: {}),
    "vocab_top_month": ("/vocab/leaderboard", lambda username: {"limit": "80", "scope": "month", "type": "space_v"}),
}


def server_process() -> psutil.Process:
    for process in psutil.process_iter(["name", "cmdline"]):
        cmdline = " ".join(process.info.get("cmdline") or [])
        if process.info.get("name", "").lower().startswith("python") and "FUTURE_SERVER_2.py" in cmdline:
            return process
    raise RuntimeError("Server 2 process not found")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8877")
    parser.add_argument("--route", choices=sorted(ROUTES), default="vocab_top_month")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--workers", type=int, default=20)
    args = parser.parse_args()

    connection = sqlite3.connect(r"C:\server data\server2.db")
    row = connection.execute(
        "SELECT content FROM documents WHERE path_key = ?",
        (r"c:\qmlearn\users\_future_auth_sessions.json",),
    ).fetchone()
    connection.close()
    payload = json.loads(bytes(row[0]).decode("utf-8")) if row and row[0] else {}
    saved = payload.get("sessions") if isinstance(payload, dict) and isinstance(payload.get("sessions"), dict) else {}
    sessions = []
    now = time.time()
    for token, row in saved.items():
        username = str(row.get("username", "") or "").strip() if isinstance(row, dict) else ""
        last_seen = float(row.get("last_seen", 0) or 0) if isinstance(row, dict) else 0.0
        if token and username and now - last_seen <= 86400:
            sessions.append((username, token))
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if password and not any(username.lower() == "hung" for username, _token in sessions):
        login = requests.post(
            f"{args.base}/auth/login",
            json={"username": "hung", "password": password},
            timeout=15,
        )
        login.raise_for_status()
        token = str(login.json().get("token", "") or "")
        if token:
            sessions.append(("hung", token))
    if len({username.lower() for username, _token in sessions}) < 2:
        raise RuntimeError("Need at least two distinct saved authenticated sessions")

    path, params_for = ROUTES[args.route]
    prepared = []
    for username, token in sessions:
        headers = {"Authorization": f"Bearer {token}"}
        params = params_for(username)
        warm = requests.get(f"{args.base}{path}", params=params, headers=headers, timeout=20)
        warm.raise_for_status()
        etag = warm.headers.get("ETag", "")
        if etag:
            headers["If-None-Match"] = etag
        prepared.append((username, params, headers))

    process = server_process()
    before = sum(process.cpu_times()[:2])
    started = time.perf_counter()

    def request_once(index: int):
        username, params, headers = prepared[index % len(prepared)]
        request_started = time.perf_counter()
        response = requests.get(f"{args.base}{path}", params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return username, response.status_code, len(response.content), (time.perf_counter() - request_started) * 1000

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        rows = list(pool.map(request_once, range(max(1, args.requests))))
    wall_ms = (time.perf_counter() - started) * 1000
    cpu_ms = max(0.0, (sum(process.cpu_times()[:2]) - before) * 1000)
    latencies = sorted(row[3] for row in rows)
    print(
        args.route,
        {
            "distinct_users": len({row[0].lower() for row in rows}),
            "requests": len(rows),
            "workers": args.workers,
            "server_cpu_ms_per_request": round(cpu_ms / len(rows), 3),
            "wall_ms": round(wall_ms, 3),
            "p50_ms": round(statistics.median(latencies), 3),
            "p95_ms": round(latencies[max(0, int(len(latencies) * 0.95) - 1)], 3),
            "response_bytes": sum(row[2] for row in rows),
            "statuses": {status: sum(1 for row in rows if row[1] == status) for status in sorted({row[1] for row in rows})},
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
