"""Benchmark the global Server 2 health payload for local and public callers."""

from __future__ import annotations

import concurrent.futures
import json
import os
import time

import requests

from benchmark_server2_100_users import BASE, measured, response_sizes, server_process, wait_for_writer_quiescence


def main() -> int:
    process = server_process()

    def phase(name: str, host: str, view: str = "") -> dict:
        wait_for_writer_quiescence()

        def request_one(index: int):
            started = time.perf_counter()
            query = f"view={view}&" if view else ""
            response = requests.get(
                f"{BASE}/health?{query}ts={time.time_ns()}-{index}",
                headers={"Host": host, "Accept-Encoding": "gzip"},
                timeout=20,
            )
            decoded, wire, request_bytes = response_sizes(response)
            payload = response.json()
            return (
                (time.perf_counter() - started) * 1000,
                response.status_code,
                decoded,
                wire,
                request_bytes,
                len(payload),
                len(json.dumps(payload.get("settings", {}), separators=(",", ":")).encode("utf-8")),
                len(json.dumps(payload.get("distributed_workers", {}), separators=(",", ":")).encode("utf-8")),
                str(response.headers.get("Content-Encoding") or ""),
                str(response.headers.get("X-Future-Cache-Hit") or ""),
            )

        def run():
            with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
                return list(pool.map(request_one, range(100)))

        rows, metrics = measured(process, run)
        result = {
            **metrics,
            "payload_keys": rows[0][5],
            "settings_bytes_per_response": rows[0][6],
            "distributed_workers_bytes_per_response": rows[0][7],
            "content_encoding": rows[0][8],
            "cache_headers": {value: sum(1 for row in rows if row[9] == value) for value in sorted({row[9] for row in rows})},
        }
        print(name, json.dumps(result, ensure_ascii=True), flush=True)
        return result

    phase("HEALTH_LOCAL", "127.0.0.1:8877")
    phase("HEALTH_LOCAL_DASHBOARD", "127.0.0.1:8877", "dashboard-v1")
    if os.environ.get("HEALTH_BENCH_LOCAL_ONLY") == "1":
        return 0
    phase("HEALTH_PUBLIC", "qm-tech.io.vn")
    phase("HEALTH_PUBLIC_DASHBOARD", "qm-tech.io.vn", "dashboard-v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
