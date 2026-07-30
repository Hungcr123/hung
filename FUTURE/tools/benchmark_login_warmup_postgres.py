"""Benchmark current PostgreSQL-only login warmup flow over real HTTP.

Added 2026-07-26: establishes the current Server 2 PostgreSQL login baseline
before any further login warmup optimization.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import platform
import secrets
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import psutil
import psycopg
import requests

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(r"C:\Users\Admin\.codex\plans\login_postgres_benchmark")
DEFAULT_BASE = "http://127.0.0.1:8877"
DEFAULT_USERS = ("hung", "quynh")
DEFAULT_SPACE_V_FOLDER = "Immediate Mission"
RESULT_SCHEMA_VERSION = "login-postgres-benchmark-result-v2"
WORKLOAD_VERSION = "login-warmup-postgres-v2"
SCENARIO_NAMES = (
    "warm_login",
    "cold_snapshot_fresh_session",
    "progress_dirty",
    "vocabulary_leaderboard_dirty",
    "same_user_two_tabs",
    "two_users_parallel",
)
FIXTURE_PREFIX = "codexloginbench"
FIXTURE_USERS = ("codexloginbench001", "codexloginbench002")
SOURCE_HASH_FILES = (
    Path("FUTURE/tools/benchmark_login_warmup_postgres.py"),
    Path("FUTURE/server_parts/users_auth_settings/03_server_data_profile.py"),
    Path("FUTURE/server_parts/http_server/03_handler_get_routes.py"),
    Path("FUTURE/server_parts/http_server/04_handler_post_routes.py"),
    Path("FUTURE/web/js_parts/05_screen_motion_layout.js"),
    Path("FUTURE/web/future.js"),
    Path("FUTURE_SERVER_2.py"),
    Path("FUTURE/server_app.py"),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def server_process(port: int) -> psutil.Process:
    for connection in psutil.net_connections(kind="tcp"):
        if connection.laddr and connection.laddr.port == port and connection.status == psutil.CONN_LISTEN and connection.pid:
            return psutil.Process(connection.pid)
    raise RuntimeError(f"Server 2 listener not found on port {port}")


def cpu_seconds(process: psutil.Process) -> float:
    row = process.cpu_times()
    return float(row.user + row.system)


def percentile(values: list[float], ratio: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(len(ordered) * ratio) - 1))
    return round(ordered[index], 3)


def summarise(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "min_ms": round(min(values), 3),
        "max_ms": round(max(values), 3),
        "mean_ms": round(statistics.fmean(values), 3),
        "p50_ms": round(statistics.median(values), 3),
        "p95_ms": percentile(values, 0.95),
        "p99_ms": percentile(values, 0.99),
    }


def response_request_bytes(response: requests.Response) -> int:
    body = response.request.body
    if body is None:
        return 0
    if isinstance(body, bytes):
        return len(body)
    return len(str(body).encode("utf-8"))


class Recorder:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.records: list[dict[str, Any]] = []

    def add(self, row: dict[str, Any]) -> None:
        with self._lock:
            self.records.append(row)


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    redacted = {}
    for key, value in headers.items():
        lowered = key.lower()
        if lowered in {"authorization", "cookie", "set-cookie"}:
            redacted[key] = "<redacted>"
        else:
            redacted[key] = value
    return redacted


def call_http(
    session: requests.Session,
    recorder: Recorder,
    base: str,
    scenario: str,
    username: str,
    group: str,
    method: str,
    path: str,
    *,
    token: str = "",
    json_body: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> tuple[requests.Response | None, dict[str, Any]]:
    url = base.rstrip("/") + path
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request_bytes = len(json.dumps(json_body, separators=(",", ":")).encode("utf-8")) if json_body is not None else 0
    started_epoch = time.time()
    started = time.perf_counter()
    response = None
    error = ""
    try:
        response = session.request(method, url, json=json_body, headers=headers, timeout=timeout)
    except Exception as exc:  # benchmark records, caller decides failure.
        error = f"{type(exc).__name__}: {exc}"
    duration_ms = (time.perf_counter() - started) * 1000
    status = int(response.status_code) if response is not None else 0
    response_bytes = len(response.content) if response is not None else 0
    wire_bytes = int(response.headers.get("Content-Length") or response_bytes) if response is not None else 0
    cache_hit = ""
    if response is not None:
        cache_hit = response.headers.get("X-Future-Cache-Hit", "")
        if not request_bytes:
            request_bytes = response_request_bytes(response)
    row = {
        "timestamp_utc": datetime.fromtimestamp(started_epoch, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "scenario": scenario,
        "username": username,
        "group": group,
        "method": method,
        "path_group": path.split("?")[0],
        "status": status,
        "duration_ms": round(duration_ms, 3),
        "response_bytes": response_bytes,
        "wire_response_bytes": wire_bytes,
        "request_bytes": request_bytes,
        "cache_hit": cache_hit,
        "error": error,
    }
    recorder.add(row)
    return response, row


def assert_ok(response: requests.Response | None, row: dict[str, Any], group: str) -> None:
    if response is None:
        raise RuntimeError(f"{group} failed: {row.get('error')}")
    if not 200 <= int(response.status_code) < 300:
        text = response.text[:240].replace("\n", " ")
        raise RuntimeError(f"{group} returned HTTP {response.status_code}: {text}")


def login_flow(base: str, recorder: Recorder, username: str, password: str, scenario: str) -> dict[str, Any]:
    session = requests.Session()
    started = time.perf_counter()
    token = login_only(base, recorder, session, username, password, scenario)
    marks = warmup_flow(base, recorder, session, username, token, scenario, started)
    return {
        "username": username,
        "scenario": scenario,
        "marks": marks,
        "request_count": 8,
    }


def login_only(
    base: str,
    recorder: Recorder,
    session: requests.Session,
    username: str,
    password: str,
    scenario: str,
) -> str:
    response, row = call_http(
        session,
        recorder,
        base,
        scenario,
        username,
        "username_check",
        "GET",
        f"/auth/username?username={quote(username)}",
    )
    assert_ok(response, row, "username_check")
    username_payload = response.json()
    if username_payload.get("exists") is not True:
        raise RuntimeError(f"{username} does not exist according to /auth/username")

    response, row = call_http(
        session,
        recorder,
        base,
        scenario,
        username,
        "login",
        "POST",
        "/auth/login",
        json_body={"username": username, "password": password},
    )
    assert_ok(response, row, "login")
    login_payload = response.json()
    token = str(login_payload.get("token") or "")
    if not token:
        raise RuntimeError(f"/auth/login did not return a token for {username}")
    return token


def warmup_flow(
    base: str,
    recorder: Recorder,
    session: requests.Session,
    username: str,
    token: str,
    scenario: str,
    started: float | None = None,
) -> dict[str, float]:
    started = started or time.perf_counter()
    marks: dict[str, float] = {"login_start_ms": 0.0}
    marks["login_done_ms"] = round((time.perf_counter() - started) * 1000, 3)
    response, row = call_http(session, recorder, base, scenario, username, "auth_me", "GET", "/auth/me", token=token)
    assert_ok(response, row, "auth_me")
    me_payload = response.json()
    if str(me_payload.get("username") or "").lower() != username.lower():
        raise RuntimeError(f"/auth/me username mismatch for {username}")
    marks["auth_me_done_ms"] = round((time.perf_counter() - started) * 1000, 3)

    response, row = call_http(
        session,
        recorder,
        base,
        scenario,
        username,
        "login_preload",
        "GET",
        f"/server-data/login-preload?username={quote(username)}&response=compact-v2",
        token=token,
    )
    assert_ok(response, row, "login_preload")
    marks["lesson_vault_usable_ms"] = round((time.perf_counter() - started) * 1000, 3)

    response, row = call_http(session, recorder, base, scenario, username, "tree_preload", "GET", "/server-data/tree-preload", token=token)
    assert_ok(response, row, "tree_preload")
    marks["warm_cache_done_ms"] = round((time.perf_counter() - started) * 1000, 3)

    response, row = call_http(session, recorder, base, scenario, username, "vocab_registry", "GET", "/vocab/registry", token=token)
    assert_ok(response, row, "vocab_registry")

    response, row = call_http(
        session,
        recorder,
        base,
        scenario,
        username,
        "leaderboard",
        "GET",
        "/vocab/leaderboard?scope=day&type=space_v&limit=20",
        token=token,
    )
    assert_ok(response, row, "leaderboard")
    marks["top_usable_ms"] = round((time.perf_counter() - started) * 1000, 3)

    space_v_path = f"{username}/{DEFAULT_SPACE_V_FOLDER}"
    response, row = call_http(
        session,
        recorder,
        base,
        scenario,
        username,
        "space_v_metadata",
        "GET",
        f"/server-data/list?path={quote(space_v_path)}",
        token=token,
    )
    assert_ok(response, row, "space_v_metadata")
    marks["space_v_metadata_usable_ms"] = round((time.perf_counter() - started) * 1000, 3)
    marks["flow_done_ms"] = round((time.perf_counter() - started) * 1000, 3)
    return marks


def same_user_two_tabs_flow(base: str, recorder: Recorder, username: str, password: str, scenario: str) -> list[dict[str, Any]]:
    session_a = requests.Session()
    started = time.perf_counter()
    token = login_only(base, recorder, session_a, username, password, scenario)
    session_b = requests.Session()
    session_b.cookies.update(session_a.cookies)
    def tab_flow(session: requests.Session) -> dict[str, Any]:
        marks = warmup_flow(base, recorder, session, username, token, scenario, started)
        return {"username": username, "scenario": scenario, "marks": marks, "request_count": 6}

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(tab_flow, session_a), pool.submit(tab_flow, session_b)]
        rows = []
        for future in as_completed(futures):
            try:
                rows.append(future.result())
            except Exception as exc:
                rows.append(
                    {
                        "scenario": scenario,
                        "username": username,
                        "error": f"{type(exc).__name__}: {exc}",
                        "marks": {},
                        "request_count": 0,
                    }
                )
    return rows


def health(base: str) -> dict[str, Any]:
    response = requests.get(base.rstrip("/") + "/health?view=dashboard-v1", timeout=20)
    response.raise_for_status()
    return response.json()


def process_sample(process: psutil.Process) -> dict[str, Any]:
    with process.oneshot():
        memory = process.memory_info()
        sqlite_handles = 0
        try:
            sqlite_handles = sum(1 for item in process.open_files() if item.path.lower().endswith((".db", ".db-wal", ".db-shm")) and "server2" in item.path.lower())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            sqlite_handles = -1
        return {
            "pid": process.pid,
            "cpu_seconds": round(cpu_seconds(process), 6),
            "rss_bytes": int(memory.rss),
            "vms_bytes": int(memory.vms),
            "threads": int(process.num_threads()),
            "status": process.status(),
            "sqlite_server2_handles": sqlite_handles,
        }


def postgres_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    left = before.get("postgres") if isinstance(before, dict) else {}
    right = after.get("postgres") if isinstance(after, dict) else {}
    if not isinstance(left, dict) or not isinstance(right, dict):
        return {"available": False}
    numeric_keys = sorted(set(left) | set(right))
    delta = {"available": True}
    for key in numeric_keys:
        try:
            delta[key] = round(float(right.get(key, 0) or 0) - float(left.get(key, 0) or 0), 6)
        except (TypeError, ValueError):
            delta[key] = right.get(key)
    return delta


def run_serial_flows(base: str, recorder: Recorder, accounts: dict[str, str], scenario: str, rounds: int) -> list[dict[str, Any]]:
    flows = []
    for _ in range(rounds):
        for username, password in accounts.items():
            flows.append(login_flow(base, recorder, username, password, scenario))
    return flows


def run_parallel_flows(
    base: str,
    recorder: Recorder,
    items: list[tuple[str, str]],
    scenario: str,
    rounds: int,
) -> list[dict[str, Any]]:
    flows = []
    for _ in range(rounds):
        with ThreadPoolExecutor(max_workers=len(items)) as pool:
            futures = [pool.submit(login_flow, base, recorder, username, password, scenario) for username, password in items]
            for future in as_completed(futures):
                try:
                    flows.append(future.result())
                except Exception as exc:
                    flows.append(
                        {
                            "scenario": scenario,
                            "username": "",
                            "error": f"{type(exc).__name__}: {exc}",
                            "marks": {},
                            "request_count": 0,
                        }
                    )
    return flows


def capture_flow_error(callback, scenario: str, username: str) -> dict[str, Any]:
    try:
        return callback()
    except Exception as exc:
        return {
            "scenario": scenario,
            "username": username,
            "error": f"{type(exc).__name__}: {exc}",
            "marks": {},
            "request_count": 0,
        }


def source_hashes() -> dict[str, Any]:
    rows = {}
    for rel in SOURCE_HASH_FILES:
        path = ROOT / rel
        rows[str(rel).replace("\\", "/")] = {
            "exists": path.exists(),
            "sha256": sha256_file(path) if path.exists() else "",
            "bytes": path.stat().st_size if path.exists() else 0,
        }
    return rows


def password_hash(value: str, salt: str = "") -> str:
    salt = str(salt or "").strip() or secrets.token_urlsafe(18)
    digest = hashlib.pbkdf2_hmac("sha256", str(value or "").encode("utf-8"), salt.encode("utf-8"), 2)
    return "pbkdf2_sha256$2$" + salt + "$" + base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def pg_dsn() -> str:
    dsn = os.environ.get("FUTURE_PG_DSN", "")
    if not dsn:
        raise RuntimeError("FUTURE_PG_DSN is required for fixture setup/cleanup; it will not be printed")
    return dsn


def pg_fixture_summary() -> dict[str, Any]:
    tables = {
        "users": "username",
        "server_load_test_credentials": "username",
        "user_auth_credentials": "username",
        "auth_sessions": "username",
        "lesson_progress": "username",
        "lesson_progress_namespaces": "username",
        "lesson_time": "username",
        "lesson_time_credit_state": "username",
        "append_events": "username",
        "vocabulary_registry": "username",
        "vocabulary_events": "username",
        "daily_earn": "username",
        "weekly_earn": "username",
        "monthly_earn": "username",
        "npc_period_earn": "username",
    }
    with psycopg.connect(pg_dsn()) as connection, connection.cursor() as cursor:
        result: dict[str, Any] = {}
        for table, column in tables.items():
            cursor.execute(
                f"SELECT count(*) FROM future_server2.{table} WHERE lower({column}) LIKE %s",
                (FIXTURE_PREFIX + "%",),
            )
            result[table] = int(cursor.fetchone()[0] or 0)
        cursor.execute(
            """
            SELECT count(*) FROM future_server2.lesson_file_aliases
            WHERE active=true AND file_id<>'' AND lower(normalized_path) LIKE 'common/%%.space_v'
            """
        )
        result["available_space_v_lessons"] = int(cursor.fetchone()[0] or 0)
        return result


def cleanup_pg_fixtures() -> dict[str, Any]:
    statements = (
        "DELETE FROM future_server2.auth_sessions WHERE lower(username) LIKE %s",
        "DELETE FROM future_server2.lesson_time_credit_state WHERE lower(username) LIKE %s",
        "DELETE FROM future_server2.lesson_time WHERE lower(username) LIKE %s",
        "DELETE FROM future_server2.lesson_progress WHERE lower(username) LIKE %s",
        "DELETE FROM future_server2.lesson_progress_namespaces WHERE lower(username) LIKE %s",
        "DELETE FROM future_server2.append_events WHERE lower(username) LIKE %s OR lower(event_key) LIKE %s",
        "DELETE FROM future_server2.vocabulary_events WHERE lower(username) LIKE %s",
        "DELETE FROM future_server2.vocabulary_registry WHERE lower(username) LIKE %s",
        "DELETE FROM future_server2.daily_earn WHERE lower(username) LIKE %s",
        "DELETE FROM future_server2.weekly_earn WHERE lower(username) LIKE %s",
        "DELETE FROM future_server2.monthly_earn WHERE lower(username) LIKE %s",
        "DELETE FROM future_server2.npc_period_earn WHERE lower(username) LIKE %s",
        "DELETE FROM future_server2.server_load_test_credentials WHERE lower(username) LIKE %s",
        "DELETE FROM future_server2.user_auth_credentials WHERE lower(username) LIKE %s",
        "DELETE FROM future_server2.users WHERE lower(username) LIKE %s",
    )
    deleted: dict[str, int] = {}
    with psycopg.connect(pg_dsn()) as connection, connection.cursor() as cursor:
        for statement in statements:
            if "event_key" in statement:
                cursor.execute(statement, (FIXTURE_PREFIX + "%", FIXTURE_PREFIX + "%"))
            else:
                cursor.execute(statement, (FIXTURE_PREFIX + "%",))
            table = statement.split("future_server2.", 1)[1].split(" ", 1)[0]
            deleted[table] = deleted.get(table, 0) + int(cursor.rowcount or 0)
        connection.commit()
    return deleted


def load_fixture_lessons(limit: int = 2) -> list[dict[str, str]]:
    with psycopg.connect(pg_dsn()) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT normalized_path,file_id FROM future_server2.lesson_file_aliases
            WHERE active=true AND file_id<>'' AND lower(normalized_path) LIKE 'common/%%.space_v'
            ORDER BY normalized_path LIMIT %s
            """,
            (limit,),
        )
        rows = cursor.fetchall()
    if len(rows) < limit:
        raise RuntimeError(f"Need {limit} canonical Space_V lessons for login dirty benchmark fixtures, found {len(rows)}")
    return [{"path": str(row[0]), "lesson_id": str(row[1])} for row in rows]


