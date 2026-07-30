#!/usr/bin/env python3
"""Migrate canonical lesson_progress rows to PostgreSQL.

This first gameplay slice copies only rows with canonical ftg-lesson file_id.
Legacy path-only rows are counted and left pending; production remains SQLite
unless FUTURE_DB_LESSON_PROGRESS_BACKEND=postgres is set for a process.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app  # noqa: E402

DATABASE = Path(r"C:\server data\server2.db")


def sqlite_rows() -> list[dict]:
    connection = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True, timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        rows: list[dict] = []
        for row in connection.execute(
            """
            SELECT username,space,progress_key,path,identity,file_id,node_index,node_count,
                   learned_count,complete,server_revision,updated_at_utc,record_json
            FROM lesson_progress
            WHERE lower(file_id) LIKE 'ftg-lesson-%'
            ORDER BY lower(username),lower(file_id)
            """
        ):
            try:
                record = json.loads(row["record_json"] or "{}")
            except Exception:
                record = {}
            rows.append({
                "username": app.normalize_username(row["username"]),
                "space": app.normalize_space_progress_space(row["space"]),
                "progress_key": app.clean(row["progress_key"]),
                "path": app.clean(row["path"]),
                "identity": app.clean(row["identity"]),
                "file_id": app.clean(row["file_id"]),
                "node_index": max(0, app.space_w_int(row["node_index"], 0)),
                "node_count": max(0, app.space_w_int(row["node_count"], 0)),
                "learned_count": max(0, app.space_w_int(row["learned_count"], 0)),
                "complete": bool(int(row["complete"] or 0)),
                "server_revision": max(0, app.space_w_int(row["server_revision"], 0)),
                "updated_at": app.clean(row["updated_at_utc"]),
                "updated_epoch": app.timestamp_to_epoch(row["updated_at_utc"]),
                "record": record if isinstance(record, dict) else {},
            })
        return rows
    finally:
        connection.close()


def sqlite_counts() -> dict:
    connection = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True, timeout=30)
    try:
        return {
            "total": int(connection.execute("SELECT count(*) FROM lesson_progress").fetchone()[0] or 0),
            "canonical": int(connection.execute("SELECT count(*) FROM lesson_progress WHERE lower(file_id) LIKE 'ftg-lesson-%'").fetchone()[0] or 0),
            "legacy_path_pending": int(connection.execute("SELECT count(*) FROM lesson_progress WHERE coalesce(file_id,'')=''").fetchone()[0] or 0),
        }
    finally:
        connection.close()


def canonical_payload(row: dict) -> dict:
    record = row.get("record") if isinstance(row.get("record"), dict) else {}
    return {
        "username": row["username"].lower(),
        "space": row["space"],
        "progress_key": row["progress_key"],
        "file_id": row["file_id"],
        "path": row["path"],
        "identity": row["identity"],
        "node_index": int(row["node_index"]),
        "node_count": int(row["node_count"]),
        "learned_count": int(row["learned_count"]),
        "complete": bool(row["complete"]),
        "server_revision": int(row["server_revision"]),
        "updated_at": app.clean(row["updated_at"]),
        "updated_epoch": float(row.get("updated_epoch", 0) or 0),
        "record": record,
    }


def fingerprint(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: (item["username"].lower(), item["file_id"].lower())):
        digest.update(json.dumps(canonical_payload(row), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def postgres_rows() -> list[dict]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT username,space,progress_key,path,identity,file_id,node_index,node_count,
                       learned_count,complete,server_revision,updated_at_utc,updated_epoch,record_json
                FROM future_server2.lesson_progress
                ORDER BY lower(username),lower(file_id)
                """
            )
            rows = []
            for row in cursor.fetchall():
                rows.append({
                    "username": app.normalize_username(row[0]),
                    "space": app.normalize_space_progress_space(row[1]),
                    "progress_key": app.clean(row[2]),
                    "path": app.clean(row[3]),
                    "identity": app.clean(row[4]),
                    "file_id": app.clean(row[5]),
                    "node_index": max(0, app.space_w_int(row[6], 0)),
                    "node_count": max(0, app.space_w_int(row[7], 0)),
                    "learned_count": max(0, app.space_w_int(row[8], 0)),
                    "complete": bool(row[9]),
                    "server_revision": max(0, app.space_w_int(row[10], 0)),
                    "updated_at": app.clean(row[11]),
                    "updated_epoch": max(0.0, float(row[12] or 0)),
                    "record": dict(row[13]) if isinstance(row[13], dict) else {},
                })
            return rows

    return app.postgres_execute(_read)


