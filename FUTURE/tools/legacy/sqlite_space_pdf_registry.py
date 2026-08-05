"""SQLite registry prototype for validated Space PDF packages on copied databases."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from future_space_pdf_package import validate_space_pdf_package
from future_space_picture_package import validate_space_picture_package


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _clean_path(value: object) -> str:
    return "/".join(part.strip() for part in str(value or "").replace("\\", "/").split("/") if part.strip())


def _package_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _semantic_fingerprint(manifest: dict) -> str:
    payload = {
        "schema": manifest.get("schema"),
        "lesson_id": manifest.get("lesson_id"),
        "document_id": manifest.get("document_id"),
        "package_revision": manifest.get("package_revision"),
        "title": manifest.get("title"),
        "owner_scope": manifest.get("owner_scope"),
        "source_sha256": manifest.get("source_sha256"),
        "source_bytes": manifest.get("source_bytes"),
    }
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _scope_allows(owner_scope: str, username: str, is_admin: bool = False) -> bool:
    scope = str(owner_scope or "").strip().lower()
    if is_admin or scope == "common":
        return True
    return scope.startswith("user:") and scope.split(":", 1)[1] == str(username or "").strip().lower()


def validate_portable_space_package(package_path: str | Path, verify_source: bool = True) -> dict:
    package = Path(package_path)
    if package.suffix.lower() == ".space_picture":
        return validate_space_picture_package(package, verify_source=verify_source)
    return validate_space_pdf_package(package, verify_source=verify_source)


# Added 2026-07-22: prototype schema stays isolated until package and migration gates pass on a DB copy.
def initialize_space_pdf_registry_schema(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS space_pdf_documents (
            document_id TEXT PRIMARY KEY,
            source_sha256 TEXT NOT NULL,
            source_bytes INTEGER NOT NULL,
            mime_type TEXT NOT NULL DEFAULT 'application/pdf',
            page_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS space_pdf_documents_hash_idx
            ON space_pdf_documents(source_sha256,source_bytes,status);
        CREATE TABLE IF NOT EXISTS space_pdf_lesson_meta (
            file_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            schema_version INTEGER NOT NULL,
            package_revision INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            owner_scope TEXT NOT NULL DEFAULT 'common',
            source_filename TEXT NOT NULL DEFAULT '',
            source_sha256 TEXT NOT NULL,
            package_fingerprint TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL,
            FOREIGN KEY (file_id) REFERENCES lesson_files(file_id) ON DELETE CASCADE,
            FOREIGN KEY (document_id) REFERENCES space_pdf_documents(document_id) ON DELETE RESTRICT
        );
        CREATE INDEX IF NOT EXISTS space_pdf_lesson_meta_document_idx
            ON space_pdf_lesson_meta(document_id,status);
        CREATE TABLE IF NOT EXISTS space_pdf_package_replicas (
            normalized_path TEXT PRIMARY KEY COLLATE NOCASE,
            file_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            package_sha256 TEXT NOT NULL,
            semantic_fingerprint TEXT NOT NULL,
            schema_version INTEGER NOT NULL,
            package_revision INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            first_seen_at_utc TEXT NOT NULL,
            last_seen_at_utc TEXT NOT NULL,
            FOREIGN KEY (file_id) REFERENCES lesson_files(file_id) ON DELETE CASCADE,
            FOREIGN KEY (document_id) REFERENCES space_pdf_documents(document_id) ON DELETE RESTRICT
        );
        CREATE INDEX IF NOT EXISTS space_pdf_package_replicas_file_idx
            ON space_pdf_package_replicas(file_id,status);
        CREATE TABLE IF NOT EXISTS space_pdf_migration_journal (
            legacy_path TEXT PRIMARY KEY COLLATE NOCASE,
            operation_id TEXT NOT NULL UNIQUE,
            proposed_file_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            package_path TEXT NOT NULL COLLATE NOCASE,
            source_sha256 TEXT NOT NULL,
            state_before_sha256 TEXT NOT NULL DEFAULT '',
            stage TEXT NOT NULL DEFAULT 'discovered',
            attempts INTEGER NOT NULL DEFAULT 0,
            error TEXT NOT NULL DEFAULT '',
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS space_pdf_migration_journal_stage_idx
            ON space_pdf_migration_journal(stage,updated_at_utc);
        """
    )
    meta_columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(space_pdf_lesson_meta)")}
    if "space_id" not in meta_columns:
        connection.execute("ALTER TABLE space_pdf_lesson_meta ADD COLUMN space_id TEXT NOT NULL DEFAULT 'Space_PDF'")
    if "asset_id" not in meta_columns:
        connection.execute("ALTER TABLE space_pdf_lesson_meta ADD COLUMN asset_id TEXT NOT NULL DEFAULT ''")
    if "asset_locator" not in meta_columns:
        connection.execute("ALTER TABLE space_pdf_lesson_meta ADD COLUMN asset_locator TEXT NOT NULL DEFAULT ''")
    document_columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(space_pdf_documents)")}
    if "asset_id" not in document_columns:
        connection.execute("ALTER TABLE space_pdf_documents ADD COLUMN asset_id TEXT NOT NULL DEFAULT ''")
    if "asset_locator" not in document_columns:
        connection.execute("ALTER TABLE space_pdf_documents ADD COLUMN asset_locator TEXT NOT NULL DEFAULT ''")
    connection.execute("CREATE INDEX IF NOT EXISTS space_pdf_documents_asset_idx ON space_pdf_documents(asset_id,status)")
    replica_columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(space_pdf_package_replicas)")}
    if "space_id" not in replica_columns:
        connection.execute("ALTER TABLE space_pdf_package_replicas ADD COLUMN space_id TEXT NOT NULL DEFAULT 'Space_PDF'")