def provision_pg_fixtures(password: str) -> list[dict[str, str]]:
    lessons = load_fixture_lessons(len(FIXTURE_USERS))
    now = utc_now()
    hashed = password_hash(password)
    with psycopg.connect(pg_dsn()) as connection, connection.cursor() as cursor:
        for index, username in enumerate(FIXTURE_USERS, start=1):
            profile = json.dumps({"full_name": f"Codex Login Bench {index:03d}", "load_test": True}, separators=(",", ":"))
            cursor.execute(
                """
                INSERT INTO future_server2.users(username,is_admin,is_test,profile_json,updated_at_utc)
                VALUES(%s,false,true,%s::jsonb,%s)
                ON CONFLICT(username) DO UPDATE SET
                  is_admin=false,is_test=true,profile_json=excluded.profile_json,updated_at_utc=excluded.updated_at_utc
                """,
                (username, profile, now),
            )
            cursor.execute(
                """
                INSERT INTO future_server2.server_load_test_credentials(username,password_hash,updated_at_utc)
                VALUES(%s,%s,%s)
                ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash,updated_at_utc=excluded.updated_at_utc
                """,
                (username, hashed, now),
            )
            cursor.execute(
                """
                INSERT INTO future_server2.user_auth_credentials(username,password_hash,source_path,updated_at_utc,updated_epoch)
                VALUES(%s,%s,%s,%s,extract(epoch from now()))
                ON CONFLICT(username) DO UPDATE SET
                  password_hash=excluded.password_hash,
                  source_path=excluded.source_path,
                  updated_at_utc=excluded.updated_at_utc,
                  updated_epoch=excluded.updated_epoch
                """,
                (username, hashed, rf"C:\QMLearn\users\{username}.txt", now),
            )
        connection.commit()
    return lessons


