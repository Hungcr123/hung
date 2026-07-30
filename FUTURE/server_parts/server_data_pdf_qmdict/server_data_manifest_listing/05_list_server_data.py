# Loaded by FUTURE.server_parts.server_data_pdf_qmdict.04_server_data_manifest_listing into the shared Future server runtime namespace.
# This is a deeper transitional split; do not import directly yet.


# Added 2026-07-21: a stale remembered folder falls back to its nearest existing parent instead of breaking Lesson Vault.
def resolve_server_data_list_folder(relative_path: str, username: str, admin: bool = False) -> tuple[str, Path | None, Path | None, str]:
    requested = clean_path_value(relative_path)
    candidate = requested
    while candidate:
        target = safe_server_data_path(candidate, username, admin=admin)
        vault_matcher = globals().get("server_database_vault_match")
        virtual_folder = vault_matcher(candidate) if bool(globals().get("SERVER_DATABASE_VAULT_ENABLED", True)) and callable(vault_matcher) else {}
        if (
            isinstance(virtual_folder, dict)
            and clean(virtual_folder.get("vault_folder_id", ""))
            and not clean_path_value(virtual_folder.get("suffix", ""))
            and clean_path_value(virtual_folder.get("path", "")).lower() == candidate.lower()
        ):
            return candidate, target, target, requested if candidate != requested else ""
        effective = server_data_resolve_folder_link_ancestor(target, username=username, admin=admin)
        if effective.exists():
            if not effective.is_dir():
                raise RuntimeError("Duong dan server data khong phai thu muc.")
            return candidate, target, effective, requested if candidate != requested else ""
        candidate = clean_path_value(candidate.rsplit("/", 1)[0]) if "/" in candidate else ""
    return "", None, None, requested


