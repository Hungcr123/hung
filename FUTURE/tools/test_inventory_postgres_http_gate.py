#!/usr/bin/env python3
"""HTTP read-runtime gate for inventory with PostgreSQL routing."""

from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import hmac
import json
import os
import secrets
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

DATABASE = Path(r"C:\server data\server2.db")
BASE = "http://127.0.0.1:18877"
PRODUCTION_BASE = "http://127.0.0.1:8877"
USERS = tuple(f"codexinvread{index:03d}" for index in range(1, 101))

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
        pass

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
    env["FUTURE_DB_INVENTORY_BACKEND"] = "postgres"
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
        out = {}
        for table in ("inventory_events", "inventory_items", "auth_sessions", "server_load_test_credentials", "users"):
            cursor = con.execute(f"DELETE FROM {table} WHERE lower(username) LIKE 'codexinvread%'")
            out[table] = int(cursor.rowcount or 0)
        con.commit()
        return out
    finally:
        con.close()

def cleanup_postgres() -> dict:
    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.inventory_events WHERE lower(username) LIKE 'codexinvread%'")
            deleted_events = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.inventory_items WHERE lower(username) LIKE 'codexinvread%'")
            deleted_items = int(cursor.rowcount or 0)
            return {"deleted_items": deleted_items, "deleted_events": deleted_events}
    return app.postgres_execute(_write)

def provision_users_and_inventory(password: str) -> None:
    now = app.utc_timestamp()
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        con.execute("BEGIN IMMEDIATE")
        for index, username in enumerate(USERS, 1):
            profile = json.dumps({"full_name": f"Codex Inventory Read {index:03d}", "load_test": True}, separators=(",", ":"))
            con.execute(
                "INSERT INTO users(username,is_admin,is_test,profile_json,updated_at_utc) VALUES(?,0,1,?,?) "
                "ON CONFLICT(username) DO UPDATE SET is_admin=0,is_test=1,profile_json=excluded.profile_json,updated_at_utc=excluded.updated_at_utc",
                (username, profile, now),
            )
            existing = con.execute("SELECT password_hash FROM server_load_test_credentials WHERE username=?", (username,)).fetchone()
            encoded = existing[0] if existing and password_hash_matches(password, existing[0]) else password_hash(password)
            con.execute(
                "INSERT INTO server_load_test_credentials(username,password_hash,updated_at_utc) VALUES(?,?,?) "
                "ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash,updated_at_utc=excluded.updated_at_utc",
                (username, encoded, now),
            )
            item_id = f"codex-inv-item-{index:03d}"
            con.execute(
                "INSERT INTO inventory_items(username,item_id,name,use_text,quantity,updated_at_utc) VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(username,item_id) DO UPDATE SET name=excluded.name,use_text=excluded.use_text,quantity=excluded.quantity,updated_at_utc=excluded.updated_at_utc",
                (username, item_id, f"Codex Inventory {index:03d}", "runtime read gate", index, now),
            )
            for event_index in range(1, 4):
                con.execute(
                    "INSERT OR REPLACE INTO inventory_events(username,event_id,item_id,quantity,awarded_at_utc) VALUES(?,?,?,?,?)",
                    (username, f"codex-inv-event-{index:03d}-{event_index}", item_id, event_index, now),
                )
        con.commit()
    finally:
        con.close()

def migrate_copy() -> dict:
    raw = subprocess.check_output([sys.executable, str(ROOT / "FUTURE/tools/migrate_inventory_to_postgres.py")], cwd=ROOT, text=True)
    return json.loads(raw)

def migrate_verify() -> dict:
    raw = subprocess.check_output([sys.executable, str(ROOT / "FUTURE/tools/migrate_inventory_to_postgres.py"), "--verify-only"], cwd=ROOT, text=True)
    return json.loads(raw)

def login(username: str, password: str) -> requests.Session:
    session = requests.Session()
    response = session.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
    response.raise_for_status()
    session.headers.update({"Authorization": f"Bearer {response.json()['token']}"})
    return session

def request_inventory(session: requests.Session, compact: bool) -> tuple[int, dict, float]:
    started = time.perf_counter()
    params = {"response": "compact-v1"} if compact else {}
    response = session.get(f"{BASE}/inventory", params=params, timeout=90)
    elapsed = (time.perf_counter() - started) * 1000
    try:
        payload = response.json()
    except Exception:
        payload = {"raw": response.text[:200]}
    return response.status_code, payload, elapsed

def item_quantity(payload: dict, username: str) -> int:
    suffix = username[-3:]
    item_id = f"codex-inv-item-{suffix}"
    inventory = payload.get("inventory") if isinstance(payload.get("inventory"), dict) else {}
    items = inventory.get("items") if isinstance(inventory.get("items"), dict) else {}
    item = items.get(item_id) if isinstance(items.get(item_id), dict) else {}
    return int(item.get("quantity", 0) or 0)

