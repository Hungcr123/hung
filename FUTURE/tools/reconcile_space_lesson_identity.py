from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sqlite3
import sys
import tempfile
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE.tools.assign_space_lesson_ids import (
    SERVER_DATA_ROOT,
    load_payload_from_text,
    payload_fingerprint,
    read_text,
    registry_load,
    registry_register,
    registry_write,
    should_scan_path,
    write_payload,
)
from future_lesson_identity import (
    apply_lesson_id_to_payload,
    generate_future_lesson_id,
    lesson_id_from_payload,
)


SERVER_DATABASE_FILE = SERVER_DATA_ROOT / "server2.db"
SERVER_DATA_MANIFEST_FILE = SERVER_DATA_ROOT / "_future_server_data_manifest.json"
TARGET_SPACE_SUFFIXES = {".space_v", ".space_w", ".space_q", ".space_p", ".space_l", ".space_s"}


def clean(value: object = "") -> str:
    return " ".join(str(value or "").strip().split())


def clean_path(value: object = "") -> str:
    return str(value or "").replace("\\", "/").strip().strip("/")


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# Added 2026-07-21: live RAM manifest state must not overwrite an identity reconciliation applied on disk.
def server2_is_listening(host: str = "127.0.0.1", port: int = 8877) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def scan_wrappers() -> tuple[dict[str, dict], list[dict], list[dict], list[dict]]:
    rows: dict[str, dict] = {}
    missing: list[dict] = []
    errors: list[dict] = []
    file_links: list[dict] = []
    for target in SERVER_DATA_ROOT.rglob("*"):
        if not target.is_file() or target.suffix.lower() not in TARGET_SPACE_SUFFIXES or not should_scan_path(target):
            continue
        try:
            payload, mode, structure = load_payload_from_text(read_text(target))
            stat = target.stat()
            relative = target.resolve().relative_to(SERVER_DATA_ROOT.resolve()).as_posix()
            if clean(payload.get("kind", "")).lower() == "future_server_data_link":
                file_links.append({
                    "target": target,
                    "path": relative,
                    "path_key": relative.lower(),
                    "marker_id": clean(lesson_id_from_payload(payload))[:240],
                    "target_lesson_id": clean(payload.get("target_lesson_id", ""))[:240],
                    "link_target": clean_path(payload.get("target", "")),
                    "space": "Space_" + target.suffix.lower().split(".space_", 1)[-1].upper(),
                })
                continue
            row = {
                "target": target,
                "path": relative,
                "path_key": relative.lower(),
                "file_id": clean(lesson_id_from_payload(payload))[:240],
                "fingerprint": payload_fingerprint(payload, mode, structure),
                "space": "Space_" + target.suffix.lower().split(".space_", 1)[-1].upper(),
                "mtime_ns": int(stat.st_mtime_ns),
                "size": int(stat.st_size),
                "payload": payload,
                "mode": mode,
                "structure": structure,
            }
            rows[row["path_key"]] = row
            if not row["file_id"]:
                missing.append(row)
        except Exception as exc:
            errors.append({"path": str(target), "error": str(exc)})
    return rows, missing, errors, file_links


def manifest_file_entries() -> dict[str, dict]:
    if not SERVER_DATA_MANIFEST_FILE.is_file():
        return {}
    manifest = json.loads(SERVER_DATA_MANIFEST_FILE.read_text(encoding="utf-8-sig", errors="replace"))
    folders = manifest.get("folders") if isinstance(manifest.get("folders"), dict) else {}
    return {
        clean_path(entry.get("path", "")).lower(): entry
        for entries in folders.values()
        for entry in (entries if isinstance(entries, list) else [])
        if isinstance(entry, dict) and clean(entry.get("type", "")).lower() == "file" and clean_path(entry.get("path", ""))
    }


def database_maps(connection: sqlite3.Connection) -> tuple[dict[str, dict], dict[str, dict]]:
    replicas = {
        clean_path(row["normalized_path"]).lower(): dict(row)
        for row in connection.execute(
            "SELECT file_id,normalized_path,fingerprint,file_mtime_ns,file_size,status FROM lesson_file_replicas"
        )
    }
    aliases = {
        clean_path(row["normalized_path"]).lower(): dict(row)
        for row in connection.execute(
            "SELECT normalized_path,file_id,source,active FROM lesson_file_aliases"
        )
    }
    return replicas, aliases


