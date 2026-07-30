#!/usr/bin/env python3
"""Migrate canonical lesson_files and lesson_file_replicas metadata to PostgreSQL."""

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
        files = [
            app.postgres_lesson_file_row_from_source(dict(row))
            for row in con.execute(
                "SELECT file_id,space_id,kind,canonical_fingerprint,identity_revision,status,created_at_utc,updated_at_utc,deleted_at_utc "
                "FROM lesson_files ORDER BY file_id"
            )
        ]
        replicas = [
            app.postgres_lesson_file_replica_row_from_source(dict(row))
            for row in con.execute(
                "SELECT replica_id,file_id,normalized_path,fingerprint,file_mtime_ns,file_size,status,first_seen_at_utc,last_seen_at_utc "
                "FROM lesson_file_replicas ORDER BY replica_id"
            )
        ]
        return {"lesson_files": files, "lesson_file_replicas": replicas}
    finally:
        con.close()

def postgres_payload() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT file_id,space_id,kind,canonical_fingerprint,identity_revision,status,created_at_utc,updated_at_utc,deleted_at_utc "
                "FROM future_server2.lesson_files ORDER BY file_id"
            )
            files = [app.postgres_lesson_file_row_from_source({
                "file_id": row[0], "space_id": row[1], "kind": row[2], "canonical_fingerprint": row[3],
                "identity_revision": row[4], "status": row[5], "created_at_utc": row[6],
                "updated_at_utc": row[7], "deleted_at_utc": row[8],
            }) for row in cursor.fetchall()]
            cursor.execute(
                "SELECT replica_id,file_id,normalized_path,fingerprint,file_mtime_ns,file_size,status,first_seen_at_utc,last_seen_at_utc "
                "FROM future_server2.lesson_file_replicas ORDER BY replica_id"
            )
            replicas = [app.postgres_lesson_file_replica_row_from_source({
                "replica_id": row[0], "file_id": row[1], "normalized_path": row[2], "fingerprint": row[3],
                "file_mtime_ns": row[4], "file_size": row[5], "status": row[6],
                "first_seen_at_utc": row[7], "last_seen_at_utc": row[8],
            }) for row in cursor.fetchall()]
        return {"lesson_files": files, "lesson_file_replicas": replicas}

    return app.postgres_execute(_read)

def fingerprint(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()

def summarize(payload: dict) -> dict:
    files = payload["lesson_files"]
    replicas = payload["lesson_file_replicas"]
    file_status: dict[str, int] = {}
    replica_status: dict[str, int] = {}
    kinds: dict[str, int] = {}
    for row in files:
        file_status[row["status"]] = file_status.get(row["status"], 0) + 1
        kinds[row["kind"]] = kinds.get(row["kind"], 0) + 1
    for row in replicas:
        replica_status[row["status"]] = replica_status.get(row["status"], 0) + 1
    return {
        "lesson_files": len(files),
        "lesson_file_replicas": len(replicas),
        "file_status": file_status,
        "replica_status": replica_status,
        "kinds": kinds,
    }

def cleanup_test_rows() -> dict:
    def _cleanup(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.lesson_file_replicas WHERE file_id LIKE 'ftg-lesson-codexpg-file%' OR normalized_path LIKE 'codex-pg-file/%'")
            deleted_replicas = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.lesson_files WHERE file_id LIKE 'ftg-lesson-codexpg-file%'")
            deleted_files = int(cursor.rowcount or 0)
            cursor.execute("SELECT count(*) FROM future_server2.lesson_files")
            files = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT count(*) FROM future_server2.lesson_file_replicas")
            replicas = int(cursor.fetchone()[0] or 0)
        return {"deleted_files": deleted_files, "deleted_replicas": deleted_replicas, "lesson_files": files, "lesson_file_replicas": replicas}

    return app.postgres_execute(_cleanup)

def round_trip() -> dict:
    now = app.utc_timestamp()
    file_row = {
        "file_id": "ftg-lesson-codexpg-file",
        "space_id": "space-codexpg",
        "kind": "space",
        "canonical_fingerprint": "codexpgfingerprint",
        "identity_revision": 1,
        "status": "active",
        "created_at_utc": now,
        "updated_at_utc": now,
        "deleted_at_utc": "",
    }
    replica_row = {
        "replica_id": 930100001,
        "file_id": "ftg-lesson-codexpg-file",
        "normalized_path": "codex-pg-file/sample.Space_V",
        "fingerprint": "codexpgfingerprint",
        "file_mtime_ns": 1,
        "file_size": 2,
        "status": "active",
        "first_seen_at_utc": now,
        "last_seen_at_utc": now,
    }
    first = app.postgres_upsert_lesson_file_row(file_row)
    second = app.postgres_upsert_lesson_file_replica_row(replica_row)
    retry = app.postgres_upsert_lesson_file_replica_row(replica_row)
    return {
        "file_ok": bool(first.get("ok")),
        "replica_ok": bool(second.get("ok")),
        "retry_same_sha": second.get("source_sha256") == retry.get("source_sha256"),
        "ok": bool(first.get("ok")) and bool(second.get("ok")) and second.get("source_sha256") == retry.get("source_sha256"),
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
            "lesson_files_fingerprint": fingerprint(sqlite["lesson_files"]),
            "lesson_file_replicas_fingerprint": fingerprint(sqlite["lesson_file_replicas"]),
            "dry_run": True,
            "postgres_pending": "FUTURE_PG_DSN is not set",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating lesson_files to PostgreSQL.")
    app.postgres_initialize_schema()
    cleanup = cleanup_test_rows() if args.cleanup_test_rows else None
    if not args.verify_only and not args.dry_run:
        for row in sqlite["lesson_files"]:
            app.postgres_upsert_lesson_file_row(row)
        for row in sqlite["lesson_file_replicas"]:
            app.postgres_upsert_lesson_file_replica_row(row)
    pg = postgres_payload()
    file_ids = {row["file_id"] for row in sqlite["lesson_files"]}
    replica_ids = {row["replica_id"] for row in sqlite["lesson_file_replicas"]}
    pg_files = [row for row in pg["lesson_files"] if row["file_id"] in file_ids]
    pg_replicas = [row for row in pg["lesson_file_replicas"] if row["replica_id"] in replica_ids]
    file_fp = fingerprint(sqlite["lesson_files"])
    pg_file_fp = fingerprint(pg_files)
    replica_fp = fingerprint(sqlite["lesson_file_replicas"])
    pg_replica_fp = fingerprint(pg_replicas)
    rt = None
    final_cleanup = None
    if not args.verify_only and not args.dry_run:
        try:
            rt = round_trip()
        finally:
            final_cleanup = cleanup_test_rows()
    result = {
        **summarize(sqlite),
        "postgres_lesson_files_total": len(pg["lesson_files"]),
        "postgres_lesson_files_matching_sqlite": len(pg_files),
        "postgres_lesson_file_replicas_total": len(pg["lesson_file_replicas"]),
        "postgres_lesson_file_replicas_matching_sqlite": len(pg_replicas),
        "lesson_files_fingerprint": file_fp,
        "postgres_lesson_files_fingerprint": pg_file_fp,
        "lesson_file_replicas_fingerprint": replica_fp,
        "postgres_lesson_file_replicas_fingerprint": pg_replica_fp,
        "parity": file_fp == pg_file_fp and replica_fp == pg_replica_fp and len(sqlite["lesson_files"]) == len(pg_files) and len(sqlite["lesson_file_replicas"]) == len(pg_replicas),
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
