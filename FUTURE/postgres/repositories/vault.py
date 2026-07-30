"""PostgreSQL runtime repository for Lesson Vault metadata."""

from __future__ import annotations

from pathlib import Path

import FUTURE.server_app as app

def load_cache_rows(username: str = "") -> dict:
    user = app.normalize_username(username)

    def _read(connection):
        with connection.cursor() as cursor:
            params = []
            user_filter = ""
            if user:
                user_filter = " AND username=%s"
                params.append(user)
            cursor.execute(
                "SELECT vault_folder_id,username,parent_folder_id,display_name,folder_type,source_path,sort_order,status "
                f"FROM future_server2.vault_folders WHERE status='active'{user_filter}",
                tuple(params),
            )
            folders = [
                {
                    "vault_folder_id": app.clean(row[0]),
                    "username": app.normalize_username(row[1]),
                    "parent_folder_id": app.clean(row[2]),
                    "display_name": app.clean(row[3]),
                    "folder_type": app.clean(row[4]),
                    "source_path": app.clean_path_value(row[5]),
                    "sort_order": int(row[6] or 0),
                    "status": app.clean(row[7]),
                }
                for row in cursor.fetchall()
            ]
            cursor.execute(
                "SELECT vault_entry_id,username,parent_folder_id,lesson_id,entry_type,physical_replica_id,source_entry_id,source_path,display_name,sort_order,status "
                f"FROM future_server2.vault_entries WHERE status='active'{user_filter}",
                tuple(params),
            )
            entries = [
                {
                    "vault_entry_id": app.clean(row[0]),
                    "username": app.normalize_username(row[1]),
                    "parent_folder_id": app.clean(row[2]),
                    "lesson_id": app.clean(row[3]),
                    "entry_type": app.clean(row[4]),
                    "physical_replica_id": row[5],
                    "source_entry_id": app.clean(row[6]),
                    "source_path": app.clean_path_value(row[7]),
                    "display_name": app.clean(row[8]),
                    "sort_order": int(row[9] or 0),
                    "status": app.clean(row[10]),
                }
                for row in cursor.fetchall()
            ]
            cursor.execute(
                "SELECT username,revision FROM future_server2.vault_revisions"
                + (" WHERE username=%s" if user else ""),
                tuple([user] if user else []),
            )
            revisions = {
                app.normalize_username(row[0]).lower(): max(0, int(row[1] or 0))
                for row in cursor.fetchall()
                if app.normalize_username(row[0])
            }
            cursor.execute("SELECT link_path FROM future_server2.lesson_folder_links WHERE status IN ('active','migrated')")
            link_paths = [app.clean_path_value(row[0]) for row in cursor.fetchall()]
        return {"folders": folders, "entries": entries, "revisions": revisions, "link_paths": link_paths}

    return app.postgres_execute(_read)


# Added 2026-07-30: resolve a Vault replica from PostgreSQL authority only.
def resolved_source_path(replica_id: object, lesson_id: str = "") -> str:
    try:
        safe_replica_id = int(replica_id)
    except (TypeError, ValueError):
        return ""
    file_id = app.clean(lesson_id)

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT normalized_path FROM future_server2.lesson_file_replicas "
                "WHERE replica_id=%s AND file_id=%s AND status='active'",
                (safe_replica_id, file_id),
            )
            row = cursor.fetchone()
        return app.clean_path_value(row[0]) if row is not None else ""

    return app.clean_path_value(app.postgres_execute(_read))


