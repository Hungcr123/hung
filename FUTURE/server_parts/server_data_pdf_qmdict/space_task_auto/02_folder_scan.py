# Loaded by FUTURE.server_parts.server_data_pdf_qmdict.03_space_task_auto into the shared Future server runtime namespace.

def _space_task_folder_row(relative_path: str, source: str = "user", direct_only: bool = False) -> dict:
    return {
        "path": clean_path_value(relative_path),
        "source": clean(source),
        "direct_only": bool(direct_only),
    }


def _space_task_candidate_folder_rows(target_user: str, settings: dict | None = None) -> list[dict]:
    target_user = normalize_username(target_user)
    settings = settings if isinstance(settings, dict) else space_task_settings_for_user(target_user)
    rows = []
    seen = set()
    for folder in settings.get("preferred_folders", []):
        # Added 2026-07-10: saved Space Task folders are normalized at write time; avoid disk checks while building payloads.
        normalized = clean_path_value(folder)
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            rows.append(_space_task_folder_row(normalized, "preferred"))
    # Updated 2026-07-20: Space Task is fully opt-in; an empty setting must never scan the learner root.
    return rows[:SPACE_TASK_MAX_FOLDERS]


def _space_task_folder_scan_signature(folder: Path) -> tuple:
    # A cheap signature: the folder mtime catches add/remove/rename of direct
    # children, which is what changes the scan result in practice. Walking the
    # whole tree just to fingerprint it would defeat the cache, so we trade a
    # short TTL for the rare deep-nested change that leaves the top mtime alone.
    try:
        stat = folder.stat()
        return (int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1_000_000_000))), int(getattr(stat, "st_size", 0) or 0))
    except Exception:
        return (0, -1)


# Added 2026-07-24: learner task discovery must never surface rollback copies.
def _space_task_path_has_backup_component(value: object) -> bool:
    parts = [part.strip().lower() for part in clean_path_value(value).split("/") if part.strip()]
    return any(
        part in {"backup", "backups"}
        or part.startswith(("_backup", "backup_", "backup-"))
        for part in parts
    )


def _space_task_files_from_manifest(rel_path: str, direct_only: bool = False) -> list[Path] | None:
    manifest = get_server_data_manifest()
    folders = manifest.get("folders") if isinstance(manifest.get("folders"), dict) else {}
    if not isinstance(folders, dict) or not folders:
        return None
    start = clean_path_value(rel_path)
    if not start:
        return None
    if start not in folders and not any(str(key or "").strip("/").lower() == start.lower() for key in folders.keys()):
        return None
    ordered_files: list[Path] = []
    pending = [start]
    visited = set()
    while pending and len(ordered_files) < SPACE_TASK_SCAN_LIMIT_PER_FOLDER:
        current = clean_path_value(pending.pop(0))
        current_key = current.lower()
        if not current or current_key in visited:
            continue
        visited.add(current_key)
        rows = folders.get(current)
        if not isinstance(rows, list):
            continue
        child_folders: list[str] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "folder":
                if direct_only:
                    continue
                child_path = clean_path_value(item.get("path", ""))
                if child_path and not _space_task_path_has_backup_component(child_path):
                    child_folders.append(child_path)
                continue
            entry_path = clean_path_value(item.get("effective_path") or item.get("link_target") or item.get("path", ""))
            extension = clean(item.get("extension", "")).lower()
            if not entry_path or _space_task_path_has_backup_component(entry_path) or extension not in LESSON_FILE_SUFFIXES:
                continue
            try:
                ordered_files.append(SERVER_DATA_ROOT / Path(entry_path))
            except Exception:
                continue
            if len(ordered_files) >= SPACE_TASK_SCAN_LIMIT_PER_FOLDER:
                break
        if child_folders:
            child_folders.sort(key=natural_sort_key)
            pending[:0] = child_folders
    return ordered_files


def _space_task_fast_sort_path(path: Path) -> str:
    # Added 2026-07-10: sort Space Task folder scans without resolving every path on disk.
    try:
        raw = str(path)
        root = str(SERVER_DATA_ROOT)
        raw_lower = raw.lower()
        root_lower = root.lower().rstrip("\\/")
        if raw_lower.startswith(root_lower):
            return raw[len(root):].lstrip("\\/").replace("\\", "/")
        return raw.replace("\\", "/")
    except Exception:
        return str(path)