def list_server_data(
    relative_path: str = "",
    username: str = "",
    admin: bool = False,
    task_owner_hint: str = "",
    fresh: bool = False,
    lightweight: bool = False,
    include_task_board: bool = True,
    include_space_task: bool = False,
) -> dict:
    username = normalize_username(username)
    ensure_info = ensure_server_data_folders(username)
    raw = clean_path_value(relative_path)
    target = None
    effective_target = None
    fallback_from = ""
    if raw:
        raw, target, effective_target, fallback_from = resolve_server_data_list_folder(raw, username, admin=admin)
    lightweight = bool(lightweight)
    raw_parts = [clean(part) for part in re.split(r"[\\/]+", raw) if clean(part)]
    raw_owner = normalize_username(raw_parts[0]) if raw_parts else ""
    own_user_folder_view = bool(raw_owner and username and raw_owner.lower() == username.lower())
    admin_view_context = bool(admin and not own_user_folder_view)
    # Updated 2026-07-06: folder Back/List must return entries+progress quickly; task boards stay on root/dashboard paths.
    include_task_board = bool(include_task_board) and not lightweight and not raw
    include_space_task = bool(include_space_task) and not lightweight and clean_path_value(raw) in {"", "common"}
    hinted_owner = normalize_username(task_owner_hint) if admin else ""
    if hinted_owner and (not learner_user_exists(hinted_owner) or not (SERVER_DATA_ROOT / hinted_owner).is_dir()):
        hinted_owner = ""
    inferred_owner = lesson_task_owner_for_path(raw, username, admin=admin)
    task_owner = hinted_owner or inferred_owner
    if admin and not task_owner and username and clean_path_value(raw) in {"", "common"}:
        task_owner = username
    stats_user = task_owner or (username if not admin else "")
    study_user = task_owner or username
    # `fresh` means "do not reuse the browser-list response cache". It must not
    # force a full manifest rebuild here, because admins often pass fresh while
    # switching learners or after small mutations. Full manifest refresh is kept
    # behind the dashboard button and the 10-minute background checker.
    manifest = get_server_data_manifest(force=False)
    current_folder_signature = ""
    if raw:
        current_folder_signature = server_data_directory_listing_signature(effective_target)
    else:
        current_folder_signature = ""
    cache_key = "|".join([
        "v2",
        "lite" if lightweight else "full",
        "tasks" if include_task_board else "deferred-tasks",
        "space-task" if include_space_task else "space-task-deferred",
        username.lower(),
        "admin" if admin else "user",
        raw.lower(),
        task_owner.lower(),
        study_user.lower(),
        stats_user.lower(),
    ])
    viewer_progress_user = username if admin_view_context and study_user and normalize_username(username) != normalize_username(study_user) else ""
    cache_signature = server_data_list_cache_signature(
        manifest,
        study_user=study_user,
        task_owner=task_owner,
        stats_user=stats_user,
        viewer_user=viewer_progress_user,
        folder_signature=current_folder_signature,
        lightweight=lightweight,
        include_task_board=include_task_board,
    )
    _list_started = time.perf_counter()
    _list_phase_ms = {}
    def _list_timing_header(total_ms: int) -> str:
        parts = [
            f"list_learning_stats;dur={_list_phase_ms.get('learning_stats', 0):.3f}",
            f"list_progress_indexes;dur={_list_phase_ms.get('progress_indexes', 0):.3f}",
            f"list_tasks;dur={_list_phase_ms.get('tasks', 0):.3f}",
            f"list_space_task;dur={_list_phase_ms.get('space_task', 0):.3f}",
            f"list_notices;dur={_list_phase_ms.get('notices', 0):.3f}",
            f"list_manifest_entries;dur={_list_phase_ms.get('manifest_entries', 0):.3f}",
            f"list_vault_merge;dur={_list_phase_ms.get('vault_merge', 0):.3f}",
            f"list_entry_loop;dur={_list_phase_ms.get('entry_loop', 0):.3f}",
            f"list_entry_exists;dur={_list_phase_ms.get('entry_exists', 0):.3f}",
            f"list_entry_folder_progress;dur={_list_phase_ms.get('entry_folder_progress', 0):.3f}",
            f"list_entry_file_study;dur={_list_phase_ms.get('entry_file_study', 0):.3f}",
            f"list_entry_file_meta;dur={_list_phase_ms.get('entry_file_meta', 0):.3f}",
            f"list_sort;dur={_list_phase_ms.get('sort', 0):.3f}",
            f"list_total;dur={total_ms:.3f}",
        ]
        return ", ".join(parts)
    cached_payload = None if fresh else get_cached_server_data_list(cache_key, cache_signature)
    if cached_payload:
        cached_payload = dict(cached_payload)
        cached_payload["_server_timing"] = f"list_cache_hit;dur={(time.perf_counter() - _list_started) * 1000:.3f}"
        return cached_payload
    _phase_started = time.perf_counter()
    # Updated 2026-07-06: Back/List uses cached learning stats only; force rebuild stays on dashboard/admin paths.
    learning_stats = {} if not include_task_board or not stats_user else lesson_user_learning_summary_cached_or_empty(stats_user)
    _list_phase_ms["learning_stats"] = int((time.perf_counter() - _phase_started) * 1000)
    _phase_started = time.perf_counter()
    progress_index = {} if lightweight or not study_user else lesson_progress_record_index(study_user)
    time_index = {} if lightweight or not study_user else lesson_time_state_index(study_user)
    viewer_progress_index = {} if lightweight or not viewer_progress_user else lesson_progress_record_index(viewer_progress_user)
    viewer_time_index = {} if lightweight or not viewer_progress_user else lesson_time_state_index(viewer_progress_user)
    _list_phase_ms["progress_indexes"] = int((time.perf_counter() - _phase_started) * 1000)
    _phase_started = time.perf_counter()
    task_rows = lesson_tasks_for_user(
        task_owner,
        username,
        progress_index,
        time_index,
        include_admin=bool(admin),
        viewer_progress_index=viewer_progress_index,
        viewer_time_index=viewer_time_index,
    ) if task_owner and include_task_board else []
    _list_phase_ms["tasks"] = int((time.perf_counter() - _phase_started) * 1000)
    _phase_started = time.perf_counter()
    should_include_space_task = bool(task_owner and (include_task_board or include_space_task))
    space_task = space_task_payload_for_user(
        task_owner,
        username,
        progress_index,
        time_index,
        include_admin=bool(admin),
        viewer_progress_index=viewer_progress_index,
        viewer_time_index=viewer_time_index,
    ) if should_include_space_task else {
        "enabled": bool(task_owner),
        "tasks": [],
        "preferred_folders": (
            space_task_settings_for_user(task_owner).get("preferred_folders", [])
            if task_owner and (include_task_board or include_space_task) else []
        ),
        "deferred": bool(task_owner and not lightweight),
        "settings_deferred": bool(task_owner and not (include_task_board or include_space_task)),
    }
    _list_phase_ms["space_task"] = int((time.perf_counter() - _phase_started) * 1000)
    space_task_rows = space_task.get("tasks", []) if isinstance(space_task, dict) else []
    _phase_started = time.perf_counter()
    notice_rows = lesson_task_notices_for_user(task_owner, admin_view=bool(admin and task_owner)) if task_owner and include_task_board else []
    _list_phase_ms["notices"] = int((time.perf_counter() - _phase_started) * 1000)
    if not raw:
        entries = []
        manifest_root_entries = []
        try:
            manifest_root_entries = [
                dict(item) for item in (manifest.get("folders", {}).get("") or [])
                if isinstance(item, dict)
            ]
        except Exception:
            manifest_root_entries = []
        if admin:
            manifest_by_name = {clean(entry.get("name", "")).lower(): dict(entry) for entry in manifest_root_entries}
            ordered_admin_roots: list[tuple[str, str]] = [("common", "shared")]
            admin_folder_exists = "admin" in manifest_by_name or (SERVER_DATA_ROOT / "admin").is_dir()
            if admin_folder_exists:
                ordered_admin_roots.append(("admin", "system-admin"))
            if username:
                ordered_admin_roots.append((username, "private"))
            try:
                other_users = [
                    normalize_username(item)
                    for item in list_dashboard_usernames()
                    if normalize_username(item) and normalize_username(item) not in {username, "admin"}
                ]
            except Exception:
                other_users = []
            for folder_name in other_users:
                entry_exists = folder_name.lower() in manifest_by_name or (SERVER_DATA_ROOT / folder_name).is_dir()
                if entry_exists:
                    ordered_admin_roots.append((folder_name, "admin-user"))
            known = set()
            for folder_name, owner in ordered_admin_roots:
                folder_key = clean(folder_name).lower()
                if not folder_key or folder_key in known or folder_key in {clean(item).lower() for item in server_data_manifest_skip_tops()}:
                    continue
                entry = manifest_by_name.get(folder_key) or server_data_manifest_root_entry(folder_name, owner)
                entry["owner"] = owner
                if owner in {"private", "admin-user"}:
                    entry["task_owner"] = folder_name
                entries.append(entry)
                known.add(folder_key)
        else:
            manifest_by_name = {clean(entry.get("name", "")).lower(): dict(entry) for entry in manifest_root_entries}
            for folder_name, owner in [("common", "shared"), (username, "private")]:
                entry = manifest_by_name.get(folder_name.lower()) or server_data_manifest_root_entry(folder_name, owner)
                entry["owner"] = owner
                entries.append(entry)
        if admin:
            admin_root_order = {"common": 0}
            admin_root_order["admin"] = 1
            if username:
                admin_root_order[username.lower()] = 1 if username.lower() == "admin" else 2
            entries.sort(key=lambda entry: (
                admin_root_order.get(clean(entry.get("name", "")).lower(), 3),
                entry.get("type") != "folder",
                natural_sort_key(entry.get("name", "")),
            ))
        else:
            entries.sort(key=lambda entry: (clean(entry.get("name", "")).lower() != "common", entry.get("type") != "folder", natural_sort_key(entry.get("name", ""))))
        payload = {
            "ok": True,
            "root": str(SERVER_DATA_ROOT),
            "path": "",
            "parent": "",
            "manifest_updated_at": clean(manifest.get("updated_at", "")) if isinstance(manifest, dict) else "",
            "manifest_signature": server_data_tree_runtime_revision(username, admin, manifest),
            "vault_revision": server_database_vault_revision(study_user or username),
            "manifest_integrity_signature": clean(manifest.get("signature", "")) if isinstance(manifest, dict) else "",
            "username": username,
            "admin": bool(admin),
            "task_owner": task_owner,
            "tasks": task_rows,
            "space_task": space_task,
            "space_tasks": space_task_rows,
            "task_notices": notice_rows,
            "learning_stats": learning_stats,
            "allowed": ensure_info,
            "entries": entries,
        }
        if fallback_from:
            payload["fallback_from"] = fallback_from
        if lightweight:
            payload["lightweight"] = True
        if task_owner and not include_task_board:
            payload["task_board_deferred"] = True
        _list_total_ms = int((time.perf_counter() - _list_started) * 1000)
        payload["_server_timing"] = _list_timing_header(_list_total_ms)
        if _list_total_ms >= int(SERVER_DATA_LIST_SLOW_LOG_MS or 0):
            stt_debug_log(
                "server_data_list_slow",
                admin=bool(admin),
                viewer=username,
                path="",
                task_owner=task_owner,
                study_user=study_user,
                stats_user=stats_user,
                total_ms=_list_total_ms,
                entries=len(entries),
                phase_ms=_list_phase_ms,
                space_task_enabled=bool(isinstance(space_task, dict) and space_task.get("enabled")),
                space_task_scanned_files=int(space_task.get("scanned_files", 0) or 0) if isinstance(space_task, dict) else 0,
                space_task_folder_count=len(space_task.get("folders", [])) if isinstance(space_task, dict) and isinstance(space_task.get("folders"), list) else 0,
            )
        if isinstance(space_task, dict) and space_task.get("pending"):
            return payload
        return remember_server_data_list(cache_key, cache_signature, payload)
    if target is None:
        target = safe_server_data_path(raw, username, admin=admin)
        effective_target = server_data_resolve_folder_link_ancestor(target, username=username, admin=admin)
        if not effective_target.exists():
            raise RuntimeError("Thu muc server data khong ton tai.")
        if not effective_target.is_dir():
            raise RuntimeError("Duong dan server data khong phai thu muc.")
    if effective_target is None:
        effective_target = server_data_resolve_folder_link_ancestor(target, username=username, admin=admin)
    entries = []
    current = clean_path_value(raw) if raw else server_data_relative(target)
    # Added 2026-07-08: QM Home/Common first paint needs Space Task fast; visible file progress hydrates after render.
    defer_entry_study = bool(include_space_task and not include_task_board and current == "common")
    virtual_link_payload = server_data_folder_link_ancestor_payload(target)
    listing_target = effective_target if virtual_link_payload else target
    top_folder = clean(raw.split("/", 1)[0]) if raw else ""
    browsing_owner_folder = bool(admin and task_owner and top_folder.lower() == task_owner.lower())
    if browsing_owner_folder and (SERVER_DATA_ROOT / "common").is_dir():
        try:
            stat = (SERVER_DATA_ROOT / "common").stat()
            entries.append({
                "name": "common",
                "path": "common",
                "type": "folder",
                "size": 0,
                "modified": int(stat.st_mtime),
                "owner": "shared",
                "task_owner": task_owner,
                "virtual_common": True,
            })
        except OSError:
            pass
    _phase_started = time.perf_counter()
    manifest_entries = None
    with SERVER_DATA_MANIFEST_LOCK:
        manifest_clean = not bool(SERVER_DATA_MANIFEST_STATE.get("dirty"))
        manifest_watcher_started = bool(SERVER_DATA_MANIFEST_STATE.get("watcher_started"))
    if virtual_link_payload:
        if manifest_clean:
            target_manifest_path = server_data_relative(listing_target)
            target_manifest_entries = server_data_manifest_folder_entries(target_manifest_path, manifest)
            if target_manifest_entries is not None:
                manifest_entries = [
                    mirrored
                    for source_entry in target_manifest_entries
                    for mirrored in [server_data_virtual_link_manifest_entry(
                        source_entry,
                        current,
                        virtual_link_payload.get("created_by", ""),
                    )]
                    if mirrored
                ]
    else:
        manifest_entries = server_data_manifest_folder_entries(current, manifest)
    if manifest_entries is None:
        manifest_entries = []
        if virtual_link_payload or not isinstance(manifest.get("folders"), dict) or not manifest.get("folders") or not lightweight:
            try:
                target_children = list(listing_target.iterdir())
            except OSError:
                target_children = []
            for item in target_children:
                try:
                    entry = server_data_virtual_link_entry(
                        item,
                        current,
                        virtual_link_payload.get("created_by", ""),
                    ) if virtual_link_payload else server_data_manifest_entry(item)
                    if entry:
                        manifest_entries.append(entry)
                        continue
                    is_dir = item.is_dir()
                    if not is_dir and not is_lesson_file(item):
                        continue
                    stat = item.stat()
                    manifest_entries.append({
                        "name": item.name,
                        "path": server_data_relative(item),
                        "type": "folder" if is_dir else "file",
                        "size": 0 if is_dir else int(stat.st_size),
                        "modified": int(stat.st_mtime),
                        "extension": "" if is_dir else item.suffix,
                    })
                except OSError:
                    continue
    elif (
        not lightweight
        and not virtual_link_payload
        and len(manifest_entries) <= 160
        and not include_space_task
        and (not manifest_clean or not manifest_watcher_started)
    ):
        # Updated 2026-07-30: the native watcher owns clean-manifest deltas; only its unavailable/dirty fallback scans disk.
        try:
            existing_keys = {
                clean_path_value(item.get("effective_path") or item.get("link_target") or item.get("path", "")).lower()
                for item in manifest_entries
                if isinstance(item, dict)
            }
            existing_names = {
                clean(item.get("name", "")).lower()
                for item in manifest_entries
                if isinstance(item, dict)
            }
            for item in listing_target.iterdir():
                try:
                    if server_data_manifest_should_skip(item):
                        continue
                    entry = server_data_manifest_entry(item)
                    if not entry:
                        continue
                    entry_key = clean_path_value(entry.get("effective_path") or entry.get("link_target") or entry.get("path", "")).lower()
                    entry_name = clean(entry.get("name", "")).lower()
                    if (entry_key and entry_key in existing_keys) or (entry_name and entry_name in existing_names):
                        continue
                    manifest_entries.append(entry)
                    if entry_key:
                        existing_keys.add(entry_key)
                    if entry_name:
                        existing_names.add(entry_name)
                except OSError:
                    continue
        except OSError:
            pass
    elif not lightweight and not virtual_link_payload and len(manifest_entries) > 160:
        # Large folders under common can freeze the vault if every navigation
        # re-scans the whole directory on top of the manifest read.
        pass
    _list_phase_ms["manifest_entries"] = int((time.perf_counter() - _phase_started) * 1000)
    # Added 2026-07-23: merge SQLite-only Vault placements without creating,
    # scanning or renaming physical files.  Existing manifest rows remain the
    # discovery source for admin-managed replicas.
    _phase_started = time.perf_counter()
    vault_matcher = globals().get("server_database_vault_match")
    vault_children_reader = globals().get("server_database_vault_children")
    if bool(globals().get("SERVER_DATABASE_VAULT_ENABLED", True)) and callable(vault_children_reader):
        exact_vault_folder = vault_matcher(current) if callable(vault_matcher) else {}
        if exact_vault_folder and clean_path_value(exact_vault_folder.get("path", "")).lower() != current.lower():
            exact_vault_folder = {}
        vault_parent_id = clean(exact_vault_folder.get("vault_folder_id", "")) if isinstance(exact_vault_folder, dict) else ""
        current_parts = [clean(part) for part in current.split("/") if clean(part)]
        current_owner = normalize_username(current_parts[0]) if current_parts else ""
        if not vault_parent_id and current_owner and current.lower() == current_owner.lower():
            vault_parent_id = _server_database_vault_root_id(current_owner)
        if vault_parent_id:
            legacy_shell_reader = globals().get("server_database_vault_is_legacy_shell")
            existing_paths = {
                clean_path_value(item.get("path", "")).lower()
                for item in manifest_entries
                if isinstance(item, dict)
                and not (callable(legacy_shell_reader) and legacy_shell_reader(item.get("path", "")))
            }
            existing_by_path = {
                clean_path_value(item.get("path", "")).lower(): item
                for item in manifest_entries
                if isinstance(item, dict) and clean_path_value(item.get("path", ""))
            }
            for virtual_item in vault_children_reader(vault_parent_id, current_owner or username):
                virtual_path = clean_path_value(virtual_item.get("path", ""))
                if not virtual_path:
                    continue
                existing_entry = existing_by_path.get(virtual_path.lower())
                if existing_entry is not None and virtual_item.get("vault_entry_id"):
                    existing_entry.update({
                        "name": clean(virtual_item.get("display_name", "")) or clean(existing_entry.get("name", "")),
                        "virtual": True,
                        "linked": False,
                        "vault_entry_id": clean(virtual_item.get("vault_entry_id", "")),
                        "lesson_id": clean(virtual_item.get("lesson_id", "")) or clean(existing_entry.get("lesson_id", "")),
                        "sort_order": int(virtual_item.get("sort_order", 0) or 0),
                        "created_by": normalize_username(virtual_item.get("username", "")),
                    })
                    continue
                if existing_entry is not None and virtual_item.get("vault_folder_id"):
                    existing_entry.update({
                        "name": clean(virtual_item.get("display_name", "")) or clean(existing_entry.get("name", "")),
                        "virtual": True,
                        "linked": False,
                        "vault_folder_id": clean(virtual_item.get("vault_folder_id", "")),
                        "sort_order": int(virtual_item.get("sort_order", 0) or 0),
                        "created_by": normalize_username(virtual_item.get("username", "")),
                    })
                    continue
                if virtual_path.lower() in existing_paths:
                    continue
                if virtual_item.get("vault_folder_id"):
                    if clean(virtual_item.get("folder_type", "")).upper() == "PHYSICAL_CONTAINER" and server_data_manifest_path(virtual_path).is_dir():
                        continue
                    virtual_folder_type = clean(virtual_item.get("folder_type", "")).upper()
                    legacy_reference = virtual_folder_type in {"COMMON_REFERENCE", "PHYSICAL_REFERENCE"}
                    source_path = clean_path_value(virtual_item.get("source_path", "")) if legacy_reference else ""
                    manifest_entries.append({
                        "name": clean(virtual_item.get("display_name", "")),
                        "path": virtual_path,
                        "type": "folder",
                        "size": 0,
                        "modified": 0,
                        "linked": legacy_reference,
                        "virtual": True,
                        "vault_folder_id": clean(virtual_item.get("vault_folder_id", "")),
                        "sort_order": int(virtual_item.get("sort_order", 0) or 0),
                        "link_target": source_path,
                        "effective_path": source_path,
                        "created_by": normalize_username(virtual_item.get("username", "")),
                    })
                elif virtual_item.get("vault_entry_id"):
                    source_resolver = globals().get("server_database_vault_resolved_source_path")
                    source_path = clean_path_value(source_resolver(virtual_item)) if callable(source_resolver) else clean_path_value(virtual_item.get("source_path", ""))
                    source_entry = server_data_manifest_entry(server_data_manifest_path(source_path)) if source_path else None
                    entry = dict(source_entry) if isinstance(source_entry, dict) else {
                        "type": "file",
                        "size": 0,
                        "modified": 0,
                        "extension": Path(source_path).suffix,
                    }
                    entry.update({
                        "name": clean(virtual_item.get("display_name", "")),
                        "path": virtual_path,
                        "type": "file",
                        "linked": True,
                        "virtual": True,
                        "vault_entry_id": clean(virtual_item.get("vault_entry_id", "")),
                        "sort_order": int(virtual_item.get("sort_order", 0) or 0),
                        "lesson_id": clean(virtual_item.get("lesson_id", "")),
                        "link_target": source_path,
                        "effective_path": source_path,
                        "created_by": normalize_username(virtual_item.get("username", "")),
                    })
                    manifest_entries.append(entry)
                existing_paths.add(virtual_path.lower())
    _list_phase_ms["vault_merge"] = int((time.perf_counter() - _phase_started) * 1000)
    _phase_started = time.perf_counter()
    _entry_exists_ms = 0
    _entry_folder_progress_ms = 0
    _entry_file_study_ms = 0
    _entry_file_meta_ms = 0
    for source_entry in manifest_entries:
        try:
            entry = dict(source_entry)
            is_dir = entry.get("type") == "folder"
            legacy_shell_reader = globals().get("server_database_vault_is_legacy_shell")
            if is_dir and not entry.get("virtual") and callable(legacy_shell_reader) and legacy_shell_reader(entry.get("path", "")):
                continue
            if not is_dir and clean(entry.get("extension", "")).lower() not in LESSON_FILE_SUFFIXES:
                continue
            if not virtual_link_payload and not entry.get("virtual"):
                entry_path_value_for_exists = clean_path_value(entry.get("effective_path") or entry.get("link_target") or entry.get("path", ""))
                if entry_path_value_for_exists:
                    try:
                        _entry_phase_started = time.perf_counter()
                        if not server_data_manifest_path(entry_path_value_for_exists).exists():
                            continue
                        _entry_exists_ms += int((time.perf_counter() - _entry_phase_started) * 1000)
                    except Exception:
                        pass
            if (entry.get("linked") or entry.get("link_target")) and not clean(entry.get("created_by", "")):
                try:
                    link_path = safe_server_data_path(clean(entry.get("path", "")), username, admin=admin)
                    link_payload = read_server_data_folder_link_payload(link_path) if is_dir else read_server_data_link_payload(link_path)
                    if link_payload:
                        entry["created_by"] = normalize_username(link_payload.get("created_by", ""))
                        entry["created_at"] = clean(link_payload.get("created_at", ""))
                except Exception:
                    pass
            if is_dir and not lightweight and (entry.get("linked") or entry.get("link_target")) and not any(key in entry for key in ("folder_count", "file_count", "space_v_file_count", "word_count")):
                try:
                    folder_path = safe_server_data_path(clean(entry.get("path", "")), username, admin=admin)
                    effective_folder = server_data_folder_link_target_path(folder_path, username=username, admin=admin) or folder_path
                    counts = server_data_folder_counts_cached(effective_folder)
                    entry.update(counts)
                    entry["counts_from_actual"] = True
                    update_server_data_folder_link_counts(folder_path, counts)
                except Exception:
                    entry.update({"folder_count": 0, "file_count": 0, "space_v_file_count": 0, "word_count": 0})
            if is_dir and not lightweight:
                _entry_phase_started = time.perf_counter()
                folder_progress_path = clean_path_value(entry.get("effective_path") or entry.get("link_target") or entry.get("path", ""))
                folder_word_count = max(0, space_w_int(entry.get("word_count", 0), 0))
                folder_progress = lesson_space_v_folder_progress_from_index(progress_index, folder_progress_path, folder_word_count) if folder_progress_path else {}
                if folder_progress:
                    entry["study"] = {
                        "title": clean(entry.get("name", "")) or Path(folder_progress_path).name,
                        "nodes": folder_word_count,
                        "progress": folder_progress,
                    }
                _entry_folder_progress_ms += int((time.perf_counter() - _entry_phase_started) * 1000)
            if entry.get("virtual") and not is_dir:
                source_value = clean_path_value(entry.get("effective_path") or entry.get("link_target", ""))
                if source_value and not server_data_manifest_path(source_value).is_file():
                    entry["source_missing"] = True
            if not is_dir and not lightweight:
                _entry_phase_started = time.perf_counter()
                entry_path_value = clean(entry.get("path", ""))
                study_path_value = clean_path_value(entry.get("effective_path") or entry.get("link_target") or entry_path_value)
                identity_ready = globals().get("server_database_lesson_identity_registry_ready")
                identity_resolver = globals().get("server_database_lesson_file_id_for_path")
                # Updated 2026-07-30: manifest identity is revision-validated; avoid resolving every admin row again.
                if callable(identity_ready) and callable(identity_resolver) and identity_ready() and not clean(entry.get("lesson_id", "")):
                    entry["lesson_id"] = clean(identity_resolver(study_path_value))[:240]
                progress_path_value = clean_path_value(entry_path_value or study_path_value)
                strict_progress_paths = bool(progress_path_value and study_path_value and progress_path_value.lower() != study_path_value.lower())
                entry_parts = [clean(part) for part in re.split(r"[\\/]+", entry_path_value) if clean(part)]
                entry_owner = normalize_username(entry_parts[0]) if entry_parts else ""
                entry_admin_view = bool(admin and not (entry_owner and username and entry_owner.lower() == username.lower()))
                item_path = server_data_manifest_path(study_path_value)
                if defer_entry_study:
                    entry["study_deferred"] = True
                else:
                    entry["study"] = summarize_lesson_study(
                        item_path,
                        study_user,
                        progress_index,
                        time_index,
                        include_admin=entry_admin_view,
                        progress_relative_path=progress_path_value,
                        path_is_effective=True,
                        progress_relative_paths=[progress_path_value, study_path_value, clean_path_value(entry.get("effective_path", "")), clean_path_value(entry.get("link_target", ""))],
                        strict_progress_paths=strict_progress_paths,
                        include_log=False,
                        file_meta=entry,
                        lesson_id=clean(entry.get("lesson_id", "")),
                    )
                    _entry_file_study_ms += int((time.perf_counter() - _entry_phase_started) * 1000)
                    try:
                        _entry_phase_started = time.perf_counter()
                        entry_ext = clean(entry.get("extension", "")).lower()
                        vocab_extensions = globals().get("VOCAB_STATS_SUPPORTED_EXTENSIONS", {".space_v", ".space_b"})
                        vocab_meta = lesson_file_vocab_meta_for_target(item_path) if entry_ext in vocab_extensions else {}
                        if vocab_meta:
                            entry.update(vocab_meta)
                        _entry_file_meta_ms += int((time.perf_counter() - _entry_phase_started) * 1000)
                    except Exception:
                        pass
                if entry_admin_view:
                    if "study" not in entry:
                        entry["study"] = {"admin_view": True, "study_deferred": True}
                    else:
                        entry["study"]["admin_view"] = True
                    if viewer_progress_user and not defer_entry_study:
                        viewer_study = summarize_lesson_study(
                            item_path,
                            viewer_progress_user,
                        viewer_progress_index,
                        viewer_time_index,
                        include_admin=True,
                        progress_relative_path=progress_path_value,
                        path_is_effective=True,
                        progress_relative_paths=[progress_path_value],
                            strict_progress_paths=strict_progress_paths,
                            include_log=False,
                            file_meta=entry,
                            lesson_id=clean(entry.get("lesson_id", "")),
                        )
                        viewer_progress = viewer_study.get("progress") if isinstance(viewer_study.get("progress"), dict) else {}
                        viewer_admin_count = max(
                            0,
                            int(viewer_study.get("admin_mine", 0) or 0),
                            int(viewer_study.get("mine", 0) or 0),
                        )
                        if viewer_progress:
                            entry["study"]["admin_progress"] = viewer_progress
                            entry["study"]["admin_progress_user"] = viewer_progress_user
                            entry["study"]["admin_time"] = viewer_study.get("time", {})
                            entry["study"]["admin_time_seconds"] = int(viewer_study.get("time_seconds", 0) or 0)
                        if viewer_admin_count:
                            entry["study"]["admin_progress_mine"] = viewer_admin_count
                            entry["study"]["admin_progress_mine_last"] = clean(viewer_study.get("admin_mine_last") or viewer_study.get("mine_last") or viewer_study.get("last", ""))
                            entry["study"]["admin_progress_completed"] = True
                entry_match_paths = {
                    clean_path_value(entry.get("path", "")).lower(),
                    clean_path_value(entry.get("effective_path", "")).lower(),
                    clean_path_value(entry.get("link_target", "")).lower(),
                }
                entry_match_paths = {item for item in entry_match_paths if item}
                task_match = next((
                    task for task in task_rows
                    if entry_match_paths.intersection({
                        clean_path_value(task.get("path", "")).lower(),
                        clean_path_value(task.get("effective_path", "")).lower(),
                        clean_path_value(task.get("link_target", "")).lower(),
                    })
                ), None)
                if task_match:
                    entry["task"] = {
                        "id": clean(task_match.get("id", "")),
                        "path": clean_path_value(task_match.get("path", "")),
                        "effective_path": clean_path_value(task_match.get("effective_path", "")),
                        "link_target": clean_path_value(task_match.get("link_target", "")),
                        "completed": bool(task_match.get("completed")),
                        "completed_at": clean(task_match.get("completed_at", "")),
                        "severity": normalize_lesson_task_severity(task_match.get("severity", "")),
                        "user_count": int(task_match.get("user_count", 0) or 0),
                        "creator_role": clean(task_match.get("creator_role", "")) or "admin",
                        "added_by": normalize_username(task_match.get("added_by", "")),
                        "can_remove": bool(task_match.get("can_remove")),
                    }
            entries.append(entry)
        except OSError:
            continue
    _list_phase_ms["entry_loop"] = int((time.perf_counter() - _phase_started) * 1000)
    _list_phase_ms["entry_exists"] = _entry_exists_ms
    _list_phase_ms["entry_folder_progress"] = _entry_folder_progress_ms
    _list_phase_ms["entry_file_study"] = _entry_file_study_ms
    _list_phase_ms["entry_file_meta"] = _entry_file_meta_ms
    _phase_started = time.perf_counter()
    def _server_data_entry_rank(entry: dict) -> int:
        entry_path = clean_path_value(entry.get("path", ""))
        entry_parts = [clean(part) for part in entry_path.split("/") if clean(part)]
        if entry.get("type") == "folder" and (entry.get("virtual_common") or entry_path.lower() == "common"):
            return 0
        if (
            entry.get("type") == "folder"
            and len(entry_parts) == 2
            and entry_parts[1].lower() == VOCAB_MISSION_PENDING_DIR.lower()
        ):
            return 1
        return 2 if entry.get("type") == "folder" else 3

    entries.sort(key=lambda entry: (
        _server_data_entry_rank(entry),
        0 if int(entry.get("sort_order", 0) or 0) > 0 else 1,
        int(entry.get("sort_order", 0) or 0) if int(entry.get("sort_order", 0) or 0) > 0 else 0,
        natural_sort_key(entry.get("name", "")),
    ))
    _list_phase_ms["sort"] = int((time.perf_counter() - _phase_started) * 1000)
    parent = ""
    if current:
        parent = server_data_relative(target.parent)
    if admin and task_owner and current == "common":
        parent = task_owner
    payload = {
        "ok": True,
        "root": str(SERVER_DATA_ROOT),
        "path": current,
        "parent": parent,
        "manifest_updated_at": clean(manifest.get("updated_at", "")) if isinstance(manifest, dict) else "",
        "manifest_signature": server_data_tree_runtime_revision(username, admin, manifest),
        "vault_revision": server_database_vault_revision(study_user or username),
        "manifest_integrity_signature": clean(manifest.get("signature", "")) if isinstance(manifest, dict) else "",
        "username": username,
        "admin": bool(admin),
        "task_owner": task_owner,
        "tasks": task_rows,
        "space_task": space_task,
        "space_tasks": space_task_rows,
        "task_notices": notice_rows,
        "learning_stats": learning_stats,
        "allowed": ensure_info,
        "entries": entries,
    }
    if fallback_from:
        payload["fallback_from"] = fallback_from
    if lightweight:
        payload["lightweight"] = True
    if task_owner and not include_task_board:
        payload["task_board_deferred"] = True
    payload["_server_timing"] = _list_timing_header(int((time.perf_counter() - _list_started) * 1000))
    _list_total_ms = int((time.perf_counter() - _list_started) * 1000)
    if _list_total_ms >= int(SERVER_DATA_LIST_SLOW_LOG_MS or 0):
        stt_debug_log(
            "server_data_list_slow",
            admin=bool(admin),
            viewer=username,
            path=current,
            task_owner=task_owner,
            study_user=study_user,
            stats_user=stats_user,
            total_ms=_list_total_ms,
            entries=len(entries),
            phase_ms=_list_phase_ms,
            space_task_enabled=bool(isinstance(space_task, dict) and space_task.get("enabled")),
            space_task_scanned_files=int(space_task.get("scanned_files", 0) or 0) if isinstance(space_task, dict) else 0,
            space_task_folder_count=len(space_task.get("folders", [])) if isinstance(space_task, dict) and isinstance(space_task.get("folders"), list) else 0,
        )
    if isinstance(space_task, dict) and space_task.get("pending"):
        return payload
    if isinstance(space_task, dict) and space_task.get("pending"):
        return payload
    return remember_server_data_list(cache_key, cache_signature, payload)


