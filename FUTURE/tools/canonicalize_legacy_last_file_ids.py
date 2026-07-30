#!/usr/bin/env python3
"""Canonicalize legacy lesson IDs inside lesson_last_file documents."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app  # noqa: E402

DATABASE = Path(r"C:\server data\server2.db")
BACKUP_DIR = Path(r"C:\Users\Admin\.codex\plans")


def _load_legacy_only_ids(connection: sqlite3.Connection) -> set[str]:
    row = connection.execute(
        "SELECT content FROM documents WHERE path_key=?",
        (r"c:\server data\_future_space_lesson_ids.json",),
    ).fetchone()
    if row is None:
        return set()
    try:
        payload = json.loads(bytes(row[0] or b"").decode("utf-8"))
    except Exception:
        return set()
    ids = payload.get("ids") if isinstance(payload, dict) and isinstance(payload.get("ids"), dict) else {}
    legacy_ids = {str(key) for key in ids}
    canonical_ids = {str(item[0]) for item in connection.execute("SELECT file_id FROM lesson_files")}
    return legacy_ids - canonical_ids


def _document_key(username: str) -> tuple[str, str]:
    path = app.lesson_last_file_path(username)
    path_key, resolved = app.server_database_document_key(path)
    return path_key, resolved


def _read_document(connection: sqlite3.Connection, username: str) -> dict:
    path_key, _resolved = _document_key(username)
    row = connection.execute("SELECT content,encoding,sha256 FROM documents WHERE path_key=?", (path_key,)).fetchone()
    if row is None:
        return {}
    encoding = app.clean(row[1]) or "utf-8"
    return json.loads(bytes(row[0] or b"").decode(encoding, errors="replace"))


def _canonical_id_for_path(connection: sqlite3.Connection, path_value: str) -> str:
    normalized = app.clean_path_value(path_value)
    if not normalized:
        return ""
    row = connection.execute(
        "SELECT file_id FROM lesson_file_aliases WHERE normalized_path=? COLLATE NOCASE AND active=1",
        (normalized,),
    ).fetchone()
    return app.clean(row[0]) if row else ""


def _canonicalize_row(connection: sqlite3.Connection, row: dict, legacy_only: set[str]) -> tuple[dict, dict | None]:
    source = dict(row)
    old_id = app.clean(source.get("lesson_id") or source.get("file_id") or source.get("identity"))
    if old_id not in legacy_only:
        return source, None
    canonical_id = _canonical_id_for_path(connection, app.clean_path_value(source.get("path", "")))
    if not canonical_id or canonical_id == old_id:
        return source, None
    source["lesson_id"] = canonical_id
    source["file_id"] = canonical_id
    source.pop("identity", None)
    return source, {
        "path": app.clean_path_value(source.get("path", "")),
        "old_id": old_id,
        "new_id": canonical_id,
    }


def canonicalize_payload(connection: sqlite3.Connection, payload: dict, username: str) -> tuple[dict, list[dict]]:
    legacy_only = _load_legacy_only_ids(connection)
    source = payload if isinstance(payload, dict) else {}
    changes: list[dict] = []
    out = json.loads(json.dumps(source, ensure_ascii=False))
    file_row = out.get("file") if isinstance(out.get("file"), dict) else None
    if file_row is not None:
        out["file"], change = _canonicalize_row(connection, file_row, legacy_only)
        if change:
            change["field"] = "file"
            changes.append(change)
    rows = out.get("recentFiles") if isinstance(out.get("recentFiles"), list) else []
    next_rows = []
    for index, item in enumerate(rows):
        if isinstance(item, dict):
            next_item, change = _canonicalize_row(connection, item, legacy_only)
            if change:
                change["field"] = f"recentFiles[{index}]"
                changes.append(change)
            next_rows.append(next_item)
        else:
            next_rows.append(item)
    out["recentFiles"] = next_rows
    if changes:
        out["updated_at"] = app.utc_timestamp()
    return app.normalize_lesson_last_file_payload(out, username, trusted_persisted=True), changes


def write_document(connection: sqlite3.Connection, username: str, payload: dict) -> dict:
    path_key, resolved = _document_key(username)
    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    updated_at = app.utc_timestamp()
    mtime_ns = app.timestamp_to_epoch(updated_at)
    connection.execute(
        """
        UPDATE documents
        SET path=?, content=?, encoding='utf-8', sha256=?, file_size=?, file_mtime_ns=?, updated_at_utc=?
        WHERE path_key=?
        """,
        (resolved, raw, digest, len(raw), int(float(mtime_ns or 0) * 1_000_000_000), updated_at, path_key),
    )
    return {"path_key": path_key, "bytes": len(raw), "sha256": digest, "updated_at_utc": updated_at}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default="nam")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    username = app.normalize_username(args.username)
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        connection.execute("PRAGMA busy_timeout=30000")
        payload = _read_document(connection, username)
        next_payload, changes = canonicalize_payload(connection, payload, username)
        result = {
            "username": username,
            "changes": changes,
            "change_count": len(changes),
            "applied": False,
            "backup": "",
            "write": None,
        }
        if args.apply and changes:
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            backup = BACKUP_DIR / f"lesson_last_file_{username}_pre_canonicalize_2026-07-25.json"
            backup.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            with connection:
                result["write"] = write_document(connection, username, next_payload)
            result["applied"] = True
            result["backup"] = str(backup)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
