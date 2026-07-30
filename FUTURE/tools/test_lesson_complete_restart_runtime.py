"""Hard-kill after the atomic progress+intent commit and verify restart convergence."""

from __future__ import annotations

import concurrent.futures
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil
import requests


ROOT = Path(__file__).resolve().parents[2]
DATABASE = Path(r"C:\server data\server2.db")
BASE = "http://127.0.0.1:8877"
USER = "codexload001"


def listener_pid() -> int:
    for connection in psutil.net_connections(kind="tcp"):
        if connection.status == psutil.CONN_LISTEN and connection.laddr and connection.laddr.port == 8877:
            return int(connection.pid or 0)
    return 0


def stop_server() -> int:
    pid = listener_pid()
    if pid:
        process = psutil.Process(pid)
        process.kill()
        process.wait(timeout=15)
    return pid


def start_server(delay_ms: int = 0) -> int:
    env = os.environ.copy()
    if delay_ms:
        env["FUTURE_TEST_COMPLETION_AFTER_PROGRESS_DELAY_MS"] = str(delay_ms)
    else:
        env.pop("FUTURE_TEST_COMPLETION_AFTER_PROGRESS_DELAY_MS", None)
    subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--replace-old"],
        cwd=str(ROOT),
        env=env,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            health = requests.get(f"{BASE}/health?view=dashboard-v1", timeout=3).json()
            if health.get("warm_ready"):
                return listener_pid()
        except Exception:
            pass
        time.sleep(0.25)
    raise RuntimeError("Server 2 did not become warm")


def login(password: str) -> str:
    response = requests.post(f"{BASE}/auth/login", json={"username": USER, "password": password}, timeout=30)
    response.raise_for_status()
    return str(response.json().get("token", ""))


def lesson() -> tuple[str, str]:
    connection = sqlite3.connect(DATABASE)
    try:
        return connection.execute(
            "SELECT normalized_path,file_id FROM lesson_file_aliases WHERE active=1 "
            "AND lower(normalized_path) LIKE 'common/%.space_w' ORDER BY normalized_path LIMIT 1"
        ).fetchone()
    finally:
        connection.close()


def state(event_key: str) -> dict:
    connection = sqlite3.connect(DATABASE)
    try:
        progress_rows = connection.execute(
            "SELECT record_json FROM lesson_progress WHERE username=?", (USER,)
        ).fetchall()
        progress = 0
        for progress_row in progress_rows:
            try:
                record = json.loads(progress_row[0])
            except Exception:
                continue
            progress_state = record.get("state") if isinstance(record.get("state"), dict) else {}
            if bool(record.get("complete") or record.get("lessonComplete") or progress_state.get("complete") or progress_state.get("lessonComplete") or int(record.get("completedRuns", record.get("completed_runs", 0)) or 0) > 0):
                progress += 1
        intents = connection.execute(
            "SELECT COUNT(*) FROM append_events WHERE stream='learning_intent' AND event_key=?", (event_key,)
        ).fetchone()[0]
        final = connection.execute(
            "SELECT event_json FROM append_events WHERE stream='learning' AND event_key=?", (event_key,)
        ).fetchone()
        summary = connection.execute(
            "SELECT content FROM documents WHERE lower(path) LIKE ? ORDER BY updated_at_utc DESC LIMIT 1",
            (f"%\\{USER}\\_future_learning_summary.json",),
        ).fetchone()
        final_payload = json.loads(final[0]) if final else {}
        summary_payload = json.loads(bytes(summary[0]).decode("utf-8")) if summary else {}
        return {
            "progress": int(progress),
            "intents": int(intents),
            "final_status": str(final_payload.get("status", "")),
            "recovered": bool(final_payload.get("recovered_after_restart")),
            "summary_completed_runs": int(summary_payload.get("completed_runs", 0) or 0),
            "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
            "journal_mode": connection.execute("PRAGMA journal_mode").fetchone()[0],
            "synchronous": int(connection.execute("PRAGMA synchronous").fetchone()[0]),
        }
    finally:
        connection.close()


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this regression only")
    stop_server()
    delayed_pid = start_server(3000)
    path, lesson_id = lesson()
    token = login(password)
    stamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    body = {"path": path, "lesson_id": lesson_id, "title": "restart regression", "nodes": 1, "completed_at": stamp, "source": "Space_W"}

    def post() -> str:
        try:
            response = requests.post(
                f"{BASE}/lesson/complete",
                headers={"Authorization": f"Bearer {token}"},
                json=body,
                timeout=15,
            )
            return f"status:{response.status_code}"
        except Exception as exc:
            return type(exc).__name__

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(post)
        deadline = time.monotonic() + 15
        event_key = ""
        while time.monotonic() < deadline:
            connection = sqlite3.connect(DATABASE)
            row = connection.execute(
                "SELECT event_key FROM append_events WHERE stream='learning_intent' AND username=? ORDER BY id DESC LIMIT 1",
                (USER,),
            ).fetchone()
            connection.close()
            if row:
                event_key = str(row[0])
                break
            time.sleep(0.01)
        if not event_key:
            raise RuntimeError("Did not observe durable completion intent")
        psutil.Process(delayed_pid).kill()
        psutil.Process(delayed_pid).wait(timeout=15)
        request_result = future.result(timeout=20)

    normal_pid = start_server(0)
    after_restart = state(event_key)
    retry_token = login(password)
    retry = requests.post(
        f"{BASE}/lesson/complete",
        headers={"Authorization": f"Bearer {retry_token}"},
        json=body,
        timeout=60,
    )
    retry.raise_for_status()
    after_retry = state(event_key)
    result = {
        "killed_pid": delayed_pid,
        "restart_pid": normal_pid,
        "request_result": request_result,
        "after_restart": after_restart,
        "retry_deduplicated": bool(retry.json().get("deduplicated")),
        "after_retry": after_retry,
    }
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    assert after_restart == {
        "progress": 1,
        "intents": 0,
        "final_status": "final",
        "recovered": True,
        "summary_completed_runs": 1,
        "quick_check": "ok",
        "journal_mode": "wal",
        "synchronous": 2,
    }
    assert result["retry_deduplicated"]
    assert after_retry == after_restart
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
