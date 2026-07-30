"""Measure cached full-body and ETag tree preload responses for 100 isolated users."""

from __future__ import annotations

import concurrent.futures
import json
import os
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE.tools.benchmark_server2_100_users import (  # noqa: E402
    BASE,
    USERS,
    measured,
    response_sizes,
    server_process,
    wait_for_writer_quiescence,
)


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active benchmark only")

    def login(username: str) -> tuple[str, str]:
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        return username, str(response.json().get("token") or "")

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        tokens = dict(pool.map(login, USERS))
    time.sleep(3.5)
    wait_for_writer_quiescence()
    process = server_process()

    def tree_request(index: int, etag: str = ""):
        username = USERS[index]
        headers = {
            "Authorization": f"Bearer {tokens[username]}",
            "Accept-Encoding": "gzip",
        }
        if etag:
            headers["If-None-Match"] = etag
        started = time.perf_counter()
        response = requests.get(f"{BASE}/server-data/tree-preload", headers=headers, timeout=30)
        if response.status_code not in {200, 304}:
            response.raise_for_status()
        decoded, wire, request_bytes = response_sizes(response)
        return (
            (time.perf_counter() - started) * 1000,
            response.status_code,
            decoded,
            wire,
            request_bytes,
            str(response.headers.get("ETag") or ""),
            str(response.headers.get("X-Future-Cache-Hit") or ""),
            str(response.headers.get("Server-Timing") or ""),
        )

    def parallel(indices, etag: str = ""):
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as pool:
            return list(pool.map(lambda index: tree_request(index, etag), indices))

    full_rows, full = measured(process, lambda: parallel(range(100)))
    etags = {row[5] for row in full_rows if row[5]}
    cache_headers = {row[6] for row in full_rows}
    if len(etags) != 1 or cache_headers != {"tree-preload"}:
        raise RuntimeError(f"Expected one shared warm tree ETag/cache entry, got etags={len(etags)} cache={cache_headers}")
    shared_etag = next(iter(etags))
    wait_for_writer_quiescence()
    not_modified_rows, not_modified = measured(process, lambda: parallel(range(100), shared_etag))
    if {row[1] for row in not_modified_rows} != {304}:
        raise RuntimeError("ETag phase did not return 304 for every user")
    wait_for_writer_quiescence()
    sequential_304_rows, sequential_304 = measured(process, lambda: [tree_request(0, shared_etag) for _ in range(10)])
    wait_for_writer_quiescence()
    single_rows, single = measured(process, lambda: [tree_request(0) for _ in range(10)])
    for metrics in (full, not_modified, sequential_304, single):
        if metrics["postgres_writer"]["tasks"] != 0:
            raise RuntimeError(f"Tree preload unexpectedly wrote SQLite state: {metrics}")
    print(json.dumps({
        "full_100": full,
        "etag_304_100": not_modified,
        "sequential_304_10": sequential_304,
        "sequential_full_10": single,
        "shared_etag": shared_etag,
        "full_cache_headers": sorted(cache_headers),
        "full_statuses": sorted({row[1] for row in full_rows}),
    }, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

