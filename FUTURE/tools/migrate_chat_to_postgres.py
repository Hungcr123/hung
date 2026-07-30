#!/usr/bin/env python3
"""Migrate chat messages and read state to PostgreSQL."""

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

def _load_json(text: object) -> dict:
    try:
        value = json.loads(text or "{}")
    except Exception:
        value = {}
    return value if isinstance(value, dict) else {}

def sqlite_payload() -> dict:
    con = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        messages = [
            {
                "id": int(row["id"] or 0),
                "username": app.normalize_username(row["username"]),
                "sender": app.clean(row["sender"]),
                "operation_id": app.clean(row["operation_id"]),
                "message": _load_json(row["message_json"]),
                "created_at_utc": app.clean(row["created_at_utc"]),
                "created_epoch": float(row["created_epoch"] or 0),
            }
            for row in con.execute(
                "SELECT id,username,sender,operation_id,message_json,created_at_utc,created_epoch FROM chat_messages ORDER BY id"
            )
        ]
        read_state = [
            {
                "username": app.normalize_username(row["username"]),
                "admin_read": int(row["admin_read"] or 0),
                "user_read": int(row["user_read"] or 0),
                "updated_at_utc": app.clean(row["updated_at_utc"]),
            }
            for row in con.execute("SELECT username,admin_read,user_read,updated_at_utc FROM chat_read_state ORDER BY lower(username)")
        ]
        return {"messages": messages, "read_state": read_state}
    finally:
        con.close()

def postgres_payload() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id,username,sender,operation_id,message_json,created_at_utc,created_epoch "
                "FROM future_server2.chat_messages ORDER BY id"
            )
            messages = [
                {
                    "id": int(row[0] or 0),
                    "username": app.normalize_username(row[1]),
                    "sender": app.clean(row[2]),
                    "operation_id": app.clean(row[3]),
                    "message": dict(row[4]) if isinstance(row[4], dict) else {},
                    "created_at_utc": app.clean(row[5]),
                    "created_epoch": float(row[6] or 0),
                }
                for row in cursor.fetchall()
            ]
            cursor.execute("SELECT username,admin_read,user_read,updated_at_utc FROM future_server2.chat_read_state ORDER BY lower(username)")
            read_state = [
                {
                    "username": app.normalize_username(row[0]),
                    "admin_read": int(row[1] or 0),
                    "user_read": int(row[2] or 0),
                    "updated_at_utc": app.clean(row[3]),
                }
                for row in cursor.fetchall()
            ]
            return {"messages": messages, "read_state": read_state}

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
            cursor.execute("DELETE FROM future_server2.chat_messages WHERE lower(username) LIKE 'codexpg%' OR id>=920000000")
            deleted_messages = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.chat_read_state WHERE lower(username) LIKE 'codexpg%'")
            deleted_read = int(cursor.rowcount or 0)
            cursor.execute("SELECT count(*) FROM future_server2.chat_messages")
            messages = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT count(*) FROM future_server2.chat_read_state")
            read_state = int(cursor.fetchone()[0] or 0)
        return {"deleted_messages": deleted_messages, "deleted_read_state": deleted_read, "messages": messages, "read_state": read_state}

    return app.postgres_execute(_cleanup)

def test_row_counts() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM future_server2.chat_messages WHERE lower(username) LIKE 'codexpg%' OR id>=920000000")
            messages = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT count(*) FROM future_server2.chat_read_state WHERE lower(username) LIKE 'codexpg%'")
            read_state = int(cursor.fetchone()[0] or 0)
        return {"messages": messages, "read_state": read_state}

    return app.postgres_execute(_read)

