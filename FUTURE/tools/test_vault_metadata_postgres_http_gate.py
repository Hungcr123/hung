#!/usr/bin/env python3
"""HTTP runtime/shadow gate for Lesson Vault metadata with PostgreSQL cache routing."""

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
import FUTURE.tools.migrate_vault_metadata_to_postgres as migrate_vault  # noqa: E402

DATABASE = Path(r"C:\server data\server2.db")
BASE = "http://127.0.0.1:18877"
USERS = tuple(f"codexpgvault{index:03d}" for index in range(1, 101))

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
    env["FUTURE_DB_VAULT_METADATA_BACKEND"] = "postgres"
    return subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--host", "127.0.0.1", "--port", "18877", "--no-browser", "--no-tunnel"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

def provision_users(password: str) -> None:
    now = app.utc_timestamp()
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        con.execute("BEGIN IMMEDIATE")
        for index, username in enumerate(USERS, 1):
            profile = json.dumps({"full_name": f"Codex PG Vault {index:03d}", "load_test": True}, separators=(",", ":"))
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
        con.commit()
    finally:
        con.close()

def cleanup_sqlite() -> dict:
    con = sqlite3.connect(DATABASE, timeout=30)
    try:
        con.execute("BEGIN IMMEDIATE")
        counts = {}
        for table in ("vault_entries", "vault_folders", "vault_revisions", "auth_sessions", "server_load_test_credentials", "users"):
            column = "username"
            con.execute(f"DELETE FROM {table} WHERE lower({column}) LIKE 'codexpgvault%'")
            counts[table] = int(con.total_changes)
        con.commit()
        return counts
    finally:
        con.close()

def cleanup_postgres() -> dict:
    def _write(connection):
        with connection.cursor() as cursor:
            out = {}
            for table in ("vault_entries", "vault_folders", "vault_revisions"):
                cursor.execute(f"DELETE FROM future_server2.{table} WHERE lower(username) LIKE 'codexpgvault%'")
                out[table] = int(cursor.rowcount or 0)
            return out
    return app.postgres_execute(_write)

def source_lesson() -> dict:
    con = sqlite3.connect(DATABASE)
    try:
        row = con.execute(
            "SELECT normalized_path,file_id FROM lesson_file_replicas "
            "WHERE status='active' AND lower(normalized_path) LIKE 'common/%' "
            "ORDER BY file_size ASC LIMIT 1"
        ).fetchone()
    finally:
        con.close()
    if not row:
        raise RuntimeError("No common lesson replica available for Vault gate")
    return {"path": row[0], "lesson_id": row[1]}

def login(username: str, password: str) -> str:
    deadline = time.monotonic() + 45
    last = ""
    while time.monotonic() < deadline:
        try:
            response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=10)
            last = f"{response.status_code} {response.text[:160]}"
            if response.status_code == 200:
                token = response.json().get("token")
                if token:
                    return token
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(0.5)
    raise RuntimeError(f"Login did not return token for {username}: {last}")

def request_json(method: str, path: str, token: str, **kwargs) -> tuple[int, dict, float]:
    started = time.perf_counter()
    response = requests.request(method, f"{BASE}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=60, **kwargs)
    elapsed = (time.perf_counter() - started) * 1000
    try:
        payload = response.json()
    except Exception:
        payload = {"raw": response.text[:200]}
    return response.status_code, payload, elapsed

def op(token: str, payload: dict) -> tuple[int, dict, float]:
    return request_json("POST", "/server-data/op", token, json=payload)

def phase(name: str, users: tuple[str, ...], tokens: dict[str, str]) -> dict:
    latencies = []
    statuses = {}
    errors = 0
    started = time.perf_counter()

    def one(username: str) -> tuple[int, float, bool]:
        status, payload, elapsed = op(tokens[username], {
            "action": "create_folder",
            "destination": username,
            "name": f"PG Vault {name} {username}",
        })
        ok = status == 200 and bool(payload.get("ok")) and bool((payload.get("result") or {}).get("vault_folder_id"))
        return status, elapsed, ok

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(users)) as executor:
        for status, elapsed, ok in executor.map(one, users):
            statuses[str(status)] = statuses.get(str(status), 0) + 1
            latencies.append(elapsed)
            if not ok:
                errors += 1
    wall = (time.perf_counter() - started) * 1000
    sorted_latencies = sorted(latencies) or [0.0]
    return {
        "name": name,
        "requests": len(users),
        "statuses": statuses,
        "errors": errors,
        "wall_ms": round(wall, 3),
        "throughput_rps": round(len(users) / (wall / 1000), 3) if wall else 0,
        "p50_ms": round(statistics.median(sorted_latencies), 3),
        "p95_ms": round(sorted_latencies[min(len(sorted_latencies) - 1, int(len(sorted_latencies) * 0.95))], 3),
        "p99_ms": round(sorted_latencies[min(len(sorted_latencies) - 1, int(len(sorted_latencies) * 0.99))], 3),
    }

