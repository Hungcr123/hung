"""Benchmark common-tree/user-overlay and Space_V delta checkpoint.

Added 2026-07-27. This is a focused benchmark harness, not production code.
It measures the current PostgreSQL-only runtime after the common-tree/user-
overlay split. It intentionally records when password-auth evidence is absent
instead of silently substituting local login for password-auth login.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil
import psycopg
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(r"C:\Users\Admin\.codex\plans\server2_postgres_full_audit")
SCHEMA = "common-overlay-spacev-benchmark-v1"
WORKLOAD = "common-overlay-spacev-split-v1"
SOURCE_FILES = (
    "FUTURE/tools/benchmark_common_overlay_spacev_checkpoint.py",
    "FUTURE/tools/benchmark_login_warmup_postgres.py",
    "FUTURE/web/js_parts/20_pdf_page_progress.js",
    "FUTURE/web/future.js",
    "FUTURE/server_parts/http_server/03_handler_get_routes.py",
    "FUTURE/server_parts/http_server/04_handler_post_routes.py",
    "FUTURE/server_parts/progress_inventory_vocab/03_space_v_progress.py",
    "FUTURE_SERVER_2.py",
    "FUTURE/server_app.py",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def clean(value: object) -> str:
    return str(value or "").strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_hashes() -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for rel in SOURCE_FILES:
        path = ROOT / rel
        rows[rel] = {
            "exists": path.exists(),
            "sha256": sha256_file(path) if path.exists() else "",
            "bytes": path.stat().st_size if path.exists() else 0,
        }
    return rows


def pg_dsn() -> str:
    dsn = os.environ.get("FUTURE_PG_DSN", "").strip()
    if not dsn:
        raise RuntimeError("FUTURE_PG_DSN is required and is not printed")
    return dsn


def pg_metrics() -> dict[str, float]:
    with psycopg.connect(pg_dsn()) as connection, connection.cursor() as cursor:
        out: dict[str, float] = {}
        cursor.execute("SELECT COALESCE(sum(xact_commit+xact_rollback),0), COALESCE(sum(blks_hit+blks_read),0) FROM pg_stat_database WHERE datname=current_database()")
        row = cursor.fetchone() or (0, 0)
        out["db_transactions"] = float(row[0] or 0)
        out["db_blocks"] = float(row[1] or 0)
        try:
            cursor.execute("SELECT COALESCE(sum(calls),0), COALESCE(sum(total_exec_time),0), COALESCE(sum(rows),0) FROM pg_stat_statements")
            row = cursor.fetchone() or (0, 0, 0)
            out["query_calls"] = float(row[0] or 0)
            out["query_exec_ms"] = float(row[1] or 0)
            out["query_rows"] = float(row[2] or 0)
        except Exception:
            try:
                connection.rollback()
            except Exception:
                pass
            out["query_calls"] = -1.0
            out["query_exec_ms"] = -1.0
            out["query_rows"] = -1.0
        cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database()")
        out["active_connections"] = float(cursor.fetchone()[0] or 0)
        return out


def pg_delta(before: dict[str, float], after: dict[str, float]) -> dict[str, float]:
    return {key: round(float(after.get(key, 0)) - float(before.get(key, 0)), 6) for key in sorted(set(before) | set(after))}


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
            "vms_bytes": int(mem.vms),
            "threads": process.num_threads(),
        }


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(len(ordered) * ratio) - 1))
    return round(ordered[idx], 3)


def summarise(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "mean_ms": round(statistics.fmean(values), 3),
        "p50_ms": round(statistics.median(values), 3),
        "p95_ms": percentile(values, 0.95),
        "p99_ms": percentile(values, 0.99),
        "min_ms": round(min(values), 3),
        "max_ms": round(max(values), 3),
    }


class Recorder:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def add(self, row: dict[str, Any]) -> None:
        self.rows.append(row)


def http_call(session: requests.Session, recorder: Recorder, base: str, scenario: str, username: str, group: str, method: str, path: str, *, token: str = "", etag: str = "", json_body: dict[str, Any] | None = None, timeout: float = 45) -> tuple[requests.Response, dict[str, Any]]:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    if etag:
        headers["If-None-Match"] = etag
    body_bytes = len(json.dumps(json_body, separators=(",", ":")).encode("utf-8")) if json_body is not None else 0
    started = time.perf_counter()
    response = session.request(method, base.rstrip("/") + path, headers=headers, json=json_body, timeout=timeout)
    elapsed = (time.perf_counter() - started) * 1000
    row = {
        "timestamp_utc": utc_now(),
        "scenario": scenario,
        "username": username,
        "group": group,
        "method": method,
        "path": path.split("?", 1)[0],
        "status": response.status_code,
        "duration_ms": round(elapsed, 3),
        "request_bytes": body_bytes,
        "response_bytes": len(response.content),
        "wire_response_bytes": int(response.headers.get("Content-Length") or len(response.content) or 0),
        "etag": response.headers.get("ETag", ""),
        "cache_hit": response.headers.get("X-Future-Cache-Hit", ""),
        "server_timing": response.headers.get("Server-Timing", ""),
        "error": "",
    }
    if response.status_code >= 400:
        row["error"] = response.text[:240]
    recorder.add(row)
    response.raise_for_status()
    return response, row


def local_session(base: str, username: str) -> tuple[requests.Session, str]:
    session = requests.Session()
    response = session.get(base.rstrip() + "/auth/codex-local-login", params={"marker": "1", "username": username, "next": "/status"}, allow_redirects=False, timeout=30)
    if response.status_code != 302:
        raise RuntimeError(f"local session failed for {username}: {response.status_code} {response.text[:160]}")
    token = ""
    for cookie in session.cookies:
        if cookie.name == "future_lesson_auth_token":
            token = cookie.value
            break
    if not token:
        set_cookie = response.headers.get("Set-Cookie", "")
        if "future_lesson_auth_token=" in set_cookie:
            token = set_cookie.split("future_lesson_auth_token=", 1)[1].split(";", 1)[0]
    if not token:
        raise RuntimeError(f"local session produced no token for {username}")
    return session, token


def password_session(base: str, recorder: Recorder, username: str, password: str, scenario: str) -> tuple[requests.Session, str]:
    session = requests.Session()
    http_call(session, recorder, base, scenario, username, "username_check", "GET", f"/auth/username?username={username}")
    response, _row = http_call(session, recorder, base, scenario, username, "login", "POST", "/auth/login", json_body={"username": username, "password": password})
    token = clean(response.json().get("token"))
    if not token:
        raise RuntimeError(f"password login returned no token for {username}")
    session.headers.update({"Authorization": "Bearer " + token})
    return session, token


def pick_space_v_row(username: str) -> dict[str, Any]:
    with psycopg.connect(pg_dsn()) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT path,identity,file_id,record_json,server_revision
            FROM future_server2.lesson_progress
            WHERE lower(username)=%s AND space='Space_V'
            ORDER BY updated_epoch DESC, updated_at_utc DESC
            LIMIT 1
            """,
            (username.lower(),),
        )
        row = cursor.fetchone()
    if not row:
        raise RuntimeError(f"No Space_V progress row for {username}")
    record = dict(row[3]) if isinstance(row[3], dict) else {}
    return {
        "path": clean(row[0] or record.get("path")),
        "identity": clean(row[1] or row[2] or record.get("identity")),
        "title": clean(record.get("title") or Path(clean(row[0])).stem),
        "record": record,
        "server_revision": int(row[4] or 0),
    }


