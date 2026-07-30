from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE.tools.assign_space_lesson_ids import (
    SERVER_DATA_ROOT,
    SPACE_SUFFIXES,
    load_payload_from_text,
    payload_fingerprint,
    read_text,
)
from future_lesson_identity import lesson_id_from_payload


PROGRESS_FILES = {
    "Space_W": "_future_space_w_progress.json",
    "Space_Q": "_future_space_q_progress.json",
    "Space_V": "_future_space_v_progress.json",
    "Space_P": "_future_space_p_progress.json",
}
SERVER_DATABASE_FILE = SERVER_DATA_ROOT / "server2.db"


def clean(value: object = "") -> str:
    return " ".join(str(value or "").strip().split())


def clean_path(value: object = "") -> str:
    return str(value or "").replace("\\", "/").strip().strip("/")


def progress_key(username: str, identity: str = "", path: str = "") -> str:
    user = clean(username).lower()
    if identity:
        source = f"identity:{clean(identity)[:240]}"
    else:
        source = f"path:{clean_path(path).lower()}"
    return hashlib.sha256(f"{user}|{source}".encode("utf-8")).hexdigest()[:32]


def timestamp_epoch(value: object = "") -> float:
    raw = clean(value)
    if not raw:
        return 0.0
    try:
        if raw.replace(".", "", 1).isdigit():
            return float(raw)
    except Exception:
        pass
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except Exception:
        return 0.0


def record_order(record: dict | None = None) -> tuple[float, int, str]:
    source = record if isinstance(record, dict) else {}
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    stamp = source.get("updatedAt") or source.get("savedAt") or state.get("updatedAt") or state.get("savedAt") or ""
    revision = int(source.get("_serverRevision") or source.get("serverRevision") or 0)
    run_id = clean(source.get("runId") or source.get("run_id") or state.get("runId") or state.get("run_id"))
    return timestamp_epoch(stamp), revision, run_id


def merge_progress_records(left: dict | None, right: dict | None) -> dict:
    old = left if isinstance(left, dict) else {}
    new = right if isinstance(right, dict) else {}
    winner = dict(new if record_order(new) >= record_order(old) else old)
    old_state = old.get("state") if isinstance(old.get("state"), dict) else {}
    new_state = new.get("state") if isinstance(new.get("state"), dict) else {}
    winner_state = dict(winner.get("state")) if isinstance(winner.get("state"), dict) else {}
    completed_runs = max(
        int(old.get("completedRuns") or old.get("completed_runs") or old_state.get("completedRuns") or 0),
        int(new.get("completedRuns") or new.get("completed_runs") or new_state.get("completedRuns") or 0),
    )
    if completed_runs:
        winner["completedRuns"] = completed_runs
        winner["completed_runs"] = completed_runs
        winner_state["completedRuns"] = completed_runs
    if bool(old.get("learned") or old_state.get("learned") or new.get("learned") or new_state.get("learned")):
        winner["learned"] = True
        winner_state["learned"] = True
    if winner_state:
        winner["state"] = winner_state
    return winner


def scan_lesson_registry() -> tuple[dict[str, dict], dict[str, list[dict]]]:
    paths: dict[str, dict] = {}
    identities: dict[str, list[dict]] = {}
    for target in SERVER_DATA_ROOT.rglob("*"):
        if not target.is_file() or target.suffix.lower() not in SPACE_SUFFIXES:
            continue
        try:
            rel_parts = target.resolve().relative_to(SERVER_DATA_ROOT.resolve()).parts
            if not rel_parts or rel_parts[0].startswith("_") or rel_parts[0].lower() in {"sound", "structure", "picture"}:
                continue
            payload, mode, structure = load_payload_from_text(read_text(target))
            lesson_id = clean(lesson_id_from_payload(payload))[:240]
            if not lesson_id:
                continue
            rel = target.resolve().relative_to(SERVER_DATA_ROOT.resolve()).as_posix()
            stat = target.stat()
            row = {
                "file_id": lesson_id,
                "path": rel,
                "fingerprint": payload_fingerprint(payload, mode, structure),
                "space": "Space_" + target.suffix.lower().split(".space_", 1)[-1].upper(),
                "mtime_ns": int(stat.st_mtime_ns),
                "size": int(stat.st_size),
            }
            paths[rel.lower()] = row
            identities.setdefault(lesson_id, []).append(row)
        except Exception:
            continue
    return paths, identities


