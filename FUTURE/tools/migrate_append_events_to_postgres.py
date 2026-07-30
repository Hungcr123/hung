#!/usr/bin/env python3
"""Migrate append_events audit/completion streams to PostgreSQL."""

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
        rows = []
        for row in con.execute("SELECT id,stream,username,event_at_utc,event_json,event_key FROM append_events ORDER BY id"):
            try:
                event = json.loads(row["event_json"] or "{}")
            except Exception:
                event = {}
            rows.append({
                "id": int(row["id"] or 0),
                "stream": app.clean(row["stream"]),
                "username": app.normalize_username(row["username"]),
                "event_at_utc": app.clean(row["event_at_utc"]),
                "event": event if isinstance(event, dict) else {},
                "event_key": app.clean(row["event_key"]),
            })
        return rows
    finally:
        con.close()


def pg_rows() -> list[dict]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT id,stream,username,event_at_utc,event_json,event_key FROM future_server2.append_events ORDER BY id")
            return [
                {
                    "id": int(row[0] or 0),
                    "stream": app.clean(row[1]),
                    "username": app.normalize_username(row[2]),
                    "event_at_utc": app.clean(row[3]),
                    "event": dict(row[4]) if isinstance(row[4], dict) else {},
                    "event_key": app.clean(row[5]),
                }
                for row in cursor.fetchall()
            ]

    return app.postgres_execute(_read)


def fingerprint(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: int(item["id"])):
        digest.update(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def cleanup_test_rows() -> dict:
    def _cleanup(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.append_events WHERE lower(username) LIKE 'codexpg%' OR lower(event_key) LIKE 'codex-pg-append-%' OR id>=910000000")
            deleted = int(cursor.rowcount or 0)
            cursor.execute("SELECT count(*) FROM future_server2.append_events")
            remaining = int(cursor.fetchone()[0] or 0)
        return {"deleted": deleted, "remaining": remaining}

    return app.postgres_execute(_cleanup)


def round_trip() -> dict:
    stamp = app.utc_timestamp()
    row = {
        "id": 910000001,
        "stream": "learning",
        "username": "codexpgappend",
        "event_at_utc": stamp,
        "event": {"event": "codex_postgres_append_test", "at": stamp, "user": "codexpgappend"},
        "event_key": "codex-pg-append-event",
    }
    first = app.postgres_upsert_append_event_row(row)
    second = app.postgres_upsert_append_event_row(row)
    return {
        "first_ok": bool(first.get("ok")),
        "second_ok": bool(second.get("ok")),
        "same_sha": first.get("source_sha256") == second.get("source_sha256"),
        "ok": bool(first.get("ok")) and bool(second.get("ok")) and first.get("source_sha256") == second.get("source_sha256"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--cleanup-test-rows", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating append_events to PostgreSQL.")
    app.postgres_initialize_schema()
    cleanup_before = cleanup_test_rows() if args.cleanup_test_rows else None
    cleanup_after = None
    rows = sqlite_rows()
    if not args.verify_only and not args.dry_run:
        for row in rows:
            app.postgres_upsert_append_event_row(row)
    rt = None
    if not args.verify_only and not args.dry_run:
        try:
            rt = round_trip()
        finally:
            cleanup_after = cleanup_test_rows()
    pg_all = pg_rows()
    ids = {row["id"] for row in rows}
    pg_subset = [row for row in pg_all if row["id"] in ids]
    sqlite_fp = fingerprint(rows)
    pg_fp = fingerprint(pg_subset)
    streams = {}
    for row in rows:
        streams[row["stream"]] = streams.get(row["stream"], 0) + 1
    result = {
        "sqlite_rows": len(rows),
        "postgres_total": len(pg_all),
        "postgres_matching_sqlite": len(pg_subset),
        "streams": streams,
        "sqlite_fingerprint": sqlite_fp,
        "postgres_fingerprint": pg_fp,
        "parity": sqlite_fp == pg_fp and len(rows) == len(pg_subset),
        "round_trip": rt,
        "cleanup": {"before": cleanup_before, "after": cleanup_after} if (cleanup_before is not None or cleanup_after is not None) else None,
        "dry_run": args.dry_run,
        "verify_only": args.verify_only,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["parity"] and (rt is None or rt.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
