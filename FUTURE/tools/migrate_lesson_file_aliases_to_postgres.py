#!/usr/bin/env python3
"""Migrate lesson_file_aliases path-to-file-id metadata to PostgreSQL."""

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
            app.postgres_lesson_file_alias_row_from_source(dict(row))
            for row in con.execute(
                "SELECT normalized_path,file_id,source,active,first_seen_at_utc,last_seen_at_utc "
                "FROM lesson_file_aliases ORDER BY lower(normalized_path)"
            )
        ]
    finally:
        con.close()

def postgres_rows() -> list[dict]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT normalized_path,file_id,source,active,first_seen_at_utc,last_seen_at_utc "
                "FROM future_server2.lesson_file_aliases ORDER BY lower(normalized_path)"
            )
            return [
                app.postgres_lesson_file_alias_row_from_source({
                    "normalized_path": row[0],
                    "file_id": row[1],
                    "source": row[2],
                    "active": row[3],
                    "first_seen_at_utc": row[4],
                    "last_seen_at_utc": row[5],
                })
                for row in cursor.fetchall()
            ]

    return app.postgres_execute(_read)

def fingerprint(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)):
        digest.update(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()

def summarize(rows: list[dict]) -> dict:
    active = sum(1 for row in rows if row.get("active"))
    by_source: dict[str, int] = {}
    file_ids = set()
    for row in rows:
        by_source[row["source"]] = by_source.get(row["source"], 0) + 1
        if row.get("file_id"):
            file_ids.add(row["file_id"])
    return {"active": active, "inactive": len(rows) - active, "sources": by_source, "file_ids": len(file_ids)}

def cleanup_test_rows() -> dict:
    def _cleanup(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.lesson_file_aliases WHERE normalized_path LIKE 'codex-pg-alias/%'")
            deleted = int(cursor.rowcount or 0)
            cursor.execute("SELECT count(*) FROM future_server2.lesson_file_aliases")
            remaining = int(cursor.fetchone()[0] or 0)
        return {"deleted": deleted, "remaining": remaining}

    return app.postgres_execute(_cleanup)

def round_trip() -> dict:
    row = {
        "normalized_path": "codex-pg-alias/sample.Space_V",
        "file_id": "ftg-lesson-codexpg-alias",
        "source": "codex",
        "active": True,
        "first_seen_at_utc": app.utc_timestamp(),
        "last_seen_at_utc": app.utc_timestamp(),
    }
    first = app.postgres_upsert_lesson_file_alias_row(row)
    retry = app.postgres_upsert_lesson_file_alias_row(row)
    return {
        "write_ok": bool(first.get("ok")),
        "retry_same_sha": first.get("source_sha256") == retry.get("source_sha256"),
        "ok": bool(first.get("ok")) and first.get("source_sha256") == retry.get("source_sha256"),
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
            "summary": summarize(sqlite),
            "dry_run": True,
            "postgres_pending": "FUTURE_PG_DSN is not set",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating lesson_file_aliases to PostgreSQL.")
    app.postgres_initialize_schema()
    cleanup = cleanup_test_rows() if args.cleanup_test_rows else None
    if not args.verify_only and not args.dry_run:
        for row in sqlite:
            app.postgres_upsert_lesson_file_alias_row(row)
    pg_all = postgres_rows()
    paths = {row["normalized_path"] for row in sqlite}
    pg_subset = [row for row in pg_all if row["normalized_path"] in paths]
    sqlite_fp = fingerprint(sqlite)
    pg_fp = fingerprint(pg_subset)
    rt = None
    final_cleanup = None
    if not args.verify_only and not args.dry_run:
        try:
            rt = round_trip()
        finally:
            final_cleanup = cleanup_test_rows()
    result = {
        "sqlite_rows": len(sqlite),
        "postgres_total": len(pg_all),
        "postgres_matching_sqlite": len(pg_subset),
        "sqlite_fingerprint": sqlite_fp,
        "postgres_fingerprint": pg_fp,
        "summary": summarize(sqlite),
        "parity": sqlite_fp == pg_fp and len(sqlite) == len(pg_subset),
        "round_trip": rt,
        "cleanup": cleanup,
        "final_cleanup": final_cleanup,
        "dry_run": args.dry_run,
        "verify_only": args.verify_only,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["parity"] and (rt is None or rt.get("ok")) else 1

if __name__ == "__main__":
    raise SystemExit(main())
