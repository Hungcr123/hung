# Loaded by FUTURE.server_parts.server_data_pdf_qmdict.04_server_data_manifest_listing into the shared Future server runtime namespace.
# This is a deeper transitional split; do not import directly yet.

def server_data_manifest_root_entry(folder_name: str, owner: str = "") -> dict:
    name = clean(folder_name)
    manifest = get_server_data_manifest()
    root_entries = manifest.get("folders", {}).get("") if isinstance(manifest.get("folders"), dict) else []
    entry = next((dict(item) for item in root_entries if isinstance(item, dict) and clean(item.get("name", "")).lower() == name.lower()), None)
    if entry:
        if owner:
            entry["owner"] = owner
        return entry
    item = SERVER_DATA_ROOT / name
    try:
        stat = item.stat()
        modified = int(stat.st_mtime)
    except OSError:
        modified = 0
    return {
        "name": name,
        "path": name,
        "type": "folder",
        "size": 0,
        "modified": modified,
        "owner": owner,
    }


def server_data_manifest_folder_entries(relative_path: str = "", manifest: dict | None = None) -> list[dict] | None:
    rel_path = str(relative_path or "").replace("\\", "/").strip("/")
    manifest = manifest if isinstance(manifest, dict) else get_server_data_manifest()
    folders = manifest.get("folders") if isinstance(manifest.get("folders"), dict) else {}
    rows = folders.get(rel_path)
    if not isinstance(rows, list):
        return None
    return [dict(item) for item in rows if isinstance(item, dict)]


# Added 2026-07-21: serve exact file identity from the clean native-watcher manifest without touching disk.
def server_data_manifest_file_entry(relative_path: str = "") -> dict | None:
    rel_path = clean_path_value(relative_path)
    if not rel_path or "/" not in rel_path:
        return None
    with SERVER_DATA_MANIFEST_LOCK:
        if SERVER_DATA_MANIFEST_STATE.get("dirty"):
            return None
        manifest = SERVER_DATA_MANIFEST_STATE.get("manifest")
    if not isinstance(manifest, dict):
        return None
    folders = manifest.get("folders") if isinstance(manifest.get("folders"), dict) else {}
    parent = rel_path.rsplit("/", 1)[0]
    rows = folders.get(parent)
    if not isinstance(rows, list):
        return None
    path_key = rel_path.lower()
    for item in rows:
        if (
            isinstance(item, dict)
            and clean(item.get("type", "")).lower() == "file"
            and clean_path_value(item.get("path", "")).lower() == path_key
        ):
            return dict(item)
    return None


def server_data_tree_compact_base(manifest: dict, trace: dict | None = None) -> dict:
    if trace is not None:
        trace.setdefault("compact_base_start", time.perf_counter())
    folders = manifest.get("folders") if isinstance(manifest.get("folders"), dict) else {}
    if trace is not None:
        trace["manifest_ready"] = time.perf_counter()
    entry_columns = [
        "type", "name", "path", "extension", "size", "modified", "link_target", "linked",
        "file_count", "folder_count", "space_v_file_count", "word_count", "created_at", "created_by",
        "raw_name", "counts_from_manifest_build", "nodes", "questions", "direct_questions", "total_nodes", "paragraphs", "sentences",
          "normal_sentences", "train_sentences", "lesson_id", "content_fingerprint",
          "document_id", "package_path", "package_revision", "package_schema_version", "package_backed", "package_status",
          "virtual", "vault_folder_id", "vault_entry_id", "sort_order", "source_missing",
    ]
    cache_key = (
        server_data_manifest_runtime_revision(manifest),
        int(manifest.get("structural_metadata_version", 0) or 0),
    )
    cache = globals().setdefault("SERVER_DATA_TREE_COMPACT_BASE_CACHE", {})
    cached = cache.get(cache_key) if isinstance(cache, dict) else None
    if isinstance(cached, dict):
        return cached
    if trace is not None:
        trace["cache_miss"] = time.perf_counter()
    rows_by_path = {}
    identity_ready_reader = globals().get("server_database_lesson_identity_registry_ready")
    identity_resolver = globals().get("server_database_lesson_file_id_for_path")
    identity_registry_ready = bool(
        callable(identity_ready_reader)
        and callable(identity_resolver)
        and identity_ready_reader()
    )
    for folder_path, raw_entries in folders.items():
        path_value = clean_path_value(folder_path)
        entries = [dict(entry) for entry in (raw_entries or []) if isinstance(entry, dict)]
        entries.sort(key=lambda entry: (
            entry.get("type") != "folder",
            natural_sort_key(clean(entry.get("name", ""))),
        ))
        compact_entries = []
        for entry in entries:
            if identity_registry_ready and clean(entry.get("lesson_id", "")):
                entry["lesson_id"] = clean(identity_resolver(entry.get("path", "")))[:240]
            values = [entry.get(column, "") for column in entry_columns]
            while values and values[-1] in ("", 0, None, False):
                values.pop()
            compact_entries.append(values)
        rows_by_path[path_value] = {
            "path": path_value,
            "parent": clean_path_value(path_value.rsplit("/", 1)[0]) if "/" in path_value else "",
            "entries": compact_entries,
        }
    if trace is not None:
        trace["rows_by_path_done"] = time.perf_counter()
    rows_by_root = {}
    for path_value in sorted(rows_by_path, key=lambda item: (item.count("/"), item.lower())):
        if not path_value:
            continue
        top = clean(path_value.split("/", 1)[0]).lower()
        rows_by_root.setdefault(top, []).append(rows_by_path[path_value])
    if trace is not None:
        trace["rows_by_root_done"] = time.perf_counter()
    result = {
        "entry_columns": entry_columns,
        "root_row": rows_by_path.get("", {"path": "", "parent": "", "entries": []}),
        "rows_by_root": rows_by_root,
    }
    if trace is not None:
        trace["result_ready"] = time.perf_counter()
    if isinstance(cache, dict):
        cache.clear()
        cache[cache_key] = result
    return result


