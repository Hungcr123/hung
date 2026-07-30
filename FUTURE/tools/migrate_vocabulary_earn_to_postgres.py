#!/usr/bin/env python3
"""Migrate vocabulary period earn tables to PostgreSQL."""

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
TABLES = {
    "day": ("daily_earn", "day_key"),
    "week": ("weekly_earn", "week_key"),
    "month": ("monthly_earn", "month_key"),
    "npc": ("npc_period_earn", "bucket_key"),
}


def sqlite_rows(scope: str) -> list[dict]:
    table, key_column = TABLES[scope]
    connection = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True, timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        rows = []
        if scope == "npc":
            query = "SELECT username,scope,bucket_key,word_key,learned_at_utc FROM npc_period_earn ORDER BY lower(username),scope,bucket_key,word_key"
        else:
            query = f"SELECT username,word_key,{key_column},learned_at_utc,event_id FROM {table} ORDER BY lower(username),word_key,{key_column}"
        for row in connection.execute(query):
            payload = {
                "username": app.normalize_username(row["username"]),
                "word_key": app.clean(row["word_key"]),
                "learned_at_utc": app.clean(row["learned_at_utc"]),
            }
            if scope == "npc":
                payload.update({"scope": app.clean(row["scope"]), "bucket_key": app.clean(row["bucket_key"])})
            else:
                payload.update({key_column: app.clean(row[key_column]), "event_id": int(row["event_id"]) if row["event_id"] is not None else None})
            rows.append(payload)
        return rows
    finally:
        connection.close()


def pg_rows(scope: str) -> list[dict]:
    table, key_column = TABLES[scope]
    pg_table = f"future_server2.{table}"

    def _read(connection):
        with connection.cursor() as cursor:
            if scope == "npc":
                cursor.execute("SELECT username,scope,bucket_key,word_key,learned_at_utc FROM future_server2.npc_period_earn ORDER BY lower(username),scope,bucket_key,word_key")
                return [
                    {
                        "username": app.normalize_username(row[0]),
                        "scope": app.clean(row[1]),
                        "bucket_key": app.clean(row[2]),
                        "word_key": app.clean(row[3]),
                        "learned_at_utc": app.clean(row[4]),
                    }
                    for row in cursor.fetchall()
                ]
            cursor.execute(f"SELECT username,word_key,{key_column},learned_at_utc,event_id FROM {pg_table} ORDER BY lower(username),word_key,{key_column}")
            return [
                {
                    "username": app.normalize_username(row[0]),
                    "word_key": app.clean(row[1]),
                    key_column: app.clean(row[2]),
                    "learned_at_utc": app.clean(row[3]),
                    "event_id": int(row[4]) if row[4] is not None else None,
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
        out = {}
        with connection.cursor() as cursor:
            for table in ("daily_earn", "weekly_earn", "monthly_earn", "npc_period_earn"):
                cursor.execute(f"DELETE FROM future_server2.{table} WHERE lower(username) LIKE 'codexpg%'")
                out[f"{table}_deleted"] = int(cursor.rowcount or 0)
                cursor.execute(f"SELECT count(*) FROM future_server2.{table}")
                out[f"{table}_remaining"] = int(cursor.fetchone()[0] or 0)
        return out

    return app.postgres_execute(_cleanup)


def round_trip() -> dict:
    stamp = app.utc_timestamp()
    rows = [
        ("day", {"username": "codexpgearn", "word_key": "codexpgearnword", "day_key": "2026-07-25", "learned_at_utc": stamp, "event_id": 900000001}),
        ("week", {"username": "codexpgearn", "word_key": "codexpgearnword", "week_key": "2026-07-20", "learned_at_utc": stamp, "event_id": 900000001}),
        ("month", {"username": "codexpgearn", "word_key": "codexpgearnword", "month_key": "2026-07", "learned_at_utc": stamp, "event_id": 900000001}),
        ("npc", {"username": "codexpgnpc", "scope": "day", "bucket_key": "2026-07-25", "word_key": "codexpgnpcword", "learned_at_utc": stamp}),
    ]
    results = [app.postgres_upsert_vocabulary_earn_row(scope, row) for scope, row in rows]
    retries = [app.postgres_upsert_vocabulary_earn_row(scope, row) for scope, row in rows]
    return {
        "ok_count": sum(1 for row in results if row.get("ok")),
        "retry_same_sha_count": sum(1 for first, second in zip(results, retries) if first.get("source_sha256") == second.get("source_sha256")),
        "ok": all(row.get("ok") for row in results) and all(first.get("source_sha256") == second.get("source_sha256") for first, second in zip(results, retries)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--cleanup-test-rows", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating vocabulary earn tables to PostgreSQL.")
    app.postgres_initialize_schema()
    cleanup_before = cleanup_test_rows() if args.cleanup_test_rows else None
    cleanup_after = None
    sqlite_by_scope = {scope: sqlite_rows(scope) for scope in TABLES}
    if not args.verify_only and not args.dry_run:
        for scope, rows in sqlite_by_scope.items():
            for row in rows:
                app.postgres_upsert_vocabulary_earn_row(scope, row)
    rt = None
    if not args.verify_only and not args.dry_run:
        try:
            rt = round_trip()
        finally:
            cleanup_after = cleanup_test_rows()
    pg_by_scope = {scope: pg_rows(scope) for scope in TABLES}
    scopes = {}
    ok = True
    for scope in TABLES:
        sqlite_fp = fingerprint(sqlite_by_scope[scope])
        pg_keys = {json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str) for row in sqlite_by_scope[scope]}
        pg_subset = [row for row in pg_by_scope[scope] if json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str) in pg_keys]
        pg_fp = fingerprint(pg_subset)
        parity = sqlite_fp == pg_fp and len(sqlite_by_scope[scope]) == len(pg_subset)
        ok = ok and parity
        scopes[scope] = {
            "sqlite_rows": len(sqlite_by_scope[scope]),
            "postgres_total": len(pg_by_scope[scope]),
            "postgres_matching_sqlite": len(pg_subset),
            "sqlite_fingerprint": sqlite_fp,
            "postgres_fingerprint": pg_fp,
            "parity": parity,
        }
    result = {
        "scopes": scopes,
        "parity": ok,
        "round_trip": rt,
        "cleanup": {"before": cleanup_before, "after": cleanup_after} if (cleanup_before is not None or cleanup_after is not None) else None,
        "dry_run": args.dry_run,
        "verify_only": args.verify_only,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if ok and (rt is None or rt.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
