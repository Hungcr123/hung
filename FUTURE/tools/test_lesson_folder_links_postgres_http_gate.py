#!/usr/bin/env python3
"""HTTP runtime/shadow gate for lesson_folder_links with PostgreSQL cache routing."""

from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import hmac
import json
import os
import secrets
import shutil
import sqlite3
import statistics
import subprocess
import sys
import time
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app  # noqa: E402
import FUTURE.tools.migrate_lesson_folder_links_to_postgres as migrate_links  # noqa: E402

DATABASE = Path(r"C:\server data\server2.db")
SERVER_DATA_ROOT = Path(r"C:\server data")
BASE = "http://127.0.0.1:18877"
USERNAME = "codexpgfolderlink001"
LINK_PATH = f"{USERNAME}/Linked"

def password_hash(value: str) -> str:
    rounds = 2
    salt = secrets.token_urlsafe(18)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode("utf-8"), salt.encode("utf-8"), rounds)
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"pbkdf2_sha256${rounds}${salt}${encoded}"

def password_hash_matches(value: str, encoded: str) -> bool:
    parts = str(encoded or "").split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", value.encode("utf-8"), parts[2].encode("utf-8"), int(parts[1]))
    return hmac.compare_digest(base64.urlsafe_b64encode(digest).decode("ascii").rstrip("="), parts[3])

def server_pid_on_port(port: int) -> int:
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
        return

def wait_health(pid: int = 0, timeout: float = 90.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            response = requests.get(f"{BASE}/health", timeout=3)
            if response.status_code == 200:
                payload = response.json()
                if payload.get("ok") and (not pid or int(payload.get("pid", 0) or 0) == pid):
                    return payload
        except Exception:
            pass
        time.sleep(0.4)
    raise RuntimeError("Test Server 2 did not become healthy")

def start_test_server() -> subprocess.Popen:
    env = dict(os.environ)
    env["FUTURE_DB_LESSON_FOLDER_LINKS_BACKEND"] = "postgres"
    env["FUTURE_HYBRID_VAULT_ENABLED"] = "0"
    return subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--host", "127.0.0.1", "--port", "18877", "--no-browser", "--no-tunnel"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

def cleanup_sqlite() -> dict:
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute("DELETE FROM lesson_folder_links WHERE lower(link_path) LIKE 'codexpgfolderlink%'")
        links = int(con.total_changes)
        for table in ("auth_sessions", "server_load_test_credentials", "users"):
            con.execute(f"DELETE FROM {table} WHERE lower(username) LIKE 'codexpgfolderlink%'")
        con.commit()
    finally:
        con.close()
    shutil.rmtree(SERVER_DATA_ROOT / USERNAME, ignore_errors=True)
    return {"links_deleted": links}

def cleanup_postgres() -> dict:
    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.lesson_folder_links WHERE lower(link_path) LIKE 'codexpgfolderlink%'")
            return {"links_deleted": int(cursor.rowcount or 0)}
    return app.postgres_execute(_write)

def provision(password: str) -> dict:
    target = "common/Study/Empower A1"
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        row = con.execute(
            "SELECT target_path FROM lesson_folder_links WHERE status IN ('active','migrated') ORDER BY lower(link_path) LIMIT 1"
        ).fetchone()
        if row and app.clean_path_value(row[0]):
            target = app.clean_path_value(row[0])
    finally:
        con.close()
    if not SERVER_DATA_ROOT.joinpath(*target.split("/")).is_dir():
        raise RuntimeError(f"Folder-link target is missing: {target}")
    now = app.utc_timestamp()
    payload = {
        "kind": getattr(app, "SERVER_DATA_LINK_KIND", "future_server_data_link"),
        "version": 1,
        "target": target,
        "target_type": "folder",
        "created_by": USERNAME,
        "created_at": now,
    }
    (SERVER_DATA_ROOT / USERNAME / "Linked").mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "INSERT INTO users(username,is_admin,is_test,profile_json,updated_at_utc) VALUES(?,0,1,'{}',?) "
            "ON CONFLICT(username) DO UPDATE SET is_admin=0,is_test=1,updated_at_utc=excluded.updated_at_utc",
            (USERNAME, now),
        )
        existing = con.execute("SELECT password_hash FROM server_load_test_credentials WHERE username=?", (USERNAME,)).fetchone()
        encoded = existing[0] if existing and password_hash_matches(password, existing[0]) else password_hash(password)
        con.execute(
            "INSERT INTO server_load_test_credentials(username,password_hash,updated_at_utc) VALUES(?,?,?) "
            "ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash,updated_at_utc=excluded.updated_at_utc",
            (USERNAME, encoded, now),
        )
        con.execute(
            "INSERT INTO lesson_folder_links(link_path,target_path,created_by,created_at_utc,payload_json,revision,status,updated_at_utc) "
            "VALUES(?,?,?,?,?,1,'active',?)",
            (LINK_PATH, target, USERNAME, now, json.dumps(payload, ensure_ascii=False, separators=(",", ":")), now),
        )
        con.commit()
    finally:
        con.close()
    app.postgres_upsert_lesson_folder_link_row({
        "link_path": LINK_PATH,
        "target_path": target,
        "created_by": USERNAME,
        "created_at_utc": now,
        "payload": payload,
        "revision": 1,
        "status": "active",
        "updated_at_utc": now,
    })
    return {"target": target}