def round_trip() -> dict:
    stamp = app.utc_timestamp()
    row = {
        "id": 920000001,
        "username": "codexpgchat",
        "sender": "user",
        "operation_id": "codex-pg-chat-operation",
        "message": {"username": "codexpgchat", "sender": "user", "text": "postgres chat slice", "at": stamp, "ts": app.timestamp_to_epoch(stamp)},
        "created_at_utc": stamp,
        "created_epoch": app.timestamp_to_epoch(stamp),
    }
    first = app.postgres_upsert_chat_message_row(row)
    duplicate = app.postgres_upsert_chat_message_row(row)
    read_first = app.postgres_upsert_chat_read_state_row({
        "username": "codexpgchat",
        "admin_read": 1,
        "user_read": 2,
        "updated_at_utc": stamp,
    })
    read_retry = app.postgres_upsert_chat_read_state_row({
        "username": "codexpgchat",
        "admin_read": 0,
        "user_read": 1,
        "updated_at_utc": stamp,
    })
    return {
        "message_ok": bool(first.get("ok")) and bool(duplicate.get("ok")),
        "message_same_sha": first.get("source_sha256") == duplicate.get("source_sha256"),
        "read_ok": bool(read_first.get("ok")) and bool(read_retry.get("ok")),
        "ok": bool(first.get("ok")) and bool(duplicate.get("ok")) and first.get("source_sha256") == duplicate.get("source_sha256") and bool(read_first.get("ok")) and bool(read_retry.get("ok")),
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
            "sqlite_messages": len(sqlite["messages"]),
            "sqlite_read_state": len(sqlite["read_state"]),
            "messages_fingerprint": fingerprint(sqlite["messages"]),
            "read_state_fingerprint": fingerprint(sqlite["read_state"]),
            "dry_run": True,
            "postgres_pending": "FUTURE_PG_DSN is not set",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating chat to PostgreSQL.")
    app.postgres_initialize_schema()
    cleanup = cleanup_test_rows() if args.cleanup_test_rows else None
    if not args.verify_only and not args.dry_run:
        for row in sqlite["messages"]:
            app.postgres_upsert_chat_message_row(row)
        for row in sqlite["read_state"]:
            app.postgres_upsert_chat_read_state_row(row)
    pg = postgres_payload()
    sqlite_message_ids = {row["id"] for row in sqlite["messages"]}
    sqlite_read_users = {row["username"] for row in sqlite["read_state"]}
    pg_messages = [row for row in pg["messages"] if row["id"] in sqlite_message_ids]
    pg_read = [row for row in pg["read_state"] if row["username"] in sqlite_read_users]
    extra_messages = [row for row in pg["messages"] if row["id"] not in sqlite_message_ids]
    extra_read = [row for row in pg["read_state"] if row["username"] not in sqlite_read_users]
    message_fp = fingerprint(sqlite["messages"])
    pg_message_fp = fingerprint(pg_messages)
    read_fp = fingerprint(sqlite["read_state"])
    pg_read_fp = fingerprint(pg_read)
    rt = None
    final_cleanup = None
    if not args.verify_only and not args.dry_run:
        try:
            rt = round_trip()
        finally:
            final_cleanup = cleanup_test_rows()
        pg = postgres_payload()
        pg_messages = [row for row in pg["messages"] if row["id"] in sqlite_message_ids]
        pg_read = [row for row in pg["read_state"] if row["username"] in sqlite_read_users]
        extra_messages = [row for row in pg["messages"] if row["id"] not in sqlite_message_ids]
        extra_read = [row for row in pg["read_state"] if row["username"] not in sqlite_read_users]
        pg_message_fp = fingerprint(pg_messages)
        pg_read_fp = fingerprint(pg_read)
    tests_remaining = test_row_counts()
    parity = (
        message_fp == pg_message_fp
        and read_fp == pg_read_fp
        and len(sqlite["messages"]) == len(pg_messages)
        and len(sqlite["read_state"]) == len(pg_read)
        and not extra_messages
        and not extra_read
        and tests_remaining == {"messages": 0, "read_state": 0}
    )
    result = {
        "sqlite_messages": len(sqlite["messages"]),
        "postgres_messages_total": len(pg["messages"]),
        "postgres_messages_matching_sqlite": len(pg_messages),
        "postgres_messages_extra": len(extra_messages),
        "sqlite_read_state": len(sqlite["read_state"]),
        "postgres_read_state_total": len(pg["read_state"]),
        "postgres_read_state_matching_sqlite": len(pg_read),
        "postgres_read_state_extra": len(extra_read),
        "messages_fingerprint": message_fp,
        "postgres_messages_fingerprint": pg_message_fp,
        "read_state_fingerprint": read_fp,
        "postgres_read_state_fingerprint": pg_read_fp,
        "test_rows_remaining": tests_remaining,
        "parity": parity,
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