def server_data_tree_runtime_revision(username: str, admin: bool = False, manifest: dict | None = None) -> str:
    source = manifest if isinstance(manifest, dict) else get_server_data_manifest(force=False)
    viewer = normalize_username(username).lower()
    vault_revision_reader = globals().get("server_database_vault_revision")
    if admin:
        base_revision = server_data_manifest_runtime_revision(source)
        revision_cache = globals().get("SERVER_DATABASE_VAULT_REVISION_CACHE", {})
        if isinstance(revision_cache, dict) and revision_cache:
            digest = hashlib.sha256(json.dumps(sorted(revision_cache.items()), separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
            return f"{base_revision}:v{digest}"
        return base_revision
    folders = source.get("folders") if isinstance(source.get("folders"), dict) else {}
    root_entries = folders.get("") if isinstance(folders.get(""), list) else []
    has_private_root = bool(viewer and any(
        clean_path_value(entry.get("path", "")).split("/", 1)[0].lower() == viewer
        for entry in root_entries
        if isinstance(entry, dict)
    ))
    roots = {"common", viewer} if has_private_root else {"common"}
    base_revision = server_data_manifest_runtime_revision(source, roots)
    vault_revision = int(vault_revision_reader(viewer) or 0) if callable(vault_revision_reader) else 0
    return f"{base_revision}:v{vault_revision}"


# Added 2026-07-27: user overlays need a cheap scoped freshness token. Missing
# private roots are represented as absent instead of cold-scanning the manifest.
def server_data_manifest_user_overlay_revision(manifest: dict | None, roots: object = None) -> str:
    source = manifest if isinstance(manifest, dict) else get_server_data_manifest(force=False)
    if not isinstance(source, dict):
        return ""
    scoped_roots = sorted({clean(root).lower() for root in (roots or []) if clean(root)})
    if not scoped_roots:
        return ""
    server_data_manifest_runtime_revision(source)
    root_revisions = source.get("runtime_root_revisions") if isinstance(source.get("runtime_root_revisions"), dict) else {}
    parts = [f"{root}:{clean(root_revisions.get(root, '')) or 'absent'}" for root in scoped_roots]
    return hashlib.sha1("|".join(parts).encode("utf-8", "ignore")).hexdigest()


def server_data_user_overlay_private_state_summary(username: str = "") -> dict:
    """Added 2026-07-28: prove empty-overlay fast path has no private state."""
    normalized = normalize_username(username)
    empty = {
        "lesson_progress": 0,
        "completed_runs": 0,
        "lesson_time": 0,
        "lesson_task_state": 0,
        "lesson_task_notices": 0,
        "vocabulary_registry": 0,
        "vocabulary_events": 0,
        "vault_folders": 0,
        "vault_entries": 0,
        "vault_hidden_paths": 0,
        "vault_revisions": 0,
    }
    if not normalized:
        return {**empty, "has_private_state": False}
    postgres_mode = globals().get("postgres_backend_mode")
    postgres_execute_fn = globals().get("postgres_execute")
    if callable(postgres_mode) and callable(postgres_execute_fn) and (
        postgres_mode("LESSON_PROGRESS") == "postgres"
        or postgres_mode("LESSON_TIME") == "postgres"
        or postgres_mode("LESSON_TASK") == "postgres"
        or postgres_mode("VOCABULARY") == "postgres"
        or postgres_mode("VAULT_METADATA") == "postgres"
    ):
        def _read(connection):
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                      (SELECT count(*) FROM future_server2.lesson_progress WHERE lower(username)=lower(%s)),
                      (SELECT count(*) FROM future_server2.lesson_progress WHERE lower(username)=lower(%s) AND complete IS TRUE),
                      (SELECT count(*) FROM future_server2.lesson_time WHERE lower(username)=lower(%s)),
                      (SELECT count(*) FROM future_server2.lesson_task_state WHERE lower(username)=lower(%s)),
                      (SELECT count(*) FROM future_server2.lesson_task_notices WHERE lower(username)=lower(%s) AND active IS TRUE),
                      (SELECT count(*) FROM future_server2.vocabulary_registry WHERE lower(username)=lower(%s)),
                      (SELECT count(*) FROM future_server2.vocabulary_events WHERE lower(username)=lower(%s)),
                      (SELECT count(*) FROM future_server2.vault_folders WHERE lower(username)=lower(%s) AND status='active'),
                      (SELECT count(*) FROM future_server2.vault_entries WHERE lower(username)=lower(%s) AND status='active'),
                      (SELECT count(*) FROM future_server2.vault_hidden_paths WHERE lower(username)=lower(%s)),
                      (SELECT count(*) FROM future_server2.vault_revisions WHERE lower(username)=lower(%s))
                    """,
                    (normalized,) * 11,
                )
                row = cursor.fetchone()
            values = [int(value or 0) for value in (row or [])]
            keys = [key for key in empty.keys()]
            summary = dict(zip(keys, values))
            summary["has_private_state"] = any(value > 0 for value in summary.values())
            return summary
        return postgres_execute_fn(_read)
    has_lesson_state_reader = globals().get("server_database_user_has_lesson_state")
    user_generation_reader = globals().get("server_database_user_generation")
    summary = dict(empty)
    summary["lesson_progress"] = 1 if callable(has_lesson_state_reader) and has_lesson_state_reader(normalized) else 0
    summary["lesson_task_state"] = int(user_generation_reader("lesson_tasks", normalized) or 0) if callable(user_generation_reader) else 0
    summary["has_private_state"] = any(value > 0 for value in summary.values())
    return summary


def server_data_user_overlay_context(username: str, admin: bool = False, manifest: dict | None = None) -> dict:
    """Added 2026-07-28: compute overlay roots and revision once per request scope."""
    viewer = normalize_username(username)
    source = manifest if isinstance(manifest, dict) else get_server_data_manifest(force=False)
    if admin:
        registered_users = {
            normalize_username(item).lower()
            for item in list_dashboard_usernames()
            if normalize_username(item)
        }
        overlay_roots = {"admin", viewer.lower(), *registered_users}
    else:
        overlay_roots = {viewer.lower()} if viewer else set()
    overlay_roots = {
        item for item in overlay_roots
        if item and item != "common" and item not in {clean(skip).lower() for skip in server_data_manifest_skip_tops()}
    }
    overlay_manifest_revision = server_data_manifest_user_overlay_revision(source, overlay_roots) if overlay_roots else ""
    vault_revision_reader = globals().get("server_database_vault_revision")
    vault_revision = int(vault_revision_reader(viewer) or 0) if callable(vault_revision_reader) and viewer else 0
    return {
        "viewer": viewer,
        "overlay_roots": overlay_roots,
        "overlay_manifest_revision": overlay_manifest_revision,
        "vault_revision": vault_revision,
        "overlay_revision": f"{overlay_manifest_revision}:v{vault_revision}",
        "structural_version": int(source.get("structural_metadata_version", 0) or 0),
    }


def server_data_tree_merge_vault_rows(rows: list[dict], entry_columns: list[str], username: str) -> list[dict]:
    """Overlay one user's SQLite Vault tree onto the immutable physical tree."""
    if not bool(globals().get("SERVER_DATABASE_VAULT_ENABLED", True)):
        return rows
    user = normalize_username(username)
    if not user:
        return rows
    lock = globals().get("SERVER_DATABASE_VAULT_CACHE_LOCK")
    folder_cache = globals().get("SERVER_DATABASE_VAULT_FOLDER_CACHE", {})
    entry_cache = globals().get("SERVER_DATABASE_VAULT_ENTRY_CACHE", {})
    folder_cache_by_user = globals().get("SERVER_DATABASE_VAULT_FOLDER_CACHE_BY_USER", {})
    entry_cache_by_user = globals().get("SERVER_DATABASE_VAULT_ENTRY_CACHE_BY_USER", {})
    if lock is None or not isinstance(folder_cache, dict) or not isinstance(entry_cache, dict):
        return rows
    with lock:
        user_key = user.lower()
        user_folder_cache = folder_cache_by_user.get(user_key) if isinstance(folder_cache_by_user, dict) else None
        user_entry_cache = entry_cache_by_user.get(user_key) if isinstance(entry_cache_by_user, dict) else None
        if not isinstance(user_folder_cache, dict):
            user_folder_cache = {
                key: item
                for key, item in folder_cache.items()
                if isinstance(item, dict) and normalize_username(item.get("username", "")).lower() == user_key
            }
        if not isinstance(user_entry_cache, dict):
            user_entry_cache = {
                key: item
                for key, item in entry_cache.items()
                if isinstance(item, dict) and normalize_username(item.get("username", "")).lower() == user_key
            }
        folders_by_id = {
            clean(item.get("vault_folder_id", "")): dict(item)
            for item in user_folder_cache.values()
            if clean(item.get("vault_folder_id", ""))
        }
        entries = [dict(item) for item in user_entry_cache.values()]
    if not folders_by_id and not entries:
        return rows
    column_index = {column: index for index, column in enumerate(entry_columns)}

    def _decode(values: list) -> dict:
        return {column: values[index] if index < len(values) else "" for column, index in column_index.items()}

    def _encode(entry: dict) -> list:
        values = [entry.get(column, "") for column in entry_columns]
        while values and values[-1] in ("", 0, None, False):
            values.pop()
        return values

    row_map = {
        clean_path_value(row.get("path", "")): {
            **row,
            "entries": [list(values) for values in (row.get("entries") or [])],
        }
        for row in rows
        if isinstance(row, dict)
    }
    template_by_lesson = {}
    for row in row_map.values():
        for values in row.get("entries") or []:
            decoded = _decode(values)
            lesson_id = clean(decoded.get("lesson_id", ""))
            if lesson_id and clean(decoded.get("type", "")).lower() == "file":
                template_by_lesson.setdefault(lesson_id, decoded)

    def _ensure_row(path_value: str) -> dict:
        path = clean_path_value(path_value)
        row = row_map.get(path)
        if row is None:
            row = {
                "path": path,
                "parent": clean_path_value(path.rsplit("/", 1)[0]) if "/" in path else "",
                "entries": [],
            }
            row_map[path] = row
        return row

    def _merge_entry(parent_path: str, entry: dict) -> None:
        parent = _ensure_row(parent_path)
        path = clean_path_value(entry.get("path", ""))
        path_index = column_index.get("path", -1)
        for index, values in enumerate(parent["entries"]):
            existing_path = clean_path_value(values[path_index] if path_index >= 0 and len(values) > path_index else "")
            if existing_path.lower() != path.lower():
                continue
            decoded = _decode(values)
            decoded.update({key: value for key, value in entry.items() if value not in ("", None) or key in {"linked", "virtual"}})
            parent["entries"][index] = _encode(decoded)
            return
        parent["entries"].append(_encode(entry))

    for folder in folders_by_id.values():
        folder_type = clean(folder.get("folder_type", "")).upper()
        folder_path = clean_path_value(folder.get("path", ""))
        if not folder_path or folder_type == "ROOT":
            continue
        _ensure_row(folder_path)
        if folder_type == "PHYSICAL_CONTAINER" and folder_path in row_map:
            continue
        parent_path = clean_path_value(folder_path.rsplit("/", 1)[0]) if "/" in folder_path else ""
        _merge_entry(parent_path, {
            "type": "folder",
            "name": clean(folder.get("display_name", "")),
            "path": folder_path,
            "virtual": True,
            "vault_folder_id": clean(folder.get("vault_folder_id", "")),
            "sort_order": int(folder.get("sort_order", 0) or 0),
            "created_by": user,
        })
    for item in entries:
        lesson_id = clean(item.get("lesson_id", ""))
        entry = dict(template_by_lesson.get(lesson_id, {}))
        entry.update({
            "type": "file",
            "name": clean(item.get("display_name", "")),
            "path": clean_path_value(item.get("path", "")),
            "lesson_id": lesson_id,
            "virtual": True,
            "linked": False,
            "vault_entry_id": clean(item.get("vault_entry_id", "")),
            "sort_order": int(item.get("sort_order", 0) or 0),
            "created_by": user,
        })
        if not clean(entry.get("extension", "")):
            entry["extension"] = Path(clean_path_value(item.get("source_path", ""))).suffix
        parent = folders_by_id.get(clean(item.get("parent_folder_id", "")), {})
        parent_path = clean_path_value(parent.get("path", ""))
        if parent_path and entry["path"]:
            _merge_entry(parent_path, entry)
    type_index = column_index.get("type", -1)
    name_index = column_index.get("name", -1)
    sort_index = column_index.get("sort_order", -1)
    for row in row_map.values():
        row["entries"].sort(key=lambda values: (
            clean(values[type_index] if type_index >= 0 and len(values) > type_index else "") != "folder",
            0 if sort_index >= 0 and len(values) > sort_index and int(values[sort_index] or 0) > 0 else 1,
            int(values[sort_index] or 0) if sort_index >= 0 and len(values) > sort_index else 0,
            natural_sort_key(clean(values[name_index] if name_index >= 0 and len(values) > name_index else "")),
        ))
    return sorted(row_map.values(), key=lambda row: (clean_path_value(row.get("path", "")).count("/"), clean_path_value(row.get("path", "")).lower()))


def build_server_data_common_tree_snapshot(manifest: dict | None = None, trace: dict | None = None) -> dict:
    """Added 2026-07-27: return the user-independent Lesson Vault common tree."""
    source = manifest if isinstance(manifest, dict) else get_server_data_manifest(force=False)
    if trace is not None:
        trace.setdefault("snapshot_start", time.perf_counter())
    compact_base = server_data_tree_compact_base(source, trace=trace)
    if trace is not None:
        trace["compact_base_done"] = time.perf_counter()
    entry_columns = compact_base.get("entry_columns") or []
    root_row = compact_base.get("root_row") if isinstance(compact_base.get("root_row"), dict) else {"path": "", "parent": "", "entries": []}
    rows_by_root = compact_base.get("rows_by_root") if isinstance(compact_base.get("rows_by_root"), dict) else {}
    type_index = entry_columns.index("type")
    path_index = entry_columns.index("path")
    compact_root_entries = []
    for values in root_row.get("entries") or []:
        entry_type = clean(values[type_index] if len(values) > type_index else "")
        entry_path = clean_path_value(values[path_index] if len(values) > path_index else "")
        if entry_type == "folder" and entry_path.split("/", 1)[0].lower() == "common":
            compact_root_entries.append(list(values))
    rows = [{**root_row, "entries": compact_root_entries}]
    rows.extend({**row, "entries": [list(values) for values in (row.get("entries") or [])]} for row in (rows_by_root.get("common") or []))
    if trace is not None:
        trace["rows_compacted"] = time.perf_counter()
    common_revision = server_data_manifest_runtime_revision(source, {"common"})
    payload = {
        "ok": True,
        "schema_version": "tree-common-v1",
        "format_version": "compact-v1",
        "frontend_compatibility_version": "login-vault-v1",
        "generated_at": utc_timestamp(),
        "common_revision": common_revision,
        "common_manifest_signature": common_revision,
        "manifest_integrity_signature": clean(source.get("signature", "")),
        "manifest_updated_at": clean(source.get("updated_at", "")),
        "format": "compact-v1",
        "entry_columns": entry_columns,
        "rows": rows,
        "row_count": len(rows),
    }
    if trace is not None:
        trace["payload_ready"] = time.perf_counter()
    return payload

def build_server_data_user_tree_overlay(
    username: str,
    admin: bool = False,
    manifest: dict | None = None,
    overlay_context: dict | None = None,
) -> dict:
    """Added 2026-07-27: return only user/private Lesson Vault rows for overlay composition."""
    context = overlay_context if isinstance(overlay_context, dict) else server_data_user_overlay_context(username, admin=admin, manifest=manifest)
    viewer = clean(context.get("viewer", "")) or normalize_username(username)
    source = manifest if isinstance(manifest, dict) else get_server_data_manifest(force=False)
    compact_base = server_data_tree_compact_base(source)
    entry_columns = compact_base.get("entry_columns") or []
    root_row = compact_base.get("root_row") if isinstance(compact_base.get("root_row"), dict) else {"path": "", "parent": "", "entries": []}
    rows_by_root = compact_base.get("rows_by_root") if isinstance(compact_base.get("rows_by_root"), dict) else {}
    overlay_roots = context.get("overlay_roots") if isinstance(context.get("overlay_roots"), set) else set()
    type_index = entry_columns.index("type")
    path_index = entry_columns.index("path")
    overlay_revision = clean(context.get("overlay_revision", ""))
    vault_revision = int(context.get("vault_revision", 0) or 0)
    viewer_key = viewer.lower()
    compact_root_entries = []
    for values in root_row.get("entries") or []:
        entry_type = clean(values[type_index] if len(values) > type_index else "")
        entry_path = clean_path_value(values[path_index] if len(values) > path_index else "")
        entry_top = clean(entry_path.split("/", 1)[0]).lower()
        if entry_type == "folder" and entry_top in overlay_roots:
            compact_root_entries.append(list(values))
    private_manifest_rows = rows_by_root.get(viewer_key) or []
    has_private_manifest_rows = any(
        bool(row.get("entries"))
        for row in private_manifest_rows
        if isinstance(row, dict)
    )
    empty_candidate = (
        not admin
        and viewer_key
        and viewer_key in overlay_roots
        and not has_private_manifest_rows
        and vault_revision == 0
    )
    private_state_summary = server_data_user_overlay_private_state_summary(viewer) if empty_candidate else {}
    if (
        empty_candidate
        and not bool(private_state_summary.get("has_private_state"))
    ):
        return {
            "ok": True,
            "schema_version": "tree-overlay-v1",
            "format_version": "compact-v1",
            "frontend_compatibility_version": "login-vault-v1",
            "username": viewer,
            "admin": False,
            "user_id": viewer_key,
            "domain_revisions": {"vault": 0, "manifest_overlay": overlay_revision},
            "overlay_revision": f"{overlay_revision}:v0",
            "overlay_manifest_signature": overlay_revision,
            "manifest_integrity_signature": clean(source.get("signature", "")),
            "manifest_updated_at": clean(source.get("updated_at", "")),
            "format": "compact-v1",
            "entry_columns": entry_columns,
            "rows": [{**root_row, "entries": []}],
            "row_count": 1,
            "changed_rows": [{**root_row, "entries": []}],
            "deleted_rows": [],
            "empty_overlay_fast_path": True,
            "empty_overlay_reason": "no_private_root_no_vault_no_lesson_state_no_lesson_tasks",
            "empty_overlay_private_state": private_state_summary,
        }
    rows = [{**root_row, "entries": compact_root_entries, **({"task_owner": viewer} if admin else {})}]
    for root in sorted(overlay_roots, key=lambda value: natural_sort_key(value)):
        root_rows = rows_by_root.get(root) or []
        if admin:
            rows.extend({**row, "entries": [list(values) for values in (row.get("entries") or [])], "task_owner": normalize_username(clean_path_value(row.get("path", "")).split("/", 1)[0]) or viewer} for row in root_rows)
        else:
            rows.extend({**row, "entries": [list(values) for values in (row.get("entries") or [])]} for row in root_rows)
    vault_users = sorted({viewer, *(normalize_username(item) for item in overlay_roots)}) if admin else [viewer]
    for vault_user in vault_users:
        if vault_user:
            rows = server_data_tree_merge_vault_rows(rows, entry_columns, vault_user)
    return {
        "ok": True,
        "schema_version": "tree-overlay-v1",
        "format_version": "compact-v1",
        "frontend_compatibility_version": "login-vault-v1",
        "username": viewer,
        "admin": bool(admin),
        "user_id": viewer.lower(),
        "domain_revisions": {"vault": vault_revision, "manifest_overlay": overlay_revision},
        "overlay_revision": f"{overlay_revision}:v{vault_revision}",
        "overlay_manifest_signature": overlay_revision,
        "manifest_integrity_signature": clean(source.get("signature", "")),
        "manifest_updated_at": clean(source.get("updated_at", "")),
        "format": "compact-v1",
        "entry_columns": entry_columns,
        "rows": rows,
        "row_count": len(rows),
        "changed_rows": rows,
        "deleted_rows": [],
    }

def warm_server_data_user_overlay_cache(manifest: dict | None = None) -> dict:
    source = manifest if isinstance(manifest, dict) else get_server_data_manifest(force=False)
    started_cpu = time.process_time()
    started_wall = time.perf_counter()
    usernames = select_startup_warmup_usernames(purpose="user-overlay")
    warmed = {}
    for username in usernames:
        admin_view = bool(is_admin_user(username))
        overlay_context = server_data_user_overlay_context(username, admin=admin_view, manifest=source)
        overlay_revision = clean(overlay_context.get("overlay_revision", ""))
        cache_key = (
            username.lower(),
            "admin" if admin_view else "user",
            f"{overlay_revision}:sm{int(source.get('structural_metadata_version', 0) or 0)}",
        )
        if cache_key in warmed:
            continue
        payload = build_server_data_user_tree_overlay(username, admin=admin_view, manifest=source, overlay_context=overlay_context)
        identity_data = json_bytes(payload)
        warmed[cache_key] = {
            "identity": identity_data,
            "gzip": gzip.compress(identity_data, compresslevel=1, mtime=0),
            "decoded_bytes": len(identity_data),
        }
    with SERVER_DATA_LIST_CACHE_LOCK:
        cache = globals().setdefault("SERVER_DATA_USER_OVERLAY_BYTES_CACHE", {})
        if isinstance(cache, dict):
            cache.update(warmed)
            if len(cache) > SERVER_DATA_TREE_PRELOAD_CACHE_MAX_ITEMS:
                stale = sorted(cache.items(), key=lambda item: len(bytes(item[1].get("gzip") or b"")))
                for old_key, _old_row in stale[: max(1, len(cache) - SERVER_DATA_TREE_PRELOAD_CACHE_MAX_ITEMS)]:
                    if old_key not in warmed:
                        cache.pop(old_key, None)
    return {
        "users": len(warmed),
        "common_cpu_ms": round((time.process_time() - started_cpu) * 1000, 1),
        "common_wall_ms": round((time.perf_counter() - started_wall) * 1000, 1),
        "gzip_bytes": sum(len(row.get("gzip") or b"") for row in warmed.values()),
        "structural_metadata_version": int(source.get("structural_metadata_version", 0) or 0),
        **startup_warmup_selection_summary(usernames),
    }

def build_server_data_tree_snapshot(username: str, admin: bool = False) -> dict:
    """Return a compact authenticated Lesson Vault tree without user progress."""
    viewer = normalize_username(username)
    manifest = get_server_data_manifest(force=False)
    common = build_server_data_common_tree_snapshot(manifest)
    overlay_context = server_data_user_overlay_context(viewer, admin=admin, manifest=manifest)
    overlay = build_server_data_user_tree_overlay(viewer, admin=admin, manifest=manifest, overlay_context=overlay_context)
    entry_columns = common.get("entry_columns") or overlay.get("entry_columns") or []
    rows = [*(common.get("rows") or []), *(overlay.get("rows") or [])]
    return {
        "ok": True,
        "username": viewer,
        "admin": bool(admin),
        "common_manifest_signature": common.get("common_manifest_signature", ""),
        "overlay_manifest_signature": overlay.get("overlay_manifest_signature", ""),
        "manifest_signature": server_data_tree_runtime_revision(viewer, admin, manifest),
        "manifest_integrity_signature": clean(manifest.get("signature", "")),
        "manifest_updated_at": clean(manifest.get("updated_at", "")),
        "format": "compact-v1",
        "common": common,
        "userOverlay": overlay,
        "entry_columns": entry_columns,
        "rows": rows,
        "row_count": len(rows),
    }


# Added 2026-07-20: common-only learners share one immutable tree payload instead of rebuilding identical gzip bytes per account.
def server_data_tree_snapshot_identity(username: str, admin: bool = False, manifest: dict | None = None) -> tuple[str, str]:
    viewer = normalize_username(username)
    if admin or not viewer:
        return viewer, viewer.lower()
    source = manifest if isinstance(manifest, dict) else get_server_data_manifest(force=False)
    compact_base = server_data_tree_compact_base(source)
    viewer_key = viewer.lower()
    rows_by_root = compact_base.get("rows_by_root") if isinstance(compact_base.get("rows_by_root"), dict) else {}
    private_rows = rows_by_root.get(viewer_key) or []
    # Updated 2026-07-20: even an empty registered root is visible UI state and cannot use a common-only payload.
    has_private_rows = any(isinstance(row, dict) for row in private_rows)
    if not has_private_rows:
        vault_children_reader = globals().get("server_database_vault_children")
        root_id_reader = globals().get("_server_database_vault_root_id")
        if callable(vault_children_reader) and callable(root_id_reader):
            has_private_rows = bool(vault_children_reader(root_id_reader(viewer), viewer))
    return (viewer, viewer_key) if has_private_rows else ("", "__shared_common_only__")


def warm_server_data_common_tree_cache(manifest: dict | None = None) -> dict:
    source = manifest if isinstance(manifest, dict) else get_server_data_manifest(force=False)
    started_cpu = time.process_time()
    started_wall = time.perf_counter()
    structural_version = int(source.get("structural_metadata_version", 0) or 0)
    common_revision = server_data_manifest_runtime_revision(source, {"common"})
    tree_cache_key = ("__shared_common_tree__", "common", f"{common_revision}:sm{structural_version}")
    payload = build_server_data_common_tree_snapshot(source)
    identity_data = json_bytes(payload)
    cached_tree = {
        "identity": b"",
        "gzip": gzip.compress(identity_data, compresslevel=1, mtime=0),
        "decoded_bytes": len(identity_data),
    }
    with SERVER_DATA_LIST_CACHE_LOCK:
        cache = globals().setdefault("SERVER_DATA_COMMON_TREE_PRELOAD_BYTES_CACHE", {})
        if isinstance(cache, dict):
            cache[tree_cache_key] = cached_tree
    return {
        "common_builds": 1,
        "common_revision": common_revision,
        "common_gzip_bytes": len(cached_tree.get("gzip") or b""),
        "common_decoded_bytes": len(identity_data),
        "cpu_ms": round((time.process_time() - started_cpu) * 1000, 1),
        "wall_ms": round((time.perf_counter() - started_wall) * 1000, 1),
    }

def warm_server_data_tree_preload_cache(manifest: dict | None = None) -> dict:
    source = manifest if isinstance(manifest, dict) else get_server_data_manifest(force=False)
    started_cpu = time.process_time()
    started_wall = time.perf_counter()
    server_data_tree_compact_base(source)
    common_warm = warm_server_data_common_tree_cache(source)
    structural_version = int(source.get("structural_metadata_version", 0) or 0)
    usernames = select_startup_warmup_usernames(purpose="tree-preload")
    if future_warmup_mode() != "benchmark":
        usernames = []
    warmed = {}
    for username in usernames:
        admin_view = bool(is_admin_user(username))
        snapshot_username, cache_identity = server_data_tree_snapshot_identity(username, admin_view, source)
        role = "admin" if admin_view else "user"
        manifest_signature = server_data_tree_runtime_revision(username, admin_view, source)
        revision = f"{manifest_signature}:sm{structural_version}"
        key = (cache_identity, role, revision)
        if key in warmed:
            continue
        payload = build_server_data_tree_snapshot(snapshot_username, admin=admin_view)
        identity_data = json_bytes(payload)
        warmed[key] = {
            "identity": b"",
            "gzip": gzip.compress(identity_data, compresslevel=1, mtime=0),
        }
    with SERVER_DATA_LIST_CACHE_LOCK:
        cache = globals().setdefault("SERVER_DATA_TREE_PRELOAD_BYTES_CACHE", {})
        if isinstance(cache, dict):
            cache.clear()
            cache.update(warmed)
    return {
        "users": len(warmed),
        "cpu_ms": round((time.process_time() - started_cpu) * 1000, 1),
        "wall_ms": round((time.perf_counter() - started_wall) * 1000, 1),
        "gzip_bytes": sum(len(row.get("gzip") or b"") for row in warmed.values()),
        "structural_metadata_version": structural_version,
        "tree_preload_per_user": future_warmup_mode() == "benchmark",
        **common_warm,
        **startup_warmup_selection_summary(usernames),
    }


def server_data_manifest_entry_word_count(entry: dict | None) -> int:
    if not isinstance(entry, dict):
        return 0
    for key in ("word_count", "words", "nodes", "node_count"):
        try:
            value = int(entry.get(key, 0) or 0)
            if value > 0:
                return value
        except Exception:
            pass
    name = clean(entry.get("name", ""))
    matches = re.findall(r"\{(\d{1,6})\}", name)
    if matches:
        try:
            return max(0, int(matches[-1]))
        except Exception:
            return 0
    return 0


def server_data_manifest_entry_label_counts(entry: dict | None) -> dict:
    counts = {"file_count": 0, "space_v_file_count": 0, "word_count": 0}
    if not isinstance(entry, dict):
        return counts
    name = clean(entry.get("name", ""))
    file_match = re.search(r"\[(\d{1,6})\s+files?\]", name, flags=re.IGNORECASE)
    word_match = re.search(r"\{(\d{1,7})\s+words?\}", name, flags=re.IGNORECASE)
    if file_match:
        try:
            counts["file_count"] = max(0, int(file_match.group(1)))
        except Exception:
            counts["file_count"] = 0
    if word_match:
        try:
            counts["word_count"] = max(0, int(word_match.group(1)))
        except Exception:
            counts["word_count"] = 0
    if counts["file_count"] and counts["word_count"]:
        counts["space_v_file_count"] = counts["file_count"]
    return counts


def server_data_manifest_folder_counts(relative_path: str = "", manifest: dict | None = None) -> dict:
    """Count linked-folder children from the manifest only.

    Lesson Vault requests must not walk a linked target folder on demand. Large
    common/user folders can contain hundreds of files, and counting them while
    an admin switches learners makes the vault feel frozen.
    """
    counts = {
        "file_count": 0,
        "space_v_file_count": 0,
        "word_count": 0,
    }
    rel_path = clean_path_value(relative_path)
    source_manifest = manifest if isinstance(manifest, dict) else get_server_data_manifest()
    folders = source_manifest.get("folders") if isinstance(source_manifest.get("folders"), dict) else {}
    if not isinstance(folders, dict):
        return counts
    seen: set[str] = set()
    stack = [rel_path]
    while stack:
        current = clean_path_value(stack.pop())
        if current.lower() in seen:
            continue
        seen.add(current.lower())
        rows = folders.get(current)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            row_type = clean(row.get("type", ""))
            if row_type == "folder":
                label_counts = server_data_manifest_entry_label_counts(row)
                if label_counts.get("file_count") or label_counts.get("word_count"):
                    counts["file_count"] += int(label_counts.get("file_count", 0) or 0)
                    counts["space_v_file_count"] += int(label_counts.get("space_v_file_count", 0) or 0)
                    counts["word_count"] += int(label_counts.get("word_count", 0) or 0)
                    continue
                child_path = clean_path_value(row.get("effective_path") or row.get("link_target") or row.get("path", ""))
                if child_path and child_path.lower() not in seen:
                    stack.append(child_path)
                continue
            extension = clean(row.get("extension", "")).lower()
            if extension not in LESSON_FILE_SUFFIXES:
                continue
            counts["file_count"] += 1
            if extension in {".space_v", ".space_b"}:
                counts["space_v_file_count"] += 1
                counts["word_count"] += server_data_manifest_entry_word_count(row)
    return counts


def server_data_list_cache_progress_signature(username: str = "") -> tuple:
    username = normalize_username(username)
    if not username:
        return ()
    signatures = []
    # Updated 2026-07-06: Space_W/Q/V/P progress saves patch touched Lesson Vault
    # rows directly. Keeping whole progress files in this signature made every
    # small save expire all folder caches for the user.
    try:
        signatures.append(("pdf", file_cache_signature(space_pdf_progress_path(username))))
    except Exception:
        signatures.append(("pdf", (0, -1)))
    try:
        signatures.append(("time", lesson_time_runtime_signature(username)))
    except Exception:
        signatures.append(("time", (0, -1)))
    try:
        signatures.append(("summary", file_cache_signature(learning_summary_path(username))))
    except Exception:
        signatures.append(("summary", (0, -1)))
    return tuple(signatures)


def server_data_directory_listing_signature(folder: Path | None) -> str:
    if folder is None:
        return ""
    try:
        target = Path(folder)
        if not target.is_dir():
            return ""
        stat = target.stat()
        resolved = str(target.resolve()).lower()
    except Exception:
        return ""
    signature = (
        resolved,
        int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))),
        int(getattr(stat, "st_ctime_ns", int(stat.st_ctime * 1_000_000_000))),
        int(getattr(stat, "st_size", 0) or 0),
    )
    cache = getattr(server_data_directory_listing_signature, "_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        setattr(server_data_directory_listing_signature, "_cache", cache)
    cached = cache.get(resolved)
    if isinstance(cached, dict) and cached.get("signature") == signature:
        value = clean(cached.get("value", ""))
        if value:
            return value
    digest = hashlib.sha1()
    for part in signature:
        digest.update(str(part).encode("utf-8", "ignore"))
        digest.update(b"|")
    value = digest.hexdigest()
    cache[resolved] = {
        "signature": signature,
        "value": value,
        "at": time.time(),
    }
    if len(cache) > 512:
        ordered = sorted(cache.items(), key=lambda item: float(item[1].get("at", 0) or 0))
        for old_key, _old_value in ordered[:128]:
            cache.pop(old_key, None)
    return value


def server_data_list_cache_signature(
    manifest: dict,
    study_user: str = "",
    task_owner: str = "",
    stats_user: str = "",
    viewer_user: str = "",
    folder_signature: str = "",
    lightweight: bool = False,
    include_task_board: bool = True,
) -> tuple:
    normalized = {normalize_username(value) for value in (study_user, task_owner, stats_user, viewer_user) if normalize_username(value)}
    manifest_revision = server_data_manifest_runtime_revision(manifest) if any(is_admin_user(user) for user in normalized) else server_data_manifest_runtime_revision(
        manifest,
        {"common", *(user.lower() for user in normalized)},
    )
    vault_revision_reader = globals().get("server_database_vault_revision")
    vault_revisions = tuple(
        (user, int(vault_revision_reader(user) or 0))
        for user in sorted(normalized)
    ) if callable(vault_revision_reader) else ()
    if lightweight:
        return (
            "lightweight",
            manifest_revision,
            clean(folder_signature),
            vault_revisions,
        )
    user_signatures = tuple((user, server_data_list_cache_progress_signature(user)) for user in sorted(normalized))
    task_users = tuple(sorted(normalized))
    task_signature = (
        tuple(
            (user, lesson_tasks_runtime_signature(user), lesson_task_notices_runtime_signature(user))
            for user in task_users
        ),
    ) if include_task_board else ("task-board-deferred",)
    return (
        manifest_revision,
        clean(folder_signature),
        task_signature,
        user_signatures,
        vault_revisions,
    )


def get_cached_server_data_list(cache_key: str, signature: tuple) -> dict | None:
    now = time.time()
    with SERVER_DATA_LIST_CACHE_LOCK:
        row = SERVER_DATA_LIST_CACHE.get(cache_key)
        if not isinstance(row, dict):
            return None
        if row.get("signature") != signature or now - float(row.get("at", 0) or 0) > SERVER_DATA_LIST_CACHE_TTL_SECONDS:
            SERVER_DATA_LIST_CACHE.pop(cache_key, None)
            return None
        payload = row.get("payload")
        if isinstance(payload, dict):
            result = dict(payload)
            response_bytes = row.get("bytes")
            if isinstance(response_bytes, bytes):
                result["_response_bytes"] = response_bytes
                result["_response_etag"] = clean(row.get("etag", ""))
                result["_response_cache_hit"] = True
            return result
    return None


# Added 2026-07-30: keep serialized bytes/ETag aligned when a compact progress delta patches a cached row.
def refresh_server_data_list_cache_row_bytes(row: dict) -> None:
    payload = row.get("payload") if isinstance(row, dict) else None
    if not isinstance(payload, dict):
        return
    response_payload = dict(payload)
    response_payload.pop("_server_timing", None)
    response_payload.pop("_response_bytes", None)
    response_payload.pop("_response_etag", None)
    response_bytes = json_bytes(response_payload)
    row["bytes"] = response_bytes
    row["etag"] = f'"server-data-list-{hashlib.sha1(response_bytes).hexdigest()}"'


def remember_server_data_list(cache_key: str, signature: tuple, payload: dict) -> dict:
    if not cache_key or not isinstance(payload, dict):
        return payload
    space_task = payload.get("space_task") if isinstance(payload.get("space_task"), dict) else {}
    if space_task.get("pending"):
        return payload
    cache_row = {
        "signature": signature,
        "payload": payload,
        "at": time.time(),
    }
    refresh_server_data_list_cache_row_bytes(cache_row)
    response_bytes = cache_row.get("bytes", b"")
    response_etag = clean(cache_row.get("etag", ""))
    with SERVER_DATA_LIST_CACHE_LOCK:
        SERVER_DATA_LIST_CACHE[cache_key] = cache_row
        if len(SERVER_DATA_LIST_CACHE) > 180:
            ordered = sorted(SERVER_DATA_LIST_CACHE.items(), key=lambda item: float(item[1].get("at", 0) or 0))
            for old_key, _old_value in ordered[:40]:
                SERVER_DATA_LIST_CACHE.pop(old_key, None)
    result = dict(payload)
    result["_response_bytes"] = response_bytes
    result["_response_etag"] = response_etag
    result["_response_cache_hit"] = False
    return result


def server_data_file_cache_key(path: Path) -> str:
    try:
        return str(path.resolve()).lower()
    except Exception:
        return str(path.absolute()).lower()


def prune_server_data_file_cache_locked() -> None:
    total = 0
    for row in SERVER_DATA_FILE_CACHE.values():
        if isinstance(row, dict):
            total += int(row.get("size", 0) or 0)
    if total <= SERVER_DATA_FILE_CACHE_MAX_BYTES and len(SERVER_DATA_FILE_CACHE) <= SERVER_DATA_FILE_CACHE_MAX_ITEMS:
        return
    ordered = sorted(SERVER_DATA_FILE_CACHE.items(), key=lambda item: float(item[1].get("at", 0) or 0))
    for old_key, row in ordered:
        if total <= SERVER_DATA_FILE_CACHE_MAX_BYTES and len(SERVER_DATA_FILE_CACHE) <= SERVER_DATA_FILE_CACHE_MAX_ITEMS:
            break
        SERVER_DATA_FILE_CACHE.pop(old_key, None)
        if isinstance(row, dict):
            total -= int(row.get("size", 0) or 0)


SPACE_V_QMDICT_PAYLOAD_CACHE: dict[str, dict] = {}
SPACE_V_QMDICT_PAYLOAD_CACHE_LOCK = threading.RLock()
SPACE_V_QMDICT_PAYLOAD_CACHE_MAX_ITEMS = 64
SPACE_V_QMDICT_SINGLEFLIGHT_LOCK = threading.RLock()
SPACE_V_QMDICT_SINGLEFLIGHT: dict[str, dict] = {}
SPACE_V_QMDICT_SINGLEFLIGHT_MAX_ITEMS = 256


def prune_space_v_qmdict_payload_cache_locked() -> None:
    if len(SPACE_V_QMDICT_PAYLOAD_CACHE) <= SPACE_V_QMDICT_PAYLOAD_CACHE_MAX_ITEMS:
        return
    ordered = sorted(SPACE_V_QMDICT_PAYLOAD_CACHE.items(), key=lambda item: float(item[1].get("at", 0) or 0))
    for old_key, _row in ordered[: max(1, len(ordered) - SPACE_V_QMDICT_PAYLOAD_CACHE_MAX_ITEMS)]:
        SPACE_V_QMDICT_PAYLOAD_CACHE.pop(old_key, None)


# Added 2026-07-21: serialize one hydrate per file revision without blocking unrelated Space_V files.
def space_v_qmdict_singleflight_lock(cache_key: str) -> threading.Lock:
    now = time.time()
    with SPACE_V_QMDICT_SINGLEFLIGHT_LOCK:
        row = SPACE_V_QMDICT_SINGLEFLIGHT.get(cache_key)
        if not isinstance(row, dict) or not isinstance(row.get("lock"), type(threading.Lock())):
            row = {"lock": threading.Lock(), "at": now}
            SPACE_V_QMDICT_SINGLEFLIGHT[cache_key] = row
        else:
            row["at"] = now
        if len(SPACE_V_QMDICT_SINGLEFLIGHT) > SPACE_V_QMDICT_SINGLEFLIGHT_MAX_ITEMS:
            ordered = sorted(SPACE_V_QMDICT_SINGLEFLIGHT.items(), key=lambda item: float(item[1].get("at", 0) or 0))
            for old_key, old_row in ordered:
                if len(SPACE_V_QMDICT_SINGLEFLIGHT) <= SPACE_V_QMDICT_SINGLEFLIGHT_MAX_ITEMS:
                    break
                old_lock = old_row.get("lock") if isinstance(old_row, dict) else None
                if old_key != cache_key and isinstance(old_lock, type(threading.Lock())) and not old_lock.locked():
                    SPACE_V_QMDICT_SINGLEFLIGHT.pop(old_key, None)
        return row["lock"]


def cached_space_v_qmdict_file_bytes(target: Path) -> tuple[bytes, dict]:
    # Added 2026-07-06: lets many learners open the same Space_V without re-hydrating QmDict each time.
    target = Path(target)
    signature = file_cache_signature(target)
    qmdict_sig = qmdict_source_signature()
    qmdict_key = (int(qmdict_sig.get("mtime_ns", 0) or 0), int(qmdict_sig.get("size", -1) or -1))
    cache_key = f"{server_data_file_cache_key(target)}|space-v-qmdict|{signature[0]}:{signature[1]}|{qmdict_key[0]}:{qmdict_key[1]}"
    now = time.time()
    with SPACE_V_QMDICT_PAYLOAD_CACHE_LOCK:
        row = SPACE_V_QMDICT_PAYLOAD_CACHE.get(cache_key)
        if isinstance(row, dict) and row.get("signature") == signature and isinstance(row.get("data"), bytes):
            row["at"] = now
            return row["data"], {**dict(row.get("meta") if isinstance(row.get("meta"), dict) else {}), "cache_hit": True, "lock_wait_ms": 0.0, "compute_ms": 0.0}
    key_lock = space_v_qmdict_singleflight_lock(cache_key)
    wait_started = time.perf_counter()
    with key_lock:
        lock_wait_ms = (time.perf_counter() - wait_started) * 1000
        with SPACE_V_QMDICT_PAYLOAD_CACHE_LOCK:
            row = SPACE_V_QMDICT_PAYLOAD_CACHE.get(cache_key)
            if isinstance(row, dict) and row.get("signature") == signature and isinstance(row.get("data"), bytes):
                row["at"] = time.time()
                return row["data"], {**dict(row.get("meta") if isinstance(row.get("meta"), dict) else {}), "cache_hit": True, "lock_wait_ms": round(lock_wait_ms, 3), "compute_ms": 0.0}
        compute_started = time.perf_counter()
        payload, _structure_path = load_future_lesson_document(target)
        hydrated_payload, hydrate_meta = hydrate_space_v_payload_with_qmdict(payload)
        data = html_bytes(encode_future_payload_code(hydrated_payload))
        compute_ms = (time.perf_counter() - compute_started) * 1000
        meta = {
            "qmdict_mtime_ns": qmdict_key[0],
            "qmdict_size": qmdict_key[1],
            "hydrated": int(hydrate_meta.get("hydrated", 0) or 0),
            "removed": int(hydrate_meta.get("removed", 0) or 0),
            "cache_hit": False,
            "lock_wait_ms": round(lock_wait_ms, 3),
            "compute_ms": round(compute_ms, 3),
        }
        with SPACE_V_QMDICT_PAYLOAD_CACHE_LOCK:
            SPACE_V_QMDICT_PAYLOAD_CACHE[cache_key] = {"signature": signature, "data": data, "meta": meta, "at": time.time()}
            prune_space_v_qmdict_payload_cache_locked()
    return data, meta


def cached_server_data_file_bytes(target: Path) -> bytes:
    signature = file_cache_signature(target)
    cache_key = server_data_file_cache_key(target)
    now = time.time()
    with SERVER_DATA_FILE_CACHE_LOCK:
        row = SERVER_DATA_FILE_CACHE.get(cache_key)
        if isinstance(row, dict) and row.get("signature") == signature and isinstance(row.get("data"), bytes):
            row["at"] = now
            return row["data"]
        if row is not None:
            SERVER_DATA_FILE_CACHE.pop(cache_key, None)
    started = time.perf_counter()
    data = target.read_bytes()
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    if elapsed_ms >= 250:
        stt_debug_log("server_data_file_disk_read_slow", path=server_data_relative(target), size=len(data), ms=elapsed_ms)
    if len(data) > SERVER_DATA_FILE_CACHE_MAX_FILE_BYTES:
        return data
    with SERVER_DATA_FILE_CACHE_LOCK:
        SERVER_DATA_FILE_CACHE[cache_key] = {
            "signature": signature,
            "data": data,
            "size": len(data),
            "at": now,
        }
        prune_server_data_file_cache_locked()
    return data
