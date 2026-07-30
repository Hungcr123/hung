"""PostgreSQL helpers for canonical migration archive rows."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def row_from_source(row: dict[str, Any], core: Any) -> dict[str, Any]:
    server_timestamp = core.clean(row.get("server_timestamp", ""))
    full_payload = row.get("full_original_payload", {})
    if isinstance(full_payload, str):
        try:
            full_payload = json.loads(full_payload)
        except Exception:
            full_payload = {"raw": full_payload}
    paths_payload = row.get("all_paths", [])
    if isinstance(paths_payload, str):
        try:
            paths_payload = json.loads(paths_payload)
        except Exception:
            paths_payload = [paths_payload] if paths_payload else []
    return {
        "migration_batch_id": core.clean(row.get("migration_batch_id", ""))[:240],
        "source_primary_key": core.clean(row.get("source_primary_key", "")),
        "target_primary_key": core.clean(row.get("target_primary_key", "")),
        "full_original_payload": full_payload,
        "lesson_id": core.clean(row.get("lesson_id", ""))[:240],
        "file_id": core.clean(row.get("file_id", ""))[:240],
        "all_paths": paths_payload,
        "revision": max(0, core.space_w_int(row.get("revision", 0), 0)),
        "server_timestamp": server_timestamp,
        "server_epoch": core.timestamp_to_epoch(server_timestamp),
        "merge_reason": core.clean(row.get("merge_reason", "")),
        "checksum": core.clean(row.get("checksum", "")),
    }


def upsert_row(row: dict[str, Any], core: Any) -> dict[str, Any]:
    payload = row_from_source(row, core)
    if not payload["migration_batch_id"] or not payload["source_primary_key"]:
        raise RuntimeError("Missing PostgreSQL canonical_migration_archive identity.")
    raw_full = json.dumps(payload["full_original_payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    raw_paths = json.dumps(payload["all_paths"], ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    source_sha256 = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.canonical_migration_archive
                    (migration_batch_id,source_primary_key,target_primary_key,full_original_payload,lesson_id,file_id,all_paths,revision,server_timestamp,server_epoch,merge_reason,checksum,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s::jsonb,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(migration_batch_id, source_primary_key) DO UPDATE SET
                    target_primary_key=excluded.target_primary_key,
                    full_original_payload=excluded.full_original_payload,
                    lesson_id=excluded.lesson_id,
                    file_id=excluded.file_id,
                    all_paths=excluded.all_paths,
                    revision=excluded.revision,
                    server_timestamp=excluded.server_timestamp,
                    server_epoch=excluded.server_epoch,
                    merge_reason=excluded.merge_reason,
                    checksum=excluded.checksum,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                (
                    payload["migration_batch_id"],
                    payload["source_primary_key"],
                    payload["target_primary_key"],
                    raw_full,
                    payload["lesson_id"],
                    payload["file_id"],
                    raw_paths,
                    payload["revision"],
                    payload["server_timestamp"],
                    payload["server_epoch"],
                    payload["merge_reason"],
                    payload["checksum"],
                    core.utc_timestamp(),
                    source_sha256,
                ),
            )
        return {
            "ok": True,
            "migration_batch_id": payload["migration_batch_id"],
            "source_primary_key": payload["source_primary_key"],
            "source_sha256": source_sha256,
        }

    return core.postgres_execute(_write)
