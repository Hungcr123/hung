#!/usr/bin/env python3
"""Migrate and verify global announcements in PostgreSQL."""

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
from FUTURE.postgres.repositories import announcements as pg_announcements  # noqa: E402

DATABASE = Path(r"C:\server data\server2.db")


def sqlite_payload() -> dict:
    con = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True, timeout=30)
    try:
        path_key, _resolved = app.server_database_document_key(app.ANNOUNCEMENTS_FILE)
        row = con.execute("SELECT content,encoding FROM documents WHERE path_key=?", (path_key,)).fetchone()
        if row is None:
            return {"items": [], "updated_at": ""}
        data = json.loads(bytes(row[0] or b"").decode(app.clean(row[1]) or "utf-8", errors="replace"))
        items = data.get("items") if isinstance(data, dict) and isinstance(data.get("items"), list) else []
        return {"items": app.split_announcement_text("\n".join(str(item or "") for item in items)), "updated_at": app.clean(data.get("updated_at", "")) if isinstance(data, dict) else ""}
    finally:
        con.close()


def fingerprint(payload: dict) -> str:
    public = {
        "items": app.split_announcement_text("\n".join(str(item or "") for item in payload.get("items", []))),
        "updated_at": app.clean(payload.get("updated_at", "")),
    }
    import hashlib
    return hashlib.sha256(json.dumps(public, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def restore_payload(payload: dict) -> None:
    pg_announcements.save_items(list(payload.get("items", [])), app.clean(payload.get("updated_at", "")) or app.utc_timestamp())


def round_trip() -> dict:
    before = pg_announcements.load()
    try:
        test_items = ["Codex announcements PostgreSQL round trip"]
        saved = pg_announcements.save_items(test_items, "2026-07-25T00:00:00Z")
        loaded = pg_announcements.load()
        return {
            "saved_ok": bool(saved.get("ok")),
            "read_after_write": loaded.get("items") == test_items,
            "idempotent_retry": pg_announcements.save_items(test_items, "2026-07-25T00:00:00Z").get("source_sha256") == saved.get("source_sha256"),
            "ok": bool(saved.get("ok")) and loaded.get("items") == test_items,
        }
    finally:
        restore_payload(before)


def result(rt: dict | None = None) -> dict:
    sqlite = sqlite_payload()
    pg = pg_announcements.load()
    return {
        "sqlite_items": len(sqlite.get("items", [])),
        "postgres_items": len(pg.get("items", [])),
        "sqlite_fingerprint": fingerprint(sqlite),
        "postgres_fingerprint": fingerprint(pg),
        "parity": fingerprint(sqlite) == fingerprint(pg),
        "round_trip": rt,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--round-trip", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before migrating announcements.")
    app.postgres_initialize_schema()
    if not args.verify_only and not args.dry_run:
        payload = sqlite_payload()
        pg_announcements.save_items(list(payload.get("items", [])), app.clean(payload.get("updated_at", "")) or app.utc_timestamp())
    rt = round_trip() if args.round_trip and not args.dry_run else None
    out = result(rt)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("parity") and (rt is None or rt.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
