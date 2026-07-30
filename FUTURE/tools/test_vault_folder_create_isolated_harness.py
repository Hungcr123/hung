#!/usr/bin/env python3
"""Fresh production-copy gate for PostgreSQL-only Lesson Vault folder creation."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import shutil
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.tools.test_lesson_complete_isolated_harness as isolated

RUN_ROOT = ROOT / "programe_cache" / "vault_folder_isolated_18877"
OUTPUT = Path(r"C:\Users\Admin\.codex\plans\vault_folder_postgres_isolated_20260729.json")
USER = "codexvaultisolated"
ADMIN = "codexvaultadmin"


def configure() -> None:
    isolated.RUN_ROOT = RUN_ROOT
    isolated.PG_ROOT = RUN_ROOT / "postgres"
    isolated.SERVER_DATA_ROOT = RUN_ROOT / "server-data"
    isolated.RUNTIME_ROOT = RUN_ROOT / "runtime"
    isolated.QMLEARN_ROOT = RUN_ROOT / "qml"
    isolated.SERVER_LOG = RUN_ROOT / "server.log"
    isolated.PG_LOG = RUN_ROOT / "postgres.log"


def password_hash(value: str) -> str:
    rounds = 2
    salt = secrets.token_urlsafe(18)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode(), salt.encode(), rounds)
    encoded = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return f"pbkdf2_sha256${rounds}${salt}${encoded}"


def provision_users() -> None:
    import psycopg

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
        for username, is_admin in ((USER, False), (ADMIN, True)):
            cursor.execute(
                """
                INSERT INTO future_server2.users
                    (username,is_admin,profile_json,updated_at_utc,updated_epoch,is_test,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,0,true,'','')
                ON CONFLICT(username) DO UPDATE SET is_admin=excluded.is_admin,is_test=true,profile_json=excluded.profile_json
                """,
                (username, is_admin, json.dumps({"source": "isolated-vault-gate"}), now),
            )
            cursor.execute(
                """
                INSERT INTO future_server2.user_auth_credentials
                    (username,password_hash,source_path,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,'isolated-vault-gate',%s,0,'','')
                ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash,updated_at_utc=excluded.updated_at_utc
                """,
                (username, password_hash(isolated.PASSWORD), now),
            )
        cursor.execute(
            """
            INSERT INTO future_server2.admin_users
                (username,enabled,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
            VALUES (%s,true,%s,0,'','')
            ON CONFLICT(username) DO UPDATE SET enabled=true,updated_at_utc=excluded.updated_at_utc
            """,
            (ADMIN, now),
        )


def login(username: str) -> str:
    response = requests.post(
        f"{isolated.BASE}/auth/login",
        json={"username": username, "password": isolated.PASSWORD},
        timeout=30,
    )
    response.raise_for_status()
    return str(response.json()["token"])


def request(token: str, payload: dict) -> dict:
    process = psutil.Process(int(requests.get(f"{isolated.BASE}/health", timeout=5).json()["pid"]))
    before_cpu = isolated.server_cpu(process)
    before_pg = isolated.postgres_cpu()
    started = time.perf_counter()
    response = requests.post(
        f"{isolated.BASE}/server-data/op",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=30,
    )
    return {
        "status": response.status_code,
        "payload": response.json(),
        "wall_ms": round((time.perf_counter() - started) * 1000, 3),
        "server_cpu_ms": round(isolated.server_cpu(process) - before_cpu, 3),
        "postgres_cpu_ms": round(isolated.postgres_cpu() - before_pg, 3),
        "response_bytes": len(response.content),
    }


def postgres_state() -> dict:
    import psycopg

    with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT display_name,parent_folder_id FROM future_server2.vault_folders WHERE username=%s AND status='active' ORDER BY display_name",
            (USER,),
        )
        rows = cursor.fetchall()
        cursor.execute("SELECT revision FROM future_server2.vault_revisions WHERE username=%s", (USER,))
        revision_row = cursor.fetchone()
    return {"active_folders": len(rows), "names": [row[0] for row in rows], "revision": int(revision_row[0] if revision_row else 0)}


def benchmark_creates(token: str, count: int = 20) -> dict:
    process = psutil.Process(int(requests.get(f"{isolated.BASE}/health", timeout=5).json()["pid"]))
    server_before = isolated.server_cpu(process)
    postgres_before = isolated.postgres_cpu()
    walls = []
    response_bytes = 0
    for index in range(count):
        started = time.perf_counter()
        response = requests.post(
            f"{isolated.BASE}/server-data/op",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "create_folder", "destination": USER, "name": f"Bench {index + 1:02d}"},
            timeout=30,
        )
        response.raise_for_status()
        walls.append((time.perf_counter() - started) * 1000)
        response_bytes += len(response.content)
    sorted_walls = sorted(walls)
    server_cpu = isolated.server_cpu(process) - server_before
    postgres_cpu = isolated.postgres_cpu() - postgres_before
    return {
        "requests": count,
        "wall_mean_ms": round(statistics.mean(walls), 3),
        "wall_p95_ms": round(sorted_walls[min(len(sorted_walls) - 1, int(len(sorted_walls) * 0.95))], 3),
        "server_cpu_total_ms": round(server_cpu, 3),
        "server_cpu_per_request_ms": round(server_cpu / count, 3),
        "postgres_cpu_total_ms": round(postgres_cpu, 3),
        "postgres_cpu_per_request_ms": round(postgres_cpu / count, 3),
        "response_bytes_mean": round(response_bytes / count, 1),
    }


def benchmark_revision_reads(token: str, count: int = 20) -> dict:
    process = psutil.Process(int(requests.get(f"{isolated.BASE}/health", timeout=5).json()["pid"]))
    server_before = isolated.server_cpu(process)
    postgres_before = isolated.postgres_cpu()
    walls = []
    response_bytes = 0
    last_payload = {}
    for _ in range(count):
        started = time.perf_counter()
        response = requests.get(
            f"{isolated.BASE}/server-data/vault-revision",
            headers={"Authorization": f"Bearer {token}"},
            params={"user": USER},
            timeout=15,
        )
        response.raise_for_status()
        walls.append((time.perf_counter() - started) * 1000)
        response_bytes += len(response.content)
        last_payload = response.json()
    server_cpu = isolated.server_cpu(process) - server_before
    postgres_cpu = isolated.postgres_cpu() - postgres_before
    return {
        "requests": count,
        "wall_mean_ms": round(statistics.mean(walls), 3),
        "wall_p95_ms": round(sorted(walls)[min(len(walls) - 1, int(len(walls) * 0.95))], 3),
        "server_cpu_total_ms": round(server_cpu, 3),
        "server_cpu_per_request_ms": round(server_cpu / count, 3),
        "postgres_cpu_total_ms": round(postgres_cpu, 3),
        "response_bytes_mean": round(response_bytes / count, 1),
        "last_payload": last_payload,
    }


def main() -> int:
    configure()
    if any(c.laddr and c.laddr.port == isolated.HTTP_PORT and c.status == psutil.CONN_LISTEN for c in psutil.net_connections(kind="tcp")):
        raise RuntimeError("port 18877 is already in use")
    shutil.rmtree(RUN_ROOT, ignore_errors=True)
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    server = None
    try:
        isolated.copy_lesson()
        isolated.start_postgres()
        dump_path = isolated.sync_production_database_snapshot()
        provision_users()
        server = isolated.start_server()
        health = isolated.wait_health(server)
        user_token = login(USER)
        admin_token = login(ADMIN)
        own = request(user_token, {"action": "create_folder", "destination": USER, "name": "My Folder"})
        admin = request(admin_token, {"action": "create_folder", "destination": USER, "target_user": USER, "name": "Admin Folder"})
        duplicate = request(user_token, {"action": "create_folder", "destination": USER, "name": "My Folder"})
        denied = request(user_token, {"action": "create_folder", "destination": ADMIN, "target_user": ADMIN, "name": "Blocked"})
        copied = request(user_token, {"action": "copy_link", "source": isolated.LESSON_PATH, "destination": USER})
        copied_path = ((copied.get("payload") or {}).get("result") or {}).get("path", "")
        renamed = request(user_token, {"action": "rename", "source": copied_path, "name": "Renamed Lesson.Space_V"})
        renamed_path = ((renamed.get("payload") or {}).get("result") or {}).get("path", "")
        moved = request(user_token, {"action": "move", "source": renamed_path, "destination": f"{USER}/My Folder"})
        moved_path = ((moved.get("payload") or {}).get("result") or {}).get("path", "")
        cloned_folder = request(user_token, {"action": "copy_link", "source": f"{USER}/My Folder", "destination": USER, "name": "Cloned Folder"})
        cloned_path = ((cloned_folder.get("payload") or {}).get("result") or {}).get("path", "")
        reordered = request(user_token, {"action": "reorder", "source": cloned_path, "direction": "up"})
        deleted_file = request(user_token, {"action": "delete_link", "source": moved_path})
        deleted_folder = request(user_token, {"action": "delete_link", "source": cloned_path})
        benchmark = benchmark_creates(user_token)
        revision_benchmark = benchmark_revision_reads(user_token)
        before_restart = postgres_state()
        sqlite_created = (isolated.SERVER_DATA_ROOT / "server2.db").exists()
        isolated.stop_server(server)
        server = isolated.start_server()
        isolated.wait_health(server)
        token_after = login(USER)
        folders_response = requests.get(
            f"{isolated.BASE}/server-data/vault-folders",
            headers={"Authorization": f"Bearer {token_after}"},
            timeout=30,
        )
        after_restart = postgres_state()
        listed_names = [row.get("display_name") for row in folders_response.json().get("folders", [])]
        evidence = {
            "database_sync": {
                "enabled": True,
                "source": "127.0.0.1:5432/future_server2",
                "method": "fresh pg_dump + pg_restore before run",
                "dump_bytes": dump_path.stat().st_size,
            },
            "resources": {"http_port": 18877, "postgres_port": 55432, "database": isolated.TEST_DATABASE},
            "health": {"pid": health.get("pid"), "ready": health.get("ready"), "warm_ready": health.get("warm_ready")},
            "requests": {
                "user_create": own,
                "admin_create": admin,
                "duplicate_name": duplicate,
                "cross_user_denied": denied,
                "copy_file": copied,
                "rename": renamed,
                "move": moved,
                "copy_folder": cloned_folder,
                "reorder": reordered,
                "delete_file": deleted_file,
                "delete_folder": deleted_folder,
            },
            "benchmark": benchmark,
            "realtime_revision": revision_benchmark,
            "durability": {
                "sqlite_database_created": sqlite_created,
                "before_restart": before_restart,
                "after_restart": after_restart,
                "folder_list_status": folders_response.status_code,
                "folder_list_names": listed_names,
            },
        }
        gates = {
            "database_sync": evidence["database_sync"]["enabled"],
            "user_create": own["status"] == 200 and own["payload"].get("ok"),
            "admin_create": admin["status"] == 200 and admin["payload"].get("ok"),
            "cross_user_denied": denied["status"] in {400, 403},
            "unique_retry_name": "My Folder - link 2" in before_restart["names"],
            "postgres_only": not sqlite_created,
            "restart_persistence": before_restart == after_restart and {"My Folder", "Admin Folder", "My Folder - link 2"}.issubset(set(listed_names)),
            "all_mutations": all(
                row["status"] == 200 and row["payload"].get("ok")
                for row in (copied, renamed, moved, cloned_folder, reordered, deleted_file, deleted_folder)
            ),
            "deleted_not_restored": "Cloned Folder" not in listed_names and "Renamed Lesson.Space_V" not in listed_names,
            "revision_endpoint": revision_benchmark["last_payload"].get("vault_revision") == before_restart["revision"],
        }
        evidence["gates"] = gates
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(evidence, ensure_ascii=False, indent=2))
        return 0 if all(gates.values()) else 1
    finally:
        isolated.stop_server(server)
        isolated.stop_postgres()
        shutil.rmtree(RUN_ROOT, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
