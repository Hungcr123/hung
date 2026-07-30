#!/usr/bin/env python3
"""Migrate users and durable auth-session hashes to PostgreSQL."""

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

def _json_loads(text: object) -> dict:
    try:
        value = json.loads(text or "{}")
    except Exception:
        value = {}
    return value if isinstance(value, dict) else {}

def sqlite_payload() -> dict:
    con = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        users = [
            {
                "username": app.normalize_username(row["username"]),
                "is_admin": bool(row["is_admin"]),
                "is_test": bool(row["is_test"]),
                "profile": _json_loads(row["profile_json"]),
                "updated_at_utc": app.clean(row["updated_at_utc"]),
            }
            for row in con.execute("SELECT username,is_admin,is_test,profile_json,updated_at_utc FROM users ORDER BY lower(username)")
        ]
        sessions = [
            {
                "token_hash": app.clean(row["token_hash"]),
                "username": app.normalize_username(row["username"]),
                "created_epoch": float(row["created_epoch"] or 0),
                "last_seen_epoch": float(row["last_seen_epoch"] or 0),
                "last_persisted_epoch": float(row["last_persisted_epoch"] or 0),
                "expires_epoch": float(row["expires_epoch"] or 0),
                "updated_at_utc": app.clean(row["updated_at_utc"]),
            }
            for row in con.execute(
                "SELECT token_hash,username,created_epoch,last_seen_epoch,last_persisted_epoch,expires_epoch,updated_at_utc "
                "FROM auth_sessions ORDER BY lower(username), token_hash"
            )
        ]
        return {"users": users, "auth_sessions": sessions}
    finally:
        con.close()

def postgres_payload() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT username,is_admin,is_test,profile_json,updated_at_utc FROM future_server2.users ORDER BY lower(username)")
            users = [
                {
                    "username": app.normalize_username(row[0]),
                    "is_admin": bool(row[1]),
                    "is_test": bool(row[2]),
                    "profile": dict(row[3]) if isinstance(row[3], dict) else {},
                    "updated_at_utc": app.clean(row[4]),
                }
                for row in cursor.fetchall()
            ]
            cursor.execute(
                "SELECT token_hash,username,created_epoch,last_seen_epoch,last_persisted_epoch,expires_epoch,updated_at_utc "
                "FROM future_server2.auth_sessions ORDER BY lower(username), token_hash"
            )
            sessions = [
                {
                    "token_hash": app.clean(row[0]),
                    "username": app.normalize_username(row[1]),
                    "created_epoch": float(row[2] or 0),
                    "last_seen_epoch": float(row[3] or 0),
                    "last_persisted_epoch": float(row[4] or 0),
                    "expires_epoch": float(row[5] or 0),
                    "updated_at_utc": app.clean(row[6]),
                }
                for row in cursor.fetchall()
            ]
            return {"users": users, "auth_sessions": sessions}

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
            cursor.execute("DELETE FROM future_server2.auth_sessions WHERE lower(username)='codexpgauth' OR token_hash LIKE 'codex-pg-auth-%'")
            deleted_sessions = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.users WHERE lower(username)='codexpgauth'")
            deleted_users = int(cursor.rowcount or 0)
            cursor.execute("SELECT count(*) FROM future_server2.users")
            users = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT count(*) FROM future_server2.auth_sessions")
            sessions = int(cursor.fetchone()[0] or 0)
        return {"deleted_users": deleted_users, "deleted_sessions": deleted_sessions, "users": users, "auth_sessions": sessions}

    return app.postgres_execute(_cleanup)

def test_row_counts() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM future_server2.auth_sessions WHERE lower(username)='codexpgauth' OR token_hash LIKE 'codex-pg-auth-%'")
            sessions = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT count(*) FROM future_server2.users WHERE lower(username)='codexpgauth'")
            users = int(cursor.fetchone()[0] or 0)
        return {"users": users, "auth_sessions": sessions}

    return app.postgres_execute(_read)