def shadow_read_check(sqlite_source_rows: list[dict], pg_source_rows: list[dict]) -> dict:
    sqlite_by_key = {(row["username"].lower(), row["file_id"].lower()): row for row in sqlite_source_rows}
    pg_by_key = {(row["username"].lower(), row["file_id"].lower()): row for row in pg_source_rows}
    missing = [key for key in sqlite_by_key if key not in pg_by_key]
    mismatches = []
    for key, sqlite_row in sqlite_by_key.items():
        pg_row = pg_by_key.get(key)
        if pg_row and fingerprint([sqlite_row]) != fingerprint([pg_row]):
            mismatches.append({"username": key[0], "file_id": key[1]})
    quynh_keys = [key for key in sqlite_by_key if key[0] == "quynh"]
    quynh_equal = all(key in pg_by_key and fingerprint([sqlite_by_key[key]]) == fingerprint([pg_by_key[key]]) for key in quynh_keys)
    return {
        "sqlite_canonical_keys": len(sqlite_by_key),
        "postgres_keys": len(pg_by_key),
        "missing_count": len(missing),
        "missing_sample": [{"username": key[0], "file_id": key[1]} for key in missing[:10]],
        "mismatch_count": len(mismatches),
        "mismatch_sample": mismatches[:10],
        "quynh_rows": len(quynh_keys),
        "quynh_equal": bool(quynh_keys and quynh_equal),
        "ok": not missing and not mismatches,
    }


def test_backend_round_trip(username: str) -> dict:
    os.environ["FUTURE_DB_LESSON_PROGRESS_BACKEND"] = "postgres"
    marker = app.utc_timestamp()
    lesson_id = "ftg-lesson-codex-progress-slice"
    key = "codex-progress-slice-key"
    record = {
        "lesson_id": lesson_id,
        "file_id": lesson_id,
        "identity": lesson_id,
        "path": "common/File 02 - {7}.Space_V",
        "nodeIndex": 2,
        "nodeCount": 10,
        "learnedCount": 2,
        "updatedAt": marker,
        "_serverRevision": 3,
        "activeRun": True,
        "runId": "codex-progress-run",
    }
    written = app.server_database_apply_progress_entry("Space_V", username, {"op": "upsert", "key": key, "record": record})
    loaded = app.server_database_load_progress_payload("Space_V", username)
    states = loaded.get("states") if isinstance(loaded, dict) and isinstance(loaded.get("states"), dict) else {}
    loaded_record = states.get(key) if isinstance(states.get(key), dict) else {}
    stale = dict(record)
    stale["_serverRevision"] = 1
    stale["nodeIndex"] = 9
    app.server_database_apply_progress_entry("Space_V", username, {"op": "upsert", "key": key, "record": stale})
    after_stale = app.server_database_load_progress_payload("Space_V", username)
    after_record = ((after_stale.get("states") or {}).get(key) if isinstance(after_stale, dict) else {}) or {}
    removed = app.server_database_apply_progress_entry("Space_V", username, {"op": "remove", "key": key, "file_id": lesson_id})
    after_remove = app.server_database_load_progress_payload("Space_V", username)
    remove_states = after_remove.get("states") if isinstance(after_remove, dict) and isinstance(after_remove.get("states"), dict) else {}
    return {
        "username": username,
        "backend_mode": app.postgres_backend_mode("LESSON_PROGRESS"),
        "written_ok": bool(written.get("ok")),
        "loaded_node_index": app.space_w_int(loaded_record.get("nodeIndex"), -1),
        "stale_node_index_after_retry": app.space_w_int(after_record.get("nodeIndex"), -1),
        "removed_ok": bool(removed.get("ok")),
        "present_after_remove": key in remove_states,
        "ok": bool(written.get("ok")) and app.space_w_int(loaded_record.get("nodeIndex"), -1) == 2 and app.space_w_int(after_record.get("nodeIndex"), -1) == 2 and key not in remove_states,
    }


def test_retry_same_payload(username: str) -> dict:
    os.environ["FUTURE_DB_LESSON_PROGRESS_BACKEND"] = "postgres"
    marker = app.utc_timestamp()
    lesson_id = "ftg-lesson-codex-progress-retry"
    key = "codex-progress-retry-key"
    record = {
        "lesson_id": lesson_id,
        "file_id": lesson_id,
        "identity": lesson_id,
        "path": "common/File 02 - {7}.Space_V",
        "nodeIndex": 4,
        "nodeCount": 10,
        "learnedCount": 4,
        "updatedAt": marker,
        "_serverRevision": 7,
        "activeRun": True,
        "runId": "codex-progress-retry-run",
    }
    first = app.server_database_apply_progress_entry("Space_V", username, {"op": "upsert", "key": key, "record": record})
    second = app.server_database_apply_progress_entry("Space_V", username, {"op": "upsert", "key": key, "record": record})
    loaded = app.server_database_load_progress_payload("Space_V", username)
    states = loaded.get("states") if isinstance(loaded, dict) and isinstance(loaded.get("states"), dict) else {}
    record_after = states.get(key) if isinstance(states.get(key), dict) else {}
    return {
        "username": username,
        "first_ok": bool(first.get("ok")),
        "second_ok": bool(second.get("ok")),
        "loaded_node_index": app.space_w_int(record_after.get("nodeIndex"), -1),
        "loaded_revision": app.space_w_int(record_after.get("_serverRevision"), -1),
        "ok": bool(first.get("ok")) and bool(second.get("ok")) and app.space_w_int(record_after.get("nodeIndex"), -1) == 4 and app.space_w_int(record_after.get("_serverRevision"), -1) == 7,
    }


