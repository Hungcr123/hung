#!/usr/bin/env python3
"""Migrate lesson time rows to PostgreSQL."""

from __future__ import annotations

import argparse
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

def sqlite_payload() -> dict:
    con = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        time_rows = [dict(row) for row in con.execute(
            "SELECT username,lesson_key,file_id,path,title,space,seconds,ticks,updated_at_utc,updated_epoch "
            "FROM lesson_time ORDER BY lower(username), lesson_key"
        )]
        credit_rows = [dict(row) for row in con.execute(
            "SELECT username,lesson_key,file_id,session_id,last_sequence,last_seen_epoch,boot_id,lease_issued_epoch,"
            "offline_credited_seconds,updated_at_utc FROM lesson_time_credit_state ORDER BY lower(username), lesson_key"
        )]
        return {
            "lesson_time": [app.postgres_lesson_time_row_from_source(row) for row in time_rows],
            "lesson_time_credit_state": [app.postgres_lesson_time_credit_row_from_source(row) for row in credit_rows],
        }
    finally:
        con.close()

def postgres_payload() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT username,lesson_key,file_id,path,title,space,seconds,ticks,updated_at_utc,updated_epoch "
                "FROM future_server2.lesson_time ORDER BY lower(username), lesson_key"
            )
            time_rows = [
                app.postgres_lesson_time_row_from_source({
                    "username": row[0], "lesson_key": row[1], "file_id": row[2], "path": row[3], "title": row[4],
                    "space": row[5], "seconds": row[6], "ticks": row[7], "updated_at_utc": row[8], "updated_epoch": row[9],
                })
                for row in cursor.fetchall()
            ]
            cursor.execute(
                "SELECT username,lesson_key,file_id,session_id,last_sequence,last_seen_epoch,boot_id,lease_issued_epoch,"
                "offline_credited_seconds,updated_at_utc FROM future_server2.lesson_time_credit_state ORDER BY lower(username), lesson_key"
            )
            credit_rows = [
                app.postgres_lesson_time_credit_row_from_source({
                    "username": row[0], "lesson_key": row[1], "file_id": row[2], "session_id": row[3],
                    "last_sequence": row[4], "last_seen_epoch": row[5], "boot_id": row[6],
                    "lease_issued_epoch": row[7], "offline_credited_seconds": row[8], "updated_at_utc": row[9],
                })
                for row in cursor.fetchall()
            ]
            return {"lesson_time": time_rows, "lesson_time_credit_state": credit_rows}

    return app.postgres_execute(_read)