def clear_server_data_list_cache() -> None:
    with SERVER_DATA_LIST_CACHE_LOCK:
        SERVER_DATA_LIST_CACHE.clear()


# Added 2026-07-23: virtual Vault writes invalidate only viewer/target scopes.
def clear_server_data_list_cache_for_user(username: str = "") -> None:
    target = normalize_username(username).casefold()
    if not target:
        return
    with SERVER_DATA_LIST_CACHE_LOCK:
        for key in list(SERVER_DATA_LIST_CACHE):
            parts = str(key).split("|")
            if target in {clean(part).casefold() for part in parts[4:]}:
                SERVER_DATA_LIST_CACHE.pop(key, None)


# Added 2026-07-05: keeps small Lesson Vault path mutations from dropping every cached folder list.
def clear_server_data_list_cache_paths(relative_paths: list[str] | tuple[str, ...] | set[str]) -> None:
    normalized_paths = {
        clean_path_value(path).lower()
        for path in (relative_paths or [])
        if clean_path_value(path)
    }
    if not normalized_paths:
        return
    def _path_matches(cached_path: str) -> bool:
        cached = clean_path_value(cached_path).lower()
        if not cached:
            return False
        for path in normalized_paths:
            if cached == path or cached.startswith(path + "/") or path.startswith(cached + "/"):
                return True
        return False
    with SERVER_DATA_LIST_CACHE_LOCK:
        for cache_key in list(SERVER_DATA_LIST_CACHE.keys()):
            parts = str(cache_key).split("|")
            cached_path = parts[6] if len(parts) > 6 else ""
            if _path_matches(cached_path):
                SERVER_DATA_LIST_CACHE.pop(cache_key, None)


