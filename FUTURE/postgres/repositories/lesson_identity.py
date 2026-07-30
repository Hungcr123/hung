"""PostgreSQL repository for portable lesson identity metadata."""

from __future__ import annotations

import hashlib
import json

import FUTURE.server_app as app

def _source_sha(row: dict) -> str:
    return hashlib.sha256(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()

def postgres_file_id_for_path(path_value: str = "") -> str:
    path = app.clean_path_value(path_value).lower()
    if not path:
        return ""

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT file_id FROM future_server2.lesson_file_aliases WHERE normalized_path=%s AND active=TRUE",
                (path,),
            )
            row = cursor.fetchone()
        return app.clean(row[0])[:240] if row is not None else ""

    return app.postgres_execute(_read)

def postgres_current_path(file_id_value: str = "") -> str:
    file_id = app.clean(file_id_value)[:240]
    if not file_id:
        return ""

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT normalized_path
                FROM future_server2.lesson_file_replicas
                WHERE file_id=%s AND status='active'
                ORDER BY CASE WHEN lower(normalized_path) LIKE 'common/%%' THEN 0 ELSE 1 END,
                    last_seen_at_utc DESC
                LIMIT 1
                """,
                (file_id,),
            )
            row = cursor.fetchone()
        return app.clean_path_value(row[0]) if row is not None else ""

    return app.postgres_execute(_read)

def postgres_active_alias_samples(limit: int = 100) -> list[dict]:
    safe_limit = max(1, min(1000, int(limit or 100)))

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT normalized_path,file_id FROM future_server2.lesson_file_aliases WHERE active=TRUE "
                "ORDER BY lower(normalized_path) LIMIT %s",
                (safe_limit,),
            )
            rows = cursor.fetchall()
        return [{"normalized_path": app.clean_path_value(row[0]).lower(), "file_id": app.clean(row[1])[:240]} for row in rows]

    return app.postgres_execute(_read)

def postgres_activity() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT state, count(*)
                FROM pg_stat_activity
                WHERE datname=current_database()
                GROUP BY state
                """
            )
            rows = cursor.fetchall()
        return {str(row[0] or "unknown"): int(row[1] or 0) for row in rows}

    return app.postgres_execute(_read)

