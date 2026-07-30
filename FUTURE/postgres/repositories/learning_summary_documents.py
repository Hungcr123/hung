"""PostgreSQL runtime repository for per-user learning summary documents.

Added 2026-07-25: keep learning summary routing scoped to this document group
instead of enabling generic document cutover while SQLite remains authoritative.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import FUTURE.server_app as app

LEARNING_SUMMARY_NAME = "_future_learning_summary.json"


def is_learning_summary_document(path: Path | str) -> bool:
    return Path(path).name.lower() == LEARNING_SUMMARY_NAME


def path_identity(path: Path | str) -> tuple[str, str]:
    return app.server_database_document_key(path)


def read_entry(path: Path | str) -> dict[str, object] | None:
    path_key, _resolved = path_identity(path)
    if not path_key:
        return None

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT path,content,encoding,sha256,file_size,file_mtime_ns,updated_at_utc
                FROM future_server2.documents
                WHERE path_key=%s
                """,
                (path_key,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return {
            "path": app.clean(row[0]),
            "content": bytes(row[1] or b""),
            "encoding": app.clean(row[2]) or "utf-8",
            "sha256": app.clean(row[3]),
            "file_size": int(row[4] or 0),
            "file_mtime_ns": int(row[5] or 0),
            "updated_at_utc": app.clean(row[6]),
        }

    return app.postgres_execute(_read)


def read_json(path: Path | str, default: object = None):
    entry = read_entry(path)
    if not isinstance(entry, dict):
        return default
    try:
        text = bytes(entry.get("content") or b"").decode(app.clean(entry.get("encoding")) or "utf-8", errors="replace")
        return json.loads(text.lstrip("\ufeff"))
    except Exception:
        return default


def upsert_json(path: Path | str, payload: dict, encoding: str = "utf-8") -> dict:
    path_key, resolved = path_identity(path)
    if not path_key:
        raise RuntimeError("Missing learning summary document identity.")
    text = json.dumps(payload if isinstance(payload, dict) else {}, ensure_ascii=False, indent=2)
    data = text.encode(encoding or "utf-8", errors="replace")
    try:
        mtime_ns = int(Path(path).stat().st_mtime_ns)
    except Exception:
        mtime_ns = 0
    return app.postgres_upsert_document_row({
        "path_key": path_key,
        "path": resolved,
        "content": data,
        "encoding": encoding or "utf-8",
        "sha256": hashlib.sha256(data).hexdigest(),
        "file_size": len(data),
        "file_mtime_ns": mtime_ns,
        "updated_at_utc": app.clean(payload.get("updatedAt", "")) or app.utc_timestamp(),
    })
