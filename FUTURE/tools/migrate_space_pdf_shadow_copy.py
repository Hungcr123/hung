"""Build portable PDF packages and migrate path state on a copied Server 2 database."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from future_space_pdf_package import build_space_pdf_package, validate_space_pdf_package
from future_space_picture_package import build_space_picture_package, validate_space_picture_package
from future_space_pdf_registry import initialize_space_pdf_registry_schema, register_space_pdf_package


SIDE_DOCUMENTS = {
    "ai_notices": "_future_space_pdf_ai_region_notices.json",
    "ai_questions": "_future_space_pdf_ai_region_questions.json",
    "audio_markers": "_future_space_pdf_audio_markers.json",
}
QUESTION_PROGRESS_DOCUMENT = "_future_space_pdf_ai_question_progress.json"


def clean_path(value: object) -> str:
    return "/".join(part.strip() for part in str(value or "").replace("\\", "/").split("/") if part.strip())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def stable_operation_id(row: dict) -> str:
    raw = "|".join([str(row["legacy_path"]).lower(), str(row["lesson_id"]), str(row["source_sha256"])])
    return "space-pdf-migrate-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def rows_hash(rows: list[dict]) -> str:
    raw = json.dumps(rows, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def timestamp_epoch(value: object) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except Exception:
        pass
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except Exception:
        return 0.0


def decode_document(connection: sqlite3.Connection, filename: str) -> dict:
    row = connection.execute(
        "SELECT content,encoding FROM documents WHERE lower(path)=lower(?) OR lower(path_key)=lower(?) ORDER BY updated_at_utc DESC LIMIT 1",
        (str(Path(r"C:\server data") / filename), str(Path(r"C:\server data") / filename).lower()),
    ).fetchone()
    if row is None:
        return {"documents": {}}
    content = row[0]
    if isinstance(content, bytes):
        content = content.decode(str(row[1] or "utf-8"))
    payload = json.loads(str(content or "{}"))
    return payload if isinstance(payload, dict) else {"documents": {}}


def portable_child_for_path(store: dict, legacy_path: str) -> object:
    wanted = clean_path(legacy_path).lower()
    documents = store.get("documents") if isinstance(store.get("documents"), dict) else {}
    matches = []
    for row in documents.values():
        if not isinstance(row, dict) or clean_path(row.get("path")).lower() != wanted:
            continue
        portable = {key: value for key, value in row.items() if key not in {"key", "path"}}
        matches.append(portable)
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    return {"documents": matches}


def path_map(lessons: dict[str, dict]) -> tuple[dict[str, str], set[str]]:
    candidates: dict[str, set[str]] = {}
    for legacy_path, row in lessons.items():
        if str(row.get("kind")) not in {"pdf", "picture"}:
            continue
        lesson_id = str(row["lesson_id"])
        for value in (legacy_path, row.get("legacy_path"), row.get("effective_path")):
            key = clean_path(value).lower()
            if key:
                candidates.setdefault(key, set()).add(lesson_id)
    resolved = {key: next(iter(ids)) for key, ids in candidates.items() if len(ids) == 1}
    ambiguous = {key for key, ids in candidates.items() if len(ids) > 1}
    return resolved, ambiguous


def child_document_key(mode: object, path: object, lesson_id: str = "") -> str:
    normalized_mode = "picture" if str(mode or "").lower() == "picture" else "pdf"
    scope = f"lesson:{lesson_id.lower()}" if lesson_id.lower().startswith("ftg-lesson-") else clean_path(path).lower()
    return hashlib.sha256(f"{normalized_mode}|{scope}".encode("utf-8")).hexdigest()[:32]


def write_document(connection: sqlite3.Connection, filename: str, payload: dict) -> None:
    absolute = str(Path(r"C:\server data") / filename)
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    connection.execute(
        "UPDATE documents SET content=?,encoding='utf-8',sha256=?,file_size=?,updated_at_utc=? "
        "WHERE lower(path)=lower(?) OR lower(path_key)=lower(?)",
        (raw, hashlib.sha256(raw).hexdigest(), len(raw), utc_now(), absolute, absolute.lower()),
    )


def migrate_child_documents(connection: sqlite3.Connection, resolved_paths: dict[str, str]) -> dict:
    changed = {}
    for label, filename in SIDE_DOCUMENTS.items():
        payload = decode_document(connection, filename)
        documents = payload.get("documents") if isinstance(payload.get("documents"), dict) else {}
        next_documents = {}
        changed_rows = 0
        for old_key, raw_document in documents.items():
            if not isinstance(raw_document, dict):
                continue
            document = dict(raw_document)
            path = clean_path(document.get("path"))
            lesson_id = resolved_paths.get(path.lower(), "")
            mode = "picture" if str(document.get("mode") or "").lower() == "picture" else "pdf"
            next_key = child_document_key(mode, path, lesson_id)
            if lesson_id:
                document["lesson_id"] = lesson_id
            document["key"] = next_key
            if next_key != str(old_key) or clean_path(raw_document.get("lesson_id")) != lesson_id:
                changed_rows += 1
            existing = next_documents.get(next_key)
            if isinstance(existing, dict):
                existing_pages = existing.get("pages") if isinstance(existing.get("pages"), dict) else {}
                for page, rows in (document.get("pages") if isinstance(document.get("pages"), dict) else {}).items():
                    current = existing_pages.get(str(page)) if isinstance(existing_pages.get(str(page)), list) else []
                    additions = rows if isinstance(rows, list) else []
                    by_id = {str(item.get("id") or ""): item for item in current if isinstance(item, dict) and item.get("id")}
                    for item in additions:
                        if isinstance(item, dict) and item.get("id"):
                            prior = by_id.get(str(item["id"]))
                            if prior is None or timestamp_epoch(item.get("updated_at") or item.get("updatedAt")) >= timestamp_epoch(prior.get("updated_at") or prior.get("updatedAt")):
                                by_id[str(item["id"])] = item
                    existing_pages[str(page)] = list(by_id.values())
                existing["pages"] = existing_pages
            else:
                next_documents[next_key] = document
        if changed_rows:
            payload["documents"] = next_documents
            payload["updated_at"] = utc_now()
            write_document(connection, filename, payload)
        changed[label] = changed_rows

    progress_payload = decode_document(connection, QUESTION_PROGRESS_DOCUMENT)
    users = progress_payload.get("users") if isinstance(progress_payload.get("users"), dict) else {}
    progress_changed = 0
    for username, records in list(users.items()):
        if not isinstance(records, dict):
            continue
        next_records = {}
        for old_key, raw_record in records.items():
            if not isinstance(raw_record, dict):
                continue
            record = dict(raw_record)
            path = clean_path(record.get("path"))
            lesson_id = resolved_paths.get(path.lower(), "")
            mode = "picture" if str(record.get("mode") or "").lower() == "picture" else "pdf"
            page = max(1, int(record.get("page", 1) or 1))
            region_key = str(record.get("regionKey") or record.get("region_key") or "")
            scope = lesson_id.lower() if lesson_id else path.lower()
            next_key = hashlib.sha256(f"{str(username).lower()}|{mode}|{scope}|{page}|{region_key}".encode("utf-8")).hexdigest()[:40]
            if lesson_id:
                record["lesson_id"] = lesson_id
            record["key"] = next_key
            if next_key != str(old_key):
                progress_changed += 1
            prior = next_records.get(next_key)
            if not isinstance(prior, dict) or timestamp_epoch(record.get("savedAt") or record.get("updatedAt")) >= timestamp_epoch(prior.get("savedAt") or prior.get("updatedAt")):
                next_records[next_key] = record
        users[username] = next_records
    if progress_changed:
        progress_payload["users"] = users
        progress_payload["updated_at"] = utc_now()
        write_document(connection, QUESTION_PROGRESS_DOCUMENT, progress_payload)
    changed["question_progress"] = progress_changed
    return changed


def progress_winner(rows: list[sqlite3.Row]) -> sqlite3.Row:
    def score(row: sqlite3.Row) -> tuple:
        try:
            record = json.loads(str(row["record_json"] or "{}"))
        except Exception:
            record = {}
        state = record.get("state") if isinstance(record.get("state"), dict) else {}
        return (
            max(timestamp_epoch(row["updated_at_utc"]), timestamp_epoch(record.get("savedAt")), timestamp_epoch(record.get("updatedAt"))),
            int(row["server_revision"] or 0),
            int(record.get("nodeIndex", state.get("nodeIndex", 0)) or 0),
            str(row["progress_key"]),
        )
    return max(rows, key=score)


def ensure_shadow_schema(connection: sqlite3.Connection) -> None:
    initialize_space_pdf_registry_schema(connection)
    columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(pdf_drawings)")}
    if "file_id" not in columns:
        connection.execute("ALTER TABLE pdf_drawings ADD COLUMN file_id TEXT NOT NULL DEFAULT ''")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS space_pdf_progress_shadow (
            username TEXT NOT NULL COLLATE NOCASE,
            file_id TEXT NOT NULL,
            source_progress_key TEXT NOT NULL,
            record_json TEXT NOT NULL,
            server_revision INTEGER NOT NULL DEFAULT 0,
            updated_at_utc TEXT NOT NULL,
            PRIMARY KEY(username,file_id)
        );
        CREATE TABLE IF NOT EXISTS space_pdf_progress_migration_sources (
            username TEXT NOT NULL COLLATE NOCASE,
            file_id TEXT NOT NULL,
            source_progress_key TEXT NOT NULL,
            is_winner INTEGER NOT NULL DEFAULT 0,
            record_json TEXT NOT NULL,
            server_revision INTEGER NOT NULL DEFAULT 0,
            updated_at_utc TEXT NOT NULL,
            PRIMARY KEY(username,file_id,source_progress_key)
        );
        CREATE TABLE IF NOT EXISTS space_pdf_drawing_shadow (
            username TEXT NOT NULL COLLATE NOCASE,
            file_id TEXT NOT NULL,
            page INTEGER NOT NULL,
            source_document_key TEXT NOT NULL,
            drawing_json TEXT NOT NULL,
            server_revision INTEGER NOT NULL,
            deleted INTEGER NOT NULL DEFAULT 0,
            updated_at_utc TEXT NOT NULL,
            PRIMARY KEY(username,file_id,page)
        );
        CREATE TABLE IF NOT EXISTS space_pdf_drawing_migration_sources (
            username TEXT NOT NULL COLLATE NOCASE,
            file_id TEXT NOT NULL,
            page INTEGER NOT NULL,
            source_document_key TEXT NOT NULL,
            row_json TEXT NOT NULL,
            is_winner INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(username,file_id,page,source_document_key)
        );
        CREATE TABLE IF NOT EXISTS space_pdf_migration_runs (
            run_id TEXT PRIMARY KEY,
            mapping_sha256 TEXT NOT NULL,
            started_at_utc TEXT NOT NULL,
            completed_at_utc TEXT NOT NULL DEFAULT '',
            report_json TEXT NOT NULL DEFAULT '{}'
        );
        """
    )


