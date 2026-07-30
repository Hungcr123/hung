# Loaded by FUTURE.server_parts.server_data_pdf_qmdict.03_space_task_auto into the shared Future server runtime namespace.

SPACE_TASK_SPACE_ORDER = ("Space_V", "Space_W", "Space_Q", "Space_P", "Space_S", "Space_L", "Space_PDF", "Space_Picture")
SPACE_TASK_ACTIVE_LIMITS = {
    "Space_V": 2,
    "Space_W": 1,
    "Space_Q": 1,
    "Space_P": 1,
    "Space_S": 1,
    "Space_L": 1,
    "Space_PDF": 1,
    "Space_Picture": 1,
}
SPACE_TASK_SCAN_LIMIT_PER_FOLDER = 900
SPACE_TASK_MAX_FOLDERS = 80
SPACE_TASK_ASSIGNMENT_MAX = 500


def _space_task_settings_rev() -> str:
    # Added 2026-07-10: give Space Task folder saves a monotonic-ish revision beyond second-level timestamps.
    return str(time.time_ns())


def _space_task_absolute_to_relative(value: object) -> str:
    raw = str(value or "").strip().strip("\"'")
    if not raw:
        return ""
    try:
        path = Path(raw)
        if not path.is_absolute():
            return ""
        relative = path.resolve().relative_to(SERVER_DATA_ROOT.resolve()).as_posix()
        return clean_path_value(relative)
    except Exception:
        return ""


def _space_task_normalize_folder(value: object, target_user: str, allow_any_top: bool = True) -> str:
    target_user = normalize_username(target_user)
    absolute_rel = _space_task_absolute_to_relative(value)
    raw = absolute_rel or clean_path_value(value)
    if not raw or not target_user:
        return ""
    parts = [part for part in raw.split("/") if part]
    if not parts:
        return ""
    top = parts[0]
    top_lower = top.lower()
    if top_lower == target_user.lower():
        normalized = "/".join([target_user, *parts[1:]])
    elif top_lower == "common":
        normalized = "/".join(["common", *parts[1:]])
    elif allow_any_top and (SERVER_DATA_ROOT / top).is_dir():
        normalized = raw
    else:
        normalized = f"{target_user}/{raw}"
    # Added 2026-07-24: a learner Vault placement is a valid Space Task folder
    # even when it has no physical directory. Its entries remain SQLite-backed.
    vault_matcher = globals().get("server_database_vault_match")
    if server_data_path_top(normalized) == target_user.lower() and callable(vault_matcher):
        virtual = vault_matcher(normalized)
        if (
            isinstance(virtual, dict)
            and clean(virtual.get("vault_folder_id", ""))
            and not clean_path_value(virtual.get("suffix", ""))
            and clean_path_value(virtual.get("path", "")).lower() == normalized.lower()
        ):
            return clean_path_value(virtual.get("path", normalized))
    try:
        folder = safe_server_data_path(normalized, target_user, admin=True)
    except Exception:
        return ""
    if not folder.is_dir():
        return ""
    return server_data_relative(folder)


def normalize_space_task_folders(value: object, target_user: str, allow_any_top: bool = True) -> list[str]:
    if isinstance(value, str):
        rows = re.split(r"[\r\n,;]+", value)
    elif isinstance(value, (list, tuple, set)):
        rows = list(value)
    else:
        rows = []
    folders = []
    seen = set()
    for item in rows:
        folder = _space_task_normalize_folder(item, target_user, allow_any_top=allow_any_top)
        key = folder.lower()
        if folder and key not in seen:
            seen.add(key)
            folders.append(folder)
        if len(folders) >= SPACE_TASK_MAX_FOLDERS:
            break
    return folders


def _space_task_clean_saved_folders(value: object) -> list[str]:
    # Added 2026-07-10: read already-normalized Space Task folders without touching disk on every payload build.
    rows = value if isinstance(value, list) else []
    folders = []
    seen = set()
    for item in rows:
        folder = clean_path_value(item)
        key = folder.lower()
        if folder and key not in seen:
            seen.add(key)
            folders.append(folder)
        if len(folders) >= SPACE_TASK_MAX_FOLDERS:
            break
    return folders


def space_task_settings_for_user(target_user: str) -> dict:
    target_user = normalize_username(target_user)
    if not target_user:
        return {"preferred_folders": [], "updated_at": "", "updated_by": "", "updated_rev": ""}
    with LESSON_TASK_LOCK:
        record = read_lesson_task_user_locked(target_user)
        settings = record.get("space_task") if isinstance(record, dict) and isinstance(record.get("space_task"), dict) else {}
    folders = _space_task_clean_saved_folders(settings.get("preferred_folders", []))
    return {
        "preferred_folders": folders,
        "updated_at": clean(settings.get("updated_at", "")),
        "updated_by": normalize_username(settings.get("updated_by", "")),
        "updated_rev": clean(settings.get("updated_rev", "")),
    }


def _space_task_assignment_key(path: object) -> str:
    return clean_path_value(path).lower()


