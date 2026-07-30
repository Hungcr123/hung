#!/usr/bin/env python3
"""Migrate inventory item totals and award events to PostgreSQL."""

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
        items = [app.postgres_inventory_item_row_from_source(dict(row)) for row in con.execute(
            "SELECT username,item_id,name,use_text,quantity,updated_at_utc FROM inventory_items ORDER BY lower(username), item_id"
        )]
        events = [app.postgres_inventory_event_row_from_source(dict(row)) for row in con.execute(
            "SELECT username,event_id,item_id,quantity,awarded_at_utc FROM inventory_events ORDER BY lower(username), event_id"
        )]
        return {"items": items, "events": events}
    finally:
        con.close()

def postgres_payload() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT username,item_id,name,use_text,quantity,updated_at_utc FROM future_server2.inventory_items ORDER BY lower(username), item_id"
            )
            items = [app.postgres_inventory_item_row_from_source({
                "username": row[0], "item_id": row[1], "name": row[2], "use_text": row[3],
                "quantity": row[4], "updated_at_utc": row[5],
            }) for row in cursor.fetchall()]
            cursor.execute(
                "SELECT username,event_id,item_id,quantity,awarded_at_utc FROM future_server2.inventory_events ORDER BY lower(username), event_id"
            )
            events = [app.postgres_inventory_event_row_from_source({
                "username": row[0], "event_id": row[1], "item_id": row[2], "quantity": row[3], "awarded_at_utc": row[4],
            }) for row in cursor.fetchall()]
        return {"items": items, "events": events}

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
            cursor.execute("DELETE FROM future_server2.inventory_events WHERE lower(username) LIKE 'codexpg%' OR event_id LIKE 'codex-pg-inventory-%'")
            deleted_events = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.inventory_items WHERE lower(username) LIKE 'codexpg%'")
            deleted_items = int(cursor.rowcount or 0)
            cursor.execute("SELECT count(*) FROM future_server2.inventory_items")
            items = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT count(*) FROM future_server2.inventory_events")
            events = int(cursor.fetchone()[0] or 0)
        return {"deleted_items": deleted_items, "deleted_events": deleted_events, "items": items, "events": events}

    return app.postgres_execute(_cleanup)

def round_trip() -> dict:
    now = app.utc_timestamp()
    item = {
        "username": "codexpginventory",
        "item_id": "codex-pg-item",
        "name": "Codex PG Item",
        "use_text": "migration test",
        "quantity": 2,
        "updated_at_utc": now,
    }
    event = {
        "username": "codexpginventory",
        "event_id": "codex-pg-inventory-event",
        "item_id": "codex-pg-item",
        "quantity": 2,
        "awarded_at_utc": now,
    }
    item_write = app.postgres_upsert_inventory_item_row(item)
    item_retry = app.postgres_upsert_inventory_item_row(item)
    event_write = app.postgres_upsert_inventory_event_row(event)
    event_retry = app.postgres_upsert_inventory_event_row(event)
    loaded = app.postgres_load_inventory_payload("codexpginventory")
    return {
        "item_ok": bool(item_write.get("ok")),
        "item_retry_same_sha": item_write.get("source_sha256") == item_retry.get("source_sha256"),
        "event_ok": bool(event_write.get("ok")),
        "event_retry_same_sha": event_write.get("source_sha256") == event_retry.get("source_sha256"),
        "loaded_quantity": loaded.get("items", {}).get("codex-pg-item", {}).get("quantity"),
        "ok": (
            bool(item_write.get("ok"))
            and item_write.get("source_sha256") == item_retry.get("source_sha256")
            and bool(event_write.get("ok"))
            and event_write.get("source_sha256") == event_retry.get("source_sha256")
            and loaded.get("items", {}).get("codex-pg-item", {}).get("quantity") == 2
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
            "sqlite_items": len(sqlite["items"]),
            "sqlite_events": len(sqlite["events"]),
            "items_fingerprint": fingerprint(sqlite["items"]),
            "events_fingerprint": fingerprint(sqlite["events"]),
            "dry_run": True,
            "postgres_pending": "FUTURE_PG_DSN is not set",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating inventory to PostgreSQL.")
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
            for row in sqlite["items"]:
                app.postgres_upsert_inventory_item_row(row)
            for row in sqlite["events"]:
                app.postgres_upsert_inventory_event_row(row)
        pg = postgres_payload()
        item_keys = {(row["username"], row["item_id"]) for row in sqlite["items"]}
        event_keys = {(row["username"], row["event_id"]) for row in sqlite["events"]}
        pg_items = [row for row in pg["items"] if (row["username"], row["item_id"]) in item_keys]
        pg_events = [row for row in pg["events"] if (row["username"], row["event_id"]) in event_keys]
        item_fp = fingerprint(sqlite["items"])
        pg_item_fp = fingerprint(pg_items)
        event_fp = fingerprint(sqlite["events"])
        pg_event_fp = fingerprint(pg_events)
        rt = None if args.verify_only or args.dry_run else round_trip()
        result = {
            "sqlite_items": len(sqlite["items"]),
            "postgres_items_total": len(pg["items"]),
            "postgres_items_matching_sqlite": len(pg_items),
            "sqlite_events": len(sqlite["events"]),
            "postgres_events_total": len(pg["events"]),
            "postgres_events_matching_sqlite": len(pg_events),
            "items_fingerprint": item_fp,
            "postgres_items_fingerprint": pg_item_fp,
            "events_fingerprint": event_fp,
            "postgres_events_fingerprint": pg_event_fp,
            "parity": item_fp == pg_item_fp and event_fp == pg_event_fp and len(sqlite["items"]) == len(pg_items) and len(sqlite["events"]) == len(pg_events),
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