# Added 2026-07-22: registration trusts only a fully verified package and commits alias metadata atomically.
def register_space_pdf_package(
    connection: sqlite3.Connection,
    package_path: str | Path,
    normalized_path: str,
    *,
    operation_id: str,
    legacy_path: str = "",
    state_before_sha256: str = "",
    actor_username: str = "",
    actor_is_admin: bool = False,
) -> dict:
    package = Path(package_path)
    manifest = validate_portable_space_package(package, verify_source=True)
    path = _clean_path(normalized_path)
    source_legacy_path = _clean_path(legacy_path) or path
    if not path or not operation_id:
        raise RuntimeError("Package path and operation ID are required.")
    if not _scope_allows(str(manifest.get("owner_scope") or ""), actor_username, actor_is_admin):
        raise RuntimeError("Package owner scope does not allow this registration.")
    now = _utc_now()
    lesson_id = str(manifest["lesson_id"])
    document_id = str(manifest["document_id"])
    source_hash = str(manifest["source_sha256"])
    source_bytes = int(manifest["source_bytes"])
    asset_id = str(manifest.get("asset_id") or "")
    asset_locator = str(manifest.get("asset_locator") or "")
    space_id = "Space_Picture" if str(manifest.get("schema") or "") == "space_picture" else "Space_PDF"
    mime_type = str(manifest.get("source_mime_type") or ("application/pdf" if space_id == "Space_PDF" else "application/octet-stream"))
    package_hash = _package_sha256(package)
    semantic_hash = _semantic_fingerprint(manifest)

    connection.execute("BEGIN IMMEDIATE")
    try:
        prior = connection.execute(
            "SELECT legacy_path,proposed_file_id,document_id,package_path,source_sha256,stage FROM space_pdf_migration_journal WHERE operation_id=?",
            (operation_id,),
        ).fetchone()
        exact_replay = prior is not None
        if prior is not None:
            if (
                _clean_path(prior[0]).lower() != source_legacy_path.lower()
                or str(prior[1]) != lesson_id
                or str(prior[2]) != document_id
                or _clean_path(prior[3]).lower() != path.lower()
                or str(prior[4]) != source_hash
            ):
                raise RuntimeError("Operation ID was already used for a different package mutation.")
        prior_legacy = connection.execute(
            "SELECT operation_id,proposed_file_id,document_id,source_sha256 FROM space_pdf_migration_journal WHERE legacy_path=? COLLATE NOCASE",
            (source_legacy_path,),
        ).fetchone()
        if prior_legacy is not None and (
            str(prior_legacy[1]) != lesson_id
            or str(prior_legacy[2]) != document_id
            or str(prior_legacy[3]) != source_hash
        ):
            raise RuntimeError("Legacy path is already journaled for a different lesson identity.")
        journal_operation_id = str(prior_legacy[0]) if prior_legacy is not None else operation_id

        existing_meta = connection.execute(
            "SELECT document_id,schema_version,package_revision,title,owner_scope,source_sha256,status,space_id,asset_id,asset_locator FROM space_pdf_lesson_meta WHERE file_id=?",
            (lesson_id,),
        ).fetchone()
        existing_lesson = connection.execute("SELECT kind FROM lesson_files WHERE file_id=?", (lesson_id,)).fetchone()
        collision = bool(existing_meta is not None and (
            str(existing_meta[0]) != document_id
            or int(existing_meta[2]) != int(manifest["package_revision"])
            or str(existing_meta[3]) != str(manifest.get("title") or "")
            or str(existing_meta[4]).lower() != str(manifest.get("owner_scope") or "").lower()
            or str(existing_meta[5]) != source_hash
            or str(existing_meta[7]) != space_id
            or bool(str(existing_meta[8])) and str(existing_meta[8]) != asset_id
            or bool(str(existing_meta[9])) and str(existing_meta[9]) != asset_locator
        ))
        if existing_lesson is not None and existing_meta is None:
            collision = True
        document_row = connection.execute(
            "SELECT source_sha256,source_bytes FROM space_pdf_documents WHERE document_id=?",
            (document_id,),
        ).fetchone()
        if document_row is not None and (str(document_row[0]) != source_hash or int(document_row[1]) != source_bytes):
            collision = True

        connection.execute(
            "INSERT INTO space_pdf_documents(document_id,source_sha256,source_bytes,mime_type,page_count,status,created_at_utc,updated_at_utc,asset_id,asset_locator) "
            "VALUES(?,?,?,?,0,?,?,?,?,?) ON CONFLICT(document_id) DO UPDATE SET updated_at_utc=excluded.updated_at_utc,"
            "asset_id=CASE WHEN excluded.asset_id<>'' THEN excluded.asset_id ELSE space_pdf_documents.asset_id END,"
            "asset_locator=CASE WHEN excluded.asset_locator<>'' THEN excluded.asset_locator ELSE space_pdf_documents.asset_locator END",
            (document_id, source_hash, source_bytes, mime_type, "collision" if collision else "active", now, now, asset_id, asset_locator),
        )
        if existing_meta is None and not collision:
            connection.execute(
                "INSERT INTO lesson_files(file_id,space_id,kind,canonical_fingerprint,identity_revision,status,created_at_utc,updated_at_utc) "
                "VALUES(?,?,'package',?,1,'active',?,?)",
                (lesson_id, space_id, semantic_hash, now, now),
            )
            connection.execute(
                "INSERT INTO space_pdf_lesson_meta(file_id,document_id,schema_version,package_revision,title,owner_scope,source_filename,source_sha256,package_fingerprint,status,created_at_utc,updated_at_utc,space_id,asset_id,asset_locator) "
                "VALUES(?,?,?,?,?,?,?,?,?,'active',?,?,?,?,?)",
                (
                    lesson_id, document_id, int(manifest["schema_version"]), int(manifest["package_revision"]),
                    str(manifest.get("title") or ""), str(manifest.get("owner_scope") or "common"),
                    str(manifest.get("source_filename") or ""), source_hash, package_hash, now, now, space_id, asset_id, asset_locator,
                ),
            )
        elif existing_meta is not None and not collision:
            # Added 2026-07-22: embedded-v1 to canonical-v2 is a representation upgrade, not a lesson collision.
            connection.execute(
                "UPDATE space_pdf_lesson_meta SET schema_version=?,package_fingerprint=?,updated_at_utc=?,"
                "asset_id=CASE WHEN ?<>'' THEN ? ELSE asset_id END,asset_locator=CASE WHEN ?<>'' THEN ? ELSE asset_locator END "
                "WHERE file_id=?",
                (int(manifest["schema_version"]), package_hash, now, asset_id, asset_id, asset_locator, asset_locator, lesson_id),
            )
        status = "collision" if collision else "active"
        connection.execute(
            "INSERT INTO space_pdf_package_replicas(normalized_path,file_id,document_id,package_sha256,semantic_fingerprint,schema_version,package_revision,status,first_seen_at_utc,last_seen_at_utc,space_id) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(normalized_path) DO UPDATE SET file_id=excluded.file_id,document_id=excluded.document_id,"
            "package_sha256=excluded.package_sha256,semantic_fingerprint=excluded.semantic_fingerprint,schema_version=excluded.schema_version,"
            "package_revision=excluded.package_revision,status=excluded.status,last_seen_at_utc=excluded.last_seen_at_utc,space_id=excluded.space_id",
            (path, lesson_id, document_id, package_hash, semantic_hash, int(manifest["schema_version"]), int(manifest["package_revision"]), status, now, now, space_id),
        )
        connection.execute(
            "INSERT INTO lesson_file_replicas(file_id,normalized_path,fingerprint,file_mtime_ns,file_size,status,first_seen_at_utc,last_seen_at_utc) "
            "VALUES(?,?,?,0,?,?,?,?) ON CONFLICT(normalized_path) DO UPDATE SET file_id=excluded.file_id,fingerprint=excluded.fingerprint,"
            "file_size=excluded.file_size,status=excluded.status,last_seen_at_utc=excluded.last_seen_at_utc",
            (lesson_id, path, semantic_hash, int(package.stat().st_size), status, now, now),
        )
        connection.execute(
            "INSERT INTO lesson_file_aliases(normalized_path,file_id,source,active,first_seen_at_utc,last_seen_at_utc) "
            "VALUES(?,?,?,?,?,?) ON CONFLICT(normalized_path) DO UPDATE SET file_id=excluded.file_id,source=excluded.source,"
            "active=excluded.active,last_seen_at_utc=excluded.last_seen_at_utc",
            (path, lesson_id, "space-picture-package" if space_id == "Space_Picture" else "space-pdf-package", 0 if collision else 1, now, now),
        )
        connection.execute(
            "INSERT INTO space_pdf_migration_journal(legacy_path,operation_id,proposed_file_id,document_id,package_path,source_sha256,state_before_sha256,stage,attempts,error,created_at_utc,updated_at_utc) "
            "VALUES(?,?,?,?,?,?,? ,?,1,'',?,?) ON CONFLICT(legacy_path) DO UPDATE SET package_path=excluded.package_path,"
            "stage=excluded.stage,attempts=space_pdf_migration_journal.attempts+1,error='',updated_at_utc=excluded.updated_at_utc",
            (source_legacy_path, journal_operation_id, lesson_id, document_id, path, source_hash, str(state_before_sha256 or ""), "failed" if collision else "committed", now, now),
        )
        connection.execute("COMMIT")
        return {"ok": not collision, "idempotent": exact_replay, "status": status, "file_id": lesson_id, "document_id": document_id, "path": path}
    except Exception:
        connection.execute("ROLLBACK")
        raise