def _space_task_assignment_identity(item: object) -> tuple[str, str]:
    if isinstance(item, dict):
        path = clean_path_value(item.get("path", ""))
    else:
        path = clean_path_value(item)
    row_key = _space_task_assignment_key(path)
    return row_key, path


def _space_task_clean_assignment_map(value: object) -> dict:
    source = value if isinstance(value, dict) else {}
    rows = {}
    for key, item in source.items():
        path = ""
        assigned_at = ""
        if isinstance(item, dict):
            path = clean_path_value(item.get("path", ""))
            assigned_at = clean(item.get("assigned_at", item.get("at", "")))
        else:
            path = clean_path_value(key)
            assigned_at = clean(item)
        row_key = _space_task_assignment_key(path or key)
        if path and assigned_at and row_key:
            rows[row_key] = {"path": path, "assigned_at": assigned_at}
        if len(rows) >= SPACE_TASK_ASSIGNMENT_MAX:
            break
    return rows


def space_task_assignments_for_active_paths(target_user: str, active_paths: object) -> dict:
    target_user = normalize_username(target_user)
    if isinstance(active_paths, str):
        raw_paths = [active_paths]
    elif isinstance(active_paths, (list, tuple, set)):
        raw_paths = list(active_paths)
    else:
        raw_paths = []
    active = []
    active_seen = set()
    for item in raw_paths:
        key, path = _space_task_assignment_identity(item)
        if path and key and key not in active_seen:
            active_seen.add(key)
            active.append({"path": path})
        if len(active) >= SPACE_TASK_ASSIGNMENT_MAX:
            break
    if not target_user:
        return {}
    now = utc_timestamp()
    with LESSON_TASK_LOCK:
        record = read_lesson_task_user_locked(target_user)
        if not isinstance(record.get("tasks"), list):
            record["tasks"] = []
        space_task = record.get("space_task") if isinstance(record.get("space_task"), dict) else {}
        existing = _space_task_clean_assignment_map(space_task.get("assigned", {}))
        next_assigned = {}
        for item in active:
            key, path = _space_task_assignment_identity(item)
            row = existing.get(key, {})
            assigned_at = clean(row.get("assigned_at", "")) or now
            next_assigned[key] = {"path": path, "assigned_at": assigned_at}
        changed = next_assigned != existing
        if changed:
            space_task["assigned"] = next_assigned
            record["space_task"] = space_task
            write_lesson_task_user_locked(target_user, record)
    return next_assigned


def save_space_task_settings(
    target_user: str,
    folders: object,
    actor_username: str = "",
    allow_any_top: bool = True,
    base_revision: str | None = None,
) -> dict:
    target_user = normalize_username(target_user)
    actor_username = normalize_username(actor_username)
    ok, message = validate_username(target_user)
    if not ok:
        raise RuntimeError(message)
    if not learner_user_exists(target_user):
        raise RuntimeError("User does not exist.")
    preferred = normalize_space_task_folders(folders, target_user, allow_any_top=allow_any_top)
    with LESSON_TASK_LOCK:
        record = read_lesson_task_user_locked(target_user)
        if not isinstance(record.get("tasks"), list):
            record["tasks"] = []
        current_space_task = record.get("space_task") if isinstance(record.get("space_task"), dict) else {}
        current_preferred = _space_task_clean_saved_folders(current_space_task.get("preferred_folders", []))
        current_revision = clean(current_space_task.get("updated_rev", ""))
        if preferred == current_preferred:
            return {
                "preferred_folders": current_preferred,
                "updated_at": clean(current_space_task.get("updated_at", "")),
                "updated_by": normalize_username(current_space_task.get("updated_by", "")),
                "updated_rev": current_revision,
                "changed": False,
            }
        if base_revision is not None and clean(base_revision) != current_revision:
            raise RuntimeError("Space Task folders changed on another device. Refresh and try again.")
        now = utc_timestamp()
        updated_rev = _space_task_settings_rev()
        current_assigned = _space_task_clean_assignment_map(current_space_task.get("assigned", {}))
        record["space_task"] = {
            "preferred_folders": preferred,
            "updated_at": now,
            "updated_by": actor_username,
            "updated_rev": updated_rev,
        }
        if current_assigned and preferred:
            record["space_task"]["assigned"] = current_assigned
        write_lesson_task_user_locked(target_user, record)
    return {
        "preferred_folders": preferred,
        "updated_at": now,
        "updated_by": actor_username,
        "updated_rev": updated_rev,
        "changed": True,
    }


