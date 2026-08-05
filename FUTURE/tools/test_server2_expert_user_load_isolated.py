#!/usr/bin/env python3
"""Fresh-snapshot 1/10/25-user read-path baseline for the Server 2 expert audit."""

from __future__ import annotations

import concurrent.futures
import json
import os
import random
import shutil
import stat
import statistics
import subprocess
import sys
import threading
import time
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "FUTURE" / "tools"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import test_lesson_complete_isolated_harness as isolated

RUN_ROOT = ROOT / "programe_cache" / "server2_expert_user_load_18877"
OUTPUT = Path(r"C:\Users\Admin\.codex\plans\server2_expert_user_load_20260801.json")
SOURCE_ROOT = Path(r"C:\server data")
MANIFEST = SOURCE_ROOT / "_future_server_data_manifest.json"
RUN_NONCE = f"{int(time.time() * 1000)}-{os.getpid()}"
USER_COUNT = 25
BUILDER_COMPLETION_TIMEOUT_SECONDS = 420.0
ROLES = ("space_v", "space_w", "space_q", "space_p", "space_l", "space_s", "space_pdf", "space_picture")
SUFFIXES = {
    "space_v": ".space_v",
    "space_w": ".space_w",
    "space_q": ".space_q",
    "space_p": ".space_p",
    "space_l": ".space_l",
    "space_s": ".space_s",
    "space_pdf": ".space_pdf",
    "space_picture": ".space_picture",
}


# Added 2026-08-01: isolate all database, runtime, worker, and Server Data resources.
def configure() -> None:
    isolated.RUN_ROOT = RUN_ROOT
    isolated.PG_ROOT = RUN_ROOT / "postgres"
    isolated.SERVER_DATA_ROOT = RUN_ROOT / "server-data"
    isolated.RUNTIME_ROOT = RUN_ROOT / "runtime"
    isolated.QMLEARN_ROOT = RUN_ROOT / "qml"
    isolated.SERVER_LOG = RUN_ROOT / "server.log"
    isolated.PG_LOG = RUN_ROOT / "postgres.log"


# Added 2026-08-03: prove an isolated benchmark never replaces production.
def listener_pid(port: int) -> int | None:
    for connection in psutil.net_connections(kind="tcp"):
        if connection.status == psutil.CONN_LISTEN and connection.laddr and connection.laddr.port == port:
            return int(connection.pid) if connection.pid else None
    return None


def assert_production_pid(expected: int | None, stage: str) -> int | None:
    current = listener_pid(8877)
    if current != expected:
        raise RuntimeError(f"production PID changed at {stage}: expected={expected}, current={current}")
    return current


# Added 2026-08-01: remove only the verified disposable audit root.
def remove_run_root() -> None:
    if not RUN_ROOT.exists():
        return

    def clear_readonly(func, path, _exc):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    shutil.rmtree(RUN_ROOT, onerror=clear_readonly)


# Added 2026-08-01: stop the isolated detached voice worker that survives a soft server exit.
def stop_isolated_voice_worker() -> None:
    for connection in psutil.net_connections(kind="tcp"):
        if not connection.laddr or connection.laddr.port != 18778 or connection.status != psutil.CONN_LISTEN or not connection.pid:
            continue
        try:
            process = psutil.Process(connection.pid)
            command = " ".join(process.cmdline()).lower()
            if "future_voice_worker_2.py" not in command or "18778" not in command:
                continue
            process.kill()
            process.wait(timeout=10)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            pass


