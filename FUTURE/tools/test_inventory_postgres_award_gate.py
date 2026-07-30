#!/usr/bin/env python3
"""HTTP award write gate for inventory SQLite vs PostgreSQL backends."""

from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
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
USERS = tuple(f"codexinvwrite{index:03d}" for index in range(1, 101))

def password_hash(value: str) -> str:
    salt = secrets.token_urlsafe(18)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode(), salt.encode(), 2)
    return "pbkdf2_sha256$2$%s$%s" % (salt, base64.urlsafe_b64encode(digest).decode().rstrip("="))

def password_hash_matches(value: str, encoded: str) -> bool:
    parts = str(encoded or "").split("$")
    if len(parts) != 4:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", value.encode(), parts[2].encode(), int(parts[1]))
    return hmac.compare_digest(base64.urlsafe_b64encode(digest).decode().rstrip("="), parts[3])

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

def wait_health(timeout: float = 90.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            response = requests.get(f"{BASE}/health", timeout=3)
            if response.status_code == 200 and response.json().get("ok"):
                return response.json()
        except Exception:
            pass
        time.sleep(0.35)
    raise RuntimeError("test server did not become healthy")

def start_server(backend: str) -> subprocess.Popen:
    env = dict(os.environ)
    if backend == "postgres":
        env["FUTURE_DB_INVENTORY_BACKEND"] = "postgres"
        env["FUTURE_TEST_INVENTORY_FORCE_ROLLBACK"] = "1"
    else:
        env.pop("FUTURE_DB_INVENTORY_BACKEND", None)
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
            cur = con.execute(f"DELETE FROM {table} WHERE lower(username) LIKE 'codexinvwrite%'")
            out[table] = int(cur.rowcount or 0)
        con.commit()
        return out
    finally:
        con.close()

def cleanup_postgres() -> dict:
    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.inventory_events WHERE lower(username) LIKE 'codexinvwrite%'")
            events = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.inventory_items WHERE lower(username) LIKE 'codexinvwrite%'")
            items = int(cursor.rowcount or 0)
        return {"inventory_items": items, "inventory_events": events}
    return app.postgres_execute(_write)

def provision_users(password: str) -> None:
    now = app.utc_timestamp()
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        con.execute("BEGIN IMMEDIATE")
        for username in USERS:
            con.execute(
                "INSERT INTO users(username,is_admin,is_test,profile_json,updated_at_utc) VALUES(?,0,1,'{}',?) "
                "ON CONFLICT(username) DO UPDATE SET is_test=1,updated_at_utc=excluded.updated_at_utc",
                (username, now),
            )
            existing = con.execute("SELECT password_hash FROM server_load_test_credentials WHERE username=?", (username,)).fetchone()
            encoded = existing[0] if existing and password_hash_matches(password, existing[0]) else password_hash(password)
            con.execute(
                "INSERT INTO server_load_test_credentials(username,password_hash,updated_at_utc) VALUES(?,?,?) "
                "ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash,updated_at_utc=excluded.updated_at_utc",
                (username, encoded, now),
            )
        con.commit()
    finally:
        con.close()

def install_sqlite_rollback_trigger() -> None:
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        con.execute("DROP TRIGGER IF EXISTS codex_inventory_rollback_test")
        con.execute(
            "CREATE TRIGGER codex_inventory_rollback_test BEFORE INSERT ON inventory_items "
            "WHEN NEW.item_id='rollback_item' BEGIN SELECT RAISE(ABORT, 'forced inventory rollback'); END"
        )
        con.commit()
    finally:
        con.close()

def drop_sqlite_rollback_trigger() -> None:
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        con.execute("DROP TRIGGER IF EXISTS codex_inventory_rollback_test")
        con.commit()
    finally:
        con.close()

def login(username: str, password: str) -> requests.Session:
    session = requests.Session()
    response = session.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
    response.raise_for_status()
    session.headers.update({"Authorization": "Bearer " + response.json()["token"]})
    return session

def award_payload(event_id: str, item_id: str = "codex_crystal", quantity: int = 1) -> dict:
    return {"event_id": event_id, "item": {"id": item_id, "name": "Codex Crystal", "use": "test"}, "quantity": quantity}

def post_award(session: requests.Session, payload: dict) -> tuple[int, dict, float]:
    started = time.perf_counter()
    response = session.post(f"{BASE}/inventory/award?response=delta-v1", json=payload, timeout=60)
    elapsed = (time.perf_counter() - started) * 1000
    try:
        body = response.json()
    except Exception:
        body = {"raw": response.text[:200]}
    return response.status_code, body, elapsed

def read_backend(backend: str, username: str, item_id: str) -> dict:
    if backend == "sqlite":
        con = sqlite3.connect(DATABASE)
        try:
            item = con.execute("SELECT quantity FROM inventory_items WHERE username=? AND item_id=?", (username, item_id)).fetchone()
            events = con.execute("SELECT COUNT(*) FROM inventory_events WHERE username=?", (username,)).fetchone()[0]
            return {"quantity": int(item[0] or 0) if item else 0, "events": int(events or 0)}
        finally:
            con.close()
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT quantity FROM future_server2.inventory_items WHERE username=%s AND item_id=%s", (username, item_id))
            item = cursor.fetchone()
            cursor.execute("SELECT COUNT(*) FROM future_server2.inventory_events WHERE username=%s", (username,))
            events = cursor.fetchone()[0]
        return {"quantity": int(item[0] or 0) if item else 0, "events": int(events or 0)}
    return app.postgres_execute(_read)

def backend_event_exists(backend: str, username: str, event_id: str, item_id: str) -> dict:
    if backend == "sqlite":
        con = sqlite3.connect(DATABASE)
        try:
            events = con.execute("SELECT COUNT(*) FROM inventory_events WHERE username=? AND event_id=?", (username, event_id)).fetchone()[0]
            items = con.execute("SELECT COUNT(*) FROM inventory_items WHERE username=? AND item_id=?", (username, item_id)).fetchone()[0]
            return {"events": int(events or 0), "items": int(items or 0)}
        finally:
            con.close()
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM future_server2.inventory_events WHERE username=%s AND event_id=%s", (username, event_id))
            events = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM future_server2.inventory_items WHERE username=%s AND item_id=%s", (username, item_id))
            items = cursor.fetchone()[0]
        return {"events": int(events or 0), "items": int(items or 0)}
    return app.postgres_execute(_read)

def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(len(ordered) * pct / 100.0))], 3)

