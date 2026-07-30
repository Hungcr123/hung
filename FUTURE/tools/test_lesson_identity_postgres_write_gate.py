#!/usr/bin/env python3
"""Process/runtime gate for PostgreSQL lesson identity registration writes."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import concurrent.futures
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app  # noqa: E402

PREFIX = "codexpgidentity"
PATH_A = f"common/{PREFIX}/alpha.Space_V"
PATH_B = f"common/{PREFIX}/beta.Space_V"
PATH_C = f"common/{PREFIX}/collision.Space_V"
PATH_SIDE = f"common/{PREFIX}/side-effect.Space_V"
FILE_A = "ftg-lesson-codexpgidentity-alpha"
FILE_B = "ftg-lesson-codexpgidentity-beta"
FILE_SIDE = "ftg-lesson-codexpgidentity-side"
USER_SIDE = "codexpgidentityuser"

def cleanup_postgres() -> dict:
    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.lesson_progress WHERE username LIKE %s OR path LIKE %s OR file_id LIKE %s", (f"{PREFIX}%", f"%{PREFIX}%", f"%{PREFIX}%"))
            progress = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.lesson_progress_namespaces WHERE username LIKE %s", (f"{PREFIX}%",))
            progress_namespaces = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.vault_entries WHERE username LIKE %s OR source_path LIKE %s OR lesson_id LIKE %s", (f"{PREFIX}%", f"%{PREFIX}%", f"%{PREFIX}%"))
            vault_entries = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.vault_folders WHERE username LIKE %s OR source_path LIKE %s", (f"{PREFIX}%", f"%{PREFIX}%"))
            vault_folders = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.vault_revisions WHERE username LIKE %s", (f"{PREFIX}%",))
            vault_revisions = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.lesson_file_aliases WHERE normalized_path LIKE %s", (f"%{PREFIX}%",))
            aliases = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.lesson_file_replicas WHERE normalized_path LIKE %s", (f"%{PREFIX}%",))
            replicas = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.lesson_files WHERE file_id LIKE %s", (f"%{PREFIX}%",))
            files = int(cursor.rowcount or 0)
        return {
            "files": files, "replicas": replicas, "aliases": aliases,
            "progress": progress, "progress_namespaces": progress_namespaces,
            "vault_entries": vault_entries, "vault_folders": vault_folders, "vault_revisions": vault_revisions,
        }

    return app.postgres_execute(_write)

def cleanup_sqlite_count() -> int:
    connection = app.server_database_connect()
    try:
        return int(connection.execute(
            "SELECT COUNT(*) FROM lesson_file_aliases WHERE lower(normalized_path) LIKE ?",
            (f"%{PREFIX}%",),
        ).fetchone()[0] or 0)
    finally:
        connection.close()

def pg_counts() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM future_server2.lesson_files WHERE file_id LIKE %s", (f"%{PREFIX}%",))
            files = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT COUNT(*) FROM future_server2.lesson_file_replicas WHERE normalized_path LIKE %s", (f"%{PREFIX}%",))
            replicas = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT COUNT(*) FROM future_server2.lesson_file_aliases WHERE normalized_path LIKE %s", (f"%{PREFIX}%",))
            aliases = int(cursor.fetchone()[0] or 0)
        return {"files": files, "replicas": replicas, "aliases": aliases}

    return app.postgres_execute(_read)

def pg_alias(path: str) -> dict:
    key = app.clean_path_value(path).lower()

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT file_id,active FROM future_server2.lesson_file_aliases WHERE normalized_path=%s",
                (key,),
            )
            row = cursor.fetchone()
        return {"file_id": app.clean(row[0]) if row else "", "active": bool(row[1]) if row else False}

    return app.postgres_execute(_read)

def restart_postgres_service() -> dict:
    before = time.perf_counter()
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Restart-Service postgresql-x64-17 -Force"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=90,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"PostgreSQL restart failed: {completed.stderr[-500:] or completed.stdout[-500:]}")
    app.POSTGRES_ADAPTER_POOL.clear()
    app.postgres_initialize_schema()
    elapsed = (time.perf_counter() - before) * 1000
    return {"ok": True, "elapsed_ms": round(elapsed, 3)}

def entry(file_id: str, path: str, fingerprint: str, size: int = 100) -> dict:
    return {
        "lesson_id": file_id,
        "path": path,
        "content_fingerprint": fingerprint,
        "modified_ns": int(time.time_ns()),
        "size": size,
        "space": "Space_V",
    }

def seed_side_effect_rows() -> dict:
    now = app.utc_timestamp()
    now_epoch = app.timestamp_to_epoch(now)
    legacy_record = {
        "key": "legacy-side",
        "path": PATH_SIDE,
        "nodeIndex": 3,
        "nodeCount": 9,
        "updatedAt": now,
        "_serverRevision": 2,
    }

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.lesson_progress
                    (username,space,progress_key,path,identity,file_id,node_index,node_count,learned_count,complete,server_revision,updated_at_utc,updated_epoch,record_json,migrated_at_utc,source_sha256)
                VALUES (%s,'Space_V','legacy-side',%s,'','',3,9,0,false,2,%s,%s,%s::jsonb,%s,'side-test')
                """,
                (USER_SIDE, PATH_SIDE.lower(), now, now_epoch, json.dumps(legacy_record, separators=(",", ":")), now),
            )
            cursor.execute(
                """
                INSERT INTO future_server2.lesson_progress_namespaces(username,space,updated_at_utc,updated_epoch)
                VALUES (%s,'Space_V',%s,%s)
                ON CONFLICT(username,space) DO UPDATE SET updated_at_utc=excluded.updated_at_utc,updated_epoch=excluded.updated_epoch
                """,
                (USER_SIDE, now, now_epoch),
            )
            cursor.execute(
                """
                INSERT INTO future_server2.vault_folders
                    (vault_folder_id,username,parent_folder_id,display_name,folder_type,source_path,sort_order,status,created_at_utc,created_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES ('codexpgidentity-folder',%s,'','Codex Identity','VIRTUAL',%s,0,'active',%s,%s,%s,%s,%s,'side-test')
                """,
                (USER_SIDE, f"common/{PREFIX}".lower(), now, now_epoch, now, now_epoch, now),
            )
            cursor.execute(
                """
                INSERT INTO future_server2.vault_entries
                    (vault_entry_id,username,parent_folder_id,lesson_id,entry_type,physical_replica_id,source_entry_id,source_path,display_name,sort_order,status,created_at_utc,created_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES ('codexpgidentity-entry',%s,'codexpgidentity-folder',%s,'COMMON_REFERENCE',NULL,NULL,%s,'Side Effect',0,'active',%s,%s,%s,%s,%s,'side-test')
                """,
                (USER_SIDE, FILE_SIDE, PATH_SIDE.lower(), now, now_epoch, now, now_epoch, now),
            )
            cursor.execute(
                """
                INSERT INTO future_server2.vault_revisions(username,revision,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,1,%s,%s,%s,'side-test')
                ON CONFLICT(username) DO UPDATE SET revision=1,updated_at_utc=excluded.updated_at_utc,updated_epoch=excluded.updated_epoch
                """,
                (USER_SIDE, now, now_epoch, now),
            )
        return {"ok": True}

    return app.postgres_execute(_write)

