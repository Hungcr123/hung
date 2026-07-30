#!/usr/bin/env python3
"""Migrate and verify Space_W speak-skip requests in PostgreSQL."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app  # noqa: E402
from FUTURE.postgres.repositories import space_w_speak_skip as pg_speak_skip  # noqa: E402

DATABASE = Path(r"C:\server data\server2.db")
TEST_ID = "codexpg-space-w-speak-skip-001"


def sqlite_payload() -> dict:
    con = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True, timeout=30)
    try:
        path_key, _resolved = app.server_database_document_key(app.SPEAK_SKIP_REQUESTS_FILE)
        row = con.execute("SELECT content,encoding FROM documents WHERE path_key=?", (path_key,)).fetchone()
        if row is None:
            return {"version": 1, "requests": {}}
        data = json.loads(bytes(row[0] or b"").decode(app.clean(row[1]) or "utf-8", errors="replace"))
        return pg_speak_skip.clean_payload(data)
    finally:
        con.close()


def counts(payload: dict) -> dict:
    rows = pg_speak_skip.clean_payload(payload).get("requests", {})
    status: dict[str, int] = {}
    users = set()
    for row in rows.values():
        if not isinstance(row, dict):
            continue
        status_key = app.clean(row.get("status", "pending")).lower() or "pending"
        status[status_key] = status.get(status_key, 0) + 1
        user = app.normalize_username(row.get("username", ""))
        if user:
            users.add(user)
    return {"requests": len(rows), "users": len(users), "status": status}


def cleanup_test_rows() -> None:
    pg_speak_skip.delete_request(TEST_ID)


def copy_sqlite() -> None:
    pg_speak_skip.save_payload(sqlite_payload())


def round_trip() -> dict:
    before = pg_speak_skip.load_payload()
    try:
        rows = dict(before.get("requests", {}))
        row = {
            "id": TEST_ID,
            "username": "hung",
            "status": "pending",
            "progressKey": "codexpg-space-w-progress",
            "sessionId": "codexpg-session",
            "path": "common/codexpg.Space_W",
            "identity": "ftg-lesson-codexpg",
            "title": "Codex Space_W speak skip",
            "nodeIndex": 1,
            "nodeCount": 3,
            "expected": "test",
            "reason": "Codex PostgreSQL round trip",
            "review": False,
            "createdAt": "2026-07-25T00:00:00Z",
            "updatedAt": "2026-07-25T00:00:00Z",
            "respondedAt": "",
        }
        rows[TEST_ID] = row
        first = pg_speak_skip.save_payload({"version": 1, "updated_at": "2026-07-25T00:00:00Z", "requests": rows})
        loaded = pg_speak_skip.load_payload()
        read_after_write = loaded.get("requests", {}).get(TEST_ID, {}).get("status") == "pending"
        rows[TEST_ID]["status"] = "accepted"
        rows[TEST_ID]["updatedAt"] = "2026-07-25T00:00:01Z"
        rows[TEST_ID]["respondedAt"] = "2026-07-25T00:00:01Z"
        accepted = pg_speak_skip.save_payload({"version": 1, "updated_at": "2026-07-25T00:00:01Z", "requests": rows})
        loaded2 = pg_speak_skip.load_payload()
        second = pg_speak_skip.save_payload({"version": 1, "updated_at": "2026-07-25T00:00:01Z", "requests": rows})
        return {
            "saved_ok": bool(first.get("ok")),
            "read_after_write": read_after_write,
            "accepted_transition": loaded2.get("requests", {}).get(TEST_ID, {}).get("status") == "accepted",
            "idempotent_retry": accepted.get("source_sha256") == second.get("source_sha256"),
            "ok": bool(first.get("ok")) and read_after_write and loaded2.get("requests", {}).get(TEST_ID, {}).get("status") == "accepted" and accepted.get("source_sha256") == second.get("source_sha256"),
        }
    finally:
        pg_speak_skip.save_payload(before)


def result(rt: dict | None = None) -> dict:
    sqlite = sqlite_payload()
    pg = pg_speak_skip.load_payload()
    sqlite_fp = pg_speak_skip.fingerprint(sqlite)
    pg_fp = pg_speak_skip.fingerprint(pg)
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
        raise RuntimeError("Set FUTURE_PG_DSN before migrating Space_W speak-skip.")
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