def login(password: str) -> str:
    deadline = time.monotonic() + 45
    last = ""
    while time.monotonic() < deadline:
        try:
            response = requests.post(f"{BASE}/auth/login", json={"username": USERNAME, "password": password}, timeout=10)
            last = f"{response.status_code} {response.text[:160]}"
            if response.status_code == 200:
                token = response.json().get("token")
                if token:
                    return token
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(0.5)
    raise RuntimeError(f"Login did not return token: {last}")

def list_link(token: str) -> tuple[int, dict, float]:
    started = time.perf_counter()
    response = requests.get(
        f"{BASE}/server-data/list",
        headers={"Authorization": f"Bearer {token}"},
        params={"path": LINK_PATH, "fresh": "1"},
        timeout=60,
    )
    elapsed = (time.perf_counter() - started) * 1000
    return response.status_code, response.json(), elapsed

def phase(name: str, token: str, count: int) -> dict:
    latencies = []
    statuses = {}
    errors = 0
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
        for status, payload, elapsed in executor.map(lambda _i: list_link(token), range(count)):
            statuses[str(status)] = statuses.get(str(status), 0) + 1
            latencies.append(elapsed)
            if status != 200 or not payload.get("ok") or not payload.get("entries"):
                errors += 1
    wall = (time.perf_counter() - started) * 1000
    ordered = sorted(latencies) or [0.0]
    return {
        "name": name,
        "requests": count,
        "statuses": statuses,
        "errors": errors,
        "wall_ms": round(wall, 3),
        "throughput_rps": round(count / (wall / 1000), 3) if wall else 0,
        "p50_ms": round(statistics.median(ordered), 3),
        "p95_ms": round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))], 3),
        "p99_ms": round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.99))], 3),
    }

def shadow() -> dict:
    sqlite = [row for row in migrate_links.sqlite_rows() if not row["link_path"].lower().startswith("codexpgfolderlink")]
    pg = [row for row in migrate_links.postgres_rows() if not row["link_path"].lower().startswith("codexpgfolderlink")]
    links = {row["link_path"] for row in sqlite}
    pg_subset = [row for row in pg if row["link_path"] in links]
    return {
        "sqlite_rows": len(sqlite),
        "postgres_matching": len(pg_subset),
        "stable_parity": migrate_links.stable_fingerprint(sqlite) == migrate_links.stable_fingerprint(pg_subset),
        "volatile_timestamp_ok": all(item.get("ok") for item in migrate_links.volatile_timestamp_checks(sqlite, pg_subset)),
    }

def main() -> int:
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("FUTURE_PG_DSN is required")
    if server_pid_on_port(18877):
        raise RuntimeError("Port 18877 already has a listener")
    app.postgres_initialize_schema()
    original_pid_file = app.SERVER_PID_FILE.read_text(encoding="utf-8") if app.SERVER_PID_FILE.is_file() else None
    process: subprocess.Popen | None = None
    password = secrets.token_urlsafe(32)
    try:
        cleanup_sqlite()
        cleanup_postgres()
        setup = provision(password)
        before = shadow()
        process = start_test_server()
        wait_health(pid=int(process.pid))
        token = login(password)
        single = list_link(token)
        phases = [phase("folder_link_list_10", token, 10), phase("folder_link_list_50", token, 50), phase("folder_link_list_100", token, 100)]
        stop_pid(int(process.pid))
        process = start_test_server()
        wait_health(pid=int(process.pid))
        token_after = login(password)
        readback = list_link(token_after)
        after = shadow()
        if single[0] != 200 or not single[1].get("ok") or not single[1].get("entries"):
            raise RuntimeError({"reason": "single folder-link list failed", "single": single[1]})
        if any(item["errors"] for item in phases):
            raise RuntimeError({"reason": "folder-link concurrency failed", "phases": phases})
        if readback[0] != 200 or not readback[1].get("ok") or not readback[1].get("entries"):
            raise RuntimeError({"reason": "folder-link restart readback failed", "readback": readback[1]})
        if not before["stable_parity"] or not before["volatile_timestamp_ok"]:
            raise RuntimeError({"reason": "folder-link shadow parity failed", "before": before, "after": after})
        print(json.dumps({
            "lesson_folder_links_postgres_http_gate": "ok",
            "setup": setup,
            "single": {"status": single[0], "entries": len(single[1].get("entries", [])), "ms": round(single[2], 3)},
            "concurrency": phases,
            "restart": {"status": readback[0], "entries": len(readback[1].get("entries", [])), "ms": round(readback[2], 3)},
            "shadow_before": before,
            "shadow_after": after,
            "production_flag": os.environ.get("FUTURE_DB_LESSON_FOLDER_LINKS_BACKEND", "off") or "off",
        }, ensure_ascii=False, indent=2))
        return 0
    finally:
        if process and process.poll() is None:
            stop_pid(int(process.pid))
        cleanup_sqlite()
        cleanup_postgres()
        try:
            if original_pid_file is None:
                app.SERVER_PID_FILE.unlink(missing_ok=True)
            else:
                app.SERVER_PID_FILE.write_text(original_pid_file, encoding="utf-8")
        except Exception:
            pass
        print(json.dumps({"cleanup": {"codexpgfolderlink_removed": True, "port_18877_busy": bool(server_pid_on_port(18877))}}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    raise SystemExit(main())
