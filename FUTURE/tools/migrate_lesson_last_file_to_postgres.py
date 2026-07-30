#!/usr/bin/env python3
"""Migrate and verify lesson_last_file/recent-files in PostgreSQL.

Requires FUTURE_PG_DSN. SQLite remains authoritative unless
FUTURE_DB_LESSON_LAST_FILE_BACKEND is explicitly set to postgres for a process.
"""

from __future__ import annotations

import argparse
import concurrent.futures
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


def _decode_document(content: bytes | str, encoding: str = "utf-8") -> dict:
    try:
        if isinstance(content, bytes):
            text = content.decode(app.clean(encoding) or "utf-8", errors="replace")
        else:
            text = str(content or "")
        payload = json.loads(text or "{}")
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _username_from_document_path(path_value: str) -> str:
    path = Path(str(path_value or ""))
    try:
        if path.name.lower() == app.LESSON_LAST_FILE_NAME.lower():
            return app.normalize_username(path.parent.name)
    except Exception:
        pass
    return ""


def sqlite_rows() -> list[dict]:
    connection = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True, timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        rows: list[dict] = []
        for row in connection.execute(
            "SELECT path,content,encoding FROM documents WHERE lower(path) LIKE ? ORDER BY lower(path)",
            (f"%{app.LESSON_LAST_FILE_NAME.lower()}",),
        ):
            username = _username_from_document_path(row["path"])
            if not username:
                continue
            payload = _decode_document(row["content"], row["encoding"])
            normalized = app.normalize_lesson_last_file_payload(payload, username, trusted_persisted=True)
            rows.append({"username": username, "state": normalized})
        return rows
    finally:
        connection.close()


