#!/usr/bin/env python3
"""Hold a freshly synced isolated Vault server for two-tab browser verification."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.tools.test_lesson_complete_isolated_harness as isolated
import FUTURE.tools.test_vault_folder_create_isolated_harness as vault_gate

RUN_ROOT = ROOT / "programe_cache" / "vault_realtime_browser_18877"
READY = RUN_ROOT / "ready.json"
STOP = RUN_ROOT / "stop"


def configure() -> None:
    test_password = str(os.environ.get("FUTURE_TEST_PASSWORD") or "").strip()
    if not test_password:
        raise RuntimeError("FUTURE_TEST_PASSWORD is required for isolated browser verification")
    isolated.PASSWORD = test_password
    isolated.RUN_ROOT = RUN_ROOT
    isolated.PG_ROOT = RUN_ROOT / "postgres"
    isolated.SERVER_DATA_ROOT = RUN_ROOT / "server-data"
    isolated.RUNTIME_ROOT = RUN_ROOT / "runtime"
    isolated.QMLEARN_ROOT = RUN_ROOT / "qml"
    isolated.SERVER_LOG = RUN_ROOT / "server.log"
    isolated.PG_LOG = RUN_ROOT / "postgres.log"
    vault_gate.RUN_ROOT = RUN_ROOT


def start_server() -> subprocess.Popen:
    env = isolated.app_env()
    env["FUTURE_TEST_AUTH_BYPASS"] = "1"
    handle = isolated.SERVER_LOG.open("ab")
    return subprocess.Popen(
        [sys.executable, "FUTURE_SERVER_2.py", "--host", "127.0.0.1", "--port", "18877", "--no-browser", "--no-tunnel", "--no-preload"],
        cwd=ROOT,
        env=env,
        stdout=handle,
        stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


# Added 2026-07-29: keep the realistic hung browser session stable while an admin mutates the isolated Vault.
def provision_hung_browser_password() -> None:
    import psycopg

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE future_server2.user_auth_credentials
            SET password_hash=%s, updated_at_utc=%s
            WHERE lower(username)='hung'
            """,
            (vault_gate.password_hash(isolated.PASSWORD), now),
        )
        if cursor.rowcount != 1:
            raise RuntimeError(f"expected one isolated hung credential row, got {cursor.rowcount}")


def main() -> int:
    configure()
    if any(c.laddr and c.laddr.port == 18877 and c.status == psutil.CONN_LISTEN for c in psutil.net_connections(kind="tcp")):
        raise RuntimeError("port 18877 is already in use")
    shutil.rmtree(RUN_ROOT, ignore_errors=True)
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    server = None
    try:
        isolated.copy_lesson()
        isolated.start_postgres()
        dump_path = isolated.sync_production_database_snapshot()
        vault_gate.provision_users()
        provision_hung_browser_password()
        server = start_server()
        health = isolated.wait_health(server)
        payload = {
            "ok": True,
            "database_sync": {
                "enabled": True,
                "source": "127.0.0.1:5432/future_server2",
                "method": "fresh pg_dump + pg_restore before run",
                "dump_bytes": dump_path.stat().st_size,
            },
            "user": vault_gate.USER,
            "base": isolated.BASE,
            "pid": health.get("pid"),
        }
        READY.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload), flush=True)
        deadline = time.monotonic() + 600
        while not STOP.exists() and time.monotonic() < deadline:
            time.sleep(0.25)
        return 0
    finally:
        isolated.stop_server(server)
        isolated.stop_postgres()
        shutil.rmtree(RUN_ROOT, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
