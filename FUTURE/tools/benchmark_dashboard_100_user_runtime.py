#!/usr/bin/env python3
"""Measure Server 2 dashboard overhead while 100 isolated users are active."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import random
import shutil
import stat
import sys
import threading
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "FUTURE" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import test_lesson_complete_isolated_harness as isolated

RUN_ROOT = ROOT / "programe_cache" / "dashboard_100_user_runtime_18877"
OUTPUT = Path(r"C:\Users\Admin\.codex\plans\dashboard_100_user_runtime_20260805.json")
USERS = tuple(f"codexdash{index:03d}" for index in range(1, 101))
LESSON_PATH = isolated.LESSON_PATH
LESSON_ID = isolated.LESSON_ID


def configure() -> None:
    isolated.RUN_ROOT = RUN_ROOT
    isolated.PG_ROOT = RUN_ROOT / "postgres"
    isolated.SERVER_DATA_ROOT = RUN_ROOT / "server-data"
    isolated.RUNTIME_ROOT = RUN_ROOT / "runtime"
    isolated.QMLEARN_ROOT = RUN_ROOT / "qml"
    isolated.SERVER_LOG = RUN_ROOT / "server.log"
    isolated.PG_LOG = RUN_ROOT / "postgres.log"


def remove_run_root() -> None:
    if not RUN_ROOT.exists():
        return

    def clear_readonly(func, path, _exc):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    shutil.rmtree(RUN_ROOT, onerror=clear_readonly)


def production_pid() -> int | None:
    for connection in psutil.net_connections(kind="tcp"):
        if connection.status == psutil.CONN_LISTEN and connection.laddr and connection.laddr.port == 8877:
            return int(connection.pid) if connection.pid else None
    return None


def provision_users() -> None:
    import psycopg
    from psycopg.types.json import Jsonb

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    password_hash = isolated.password_hash(isolated.PASSWORD)
    with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
        for username in USERS:
            cursor.execute(
                """INSERT INTO future_server2.users
                   (username,is_admin,is_test,profile_json,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                   VALUES (%s,false,true,%s,%s,0,'','')
                   ON CONFLICT (username) DO UPDATE SET is_test=true,profile_json=excluded.profile_json""",
                (username, Jsonb({"source": "dashboard-100-user-runtime", "load_test": True}), now),
            )
            cursor.execute(
                """INSERT INTO future_server2.user_auth_credentials
                   (username,password_hash,source_path,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                   VALUES (%s,%s,'dashboard-100-user-runtime',%s,0,'','')
                   ON CONFLICT (username) DO UPDATE SET password_hash=excluded.password_hash,updated_at_utc=excluded.updated_at_utc""",
                (username, password_hash, now),
            )
        connection.commit()


def cpu_seconds(process: psutil.Process) -> float:
    row = process.cpu_times()
    return float(row.user + row.system)


def response_sizes(response: requests.Response) -> tuple[int, int, int]:
    decoded = len(response.content)
    wire = int(response.headers.get("Content-Length") or decoded)
    body = response.request.body
    request_bytes = len(body) if isinstance(body, bytes) else len(str(body or "").encode("utf-8"))
    return decoded, wire, request_bytes


def percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    return ordered[max(0, min(len(ordered) - 1, int(len(ordered) * ratio) - 1))]


class UserAgent:
    def __init__(self, username: str, token: str, seed: int):
        self.username = username
        self.random = random.Random(seed)
        self.sequence = 0
        self.offline_lease = ""
        self.session_id = f"dashboard-bench-{uuid.uuid4().hex}"
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}", "Accept-Encoding": "gzip"})

    def request(self, action: str) -> dict:
        started = time.perf_counter()
        response = None
        try:
            if action == "tree":
                response = self.session.get(f"{isolated.BASE}/server-data/tree-preload", timeout=30)
            elif action == "tasks":
                response = self.session.get(f"{isolated.BASE}/lesson-tasks", params={"user": self.username}, timeout=30)
            elif action == "file":
                response = self.session.get(f"{isolated.BASE}/server-data/file", params={"path": LESSON_PATH}, timeout=30)
            elif action == "progress":
                response = self.session.get(
                    f"{isolated.BASE}/space-v/progress",
                    params={"path": LESSON_PATH, "identity": LESSON_ID, "lesson_id": LESSON_ID},
                    timeout=30,
                )
            elif action == "time":
                self.sequence += 1
                response = self.session.post(
                    f"{isolated.BASE}/lesson/time",
                    json={
                        "path": LESSON_PATH,
                        "lesson_id": LESSON_ID,
                        "space": "Space_V",
                        "seconds": 1,
                        "protocol": "server-time-v1",
                        "session_id": self.session_id,
                        "sequence": self.sequence,
                        "offline_lease": self.offline_lease,
                    },
                    timeout=30,
                )
                if response.ok:
                    payload = response.json().get("time") or {}
                    self.offline_lease = str(payload.get("offlineLease") or self.offline_lease)
            elif action == "complete":
                stamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
                response = self.session.post(
                    f"{isolated.BASE}/space-v/progress?client_source=space_v_complete&response=compact-v1",
                    json={
                        "path": LESSON_PATH,
                        "identity": LESSON_ID,
                        "lesson_id": LESSON_ID,
                        "space": "Space_V",
                        "complete": True,
                        "completed": True,
                        "progressDone": 1,
                        "progressTotal": 1,
                        "learnedWords": [{"word": "dashboard"}],
                        "state": {"completed": True, "studyIndexes": []},
                        "savedAt": stamp,
                        "completion_trace_id": f"dashboard-bench-{self.username}-{self.sequence}",
                    },
                    timeout=45,
                )
            elif action == "inventory":
                response = self.session.get(f"{isolated.BASE}/inventory", params={"response": "compact-v1"}, timeout=30)
            else:
                response = self.session.get(f"{isolated.BASE}/settings", timeout=30)
            status = int(response.status_code)
            if status not in {200, 304, 409, 429}:
                response.raise_for_status()
            decoded, wire, request_bytes = response_sizes(response)
            return {
                "action": action,
                "latency_ms": (time.perf_counter() - started) * 1000,
                "status": status,
                "decoded": decoded,
                "wire": wire,
                "request_bytes": request_bytes,
                "error": "",
            }
        except Exception as exc:
            return {
                "action": action,
                "latency_ms": (time.perf_counter() - started) * 1000,
                "status": int(response.status_code) if response is not None else 0,
                "decoded": len(response.content) if response is not None else 0,
                "wire": int(response.headers.get("Content-Length") or len(response.content)) if response is not None else 0,
                "request_bytes": 0,
                "error": f"{type(exc).__name__}: {exc}",
            }


def login_users() -> list[UserAgent]:
    def login(index: int) -> UserAgent:
        username = USERS[index]
        response = requests.post(
            f"{isolated.BASE}/auth/login",
            json={"username": username, "password": isolated.PASSWORD},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if (payload.get("server_data") or {}).get("load_test") is not True:
            raise RuntimeError(f"not isolated load-test user: {username}")
        return UserAgent(username, str(payload["token"]), 20260805 + index * 17)

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        return list(pool.map(login, range(len(USERS))))


def summarize_rows(rows: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[str(row["action"])].append(row)
    result = {}
    for action, action_rows in sorted(grouped.items()):
        latencies = [float(row["latency_ms"]) for row in action_rows]
        result[action] = {
            "requests": len(action_rows),
            "errors": sum(1 for row in action_rows if row.get("error")),
            "statuses": dict(Counter(int(row.get("status", 0)) for row in action_rows)),
            "p50_ms": round(percentile(latencies, 0.50), 3),
            "p95_ms": round(percentile(latencies, 0.95), 3),
            "p99_ms": round(percentile(latencies, 0.99), 3),
            "decoded_bytes": sum(int(row.get("decoded", 0)) for row in action_rows),
            "wire_bytes": sum(int(row.get("wire", 0)) for row in action_rows),
            "error_samples": [row.get("error", "") for row in action_rows if row.get("error")][:3],
        }
    return result


def run_phase(label: str, users: list[UserAgent], duration: float, dashboard: bool) -> dict:
    process = psutil.Process(int(requests.get(f"{isolated.BASE}/health", timeout=10).json()["pid"]))
    rows: list[dict] = []
    rows_lock = threading.Lock()
    dashboard_rows: list[dict] = []
    dashboard_lock = threading.Lock()
    stop_dashboard = threading.Event()
    actions = ("tree", "tasks", "file", "progress", "time", "inventory", "settings", "complete")
    weights = (8, 8, 12, 14, 18, 8, 8, 2)
    deadline = time.perf_counter() + duration
    before_cpu = cpu_seconds(process)
    before_io = process.io_counters()
    writer_before = requests.get(f"{isolated.BASE}/health?view=dashboard-v1", timeout=10).json().get("postgres_writer", {})

    def dashboard_poll_loop() -> None:
        next_health = 0.0
        next_learning = 0.0
        next_login = 0.0
        requests.get(f"{isolated.BASE}/status?ts=dashboard-benchmark", timeout=15)
        while not stop_dashboard.is_set():
            now = time.perf_counter()
            work: list[tuple[str, str]] = []
            if now >= next_health:
                work.append(("dashboard_health", "/health?view=dashboard-v1"))
                next_health = now + 1.0
            if now >= next_learning:
                work.append(("dashboard_learning_log", "/dashboard/learning-log?limit=200"))
                next_learning = now + 10.0
            if now >= next_login:
                work.append(("dashboard_login_log", "/dashboard/login-log?limit=200"))
                next_login = now + 10.0
            for action, path in work:
                started = time.perf_counter()
                response = None
                try:
                    response = requests.get(f"{isolated.BASE}{path}&ts={time.time_ns()}", timeout=10)
                    decoded, wire, request_bytes = response_sizes(response)
                    row = {
                        "action": action,
                        "latency_ms": (time.perf_counter() - started) * 1000,
                        "status": response.status_code,
                        "decoded": decoded,
                        "wire": wire,
                        "request_bytes": request_bytes,
                        "error": "",
                    }
                except Exception as exc:
                    row = {
                        "action": action,
                        "latency_ms": (time.perf_counter() - started) * 1000,
                        "status": int(response.status_code) if response is not None else 0,
                        "decoded": len(response.content) if response is not None else 0,
                        "wire": 0,
                        "request_bytes": 0,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                with dashboard_lock:
                    dashboard_rows.append(row)
            stop_dashboard.wait(0.1)

    dashboard_thread = None
    if dashboard:
        dashboard_thread = threading.Thread(target=dashboard_poll_loop, name="dashboard-open-poll", daemon=True)
        dashboard_thread.start()

    def run_user(user: UserAgent) -> int:
        local_rows = []
        while time.perf_counter() < deadline:
            action = user.random.choices(actions, weights=weights, k=1)[0]
            local_rows.append(user.request(action))
            time.sleep(user.random.uniform(0.12, 0.55))
        with rows_lock:
            rows.extend(local_rows)
        return len(local_rows)

    started = time.perf_counter()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(users)) as pool:
            list(pool.map(run_user, users))
    finally:
        stop_dashboard.set()
        if dashboard_thread is not None:
            dashboard_thread.join(timeout=5)
    wall = time.perf_counter() - started
    after_cpu = cpu_seconds(process)
    after_io = process.io_counters()
    writer_after = requests.get(f"{isolated.BASE}/health?view=dashboard-v1", timeout=10).json().get("postgres_writer", {})
    health = requests.get(f"{isolated.BASE}/health?view=dashboard-v1&ts=phase-end", timeout=10).json()
    return {
        "label": label,
        "dashboard_open": dashboard,
        "duration_seconds": round(wall, 3),
        "users": len(users),
        "user_requests": len(rows),
        "dashboard_requests": len(dashboard_rows),
        "server_cpu_ms": round((after_cpu - before_cpu) * 1000, 3),
        "server_cpu_ms_per_total_request": round((after_cpu - before_cpu) * 1000 / max(1, len(rows) + len(dashboard_rows)), 3),
        "whole_machine_cpu_percent": round(((after_cpu - before_cpu) / max(0.001, wall) / psutil.cpu_count()) * 100, 4),
        "process_io": {
            "read_bytes": max(0, int(after_io.read_bytes - before_io.read_bytes)),
            "write_bytes": max(0, int(after_io.write_bytes - before_io.write_bytes)),
        },
        "postgres_writer_delta": {
            key: round(float(writer_after.get(key, 0) or 0) - float(writer_before.get(key, 0) or 0), 3)
            for key in ("batches", "tasks", "queue_wait_ms", "begin_wait_ms", "commit_ms", "busy_errors")
        },
        "dashboard_recent_log_state": health.get("dashboard_recent_log_state"),
        "last_learning_event": health.get("last_learning_event"),
        "last_login_event": health.get("last_login_event"),
        "user_actions": summarize_rows(rows),
        "dashboard_actions": summarize_rows(dashboard_rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=45.0)
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    configure()
    prod_before = production_pid()
    if any(c.laddr and c.laddr.port == isolated.HTTP_PORT and c.status == psutil.CONN_LISTEN for c in psutil.net_connections(kind="tcp")):
        raise RuntimeError("isolated port 18877 already in use")
    pg_process = None
    server = None
    result = {}
    try:
        remove_run_root()
        RUN_ROOT.mkdir(parents=True, exist_ok=True)
        pg_process = isolated.start_postgres()
        dump_path = isolated.sync_production_database_snapshot()
        isolated.initialize_schema()
        provision_users()
        isolated.copy_lesson()
        server = isolated.start_server(no_preload=True)
        health = isolated.wait_health(server)
        users = login_users()
        # Establish offline leases before measured phases.
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
            list(pool.map(lambda user: user.request("time"), users))
        baseline = run_phase("baseline_no_dashboard", users, args.duration, dashboard=False)
        time.sleep(3)
        dashboard_open = run_phase("dashboard_open", users, args.duration, dashboard=True)
        dashboard_cpu_extra = dashboard_open["server_cpu_ms"] - baseline["server_cpu_ms"]
        result = {
            "ok": True,
            "database_sync": {
                "enabled": True,
                "method": "fresh pg_dump + pg_restore before run",
                "dump_bytes": dump_path.stat().st_size,
            },
            "resources": {
                "run_root": str(RUN_ROOT),
                "http_port": isolated.HTTP_PORT,
                "postgres_port": isolated.PG_PORT,
                "server_data_root": str(isolated.SERVER_DATA_ROOT),
                "runtime_root": str(isolated.RUNTIME_ROOT),
                "production_pid_before": prod_before,
                "production_pid_after": production_pid(),
            },
            "startup_health": {
                "pid": health.get("pid"),
                "ready": health.get("ready"),
                "warm_ready": health.get("warm_ready"),
                "dashboard_recent_log_state": health.get("dashboard_recent_log_state"),
            },
            "phases": {
                "baseline_no_dashboard": baseline,
                "dashboard_open": dashboard_open,
            },
            "dashboard_overhead": {
                "server_cpu_ms_extra": round(dashboard_cpu_extra, 3),
                "server_cpu_percent_extra_of_one_core": round(dashboard_cpu_extra / max(1.0, dashboard_open["duration_seconds"] * 1000) * 100, 4),
                "server_cpu_percent_extra_whole_machine": round(dashboard_cpu_extra / max(1.0, dashboard_open["duration_seconds"] * 1000) / psutil.cpu_count() * 100, 4),
            },
            "cleanup_required": False,
        }
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
        return 0
    finally:
        isolated.stop_server(server)
        isolated.stop_postgres()
        if pg_process is not None and pg_process.poll() is None:
            try:
                pg_process.terminate()
            except Exception:
                pass
        remove_run_root()


if __name__ == "__main__":
    raise SystemExit(main())
