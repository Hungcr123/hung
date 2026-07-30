#!/usr/bin/env python3
"""Measure PostgreSQL-only Server 2 login CPU baseline without changing runtime code."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import statistics
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

import psutil
import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app  # noqa: E402

BASE = "http://127.0.0.1:18877"
OUT_DIR = Path(r"C:\Users\Admin\.codex\plans\server2_login_baseline_20260727")
TEST_PREFIX = "codexloginload"
LOAD_USERS = tuple(f"{TEST_PREFIX}{index:03d}" for index in range(1, 101))
AUTH_DOMAINS = (
    "AI_HISTORY_DOCUMENTS",
    "ANNOUNCEMENTS",
    "APPEND_EVENTS",
    "AUTH",
    "CHAT",
    "INVENTORY",
    "LEADERBOARD_DOCUMENTS",
    "LEARNING_SUMMARY_DOCUMENTS",
    "LESSON_FOLDER_LINKS",
    "LESSON_IDENTITY",
    "LESSON_LAST_FILE",
    "LESSON_PROGRESS",
    "LESSON_TASK",
    "LESSON_TASK_NOTICES",
    "LESSON_TIME",
    "PDF_DRAWINGS",
    "QMDICT_DOCUMENTS",
    "QM_CITY_DOCUMENTS",
    "SPACE_PDF_AI_DOCUMENTS",
    "SPACE_W_SPEAK_SKIP",
    "USER_AUTH_DOCS",
    "USER_PREFERENCES",
    "VAULT_METADATA",
    "VIEWER_TOOL_DOCUMENTS",
    "VOCABULARY",
    "VOCAB_IMAGE_CACHE",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(len(ordered) * pct / 100.0))], 3)


def summary(values: list[float]) -> dict:
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "mean": round(statistics.fmean(values), 3),
        "p50": percentile(values, 50),
        "p95": percentile(values, 95),
        "p99": percentile(values, 99),
        "max": round(max(values), 3),
    }


def password_hash(value: str) -> str:
    salt = secrets.token_urlsafe(18)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode("utf-8"), salt.encode("utf-8"), 2)
    return "pbkdf2_sha256$2$%s$%s" % (salt, base64.urlsafe_b64encode(digest).decode("ascii").rstrip("="))


def process_cpu(process: psutil.Process) -> float:
    row = process.cpu_times()
    return float(row.user + row.system)


def process_tree(root: psutil.Process) -> list[psutil.Process]:
    rows = [root]
    try:
        rows.extend(root.children(recursive=True))
    except Exception:
        pass
    return rows


def snapshot_processes(pids: list[int]) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for pid in pids:
        try:
            proc = psutil.Process(pid)
            with proc.oneshot():
                mem = proc.memory_info()
                out[pid] = {
                    "pid": pid,
                    "name": proc.name(),
                    "cmdline": " ".join(proc.cmdline())[:480],
                    "cpu_seconds": round(process_cpu(proc), 6),
                    "rss_bytes": int(mem.rss),
                    "threads": proc.num_threads(),
                    "handles": proc.num_handles() if hasattr(proc, "num_handles") else None,
                }
        except Exception as exc:
            out[pid] = {"pid": pid, "error": str(exc), "cpu_seconds": 0.0}
    return out


def cpu_sum(rows: dict[int, dict]) -> float:
    return sum(float(row.get("cpu_seconds") or 0.0) for row in rows.values())


def listener_pid(port: int) -> int:
    for conn in psutil.net_connections(kind="tcp"):
        if conn.laddr and conn.laddr.port == port and conn.status == psutil.CONN_LISTEN and conn.pid:
            return int(conn.pid)
    return 0


def all_listener_pids(port: int) -> list[int]:
    pids = set()
    for conn in psutil.net_connections(kind="tcp"):
        if conn.laddr and conn.laddr.port == port and conn.status == psutil.CONN_LISTEN and conn.pid:
            pids.add(int(conn.pid))
    return sorted(pids)


def health(base: str) -> dict:
    response = requests.get(base.rstrip("/") + "/health?view=dashboard-v1", timeout=15)
    response.raise_for_status()
    return response.json()


def wait_health(base: str, timeout: float = 180.0) -> dict:
    deadline = time.monotonic() + timeout
    last: dict = {}
    while time.monotonic() < deadline:
        try:
            last = health(base)
            if last.get("ok") and last.get("warm_ready"):
                return last
        except Exception as exc:
            last = {"error": str(exc)}
        time.sleep(0.5)
    raise RuntimeError(f"Server did not become warm: {last}")


def postgres_pids() -> list[int]:
    rows = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = (proc.info.get("name") or "").lower()
            cmd = " ".join(proc.info.get("cmdline") or []).lower()
            if "postgres" in name or "postgres" in cmd:
                rows.append(int(proc.pid))
        except Exception:
            pass
    return sorted(set(rows))


def worker_pids(health_row: dict) -> list[int]:
    pids = []
    for key in ("worker_pid", "process_worker_pid"):
        try:
            if health_row.get(key):
                pids.append(int(health_row[key]))
        except Exception:
            pass
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmd = " ".join(proc.info.get("cmdline") or "").lower()
            if "future_process_worker_2.py" in cmd:
                pids.append(int(proc.pid))
        except Exception:
            pass
    return sorted(set(pids))


def sample_window(name: str, duration: float, server_pid: int, dashboard_pids: list[int] | None = None) -> dict:
    dashboard_pids = dashboard_pids or []
    h0 = health(BASE)
    server_pids = sorted(set([server_pid] + [int(pid) for pid in all_listener_pids(18877)]))
    pg_pids = postgres_pids()
    wk_pids = worker_pids(h0)
    tracked = sorted(set(server_pids + pg_pids + wk_pids + dashboard_pids))
    before = snapshot_processes(tracked)
    server_before = cpu_sum({pid: before[pid] for pid in server_pids if pid in before})
    pg_before = cpu_sum({pid: before[pid] for pid in pg_pids if pid in before})
    wk_before = cpu_sum({pid: before[pid] for pid in wk_pids if pid in before})
    dash_before = cpu_sum({pid: before[pid] for pid in dashboard_pids if pid in before})
    samples = []
    peak_total = 0.0
    wall0 = time.perf_counter()
    while time.perf_counter() - wall0 < duration:
        whole = psutil.cpu_percent(interval=0.2)
        peak_total = max(peak_total, whole)
        try:
            proc = psutil.Process(server_pid)
            cpu = proc.cpu_percent(interval=None)
            mem = proc.memory_info()
            samples.append({"t": round(time.perf_counter() - wall0, 3), "server_cpu_percent_one_core": cpu, "server_rss_bytes": mem.rss, "whole_cpu_percent": whole})
        except Exception as exc:
            samples.append({"t": round(time.perf_counter() - wall0, 3), "error": str(exc), "whole_cpu_percent": whole})
    wall = time.perf_counter() - wall0
    after = snapshot_processes(tracked)
    h1 = health(BASE)
    server_after = cpu_sum({pid: after[pid] for pid in server_pids if pid in after})
    pg_after = cpu_sum({pid: after[pid] for pid in pg_pids if pid in after})
    wk_after = cpu_sum({pid: after[pid] for pid in wk_pids if pid in after})
    dash_after = cpu_sum({pid: after[pid] for pid in dashboard_pids if pid in after})
    server_cpu_ms = max(0.0, (server_after - server_before) * 1000)
    return {
        "name": name,
        "duration_seconds": round(wall, 3),
        "server_pids": server_pids,
        "postgres_pids": pg_pids,
        "worker_pids": wk_pids,
        "dashboard_pids": dashboard_pids,
        "server_cpu_ms": round(server_cpu_ms, 3),
        "server_cpu_percent_whole_machine_avg": round(server_cpu_ms / max(1.0, wall * psutil.cpu_count(logical=True) * 10), 3),
        "postgres_cpu_ms": round(max(0.0, (pg_after - pg_before) * 1000), 3),
        "worker_cpu_ms": round(max(0.0, (wk_after - wk_before) * 1000), 3),
        "dashboard_cpu_ms": round(max(0.0, (dash_after - dash_before) * 1000), 3),
        "whole_cpu_percent_peak": round(peak_total, 3),
        "server_sample_peak_one_core": round(max((float(s.get("server_cpu_percent_one_core") or 0.0) for s in samples), default=0.0), 3),
        "before": before,
        "after": after,
        "postgres_delta": postgres_delta(h0, h1),
    }


def postgres_delta(before: dict, after: dict) -> dict:
    left = before.get("postgres") if isinstance(before, dict) else {}
    right = after.get("postgres") if isinstance(after, dict) else {}
    if not isinstance(left, dict) or not isinstance(right, dict):
        return {"available": False}
    out = {"available": True}
    for key in sorted(set(left) | set(right)):
        try:
            out[key] = round(float(right.get(key, 0) or 0) - float(left.get(key, 0) or 0), 6)
        except Exception:
            out[key] = right.get(key)
    return out


class Recorder:
    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.lock = threading.Lock()

    def add(self, row: dict) -> None:
        with self.lock:
            self.rows.append(row)


def call(session: requests.Session, recorder: Recorder, username: str, group: str, method: str, path: str, token: str = "", body: dict | None = None) -> requests.Response:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    started = time.perf_counter()
    error = ""
    response = None
    try:
        response = session.request(method, BASE + path, headers=headers, json=body, timeout=60)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    ms = (time.perf_counter() - started) * 1000
    status = int(response.status_code) if response is not None else 0
    row = {
        "username": username,
        "group": group,
        "method": method,
        "path_group": path.split("?", 1)[0],
        "status": status,
        "duration_ms": round(ms, 3),
        "response_bytes": len(response.content) if response is not None else 0,
        "wire_response_bytes": int(response.headers.get("Content-Length") or len(response.content)) if response is not None else 0,
        "cache_hit": response.headers.get("X-Future-Cache-Hit", "") if response is not None else "",
        "error": error,
    }
    recorder.add(row)
    if response is None:
        raise RuntimeError(error)
    if not 200 <= response.status_code < 300 and response.status_code != 304:
        raise RuntimeError(f"{group} HTTP {response.status_code}: {response.text[:180]}")
    return response


def login_sequence(username: str, password: str, recorder: Recorder) -> dict:
    session = requests.Session()
    start = time.perf_counter()
    call(session, recorder, username, "announcements", "GET", "/announcements?ts=0")
    call(session, recorder, username, "settings", "GET", "/settings?ts=0")
    call(session, recorder, username, "username_check", "GET", f"/auth/username?username={quote(username)}")
    response = call(session, recorder, username, "login", "POST", "/auth/login", body={"username": username, "password": password})
    token = response.json().get("token") or ""
    if not token:
        raise RuntimeError("login token missing")
    call(session, recorder, username, "auth_me", "GET", "/auth/me", token=token)
    call(session, recorder, username, "login_preload", "GET", f"/server-data/login-preload?username={quote(username)}&response=compact-v2", token=token)
    call(session, recorder, username, "common_tree", "GET", "/server-data/common-tree", token=token)
    call(session, recorder, username, "user_overlay", "GET", "/server-data/user-overlay", token=token)
    call(session, recorder, username, "folder_list", "GET", f"/server-data/list?path=common&task_owner={quote(username)}&defer_task_board=1&include_space_task=1", token=token)
    call(session, recorder, username, "lesson_tasks", "GET", f"/lesson-tasks?user={quote(username)}", token=token)
    call(session, recorder, username, "lesson_tasks_status", "GET", f"/lesson-tasks/status?user={quote(username)}", token=token)
    call(session, recorder, username, "vocab_registry", "GET", "/vocab/registry", token=token)
    call(session, recorder, username, "leaderboard", "GET", "/vocab/leaderboard?scope=day&type=space_v&limit=20", token=token)
    return {"username": username, "wall_ms": round((time.perf_counter() - start) * 1000, 3), "request_count": 13}


def endpoint_summary(rows: list[dict]) -> dict:
    out: dict[str, dict] = {}
    for row in rows:
        out.setdefault(row["group"], {"durations": [], "statuses": {}, "bytes": 0, "errors": 0, "cache_hit_values": set()})
        bucket = out[row["group"]]
        bucket["durations"].append(float(row["duration_ms"]))
        bucket["statuses"][str(row["status"])] = bucket["statuses"].get(str(row["status"]), 0) + 1
        bucket["bytes"] += int(row.get("wire_response_bytes") or 0)
        bucket["errors"] += 1 if row.get("error") or int(row.get("status") or 0) >= 400 else 0
        if row.get("cache_hit"):
            bucket["cache_hit_values"].add(str(row.get("cache_hit")))
    return {
        key: {
            **summary(value["durations"]),
            "statuses": value["statuses"],
            "wire_response_bytes": value["bytes"],
            "errors": value["errors"],
            "cache_hit_values": sorted(value["cache_hit_values"]),
        }
        for key, value in out.items()
    }


def measure_login_phase(name: str, accounts: list[tuple[str, str]], server_pid: int, rounds: int = 1, concurrent: bool = False, dashboard_pids: list[int] | None = None) -> dict:
    recorder = Recorder()
    h0 = health(BASE)
    tracked = sorted(set([server_pid] + all_listener_pids(18877) + postgres_pids() + worker_pids(h0) + (dashboard_pids or [])))
    before = snapshot_processes(tracked)
    whole_peak = 0.0
    stop = threading.Event()

    def sampler() -> None:
        nonlocal whole_peak
        while not stop.is_set():
            whole_peak = max(whole_peak, psutil.cpu_percent(interval=0.2))

    thread = threading.Thread(target=sampler, daemon=True)
    thread.start()
    flows: list[dict] = []
    errors: list[str] = []
    wall0 = time.perf_counter()
    try:
        for _ in range(rounds):
            if concurrent:
                with ThreadPoolExecutor(max_workers=len(accounts)) as pool:
                    futures = [pool.submit(login_sequence, username, password, recorder) for username, password in accounts]
                    for future in as_completed(futures):
                        try:
                            flows.append(future.result())
                        except Exception as exc:
                            errors.append(f"{type(exc).__name__}: {exc}")
            else:
                for username, password in accounts:
                    try:
                        flows.append(login_sequence(username, password, recorder))
                    except Exception as exc:
                        errors.append(f"{type(exc).__name__}: {exc}")
    finally:
        stop.set()
        thread.join(timeout=2)
    wall = time.perf_counter() - wall0
    after = snapshot_processes(tracked)
    h1 = health(BASE)
    server_pids = sorted(set([server_pid] + all_listener_pids(18877)))
    pg_pids = postgres_pids()
    wk_pids = worker_pids(h0)
    dash_pids = dashboard_pids or []
    server_cpu = max(0.0, (cpu_sum({pid: after[pid] for pid in server_pids if pid in after}) - cpu_sum({pid: before[pid] for pid in server_pids if pid in before})) * 1000)
    pg_cpu = max(0.0, (cpu_sum({pid: after[pid] for pid in pg_pids if pid in after}) - cpu_sum({pid: before[pid] for pid in pg_pids if pid in before})) * 1000)
    wk_cpu = max(0.0, (cpu_sum({pid: after[pid] for pid in wk_pids if pid in after}) - cpu_sum({pid: before[pid] for pid in wk_pids if pid in before})) * 1000)
    dash_cpu = max(0.0, (cpu_sum({pid: after[pid] for pid in dash_pids if pid in after}) - cpu_sum({pid: before[pid] for pid in dash_pids if pid in before})) * 1000)
    pg_delta = postgres_delta(h0, h1)
    return {
        "name": name,
        "accounts": [username for username, _ in accounts],
        "rounds": rounds,
        "concurrent": concurrent,
        "flows": len(flows),
        "requests": len(recorder.rows),
        "errors": len(errors) + sum(1 for row in recorder.rows if row.get("error") or int(row.get("status") or 0) >= 400),
        "error_samples": errors[:5],
        "wall_ms": round(wall * 1000, 3),
        "flow_wall_ms": summary([float(flow["wall_ms"]) for flow in flows]),
        "server_cpu_ms": round(server_cpu, 3),
        "server_cpu_ms_per_login": round(server_cpu / max(1, len(flows)), 3),
        "postgres_cpu_ms": round(pg_cpu, 3),
        "postgres_cpu_ms_per_login": round(pg_cpu / max(1, len(flows)), 3),
        "worker_cpu_ms": round(wk_cpu, 3),
        "dashboard_cpu_ms": round(dash_cpu, 3),
        "whole_cpu_percent_peak": round(whole_peak, 3),
        "postgres_delta": pg_delta,
        "sql_execute_per_login": round(float(pg_delta.get("sql_execute") or 0) / max(1, len(flows)), 3),
        "transactions_per_login": round(float(pg_delta.get("transactions") or 0) / max(1, len(flows)), 3),
        "endpoint_metrics": endpoint_summary(recorder.rows),
        "duplicate_request_counts": {key: value["count"] for key, value in endpoint_summary(recorder.rows).items() if value.get("count", 0) > len(flows)},
    }


def cleanup_load_users() -> dict:
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


def provision_load_users(password: str) -> None:
    now = utc_now()
    hashed = password_hash(password)
    for username in LOAD_USERS:
        app.postgres_upsert_user_row({
            "username": username,
            "is_admin": False,
            "is_test": False,
            "profile_json": {"full_name": f"Codex Login Load {username[-3:]}", "load_test": True},
            "updated_at_utc": now,
        })
        app.postgres_upsert_user_auth_credential(username, hashed, "benchmark:login-cpu-baseline")


def dashboard_processes(profile: Path) -> list[int]:
    marker = str(profile).lower()
    pids = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmd = " ".join(proc.info.get("cmdline") or []).lower()
            name = (proc.info.get("name") or "").lower()
            if marker in cmd and ("chrome" in name or "msedge" in name or "browser" in name):
                pids.append(int(proc.pid))
        except Exception:
            pass
    return sorted(set(pids))


def launch_dashboard(profile: Path, mode: str) -> subprocess.Popen:
    chrome = os.environ.get("FUTURE_BROWSER_EXE") or r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    args = [
        chrome,
        f"--user-data-dir={profile}",
        "--no-first-run",
        "--disable-background-networking",
        "--disable-sync",
        "--disable-features=Translate,MediaRouter",
        "--new-window",
        BASE + "/status",
    ]
    if mode == "hidden":
        args.insert(-1, "--start-minimized")
    return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def close_dashboard(proc: subprocess.Popen | None, profile: Path) -> dict:
    pids = dashboard_processes(profile)
    for pid in pids:
        try:
            psutil.Process(pid).kill()
        except Exception:
            pass
    if proc is not None:
        try:
            proc.kill()
        except Exception:
            pass
    time.sleep(1)
    remaining = dashboard_processes(profile)
    return {"killed_pids": pids, "remaining_pids": remaining}


def redacted_dsn() -> dict:
    dsn = os.environ.get("FUTURE_PG_DSN", "")
    parsed = urlparse(dsn)
    return {"scheme": parsed.scheme, "host": parsed.hostname, "port": parsed.port, "database": parsed.path.lstrip("/"), "username": parsed.username, "password_set": bool(parsed.password)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUT_DIR / "login_cpu_baseline_full_20260727.json"))
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--settle-seconds", type=float, default=0.0)
    parser.add_argument("--skip-dashboard", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    actual_passwords = json.loads(os.environ.get("FUTURE_LOGIN_BENCH_PASSWORDS_JSON") or "{}")
    actual_accounts = [(name, actual_passwords[name]) for name in ("hung", "quynh", "hungcr") if actual_passwords.get(name)]
    if not actual_accounts:
        raise RuntimeError("FUTURE_LOGIN_BENCH_PASSWORDS_JSON must provide benchmark accounts")
    load_password = os.environ.get("FUTURE_LOGIN_LOAD_PASSWORD") or ("codex-load-" + secrets.token_urlsafe(12))

    h = wait_health(BASE)
    if args.settle_seconds > 0:
        time.sleep(args.settle_seconds)
        h = health(BASE)
    server_pid = int(h.get("pid") or listener_pid(18877))
    result = {
        "started_utc": utc_now(),
        "base": BASE,
        "server": {
            "pid": server_pid,
            "listener_pids": all_listener_pids(18877),
            "command_line": snapshot_processes([server_pid]).get(server_pid, {}).get("cmdline", ""),
            "postgres_only": bool((h.get("sqlite_writer") or {}).get("postgres_only") is True and (h.get("sqlite_writer") or {}).get("enabled") is False),
            "sqlite_writer": h.get("sqlite_writer"),
            "dashboard_status": h.get("dashboard_status"),
            "worker_pid": h.get("worker_pid"),
            "logical_cpu": psutil.cpu_count(logical=True),
            "pg_dsn_redacted": redacted_dsn(),
        },
        "cleanup_before": cleanup_load_users(),
        "phases": {},
        "dashboard": {},
    }
    if not result["server"]["postgres_only"]:
        raise RuntimeError("health does not prove PostgreSQL-only runtime")

    dash_cleanup = {}
    try:
        result["phases"]["idle_baseline"] = sample_window("idle_baseline", args.idle_seconds, server_pid)
        for username, password in actual_accounts:
            result["phases"][f"single_{username}"] = measure_login_phase(f"single_{username}", [(username, password)], server_pid, rounds=1, concurrent=False)
            result["phases"][f"post_login_10s_{username}"] = sample_window(f"post_login_10s_{username}", 10.0, server_pid)
            result["phases"][f"relogin_cache_{username}"] = measure_login_phase(f"relogin_cache_{username}", [(username, password)], server_pid, rounds=3, concurrent=False)

        if not args.skip_dashboard:
            modes = ["closed", "visible", "hidden"]
            for mode in modes:
                proc = None
                profile = OUT_DIR / f"dashboard_profile_{mode}"
                if mode != "closed":
                    proc = launch_dashboard(profile, mode)
                    time.sleep(8)
                pids = dashboard_processes(profile) if mode != "closed" else []
                result["dashboard"][mode] = measure_login_phase(f"dashboard_{mode}_login", actual_accounts[:2], server_pid, rounds=2, concurrent=True, dashboard_pids=pids)
                if mode != "closed":
                    dash_cleanup[mode] = close_dashboard(proc, profile)
                    try:
                        import shutil
                        shutil.rmtree(profile, ignore_errors=True)
                    except Exception:
                        pass

        provision_load_users(load_password)
        result["load_cleanup_after_provision_probe"] = {"provisioned": len(LOAD_USERS)}
        load_levels = [1, 5, 10, 25, 50, 100]
        result["load"] = {}
        for level in load_levels:
            accounts = [(username, load_password) for username in LOAD_USERS[:level]]
            phase = measure_login_phase(f"load_{level}", accounts, server_pid, rounds=3, concurrent=True)
            result["load"][str(level)] = phase
            if phase["errors"] > max(1, int(phase["flows"] * 0.01)):
                result["load_stop_reason"] = f"errors exceeded threshold at {level}"
                break
            if phase["flow_wall_ms"].get("p95") and phase["flow_wall_ms"]["p95"] > 10000:
                result["load_stop_reason"] = f"P95 exceeded 10s at {level}"
                break
            if phase["whole_cpu_percent_peak"] > 85:
                result["load_stop_reason"] = f"whole CPU exceeded 85% at {level}"
                break
    finally:
        result["cleanup_after"] = cleanup_load_users()
        result["dashboard_cleanup"] = dash_cleanup
        result["health_after"] = health(BASE)
        result["production_8877_health"] = None
        try:
            live = requests.get("http://127.0.0.1:8877/health?view=dashboard-v1", timeout=5).json()
            result["production_8877_health"] = {"ok": live.get("ok"), "pid": live.get("pid"), "postgres_only": (live.get("sqlite_writer") or {}).get("postgres_only")}
        except Exception as exc:
            result["production_8877_health"] = {"error": str(exc)}
        result["finished_utc"] = utc_now()
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": args.output, "server_pid": server_pid, "load_levels": list(result.get("load", {}).keys()), "cleanup_after": result.get("cleanup_after")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    for domain in AUTH_DOMAINS:
        os.environ.setdefault(f"FUTURE_DB_{domain}_BACKEND", "postgres")
    os.environ.setdefault("FUTURE_POSTGRES_ONLY", "1")
    raise SystemExit(main())