def resolve_space_pdf_lesson(
    connection: sqlite3.Connection,
    normalized_path: str,
    username: str,
    *,
    is_admin: bool = False,
) -> dict:
    path = _clean_path(normalized_path)
    row = connection.execute(
        "SELECT a.file_id,m.document_id,m.owner_scope,m.package_revision,r.package_sha256 "
        "FROM lesson_file_aliases a JOIN space_pdf_lesson_meta m ON m.file_id=a.file_id "
        "JOIN space_pdf_package_replicas r ON r.normalized_path=a.normalized_path "
        "WHERE a.normalized_path=? COLLATE NOCASE AND a.active=1 AND r.status='active' AND m.status='active'",
        (path,),
    ).fetchone()
    if row is None:
        return {}
    if not _scope_allows(str(row[2]), username, is_admin):
        raise PermissionError("Space PDF lesson belongs to another user scope.")
    return {"file_id": str(row[0]), "document_id": str(row[1]), "owner_scope": str(row[2]), "package_revision": int(row[3]), "package_sha256": str(row[4]), "path": path}


# Added 2026-07-22: portable packages resolve from embedded identity; path rows are only a rebuildable discovery cache.
def resolve_space_pdf_package_identity(
    connection: sqlite3.Connection,
    package_path: str | Path,
    username: str,
    *,
    is_admin: bool = False,
) -> dict:
    package = Path(package_path)
    manifest = validate_space_pdf_package(package, verify_source=True)
    lesson_id = str(manifest["lesson_id"])
    row = connection.execute(
        "SELECT document_id,owner_scope,package_revision,source_sha256,status "
        "FROM space_pdf_lesson_meta WHERE file_id=?",
        (lesson_id,),
    ).fetchone()
    if row is None:
        return {
            "status": "unregistered",
            "file_id": lesson_id,
            "document_id": str(manifest["document_id"]),
            "owner_scope": str(manifest.get("owner_scope") or "common"),
        }
    owner_scope = str(row[1])
    if not _scope_allows(owner_scope, username, is_admin):
        raise PermissionError("Space PDF lesson belongs to another user scope.")
    if (
        str(row[0]) != str(manifest["document_id"])
        or int(row[2]) != int(manifest["package_revision"])
        or str(row[3]) != str(manifest["source_sha256"])
        or str(row[4]) != "active"
    ):
        return {"status": "collision", "file_id": lesson_id, "document_id": str(manifest["document_id"])}
    return {
        "status": "active",
        "file_id": lesson_id,
        "document_id": str(row[0]),
        "owner_scope": owner_scope,
        "package_revision": int(row[2]),
    }


def deactivate_space_pdf_replica(connection: sqlite3.Connection, normalized_path: str) -> bool:
    path = _clean_path(normalized_path)
    connection.execute("BEGIN IMMEDIATE")
    try:
        changed = connection.execute(
            "UPDATE space_pdf_package_replicas SET status='inactive',last_seen_at_utc=? WHERE normalized_path=? COLLATE NOCASE AND status<>'inactive'",
            (_utc_now(), path),
        ).rowcount
        connection.execute(
            "UPDATE lesson_file_replicas SET status='inactive',last_seen_at_utc=? WHERE normalized_path=? COLLATE NOCASE",
            (_utc_now(), path),
        )
        connection.execute(
            "UPDATE lesson_file_aliases SET active=0,last_seen_at_utc=? WHERE normalized_path=? COLLATE NOCASE",
            (_utc_now(), path),
        )
        connection.execute("COMMIT")
        return bool(changed)
    except Exception:
        connection.execute("ROLLBACK")
        raise
