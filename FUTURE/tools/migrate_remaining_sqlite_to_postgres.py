#!/usr/bin/env python3
"""Offline-only migration for SQLite tables not yet covered by PostgreSQL.

This tool is intentionally not imported by Server 2 runtime. It reads the
closed/quiesced SQLite files and copies the remaining tables into PostgreSQL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

import psycopg

SERVER2_DB = Path(r"C:\server data\server2.db")
STRUCTURE_DB = Path(r"C:\server data\structure_assets.db")
SCHEMA = "future_server2"

TABLES: dict[str, dict[str, Any]] = {
    "server_load_test_credentials": {
        "db": SERVER2_DB,
        "columns": ["username", "password_hash", "updated_at_utc"],
        "pk": ["username"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS future_server2.server_load_test_credentials (
                username text PRIMARY KEY REFERENCES future_server2.users(username) ON DELETE CASCADE,
                password_hash text NOT NULL,
                updated_at_utc text NOT NULL
            )
        """,
    },
    "space_pdf_drawing_migration_sources": {
        "db": SERVER2_DB,
        "columns": ["username", "file_id", "page", "source_document_key", "row_json", "is_winner"],
        "pk": ["username", "file_id", "page", "source_document_key"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS future_server2.space_pdf_drawing_migration_sources (
                username text NOT NULL,
                file_id text NOT NULL,
                page integer NOT NULL,
                source_document_key text NOT NULL,
                row_json text NOT NULL,
                is_winner integer NOT NULL DEFAULT 0,
                PRIMARY KEY(username, file_id, page, source_document_key)
            )
        """,
    },
    "space_pdf_drawing_shadow": {
        "db": SERVER2_DB,
        "columns": ["username", "file_id", "page", "source_document_key", "drawing_json", "server_revision", "deleted", "updated_at_utc"],
        "pk": ["username", "file_id", "page"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS future_server2.space_pdf_drawing_shadow (
                username text NOT NULL,
                file_id text NOT NULL,
                page integer NOT NULL,
                source_document_key text NOT NULL,
                drawing_json text NOT NULL,
                server_revision integer NOT NULL,
                deleted integer NOT NULL DEFAULT 0,
                updated_at_utc text NOT NULL,
                PRIMARY KEY(username, file_id, page)
            )
        """,
    },
    "space_pdf_migration_journal": {
        "db": SERVER2_DB,
        "columns": ["legacy_path", "operation_id", "proposed_file_id", "document_id", "package_path", "source_sha256", "state_before_sha256", "stage", "attempts", "error", "created_at_utc", "updated_at_utc"],
        "pk": ["legacy_path"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS future_server2.space_pdf_migration_journal (
                legacy_path text PRIMARY KEY,
                operation_id text NOT NULL UNIQUE,
                proposed_file_id text NOT NULL,
                document_id text NOT NULL,
                package_path text NOT NULL,
                source_sha256 text NOT NULL,
                state_before_sha256 text NOT NULL DEFAULT '',
                stage text NOT NULL DEFAULT 'discovered',
                attempts integer NOT NULL DEFAULT 0,
                error text NOT NULL DEFAULT '',
                created_at_utc text NOT NULL,
                updated_at_utc text NOT NULL
            )
        """,
        "indexes": [
            "CREATE INDEX IF NOT EXISTS space_pdf_migration_journal_stage_idx ON future_server2.space_pdf_migration_journal(stage)"
        ],
    },
    "space_pdf_migration_runs": {
        "db": SERVER2_DB,
        "columns": ["run_id", "mapping_sha256", "started_at_utc", "completed_at_utc", "report_json"],
        "pk": ["run_id"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS future_server2.space_pdf_migration_runs (
                run_id text PRIMARY KEY,
                mapping_sha256 text NOT NULL,
                started_at_utc text NOT NULL,
                completed_at_utc text NOT NULL DEFAULT '',
                report_json text NOT NULL DEFAULT '{}'
            )
        """,
    },
    "space_pdf_progress_migration_sources": {
        "db": SERVER2_DB,
        "columns": ["username", "file_id", "source_progress_key", "is_winner", "record_json", "server_revision", "updated_at_utc"],
        "pk": ["username", "file_id", "source_progress_key"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS future_server2.space_pdf_progress_migration_sources (
                username text NOT NULL,
                file_id text NOT NULL,
                source_progress_key text NOT NULL,
                is_winner integer NOT NULL DEFAULT 0,
                record_json text NOT NULL,
                server_revision integer NOT NULL DEFAULT 0,
                updated_at_utc text NOT NULL,
                PRIMARY KEY(username, file_id, source_progress_key)
            )
        """,
    },
    "space_pdf_progress_shadow": {
        "db": SERVER2_DB,
        "columns": ["username", "file_id", "source_progress_key", "record_json", "server_revision", "updated_at_utc"],
        "pk": ["username", "file_id"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS future_server2.space_pdf_progress_shadow (
                username text NOT NULL,
                file_id text NOT NULL,
                source_progress_key text NOT NULL,
                record_json text NOT NULL,
                server_revision integer NOT NULL DEFAULT 0,
                updated_at_utc text NOT NULL,
                PRIMARY KEY(username, file_id)
            )
        """,
    },
    "sqlite_sequence": {
        "db": SERVER2_DB,
        "columns": ["name", "seq"],
        "pk": ["name"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS future_server2.sqlite_sequence (
                name text PRIMARY KEY,
                seq bigint NOT NULL
            )
        """,
    },
    "vault_hidden_paths": {
        "db": SERVER2_DB,
        "columns": ["username", "normalized_path", "created_at_utc", "updated_at_utc"],
        "pk": ["username", "normalized_path"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS future_server2.vault_hidden_paths (
                username text NOT NULL REFERENCES future_server2.users(username) ON DELETE CASCADE,
                normalized_path text NOT NULL,
                created_at_utc text NOT NULL,
                updated_at_utc text NOT NULL,
                PRIMARY KEY(username, normalized_path)
            )
        """,
        "indexes": [
            "CREATE INDEX IF NOT EXISTS vault_hidden_paths_path_idx ON future_server2.vault_hidden_paths(normalized_path)"
        ],
    },
    "assets": {
        "db": STRUCTURE_DB,
        "columns": ["path_key", "path", "content_gzip", "raw_size", "raw_sha256", "source_mtime_ns", "revision_ns"],
        "pk": ["path_key"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS future_server2.assets (
                path_key text PRIMARY KEY,
                path text NOT NULL,
                content_gzip bytea NOT NULL,
                raw_size bigint NOT NULL,
                raw_sha256 text NOT NULL,
                source_mtime_ns bigint NOT NULL,
                revision_ns bigint NOT NULL
            )
        """,
    },
    "ocr_pages": {
        "db": STRUCTURE_DB,
        "columns": ["folder_key", "folder_path", "file_key", "file_name", "content_text", "source_mtime_ns", "source_size"],
        "pk": ["folder_key", "file_key"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS future_server2.ocr_pages (
                folder_key text NOT NULL,
                folder_path text NOT NULL,
                file_key text NOT NULL,
                file_name text NOT NULL,
                content_text text NOT NULL,
                source_mtime_ns bigint NOT NULL,
                source_size bigint NOT NULL,
                PRIMARY KEY(folder_key, file_key)
            )
        """,
    },
    "registry_documents": {
        "db": STRUCTURE_DB,
        "columns": ["key", "payload_json", "revision_ns"],
        "pk": ["key"],
        "ddl": """
            CREATE TABLE IF NOT EXISTS future_server2.registry_documents (
                key text PRIMARY KEY,
                payload_json text NOT NULL,
                revision_ns bigint NOT NULL
            )
        """,
    },
}


def sqlite_connect(path: Path) -> sqlite3.Connection:
    uri = "file:" + path.as_posix().replace(":", "%3A") + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def normalize_value(value: Any) -> Any:
    if isinstance(value, memoryview):
        return bytes(value)
    return value


def sqlite_rows(table: str) -> list[dict[str, Any]]:
    spec = TABLES[table]
    columns = spec["columns"]
    pk_columns = spec["pk"]
    with sqlite_connect(spec["db"]) as connection:
        query = ", ".join(f'"{column}"' for column in columns)
        order_sql = ", ".join(f'"{column}"' for column in pk_columns)
        return [
            {column: normalize_value(row[column]) for column in columns}
            for row in connection.execute(f'SELECT {query} FROM "{table}" ORDER BY {order_sql}')
        ]


def fingerprint(rows: list[dict[str, Any]]) -> str:
    prepared_rows = []
    for row in rows:
        prepared = {}
        for key, value in row.items():
            if isinstance(value, memoryview):
                prepared[key] = hashlib.sha256(bytes(value)).hexdigest()
            elif isinstance(value, (bytes, bytearray)):
                prepared[key] = hashlib.sha256(bytes(value)).hexdigest()
            else:
                prepared[key] = value
        prepared_rows.append(json.dumps(prepared, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str))
    digest = hashlib.sha256()
    for encoded in sorted(prepared_rows):
        digest.update(encoded.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def pg_rows(connection, table: str) -> list[dict[str, Any]]:
    spec = TABLES[table]
    columns = spec["columns"]
    pk_columns = spec["pk"]
    column_sql = ", ".join(f'"{column}"' for column in columns)
    order_sql = ", ".join(f'"{column}"' for column in pk_columns)
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT {column_sql} FROM {SCHEMA}."{table}" ORDER BY {order_sql}')
        result = []
        for row in cursor.fetchall():
            result.append({column: normalize_value(value) for column, value in zip(columns, row)})
        return result


def ensure_schema(connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
        for spec in TABLES.values():
            cursor.execute(spec["ddl"])
            for index_sql in spec.get("indexes", []):
                cursor.execute(index_sql)
    connection.commit()


def copy_table(connection, table: str) -> dict[str, Any]:
    rows = sqlite_rows(table)
    spec = TABLES[table]
    columns = spec["columns"]
    pk_columns = spec["pk"]
    placeholders = ", ".join(["%s"] * len(columns))
    column_sql = ", ".join(f'"{column}"' for column in columns)
    conflict_sql = ", ".join(f'"{column}"' for column in pk_columns)
    update_columns = [column for column in columns if column not in pk_columns]
    if update_columns:
        update_sql = ", ".join(f'"{column}"=EXCLUDED."{column}"' for column in update_columns)
        conflict_action = f"DO UPDATE SET {update_sql}"
    else:
        conflict_action = "DO NOTHING"
    query = f'INSERT INTO {SCHEMA}."{table}" ({column_sql}) VALUES ({placeholders}) ON CONFLICT ({conflict_sql}) {conflict_action}'
    with connection.cursor() as cursor:
        cursor.executemany(query, [[row[column] for column in columns] for row in rows])
    connection.commit()
    pg = pg_rows(connection, table)
    return {
        "table": table,
        "sqlite_rows": len(rows),
        "postgres_rows": len(pg),
        "sqlite_fingerprint": fingerprint(rows),
        "postgres_fingerprint": fingerprint(pg),
        "parity": len(rows) == len(pg) and fingerprint(rows) == fingerprint(pg),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--tables", nargs="*", default=sorted(TABLES))
    args = parser.parse_args()
    dsn = os.environ.get("FUTURE_PG_DSN", "")
    if not dsn:
        raise RuntimeError("FUTURE_PG_DSN is required.")
    selected = [table for table in args.tables if table in TABLES]
    if not selected:
        raise RuntimeError("No known tables selected.")
    with psycopg.connect(dsn) as connection:
        ensure_schema(connection)
        results = []
        for table in selected:
            if args.verify_only:
                sqlite = sqlite_rows(table)
                pg = pg_rows(connection, table)
                results.append({
                    "table": table,
                    "sqlite_rows": len(sqlite),
                    "postgres_rows": len(pg),
                    "sqlite_fingerprint": fingerprint(sqlite),
                    "postgres_fingerprint": fingerprint(pg),
                    "parity": len(sqlite) == len(pg) and fingerprint(sqlite) == fingerprint(pg),
                })
            else:
                results.append(copy_table(connection, table))
    output = {"verify_only": args.verify_only, "tables": results, "ok": all(row["parity"] for row in results)}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
