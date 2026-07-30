#!/usr/bin/env python3
"""Migrate and verify per-user lesson task notices in PostgreSQL."""

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
from FUTURE.postgres.repositories import lesson_task_notices as pg_notices  # noqa: E402

DATABASE = Path(r"C:\server data\server2.db")
TEST_USER = "codexpgtasknotice"


def sqlite_payload() -> dict:
    con = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True, timeout=30)
    try:
        path_key, _resolved = app.server_database_document_key(app.LESSON_TASK_NOTICES_FILE)
        row = con.execute("SELECT content,encoding FROM documents WHERE path_key=?", (path_key,)).fetchone()
        if row is None:
            return {"version": 1, "by_user": {}}
        data = json.loads(bytes(row[0] or b"").decode(app.clean(row[1]) or "utf-8", errors="replace"))
        return app._clean_lesson_task_notice_store(data)
    finally:
        con.close()


def fingerprint(payload: dict) -> str:
    cleaned = app._clean_lesson_task_notice_store(payload)
    return hashlib.sha256(
        json.dumps(cleaned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def counts(payload: dict) -> dict:
    cleaned = app._clean_lesson_task_notice_store(payload)
    users = cleaned.get("by_user", {}) if isinstance(cleaned.get("by_user"), dict) else {}
    notice_count = 0
    read_count = 0
    seen_count = 0
    for record in users.values():
        if not isinstance(record, dict):
            continue
        notice_count += len(record.get("notices") if isinstance(record.get("notices"), list) else [])
        read_count += len(record.get("read") if isinstance(record.get("read"), dict) else {})
        seen_count += len(record.get("seen") if isinstance(record.get("seen"), dict) else {})
    return {"users": len(users), "notices": notice_count, "read": read_count, "seen": seen_count}


def cleanup_test_rows() -> None:
    pg_notices.delete_user(TEST_USER)


def copy_sqlite() -> None:
    pg_notices.save_payload(sqlite_payload())


def round_trip() -> dict:
    before = pg_notices.load_payload(TEST_USER)
    test_notice = {
        "id": "codexpg-task-notice-001",
        "text": "Codex PostgreSQL lesson task notice round trip",
        "language": "en",
        "mode": "always",
        "repeat": True,
        "created_at": "2026-07-25T00:00:00Z",
        "updated_at": "2026-07-25T00:00:01Z",
        "created_by": "codex",
        "active": True,
    }
    payload = {
        "version": 1,
        "by_user": {
            TEST_USER: {
                "notices": [test_notice],
                "read": {test_notice["id"]: "2026-07-25T00:00:02Z"},
                "seen": {test_notice["id"]: "2026-07-25T00:00:03Z"},
            }
        },
    }
    try:
        first = pg_notices.save_payload(payload, TEST_USER)
        loaded = pg_notices.load_payload(TEST_USER)
        second = pg_notices.save_payload(payload, TEST_USER)
        expected = app._clean_lesson_task_notice_store(payload)
        return {
            "saved_ok": bool(first.get("ok")),
            "read_after_write": loaded == expected,
            "idempotent_retry": first.get("source_sha256") == second.get("source_sha256"),
            "ok": bool(first.get("ok")) and loaded == expected and first.get("source_sha256") == second.get("source_sha256"),
        }
    finally:
        if before.get("by_user"):
            pg_notices.save_payload(before, TEST_USER)
        else:
            cleanup_test_rows()


def result(rt: dict | None = None) -> dict:
    sqlite = sqlite_payload()
    pg = pg_notices.load_payload()
    sqlite_fp = fingerprint(sqlite)
    pg_fp = fingerprint(pg)
    return {
        "sqlite_counts": counts(sqlite),
        "postgres_counts": counts(pg),
        "sqlite_fingerprint": sqlite_fp,
        "postgres_fingerprint": pg_fp,
        "parity": sqlite_fp == pg_fp,
        "round_trip": rt,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--round-trip", action="store_true")
    parser.add_argument("--cleanup-test-rows", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating lesson task notices.")
    app.postgres_initialize_schema()
    if args.cleanup_test_rows:
        cleanup_test_rows()
    if not args.verify_only and not args.dry_run:
        copy_sqlite()
    rt = round_trip() if args.round_trip and not args.dry_run else None
    out = result(rt)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("parity") and (rt is None or rt.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