def create_virtual_folder(username: str, destination: str, desired_name: str, folder_id: str, now: str) -> dict:
    """Added 2026-07-29: create one Vault folder and revision in one PostgreSQL transaction."""
    user = app.normalize_username(username)
    parts = [app.clean(part) for part in app.clean_path_value(destination).split("/") if app.clean(part)]
    if not user or not parts or app.normalize_username(parts[0]).lower() != user.lower():
        raise RuntimeError("Invalid Vault destination.")
    wanted = app.clean(desired_name) or "New folder"
    created_epoch = app.timestamp_to_epoch(now)

    def _write(connection):
        with connection.cursor() as cursor:
            # Serialize one user's naming/revision stream across Server 2 processes.
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext(lower(%s)))", (user,))
            root_id = app._server_database_vault_root_id(user)
            cursor.execute(
                """
                INSERT INTO future_server2.vault_folders
                    (vault_folder_id,username,parent_folder_id,display_name,folder_type,source_path,status,created_at_utc,created_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,'',%s,'ROOT',%s,'active',%s,%s,%s,%s,%s,'')
                ON CONFLICT(vault_folder_id) DO NOTHING
                """,
                (root_id, user, user, user, now, created_epoch, now, created_epoch, now),
            )
            parent_id = root_id
            current_path = user
            for part in parts[1:]:
                cursor.execute(
                    """
                    SELECT vault_folder_id,source_path,folder_type
                    FROM future_server2.vault_folders
                    WHERE username=%s AND parent_folder_id=%s AND lower(display_name)=lower(%s) AND status='active'
                    ORDER BY vault_folder_id LIMIT 1
                    """,
                    (user, parent_id, part),
                )
                row = cursor.fetchone()
                current_path = app.clean_path_value(f"{current_path}/{part}")
                if row:
                    parent_id = app.clean(row[0])
                    continue
                container_id = app._server_database_vault_id("vault-folder", f"{user}|{current_path}")
                cursor.execute(
                    """
                    INSERT INTO future_server2.vault_folders
                        (vault_folder_id,username,parent_folder_id,display_name,folder_type,source_path,status,created_at_utc,created_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,'PHYSICAL_CONTAINER',%s,'active',%s,%s,%s,%s,%s,'')
                    ON CONFLICT(vault_folder_id) DO UPDATE SET status='active',updated_at_utc=excluded.updated_at_utc,updated_epoch=excluded.updated_epoch
                    """,
                    (container_id, user, parent_id, part, current_path, now, created_epoch, now, created_epoch, now),
                )
                parent_id = container_id
            cursor.execute(
                """
                SELECT display_name FROM future_server2.vault_folders
                WHERE username=%s AND parent_folder_id=%s AND status='active'
                UNION ALL
                SELECT display_name FROM future_server2.vault_entries
                WHERE username=%s AND parent_folder_id=%s AND status='active'
                """,
                (user, parent_id, user, parent_id),
            )
            names = {app.clean(row[0]).lower() for row in cursor.fetchall()}
            name = wanted
            suffix = Path(wanted).suffix
            stem = wanted[:-len(suffix)] if suffix else wanted
            for index in range(1, 10000):
                if name.lower() not in names:
                    break
                name = f"{stem} - link {index + 1}{suffix}"
            else:
                raise RuntimeError("Cannot allocate Vault display name.")
            cursor.execute(
                """
                INSERT INTO future_server2.vault_folders
                    (vault_folder_id,username,parent_folder_id,display_name,folder_type,source_path,status,created_at_utc,created_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,'VIRTUAL','','active',%s,%s,%s,%s,%s,'')
                """,
                (folder_id, user, parent_id, name, now, created_epoch, now, created_epoch, now),
            )
            cursor.execute(
                """
                INSERT INTO future_server2.vault_revisions
                    (username,revision,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,1,%s,%s,%s,'')
                ON CONFLICT(username) DO UPDATE SET
                    revision=future_server2.vault_revisions.revision+1,
                    updated_at_utc=excluded.updated_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc
                RETURNING revision
                """,
                (user, now, created_epoch, now),
            )
            revision = max(1, int(cursor.fetchone()[0] or 1))
        return {
            "vault_folder_id": folder_id,
            "username": user,
            "parent_folder_id": parent_id,
            "display_name": name,
            "folder_type": "VIRTUAL",
            "source_path": "",
            "sort_order": 0,
            "status": "active",
            "revision": revision,
        }

    return app.postgres_execute(_write)