def progress_dirty_flow(
    base: str,
    recorder: Recorder,
    username: str,
    password: str,
    lesson: dict[str, str],
) -> dict[str, Any]:
    session = requests.Session()
    started = time.perf_counter()
    token = login_only(base, recorder, session, username, password, "progress_dirty")
    stamp = utc_now()
    run_id = f"{FIXTURE_PREFIX}-progress-run"
    payload = {
        "action": "autosave",
        "path": lesson["path"],
        "identity": lesson["lesson_id"],
        "lesson_id": lesson["lesson_id"],
        "title": Path(lesson["path"]).stem,
        "savedAt": stamp,
        "updatedAt": stamp,
        "runId": run_id,
        "activeRun": True,
        "syncOperationId": f"{FIXTURE_PREFIX}-progress-op",
        "complete": False,
        "completedRuns": 0,
        "nodeIndex": 1,
        "nodeCount": 25,
        "learnedCount": 1,
        "learned": [f"{FIXTURE_PREFIX}-word-001"],
        "state": {
            "savedAt": stamp,
            "updatedAt": stamp,
            "runId": run_id,
            "activeRun": True,
            "syncOperationId": f"{FIXTURE_PREFIX}-progress-op",
            "complete": False,
            "lessonComplete": False,
            "completedRuns": 0,
            "currentIndex": 1,
            "nodeCount": 25,
            "learnedCount": 1,
            "learned": [f"{FIXTURE_PREFIX}-word-001"],
        },
    }
    response, row = call_http(
        session,
        recorder,
        base,
        "progress_dirty",
        username,
        "progress_dirty_write",
        "POST",
        "/space-v/progress?client_source=login_postgres_benchmark&response=compact-v1",
        token=token,
        json_body=payload,
        timeout=45,
    )
    assert_ok(response, row, "progress_dirty_write")
    marks = warmup_flow(base, recorder, session, username, token, "progress_dirty", started)
    return {"username": username, "scenario": "progress_dirty", "marks": marks, "request_count": 9}