def phase_same_user(name: str, username: str, token: str, requests_count: int) -> dict:
    latencies = []
    statuses = {}
    errors = 0
    started = time.perf_counter()

    def one(index: int) -> tuple[int, float, bool]:
        status, payload, elapsed = op(token, {
            "action": "create_folder",
            "destination": username,
            "name": f"PG Vault {name} {index:03d}",
        })
        ok = status == 200 and bool(payload.get("ok")) and bool((payload.get("result") or {}).get("vault_folder_id"))
        return status, elapsed, ok

    with concurrent.futures.ThreadPoolExecutor(max_workers=requests_count) as executor:
        for status, elapsed, ok in executor.map(one, range(1, requests_count + 1)):
            statuses[str(status)] = statuses.get(str(status), 0) + 1
            latencies.append(elapsed)
            if not ok:
                errors += 1
    wall = (time.perf_counter() - started) * 1000
    sorted_latencies = sorted(latencies) or [0.0]
    return {
        "name": name,
        "requests": requests_count,
        "statuses": statuses,
        "errors": errors,
        "wall_ms": round(wall, 3),
        "throughput_rps": round(requests_count / (wall / 1000), 3) if wall else 0,
        "p50_ms": round(statistics.median(sorted_latencies), 3),
        "p95_ms": round(sorted_latencies[min(len(sorted_latencies) - 1, int(len(sorted_latencies) * 0.95))], 3),
        "p99_ms": round(sorted_latencies[min(len(sorted_latencies) - 1, int(len(sorted_latencies) * 0.99))], 3),
    }

def user_counts(username: str) -> dict:
    con = sqlite3.connect(DATABASE)
    try:
        sqlite_counts = {
            "folders": con.execute("SELECT COUNT(*) FROM vault_folders WHERE username=?", (username,)).fetchone()[0],
            "entries": con.execute("SELECT COUNT(*) FROM vault_entries WHERE username=?", (username,)).fetchone()[0],
            "revisions": con.execute("SELECT COUNT(*) FROM vault_revisions WHERE username=?", (username,)).fetchone()[0],
        }
    finally:
        con.close()

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM future_server2.vault_folders WHERE username=%s", (username,))
            folders = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT COUNT(*) FROM future_server2.vault_entries WHERE username=%s", (username,))
            entries = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT COUNT(*) FROM future_server2.vault_revisions WHERE username=%s", (username,))
            revisions = int(cursor.fetchone()[0] or 0)
            return {"folders": folders, "entries": entries, "revisions": revisions}
    return {"sqlite": sqlite_counts, "postgres": app.postgres_execute(_read)}

def main() -> int:
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("FUTURE_PG_DSN is required")
    if server_pid_on_port(18877):
        raise RuntimeError("Port 18877 already has a listener")
    app.postgres_initialize_schema()
    pre = migrate_vault.main_verify_for_gate() if hasattr(migrate_vault, "main_verify_for_gate") else None
    original_pid_file = app.SERVER_PID_FILE.read_text(encoding="utf-8") if app.SERVER_PID_FILE.is_file() else None
    password = secrets.token_urlsafe(32)
    process: subprocess.Popen | None = None
    result = {}
    try:
        cleanup_sqlite()
        cleanup_postgres()
        provision_users(password)
        lesson = source_lesson()
        process = start_test_server()
        wait_health(pid=int(process.pid))
        tokens = {username: login(username, password) for username in USERS}
        token = tokens[USERS[0]]
        create = op(token, {"action": "create_folder", "destination": USERS[0], "name": "PG Vault Home"})
        copy = op(token, {"action": "copy_link", "source": lesson["path"], "destination": USERS[0]})
        copied_path = app.clean_path_value(((copy[1].get("result") or {}).get("path", "")))
        rename = op(token, {"action": "rename", "source": copied_path, "name": "Renamed PG Vault.Space_V"}) if copied_path else (0, {}, 0.0)
        renamed_path = app.clean_path_value(((rename[1].get("result") or {}).get("path", "")))
        listed = request_json("GET", f"/server-data/list?path={USERS[0]}&fresh=1", token)
        folders = request_json("GET", "/server-data/vault-folders", token)
        delete = op(token, {"action": "delete_link", "source": renamed_path}) if renamed_path else (0, {}, 0.0)
        phases = [
            phase("vault_create_10", USERS[:10], tokens),
            phase("vault_create_50", USERS[:50], tokens),
            phase("vault_create_100", USERS, tokens),
            phase_same_user("vault_same_user_10", USERS[0], token, 10),
            phase_same_user("vault_same_user_50", USERS[0], token, 50),
            phase_same_user("vault_same_user_100", USERS[0], token, 100),
        ]
        before_restart = user_counts(USERS[0])
        stop_pid(int(process.pid))
        process = start_test_server()
        wait_health(pid=int(process.pid))
        token_after = login(USERS[0], password)
        readback = request_json("GET", f"/server-data/list?path={USERS[0]}&fresh=1", token_after)
        after_restart = user_counts(USERS[0])
        invalid = op(token_after, {"action": "copy_link", "source": lesson["path"], "destination": "common"})
        if any(call[0] != 200 or not call[1].get("ok") for call in (create, copy, rename, listed, folders, delete, readback)):
            raise RuntimeError({"reason": "Vault HTTP flow failed", "create": create[1], "copy": copy[1], "rename": rename[1], "listed": listed[1], "folders": folders[1], "delete": delete[1], "readback": readback[1]})
        if invalid[0] == 200:
            raise RuntimeError({"reason": "Vault invalid common destination was accepted", "invalid": invalid[1]})
        if any(item["errors"] for item in phases):
            raise RuntimeError({"reason": "Vault concurrency phase failed", "phases": phases})
        result = {
            "vault_metadata_postgres_http_gate": "ok",
            "pre_verify": pre,
            "single": {
                "create_status": create[0],
                "copy_status": copy[0],
                "rename_status": rename[0],
                "delete_status": delete[0],
                "list_status": listed[0],
                "folders_status": folders[0],
                "invalid_common_destination_status": invalid[0],
            },
            "concurrency": phases,
            "restart": {"before": before_restart, "after": after_restart, "readback_status": readback[0]},
            "production_flag": os.environ.get("FUTURE_DB_VAULT_METADATA_BACKEND", "off") or "off",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
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
        print(json.dumps({"cleanup": {"sqlite_pg_users_removed": True, "port_18877_busy": bool(server_pid_on_port(18877))}}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    raise SystemExit(main())
