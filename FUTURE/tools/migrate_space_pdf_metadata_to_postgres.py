#!/usr/bin/env python3
"""Migrate Space PDF/Picture canonical package metadata to PostgreSQL."""

from __future__ import annotations

import argparse, hashlib, json, os, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app  # noqa: E402

DATABASE = Path(r"C:\server data\server2.db")

TABLES = {
    "documents": ("space_pdf_documents", app.postgres_space_pdf_document_row_from_source, app.postgres_upsert_space_pdf_document_row),
    "lesson_meta": ("space_pdf_lesson_meta", app.postgres_space_pdf_lesson_meta_row_from_source, app.postgres_upsert_space_pdf_lesson_meta_row),
    "package_replicas": ("space_pdf_package_replicas", app.postgres_space_pdf_package_replica_row_from_source, app.postgres_upsert_space_pdf_package_replica_row),
}

def sqlite_payload() -> dict:
    con = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        return {
            "documents": [TABLES["documents"][1](dict(row)) for row in con.execute("SELECT * FROM space_pdf_documents ORDER BY document_id")],
            "lesson_meta": [TABLES["lesson_meta"][1](dict(row)) for row in con.execute("SELECT * FROM space_pdf_lesson_meta ORDER BY file_id")],
            "package_replicas": [TABLES["package_replicas"][1](dict(row)) for row in con.execute("SELECT * FROM space_pdf_package_replicas ORDER BY lower(normalized_path)")],
        }
    finally:
        con.close()

def postgres_payload() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT document_id,source_sha256,source_bytes,mime_type,page_count,status,created_at_utc,updated_at_utc,asset_id,asset_locator FROM future_server2.space_pdf_documents ORDER BY document_id")
            docs = [app.postgres_space_pdf_document_row_from_source({"document_id": r[0], "source_sha256": r[1], "source_bytes": r[2], "mime_type": r[3], "page_count": r[4], "status": r[5], "created_at_utc": r[6], "updated_at_utc": r[7], "asset_id": r[8], "asset_locator": r[9]}) for r in cursor.fetchall()]
            cursor.execute("SELECT file_id,document_id,schema_version,package_revision,title,owner_scope,source_filename,source_sha256,package_fingerprint,status,created_at_utc,updated_at_utc,space_id,asset_id,asset_locator FROM future_server2.space_pdf_lesson_meta ORDER BY file_id")
            meta = [app.postgres_space_pdf_lesson_meta_row_from_source({"file_id": r[0], "document_id": r[1], "schema_version": r[2], "package_revision": r[3], "title": r[4], "owner_scope": r[5], "source_filename": r[6], "source_sha256": r[7], "package_fingerprint": r[8], "status": r[9], "created_at_utc": r[10], "updated_at_utc": r[11], "space_id": r[12], "asset_id": r[13], "asset_locator": r[14]}) for r in cursor.fetchall()]
            cursor.execute("SELECT normalized_path,file_id,document_id,package_sha256,semantic_fingerprint,schema_version,package_revision,status,first_seen_at_utc,last_seen_at_utc,space_id FROM future_server2.space_pdf_package_replicas ORDER BY lower(normalized_path)")
            reps = [app.postgres_space_pdf_package_replica_row_from_source({"normalized_path": r[0], "file_id": r[1], "document_id": r[2], "package_sha256": r[3], "semantic_fingerprint": r[4], "schema_version": r[5], "package_revision": r[6], "status": r[7], "first_seen_at_utc": r[8], "last_seen_at_utc": r[9], "space_id": r[10]}) for r in cursor.fetchall()]
        return {"documents": docs, "lesson_meta": meta, "package_replicas": reps}
    return app.postgres_execute(_read)

def fp(rows):
    h = hashlib.sha256()
    encoded_rows = [
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        for row in rows
    ]
    for row in sorted(encoded_rows):
        h.update(row.encode("utf-8")); h.update(b"\n")
    return h.hexdigest()

