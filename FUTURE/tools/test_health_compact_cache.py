"""Regression for compatible full health and compact cached dashboard health."""

from __future__ import annotations

import concurrent.futures
import time

import requests


BASE = "http://127.0.0.1:8877"
REQUIRED_DYNAMIC_KEYS = {
    "ok",
    "service",
    "server_time",
    "server_timestamp",
    "model_name",
    "language",
    "ready",
    "started_at",
    "workload",
    "distributed_workers",
}


def get_health(view: str = "") -> requests.Response:
    suffix = f"?view={view}&ts={time.time_ns()}" if view else f"?ts={time.time_ns()}"
    return requests.get(f"{BASE}/health{suffix}", timeout=15)


def main() -> int:
    full = get_health()
    full.raise_for_status()
    full_payload = full.json()
    if "settings" not in full_payload or not REQUIRED_DYNAMIC_KEYS.issubset(full_payload):
        raise RuntimeError("Legacy full /health compatibility payload is incomplete")

    compact = get_health("dashboard-v1")
    compact.raise_for_status()
    compact_payload = compact.json()
    if "settings" in compact_payload or not REQUIRED_DYNAMIC_KEYS.issubset(compact_payload):
        raise RuntimeError("Compact dashboard health payload is incomplete")
    if set(full_payload) - {"settings"} != set(compact_payload):
        raise RuntimeError("Compact health removed fields other than settings")
    if len(compact.content) >= len(full.content) * 0.6:
        raise RuntimeError("Compact health did not materially reduce payload bytes")

    def request_one(index: int):
        response = requests.get(
            f"{BASE}/health?view=dashboard-v1&ts={time.time_ns()}-{index}",
            timeout=15,
        )
        return response.status_code, response.headers.get("X-Future-Cache-Hit", ""), response.content

    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        rows = list(pool.map(request_one, range(100)))
    if any(status != 200 for status, _cache, _data in rows):
        raise RuntimeError("Concurrent compact health returned a non-200 response")
    builds = sum(1 for _status, cache, _data in rows if cache == "health-build")
    hits = sum(1 for _status, cache, _data in rows if cache == "health-bytes")
    if builds > 2 or hits < 98:
        raise RuntimeError(f"Health byte cache did not coalesce the burst: builds={builds} hits={hits}")

    first_time = str(compact_payload.get("server_timestamp") or "")
    time.sleep(1.1)
    refreshed = get_health("dashboard-v1")
    refreshed.raise_for_status()
    if refreshed.headers.get("X-Future-Cache-Hit") != "health-build":
        raise RuntimeError("Health cache did not expire after its freshness window")
    if str(refreshed.json().get("server_timestamp") or "") == first_time:
        raise RuntimeError("Health timestamp did not refresh after cache expiry")

    print(
        "health_compact_cache=ok full_compatible=true compact_settings=false "
        f"full_bytes={len(full.content)} compact_bytes={len(compact.content)} builds={builds} hits={hits}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
