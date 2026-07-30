#!/usr/bin/env python3
"""Measure Server 2 startup warmup modes on isolated port 18877.

Added 2026-07-28 for the startup warmup checkpoint. This intentionally avoids
login credentials and production 8877 mutation; login correctness is covered by
the credential-gated HTTP gate.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import psutil
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(r"C:\Users\Admin\.codex\plans\server2_postgres_full_audit")
BASE = "http://127.0.0.1:18877"


def port_pid(port: int) -> int:
    for connection in psutil.net_connections(kind="tcp"):
        if connection.laddr and connection.laddr.port == port and connection.status == psutil.CONN_LISTEN and connection.pid:
            return int(connection.pid)
    return 0


def stop_pid(pid: int) -> None:
    if not pid:
        return
    try:
        process = psutil.Process(pid)
        process.kill()
        process.wait(timeout=20)
    except psutil.NoSuchProcess:
        pass
    except Exception:
        pass


def process_cpu_seconds(process: psutil.Process) -> float:
    row = process.cpu_times()
    return float(row.user + row.system)


def process_sample(pid: int) -> dict[str, Any]:
    if not pid:
        return {}
    try:
        process = psutil.Process(pid)
        mem = process.memory_info()
        return {
            "pid": pid,
            "cpu_seconds": process_cpu_seconds(process),
            "rss_bytes": int(mem.rss),
            "threads": int(process.num_threads()),
        }
    except Exception as exc:
        return {"pid": pid, "error": str(exc)}


def parse_warmup_log(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {"raw_lines": []}
    for line in text.splitlines():
        if any(marker in line for marker in ("Warmup mode:", "Common Tree warm:", "Server data user overlay warm:", "Server data login preload warm:", "Server data login folder-list warm:")):
            out["raw_lines"].append(line)
    match = re.search(
        r"Warmup mode: (?P<mode>\w+); selected users: (?P<selected>\d+); selected test users: (?P<selected_test>\d+); "
        r"real users total: (?P<real_total>\d+); test users skipped: (?P<test_skipped>\d+); include_test_users=(?P<include>\d+)",
        text,
    )
    if match:
        out["selection"] = {
            "mode": match.group("mode"),
            "selected_users": int(match.group("selected")),
            "selected_test_users": int(match.group("selected_test")),
            "real_users_total": int(match.group("real_total")),
            "test_users_skipped": int(match.group("test_skipped")),
            "include_test_users": bool(int(match.group("include"))),
        }
    match = re.search(
        r"Common Tree warm: revision (?P<revision>[0-9a-f]+), build (?P<build>\d+), (?P<cpu>[0-9.]+)ms CPU, (?P<gzip>\d+) gzip bytes. "
        r"Tree-preload per-user warm: (?P<tree_status>[^,]+), (?P<tree_users>\d+) users, (?P<tree_gzip>\d+) gzip bytes.",
        text,
    )
    if match:
        out["common_tree"] = {
            "revision": match.group("revision"),
            "build_count": int(match.group("build")),
            "cpu_ms": float(match.group("cpu")),
            "gzip_bytes": int(match.group("gzip")),
            "tree_preload_status": match.group("tree_status"),
            "tree_preload_users": int(match.group("tree_users")),
            "tree_preload_gzip_bytes": int(match.group("tree_gzip")),
        }
    match = re.search(r"Server data user overlay warm: (?P<users>\d+) users, (?P<cpu>[0-9.]+)ms CPU, (?P<gzip>\d+) gzip bytes.", text)
    if match:
        out["user_overlay"] = {"users": int(match.group("users")), "cpu_ms": float(match.group("cpu")), "gzip_bytes": int(match.group("gzip"))}
    match = re.search(r"Server data login preload warm: (?P<users>\d+) users, (?P<cpu>[0-9.]+)ms CPU.", text)
    if match:
        out["login_preload"] = {"users": int(match.group("users")), "cpu_ms": float(match.group("cpu"))}
    match = re.search(r"Server data login folder-list warm: (?P<users>\d+) users, (?P<cpu>[0-9.]+)ms CPU, (?P<errors>\d+) errors.", text)
    if match:
        out["folder_list"] = {"users": int(match.group("users")), "cpu_ms": float(match.group("cpu")), "errors": int(match.group("errors"))}
    return out


def wait_endpoint(path: str, timeout: float) -> tuple[float, int, dict[str, Any]]:
    deadline = time.perf_counter() + timeout
    started = time.perf_counter()
    last_payload: dict[str, Any] = {}
    last_status = 0
    while time.perf_counter() < deadline:
        try:
            response = requests.get(BASE + path, timeout=3)
            last_status = response.status_code
            try:
                last_payload = response.json()
            except Exception:
                last_payload = {"text_prefix": response.text[:120]}
            if response.status_code < 500:
                return (time.perf_counter() - started) * 1000.0, response.status_code, last_payload
        except Exception as exc:
            last_payload = {"error": str(exc)}
        time.sleep(0.25)
    return (time.perf_counter() - started) * 1000.0, last_status, last_payload


def wait_warm_ready(timeout: float) -> tuple[float, dict[str, Any]]:
    deadline = time.perf_counter() + timeout
    started = time.perf_counter()
    last_payload: dict[str, Any] = {}
    while time.perf_counter() < deadline:
        try:
            response = requests.get(BASE + "/health?view=startup-warmup-benchmark", timeout=3)
            last_payload = response.json()
            if response.status_code == 200 and last_payload.get("warm_ready"):
                return (time.perf_counter() - started) * 1000.0, last_payload
        except Exception as exc:
            last_payload = {"error": str(exc)}
        time.sleep(0.5)
    return (time.perf_counter() - started) * 1000.0, last_payload


def run_mode(mode: str, include_test: bool, warmup_users: str, warmup_prefixes: str) -> dict[str, Any]:
    existing = port_pid(18877)
    if existing:
        stop_pid(existing)
        time.sleep(1)
    before_8877 = port_pid(8877)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stdout_path = OUT_DIR / f"startup_warmup_mode_{mode}_18877.out.log"
    stderr_path = OUT_DIR / f"startup_warmup_mode_{mode}_18877.err.log"
    for path in (stdout_path, stderr_path):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    env = dict(os.environ)
    env["FUTURE_WARMUP_MODE"] = mode
    env["FUTURE_INCLUDE_TEST_USERS"] = "1" if include_test else "0"
    if warmup_users:
        env["FUTURE_WARMUP_USERS"] = warmup_users
    else:
        env.pop("FUTURE_WARMUP_USERS", None)
    if warmup_prefixes:
        env["FUTURE_WARMUP_USER_PREFIXES"] = warmup_prefixes
    else:
        env.pop("FUTURE_WARMUP_USER_PREFIXES", None)
    env["FUTURE_POSTGRES_ONLY"] = "1"
    env.pop("FUTURE_DB_BACKEND", None)
    env.pop("FUTURE_POSTGRES_BACKEND", None)
    started_wall = time.perf_counter()
    process = subprocess.Popen(
        [
            sys.executable,
            "FUTURE_SERVER_2.py",
            "--host",
            "127.0.0.1",
            "--port",
            "18877",
            "--no-browser",
            "--no-tunnel",
            "--no-preload",
        ],
        cwd=str(ROOT),
        env=env,
        stdout=stdout_path.open("wb"),
        stderr=stderr_path.open("wb"),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    peak_rss = 0
    health_ms, health_status, health_payload = wait_endpoint("/health?view=startup-warmup-benchmark", 90)
    login_ms, login_status, _login_payload = wait_endpoint("/login", 20)
    warm_ms, warm_payload = wait_warm_ready(120)
    sample = process_sample(process.pid)
    peak_rss = max(peak_rss, int(sample.get("rss_bytes", 0) or 0))
    total_wall_ms = (time.perf_counter() - started_wall) * 1000.0
    cpu_ms = round(float(sample.get("cpu_seconds", 0.0) or 0.0) * 1000.0, 3)
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.exists() else ""
    result = {
        "mode": mode,
        "include_test_users": include_test,
        "warmup_users": warmup_users,
        "warmup_prefixes": warmup_prefixes,
        "started_pid": process.pid,
        "health_ms": round(health_ms, 3),
        "health_status": health_status,
        "login_ready_ms": round(login_ms, 3),
        "login_status": login_status,
        "warm_ready_wait_ms": round(warm_ms, 3),
        "warm_ready": bool(warm_payload.get("warm_ready")),
        "total_wall_ms": round(total_wall_ms, 3),
        "cpu_ms_at_warm_ready": cpu_ms,
        "rss_bytes_at_warm_ready": int(sample.get("rss_bytes", 0) or 0),
        "threads_at_warm_ready": int(sample.get("threads", 0) or 0),
        "postgres_only": bool(health_payload.get("postgres_only") or ((health_payload.get("postgres_writer") or {}).get("postgres_only"))),
        "postgres_writer": health_payload.get("postgres_writer"),
        "warmup_log": parse_warmup_log(stdout_text),
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "port_8877_before": before_8877,
    }
    stop_pid(port_pid(18877) or process.pid)
    time.sleep(1)
    result["port_18877_after_stop"] = port_pid(18877)
    result["port_8877_after_stop"] = port_pid(8877)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUT_DIR / "startup_warmup_modes_benchmark_20260728.json"))
    args = parser.parse_args()
    modes = [
        ("production", False, "", ""),
        ("lazy", False, "", ""),
        ("benchmark", True, "codexload001,codexload002", ""),
    ]
    results = [run_mode(*item) for item in modes]
    output = Path(args.output)
    payload = {
        "ok": all(row.get("health_status") == 200 and row.get("warm_ready") and row.get("port_18877_after_stop") == 0 for row in results),
        "production_8877_touched": False,
        "results": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    print(json.dumps({"ok": payload["ok"], "output": str(output)}, ensure_ascii=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