def read_side_effect_rows() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT file_id,path,node_index,node_count FROM future_server2.lesson_progress WHERE username=%s", (USER_SIDE,))
            progress = [tuple(row) for row in cursor.fetchall()]
            cursor.execute("SELECT entry_type,physical_replica_id,source_path FROM future_server2.vault_entries WHERE username=%s", (USER_SIDE,))
            vault = [tuple(row) for row in cursor.fetchall()]
            cursor.execute("SELECT revision FROM future_server2.vault_revisions WHERE username=%s", (USER_SIDE,))
            revision = cursor.fetchone()
        return {"progress": progress, "vault": vault, "revision": int(revision[0] or 0) if revision else 0}

    return app.postgres_execute(_read)

def concurrent_distinct(count: int) -> dict:
    users = range(1, count + 1)
    started = time.perf_counter()

    def one(index: int) -> tuple[bool, str]:
        file_id = f"ftg-lesson-{PREFIX}-distinct-{count}-{index:03d}"
        path = f"common/{PREFIX}/distinct-{count}-{index:03d}.Space_V"
        try:
            result = app.server_database_register_lesson_file_entries([
                entry(file_id, path, f"sha-distinct-{count}-{index}", 100 + index)
            ])
            if result.get("registered") != 1 or result.get("collisions") != 0:
                return False, json.dumps(result, ensure_ascii=False)
            if app.server_database_lesson_file_id_for_path(path) != file_id:
                return False, "read_after_write_mismatch"
            return True, ""
        except Exception as exc:
            return False, str(exc)

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, count)) as executor:
        rows = list(executor.map(one, users))
    errors = [error for ok, error in rows if not ok][:5]
    wall = (time.perf_counter() - started) * 1000
    return {
        "requests": count,
        "success": sum(1 for ok, _ in rows if ok),
        "errors": len(errors),
        "sample_errors": errors,
        "wall_ms": round(wall, 3),
        "throughput_rps": round((count / wall) * 1000, 3) if wall else 0,
    }

