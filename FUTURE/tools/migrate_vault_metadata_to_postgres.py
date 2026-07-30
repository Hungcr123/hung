#!/usr/bin/env python3
"""Migrate Lesson Vault folder/entry/revision metadata to PostgreSQL."""

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
        folders = [app.postgres_vault_folder_row_from_source(dict(row)) for row in con.execute(
            "SELECT vault_folder_id,username,parent_folder_id,display_name,folder_type,source_path,sort_order,status,created_at_utc,updated_at_utc FROM vault_folders ORDER BY vault_folder_id"
        )]
        entries = [app.postgres_vault_entry_row_from_source(dict(row)) for row in con.execute(
            "SELECT vault_entry_id,username,parent_folder_id,lesson_id,entry_type,physical_replica_id,source_entry_id,source_path,display_name,sort_order,status,created_at_utc,updated_at_utc FROM vault_entries ORDER BY vault_entry_id"
        )]
        revisions = [app.postgres_vault_revision_row_from_source(dict(row)) for row in con.execute(
            "SELECT username,revision,updated_at_utc FROM vault_revisions ORDER BY lower(username)"
        )]
        return {"vault_folders": folders, "vault_entries": entries, "vault_revisions": revisions}
    finally:
        con.close()

def postgres_payload() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT vault_folder_id,username,parent_folder_id,display_name,folder_type,source_path,sort_order,status,created_at_utc,updated_at_utc FROM future_server2.vault_folders ORDER BY vault_folder_id")
            folders = [app.postgres_vault_folder_row_from_source({
                "vault_folder_id": row[0], "username": row[1], "parent_folder_id": row[2], "display_name": row[3],
                "folder_type": row[4], "source_path": row[5], "sort_order": row[6], "status": row[7],
                "created_at_utc": row[8], "updated_at_utc": row[9],
            }) for row in cursor.fetchall()]
            cursor.execute("SELECT vault_entry_id,username,parent_folder_id,lesson_id,entry_type,physical_replica_id,source_entry_id,source_path,display_name,sort_order,status,created_at_utc,updated_at_utc FROM future_server2.vault_entries ORDER BY vault_entry_id")
            entries = [app.postgres_vault_entry_row_from_source({
                "vault_entry_id": row[0], "username": row[1], "parent_folder_id": row[2], "lesson_id": row[3],
                "entry_type": row[4], "physical_replica_id": row[5], "source_entry_id": row[6], "source_path": row[7],
                "display_name": row[8], "sort_order": row[9], "status": row[10], "created_at_utc": row[11], "updated_at_utc": row[12],
            }) for row in cursor.fetchall()]
            cursor.execute("SELECT username,revision,updated_at_utc FROM future_server2.vault_revisions ORDER BY lower(username)")
            revisions = [app.postgres_vault_revision_row_from_source({"username": row[0], "revision": row[1], "updated_at_utc": row[2]}) for row in cursor.fetchall()]
        return {"vault_folders": folders, "vault_entries": entries, "vault_revisions": revisions}

    return app.postgres_execute(_read)