def mutate_vault(
    action: str,
    username: str,
    source: str,
    destination: str,
    source_entry: dict,
    source_folder: dict,
    desired_name: str,
    direction: str,
    now: str,
) -> dict:
    """Added 2026-07-29: apply non-create Vault mutations directly in PostgreSQL."""
    user = app.normalize_username(username)
    operation = app.clean(action).lower()
    source_path = app.clean_path_value(source)
    destination_path = app.clean_path_value(destination)
    updated_epoch = app.timestamp_to_epoch(now)
    if not user or operation not in {"copy_link", "move", "rename", "reorder", "delete_link"}:
        raise RuntimeError("Invalid PostgreSQL Vault operation.")

    def ensure_parent(cursor, path_value: str) -> str:
        parts = [app.clean(part) for part in app.clean_path_value(path_value).split("/") if app.clean(part)]
        if not parts or app.normalize_username(parts[0]).lower() != user.lower():
            raise RuntimeError("Invalid Vault destination.")
        root_id = app._server_database_vault_root_id(user)
        cursor.execute(
            """
            INSERT INTO future_server2.vault_folders
                (vault_folder_id,username,parent_folder_id,display_name,folder_type,source_path,status,created_at_utc,created_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
            VALUES (%s,%s,'',%s,'ROOT',%s,'active',%s,%s,%s,%s,%s,'')
            ON CONFLICT(vault_folder_id) DO NOTHING
            """,
            (root_id, user, user, user, now, updated_epoch, now, updated_epoch, now),
        )
        parent_id = root_id
        current = user
        for part in parts[1:]:
            cursor.execute(
                "SELECT vault_folder_id FROM future_server2.vault_folders WHERE username=%s AND parent_folder_id=%s AND lower(display_name)=lower(%s) AND status='active' ORDER BY vault_folder_id LIMIT 1",
                (user, parent_id, part),
            )
            row = cursor.fetchone()
            current = app.clean_path_value(f"{current}/{part}")
            if row:
                parent_id = app.clean(row[0])
                continue
            container_id = app._server_database_vault_id("vault-folder", f"{user}|{current}")
            cursor.execute(
                """
                INSERT INTO future_server2.vault_folders
                    (vault_folder_id,username,parent_folder_id,display_name,folder_type,source_path,status,created_at_utc,created_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,'PHYSICAL_CONTAINER',%s,'active',%s,%s,%s,%s,%s,'')
                ON CONFLICT(vault_folder_id) DO UPDATE SET status='active',updated_at_utc=excluded.updated_at_utc,updated_epoch=excluded.updated_epoch
                """,
                (container_id, user, parent_id, part, current, now, updated_epoch, now, updated_epoch, now),
            )
            parent_id = container_id
        return parent_id

    def unique_name(cursor, parent_id: str, wanted: str) -> str:
        base = app.clean(wanted) or "Lesson"
        cursor.execute(
            """
            SELECT display_name FROM future_server2.vault_folders WHERE username=%s AND parent_folder_id=%s AND status='active'
            UNION ALL
            SELECT display_name FROM future_server2.vault_entries WHERE username=%s AND parent_folder_id=%s AND status='active'
            """,
            (user, parent_id, user, parent_id),
        )
        names = {app.clean(row[0]).lower() for row in cursor.fetchall()}
        suffix = Path(base).suffix
        stem = base[:-len(suffix)] if suffix else base
        candidate = base
        for index in range(1, 10000):
            if candidate.lower() not in names:
                return candidate
            candidate = f"{stem} - link {index + 1}{suffix}"
        raise RuntimeError("Cannot allocate Vault display name.")

    def touch_revision(cursor) -> int:
        cursor.execute(
            """
            INSERT INTO future_server2.vault_revisions(username,revision,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
            VALUES (%s,1,%s,%s,%s,'')
            ON CONFLICT(username) DO UPDATE SET
                revision=future_server2.vault_revisions.revision+1,
                updated_at_utc=excluded.updated_at_utc,
                updated_epoch=excluded.updated_epoch,
                migrated_at_utc=excluded.migrated_at_utc
            RETURNING revision
            """,
            (user, now, updated_epoch, now),
        )
        return max(1, int(cursor.fetchone()[0] or 1))

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext(lower(%s)))", (user,))
            entry_id = app.clean((source_entry or {}).get("vault_entry_id", ""))
            folder_id = app.clean((source_folder or {}).get("vault_folder_id", ""))
            entry_row = None
            folder_row = None
            if entry_id:
                cursor.execute(
                    "SELECT vault_entry_id,parent_folder_id,lesson_id,entry_type,physical_replica_id,source_entry_id,source_path,display_name,sort_order FROM future_server2.vault_entries WHERE vault_entry_id=%s AND username=%s AND status='active'",
                    (entry_id, user),
                )
                entry_row = cursor.fetchone()
            if folder_id:
                cursor.execute(
                    "SELECT vault_folder_id,parent_folder_id,display_name,folder_type,source_path,sort_order FROM future_server2.vault_folders WHERE vault_folder_id=%s AND username=%s AND status='active'",
                    (folder_id, user),
                )
                folder_row = cursor.fetchone()

            result = {}
            if operation == "copy_link":
                parent_id = ensure_parent(cursor, destination_path)
                base_name = app.clean(desired_name) or app.clean((source_folder or source_entry or {}).get("display_name", "")) or Path(source_path).name
                name = unique_name(cursor, parent_id, base_name)
                if folder_row:
                    new_root_id = app._server_database_vault_id("vault-folder")
                    cursor.execute(
                        "INSERT INTO future_server2.vault_folders(vault_folder_id,username,parent_folder_id,display_name,folder_type,source_path,status,created_at_utc,created_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256) VALUES(%s,%s,%s,%s,'VIRTUAL_IMPORT',%s,'active',%s,%s,%s,%s,%s,'')",
                        (new_root_id, user, parent_id, name, app.clean_path_value(folder_row[4]), now, updated_epoch, now, updated_epoch, now),
                    )
                    cursor.execute(
                        "SELECT vault_folder_id,parent_folder_id,display_name,sort_order FROM future_server2.vault_folders WHERE username=%s AND status='active'",
                        (user,),
                    )
                    folders = cursor.fetchall()
                    cursor.execute(
                        "SELECT vault_entry_id,parent_folder_id,lesson_id,entry_type,physical_replica_id,source_entry_id,source_path,display_name,sort_order FROM future_server2.vault_entries WHERE username=%s AND status='active'",
                        (user,),
                    )
                    entries = cursor.fetchall()
                    children = {}
                    for row in folders:
                        children.setdefault(app.clean(row[1]), []).append(row)
                    entry_children = {}
                    for row in entries:
                        entry_children.setdefault(app.clean(row[1]), []).append(row)
                    queue = [(folder_id, new_root_id)]
                    while queue:
                        old_parent, new_parent = queue.pop(0)
                        for row in entry_children.get(old_parent, []):
                            new_entry_id = app._server_database_vault_id("vault-entry")
                            cursor.execute(
                                "INSERT INTO future_server2.vault_entries(vault_entry_id,username,parent_folder_id,lesson_id,entry_type,physical_replica_id,source_entry_id,source_path,display_name,sort_order,status,created_at_utc,created_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'active',%s,%s,%s,%s,%s,'')",
                                (new_entry_id, user, new_parent, app.clean(row[2]), app.clean(row[3]), row[4], app.clean(row[0]), app.clean_path_value(row[6]), app.clean(row[7]), int(row[8] or 0), now, updated_epoch, now, updated_epoch, now),
                            )
                        for row in children.get(old_parent, []):
                            new_folder_id = app._server_database_vault_id("vault-folder")
                            cursor.execute(
                                "INSERT INTO future_server2.vault_folders(vault_folder_id,username,parent_folder_id,display_name,folder_type,source_path,sort_order,status,created_at_utc,created_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256) VALUES(%s,%s,%s,%s,'VIRTUAL','',%s,'active',%s,%s,%s,%s,%s,'')",
                                (new_folder_id, user, new_parent, app.clean(row[2]), int(row[3] or 0), now, updated_epoch, now, updated_epoch, now),
                            )
                            queue.append((app.clean(row[0]), new_folder_id))
                    result = {"path": app.clean_path_value(f"{destination_path}/{name}"), "name": name, "type": "folder", "vault_folder_id": new_root_id, "virtual": True}
                else:
                    lesson_id = app.clean(entry_row[2]) if entry_row else ""
                    replica_id = entry_row[4] if entry_row else None
                    physical_source = app.clean_path_value(entry_row[6]) if entry_row else source_path
                    if not lesson_id:
                        cursor.execute(
                            "SELECT replica_id,file_id,normalized_path FROM future_server2.lesson_file_replicas WHERE lower(normalized_path)=lower(%s) AND status='active' ORDER BY replica_id LIMIT 1",
                            (physical_source,),
                        )
                        replica = cursor.fetchone()
                        if replica:
                            replica_id, lesson_id, physical_source = replica[0], app.clean(replica[1]), app.clean_path_value(replica[2])
                    if not lesson_id:
                        prefix = physical_source.rstrip("/") + "/%"
                        cursor.execute(
                            "SELECT replica_id,file_id,normalized_path FROM future_server2.lesson_file_replicas WHERE normalized_path ILIKE %s AND status='active' ORDER BY normalized_path",
                            (prefix,),
                        )
                        replicas = cursor.fetchall()
                        if not replicas:
                            raise RuntimeError("Source lesson or folder has no registered lesson_id.")
                        new_root_id = app._server_database_vault_id("vault-folder")
                        cursor.execute(
                            "INSERT INTO future_server2.vault_folders(vault_folder_id,username,parent_folder_id,display_name,folder_type,source_path,status,created_at_utc,created_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256) VALUES(%s,%s,%s,%s,'VIRTUAL_IMPORT',%s,'active',%s,%s,%s,%s,%s,'')",
                            (new_root_id, user, parent_id, name, physical_source, now, updated_epoch, now, updated_epoch, now),
                        )
                        folder_ids = {"": new_root_id}
                        for replica in replicas:
                            relative = app.clean_path_value(replica[2])[len(physical_source):].lstrip("/")
                            parts = [app.clean(part) for part in relative.split("/") if app.clean(part)]
                            if not parts:
                                continue
                            nested_parent = new_root_id
                            relative_parent = ""
                            for folder_name in parts[:-1]:
                                relative_parent = app.clean_path_value(f"{relative_parent}/{folder_name}")
                                nested_id = folder_ids.get(relative_parent)
                                if not nested_id:
                                    nested_id = app._server_database_vault_id("vault-folder", f"{user}|{new_root_id}|{relative_parent}")
                                    cursor.execute(
                                        "INSERT INTO future_server2.vault_folders(vault_folder_id,username,parent_folder_id,display_name,folder_type,source_path,status,created_at_utc,created_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256) VALUES(%s,%s,%s,%s,'VIRTUAL','','active',%s,%s,%s,%s,%s,'') ON CONFLICT(vault_folder_id) DO NOTHING",
                                        (nested_id, user, nested_parent, folder_name, now, updated_epoch, now, updated_epoch, now),
                                    )
                                    folder_ids[relative_parent] = nested_id
                                nested_parent = nested_id
                            new_entry_id = app._server_database_vault_id("vault-entry", f"{user}|{new_root_id}|{relative}")
                            cursor.execute(
                                "INSERT INTO future_server2.vault_entries(vault_entry_id,username,parent_folder_id,lesson_id,entry_type,physical_replica_id,source_entry_id,source_path,display_name,status,created_at_utc,created_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256) VALUES(%s,%s,%s,%s,%s,%s,'',%s,%s,'active',%s,%s,%s,%s,%s,'') ON CONFLICT(vault_entry_id) DO NOTHING",
                                (new_entry_id, user, nested_parent, app.clean(replica[1]), "COMMON_REFERENCE" if app.server_data_path_top(replica[2]) == "common" else "PHYSICAL_REPLICA", replica[0], app.clean_path_value(replica[2]), parts[-1], now, updated_epoch, now, updated_epoch, now),
                            )
                        result = {"path": app.clean_path_value(f"{destination_path}/{name}"), "name": name, "type": "folder", "vault_folder_id": new_root_id, "virtual": True}
                    else:
                        new_entry_id = app._server_database_vault_id("vault-entry")
                        cursor.execute(
                            "INSERT INTO future_server2.vault_entries(vault_entry_id,username,parent_folder_id,lesson_id,entry_type,physical_replica_id,source_entry_id,source_path,display_name,status,created_at_utc,created_epoch,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'active',%s,%s,%s,%s,%s,'')",
                            (new_entry_id, user, parent_id, lesson_id, "COMMON_REFERENCE" if app.server_data_path_top(physical_source) == "common" else "PHYSICAL_REPLICA", replica_id, entry_id, physical_source, name, now, updated_epoch, now, updated_epoch, now),
                        )
                        result = {"path": app.clean_path_value(f"{destination_path}/{name}"), "name": name, "type": "file", "vault_entry_id": new_entry_id, "lesson_id": lesson_id, "virtual": True}
            elif operation == "reorder":
                row = entry_row or folder_row
                if not row:
                    raise RuntimeError("Only a Vault placement can be reordered.")
                is_entry = bool(entry_row)
                table = "vault_entries" if is_entry else "vault_folders"
                id_column = "vault_entry_id" if is_entry else "vault_folder_id"
                item_id = app.clean(row[0])
                parent_id = app.clean(row[1])
                cursor.execute(
                    f"SELECT {id_column},display_name,sort_order FROM future_server2.{table} WHERE username=%s AND parent_folder_id=%s AND status='active' ORDER BY CASE WHEN sort_order>0 THEN 0 ELSE 1 END,sort_order,lower(display_name)",
                    (user, parent_id),
                )
                siblings = cursor.fetchall()
                ids = [app.clean(item[0]) for item in siblings]
                if item_id not in ids:
                    raise RuntimeError("Vault placement is no longer active.")
                current_index = ids.index(item_id)
                target_index = current_index - 1 if direction == "up" else current_index + 1 if direction == "down" else current_index
                target_index = max(0, min(len(ids) - 1, target_index))
                if target_index != current_index:
                    ids[current_index], ids[target_index] = ids[target_index], ids[current_index]
                cursor.executemany(
                    f"UPDATE future_server2.{table} SET sort_order=%s,updated_at_utc=%s,updated_epoch=%s WHERE {id_column}=%s AND username=%s",
                    [((index + 1) * 10, now, updated_epoch, sibling_id, user) for index, sibling_id in enumerate(ids)],
                )
                result = {"path": source_path, "name": app.clean(row[2] if is_entry else row[2]), "type": "file" if is_entry else "folder", id_column: item_id, "sort_order": (target_index + 1) * 10, "virtual": True}
            elif operation in {"move", "rename"}:
                row = entry_row or folder_row
                if not row:
                    raise RuntimeError("Only a Vault placement can be moved or renamed.")
                is_entry = bool(entry_row)
                item_id = app.clean(row[0])
                current_parent = app.clean(row[1])
                current_name = app.clean(row[7] if is_entry else row[2])
                if not is_entry and item_id == app._server_database_vault_root_id(user):
                    raise RuntimeError("Cannot move Vault root.")
                if operation == "move" and (destination_path.lower() == source_path.lower() or destination_path.lower().startswith(source_path.lower() + "/")):
                    raise RuntimeError("Cannot move a Vault folder into itself.")
                parent_id = ensure_parent(cursor, destination_path) if operation == "move" else current_parent
                name = app.clean(desired_name) or current_name
                if operation == "move":
                    name = unique_name(cursor, parent_id, name)
                table = "vault_entries" if is_entry else "vault_folders"
                id_column = "vault_entry_id" if is_entry else "vault_folder_id"
                cursor.execute(
                    f"UPDATE future_server2.{table} SET parent_folder_id=%s,display_name=%s,updated_at_utc=%s,updated_epoch=%s WHERE {id_column}=%s AND username=%s",
                    (parent_id, name, now, updated_epoch, item_id, user),
                )
                result_path = app.clean_path_value(f"{destination_path}/{name}" if operation == "move" else f"{source_path.rsplit('/', 1)[0]}/{name}")
                result = {"path": result_path, "name": name, "type": "file" if is_entry else "folder", id_column: item_id, "virtual": True}
            else:
                if entry_row:
                    cursor.execute(
                        "UPDATE future_server2.vault_entries SET status='removed',updated_at_utc=%s,updated_epoch=%s WHERE vault_entry_id=%s AND username=%s",
                        (now, updated_epoch, entry_id, user),
                    )
                    result = {"path": source_path, "name": app.clean(entry_row[7]), "type": "file", "vault_entry_id": entry_id, "virtual": True}
                elif folder_row:
                    if folder_id == app._server_database_vault_root_id(user):
                        raise RuntimeError("Cannot remove Vault root.")
                    cursor.execute(
                        """
                        WITH RECURSIVE subtree(id) AS (
                            SELECT %s UNION ALL
                            SELECT f.vault_folder_id FROM future_server2.vault_folders f JOIN subtree s ON f.parent_folder_id=s.id
                            WHERE f.username=%s AND f.status='active'
                        )
                        UPDATE future_server2.vault_entries SET status='removed',updated_at_utc=%s,updated_epoch=%s
                        WHERE username=%s AND parent_folder_id IN (SELECT id FROM subtree)
                        """,
                        (folder_id, user, now, updated_epoch, user),
                    )
                    cursor.execute(
                        """
                        WITH RECURSIVE subtree(id) AS (
                            SELECT %s UNION ALL
                            SELECT f.vault_folder_id FROM future_server2.vault_folders f JOIN subtree s ON f.parent_folder_id=s.id
                            WHERE f.username=%s AND f.status='active'
                        )
                        UPDATE future_server2.vault_folders SET status='removed',updated_at_utc=%s,updated_epoch=%s
                        WHERE username=%s AND vault_folder_id IN (SELECT id FROM subtree)
                        """,
                        (folder_id, user, now, updated_epoch, user),
                    )
                    result = {"path": source_path, "name": app.clean(folder_row[2]), "type": "folder", "vault_folder_id": folder_id, "virtual": True}
                else:
                    raise RuntimeError("Only a Vault placement can be removed.")
            result["vault_revision"] = touch_revision(cursor)
            return result

    return app.postgres_execute(_write)

