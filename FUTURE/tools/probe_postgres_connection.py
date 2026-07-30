#!/usr/bin/env python3
"""Probe the configured PostgreSQL DSN without printing secrets."""

from __future__ import annotations

import json
import os
import sys
import urllib.parse


def redacted_dsn(dsn: str) -> str:
    if not dsn:
        return ""
    parsed = urllib.parse.urlsplit(dsn)
    netloc = parsed.netloc
    if "@" in netloc:
        auth, host = netloc.rsplit("@", 1)
        user = auth.split(":", 1)[0]
        netloc = f"{user}:***@{host}" if user else f"***@{host}"
    return urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def main() -> int:
    dsn = os.environ.get("FUTURE_PG_DSN", "")
    result = {
        "dsn_set": bool(dsn),
        "dsn": redacted_dsn(dsn),
        "ok": False,
    }
    if not dsn:
        result["pending"] = "FUTURE_PG_DSN is not set"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2
    try:
        import psycopg

        with psycopg.connect(dsn, connect_timeout=5) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1, current_database(), current_user")
                one, database, user = cursor.fetchone()
                cursor.execute(
                    "SELECT has_schema_privilege(current_user, 'future_server2', 'USAGE'), "
                    "has_schema_privilege(current_user, 'future_server2', 'CREATE')"
                )
                schema_usage, schema_create = cursor.fetchone()
                cursor.execute(
                    """
                    SELECT has_table_privilege(current_user, 'future_server2.database_meta', 'SELECT,INSERT,UPDATE,DELETE')
                    WHERE to_regclass('future_server2.database_meta') IS NOT NULL
                    """
                )
                row = cursor.fetchone()
        result.update(
            {
                "ok": one == 1,
                "database": database,
                "user": user,
                "schema_usage": bool(schema_usage),
                "schema_create": bool(schema_create),
                "database_meta_rw": None if row is None else bool(row[0]),
            }
        )
    except Exception as exc:
        result.update({"error_type": type(exc).__name__, "error": str(exc).splitlines()[0][:240]})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