# Added 2026-07-06: patch one lesson row after Space_V progress saves without expiring the whole folder cache.
def patch_server_data_list_cache_study(
    relative_paths: list[str] | tuple[str, ...] | set[str],
    study: dict | None = None,
    username: str = "",
) -> int:
    wanted_paths = {
        clean_path_value(path).lower()
        for path in (relative_paths or [])
        if clean_path_value(path)
    }
    if not wanted_paths or not isinstance(study, dict):
        return 0
    wanted_user = normalize_username(username).lower()
    patched = 0
    with SERVER_DATA_LIST_CACHE_LOCK:
        cached_rows = list(SERVER_DATA_LIST_CACHE.items())
        for cache_key, cache_row in cached_rows:
            row_patched = False
            parts = str(cache_key).split("|")
            study_user = normalize_username(parts[8] if len(parts) > 8 else "").lower()
            if wanted_user and study_user != wanted_user:
                continue
            payload = cache_row.get("payload") if isinstance(cache_row, dict) else {}
            entries = payload.get("entries") if isinstance(payload, dict) else []
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict) or entry.get("type") != "file":
                    continue
                entry_paths = {
                    clean_path_value(entry.get(key, "")).lower()
                    for key in ("path", "effective_path", "link_target", "linked_path", "source_path", "original_path")
                    if clean_path_value(entry.get(key, ""))
                }
                if not entry_paths.intersection(wanted_paths):
                    continue
                current_study = entry.get("study") if isinstance(entry.get("study"), dict) else {}
                entry["study"] = {**current_study, **study}
                patched += 1
                row_patched = True
            if row_patched:
                refresh_bytes = globals().get("refresh_server_data_list_cache_row_bytes")
                if callable(refresh_bytes):
                    refresh_bytes(cache_row)
    return patched
