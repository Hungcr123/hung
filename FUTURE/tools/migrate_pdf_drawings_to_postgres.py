#!/usr/bin/env python3
"""Migrate and verify Space_PDF/Picture drawing rows in PostgreSQL.

Production remains SQLite unless FUTURE_DB_PDF_DRAWINGS_BACKEND=postgres is set
for a process. This tool is idempotent and does not modify SQLite.
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
            """
            SELECT username,document_key,page,progress_key,path,identity,title,mode,drawing_json,
                   content_hash,last_operation_id,server_revision,updated_at_utc,updated_epoch,
                   updated_by,deleted,file_id
            FROM pdf_drawings ORDER BY lower(username),document_key,page
            """
        ):
            try:
                drawing = json.loads(row["drawing_json"] or "{}")
            except Exception:
                drawing = {}
            rows.append({
                "username": app.normalize_username(row["username"]),
                "document_key": app.clean(row["document_key"])[:64],
                "page": max(1, app.space_w_int(row["page"], 1)),
                "progress_key": app.clean(row["progress_key"]),
                "path": app.clean_path_value(row["path"]),
                "identity": app.clean(row["identity"]),
                "title": app.clean(row["title"]),
                "mode": app.clean(row["mode"]),
                "drawing": drawing if isinstance(drawing, dict) else {},
                "content_hash": app.clean(row["content_hash"]),
                "last_operation_id": app.clean(row["last_operation_id"]),
                "server_revision": max(1, app.space_w_int(row["server_revision"], 1)),
                "updated_at_utc": app.clean(row["updated_at_utc"]),
                "updated_epoch": max(0.0, float(row["updated_epoch"] or 0.0)),
                "updated_by": app.normalize_username(row["updated_by"]),
                "deleted": bool(row["deleted"]),
                "file_id": app.clean(row["file_id"] or row["identity"]),
            })
        return rows
    finally:
        connection.close()


def canonical_payload(row: dict) -> dict:
    return {
        "username": row["username"].lower(),
        "document_key": row["document_key"],
        "page": int(row["page"]),
        "progress_key": row["progress_key"],
        "path": row["path"],
        "identity": row["identity"],
        "title": row["title"],
        "mode": row["mode"],
        "drawing": row.get("drawing") or {},
        "content_hash": row["content_hash"],
        "last_operation_id": row["last_operation_id"],
        "server_revision": int(row["server_revision"]),
        "updated_at_utc": row["updated_at_utc"],
        "updated_epoch": float(row["updated_epoch"]),
        "updated_by": row["updated_by"],
        "deleted": bool(row["deleted"]),
        "file_id": row["file_id"],
    }


def fingerprint(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: (item["username"].lower(), item["document_key"], int(item["page"]))):
        digest.update(json.dumps(canonical_payload(row), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def postgres_rows() -> list[dict]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT username,document_key,page,progress_key,path,identity,title,mode,drawing_json,
                       content_hash,last_operation_id,server_revision,updated_at_utc,updated_epoch,
                       updated_by,deleted,file_id
                FROM future_server2.pdf_drawings ORDER BY lower(username),document_key,page
                """
            )
            rows = []
            for row in cursor.fetchall():
                rows.append({
                    "username": app.normalize_username(row[0]),
                    "document_key": app.clean(row[1])[:64],
                    "page": max(1, app.space_w_int(row[2], 1)),
                    "progress_key": app.clean(row[3]),
                    "path": app.clean_path_value(row[4]),
                    "identity": app.clean(row[5]),
                    "title": app.clean(row[6]),
                    "mode": app.clean(row[7]),
                    "drawing": dict(row[8]) if isinstance(row[8], dict) else {},
                    "content_hash": app.clean(row[9]),
                    "last_operation_id": app.clean(row[10]),
                    "server_revision": max(1, app.space_w_int(row[11], 1)),
                    "updated_at_utc": app.clean(row[12]),
                    "updated_epoch": max(0.0, float(row[13] or 0.0)),
                    "updated_by": app.normalize_username(row[14]),
                    "deleted": bool(row[15]),
                    "file_id": app.clean(row[16]),
                })
            return rows

    return app.postgres_execute(_read)


