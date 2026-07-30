#!/usr/bin/env python3
"""Migrate lesson_folder_links metadata to PostgreSQL."""

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
            app.postgres_lesson_folder_link_row_from_source(dict(row))
            for row in con.execute(
                "SELECT link_path,target_path,created_by,created_at_utc,payload_json,revision,status,updated_at_utc "
                "FROM lesson_folder_links ORDER BY lower(link_path)"
            )
        ]
    finally:
        con.close()

def postgres_rows() -> list[dict]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT link_path,target_path,created_by,created_at_utc,payload_json,revision,status,updated_at_utc "
                "FROM future_server2.lesson_folder_links ORDER BY lower(link_path)"
            )
            return [
                app.postgres_lesson_folder_link_row_from_source({
                    "link_path": row[0], "target_path": row[1], "created_by": row[2], "created_at_utc": row[3],
                    "payload_json": row[4], "revision": row[5], "status": row[6], "updated_at_utc": row[7],
                })
                for row in cursor.fetchall()
            ]
    return app.postgres_execute(_read)

def fingerprint(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()

def stable_row(row: dict) -> dict:
    stable = dict(row)
    stable["updated_at_utc"] = ""
    stable["updated_epoch"] = 0
    return stable

def stable_fingerprint(rows: list[dict]) -> str:
    return fingerprint([stable_row(row) for row in rows])

def volatile_timestamp_checks(sqlite_rows: list[dict], pg_rows: list[dict]) -> list[dict]:
    pg_by_link = {row["link_path"]: row for row in pg_rows}
    checks = []
    for row in sqlite_rows:
        pg_row = pg_by_link.get(row["link_path"], {})
        sqlite_epoch = float(row.get("updated_epoch", 0) or 0)
        pg_epoch = float(pg_row.get("updated_epoch", 0) or 0)
        checks.append(
            {
                "link_path": row["link_path"],
                "sqlite_timestamp_present": bool(row.get("updated_at_utc")),
                "postgres_timestamp_present": bool(pg_row.get("updated_at_utc")),
                "sqlite_epoch": sqlite_epoch,
                "postgres_epoch": pg_epoch,
                "status_match": row.get("status") == pg_row.get("status"),
                "revision_match": row.get("revision") == pg_row.get("revision"),
                "ok": bool(row.get("updated_at_utc")) and bool(pg_row.get("updated_at_utc")) and sqlite_epoch > 0 and pg_epoch > 0 and row.get("status") == pg_row.get("status") and row.get("revision") == pg_row.get("revision"),
            }
        )
    return checks

def summarize(rows: list[dict]) -> dict:
    statuses: dict[str, int] = {}
    actors: dict[str, int] = {}
    for row in rows:
        statuses[row["status"]] = statuses.get(row["status"], 0) + 1
        actor = row["created_by"] or ""
        actors[actor] = actors.get(actor, 0) + 1
    return {"rows": len(rows), "status": statuses, "actors": actors}

def cleanup_test_rows() -> dict:
    def _cleanup(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.lesson_folder_links WHERE link_path LIKE 'codex-pg-folder-link/%'")
            deleted = int(cursor.rowcount or 0)
            cursor.execute("SELECT count(*) FROM future_server2.lesson_folder_links")
            remaining = int(cursor.fetchone()[0] or 0)
        return {"deleted": deleted, "remaining": remaining}
    return app.postgres_execute(_cleanup)

def round_trip() -> dict:
    now = app.utc_timestamp()
    row = {
        "link_path": "codex-pg-folder-link/source",
        "target_path": "common/codex-pg-folder-link/target",
        "created_by": "codexpgfolderlink",
        "created_at_utc": now,
        "payload": {"target": "common/codex-pg-folder-link/target", "created_by": "codexpgfolderlink"},
        "revision": 1,
        "status": "active",
        "updated_at_utc": now,
    }
    first = app.postgres_upsert_lesson_folder_link_row(row)
    retry = app.postgres_upsert_lesson_folder_link_row(row)
    return {"write_ok": bool(first.get("ok")), "retry_same_sha": first.get("source_sha256") == retry.get("source_sha256"), "ok": bool(first.get("ok")) and first.get("source_sha256") == retry.get("source_sha256")}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--cleanup-test-rows", action="store_true")
    args = parser.parse_args()
    sqlite = sqlite_rows()
    if args.dry_run and not os.environ.get("FUTURE_PG_DSN"):
        result = {**summarize(sqlite), "fingerprint": fingerprint(sqlite), "dry_run": True, "postgres_pending": "FUTURE_PG_DSN is not set"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating lesson_folder_links to PostgreSQL.")
    app.postgres_initialize_schema()
    cleanup = cleanup_test_rows()
    rt = None
    result = {"parity": False, "round_trip": None}
    try:
        if not args.verify_only and not args.dry_run:
            for row in sqlite:
                app.postgres_upsert_lesson_folder_link_row(row)
        pg_all = postgres_rows()
        links = {row["link_path"] for row in sqlite}
        pg_subset = [row for row in pg_all if row["link_path"] in links]
        sqlite_fp = fingerprint(sqlite)
        pg_fp = fingerprint(pg_subset)
        sqlite_stable_fp = stable_fingerprint(sqlite)
        pg_stable_fp = stable_fingerprint(pg_subset)
        volatile_checks = volatile_timestamp_checks(sqlite, pg_subset)
        stable_parity = sqlite_stable_fp == pg_stable_fp and len(sqlite) == len(pg_subset)
        volatile_ok = all(check.get("ok") for check in volatile_checks)
        rt = None if args.verify_only or args.dry_run else round_trip()
        result = {
            **summarize(sqlite),
            "postgres_total": len(pg_all),
            "postgres_matching_sqlite": len(pg_subset),
            "fingerprint": sqlite_fp,
            "postgres_fingerprint": pg_fp,
            "strict_parity": sqlite_fp == pg_fp and len(sqlite) == len(pg_subset),
            "stable_fingerprint": sqlite_stable_fp,
            "postgres_stable_fingerprint": pg_stable_fp,
            "stable_parity": stable_parity,
            "volatile_timestamp_checks": volatile_checks,
            "volatile_timestamp_ok": volatile_ok,
            "parity": stable_parity and volatile_ok,
            "round_trip": rt,
            "cleanup": cleanup,
            "post_round_trip_cleanup": None,
            "verify_only": args.verify_only,
            "dry_run": args.dry_run,
        }
    finally:
        result["post_round_trip_cleanup"] = cleanup_test_rows()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["parity"] and (rt is None or rt.get("ok")) else 1

if __name__ == "__main__":
    raise SystemExit(main())
