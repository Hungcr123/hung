#!/usr/bin/env python3
"""Migrate vocabulary registry/events to PostgreSQL.

This slice copies vocabulary_registry and vocabulary_events only. The wider
vocabulary transaction still remains SQLite until period/leaderboard tables are
migrated, so production feature flags stay off.
"""

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


def sqlite_registry_rows() -> list[dict]:
    connection = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True, timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        rows = []
        for row in connection.execute("SELECT * FROM vocabulary_registry ORDER BY lower(username),word_key"):
            try:
                sources = json.loads(row["sources_json"] or "[]")
            except Exception:
                sources = []
            rows.append({
                "username": app.normalize_username(row["username"]),
                "word_key": app.clean(row["word_key"]),
                "word": app.clean(row["word"]),
                "meaning": app.clean(row["meaning"]),
                "pron": app.clean(row["pron"]),
                "word_type": app.clean(row["word_type"]),
                "learn_count": max(0, app.space_w_int(row["learn_count"], 0)),
                "first_at_utc": app.clean(row["first_at_utc"]),
                "last_at_utc": app.clean(row["last_at_utc"]),
                "sources": sources if isinstance(sources, list) else [],
                "qmdict_missing": bool(row["qmdict_missing"]),
            })
        return rows
    finally:
        connection.close()


def sqlite_event_rows() -> list[dict]:
    connection = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True, timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        return [
            {
                "id": int(row["id"] or 0),
                "username": app.normalize_username(row["username"]),
                "word_key": app.clean(row["word_key"]),
                "source_path": app.clean_path_value(row["source_path"]),
                "event_key": app.clean(row["event_key"]),
                "learned_at_utc": app.clean(row["learned_at_utc"]),
                "local_day": app.clean(row["local_day"]),
                "iso_week": app.clean(row["iso_week"]),
                "local_month": app.clean(row["local_month"]),
            }
            for row in connection.execute("SELECT * FROM vocabulary_events ORDER BY id")
        ]
    finally:
        connection.close()


def pg_registry_rows() -> list[dict]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT username,word_key,word,meaning,pron,word_type,learn_count,first_at_utc,last_at_utc,sources_json,qmdict_missing FROM future_server2.vocabulary_registry ORDER BY lower(username),word_key"
            )
            return [
                {
                    "username": app.normalize_username(row[0]),
                    "word_key": app.clean(row[1]),
                    "word": app.clean(row[2]),
                    "meaning": app.clean(row[3]),
                    "pron": app.clean(row[4]),
                    "word_type": app.clean(row[5]),
                    "learn_count": max(0, app.space_w_int(row[6], 0)),
                    "first_at_utc": app.clean(row[7]),
                    "last_at_utc": app.clean(row[8]),
                    "sources": row[9] if isinstance(row[9], list) else [],
                    "qmdict_missing": bool(row[10]),
                }
                for row in cursor.fetchall()
            ]

    return app.postgres_execute(_read)


def pg_event_rows() -> list[dict]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT id,username,word_key,source_path,event_key,learned_at_utc,local_day,iso_week,local_month FROM future_server2.vocabulary_events ORDER BY id")
            return [
                {
                    "id": int(row[0] or 0),
                    "username": app.normalize_username(row[1]),
                    "word_key": app.clean(row[2]),
                    "source_path": app.clean_path_value(row[3]),
                    "event_key": app.clean(row[4]),
                    "learned_at_utc": app.clean(row[5]),
                    "local_day": app.clean(row[6]),
                    "iso_week": app.clean(row[7]),
                    "local_month": app.clean(row[8]),
                }
                for row in cursor.fetchall()
            ]

    return app.postgres_execute(_read)


