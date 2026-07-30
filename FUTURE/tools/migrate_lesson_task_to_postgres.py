#!/usr/bin/env python3
"""Migrate Lesson Task state rows to PostgreSQL."""

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

def _loads(text: object) -> dict:
    try:
        value = json.loads(text or "{}")
    except Exception:
        value = {}
    return value if isinstance(value, dict) else {}

def sqlite_rows() -> list[dict]:
    con = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        return [
            {
                "username": app.normalize_username(row["username"]),
                "record": _loads(row["record_json"]),
                "server_revision": int(row["server_revision"] or 0),
                "updated_at_utc": app.clean(row["updated_at_utc"]),
            }
            for row in con.execute(
                "SELECT username,record_json,server_revision,updated_at_utc FROM lesson_task_state ORDER BY lower(username)"
            )
        ]
    finally:
        con.close()

def postgres_rows() -> list[dict]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT username,record_json,server_revision,updated_at_utc FROM future_server2.lesson_task_state ORDER BY lower(username)"
            )
            return [
                {
                    "username": app.normalize_username(row[0]),
                    "record": dict(row[1]) if isinstance(row[1], dict) else {},
                    "server_revision": int(row[2] or 0),
                    "updated_at_utc": app.clean(row[3]),
                }
                for row in cursor.fetchall()
            ]

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
            cursor.execute("DELETE FROM future_server2.lesson_task_state WHERE lower(username) LIKE 'codexpg%'")
            deleted = int(cursor.rowcount or 0)
            cursor.execute("SELECT count(*) FROM future_server2.lesson_task_state")
            remaining = int(cursor.fetchone()[0] or 0)
        return {"deleted": deleted, "remaining": remaining}

    return app.postgres_execute(_cleanup)

def round_trip() -> dict:
    username = "codexpglessontask"
    first = app.postgres_write_lesson_task_record(username, {"tasks": [{"path": "common/File 01.Space_V", "file_id": "ftg-lesson-codexpg"}]})
    retry = app.postgres_write_lesson_task_record(username, {"tasks": [{"path": "common/File 01.Space_V", "file_id": "ftg-lesson-codexpg"}]})
    loaded = app.postgres_load_lesson_task_record(username)
    deleted = app.postgres_delete_lesson_task_record(username)
    return {
        "first_changed": bool(first.get("changed")),
        "retry_unchanged": retry.get("changed") is False,
        "loaded_revision": int(loaded.get("revision") or 0),
        "deleted": bool(deleted),
        "ok": bool(first.get("changed")) and retry.get("changed") is False and int(loaded.get("revision") or 0) >= 1 and bool(deleted),
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--cleanup-test-rows", action="store_true")
    args = parser.parse_args()
    sqlite = sqlite_rows()
    if args.dry_run and not os.environ.get("FUTURE_PG_DSN"):
        result = {
            "sqlite_rows": len(sqlite),
            "sqlite_fingerprint": fingerprint(sqlite),
            "dry_run": True,
            "postgres_pending": "FUTURE_PG_DSN is not set",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating Lesson Task to PostgreSQL.")
    app.postgres_initialize_schema()
    cleanup = cleanup_test_rows()
    rt = None
    result = {"parity": False, "round_trip": None, "cleanup": cleanup}
    try:
        if not args.verify_only and not args.dry_run:
            for row in sqlite:
                app.postgres_upsert_lesson_task_state_row(row)
        pg_all = postgres_rows()
        sqlite_users = {row["username"] for row in sqlite}
        pg_subset = [row for row in pg_all if row["username"] in sqlite_users]
        sqlite_fp = fingerprint(sqlite)
        pg_fp = fingerprint(pg_subset)
        rt = None if args.verify_only or args.dry_run else round_trip()
        result = {
            "sqlite_rows": len(sqlite),
            "postgres_total": len(pg_all),
            "postgres_matching_sqlite": len(pg_subset),
            "sqlite_fingerprint": sqlite_fp,
            "postgres_fingerprint": pg_fp,
            "parity": sqlite_fp == pg_fp and len(sqlite) == len(pg_subset),
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
