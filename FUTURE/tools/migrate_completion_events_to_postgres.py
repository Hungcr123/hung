#!/usr/bin/env python3
"""Migrate completion-related learning events to PostgreSQL append_events."""

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
COMPLETION_STREAMS = ("learning", "learning_intent")

def _event_json(text: object) -> dict:
    try:
        value = json.loads(text or "{}")
    except Exception:
        value = {}
    return value if isinstance(value, dict) else {}

def _completion_event(row: sqlite3.Row | tuple) -> dict:
    if isinstance(row, sqlite3.Row):
        event = _event_json(row["event_json"])
        return {
            "id": int(row["id"] or 0),
            "stream": app.clean(row["stream"]),
            "username": app.normalize_username(row["username"]),
            "event_at_utc": app.clean(row["event_at_utc"]),
            "event_key": app.clean(row["event_key"]),
            "event": event,
            "status": app.clean(event.get("status", "")).lower(),
            "event_name": app.clean(event.get("event", "")).lower(),
        }
    event = dict(row[5]) if isinstance(row[5], dict) else {}
    return {
        "id": int(row[0] or 0),
        "stream": app.clean(row[1]),
        "username": app.normalize_username(row[2]),
        "event_at_utc": app.clean(row[3]),
        "event_key": app.clean(row[4]),
        "event": event,
        "status": app.clean(event.get("status", "")).lower(),
        "event_name": app.clean(event.get("event", "")).lower(),
    }

def sqlite_rows() -> list[dict]:
    con = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT id,stream,username,event_at_utc,event_key,event_json FROM append_events "
            "WHERE stream IN ('learning','learning_intent') ORDER BY id"
        ).fetchall()
        return [
            item for item in (_completion_event(row) for row in rows)
            if item["stream"] == "learning_intent" or item["event_name"] == "lesson_complete"
        ]
    finally:
        con.close()

def postgres_rows() -> list[dict]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id,stream,username,event_at_utc,event_key,event_json FROM future_server2.append_events "
                "WHERE stream IN ('learning','learning_intent') ORDER BY id"
            )
            return [
                item for item in (_completion_event(row) for row in cursor.fetchall())
                if item["stream"] == "learning_intent" or item["event_name"] == "lesson_complete"
            ]

    return app.postgres_execute(_read)

def fingerprint(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()

def summarize(rows: list[dict]) -> dict:
    streams: dict[str, int] = {}
    statuses: dict[str, int] = {}
    names: dict[str, int] = {}
    keyed = 0
    for row in rows:
        streams[row["stream"]] = streams.get(row["stream"], 0) + 1
        statuses[row["status"]] = statuses.get(row["status"], 0) + 1
        names[row["event_name"]] = names.get(row["event_name"], 0) + 1
        if row["event_key"]:
            keyed += 1
    return {"streams": streams, "statuses": statuses, "event_names": names, "with_event_key": keyed}

def cleanup_test_rows() -> dict:
    def _cleanup(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM future_server2.append_events "
                "WHERE id>=930000000 OR lower(username) LIKE 'codexpgcompletion%' OR event_key LIKE 'codex-pg-completion-%'"
            )
            deleted = int(cursor.rowcount or 0)
            cursor.execute("SELECT count(*) FROM future_server2.append_events WHERE stream IN ('learning','learning_intent')")
            remaining = int(cursor.fetchone()[0] or 0)
        return {"deleted": deleted, "completion_events_remaining": remaining}

    return app.postgres_execute(_cleanup)

def round_trip() -> dict:
    stamp = app.utc_timestamp()
    intent = {
        "id": 930000001,
        "stream": "learning_intent",
        "username": "codexpgcompletion",
        "event_at_utc": stamp,
        "event_key": "codex-pg-completion-event",
        "event": {"event": "lesson_complete_intent", "status": "pending", "user": "codexpgcompletion", "at": stamp},
    }
    final = {
        "id": 930000002,
        "stream": "learning",
        "username": "codexpgcompletion",
        "event_at_utc": stamp,
        "event_key": "codex-pg-completion-event",
        "event": {"event": "lesson_complete", "status": "final", "user": "codexpgcompletion", "at": stamp},
    }
    first = app.postgres_upsert_append_event_row(intent)
    retry = app.postgres_upsert_append_event_row(intent)
    done = app.postgres_upsert_append_event_row(final)
    return {
        "intent_ok": bool(first.get("ok")),
        "retry_same_sha": first.get("source_sha256") == retry.get("source_sha256"),
        "final_ok": bool(done.get("ok")),
        "ok": bool(first.get("ok")) and first.get("source_sha256") == retry.get("source_sha256") and bool(done.get("ok")),
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
        raise RuntimeError("Set FUTURE_PG_DSN before migrating completion events to PostgreSQL.")
    app.postgres_initialize_schema()
    cleanup_before = cleanup_test_rows() if args.cleanup_test_rows else None
    cleanup_after = None
    if not args.verify_only and not args.dry_run:
        for row in sqlite:
            app.postgres_upsert_append_event_row(row)
    rt = None
    if not args.verify_only and not args.dry_run:
        try:
            rt = round_trip()
        finally:
            cleanup_after = cleanup_test_rows()
    pg_all = postgres_rows()
    sqlite_ids = {row["id"] for row in sqlite}
    pg_subset = [row for row in pg_all if row["id"] in sqlite_ids]
    sqlite_fp = fingerprint(sqlite)
    pg_fp = fingerprint(pg_subset)
    result = {
        "sqlite_rows": len(sqlite),
        "postgres_total_completion_events": len(pg_all),
        "postgres_matching_sqlite": len(pg_subset),
        "sqlite_fingerprint": sqlite_fp,
        "postgres_fingerprint": pg_fp,
        "summary": summarize(sqlite),
        "parity": sqlite_fp == pg_fp and len(sqlite) == len(pg_subset),
        "round_trip": rt,
        "cleanup": {"before": cleanup_before, "after": cleanup_after} if (cleanup_before is not None or cleanup_after is not None) else None,
        "dry_run": args.dry_run,
        "verify_only": args.verify_only,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["parity"] and (rt is None or rt.get("ok")) else 1

if __name__ == "__main__":
    raise SystemExit(main())