def migrate_database(dry_run: bool = False, archive_missing: bool = False, archive_output: str = "") -> dict:
    path_map, identities = scan_lesson_registry()
    divergent = {
        lesson_id: sorted({row["fingerprint"] for row in rows})
        for lesson_id, rows in identities.items()
        if len({row["fingerprint"] for row in rows}) > 1
    }
    if divergent:
        raise RuntimeError(f"Refusing progress migration: {len(divergent)} divergent lesson IDs remain")
    connection = sqlite3.connect(str(SERVER_DATABASE_FILE), timeout=30.0)
    connection.row_factory = sqlite3.Row
    migrated = 0
    unresolved = 0
    merged = 0
    time_migrated = 0
    time_merged = 0
    credit_migrated = 0
    orphan_rows: list[dict] = []
    try:
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA foreign_keys=ON")
        if not dry_run:
            connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS lesson_files (
                file_id TEXT PRIMARY KEY, space_id TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL DEFAULT 'space',
                canonical_fingerprint TEXT NOT NULL DEFAULT '', identity_revision INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'active', created_at_utc TEXT NOT NULL, updated_at_utc TEXT NOT NULL,
                deleted_at_utc TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS lesson_file_replicas (
                replica_id INTEGER PRIMARY KEY AUTOINCREMENT, file_id TEXT NOT NULL,
                normalized_path TEXT NOT NULL COLLATE NOCASE, fingerprint TEXT NOT NULL DEFAULT '',
                file_mtime_ns INTEGER NOT NULL DEFAULT 0, file_size INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active', first_seen_at_utc TEXT NOT NULL, last_seen_at_utc TEXT NOT NULL,
                UNIQUE(normalized_path), FOREIGN KEY (file_id) REFERENCES lesson_files(file_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS lesson_file_aliases (
                normalized_path TEXT PRIMARY KEY COLLATE NOCASE, file_id TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'manifest',
                active INTEGER NOT NULL DEFAULT 1, first_seen_at_utc TEXT NOT NULL, last_seen_at_utc TEXT NOT NULL,
                FOREIGN KEY (file_id) REFERENCES lesson_files(file_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS lesson_progress_orphans (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL COLLATE NOCASE, space TEXT NOT NULL,
                progress_key TEXT NOT NULL, path TEXT NOT NULL DEFAULT '', identity TEXT NOT NULL DEFAULT '',
                server_revision INTEGER NOT NULL DEFAULT 0, updated_at_utc TEXT NOT NULL, record_json TEXT NOT NULL,
                archived_at_utc TEXT NOT NULL, reason TEXT NOT NULL DEFAULT 'missing_file',
                UNIQUE(username,space,progress_key)
            );
            """
            )
            progress_columns = {str(row[1]).lower() for row in connection.execute("PRAGMA table_info(lesson_progress)")}
            if "file_id" not in progress_columns:
                connection.execute("ALTER TABLE lesson_progress ADD COLUMN file_id TEXT NOT NULL DEFAULT ''")
            time_columns = {str(row[1]).lower() for row in connection.execute("PRAGMA table_info(lesson_time)")}
            if "file_id" not in time_columns:
                connection.execute("ALTER TABLE lesson_time ADD COLUMN file_id TEXT NOT NULL DEFAULT ''")
            credit_columns = {str(row[1]).lower() for row in connection.execute("PRAGMA table_info(lesson_time_credit_state)")}
            if "file_id" not in credit_columns:
                connection.execute("ALTER TABLE lesson_time_credit_state ADD COLUMN file_id TEXT NOT NULL DEFAULT ''")
        if dry_run:
            rows = list(connection.execute("SELECT username,space,progress_key,path,identity,record_json FROM lesson_progress"))
        else:
            connection.execute("BEGIN IMMEDIATE")
            now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            for lesson_id, replicas in identities.items():
                first = replicas[0]
                connection.execute(
                    "INSERT INTO lesson_files(file_id,space_id,kind,canonical_fingerprint,identity_revision,status,created_at_utc,updated_at_utc) "
                    "VALUES(?,?,?,?,1,'active',?,?) ON CONFLICT(file_id) DO UPDATE SET space_id=excluded.space_id,"
                    "canonical_fingerprint=excluded.canonical_fingerprint,status='active',updated_at_utc=excluded.updated_at_utc",
                    (lesson_id, first["space"], "space", first["fingerprint"], now, now),
                )
                for replica in replicas:
                    connection.execute(
                        "INSERT INTO lesson_file_replicas(file_id,normalized_path,fingerprint,file_mtime_ns,file_size,status,first_seen_at_utc,last_seen_at_utc) "
                        "VALUES(?,?,?,?,?,'active',?,?) ON CONFLICT(normalized_path) DO UPDATE SET file_id=excluded.file_id,"
                        "fingerprint=excluded.fingerprint,file_mtime_ns=excluded.file_mtime_ns,file_size=excluded.file_size,status='active',last_seen_at_utc=excluded.last_seen_at_utc",
                        (lesson_id, replica["path"], replica["fingerprint"], replica["mtime_ns"], replica["size"], now, now),
                    )
                    connection.execute(
                        "INSERT INTO lesson_file_aliases(normalized_path,file_id,source,active,first_seen_at_utc,last_seen_at_utc) "
                        "VALUES(?,?,'migration',1,?,?) ON CONFLICT(normalized_path) DO UPDATE SET file_id=excluded.file_id,active=1,last_seen_at_utc=excluded.last_seen_at_utc",
                        (replica["path"], lesson_id, now, now),
                    )
            rows = list(connection.execute("SELECT rowid,* FROM lesson_progress"))
        for row in rows:
            rel = clean_path(row["path"])
            suffix = Path(rel).suffix.lower()
            if suffix == ".pdf" or suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}:
                continue
            registry = path_map.get(rel.lower())
            lesson_id = clean((registry or {}).get("file_id", ""))
            if not lesson_id:
                unresolved += 1
                orphan_rows.append({key: row[key] for key in row.keys()})
                continue
            new_key = progress_key(row["username"], identity=lesson_id)
            migrated += 1
            if dry_run:
                continue
            try:
                record = json.loads(row["record_json"])
            except Exception:
                record = {}
            record = dict(record) if isinstance(record, dict) else {}
            record.update({"key": new_key, "identity": lesson_id, "lesson_id": lesson_id, "path": rel})
            duplicate = connection.execute(
                "SELECT rowid,record_json FROM lesson_progress WHERE username=? AND space=? AND progress_key=? AND rowid<>?",
                (row["username"], row["space"], new_key, row["rowid"]),
            ).fetchone()
            if duplicate is not None:
                try:
                    previous = json.loads(duplicate["record_json"])
                except Exception:
                    previous = {}
                record = merge_progress_records(previous, record)
                connection.execute("DELETE FROM lesson_progress WHERE rowid=?", (duplicate["rowid"],))
                merged += 1
            connection.execute(
                "UPDATE lesson_progress SET progress_key=?,identity=?,file_id=?,record_json=? WHERE rowid=?",
                (new_key, lesson_id, lesson_id, json.dumps(record, ensure_ascii=False, separators=(",", ":")), row["rowid"]),
            )
        if not dry_run:
            if archive_missing:
                archived_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
                if archive_output:
                    archive_path = Path(archive_output)
                    archive_path.parent.mkdir(parents=True, exist_ok=True)
                    archive_path.write_text(
                        json.dumps({"archived_at": archived_at, "reason": "missing_file", "rows": orphan_rows}, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                for row in orphan_rows:
                    connection.execute(
                        "INSERT INTO lesson_progress_orphans(username,space,progress_key,path,identity,server_revision,updated_at_utc,record_json,archived_at_utc,reason) "
                        "VALUES(?,?,?,?,?,?,?,?,?,'missing_file') ON CONFLICT(username,space,progress_key) DO UPDATE SET "
                        "path=excluded.path,identity=excluded.identity,server_revision=excluded.server_revision,updated_at_utc=excluded.updated_at_utc,"
                        "record_json=excluded.record_json,archived_at_utc=excluded.archived_at_utc",
                        (
                            row["username"], row["space"], row["progress_key"], row["path"], row["identity"],
                            int(row["server_revision"] or 0), row["updated_at_utc"], row["record_json"], archived_at,
                        ),
                    )
                    connection.execute("DELETE FROM lesson_progress WHERE rowid=?", (row["rowid"],))
            time_rows = list(connection.execute("SELECT rowid,* FROM lesson_time"))
            credit_targets: dict[tuple[str, str], tuple[str, str]] = {}
            for row in time_rows:
                rel = clean_path(row["path"])
                suffix = Path(rel).suffix.lower()
                if suffix == ".pdf" or suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}:
                    continue
                registry = path_map.get(rel.lower())
                lesson_id = clean((registry or {}).get("file_id", ""))
                if not lesson_id:
                    continue
                new_key = hashlib.sha256(f"file_id:{lesson_id}".lower().encode("utf-8")).hexdigest()[:32]
                old_key = clean(row["lesson_key"])
                credit_targets[(clean(row["username"]).lower(), old_key)] = (new_key, lesson_id)
                time_migrated += 1
                if old_key == new_key:
                    connection.execute("UPDATE lesson_time SET file_id=? WHERE rowid=?", (lesson_id, row["rowid"]))
                    continue
                target = connection.execute(
                    "SELECT rowid,* FROM lesson_time WHERE username=? AND lesson_key=? AND rowid<>?",
                    (row["username"], new_key, row["rowid"]),
                ).fetchone()
                if target is not None:
                    connection.execute(
                        "UPDATE lesson_time SET file_id=?,path=?,title=CASE WHEN title='' THEN ? ELSE title END,"
                        "space=CASE WHEN space='' THEN ? ELSE space END,seconds=?,ticks=?,updated_at_utc=?,updated_epoch=? WHERE rowid=?",
                        (
                            lesson_id, rel, row["title"], row["space"],
                            max(0, int(target["seconds"] or 0)) + max(0, int(row["seconds"] or 0)),
                            max(0, int(target["ticks"] or 0)) + max(0, int(row["ticks"] or 0)),
                            max(clean(target["updated_at_utc"]), clean(row["updated_at_utc"])),
                            max(float(target["updated_epoch"] or 0), float(row["updated_epoch"] or 0)), target["rowid"],
                        ),
                    )
                    connection.execute("DELETE FROM lesson_time WHERE rowid=?", (row["rowid"],))
                    time_merged += 1
                else:
                    connection.execute(
                        "UPDATE lesson_time SET lesson_key=?,file_id=? WHERE rowid=?",
                        (new_key, lesson_id, row["rowid"]),
                    )
            for row in list(connection.execute("SELECT rowid,* FROM lesson_time_credit_state")):
                target_identity = credit_targets.get((clean(row["username"]).lower(), clean(row["lesson_key"])))
                if not target_identity:
                    continue
                new_key, lesson_id = target_identity
                credit_migrated += 1
                if clean(row["lesson_key"]) == new_key:
                    connection.execute("UPDATE lesson_time_credit_state SET file_id=? WHERE rowid=?", (lesson_id, row["rowid"]))
                    continue
                target = connection.execute(
                    "SELECT rowid,* FROM lesson_time_credit_state WHERE username=? AND lesson_key=? AND rowid<>?",
                    (row["username"], new_key, row["rowid"]),
                ).fetchone()
                if target is not None:
                    winner = row if float(row["last_seen_epoch"] or 0) >= float(target["last_seen_epoch"] or 0) else target
                    connection.execute(
                        "UPDATE lesson_time_credit_state SET file_id=?,session_id=?,last_sequence=?,last_seen_epoch=?,boot_id=?,"
                        "lease_issued_epoch=?,offline_credited_seconds=?,updated_at_utc=? WHERE rowid=?",
                        (
                            lesson_id, winner["session_id"], winner["last_sequence"], winner["last_seen_epoch"], winner["boot_id"],
                            winner["lease_issued_epoch"], max(int(row["offline_credited_seconds"] or 0), int(target["offline_credited_seconds"] or 0)),
                            max(clean(row["updated_at_utc"]), clean(target["updated_at_utc"])), target["rowid"],
                        ),
                    )
                    connection.execute("DELETE FROM lesson_time_credit_state WHERE rowid=?", (row["rowid"],))
                else:
                    connection.execute(
                        "UPDATE lesson_time_credit_state SET lesson_key=?,file_id=? WHERE rowid=?",
                        (new_key, lesson_id, row["rowid"]),
                    )
            connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS lesson_progress_user_file_idx ON lesson_progress(username,file_id) WHERE file_id<>''")
            connection.execute("CREATE INDEX IF NOT EXISTS lesson_progress_user_file_lookup_idx ON lesson_progress(username,file_id)")
            connection.commit()
        return {
            "dry_run": dry_run,
            "registered_files": len(identities),
            "registered_replicas": len(path_map),
            "progress_migrated": migrated,
            "progress_merged": merged,
            "progress_unresolved": unresolved,
            "lesson_time_migrated": time_migrated,
            "lesson_time_merged": time_merged,
            "lesson_time_credit_migrated": credit_migrated,
            "progress_archived": len(orphan_rows) if archive_missing and not dry_run else 0,
        }
    except Exception:
        if not dry_run:
            connection.rollback()
        raise
    finally:
        connection.close()


def lesson_id_for_relative_path(path_value: str) -> str:
    rel = clean_path(path_value)
    if not rel:
        return ""
    target = (SERVER_DATA_ROOT / rel).resolve()
    root = SERVER_DATA_ROOT.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return ""
    if not target.is_file():
        return ""
    try:
        payload, _mode, _structure = load_payload_from_text(read_text(target))
        return clean(lesson_id_from_payload(payload))[:240]
    except Exception:
        return ""


def migrate_user_file(username: str, path: Path, dry_run: bool = False) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {"file": str(path), "changed": 0, "error": str(exc)}
    states = payload.get("states") if isinstance(payload.get("states"), dict) else {}
    if not states:
        return {"file": str(path), "changed": 0, "states": 0}
    changed = 0
    migrated = {}
    for old_key, record in states.items():
        if not isinstance(record, dict):
            continue
        identity = clean(record.get("identity") or record.get("lesson_id") or record.get("lessonId"))[:240]
        rel_path = clean_path(record.get("path") or (record.get("state") or {}).get("path") if isinstance(record.get("state"), dict) else record.get("path"))
        if not identity:
            identity = lesson_id_for_relative_path(rel_path)
        if not identity:
            migrated[clean(old_key)] = record
            continue
        new_key = progress_key(username, identity=identity)
        next_record = dict(record)
        next_record["identity"] = identity
        next_record["lesson_id"] = identity
        next_record["key"] = new_key
        if clean(old_key) and clean(old_key) != new_key:
            next_record["legacy_path_key"] = clean(old_key)
            changed += 1
        previous = migrated.get(new_key)
        if isinstance(previous, dict):
            previous_stamp = clean(previous.get("updatedAt") or previous.get("savedAt"))
            next_stamp = clean(next_record.get("updatedAt") or next_record.get("savedAt"))
            if previous_stamp > next_stamp:
                next_record = previous
        migrated[new_key] = next_record
    if changed and not dry_run:
        out = dict(payload)
        out["states"] = migrated
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"file": str(path), "changed": changed, "states": len(states), "next_states": len(migrated)}


def migrate_all(dry_run: bool = False) -> dict:
    results = []
    users = 0
    changed = 0
    for folder in SERVER_DATA_ROOT.iterdir():
        if not folder.is_dir() or folder.name.lower() in {"common", "sound", "structure", "picture"} or folder.name.startswith("_"):
            continue
        user_changed = 0
        for filename in PROGRESS_FILES.values():
            path = folder / filename
            if not path.is_file():
                continue
            result = migrate_user_file(folder.name, path, dry_run=dry_run)
            user_changed += int(result.get("changed", 0) or 0)
            if result.get("changed") or result.get("error"):
                results.append(result)
        if user_changed:
            users += 1
            changed += user_changed
    return {"dry_run": dry_run, "users_changed": users, "records_changed": changed, "files": results[:200], "file_count": len(results)}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--legacy-json", action="store_true")
    parser.add_argument("--archive-missing", action="store_true")
    parser.add_argument("--archive-output", default="")
    args = parser.parse_args()
    result = migrate_database(
        dry_run=bool(args.dry_run),
        archive_missing=bool(args.archive_missing),
        archive_output=clean(args.archive_output),
    )
    if args.legacy_json:
        result["legacy_json"] = migrate_all(dry_run=bool(args.dry_run))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