def test_concurrent_writes(prefix: str, users: int = 12) -> dict:
    os.environ["FUTURE_DB_LESSON_PROGRESS_BACKEND"] = "postgres"
    usernames = [f"{prefix}{index:03d}" for index in range(1, users + 1)]

    def _write(index_username: tuple[int, str]) -> dict:
        index, username = index_username
        marker = app.utc_timestamp()
        lesson_id = f"ftg-lesson-codex-progress-concurrent-{index:03d}"
        key = f"codex-progress-concurrent-key-{index:03d}"
        record = {
            "lesson_id": lesson_id,
            "file_id": lesson_id,
            "identity": lesson_id,
            "path": "common/File 02 - {7}.Space_V",
            "nodeIndex": index,
            "nodeCount": 20,
            "learnedCount": index,
            "updatedAt": marker,
            "_serverRevision": index,
            "activeRun": True,
            "runId": f"codex-progress-concurrent-run-{index:03d}",
        }
        app.server_database_apply_progress_entry("Space_V", username, {"op": "upsert", "key": key, "record": record})
        loaded = app.server_database_load_progress_payload("Space_V", username)
        states = loaded.get("states") if isinstance(loaded, dict) and isinstance(loaded.get("states"), dict) else {}
        loaded_record = states.get(key) if isinstance(states.get(key), dict) else {}
        return {
            "username": username,
            "file_id": lesson_id,
            "loaded_node_index": app.space_w_int(loaded_record.get("nodeIndex"), -1),
            "loaded_lesson_id": app.clean(loaded_record.get("lesson_id") or loaded_record.get("file_id")),
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(12, users)) as executor:
        results = list(executor.map(_write, enumerate(usernames, start=1)))
    errors = [
        row for index, row in enumerate(results, start=1)
        if row.get("loaded_node_index") != index or row.get("loaded_lesson_id") != row.get("file_id")
    ]
    return {
        "users": users,
        "ok_count": users - len(errors),
        "error_count": len(errors),
        "error_sample": errors[:5],
        "ok": not errors,
    }


def cleanup_test_rows() -> dict:
    def _cleanup(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM future_server2.lesson_progress WHERE lower(username) LIKE 'codexpg%' OR lower(file_id) LIKE 'ftg-lesson-codex-progress-%'"
            )
            progress_deleted = int(cursor.rowcount or 0)
            cursor.execute(
                "DELETE FROM future_server2.lesson_progress_namespaces WHERE lower(username) LIKE 'codexpg%'"
            )
            namespace_deleted = int(cursor.rowcount or 0)
            cursor.execute("SELECT count(*) FROM future_server2.lesson_progress")
            remaining = int(cursor.fetchone()[0] or 0)
        return {"progress_deleted": progress_deleted, "namespace_deleted": namespace_deleted, "remaining_progress_rows": remaining}

    return app.postgres_execute(_cleanup)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--exercise-gates", action="store_true")
    parser.add_argument("--cleanup-test-rows", action="store_true")
    parser.add_argument("--round-trip-user", default="codexpgprogress")
    args = parser.parse_args()
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating lesson_progress to PostgreSQL.")
    app.postgres_initialize_schema()
    cleanup = cleanup_test_rows() if args.cleanup_test_rows else None
    rows = sqlite_rows()
    if not args.verify_only and not args.dry_run:
        for row in rows:
            app.postgres_upsert_lesson_progress_row(row)
    pg_rows_all = postgres_rows()
    sqlite_keys = {(row["username"].lower(), row["file_id"].lower()) for row in rows}
    pg_subset = [row for row in pg_rows_all if (row["username"].lower(), row["file_id"].lower()) in sqlite_keys]
    sqlite_fp = fingerprint(rows)
    pg_fp = fingerprint(pg_subset)
    round_trip = None
    retry_same_payload = None
    concurrent_writes = None
    if not args.verify_only and not args.dry_run:
        round_trip = test_backend_round_trip(args.round_trip_user)
        if args.exercise_gates:
            retry_same_payload = test_retry_same_payload("codexpgprogressretry")
            concurrent_writes = test_concurrent_writes("codexpgprogress", 12)
    result = {
        "sqlite_counts": sqlite_counts(),
        "sqlite_canonical_rows": len(rows),
        "postgres_rows_total": len(pg_rows_all),
        "postgres_rows_matching_sqlite_canonical": len(pg_subset),
        "sqlite_fingerprint": sqlite_fp,
        "postgres_fingerprint_for_sqlite_canonical": pg_fp,
        "parity": sqlite_fp == pg_fp and len(rows) == len(pg_subset),
        "shadow_read": shadow_read_check(rows, pg_subset),
        "round_trip": round_trip,
        "retry_same_payload": retry_same_payload,
        "concurrent_writes": concurrent_writes,
        "cleanup": cleanup,
        "dry_run": args.dry_run,
        "verify_only": args.verify_only,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if (
        result["parity"]
        and result["shadow_read"].get("ok")
        and (round_trip is None or round_trip.get("ok"))
        and (retry_same_payload is None or retry_same_payload.get("ok"))
        and (concurrent_writes is None or concurrent_writes.get("ok"))
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