def fingerprint(rows: list[dict], key_fields: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: tuple(str(item.get(field, "")).lower() for field in key_fields)):
        digest.update(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def cleanup_test_rows() -> dict:
    def _cleanup(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.vocabulary_events WHERE lower(username) LIKE 'codexpg%' OR lower(event_key) LIKE 'codex-pg-vocab-%'")
            events = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.vocabulary_registry WHERE lower(username) LIKE 'codexpg%' OR lower(word_key) LIKE 'codexpg%'")
            registry = int(cursor.rowcount or 0)
            cursor.execute("SELECT count(*) FROM future_server2.vocabulary_registry")
            registry_remaining = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT count(*) FROM future_server2.vocabulary_events")
            events_remaining = int(cursor.fetchone()[0] or 0)
        return {"registry_deleted": registry, "events_deleted": events, "registry_remaining": registry_remaining, "events_remaining": events_remaining}

    return app.postgres_execute(_cleanup)


def round_trip() -> dict:
    stamp = app.utc_timestamp()
    registry = app.postgres_upsert_vocabulary_registry_row({
        "username": "codexpgvocab",
        "word_key": "codexpgword",
        "word": "codexpgword",
        "meaning": "postgres vocabulary adapter test",
        "learn_count": 1,
        "first_at_utc": stamp,
        "last_at_utc": stamp,
        "sources": ["codex/postgres/vocab"],
    })
    event = app.postgres_upsert_vocabulary_event_row({
        "id": 900000001,
        "username": "codexpgvocab",
        "word_key": "codexpgword",
        "source_path": "codex/postgres/vocab",
        "event_key": "codex-pg-vocab-event",
        "learned_at_utc": stamp,
        "local_day": "2026-07-25",
        "iso_week": "2026-07-20",
        "local_month": "2026-07",
    })
    registry_retry = app.postgres_upsert_vocabulary_registry_row({
        "username": "codexpgvocab",
        "word_key": "codexpgword",
        "word": "codexpgword",
        "meaning": "postgres vocabulary adapter test",
        "learn_count": 1,
        "first_at_utc": stamp,
        "last_at_utc": stamp,
        "sources": ["codex/postgres/vocab"],
    })
    return {
        "registry_ok": bool(registry.get("ok")),
        "event_ok": bool(event.get("ok")),
        "registry_retry_same_sha": registry.get("source_sha256") == registry_retry.get("source_sha256"),
        "ok": bool(registry.get("ok")) and bool(event.get("ok")) and registry.get("source_sha256") == registry_retry.get("source_sha256"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--cleanup-test-rows", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating vocabulary to PostgreSQL.")
    app.postgres_initialize_schema()
    cleanup_before = cleanup_test_rows() if args.cleanup_test_rows else None
    cleanup_after = None
    rt = None
    try:
        sqlite_registry = sqlite_registry_rows()
        sqlite_events = sqlite_event_rows()
        if not args.verify_only and not args.dry_run:
            for row in sqlite_registry:
                app.postgres_upsert_vocabulary_registry_row(row)
            for row in sqlite_events:
                app.postgres_upsert_vocabulary_event_row(row)
        pg_registry = pg_registry_rows()
        pg_events = pg_event_rows()
        sqlite_registry_keys = {(row["username"].lower(), row["word_key"]) for row in sqlite_registry}
        sqlite_event_ids = {row["id"] for row in sqlite_events}
        pg_registry_subset = [row for row in pg_registry if (row["username"].lower(), row["word_key"]) in sqlite_registry_keys]
        pg_events_subset = [row for row in pg_events if row["id"] in sqlite_event_ids]
        registry_fp = fingerprint(sqlite_registry, ("username", "word_key"))
        pg_registry_fp = fingerprint(pg_registry_subset, ("username", "word_key"))
        events_fp = fingerprint(sqlite_events, ("id",))
        pg_events_fp = fingerprint(pg_events_subset, ("id",))
        if not args.verify_only and not args.dry_run:
            rt = round_trip()
    finally:
        if not args.verify_only and not args.dry_run:
            cleanup_after = cleanup_test_rows()
    result = {
        "sqlite_registry_rows": len(sqlite_registry),
        "postgres_registry_total": len(pg_registry),
        "postgres_registry_matching_sqlite": len(pg_registry_subset),
        "sqlite_events_rows": len(sqlite_events),
        "postgres_events_total": len(pg_events),
        "postgres_events_matching_sqlite": len(pg_events_subset),
        "registry_fingerprint": registry_fp,
        "postgres_registry_fingerprint": pg_registry_fp,
        "events_fingerprint": events_fp,
        "postgres_events_fingerprint": pg_events_fp,
        "parity": registry_fp == pg_registry_fp and events_fp == pg_events_fp and len(sqlite_registry) == len(pg_registry_subset) and len(sqlite_events) == len(pg_events_subset),
        "round_trip": rt,
        "cleanup": {"before": cleanup_before, "after": cleanup_after},
        "dry_run": args.dry_run,
        "verify_only": args.verify_only,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["parity"] and (rt is None or rt.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
