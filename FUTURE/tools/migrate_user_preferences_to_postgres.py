#!/usr/bin/env python3
"""Migrate and verify the user_preferences vertical slice in PostgreSQL.

Requires FUTURE_PG_DSN. Does not change production feature flags or cut over
Server 2. SQLite remains authoritative unless FUTURE_DB_USER_PREFERENCES_BACKEND
is explicitly set to postgres for a process.
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


def sqlite_rows() -> list[dict]:
    connection = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True, timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        rows = []
        for row in connection.execute(
            "SELECT username,preferences_json,server_revision,updated_at_utc,updated_epoch "
            "FROM user_preferences ORDER BY lower(username)"
        ):
            try:
                preferences = json.loads(str(row["preferences_json"] or "{}"))
            except Exception:
                preferences = {}
            rows.append({
                "username": app.normalize_username(row["username"]),
                "preferences": preferences if isinstance(preferences, dict) else {},
                "server_revision": max(1, int(row["server_revision"] or 1)),
                "updated_at": app.clean(row["updated_at_utc"]),
                "updated_epoch": max(0.0, float(row["updated_epoch"] or 0)),
            })
        return rows
    finally:
        connection.close()


def fingerprint(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: item["username"].lower()):
        payload = {
            "username": row["username"].lower(),
            "preferences": row.get("preferences") or {},
            "server_revision": max(1, int(row.get("server_revision", 1) or 1)),
            "updated_at": app.clean(row.get("updated_at")),
            "updated_epoch": max(0.0, float(row.get("updated_epoch", 0) or 0)),
        }
        digest.update(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def postgres_rows() -> list[dict]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT username,preferences_json,server_revision,updated_at_utc,updated_epoch "
                "FROM future_server2.user_preferences ORDER BY lower(username)"
            )
            rows = []
            for row in cursor.fetchall():
                rows.append({
                    "username": app.normalize_username(row[0]),
                    "preferences": row[1] if isinstance(row[1], dict) else {},
                    "server_revision": max(1, int(row[2] or 1)),
                    "updated_at": app.clean(row[3]),
                    "updated_epoch": max(0.0, float(row[4] or 0)),
                })
            return rows

    return app.postgres_execute(_read)


def test_adapter_round_trip(username: str) -> dict:
    before = app.postgres_load_user_preferences(username)
    marker = app.utc_timestamp()
    voice_marker = f"codex-postgres-adapter-{marker}"
    written = app.postgres_save_user_preferences(username, {
        "pdf_settings": {
            "ui": {
                "aiNoticeVoice": voice_marker,
                "aiNoticeSpeakMode": "off",
            }
        }
    })
    after = app.postgres_load_user_preferences(username)
    after_preferences = after.get("preferences") or {}
    after_pdf = after_preferences.get("pdf_settings") if isinstance(after_preferences.get("pdf_settings"), dict) else {}
    after_ui = after_pdf.get("ui") if isinstance(after_pdf.get("ui"), dict) else {}
    read_marker = str(after_ui.get("aiNoticeVoice") or "")
    return {
        "username": username,
        "before_revision": int(before.get("server_revision", 0) or 0) if before else 0,
        "written_revision": int(written.get("server_revision", 0) or 0),
        "after_revision": int(after.get("server_revision", 0) or 0),
        "changed": bool(written.get("changed")),
        "read_marker": read_marker,
        "expected_marker": voice_marker,
        "ok": bool(written.get("changed") and read_marker == voice_marker),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--round-trip-user", default="codexpgprefs")
    args = parser.parse_args()
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating user_preferences to PostgreSQL.")
    rows = sqlite_rows()
    app.postgres_initialize_schema()
    if not args.verify_only and not args.dry_run:
        for row in rows:
            app.postgres_upsert_user_preferences_row(row)
    pg_rows = postgres_rows()
    sqlite_fp = fingerprint(rows)
    pg_subset = [row for row in pg_rows if row["username"].lower() in {item["username"].lower() for item in rows}]
    pg_fp = fingerprint(pg_subset)
    round_trip = None
    if not args.verify_only and not args.dry_run:
        round_trip = test_adapter_round_trip(args.round_trip_user)
    result = {
        "sqlite_rows": len(rows),
        "postgres_rows_total": len(pg_rows),
        "postgres_rows_matching_sqlite_users": len(pg_subset),
        "sqlite_fingerprint": sqlite_fp,
        "postgres_fingerprint_for_sqlite_users": pg_fp,
        "parity": sqlite_fp == pg_fp and len(rows) == len(pg_subset),
        "round_trip": round_trip,
        "dry_run": args.dry_run,
        "verify_only": args.verify_only,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["parity"] and (round_trip is None or round_trip.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
