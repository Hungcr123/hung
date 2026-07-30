"""Run reproducible phased mixed load across 100 isolated Server 2 learners."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import random
import sqlite3
import threading
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psutil
import requests

import benchmark_server2_realistic_workload as legacy


BASE = legacy.BASE
DATABASE = legacy.DATABASE
MANIFEST = legacy.MANIFEST
USERS = legacy.USERS
CACHED_OCR_PDF = "common/PDF/Empower/627_1- Empower 2nd B1 Student's Book.PDF"

ROLE_COUNTS = (
    ("space_v", 15),
    ("space_w", 5),
    ("space_q", 15),
    ("space_p", 5),
    ("space_l", 5),
    ("space_s", 5),
    ("leaderboard", 10),
    ("login_refresh", 10),
    ("lesson_vault", 15),
    ("pdf_cached", 8),
    ("pdf_ocr", 2),
    ("mixed", 5),
)

ROLE_ACTIONS = {
    "space_v": (("lesson_file_read", 2), ("progress_read", 3), ("progress_write", 2), ("progress_retry", 1), ("lesson_time_write", 1)),
    "space_w": (("lesson_file_read", 2), ("progress_read", 3), ("progress_write", 2), ("progress_retry", 1), ("lesson_time_write", 1)),
    "space_q": (("lesson_file_read", 2), ("progress_read", 3), ("progress_write", 2), ("progress_stale", 1), ("lesson_time_write", 1)),
    "space_p": (("lesson_file_read", 2), ("progress_read", 3), ("progress_write", 2), ("progress_retry", 1), ("lesson_time_write", 1)),
    "space_l": (("lesson_file_read", 2), ("progress_read", 3), ("progress_write", 2), ("progress_stale", 1), ("lesson_time_write", 1)),
    "space_s": (("lesson_file_read", 2), ("progress_read", 3), ("progress_write", 2), ("progress_retry", 1), ("lesson_time_write", 1)),
    "leaderboard": (("leaderboard_read", 5), ("inventory_read", 1), ("announcements_read", 1), ("settings_read", 1)),
    "login_refresh": (("auth_me", 4), ("login_refresh", 1), ("tree_read", 1), ("settings_read", 1)),
    "lesson_vault": (("tree_read", 4), ("tasks_read", 2), ("lesson_file_read", 2), ("last_file_read", 1)),
    "pdf_cached": (("pdf_progress_read", 3), ("drawing_read", 2), ("cached_ocr_read", 2), ("pdf_progress_write", 1), ("pdf_pin_write", 1)),
    "pdf_ocr": (("pdf_progress_read", 2), ("cached_ocr_read", 3), ("cold_ocr_region", 1)),
    "mixed": (("inventory_read", 2), ("inventory_write", 1), ("announcements_read", 2), ("lesson_time_write", 2), ("drawing_write", 1)),
}

SPACE_SUFFIX = {
    "space_v": ".space_v",
    "space_w": ".space_w",
    "space_q": ".space_q",
    "space_p": ".space_p",
    "space_l": ".space_l",
    "space_s": ".space_s",
}

ROLE_SPACE = {
    "space_v": "Space_V",
    "space_w": "Space_W",
    "space_q": "Space_Q",
    "space_p": "Space_P",
    "space_l": "Space_L",
    "space_s": "Space_S",
}

FULL_PHASES = (
    ("warmup_25", 300.0, 25, 0.4, 1.6),
    ("steady_25", 600.0, 25, 0.4, 1.6),
    ("steady_50", 600.0, 50, 0.4, 1.6),
    ("steady_100", 900.0, 100, 0.4, 1.6),
    ("burst_100", 120.0, 100, 0.02, 0.12),
    ("recovery", 300.0, 0, 0.0, 0.0),
)

SMOKE_PHASES = (
    ("warmup_25", 8.0, 25, 0.15, 0.45),
    ("steady_50", 12.0, 50, 0.15, 0.45),
    ("steady_100", 18.0, 100, 0.15, 0.45),
    ("burst_100", 8.0, 100, 0.01, 0.05),
    ("recovery", 5.0, 0, 0.0, 0.0),
)

TRIAD_PHASES = (
    ("warmup_10", 8.0, 10, 0.15, 0.45),
    ("steady_50", 12.0, 50, 0.15, 0.45),
    ("steady_100", 18.0, 100, 0.15, 0.45),
    ("burst_100", 8.0, 100, 0.01, 0.05),
    ("recovery", 5.0, 0, 0.0, 0.0),
)

BOUNDED_PHASES = (
    ("warmup_25", 30.0, 25, 0.25, 0.8),
    ("steady_50", 60.0, 50, 0.3, 1.0),
    ("steady_100", 150.0, 100, 0.3, 1.0),
    ("burst_100", 30.0, 100, 0.01, 0.06),
    ("recovery", 30.0, 0, 0.0, 0.0),
)

PROBE_PHASES = (
    ("probe", 5.0, 100, 0.01, 0.05),
    ("recovery", 8.0, 0, 0.0, 0.0),
)


def clean(value: object = "") -> str:
    return str(value or "").strip()


def load_paths_by_space() -> tuple[dict[str, list[str]], list[str], dict[str, str], dict]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = {
        clean(entry.get("path")): entry
        for entries in (payload.get("folders") or {}).values()
        for entry in entries if isinstance(entries, list) and isinstance(entry, dict)
        if clean(entry.get("type")).lower() == "file" and clean(entry.get("path")).lower().startswith("common/")
    }
    files = sorted(entries, key=str.lower)
    spaces = {
        role: [path for path in files if path.lower().endswith(suffix)]
        for role, suffix in SPACE_SUFFIX.items()
    }
    raw_pdf_env = [
        clean(item).replace("\\", "/")
        for item in os.environ.get("FUTURE_BENCHMARK_RAW_PDF_PATHS", "").split(";")
        if clean(item)
    ]
    raw_pdf_env_set = {item.lower() for item in raw_pdf_env}
    pdfs = [
        path for path in files
        if path.lower().endswith((".pdf", ".space_pdf")) and path.lower() not in raw_pdf_env_set
    ]
    raw_pdfs = raw_pdf_env or [path for path in pdfs if path.lower().endswith(".pdf")]
    for role, paths in spaces.items():
        if not paths:
            raise RuntimeError(f"No lesson path for {role}")
    if len(pdfs) < 10:
        raise RuntimeError(f"Need at least 10 PDFs, found {len(pdfs)}")
    if not raw_pdfs:
        raise RuntimeError("Need at least 1 raw PDF for /pdf/ocr cold-region coverage")
    connection = sqlite3.connect(DATABASE)
    try:
        registry_ids = {
            clean(row[0]).lower(): clean(row[1])
            for row in connection.execute("SELECT normalized_path,file_id FROM lesson_file_aliases WHERE active=1")
        }
    finally:
        connection.close()
    lesson_ids = {
        path: registry_ids.get(
            (clean(entries[path].get("package_path")) if entries[path].get("package_backed") else path).lower(),
            "",
        )
        for path in files
    }
    selected = set(pdfs).union(*(set(paths) for paths in spaces.values()))
    missing = [path for path in selected if not lesson_ids.get(path)]
    if missing:
        raise RuntimeError(f"Canonical lesson_id missing for {len(missing)} benchmark paths: {missing[:3]}")
    identity_audit = {
        "selected_paths": len(selected),
        "registry_ids": sum(bool(lesson_ids.get(path)) for path in selected),
        "manifest_registry_mismatches": sum(clean(entries[path].get("lesson_id")) != lesson_ids.get(path) for path in selected),
    }
    return spaces, pdfs, raw_pdfs, lesson_ids, identity_audit


def role_names() -> list[str]:
    rows = []
    for role, count in ROLE_COUNTS:
        rows.extend([role] * count)
    if len(rows) != 100:
        raise RuntimeError(f"Role matrix must contain 100 users, got {len(rows)}")
    return rows


def choose_weighted(rng: random.Random, options: tuple[tuple[str, int], ...]) -> str:
    point = rng.uniform(0, sum(weight for _action, weight in options))
    total = 0.0
    for action, weight in options:
        total += weight
        if point <= total:
            return action
    return options[-1][0]


def response_row(action: str, started: float, response: requests.Response | None, error: str = "", **extra) -> dict:
    decoded = wire = request_bytes = 0
    status = 0
    if response is not None:
        status = int(response.status_code)
        decoded, wire, request_bytes = legacy.request_sizes(response)
    return {
        "action": action,
        "latency_ms": (time.perf_counter() - started) * 1000,
        "status": status,
        "decoded": decoded,
        "wire": wire,
        "request_bytes": request_bytes,
        "retry": action.endswith("retry"),
        "replay": action.endswith("stale"),
        "error": error,
        **extra,
    }


class MixedUser(legacy.VirtualUser):
    def __init__(self, *args, role: str, password: str, lesson_id: str, pdf_lesson_id: str, raw_pdf_path: str = "", disable_ocr: bool = False, forced_action: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self.role = role
        self.password = password
        self.lesson_id = clean(lesson_id)
        self.pdf_lesson_id = clean(pdf_lesson_id)
        self.pdf_identity = self.pdf_lesson_id
        self.raw_pdf_path = clean(raw_pdf_path)
        self.disable_ocr = disable_ocr
        self.forced_action = clean(forced_action)
        self.space = ROLE_SPACE.get(role, "Space_V")
        self.run_id = f"mixed-run-{self.username}-{uuid.uuid4().hex}"
        self.progress_identity = f"mixed:{self.username}:{self.role}"
        self.progress_operation = ""
        self.last_progress_payload: dict | None = None
        self.stale_progress_payload: dict | None = None

    def _reset_session_after_transport_abort(self) -> None:
        headers = dict(self.session.headers)
        try:
            self.session.close()
        except Exception:
            pass
        self.session = requests.Session()
        self.session.headers.update(headers)

    def choose_action(self) -> str:
        if self.forced_action:
            return self.forced_action
        if self.disable_ocr and self.role == "pdf_cached":
            return choose_weighted(self.random, (("pdf_progress_read", 3), ("drawing_read", 2), ("pdf_progress_write", 1), ("pdf_pin_write", 1)))
        if self.disable_ocr and self.role == "pdf_ocr":
            return choose_weighted(self.random, (("pdf_progress_read", 3), ("drawing_read", 2)))
        return choose_weighted(self.random, ROLE_ACTIONS[self.role])

    def _send(self, action: str, method: str, url: str, **kwargs) -> dict:
        started = time.perf_counter()
        response = None
        try:
            response = self.session.request(method, url, **kwargs)
            if response.status_code not in {200, 304, 429}:
                response.raise_for_status()
            return response_row(action, started, response, role=self.role)
        except Exception as exc:
            error_text = str(exc)
            if action in {"cached_ocr_read", "cold_ocr_region"} and ("10053" in error_text or "Connection aborted" in error_text):
                self._reset_session_after_transport_abort()
                retry_started = time.perf_counter()
                retry_response = None
                try:
                    retry_response = self.session.request(method, url, **kwargs)
                    if retry_response.status_code not in {200, 304, 429}:
                        retry_response.raise_for_status()
                    row = response_row(action, retry_started, retry_response, role=self.role)
                    row["transport_retry"] = True
                    return row
                except Exception as retry_exc:
                    return response_row(action, started, retry_response, str(retry_exc), role=self.role, transport_retry=True)
            return response_row(action, started, response, str(exc), role=self.role)

    def _progress_endpoint(self) -> str:
        if self.role == "space_v":
            return "/space-v/progress"
        if self.role == "space_w":
            return "/space-w/progress"
        if self.role == "space_q":
            return "/space-q/progress"
        return "/space-p/progress"

    def _progress_payload(self, stale: bool = False) -> dict:
        if stale and (self.stale_progress_payload or self.last_progress_payload):
            payload = json.loads(json.dumps(self.stale_progress_payload or self.last_progress_payload))
            old_stamp = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            payload["savedAt"] = old_stamp
            payload["updatedAt"] = old_stamp
            payload["syncOperationId"] = f"mixed-stale-{uuid.uuid4().hex}"
            payload.setdefault("state", {}).update({"savedAt": old_stamp, "updatedAt": old_stamp, "syncOperationId": payload["syncOperationId"]})
            return payload
        self.progress_counter += 1
        now = datetime.now(timezone.utc)
        stamp = now.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        operation_id = f"mixed-progress-{self.username}-{uuid.uuid4().hex}"
        total = 25 if self.role == "space_v" else (20 if self.role == "space_w" else (24 if self.role == "space_q" else 12))
        done = min(total - 1, self.progress_counter)
        state = {
            "savedAt": stamp,
            "updatedAt": stamp,
            "runId": self.run_id,
            "activeRun": True,
            "syncOperationId": operation_id,
            "complete": False,
            "lessonComplete": False,
            "completedRuns": 0,
        }
        payload = {
            "action": "autosave",
            "path": self.lesson_path,
            "identity": self.lesson_id,
            "lesson_id": self.lesson_id,
            "title": Path(self.lesson_path).stem,
            "savedAt": stamp,
            "updatedAt": stamp,
            "runId": self.run_id,
            "activeRun": True,
            "syncOperationId": operation_id,
            "complete": False,
            "completedRuns": 0,
            "state": state,
        }
        if self.role == "space_v":
            learned = [f"mixed-word-{index:03d}" for index in range(done)]
            payload.update({"nodeIndex": done, "nodeCount": total, "learnedCount": done, "learned": learned})
            state.update({"currentIndex": done, "nodeCount": total, "learnedCount": done, "learned": learned})
        elif self.role == "space_w":
            payload.update({"progressDone": done, "progressTotal": total})
            state.update({"progressDone": done, "progressTotal": total, "trainEnabled": bool(self.index % 2)})
        elif self.role == "space_q":
            payload.update({"nodeIndex": done, "nodeCount": total})
            state.update({"questionDone": done, "questionTotal": total})
        else:
            payload.update({"space": self.space, "nodeIndex": done, "nodeCount": total})
            state.update({"space": self.space, "spaceMode": self.space.lower(), "completedSegments": done, "totalSegments": total})
        if self.last_progress_payload:
            self.stale_progress_payload = json.loads(json.dumps(self.last_progress_payload))
            old_stamp = (now - timedelta(minutes=5)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            self.stale_progress_payload["savedAt"] = old_stamp
            self.stale_progress_payload["updatedAt"] = old_stamp
            self.stale_progress_payload.setdefault("state", {})["savedAt"] = old_stamp
        self.last_progress_payload = json.loads(json.dumps(payload))
        self.progress_operation = operation_id
        return payload

    def request(self, action: str, retry: bool = False, replay: bool = False) -> dict:
        if action in {"progress_read", "progress_write", "progress_retry", "progress_stale"}:
            endpoint = self._progress_endpoint()
            if action == "progress_read":
                return self._send(action, "GET", f"{BASE}{endpoint}", params={"path": self.lesson_path, "identity": self.lesson_id, "lesson_id": self.lesson_id, "space": self.space}, timeout=30)
            if action == "progress_retry" and self.last_progress_payload:
                payload = json.loads(json.dumps(self.last_progress_payload))
            else:
                payload = self._progress_payload(stale=action == "progress_stale")
            return self._send(action, "POST", f"{BASE}{endpoint}?client_source=mixed_100&response=compact-v1", json=payload, timeout=45)
        if action == "lesson_time_write":
            sequence = self.time_sequence + 1
            payload = {
                "path": self.lesson_path,
                "lesson_id": self.lesson_id,
                "space": self.space,
                "seconds": 1,
                "protocol": "server-time-v1",
                "session_id": self.time_session_id,
                "sequence": sequence,
                "offline_lease": self.offline_lease,
            }
            started = time.perf_counter()
            response = None
            try:
                response = self.session.post(f"{BASE}/lesson/time", json=payload, timeout=30)
                if response.status_code not in {200, 429}:
                    response.raise_for_status()
                if response.status_code == 200:
                    time_payload = response.json().get("time") or {}
                    self.offline_lease = clean(time_payload.get("offlineLease") or self.offline_lease)
                    self.time_sequence = sequence
                return response_row(action, started, response, role=self.role)
            except Exception as exc:
                return response_row(action, started, response, str(exc), role=self.role)
        if action == "auth_me":
            return self._send(action, "GET", f"{BASE}/auth/me", timeout=30)
        if action == "login_refresh":
            started = time.perf_counter()
            response = None
            try:
                response = requests.post(f"{BASE}/auth/login", json={"username": self.username, "password": self.password}, timeout=30)
                response.raise_for_status()
                token = clean(response.json().get("token"))
                if token:
                    self.session.headers.update({"Authorization": f"Bearer {token}"})
                return response_row(action, started, response, role=self.role)
            except Exception as exc:
                return response_row(action, started, response, str(exc), role=self.role)
        if action == "last_file_read":
            return self._send(action, "GET", f"{BASE}/server-data/last-file", timeout=30)
        if action == "cached_ocr_read":
            page = 10 + self.index % 20
            return self._send(action, "POST", f"{BASE}/pdf/cache-ocr-page?client_source=mixed_cached_ocr", json={"path": CACHED_OCR_PDF, "mode": "pdf", "page": page, "title": Path(CACHED_OCR_PDF).stem}, timeout=45)
        if action == "cold_ocr_region":
            page = 1 + self.index % 5
            return self._send(action, "POST", f"{BASE}/pdf/ocr?client_source=mixed_cold_ocr", json={"path": self.raw_pdf_path or self.pdf_path, "page": page, "scale": 2.0, "rect": {"x": 0.08, "y": 0.08, "width": 0.32, "height": 0.18}}, timeout=90)
        row = super().request(action, retry=retry, replay=replay)
        row["role"] = self.role
        return row


def process_category(process: psutil.Process, server_pid: int) -> str:
    if process.pid == server_pid:
        return "server2"
    try:
        text = " ".join(process.cmdline()).lower()
        name = process.name().lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return ""
    if "future_stt_worker" in text:
        return "stt_worker"
    if "future_distributed_worker" in text:
        return "distributed_worker"
    if "cloudflared" in text or "cloudflared" in name:
        return "cloudflared"
    if any(marker in text or marker in name for marker in ("tesseract", "pdftoppm", "mutool", "pdfinfo")):
        return "ocr_pdf_worker"
    return ""


def process_snapshot(server_pid: int) -> dict[str, dict]:
    grouped: dict[str, dict] = defaultdict(lambda: {"cpu_seconds": 0.0, "rss": 0, "read_bytes": 0, "write_bytes": 0, "pids": []})
    for process in psutil.process_iter():
        category = process_category(process, server_pid)
        if not category:
            continue
        try:
            cpu = process.cpu_times()
            io = process.io_counters()
            memory = process.memory_info()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        row = grouped[category]
        row["cpu_seconds"] += float(cpu.user + cpu.system)
        row["rss"] += int(memory.rss)
        row["read_bytes"] += int(io.read_bytes)
        row["write_bytes"] += int(io.write_bytes)
        row["pids"].append(process.pid)
    return dict(grouped)


def process_delta(before: dict, after: dict) -> dict:
    result = {}
    for category in sorted(set(before) | set(after)):
        left = before.get(category, {})
        right = after.get(category, {})
        result[category] = {
            "cpu_ms": round(max(0.0, float(right.get("cpu_seconds", 0)) - float(left.get("cpu_seconds", 0))) * 1000, 3),
            "rss_before": int(left.get("rss", 0)),
            "rss_after": int(right.get("rss", 0)),
            "read_bytes": max(0, int(right.get("read_bytes", 0)) - int(left.get("read_bytes", 0))),
            "write_bytes": max(0, int(right.get("write_bytes", 0)) - int(left.get("write_bytes", 0))),
            "pids": right.get("pids") or left.get("pids") or [],
        }
    return result


def system_cpu_percent(before, after) -> float:
    before_total = sum(before)
    after_total = sum(after)
    total = max(0.000001, after_total - before_total)
    idle = max(0.0, (after.idle + getattr(after, "iowait", 0.0)) - (before.idle + getattr(before, "iowait", 0.0)))
    return round(max(0.0, min(100.0, (1.0 - idle / total) * 100.0)), 3)


def sqlite_writer() -> dict:
    return requests.get(f"{BASE}/health", timeout=15).json().get("sqlite_writer", {})


def writer_delta(before: dict, after: dict) -> dict:
    return {
        key: round(float(after.get(key, 0) or 0) - float(before.get(key, 0) or 0), 3)
        for key in ("batches", "tasks", "queue_wait_ms", "begin_wait_ms", "commit_ms", "busy_errors")
    }


# Added 2026-07-26: expose live soak counters so a 30-minute run is only credited while mixed workload is active.
def workload_counter_summary(rows: list[dict], started: float, phase_name: str, active_count: int, login_successes: int, login_failures: int) -> dict:
    elapsed = max(0.001, time.perf_counter() - started)
    read_requests = 0
    write_requests = 0
    timeouts = 0
    errors = 0
    for row in rows:
        action = clean(row.get("action", "")).lower()
        error = clean(row.get("error", ""))
        if error:
            errors += 1
            if "timeout" in error.lower() or "timed out" in error.lower():
                timeouts += 1
        if any(marker in action for marker in ("write", "save", "sync", "complete", "drawing", "retry", "respond", "reset")):
            write_requests += 1
        else:
            read_requests += 1
    return {
        "phase": phase_name,
        "configured_virtual_users": 100,
        "actual_active_users": active_count,
        "cumulative_requests": len(rows),
        "read_requests": read_requests,
        "write_requests": write_requests,
        "requests_per_second": round(len(rows) / elapsed, 3),
        "login_successes": login_successes,
        "login_failures": login_failures,
        "errors": errors,
        "timeouts": timeouts,
        "elapsed_seconds": round(elapsed, 3),
    }


def wait_for_writer_quiescence(timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    previous = None
    stable = 0
    while time.monotonic() < deadline:
        current = sqlite_writer()
        key = (int(current.get("tasks", 0) or 0), int(current.get("batches", 0) or 0), int(current.get("queue_depth", 0) or 0))
        if key == previous and not key[2]:
            stable += 1
            if stable >= 3:
                return
        else:
            stable = 0
            previous = key
        time.sleep(0.2)
    raise RuntimeError("SQLite writer did not become quiescent")


def wait_for_server_warm(timeout: float = 180.0) -> dict:
    deadline = time.monotonic() + timeout
    last = {}
    while time.monotonic() < deadline:
        try:
            last = requests.get(f"{BASE}/health", timeout=15).json()
        except requests.RequestException as exc:
            last = {"warm_ready": False, "probe_error": str(exc)}
            time.sleep(0.5)
            continue
        if last.get("warm_ready"):
            return last
        if last.get("warm_finished_at") and not last.get("warm_ready"):
            raise RuntimeError(f"Server warm failed: {last.get('warm_status') or last.get('last_error')}")
        time.sleep(0.5)
    raise RuntimeError(f"Server warm timeout: {last.get('warm_status')}")


def wait_for_server_idle(process: psutil.Process, timeout: float = 180.0) -> dict:
    started = time.monotonic()
    deadline = started + timeout
    stable = 0
    previous_cpu = sum(process.cpu_times()[:2])
    previous_rss = int(process.memory_info().rss)
    last = {}
    while time.monotonic() < deadline:
        time.sleep(1.0)
        current_cpu = sum(process.cpu_times()[:2])
        current_rss = int(process.memory_info().rss)
        health = requests.get(f"{BASE}/health", timeout=15).json()
        queues = (health.get("workload") or {}).get("queues") or {}
        queue_busy = any(int(row.get("pending", 0) or 0) or int(row.get("active", 0) or 0) for row in queues.values() if isinstance(row, dict))
        writer = health.get("sqlite_writer") or {}
        cpu_delta = max(0.0, current_cpu - previous_cpu)
        rss_delta = abs(current_rss - previous_rss)
        last = {"cpu_ms_last_second": round(cpu_delta * 1000, 3), "rss": current_rss, "rss_delta": rss_delta, "queue_busy": queue_busy, "writer_depth": int(writer.get("queue_depth", 0) or 0)}
        if cpu_delta <= 0.25 and rss_delta <= 4 * 1024 * 1024 and not queue_busy and not last["writer_depth"]:
            stable += 1
            if stable >= 3:
                return {**last, "wait_seconds": round(time.monotonic() - started, 3)}
        else:
            stable = 0
        previous_cpu = current_cpu
        previous_rss = current_rss
    raise RuntimeError(f"Server idle timeout: {last}")


def run_phase(name: str, duration: float, active_users: list[MixedUser], think_min: float, think_max: float, server_pid: int, login_successes: int = 0, login_failures: int = 0) -> dict:
    writer_before = sqlite_writer()
    process_before = process_snapshot(server_pid)
    system_before = psutil.cpu_times()
    disk_before = psutil.disk_io_counters()
    wal_path = Path(str(DATABASE) + "-wal")
    wal_before = wal_path.stat().st_size if wal_path.exists() else 0
    rows: list[dict] = []
    lock = threading.Lock()
    started = time.perf_counter()
    deadline = started + duration
    next_heartbeat = started + 300.0

    if active_users:
        barrier = threading.Barrier(len(active_users))

        def run_user(user: MixedUser) -> None:
            barrier.wait()
            while time.perf_counter() < deadline:
                row = user.request(user.choose_action())
                with lock:
                    rows.append(row)
                time.sleep(user.random.uniform(think_min, think_max))

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(active_users)) as pool:
            futures = [pool.submit(run_user, user) for user in active_users]
            while futures:
                done, pending = concurrent.futures.wait(futures, timeout=1.0, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    future.result()
                futures = list(pending)
                now = time.perf_counter()
                if now >= next_heartbeat:
                    with lock:
                        snapshot = list(rows)
                    print("HEARTBEAT", json.dumps(workload_counter_summary(snapshot, started, name, len(active_users), login_successes, login_failures), ensure_ascii=True, separators=(",", ":")), flush=True)
                    next_heartbeat += 300.0
    else:
        time.sleep(duration)

    wall = time.perf_counter() - started
    system_after = psutil.cpu_times()
    disk_after = psutil.disk_io_counters()
    process_after = process_snapshot(server_pid)
    writer_after = sqlite_writer()
    wal_after = wal_path.stat().st_size if wal_path.exists() else 0
    errors = [row for row in rows if row.get("error")]
    return {
        "name": name,
        "active_users": len(active_users),
        "duration_seconds": round(wall, 3),
        "requests": len(rows),
        "requests_per_second": round(len(rows) / max(0.001, wall), 3),
        "errors": len(errors),
        "error_samples": errors[:5],
        "status_counts": dict(Counter(int(row.get("status", 0)) for row in rows)),
        "roles": dict(Counter(row.get("role", "") for row in rows)),
        "actions": legacy.summarize_rows(rows),
        "processes": process_delta(process_before, process_after),
        "whole_machine": {
            "cpu_percent": system_cpu_percent(system_before, system_after),
            "disk_read_bytes": max(0, int(disk_after.read_bytes - disk_before.read_bytes)),
            "disk_write_bytes": max(0, int(disk_after.write_bytes - disk_before.write_bytes)),
            "disk_read_ops": max(0, int(disk_after.read_count - disk_before.read_count)),
            "disk_write_ops": max(0, int(disk_after.write_count - disk_before.write_count)),
        },
        "sqlite_writer": writer_delta(writer_before, writer_after),
        "wal_size_delta": wal_after - wal_before,
    }


def database_state() -> dict:
    connection = sqlite3.connect(DATABASE)
    try:
        result = {
            "progress_by_space": dict(connection.execute("SELECT space,COUNT(*) FROM lesson_progress WHERE username LIKE 'codexload%' GROUP BY space")),
            "progress_namespaces": connection.execute("SELECT COUNT(*) FROM lesson_progress_namespaces WHERE username LIKE 'codexload%'").fetchone()[0],
            "time_rows": connection.execute("SELECT COUNT(*) FROM lesson_time WHERE username LIKE 'codexload%'").fetchone()[0],
            "time_seconds": connection.execute("SELECT COALESCE(SUM(seconds),0) FROM lesson_time WHERE username LIKE 'codexload%'").fetchone()[0],
            "drawing_rows": connection.execute("SELECT COUNT(*) FROM pdf_drawings WHERE username LIKE 'codexload%'").fetchone()[0],
            "inventory_rows": connection.execute("SELECT COUNT(*) FROM inventory_items WHERE username LIKE 'codexload%'").fetchone()[0],
            "auth_sessions": connection.execute("SELECT COUNT(*) FROM auth_sessions WHERE username LIKE 'codexload%'").fetchone()[0],
            "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
            "journal_mode": connection.execute("PRAGMA journal_mode").fetchone()[0],
            "synchronous": connection.execute("PRAGMA synchronous").fetchone()[0],
        }
        return result
    finally:
        connection.close()


def sqlite_runtime_gate() -> dict:
    required_tables = {
        "auth_sessions",
        "inventory_items",
        "lesson_progress",
        "lesson_progress_namespaces",
        "lesson_time",
        "pdf_drawings",
        "server_load_test_credentials",
        "users",
    }
    connection = sqlite3.connect(DATABASE)
    try:
        tables = {str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        result = {
            "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
            "journal_mode": clean(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower(),
            "synchronous": int(connection.execute("PRAGMA synchronous").fetchone()[0]),
            "missing_tables": sorted(required_tables - tables),
            "test_users": int(connection.execute("SELECT COUNT(*) FROM users WHERE is_test=1 AND username LIKE 'codexload%'").fetchone()[0]),
            "test_credentials": int(connection.execute("SELECT COUNT(*) FROM server_load_test_credentials WHERE username LIKE 'codexload%'").fetchone()[0]),
        }
    finally:
        connection.close()
    if result != {**result, "quick_check": "ok", "journal_mode": "wal", "synchronous": 2, "missing_tables": [], "test_users": 100, "test_credentials": 100}:
        raise RuntimeError(f"SQLite benchmark gate failed: {result}")
    return result


def legacy_test_artifacts() -> list[str]:
    if os.environ.get("FUTURE_BENCHMARK_LOCAL_LOGIN") == "1":
        return []
    qroot = Path(os.environ.get("FUTURE_QMLEARN_ROOT", r"C:\QMLearn"))
    server_root = Path(os.environ.get("FUTURE_SERVER_DATA_ROOT", r"C:\server data"))
    roots = (qroot / "users", qroot / "server_users", server_root)
    rows = []
    for root in roots:
        for index in range(1, 101):
            username = f"codexload{index:03d}"
            for target in (root / username, root / f"{username}.txt"):
                if target.exists():
                    rows.append(str(target))
        if root != server_root:
            rows.extend(str(path) for path in root.glob("codexload*_*"))
    return sorted(set(rows), key=str.lower)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("smoke", "triad", "bounded", "full", "probe"), default="smoke")
    parser.add_argument("--seed", type=int, default=20260721)
    parser.add_argument("--output", default="")
    parser.add_argument("--disable-ocr", action="store_true")
    parser.add_argument("--only-action", default="")
    parser.add_argument("--only-role", choices=tuple(dict(ROLE_COUNTS)), default="")
    parser.add_argument("--skip-server-warm", action="store_true")
    parser.add_argument("--skip-idle-gate", action="store_true")
    args = parser.parse_args()
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this benchmark only")

    sqlite_gate = sqlite_runtime_gate()
    legacy_before = legacy_test_artifacts()
    if legacy_before:
        raise RuntimeError(f"Legacy load-test artifacts must be cleaned before benchmark: {legacy_before[:3]}")
    spaces, pdfs, raw_pdfs, lesson_ids, identity_audit = load_paths_by_space()
    roles = role_names()
    server = legacy.server_process()
    warm_state = {} if args.skip_server_warm else wait_for_server_warm()

    def login(index: int) -> tuple[int, str]:
        if os.environ.get("FUTURE_BENCHMARK_LOCAL_LOGIN") == "1":
            response = requests.post(
                f"{BASE}/auth/codex-local-login",
                json={"username": USERS[index]},
                headers={"X-Future-Codex-Local-Login": "1"},
                timeout=30,
            )
        else:
            response = requests.post(f"{BASE}/auth/login", json={"username": USERS[index], "password": password}, timeout=30)
        try:
            payload = response.json()
        except Exception:
            payload = {"raw": response.text[:200]}
        if response.status_code != 200:
            raise RuntimeError(f"Login failed for {USERS[index]}: {response.status_code} {payload}")
        if (payload.get("server_data") or {}).get("load_test") is not True and os.environ.get("FUTURE_BENCHMARK_LOCAL_LOGIN") != "1":
            raise RuntimeError(f"Load-test isolation missing for {USERS[index]}")
        return index, clean(payload.get("token"))

    login_started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        tokens = dict(pool.map(login, range(100)))
    login_seconds = time.perf_counter() - login_started

    role_offsets = defaultdict(int)
    users = []
    for index, role in enumerate(roles):
        if role in spaces:
            pool = spaces[role]
            lesson = pool[role_offsets[role] % len(pool)]
            role_offsets[role] += 1
        else:
            lesson = spaces["space_v"][index % len(spaces["space_v"])]
        pdf = pdfs[index % len(pdfs)]
        raw_pdf = raw_pdfs[index % len(raw_pdfs)]
        users.append(MixedUser(
            index, USERS[index], tokens[index], lesson, pdf, args.seed,
            role=role,
            password=password,
            lesson_id=lesson_ids[lesson],
            pdf_lesson_id=lesson_ids[pdf],
            raw_pdf_path=raw_pdf,
            disable_ocr=args.disable_ocr,
            forced_action=args.only_action,
        ))

    # Establish signed leases once so timed heartbeats measure the normal path.
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        lease_rows = list(pool.map(lambda user: user.request("lesson_time_write"), users))
    if any(row.get("error") for row in lease_rows):
        raise RuntimeError(f"Lease setup failed: {[row for row in lease_rows if row.get('error')][:3]}")
    progress_users = [user for user in users if user.role in ROLE_SPACE]
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as pool:
        progress_seed_rows = list(pool.map(lambda user: user.request("progress_write"), progress_users))
    if any(row.get("error") for row in progress_seed_rows):
        raise RuntimeError(f"Progress setup failed: {[row for row in progress_seed_rows if row.get('error')][:3]}")

    order = [index for index, user in enumerate(users) if not args.only_role or user.role == args.only_role]
    random.Random(args.seed).shuffle(order)
    phases = (
        SMOKE_PHASES if args.profile == "smoke"
        else TRIAD_PHASES if args.profile == "triad"
        else BOUNDED_PHASES if args.profile == "bounded"
        else PROBE_PHASES if args.profile == "probe"
        else FULL_PHASES
    )
    wait_for_writer_quiescence(timeout=15.0)
    idle_state = {} if args.skip_idle_gate else wait_for_server_idle(server)
    results = []
    for name, duration, count, think_min, think_max in phases:
        active = [users[index] for index in order[: min(count, len(order))]]
        phase = run_phase(name, duration, active, think_min, think_max, server.pid, login_successes=len(tokens), login_failures=100 - len(tokens))
        results.append(phase)
        print("PHASE", json.dumps(phase, ensure_ascii=True, separators=(",", ":")), flush=True)

    legacy_after = legacy_test_artifacts()
    result = {
        "profile": args.profile,
        "seed": args.seed,
        "users": 100,
        "sessions": 100,
        "disable_ocr": args.disable_ocr,
        "only_action": args.only_action,
        "only_role": args.only_role,
        "server_warm": {
            "skipped": args.skip_server_warm,
            "ready": bool(warm_state.get("warm_ready")) if warm_state else False,
            "qmdict_ready": bool(warm_state.get("warm_ready")) if warm_state else False,
            "qmdict_ms": int(warm_state.get("qmdict_runtime_warm_ms", 0) or 0) if warm_state else 0,
        },
        "server_idle": {"skipped": args.skip_idle_gate, **idle_state},
        "role_matrix": dict(ROLE_COUNTS),
        "identity_coverage": {
            "canonical_lesson_ids": sum(1 for user in users if user.lesson_id),
            "canonical_pdf_ids": sum(1 for user in users if user.pdf_lesson_id),
            **identity_audit,
        },
        "sqlite_runtime_gate": sqlite_gate,
        "legacy_test_artifacts": {
            "before": legacy_before,
            "after": legacy_after,
            "created": sorted(set(legacy_after) - set(legacy_before), key=str.lower),
        },
        "login_seconds": round(login_seconds, 3),
        "phases": results,
        "database_state": database_state(),
        "cleanup_required": True,
    }
    encoded = json.dumps(result, ensure_ascii=True, indent=2)
    print(encoded)
    if args.output:
        Path(args.output).write_text(encoded, encoding="utf-8")
    return 0 if all(not phase["errors"] for phase in results) and not legacy_after else 2


if __name__ == "__main__":
    raise SystemExit(main())