def cleanup_test_rows() -> dict:
    def _cleanup(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.space_pdf_package_replicas WHERE file_id LIKE 'codex-pg-space-pdf-%' OR normalized_path LIKE 'codex-pg-space-pdf/%'")
            replicas = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.space_pdf_lesson_meta WHERE file_id LIKE 'codex-pg-space-pdf-%'")
            meta = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.space_pdf_documents WHERE document_id LIKE 'codex-pg-space-pdf-%'")
            documents = int(cursor.rowcount or 0)
        return {"documents": documents, "lesson_meta": meta, "package_replicas": replicas}
    return app.postgres_execute(_cleanup)

def round_trip() -> dict:
    now = app.utc_timestamp()
    doc = {
        "document_id": "codex-pg-space-pdf-document",
        "source_sha256": "codex-pg-source",
        "source_bytes": 123,
        "mime_type": "application/pdf",
        "page_count": 2,
        "status": "active",
        "created_at_utc": now,
        "updated_at_utc": now,
        "asset_id": "codex-pg-space-pdf-asset",
        "asset_locator": "_assets/pdf/codex-pg-space-pdf.pdf",
    }
    meta = {
        "file_id": "codex-pg-space-pdf-file",
        "document_id": doc["document_id"],
        "schema_version": 2,
        "package_revision": 1,
        "title": "Codex PG Space PDF",
        "owner_scope": "codex",
        "source_filename": "codex.pdf",
        "source_sha256": doc["source_sha256"],
        "package_fingerprint": "codex-pg-fingerprint",
        "status": "active",
        "created_at_utc": now,
        "updated_at_utc": now,
        "space_id": "Space_PDF",
        "asset_id": doc["asset_id"],
        "asset_locator": doc["asset_locator"],
    }
    replica = {
        "normalized_path": "codex-pg-space-pdf/codex.space_pdf",
        "file_id": meta["file_id"],
        "document_id": doc["document_id"],
        "package_sha256": "codex-pg-package",
        "semantic_fingerprint": meta["package_fingerprint"],
        "schema_version": 2,
        "package_revision": 1,
        "status": "active",
        "first_seen_at_utc": now,
        "last_seen_at_utc": now,
        "space_id": "Space_PDF",
    }
    first = [
        app.postgres_upsert_space_pdf_document_row(doc),
        app.postgres_upsert_space_pdf_lesson_meta_row(meta),
        app.postgres_upsert_space_pdf_package_replica_row(replica),
    ]
    retry = [
        app.postgres_upsert_space_pdf_document_row(doc),
        app.postgres_upsert_space_pdf_lesson_meta_row(meta),
        app.postgres_upsert_space_pdf_package_replica_row(replica),
    ]
    return {
        "write_ok": all(bool(row.get("ok")) for row in first),
        "retry_same_sha": [a.get("row_sha256") or a.get("source_sha256") for a in first] == [b.get("row_sha256") or b.get("source_sha256") for b in retry],
        "ok": all(bool(row.get("ok")) for row in first) and ([a.get("row_sha256") or a.get("source_sha256") for a in first] == [b.get("row_sha256") or b.get("source_sha256") for b in retry]),
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--cleanup-test-rows", action="store_true")
    args = ap.parse_args()
    sqlite = sqlite_payload()
    result = {
        "documents": len(sqlite["documents"]),
        "lesson_meta": len(sqlite["lesson_meta"]),
        "package_replicas": len(sqlite["package_replicas"]),
        "documents_fingerprint": fp(sqlite["documents"]),
        "lesson_meta_fingerprint": fp(sqlite["lesson_meta"]),
        "package_replicas_fingerprint": fp(sqlite["package_replicas"]),
    }
    if args.dry_run and not os.environ.get("FUTURE_PG_DSN"):
        result.update({"dry_run": True, "postgres_pending": "FUTURE_PG_DSN is not set"})
        print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating space_pdf metadata to PostgreSQL.")
    app.postgres_initialize_schema()
    cleanup = cleanup_test_rows()
    rt = None
    try:
        if not args.verify_only and not args.dry_run:
            for key, rows in sqlite.items():
                upsert = TABLES[key][2]
                for row in rows:
                    upsert(row)
        pg = postgres_payload()
        rt = None if args.verify_only or args.dry_run else round_trip()
        result.update({
            "postgres_documents": len(pg["documents"]),
            "postgres_lesson_meta": len(pg["lesson_meta"]),
            "postgres_package_replicas": len(pg["package_replicas"]),
            "postgres_documents_fingerprint": fp(pg["documents"]),
            "postgres_lesson_meta_fingerprint": fp(pg["lesson_meta"]),
            "postgres_package_replicas_fingerprint": fp(pg["package_replicas"]),
            "parity": fp(sqlite["documents"]) == fp(pg["documents"]) and fp(sqlite["lesson_meta"]) == fp(pg["lesson_meta"]) and fp(sqlite["package_replicas"]) == fp(pg["package_replicas"]),
            "round_trip": rt,
            "cleanup": cleanup,
            "post_round_trip_cleanup": None,
            "verify_only": args.verify_only,
        })
    finally:
        result["post_round_trip_cleanup"] = cleanup_test_rows()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["parity"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
