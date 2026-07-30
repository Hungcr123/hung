"""Build a read-only canonical-ID migration/archive prototype from a copied SQLite DB."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


def norm_path(value: object) -> str:
    return unicodedata.normalize("NFC", str(value or "").replace("\\", "/").strip("/")).casefold()


def clean(value: object) -> str:
    return str(value or "").strip()


def json_object(value: object) -> dict:
    try:
        parsed = json.loads(value or "{}")
    except Exception:
        parsed = {}
    return parsed if isinstance(parsed, dict) else {}


def stable_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def checksum(value: object) -> str:
    return hashlib.sha256(stable_json(value)).hexdigest()


class Prototype:
    def __init__(self, connection: sqlite3.Connection, source_checksum: str) -> None:
        self.connection = connection
        self.connection.row_factory = sqlite3.Row
        self.source_checksum = source_checksum
        self.batch_id = f"canonical-id-dryrun-20260724-{source_checksum[:12]}"
        self.active = {
            norm_path(row["normalized_path"]): clean(row["file_id"])
            for row in connection.execute("SELECT normalized_path,file_id FROM lesson_file_aliases WHERE active=1")
        }
        self.inactive = {
            norm_path(row["normalized_path"]): clean(row["file_id"])
            for row in connection.execute("SELECT normalized_path,file_id FROM lesson_file_aliases WHERE active=0")
        }
        self.links = [
            (norm_path(row["link_path"]), norm_path(row["target_path"]))
            for row in connection.execute(
                "SELECT link_path,target_path FROM lesson_folder_links WHERE status IN ('active','migrated')"
            )
        ]
        self.files = {
            clean(row["file_id"]): {
                "space_type": clean(row["kind"] or row["space_id"]),
                "identity_revision": int(row["identity_revision"] or 0),
                "status": clean(row["status"]),
            }
            for row in connection.execute(
                "SELECT file_id,space_id,kind,identity_revision,status FROM lesson_files"
            )
        }

    def resolve(self, path: object) -> tuple[str, str, str]:
        raw = norm_path(path)
        if not raw:
            return "unresolved", "", ""
        if raw in self.active:
            return "high_alias", self.active[raw], raw
        if raw in self.inactive:
            return "collision", self.inactive[raw], raw
        parts = raw.split("/")
        for link_root, target_root in self.links:
            if raw != link_root and not raw.startswith(link_root + "/"):
                continue
            mapped = "/".join([target_root, *parts[len(link_root.split("/")):]])
            if mapped in self.active:
                return "high_folder_link", self.active[mapped], mapped
            if mapped in self.inactive:
                return "collision", self.inactive[mapped], mapped
        return "unresolved", "", raw

    def archive(self, *, table: str, source_key: object, target_key: object, original: object,
                file_id: str, paths: list[str], revision: int, server_timestamp: str,
                merge_reason: str, action: str, operation_id: str = "") -> dict:
        metadata = self.files.get(file_id, {})
        original_checksum = checksum(original)
        return {
            "migration_batch_id": self.batch_id,
            "source_table": table,
            "source_primary_key": source_key,
            "target_primary_key": target_key,
            "full_original_payload": original,
            "lesson_id": file_id,
            "file_id": file_id,
            "space_type": metadata.get("space_type", ""),
            "identity_revision": metadata.get("identity_revision", 0),
            "all_paths": sorted({clean(path) for path in paths if clean(path)}, key=str.casefold),
            "revision": max(0, int(revision or 0)),
            "server_timestamp": clean(server_timestamp),
            "merge_reason": merge_reason,
            "proposed_action": action,
            "proposed_operation_id": operation_id,
            "checksum": original_checksum,
        }

    def drawing_actions(self) -> tuple[list[dict], list[dict]]:
        actions: list[dict] = []
        blocked: list[dict] = []
        rows = self.connection.execute(
            "SELECT rowid,* FROM pdf_drawings WHERE file_id='' OR file_id IS NULL"
        )
        for row in rows:
            original = dict(row)
            status, file_id, _mapped_path = self.resolve(row["path"])
            if status not in {"high_alias", "high_folder_link"} or not file_id:
                blocked.append({"rowid": row["rowid"], "status": status, "path": row["path"], "file_id": file_id})
                continue
            target = self.connection.execute(
                "SELECT rowid,server_revision,updated_epoch FROM pdf_drawings "
                "WHERE username=? AND file_id=? AND page=? AND rowid<>? ORDER BY server_revision DESC,updated_epoch DESC LIMIT 1",
                (row["username"], file_id, row["page"], row["rowid"]),
            ).fetchone()
            action = "merge_required" if target is not None else "enrich_file_id"
            target_key = [row["username"], file_id, int(row["page"] or 0)]
            actions.append(self.archive(
                table="pdf_drawings",
                source_key=row["rowid"],
                target_key=target_key,
                original=original,
                file_id=file_id,
                paths=[row["path"]],
                revision=int(row["server_revision"] or 0),
                server_timestamp=row["updated_at_utc"],
                merge_reason=status,
                action=action,
                operation_id=clean(row["last_operation_id"]),
            ))
        return actions, blocked

    def completion_actions(self) -> tuple[list[dict], list[dict]]:
        actions: list[dict] = []
        blocked: list[dict] = []
        rows = self.connection.execute(
            "SELECT rowid,* FROM append_events WHERE stream IN ('learning','learning_intent') ORDER BY id"
        )
        for row in rows:
            event = json_object(row["event_json"])
            event_name = clean(event.get("event") or event.get("type") or event.get("status")).casefold()
            if not any(token in event_name for token in ("complete", "completion", "final")):
                continue
            existing_id = clean(event.get("lesson_id") or event.get("file_id"))
            if existing_id:
                continue
            paths = [
                clean(event.get("path")), clean(event.get("display_path")), clean(event.get("effective_path")),
                clean(event.get("source_path")), clean(event.get("linked_path")), clean(event.get("link_path")),
            ]
            resolutions = [self.resolve(path) for path in paths if path]
            ids = {file_id for status, file_id, _mapped in resolutions if file_id}
            statuses = {status for status, _file_id, _mapped in resolutions}
            if len(ids) != 1 or "collision" in statuses:
                blocked.append({
                    "event_id": row["id"],
                    "status": "ambiguous" if len(ids) > 1 else ("collision" if "collision" in statuses else "unresolved"),
                    "paths": [path for path in paths if path], "candidate_file_ids": sorted(ids),
                })
                continue
            file_id = next(iter(ids))
            event_checksum = checksum(event)
            operation_id = clean(event.get("operation_id") or event.get("completion_id"))
            if not operation_id:
                operation_id = f"legacy-event:{row['id']}:{event_checksum[:20]}"
            actions.append(self.archive(
                table="append_events",
                source_key=row["id"],
                target_key=row["id"],
                original=event,
                file_id=file_id,
                paths=paths,
                revision=int(row["id"] or 0),
                server_timestamp=row["event_at_utc"],
                merge_reason="active_alias_exact" if "high_alias" in statuses else "folder_link_target",
                action="enrich_event_identity",
                operation_id=operation_id,
            ))
        return actions, blocked

    def run(self) -> dict:
        drawing_actions, drawing_blocked = self.drawing_actions()
        completion_actions, completion_blocked = self.completion_actions()
        archives = drawing_actions + completion_actions
        return {
            "read_only": True,
            "migration_authorized": False,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "migration_batch_id": self.batch_id,
            "source_db_sha256": self.source_checksum,
            "summary": {
                "archive_rows": len(archives),
                "drawing_actions": len(drawing_actions),
                "drawing_merge_required": sum(row["proposed_action"] == "merge_required" for row in drawing_actions),
                "drawing_blocked": len(drawing_blocked),
                "completion_actions": len(completion_actions),
                "completion_blocked": len(completion_blocked),
            },
            "archive_prototype": archives,
            "blocked": {
                "pdf_drawings": drawing_blocked,
                "completion_events": completion_blocked,
            },
            "rollback_contract": {
                "restore_by": ["source_table", "source_primary_key", "checksum"],
                "verify": "SHA-256 full_original_payload before restore; target rows remain untouched in dry-run",
                "live_writes_performed": 0,
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Copied/staging SQLite DB only")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    db_path = Path(args.db).resolve()
    live_path = Path(r"C:\server data\server2.db").resolve()
    if db_path == live_path:
        raise SystemExit("Refusing to prototype against the live Server 2 database")
    source_checksum = hashlib.sha256(db_path.read_bytes()).hexdigest()
    connection = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        report = Prototype(connection, source_checksum).run()
    finally:
        connection.close()
    encoded = stable_json(report)
    report["report_sha256"] = hashlib.sha256(encoded).hexdigest()
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
