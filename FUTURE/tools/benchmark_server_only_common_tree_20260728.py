#!/usr/bin/env python3
"""Server-only HTTP benchmark for /server-data/common-tree and login flow.

Added 2026-07-28 to measure Server 2 without browser, DOM, or IndexedDB noise.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import re
import secrets
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil
import psycopg
import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app  # noqa: E402

OUT_DIR = Path(r"C:\Users\Admin\.codex\plans\server2_common_tree_server_only_20260728")
BASE = "http://127.0.0.1:18877"
TEST_PREFIX = "codexsrvonly"
LOAD_USERS = tuple(f"{TEST_PREFIX}{index:03d}" for index in range(1, 101))
SPLIT_FLOW_ENDPOINTS = (
    ("auth_me", "GET", "/auth/me"),
    ("login_preload", "GET", "/server-data/login-preload?response=compact-v2"),
    ("common_tree", "GET", "/server-data/common-tree"),
    ("user_overlay", "GET", "/server-data/user-overlay"),
    ("folder_list", "GET", "/server-data/list?path=common&defer_task_board=1&include_space_task=1"),
    ("lesson_tasks", "GET", "/lesson-tasks"),
    ("lesson_tasks_status", "GET", "/lesson-tasks/status"),
)
MINIMAL_LOGIN_ENDPOINTS = (
    ("auth_me", "GET", "/auth/me"),
    ("login_preload", "GET", "/server-data/login-preload?response=compact-v2"),
    ("common_tree", "GET", "/server-data/common-tree"),
    ("user_overlay", "GET", "/server-data/user-overlay"),
)
OBJECTIVE_LOGIN_ENDPOINTS = (
    ("login_preload", "GET", "/server-data/login-preload?response=compact-v2"),
    ("common_tree", "GET", "/server-data/common-tree"),
    ("user_overlay", "GET", "/server-data/user-overlay"),
)
COMPAT_TREE_PRELOAD_ENDPOINT = ("tree_preload", "GET", "/server-data/tree-preload")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(len(ordered) * pct / 100.0) - 1))
    return round(ordered[idx], 3)


def summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "mean_ms": round(statistics.fmean(values), 3),
        "p50_ms": round(statistics.median(values), 3),
        "p95_ms": percentile(values, 95),
        "p99_ms": percentile(values, 99),
        "max_ms": round(max(values), 3),
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def password_hash(value: str) -> str:
    salt = secrets.token_urlsafe(18)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode("utf-8"), salt.encode("utf-8"), 2)
    return "pbkdf2_sha256$2$%s$%s" % (salt, base64.urlsafe_b64encode(digest).decode("ascii").rstrip("="))


def cleanup_test_users() -> dict[str, int]:
    prefix = TEST_PREFIX + "%"

    def _write(connection):
        deleted = {}
        with connection.cursor() as cursor:
            for table in (
                "auth_sessions",
                "lesson_time_credit_state",
                "lesson_time",
                "lesson_progress",
                "lesson_progress_namespaces",
                "append_events",
                "vocabulary_events",
                "vocabulary_registry",
                "daily_earn",
                "weekly_earn",
                "monthly_earn",
                "npc_period_earn",
                "server_load_test_credentials",
                "user_auth_credentials",
                "users",
            ):
                if table == "append_events":
                    cursor.execute(f"DELETE FROM future_server2.{table} WHERE lower(username) LIKE %s OR lower(event_key) LIKE %s", (prefix, prefix))
                else:
                    cursor.execute(f"DELETE FROM future_server2.{table} WHERE lower(username) LIKE %s", (prefix,))
                deleted[table] = int(cursor.rowcount or 0)
        return deleted

    return app.postgres_execute(_write)


def provision_test_users(password: str) -> None:
    hashed = password_hash(password)
    now = utc_now()
    for username in LOAD_USERS:
        app.postgres_upsert_user_row({
            "username": username,
            "is_admin": False,
            # Updated 2026-07-28: benchmark accounts use real password auth but
            # remain test metadata so production startup warmup excludes them.
            "is_test": True,
            "profile_json": {"full_name": f"Server Only {username[-3:]}", "benchmark": "server-only-common-tree"},
            "updated_at_utc": now,
        })
        app.postgres_upsert_user_auth_credential(username, hashed, "benchmark:server-only-common-tree")


def server_process(port: int) -> psutil.Process:
    for conn in psutil.net_connections(kind="tcp"):
        if conn.laddr and conn.laddr.port == port and conn.status == psutil.CONN_LISTEN and conn.pid:
            return psutil.Process(conn.pid)
    raise RuntimeError(f"No Server 2 listener on port {port}")


def cpu_seconds(process: psutil.Process) -> float:
    row = process.cpu_times()
    return float(row.user + row.system)


def process_sample(process: psutil.Process) -> dict[str, Any]:
    with process.oneshot():
        mem = process.memory_info()
        return {
            "pid": process.pid,
            "cpu_seconds": cpu_seconds(process),
            "rss_bytes": int(mem.rss),
            "threads": process.num_threads(),
        }


def postgres_metrics() -> dict[str, float]:
    dsn = os.environ.get("FUTURE_PG_DSN", "").strip()
    if not dsn:
        return {"available": 0.0}
    with psycopg.connect(dsn) as connection, connection.cursor() as cursor:
        out: dict[str, float] = {}
        cursor.execute("SELECT COALESCE(sum(xact_commit+xact_rollback),0), COALESCE(sum(blks_hit+blks_read),0) FROM pg_stat_database WHERE datname=current_database()")
        row = cursor.fetchone() or (0, 0)
        out["db_transactions"] = float(row[0] or 0)
        out["db_blocks"] = float(row[1] or 0)
        cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database()")
        out["active_connections"] = float(cursor.fetchone()[0] or 0)
        return out


def postgres_delta(before: dict[str, float], after: dict[str, float]) -> dict[str, float]:
    return {key: round(float(after.get(key, 0)) - float(before.get(key, 0)), 6) for key in sorted(set(before) | set(after))}


class Recorder:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def add(self, row: dict[str, Any]) -> None:
        self.rows.append(row)


def endpoint_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        bucket = out.setdefault(row["group"], {"durations": [], "client_minus_server": [], "statuses": {}, "bytes": 0, "errors": 0, "cache_hit_counts": {}, "server_timing": []})
        bucket["durations"].append(float(row["duration_ms"]))
        bucket["statuses"][str(row["status"])] = bucket["statuses"].get(str(row["status"]), 0) + 1
        bucket["bytes"] += int(row.get("wire_response_bytes") or 0)
        bucket["errors"] += 1 if row.get("error") or int(row.get("status") or 0) >= 400 else 0
        if row.get("cache_hit"):
            hit = str(row.get("cache_hit"))
            bucket["cache_hit_counts"][hit] = bucket["cache_hit_counts"].get(hit, 0) + 1
        if row.get("server_timing"):
            bucket["server_timing"].append(row["server_timing"])
            dominant = _dominant_server_timing_ms(row["server_timing"])
            if dominant >= 0:
                bucket["client_minus_server"].append(max(0.0, float(row["duration_ms"]) - dominant))
    def _timing_summary(headers: list[str]) -> dict[str, Any]:
        values: dict[str, list[float]] = {}
        for header in headers:
            for name, value in re.findall(r"([a-zA-Z0-9_\-]+);dur=([0-9.]+)", header or ""):
                values.setdefault(name, []).append(float(value))
        return {key: summary(items) for key, items in sorted(values.items())}
    return {
        key: {
            **summary(value["durations"]),
            "statuses": value["statuses"],
            "wire_response_bytes": value["bytes"],
            "errors": value["errors"],
            "cache_hit_counts": value["cache_hit_counts"],
            "server_timing": _timing_summary(value["server_timing"]),
            "client_minus_server_ms": summary(value["client_minus_server"]),
        }
        for key, value in out.items()
    }

def _dominant_server_timing_ms(header: str = "") -> float:
    values = {
        name: float(value)
        for name, value in re.findall(r"([a-zA-Z0-9_\-]+);dur=([0-9.]+)", header or "")
    }
    for name in (
        "common_prepare",
        "overlay_prepare",
        "login_preload_total",
        "lesson_tasks_total",
        "list_total",
    ):
        if name in values:
            return values[name]
    return -1.0


def call(
    session: requests.Session,
    recorder: Recorder,
    username: str,
    group: str,
    method: str,
    path: str,
    *,
    token: str = "",
    body: dict[str, Any] | None = None,
    etag: str = "",
) -> requests.Response:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if etag:
        headers["If-None-Match"] = etag
    started = time.perf_counter()
    response = session.request(method, BASE + path, headers=headers, json=body, timeout=60)
    elapsed = (time.perf_counter() - started) * 1000
    row = {
        "timestamp_utc": utc_now(),
        "username": username,
        "group": group,
        "method": method,
        "path": path.split("?", 1)[0],
        "status": response.status_code,
        "duration_ms": round(elapsed, 3),
        "request_bytes": len(json.dumps(body, separators=(",", ":")).encode("utf-8")) if body is not None else 0,
        "response_bytes": len(response.content),
        "wire_response_bytes": int(response.headers.get("Content-Length") or len(response.content) or 0),
        "cache_hit": response.headers.get("X-Future-Cache-Hit", ""),
        "server_timing": response.headers.get("Server-Timing", ""),
        "error": "",
    }
    if response.status_code >= 400:
        row["error"] = response.text[:240]
    recorder.add(row)
    response.raise_for_status()
    return response


def password_login(username: str, password: str, recorder: Recorder) -> tuple[requests.Session, str]:
    session = requests.Session()
    call(session, recorder, username, "username_check", "GET", f"/auth/username?username={username}")
    response = call(session, recorder, username, "login", "POST", "/auth/login", body={"username": username, "password": password})
    token = ""
    try:
        token = str((response.json() or {}).get("token") or "")
    except Exception:
        token = ""
    if not token:
        raise RuntimeError(f"missing token for {username}")
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session, token


def login_flow(username: str, password: str, recorder: Recorder, endpoints: tuple[tuple[str, str, str], ...], warm_revalidate: bool = False) -> dict[str, Any]:
    session, token = password_login(username, password, recorder)
    etags: dict[str, str] = {}
    seed_wall_ms = 0.0
    if warm_revalidate:
        seed_started = time.perf_counter()
        for group, method, path in endpoints:
            if group in {"common_tree", "user_overlay", "login_preload"}:
                response = call(session, recorder, username, f"{group}_warm_seed", method, path, token=token)
                etags[group] = response.headers.get("ETag", "")
        seed_wall_ms = (time.perf_counter() - seed_started) * 1000
    started = time.perf_counter()
    for group, method, path in endpoints:
        call(session, recorder, username, group, method, path, token=token, etag=etags.get(group, ""))
    return {
        "username": username,
        "wall_ms": round((time.perf_counter() - started) * 1000, 3),
        "seed_wall_ms": round(seed_wall_ms, 3),
        "request_count": len(endpoints) + 2 + len(etags),
    }


def run_batch(accounts: list[tuple[str, str]], level: int, rounds: int, endpoints: tuple[tuple[str, str, str], ...], warm_revalidate: bool = False) -> dict[str, Any]:
    recorder = Recorder()
    process = server_process(18877)
    before = process_sample(process)
    before_pg = postgres_metrics()
    started_wall = time.perf_counter()
    flows: list[dict[str, Any]] = []
    errors: list[str] = []
    for _ in range(rounds):
        with ThreadPoolExecutor(max_workers=level) as pool:
            futures = [pool.submit(login_flow, accounts[index % len(accounts)][0], accounts[index % len(accounts)][1], recorder, endpoints, warm_revalidate) for index in range(level)]
            for future in as_completed(futures):
                try:
                    flows.append(future.result())
                except Exception as exc:
                    errors.append(f"{type(exc).__name__}: {exc}")
    after = process_sample(process)
    after_pg = postgres_metrics()
    wall_ms = (time.perf_counter() - started_wall) * 1000
    server_cpu_ms = max(0.0, (after["cpu_seconds"] - before["cpu_seconds"]) * 1000)
    endpoint_metrics = endpoint_summary(recorder.rows)
    return {
        "level": level,
        "rounds": rounds,
        "accounts": [username for username, _password in accounts],
        "flows": len(flows),
        "requests": len(recorder.rows),
        "errors": len(errors) + sum(1 for row in recorder.rows if row.get("error") or int(row.get("status") or 0) >= 400),
        "error_samples": errors[:5],
        "wall_ms": round(wall_ms, 3),
        "server_before": before,
        "server_after": after,
        "server_cpu_ms": round(server_cpu_ms, 3),
        "server_cpu_ms_per_flow": round(server_cpu_ms / max(1, len(flows)), 3),
        "postgres_delta": postgres_delta(before_pg, after_pg),
        "endpoint_metrics": endpoint_metrics,
        "flow_wall_ms": summary([float(flow["wall_ms"]) for flow in flows]),
        "requests_raw": recorder.rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUT_DIR / "server_only_common_tree_20260728.json"))
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--compat-tree-preload", action="store_true", help="Include legacy /server-data/tree-preload in the measured flow.")
    parser.add_argument("--objective-login", action="store_true", help="Measure only the objective login flow: login-preload + common-tree + user-overlay.")
    parser.add_argument("--minimal-login", action="store_true", help="Measure only auth/login + common-tree + user-overlay.")
    parser.add_argument("--warm-revalidate", action="store_true", help="Seed ETags then measure If-None-Match revalidation for cacheable endpoints.")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    load_password = "codex-" + secrets.token_urlsafe(18)
    accounts = [(username, load_password) for username in LOAD_USERS]
    base_endpoints = OBJECTIVE_LOGIN_ENDPOINTS if args.objective_login else (MINIMAL_LOGIN_ENDPOINTS if args.minimal_login else SPLIT_FLOW_ENDPOINTS)
    endpoints = base_endpoints + ((COMPAT_TREE_PRELOAD_ENDPOINT,) if args.compat_tree_preload else ())
    result = {
        "schema": "server-only-common-tree-v1",
        "flow_profile": (
            ("objective-login" if args.objective_login else ("minimal-login" if args.minimal_login else "split-login"))
            + ("-plus-compat-tree-preload" if args.compat_tree_preload else "")
            + ("-warm-revalidate" if args.warm_revalidate else "-cold-http")
        ),
        "flow_endpoints": [row[0] for row in endpoints],
        "started_utc": utc_now(),
        "source_hashes": {
            "FUTURE/tools/benchmark_server_only_common_tree_20260728.py": sha256_file(Path(__file__)),
            "FUTURE/web/future.js": sha256_file(ROOT / "FUTURE/web/future.js"),
            "FUTURE/server_parts/http_server/03_handler_get_routes.py": sha256_file(ROOT / "FUTURE/server_parts/http_server/03_handler_get_routes.py"),
            "FUTURE/server_parts/server_data_pdf_qmdict/server_data_manifest_listing/03_manifest_query_cache.py": sha256_file(ROOT / "FUTURE/server_parts/server_data_pdf_qmdict/server_data_manifest_listing/03_manifest_query_cache.py"),
        },
        "server": {},
        "runs": {},
        "cleanup_before": {},
        "cleanup_after": {},
    }
    try:
        health = requests.get(BASE + "/health?view=dashboard-v1", timeout=10).json()
        result["server"] = {
            "pid": int(health.get("pid") or 0),
            "postgres_only": bool((health.get("postgres_writer") or {}).get("postgres_only") is True),
            "warm_ready": bool(health.get("warm_ready")),
            "postgres_writer": health.get("postgres_writer"),
            "pg_dsn_present": bool(os.environ.get("FUTURE_PG_DSN")),
        }
        if not result["server"]["postgres_only"]:
            raise RuntimeError("test server is not PostgreSQL-only")
        result["cleanup_before"] = cleanup_test_users()
        provision_test_users(load_password)
        for level in (1, 5, 10, 25, 50, 100):
            result["runs"][str(level)] = run_batch(accounts[:level], level, args.rounds, endpoints, args.warm_revalidate)
            phase = result["runs"][str(level)]
            if phase["errors"] > max(1, int(phase["flows"] * 0.01)):
                result["stop_reason"] = f"errors exceeded threshold at level {level}"
                break
    finally:
        result["cleanup_after"] = cleanup_test_users()
        result["health_after"] = requests.get(BASE + "/health?view=dashboard-v1", timeout=10).json()
        result["finished_utc"] = utc_now()
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": args.output, "levels": list(result["runs"].keys())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