def fingerprint(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()

def cleanup_test_rows() -> dict:
    def _cleanup(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.lesson_time_credit_state WHERE lower(username) LIKE 'codexpg%'")
            deleted_credit = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.lesson_time WHERE lower(username) LIKE 'codexpg%'")
            deleted_time = int(cursor.rowcount or 0)
            cursor.execute("SELECT count(*) FROM future_server2.lesson_time")
            time_count = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT count(*) FROM future_server2.lesson_time_credit_state")
            credit_count = int(cursor.fetchone()[0] or 0)
        return {"deleted_time": deleted_time, "deleted_credit": deleted_credit, "lesson_time": time_count, "lesson_time_credit_state": credit_count}

    return app.postgres_execute(_cleanup)

def round_trip() -> dict:
    now = app.utc_timestamp()
    row = {
        "username": "codexpgtimeread",
        "lesson_key": "ftg-lesson-codexpg-time",
        "file_id": "ftg-lesson-codexpg-time",
        "path": "common/File 01.Space_V",
        "title": "Codex PG Time",
        "space": "Space_V",
        "seconds": 75,
        "ticks": 3,
        "updated_at_utc": now,
        "updated_epoch": app.timestamp_to_epoch(now),
    }
    write = app.postgres_upsert_lesson_time_row(row)
    retry = app.postgres_upsert_lesson_time_row(row)
    credit_row = {
        "username": "codexpgtimeread",
        "lesson_key": "ftg-lesson-codexpg-time",
        "file_id": "ftg-lesson-codexpg-time",
        "session_id": "codexpg-session",
        "last_sequence": 7,
        "last_seen_epoch": app.timestamp_to_epoch(now),
        "boot_id": "codexpg-boot",
        "lease_issued_epoch": app.timestamp_to_epoch(now),
        "offline_credited_seconds": 15,
        "updated_at_utc": now,
    }
    credit_write = app.postgres_upsert_lesson_time_credit_state_row(credit_row)
    credit_retry = app.postgres_upsert_lesson_time_credit_state_row(credit_row)
    loaded = app.postgres_load_lesson_time_payload("codexpgtimeread")
    state = loaded.get("states", {}).get("ftg-lesson-codexpg-time", {})
    return {
        "write_ok": bool(write.get("ok")),
        "retry_same_sha": write.get("source_sha256") == retry.get("source_sha256"),
        "credit_write_ok": bool(credit_write.get("ok")),
        "credit_retry_same_sha": credit_write.get("source_sha256") == credit_retry.get("source_sha256"),
        "loaded_seconds": state.get("seconds"),
        "ok": (
            bool(write.get("ok"))
            and write.get("source_sha256") == retry.get("source_sha256")
            and bool(credit_write.get("ok"))
            and credit_write.get("source_sha256") == credit_retry.get("source_sha256")
            and state.get("seconds") == 75
        ),
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--cleanup-test-rows", action="store_true")
    args = parser.parse_args()
    sqlite = sqlite_payload()
    if args.dry_run and not os.environ.get("FUTURE_PG_DSN"):
        result = {
            "sqlite_lesson_time": len(sqlite["lesson_time"]),
            "sqlite_lesson_time_credit_state": len(sqlite["lesson_time_credit_state"]),
            "lesson_time_fingerprint": fingerprint(sqlite["lesson_time"]),
            "lesson_time_credit_state_fingerprint": fingerprint(sqlite["lesson_time_credit_state"]),
            "dry_run": True,
            "postgres_pending": "FUTURE_PG_DSN is not set",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating lesson_time to PostgreSQL.")
    app.postgres_initialize_schema()
    cleanup = cleanup_test_rows() if args.cleanup_test_rows else None
    if args.cleanup_test_rows and not args.verify_only and not args.dry_run:
        result = {"cleanup": cleanup, "cleanup_only": True}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    rt = None
    result = {"parity": False, "round_trip": None, "cleanup": cleanup}
    try:
        if not args.verify_only and not args.dry_run:
            for row in sqlite["lesson_time"]:
                app.postgres_upsert_lesson_time_row(row)
            for row in sqlite["lesson_time_credit_state"]:
                app.postgres_upsert_lesson_time_credit_state_row(row)
        pg = postgres_payload()
        sqlite_time_keys = {(row["username"], row["lesson_key"]) for row in sqlite["lesson_time"]}
        sqlite_credit_keys = {(row["username"], row["lesson_key"]) for row in sqlite["lesson_time_credit_state"]}
        pg_time = [row for row in pg["lesson_time"] if (row["username"], row["lesson_key"]) in sqlite_time_keys]
        pg_credit = [row for row in pg["lesson_time_credit_state"] if (row["username"], row["lesson_key"]) in sqlite_credit_keys]
        time_fp = fingerprint(sqlite["lesson_time"])
        pg_time_fp = fingerprint(pg_time)
        credit_fp = fingerprint(sqlite["lesson_time_credit_state"])
        pg_credit_fp = fingerprint(pg_credit)
        rt = None if args.verify_only or args.dry_run else round_trip()
        result = {
            "sqlite_lesson_time": len(sqlite["lesson_time"]),
            "postgres_lesson_time_total": len(pg["lesson_time"]),
            "postgres_lesson_time_matching_sqlite": len(pg_time),
            "sqlite_lesson_time_credit_state": len(sqlite["lesson_time_credit_state"]),
            "postgres_lesson_time_credit_state_total": len(pg["lesson_time_credit_state"]),
            "postgres_lesson_time_credit_state_matching_sqlite": len(pg_credit),
            "lesson_time_fingerprint": time_fp,
            "postgres_lesson_time_fingerprint": pg_time_fp,
            "lesson_time_credit_state_fingerprint": credit_fp,
            "postgres_lesson_time_credit_state_fingerprint": pg_credit_fp,
            "parity": time_fp == pg_time_fp and credit_fp == pg_credit_fp and len(sqlite["lesson_time"]) == len(pg_time) and len(sqlite["lesson_time_credit_state"]) == len(pg_credit),
            "round_trip": rt,
            "cleanup": cleanup,
            "post_round_trip_cleanup": None,
            "dry_run": args.dry_run,
            "verify_only": args.verify_only,
        }
    finally:
        result["post_round_trip_cleanup"] = cleanup_test_rows()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["parity"] and (rt is None or rt.get("ok")) else 1

if __name__ == "__main__":
    raise SystemExit(main())