def concurrent_same_alias(count: int) -> dict:
    file_id = f"ftg-lesson-{PREFIX}-same-{count}"
    path = f"common/{PREFIX}/same-{count}.Space_V"
    started = time.perf_counter()

    def one(index: int) -> tuple[bool, str]:
        try:
            result = app.server_database_register_lesson_file_entries([
                entry(file_id, path, "sha-same", 200 + index)
            ])
            if result.get("registered") != 1 or result.get("collisions") != 0:
                return False, json.dumps(result, ensure_ascii=False)
            return True, ""
        except Exception as exc:
            return False, str(exc)

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, count)) as executor:
        rows = list(executor.map(one, range(1, count + 1)))
    errors = [error for ok, error in rows if not ok][:5]
    wall = (time.perf_counter() - started) * 1000
    final_id = app.server_database_lesson_file_id_for_path(path)
    return {
        "requests": count,
        "success": sum(1 for ok, _ in rows if ok),
        "errors": len(errors),
        "sample_errors": errors,
        "final_id_ok": final_id == file_id,
        "wall_ms": round(wall, 3),
        "throughput_rps": round((count / wall) * 1000, 3) if wall else 0,
    }

def main() -> int:
    os.environ["FUTURE_DB_LESSON_IDENTITY_BACKEND"] = "postgres"
    os.environ["FUTURE_DB_LESSON_PROGRESS_BACKEND"] = "postgres"
    os.environ["FUTURE_DB_VAULT_METADATA_BACKEND"] = "postgres"
    app.postgres_initialize_schema()
    cleanup = {"postgres_before": cleanup_postgres(), "sqlite_before": cleanup_sqlite_count()}
    try:
        first = app.server_database_register_lesson_file_entries([entry(FILE_A, PATH_A, "sha-alpha", 111)])
        if first.get("registered") != 1 or first.get("collisions") != 0:
            raise RuntimeError(f"first register failed: {first}")
        read_a = app.server_database_lesson_file_id_for_path(PATH_A)
        current_a = app.server_database_lesson_current_path(FILE_A)
        if read_a != FILE_A or app.clean_path_value(current_a).lower() != PATH_A.lower():
            raise RuntimeError(f"read after write failed: {read_a} {current_a}")
        retry = app.server_database_register_lesson_file_entries([entry(FILE_A, PATH_A, "sha-alpha", 111)])
        if retry.get("registered") != 1 or retry.get("collisions") != 0:
            raise RuntimeError(f"retry failed: {retry}")
        updated = app.server_database_register_lesson_file_entries([entry(FILE_A, PATH_A, "sha-alpha-2", 222)])
        if updated.get("registered") != 1:
            raise RuntimeError(f"update failed: {updated}")
        second = app.server_database_register_lesson_file_entries([entry(FILE_B, PATH_B, "sha-beta", 333)])
        if second.get("registered") != 1:
            raise RuntimeError(f"second register failed: {second}")
        collision = app.server_database_register_lesson_file_entries([entry(FILE_A, PATH_C, "sha-collision", 444)])
        alias_c = pg_alias(PATH_C)
        if collision.get("collisions") != 1 or alias_c.get("active"):
            raise RuntimeError(f"collision semantics failed: {collision} {alias_c}")
        inactive = app.server_database_mark_lesson_file_paths_inactive([PATH_A])
        if inactive < 1:
            raise RuntimeError(f"inactive failed: {inactive}")
        app.SERVER_DATABASE_LESSON_FILE_ALIAS_CACHE.pop(PATH_A.lower(), None)
        if app.server_database_lesson_file_id_for_path(PATH_A):
            raise RuntimeError("inactive alias still resolved")
        distinct = [concurrent_distinct(size) for size in (10, 50, 100)]
        same_alias = [concurrent_same_alias(size) for size in (10, 50, 100)]
        for row in distinct + same_alias:
            if row.get("success") != row.get("requests") or row.get("errors") or row.get("final_id_ok") is False:
                raise RuntimeError(f"concurrency failed: {row}")
        seed_side_effect = seed_side_effect_rows()
        side_effect = app.server_database_register_lesson_file_entries([entry(FILE_SIDE, PATH_SIDE, "sha-side", 888)])
        if side_effect.get("reattached_progress") != 1 or side_effect.get("rebound_vault_entries") != 1:
            raise RuntimeError(f"side-effect result failed: {side_effect}")
        side_rows = read_side_effect_rows()
        progress_rows = side_rows.get("progress") or []
        vault_rows = side_rows.get("vault") or []
        if len(progress_rows) != 1 or progress_rows[0][0] != FILE_SIDE or progress_rows[0][2] != 3:
            raise RuntimeError(f"progress reattach failed: {side_rows}")
        if len(vault_rows) != 1 or vault_rows[0][0] != "PHYSICAL_REPLICA" or not vault_rows[0][1]:
            raise RuntimeError(f"vault rebind failed: {side_rows}")
        restart_path = f"common/{PREFIX}/restart.Space_V"
        restart_file = f"ftg-lesson-{PREFIX}-restart"
        restart_write = app.server_database_register_lesson_file_entries([
            entry(restart_file, restart_path, "sha-restart", 777)
        ])
        if restart_write.get("registered") != 1:
            raise RuntimeError(f"restart fixture write failed: {restart_write}")
        restart = restart_postgres_service()
        app.SERVER_DATABASE_LESSON_FILE_ALIAS_CACHE.pop(restart_path.lower(), None)
        restart_read = app.server_database_lesson_file_id_for_path(restart_path)
        restart_current = app.server_database_lesson_current_path(restart_file)
        if restart_read != restart_file or app.clean_path_value(restart_current).lower() != restart_path.lower():
            raise RuntimeError(f"restart readback failed: {restart_read} {restart_current}")
        cleanup["postgres_after"] = cleanup_postgres()
        cleanup["sqlite_after"] = cleanup_sqlite_count()
        final_counts = pg_counts()
        if any(final_counts.values()) or cleanup["sqlite_after"]:
            raise RuntimeError(f"cleanup failed: pg={final_counts} sqlite={cleanup['sqlite_after']}")
        result = {
            "ok": True,
            "first": first,
            "retry": retry,
            "updated": updated,
            "second": second,
            "collision": collision,
            "inactive": inactive,
            "distinct_concurrency": distinct,
            "same_alias_concurrency": same_alias,
            "seed_side_effect": seed_side_effect,
            "side_effect": side_effect,
            "side_effect_rows": side_rows,
            "restart": restart,
            "restart_readback": {
                "file_id": restart_read,
                "current_path": restart_current,
            },
            "cleanup": cleanup,
            "final_counts": final_counts,
            "production_flag": os.environ.get("FUTURE_DB_LESSON_IDENTITY_BACKEND", "off"),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    finally:
        cleanup_postgres()
        os.environ.pop("FUTURE_DB_LESSON_IDENTITY_BACKEND", None)
        os.environ.pop("FUTURE_DB_LESSON_PROGRESS_BACKEND", None)
        os.environ.pop("FUTURE_DB_VAULT_METADATA_BACKEND", None)

if __name__ == "__main__":
    raise SystemExit(main())