def phase(name: str, backend: str, users: tuple[str, ...], sessions: dict[str, requests.Session], event_prefix: str, same_item: bool = False) -> dict:
    latencies = []
    errors = 0
    mismatches = 0
    awarded = 0
    sample_errors = []
    def one(pair):
        index, username = pair
        item_id = "codex_shared" if same_item else f"codex_item_{index:03d}"
        payload = award_payload(f"{event_prefix}-{username}-{index}", item_id, 1)
        return username, item_id, post_award(sessions[username], payload)
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, len(users))) as executor:
        rows = list(executor.map(one, enumerate(users, 1)))
    for username, item_id, (status, body, elapsed) in rows:
        latencies.append(elapsed)
        if status != 200:
            errors += 1
            if len(sample_errors) < 3:
                sample_errors.append({"status": status, "body": body})
        if bool(body.get("awarded")):
            awarded += 1
        state = read_backend(backend, username, item_id)
        if status != 200 or state["quantity"] < 1 or state["events"] < 1:
            mismatches += 1
    wall = (time.perf_counter() - started) * 1000
    return {
        "name": name,
        "backend": backend,
        "requests": len(users),
        "success": len(users) - errors,
        "errors": errors,
        "timeouts": 0,
        "awarded": awarded,
        "mismatches": mismatches,
        "sample_errors": sample_errors,
        "wall_ms": round(wall, 3),
        "throughput_rps": round(len(users) / max(0.001, wall / 1000), 3),
        "p50_ms": percentile(latencies, 50),
        "p95_ms": percentile(latencies, 95),
        "p99_ms": percentile(latencies, 99),
    }