def migrate_state(connection: sqlite3.Connection, resolved_paths: dict[str, str], ambiguous_paths: set[str]) -> dict:
    changed = {"progress_file_id": 0, "progress_rekey": 0, "drawing_file_id": 0, "drawing_rekey": 0, "time_file_id": 0, "task_items": 0}
    quarantined = []
    for path_key, lesson_id in resolved_paths.items():
        changed["drawing_file_id"] += connection.execute(
            "UPDATE pdf_drawings SET file_id=? WHERE lower(replace(path,'\\','/'))=? AND file_id<>?",
            (lesson_id, path_key, lesson_id),
        ).rowcount
        changed["time_file_id"] += connection.execute(
            "UPDATE lesson_time SET file_id=? WHERE lower(replace(path,'\\','/'))=? AND file_id<>?",
            (lesson_id, path_key, lesson_id),
        ).rowcount

    progress_groups: dict[tuple[str, str], list[sqlite3.Row]] = {}
    for row in connection.execute("SELECT * FROM lesson_progress WHERE space='Space_PDF'"):
        target_id = resolved_paths.get(clean_path(row["path"]).lower(), "")
        if not target_id:
            continue
        current_id = str(row["file_id"] or "")
        if current_id and current_id != target_id:
            quarantined.append(clean_path(row["path"]).lower())
            continue
        progress_groups.setdefault((str(row["username"]).lower(), target_id), []).append(row)
    for (_username_key, file_id), rows in progress_groups.items():
        winner = progress_winner(rows)
        canonical_key = hashlib.sha256(f"{str(winner['username']).lower()}|identity:{file_id}".encode("utf-8")).hexdigest()[:32]
        archived_sources = connection.execute(
            "SELECT COUNT(*) FROM space_pdf_progress_migration_sources WHERE username=? AND file_id=?",
            (winner["username"], file_id),
        ).fetchone()[0]
        for row in rows:
            if not archived_sources or str(row["progress_key"]) != canonical_key:
                connection.execute(
                    "INSERT INTO space_pdf_progress_migration_sources(username,file_id,source_progress_key,is_winner,record_json,server_revision,updated_at_utc) "
                    "VALUES(?,?,?,?,?,?,?) ON CONFLICT(username,file_id,source_progress_key) DO UPDATE SET "
                    "is_winner=excluded.is_winner,record_json=excluded.record_json,server_revision=excluded.server_revision,updated_at_utc=excluded.updated_at_utc",
                    (row["username"], file_id, row["progress_key"], 1 if row["progress_key"] == winner["progress_key"] else 0, row["record_json"], row["server_revision"], row["updated_at_utc"]),
                )
        if str(winner["file_id"] or "") != file_id:
            changed["progress_file_id"] += connection.execute(
                "UPDATE lesson_progress SET file_id=? WHERE username=? AND space='Space_PDF' AND progress_key=? AND file_id=''",
                (file_id, winner["username"], winner["progress_key"]),
            ).rowcount
        connection.execute(
            "INSERT INTO space_pdf_progress_shadow(username,file_id,source_progress_key,record_json,server_revision,updated_at_utc) "
            "VALUES(?,?,?,?,?,?) ON CONFLICT(username,file_id) DO UPDATE SET source_progress_key=excluded.source_progress_key,"
            "record_json=excluded.record_json,server_revision=excluded.server_revision,updated_at_utc=excluded.updated_at_utc",
            (winner["username"], file_id, winner["progress_key"], winner["record_json"], winner["server_revision"], winner["updated_at_utc"]),
        )

        record = json.loads(str(winner["record_json"] or "{}"))
        max_revision = max(int(row["server_revision"] or 0) for row in rows)
        record.update({"key": canonical_key, "identity": file_id, "lesson_id": file_id, "_serverRevision": max_revision})
        record_json = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        source_keys = [str(row["progress_key"]) for row in rows]
        if len(rows) != 1 or source_keys[0] != canonical_key or str(winner["file_id"] or "") != file_id:
            changed["progress_rekey"] += 1
        placeholders = ",".join("?" for _ in source_keys)
        connection.execute(
            f"DELETE FROM lesson_progress WHERE username=? AND space='Space_PDF' AND progress_key IN ({placeholders})",
            (winner["username"], *source_keys),
        )
        connection.execute(
            "INSERT INTO lesson_progress(username,space,progress_key,path,identity,node_index,node_count,learned_count,complete,updated_at_utc,record_json,server_revision,file_id) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                winner["username"], "Space_PDF", canonical_key, winner["path"], file_id,
                winner["node_index"], winner["node_count"], winner["learned_count"], winner["complete"],
                winner["updated_at_utc"], record_json, max_revision, file_id,
            ),
        )

    drawing_groups: dict[tuple[str, str, int], list[sqlite3.Row]] = {}
    for row in connection.execute("SELECT * FROM pdf_drawings WHERE file_id<>''"):
        drawing_groups.setdefault((str(row["username"]).lower(), str(row["file_id"]), int(row["page"])), []).append(row)
        connection.execute(
            "INSERT INTO space_pdf_drawing_shadow(username,file_id,page,source_document_key,drawing_json,server_revision,deleted,updated_at_utc) "
            "VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(username,file_id,page) DO UPDATE SET "
            "source_document_key=excluded.source_document_key,drawing_json=excluded.drawing_json,"
            "server_revision=excluded.server_revision,deleted=excluded.deleted,updated_at_utc=excluded.updated_at_utc",
            (row["username"], row["file_id"], row["page"], row["document_key"], row["drawing_json"], row["server_revision"], row["deleted"], row["updated_at_utc"]),
        )
    for (_username_key, file_id, page), rows in drawing_groups.items():
        winner = max(rows, key=lambda row: (float(row["updated_epoch"] or 0), int(row["server_revision"] or 0), str(row["document_key"])))
        distinct_payloads = {(str(row["content_hash"]), int(row["deleted"] or 0)) for row in rows}
        if len(distinct_payloads) > 1:
            raise RuntimeError(f"Divergent drawing collision for {winner['username']} {file_id} page {page}")
        canonical_document_key = hashlib.sha256(f"lesson:{file_id.lower()}".encode("utf-8")).hexdigest()[:32]
        archived_sources = connection.execute(
            "SELECT COUNT(*) FROM space_pdf_drawing_migration_sources WHERE username=? AND file_id=? AND page=?",
            (winner["username"], file_id, page),
        ).fetchone()[0]
        for row in rows:
            if not archived_sources or str(row["document_key"]) != canonical_document_key:
                connection.execute(
                    "INSERT INTO space_pdf_drawing_migration_sources(username,file_id,page,source_document_key,row_json,is_winner) "
                    "VALUES(?,?,?,?,?,?) ON CONFLICT(username,file_id,page,source_document_key) DO UPDATE SET row_json=excluded.row_json,is_winner=excluded.is_winner",
                    (row["username"], file_id, page, row["document_key"], json.dumps(dict(row), ensure_ascii=False, separators=(",", ":"), default=str), 1 if row["document_key"] == winner["document_key"] else 0),
                )
        if len(rows) != 1 or str(winner["document_key"]) != canonical_document_key:
            changed["drawing_rekey"] += 1
        connection.execute("DELETE FROM pdf_drawings WHERE username=? AND file_id=? AND page=?", (winner["username"], file_id, page))
        connection.execute(
            "INSERT INTO pdf_drawings(username,document_key,page,progress_key,path,identity,title,mode,drawing_json,content_hash,last_operation_id,deleted,server_revision,updated_at_utc,updated_epoch,updated_by,file_id) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                winner["username"], canonical_document_key, page,
                hashlib.sha256(f"{str(winner['username']).lower()}|identity:{file_id}".encode("utf-8")).hexdigest()[:32],
                winner["path"], file_id, winner["title"], winner["mode"], winner["drawing_json"], winner["content_hash"],
                winner["last_operation_id"], winner["deleted"], winner["server_revision"], winner["updated_at_utc"],
                winner["updated_epoch"], winner["updated_by"], file_id,
            ),
        )

    def attach_ids(value: object) -> object:
        if isinstance(value, list):
            return [attach_ids(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {key: attach_ids(item) for key, item in value.items()}
        key = clean_path(result.get("effective_path") or result.get("path")).lower()
        if key in ambiguous_paths:
            quarantined.append(key)
        elif key in resolved_paths:
            expected = resolved_paths[key]
            current = str(result.get("lesson_id") or result.get("file_id") or "")
            if current and current != expected:
                quarantined.append(key)
            else:
                if result.get("lesson_id") != expected or result.get("file_id") != expected:
                    changed["task_items"] += 1
                result["lesson_id"] = expected
                result["file_id"] = expected
        return result

    for row in connection.execute("SELECT username,record_json FROM lesson_task_state").fetchall():
        payload = json.loads(str(row["record_json"] or "{}"))
        migrated = attach_ids(payload)
        encoded = json.dumps(migrated, ensure_ascii=False, separators=(",", ":"))
        if encoded != str(row["record_json"]):
            connection.execute("UPDATE lesson_task_state SET record_json=? WHERE username=?", (encoded, row["username"]))
    return {**changed, "quarantined_paths": sorted(set(quarantined))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--source-root", type=Path, default=Path(r"C:\server data"))
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--kind", choices=("all", "pdf", "picture"), default="all")
    args = parser.parse_args()

    mapping_bytes = args.mapping.read_bytes()
    mapping = json.loads(mapping_bytes.decode("utf-8"))
    lessons = mapping.get("lessons") if isinstance(mapping.get("lessons"), dict) else {}
    allowed_kinds = {"pdf", "picture"} if args.kind == "all" else {args.kind}
    pdf_rows = [(path, row) for path, row in sorted(lessons.items(), key=lambda item: item[0].lower()) if row.get("kind") in allowed_kinds]
    if args.limit > 0:
        pdf_rows = pdf_rows[: args.limit]
    args.output_root.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(args.database, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=15000")
    ensure_shadow_schema(connection)
    stores = {label: decode_document(connection, filename) for label, filename in SIDE_DOCUMENTS.items()}
    resolved_paths, ambiguous_paths = path_map({path: row for path, row in pdf_rows})
    run_id = "space-pdf-shadow-" + hashlib.sha256(mapping_bytes + str(args.limit).encode("ascii")).hexdigest()[:32]
    connection.execute(
        "INSERT OR IGNORE INTO space_pdf_migration_runs(run_id,mapping_sha256,started_at_utc) VALUES(?,?,?)",
        (run_id, hashlib.sha256(mapping_bytes).hexdigest(), utc_now()),
    )

    results = []
    for legacy_path, row in pdf_rows:
        source = args.source_root.joinpath(*clean_path(row.get("effective_path") or legacy_path).split("/"))
        output_rel = clean_path(row["proposed_package_path"])
        output = args.output_root.joinpath(*output_rel.split("/"))
        state_rows = [dict(item) for item in connection.execute(
            "SELECT username,progress_key,server_revision,updated_at_utc,record_json FROM lesson_progress "
            "WHERE space='Space_PDF' AND lower(replace(path,'\\','/'))=? ORDER BY username,progress_key",
            (clean_path(legacy_path).lower(),),
        )]
        state_before = rows_hash(state_rows)
        status = "built"
        if output.is_file():
            manifest = validate_space_picture_package(output, verify_source=True) if row.get("kind") == "picture" else validate_space_pdf_package(output, verify_source=True)
            if manifest["lesson_id"] != row["lesson_id"] or manifest["document_id"] != row["document_id"] or manifest["source_sha256"] != row["source_sha256"]:
                raise RuntimeError(f"Existing package conflicts with frozen mapping: {output}")
            status = "existing"
        else:
            builder = build_space_picture_package if row.get("kind") == "picture" else build_space_pdf_package
            builder(
                source, output, title=Path(legacy_path).stem,
                owner_scope="common" if str(row.get("owner_scope")).lower() == "common" else f"user:{str(row.get('owner_scope')).lower()}",
                lesson_id=str(row["lesson_id"]), document_id=str(row["document_id"]),
                ai_notices=portable_child_for_path(stores["ai_notices"], legacy_path),
                ai_questions=portable_child_for_path(stores["ai_questions"], legacy_path),
                audio_markers=portable_child_for_path(stores["audio_markers"], legacy_path),
            )
        registered = register_space_pdf_package(
            connection,
            output,
            output_rel,
            operation_id=stable_operation_id(row),
            legacy_path=legacy_path,
            state_before_sha256=state_before,
            actor_username="migration",
            actor_is_admin=True,
        )
        if not registered.get("ok"):
            raise RuntimeError(f"Package was quarantined during copied migration: {legacy_path}")
        results.append({"legacy_path": legacy_path, "package_path": output_rel, "lesson_id": row["lesson_id"], "status": status})

    connection.execute("BEGIN IMMEDIATE")
    try:
        state_result = migrate_state(connection, resolved_paths, ambiguous_paths)
        state_result["child_documents"] = migrate_child_documents(connection, resolved_paths)
        pause_seconds = float(os.environ.get("FUTURE_SPACE_PDF_MIGRATION_TEST_PAUSE_BEFORE_COMMIT", "0") or 0)
        if pause_seconds > 0:
            signal_path = os.environ.get("FUTURE_SPACE_PDF_MIGRATION_TEST_SIGNAL", "").strip()
            if signal_path:
                Path(signal_path).write_text("ready", encoding="ascii")
            time.sleep(min(300.0, pause_seconds))
        connection.execute(
            "UPDATE space_pdf_migration_journal SET stage='validated',updated_at_utc=? WHERE operation_id LIKE 'space-pdf-migrate-%' AND stage='committed'",
            (utc_now(),),
        )
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise

    report = {
        "run_id": run_id,
        "packages": len(results),
        "built": sum(row["status"] == "built" for row in results),
        "existing": sum(row["status"] == "existing" for row in results),
        "state": state_result,
        "progress_shadow_rows": connection.execute("SELECT COUNT(*) FROM space_pdf_progress_shadow").fetchone()[0],
        "drawing_shadow_rows": connection.execute("SELECT COUNT(*) FROM space_pdf_drawing_shadow").fetchone()[0],
        "progress_source_rows": connection.execute("SELECT COUNT(*) FROM space_pdf_progress_migration_sources").fetchone()[0],
        "foreign_key_errors": len(connection.execute("PRAGMA foreign_key_check").fetchall()),
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
        "journal_mode": connection.execute("PRAGMA journal_mode").fetchone()[0],
        "synchronous": connection.execute("PRAGMA synchronous").fetchone()[0],
        "results": results,
    }
    encoded_report = json.dumps(report, ensure_ascii=False, indent=2)
    args.report.write_text(encoded_report, encoding="utf-8")
    connection.execute(
        "UPDATE space_pdf_migration_runs SET completed_at_utc=?,report_json=? WHERE run_id=?",
        (utc_now(), json.dumps(report, ensure_ascii=False, separators=(",", ":")), run_id),
    )
    connection.close()
    print(json.dumps({key: report[key] for key in ("packages", "built", "existing", "state", "progress_shadow_rows", "drawing_shadow_rows", "foreign_key_errors", "quick_check")}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