def vocabulary_dirty_flow(
    base: str,
    recorder: Recorder,
    username: str,
    password: str,
    lesson: dict[str, str],
) -> dict[str, Any]:
    session = requests.Session()
    started = time.perf_counter()
    token = login_only(base, recorder, session, username, password, "vocabulary_leaderboard_dirty")
    stamp = utc_now()
    payload = {
        "path": lesson["path"],
        "lesson_id": lesson["lesson_id"],
        "file_id": lesson["lesson_id"],
        "title": f"Codex Login Bench {username}",
        "nodes": 1,
        "completed_at": stamp,
        "completion_run_id": f"{FIXTURE_PREFIX}-complete-run",
        "source": "Space_V",
    }
    response, row = call_http(
        session,
        recorder,
        base,
        "vocabulary_leaderboard_dirty",
        username,
        "vocabulary_dirty_complete",
        "POST",
        "/lesson/complete",
        token=token,
        json_body=payload,
        timeout=120,
    )
    assert_ok(response, row, "vocabulary_dirty_complete")
    marks = warmup_flow(base, recorder, session, username, token, "vocabulary_leaderboard_dirty", started)
    return {"username": username, "scenario": "vocabulary_leaderboard_dirty", "marks": marks, "request_count": 9}


def endpoint_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in records:
        groups.setdefault(str(row["group"]), []).append(row)
    result = {}
    for group, rows in groups.items():
        durations = [float(row["duration_ms"]) for row in rows]
        statuses = {str(status): sum(1 for row in rows if int(row["status"]) == status) for status in sorted({int(row["status"]) for row in rows})}
        result[group] = {
            **summarise(durations),
            "statuses": statuses,
            "errors": sum(1 for row in rows if row.get("error") or int(row.get("status") or 0) >= 400),
            "response_bytes": sum(int(row.get("response_bytes") or 0) for row in rows),
            "wire_response_bytes": sum(int(row.get("wire_response_bytes") or 0) for row in rows),
            "request_bytes": sum(int(row.get("request_bytes") or 0) for row in rows),
            "cache_hit_values": sorted({str(row.get("cache_hit") or "") for row in rows if row.get("cache_hit")}),
        }
    return result