def event_count(payload: dict) -> int:
    inventory = payload.get("inventory") if isinstance(payload.get("inventory"), dict) else {}
    events = inventory.get("events") if isinstance(inventory.get("events"), list) else []
    return len(events)

def phase(name: str, users: tuple[str, ...], sessions: dict[str, requests.Session], compact: bool) -> dict:
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(users)) as executor:
        rows = list(executor.map(lambda user: request_inventory(sessions[user], compact), users))
    latencies = sorted(row[2] for row in rows)
    statuses: dict[str, int] = {}
    bad_quantity = 0
    bad_events = 0
    for user, row in zip(users, rows):
        statuses[str(row[0])] = statuses.get(str(row[0]), 0) + 1
        expected = int(user[-3:])
        if row[0] != 200 or item_quantity(row[1], user) != expected:
            bad_quantity += 1
        if not compact and event_count(row[1]) != 3:
            bad_events += 1
        if compact and event_count(row[1]) != 0:
            bad_events += 1
    wall = (time.perf_counter() - started) * 1000
    return {
        "name": name,
        "requests": len(users),
        "statuses": statuses,
        "errors": sum(1 for row in rows if row[0] >= 400),
        "bad_quantity": bad_quantity,
        "bad_events": bad_events,
        "wall_ms": round(wall, 3),
        "throughput_rps": round(len(users) / max(0.001, wall / 1000), 3),
        "p50_ms": round(statistics.median(latencies), 3) if latencies else 0,
        "p95_ms": round(latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))], 3) if latencies else 0,
        "p99_ms": round(latencies[min(len(latencies) - 1, int(len(latencies) * 0.99))], 3) if latencies else 0,
    }

def production_health() -> dict:
    try:
        response = requests.get(f"{PRODUCTION_BASE}/health", timeout=5)
        payload = response.json()
        return {"status": response.status_code, "ok": bool(payload.get("ok")), "writer_queue": (payload.get("sqlite_writer") or {}).get("queue_depth")}
    except Exception as exc:
        return {"status": 0, "ok": False, "error": type(exc).__name__}

def main() -> int:
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before running the inventory PostgreSQL HTTP gate.")
    password = secrets.token_urlsafe(24)
    original_pid_text = app.SERVER_PID_FILE.read_text(encoding="utf-8") if app.SERVER_PID_FILE.exists() else None
    proc: subprocess.Popen | None = None
    result: dict = {"ok": False}
    try:
        cleanup_sqlite()
        cleanup_postgres()
        provision_users_and_inventory(password)
        copy_result = migrate_copy()
        if not copy_result.get("parity"):
            raise RuntimeError(f"copy parity failed: {copy_result}")
        existing = server_pid_on_port(18877)
        if existing:
            stop_pid(existing)
        proc = start_test_server()
        wait_health(proc.pid)
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
            sessions = dict(zip(USERS, executor.map(lambda user: login(user, password), USERS)))
        phases = []
        for count in (1, 10, 50, 100):
            phases.append(phase(f"{count}_compact_read", USERS[:count], sessions, True))
            phases.append(phase(f"{count}_full_read", USERS[:count], sessions, False))
        if any(item["errors"] or item["bad_quantity"] or item["bad_events"] for item in phases):
            raise RuntimeError(f"read phase failed: {phases}")
        stop_pid(proc.pid)
        proc = None
        proc = start_test_server()
        wait_health(proc.pid)
        restart_session = login(USERS[0], password)
        restart_read = request_inventory(restart_session, False)
        if restart_read[0] != 200 or item_quantity(restart_read[1], USERS[0]) != 1 or event_count(restart_read[1]) != 3:
            raise RuntimeError("restart readback failed")
        verify = migrate_verify()
        if not verify.get("parity"):
            raise RuntimeError(f"verify-only failed: {verify}")
        result = {"ok": True, "copy": copy_result, "phases": phases, "restart_read_status": restart_read[0], "verify_only": verify}
    finally:
        if proc is not None:
            stop_pid(proc.pid)
        cleanup_pg = cleanup_postgres()
        cleanup_sq = cleanup_sqlite()
        final_verify = None
        try:
            final_verify = migrate_verify()
        except Exception as exc:
            final_verify = {"ok": False, "error": str(exc)}
        result["cleanup"] = {"postgres": cleanup_pg, "sqlite": cleanup_sq}
        result["final_verify_only"] = final_verify
        result["production_health"] = production_health()
        result["port_18877_pid"] = server_pid_on_port(18877)
        if original_pid_text is None:
            app.SERVER_PID_FILE.unlink(missing_ok=True)
        else:
            app.SERVER_PID_FILE.write_text(original_pid_text, encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") and result.get("final_verify_only", {}).get("parity") and result.get("port_18877_pid") == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