def _progress_row_from_record(space: str, username: str, key: str, record: dict) -> dict:
    normalized_space = app.normalize_space_progress_space(space)
    normalized_user = app.normalize_username(username)
    payload = dict(record) if isinstance(record, dict) else {}
    if normalized_space in {"Space_PDF", "Space_Picture"}:
        payload = app.server_database_normalize_pdf_progress_record(payload)
    payload, completion_summary = app.server_database_canonicalize_progress_completion(payload, normalized_space)
    payload = app.server_database_normalize_timestamps(payload)
    updated_at = app.normalize_timestamp_text(payload.get("updatedAt") or payload.get("savedAt"), fallback_now=True)
    file_id = app.clean(payload.get("lesson_id") or payload.get("file_id") or payload.get("identity"))[:240]
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return {
        "username": normalized_user,
        "space": normalized_space,
        "progress_key": app.clean(key),
        "path": app.clean(payload.get("path", "")),
        "identity": app.clean(payload.get("identity", "")),
        "file_id": file_id,
        "node_index": max(0, app.space_w_int(payload.get("nodeIndex", 0), 0)),
        "node_count": max(0, app.space_w_int(payload.get("nodeCount", 0), 0)),
        "learned_count": max(0, app.space_w_int(completion_summary.get("learned_count", payload.get("learnedCount", 0)), 0)),
        "complete": bool(completion_summary.get("current_run_complete")),
        "server_revision": max(0, app.space_w_int(payload.get("_serverRevision", 0), 0)),
        "updated_at": updated_at,
        "updated_epoch": app.timestamp_to_epoch(updated_at),
        "record_json": raw,
        "source_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    }

def _upsert_progress_row(cursor, row: dict) -> None:
    cursor.execute(
        """
        INSERT INTO future_server2.lesson_progress_namespaces(username,space,updated_at_utc,updated_epoch)
        VALUES (%s,%s,%s,%s)
        ON CONFLICT (username,space) DO UPDATE SET
            updated_at_utc=excluded.updated_at_utc,
            updated_epoch=excluded.updated_epoch
        """,
        (row["username"], row["space"], row["updated_at"], row["updated_epoch"]),
    )
    cursor.execute(
        """
        INSERT INTO future_server2.lesson_progress
            (username,space,progress_key,path,identity,file_id,node_index,node_count,learned_count,complete,server_revision,updated_at_utc,updated_epoch,record_json,migrated_at_utc,source_sha256)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
        ON CONFLICT (username,file_id) DO UPDATE SET
            space=excluded.space,
            progress_key=excluded.progress_key,
            path=excluded.path,
            identity=excluded.identity,
            node_index=excluded.node_index,
            node_count=excluded.node_count,
            learned_count=excluded.learned_count,
            complete=excluded.complete,
            server_revision=excluded.server_revision,
            updated_at_utc=excluded.updated_at_utc,
            updated_epoch=excluded.updated_epoch,
            record_json=excluded.record_json,
            migrated_at_utc=excluded.migrated_at_utc,
            source_sha256=excluded.source_sha256
        WHERE excluded.server_revision>=future_server2.lesson_progress.server_revision
        """,
        (
            row["username"], row["space"], row["progress_key"], row["path"], row["identity"],
            row["file_id"], row["node_index"], row["node_count"], row["learned_count"], row["complete"],
            row["server_revision"], row["updated_at"], row["updated_epoch"], row["record_json"],
            app.utc_timestamp(), row["source_sha256"],
        ),
    )

def _reattach_legacy_progress(cursor, file_id: str, path: str) -> tuple[int, set[str]]:
    if app.postgres_backend_mode("LESSON_PROGRESS") != "postgres":
        return 0, set()
    cursor.execute(
        """
        SELECT username,space,progress_key,record_json
        FROM future_server2.lesson_progress
        WHERE file_id='' AND lower(path)=lower(%s)
        """,
        (path,),
    )
    rows = cursor.fetchall()
    attached = 0
    users: set[str] = set()
    merge_records = getattr(app, "_server_database_merge_identity_progress_records", None)
    for row in rows:
        username = app.normalize_username(row[0])
        space = app.normalize_space_progress_space(row[1])
        old_key = app.clean(row[2])
        legacy_record = dict(row[3]) if isinstance(row[3], dict) else {}
        new_key = hashlib.sha256(f"{username.lower()}|identity:{file_id}".encode("utf-8")).hexdigest()[:32]
        cursor.execute(
            "SELECT record_json FROM future_server2.lesson_progress WHERE username=%s AND space=%s AND progress_key=%s AND file_id<>''",
            (username, space, new_key),
        )
        target = cursor.fetchone()
        current_record = dict(target[0]) if target and isinstance(target[0], dict) else {}
        record = merge_records(current_record, legacy_record) if callable(merge_records) else {**current_record, **legacy_record}
        record.update({"key": new_key, "identity": file_id, "file_id": file_id, "lesson_id": file_id, "path": path})
        progress_row = _progress_row_from_record(space, username, new_key, record)
        _upsert_progress_row(cursor, progress_row)
        cursor.execute(
            "DELETE FROM future_server2.lesson_progress WHERE username=%s AND space=%s AND progress_key=%s AND file_id=''",
            (username, space, old_key),
        )
        if username:
            users.add(username)
        attached += 1
    return attached, users

def _rebind_vault_entries(cursor, file_id: str, path: str, replica_id: int, now: str, now_epoch: float) -> tuple[int, set[str]]:
    if app.postgres_backend_mode("VAULT_METADATA") != "postgres":
        return 0, set()
    cursor.execute(
        """
        UPDATE future_server2.vault_entries
        SET entry_type='PHYSICAL_REPLICA',
            physical_replica_id=%s,
            source_path=%s,
            updated_at_utc=%s,
            updated_epoch=%s,
            migrated_at_utc=%s
        WHERE lesson_id=%s AND status='active' AND lower(source_path)=lower(%s)
        RETURNING username
        """,
        (replica_id, path, now, now_epoch, now, file_id, path),
    )
    users = {app.normalize_username(row[0]) for row in cursor.fetchall() if app.normalize_username(row[0])}
    for user in users:
        cursor.execute(
            """
            INSERT INTO future_server2.vault_revisions(username,revision,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
            VALUES (%s,1,%s,%s,%s,'runtime')
            ON CONFLICT(username) DO UPDATE SET
                revision=future_server2.vault_revisions.revision+1,
                updated_at_utc=excluded.updated_at_utc,
                updated_epoch=excluded.updated_epoch,
                migrated_at_utc=excluded.migrated_at_utc,
                source_sha256=excluded.source_sha256
            """,
            (user, now, now_epoch, now),
        )
    return len(users), users

# Added 2026-07-25: PostgreSQL runtime registration for identity-only lesson file rows.
def register_lesson_file_entries(entries: list[dict] | tuple[dict, ...], inactive_paths=()) -> dict:
    rows = [dict(entry) for entry in (entries or []) if isinstance(entry, dict) and app.clean(entry.get("lesson_id", ""))]
    normalized_inactive = sorted({app.clean_path_value(path) for path in (inactive_paths or []) if app.clean_path_value(path)})
    if not rows and not normalized_inactive:
        return {"ok": True, "registered": 0, "collisions": 0, "inactive": 0, "active_aliases": [], "quarantined_aliases": []}

    def _write(connection):
        now = app.utc_timestamp()
        now_epoch = app.timestamp_to_epoch(now)
        registered = 0
        collisions = 0
        inactive = 0
        reattached_progress = 0
        reattached_users: set[str] = set()
        rebound_vault_entries = 0
        rebound_vault_users: set[str] = set()
        active_aliases: list[tuple[str, str]] = []
        quarantined_aliases: list[str] = []
        with connection.cursor() as cursor:
            incoming_by_file: dict[str, dict[str, list[str]]] = {}
            for entry in rows:
                file_id = app.clean(entry.get("lesson_id", ""))[:240]
                path = app.clean_path_value(entry.get("path", ""))
                fingerprint = app.clean(entry.get("content_fingerprint", ""))[:320]
                if file_id and path and fingerprint:
                    incoming_by_file.setdefault(file_id, {}).setdefault(fingerprint, []).append(path.lower())
            for file_id, fingerprint_groups in incoming_by_file.items():
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s))",
                    (f"future_server2.lesson_identity.file:{file_id}",),
                )
                if len(fingerprint_groups) != 1:
                    continue
                fingerprint, paths = next(iter(fingerprint_groups.items()))
                for path in paths:
                    cursor.execute(
                        "UPDATE future_server2.lesson_file_replicas SET fingerprint=%s WHERE file_id=%s AND lower(normalized_path)=lower(%s)",
                        (fingerprint, file_id, path),
                    )
                cursor.execute(
                    "UPDATE future_server2.lesson_files SET canonical_fingerprint=%s,status='active',updated_at_utc=%s,updated_epoch=%s WHERE file_id=%s",
                    (fingerprint, now, now_epoch, file_id),
                )
            for path in normalized_inactive:
                cursor.execute(
                    """
                    UPDATE future_server2.lesson_file_replicas
                    SET status='inactive',last_seen_at_utc=%s,last_seen_epoch=%s,migrated_at_utc=%s
                    WHERE (lower(normalized_path)=lower(%s) OR lower(normalized_path) LIKE lower(%s) ESCAPE '\\')
                        AND status<>'inactive'
                    """,
                    (now, now_epoch, now, path, path.replace("%", "\\%").replace("_", "\\_") + "/%"),
                )
                inactive += max(0, int(cursor.rowcount or 0))
                cursor.execute(
                    """
                    UPDATE future_server2.lesson_file_aliases
                    SET active=FALSE,last_seen_at_utc=%s,last_seen_epoch=%s,migrated_at_utc=%s
                    WHERE (lower(normalized_path)=lower(%s) OR lower(normalized_path) LIKE lower(%s) ESCAPE '\\')
                        AND active=TRUE
                    """,
                    (now, now_epoch, now, path, path.replace("%", "\\%").replace("_", "\\_") + "/%"),
                )
            for entry in rows:
                file_id = app.clean(entry.get("lesson_id", ""))[:240]
                path = app.clean_path_value(entry.get("path", ""))
                path_key = path.lower()
                fingerprint = app.clean(entry.get("content_fingerprint", ""))[:320]
                if not file_id or not path or not file_id.lower().startswith("ftg-lesson-"):
                    continue
                suffix = Path(path).suffix.lower()
                if suffix == ".pdf" or suffix in app.IMAGE_FILE_SUFFIXES:
                    continue
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s))",
                    (f"future_server2.lesson_identity.file:{file_id}",),
                )
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s))",
                    (f"future_server2.lesson_identity.path:{path_key}",),
                )
                space_id = "Space_" + suffix.split(".space_", 1)[-1].upper() if suffix.startswith(".space_") else app.clean(entry.get("space", ""))
                cursor.execute(
                    """
                    SELECT fingerprint
                    FROM future_server2.lesson_file_replicas
                    WHERE file_id=%s AND lower(normalized_path)<>lower(%s) AND status='active' AND fingerprint<>''
                    """,
                    (file_id, path_key),
                )
                other_fingerprints = {app.clean(row[0]) for row in cursor.fetchall() if app.clean(row[0])}
                collision = bool(fingerprint and other_fingerprints and fingerprint not in other_fingerprints)
                file_payload = {
                    "file_id": file_id,
                    "space_id": space_id,
                    "kind": "space",
                    "canonical_fingerprint": fingerprint,
                    "identity_revision": 1,
                    "status": "collision" if collision else "active",
                    "created_at_utc": now,
                    "created_epoch": now_epoch,
                    "updated_at_utc": now,
                    "updated_epoch": now_epoch,
                    "deleted_at_utc": "",
                    "deleted_epoch": 0,
                }
                cursor.execute(
                    """
                    INSERT INTO future_server2.lesson_files
                        (file_id,space_id,kind,canonical_fingerprint,identity_revision,status,created_at_utc,created_epoch,updated_at_utc,updated_epoch,deleted_at_utc,deleted_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,'space',%s,1,%s,%s,%s,%s,%s,'',0,%s,%s)
                    ON CONFLICT(file_id) DO UPDATE SET
                        space_id=CASE WHEN excluded.space_id<>'' THEN excluded.space_id ELSE future_server2.lesson_files.space_id END,
                        canonical_fingerprint=CASE WHEN future_server2.lesson_files.canonical_fingerprint='' THEN excluded.canonical_fingerprint ELSE future_server2.lesson_files.canonical_fingerprint END,
                        status=excluded.status,
                        updated_at_utc=excluded.updated_at_utc,
                        updated_epoch=excluded.updated_epoch,
                        migrated_at_utc=excluded.migrated_at_utc,
                        source_sha256=excluded.source_sha256
                    """,
                    (file_id, space_id, fingerprint, file_payload["status"], now, now_epoch, now, now_epoch, now, _source_sha(file_payload)),
                )
                cursor.execute("SELECT replica_id FROM future_server2.lesson_file_replicas WHERE lower(normalized_path)=lower(%s)", (path_key,))
                replica_row = cursor.fetchone()
                if replica_row is None:
                    cursor.execute("SELECT nextval('future_server2.lesson_file_replicas_runtime_id_seq')")
                    replica_id = int((cursor.fetchone() or [1])[0] or 1)
                else:
                    replica_id = int(replica_row[0] or 0)
                replica_payload = {
                    "replica_id": replica_id,
                    "file_id": file_id,
                    "normalized_path": path_key,
                    "fingerprint": fingerprint,
                    "file_mtime_ns": max(0, app.space_w_int(entry.get("modified_ns", 0), 0)),
                    "file_size": max(0, app.space_w_int(entry.get("size", 0), 0)),
                    "status": "collision" if collision else "active",
                    "first_seen_at_utc": now,
                    "first_seen_epoch": now_epoch,
                    "last_seen_at_utc": now,
                    "last_seen_epoch": now_epoch,
                }
                cursor.execute(
                    """
                    INSERT INTO future_server2.lesson_file_replicas
                        (replica_id,file_id,normalized_path,fingerprint,file_mtime_ns,file_size,status,first_seen_at_utc,first_seen_epoch,last_seen_at_utc,last_seen_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(normalized_path) DO UPDATE SET
                        file_id=excluded.file_id,fingerprint=excluded.fingerprint,file_mtime_ns=excluded.file_mtime_ns,
                        file_size=excluded.file_size,status=excluded.status,last_seen_at_utc=excluded.last_seen_at_utc,
                        last_seen_epoch=excluded.last_seen_epoch,migrated_at_utc=excluded.migrated_at_utc,source_sha256=excluded.source_sha256
                    """,
                    (
                        replica_id, file_id, path_key, fingerprint, replica_payload["file_mtime_ns"], replica_payload["file_size"],
                        replica_payload["status"], now, now_epoch, now, now_epoch, now, _source_sha(replica_payload),
                    ),
                )
                alias_payload = {
                    "normalized_path": path_key,
                    "file_id": file_id,
                    "source": "manifest",
                    "active": not collision,
                    "first_seen_at_utc": now,
                    "first_seen_epoch": now_epoch,
                    "last_seen_at_utc": now,
                    "last_seen_epoch": now_epoch,
                }
                cursor.execute(
                    """
                    INSERT INTO future_server2.lesson_file_aliases
                        (normalized_path,file_id,source,active,first_seen_at_utc,first_seen_epoch,last_seen_at_utc,last_seen_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,'manifest',%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(normalized_path) DO UPDATE SET
                        file_id=excluded.file_id,source='manifest',active=excluded.active,
                        last_seen_at_utc=excluded.last_seen_at_utc,last_seen_epoch=excluded.last_seen_epoch,
                        migrated_at_utc=excluded.migrated_at_utc,source_sha256=excluded.source_sha256
                    """,
                    (path_key, file_id, not collision, now, now_epoch, now, now_epoch, now, _source_sha(alias_payload)),
                )
                if collision:
                    quarantined_aliases.append(path_key)
                else:
                    active_aliases.append((path_key, file_id))
                    attached, users = _reattach_legacy_progress(cursor, file_id, path_key)
                    reattached_progress += attached
                    reattached_users.update(users)
                    rebound, vault_users = _rebind_vault_entries(cursor, file_id, path_key, replica_id, now, now_epoch)
                    rebound_vault_entries += rebound
                    rebound_vault_users.update(vault_users)
                registered += 1
                collisions += 1 if collision else 0
        return {
            "ok": True,
            "registered": registered,
            "collisions": collisions,
            "reattached_progress": reattached_progress,
            "reattached_users": sorted(reattached_users),
            "inactive": inactive,
            "active_aliases": active_aliases,
            "quarantined_aliases": quarantined_aliases,
            "rebound_vault_entries": rebound_vault_entries,
            "rebound_vault_users": sorted(rebound_vault_users),
        }

    return app.postgres_execute(_write)