def fingerprint(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: item["username"].lower()):
        payload = {
            "username": row["username"].lower(),
            "state": row.get("state") or {},
        }
        digest.update(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def postgres_rows() -> list[dict]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT username,state_json FROM future_server2.lesson_last_file ORDER BY lower(username)")
            return [
                {
                    "username": app.normalize_username(row[0]),
                    "state": dict(row[1]) if isinstance(row[1], dict) else {},
                }
                for row in cursor.fetchall()
            ]

    return app.postgres_execute(_read)


def postgres_row_count() -> int:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM future_server2.lesson_last_file")
            row = cursor.fetchone()
        return int(row[0] or 0) if row else 0

    return app.postgres_execute(_read)


def shadow_read_check(sqlite_source_rows: list[dict], pg_source_rows: list[dict]) -> dict:
    sqlite_by_user = {row["username"].lower(): row for row in sqlite_source_rows}
    pg_by_user = {row["username"].lower(): row for row in pg_source_rows}
    missing_in_pg = []
    mismatches = []
    for key, sqlite_row in sqlite_by_user.items():
        pg_row = pg_by_user.get(key)
        if not pg_row:
            missing_in_pg.append(sqlite_row["username"])
            continue
        if fingerprint([sqlite_row]) != fingerprint([pg_row]):
            mismatches.append({"username": sqlite_row["username"]})
    extra_in_pg = sorted(key for key in pg_by_user if key not in sqlite_by_user)
    quynh = sqlite_by_user.get("quynh")
    quynh_pg = pg_by_user.get("quynh")
    return {
        "sqlite_users": len(sqlite_by_user),
        "postgres_users": len(pg_by_user),
        "missing_in_pg": missing_in_pg[:20],
        "extra_in_pg": extra_in_pg[:20],
        "mismatch_count": len(mismatches),
        "mismatch_sample": mismatches[:10],
        "quynh_checked": bool(quynh and quynh_pg),
        "quynh_equal": bool(quynh and quynh_pg and fingerprint([quynh]) == fingerprint([quynh_pg])),
        "ok": not missing_in_pg and not mismatches,
    }


def test_retry_idempotent(username: str) -> dict:
    marker = app.utc_timestamp()
    payload = {
        "version": 1,
        "updated_at": marker,
        "file": {
            "path": "common/File 02 - {7}.Space_V",
            "title": "Codex PostgreSQL Last File Retry",
            "space": "Space_V",
            "accessedAt": marker,
        },
        "recentFiles": [],
        "selectedFolder": {"path": "common", "selected_at": marker, "source": "postgres-adapter-retry"},
    }
    before_count = postgres_row_count()
    first = app.postgres_upsert_lesson_last_file_row(username, payload)
    middle_count = postgres_row_count()
    second = app.postgres_upsert_lesson_last_file_row(username, payload)
    after_count = postgres_row_count()
    return {
        "username": username,
        "before_count": before_count,
        "middle_count": middle_count,
        "after_count": after_count,
        "first_sha256": first.get("source_sha256"),
        "second_sha256": second.get("source_sha256"),
        "ok": middle_count == before_count + 1 and after_count == middle_count and first.get("source_sha256") == second.get("source_sha256"),
    }


def test_concurrent_backend_writes(prefix: str, users: int = 12) -> dict:
    os.environ["FUTURE_DB_LESSON_LAST_FILE_BACKEND"] = "postgres"
    usernames = [f"{prefix}{index:03d}" for index in range(1, users + 1)]
    for username in usernames:
        app.LESSON_LAST_FILE_CACHE.pop(app.normalize_username(username).lower(), None)

    def _write(username: str) -> dict:
        marker = app.utc_timestamp()
        payload = {
            "version": 1,
            "updated_at": marker,
            "file": {
                "path": "common/File 02 - {7}.Space_V",
                "title": f"Codex PostgreSQL Last File {username}",
                "space": "Space_V",
                "accessedAt": marker,
            },
            "recentFiles": [],
            "selectedFolder": {"path": "common", "selected_at": marker, "source": "postgres-adapter-concurrent"},
        }
        written = app.remember_lesson_last_file(username, payload)
        app.flush_lesson_last_file_state(username)
        loaded = app.postgres_load_lesson_last_file(username)
        file_row = loaded.get("file") if isinstance(loaded.get("file"), dict) else {}
        return {
            "username": username,
            "written_path": app.clean_path_value((written.get("file") or {}).get("path", "")) if isinstance(written, dict) else "",
            "read_path": app.clean_path_value(file_row.get("path", "")),
            "read_lesson_id": app.clean(file_row.get("lesson_id") or file_row.get("file_id")),
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(12, users)) as executor:
        results = list(executor.map(_write, usernames))
    errors = [row for row in results if row.get("read_path") != "common/File 02 - {7}.Space_V"]
    return {
        "users": users,
        "backend_mode": app.postgres_backend_mode("LESSON_LAST_FILE"),
        "ok_count": users - len(errors),
        "error_count": len(errors),
        "error_sample": errors[:5],
        "ok": not errors,
    }


def test_backend_round_trip(username: str) -> dict:
    before = app.postgres_load_lesson_last_file(username)
    marker = app.utc_timestamp()
    test_path = "common/File 02 - {7}.Space_V"
    payload = {
        "version": 1,
        "updated_at": marker,
        "file": {
            "path": test_path,
            "title": "Codex PostgreSQL Last File",
            "space": "Space_V",
            "accessedAt": marker,
        },
        "recentFiles": [],
        "selectedFolder": {"path": "common", "selected_at": marker, "source": "postgres-adapter-test"},
    }
    written = app.remember_lesson_last_file(username, payload)
    app.flush_lesson_last_file_state(username)
    loaded = app.read_lesson_last_file_state(username)
    file_row = loaded.get("file") if isinstance(loaded.get("file"), dict) else {}
    return {
        "username": username,
        "backend_mode": app.postgres_backend_mode("LESSON_LAST_FILE"),
        "before_had_state": bool(before),
        "written_path": app.clean_path_value((written.get("file") or {}).get("path", "")) if isinstance(written, dict) else "",
        "read_path": app.clean_path_value(file_row.get("path", "")),
        "expected_path": test_path,
        "read_lesson_id": app.clean(file_row.get("lesson_id") or file_row.get("file_id")),
        "ok": app.clean_path_value(file_row.get("path", "")) == test_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--exercise-gates", action="store_true")
    parser.add_argument("--round-trip-user", default="codexpglastfile")
    args = parser.parse_args()
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating lesson_last_file to PostgreSQL.")
    rows = sqlite_rows()
    app.postgres_initialize_schema()
    if not args.verify_only and not args.dry_run:
        for row in rows:
            app.postgres_upsert_lesson_last_file_row(row["username"], row["state"])
    pg_rows = postgres_rows()
    sqlite_users = {row["username"].lower() for row in rows}
    pg_subset = [row for row in pg_rows if row["username"].lower() in sqlite_users]
    sqlite_fp = fingerprint(rows)
    pg_fp = fingerprint(pg_subset)
    round_trip = None
    retry_idempotent = None
    concurrent_writes = None
    if not args.verify_only and not args.dry_run:
        os.environ["FUTURE_DB_LESSON_LAST_FILE_BACKEND"] = "postgres"
        app.LESSON_LAST_FILE_CACHE.pop(app.normalize_username(args.round_trip_user).lower(), None)
        round_trip = test_backend_round_trip(args.round_trip_user)
        if args.exercise_gates:
            retry_idempotent = test_retry_idempotent("codexpglastfileretry")
            concurrent_writes = test_concurrent_backend_writes("codexpglast", 12)
    result = {
        "sqlite_rows": len(rows),
        "postgres_rows_total": len(pg_rows),
        "postgres_rows_matching_sqlite_users": len(pg_subset),
        "sqlite_fingerprint": sqlite_fp,
        "postgres_fingerprint_for_sqlite_users": pg_fp,
        "parity": sqlite_fp == pg_fp and len(rows) == len(pg_subset),
        "shadow_read": shadow_read_check(rows, pg_subset),
        "round_trip": round_trip,
        "retry_idempotent": retry_idempotent,
        "concurrent_writes": concurrent_writes,
        "dry_run": args.dry_run,
        "verify_only": args.verify_only,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if (
        result["parity"]
        and result["shadow_read"].get("ok")
        and (round_trip is None or round_trip.get("ok"))
        and (retry_idempotent is None or retry_idempotent.get("ok"))
        and (concurrent_writes is None or concurrent_writes.get("ok"))
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
