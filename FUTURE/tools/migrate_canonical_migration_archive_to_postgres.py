#!/usr/bin/env python3
"""Migrate canonical migration repair archive rows to PostgreSQL."""

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
            app.postgres_canonical_migration_archive_row_from_source(dict(row))
            for row in con.execute(
                """
                SELECT migration_batch_id,source_primary_key,target_primary_key,full_original_payload,
                       lesson_id,file_id,all_paths,revision,server_timestamp,merge_reason,checksum
                FROM canonical_migration_archive
                ORDER BY migration_batch_id, source_primary_key
                """
            )
        ]
    finally:
        con.close()

def postgres_rows(keys: set[tuple[str, str]] | None = None) -> list[dict]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT migration_batch_id,source_primary_key,target_primary_key,full_original_payload,
                       lesson_id,file_id,all_paths,revision,server_timestamp,merge_reason,checksum
                FROM future_server2.canonical_migration_archive
                ORDER BY migration_batch_id, source_primary_key
                """
            )
            rows = []
            for row in cursor.fetchall():
                current = app.postgres_canonical_migration_archive_row_from_source(
                    {
                        "migration_batch_id": row[0],
                        "source_primary_key": row[1],
                        "target_primary_key": row[2],
                        "full_original_payload": row[3],
                        "lesson_id": row[4],
                        "file_id": row[5],
                        "all_paths": row[6],
                        "revision": row[7],
                        "server_timestamp": row[8],
                        "merge_reason": row[9],
                        "checksum": row[10],
                    }
                )
                if keys is None or (current["migration_batch_id"], current["source_primary_key"]) in keys:
                    rows.append(current)
            return rows
    return app.postgres_execute(_read)

def fingerprint(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()

def round_trip() -> dict:
    row = {
        "migration_batch_id": "codex-pg-canonical-archive-round-trip",
        "source_primary_key": json.dumps({"source": "codex"}, sort_keys=True),
        "target_primary_key": json.dumps({"target": "codex"}, sort_keys=True),
        "full_original_payload": {"ok": True, "kind": "round-trip"},
        "lesson_id": "codex-pg-lesson",
        "file_id": "codex-pg-file",
        "all_paths": ["codex/path"],
        "revision": 1,
        "server_timestamp": app.utc_timestamp(),
        "merge_reason": "codex PostgreSQL archive adapter idempotency check",
        "checksum": "codex-pg-checksum",
    }
    first = app.postgres_upsert_canonical_migration_archive_row(row)
    retry = app.postgres_upsert_canonical_migration_archive_row(row)
    return {
        "write_ok": bool(first.get("ok")),
        "retry_same_sha": first.get("source_sha256") == retry.get("source_sha256"),
        "ok": bool(first.get("ok")) and first.get("source_sha256") == retry.get("source_sha256"),
    }

def cleanup_test_rows() -> dict:
    def _cleanup(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.canonical_migration_archive WHERE migration_batch_id LIKE 'codex-pg-%'")
            deleted = int(cursor.rowcount or 0)
            cursor.execute("SELECT count(*) FROM future_server2.canonical_migration_archive")
            remaining = int(cursor.fetchone()[0] or 0)
        return {"deleted": deleted, "remaining": remaining}
    return app.postgres_execute(_cleanup)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--cleanup-test-rows", action="store_true")
    args = parser.parse_args()
    sqlite = sqlite_rows()
    sqlite_fp = fingerprint(sqlite)
    if args.dry_run and not os.environ.get("FUTURE_PG_DSN"):
        print(json.dumps({"sqlite_rows": len(sqlite), "sqlite_fingerprint": sqlite_fp, "dry_run": True, "postgres_pending": "FUTURE_PG_DSN is not set"}, ensure_ascii=False, indent=2))
        return 0
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating canonical_migration_archive to PostgreSQL.")
    app.postgres_initialize_schema()
    cleanup = cleanup_test_rows() if args.cleanup_test_rows else None
    rt = None
    post_round_trip_cleanup = None
    try:
        if not args.verify_only and not args.dry_run:
            for row in sqlite:
                app.postgres_upsert_canonical_migration_archive_row(row)
        keys = {(row["migration_batch_id"], row["source_primary_key"]) for row in sqlite}
        pg = postgres_rows(keys)
        pg_fp = fingerprint(pg)
        rt = None if args.verify_only or args.dry_run else round_trip()
    finally:
        if not args.verify_only and not args.dry_run:
            post_round_trip_cleanup = cleanup_test_rows()
    result = {
        "sqlite_rows": len(sqlite),
        "postgres_matching_sqlite": len(pg),
        "sqlite_fingerprint": sqlite_fp,
        "postgres_fingerprint": pg_fp,
        "parity": sqlite_fp == pg_fp and len(sqlite) == len(pg),
        "round_trip": rt,
        "cleanup": cleanup,
        "post_round_trip_cleanup": post_round_trip_cleanup,
        "verify_only": args.verify_only,
        "dry_run": args.dry_run,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["parity"] and (rt is None or rt.get("ok")) else 1

if __name__ == "__main__":
    raise SystemExit(main())