def load_folder_link_cache_rows() -> dict[str, dict]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT link_path,target_path,created_by,created_at_utc,payload_json,revision,status
                FROM future_server2.lesson_folder_links
                WHERE status='active'
                ORDER BY lower(link_path)
                """
            )
            rows = cursor.fetchall()
        loaded = {}
        for row in rows:
            payload = row[4] if isinstance(row[4], dict) else {}
            payload = dict(payload) if isinstance(payload, dict) else {}
            payload.update({
                "kind": app.clean(payload.get("kind")) or app.clean(getattr(app, "SERVER_DATA_LINK_KIND", "future_server_data_link")),
                "version": max(1, app.space_w_int(payload.get("version", 1), 1)),
                "target": app.clean_path_value(row[1]),
                "target_type": "folder",
                "created_by": app.normalize_username(row[2]),
                "created_at": app.clean(row[3]),
                "revision": max(1, app.space_w_int(row[5], 1)),
            })
            loaded[app.clean_path_value(row[0]).lower()] = payload
        return loaded

    return app.postgres_execute(_read)

def upsert_folder_link(link_path: str, payload: dict, now: str = "") -> dict:
    row = {
        "link_path": app.clean_path_value(link_path),
        "target_path": app.clean_path_value((payload or {}).get("target", "")),
        "created_by": app.normalize_username((payload or {}).get("created_by", "")),
        "created_at_utc": app.clean((payload or {}).get("created_at", "")),
        "payload": dict(payload or {}),
        "revision": max(1, app.space_w_int((payload or {}).get("revision", 1), 1)),
        "status": "active",
        "updated_at_utc": app.clean(now) or app.utc_timestamp(),
    }
    return app.postgres_upsert_lesson_folder_link_row(row)

def delete_folder_link(link_path: str) -> dict:
    normalized = app.clean_path_value(link_path)
    if not normalized:
        return {"ok": False, "deleted": 0}

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.lesson_folder_links WHERE link_path=%s", (normalized,))
            return {"ok": True, "deleted": int(cursor.rowcount or 0)}

    return app.postgres_execute(_write)