def cleanup_test_rows() -> dict:
    def _cleanup(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.vault_entries WHERE username LIKE 'codexpgvault%' OR vault_entry_id LIKE 'codex-pg-vault-%'")
            deleted_entries = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.vault_folders WHERE username LIKE 'codexpgvault%' OR vault_folder_id LIKE 'codex-pg-vault-%'")
            deleted_folders = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.vault_revisions WHERE username LIKE 'codexpgvault%'")
            deleted_revisions = int(cursor.rowcount or 0)
        return {"deleted_folders": deleted_folders, "deleted_entries": deleted_entries, "deleted_revisions": deleted_revisions}

    return app.postgres_execute(_cleanup)

def round_trip() -> dict:
    now = app.utc_timestamp()
    folder = {"vault_folder_id": "codex-pg-vault-folder", "username": "codexpgvault", "parent_folder_id": "", "display_name": "Codex Vault", "folder_type": "VIRTUAL", "source_path": "", "sort_order": 1, "status": "active", "created_at_utc": now, "updated_at_utc": now}
    entry = {"vault_entry_id": "codex-pg-vault-entry", "username": "codexpgvault", "parent_folder_id": "codex-pg-vault-folder", "lesson_id": "ftg-lesson-codexpg-file", "entry_type": "LESSON", "physical_replica_id": None, "source_entry_id": "", "source_path": "codex-pg-vault/sample.Space_V", "display_name": "Sample", "sort_order": 1, "status": "active", "created_at_utc": now, "updated_at_utc": now}
    rev = {"username": "codexpgvault", "revision": 2, "updated_at_utc": now}
    f = app.postgres_upsert_vault_folder_row(folder)
    e = app.postgres_upsert_vault_entry_row(entry)
    r = app.postgres_upsert_vault_revision_row(rev)
    return {"folder_ok": bool(f.get("ok")), "entry_ok": bool(e.get("ok")), "revision_ok": bool(r.get("ok")), "ok": bool(f.get("ok")) and bool(e.get("ok")) and bool(r.get("ok"))}

def fingerprint(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()

def summarize(payload: dict) -> dict:
    status_folders: dict[str, int] = {}
    entry_types: dict[str, int] = {}
    status_entries: dict[str, int] = {}
    users = set()
    for row in payload["vault_folders"]:
        status_folders[row["status"]] = status_folders.get(row["status"], 0) + 1
        users.add(row["username"])
    for row in payload["vault_entries"]:
        entry_types[row["entry_type"]] = entry_types.get(row["entry_type"], 0) + 1
        status_entries[row["status"]] = status_entries.get(row["status"], 0) + 1
        users.add(row["username"])
    return {
        "vault_folders": len(payload["vault_folders"]),
        "vault_entries": len(payload["vault_entries"]),
        "vault_revisions": len(payload["vault_revisions"]),
        "users": len([user for user in users if user]),
        "folder_status": status_folders,
        "entry_status": status_entries,
        "entry_types": entry_types,
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
            **summarize(sqlite),
            "vault_folders_fingerprint": fingerprint(sqlite["vault_folders"]),
            "vault_entries_fingerprint": fingerprint(sqlite["vault_entries"]),
            "vault_revisions_fingerprint": fingerprint(sqlite["vault_revisions"]),
            "dry_run": True,
            "postgres_pending": "FUTURE_PG_DSN is not set",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating Vault metadata to PostgreSQL.")
    app.postgres_initialize_schema()
    cleanup = cleanup_test_rows()
    rt = None
    result = {"parity": False, "round_trip": None}
    try:
        if not args.verify_only and not args.dry_run:
            for row in sqlite["vault_folders"]:
                app.postgres_upsert_vault_folder_row(row)
            for row in sqlite["vault_entries"]:
                app.postgres_upsert_vault_entry_row(row)
            for row in sqlite["vault_revisions"]:
                app.postgres_upsert_vault_revision_row(row)
        pg = postgres_payload()
        folder_ids = {row["vault_folder_id"] for row in sqlite["vault_folders"]}
        entry_ids = {row["vault_entry_id"] for row in sqlite["vault_entries"]}
        rev_users = {row["username"] for row in sqlite["vault_revisions"]}
        pg_folders = [row for row in pg["vault_folders"] if row["vault_folder_id"] in folder_ids]
        pg_entries = [row for row in pg["vault_entries"] if row["vault_entry_id"] in entry_ids]
        pg_revisions = [row for row in pg["vault_revisions"] if row["username"] in rev_users]
        rt = None if args.verify_only or args.dry_run else round_trip()
        result = {
            **summarize(sqlite),
            "vault_folders_fingerprint": fingerprint(sqlite["vault_folders"]),
            "postgres_vault_folders_fingerprint": fingerprint(pg_folders),
            "vault_entries_fingerprint": fingerprint(sqlite["vault_entries"]),
            "postgres_vault_entries_fingerprint": fingerprint(pg_entries),
            "vault_revisions_fingerprint": fingerprint(sqlite["vault_revisions"]),
            "postgres_vault_revisions_fingerprint": fingerprint(pg_revisions),
            "postgres_vault_folders_matching_sqlite": len(pg_folders),
            "postgres_vault_entries_matching_sqlite": len(pg_entries),
            "postgres_vault_revisions_matching_sqlite": len(pg_revisions),
            "parity": fingerprint(sqlite["vault_folders"]) == fingerprint(pg_folders) and fingerprint(sqlite["vault_entries"]) == fingerprint(pg_entries) and fingerprint(sqlite["vault_revisions"]) == fingerprint(pg_revisions),
            "round_trip": rt,
            "cleanup": cleanup,
            "post_round_trip_cleanup": None,
            "verify_only": args.verify_only,
            "dry_run": args.dry_run,
        }
    finally:
        result["post_round_trip_cleanup"] = cleanup_test_rows()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("parity") and (rt is None or rt.get("ok")) else 1

if __name__ == "__main__":
    raise SystemExit(main())