def mark_lesson_file_paths_inactive(paths: list[str] | tuple[str, ...] | set[str]) -> int:
    normalized = sorted({app.clean_path_value(path) for path in (paths or []) if app.clean_path_value(path)})
    if not normalized:
        return 0

    def _write(connection):
        now = app.utc_timestamp()
        now_epoch = app.timestamp_to_epoch(now)
        changed = 0
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext('future_server2.lesson_identity.inactive'))")
            for path in normalized:
                cursor.execute(
                    """
                    UPDATE future_server2.lesson_file_replicas
                    SET status='inactive',last_seen_at_utc=%s,last_seen_epoch=%s,migrated_at_utc=%s
                    WHERE (lower(normalized_path)=lower(%s) OR lower(normalized_path) LIKE lower(%s) ESCAPE '\\')
                        AND status<>'inactive'
                    """,
                    (now, now_epoch, now, path, path.replace("%", "\\%").replace("_", "\\_") + "/%"),
                )
                changed += max(0, int(cursor.rowcount or 0))
                cursor.execute(
                    """
                    UPDATE future_server2.lesson_file_aliases
                    SET active=FALSE,last_seen_at_utc=%s,last_seen_epoch=%s,migrated_at_utc=%s
                    WHERE (lower(normalized_path)=lower(%s) OR lower(normalized_path) LIKE lower(%s) ESCAPE '\\')
                        AND active=TRUE
                    """,
                    (now, now_epoch, now, path, path.replace("%", "\\%").replace("_", "\\_") + "/%"),
                )
        return changed

    return int(app.postgres_execute(_write) or 0)
