"""PostgreSQL runtime repository for selected Server 2 system documents."""

from __future__ import annotations

import hashlib
from pathlib import Path

import FUTURE.server_app as app

EXCLUDED_SYSTEM_DOCUMENT_NAMES = {
    "_future_frontend_reload.json",
    "_future_cloudflare_email_routing.json",
    "_future_cloudflare_email_routing_inbox.json",
}

POSTGRES_SYSTEM_DOCUMENT_NAMES = {
    "_future_audio_cache_epoch.json",
    "_future_settings.json",
    "_future_manifest_build_pending.json",
}


def is_system_document(path: Path | str) -> bool:
    # Added 2026-07-30: Server settings are authoritative in PostgreSQL so
    # tunnel/domain configuration survives a PostgreSQL-only restart.
    return Path(path).name.lower() in POSTGRES_SYSTEM_DOCUMENT_NAMES

def is_policy_excluded_system_document(path: Path | str) -> bool:
    return Path(path).name.lower() in EXCLUDED_SYSTEM_DOCUMENT_NAMES


def read_entry(path: Path | str) -> dict[str, object] | None:
    path_key, _resolved = app.server_database_document_key(path)
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


def upsert_text(path: Path | str, text: str, encoding: str = "utf-8", updated_at_utc: str = "", file_mtime_ns: int = 0) -> dict:
    path_key, resolved = app.server_database_document_key(path)
    data = str(text).encode(encoding or "utf-8", errors="replace")
    mtime_ns = max(0, app.space_w_int(file_mtime_ns, 0))
    if not mtime_ns:
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
        "updated_at_utc": app.clean(updated_at_utc) or app.utc_timestamp(),
    })