def _space_task_files_in_folder(folder_row: dict, target_user: str) -> list[Path]:
    rel_path = clean_path_value(folder_row.get("path", ""))
    if not rel_path:
        return []
    # Added 2026-07-24: scan SQLite Vault placements by their registered lesson
    # entries instead of requiring a matching physical learner directory.
    vault_matcher = globals().get("server_database_vault_match")
    vault_children = globals().get("server_database_vault_children")
    vault_source = globals().get("server_database_vault_resolved_source_path")
    if server_data_path_top(rel_path) == normalize_username(target_user).lower() and callable(vault_matcher) and callable(vault_children):
        virtual = vault_matcher(rel_path)
        if isinstance(virtual, dict) and clean(virtual.get("vault_folder_id", "")) and not clean_path_value(virtual.get("suffix", "")):
            files = []
            seen_folders = set()
            seen_paths = set()
            pending = [clean(virtual.get("vault_folder_id", ""))]
            while pending and len(files) < SPACE_TASK_SCAN_LIMIT_PER_FOLDER:
                folder_id = clean(pending.pop(0))
                if not folder_id or folder_id in seen_folders:
                    continue
                seen_folders.add(folder_id)
                for item in vault_children(folder_id, target_user):
                    child_id = clean(item.get("vault_folder_id", ""))
                    if child_id:
                        pending.append(child_id)
                        continue
                    source_path = vault_source(item) if callable(vault_source) else clean_path_value(item.get("source_path", ""))
                    source_path = clean_path_value(source_path)
                    source_key = source_path.lower()
                    if not source_path or source_key in seen_paths or _space_task_path_has_backup_component(source_path):
                        continue
                    try:
                        source_file = SERVER_DATA_ROOT / Path(source_path)
                    except Exception:
                        continue
                    if is_lesson_file(source_file):
                        seen_paths.add(source_key)
                        files.append(source_file)
                    if len(files) >= SPACE_TASK_SCAN_LIMIT_PER_FOLDER:
                        break
            return sorted(files, key=lambda path: natural_sort_key(_space_task_fast_sort_path(path) or path.name))
    try:
        folder = safe_server_data_path(rel_path, target_user, admin=True)
    except Exception:
        return []
    if not folder.is_dir():
        return []
    try:
        effective_folder = server_data_resolve_folder_link_ancestor(folder, username=target_user, admin=True)
    except Exception:
        effective_folder = folder
    if not effective_folder.is_dir():
        return []
    direct_only = bool(folder_row.get("direct_only"))
    cache_key = (str(folder).lower(), str(effective_folder).lower(), bool(direct_only))
    signature = (_space_task_folder_scan_signature(folder), _space_task_folder_scan_signature(effective_folder))
    now = time.time()
    with SPACE_TASK_FOLDER_SCAN_CACHE_LOCK:
        row = SPACE_TASK_FOLDER_SCAN_CACHE.get(cache_key)
        if (
            isinstance(row, dict)
            and row.get("signature") == signature
            and now - float(row.get("at", 0) or 0) < SPACE_TASK_FOLDER_SCAN_TTL_SECONDS
        ):
            return list(row.get("files") or [])
    # Updated 2026-07-08: use the warm manifest first; huge asset folders like Sound must not rglob tens of thousands of files.
    files = _space_task_files_from_manifest(rel_path, direct_only=direct_only)
    effective_rel_path = server_data_relative(effective_folder)
    if effective_rel_path and effective_rel_path.lower() != rel_path.lower():
        effective_files = _space_task_files_from_manifest(effective_rel_path, direct_only=direct_only)
        if effective_files is not None:
            files = effective_files
    if files is None:
        files = []
        try:
            iterator = effective_folder.iterdir() if direct_only else effective_folder.rglob("*")
            for path in iterator:
                if len(files) >= SPACE_TASK_SCAN_LIMIT_PER_FOLDER:
                    break
                relative_candidate = server_data_relative(path)
                if path.is_file() and not _space_task_path_has_backup_component(relative_candidate) and is_lesson_file(path):
                    files.append(path)
        except Exception:
            files = None
    if files is None:
        files = []
    ordered = sorted(files, key=lambda path: natural_sort_key(_space_task_fast_sort_path(path) or path.name))
    with SPACE_TASK_FOLDER_SCAN_CACHE_LOCK:
        SPACE_TASK_FOLDER_SCAN_CACHE[cache_key] = {"signature": signature, "files": list(ordered), "at": now}
        if len(SPACE_TASK_FOLDER_SCAN_CACHE) > 256:
            stale = sorted(SPACE_TASK_FOLDER_SCAN_CACHE.items(), key=lambda item: float(item[1].get("at", 0) or 0))
            for old_key, _v in stale[:64]:
                SPACE_TASK_FOLDER_SCAN_CACHE.pop(old_key, None)
    return ordered


def _space_task_file_space(path: Path, relative_path: str = "") -> str:
    space = lesson_progress_space_for_path(relative_path or server_data_relative(path), path.suffix.lower())
    return space if space in SPACE_TASK_ACTIVE_LIMITS else ""


def _space_task_limits_satisfied(counts: dict[str, int]) -> bool:
    for space, limit in SPACE_TASK_ACTIVE_LIMITS.items():
        if int(counts.get(space, 0) or 0) < int(limit or 0):
            return False
    return True


def _space_task_source_for_file(path: Path, target_user: str, folder_row: dict, folder_index: int, order_index: int) -> dict:
    rel_path = server_data_relative(path)
    space = _space_task_file_space(path, rel_path)
    digest_source = rel_path.lower()
    digest = hashlib.sha1(f"{target_user.lower()}|{digest_source}|space-task".encode("utf-8")).hexdigest()[:18]
    return {
        "id": f"space-task-{digest}",
        "path": rel_path,
        "name": path.name,
        "creator_role": "space_task",
        "added_by": "system",
        "added_at": "",
        "severity": "normal",
        "space_task": True,
        "auto_task": True,
        "space": space,
        "folder": clean_path_value(folder_row.get("path", "")),
        "folder_source": clean(folder_row.get("source", "")),
        "folder_rank": int(folder_index),
        "space_task_order": int(order_index),
    }
