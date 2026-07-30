#!/usr/bin/env python3
"""Migrate QmDict maintenance/cache documents to PostgreSQL."""

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
WHERE = "lower(path) like '%\\_future_qmdict_%'"


def sqlite_rows() -> list[dict]:
    con = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        rows = []
        for row in con.execute(
            f"SELECT path_key,path,content,encoding,sha256,file_size,file_mtime_ns,updated_at_utc FROM documents WHERE {WHERE} ORDER BY path_key"
        ):
            content = bytes(row["content"] or b"")
            rows.append({
                "path_key": app.clean(row["path_key"]).lower(),
                "path": app.clean(row["path"]),
                "content": content,
                "encoding": app.clean(row["encoding"]) or "utf-8",
                "sha256": app.clean(row["sha256"]) or hashlib.sha256(content).hexdigest(),
                "file_size": int(row["file_size"] or len(content)),
                "file_mtime_ns": int(row["file_mtime_ns"] or 0),
                "updated_at_utc": app.clean(row["updated_at_utc"]),
            })
        return rows
    finally:
        con.close()


def pg_rows() -> list[dict]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT path_key,path,content,encoding,sha256,file_size,file_mtime_ns,updated_at_utc FROM future_server2.documents WHERE lower(path) like '%\\_future_qmdict_%' ORDER BY path_key"
            )
            return [
                {
                    "path_key": app.clean(row[0]).lower(),
                    "path": app.clean(row[1]),
                    "content": bytes(row[2] or b""),
                    "encoding": app.clean(row[3]) or "utf-8",
                    "sha256": app.clean(row[4]),
                    "file_size": int(row[5] or 0),
                    "file_mtime_ns": int(row[6] or 0),
                    "updated_at_utc": app.clean(row[7]),
                }
                for row in cursor.fetchall()
            ]

    return app.postgres_execute(_read)


def public_row(row: dict) -> dict:
    content = bytes(row["content"] or b"")
    return {k: v for k, v in row.items() if k != "content"} | {
        "content_sha256": hashlib.sha256(content).hexdigest(),
        "content_len": len(content),
    }


def fingerprint(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: item["path_key"]):
        digest.update(json.dumps(public_row(row), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def cleanup_test_rows() -> dict:
    def _cleanup(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.documents WHERE path_key like '%codexpgqmdict%'")
            deleted = int(cursor.rowcount or 0)
            cursor.execute("SELECT count(*), coalesce(sum(file_size),0) FROM future_server2.documents WHERE lower(path) like '%\\_future_qmdict_%'")
            row = cursor.fetchone()
        return {"deleted": deleted, "remaining_qmdict_documents": int(row[0] or 0), "remaining_bytes": int(row[1] or 0)}

    return app.postgres_execute(_cleanup)


def round_trip() -> dict:
    content = b'{"version":1,"codex":"qmdict"}'
    row = {
        "path_key": "c:\\server data\\codexpgqmdict\\_future_qmdict_smoke.json",
        "path": r"C:\server data\codexpgqmdict\_future_qmdict_smoke.json",
        "content": content,
        "encoding": "utf-8",
        "sha256": hashlib.sha256(content).hexdigest(),
        "file_size": len(content),
        "file_mtime_ns": 1,
        "updated_at_utc": "2026-07-25T00:00:00Z",
    }
    first = app.postgres_upsert_document_row(row)
    second = app.postgres_upsert_document_row(row)
    return {"first_ok": bool(first.get("ok")), "second_ok": bool(second.get("ok")), "same_sha": first.get("sha256") == second.get("sha256"), "ok": bool(first.get("ok")) and bool(second.get("ok")) and first.get("sha256") == second.get("sha256")}


def parity_result(rt: dict | None = None, cleanup_before: dict | None = None, cleanup_after: dict | None = None, args: argparse.Namespace | None = None) -> dict:
    rows = sqlite_rows()
    pg_all = pg_rows()
    keys = {row["path_key"] for row in rows}
    pg_subset = [row for row in pg_all if row["path_key"] in keys]
    sqlite_fp = fingerprint(rows)
    pg_fp = fingerprint(pg_subset)
    return {
        "sqlite_rows": len(rows),
        "sqlite_bytes": sum(int(row["file_size"] or 0) for row in rows),
        "postgres_selected_total": len(pg_all),
        "postgres_matching_sqlite": len(pg_subset),
        "sqlite_fingerprint": sqlite_fp,
        "postgres_fingerprint": pg_fp,
        "missing": sorted(keys - {row["path_key"] for row in pg_subset})[:20],
        "extra": sorted({row["path_key"] for row in pg_all} - keys)[:20],
        "parity": sqlite_fp == pg_fp and len(rows) == len(pg_subset) and len(pg_all) == len(pg_subset),
        "round_trip": rt,
        "cleanup": {"before": cleanup_before, "after": cleanup_after},
        "dry_run": bool(args and args.dry_run),
        "verify_only": bool(args and args.verify_only),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--cleanup-test-rows", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating QmDict documents to PostgreSQL.")
    app.postgres_initialize_schema()
    cleanup_before = cleanup_test_rows() if args.cleanup_test_rows else None
    cleanup_after = None
    rt = None
    result = {}
    try:
        rows = sqlite_rows()
        if not args.verify_only and not args.dry_run:
            for row in rows:
                app.postgres_upsert_document_row(row)
            rt = round_trip()
        result = parity_result(rt, cleanup_before, cleanup_after, args)
    finally:
        if not args.verify_only and not args.dry_run:
            cleanup_after = cleanup_test_rows()
    if cleanup_after is not None:
        result = parity_result(rt, cleanup_before, cleanup_after, args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("parity") and (rt is None or rt.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
