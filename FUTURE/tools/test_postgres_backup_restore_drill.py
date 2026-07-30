"""Run an isolated PostgreSQL logical backup/restore drill on the readiness DB."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA = "drill_backup_restore_20260726"


def dsn_with_db(dsn: str, database: str) -> str:
    base = dsn
    query = ""
    if "?" in dsn:
        base, query = dsn.split("?", 1)
        query = "?" + query
    slash = base.rfind("/")
    if slash < 0:
        raise RuntimeError("DSN must include a database name")
    return base[: slash + 1] + database + query


def serial(value: object) -> object:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return f"base64:{base64.b64encode(value).decode('ascii')}"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(json_ready(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return value


def json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [json_ready(item) for item in value]
    return serial(value)


def restore_value(value: object) -> object:
    if isinstance(value, str) and value.startswith("base64:"):
        return base64.b64decode(value.split(":", 1)[1].encode("ascii"))
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(json_ready(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return value


def row_fingerprint(rows: list[list[object]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(json.dumps([serial(value) for value in row], ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def schema_tables(con: psycopg.Connection, schema: str) -> list[str]:
    rows = con.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """,
        (schema,),
    ).fetchall()
    return [str(row[0]) for row in rows]


def table_columns(con: psycopg.Connection, schema: str, table: str) -> list[str]:
    rows = con.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
        """,
        (schema, table),
    ).fetchall()
    return [str(row[0]) for row in rows]


def read_table(con: psycopg.Connection, schema: str, table: str) -> tuple[list[str], list[list[object]]]:
    columns = table_columns(con, schema, table)
    order_sql = ", ".join(f'"{column}"' for column in columns)
    query = f'SELECT * FROM "{schema}"."{table}" ORDER BY {order_sql}'
    rows = [list(row) for row in con.execute(query).fetchall()]
    return columns, rows


def create_schema(con: psycopg.Connection, schema: str) -> None:
    con.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')


def drop_schema(con: psycopg.Connection, schema: str) -> None:
    con.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


def backup_snapshot(con: psycopg.Connection, schema: str) -> dict:
    tables = schema_tables(con, schema)
    payload = {
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_schema": schema,
        "tables": {},
    }
    for table in tables:
        columns, rows = read_table(con, schema, table)
        payload["tables"][table] = {
            "columns": columns,
            "row_count": len(rows),
            "fingerprint": row_fingerprint(rows),
            "rows": rows,
        }
    return payload


def write_backup_file(payload: dict, path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(json_ready(payload), ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8")
    return {
        "path": str(path),
        "size": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def restore_snapshot(con: psycopg.Connection, source_schema: str, target_schema: str, payload: dict) -> None:
    drop_schema(con, target_schema)
    create_schema(con, target_schema)
    for table, meta in payload["tables"].items():
        con.execute(
            f'CREATE TABLE "{target_schema}"."{table}" (LIKE "{source_schema}"."{table}" INCLUDING ALL)'
        )
        columns = meta["columns"]
        column_sql = ", ".join(f'"{column}"' for column in columns)
        placeholders = ", ".join(["%s"] * len(columns))
        insert_sql = f'INSERT INTO "{target_schema}"."{table}" ({column_sql}) VALUES ({placeholders})'
        for row in meta["rows"]:
            con.execute(insert_sql, [restore_value(value) for value in row])


def verify_snapshot(con: psycopg.Connection, schema: str, baseline: dict) -> dict:
    result = {}
    for table, meta in baseline["tables"].items():
        columns, rows = read_table(con, schema, table)
        result[table] = {
            "columns_match": columns == meta["columns"],
            "row_count": len(rows),
            "row_count_match": len(rows) == meta["row_count"],
            "fingerprint": row_fingerprint(rows),
            "fingerprint_match": row_fingerprint(rows) == meta["fingerprint"],
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", default=DEFAULT_SCHEMA)
    parser.add_argument("--output", default=str(Path.home() / ".codex" / "plans" / "server2_postgres_backup_restore_drill_2026-07-26.json"))
    args = parser.parse_args()
    dsn = os.environ.get("FUTURE_PG_DSN", "")
    if not dsn:
        raise RuntimeError("FUTURE_PG_DSN is required")

    schema = args.schema
    output = Path(args.output)
    backup_started = time.perf_counter()
    with psycopg.connect(dsn_with_db(dsn, "future_server2_readiness_20260726")) as con:
        con.execute("SET statement_timeout = '0'")
        baseline = backup_snapshot(con, "future_server2")
        backup_info = write_backup_file(baseline, output)
    backup_seconds = round(time.perf_counter() - backup_started, 3)

    restore_started = time.perf_counter()
    with psycopg.connect(dsn_with_db(dsn, "future_server2_readiness_20260726")) as con:
        con.execute("SET statement_timeout = '0'")
        create_schema(con, schema)
        restore_snapshot(con, "future_server2", schema, baseline)
        verification = verify_snapshot(con, schema, baseline)
        con.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
    restore_seconds = round(time.perf_counter() - restore_started, 3)

    summary = {
        "backup": backup_info,
        "backup_seconds": backup_seconds,
        "restore_seconds": restore_seconds,
        "table_count": len(baseline["tables"]),
        "verification": verification,
        "all_tables_ok": all(
            row["columns_match"] and row["row_count_match"] and row["fingerprint_match"]
            for row in verification.values()
        ),
    }
    output.write_text(json.dumps(json_ready(summary), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(json_ready(summary), ensure_ascii=False, indent=2))
    return 0 if summary["all_tables_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
