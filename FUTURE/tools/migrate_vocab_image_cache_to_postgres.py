#!/usr/bin/env python3
"""Migrate derived vocabulary image cache rows to PostgreSQL."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
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
            app.postgres_vocab_image_cache_row_from_source(dict(row))
            for row in con.execute("SELECT word_key,image_json,expires_epoch,updated_at_utc FROM vocab_image_cache ORDER BY word_key")
        ]
    finally:
        con.close()

def postgres_rows() -> list[dict]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT word_key,image_json,expires_epoch,updated_at_utc FROM future_server2.vocab_image_cache ORDER BY word_key")
            return [
                app.postgres_vocab_image_cache_row_from_source({
                    "word_key": row[0],
                    "image_json": row[1],
                    "expires_epoch": row[2],
                    "updated_at_utc": row[3],
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

def cleanup_test_rows() -> dict:
    def _cleanup(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.vocab_image_cache WHERE word_key LIKE 'codex-pg-image-%'")
            deleted = int(cursor.rowcount or 0)
            cursor.execute("SELECT count(*) FROM future_server2.vocab_image_cache")
            remaining = int(cursor.fetchone()[0] or 0)
        return {"deleted": deleted, "remaining": remaining}

    return app.postgres_execute(_cleanup)

def round_trip() -> dict:
    row = {
        "word_key": "codex-pg-image-word",
        "image": {"ok": True, "source": "postgres"},
        "expires_epoch": time.time() + 30 * 24 * 60 * 60,
        "updated_at_utc": app.utc_timestamp(),
    }
    first = app.postgres_upsert_vocab_image_cache_row(row)
    retry = app.postgres_upsert_vocab_image_cache_row(row)
    loaded = app.postgres_load_vocab_image_cache("codex-pg-image-word") or {}
    rows = app.postgres_load_vocab_image_cache_rows(10000)
    return {
        "write_ok": bool(first.get("ok")),
        "retry_same_sha": first.get("source_sha256") == retry.get("source_sha256"),
        "loaded_ok": bool((loaded.get("image") or {}).get("ok")),
        "listed": any(item.get("word_key") == "codex-pg-image-word" for item in rows),
        "ok": bool(first.get("ok")) and first.get("source_sha256") == retry.get("source_sha256") and bool((loaded.get("image") or {}).get("ok")) and any(item.get("word_key") == "codex-pg-image-word" for item in rows),
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
            "nonexpired_rows": sum(1 for row in sqlite if row.get("expires_epoch", 0) > time.time()),
            "dry_run": True,
            "postgres_pending": "FUTURE_PG_DSN is not set",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating vocab_image_cache to PostgreSQL.")
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
            for row in sqlite:
                app.postgres_upsert_vocab_image_cache_row(row)
        pg_all = postgres_rows()
        keys = {row["word_key"] for row in sqlite}
        pg_subset = [row for row in pg_all if row["word_key"] in keys]
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