def run_cache_sequence(base: str, recorder: Recorder, username: str, session: requests.Session, token: str, scenario: str, rounds: int, warmup: bool = False) -> list[float]:
    durations: list[float] = []
    common_etag = ""
    overlay_etag = ""
    for _ in range(rounds):
        started = time.perf_counter()
        _auth, _ = http_call(session, recorder, base, scenario, username, "auth_me", "GET", "/auth/me")
        common, common_row = http_call(session, recorder, base, scenario, username, "common_tree", "GET", "/server-data/common-tree", etag=common_etag)
        overlay, overlay_row = http_call(session, recorder, base, scenario, username, "user_overlay", "GET", "/server-data/user-overlay", etag=overlay_etag)
        if common.status_code == 200:
            common_etag = common_row["etag"]
        if overlay.status_code == 200:
            overlay_etag = overlay_row["etag"]
        if not warmup:
            durations.append((time.perf_counter() - started) * 1000)
    return durations


def run_spacev_write_retry(base: str, recorder: Recorder, username: str, session: requests.Session, token: str, scenario: str, rounds: int, warmup: bool = False) -> list[float]:
    target = pick_space_v_row(username)
    durations: list[float] = []
    for index in range(rounds):
        session, token = local_session(base, username)
        source = json.loads(json.dumps(target["record"], ensure_ascii=False))
        stamp = f"{utc_now()}-{index}"
        operation = f"codex-perf-{username}-{index}"
        state = source.get("state") if isinstance(source.get("state"), dict) else {}
        source.update({
            "path": target["path"],
            "identity": target["identity"],
            "lesson_id": target["identity"],
            "title": target["title"],
            "action": "autosave",
            "savedAt": stamp,
            "updatedAt": stamp,
            "syncOperationId": operation,
            "nodeIndex": max(1, int(source.get("nodeIndex") or 1)),
            "nodeCount": max(1, int(source.get("nodeCount") or 25)),
            "learnedCount": max(1, int(source.get("learnedCount") or 1)),
        })
        state.update({"savedAt": stamp, "updatedAt": stamp, "syncOperationId": operation, "path": target["path"], "identity": target["identity"]})
        source["state"] = state
        started = time.perf_counter()
        response, _row = http_call(session, recorder, base, scenario, username, "space_v_write", "POST", "/space-v/progress?client_source=checkpoint_perf&response=compact-v1", json_body=source)
        response_json = response.json()
        schema = clean(response_json.get("response_schema"))
        if schema != "space-v-progress-compact-v1":
            raise RuntimeError(f"Space_V write did not return compact delta: {schema}")
        http_call(session, recorder, base, scenario, username, "space_v_retry_same_operation", "POST", "/space-v/progress?client_source=checkpoint_perf&response=compact-v1", json_body=source)
        if not warmup:
            durations.append((time.perf_counter() - started) * 1000)
    return durations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:18877")
    parser.add_argument("--port", type=int, default=18877)
    parser.add_argument("--prefix", default="checkpoint_007_common_overlay_spacev_current")
    parser.add_argument("--warmup-rounds", type=int, default=5)
    parser.add_argument("--rounds", type=int, default=30)
    args = parser.parse_args()

    process = server_process(args.port)
    recorder = Recorder()
    accounts = {"hung": os.environ.get("FUTURE_LOGIN_BENCH_PASSWORD_HUNG", ""), "quynh": os.environ.get("FUTURE_LOGIN_BENCH_PASSWORD_QUYNH", "")}
    password_auth_available = all(clean(value) for value in accounts.values())
    before_process = process_sample(process)
    before_pg = pg_metrics()
    started_cpu = before_process["cpu_seconds"]
    started_wall = time.perf_counter()
    errors: list[str] = []
    flow_durations: dict[str, list[float]] = {}

    sessions: dict[str, tuple[requests.Session, str]] = {}
    try:
        for username in ("hung", "quynh"):
            sessions[username] = local_session(args.base, username)
        # warmup
        for username, (session, token) in sessions.items():
            run_cache_sequence(args.base, recorder, username, session, token, "warmup_cache", args.warmup_rounds, warmup=True)
            run_spacev_write_retry(args.base, recorder, username, session, token, "warmup_spacev", args.warmup_rounds, warmup=True)
        flow_durations["login_persistent_cache_warm"] = []
        flow_durations["tab_new"] = []
        flow_durations["browser_reopen"] = []
        flow_durations["hung_quynh_alternating"] = []
        for index in range(args.rounds):
            username = "hung" if index % 2 == 0 else "quynh"
            session, token = local_session(args.base, username)
            flow_durations["login_persistent_cache_warm"].extend(run_cache_sequence(args.base, recorder, username, session, token, "login_persistent_cache_warm", 1))
        for index in range(args.rounds):
            username = "hung" if index % 2 == 0 else "quynh"
            session, token = local_session(args.base, username)
            flow_durations["tab_new"].extend(run_cache_sequence(args.base, recorder, username, session, token, "tab_new", 1))
        for index in range(args.rounds):
            username = "hung" if index % 2 == 0 else "quynh"
            session, token = local_session(args.base, username)
            flow_durations["browser_reopen"].extend(run_cache_sequence(args.base, recorder, username, session, token, "browser_reopen", 1))
        for index in range(args.rounds):
            username = "hung" if index % 2 == 0 else "quynh"
            session, token = local_session(args.base, username)
            flow_durations["hung_quynh_alternating"].extend(run_cache_sequence(args.base, recorder, username, session, token, "hung_quynh_alternating", 1))
        flow_durations["space_v_progress_write_retry"] = []
        for username, (session, token) in sessions.items():
            flow_durations["space_v_progress_write_retry"].extend(run_spacev_write_retry(args.base, recorder, username, session, token, "space_v_progress_write_retry", args.rounds))
        if password_auth_available:
            flow_durations["login_cold"] = []
            for index in range(args.rounds):
                username = "hung" if index % 2 == 0 else "quynh"
                session, token = password_session(args.base, recorder, username, accounts[username], "login_cold")
                flow_durations["login_cold"].extend(run_cache_sequence(args.base, recorder, username, session, token, "login_cold", 1))
        else:
            errors.append("login_cold password-auth scenario NOT PROVEN: FUTURE_LOGIN_BENCH_PASSWORD_HUNG/QUYNH not present")
    finally:
        after_process = process_sample(process)
        after_pg = pg_metrics()

    total_wall_ms = (time.perf_counter() - started_wall) * 1000
    total_cpu_ms = (after_process["cpu_seconds"] - started_cpu) * 1000
    raw = {
        "schema": SCHEMA,
        "workload": WORKLOAD,
        "started_at_utc": utc_now(),
        "source_hashes": source_hashes(),
        "harness_hash": sha256_file(ROOT / "FUTURE/tools/benchmark_common_overlay_spacev_checkpoint.py"),
        "baseline_status": {
            "checkpoint_001": "scope-limited-valid-for-old-tree-preload-only",
            "reason": "old baseline used same login harness for /server-data/tree-preload before split; it cannot prove new /server-data/common-tree and /server-data/user-overlay scenarios or browser cache fallback",
        },
        "auth": {
            "session_method_for_cache_scenarios": "localhost_codex_local_login",
            "password_auth_available": password_auth_available,
        },
        "rounds": {"warmup": args.warmup_rounds, "measured": args.rounds},
        "process_before": before_process,
        "process_after": after_process,
        "postgres_delta": pg_delta(before_pg, after_pg),
        "total_wall_ms": round(total_wall_ms, 3),
        "total_cpu_ms": round(total_cpu_ms, 3),
        "cpu_ms_per_request": round(total_cpu_ms / max(1, len(recorder.rows)), 6),
        "flow_metrics": {key: summarise(value) for key, value in flow_durations.items()},
        "endpoint_metrics": {},
        "requests": recorder.rows,
        "errors": errors + [row["error"] for row in recorder.rows if row.get("error")],
    }
    for group in sorted({row["group"] for row in recorder.rows}):
        rows = [row for row in recorder.rows if row["group"] == group]
        raw["endpoint_metrics"][group] = {
            **summarise([float(row["duration_ms"]) for row in rows]),
            "calls": len(rows),
            "request_bytes": sum(int(row["request_bytes"]) for row in rows),
            "response_bytes": sum(int(row["response_bytes"]) for row in rows),
            "wire_response_bytes": sum(int(row["wire_response_bytes"]) for row in rows),
            "statuses": {str(status): sum(1 for row in rows if int(row["status"]) == status) for status in sorted({int(row["status"]) for row in rows})},
            "cache_hits": {hit: sum(1 for row in rows if row["cache_hit"] == hit) for hit in sorted({row["cache_hit"] for row in rows})},
        }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = OUT_DIR / f"{args.prefix}_raw.json"
    csv_path = OUT_DIR / f"{args.prefix}_requests.csv"
    summary_path = OUT_DIR / f"{args.prefix}_summary.md"
    raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(recorder.rows[0].keys()) if recorder.rows else ["empty"])
        writer.writeheader()
        writer.writerows(recorder.rows)
    lines = [
        f"# {args.prefix}",
        "",
        f"- schema: `{SCHEMA}`",
        f"- workload: `{WORKLOAD}`",
        f"- total_requests: `{len(recorder.rows)}`",
        f"- total_cpu_ms: `{raw['total_cpu_ms']}`",
        f"- cpu_ms_per_request: `{raw['cpu_ms_per_request']}`",
        f"- total_wall_ms: `{raw['total_wall_ms']}`",
        f"- password_auth_available: `{password_auth_available}`",
        f"- decision: `INSUFFICIENT EVIDENCE`",
        "",
        "| Scenario | Count | P50 ms | P95 ms | P99 ms | Mean ms |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, value in raw["flow_metrics"].items():
        lines.append(f"| {key} | {value.get('count',0)} | {value.get('p50_ms',0)} | {value.get('p95_ms',0)} | {value.get('p99_ms',0)} | {value.get('mean_ms',0)} |")
    lines.extend(["", "| Endpoint | Calls | P50 ms | P95 ms | P99 ms | Wire bytes | Cache hits |", "| --- | ---: | ---: | ---: | ---: | ---: | --- |"])
    for key, value in raw["endpoint_metrics"].items():
        lines.append(f"| {key} | {value.get('calls',0)} | {value.get('p50_ms',0)} | {value.get('p95_ms',0)} | {value.get('p99_ms',0)} | {value.get('wire_response_bytes',0)} | `{json.dumps(value.get('cache_hits',{}), ensure_ascii=False)}` |")
    if errors:
        lines.extend(["", "## Gaps", *[f"- {item}" for item in errors]])
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"ok": not raw["errors"], "raw": str(raw_path), "summary": str(summary_path), "requests": len(recorder.rows), "errors": raw["errors"][:5]}, ensure_ascii=False))
    return 0 if not raw["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