# Added 2026-08-02: attach one disposable real TTS worker for builder throughput measurements.
def start_isolated_distributed_worker() -> tuple[subprocess.Popen, object]:
    log_path = RUN_ROOT / "distributed-worker.log"
    log_file = log_path.open("w", encoding="utf-8")
    env = dict(os.environ)
    env.update(
        {
            "FUTURE_APP_ROOT": str(ROOT),
            "FUTURE_QMLEARN_ROOT": str(isolated.QMLEARN_ROOT),
            "FUTURE_SERVER_DATA_ROOT": str(isolated.SERVER_DATA_ROOT),
            "FUTURE_SERVER2_SQLITE_DB": str(isolated.SERVER_DATA_ROOT / "server2.db"),
        }
    )
    process = subprocess.Popen(
        [
            sys.executable,
            str(ROOT / "FUTURE" / "server2" / "future_distributed_worker_client.py"),
            "--server", "http://127.0.0.1:18890",
            "--token", "server2-expert-user-load-isolated-token",
            "--owner-user", "codexloadadmin",
            "--capabilities", "tts",
            "--max-jobs", "tts=4",
            "--poll-seconds", "0.25",
        ],
        cwd=ROOT,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    return process, log_file


# Added 2026-08-02: wait until the isolated worker is registered before P3 phases.
def wait_isolated_distributed_worker(timeout_seconds: float = 90.0) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last = {}
    while time.monotonic() < deadline:
        try:
            last = requests.get(f"{isolated.BASE}/health", timeout=5).json()
            workers = (last.get("distributed_workers") or {}).get("workers") or []
            if any(str(row.get("status", "")).lower() == "online" and "tts" in (row.get("capabilities") or []) for row in workers):
                return {"ready": True, "workers": workers}
        except Exception:
            pass
        time.sleep(0.5)
    return {"ready": False, "workers": (last.get("distributed_workers") or {}).get("workers") or []}


# Added 2026-08-02: terminate only the disposable worker child and close its log.
def stop_isolated_distributed_worker(process: subprocess.Popen | None, log_file: object) -> None:
    if process is not None:
        try:
            process.terminate()
            process.wait(timeout=20)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass
    try:
        log_file.close()
    except Exception:
        pass


# Added 2026-08-01: choose one real current fixture per supported lesson space.
def select_fixtures() -> dict[str, dict]:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = [
        entry
        for rows in (payload.get("folders") or {}).values()
        for entry in (rows if isinstance(rows, list) else [])
        if isinstance(entry, dict) and str(entry.get("type") or "").lower() == "file"
    ]
    result: dict[str, dict] = {}
    for role, suffix in SUFFIXES.items():
        candidates = [entry for entry in entries if str(entry.get("path") or "").lower().endswith(suffix)]
        common = [entry for entry in candidates if str(entry.get("path") or "").lower().startswith("common/")]
        entry = (common or candidates)[0] if (common or candidates) else None
        if not entry:
            raise RuntimeError(f"No fixture for {role}")
        result[role] = dict(entry)
    return result


# Added 2026-08-01: copy only selected lessons and directly referenced Structure payloads.
def prepare_server_data(fixtures: dict[str, dict]) -> dict[str, dict]:
    target_dir = isolated.SERVER_DATA_ROOT / "common" / "expert-audit"
    target_dir.mkdir(parents=True, exist_ok=True)
    prepared: dict[str, dict] = {}
    for role, entry in fixtures.items():
        source = SOURCE_ROOT / str(entry["path"]).replace("/", os.sep)
        target = target_dir / f"{role}{source.suffix}"
        shutil.copy2(source, target)
        lesson_id = str(entry.get("lesson_id") or entry.get("file_id") or "").strip()
        if source.suffix.lower() in {".space_pdf", ".space_picture"}:
            with zipfile.ZipFile(source) as package:
                package_manifest = json.loads(package.read("manifest.json"))
            if str(package_manifest.get("owner_scope") or "").lower().startswith("user:"):
                package_manifest["owner_scope"] = "common"
                with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as package:
                    package.writestr("manifest.json", json.dumps(package_manifest, ensure_ascii=False, separators=(",", ":")))
            lesson_id = str(package_manifest.get("lesson_id") or lesson_id).strip()
            asset_locator = str(package_manifest.get("asset_locator") or "").strip().replace("/", os.sep)
            if asset_locator:
                asset_source = SOURCE_ROOT / asset_locator
                asset_target = isolated.SERVER_DATA_ROOT / asset_locator
                asset_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(asset_source, asset_target)
        else:
            try:
                wrapper = json.loads(source.read_text(encoding="utf-8-sig"))
            except Exception:
                wrapper = {}
            lesson_id = str(wrapper.get("lesson_id") or wrapper.get("lessonId") or lesson_id).strip()
            structure = str(wrapper.get("structure") or "").strip().replace("/", os.sep)
            if structure:
                structure_source = SOURCE_ROOT / structure
                if structure_source.is_file():
                    structure_target = isolated.SERVER_DATA_ROOT / structure
                    structure_target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(structure_source, structure_target)
        prepared[role] = {
            "path": target.relative_to(isolated.SERVER_DATA_ROOT).as_posix(),
            "lesson_id": lesson_id,
            "bytes": target.stat().st_size,
        }
    for name in ("Sound", "Picture", "NPC_TOP"):
        (isolated.SERVER_DATA_ROOT / name).mkdir(parents=True, exist_ok=True)
    # Added 2026-08-02: create more unique list keys than the bounded response cache can retain.
    eviction_paths: list[str] = []
    source_role = prepared["space_q"]
    source_path = isolated.SERVER_DATA_ROOT / source_role["path"]
    for index in range(8):
        folder = isolated.SERVER_DATA_ROOT / "common" / f"expert-evict-{index:02d}"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"evict-{index:02d}{source_path.suffix}"
        shutil.copy2(source_path, target)
        eviction_paths.append(target.relative_to(isolated.SERVER_DATA_ROOT).as_posix())
    prepared["_eviction_paths"] = {"paths": eviction_paths}
    return prepared


# Added 2026-08-01: provision 25 distinct users only inside the copied PostgreSQL database.
def provision_users() -> list[str]:
    import psycopg
    from psycopg.types.json import Jsonb

    users = [f"codexperf{index:03d}" for index in range(1, USER_COUNT + 1)]
    now = "2026-08-01T00:00:00Z"
    with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
        for username in users:
            cursor.execute(
                """INSERT INTO future_server2.users
                   (username,is_admin,is_test,profile_json,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                   VALUES (%s,false,true,%s,%s,0,'','')
                   ON CONFLICT (username) DO UPDATE SET is_test=true,profile_json=excluded.profile_json""",
                (username, Jsonb({"source": "server2-expert-user-load"}), now),
            )
            cursor.execute(
                """INSERT INTO future_server2.user_auth_credentials
                   (username,password_hash,source_path,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                   VALUES (%s,%s,'server2-expert-user-load',%s,0,'','')
                   ON CONFLICT (username) DO UPDATE SET password_hash=excluded.password_hash""",
                (username, isolated.password_hash(isolated.PASSWORD), now),
            )
        connection.commit()
    return users


# Added 2026-08-01: calculate stable nearest-rank percentiles for latency evidence.
def percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    return ordered[max(0, min(len(ordered) - 1, int(len(ordered) * ratio) - 1))]


# Added 2026-08-01: capture server plus child-worker CPU, memory, I/O, handles, and files.
def process_snapshot(server: psutil.Process) -> dict:
    processes = [server]
    try:
        processes.extend(server.children(recursive=True))
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    row = {"cpu_seconds": 0.0, "rss_bytes": 0, "read_bytes": 0, "write_bytes": 0, "threads": 0, "handles": 0, "open_files": 0, "pids": [], "per_pid": {}}
    for process in processes:
        try:
            cpu = process.cpu_times()
            memory = process.memory_info()
            io = process.io_counters()
            row["cpu_seconds"] += float(cpu.user + cpu.system)
            row["rss_bytes"] += int(memory.rss)
            row["read_bytes"] += int(io.read_bytes)
            row["write_bytes"] += int(io.write_bytes)
            row["threads"] += int(process.num_threads())
            row["handles"] += int(process.num_handles()) if hasattr(process, "num_handles") else 0
            row["open_files"] += len(process.open_files())
            row["pids"].append(process.pid)
            row["per_pid"][process.pid] = {
                "cpu_seconds": float(cpu.user + cpu.system),
                "read_bytes": int(io.read_bytes),
                "write_bytes": int(io.write_bytes),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return row


# Added 2026-08-01: produce deltas without losing peak resource samples.
def process_delta(before: dict, after: dict, samples: list[dict], wall: float) -> dict:
    snapshots = [before, *samples, after]
    per_pid: dict[int, list[dict]] = defaultdict(list)
    for snapshot in snapshots:
        for pid, row in snapshot.get("per_pid", {}).items():
            per_pid[int(pid)].append(row)
    cpu_delta = sum(max(row["cpu_seconds"] for row in rows) - min(row["cpu_seconds"] for row in rows) for rows in per_pid.values())
    read_delta = sum(max(row["read_bytes"] for row in rows) - min(row["read_bytes"] for row in rows) for rows in per_pid.values())
    write_delta = sum(max(row["write_bytes"] for row in rows) - min(row["write_bytes"] for row in rows) for rows in per_pid.values())
    return {
        "cpu_seconds": round(cpu_delta, 4),
        "whole_machine_cpu_percent": round((cpu_delta / max(0.001, wall) / psutil.cpu_count()) * 100, 4),
        "rss_start_bytes": before["rss_bytes"],
        "rss_end_bytes": after["rss_bytes"],
        "rss_delta_bytes": after["rss_bytes"] - before["rss_bytes"],
        "rss_peak_bytes": max([before["rss_bytes"], after["rss_bytes"], *[sample["rss_bytes"] for sample in samples]]),
        "read_bytes": read_delta,
        "write_bytes": write_delta,
        "threads_peak": max([before["threads"], after["threads"], *[sample["threads"] for sample in samples]]),
        "handles_peak": max([before["handles"], after["handles"], *[sample["handles"] for sample in samples]]),
        "open_files_peak": max([before["open_files"], after["open_files"], *[sample["open_files"] for sample in samples]]),
    }


# Added 2026-08-01: convert one response into compact latency/cache evidence.
def request_row(action: str, role: str, started: float, response: requests.Response | None, error: str = "") -> dict:
    return {
        "action": action,
        "role": role,
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "status": int(response.status_code) if response is not None else 0,
        "bytes": len(response.content) if response is not None else 0,
        "cache": str(response.headers.get("X-Future-Cache-Hit") or "") if response is not None else "",
        "server_timing": str(response.headers.get("Server-Timing") or "") if response is not None else "",
        "error": error,
        "error_body": str(response.text[:300]) if response is not None and response.status_code >= 400 else "",
    }


# Added 2026-08-01: parse server-side phase timings for lock/CPU hotspot attribution.
def parse_server_timing(value: str) -> dict[str, float]:
    result = {}
    for name, duration in re.findall(r"([A-Za-z0-9_-]+);dur=([0-9.]+)", value or ""):
        result[name] = float(duration)
    return result


# Added 2026-08-01: run one representative authenticated read for the assigned role.
def perform_request(session: requests.Session, action: str, fixture: dict, role: str, username: str) -> dict:
    started = time.perf_counter()
    response = None
    try:
        if action == "auth":
            response = session.get(f"{isolated.BASE}/auth/me", timeout=30)
        elif action == "tree":
            response = session.get(f"{isolated.BASE}/server-data/tree-preload", timeout=45)
        elif action == "list":
            response = session.get(f"{isolated.BASE}/server-data/list", params={"path": "common/expert-audit"}, timeout=45)
        elif action == "tasks":
            response = session.get(f"{isolated.BASE}/lesson-tasks", params={"user": username}, timeout=30)
        elif action == "file":
            if role in {"space_pdf", "space_picture"}:
                response = session.post(f"{isolated.BASE}/lessons/open", json={"path": fixture["path"]}, timeout=45)
            else:
                response = session.get(f"{isolated.BASE}/server-data/file", params={"path": fixture["path"]}, timeout=45)
        elif action == "progress":
            if role == "space_v":
                endpoint = "/space-v/progress"
            elif role == "space_w":
                endpoint = "/space-w/progress"
            elif role == "space_q":
                endpoint = "/space-q/progress"
            elif role in {"space_pdf", "space_picture"}:
                endpoint = "/space-pdf/progress"
            else:
                endpoint = "/space-p/progress"
            response = session.get(
                f"{isolated.BASE}{endpoint}",
                params={"path": fixture["path"], "identity": fixture["lesson_id"], "lesson_id": fixture["lesson_id"], "space": role.replace("space_", "Space_").upper()},
                timeout=30,
            )
        elif action == "inventory":
            response = session.get(f"{isolated.BASE}/inventory", params={"response": "compact-v1"}, timeout=30)
        else:
            response = session.get(f"{isolated.BASE}/settings", timeout=30)
        if response.status_code not in {200, 304}:
            response.raise_for_status()
        return request_row(action, role, started, response)
    except Exception as exc:
        return request_row(action, role, started, response, f"{type(exc).__name__}: {exc}")


# Added 2026-08-01: summarize endpoint distributions and cache response headers.
def summarize_rows(rows: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["action"]].append(row)
    result = {}
    for action, action_rows in sorted(grouped.items()):
        latencies = [float(row["latency_ms"]) for row in action_rows]
        timing_by_name: dict[str, list[float]] = defaultdict(list)
        for row in action_rows:
            for name, duration in parse_server_timing(row["server_timing"]).items():
                timing_by_name[name].append(duration)
        result[action] = {
            "requests": len(action_rows),
            "errors": sum(1 for row in action_rows if row["error"]),
            "statuses": dict(Counter(row["status"] for row in action_rows)),
            "p50_ms": round(statistics.median(latencies), 3),
            "p95_ms": round(percentile(latencies, 0.95), 3),
            "p99_ms": round(percentile(latencies, 0.99), 3),
            "bytes": sum(int(row["bytes"]) for row in action_rows),
            "cache_headers": dict(Counter(row["cache"] or "none" for row in action_rows)),
            "roles": dict(Counter(row["role"] for row in action_rows)),
            "error_samples": [row["error_body"] or row["error"] for row in action_rows if row["error"]][:3],
            "server_timing_ms": {
                name: {
                    "p50": round(statistics.median(values), 3),
                    "p95": round(percentile(values, 0.95), 3),
                    "p99": round(percentile(values, 0.99), 3),
                    "max": round(max(values), 3),
                }
                for name, values in sorted(timing_by_name.items())
            },
        }
    return result


# Added 2026-08-01: execute a fixed request count with distinct concurrent users.
def run_phase(name: str, users: list[dict], active_count: int, iterations: int, server: psutil.Process) -> dict:
    active = users[:active_count]
    actions = ("auth", "tree", "list", "tasks", "file", "progress", "inventory", "settings")
    before_process = process_snapshot(server)
    before_health = requests.get(f"{isolated.BASE}/health", timeout=10).json()
    samples: list[dict] = []
    stop_samples = threading.Event()

    def sampler() -> None:
        while not stop_samples.wait(0.25):
            samples.append(process_snapshot(server))

    sample_thread = threading.Thread(target=sampler, daemon=True)
    sample_thread.start()
    started = time.perf_counter()

    def run_user(user: dict) -> list[dict]:
        rng = random.Random(20260801 + user["index"] + active_count * 100)
        rows = []
        for index in range(iterations):
            action = actions[(index + rng.randrange(len(actions))) % len(actions)]
            rows.append(perform_request(user["session"], action, user["fixture"], user["role"], user["username"]))
        return rows

    with concurrent.futures.ThreadPoolExecutor(max_workers=active_count) as pool:
        nested = list(pool.map(run_user, active))
    wall = time.perf_counter() - started
    stop_samples.set()
    sample_thread.join(timeout=2)
    after_process = process_snapshot(server)
    after_health = requests.get(f"{isolated.BASE}/health", timeout=10).json()
    rows = [row for group in nested for row in group]
    before_pg = before_health.get("postgres") or {}
    after_pg = after_health.get("postgres") or {}
    return {
        "name": name,
        "users": active_count,
        "requests": len(rows),
        "wall_seconds": round(wall, 3),
        "throughput_rps": round(len(rows) / max(0.001, wall), 3),
        "errors": sum(1 for row in rows if row["error"]),
        "latency": summarize_rows(rows),
        "process": process_delta(before_process, after_process, samples, wall),
        "postgres": {
            "sql_round_trips": int(after_pg.get("sql_round_trips", 0) or 0) - int(before_pg.get("sql_round_trips", 0) or 0),
            "transactions": int(after_pg.get("transactions", 0) or 0) - int(before_pg.get("transactions", 0) or 0),
            "pool_wait_count": int(after_pg.get("pool_wait_count", 0) or 0) - int(before_pg.get("pool_wait_count", 0) or 0),
            "pool_wait_ms": round(float(after_pg.get("pool_wait_ms_total", 0) or 0) - float(before_pg.get("pool_wait_ms_total", 0) or 0), 3),
            "pool_idle_end": int(after_pg.get("pool_idle", 0) or 0),
            "pool_active_end": int(after_pg.get("pool_active", 0) or 0),
        },
        "durable_tts_queue": after_health.get("durable_tts_queue") or {},
    }


# Added 2026-08-03: wait for this run's durable jobs so HTTP backpressure is not mistaken for throughput.
def wait_builder_completion(build_prefix: str, expected: int, timeout_seconds: float = BUILDER_COMPLETION_TIMEOUT_SECONDS) -> dict:
    import psycopg

    started = time.perf_counter()
    deadline = time.monotonic() + max(1.0, float(timeout_seconds or 0))
    rows = []
    query_errors: list[str] = []
    while time.monotonic() < deadline:
        try:
            with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT status, created_epoch, started_epoch, completed_epoch,
                           artifact_size, attempt_count, last_error
                    FROM future_server2.tts_jobs
                    WHERE build_id LIKE %s
                    ORDER BY build_id
                    """,
                    (f"{build_prefix}%",),
                )
                rows = list(cursor.fetchall())
        except psycopg.OperationalError as exc:
            query_errors.append(str(exc)[:240])
            time.sleep(0.25)
            continue
        terminal = sum(1 for row in rows if str(row[0]) in {"completed", "failed", "cancelled"})
        if len(rows) >= expected and terminal >= expected:
            break
        time.sleep(0.25)
    statuses = Counter(str(row[0]) for row in rows)
    queue_waits = [max(0.0, float(row[2]) - float(row[1])) * 1000 for row in rows if float(row[2] or 0) > 0]
    completions = [max(0.0, float(row[3]) - float(row[1])) * 1000 for row in rows if float(row[3] or 0) > 0]
    wall = time.perf_counter() - started
    completed = int(statuses.get("completed", 0))
    return {
        "ok": len(rows) == expected and completed == expected,
        "expected": expected,
        "observed": len(rows),
        "statuses": dict(statuses),
        "wall_seconds": round(wall, 3),
        "throughput_jobs_per_second": round(completed / max(0.001, wall), 3),
        "queue_wait_p50_ms": round(statistics.median(queue_waits), 3) if queue_waits else None,
        "queue_wait_p95_ms": round(percentile(queue_waits, 0.95), 3) if queue_waits else None,
        "queue_wait_p99_ms": round(percentile(queue_waits, 0.99), 3) if queue_waits else None,
        "completion_p50_ms": round(statistics.median(completions), 3) if completions else None,
        "completion_p95_ms": round(percentile(completions, 0.95), 3) if completions else None,
        "completion_p99_ms": round(percentile(completions, 0.99), 3) if completions else None,
        "artifact_bytes": sum(int(row[4] or 0) for row in rows),
        "attempts": sum(int(row[5] or 0) for row in rows),
        "error_samples": [str(row[6])[:240] for row in rows if str(row[6] or "")][:4],
        "query_error_samples": query_errors[:4],
    }


# Added 2026-08-02: exercise real P3 builder requests concurrently with learner reads.
def run_builder_phase(users: list[dict], server: psutil.Process, tag: str = "", count: int = 16) -> dict:
    results: list[dict] = []
    lock = threading.Lock()
    started = time.perf_counter()

    safe_tag = tag or "main"
    build_prefix = f"builder-audit-{RUN_NONCE}-{safe_tag}-"

    def submit(index: int) -> dict:
        request_started = time.perf_counter()
        try:
            response = requests.post(
                f"{isolated.BASE}/builder/tts",
                headers={"Host": "127.0.0.1:18877"},
                json={
                    "text": f"builder contention probe {RUN_NONCE} {safe_tag} {index} with enough text to occupy the background lane",
                    "voice": "kokoro:af_jessica",
                    "source": "builder_audit_p3",
                    "build_id": f"{build_prefix}{index}",
                },
                timeout=120,
            )
            response_payload = response.json()
            return {
                "status": response.status_code,
                "latency_ms": round((time.perf_counter() - request_started) * 1000, 3),
                "queued": bool(response.status_code == 503 or response_payload.get("queued")),
                "throttled_for_users": bool(response_payload.get("throttled_for_users")),
                "learner_requests": int(response_payload.get("learner_requests", 0) or 0),
                "error": "" if response.status_code < 400 or response.status_code == 503 else str(response_payload.get("error", "")),
            }
        except Exception as exc:
            return {"status": 0, "latency_ms": round((time.perf_counter() - request_started) * 1000, 3), "error": str(exc)}

    before = process_snapshot(server)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(submit, index) for index in range(max(1, int(count or 1)))]
        for future in futures:
            with lock:
                results.append(future.result())
    after = process_snapshot(server)
    latencies = [float(row["latency_ms"]) for row in results]
    completion = wait_builder_completion(build_prefix, len(results))
    return {
        "requests": len(results),
        "wall_seconds": round(time.perf_counter() - started, 3),
        "statuses": dict(Counter(str(row.get("status", 0)) for row in results)),
        "queued": sum(1 for row in results if row.get("queued")),
        "throttled_for_users": sum(1 for row in results if row.get("throttled_for_users")),
        "max_learner_requests": max((int(row.get("learner_requests", 0) or 0) for row in results), default=0),
        "errors": sum(1 for row in results if row.get("error")),
        "error_samples": [row.get("error", "") for row in results if row.get("error")][:4],
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(percentile(latencies, 0.95), 3),
        "p99_ms": round(percentile(latencies, 0.99), 3),
        "process_cpu_seconds": round(after["cpu_seconds"] - before["cpu_seconds"], 4),
        "process_read_bytes": max(0, after["read_bytes"] - before["read_bytes"]),
        "process_write_bytes": max(0, after["write_bytes"] - before["write_bytes"]),
        "completion": completion,
    }


# Added 2026-08-02: paired same-process cycles separate builder impact from tail-latency variance.
def run_paired_builder_cycle(users: list[dict], server: psutil.Process, index: int, active_count: int = 25, requests_per_user: int = 20) -> dict:
    holder: dict[str, dict] = {}

    # Warm the same lesson/task/cache keys before either measured arm so the
    # comparison is not simply cold-build versus warm-cache latency.
    warmup = run_phase(
        f"paired_warmup_{index}",
        users,
        active_count,
        max(4, requests_per_user // 4),
        server,
    )
    baseline = run_phase(f"paired_baseline_{index}", users, active_count, requests_per_user, server)

    def builder_target() -> None:
        holder["builder"] = run_builder_phase(users, server, tag=f"pair-{active_count}-{index}", count=16)

    thread = threading.Thread(target=builder_target, daemon=True)
    thread.start()
    time.sleep(0.25)
    mixed = run_phase(f"paired_mixed_{index}", users, active_count, requests_per_user, server)
    thread.join(timeout=BUILDER_COMPLETION_TIMEOUT_SECONDS + 60.0)
    if thread.is_alive():
        raise RuntimeError(f"Paired builder cycle {index} did not finish.")
    return {"index": index, "warmup": warmup, "mixed": mixed, "baseline": baseline, "builder": holder.get("builder", {})}


# Added 2026-08-02: fill the bounded per-user list cache and verify oldest-key eviction.
def run_cache_eviction_phase(users: list[dict], paths: list[str], server: psutil.Process) -> dict:
    if not paths:
        raise RuntimeError("cache eviction fixture list is empty")
    before = process_snapshot(server)
    rows: list[dict] = []
    started = time.perf_counter()
    for user in users:
        for path in paths:
            request_started = time.perf_counter()
            try:
                response = user["session"].get(
                    f"{isolated.BASE}/server-data/list",
                    params={"path": path.rsplit("/", 1)[0]},
                    headers={"Host": "127.0.0.1:18877"},
                    timeout=20,
                )
                rows.append({
                    "status": response.status_code,
                    "latency_ms": round((time.perf_counter() - request_started) * 1000, 3),
                    "cache": str(response.headers.get("X-Future-Cache-Hit") or ""),
                })
            except Exception as exc:
                rows.append({"status": 0, "latency_ms": round((time.perf_counter() - request_started) * 1000, 3), "cache": "", "error": str(exc)})
    first_path = paths[0].rsplit("/", 1)[0]
    last_path = paths[-1].rsplit("/", 1)[0]
    probes: dict[str, dict] = {}
    for label, path, user in (("oldest", first_path, users[0]), ("newest", last_path, users[-1])):
        request_started = time.perf_counter()
        response = user["session"].get(
            f"{isolated.BASE}/server-data/list",
            params={"path": path},
            headers={"Host": "127.0.0.1:18877"},
            timeout=20,
        )
        probes[label] = {
            "status": response.status_code,
            "latency_ms": round((time.perf_counter() - request_started) * 1000, 3),
            "cache": str(response.headers.get("X-Future-Cache-Hit") or ""),
        }
    after = process_snapshot(server)
    latencies = [float(row["latency_ms"]) for row in rows]
    return {
        "unique_keys": len(users) * len(paths),
        "requests": len(rows),
        "wall_seconds": round(time.perf_counter() - started, 3),
        "errors": sum(1 for row in rows if row.get("error") or row.get("status") != 200),
        "cache_headers": dict(Counter(row["cache"] or "none" for row in rows)),
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(percentile(latencies, 0.95), 3),
        "p99_ms": round(percentile(latencies, 0.99), 3),
        "probes": probes,
        "process": process_delta(before, after, [], max(0.001, time.perf_counter() - started)),
    }


# Added 2026-08-02: concurrently write distinct user progress and verify no cross-user or stale overwrite.
def run_progress_mutation_phase(users: list[dict], fixture: dict, server: psutil.Process) -> dict:
    path = str(fixture["path"])
    identity = str(fixture["lesson_id"])
    started = time.perf_counter()

    def write_one(user: dict) -> dict:
        now = time.time()
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
        run_id = f"audit-{user['username']}-{int(now * 1000)}"
        body = {
            "action": "autosave",
            "path": path,
            "identity": identity,
            "lesson_id": identity,
            "file_id": identity,
            "runId": run_id,
            "activeRun": True,
            "nodeIndex": 1,
            "nodeCount": 13,
            "learnedCount": 1,
            "savedAt": stamp,
            "updatedAt": stamp,
            "syncOperationId": f"{run_id}-op",
            "state": {
                "runId": run_id,
                "activeRun": True,
                "learned": [user["username"]],
                "learnedWords": [{"word": user["username"]}],
                "learnedCount": 1,
                "nodeCount": 13,
                "nodeIndex": 1,
                "savedAt": stamp,
                "lessonSource": {"path": path, "lesson_id": identity},
            },
        }
        response = user["session"].post(
            f"{isolated.BASE}/space-v/progress?client_source=expert_progress_mutation&response=compact-v1",
            headers={"Host": "127.0.0.1:18877"},
            json=body,
            timeout=45,
        )
        return {"user": user["username"], "status": response.status_code, "body": response.json()}

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(users)) as pool:
        writes = list(pool.map(write_one, users))
    reads: list[dict] = []
    for user in users:
        response = user["session"].get(
            f"{isolated.BASE}/space-v/progress",
            params={"path": path, "identity": identity, "lesson_id": identity},
            headers={"Host": "127.0.0.1:18877"},
            timeout=45,
        )
        payload = response.json()
        record = payload.get("record") if isinstance(payload.get("record"), dict) else payload
        learned = record.get("state", {}).get("learned", []) if isinstance(record.get("state"), dict) else []
        reads.append({"user": user["username"], "status": response.status_code, "learned": learned})
    return {
        "users": len(users),
        "writes": len(writes),
        "write_errors": sum(1 for row in writes if row.get("status") != 200),
        "read_errors": sum(1 for row in reads if row.get("status") != 200),
        "cross_user_leaks": sum(1 for row in reads if row.get("learned") and row["learned"] != [row["user"]]),
        "wall_seconds": round(time.perf_counter() - started, 3),
        "process": process_snapshot(server),
    }


# Added 2026-08-01: orchestrate fresh snapshot, current fixtures, restart, and cleanup evidence.
def main() -> int:
    configure()
    production_pid_before = listener_pid(8877)
    remove_run_root()
    RUN_ROOT.mkdir(parents=True)
    server_process = None
    distributed_worker_process = None
    distributed_worker_log = None
    distributed_worker_registration = {"ready": False, "workers": []}
    try:
        isolated.start_postgres()
        dump = isolated.sync_production_database_snapshot()
        isolated.initialize_schema()
        fixtures = prepare_server_data(select_fixtures())
        usernames = provision_users()
        server_process = isolated.start_server(
            no_preload=False,
            extra_env={
                "FUTURE_DISTRIBUTED_WORKER_PORT": "18890",
                "FUTURE_DISTRIBUTED_WORKER_HOST": "127.0.0.1",
                "FUTURE_DISTRIBUTED_WORKER_TOKEN": "server2-expert-user-load-isolated-token",
                "FUTURE_VOICE_WORKER_PORT": "18778",
            },
        )
        health = isolated.wait_health(server_process)
        production_pid_during = assert_production_pid(production_pid_before, "isolated-server-ready")
        distributed_worker_process, distributed_worker_log = start_isolated_distributed_worker()
        distributed_worker_registration = wait_isolated_distributed_worker()
        users = []
        for index, username in enumerate(usernames):
            token = isolated.login(username)
            session = requests.Session()
            session.headers.update({"Authorization": f"Bearer {token}"})
            role = ROLES[index % len(ROLES)]
            users.append({"index": index, "username": username, "role": role, "fixture": fixtures[role], "session": session})
        server = psutil.Process(int(health["pid"]))
        cold_started = time.perf_counter()
        cold_rows = [perform_request(users[0]["session"], action, users[0]["fixture"], users[0]["role"], users[0]["username"]) for action in ("auth", "tree", "list", "tasks", "file", "progress", "inventory", "settings")]
        cold_wall = time.perf_counter() - cold_started
        phases = [
            run_phase("warm_1_user", users, 1, 32, server),
            run_phase("warm_10_users", users, 10, 24, server),
            run_phase("warm_25_users", users, 25, 20, server),
        ]
        cache_eviction = run_cache_eviction_phase(users, fixtures["_eviction_paths"]["paths"], server)
        cache_cycles = [run_phase(f"cache_cycle_{index + 1}", users, 25, 8, server) for index in range(3)]
        progress_mutation = run_progress_mutation_phase(users, fixtures["space_v"], server)
        builder_holder: dict[str, dict] = {}

        def builder_target() -> None:
            builder_holder["result"] = run_builder_phase(users, server)

        builder_thread = threading.Thread(target=builder_target, daemon=True)
        builder_thread.start()
        time.sleep(0.25)
        mixed_user_phase = run_phase("warm_25_users_with_builder", users, 25, 20, server)
        builder_thread.join(timeout=BUILDER_COMPLETION_TIMEOUT_SECONDS + 60.0)
        if builder_thread.is_alive():
            raise RuntimeError(f"Builder audit did not finish within {BUILDER_COMPLETION_TIMEOUT_SECONDS + 60.0:.0f} seconds.")
        builder_phase = builder_holder.get("result") or {"errors": 1, "error": "missing builder result"}
        builder_population_phases = [
            run_paired_builder_cycle(users, server, 1, active_count=1, requests_per_user=32),
            run_paired_builder_cycle(users, server, 1, active_count=10, requests_per_user=24),
        ]
        paired_builder_cycles = [run_paired_builder_cycle(users, server, index, active_count=25, requests_per_user=20) for index in range(1, 4)]
        production_pid_after_load = assert_production_pid(production_pid_before, "after-load")
        result = {
            "ok": all(phase["errors"] == 0 for phase in phases)
            and mixed_user_phase["errors"] == 0
            and int(builder_phase.get("errors", 0) or 0) == 0
            and int(cache_eviction.get("errors", 0) or 0) == 0
            and all(int(cycle.get("errors", 0) or 0) == 0 for cycle in cache_cycles)
            and int(progress_mutation.get("write_errors", 0) or 0) == 0
            and int(progress_mutation.get("read_errors", 0) or 0) == 0
            and int(progress_mutation.get("cross_user_leaks", 0) or 0) == 0
            and all(int(cycle.get("warmup", {}).get("errors", 0) or 0) == 0 and int(cycle.get("mixed", {}).get("errors", 0) or 0) == 0 and int(cycle.get("baseline", {}).get("errors", 0) or 0) == 0 and int(cycle.get("builder", {}).get("errors", 0) or 0) == 0 for cycle in paired_builder_cycles)
            and all(int(cycle.get("warmup", {}).get("errors", 0) or 0) == 0 and int(cycle.get("mixed", {}).get("errors", 0) or 0) == 0 and int(cycle.get("baseline", {}).get("errors", 0) or 0) == 0 and int(cycle.get("builder", {}).get("errors", 0) or 0) == 0 for cycle in builder_population_phases)
            and bool(builder_phase.get("completion", {}).get("ok"))
            and all(bool(cycle.get("builder", {}).get("completion", {}).get("ok")) for cycle in paired_builder_cycles)
            and all(bool(cycle.get("builder", {}).get("completion", {}).get("ok")) for cycle in builder_population_phases)
            and bool(distributed_worker_registration.get("ready"))
            and not any(row["error"] for row in cold_rows),
            "database_sync": {"enabled": True, "method": "fresh pg_dump + pg_restore", "dump_bytes": dump.stat().st_size},
            "resources": {
                "http": isolated.BASE,
                "postgres": isolated.PG_PORT,
                "server_data_root": str(isolated.SERVER_DATA_ROOT),
                "production_mutated": False,
                "production_pid_before": production_pid_before,
                "production_pid_during": production_pid_during,
                "production_pid_after_load": production_pid_after_load,
            },
            "fixtures": fixtures,
            "health": {"pid": health.get("pid"), "ready": health.get("ready"), "warm_ready": health.get("warm_ready")},
            "distributed_worker_registration": distributed_worker_registration,
            "cold_single_user": {"wall_seconds": round(cold_wall, 3), "latency": summarize_rows(cold_rows), "errors": sum(1 for row in cold_rows if row["error"])},
            "phases": phases,
            "mixed_user_phase": mixed_user_phase,
            "builder_phase": builder_phase,
            "builder_population_phases": builder_population_phases,
            "paired_builder_cycles": paired_builder_cycles,
            "cache_eviction": cache_eviction,
            "cache_cycles": cache_cycles,
            "progress_mutation": progress_mutation,
        }
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["ok"] else 1
    finally:
        stop_isolated_distributed_worker(distributed_worker_process, distributed_worker_log)
        isolated.stop_server(server_process)
        stop_isolated_voice_worker()
        isolated.stop_postgres()
        remove_run_root()


if __name__ == "__main__":
    raise SystemExit(main())
