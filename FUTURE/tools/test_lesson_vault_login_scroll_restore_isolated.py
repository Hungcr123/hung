#!/usr/bin/env python3
"""Fresh production-snapshot browser gate for login last-file scroll restoration."""

from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.tools.test_lesson_complete_isolated_harness as isolated

RUN_ROOT = ROOT / "programe_cache" / "lesson_vault_login_scroll_18877"
OUTPUT = Path(r"C:\Users\Admin\.codex\plans\lesson_vault_login_scroll_restore_isolated_20260731.json")
USERNAME = "quynh"
PRODUCTION_SERVER_DATA = Path(r"C:\server data")


def configure() -> None:
    isolated.RUN_ROOT = RUN_ROOT
    isolated.PG_ROOT = RUN_ROOT / "postgres"
    isolated.SERVER_DATA_ROOT = RUN_ROOT / "server-data"
    isolated.RUNTIME_ROOT = RUN_ROOT / "runtime"
    isolated.QMLEARN_ROOT = RUN_ROOT / "qml"
    isolated.SERVER_LOG = RUN_ROOT / "server.log"
    isolated.PG_LOG = RUN_ROOT / "postgres.log"


def provision_user_and_copy_folder(password: str) -> dict:
    import psycopg

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
        cursor.execute(
            "UPDATE future_server2.user_auth_credentials SET password_hash=%s, updated_at_utc=%s WHERE lower(username)=lower(%s)",
            (isolated.password_hash(password), now, USERNAME),
        )
        if cursor.rowcount != 1:
            raise RuntimeError(f"expected one isolated credential row for {USERNAME}, got {cursor.rowcount}")
        cursor.execute(
            "SELECT state_json FROM future_server2.lesson_last_file WHERE lower(username)=lower(%s)",
            (USERNAME,),
        )
        row = cursor.fetchone()
        state = row[0] if row and isinstance(row[0], dict) else {}
        connection.commit()
    file_row = state.get("file") if isinstance(state.get("file"), dict) else {}
    file_path = str(file_row.get("path") or "").replace("\\", "/").strip("/")
    if not file_path:
        raise RuntimeError(f"isolated production snapshot has no last file for {USERNAME}")
    parent = Path(file_path).parent
    source_parent = PRODUCTION_SERVER_DATA / parent
    target_parent = isolated.SERVER_DATA_ROOT / parent
    if not source_parent.is_dir():
        raise RuntimeError(f"last-file parent is missing: {source_parent}")
    shutil.copytree(source_parent, target_parent, dirs_exist_ok=True)
    for directory in ("Sound", "Picture", "NPC_TOP"):
        (isolated.SERVER_DATA_ROOT / directory).mkdir(parents=True, exist_ok=True)
    return {"file": file_path, "parent": parent.as_posix(), "copied_files": sum(1 for path in target_parent.rglob("*") if path.is_file())}


def main() -> int:
    configure()
    if any(connection.laddr and connection.laddr.port == isolated.HTTP_PORT and connection.status == psutil.CONN_LISTEN for connection in psutil.net_connections(kind="tcp")):
        raise RuntimeError(f"port {isolated.HTTP_PORT} is already in use")
    shutil.rmtree(RUN_ROOT, ignore_errors=True)
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    password = secrets.token_urlsafe(24)
    server = None
    try:
        isolated.start_postgres()
        dump = isolated.sync_production_database_snapshot()
        target = provision_user_and_copy_folder(password)
        server = isolated.start_server(no_preload=True)
        health = isolated.wait_health(server)
        env = dict(os.environ)
        env["FUTURE_TEST_PASSWORD"] = password
        probe = subprocess.run(
            ["node", "FUTURE/tools/probe_lesson_vault_login_scroll_restore.cjs", isolated.BASE, USERNAME],
            cwd=ROOT,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=180,
        )
        if probe.returncode != 0:
            raise RuntimeError(f"browser probe failed: {probe.stdout[-4000:]}\n{probe.stderr[-4000:]}")
        browser_result = json.loads(probe.stdout)
        evidence = {
            "ok": bool(browser_result.get("ok")),
            "database_sync": {
                "enabled": True,
                "source": "127.0.0.1:5432/future_server2",
                "method": "fresh pg_dump + pg_restore before run",
                "dump_bytes": dump.stat().st_size,
            },
            "resources": {
                "http": isolated.BASE,
                "postgres_port": isolated.PG_PORT,
                "server_data_root": str(isolated.SERVER_DATA_ROOT),
                "production_mutated": False,
            },
            "health": {"pid": health.get("pid"), "ready": health.get("ready"), "warm_ready": health.get("warm_ready")},
            "user": USERNAME,
            "target": target,
            "browser": browser_result,
        }
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"ok": evidence["ok"], "evidence": str(OUTPUT), "target": target, "fresh_login": browser_result.get("first"), "refresh": browser_result.get("refreshed")}, ensure_ascii=False))
        return 0 if evidence["ok"] else 1
    finally:
        isolated.stop_server(server)
        isolated.stop_postgres()
        shutil.rmtree(RUN_ROOT, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
