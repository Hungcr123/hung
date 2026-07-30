#!/usr/bin/env python3
"""Probe /server-data/user-overlay single-flight and cache isolation.

Added 2026-07-28 for the final user-overlay verification checkpoint.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE.tools import probe_user_overlay_abc_correctness_20260728 as abc_gate

BASE = "http://127.0.0.1:18877"
OUT = Path(r"C:\Users\Admin\.codex\plans\server2_user_overlay_opt_20260727\overlay_isolation_20260728.json")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def timing(header: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for name, value in re.findall(r"([a-zA-Z0-9_\-]+);dur=([0-9.]+)", header or ""):
        out[name] = float(value)
    return out


def login(base: str, username: str, password: str) -> requests.Session:
    session = requests.Session()
    response = session.post(base + "/auth/login", json={"username": username, "password": password}, timeout=45)
    response.raise_for_status()
    token = str((response.json() or {}).get("token") or "")
    if not token:
        raise RuntimeError(f"missing token for {username}")
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session


def probe_overlay(session: requests.Session, base: str, username: str) -> dict:
    started = time.perf_counter()
    response = session.get(base + "/server-data/user-overlay", headers={"Accept-Encoding": "gzip"}, timeout=60)
    elapsed = (time.perf_counter() - started) * 1000
    payload = response.json() if response.content else {}
    return {
        "status": response.status_code,
        "elapsed_ms": round(elapsed, 3),
        "cache_hit": response.headers.get("X-Future-Cache-Hit", ""),
        "overlay_revision": payload.get("overlay_revision", ""),
        "overlay_rows": int(payload.get("row_count", 0) or 0),
        "fast_path": bool(payload.get("empty_overlay_fast_path")),
        "overlay_manifest_ms": timing(response.headers.get("Server-Timing", "")).get("overlay_manifest_revision", 0.0),
        "overlay_lock_ms": timing(response.headers.get("Server-Timing", "")).get("overlay_lock", 0.0),
    }


def run_same_user(base: str, username: str, password: str, count: int) -> dict:
    session = login(base, username, password)
    probe_overlay(session, base, username)  # warm once
    rows = []
    with ThreadPoolExecutor(max_workers=count) as pool:
        futures = [pool.submit(probe_overlay, session, base, username) for _ in range(count)]
        for future in as_completed(futures):
            rows.append(future.result())
    elapsed = [row["elapsed_ms"] for row in rows]
    return {
        "username": username,
        "count": count,
        "statuses": {str(code): sum(1 for row in rows if row["status"] == code) for code in sorted({row["status"] for row in rows})},
        "cache_hits": {hit: sum(1 for row in rows if row["cache_hit"] == hit) for hit in sorted({row["cache_hit"] for row in rows})},
        "p50_ms": round(statistics.median(elapsed), 3) if elapsed else 0,
        "p95_ms": round(sorted(elapsed)[min(len(elapsed) - 1, int(len(elapsed) * 0.95))], 3) if elapsed else 0,
        "max_overlay_lock_ms": round(max(row["overlay_lock_ms"] for row in rows), 3) if rows else 0,
        "max_overlay_manifest_ms": round(max(row["overlay_manifest_ms"] for row in rows), 3) if rows else 0,
        "fast_path_count": sum(1 for row in rows if row["fast_path"]),
    }


def run_multi_user(base: str, credentials: dict[str, str], count: int) -> dict:
    sessions = {username: login(base, username, password) for username, password in credentials.items()}
    for username, session in sessions.items():
        probe_overlay(session, base, username)
    usernames = list(credentials.keys())
    rows = []
    with ThreadPoolExecutor(max_workers=count) as pool:
        futures = [pool.submit(probe_overlay, sessions[usernames[index % len(usernames)]], base, usernames[index % len(usernames)]) for index in range(count)]
        for future in as_completed(futures):
            rows.append(future.result())
    elapsed = [row["elapsed_ms"] for row in rows]
    return {
        "count": count,
        "statuses": {str(code): sum(1 for row in rows if row["status"] == code) for code in sorted({row["status"] for row in rows})},
        "cache_hits": {hit: sum(1 for row in rows if row["cache_hit"] == hit) for hit in sorted({row["cache_hit"] for row in rows})},
        "p50_ms": round(statistics.median(elapsed), 3) if elapsed else 0,
        "p95_ms": round(sorted(elapsed)[min(len(elapsed) - 1, int(len(elapsed) * 0.95))], 3) if elapsed else 0,
        "max_overlay_lock_ms": round(max(row["overlay_lock_ms"] for row in rows), 3) if rows else 0,
        "max_overlay_manifest_ms": round(max(row["overlay_manifest_ms"] for row in rows), 3) if rows else 0,
        "fast_path_count": sum(1 for row in rows if row["fast_path"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=BASE)
    parser.add_argument("--output", default=str(OUT))
    args = parser.parse_args()
    result = {"timestamp_utc": utc_now(), "cleanup_before": abc_gate.cleanup()}
    try:
        lessons = abc_gate.pick_common_lessons()
        groups = abc_gate.seed_users(abc_gate.TEST_PASSWORD, lessons)
        result["groups"] = groups
        result["restart_after_seed"] = abc_gate.restart_test_server()
        credentials = {
            username: abc_gate.TEST_PASSWORD
            for users in groups.values()
            for username in users
        }
        result["same_user"] = run_same_user(args.base, groups["B"][0], abc_gate.TEST_PASSWORD, 10)
        result["multi_user"] = run_multi_user(args.base, credentials, 12)
        result["pass"] = (
            result["same_user"]["statuses"].get("200", 0) == 10
            and result["multi_user"]["statuses"].get("200", 0) == 12
            and result["same_user"]["max_overlay_lock_ms"] < 5000
            and result["multi_user"]["max_overlay_lock_ms"] < 5000
        )
    finally:
        result["cleanup_after"] = abc_gate.cleanup()
        result["finished_utc"] = utc_now()
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": result["pass"], "output": str(out)}, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
