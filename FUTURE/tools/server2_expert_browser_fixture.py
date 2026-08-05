#!/usr/bin/env python3
"""Keep a fresh-snapshot isolated Server 2 alive for an in-app browser audit."""

from __future__ import annotations

import json
import time
from pathlib import Path

import test_server2_expert_user_load_isolated as load


RUN_ROOT = load.ROOT / "programe_cache" / "server2_expert_browser_18877"
READY = RUN_ROOT / "fixture.json"
STOP = RUN_ROOT / "stop"
USERNAME = "codexgate000"


def provision_browser_user() -> str:
    import psycopg
    from psycopg.types.json import Jsonb

    with psycopg.connect(load.isolated.PG_DSN) as connection, connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO future_server2.users
               (username,is_admin,is_test,profile_json,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
               VALUES (%s,false,true,%s,'2026-08-02T00:00:00Z',0,'','')
               ON CONFLICT (username) DO UPDATE SET is_test=true,profile_json=excluded.profile_json""",
            (USERNAME, Jsonb({"source": "server2-expert-browser"})),
        )
        cursor.execute(
            """INSERT INTO future_server2.user_auth_credentials
               (username,password_hash,source_path,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
               VALUES (%s,%s,'server2-expert-browser','2026-08-02T00:00:00Z',0,'','')
               ON CONFLICT (username) DO UPDATE SET password_hash=excluded.password_hash""",
            (USERNAME, load.isolated.password_hash(load.isolated.PASSWORD)),
        )
        connection.commit()
    return USERNAME


def main() -> int:
    load.RUN_ROOT = RUN_ROOT
    load.OUTPUT = RUN_ROOT / "unused.json"
    load.configure()
    load.remove_run_root()
    RUN_ROOT.mkdir(parents=True)
    server = None
    try:
        load.isolated.start_postgres()
        dump = load.isolated.sync_production_database_snapshot()
        load.isolated.initialize_schema()
        fixtures = load.prepare_server_data(load.select_fixtures())
        load.provision_users()
        username = provision_browser_user()
        server = load.isolated.start_server(
            no_preload=False,
            extra_env={
                "FUTURE_DISTRIBUTED_WORKER_PORT": "18890",
                "FUTURE_DISTRIBUTED_WORKER_TOKEN": "server2-expert-browser-isolated-token",
                "FUTURE_VOICE_WORKER_PORT": "18778",
            },
        )
        health = load.isolated.wait_health(server)
        token = load.isolated.login(username)
        READY.write_text(json.dumps({
            "database_sync": {"enabled": True, "dump_bytes": dump.stat().st_size},
            "base": load.isolated.BASE,
            "username": username,
            "password": load.isolated.PASSWORD,
            "token": token,
            "fixtures": fixtures,
            "health": {"pid": health.get("pid"), "ready": health.get("ready"), "warm_ready": health.get("warm_ready")},
        }, ensure_ascii=False), encoding="utf-8")
        deadline = time.time() + 15 * 60
        while time.time() < deadline and not STOP.exists():
            time.sleep(0.25)
        return 0
    finally:
        load.isolated.stop_server(server)
        load.stop_isolated_voice_worker()
        load.isolated.stop_postgres()
        load.remove_run_root()


if __name__ == "__main__":
    raise SystemExit(main())
