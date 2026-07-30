"""Measure authenticated Server 2 hot-route wall time, bytes, cache status, and process CPU."""

from __future__ import annotations

import argparse
import concurrent.futures
import os
import statistics
import time

import psutil
import requests


ROUTES = {
    "tree_preload": ("/server-data/tree-preload", {}),
    "login_preload": ("/server-data/login-preload", {"username": "{username}"}),
    "settings": ("/settings", {}),
    "announcements": ("/announcements", {}),
    "lesson_tasks": ("/lesson-tasks", {"user": "{username}"}),
    "last_file": ("/server-data/last-file", {}),
    "vocab_registry": ("/vocab/registry", {}),
    "vocab_top_month": ("/vocab/leaderboard", {"limit": "80", "double_check": "0", "scope": "month", "type": "space_v"}),
}


def server_process() -> psutil.Process:
    for process in psutil.process_iter(["name", "cmdline"]):
        cmdline = " ".join(process.info.get("cmdline") or [])
        if process.info.get("name", "").lower().startswith("python") and "FUTURE_SERVER_2.py" in cmdline:
            return process
    raise RuntimeError("Server 2 process not found")


def process_cpu_seconds(process: psutil.Process) -> float:
    row = process.cpu_times()
    return float(row.user + row.system)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8877")
    parser.add_argument("--username", default="hung")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--no-etag", action="store_true")
    parser.add_argument("--skip-warm", action="store_true")
    parser.add_argument("--route", action="append", choices=sorted(ROUTES))
    args = parser.parse_args()
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active benchmark only")

    login = requests.post(
        f"{args.base}/auth/login",
        json={"username": args.username, "password": password},
        timeout=15,
    )
    login.raise_for_status()
    token = login.json().get("token", "")
    if not token:
        raise RuntimeError("Login response did not contain a token")
    auth_headers = {"Authorization": f"Bearer {token}"}
    process = server_process()

    selected = args.route or list(ROUTES)
    for name in selected:
        path, raw_params = ROUTES[name]
        params = {key: value.format(username=args.username) for key, value in raw_params.items()}
        etag = ""
        if not args.skip_warm:
            warm = requests.get(f"{args.base}{path}", params=params, headers=auth_headers, timeout=20)
            warm.raise_for_status()
            etag = warm.headers.get("ETag", "")
        headers = dict(auth_headers)
        if etag and not args.no_etag:
            headers["If-None-Match"] = etag

        def request_once(_index: int) -> tuple[float, int, int, str]:
            started = time.perf_counter()
            response = requests.get(f"{args.base}{path}", params=params, headers=headers, timeout=30)
            elapsed_ms = (time.perf_counter() - started) * 1000
            response.raise_for_status()
            return elapsed_ms, response.status_code, len(response.content), response.headers.get("X-Future-Cache-Hit", "")

        cpu_before = process_cpu_seconds(process)
        wall_started = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            rows = list(executor.map(request_once, range(max(1, args.requests))))
        wall_ms = (time.perf_counter() - wall_started) * 1000
        cpu_ms = max(0.0, (process_cpu_seconds(process) - cpu_before) * 1000)
        latencies = [row[0] for row in rows]
        statuses: dict[int, int] = {}
        cache_headers: dict[str, int] = {}
        for _latency, status, _size, cache_header in rows:
            statuses[status] = statuses.get(status, 0) + 1
            cache_headers[cache_header or "-"] = cache_headers.get(cache_header or "-", 0) + 1
        print(
            name,
            {
                "requests": len(rows),
                "workers": args.workers,
                "wall_ms": round(wall_ms, 3),
                "server_cpu_ms": round(cpu_ms, 3),
                "cpu_ms_per_request": round(cpu_ms / len(rows), 3),
                "latency_p50_ms": round(statistics.median(latencies), 3),
                "latency_p95_ms": round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 3),
                "response_bytes": sum(row[2] for row in rows),
                "statuses": statuses,
                "cache": cache_headers,
                "etag": bool(etag),
            },
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