# Added 2026-07-22: atomically remove one Space Task folder group across manual and automatic type buckets.
def remove_space_task_group(
    target_user: str,
    relative_path: str = "",
    task_id: str = "",
    folder_group_key: str = "",
    folder_path: str = "",
    actor_username: str = "",
    base_revision: str | None = None,
) -> dict:
    target_user = normalize_username(target_user)
    actor_username = normalize_username(actor_username)
    ok, message = validate_username(target_user)
    if not ok:
        raise RuntimeError(message)
    wanted_path = clean_path_value(relative_path)
    wanted_id = clean(task_id)
    requested_group_key = clean(folder_group_key).lower()
    requested_folder = clean_path_value(folder_path)
    if not wanted_path and not wanted_id:
        raise RuntimeError("Missing Space Task item.")

    payload_reader = globals().get("space_task_payload_for_user")
    current_payload = payload_reader(target_user, actor_username, include_admin=is_admin_user(actor_username)) if callable(payload_reader) else {}
    current_auto_tasks = current_payload.get("tasks") if isinstance(current_payload, dict) and isinstance(current_payload.get("tasks"), list) else []

    with LESSON_TASK_LOCK:
        record = read_lesson_task_user_locked(target_user)
        manual_tasks = record.get("tasks") if isinstance(record.get("tasks"), list) else []
        current_space_task = record.get("space_task") if isinstance(record.get("space_task"), dict) else {}
        current_revision = clean(current_space_task.get("updated_rev", ""))
        preferred = _space_task_clean_saved_folders(current_space_task.get("preferred_folders", []))
        target_task = None
        for task in [*manual_tasks, *current_auto_tasks]:
            if not isinstance(task, dict):
                continue
            matches_target = (
                clean_path_value(task.get("path", "")).lower() == wanted_path.lower()
                if wanted_path
                else bool(wanted_id and clean(task.get("id", "")) == wanted_id)
            )
            if matches_target:
                target_task = task
                break
        if not target_task:
            raise RuntimeError("Space Task item not found.")

        selected_group = lesson_task_folder_group_metadata(target_task)
        selected_key = clean(selected_group.get("folder_group_key", "")).lower()
        selected_folder_path = clean_path_value(selected_group.get("folder_path", ""))
        if requested_group_key and selected_key and requested_group_key != selected_key:
            raise RuntimeError("Space Task folder group changed. Refresh and try again.")
        if requested_folder and selected_folder_path and requested_folder.lower() != selected_folder_path.lower():
            raise RuntimeError("Space Task folder path changed. Refresh and try again.")

        def same_selected_group(task):
            if not isinstance(task, dict):
                return False
            if not selected_key:
                return (
                    clean_path_value(task.get("path", "")).lower() == wanted_path.lower()
                    if wanted_path
                    else bool(wanted_id and clean(task.get("id", "")) == wanted_id)
                )
            task_group = lesson_task_folder_group_metadata(task)
            task_key = clean(task.get("folder_group_key") or task_group.get("folder_group_key", "")).lower()
            return task_key == selected_key

        removed_manual = [task for task in manual_tasks if same_selected_group(task)]
        remaining_manual = [task for task in manual_tasks if not same_selected_group(task)]
        removed_auto = [task for task in current_auto_tasks if same_selected_group(task)]
        remaining_auto = [task for task in current_auto_tasks if not same_selected_group(task)]

        removed_folders = []
        if selected_key:
            for candidate in preferred:
                candidate_group = lesson_task_folder_group_metadata({"path": wanted_path, "folder": candidate})
                candidate_key = clean(candidate_group.get("folder_group_key", "")).lower()
                candidate_path = clean_path_value(candidate_group.get("folder_path", ""))
                if candidate_key == selected_key or (selected_folder_path and candidate_path.lower() == selected_folder_path.lower()):
                    removed_folders.append(candidate)
        if removed_folders and base_revision is not None and clean(base_revision) != current_revision:
            raise RuntimeError("Space Task folders changed on another device. Refresh and try again.")
        remaining_folders = [folder for folder in preferred if folder not in removed_folders]

        matching_tasks = [*removed_manual, *removed_auto]
        removed_paths = {clean_path_value(task.get("path", "")).lower() for task in matching_tasks if clean_path_value(task.get("path", ""))}
        removed_prefixes = [folder.lower().rstrip("/") + "/" for folder in removed_folders]
        current_assigned = _space_task_clean_assignment_map(current_space_task.get("assigned", {}))
        remaining_assigned = {
            key: value
            for key, value in current_assigned.items()
            if key not in removed_paths and not any(key.startswith(prefix) for prefix in removed_prefixes)
        }
        if removed_folders:
            next_space_task = {
                "preferred_folders": remaining_folders,
                "updated_at": utc_timestamp(),
                "updated_by": actor_username,
                "updated_rev": _space_task_settings_rev(),
            }
            if remaining_assigned and remaining_folders:
                next_space_task["assigned"] = remaining_assigned
        else:
            next_space_task = dict(current_space_task)
        record["tasks"] = remaining_manual
        record["space_task"] = next_space_task
        write_lesson_task_user_locked(target_user, record)

    removed_rows = []
    removed_seen = set()
    for task in matching_tasks:
        row = {"id": clean(task.get("id", "")), "path": clean_path_value(task.get("path", ""))}
        row_key = ("path", row["path"].lower()) if row["path"] else ("id", row["id"])
        if row_key not in removed_seen:
            removed_seen.add(row_key)
            removed_rows.append(row)
    return {
        "removed": removed_rows[0] if removed_rows else {"id": wanted_id, "path": wanted_path},
        "removed_tasks": removed_rows,
        "removed_count": len(removed_rows),
        **selected_group,
        "space_task": {**next_space_task, "tasks": remaining_auto, "pending": False, "stale": False},
        "space_tasks": remaining_auto,
    }