def replace_auth_sessions_snapshot(rows: list[dict]) -> dict:
    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.auth_sessions")
            deleted = int(cursor.rowcount or 0)
            for row in rows:
                updated_at = app.clean(row.get("updated_at_utc")) or app.utc_timestamp()
                cursor.execute(
                    """
                    INSERT INTO future_server2.auth_sessions
                        (token_hash,username,created_epoch,last_seen_epoch,last_persisted_epoch,expires_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        app.clean(row.get("token_hash", "")),
                        app.normalize_username(row.get("username", "")),
                        float(row.get("created_epoch") or 0),
                        float(row.get("last_seen_epoch") or 0),
                        float(row.get("last_persisted_epoch") or 0),
                        float(row.get("expires_epoch") or 0),
                        updated_at,
                        app.timestamp_to_epoch(updated_at),
                        app.utc_timestamp(),
                        hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest(),
                    ),
                )
        return {"deleted": deleted, "inserted": len(rows)}

    return app.postgres_execute(_write)

def round_trip() -> dict:
    username = "codexpgauth"
    stamp = app.utc_timestamp()
    user = app.postgres_upsert_user_row({
        "username": username,
        "is_admin": False,
        "is_test": True,
        "profile": {"display_name": "Codex PG Auth", "purpose": "postgres_migration_round_trip"},
        "updated_at_utc": stamp,
    })
    session = app.postgres_upsert_auth_session_row({
        "token_hash": "codex-pg-auth-session-hash",
        "username": username,
        "created_epoch": time.time(),
        "last_seen_epoch": time.time(),
        "last_persisted_epoch": time.time(),
        "expires_epoch": time.time() + 3600,
        "updated_at_utc": stamp,
    })
    duplicate = app.postgres_upsert_auth_session_row({
        "token_hash": "codex-pg-auth-session-hash",
        "username": username,
        "created_epoch": time.time(),
        "last_seen_epoch": time.time(),
        "last_persisted_epoch": time.time(),
        "expires_epoch": time.time() + 3600,
        "updated_at_utc": stamp,
    })
    return {
        "user_ok": bool(user.get("ok")),
        "session_ok": bool(session.get("ok")),
        "duplicate_ok": bool(duplicate.get("ok")),
        "ok": bool(user.get("ok")) and bool(session.get("ok")) and bool(duplicate.get("ok")),
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--cleanup-test-rows", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating auth users to PostgreSQL.")
    app.postgres_initialize_schema()
    cleanup = cleanup_test_rows() if args.cleanup_test_rows else None
    if args.cleanup_test_rows and args.verify_only:
        result = {"cleanup": cleanup, "verify_only": True, "cleanup_only": True}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    sqlite = sqlite_payload()
    rt = None
    result = {"parity": False, "round_trip": None}
    try:
        if not args.verify_only and not args.dry_run:
            for row in sqlite["users"]:
                app.postgres_upsert_user_row(row)
            session_replace = replace_auth_sessions_snapshot(sqlite["auth_sessions"])
        else:
            session_replace = None
        pg = postgres_payload()
        sqlite_users = {row["username"]: row for row in sqlite["users"]}
        sqlite_session_tokens = {row["token_hash"] for row in sqlite["auth_sessions"]}
        pg_users_subset = [row for row in pg["users"] if row["username"] in sqlite_users]
        pg_sessions_subset = [row for row in pg["auth_sessions"] if row["token_hash"] in sqlite_session_tokens]
        pg_usernames = {row["username"] for row in pg["users"]}
        pg_session_tokens = {row["token_hash"] for row in pg["auth_sessions"]}
        extra_users = sorted(pg_usernames - set(sqlite_users))
        missing_users = sorted(set(sqlite_users) - pg_usernames)
        extra_sessions = sorted(pg_session_tokens - sqlite_session_tokens)
        missing_sessions = sorted(sqlite_session_tokens - pg_session_tokens)
        user_fp = fingerprint(sqlite["users"])
        pg_user_fp = fingerprint(pg_users_subset)
        session_fp = fingerprint(sqlite["auth_sessions"])
        pg_session_fp = fingerprint(pg_sessions_subset)
        rt = None if args.verify_only or args.dry_run else round_trip()
        if rt is not None:
            result["post_round_trip_cleanup"] = cleanup_test_rows()
            pg = postgres_payload()
            pg_users_subset = [row for row in pg["users"] if row["username"] in sqlite_users]
            pg_sessions_subset = [row for row in pg["auth_sessions"] if row["token_hash"] in sqlite_session_tokens]
            pg_usernames = {row["username"] for row in pg["users"]}
            pg_session_tokens = {row["token_hash"] for row in pg["auth_sessions"]}
            extra_users = sorted(pg_usernames - set(sqlite_users))
            missing_users = sorted(set(sqlite_users) - pg_usernames)
            extra_sessions = sorted(pg_session_tokens - sqlite_session_tokens)
            missing_sessions = sorted(sqlite_session_tokens - pg_session_tokens)
            pg_user_fp = fingerprint(pg_users_subset)
            pg_session_fp = fingerprint(pg_sessions_subset)
        tests_remaining = test_row_counts()
        parity = (
            user_fp == pg_user_fp
            and session_fp == pg_session_fp
            and len(sqlite["users"]) == len(pg_users_subset)
            and len(sqlite["auth_sessions"]) == len(pg_sessions_subset)
            and not extra_users
            and not missing_users
            and not extra_sessions
            and not missing_sessions
            and tests_remaining == {"users": 0, "auth_sessions": 0}
        )
        result = {
            "sqlite_users": len(sqlite["users"]),
            "postgres_users_total": len(pg["users"]),
            "postgres_users_matching_sqlite": len(pg_users_subset),
            "postgres_users_extra": len(extra_users),
            "postgres_users_missing": len(missing_users),
            "sqlite_auth_sessions": len(sqlite["auth_sessions"]),
            "postgres_auth_sessions_total": len(pg["auth_sessions"]),
            "postgres_auth_sessions_matching_sqlite": len(pg_sessions_subset),
            "postgres_auth_sessions_extra": len(extra_sessions),
            "postgres_auth_sessions_missing": len(missing_sessions),
            "users_fingerprint": user_fp,
            "postgres_users_fingerprint": pg_user_fp,
            "auth_sessions_fingerprint": session_fp,
            "postgres_auth_sessions_fingerprint": pg_session_fp,
            "test_rows_remaining": tests_remaining,
            "parity": parity,
            "round_trip": rt,
            "auth_sessions_snapshot_replace": session_replace,
            "cleanup": cleanup,
            "post_round_trip_cleanup": result.get("post_round_trip_cleanup"),
            "dry_run": args.dry_run,
            "verify_only": args.verify_only,
        }
    finally:
        pass
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["parity"] and (rt is None or rt.get("ok")) else 1

if __name__ == "__main__":
    raise SystemExit(main())