def cleanup_test_rows() -> dict:
    def _cleanup(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.pdf_drawings WHERE lower(username) LIKE 'codexpg%'")
            deleted = int(cursor.rowcount or 0)
            cursor.execute("SELECT count(*) FROM future_server2.pdf_drawings")
            remaining = int(cursor.fetchone()[0] or 0)
        return {"deleted": deleted, "remaining": remaining}

    return app.postgres_execute(_cleanup)


def test_backend_round_trip(username: str) -> dict:
    os.environ["FUTURE_DB_PDF_DRAWINGS_BACKEND"] = "postgres"
    marker = app.utc_timestamp()
    document_key = "codexpgdrawingdoc"
    page = 3
    row = {
        "progress_key": "codexpgdrawingprogress",
        "path": "common/File 02 - {7}.Space_V",
        "identity": "ftg-lesson-codex-pdf-drawing",
        "file_id": "ftg-lesson-codex-pdf-drawing",
        "title": "Codex PDF Drawing",
        "mode": "pdf",
        "drawing": {"page": page, "dataUrl": "", "vector": {"version": 2, "width": 1000, "height": 1000, "items": []}, "updatedAt": marker, "updatedBy": username},
        "last_operation_id": "codex-pg-drawing-op-1",
        "deleted": False,
        "updated_at_utc": marker,
        "updated_epoch": app.timestamp_to_epoch(marker),
        "updated_by": username,
    }
    saved = app.server_database_write_pdf_drawing_row(username, document_key, page, row)
    read = app.server_database_read_pdf_drawing_row(username, document_key, page)
    duplicate = app.server_database_write_pdf_drawing_row(username, document_key, page, row)
    removed = app.server_database_write_pdf_drawing_row(username, document_key, page, remove=True)
    after_remove = app.server_database_read_pdf_drawing_row(username, document_key, page)
    return {
        "username": username,
        "saved_revision": app.space_w_int(saved.get("server_revision"), 0),
        "read_revision": app.space_w_int(read.get("server_revision"), 0),
        "duplicate_revision": app.space_w_int(duplicate.get("server_revision"), 0),
        "removed": bool(removed.get("removed")),
        "present_after_remove": bool(after_remove),
        "ok": app.space_w_int(saved.get("server_revision"), 0) >= 1 and app.space_w_int(read.get("server_revision"), 0) >= 1 and app.space_w_int(duplicate.get("server_revision"), 0) >= app.space_w_int(read.get("server_revision"), 0) and bool(removed.get("removed")) and not after_remove,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--cleanup-test-rows", action="store_true")
    parser.add_argument("--round-trip-user", default="codexpgdrawing")
    args = parser.parse_args()
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating pdf_drawings to PostgreSQL.")
    app.postgres_initialize_schema()
    cleanup = cleanup_test_rows() if args.cleanup_test_rows else None
    rows = sqlite_rows()
    if not args.verify_only and not args.dry_run:
        for row in rows:
            app.postgres_upsert_pdf_drawing_row(row)
    pg_rows = postgres_rows()
    sqlite_keys = {(row["username"].lower(), row["document_key"], int(row["page"])) for row in rows}
    pg_subset = [row for row in pg_rows if (row["username"].lower(), row["document_key"], int(row["page"])) in sqlite_keys]
    sqlite_fp = fingerprint(rows)
    pg_fp = fingerprint(pg_subset)
    round_trip = None
    if not args.verify_only and not args.dry_run:
        round_trip = test_backend_round_trip(args.round_trip_user)
    result = {
        "sqlite_rows": len(rows),
        "postgres_rows_total": len(pg_rows),
        "postgres_rows_matching_sqlite": len(pg_subset),
        "sqlite_fingerprint": sqlite_fp,
        "postgres_fingerprint_for_sqlite": pg_fp,
        "parity": sqlite_fp == pg_fp and len(rows) == len(pg_subset),
        "round_trip": round_trip,
        "cleanup": cleanup,
        "dry_run": args.dry_run,
        "verify_only": args.verify_only,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["parity"] and (round_trip is None or round_trip.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