def old_id_reference_counts(connection: sqlite3.Connection, old_ids: set[str]) -> dict:
    if not old_ids:
        return {}
    values = sorted(old_ids)
    placeholders = ",".join("?" for _ in values)
    result: dict[str, int] = {}
    for table in ("lesson_progress", "lesson_time", "lesson_time_credit_state"):
        columns = {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}
        for column in ("file_id", "identity"):
            if column in columns:
                count = int(connection.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE {column} IN ({placeholders})", values
                ).fetchone()[0] or 0)
                result[f"{table}.{column}"] = count
    for table in ("lesson_task_state", "documents", "append_events"):
        columns = [
            str(row[1])
            for row in connection.execute(f"PRAGMA table_info({table})")
            if str(row[2] or "").upper() in {"", "TEXT"}
        ]
        counts = Counter()
        if columns:
            query = "SELECT " + ",".join(f"CAST({column} AS TEXT)" for column in columns) + f" FROM {table}"
            for row in connection.execute(query):
                for index, column in enumerate(columns):
                    text = str(row[index] or "")
                    if any(file_id in text for file_id in values):
                        counts[column] += 1
        for column, count in counts.items():
            result[f"{table}.{column}"] = int(count)
    return result


def build_audit() -> tuple[dict, dict[str, dict], list[dict], list[dict], list[dict]]:
    wrappers, missing, errors, file_links = scan_wrappers()
    manifest_entries = manifest_file_entries()
    connection = sqlite3.connect(str(SERVER_DATABASE_FILE), timeout=30.0)
    connection.row_factory = sqlite3.Row
    try:
        replicas, aliases = database_maps(connection)
        fingerprints: dict[str, set[str]] = defaultdict(set)
        paths_by_id: dict[str, list[str]] = defaultdict(list)
        actionable: list[dict] = []
        mismatches: list[dict] = []
        manifest_actionable: list[dict] = []
        manifest_mismatches: list[dict] = []
        for row in wrappers.values():
            if row["file_id"]:
                fingerprints[row["file_id"]].add(row["fingerprint"])
                paths_by_id[row["file_id"]].append(row["path"])
            replica = replicas.get(row["path_key"])
            alias = aliases.get(row["path_key"])
            mismatch = bool(row["file_id"] and (
                not replica
                or clean(replica.get("file_id")) != row["file_id"]
                or not alias
                or clean(alias.get("file_id")) != row["file_id"]
            ))
            stale_state = bool(row["file_id"] and (
                not replica
                or clean(replica.get("status")).lower() != "active"
                or not alias
                or int(alias.get("active", 0) or 0) != 1
            ))
            if mismatch:
                mismatches.append({
                    "path": row["path"],
                    "wrapper_id": row["file_id"],
                    "replica_id": clean((replica or {}).get("file_id")),
                    "alias_id": clean((alias or {}).get("file_id")),
                })
            if mismatch or stale_state or not row["file_id"]:
                actionable.append(row)
            manifest_entry = manifest_entries.get(row["path_key"])
            manifest_mismatch = bool(
                row["file_id"]
                and (
                    not manifest_entry
                    or clean(manifest_entry.get("lesson_id")) != row["file_id"]
                )
            )
            if manifest_mismatch:
                manifest_actionable.append(row)
                manifest_mismatches.append({
                    "path": row["path"],
                    "wrapper_id": row["file_id"],
                    "manifest_id": clean((manifest_entry or {}).get("lesson_id")),
                    "fingerprint_match": bool(
                        manifest_entry
                        and clean(manifest_entry.get("content_fingerprint")) == row["fingerprint"]
                    ),
                })
        file_link_mismatches = []
        for link in file_links:
            manifest_entry = manifest_entries.get(link["path_key"], {})
            canonical_id = clean(manifest_entry.get("lesson_id") or link.get("target_lesson_id"))[:240]
            replica = replicas.get(link["path_key"])
            alias = aliases.get(link["path_key"])
            if not canonical_id:
                errors.append({"path": link["path"], "error": "File link has no canonical target lesson_id."})
                continue
            mismatch = bool(
                not replica
                or clean(replica.get("file_id")) != canonical_id
                or clean(replica.get("status")).lower() != "active"
                or not alias
                or clean(alias.get("file_id")) != canonical_id
                or int(alias.get("active", 0) or 0) != 1
            )
            if mismatch:
                row = {
                    **link,
                    "file_id": canonical_id,
                    "fingerprint": clean(manifest_entry.get("content_fingerprint", ""))[:320],
                    "mtime_ns": int(manifest_entry.get("modified_ns", 0) or 0),
                    "size": int(manifest_entry.get("size", 0) or 0),
                    "source": "file-link",
                }
                actionable.append(row)
                item = {
                    "kind": "file_link",
                    "path": link["path"],
                    "wrapper_id": canonical_id,
                    "replica_id": clean((replica or {}).get("file_id")),
                    "alias_id": clean((alias or {}).get("file_id")),
                }
                mismatches.append(item)
                file_link_mismatches.append(item)
        divergent = {
            file_id: {"fingerprints": sorted(values), "paths": paths_by_id[file_id]}
            for file_id, values in fingerprints.items()
            if len(values) > 1
        }
        old_ids = {
            item["replica_id"]
            for item in mismatches
            if item["replica_id"] and item["replica_id"] != item["wrapper_id"]
        }
        counts = {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] or 0)
            for table in ("lesson_files", "lesson_file_replicas", "lesson_file_aliases")
        }
        counts["active_replicas"] = int(connection.execute(
            "SELECT COUNT(*) FROM lesson_file_replicas WHERE status='active'"
        ).fetchone()[0] or 0)
        counts["collision_replicas"] = int(connection.execute(
            "SELECT COUNT(*) FROM lesson_file_replicas WHERE status='collision'"
        ).fetchone()[0] or 0)
        counts["active_aliases"] = int(connection.execute(
            "SELECT COUNT(*) FROM lesson_file_aliases WHERE active=1"
        ).fetchone()[0] or 0)
        counts["inactive_aliases"] = int(connection.execute(
            "SELECT COUNT(*) FROM lesson_file_aliases WHERE active=0"
        ).fetchone()[0] or 0)
        zero_replica = int(connection.execute(
            "SELECT COUNT(*) FROM lesson_files f WHERE NOT EXISTS "
            "(SELECT 1 FROM lesson_file_replicas r WHERE r.file_id=f.file_id)"
        ).fetchone()[0] or 0)
        audit = {
            "physical_wrappers": len(wrappers),
            "logical_wrapper_ids": len(fingerprints),
            "missing_ids": len(missing),
            "parse_errors": len(errors),
            "valid_replica_groups": sum(1 for paths in paths_by_id.values() if len(paths) > 1),
            "valid_replica_files": sum(len(paths) for paths in paths_by_id.values() if len(paths) > 1),
            "divergent_groups": len(divergent),
            "wrapper_replica_mismatches": len(mismatches),
            "legacy_file_links": len(file_links),
            "file_link_identity_mismatches": len(file_link_mismatches),
            "database_actionable_paths": len(actionable),
            "manifest_actionable_paths": len(manifest_actionable),
            "actionable_paths": len({row["path_key"] for row in (*actionable, *manifest_actionable)}),
            "lesson_files_zero_replicas": zero_replica,
            "database": counts,
            "old_id_references": old_id_reference_counts(connection, old_ids),
            "missing_paths": [row["path"] for row in missing],
            "mismatch_sample": mismatches[:20],
            "manifest_mismatch_sample": manifest_mismatches[:20],
            "divergent": divergent,
            "errors": errors[:20],
        }
        return audit, wrappers, missing, actionable, manifest_actionable
    finally:
        connection.close()


