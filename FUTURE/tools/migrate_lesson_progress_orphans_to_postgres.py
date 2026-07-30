#!/usr/bin/env python3
"""Migrate archived lesson_progress_orphans to PostgreSQL."""

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

def sqlite_rows() -> list[dict]:
    con = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        return [
            app.postgres_lesson_progress_orphan_row_from_source(dict(row))
            for row in con.execute(
                "SELECT id,username,space,progress_key,path,identity,server_revision,updated_at_utc,record_json,archived_at_utc,reason "
                "FROM lesson_progress_orphans ORDER BY id"
            )
        ]
    finally:
        con.close()

def postgres_rows() -> list[dict]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id,username,space,progress_key,path,identity,server_revision,updated_at_utc,record_json,archived_at_utc,reason "
                "FROM future_server2.lesson_progress_orphans ORDER BY id"
            )
            return [
                app.postgres_lesson_progress_orphan_row_from_source({
                    "id": row[0], "username": row[1], "space": row[2], "progress_key": row[3],
                    "path": row[4], "identity": row[5], "server_revision": row[6],
                    "updated_at_utc": row[7], "record_json": row[8], "archived_at_utc": row[9], "reason": row[10],
                })
                for row in cursor.fetchall()
            ]
    return app.postgres_execute(_read)

def fingerprint(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()

def summarize(rows: list[dict]) -> dict:
    by_space: dict[str, int] = {}
    by_reason: dict[str, int] = {}
    for row in rows:
        by_space[row["space"]] = by_space.get(row["space"], 0) + 1
        by_reason[row["reason"]] = by_reason.get(row["reason"], 0) + 1
    return {"rows": len(rows), "spaces": by_space, "reasons": by_reason}

def cleanup_test_rows() -> dict:
    def _cleanup(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.lesson_progress_orphans WHERE username LIKE 'codexpgorphan%' OR id>=940000000")
            deleted = int(cursor.rowcount or 0)
            cursor.execute("SELECT count(*) FROM future_server2.lesson_progress_orphans")
            remaining = int(cursor.fetchone()[0] or 0)
        return {"deleted": deleted, "remaining": remaining}
    return app.postgres_execute(_cleanup)

def round_trip() -> dict:
    now = app.utc_timestamp()
    row = {
        "id": 940000001,
        "username": "codexpgorphan",
        "space": "Space_V",
        "progress_key": "legacy/path.Space_V",
        "path": "legacy/path.Space_V",
        "identity": "",
        "server_revision": 3,
        "updated_at_utc": now,
        "record": {"path": "legacy/path.Space_V", "_serverRevision": 3},
        "archived_at_utc": now,
        "reason": "codex",
    }
    first = app.postgres_upsert_lesson_progress_orphan_row(row)
    retry = app.postgres_upsert_lesson_progress_orphan_row(row)
    return {"write_ok": bool(first.get("ok")), "retry_same_sha": first.get("source_sha256") == retry.get("source_sha256"), "ok": bool(first.get("ok")) and first.get("source_sha256") == retry.get("source_sha256")}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--cleanup-test-rows", action="store_true")
    args = parser.parse_args()
    sqlite = sqlite_rows()
    if args.dry_run and not os.environ.get("FUTURE_PG_DSN"):
        result = {**summarize(sqlite), "fingerprint": fingerprint(sqlite), "dry_run": True, "postgres_pending": "FUTURE_PG_DSN is not set"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating lesson_progress_orphans to PostgreSQL.")
    app.postgres_initialize_schema()
    cleanup = cleanup_test_rows()
    rt = None
    result = {"parity": False, "round_trip": None}
    try:
        if not args.verify_only and not args.dry_run:
            for row in sqlite:
                app.postgres_upsert_lesson_progress_orphan_row(row)
        pg_all = postgres_rows()
        ids = {row["id"] for row in sqlite}
        pg_subset = [row for row in pg_all if row["id"] in ids]
        sqlite_fp = fingerprint(sqlite)
        pg_fp = fingerprint(pg_subset)
        rt = None if args.verify_only or args.dry_run else round_trip()
        result = {
            **summarize(sqlite),
            "postgres_total": len(pg_all),
            "postgres_matching_sqlite": len(pg_subset),
            "fingerprint": sqlite_fp,
            "postgres_fingerprint": pg_fp,
            "parity": sqlite_fp == pg_fp and len(sqlite) == len(pg_subset),
            "round_trip": rt,
            "cleanup": cleanup,
            "post_round_trip_cleanup": None,
            "verify_only": args.verify_only,
            "dry_run": args.dry_run,
        }
    finally:
        result["post_round_trip_cleanup"] = cleanup_test_rows()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["parity"] and (rt is None or rt.get("ok")) else 1

if __name__ == "__main__":
    raise SystemExit(main())