def flow_metrics(flows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = (
        "login_done_ms",
        "auth_me_done_ms",
        "lesson_vault_usable_ms",
        "warm_cache_done_ms",
        "top_usable_ms",
        "space_v_metadata_usable_ms",
        "flow_done_ms",
    )
    result = {}
    for key in keys:
        result[key] = summarise([float(flow["marks"][key]) for flow in flows if key in flow.get("marks", {})])
    return result


def write_outputs(prefix: str, output_dir: Path, raw: dict[str, Any], records: list[dict[str, Any]], overwrite: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "raw": output_dir / f"{prefix}_raw.json",
        "summary": output_dir / f"{prefix}_summary.md",
        "requests": output_dir / f"{prefix}_requests.csv",
        "environment": output_dir / f"{prefix}_environment.json",
        "source_hashes": output_dir / f"{prefix}_source_hashes.json",
    }
    existing = [str(path) for path in paths.values() if path.exists()]
    if existing and not overwrite:
        raise RuntimeError("Refusing to overwrite existing benchmark outputs: " + ", ".join(existing))

    paths["raw"].write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["environment"].write_text(json.dumps(raw["environment"], ensure_ascii=False, indent=2), encoding="utf-8")
    paths["source_hashes"].write_text(json.dumps(raw["source_hashes"], ensure_ascii=False, indent=2), encoding="utf-8")
    with paths["requests"].open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "timestamp_utc",
            "scenario",
            "username",
            "group",
            "method",
            "path_group",
            "status",
            "duration_ms",
            "response_bytes",
            "wire_response_bytes",
            "request_bytes",
            "cache_hit",
            "error",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in records:
            writer.writerow({key: row.get(key, "") for key in fieldnames})

    summary = raw["summary"]
    lines = [
        f"# {prefix} login PostgreSQL benchmark",
        "",
        f"- status: {raw['status']}",
        f"- timestamp_utc: {raw['timestamp_utc']}",
        f"- mode: {raw['mode']}",
        f"- server_pid: {raw['environment']['server_pid']}",
        f"- postgres_only: {raw['environment']['postgres_only']}",
        f"- sqlite_writer_enabled: {raw['environment']['sqlite_writer_enabled']}",
        f"- users: {', '.join(raw['users'])}",
        f"- total_requests: {summary['total_requests']}",
        f"- errors: {summary['errors']}",
        f"- total_wall_ms: {summary['total_wall_ms']}",
        f"- total_server_cpu_ms: {summary['total_server_cpu_ms']}",
        f"- cpu_ms_per_login_flow: {summary['cpu_ms_per_login_flow']}",
        "",
        "## User-visible flow",
        "",
        "| metric | count | p50 ms | p95 ms | p99 ms | max ms |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, value in summary["flow_metrics"].items():
        lines.append(
            f"| {key} | {value.get('count', 0)} | {value.get('p50_ms', 'NOT MEASURED')} | "
            f"{value.get('p95_ms', 'NOT MEASURED')} | {value.get('p99_ms', 'NOT MEASURED')} | "
            f"{value.get('max_ms', 'NOT MEASURED')} |"
        )
    lines.extend(["", "## Endpoint metrics", "", "| endpoint | count | p50 ms | p95 ms | p99 ms | errors |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
    for key, value in summary["endpoint_metrics"].items():
        lines.append(
            f"| {key} | {value.get('count', 0)} | {value.get('p50_ms', 'NOT MEASURED')} | "
            f"{value.get('p95_ms', 'NOT MEASURED')} | {value.get('p99_ms', 'NOT MEASURED')} | "
            f"{value.get('errors', 0)} |"
        )
    lines.extend(["", "## Scenario coverage", ""])
    for key, value in raw["scenario_coverage"].items():
        lines.append(f"- {key}: {value}")
    paths["summary"].write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_accounts() -> dict[str, str]:
    users = tuple(item.strip().lower() for item in os.environ.get("FUTURE_LOGIN_BENCH_USERS", ",".join(DEFAULT_USERS)).split(",") if item.strip())
    passwords_json = os.environ.get("FUTURE_LOGIN_BENCH_PASSWORDS_JSON", "")
    passwords = json.loads(passwords_json) if passwords_json else {}
    accounts = {}
    missing = []
    for username in users:
        value = passwords.get(username) or os.environ.get(f"FUTURE_LOGIN_BENCH_PASSWORD_{username.upper()}", "")
        if not value:
            missing.append(username)
        else:
            accounts[username] = str(value)
    if missing:
        raise RuntimeError("Missing benchmark passwords for users: " + ", ".join(missing))
    return accounts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--port", type=int, default=8877)
    parser.add_argument("--prefix", default="baseline_current")
    parser.add_argument("--mode", choices=("trace", "measurement"), default="measurement")
    parser.add_argument("--warm-rounds", type=int, default=20)
    parser.add_argument("--warmup-rounds", type=int, default=5)
    parser.add_argument("--cold-rounds", type=int, default=5)
    parser.add_argument("--parallel-rounds", type=int, default=5)
    parser.add_argument("--observe-seconds", type=float, default=30.0)
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    accounts = parse_accounts()
    fixture_password = os.environ.get("FUTURE_LOGIN_BENCH_FIXTURE_PASSWORD", "codexloginbench-local-only")
    process = server_process(args.port)
    before_health = health(args.base)
    sqlite_writer = before_health.get("sqlite_writer") if isinstance(before_health, dict) else {}
    postgres_only = bool(isinstance(sqlite_writer, dict) and sqlite_writer.get("postgres_only") is True and sqlite_writer.get("enabled") is False)
    if not postgres_only:
        raise RuntimeError("Server health does not prove PostgreSQL-only runtime")

    recorder = Recorder()
    process_before = process_sample(process)
    cpu_before = cpu_seconds(process)
    wall_started = time.perf_counter()

    flows: list[dict[str, Any]] = []
    unmeasured: dict[str, str] = {}
    fixture_cleanup_before = cleanup_pg_fixtures()
    fixture_summary_before = pg_fixture_summary()
    fixture_lessons: list[dict[str, str]] = []
    fixture_summary_after_provision: dict[str, Any] = {}
    fixture_cleanup_after: dict[str, Any] = {}
    fixture_summary_after_cleanup: dict[str, Any] = {}
    try:
        fixture_lessons = provision_pg_fixtures(fixture_password)
        fixture_summary_after_provision = pg_fixture_summary()

        for _ in range(max(0, args.warmup_rounds)):
            for username, password in accounts.items():
                login_flow(args.base, Recorder(), username, password, "warmup_unmeasured")
        flows.extend(run_serial_flows(args.base, recorder, accounts, "warm_login", args.warm_rounds))
        flows.extend(run_serial_flows(args.base, recorder, accounts, "cold_snapshot_fresh_session", args.cold_rounds))

        first_user = next(iter(accounts))
        for _ in range(args.parallel_rounds):
            flows.extend(same_user_two_tabs_flow(args.base, recorder, first_user, accounts[first_user], "same_user_two_tabs"))
        if len(accounts) >= 2:
            flows.extend(run_parallel_flows(args.base, recorder, list(accounts.items())[:2], "two_users_parallel", args.parallel_rounds))
        else:
            unmeasured["two_users_parallel"] = "requires at least two configured users"

        flows.append(
            capture_flow_error(
                lambda: progress_dirty_flow(args.base, recorder, FIXTURE_USERS[0], fixture_password, fixture_lessons[0]),
                "progress_dirty",
                FIXTURE_USERS[0],
            )
        )
        flows.append(
            capture_flow_error(
                lambda: vocabulary_dirty_flow(args.base, recorder, FIXTURE_USERS[1], fixture_password, fixture_lessons[1]),
                "vocabulary_leaderboard_dirty",
                FIXTURE_USERS[1],
            )
        )

        # Added 2026-07-30: isolate post-login background CPU from request CPU.
        observe_cpu_before = cpu_seconds(process)
        observe_started = time.perf_counter()
        time.sleep(max(0.0, float(args.observe_seconds)))
        observe_wall_ms = round((time.perf_counter() - observe_started) * 1000, 3)
        observe_server_cpu_ms = round(max(0.0, (cpu_seconds(process) - observe_cpu_before) * 1000), 3)
    finally:
        fixture_cleanup_after = cleanup_pg_fixtures()
        fixture_summary_after_cleanup = pg_fixture_summary()

    total_wall_ms = round((time.perf_counter() - wall_started) * 1000, 3)
    total_cpu_ms = round(max(0.0, (cpu_seconds(process) - cpu_before) * 1000), 3)
    process_after = process_sample(process)
    after_health = health(args.base)
    requests_rows = recorder.records
    errors = sum(1 for row in requests_rows if row.get("error") or int(row.get("status") or 0) >= 400)
    flow_errors = [flow for flow in flows if flow.get("error")]
    hash_rows = source_hashes()
    harness_hash = hash_rows.get("FUTURE/tools/benchmark_login_warmup_postgres.py", {}).get("sha256", "")

    environment = {
        "timestamp_utc": utc_now(),
        "base": args.base,
        "server_pid": process.pid,
        "python": sys.version,
        "platform": platform.platform(),
        "cpu_logical": psutil.cpu_count(logical=True),
        "cpu_physical": psutil.cpu_count(logical=False),
        "ram_total_bytes": psutil.virtual_memory().total,
        "postgres": after_health.get("postgres") if isinstance(after_health, dict) else {},
        "sqlite_writer_enabled": sqlite_writer.get("enabled") if isinstance(sqlite_writer, dict) else None,
        "postgres_only": postgres_only,
        "sqlite_handles": process_after.get("sqlite_server2_handles"),
        "env_flags_redacted": {
            key: ("<set>" if any(token in key.upper() for token in ("DSN", "PASS", "TOKEN", "SECRET", "PASSWORD")) else value)
            for key, value in os.environ.items()
            if key.startswith("FUTURE_")
        },
    }
    summary = {
        "result_schema_version": RESULT_SCHEMA_VERSION,
        "workload_version": WORKLOAD_VERSION,
        "scenario_names": list(SCENARIO_NAMES),
        "scenario_rounds": {
            "warmup_unmeasured_per_user": args.warmup_rounds,
            "warm_login_per_user": args.warm_rounds,
            "cold_snapshot_fresh_session_per_user": args.cold_rounds,
            "same_user_two_tabs_rounds": args.parallel_rounds,
            "two_users_parallel_rounds": args.parallel_rounds if len(accounts) >= 2 else 0,
            "progress_dirty_runs": 1,
            "vocabulary_leaderboard_dirty_runs": 1,
            "observe_seconds": float(args.observe_seconds),
        },
        "total_requests": len(requests_rows),
        "errors": errors,
        "flow_errors": len(flow_errors),
        "total_wall_ms": total_wall_ms,
        "observe_window_ms": observe_wall_ms,
        "observe_server_cpu_ms": observe_server_cpu_ms,
        "observe_server_machine_cpu_percent": round(
            (observe_server_cpu_ms / max(1.0, observe_wall_ms)) / max(1, psutil.cpu_count(logical=True)) * 100,
            4,
        ),
        "total_server_cpu_ms": total_cpu_ms,
        "cpu_ms_per_login_flow": round(total_cpu_ms / max(1, len(flows)), 3),
        "process_before": process_before,
        "process_after": process_after,
        "postgres_delta": postgres_delta(before_health, after_health),
        "fixture_summary": {
            "cleanup_before": fixture_cleanup_before,
            "before": fixture_summary_before,
            "after_provision": fixture_summary_after_provision,
            "cleanup_after": fixture_cleanup_after,
            "after_cleanup": fixture_summary_after_cleanup,
            "fixture_users": list(FIXTURE_USERS),
            "fixture_lessons": fixture_lessons,
        },
        "flow_metrics": flow_metrics(flows),
        "endpoint_metrics": endpoint_metrics(requests_rows),
    }
    scenario_coverage = {
        "warm_login": f"measured {args.warm_rounds} rounds per user after {args.warmup_rounds} unmeasured warmup rounds",
        "cold_snapshot_fresh_session": f"measured {args.cold_rounds} rounds per user with fresh HTTP session each flow",
        "same_user_two_tabs": f"measured {args.parallel_rounds} concurrent two-tab rounds for {first_user}",
        "two_users_parallel": f"measured {args.parallel_rounds} concurrent rounds" if len(accounts) >= 2 else unmeasured["two_users_parallel"],
        "progress_dirty": "measured once using PostgreSQL load-test fixture user and cleaned by prefix",
        "vocabulary_leaderboard_dirty": "measured once using PostgreSQL load-test fixture user and cleaned by prefix",
        **unmeasured,
    }
    status = "PASS" if errors == 0 and not flow_errors and not unmeasured else "PARTIAL"
    raw = {
        "result_schema_version": RESULT_SCHEMA_VERSION,
        "workload_version": WORKLOAD_VERSION,
        "status": status,
        "timestamp_utc": utc_now(),
        "mode": args.mode,
        "harness_sha256": harness_hash,
        "users": list(accounts),
        "summary": summary,
        "scenario_coverage": scenario_coverage,
        "environment": environment,
        "source_hashes": hash_rows,
        "flows": flows,
        "not_measured": unmeasured,
    }
    write_outputs(args.prefix, Path(args.output_dir), raw, requests_rows, args.overwrite)
    print(f"CURRENT POSTGRES LOGIN BASELINE: {status}")
    print(f"output_dir={Path(args.output_dir)} prefix={args.prefix}")
    print(f"requests={len(requests_rows)} errors={errors} cpu_ms_per_login_flow={summary['cpu_ms_per_login_flow']}")
    print(f"login_p95_ms={summary['flow_metrics']['login_done_ms'].get('p95_ms')}")
    print(f"warm_complete_p95_ms={summary['flow_metrics']['warm_cache_done_ms'].get('p95_ms')}")
    print(f"top_p95_ms={summary['flow_metrics']['top_usable_ms'].get('p95_ms')}")
    print(f"space_v_p95_ms={summary['flow_metrics']['space_v_metadata_usable_ms'].get('p95_ms')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
