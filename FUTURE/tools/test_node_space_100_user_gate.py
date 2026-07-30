#!/usr/bin/env python3
"""Reproducible 100-user A/B gate for node-space completion and Top."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import random
import secrets
import shutil
import statistics
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.tools.test_lesson_complete_isolated_harness as isolated

RUN_ROOT = ROOT / "programe_cache" / "node_space_100_user_gate_18877"
OUTPUT = Path(r"C:\Users\Admin\.codex\plans\node_space_100_user_gate_20260729.json")
DOM_MARKER = RUN_ROOT / "dom_result.json"
SNAPSHOT_DUMP = RUN_ROOT / "production_snapshot.dump"
SNAPSHOT_META = RUN_ROOT / "production_snapshot_meta.json"
USER_COUNT = 100
COMPLETIONS_PER_USER = 5
COLD_COUNT = 20
RETRY_COUNT = 25
MAX_WORKERS = 20
RUN_MAX_WORKERS = MAX_WORKERS
HOT_TOP_LIMIT = 80
SPACE_TYPES = ("space_q", "space_w", "space_p", "space_l", "space_s")
EXTENSIONS = {
    "space_q": ".Space_Q",
    "space_w": ".Space_W",
    "space_p": ".Space_P",
    "space_l": ".Space_L",
    "space_s": ".Space_S",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    rows = sorted(float(value) for value in values)
    index = max(0, min(len(rows) - 1, math.ceil(len(rows) * fraction) - 1))
    return round(rows[index], 3)


def distribution(values: list[float]) -> dict:
    rows = [float(value) for value in values]
    return {
        "count": len(rows),
        "min": round(min(rows), 3) if rows else 0.0,
        "mean": round(statistics.mean(rows), 3) if rows else 0.0,
        "p50": percentile(rows, 0.50),
        "p95": percentile(rows, 0.95),
        "p99": percentile(rows, 0.99),
        "max": round(max(rows), 3) if rows else 0.0,
    }


def configure_paths() -> None:
    isolated.RUN_ROOT = RUN_ROOT
    isolated.PG_ROOT = RUN_ROOT / "postgres"
    isolated.SERVER_DATA_ROOT = RUN_ROOT / "server-data"
    isolated.RUNTIME_ROOT = RUN_ROOT / "runtime"
    isolated.QMLEARN_ROOT = RUN_ROOT / "qml"
    isolated.SERVER_LOG = RUN_ROOT / "server.log"
    isolated.PG_LOG = RUN_ROOT / "postgres.log"


def safe_clean_mode_data() -> None:
    targets = [isolated.SERVER_DATA_ROOT, isolated.RUNTIME_ROOT, isolated.QMLEARN_ROOT]
    resolved_root = RUN_ROOT.resolve()
    for target in targets:
        resolved = target.resolve()
        if resolved_root not in resolved.parents:
            raise RuntimeError(f"refusing to clean outside isolated root: {resolved}")
        shutil.rmtree(resolved, ignore_errors=True)
    for target in targets:
        target.mkdir(parents=True, exist_ok=True)
    for name in ("Sound", "Picture", "NPC_TOP"):
        (isolated.SERVER_DATA_ROOT / name).mkdir(parents=True, exist_ok=True)
    isolated.SERVER_LOG.write_text("", encoding="utf-8")


def dump_production_once() -> dict:
    started = utc_now()
    command = [
        str(isolated.PG_BIN / "pg_dump.exe"),
        isolated.PRODUCTION_DSN,
        "--format=custom",
        "--schema=future_server2",
        "--no-owner",
        "--no-privileges",
        "--file",
        str(SNAPSHOT_DUMP),
    ]
    isolated.run(command, timeout=900)
    meta = {
        "enabled": True,
        "source": isolated.PRODUCTION_DSN.replace("future_server2_app@", "***@"),
        "target": isolated.PG_DSN.replace("future_server2_app@", "***@"),
        "method": "single pg_dump reused by baseline and manifest via pg_restore",
        "snapshot_started_at_utc": started,
        "snapshot_finished_at_utc": utc_now(),
        "dump_path": str(SNAPSHOT_DUMP),
        "dump_bytes": SNAPSHOT_DUMP.stat().st_size,
        "sha256": hashlib.sha256(SNAPSHOT_DUMP.read_bytes()).hexdigest(),
    }
    SNAPSHOT_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def restore_snapshot() -> None:
    subprocess.run(
        [str(isolated.PG_BIN / "dropdb.exe"), "-h", "127.0.0.1", "-p", str(isolated.PG_PORT), "-U", "future_server2_app", "--if-exists", isolated.TEST_DATABASE],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    isolated.run([
        str(isolated.PG_BIN / "createdb.exe"), "-h", "127.0.0.1", "-p", str(isolated.PG_PORT),
        "-U", "future_server2_app", isolated.TEST_DATABASE,
    ], timeout=120)
    isolated.run([
        str(isolated.PG_BIN / "pg_restore.exe"), "--no-owner", "--no-privileges",
        "--dbname", isolated.PG_DSN, str(SNAPSHOT_DUMP),
    ], timeout=900)


def select_lessons() -> dict[str, list[dict]]:
    manifest_path = Path(r"C:\server data\_future_server_data_manifest.json")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    folders = payload.get("folders") if isinstance(payload.get("folders"), dict) else {}
    selected = {}
    for space_type in SPACE_TYPES:
        extension = EXTENSIONS[space_type].lower()
        candidates = []
        for entries in folders.values():
            for entry in entries if isinstance(entries, list) else []:
                if not isinstance(entry, dict) or str(entry.get("extension", "")).lower() != extension:
                    continue
                path = str(entry.get("path", "")).replace("\\", "/")
                lesson_id = str(entry.get("lesson_id", ""))
                nodes = max(0, int(entry.get("nodes", 0) or 0))
                points = max(0, int(entry.get("total_nodes", 0) or 0), int(entry.get("questions", 0) or 0)) if space_type == "space_q" else nodes
                if not path.startswith("common/") or not lesson_id.startswith("ftg-lesson-") or nodes <= 0 or points <= 0 or len(path) > 190:
                    continue
                source = Path(r"C:\server data") / path.replace("/", "\\")
                if source.is_file():
                    candidates.append({"space_type": space_type, "path": path, "lesson_id": lesson_id, "nodes": nodes, "points": points, "source": str(source)})
        candidates.sort(key=lambda row: (len(row["path"]), row["points"], row["path"].lower()))
        unique_points = []
        used = set()
        for row in candidates:
            if row["points"] in used:
                continue
            unique_points.append(row)
            used.add(row["points"])
            if len(unique_points) == 5:
                break
        if len(unique_points) < 5:
            used_ids = {row["lesson_id"] for row in unique_points}
            unique_points.extend(row for row in candidates if row["lesson_id"] not in used_ids and len(unique_points) < 5)
        if len(unique_points) < 5:
            raise RuntimeError(f"not enough real lessons for {space_type}")
        selected[space_type] = unique_points[:5]
    return selected


def copy_lessons(lessons: dict[str, list[dict]]) -> None:
    for rows in lessons.values():
        for row in rows:
            source = Path(row["source"])
            target = isolated.SERVER_DATA_ROOT / row["path"].replace("/", "\\")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def test_username(index: int) -> str:
    return f"codexgate{index:03d}"


def raw_token(index: int, seed: int) -> str:
    return hashlib.sha256(f"isolated-node-gate|{seed}|{index}".encode()).hexdigest()


def password_hash(value: str) -> str:
    rounds = 2
    salt = secrets.token_urlsafe(18)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode(), salt.encode(), rounds)
    encoded = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return f"pbkdf2_sha256${rounds}${salt}${encoded}"


def provision_users(seed: int, password: str) -> dict[str, str]:
    import psycopg

    now_epoch = time.time()
    now = utc_now()
    tokens = {}
    with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
        for index in range(USER_COUNT):
            username = test_username(index)
            token = raw_token(index, seed)
            tokens[username] = token
            cursor.execute(
                """
                INSERT INTO future_server2.users
                    (username,is_admin,profile_json,updated_at_utc,updated_epoch,is_test,migrated_at_utc,source_sha256)
                VALUES (%s,false,%s,%s,%s,true,'','')
                ON CONFLICT(username) DO UPDATE SET is_admin=false,is_test=true,profile_json=excluded.profile_json
                """,
                (username, json.dumps({
                    "full_name": username,
                    "gender": "male",
                    "birth_date": "2000-01-01",
                    "load_test": True,
                    "source": "node-space-100-user-gate",
                }), now, now_epoch),
            )
            cursor.execute(
                """
                INSERT INTO future_server2.user_auth_credentials
                    (username,password_hash,source_path,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,'node-space-100-user-gate',%s,%s,'','')
                ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash,updated_at_utc=excluded.updated_at_utc
                """,
                (username, password_hash(password), now, now_epoch),
            )
            cursor.execute(
                """
                INSERT INTO future_server2.auth_sessions
                    (token_hash,username,created_epoch,last_seen_epoch,last_persisted_epoch,expires_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'','')
                ON CONFLICT(token_hash) DO UPDATE SET username=excluded.username,expires_epoch=excluded.expires_epoch
                """,
                (hashlib.sha256(token.encode()).hexdigest(), username, now_epoch, now_epoch, now_epoch, now_epoch + 86400, now, now_epoch),
            )
        connection.commit()
    return tokens


def build_events(seed: int, lessons: dict[str, list[dict]]) -> list[dict]:
    rng = random.Random(seed)
    events = []
    for user_index in range(USER_COUNT):
        username = test_username(user_index)
        space_order = list(SPACE_TYPES)
        duplicate_type = ""
        if user_index < 20:
            duplicate_type = SPACE_TYPES[user_index % len(SPACE_TYPES)]
            removed_type = SPACE_TYPES[(user_index + 1) % len(SPACE_TYPES)]
            space_order.remove(removed_type)
            space_order.append(duplicate_type)
        rng.shuffle(space_order)
        base_times = sorted(rng.uniform(0.0, 10.0) for _ in range(COMPLETIONS_PER_USER))
        duplicate_positions = [index for index, value in enumerate(space_order) if value == duplicate_type]
        if len(duplicate_positions) == 2:
            first_position, second_position = duplicate_positions
            base_times[second_position] = min(10.0, base_times[first_position] + rng.uniform(0.05, 0.20))
        elif user_index < 30:
            base_times[1] = min(10.0, base_times[0] + rng.uniform(0.05, 0.20))
        type_occurrences: dict[str, int] = {}
        for event_index, space_type in enumerate(space_order):
            occurrence = type_occurrences.get(space_type, 0)
            type_occurrences[space_type] = occurrence + 1
            lesson = lessons[space_type][(user_index + occurrence) % len(lessons[space_type])]
            event_id = f"gate-{seed}-{user_index:03d}-{event_index}-{space_type}"
            events.append({
                "username": username,
                "user_index": user_index,
                "space_type": space_type,
                "lesson": lesson,
                "run_id": event_id,
                "offset_seconds": round(base_times[event_index], 4),
                "same_space_pair": bool(duplicate_type and space_type == duplicate_type),
            })
    burst_rng = random.Random(seed ^ 0x5A17)
    for burst_index in range(10):
        burst_size = burst_rng.randint(5, 20)
        burst_at = burst_rng.uniform(0.3, 9.5)
        candidates = burst_rng.sample(events, burst_size)
        for event in candidates:
            event["offset_seconds"] = round(min(10.0, burst_at + burst_rng.uniform(0.0, 0.12)), 4)
            event["burst"] = burst_index
    events.sort(key=lambda row: (row["offset_seconds"], row["username"], row["space_type"]))
    for sequence, event in enumerate(events):
        event["sequence"] = sequence
    return events


def completion_body(event: dict) -> dict:
    lesson = event["lesson"]
    stamp = utc_now()
    return {
        "path": lesson["path"],
        "lesson_id": lesson["lesson_id"],
        "file_id": lesson["lesson_id"],
        "title": Path(lesson["path"]).stem,
        "name": Path(lesson["path"]).name,
        "nodes": lesson["nodes"],
        "completed_at": stamp,
        "completion_run_id": event["run_id"],
        "source": event["space_type"].replace("space_", "Space_").upper(),
        "completion_trace_id": f"gate-{event['sequence']:04d}-{secrets.token_hex(4)}",
    }


def select_balanced_cold_events(events: list[dict]) -> list[dict]:
    # Added 2026-07-29: cold measures startup contention across distinct users;
    # same-user locking remains covered by the scheduled warm workload.
    selected = []
    used_users = set()
    per_space = COLD_COUNT // len(SPACE_TYPES)
    for space_type in SPACE_TYPES:
        for event in events:
            if event["space_type"] != space_type or event["username"] in used_users:
                continue
            selected.append(event)
            used_users.add(event["username"])
            if sum(row["space_type"] == space_type for row in selected) >= per_space:
                break
    if len(selected) != COLD_COUNT:
        raise RuntimeError("could not select balanced distinct-user cold events")
    return selected


def wait_ready_only(server: subprocess.Popen) -> dict:
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        try:
            payload = requests.get(f"{isolated.BASE}/health?view=dashboard-v1", timeout=5).json()
            if int(payload.get("pid", 0) or 0) == server.pid and payload.get("ready"):
                return payload
        except Exception:
            pass
        time.sleep(0.1)
    raise RuntimeError("isolated Server 2 did not reach ready")


def wait_warm(server: subprocess.Popen) -> dict:
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        try:
            payload = requests.get(f"{isolated.BASE}/health?view=dashboard-v1", timeout=5).json()
            if int(payload.get("pid", 0) or 0) == server.pid and payload.get("ready") and payload.get("warm_ready"):
                return payload
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError("isolated Server 2 did not reach warm_ready")


def health() -> dict:
    return requests.get(f"{isolated.BASE}/health?view=dashboard-v1", timeout=10).json()


def top_row(payload: dict, username: str) -> dict | None:
    boards = payload.get("boards") if isinstance(payload.get("boards"), dict) else {}
    rows = boards.get("total") if isinstance(boards.get("total"), list) else payload.get("users", [])
    return next((row for row in rows if isinstance(row, dict) and str(row.get("username", "")).lower() == username.lower()), None)


class ThreadMonitor:
    def __init__(self, process: psutil.Process):
        self.process = process
        self.stop_event = threading.Event()
        self.peak = 0
        self.samples = 0
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self.stop_event.is_set():
            try:
                self.peak = max(self.peak, self.process.num_threads())
                self.samples += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return
            time.sleep(0.02)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.stop_event.set()
        self.thread.join(timeout=2)


class PostgresLockMonitor:
    # Added 2026-07-29: sample real PostgreSQL lock waits during the load gate.
    def __init__(self):
        self.stop_event = threading.Event()
        self.samples = 0
        self.samples_with_wait = 0
        self.max_waiters = 0
        self.max_ungranted_locks = 0
        self.max_query_wait_ms = 0.0
        self.errors = 0
        self.thread = threading.Thread(target=self._run, daemon=True, name="node-space-pg-lock-monitor")

    def _run(self) -> None:
        import psycopg

        try:
            with psycopg.connect(isolated.PG_DSN, autocommit=True) as connection, connection.cursor() as cursor:
                while not self.stop_event.is_set():
                    try:
                        cursor.execute(
                            """
                            SELECT
                                count(*) FILTER (WHERE wait_event_type='Lock'),
                                COALESCE(max(EXTRACT(EPOCH FROM (clock_timestamp()-query_start))*1000)
                                    FILTER (WHERE wait_event_type='Lock'), 0),
                                (SELECT count(*) FROM pg_locks WHERE NOT granted)
                            FROM pg_stat_activity
                            WHERE datname=current_database()
                            """
                        )
                        waiters, wait_ms, ungranted = cursor.fetchone()
                        waiters = int(waiters or 0)
                        ungranted = int(ungranted or 0)
                        self.samples += 1
                        self.max_waiters = max(self.max_waiters, waiters)
                        self.max_ungranted_locks = max(self.max_ungranted_locks, ungranted)
                        self.max_query_wait_ms = max(self.max_query_wait_ms, float(wait_ms or 0.0))
                        if waiters or ungranted:
                            self.samples_with_wait += 1
                    except Exception:
                        self.errors += 1
                    time.sleep(0.05)
        except Exception:
            self.errors += 1

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.stop_event.set()
        self.thread.join(timeout=2)


def request_event(process: psutil.Process, token: str, event: dict) -> dict:
    body = completion_body(event)
    completion_started = time.perf_counter()
    try:
        response = requests.post(
            f"{isolated.BASE}/lesson/complete",
            headers={"Authorization": f"Bearer {token}"},
            json=body,
            timeout=30,
        )
        completion_wall = (time.perf_counter() - completion_started) * 1000.0
        completion_bytes = len(response.content)
        payload = response.json()
    except Exception as exc:
        return {"event": event, "body": body, "error": str(exc), "timeout": isinstance(exc, requests.Timeout)}
    if response.status_code != 200:
        return {
            "event": event,
            "body": body,
            "status": response.status_code,
            "completion_wall_ms": round(completion_wall, 3),
            "completion_bytes": completion_bytes,
            "payload": payload,
            "error": str(payload.get("error", "") or "").strip() or f"completion status {response.status_code}",
            "timeout": False,
        }
    top_started = time.perf_counter()
    try:
        top_response = None
        top_payload = {}
        top_attempts = 0
        top_pending = False
        first_top_wall = 0.0
        first_completion_to_top = 0.0
        first_top_bytes = 0
        while True:
            top_attempts += 1
            top_response = requests.get(
                f"{isolated.BASE}/vocab/leaderboard",
                headers={"Authorization": f"Bearer {token}"},
                params={"limit": HOT_TOP_LIMIT, "double_check": 0, "scope": "total", "type": event["space_type"]},
                timeout=30,
            )
            top_payload = top_response.json()
            if top_attempts == 1:
                first_top_wall = (time.perf_counter() - top_started) * 1000.0
                first_completion_to_top = (time.perf_counter() - completion_started) * 1000.0
                first_top_bytes = len(top_response.content)
            top_pending = top_response.headers.get("X-Future-Top-Pending", "0") == "1"
            if not top_pending or (time.perf_counter() - top_started) >= 8.0:
                break
            retry_ms = max(100, min(1200, int(top_response.headers.get("X-Future-Top-Retry-Ms", "1000") or 1000)))
            time.sleep(retry_ms / 1000.0)
        top_wall = (time.perf_counter() - top_started) * 1000.0
        completion_to_top = (time.perf_counter() - completion_started) * 1000.0
        row = top_row(top_payload, event["username"])
    except Exception as exc:
        return {
            "event": event,
            "body": body,
            "status": response.status_code,
            "completion_wall_ms": round(completion_wall, 3),
            "completion_bytes": completion_bytes,
            "payload": payload,
            "error": f"top: {exc}",
            "timeout": isinstance(exc, requests.Timeout),
        }
    return {
        "event": event,
        "body": body,
        "status": response.status_code,
        "completion_wall_ms": round(completion_wall, 3),
        "completion_bytes": completion_bytes,
        "payload": payload,
        "top_status": top_response.status_code,
        "top_wall_ms": round(first_top_wall, 3),
        "completion_to_top_api_ms": round(first_completion_to_top, 3),
        "completion_to_top_revision_ms": round(completion_to_top, 3),
        "top_revision_wall_ms": round(top_wall, 3),
        "top_bytes": first_top_bytes,
        "top_revision_bytes": len(top_response.content),
        "top_row": row,
        "top_present": isinstance(row, dict),
        "top_pending_attempts": top_attempts,
        "top_pending_final": top_pending,
    }


def run_scheduled(process: psutil.Process, tokens: dict[str, str], events: list[dict], workers: int | None = None) -> list[dict]:
    workers = max(1, int(workers or RUN_MAX_WORKERS))
    started = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for event in events:
            deadline = started + float(event["offset_seconds"])
            remaining = deadline - time.perf_counter()
            if remaining > 0:
                time.sleep(remaining)
            futures.append(executor.submit(request_event, process, tokens[event["username"]], event))
        for future in as_completed(futures):
            results.append(future.result())
    return results


def metric_delta(after: dict, before: dict, key: str) -> float:
    return round(float(after.get(key, 0) or 0) - float(before.get(key, 0) or 0), 3)


def summarize_results(rows: list[dict]) -> dict:
    successful = [row for row in rows if row.get("status") == 200 and row.get("top_status") == 200 and not row.get("error")]
    by_space = {}
    for space_type in SPACE_TYPES:
        selected = [row for row in successful if row["event"]["space_type"] == space_type]
        by_space[space_type] = {
            "completion_wall_ms": distribution([row["completion_wall_ms"] for row in selected]),
            "completion_to_top_api_ms": distribution([row["completion_to_top_api_ms"] for row in selected]),
            "completion_to_top_revision_ms": distribution([row["completion_to_top_revision_ms"] for row in selected]),
            "top_wall_ms": distribution([row["top_wall_ms"] for row in selected]),
            "top_revision_wall_ms": distribution([row["top_revision_wall_ms"] for row in selected]),
            "lock_wait_ms": distribution([float((row.get("payload") or {}).get("timing_ms", {}).get("lock_wait", 0) or 0) for row in selected]),
        }
    sql_values = [float((row.get("payload") or {}).get("postgres_delta", {}).get("sql_round_trips", 0) or 0) for row in successful]
    tx_values = [float((row.get("payload") or {}).get("postgres_delta", {}).get("transactions", 0) or 0) for row in successful]
    max_row = max(successful, key=lambda row: row["completion_wall_ms"], default={})
    slowest_by_space = {}
    for space_type in SPACE_TYPES:
        space_rows = [row for row in successful if (row.get("event") or {}).get("space_type") == space_type]
        space_rows.sort(key=lambda row: float(row.get("completion_wall_ms", 0) or 0), reverse=True)
        slowest_by_space[space_type] = [
            {
                "username": (row.get("event") or {}).get("username"),
                "wall_ms": row.get("completion_wall_ms"),
                "timing_ms": (row.get("payload") or {}).get("timing_ms", {}),
                "postgres_stages": (row.get("payload") or {}).get("postgres_delta", {}).get("stage_totals", {}),
            }
            for row in space_rows[:5]
        ]
    return {
        "requests": len(rows),
        "success": len(successful),
        "errors": sum(bool(row.get("error")) for row in rows),
        "timeouts": sum(bool(row.get("timeout")) for row in rows),
        "top_missing": sum(not row.get("top_present", False) for row in successful),
        "top_pending_attempts": sum(max(0, int(row.get("top_pending_attempts", 0) or 0) - 1) for row in successful),
        "top_pending_final": sum(bool(row.get("top_pending_final")) for row in successful),
        "completion_wall_ms": distribution([row["completion_wall_ms"] for row in successful]),
        "completion_to_top_api_ms": distribution([row["completion_to_top_api_ms"] for row in successful]),
        "completion_to_top_revision_ms": distribution([row["completion_to_top_revision_ms"] for row in successful]),
        "response_bytes": {
            "completion": distribution([row["completion_bytes"] for row in successful]),
            "top": distribution([row["top_bytes"] for row in successful]),
        },
        "sql_average": round(statistics.mean(sql_values), 3) if sql_values else 0.0,
        "transaction_average": round(statistics.mean(tx_values), 3) if tx_values else 0.0,
        "by_space": by_space,
        "slowest_by_space": slowest_by_space,
        "slowest": {
            "username": ((max_row.get("event") or {}).get("username")),
            "space_type": ((max_row.get("event") or {}).get("space_type")),
            "wall_ms": max_row.get("completion_wall_ms"),
            "timing_ms": (max_row.get("payload") or {}).get("timing_ms", {}),
            "postgres_stages": (max_row.get("payload") or {}).get("postgres_delta", {}).get("stage_totals", {}),
        },
        "failure_samples": [
            {
                "username": (row.get("event") or {}).get("username"),
                "space_type": (row.get("event") or {}).get("space_type"),
                "status": row.get("status"),
                "error": row.get("error") or (row.get("payload") or {}).get("error"),
            }
            for row in rows if row.get("status") != 200 or row.get("error")
        ][:20],
    }


def database_correctness(events: list[dict], expected_scores: dict[str, dict[str, int]]) -> dict:
    import psycopg

    usernames = [test_username(index) for index in range(USER_COUNT)]
    with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT username,count(*) FROM future_server2.append_events WHERE stream='learning' AND username=ANY(%s) GROUP BY username", (usernames,))
        event_counts = {row[0]: int(row[1]) for row in cursor.fetchall()}
        cursor.execute("SELECT username,count(*) FROM future_server2.lesson_progress WHERE username=ANY(%s) GROUP BY username", (usernames,))
        progress_counts = {row[0]: int(row[1]) for row in cursor.fetchall()}
        cursor.execute("SELECT path,convert_from(content,'UTF8') FROM future_server2.documents WHERE lower(path) LIKE %s", ("%_future_learning_summary.json",))
        summaries = {}
        for path, text in cursor.fetchall():
            try:
                payload = json.loads(text)
            except Exception:
                continue
            username = str(payload.get("username", ""))
            if username in usernames:
                summaries[username] = payload
        cursor.execute(
            "SELECT path,convert_from(content,'UTF8') FROM future_server2.documents "
            "WHERE lower(path) LIKE %s",
            ("%space_leaderboard_activity.json",),
        )
        activity_payload = {}
        for _path, text in cursor.fetchall():
            try:
                candidate = json.loads(text)
            except Exception:
                continue
            if isinstance(candidate, dict) and len(text) >= len(json.dumps(activity_payload, ensure_ascii=False)):
                activity_payload = candidate
    activity_boards = activity_payload.get("boards") if isinstance(activity_payload.get("boards"), dict) else {}
    activity_scores_exact = True
    activity_completed_total = 0
    activity_test_users = 0
    for space_type, expected in expected_scores.items():
        board = activity_boards.get(space_type) if isinstance(activity_boards.get(space_type), dict) else {}
        board_users = board.get("users") if isinstance(board.get("users"), dict) else {}
        activity_test_users += sum(username in board_users for username in expected)
        for username, score in expected.items():
            row = board_users.get(username) if isinstance(board_users.get(username), dict) else {}
            activity_scores_exact = activity_scores_exact and int(row.get("total_points", -1) or -1) == int(score)
            completed = row.get("completed") if isinstance(row.get("completed"), dict) else {}
            activity_completed_total += len(completed)
    checks = {
        "event_counts_exact": all(event_counts.get(username, 0) == COMPLETIONS_PER_USER for username in usernames),
        "progress_counts_exact": all(progress_counts.get(username, 0) == COMPLETIONS_PER_USER for username in usernames),
        "summary_count_exact": len(summaries) == USER_COUNT,
        "summary_completed_runs_exact": all(int((summaries.get(username) or {}).get("completed_runs", 0) or 0) == COMPLETIONS_PER_USER for username in usernames),
        "summary_total_files_exact": all(int((summaries.get(username) or {}).get("total_files", 0) or 0) == COMPLETIONS_PER_USER for username in usernames),
        "activity_snapshot_scores_exact": activity_scores_exact,
        "activity_snapshot_users_exact": activity_test_users == sum(len(expected) for expected in expected_scores.values()),
        "activity_snapshot_completed_exact": activity_completed_total == len(events),
    }
    return {
        "checks": checks,
        "events_total": sum(event_counts.values()),
        "progress_total": sum(progress_counts.values()),
        "summary_completed_runs_total": sum(int(row.get("completed_runs", 0) or 0) for row in summaries.values()),
        "summary_total_files_total": sum(int(row.get("total_files", 0) or 0) for row in summaries.values()),
        "activity_snapshot_test_users": activity_test_users,
        "activity_snapshot_completed_total": activity_completed_total,
        "expected_events": len(events),
        "expected_scores": expected_scores,
    }


def final_top_correctness(tokens: dict[str, str], expected_scores: dict[str, dict[str, int]], double_check: bool = False) -> dict:
    viewer = test_username(0)
    result = {}
    for space_type in SPACE_TYPES:
        response = requests.get(
            f"{isolated.BASE}/vocab/leaderboard",
            headers={"Authorization": f"Bearer {tokens[viewer]}"},
            params={"limit": 500, "scope": "total", "type": space_type, "double_check": int(bool(double_check))},
            timeout=30,
        )
        payload = response.json()
        rows = (payload.get("boards") or {}).get("total", [])
        row_map = {str(row.get("username", "")): row for row in rows if isinstance(row, dict)}
        expected = expected_scores[space_type]
        exact = all(int((row_map.get(username) or {}).get("score", -1) or -1) == score for username, score in expected.items())
        tie_ok = True
        by_score = {}
        for username, score in expected.items():
            by_score.setdefault(score, []).append(username)
        for tied in by_score.values():
            if len(tied) < 2:
                continue
            observed = sorted(tied, key=lambda username: int((row_map.get(username) or {}).get("rank", 10**9)))
            if observed != sorted(tied, key=str.lower):
                tie_ok = False
                break
        result[space_type] = {
            "status": response.status_code,
            "expected_users": len(expected),
            "test_users_present": sum(username in row_map for username in expected),
            "scores_exact": exact,
            "tie_order_exact": tie_ok,
            "response_bytes": len(response.content),
            "test_user_ranks": {username: int((row_map.get(username) or {}).get("rank", 0) or 0) for username in expected},
            "test_user_scores": {username: int((row_map.get(username) or {}).get("score", 0) or 0) for username in expected},
        }
    return result


def rank_transition_audit(rows: list[dict], final_top: dict) -> dict:
    # Added 2026-07-29: prove that staggered arrivals actually move ranks.
    changed = improved = worsened = 0
    eligible_visible = eligible_missing = 0
    observed = 0
    for row in rows:
        event = row.get("event") or {}
        space_type = str(event.get("space_type", ""))
        username = str(event.get("username", ""))
        initial_rank = int((row.get("top_row") or {}).get("rank", 0) or 0)
        final_rank = int(((final_top.get(space_type) or {}).get("test_user_ranks") or {}).get(username, 0) or 0)
        if 0 < final_rank <= HOT_TOP_LIMIT:
            if initial_rank:
                eligible_visible += 1
            else:
                eligible_missing += 1
        if not initial_rank or not final_rank:
            continue
        observed += 1
        if initial_rank != final_rank:
            changed += 1
            if final_rank < initial_rank:
                improved += 1
            else:
                worsened += 1
    return {
        "observed": observed,
        "changed": changed,
        "improved": improved,
        "worsened": worsened,
        "eligible_visible": eligible_visible,
        "eligible_missing": eligible_missing,
        "hot_top_limit": HOT_TOP_LIMIT,
    }


def space_l_spike_audit(rows: list[dict]) -> dict:
    # Added 2026-07-29: retain the full slow tail instead of hiding a 3s spike.
    selected = [row for row in rows if (row.get("event") or {}).get("space_type") == "space_l"]
    selected.sort(key=lambda row: float(row.get("completion_wall_ms", 0) or 0), reverse=True)
    return {
        "requests": len(selected),
        "over_3000_ms": sum(float(row.get("completion_wall_ms", 0) or 0) >= 3000 for row in selected),
        "completion_wall_ms": distribution([row.get("completion_wall_ms", 0) for row in selected]),
        "worst": [
            {
                "username": (row.get("event") or {}).get("username"),
                "wall_ms": row.get("completion_wall_ms"),
                "timing_ms": (row.get("payload") or {}).get("timing_ms", {}),
                "postgres_stages": (row.get("payload") or {}).get("postgres_delta", {}).get("stage_totals", {}),
            }
            for row in selected[:10]
        ],
    }


def run_mode(mode: str, seed: int, password: str, lessons: dict[str, list[dict]], events: list[dict], keep_alive: bool, global_dirty: bool = False) -> tuple[dict, subprocess.Popen | None, dict[str, str]]:
    restore_snapshot()
    safe_clean_mode_data()
    copy_lessons(lessons)
    tokens = provision_users(seed, password)
    server = isolated.start_server(
        no_preload=False,
        extra_env={
            "FUTURE_TEST_NODE_COMPLETION_FORCE_FILE_DECODE": "1" if mode == "baseline" else "0",
            "FUTURE_TEST_NODE_COMPLETION_STRICT_FILE_DECODE": "1" if mode == "baseline" else "0",
            "FUTURE_TEST_NODE_TOP_GLOBAL_DIRTY": "1" if global_dirty else "0",
            "FUTURE_ISOLATED_LOAD_TEST": "1",
        },
    )
    process = psutil.Process(server.pid)
    ready_health = wait_ready_only(server)
    # Added 2026-07-29: keep the true-cold sample balanced across all five Spaces.
    cold_events = select_balanced_cold_events(events)
    cold_ids = {event["run_id"] for event in cold_events}
    warm_events = [event for event in events if event["run_id"] not in cold_ids]
    expected_scores = {space_type: {} for space_type in SPACE_TYPES}
    for event in events:
        board_scores = expected_scores[event["space_type"]]
        board_scores[event["username"]] = int(board_scores.get(event["username"], 0)) + int(event["lesson"]["points"])
    server_cpu_before = isolated.server_cpu(server)
    postgres_cpu_before = isolated.postgres_cpu()
    # Added 2026-07-29: avoid an extra dashboard probe before the pre-warm batch.
    metrics_before = ready_health
    with ThreadMonitor(process) as monitor, PostgresLockMonitor() as lock_monitor:
        cold_server_cpu_before = isolated.server_cpu(server)
        cold_postgres_cpu_before = isolated.postgres_cpu()
        cold_started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=COLD_COUNT) as executor:
            cold_rows = list(executor.map(lambda event: request_event(process, tokens[event["username"]], event), cold_events))
        cold_wall_ms = (time.perf_counter() - cold_started) * 1000.0
        cold_server_cpu_after = isolated.server_cpu(server)
        cold_postgres_cpu_after = isolated.postgres_cpu()
        post_cold_health = health()
        warm_health = wait_warm(server)
        warm_started = time.perf_counter()
        warm_rows = run_scheduled(process, tokens, warm_events, workers=RUN_MAX_WORKERS)
        warm_wall_ms = (time.perf_counter() - warm_started) * 1000.0
        retry_rows = []
        for original in warm_rows[:RETRY_COUNT]:
            if not original.get("body"):
                continue
            started = time.perf_counter()
            response = requests.post(
                f"{isolated.BASE}/lesson/complete",
                headers={"Authorization": f"Bearer {tokens[original['event']['username']]}"},
                json=original["body"],
                timeout=30,
            )
            retry_rows.append({
                "status": response.status_code,
                "wall_ms": round((time.perf_counter() - started) * 1000.0, 3),
                "payload": response.json(),
                "response_bytes": len(response.content),
            })
        time.sleep(3.0)
    metrics_after = health()
    server_cpu_after = isolated.server_cpu(server)
    postgres_cpu_after = isolated.postgres_cpu()
    all_rows = cold_rows + warm_rows
    response_run_values = {}
    for row in all_rows:
        username = (row.get("event") or {}).get("username")
        completed_runs = int((row.get("payload") or {}).get("learning_stats", {}).get("completed_runs", 0) or 0)
        response_run_values.setdefault(username, []).append(completed_runs)
    stale_summary_ok = all(sorted(values) == list(range(1, COMPLETIONS_PER_USER + 1)) for values in response_run_values.values())
    database = database_correctness(events, expected_scores)
    top = final_top_correctness(tokens, expected_scores)
    rank_metrics_before = health().get("leaderboard_runtime") or {}
    rank_top = final_top_correctness(tokens, expected_scores, double_check=True)
    time.sleep(2.5)
    rank_metrics_after = health().get("leaderboard_runtime") or {}
    rank_board_before = rank_metrics_before.get("leaderboard") or {}
    rank_board_after = rank_metrics_after.get("leaderboard") or {}
    retry_ok = all(
        row["status"] == 200 and bool((row.get("payload") or {}).get("duplicate") or (row.get("payload") or {}).get("deduplicated"))
        for row in retry_rows
    ) and len(retry_rows) == RETRY_COUNT
    before_pg = metrics_before.get("postgres") if isinstance(metrics_before.get("postgres"), dict) else {}
    after_pg = metrics_after.get("postgres") if isinstance(metrics_after.get("postgres"), dict) else {}
    before_runtime = metrics_before.get("leaderboard_runtime") if isinstance(metrics_before.get("leaderboard_runtime"), dict) else {}
    after_runtime = metrics_after.get("leaderboard_runtime") if isinstance(metrics_after.get("leaderboard_runtime"), dict) else {}
    before_activity = before_runtime.get("activity_snapshot") if isinstance(before_runtime.get("activity_snapshot"), dict) else {}
    after_activity = after_runtime.get("activity_snapshot") if isinstance(after_runtime.get("activity_snapshot"), dict) else {}
    before_node_batch = before_runtime.get("node_top_batch") if isinstance(before_runtime.get("node_top_batch"), dict) else {}
    after_node_batch = after_runtime.get("node_top_batch") if isinstance(after_runtime.get("node_top_batch"), dict) else {}
    before_board = before_runtime.get("leaderboard") if isinstance(before_runtime.get("leaderboard"), dict) else {}
    after_board = after_runtime.get("leaderboard") if isinstance(after_runtime.get("leaderboard"), dict) else {}
    result = {
        "mode": mode,
        "ready_health": {key: ready_health.get(key) for key in ("pid", "ready", "warm_ready", "warm_status")},
        "post_cold_health": {key: post_cold_health.get(key) for key in ("pid", "ready", "warm_ready", "warm_status")},
        "warm_health": {key: warm_health.get(key) for key in ("pid", "ready", "warm_ready", "warm_status")},
        "cold_launched_before_warm_ready": not bool(ready_health.get("warm_ready")),
        "cold_batch_wall_ms": round(cold_wall_ms, 3),
        "warm_batch_wall_ms": round(warm_wall_ms, 3),
        "cold": summarize_results(cold_rows),
        "warm": summarize_results(warm_rows),
        "cold_cpu": {
            "server_ms": round(cold_server_cpu_after - cold_server_cpu_before, 3),
            "postgres_ms": round(cold_postgres_cpu_after - cold_postgres_cpu_before, 3),
        },
        "aggregate_cpu": {
            "server_ms": round(server_cpu_after - server_cpu_before, 3),
            "postgres_ms": round(postgres_cpu_after - postgres_cpu_before, 3),
        },
        "peak_thread_count": monitor.peak,
        "thread_samples": monitor.samples,
        "lock_wait": {
            "samples": lock_monitor.samples,
            "samples_with_wait": lock_monitor.samples_with_wait,
            "max_waiters": lock_monitor.max_waiters,
            "max_ungranted_locks": lock_monitor.max_ungranted_locks,
            "max_query_wait_ms": round(lock_monitor.max_query_wait_ms, 3),
            "monitor_errors": lock_monitor.errors,
        },
        "pool": {
            "wait_count": metric_delta(after_pg, before_pg, "pool_wait_count"),
            "wait_ms_total": metric_delta(after_pg, before_pg, "pool_wait_ms_total"),
            "wait_ms_max_after": after_pg.get("pool_wait_ms_max", 0),
            "size_before": before_pg.get("pool_size", 0),
            "size_after": after_pg.get("pool_size", 0),
            "active_after": after_pg.get("pool_active", 0),
            "idle_after": after_pg.get("pool_idle", 0),
        },
        "runtime_counters": {
            "rank_change_events": metric_delta(after_board, before_board, "rank_change_events"),
            "response_seed_count": metric_delta(after_board, before_board, "response_seed_count"),
            "full_build_count": metric_delta(after_board, before_board, "full_build_count"),
            "historical_backfill_count": metric_delta(after_board, before_board, "historical_backfill_count"),
            "rank_snapshot_requests": metric_delta(after_board, before_board, "rank_snapshot_requests"),
            "rank_serialize_count": metric_delta(after_board, before_board, "rank_serialize_count"),
            "rank_write_count": metric_delta(after_board, before_board, "rank_write_count"),
            "rank_write_failures": metric_delta(after_board, before_board, "rank_write_failures"),
            "activity_snapshot_requests": metric_delta(after_activity, before_activity, "snapshot_requests"),
            "activity_serialize_count": metric_delta(after_activity, before_activity, "serialize_count"),
            "activity_write_count": metric_delta(after_activity, before_activity, "write_count"),
            "activity_write_failures": metric_delta(after_activity, before_activity, "write_failures"),
            "activity_worker_starts": metric_delta(after_activity, before_activity, "worker_starts"),
            "activity_last_bytes": after_activity.get("last_bytes", 0),
            "activity_write_ms_max": after_activity.get("write_ms_max", 0),
            "rank_worker_threads": after_runtime.get("rank_worker_threads", 0),
            "activity_worker_threads": after_runtime.get("activity_worker_threads", 0),
            "node_top_dirty_count": metric_delta(after_board, before_board, "node_top_dirty_count"),
            "node_top_refresh_requests": metric_delta(after_board, before_board, "node_top_refresh_requests"),
            "node_top_batch_build_count": metric_delta(after_board, before_board, "node_top_batch_build_count"),
            "node_top_batch_build_failures": metric_delta(after_board, before_board, "node_top_batch_build_failures"),
            "node_top_batch_worker_starts": metric_delta(after_node_batch, before_node_batch, "worker_starts"),
            "node_top_batch_threads": after_runtime.get("node_top_batch_threads", 0),
        },
        "retry": {
            "count": len(retry_rows),
            "all_deduplicated": retry_ok,
            "wall_ms": distribution([row["wall_ms"] for row in retry_rows]),
            "response_bytes": distribution([row["response_bytes"] for row in retry_rows]),
        },
        "response_summary_fresh": stale_summary_ok,
        "database": database,
        "top": top,
        "rank_audit": {
            "top": rank_top,
            "transitions": rank_transition_audit(all_rows, rank_top),
            "runtime": {
                key: metric_delta(rank_board_after, rank_board_before, key)
                for key in (
                    "rank_change_events",
                    "rank_snapshot_requests",
                    "rank_worker_starts",
                    "rank_serialize_count",
                    "rank_write_count",
                    "rank_write_failures",
                    "full_build_count",
                    "historical_backfill_count",
                )
            },
        },
        "space_l_spike_audit": space_l_spike_audit(all_rows),
    }
    isolated.stop_server(server)
    restart = isolated.start_server(
        no_preload=False,
        extra_env={
            "FUTURE_TEST_NODE_COMPLETION_FORCE_FILE_DECODE": "1" if mode == "baseline" else "0",
            "FUTURE_TEST_NODE_COMPLETION_STRICT_FILE_DECODE": "1" if mode == "baseline" else "0",
            "FUTURE_TEST_NODE_TOP_GLOBAL_DIRTY": "1" if global_dirty else "0",
            "FUTURE_ISOLATED_LOAD_TEST": "1",
        },
    )
    restart_health = wait_warm(restart)
    restart_top = final_top_correctness(tokens, expected_scores, double_check=True)
    restart_db = database_correctness(events, expected_scores)
    result["restart"] = {
        "health": {key: restart_health.get(key) for key in ("pid", "ready", "warm_ready", "warm_status")},
        "top": restart_top,
        "database": restart_db,
    }
    if keep_alive:
        return result, restart, tokens
    isolated.stop_server(restart)
    return result, None, tokens


def compare_modes(baseline: dict, manifest: dict) -> dict:
    spaces = {}
    all_non_regressed = True
    for space_type in SPACE_TYPES:
        base = baseline["warm"]["by_space"][space_type]["completion_wall_ms"]
        fast = manifest["warm"]["by_space"][space_type]["completion_wall_ms"]
        cold_base = baseline["cold"]["by_space"][space_type]["completion_wall_ms"]
        cold_fast = manifest["cold"]["by_space"][space_type]["completion_wall_ms"]
        p95_ok = float(fast["p95"]) <= float(base["p95"])
        p99_ok = float(fast["p99"]) <= float(base["p99"])
        all_non_regressed = all_non_regressed and p95_ok and p99_ok
        spaces[space_type] = {
            "baseline_p50": base["p50"],
            "manifest_p50": fast["p50"],
            "baseline_p95": base["p95"],
            "manifest_p95": fast["p95"],
            "baseline_p99": base["p99"],
            "manifest_p99": fast["p99"],
            "p95_not_worse": p95_ok,
            "p99_not_worse": p99_ok,
            "cold_baseline_p50": cold_base["p50"],
            "cold_manifest_p50": cold_fast["p50"],
            "cold_baseline_p95": cold_base["p95"],
            "cold_manifest_p95": cold_fast["p95"],
            "cold_baseline_p99": cold_base["p99"],
            "cold_manifest_p99": cold_fast["p99"],
        }
    mode_checks = {}
    for mode_name, mode in (("baseline", baseline), ("manifest", manifest)):
        checks = list(mode["database"]["checks"].values())
        checks.extend(row["scores_exact"] and row["tie_order_exact"] and row["test_users_present"] == row["expected_users"] for row in mode["top"].values())
        checks.extend(row["scores_exact"] and row["tie_order_exact"] and row["test_users_present"] == row["expected_users"] for row in mode["rank_audit"]["top"].values())
        checks.extend(row["scores_exact"] and row["tie_order_exact"] and row["test_users_present"] == row["expected_users"] for row in mode["restart"]["top"].values())
        checks.extend([
            mode["cold"]["errors"] == 0,
            mode["warm"]["errors"] == 0,
            mode["rank_audit"]["transitions"]["eligible_missing"] == 0,
            mode["cold_launched_before_warm_ready"],
            mode["retry"]["all_deduplicated"],
            mode["response_summary_fresh"],
            mode["runtime_counters"]["historical_backfill_count"] == 0,
            mode["runtime_counters"]["full_build_count"] == 0,
            mode["runtime_counters"]["rank_write_failures"] == 0,
            mode["runtime_counters"]["activity_write_failures"] == 0,
            mode["runtime_counters"]["rank_worker_threads"] <= 1,
            mode["runtime_counters"]["activity_worker_threads"] <= 1,
            mode["runtime_counters"]["activity_snapshot_requests"] >= mode["cold"]["success"] + mode["warm"]["success"],
            mode["runtime_counters"]["activity_serialize_count"] <= max(
                2,
                math.ceil((mode["cold"]["success"] + mode["warm"]["success"]) / 100),
            ),
            mode["runtime_counters"]["activity_write_count"] <= mode["runtime_counters"]["activity_serialize_count"],
            mode["lock_wait"]["monitor_errors"] == 0,
            mode["rank_audit"]["transitions"]["changed"] > 0,
            mode["rank_audit"]["transitions"]["improved"] > 0,
            mode["rank_audit"]["transitions"]["worsened"] > 0,
        ])
        mode_checks[mode_name] = checks
    cold_p95_ok = manifest["cold"]["completion_wall_ms"]["p95"] <= baseline["cold"]["completion_wall_ms"]["p95"]
    cold_p99_ok = manifest["cold"]["completion_wall_ms"]["p99"] <= baseline["cold"]["completion_wall_ms"]["p99"]
    cold_wall_ok = manifest["cold_batch_wall_ms"] < baseline["cold_batch_wall_ms"]
    cold_cpu_ok = manifest["cold_cpu"]["server_ms"] < baseline["cold_cpu"]["server_ms"]
    return {
        "spaces": spaces,
        "baseline_correctness_100_percent": all(bool(value) for value in mode_checks["baseline"]),
        "manifest_correctness_100_percent": all(bool(value) for value in mode_checks["manifest"]),
        "p95_p99_not_worse": all_non_regressed,
        "cold_p95_not_worse": cold_p95_ok,
        "cold_p99_not_worse": cold_p99_ok,
        "manifest_cold_wall_improved": cold_wall_ok,
        "manifest_cold_server_cpu_improved": cold_cpu_ok,
        "manifest_total_wall_improved": manifest["warm_batch_wall_ms"] < baseline["warm_batch_wall_ms"],
        "manifest_server_cpu_improved": manifest["aggregate_cpu"]["server_ms"] < baseline["aggregate_cpu"]["server_ms"],
        "keep_manifest": bool(
            all(mode_checks["manifest"])
            and all_non_regressed
            and cold_p95_ok
            and cold_p99_ok
            and cold_wall_ok
            and cold_cpu_ok
            and manifest["warm_batch_wall_ms"] < baseline["warm_batch_wall_ms"]
            and manifest["aggregate_cpu"]["server_ms"] < baseline["aggregate_cpu"]["server_ms"]
        ),
    }


def main() -> int:
    global RUN_MAX_WORKERS
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=2026072907)
    parser.add_argument("--keep-manifest-server", action="store_true")
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument("--global-dirty", action="store_true")
    parser.add_argument("--cold-probe", action="store_true")
    parser.add_argument("--cold-stagger-seconds", type=float, default=0.0)
    parser.add_argument("--probe-output", type=Path)
    parser.add_argument("--keep-probe-server", action="store_true")
    parser.add_argument("--max-workers", type=int, default=MAX_WORKERS)
    args = parser.parse_args()
    RUN_MAX_WORKERS = max(1, min(MAX_WORKERS, int(args.max_workers or MAX_WORKERS)))
    password = os.environ.get("FUTURE_LOAD_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("FUTURE_LOAD_TEST_PASSWORD is required and is never written to evidence")
    configure_paths()
    shutil.rmtree(RUN_ROOT, ignore_errors=True)
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    server = None
    try:
        isolated.start_postgres()
        snapshot = dump_production_once()
        lessons = select_lessons()
        events = build_events(args.seed, lessons)
        if args.cold_probe:
            restore_snapshot()
            safe_clean_mode_data()
            copy_lessons(lessons)
            tokens = provision_users(args.seed, password)
            server = isolated.start_server(no_preload=False, extra_env={"FUTURE_ISOLATED_LOAD_TEST": "1"})
            ready = wait_ready_only(server)
            cold_events = select_balanced_cold_events(events)
            process = psutil.Process(server.pid)
            server_cpu_before = isolated.server_cpu(server)
            postgres_cpu_before = isolated.postgres_cpu()
            health_before = health()
            batch_started = time.perf_counter()
            with ThreadPoolExecutor(max_workers=COLD_COUNT) as executor:
                futures = []
                for event_index, event in enumerate(cold_events):
                    deadline = batch_started + (event_index * max(0.0, args.cold_stagger_seconds))
                    remaining = deadline - time.perf_counter()
                    if remaining > 0:
                        time.sleep(remaining)
                    futures.append(executor.submit(request_event, process, tokens[event["username"]], event))
                rows = [future.result() for future in futures]
            batch_wall_ms = (time.perf_counter() - batch_started) * 1000.0
            health_after = health()
            probe = {
                "database_sync": snapshot,
                "ready": {key: ready.get(key) for key in ("pid", "ready", "warm_ready", "warm_status")},
                "arrival": {
                    "count": len(cold_events),
                    "stagger_seconds": max(0.0, args.cold_stagger_seconds),
                    "batch_wall_ms": round(batch_wall_ms, 3),
                },
                "summary": summarize_results(rows),
                "cpu": {
                    "server_ms": round(isolated.server_cpu(server) - server_cpu_before, 3),
                    "postgres_ms": round(isolated.postgres_cpu() - postgres_cpu_before, 3),
                },
                "postgres_pool": {
                    key: metric_delta(health_after.get("postgres") or {}, health_before.get("postgres") or {}, key)
                    for key in ("pool_wait_count", "pool_wait_ms_total", "transactions", "sql_round_trips")
                },
                "failures": [
                    {
                        "status": row.get("status"),
                        "space_type": (row.get("event") or {}).get("space_type"),
                        "username": (row.get("event") or {}).get("username"),
                        "payload": row.get("payload"),
                        "error": row.get("error"),
                    }
                    for row in rows if row.get("status") != 200 or row.get("error")
                ],
            }
            if args.probe_output:
                args.probe_output.parent.mkdir(parents=True, exist_ok=True)
                args.probe_output.write_text(json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(probe, ensure_ascii=False, indent=2))
            if args.keep_probe_server:
                print(f"DOM_READY user={test_username(0)} url={isolated.BASE}/login marker={DOM_MARKER}", flush=True)
                deadline = time.monotonic() + 900
                while time.monotonic() < deadline and not DOM_MARKER.is_file():
                    time.sleep(0.25)
            return 0
        baseline = None
        if not args.manifest_only:
            baseline, _server, _tokens = run_mode("baseline", args.seed, password, lessons, events, False, args.global_dirty)
        manifest, server, _tokens = run_mode("manifest", args.seed, password, lessons, events, args.keep_manifest_server, args.global_dirty)
        comparison = compare_modes(baseline, manifest) if baseline is not None else {
            "mode": "manifest-only",
            "correctness_100_percent": (
                all(manifest["database"]["checks"].values())
                and all(row["scores_exact"] and row["tie_order_exact"] and row["test_users_present"] == row["expected_users"] for row in manifest["top"].values())
                and all(row["scores_exact"] and row["tie_order_exact"] and row["test_users_present"] == row["expected_users"] for row in manifest["rank_audit"]["top"].values())
                and all(row["scores_exact"] and row["tie_order_exact"] and row["test_users_present"] == row["expected_users"] for row in manifest["restart"]["top"].values())
                and manifest["retry"]["all_deduplicated"]
                and manifest["response_summary_fresh"]
                and manifest["cold"]["errors"] == 0
                and manifest["warm"]["errors"] == 0
                and manifest["cold"]["top_pending_final"] == 0
                and manifest["warm"]["top_pending_final"] == 0
                and manifest["rank_audit"]["transitions"]["eligible_missing"] == 0
                and manifest["lock_wait"]["monitor_errors"] == 0
                and manifest["rank_audit"]["transitions"]["changed"] > 0
                and manifest["rank_audit"]["transitions"]["improved"] > 0
                and manifest["rank_audit"]["transitions"]["worsened"] > 0
                and manifest["runtime_counters"]["activity_serialize_count"] <= max(
                    2,
                    math.ceil((manifest["cold"]["success"] + manifest["warm"]["success"]) / 100),
                )
                and manifest["runtime_counters"]["full_build_count"] == 0
                and manifest["runtime_counters"]["historical_backfill_count"] == 0
                and manifest["runtime_counters"]["rank_worker_threads"] <= 1
                and manifest["runtime_counters"]["activity_worker_threads"] <= 1
                and manifest["runtime_counters"]["node_top_batch_threads"] <= 1
            ),
            "keep_manifest": False,
            "note": "manifest-only run has no baseline comparison",
        }
        output = {
            "database_sync": snapshot,
            "random_seed": args.seed,
            "workload": {
                "users": USER_COUNT,
                "completion_requests": len(events),
                "retry_requests": RETRY_COUNT,
                "space_mix": {space_type: sum(event["space_type"] == space_type for event in events) for space_type in SPACE_TYPES},
                "delay_range_seconds": [0, 10],
                "max_concurrency": RUN_MAX_WORKERS,
                "hot_top_limit": HOT_TOP_LIMIT,
                "burst_groups": 10,
                "same_space_pair_users": len({event["username"] for event in events if event.get("same_space_pair")}),
                "lessons": {space_type: [{key: row[key] for key in ("path", "lesson_id", "nodes", "points")} for row in rows] for space_type, rows in lessons.items()},
            },
            "baseline": baseline,
            "manifest": manifest,
            "comparison": comparison,
            "dom": {"pending": bool(args.keep_manifest_server)},
        }
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({
            "database_sync": snapshot,
            "random_seed": args.seed,
            "workload": output["workload"],
            "baseline": None if baseline is None else {"cold": baseline["cold"], "warm": baseline["warm"], "cpu": baseline["aggregate_cpu"], "runtime": baseline["runtime_counters"]},
            "manifest": {"cold": manifest["cold"], "warm": manifest["warm"], "cpu": manifest["aggregate_cpu"], "runtime": manifest["runtime_counters"]},
            "comparison": comparison,
            "output": str(OUTPUT),
        }, ensure_ascii=False, indent=2))
        if args.keep_manifest_server:
            print(f"DOM_READY user={test_username(0)} url={isolated.BASE}/login marker={DOM_MARKER}", flush=True)
            deadline = time.monotonic() + 900
            while time.monotonic() < deadline and not DOM_MARKER.is_file():
                time.sleep(0.25)
            if DOM_MARKER.is_file():
                output["dom"] = json.loads(DOM_MARKER.read_text(encoding="utf-8"))
                OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
            else:
                output["dom"] = {"pending": False, "error": "DOM marker timeout"}
                OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        if baseline is None:
            if not comparison["correctness_100_percent"]:
                raise RuntimeError(f"manifest-only gate failed: {comparison}")
            return 0
        if not comparison["keep_manifest"]:
            raise RuntimeError(f"100-user A/B gate failed: {comparison}")
        return 0
    finally:
        isolated.stop_server(server)
        isolated.stop_postgres()


if __name__ == "__main__":
    raise SystemExit(main())