def update_manifest(rows: list[dict], identity_only_rows: list[dict] | None = None) -> int:
    """2026-07-22: Repair manifest identity without replacing its structural fingerprints."""
    identity_only_rows = identity_only_rows or []
    if not SERVER_DATA_MANIFEST_FILE.is_file() or not rows and not identity_only_rows:
        return 0
    manifest = json.loads(SERVER_DATA_MANIFEST_FILE.read_text(encoding="utf-8-sig", errors="replace"))
    folders = manifest.get("folders") if isinstance(manifest.get("folders"), dict) else {}
    by_path = {row["path_key"]: row for row in rows}
    identity_only_by_path = {
        row["path_key"]: row
        for row in identity_only_rows
        if row["path_key"] not in by_path
    }
    changed = 0
    changed_roots: set[str] = set()
    for entries in folders.values():
        for entry in entries if isinstance(entries, list) else []:
            if not isinstance(entry, dict):
                continue
            path_key = clean_path(entry.get("path", "")).lower()
            row = by_path.get(path_key)
            identity_only = False
            if not row:
                row = identity_only_by_path.get(path_key)
                identity_only = bool(row)
            if not row:
                continue
            values = {"lesson_id": row["file_id"]}
            if not identity_only:
                values.update({
                    "content_fingerprint": row["fingerprint"],
                    "modified_ns": row["mtime_ns"],
                    "modified": int(row["mtime_ns"] // 1_000_000_000),
                    "size": row["size"],
                })
            if any(entry.get(key) != value for key, value in values.items()):
                entry.update(values)
                changed += 1
                changed_roots.add(row["path"].split("/", 1)[0].lower())
    if not changed:
        return 0
    seed = f"identity-reconcile|{time.time_ns()}|{changed}"
    revision = hashlib.sha1(seed.encode("ascii")).hexdigest()
    root_revisions = dict(manifest.get("runtime_root_revisions") or {})
    for root in changed_roots:
        root_revisions[root] = hashlib.sha1(f"{root}|{revision}".encode("utf-8")).hexdigest()
    manifest["runtime_root_revisions"] = root_revisions
    manifest["runtime_root_revision_version"] = 1
    manifest["runtime_revision"] = revision
    manifest["updated_at"] = utc_timestamp()
    atomic_write_json(SERVER_DATA_MANIFEST_FILE, manifest)
    return changed


def assign_missing_ids(missing: list[dict], reserved: set[str]) -> list[dict]:
    if not missing:
        return []
    registry = registry_load()
    changed = []
    for row in missing:
        lesson_id = generate_future_lesson_id(reserved)
        reserved.add(lesson_id)
        apply_lesson_id_to_payload(row["payload"], lesson_id)
        write_payload(row["target"], row["payload"], row["mode"], row["structure"])
        registry_register(registry, lesson_id, row["target"])
        stat = row["target"].stat()
        row.update({
            "file_id": lesson_id,
            "fingerprint": payload_fingerprint(row["payload"], row["mode"], row["structure"]),
            "mtime_ns": int(stat.st_mtime_ns),
            "size": int(stat.st_size),
        })
        changed.append(row)
    registry_write(registry)
    return changed


def reconcile(backup_dir: Path) -> dict:
    if not backup_dir.is_dir() or not (backup_dir / "server2.db").is_file():
        raise RuntimeError("A verified backup directory containing server2.db is required.")
    before, wrappers, missing, actionable, manifest_actionable = build_audit()
    if before["parse_errors"] or before["divergent_groups"]:
        raise RuntimeError("Refusing reconciliation while parse errors or divergent wrapper groups exist.")
    if any(before["old_id_references"].values()):
        raise RuntimeError(f"Stale IDs are still referenced by mutable state: {before['old_id_references']}")
    reserved = {row["file_id"] for row in wrappers.values() if row["file_id"]}
    assigned = assign_missing_ids(missing, reserved)
    actionable_by_path = {row["path_key"]: row for row in actionable}
    for row in assigned:
        actionable_by_path[row["path_key"]] = row
        wrappers[row["path_key"]] = row
    rows = list(actionable_by_path.values())
    connection = sqlite3.connect(str(SERVER_DATABASE_FILE), timeout=30.0)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        now = utc_timestamp()
        for row in rows:
            existing = connection.execute(
                "SELECT canonical_fingerprint FROM lesson_files WHERE file_id=?", (row["file_id"],)
            ).fetchone()
            connection.execute(
                "INSERT INTO lesson_files(file_id,space_id,kind,canonical_fingerprint,identity_revision,status,created_at_utc,updated_at_utc) "
                "VALUES(?,?,?,?,1,'active',?,?) ON CONFLICT(file_id) DO UPDATE SET "
                "space_id=excluded.space_id,canonical_fingerprint=excluded.canonical_fingerprint,"
                "identity_revision=lesson_files.identity_revision+CASE WHEN lesson_files.canonical_fingerprint<>excluded.canonical_fingerprint THEN 1 ELSE 0 END,"
                "status='active',deleted_at_utc='',updated_at_utc=excluded.updated_at_utc",
                (row["file_id"], row["space"], "space", row["fingerprint"], now, now),
            )
            connection.execute(
                "INSERT INTO lesson_file_replicas(file_id,normalized_path,fingerprint,file_mtime_ns,file_size,status,first_seen_at_utc,last_seen_at_utc) "
                "VALUES(?,?,?,?,?,'active',?,?) ON CONFLICT(normalized_path) DO UPDATE SET "
                "file_id=excluded.file_id,fingerprint=excluded.fingerprint,file_mtime_ns=excluded.file_mtime_ns,"
                "file_size=excluded.file_size,status='active',last_seen_at_utc=excluded.last_seen_at_utc",
                (row["file_id"], row["path"], row["fingerprint"], row["mtime_ns"], row["size"], now, now),
            )
            alias_source = clean(row.get("source", "identity-reconcile")) or "identity-reconcile"
            connection.execute(
                "INSERT INTO lesson_file_aliases(normalized_path,file_id,source,active,first_seen_at_utc,last_seen_at_utc) "
                "VALUES(?,?,?,1,?,?) ON CONFLICT(normalized_path) DO UPDATE SET "
                "file_id=excluded.file_id,source=excluded.source,active=1,last_seen_at_utc=excluded.last_seen_at_utc",
                (row["path"], row["file_id"], alias_source, now, now),
            )
        connection.execute(
            "UPDATE lesson_files SET status='inactive',deleted_at_utc=CASE WHEN deleted_at_utc='' THEN ? ELSE deleted_at_utc END,updated_at_utc=? "
            "WHERE status='active' AND NOT EXISTS (SELECT 1 FROM lesson_file_replicas r WHERE r.file_id=lesson_files.file_id AND r.status='active')",
            (now, now),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    manifest_changed = update_manifest(rows, manifest_actionable)
    after, _wrappers, _missing, _actionable, _manifest_actionable = build_audit()
    return {
        "backup": str(backup_dir),
        "assigned_missing": len(assigned),
        "database_paths_reconciled": len(rows),
        "manifest_entries_changed": manifest_changed,
        "before": before,
        "after": after,
    }


def reconcile_manifest_only(backup_dir: Path) -> dict:
    if not backup_dir.is_dir() or not (backup_dir / "server2.db").is_file() or not (backup_dir / "_future_server_data_manifest.json").is_file():
        raise RuntimeError("A verified backup directory containing server2.db and manifest is required.")
    manifest_entries = manifest_file_entries()
    connection = sqlite3.connect(str(SERVER_DATABASE_FILE), timeout=30.0)
    connection.row_factory = sqlite3.Row
    try:
        replicas, aliases = database_maps(connection)
    finally:
        connection.close()

    def candidates() -> tuple[list[dict], list[dict]]:
        rows = []
        errors = []
        for path_key, entry in manifest_entries.items():
            path = clean_path(entry.get("path", ""))
            if Path(path).suffix.lower() not in TARGET_SPACE_SUFFIXES:
                continue
            replica = replicas.get(path_key)
            alias = aliases.get(path_key)
            registry_id = clean((alias or {}).get("file_id"))[:240]
            if not registry_id or int((alias or {}).get("active", 0) or 0) != 1 or clean((replica or {}).get("status")).lower() != "active":
                continue
            if clean(entry.get("lesson_id")) == registry_id:
                continue
            target = SERVER_DATA_ROOT / Path(path)
            try:
                payload, mode, structure = load_payload_from_text(read_text(target))
                wrapper_id = clean(lesson_id_from_payload(payload))[:240]
                if wrapper_id != registry_id:
                    errors.append({"path": path, "wrapper_id": wrapper_id, "registry_id": registry_id})
                    continue
                stat = target.stat()
                rows.append({
                    "path": path,
                    "path_key": path_key,
                    "file_id": registry_id,
                    "fingerprint": payload_fingerprint(payload, mode, structure),
                    "mtime_ns": int(stat.st_mtime_ns),
                    "size": int(stat.st_size),
                })
            except Exception as exc:
                errors.append({"path": path, "error": str(exc)})
        return rows, errors

    safe_rows, errors = candidates()
    if errors:
        raise RuntimeError(f"Refusing manifest-only repair; {len(errors)} wrapper/registry checks failed: {errors[:3]}")
    before_count = len(safe_rows)
    changed = update_manifest([], safe_rows)
    manifest_entries.clear()
    manifest_entries.update(manifest_file_entries())
    remaining, after_errors = candidates()
    return {
        "mode": "manifest-only",
        "backup": str(backup_dir),
        "manifest_entries_changed": changed,
        "before_manifest_mismatches": before_count,
        "remaining_safe_manifest_paths": len(remaining),
        "verification_errors": after_errors,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Audit and reconcile Space wrapper lesson IDs with SQLite and manifest identity.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument("--backup-dir", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    if args.apply or args.manifest_only:
        if server2_is_listening():
            raise RuntimeError("Stop Server 2 before --apply so stale RAM manifest state cannot overwrite reconciliation.")
        result = reconcile_manifest_only(Path(args.backup_dir)) if args.manifest_only else reconcile(Path(args.backup_dir))
    else:
        result, _wrappers, _missing, _actionable, _manifest_actionable = build_audit()
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    failed = result.get("after", result)
    if args.manifest_only:
        return 1 if failed.get("parse_errors") or result.get("remaining_safe_manifest_paths") else 0
    return 1 if failed.get("parse_errors") or failed.get("divergent_groups") else 0


if __name__ == "__main__":
    raise SystemExit(main())
