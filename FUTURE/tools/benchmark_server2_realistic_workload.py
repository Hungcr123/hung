"""Run a sustained mixed Server 2 workload with 100 distinct virtual learners."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import random
import sqlite3
import statistics
import threading
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import psutil
import requests


BASE = os.environ.get("FUTURE_BENCHMARK_BASE", "http://127.0.0.1:8877")
_SERVER_DATA_ROOT = Path(os.environ.get("FUTURE_SERVER_DATA_ROOT", r"C:\server data"))
DATABASE = Path(os.environ.get("FUTURE_SERVER2_SQLITE_DB", "")) if os.environ.get("FUTURE_SERVER2_SQLITE_DB") else _SERVER_DATA_ROOT / "server2.db"
MANIFEST = _SERVER_DATA_ROOT / "_future_server_data_manifest.json"
USERS = tuple(f"codexload{index:03d}" for index in range(1, 101))
ACTION_WEIGHTS = (
    ("tree_read", 10),
    ("tasks_read", 10),
    ("lesson_file_read", 15),
    ("pdf_progress_read", 8),
    ("drawing_read", 5),
    ("inventory_read", 5),
    ("leaderboard_read", 5),
    ("announcements_read", 7),
    ("settings_read", 7),
    ("lesson_time_write", 10),
    ("pdf_progress_write", 6),
    ("inventory_write", 4),
    ("pdf_pin_write", 5),
    ("drawing_write", 3),
)


def server_process() -> psutil.Process:
    port = int(BASE.rsplit(":", 1)[-1].split("/", 1)[0])
    for connection in psutil.net_connections(kind="tcp"):
        if connection.laddr and connection.laddr.port == port and connection.status == psutil.CONN_LISTEN and connection.pid:
            return psutil.Process(connection.pid)
    raise RuntimeError(f"Server 2 listener not found on port {port}")


def load_paths() -> tuple[list[str], list[str]]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files = {
        str(entry.get("path", "")).strip()
        for entries in (payload.get("folders") or {}).values()
        for entry in entries if isinstance(entries, list) and isinstance(entry, dict)
        if str(entry.get("type", "")).lower() == "file" and str(entry.get("path", "")).lower().startswith("common/")
    }
    lessons = sorted(
        (path for path in files if path.lower().endswith((".space_v", ".space_w", ".space_q", ".space_p", ".space_l", ".space_s"))),
        key=str.lower,
    )
    pdfs = sorted((path for path in files if path.lower().endswith(".pdf")), key=str.lower)
    if len(lessons) < 100 or len(pdfs) < 100:
        raise RuntimeError(f"Need 100 lessons/PDFs, found lessons={len(lessons)} pdfs={len(pdfs)}")
    return lessons[:100], pdfs[:100]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def request_sizes(response: requests.Response) -> tuple[int, int, int]:
    decoded = len(response.content)
    wire = int(response.headers.get("Content-Length") or decoded)
    body = response.request.body
    request_bytes = len(body) if isinstance(body, bytes) else len(str(body or "").encode("utf-8"))
    return decoded, wire, request_bytes


def percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, int(len(ordered) * ratio) - 1)] if ordered else 0.0


def sample_slope_per_minute(samples: list[dict], key: str) -> float:
    if len(samples) < 2:
        return 0.0
    x0 = float(samples[0]["at"])
    xs = [float(row["at"]) - x0 for row in samples]
    ys = [float(row.get(key, 0) or 0) for row in samples]
    x_mean = statistics.mean(xs)
    y_mean = statistics.mean(ys)
    denominator = sum((value - x_mean) ** 2 for value in xs)
    if denominator <= 0:
        return 0.0
    return sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denominator * 60.0


def summarize_resource_samples(samples: list[dict]) -> dict:
    if not samples:
        return {}
    halfway = max(0, len(samples) // 2)
    second_half = samples[halfway:]
    rss_values = [int(row["rss_bytes"]) for row in samples]
    return {
        "samples": len(samples),
        "rss_start_bytes": rss_values[0],
        "rss_end_bytes": rss_values[-1],
        "rss_delta_bytes": rss_values[-1] - rss_values[0],
        "rss_max_bytes": max(rss_values),
        "rss_p95_bytes": int(percentile(rss_values, 0.95)),
        "rss_slope_bytes_per_minute": round(sample_slope_per_minute(samples, "rss_bytes"), 3),
        "rss_second_half_slope_bytes_per_minute": round(sample_slope_per_minute(second_half, "rss_bytes"), 3),
        "threads_start": int(samples[0]["threads"]),
        "threads_end": int(samples[-1]["threads"]),
        "threads_max": max(int(row["threads"]) for row in samples),
        "handles_start": int(samples[0].get("handles", 0) or 0),
        "handles_end": int(samples[-1].get("handles", 0) or 0),
        "handles_max": max(int(row.get("handles", 0) or 0) for row in samples),
        "connections_start": int(samples[0]["connections"]),
        "connections_end": int(samples[-1]["connections"]),
        "connections_max": max(int(row["connections"]) for row in samples),
    }


def summarize_rows(rows: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["action"]].append(row)
    result = {}
    for action, action_rows in sorted(grouped.items()):
        latencies = [float(row["latency_ms"]) for row in action_rows]
        result[action] = {
            "requests": len(action_rows),
            "errors": sum(1 for row in action_rows if row.get("error")),
            "statuses": dict(Counter(int(row.get("status", 0)) for row in action_rows)),
            "p50_ms": round(statistics.median(latencies), 3),
            "p95_ms": round(percentile(latencies, 0.95), 3),
            "p99_ms": round(percentile(latencies, 0.99), 3),
            "decoded_response_bytes": sum(int(row.get("decoded", 0)) for row in action_rows),
            "wire_response_bytes": sum(int(row.get("wire", 0)) for row in action_rows),
            "request_body_bytes": sum(int(row.get("request_bytes", 0)) for row in action_rows),
            "retries": sum(1 for row in action_rows if row.get("retry")),
            "replays": sum(1 for row in action_rows if row.get("replay")),
        }
    return result


class VirtualUser:
    def __init__(self, index: int, username: str, token: str, lesson_path: str, pdf_path: str, seed: int):
        self.index = index
        self.username = username
        self.lesson_path = lesson_path
        self.pdf_path = pdf_path
        self.pdf_identity = f"realistic-pdf-{index:03d}"
        self.pdf_page = 1 + index % 10
        self.profile = ("new", "light", "medium", "heavy")[min(3, index // 25)]
        self.random = random.Random(seed + index * 7919)
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}", "Accept-Encoding": "gzip"})
        self.time_session_id = f"realistic-time-{uuid.uuid4().hex}"
        self.time_sequence = 0
        self.offline_lease = ""
        self.etags: dict[str, str] = {}
        self.last_inventory_event = ""
        self.last_drawing_payload: dict | None = None
        self.progress_counter = 0

    def choose_action(self) -> str:
        pick = self.random.uniform(0, sum(weight for _action, weight in ACTION_WEIGHTS))
        upto = 0.0
        for action, weight in ACTION_WEIGHTS:
            upto += weight
            if pick <= upto:
                return action
        return ACTION_WEIGHTS[-1][0]

    def request(self, action: str, retry: bool = False, replay: bool = False) -> dict:
        started = time.perf_counter()
        response = None
        try:
            if action == "tree_read":
                headers = {"If-None-Match": self.etags["tree"]} if self.etags.get("tree") else {}
                response = self.session.get(f"{BASE}/server-data/tree-preload", headers=headers, timeout=45)
                if response.headers.get("ETag"):
                    self.etags["tree"] = response.headers["ETag"]
            elif action == "tasks_read":
                response = self.session.get(f"{BASE}/lesson-tasks", params={"user": self.username}, timeout=30)
            elif action == "lesson_file_read":
                response = self.session.get(f"{BASE}/server-data/file", params={"path": self.lesson_path}, timeout=45)
            elif action == "pdf_progress_read":
                response = self.session.get(
                    f"{BASE}/space-pdf/progress",
                    params={"path": self.pdf_path, "identity": self.pdf_identity},
                    timeout=30,
                )
            elif action == "drawing_read":
                response = self.session.get(
                    f"{BASE}/space-pdf/drawing",
                    params={"path": self.pdf_path, "identity": self.pdf_identity, "page": self.pdf_page},
                    timeout=30,
                )
            elif action == "inventory_read":
                response = self.session.get(f"{BASE}/inventory", params={"response": "compact-v1"}, timeout=30)
            elif action == "leaderboard_read":
                response = self.session.get(
                    f"{BASE}/vocab/leaderboard",
                    params={"limit": 20, "scope": "month", "type": "space_v"},
                    timeout=30,
                )
            elif action in {"announcements_read", "settings_read"}:
                key = "announcements" if action == "announcements_read" else "settings"
                headers = {"If-None-Match": self.etags[key]} if self.etags.get(key) else {}
                response = self.session.get(f"{BASE}/{key}", headers=headers, timeout=30)
                if response.headers.get("ETag"):
                    self.etags[key] = response.headers["ETag"]
            elif action == "lesson_time_write":
                sequence = max(0, self.time_sequence - 1) if replay else self.time_sequence + 1
                payload = {
                    "path": self.lesson_path,
                    "space": "Space_V",
                    "seconds": 1,
                    "protocol": "server-time-v1",
                    "session_id": self.time_session_id,
                    "sequence": sequence,
                    "offline_lease": self.offline_lease,
                }
                response = self.session.post(f"{BASE}/lesson/time", json=payload, timeout=30)
                if not replay and response.ok:
                    self.time_sequence = sequence
                    time_payload = response.json().get("time") or {}
                    self.offline_lease = str(time_payload.get("offlineLease") or self.offline_lease)
            elif action in {"pdf_progress_write", "pdf_pin_write"}:
                self.progress_counter += 1
                page = 1 + (self.pdf_page + self.progress_counter) % 40
                stamp = utc_now()
                payload = {
                    "path": self.pdf_path,
                    "identity": self.pdf_identity,
                    "title": f"Realistic PDF {self.index:03d}",
                    "mode": "pdf",
                    "page": page,
                    "pages": 80,
                    "savedAt": stamp,
                    "state": {"page": page, "pages": 80, "recentPages": [page, self.pdf_page]},
                }
                source = "realistic_pdf_progress"
                if action == "pdf_pin_write":
                    payload.update({"pinOnly": True, "pinnedPages": sorted({self.pdf_page, page}), "pinnedPagesUpdatedAt": stamp})
                    payload["state"].update({"pinnedPages": payload["pinnedPages"], "pinnedPagesUpdatedAt": stamp})
                    source = "pdf_pin_save"
                response = self.session.post(f"{BASE}/space-pdf/progress?client_source={source}", json=payload, timeout=45)
            elif action == "inventory_write":
                event_id = self.last_inventory_event if retry and self.last_inventory_event else f"realistic:{self.username}:{uuid.uuid4().hex}"
                self.last_inventory_event = event_id
                response = self.session.post(
                    f"{BASE}/inventory/award?response=delta-v1",
                    json={
                        "event_id": event_id,
                        "quantity": 1,
                        "item": {"id": "realistic_crystal", "name": "Realistic Crystal", "use": "Synthetic sustained workload"},
                    },
                    timeout=30,
                )
            elif action == "drawing_write":
                if retry and self.last_drawing_payload:
                    payload = dict(self.last_drawing_payload)
                else:
                    stamp = utc_now()
                    payload = {
                        "path": self.pdf_path,
                        "identity": self.pdf_identity,
                        "title": f"Realistic PDF {self.index:03d}",
                        "mode": "pdf",
                        "page": self.pdf_page,
                        "operationId": f"realistic-drawing:{self.username}:{uuid.uuid4().hex}",
                        "clientUpdatedAt": stamp,
                        "vector": {
                            "version": 2,
                            "width": 10000,
                            "height": 10000,
                            "items": [{
                                "kind": "pen",
                                "color": "#f25f3a",
                                "width": 16,
                                "points": [{"x": 100 + self.progress_counter, "y": 200}, {"x": 350 + self.progress_counter, "y": 450}],
                            }],
                        },
                    }
                    self.last_drawing_payload = dict(payload)
                response = self.session.post(f"{BASE}/space-pdf/drawing", json=payload, timeout=45)
            else:
                raise RuntimeError(f"Unknown action: {action}")
            status = int(response.status_code)
            if status not in {200, 304, 429}:
                response.raise_for_status()
            decoded, wire, request_bytes = request_sizes(response)
            return {
                "action": action,
                "latency_ms": (time.perf_counter() - started) * 1000,
                "status": status,
                "decoded": decoded,
                "wire": wire,
                "request_bytes": request_bytes,
                "retry": retry,
                "replay": replay,
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
                "retry": retry,
                "replay": replay,
                "error": str(exc),
            }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=120.0)
    parser.add_argument("--think-min", type=float, default=0.4)
    parser.add_argument("--think-max", type=float, default=1.6)
    parser.add_argument("--seed", type=int, default=20260720)
    parser.add_argument("--label", default="steady")
    parser.add_argument("--output", default="")
    parser.add_argument("--only-action", choices=tuple(action for action, _weight in ACTION_WEIGHTS), default="")
    parser.add_argument("--secondary-action", choices=("",) + tuple(action for action, _weight in ACTION_WEIGHTS), default="")
    parser.add_argument("--secondary-users", type=int, default=0)
    parser.add_argument("--retry-rate", type=float, default=0.15)
    parser.add_argument("--replay-rate", type=float, default=0.08)
    parser.add_argument("--sample-interval", type=float, default=0.2)
    args = parser.parse_args()
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active benchmark only")
    lessons, pdfs = load_paths()
    process = server_process()

    def login(index: int) -> tuple[int, str]:
        username = USERS[index]
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        if (response.json().get("server_data") or {}).get("load_test") is not True:
            raise RuntimeError(f"Load-test isolation missing for {username}")
        return index, str(response.json()["token"])

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        tokens = dict(pool.map(login, range(100)))
    users = [VirtualUser(index, USERS[index], tokens[index], lessons[index], pdfs[index], args.seed) for index in range(100)]

    # Establish signed time leases before the timed workload.
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        lease_rows = list(pool.map(lambda user: user.request("lesson_time_write"), users))
    if any(row.get("error") for row in lease_rows):
        raise RuntimeError(f"Time lease setup failed: {[row for row in lease_rows if row.get('error')][:3]}")

    # Create four stable state profiles without counting setup in the measured phase.
    for user in users[25:50]:
        user.request("pdf_progress_write")
    for user in users[50:75]:
        for _ in range(3):
            user.request("pdf_progress_write")
        user.request("drawing_write")
    for user in users[75:]:
        for _ in range(8):
            user.request("pdf_progress_write")
        user.request("pdf_pin_write")
        for _ in range(3):
            user.request("drawing_write")

    rows: list[dict] = []
    rows_lock = threading.Lock()
    start_barrier = threading.Barrier(len(users))
    started_wall = time.perf_counter()
    deadline = started_wall + max(1.0, args.duration)
    before_cpu = sum(process.cpu_times()[:2])
    before_io = process.io_counters()
    wal_path = Path(str(DATABASE) + "-wal")
    before_wal = wal_path.stat().st_size if wal_path.exists() else 0
    writer_before = requests.get(f"{BASE}/health", timeout=15).json().get("sqlite_writer", {})
    writer_samples: list[dict] = []
    resource_samples: list[dict] = []
    writer_sample_stop = threading.Event()

    # Added 2026-07-21: expose observer load and process growth so soak results cannot hide health-poll CPU or leaks.
    def sample_writer_queue() -> None:
        last_resource_sample = 0.0
        sample_interval = max(0.1, float(args.sample_interval or 0.2))
        while not writer_sample_stop.wait(sample_interval):
            now = time.perf_counter()
            try:
                writer = requests.get(f"{BASE}/health", timeout=5).json().get("sqlite_writer", {})
                writer_samples.append({
                    "at": now,
                    "depth": max(0, int(writer.get("queue_depth", 0) or 0)),
                    "tasks": max(0, int(writer.get("tasks", 0) or 0)),
                    "batches": max(0, int(writer.get("batches", 0) or 0)),
                })
            except requests.RequestException:
                pass
            if now - last_resource_sample >= 1.0:
                memory = process.memory_info()
                try:
                    handles = process.num_handles()
                except (AttributeError, psutil.Error):
                    handles = 0
                try:
                    connections = len(process.net_connections(kind="tcp"))
                except psutil.Error:
                    connections = 0
                resource_samples.append({
                    "at": now,
                    "rss_bytes": int(memory.rss),
                    "threads": int(process.num_threads()),
                    "handles": int(handles),
                    "connections": int(connections),
                })
                last_resource_sample = now

    writer_sampler = threading.Thread(target=sample_writer_queue, name="server2-writer-queue-sampler", daemon=True)
    writer_sampler.start()

    def run_user(user: VirtualUser) -> int:
        local_rows = []
        start_barrier.wait()
        while time.perf_counter() < deadline:
            secondary_cutoff = 100 - max(0, min(100, args.secondary_users))
            action = args.secondary_action if args.secondary_action and user.index >= secondary_cutoff else (args.only_action or user.choose_action())
            replay = action == "lesson_time_write" and user.random.random() < max(0.0, min(1.0, args.replay_rate))
            retry = action in {"inventory_write", "drawing_write"} and user.random.random() < max(0.0, min(1.0, args.retry_rate))
            row = user.request(action, retry=retry, replay=replay)
            local_rows.append(row)
            # Simulate a lost response by safely replaying a small fraction of idempotent writes.
            if not row.get("error") and action in {"inventory_write", "drawing_write"} and user.random.random() < 0.03:
                local_rows.append(user.request(action, retry=True))
            time.sleep(user.random.uniform(max(0.0, args.think_min), max(args.think_min, args.think_max)))
        with rows_lock:
            rows.extend(local_rows)
        return len(local_rows)

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as pool:
            list(pool.map(run_user, users))
    finally:
        writer_sample_stop.set()
        writer_sampler.join(timeout=2.0)

    wall_seconds = time.perf_counter() - started_wall
    after_cpu = sum(process.cpu_times()[:2])
    after_io = process.io_counters()
    after_wal = wal_path.stat().st_size if wal_path.exists() else 0
    writer_after = requests.get(f"{BASE}/health", timeout=15).json().get("sqlite_writer", {})
    errors = [row for row in rows if row.get("error")]
    connection = sqlite3.connect(DATABASE)
    profiles = {
        "progress_rows": connection.execute("SELECT COUNT(*) FROM lesson_progress WHERE username LIKE 'codexload%'").fetchone()[0],
        "progress_namespaces": connection.execute("SELECT COUNT(*) FROM lesson_progress_namespaces WHERE username LIKE 'codexload%'").fetchone()[0],
        "time_rows": connection.execute("SELECT COUNT(*) FROM lesson_time WHERE username LIKE 'codexload%'").fetchone()[0],
        "drawing_rows": connection.execute("SELECT COUNT(*) FROM pdf_drawings WHERE username LIKE 'codexload%'").fetchone()[0],
        "inventory_rows": connection.execute("SELECT COUNT(*) FROM inventory_items WHERE username LIKE 'codexload%'").fetchone()[0],
    }
    connection.close()
    filesystem_wal = []
    for index in range(1, 101):
        path = Path(rf"C:\QMLearn\users\codexload{index:03d}\_future_space_pdf_progress.json.wal.jsonl")
        if path.is_file():
            filesystem_wal.append({"path": str(path), "bytes": path.stat().st_size})
    result = {
        "label": args.label,
        "users": len(users),
        "duration_seconds": round(wall_seconds, 3),
        "requests": len(rows),
        "requests_per_second": round(len(rows) / max(0.001, wall_seconds), 3),
        "server_cpu_ms": round((after_cpu - before_cpu) * 1000, 3),
        "server_cpu_ms_per_request": round((after_cpu - before_cpu) * 1000 / max(1, len(rows)), 3),
        "errors": len(errors),
        "error_samples": errors[:5],
        "profile_users": {"new": 25, "light": 25, "medium": 25, "heavy": 25},
        "state_rows": profiles,
        "process_io": {
            "read_ops": max(0, after_io.read_count - before_io.read_count),
            "write_ops": max(0, after_io.write_count - before_io.write_count),
            "read_bytes": max(0, after_io.read_bytes - before_io.read_bytes),
            "write_bytes": max(0, after_io.write_bytes - before_io.write_bytes),
        },
        "wal_size_delta": after_wal - before_wal,
        "sqlite_writer": {
            "samples": len(writer_samples),
            "observer_health_requests": len(writer_samples) + 2,
            "observer_sample_interval_seconds": max(0.1, float(args.sample_interval or 0.2)),
            "queue_depth_max": max((row["depth"] for row in writer_samples), default=0),
            "queue_depth_p95": round(percentile([row["depth"] for row in writer_samples], 0.95), 3) if writer_samples else 0,
            "queue_nonzero_samples": sum(1 for row in writer_samples if row["depth"] > 0),
            "delta": {
                key: round(float(writer_after.get(key, 0) or 0) - float(writer_before.get(key, 0) or 0), 3)
                for key in ("batches", "tasks", "queue_wait_ms", "begin_wait_ms", "commit_ms", "busy_errors")
            },
        },
        "server_resources": summarize_resource_samples(resource_samples),
        "filesystem_pdf_wal": {"files": len(filesystem_wal), "bytes": sum(row["bytes"] for row in filesystem_wal)},
        "actions": summarize_rows(rows),
        "cleanup_required": True,
    }
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