def run_backend(backend: str, password: str) -> dict:
    stop_pid(server_pid_on_port(18877))
    cleanup_sqlite()
    cleanup_postgres()
    provision_users(password)
    if backend == "sqlite":
        install_sqlite_rollback_trigger()
    proc = start_server(backend)
    try:
        health = wait_health()
        sessions = {username: login(username, password) for username in USERS}
        single = phase("single", backend, USERS[:1], sessions, f"{backend}-single")
        retry_payload = award_payload(f"{backend}-retry-event", "codex_retry", 3)
        first_retry = post_award(sessions[USERS[0]], retry_payload)
        exact_retry = post_award(sessions[USERS[0]], retry_payload)
        conflict_retry = post_award(sessions[USERS[0]], award_payload(f"{backend}-retry-event", "codex_conflict", 9))
        rollback_event = f"{backend}-rollback-event"
        rollback = post_award(sessions[USERS[0]], award_payload(rollback_event, "rollback_item", 1))
        rollback_state = backend_event_exists(backend, USERS[0], rollback_event, "rollback_item")
        distinct10 = phase("distinct10", backend, USERS[:10], sessions, f"{backend}-d10")
        distinct50 = phase("distinct50", backend, USERS[:50], sessions, f"{backend}-d50")
        distinct100 = phase("distinct100", backend, USERS, sessions, f"{backend}-d100")
        same_item = phase("same_item_100", backend, USERS, sessions, f"{backend}-sameitem", same_item=True)
        return {
            "backend": backend,
            "health_pid": health.get("pid"),
            "phases": [single, distinct10, distinct50, distinct100, same_item],
            "retry": {
                "first": {"status": first_retry[0], "awarded": first_retry[1].get("awarded")},
                "exact": {"status": exact_retry[0], "awarded": exact_retry[1].get("awarded")},
                "conflict": {"status": conflict_retry[0], "awarded": conflict_retry[1].get("awarded"), "item": (conflict_retry[1].get("item") or {}).get("id")},
            },
            "rollback": {"status": rollback[0], "body": rollback[1], "state": rollback_state},
        }
    finally:
        stop_pid(proc.pid if proc else 0)
        if backend == "sqlite":
            drop_sqlite_rollback_trigger()

def main() -> int:
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before running inventory award gate.")
    password = secrets.token_urlsafe(24)
    result = {"ok": False}
    try:
        sqlite = run_backend("sqlite", password)
        postgres = run_backend("postgres", password)
        cleanup = {"sqlite": cleanup_sqlite(), "postgres": cleanup_postgres()}
        ok = all(phase["errors"] == 0 and phase["mismatches"] == 0 for item in (sqlite, postgres) for phase in item["phases"])
        ok = ok and sqlite["retry"]["first"]["awarded"] is True and sqlite["retry"]["exact"]["awarded"] is False
        ok = ok and postgres["retry"]["first"]["awarded"] is True and postgres["retry"]["exact"]["awarded"] is False
        ok = ok and sqlite["retry"]["conflict"]["item"] == "codex_retry" and postgres["retry"]["conflict"]["item"] == "codex_retry"
        ok = ok and sqlite["rollback"]["status"] == 400 and postgres["rollback"]["status"] == 400
        ok = ok and sqlite["rollback"]["state"] == {"events": 0, "items": 0} and postgres["rollback"]["state"] == {"events": 0, "items": 0}
        result = {"ok": ok, "sqlite": sqlite, "postgres": postgres, "cleanup": cleanup, "production_enabled": os.environ.get("FUTURE_DB_INVENTORY_BACKEND", "") or "off"}
    finally:
        stop_pid(server_pid_on_port(18877))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1

if __name__ == "__main__":
    raise SystemExit(main())
