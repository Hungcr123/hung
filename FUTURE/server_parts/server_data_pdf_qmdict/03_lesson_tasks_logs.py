# Loaded by FUTURE.server_parts.07_server_data_pdf_qmdict into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def lesson_task_owner_for_path(relative_path: str = "", username: str = "", admin: bool = False) -> str:
    username = normalize_username(username)
    raw = clean_path_value(relative_path)
    if not admin:
        return username
    if not raw:
        return ""
    top = clean(raw.split("/", 1)[0])
    reserved = {"common", "Sound", "Structure", "Picture", "server_log"}
    if top and top not in reserved and (SERVER_DATA_ROOT / top).is_dir():
        return normalize_username(top)
    return ""


# Added 2026-07-22: one canonical folder key drives Space Task ordering, hover metadata, color, and atomic group removal.
def lesson_task_folder_group_metadata(item: dict | None) -> dict:
    source = item if isinstance(item, dict) else {}
    folder_id = clean(source.get("folder_id") or source.get("folderId"))[:240]
    path = clean_path_value(source.get("path") or source.get("normalized_path") or source.get("effective_path"))
    explicit_folder = clean_path_value(source.get("folder_path") or source.get("folder"))
    folder_path = explicit_folder
    if not folder_path and path:
        parts = [part for part in path.split("/") if part]
        if len(parts) >= 3:
            folder_path = "/".join(parts[:-1])
    folder_parts = [part for part in folder_path.split("/") if part]
    if folder_path and len(folder_parts) < 2:
        folder_path = ""
        folder_parts = []
    if folder_path and path:
        folder_prefix = folder_path.lower().rstrip("/") + "/"
        if not path.lower().startswith(folder_prefix):
            folder_path = ""
            folder_parts = []
    folder_name = clean(source.get("folder_name")) or (folder_parts[-1] if folder_parts else "")
    folder_chain = clean_path_value(source.get("folder_chain")) or folder_path
    if folder_id:
        group_key = f"folder-id:{folder_id.lower()}"
    elif folder_path:
        group_key = f"folder-path:{folder_path.lower()}"
    else:
        group_key = ""
    return {
        "folder_id": folder_id,
        "folder_path": folder_path,
        "folder_name": folder_name,
        "folder_chain": folder_chain,
        "folder_group_key": group_key,
        "folder_backed": bool(group_key),
    }

def merged_username_study_row(rows: object, username: str) -> dict:
    wanted = normalize_username(username)
    if not wanted or not isinstance(rows, dict):
        return {}
    merged: dict = {}
    seen_dates: set[str] = set()
    dates: list[str] = []
    for raw_name, raw_row in rows.items():
        if normalize_username(raw_name) != wanted or not isinstance(raw_row, dict):
            continue
        merged["count"] = int(merged.get("count", 0) or 0) + max(0, int(raw_row.get("count", 0) or 0))
        last = clean(raw_row.get("last", ""))
        if last and timestamp_order_key(last) > timestamp_order_key(merged.get("last", "")):
            merged["last"] = last
        for item in raw_row.get("dates") if isinstance(raw_row.get("dates"), list) else []:
            stamp = clean(item)
            if stamp and stamp not in seen_dates:
                seen_dates.add(stamp)
                dates.append(stamp)
        for key, value in raw_row.items():
            if key in {"count", "last", "dates"}:
                continue
            if key not in merged or merged.get(key) in ("", None, [], {}):
                merged[key] = value
    if dates:
        merged["dates"] = dates[-60:]
    return merged

def _clean_lesson_task_assigned_rows(value: object) -> dict:
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
        assignment_key = clean_path_value(key or path).lower()
        if not path or not assigned_at or not assignment_key:
            continue
        current = rows.get(assignment_key)
        if not isinstance(current, dict) or timestamp_order_key(assigned_at) >= timestamp_order_key(current.get("assigned_at", "")):
            rows[assignment_key] = {"path": path, "assigned_at": assigned_at}
    return rows

def _clean_lesson_task_item(item: dict) -> dict | None:
    source = item if isinstance(item, dict) else {}
    path = clean_path_value(source.get("path", ""))
    if not path:
        return None
    out = dict(source)
    out["path"] = path
    if "effective_path" in out:
        out["effective_path"] = clean_path_value(out.get("effective_path", ""))
    if "link_target" in out:
        out["link_target"] = clean_path_value(out.get("link_target", ""))
    if "folder" in out:
        out["folder"] = clean_path_value(out.get("folder", ""))
    if "folder_path" in out:
        out["folder_path"] = clean_path_value(out.get("folder_path", ""))
    if "folder_chain" in out:
        out["folder_chain"] = clean_path_value(out.get("folder_chain", ""))
    if "folder_id" in out:
        out["folder_id"] = clean(out.get("folder_id", ""))[:240]
    if "folder_name" in out:
        out["folder_name"] = clean(out.get("folder_name", ""))
    if "id" in out:
        out["id"] = clean(out.get("id", ""))
    if "name" in out:
        out["name"] = clean(out.get("name", ""))
    if "title" in out:
        out["title"] = clean(out.get("title", ""))
    if "space" in out:
        out["space"] = clean(out.get("space", ""))
    if "added_by" in out:
        out["added_by"] = normalize_username(out.get("added_by", ""))
    if "creator_role" in out:
        out["creator_role"] = lesson_task_creator_role(out)
    if "severity" in out:
        out["severity"] = normalize_lesson_task_severity(out.get("severity", ""))
    if "added_at" in out:
        out["added_at"] = clean(out.get("added_at", ""))
    if "completed_at" in out:
        out["completed_at"] = clean(out.get("completed_at", ""))
    return out

def _merge_lesson_task_item(existing: dict | None, incoming: dict) -> dict:
    if not isinstance(existing, dict):
        return dict(incoming)
    merged = dict(existing)
    for key in ("id", "effective_path", "link_target", "name", "title", "space", "folder", "folder_id", "folder_path", "folder_name", "folder_chain"):
        current = clean_path_value(merged.get(key, "")) if key in {"effective_path", "link_target", "folder", "folder_path", "folder_chain"} else clean(merged.get(key, ""))
        candidate = clean_path_value(incoming.get(key, "")) if key in {"effective_path", "link_target", "folder", "folder_path", "folder_chain"} else clean(incoming.get(key, ""))
        if candidate and not current:
            merged[key] = candidate
    incoming_added_by = normalize_username(incoming.get("added_by", ""))
    if incoming_added_by and not normalize_username(merged.get("added_by", "")):
        merged["added_by"] = incoming_added_by
    current_role = lesson_task_creator_role(merged)
    incoming_role = lesson_task_creator_role(incoming)
    if incoming_role == "admin" and current_role != "admin":
        merged["creator_role"] = "admin"
    elif not clean(merged.get("creator_role", "")) and incoming_role:
        merged["creator_role"] = incoming_role
    current_severity = normalize_lesson_task_severity(merged.get("severity", ""))
    incoming_severity = normalize_lesson_task_severity(incoming.get("severity", ""))
    if incoming_severity == "critical" or (incoming_severity == "high" and current_severity == "normal"):
        merged["severity"] = incoming_severity
    elif not clean(merged.get("severity", "")):
        merged["severity"] = incoming_severity
    incoming_added_at = clean(incoming.get("added_at", ""))
    if incoming_added_at and (not clean(merged.get("added_at", "")) or timestamp_order_key(incoming_added_at) < timestamp_order_key(merged.get("added_at", ""))):
        merged["added_at"] = incoming_added_at
    incoming_completed_at = clean(incoming.get("completed_at", ""))
    if incoming_completed_at and timestamp_order_key(incoming_completed_at) > timestamp_order_key(merged.get("completed_at", "")):
        merged["completed_at"] = incoming_completed_at
    return merged

def _merge_lesson_task_rows(*groups: object) -> list[dict]:
    rows_by_path = {}
    order: list[str] = []
    for group in groups:
        source = group if isinstance(group, list) else []
        for item in source:
            clean_item = _clean_lesson_task_item(item)
            if not clean_item:
                continue
            key = clean_item["path"].lower()
            if key not in rows_by_path:
                order.append(key)
                rows_by_path[key] = clean_item
            else:
                rows_by_path[key] = _merge_lesson_task_item(rows_by_path[key], clean_item)
    return [rows_by_path[key] for key in order][-300:]

def _merge_lesson_task_space_task(existing: object, incoming: object) -> dict:
    assigned = {}
    updated_at = ""
    updated_by = ""
    updated_rev = ""
    preferred_folders: list[str] = []
    preferred_source_key = ("", timestamp_order_key(""))
    for source in (existing if isinstance(existing, dict) else {}, incoming if isinstance(incoming, dict) else {}):
        for key, row in _clean_lesson_task_assigned_rows(source.get("assigned", {})).items():
            current = assigned.get(key)
            if not isinstance(current, dict) or timestamp_order_key(row.get("assigned_at", "")) >= timestamp_order_key(current.get("assigned_at", "")):
                assigned[key] = row
        source_updated_at = clean(source.get("updated_at", ""))
        source_updated_by = normalize_username(source.get("updated_by", ""))
        source_updated_rev = clean(source.get("updated_rev", ""))
        source_key = (source_updated_rev, timestamp_order_key(source_updated_at))
        if source_key >= preferred_source_key:
            # Added 2026-07-10: Space Task folder settings are replace-on-save, so newer settings clear old folders.
            preferred_source_key = source_key
            preferred_seen: set[str] = set()
            preferred_folders = []
            preferred = source.get("preferred_folders") if isinstance(source.get("preferred_folders"), list) else []
            for item in preferred:
                path = clean_path_value(item)
                key = path.lower()
                if path and key not in preferred_seen:
                    preferred_seen.add(key)
                    preferred_folders.append(path)
        if source_key >= (updated_rev, timestamp_order_key(updated_at)):
            updated_rev = source_updated_rev
            updated_at = source_updated_at
            updated_by = source_updated_by or updated_by
        elif source_updated_by and not updated_by:
            updated_by = source_updated_by
    if not preferred_folders and not assigned and not updated_at and not updated_by:
        return {}
    out = {
        "preferred_folders": preferred_folders[:80],
        "updated_at": updated_at,
        "updated_by": updated_by,
    }
    if updated_rev:
        out["updated_rev"] = updated_rev
    if assigned:
        out["assigned"] = dict(list(assigned.items())[-500:])
    return out

def _merge_lesson_task_record(existing: object, incoming: object) -> dict:
    current = existing if isinstance(existing, dict) else {}
    source = incoming if isinstance(incoming, dict) else {}
    out = {
        "tasks": _merge_lesson_task_rows(current.get("tasks"), source.get("tasks")),
    }
    space_task = _merge_lesson_task_space_task(current.get("space_task"), source.get("space_task"))
    if space_task:
        out["space_task"] = space_task
    return out

def _clean_lesson_task_store(payload: object) -> dict:
    source = payload if isinstance(payload, dict) else {}
    by_user = source.get("by_user") if isinstance(source.get("by_user"), dict) else {}
    out = {"version": 1, "updated_at": clean(source.get("updated_at", "")), "by_user": {}}
    for username, record in by_user.items():
        clean_user = normalize_username(username)
        if not clean_user or not isinstance(record, dict):
            continue
        out["by_user"][clean_user] = _merge_lesson_task_record(out["by_user"].get(clean_user), record)
    return out

def _merge_notice_stamp_map(*groups: object) -> dict:
    out = {}
    for group in groups:
        source = group if isinstance(group, dict) else {}
        for raw_id, raw_stamp in source.items():
            notice_id = clean(raw_id)
            stamp = clean(raw_stamp)
            if notice_id and stamp and timestamp_order_key(stamp) >= timestamp_order_key(out.get(notice_id, "")):
                out[notice_id] = stamp
    return out

def _merge_lesson_task_notice_rows(*groups: object) -> list[dict]:
    rows_by_id = {}
    order: list[str] = []
    for group in groups:
        source = group if isinstance(group, list) else []
        for item in source:
            if not isinstance(item, dict):
                continue
            notice_id = clean(item.get("id", ""))
            if not notice_id:
                continue
            candidate = dict(item)
            current = rows_by_id.get(notice_id)
            if not isinstance(current, dict):
                rows_by_id[notice_id] = candidate
                order.append(notice_id)
                continue
            merged = dict(current)
            for key, value in candidate.items():
                if value not in ("", None, [], {}):
                    merged[key] = value
            created_at = clean(candidate.get("created_at", ""))
            if created_at and (not clean(current.get("created_at", "")) or timestamp_order_key(created_at) < timestamp_order_key(current.get("created_at", ""))):
                merged["created_at"] = created_at
            rows_by_id[notice_id] = merged
    return [rows_by_id[key] for key in order][-200:]

def _merge_lesson_task_notice_record(existing: object, incoming: object) -> dict:
    current = existing if isinstance(existing, dict) else {}
    source = incoming if isinstance(incoming, dict) else {}
    out = {
        "notices": _merge_lesson_task_notice_rows(current.get("notices"), source.get("notices")),
        "read": _merge_notice_stamp_map(current.get("read"), source.get("read")),
    }
    seen = _merge_notice_stamp_map(current.get("seen"), source.get("seen"))
    if seen:
        out["seen"] = seen
    return out

def _clean_lesson_task_notice_store(payload: object) -> dict:
    source = payload if isinstance(payload, dict) else {}
    by_user = source.get("by_user") if isinstance(source.get("by_user"), dict) else {}
    out = {"version": 1, "by_user": {}}
    for username, record in by_user.items():
        clean_user = normalize_username(username)
        if not clean_user or not isinstance(record, dict):
            continue
        out["by_user"][clean_user] = _merge_lesson_task_notice_record(out["by_user"].get(clean_user), record)
    return out


def read_lesson_tasks_locked() -> dict:
    return _clean_lesson_task_store(server_database_load_all_lesson_task_records())


# Added 2026-07-20: serialize one learner's task mutations without blocking independent SQLite group commits.
def lesson_task_user_lock(target_user: str):
    cache_key = normalize_username(target_user).lower()
    with LESSON_TASKS_RAM_CACHE_LOCK:
        locks = globals().setdefault("LESSON_TASKS_USER_LOCKS", {})
        lock = locks.get(cache_key)
        if lock is None:
            lock = threading.RLock()
            locks[cache_key] = lock
        return lock


# Added 2026-07-20: hot task reads hydrate only the requested user's SQLite row.
def read_lesson_task_user_locked(target_user: str) -> dict:
    target_user = normalize_username(target_user)
    if not target_user:
        return {"tasks": []}
    cache_key = target_user.lower()
    with LESSON_TASKS_RAM_CACHE_LOCK:
        cache = globals().setdefault("LESSON_TASKS_USER_RECORD_CACHE", {})
        cached = cache.get(cache_key) if isinstance(cache, dict) else None
        if isinstance(cached, dict) and isinstance(cached.get("record"), dict):
            cached["at"] = time.time()
            return cached["record"]
    loaded = server_database_load_lesson_task_record(target_user)
    record = _merge_lesson_task_record({}, loaded.get("record"))
    revision = max(0, space_w_int(loaded.get("revision", 0), 0))
    with LESSON_TASKS_RAM_CACHE_LOCK:
        cache = globals().setdefault("LESSON_TASKS_USER_RECORD_CACHE", {})
        cache[cache_key] = {"record": record, "revision": revision, "at": time.time()}
        revisions = globals().setdefault("LESSON_TASKS_USER_REVISIONS", {})
        revisions[cache_key] = revision
    return record


def lesson_tasks_user_revision(target_user: str = "", bump: bool = False) -> int:
    target_user = normalize_username(target_user).lower()
    if not target_user:
        return 0
    with LESSON_TASKS_RAM_CACHE_LOCK:
        revisions = globals().setdefault("LESSON_TASKS_USER_REVISIONS", {})
        current = int(revisions.get(target_user, 0) or 0)
        if bump:
            current += 1
            revisions[target_user] = current
        return current


# Added 2026-07-20: ACK only after the affected user's compact task row commits in SQLite.
def write_lesson_task_user_locked(target_user: str, record: dict | None = None) -> dict:
    target_user = normalize_username(target_user)
    cleaned = _merge_lesson_task_record({}, record)
    result = server_database_write_lesson_task_record(target_user, cleaned)
    revision = max(0, space_w_int(result.get("revision", 0), 0))
    with LESSON_TASKS_RAM_CACHE_LOCK:
        cache_key = target_user.lower()
        cache = globals().setdefault("LESSON_TASKS_USER_RECORD_CACHE", {})
        cache[cache_key] = {"record": cleaned, "revision": revision, "at": time.time()}
        revisions = globals().setdefault("LESSON_TASKS_USER_REVISIONS", {})
        revisions[cache_key] = revision
    return cleaned


def delete_lesson_task_user_locked(target_user: str) -> bool:
    target_user = normalize_username(target_user)
    removed = server_database_delete_lesson_task_record(target_user)
    with LESSON_TASKS_RAM_CACHE_LOCK:
        cache_key = target_user.lower()
        cache = globals().setdefault("LESSON_TASKS_USER_RECORD_CACHE", {})
        cache.pop(cache_key, None)
        revisions = globals().setdefault("LESSON_TASKS_USER_REVISIONS", {})
        revisions[cache_key] = int(revisions.get(cache_key, 0) or 0) + 1
    return removed


def write_lesson_tasks_locked(payload: dict, target_user: str = "") -> None:
    cleaned = _clean_lesson_task_store(payload)
    if target_user:
        write_lesson_task_user_locked(target_user, cleaned.get("by_user", {}).get(normalize_username(target_user), {}))
        return
    for username, record in cleaned.get("by_user", {}).items():
        write_lesson_task_user_locked(username, record)


def write_lesson_tasks_clean_payload_locked(payload: dict, target_user: str = "") -> None:
    write_lesson_tasks_locked(payload, target_user)


def flush_lesson_tasks_ram_cache(force: bool = False) -> None:
    with LESSON_TASKS_RAM_CACHE_LOCK:
        row = LESSON_TASKS_RAM_CACHE.get("store")
        if not isinstance(row, dict) or not bool(row.get("dirty")) or not isinstance(row.get("payload"), dict):
            return
        now = time.time()
        if not force and now - float(row.get("last_flush", 0.0) or 0.0) < LESSON_TASKS_WRITEBEHIND_FLUSH_SECONDS:
            return
        payload = _clean_lesson_task_store(row.get("payload"))
        version = int(row.get("version", LESSON_TASKS_RAM_CACHE.get("version", 0)) or 0)
    SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    out = {
        "version": 1,
        "updated_at": utc_timestamp(),
        "by_user": payload.get("by_user", {}),
    }
    atomic_write_json(LESSON_TASKS_FILE, out, indent=2)
    with LESSON_TASKS_RAM_CACHE_LOCK:
        if int(LESSON_TASKS_RAM_CACHE.get("version", 0) or 0) != version:
            return
        LESSON_TASKS_RAM_CACHE["store"] = {
            "payload": out,
            "dirty": False,
            "version": version,
            "last_flush": time.time(),
            "at": time.time(),
        }


def flush_lesson_task_notices_ram_cache(force: bool = False) -> None:
    with LESSON_TASK_NOTICES_RAM_CACHE_LOCK:
        row = LESSON_TASK_NOTICES_RAM_CACHE.get("store")
        if not isinstance(row, dict) or not bool(row.get("dirty")) or not isinstance(row.get("payload"), dict):
            return
        now = time.time()
        if not force and now - float(row.get("last_flush", 0.0) or 0.0) < LESSON_TASKS_WRITEBEHIND_FLUSH_SECONDS:
            return
        payload = _clean_lesson_task_notice_store(row.get("payload"))
        version = int(row.get("version", LESSON_TASK_NOTICES_RAM_CACHE.get("version", 0)) or 0)
    SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    atomic_write_json(LESSON_TASK_NOTICES_FILE, payload, indent=2)
    with LESSON_TASK_NOTICES_RAM_CACHE_LOCK:
        if int(LESSON_TASK_NOTICES_RAM_CACHE.get("version", 0) or 0) != version:
            return
        LESSON_TASK_NOTICES_RAM_CACHE["store"] = {
            "payload": payload,
            "dirty": False,
            "version": version,
            "last_flush": time.time(),
            "at": time.time(),
        }


def lesson_tasks_runtime_signature(target_user: str = "") -> tuple:
    normalized_user = normalize_username(target_user)
    if normalized_user:
        return ("user", normalized_user.lower(), lesson_tasks_user_revision(normalized_user))
    with LESSON_TASKS_RAM_CACHE_LOCK:
        row = LESSON_TASKS_RAM_CACHE.get("store")
        version = int(LESSON_TASKS_RAM_CACHE.get("version", 0) or 0)
        dirty = bool((row or {}).get("dirty")) if isinstance(row, dict) else False
        updated_at = clean((row or {}).get("payload", {}).get("updated_at", "")) if isinstance((row or {}).get("payload"), dict) else ""
    return ("ram", version, dirty, updated_at)


def lesson_task_notices_user_revision(target_user: str = "", bump: bool = False) -> int:
    target_user = normalize_username(target_user).lower()
    if not target_user:
        return 0
    with LESSON_TASK_NOTICES_RAM_CACHE_LOCK:
        revisions = globals().setdefault("LESSON_TASK_NOTICES_USER_REVISIONS", {})
        current = int(revisions.get(target_user, 0) or 0)
        if bump:
            current += 1
            revisions[target_user] = current
        return current


def lesson_task_notices_runtime_signature(target_user: str = "") -> tuple:
    normalized_user = normalize_username(target_user)
    if normalized_user:
        return ("user", normalized_user.lower(), lesson_task_notices_user_revision(normalized_user))
    with LESSON_TASK_NOTICES_RAM_CACHE_LOCK:
        row = LESSON_TASK_NOTICES_RAM_CACHE.get("store")
        version = int(LESSON_TASK_NOTICES_RAM_CACHE.get("version", 0) or 0)
        dirty = bool((row or {}).get("dirty")) if isinstance(row, dict) else False
        updated_at = clean((row or {}).get("payload", {}).get("updated_at", "")) if isinstance((row or {}).get("payload"), dict) else ""
    return ("ram", version, dirty, updated_at)


def start_lesson_tasks_writebehind_flusher() -> None:
    global LESSON_TASKS_WRITEBEHIND_STARTED
    if LESSON_TASKS_WRITEBEHIND_STARTED:
        return
    LESSON_TASKS_WRITEBEHIND_STARTED = True

    def _runner() -> None:
        while not SERVER_STATE.get("shutdown_requested"):
            time.sleep(0.75)
            try:
                flush_lesson_tasks_ram_cache(False)
                flush_lesson_task_notices_ram_cache(False)
            except Exception:
                pass
        try:
            flush_lesson_tasks_ram_cache(True)
            flush_lesson_task_notices_ram_cache(True)
        except Exception:
            pass

    threading.Thread(target=_runner, daemon=True, name="future-lesson-task-writebehind").start()


atexit.register(lambda: flush_lesson_tasks_ram_cache(True))
atexit.register(lambda: flush_lesson_task_notices_ram_cache(True))


def lesson_task_id(username: str, relative_path: str, file_id: str = "") -> str:
    stable_id = clean(file_id)[:240]
    source = f"id:{stable_id.lower()}" if stable_id.lower().startswith("ftg-lesson-") else clean_path_value(relative_path).lower()
    digest = hashlib.sha1(f"{normalize_username(username).lower()}|{source}".encode("utf-8")).hexdigest()[:18]
    return f"task-{digest}"


def normalize_lesson_task_severity(value: str = "") -> str:
    raw = clean(value).lower()
    if raw in {"critical", "high", "normal"}:
        return raw
    if raw in {"urgent", "danger", "red"}:
        return "critical"
    if raw in {"important", "medium", "warning", "warn"}:
        return "high"
    return "normal"


def lesson_task_creator_role(item: dict) -> str:
    source = item if isinstance(item, dict) else {}
    role = clean(
        source.get("creator_role", source.get("created_by_role", source.get("source", source.get("origin", ""))))
    ).lower()
    if role in {"space_task", "space-task", "auto", "system"}:
        return "space_task"
    if role in {"user", "learner", "student", "self", "personal"}:
        return "user"
    return "admin"


def lesson_task_file_info(raw_path: str, target_user: str, file_id: str = "") -> dict:
    # Updated 2026-07-22: task identity follows lesson_id to the current active package; path is only a locator/legacy alias.
    raw_path = clean_path_value(raw_path)
    target_user = normalize_username(target_user)
    if not raw_path:
        return {}
    top = raw_path.split("/", 1)[0].lower()
    manifest_entry = None
    resolved_path = raw_path
    if top in {"common", target_user.lower()}:
        manifest_entry = server_data_manifest_file_entry(raw_path)
    requested_id = clean(file_id)[:240]
    if not isinstance(manifest_entry, dict) and requested_id.lower().startswith("ftg-lesson-"):
        current_path_reader = globals().get("server_database_lesson_current_path")
        current_path = clean_path_value(current_path_reader(requested_id)) if callable(current_path_reader) else ""
        current_top = current_path.split("/", 1)[0].lower() if current_path else ""
        if current_top in {"common", target_user.lower()}:
            current_entry = server_data_manifest_file_entry(current_path)
            if isinstance(current_entry, dict):
                resolved_path = current_path
                manifest_entry = current_entry
    if isinstance(manifest_entry, dict) and is_lesson_file(server_data_manifest_path(resolved_path)):
        link_target = clean_path_value(manifest_entry.get("link_target", ""))
        effective_path = link_target or resolved_path
        effective_entry = server_data_manifest_file_entry(effective_path) if link_target else manifest_entry
        return {
            "target": server_data_manifest_path(resolved_path),
            "effective_target": server_data_manifest_path(effective_path),
            "target_path": resolved_path,
            "effective_path": effective_path,
            "original_path": raw_path if raw_path.lower() != resolved_path.lower() else "",
            "link_target": link_target,
            "file_exists": True,
            "manifest_entry": effective_entry if isinstance(effective_entry, dict) else manifest_entry,
            "from_manifest": True,
        }
    cache_user = "" if top == "common" else target_user
    cache_key = f"{cache_user}|{raw_path.lower()}"
    now = time.time()
    cache = globals().setdefault("LESSON_TASK_FILE_INFO_CACHE", {})
    lock = globals().setdefault("LESSON_TASK_FILE_INFO_CACHE_LOCK", threading.RLock())
    with lock:
        row = cache.get(cache_key) if isinstance(cache, dict) else None
        if isinstance(row, dict) and now - float(row.get("at", 0.0) or 0.0) < 2.0:
            info = row.get("info")
            if isinstance(info, dict):
                return dict(info)
    try:
        target = safe_server_data_path(raw_path, target_user, admin=True)
    except Exception:
        target = None
    effective_target = None
    link_payload = {}
    if target:
        try:
            link_payload = read_server_data_link_payload(target)
            effective_target = server_data_effective_file_path(target, username=target_user, admin=True)
        except Exception:
            effective_target = target
    file_exists = bool(effective_target and effective_target.is_file() and is_lesson_file(effective_target))
    fallback_manifest_entry = server_data_manifest_entry(effective_target) if file_exists else None
    info = {
        "target": target,
        "effective_target": effective_target,
        "target_path": server_data_relative(target) if target else raw_path,
        "effective_path": server_data_relative(effective_target) if effective_target else "",
        "link_target": clean_path_value(link_payload.get("target", "")),
        "file_exists": file_exists,
        "manifest_entry": fallback_manifest_entry if isinstance(fallback_manifest_entry, dict) else {},
    }
    with lock:
        if isinstance(cache, dict):
            cache[cache_key] = {"info": dict(info), "at": now}
            if len(cache) > 512:
                ordered = sorted(cache.items(), key=lambda item: float((item[1] or {}).get("at", 0.0) or 0.0))
                for old_key, _old_value in ordered[:128]:
                    cache.pop(old_key, None)
    return info


# Added 2026-07-30: task cards only need structural fields already validated by the manifest, not a lesson decode.
def lesson_task_file_meta_from_manifest(manifest_entry: dict | None, fallback_path: Path | None = None) -> dict:
    source = manifest_entry if isinstance(manifest_entry, dict) else {}
    if not source or clean(source.get("type", "")).lower() != "file":
        return {}
    meta = {
        key: source.get(key)
        for key in (
            "lesson_id", "file_id", "nodes", "questions", "direct_questions", "total_nodes", "paragraphs",
            "sentences", "normal_sentences", "train_sentences", "mime_type", "document_id", "asset_id",
        )
        if source.get(key) is not None
    }
    meta["title"] = clean(source.get("title") or source.get("name")) or (fallback_path.stem if fallback_path else "")
    return meta


def lesson_task_completion(
    relative_path: str,
    target_user: str,
    file_meta: dict | None = None,
    effective_target: Path | None = None,
) -> dict:
    target_user = normalize_username(target_user)
    raw = clean_path_value(relative_path)
    if not raw:
        return {"completed": False, "count": 0, "last": ""}
    try:
        if not raw:
            return {"completed": False, "count": 0, "last": ""}
        target = safe_server_data_path(raw, target_user, admin=True)
        if effective_target is not None:
            effective = Path(effective_target)
        else:
            effective = server_data_effective_file_path(target, username=target_user, admin=True)
            if not effective.is_file() or not is_lesson_file(effective):
                return {"completed": False, "count": 0, "last": ""}
        meta = file_meta if isinstance(file_meta, dict) else cached_lesson_file_metadata(effective)
        study = meta.get("study") if isinstance(meta.get("study"), dict) else {}
        log_paths = [raw, server_data_relative(target), server_data_relative(effective)]
        users = study.get("users", {})
        mine = merged_username_study_row(users, target_user)
        admins = study.get("admins", {})
        admin_mine = merged_username_study_row(admins, target_user)
        log_mine = learning_completion_user_row_for_paths(log_paths, username=target_user, admin=True)
        count = max(
            int(mine.get("count", 0) or 0) if isinstance(mine, dict) else 0,
            int(admin_mine.get("count", 0) or 0) if isinstance(admin_mine, dict) else 0,
            int(log_mine.get("count", 0) or 0) if isinstance(log_mine, dict) else 0,
        )
        last = timestamp_latest_text(
            clean(mine.get("last", "")) if isinstance(mine, dict) else "",
            clean(admin_mine.get("last", "")) if isinstance(admin_mine, dict) else "",
            clean(log_mine.get("last", "")) if isinstance(log_mine, dict) else "",
        )
        return {"completed": count > 0, "count": count, "last": last}
    except Exception:
        return {"completed": False, "count": 0, "last": ""}


# Added 2026-07-20: reuse summarize_lesson_study output instead of scanning completion state twice per task.
def lesson_task_completion_from_study(
    study: dict | None = None,
    meta: dict | None = None,
    target_user: str = "",
    include_admin: bool = False,
    canonical_lesson_id: str = "",
) -> dict:
    source = study if isinstance(study, dict) else {}
    progress = source.get("progress") if isinstance(source.get("progress"), dict) else {}
    meta_source = meta if isinstance(meta, dict) else {}
    meta_study = meta_source.get("study") if isinstance(meta_source.get("study"), dict) else {}
    meta_user = merged_username_study_row(meta_study.get("users", {}), target_user)
    meta_admin = merged_username_study_row(meta_study.get("admins", {}), target_user)
    canonical = clean(canonical_lesson_id).lower().startswith("ftg-lesson-")
    count = max(
        0,
        space_w_int(source.get("mine", 0), 0),
        space_w_int(source.get("admin_mine", 0), 0) if include_admin else 0,
        0 if canonical else space_w_int(meta_user.get("count", 0), 0),
        0 if canonical else space_w_int(meta_admin.get("count", 0), 0),
    )
    total = max(0, space_w_int(progress.get("total", 0), 0))
    done = max(0, space_w_int(progress.get("done", 0), 0))
    # Added 2026-07-28: an identified active run always outranks lifetime completion history.
    active_run_value = progress.get("activeRun", progress.get("active_run"))
    active_run = active_run_value if isinstance(active_run_value, dict) else {}
    active_in_progress = bool(
        active_run_value is True
        or progress.get("in_progress")
        or progress.get("active_run") is True
        or active_run.get("active")
        or active_run.get("in_progress")
    )
    progress_completed = bool(
        not active_in_progress
        and (
            progress.get("completed")
            or (total and done >= total)
            or max(0, space_w_int(progress.get("percent", 0), 0)) >= 100
        )
    )
    progress_only_completion = bool(progress_completed and count <= 0)
    if progress_completed and count <= 0:
        count = 1
    last = timestamp_latest_text(
        clean(source.get("mine_last", "")),
        clean(source.get("admin_mine_last", "")) if include_admin else "",
        clean(meta_user.get("last", "")),
        clean(meta_admin.get("last", "")),
        clean(progress.get("updatedAt") or progress.get("savedAt")) if progress_only_completion else "",
    )
    return {"completed": bool(count > 0 and not active_in_progress), "count": count, "last": last}


def normalize_lesson_task(
    item: dict,
    target_user: str,
    viewer_username: str = "",
    progress_index: dict[tuple[str, str], dict] | None = None,
    time_index: dict[str, dict] | None = None,
    include_admin: bool = False,
    viewer_progress_index: dict[tuple[str, str], dict] | None = None,
    viewer_time_index: dict[str, dict] | None = None,
) -> dict | None:
    source = item if isinstance(item, dict) else {}
    raw_path = clean_path_value(source.get("path", ""))
    if not raw_path:
        return None
    requested_file_id = clean(source.get("lesson_id") or source.get("file_id"))[:240]
    file_info = lesson_task_file_info(raw_path, target_user, requested_file_id)
    target = file_info.get("target")
    effective_target = file_info.get("effective_target")
    file_exists = bool(file_info.get("file_exists"))
    effective_path = clean_path_value(file_info.get("effective_path", ""))
    completion = {"completed": False, "count": 0, "last": ""}
    title = clean(source.get("title", ""))
    study = {}
    meta = {}
    name = clean(source.get("name", "")) or Path(raw_path).name
    added_by = normalize_username(source.get("added_by", source.get("created_by", "")))
    creator_role = lesson_task_creator_role(source)
    is_space_task = creator_role == "space_task" or truthy(source.get("space_task", source.get("auto_task", False)), False)
    viewer_username = normalize_username(viewer_username)
    viewer_is_admin = bool(viewer_username and is_admin_user(viewer_username))
    can_remove = bool(
        viewer_is_admin
        or (
            viewer_username
            and viewer_username == normalize_username(target_user)
        )
    )
    if file_exists and effective_target:
        try:
            meta = lesson_task_file_meta_from_manifest(file_info.get("manifest_entry"), effective_target)
            if not meta:
                meta = cached_lesson_file_metadata(effective_target, manifest_entry=file_info.get("manifest_entry"))
            canonical_file_id = clean(
                requested_file_id
                or meta.get("lesson_id", "")
                or meta.get("file_id", "")
                or (file_info.get("manifest_entry") or {}).get("lesson_id", "")
                or (file_info.get("manifest_entry") or {}).get("file_id", "")
            )[:240]
            title = title or clean(meta.get("title", "")) or effective_target.stem
            study = summarize_lesson_study(
                effective_target,
                target_user or viewer_username,
                progress_index,
                time_index,
                include_admin=include_admin,
                progress_relative_path=effective_path or raw_path,
                path_is_effective=True,
                progress_relative_paths=[raw_path, effective_path],
                strict_progress_paths=True,
                file_meta=meta,
                lesson_id=canonical_file_id,
            )
            completion = lesson_task_completion_from_study(
                study,
                meta,
                target_user,
                include_admin=include_admin,
                canonical_lesson_id=canonical_file_id,
            )
            if include_admin and viewer_is_admin and viewer_username and viewer_username != normalize_username(target_user):
                viewer_study = summarize_lesson_study(
                    effective_target,
                    viewer_username,
                    viewer_progress_index,
                    viewer_time_index,
                    include_admin=True,
                    progress_relative_path=effective_path or raw_path,
                    path_is_effective=True,
                    progress_relative_paths=[raw_path, effective_path],
                    strict_progress_paths=True,
                    file_meta=meta,
                    lesson_id=canonical_file_id,
                )
                viewer_progress = viewer_study.get("progress") if isinstance(viewer_study.get("progress"), dict) else {}
                viewer_admin_count = max(
                    0,
                    int(viewer_study.get("admin_mine", 0) or 0),
                    int(viewer_study.get("mine", 0) or 0),
                )
                if viewer_progress:
                    study["admin_progress"] = viewer_progress
                    study["admin_progress_user"] = viewer_username
                    study["admin_time"] = viewer_study.get("time", {})
                    study["admin_time_seconds"] = int(viewer_study.get("time_seconds", 0) or 0)
                if viewer_admin_count:
                    study["admin_progress_mine"] = viewer_admin_count
                    study["admin_progress_mine_last"] = clean(viewer_study.get("admin_mine_last") or viewer_study.get("mine_last") or viewer_study.get("last", ""))
                    study["admin_progress_completed"] = True
            manifest_entry = file_info.get("manifest_entry") if isinstance(file_info.get("manifest_entry"), dict) else {}
            name = clean(manifest_entry.get("name", "")) or (target.name if target else effective_target.name)
        except Exception:
            pass
    else:
        completion = lesson_task_completion(effective_path or raw_path, target_user)
    if not file_exists and not completion.get("completed") and effective_path and effective_path.lower() != raw_path.lower():
        link_completion = lesson_task_completion(raw_path, target_user)
        if link_completion.get("completed") or int(link_completion.get("count", 0) or 0) > int(completion.get("count", 0) or 0):
            completion = link_completion
    file_id = clean(source.get("lesson_id") or source.get("file_id") or meta.get("lesson_id") or meta.get("file_id"))[:240]
    if not file_id:
        alias_reader = globals().get("server_database_lesson_file_id_for_path")
        file_id = clean(alias_reader(effective_path or raw_path))[:240] if callable(alias_reader) else ""
    manifest_entry = file_info.get("manifest_entry") if isinstance(file_info.get("manifest_entry"), dict) else {}
    normalized_path = clean_path_value(file_info.get("target_path", "")) or raw_path
    extension = clean(manifest_entry.get("extension", "")) or Path(effective_path or raw_path).suffix
    lower_extension = extension.lower()
    lower_locator = (effective_path or normalized_path).lower()
    is_pdf = bool(lower_extension == ".pdf" or lower_locator.endswith(".space_pdf"))
    is_picture = bool(lower_locator.endswith(".space_picture"))
    package_backed = bool(is_pdf or is_picture or lower_locator.endswith((".space_pdf", ".space_picture")))
    file_type = "pdf" if is_pdf else ("picture" if is_picture else (lower_extension.lstrip(".") or "lesson"))
    mime_type = clean(meta.get("mime_type") or manifest_entry.get("mime_type"))
    if not mime_type:
        mime_type = "application/pdf" if is_pdf else ("image/*" if is_picture else "application/octet-stream")
    source_type = "package" if package_backed else "lesson"
    open_action = "space_pdf" if is_pdf else ("space_picture" if is_picture else "lesson")
    document_id = clean(meta.get("document_id") or meta.get("asset_id") or manifest_entry.get("document_id") or manifest_entry.get("asset_id"))
    package_path = normalized_path if package_backed else ""
    # Added 2026-07-24: Space Task cards must retain the selected folder/link
    # locator for Lesson Vault focus while canonical bytes stay in effective_path.
    display_path = raw_path if is_space_task else normalized_path
    folder_group = lesson_task_folder_group_metadata({**source, "path": display_path})
    return {
        "id": clean(source.get("id", "")) or lesson_task_id(target_user, raw_path, file_id),
        "lesson_id": file_id if file_id.lower().startswith("ftg-lesson-") else "",
        "file_id": file_id if file_id.lower().startswith("ftg-lesson-") else "",
        "path": display_path,
        "normalized_path": display_path,
        "canonical_path": normalized_path,
        "effective_path": effective_path,
        "original_path": clean_path_value(file_info.get("original_path", "")),
        "link_target": clean_path_value(file_info.get("link_target", "")),
        "filename": name or Path(normalized_path).name,
        "extension": extension,
        "mime_type": mime_type,
        "file_type": file_type,
        "source_type": source_type,
        "is_pdf": is_pdf,
        "icon": "pdf" if is_pdf else ("picture" if is_picture else "file"),
        "open_action": open_action,
        "document_id": document_id,
        "package_path": package_path,
        "package_backed": package_backed,
        "name": name,
        "title": title or name or "Lesson task",
        "added_by": added_by,
        "creator_role": creator_role,
        "space_task": bool(is_space_task),
        "auto_task": bool(is_space_task),
        "space": clean(source.get("space", "")),
        "folder": clean_path_value(source.get("folder", "")),
        **folder_group,
        "can_remove": can_remove,
        "added_at": clean(source.get("added_at", "")),
        "severity": normalize_lesson_task_severity(source.get("severity", "")),
        "available": file_exists,
        "completed": bool(source.get("completed_at")) or bool(completion.get("completed")),
        "completed_at": clean(source.get("completed_at", "")) or clean(completion.get("last", "")),
        "user_count": int(completion.get("count", 0) or 0),
        "study": study,
    }


def lesson_tasks_for_user(
    target_user: str,
    viewer_username: str = "",
    progress_index: dict[tuple[str, str], dict] | None = None,
    time_index: dict[str, dict] | None = None,
    include_admin: bool = False,
    viewer_progress_index: dict[tuple[str, str], dict] | None = None,
    viewer_time_index: dict[str, dict] | None = None,
) -> list[dict]:
    target_user = normalize_username(target_user)
    if not target_user:
        return []
    with lesson_task_user_lock(target_user):
        record = read_lesson_task_user_locked(target_user)
        rows = record.get("tasks") if isinstance(record, dict) and isinstance(record.get("tasks"), list) else []
    tasks = []
    for item in rows:
        task = normalize_lesson_task(
            item,
            target_user,
            viewer_username,
            progress_index,
            time_index,
            include_admin=include_admin,
            viewer_progress_index=viewer_progress_index,
            viewer_time_index=viewer_time_index,
        )
        if task:
            tasks.append(task)
    return tasks


def lesson_task_notice_text(value: object, limit: int = 2200) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    return text[:limit]


def read_lesson_task_notices_locked() -> dict:
    start_lesson_tasks_writebehind_flusher()
    if postgres_backend_enabled("LESSON_TASK_NOTICES"):
        from FUTURE.postgres.repositories import lesson_task_notices as pg_lesson_task_notices
        payload_out = pg_lesson_task_notices.load_payload()
        with LESSON_TASK_NOTICES_RAM_CACHE_LOCK:
            LESSON_TASK_NOTICES_RAM_CACHE["store"] = {
                "payload": payload_out,
                "dirty": False,
                "version": int(LESSON_TASK_NOTICES_RAM_CACHE.get("version", 0) or 0),
                "last_flush": time.time(),
                "at": time.time(),
            }
        return payload_out
    with LESSON_TASK_NOTICES_RAM_CACHE_LOCK:
        row = LESSON_TASK_NOTICES_RAM_CACHE.get("store")
        if isinstance(row, dict) and isinstance(row.get("payload"), dict):
            row["at"] = time.time()
            return row["payload"]
    payload_out = {"version": 1, "by_user": {}}
    payload = server_database_read_document_json(LESSON_TASK_NOTICES_FILE, {})
    if isinstance(payload, dict):
        payload_out = _clean_lesson_task_notice_store(payload)
    with LESSON_TASK_NOTICES_RAM_CACHE_LOCK:
        LESSON_TASK_NOTICES_RAM_CACHE["store"] = {
            "payload": payload_out,
            "dirty": False,
            "version": int(LESSON_TASK_NOTICES_RAM_CACHE.get("version", 0) or 0),
            "last_flush": time.time(),
            "at": time.time(),
        }
    return payload_out


def read_lesson_task_notices_for_user_store(target_user: str = "") -> dict:
    target_user = normalize_username(target_user)
    if target_user and postgres_backend_enabled("LESSON_TASK_NOTICES"):
        from FUTURE.postgres.repositories import lesson_task_notices as pg_lesson_task_notices
        return pg_lesson_task_notices.load_payload(target_user)
    return read_lesson_task_notices_locked()

def write_lesson_task_notices_locked(payload: dict, target_user: str = "") -> None:
    cleaned = _clean_lesson_task_notice_store(payload)
    start_lesson_tasks_writebehind_flusher()
    if postgres_backend_enabled("LESSON_TASK_NOTICES"):
        from FUTURE.postgres.repositories import lesson_task_notices as pg_lesson_task_notices
        pg_lesson_task_notices.save_payload(cleaned, target_user)
        with LESSON_TASK_NOTICES_RAM_CACHE_LOCK:
            current_version = int(LESSON_TASK_NOTICES_RAM_CACHE.get("version", 0) or 0) + 1
            LESSON_TASK_NOTICES_RAM_CACHE["version"] = current_version
            LESSON_TASK_NOTICES_RAM_CACHE["store"] = {
                "payload": cleaned,
                "dirty": False,
                "version": current_version,
                "last_flush": time.time(),
                "at": time.time(),
            }
        lesson_task_notices_user_revision(target_user, bump=True)
        return
    with LESSON_TASK_NOTICES_RAM_CACHE_LOCK:
        current_version = int(LESSON_TASK_NOTICES_RAM_CACHE.get("version", 0) or 0) + 1
        LESSON_TASK_NOTICES_RAM_CACHE["version"] = current_version
        LESSON_TASK_NOTICES_RAM_CACHE["store"] = {
            "payload": cleaned,
            "dirty": True,
            "version": current_version,
            "last_flush": float((LESSON_TASK_NOTICES_RAM_CACHE.get("store") or {}).get("last_flush", 0.0) or 0.0),
            "at": time.time(),
        }
    lesson_task_notices_user_revision(target_user, bump=True)


def normalize_lesson_task_notice_audio(source: dict) -> dict:
    data = source if isinstance(source, dict) else {}
    audio = data.get("audio") if isinstance(data.get("audio"), dict) else {}
    path = clean(audio.get("url") or audio.get("path") or audio.get("src") or data.get("audio_path", ""))
    mime = clean(audio.get("mime") or data.get("audio_mime", "")) or "audio/mpeg"
    base64_data = clean(audio.get("base64") or audio.get("data") or "")
    if path:
        return {"url": path, "path": path, "mime": mime}
    if base64_data:
        return {"base64": base64_data, "mime": mime}
    return {}


def normalize_lesson_task_notice(
    item: dict,
    target_user: str = "",
    include_read: bool = False,
    read_at: str = "",
    seen_at: str = "",
) -> dict | None:
    source = item if isinstance(item, dict) else {}
    notice_id = clean(source.get("id", "")) or f"notice-{uuid.uuid4().hex[:16]}"
    text = lesson_task_notice_text(source.get("text", ""))
    if not text:
        return None
    language = clean(source.get("language", "")).lower()
    if language not in {"vi", "en"}:
        language = "vi"
    mode = clean(source.get("mode", "")).lower()
    if mode in {"day", "24h", "daily", "one_day", "oneday"}:
        mode = "day"
    else:
        repeat = truthy(source.get("repeat", False), False) or mode in {"always", "repeat", "every", "login"}
        mode = "always" if repeat else "once"
    audio_enabled = truthy(source.get("audio_enabled", source.get("audioEnabled", False)), False)
    require_ack = truthy(source.get("require_ack", source.get("requireAck", False)), False)
    repeat_limit = max(0, min(999, space_w_int(source.get("repeat_limit", source.get("repeatLimit", source.get("max_shows", source.get("maxShows", 0)))), 0)))
    back_interval = max(1, min(99, space_w_int(source.get("back_interval", source.get("backInterval", source.get("back_gap", source.get("backGap", 1)))), 1)))
    until_tasks_complete = truthy(source.get("until_tasks_complete", source.get("untilTasksComplete", source.get("until_complete", source.get("untilComplete", False)))), False)
    notice_style = normalize_task_notice_style(source.get("notice_style", source.get("noticeStyle", source.get("style", "hologram"))))
    voice = clean(source.get("voice", "")) or ("edge:vi-VN-NamMinhNeural" if language == "vi" else "kokoro:am_michael")
    voice_label = clean(source.get("voice_label", source.get("voiceLabel", "")))
    audio = normalize_lesson_task_notice_audio(source)
    result = {
        "id": notice_id,
        "user": normalize_username(target_user or source.get("user", "")),
        "text": text,
        "language": language,
        "mode": mode,
        "repeat": mode == "always",
        "duration_hours": 24 if mode == "day" else 0,
        "notice_style": notice_style,
        "audio_enabled": audio_enabled,
        "require_ack": require_ack,
        "repeat_limit": repeat_limit,
        "back_interval": back_interval,
        "until_tasks_complete": until_tasks_complete,
        "voice": voice,
        "voice_label": voice_label,
        "translation_en": lesson_task_notice_text(source.get("translation_en", source.get("translationEn", source.get("english", "")))),
        "translation_vi": lesson_task_notice_text(source.get("translation_vi", source.get("translationVi", source.get("vietnamese", "")))),
        "speaker_name": clean(source.get("speaker_name", source.get("speakerName", source.get("name", ""))))[:120],
        "avatar": clean(source.get("avatar", source.get("avatar_url", source.get("avatarUrl", ""))))[:600],
        "created_at": clean(source.get("created_at", source.get("createdAt", ""))),
        "updated_at": clean(source.get("updated_at", source.get("updatedAt", ""))),
        "created_by": normalize_username(source.get("created_by", source.get("createdBy", ""))),
        "active": not (source.get("active") is False),
    }
    if audio:
        result["audio"] = audio
        result["audio_path"] = audio.get("url") or audio.get("path") or ""
        result["audio_mime"] = audio.get("mime") or "audio/mpeg"
    if include_read:
        result["read_at"] = clean(read_at)
        result["seen_at"] = clean(seen_at)
    return result


def lesson_tasks_have_pending(target_user: str) -> bool:
    target_user = normalize_username(target_user)
    if not target_user:
        return False
    try:
        with lesson_task_user_lock(target_user):
            record = read_lesson_task_user_locked(target_user)
            rows = record.get("tasks") if isinstance(record, dict) and isinstance(record.get("tasks"), list) else []
        for row in rows:
            if not isinstance(row, dict):
                continue
            raw_path = clean_path_value(row.get("path", ""))
            if not raw_path:
                continue
            if clean(row.get("completed_at", "")):
                continue
            completion = lesson_task_completion(raw_path, target_user)
            if not completion.get("completed"):
                return True
    except Exception:
        return False
    return False


def lesson_task_notices_for_user(target_user: str, admin_view: bool = False, pending_tasks: bool | None = None) -> list[dict]:
    target_user = normalize_username(target_user)
    if not target_user:
        return []
    with LESSON_TASK_NOTICE_LOCK:
        payload = read_lesson_task_notices_for_user_store(target_user)
        record = payload.get("by_user", {}).get(target_user, {})
        rows = record.get("notices") if isinstance(record, dict) and isinstance(record.get("notices"), list) else []
        read_map = record.get("read") if isinstance(record, dict) and isinstance(record.get("read"), dict) else {}
        seen_map = record.get("seen") if isinstance(record, dict) and isinstance(record.get("seen"), dict) else {}
    normalized_notices = []
    for row in rows:
        row_id = clean(row.get("id", "")) if isinstance(row, dict) else ""
        notice = normalize_lesson_task_notice(
            row,
            target_user,
            include_read=admin_view,
            read_at=read_map.get(row_id, ""),
            seen_at=seen_map.get(row_id, ""),
        )
        if not notice:
            continue
        normalized_notices.append(notice)
    # Updated 2026-07-22: inspect lesson completion only when a notice depends on it.
    needs_pending_tasks = bool(
        not admin_view
        and any(truthy(notice.get("until_tasks_complete", False), False) for notice in normalized_notices)
    )
    has_pending_tasks = True
    if needs_pending_tasks:
        has_pending_tasks = lesson_tasks_have_pending(target_user) if pending_tasks is None else bool(pending_tasks)
    notices = []
    for notice in normalized_notices:
        if not admin_view:
            if not notice.get("active", True):
                continue
            scheduled_notice = (
                max(0, space_w_int(notice.get("repeat_limit", 0), 0)) > 1
                or max(1, space_w_int(notice.get("back_interval", 1), 1)) > 1
                or truthy(notice.get("until_tasks_complete", False), False)
            )
            if truthy(notice.get("until_tasks_complete", False), False) and not has_pending_tasks:
                continue
            if notice.get("mode") == "day":
                first_seen = timestamp_to_epoch(seen_map.get(notice["id"], ""))
                if first_seen and time.time() - first_seen > 24 * 60 * 60:
                    continue
            elif notice.get("mode") != "always" and read_map.get(notice["id"]) and not scheduled_notice:
                continue
        notices.append(notice)
    return notices[-80:] if admin_view else notices[-12:]


def lesson_task_notice_payload(target_user: str, viewer_username: str = "") -> dict:
    target_user = normalize_username(target_user)
    viewer_username = normalize_username(viewer_username)
    admin_view = bool(viewer_username and is_admin_user(viewer_username) and viewer_username != target_user)
    return {
        "task_owner": target_user,
        "task_notices": lesson_task_notices_for_user(target_user, admin_view=admin_view),
    }


# Added 2026-07-20; updated 2026-07-21: cache complete task-board bytes until an exact dependency revision changes.
def lesson_tasks_response_signature(target_user: str, viewer_username: str = "", include_admin: bool = False) -> tuple:
    target_user = normalize_username(target_user)
    viewer_username = normalize_username(viewer_username)
    manifest = get_server_data_manifest()
    settings = space_task_settings_for_user(target_user)
    manifest_roots = {"common"}
    manifest_roots.update(
        clean_path_value(path).split("/", 1)[0].lower()
        for path in settings.get("preferred_folders", [])
        if clean_path_value(path)
    )
    rows = [
        lesson_tasks_runtime_signature(target_user),
        lesson_task_notices_runtime_signature(target_user),
        lesson_progress_index_runtime_token(target_user),
        lesson_time_runtime_signature(target_user),
        server_database_document_signature(USER_ROOT / target_user / LEARNING_SUMMARY_FILE_NAME),
        server_data_manifest_runtime_revision(manifest, manifest_roots) if settings.get("preferred_folders") else "",
        lesson_tasks_file_dependency_signature(target_user),
        clean(settings.get("updated_rev", "")),
        space_task_payload_user_revision(target_user),
        server_database_user_generation("learning_events", target_user),
    ]
    if include_admin and viewer_username and viewer_username != target_user:
        rows.extend([
            lesson_progress_index_runtime_token(viewer_username),
            lesson_time_runtime_signature(viewer_username),
            server_database_user_generation("learning_events", viewer_username),
        ])
    return tuple(rows)


# Added 2026-07-21: invalidate task-board bytes from exact task file revisions without statting clean manifest entries.
def lesson_tasks_file_dependency_signature(target_user: str) -> tuple:
    target_user = normalize_username(target_user)
    if not target_user:
        return ()
    with SERVER_DATA_MANIFEST_LOCK:
        manifest_dirty = bool(SERVER_DATA_MANIFEST_STATE.get("dirty"))
    if manifest_dirty:
        # Do not cache across the short watcher debounce window while file identities are unsettled.
        return ("manifest-dirty", time.monotonic_ns())
    with lesson_task_user_lock(target_user):
        record = read_lesson_task_user_locked(target_user)
        task_rows = record.get("tasks") if isinstance(record, dict) and isinstance(record.get("tasks"), list) else []
        paths = [
            (
                clean_path_value(item.get("path", "")),
                clean(item.get("lesson_id") or item.get("file_id"))[:240],
            )
            for item in task_rows
            if isinstance(item, dict)
        ]
    tokens = []
    for raw_path, file_id in paths:
        if not raw_path:
            continue
        entry = server_data_manifest_file_entry(raw_path)
        if not isinstance(entry, dict) and file_id.lower().startswith("ftg-lesson-"):
            current_path_reader = globals().get("server_database_lesson_current_path")
            current_path = clean_path_value(current_path_reader(file_id)) if callable(current_path_reader) else ""
            current_top = current_path.split("/", 1)[0].lower() if current_path else ""
            if current_top in {"common", target_user.lower()}:
                entry = server_data_manifest_file_entry(current_path)
        link_target = clean_path_value(entry.get("link_target", "")) if isinstance(entry, dict) else ""
        effective_entry = server_data_manifest_file_entry(link_target) if link_target else entry
        if isinstance(effective_entry, dict):
            tokens.append((
                raw_path.lower(),
                file_id.lower(),
                link_target.lower(),
                int(effective_entry.get("modified_ns", 0) or 0),
                int(effective_entry.get("size", -1) or -1),
                int(effective_entry.get("metadata_dependency_mtime_ns", 0) or 0),
                int(effective_entry.get("metadata_dependency_size", -1) or -1),
            ))
            continue
        info = lesson_task_file_info(raw_path, target_user, file_id)
        effective_target = info.get("effective_target") if isinstance(info, dict) else None
        signature = file_cache_signature(Path(effective_target)) if effective_target else (0, -1)
        tokens.append((raw_path.lower(), file_id.lower(), clean_path_value(info.get("effective_path", "")).lower(), *signature))
    return tuple(tokens)


# Added 2026-07-21: a completed/failed bounded Space Task build invalidates only that learner's pending bytes.
def invalidate_lesson_tasks_response_cache(target_user: str = "") -> None:
    target_user = normalize_username(target_user)
    if not target_user:
        return
    cache = globals().setdefault("LESSON_TASKS_RESPONSE_BYTES_CACHE", {})
    lock = globals().setdefault("LESSON_TASKS_RESPONSE_BYTES_CACHE_LOCK", threading.RLock())
    with lock:
        for cache_key in list(cache.keys()):
            if isinstance(cache_key, tuple) and cache_key and normalize_username(cache_key[0]) == target_user:
                cache.pop(cache_key, None)


def lesson_tasks_response_cache_row(target_user: str, viewer_username: str = "", include_admin: bool = False) -> dict | None:
    target_user = normalize_username(target_user)
    viewer_username = normalize_username(viewer_username)
    cache_key = (target_user, viewer_username if include_admin else "", bool(include_admin))
    signature = lesson_tasks_response_signature(target_user, viewer_username, include_admin)
    cache = globals().setdefault("LESSON_TASKS_RESPONSE_BYTES_CACHE", {})
    lock = globals().setdefault("LESSON_TASKS_RESPONSE_BYTES_CACHE_LOCK", threading.RLock())
    with lock:
        row = cache.get(cache_key) if isinstance(cache, dict) else None
        if (
            isinstance(row, dict)
            and row.get("signature") == signature
            and isinstance(row.get("payload"), dict)
            and isinstance(row.get("bytes"), bytes)
        ):
            return {**row, "cache_hit": True}
    return None


# Added 2026-07-20: detect Task Board state without treating unrelated time/progress rows as renderable tasks.
def lesson_tasks_user_has_renderable_state(target_user: str) -> bool:
    target_user = normalize_username(target_user)
    if not target_user:
        return False
    with lesson_task_user_lock(target_user):
        task_record = read_lesson_task_user_locked(target_user)
        if isinstance(task_record, dict):
            if isinstance(task_record.get("tasks"), list) and task_record.get("tasks"):
                return True
            settings = task_record.get("space_task") if isinstance(task_record.get("space_task"), dict) else {}
            if settings.get("preferred_folders") or settings.get("assigned") or clean(settings.get("updated_rev", "")):
                return True
    with LESSON_TASK_NOTICE_LOCK:
        notice_store = read_lesson_task_notices_for_user_store(target_user)
        notice_record = (notice_store.get("by_user") or {}).get(target_user, {}) if isinstance(notice_store, dict) else {}
        if isinstance(notice_record, dict) and (notice_record.get("notices") or notice_record.get("read") or notice_record.get("seen")):
            return True
    if server_database_document_exists(USER_ROOT / target_user / LEARNING_SUMMARY_FILE_NAME):
        return True
    return False


def build_lesson_tasks_response_cache_row(target_user: str, viewer_username: str = "", include_admin: bool = False) -> dict:
    build_started = time.perf_counter()
    stage_started = build_started
    timing = {}
    target_user = normalize_username(target_user)
    viewer_username = normalize_username(viewer_username)
    renderable = bool(include_admin or lesson_tasks_user_has_renderable_state(target_user))
    timing["renderable"] = (time.perf_counter() - stage_started) * 1000
    if not renderable:
        stage_started = time.perf_counter()
        payload = {
            "ok": True,
            "task_owner": target_user,
            "tasks": [],
            "space_task": _space_task_empty_opt_in_payload({}),
            "space_tasks": [],
            "task_notices": [],
            "learning_stats": empty_lesson_learning_summary(target_user),
            "admin": False,
        }
        data = json_bytes(payload)
        timing["serialize"] = (time.perf_counter() - stage_started) * 1000
        stage_started = time.perf_counter()
        signature = lesson_tasks_response_signature(target_user, viewer_username, include_admin)
        timing["signature"] = (time.perf_counter() - stage_started) * 1000
        timing["build_total"] = (time.perf_counter() - build_started) * 1000
        row = {
            "signature": signature,
            "payload": payload,
            "bytes": data,
            "etag": f'"lesson-tasks-{hashlib.sha1(data).hexdigest()}"',
            "at": time.time(),
            "cache_hit": False,
            "stateless": True,
            "timing": timing,
        }
        cache = globals().setdefault("LESSON_TASKS_RESPONSE_BYTES_CACHE", {})
        lock = globals().setdefault("LESSON_TASKS_RESPONSE_BYTES_CACHE_LOCK", threading.RLock())
        with lock:
            cache[(target_user, "", False)] = row
        return row
    stage_started = time.perf_counter()
    has_learning_state = server_database_user_has_lesson_state(target_user)
    timing["state_probe"] = (time.perf_counter() - stage_started) * 1000
    stage_started = time.perf_counter()
    progress_index = lesson_progress_record_index(target_user) if has_learning_state else {}
    time_index = lesson_time_state_index(target_user) if has_learning_state else {}
    viewer_progress_user = viewer_username if include_admin and viewer_username != target_user else ""
    viewer_progress_index = lesson_progress_record_index(viewer_progress_user) if viewer_progress_user else {}
    viewer_time_index = lesson_time_state_index(viewer_progress_user) if viewer_progress_user else {}
    timing["indexes"] = (time.perf_counter() - stage_started) * 1000
    stage_started = time.perf_counter()
    tasks = lesson_tasks_for_user(
        target_user,
        viewer_username,
        progress_index,
        time_index,
        include_admin=include_admin,
        viewer_progress_index=viewer_progress_index,
        viewer_time_index=viewer_time_index,
    )
    timing["manual_tasks"] = (time.perf_counter() - stage_started) * 1000
    # Updated 2026-07-21: finish the compact explicit-task work before cold Space Task workers compete for CPU.
    stage_started = time.perf_counter()
    space_task = space_task_payload_for_user(
        target_user,
        viewer_username,
        progress_index,
        time_index,
        include_admin=include_admin,
        viewer_progress_index=viewer_progress_index,
        viewer_time_index=viewer_time_index,
    )
    timing["space_task"] = (time.perf_counter() - stage_started) * 1000
    # Added 2026-07-20: normal Task GET must never rebuild a user's lifetime summary by scanning every lesson.
    stage_started = time.perf_counter()
    learning_stats = lesson_user_learning_summary_cached_or_empty(target_user)
    task_notices = lesson_task_notices_for_user(
        target_user,
        admin_view=bool(include_admin and viewer_username != target_user),
        pending_tasks=any(not bool(item.get("completed")) for item in tasks if isinstance(item, dict)),
    )
    timing["summary_notices"] = (time.perf_counter() - stage_started) * 1000
    stage_started = time.perf_counter()
    payload = {
        "ok": True,
        "task_owner": target_user,
        "tasks": tasks,
        "space_task": space_task,
        "space_tasks": space_task.get("tasks", []),
        "task_notices": task_notices,
        "learning_stats": learning_stats,
        "admin": bool(include_admin),
    }
    data = json_bytes(payload)
    timing["serialize"] = (time.perf_counter() - stage_started) * 1000
    stage_started = time.perf_counter()
    signature = lesson_tasks_response_signature(target_user, viewer_username, include_admin)
    timing["signature"] = (time.perf_counter() - stage_started) * 1000
    timing["build_total"] = (time.perf_counter() - build_started) * 1000
    row = {
        "signature": signature,
        "payload": payload,
        "bytes": data,
        "etag": f'"lesson-tasks-{hashlib.sha1(data).hexdigest()}"',
        "at": time.time(),
        "cache_hit": False,
        "timing": timing,
    }
    cache_key = (target_user, viewer_username if include_admin else "", bool(include_admin))
    cache = globals().setdefault("LESSON_TASKS_RESPONSE_BYTES_CACHE", {})
    lock = globals().setdefault("LESSON_TASKS_RESPONSE_BYTES_CACHE_LOCK", threading.RLock())
    with lock:
        cache[cache_key] = row
        if len(cache) > 128:
            stale = sorted(cache.items(), key=lambda item: float((item[1] or {}).get("at", 0.0) or 0.0))
            for old_key, _old_row in stale[:32]:
                if old_key != cache_key:
                    cache.pop(old_key, None)
    return row


def get_or_build_lesson_tasks_response_cache_row(target_user: str, viewer_username: str = "", include_admin: bool = False) -> dict:
    cached = lesson_tasks_response_cache_row(target_user, viewer_username, include_admin)
    if isinstance(cached, dict):
        return cached
    target_user = normalize_username(target_user)
    viewer_username = normalize_username(viewer_username)
    cache_key = (target_user, viewer_username if include_admin else "", bool(include_admin))
    lock = globals().setdefault("LESSON_TASKS_RESPONSE_BYTES_CACHE_LOCK", threading.RLock())
    inflight = globals().setdefault("LESSON_TASKS_RESPONSE_BUILD_INFLIGHT", {})
    should_build = False
    with lock:
        event = inflight.get(cache_key) if isinstance(inflight, dict) else None
        if not hasattr(event, "wait"):
            event = threading.Event()
            inflight[cache_key] = event
            should_build = True
    if not should_build:
        event.wait(12.0)
        cached = lesson_tasks_response_cache_row(target_user, viewer_username, include_admin)
        if isinstance(cached, dict):
            cached["coalesced"] = True
            return cached
    try:
        return build_lesson_tasks_response_cache_row(target_user, viewer_username, include_admin)
    finally:
        if should_build:
            with lock:
                inflight.pop(cache_key, None)
                event.set()

def lesson_tasks_cache_warm_candidates(limit: int = 8) -> list[str]:
    index = learning_completion_log_index()
    totals: dict[str, int] = {}
    for study in index.values():
        if not isinstance(study, dict):
            continue
        for bucket in ("users", "admins"):
            rows = study.get(bucket) if isinstance(study.get(bucket), dict) else {}
            for username, row in rows.items():
                normalized = normalize_username(username)
                if not normalized:
                    continue
                totals[normalized] = totals.get(normalized, 0) + max(0, space_w_int((row or {}).get("count", 0), 0))
    if not totals:
        try:
            return list_dashboard_usernames()[: max(0, int(limit or 0))]
        except Exception:
            return []
    ordered = sorted(totals.items(), key=lambda item: (-int(item[1] or 0), item[0]))
    return [username for username, _count in ordered[: max(0, int(limit or 0))]]

def warm_lesson_tasks_response_cache_async(limit: int = 8, delay: float = 1.0) -> None:
    def _worker() -> None:
        started = time.perf_counter()
        warmed = 0
        failed = 0
        candidates: list[str] = []
        try:
            if delay > 0:
                time.sleep(delay)
            candidates = lesson_tasks_cache_warm_candidates(limit)
            for username in candidates:
                try:
                    get_or_build_lesson_tasks_response_cache_row(username, "", False)
                    warmed += 1
                except Exception as exc:
                    failed += 1
                    stt_debug_log("lesson_tasks_response_cache_warm_failed", user=username, error=str(exc))
            stt_debug_log(
                "lesson_tasks_response_cache_warmed",
                candidates=candidates,
                warmed=warmed,
                failed=failed,
                ms=round((time.perf_counter() - started) * 1000, 3),
            )
        except Exception as exc:
            stt_debug_log("lesson_tasks_response_cache_warm_runner_failed", error=str(exc))

    threading.Thread(target=_worker, daemon=True, name="lesson-tasks-response-cache").start()


def build_lesson_task_notice_record(target_user: str, payload: dict, admin_username: str, transient: bool = False) -> dict:
    target_user = normalize_username(target_user)
    admin_username = normalize_username(admin_username)
    ok, message = validate_username(target_user)
    if not ok:
        raise RuntimeError(message)
    if not learner_user_exists(target_user):
        raise RuntimeError("User does not exist.")
    source = payload if isinstance(payload, dict) else {}
    notice_id = clean(source.get("id", ""))
    now = utc_timestamp()
    language = clean(source.get("language", "")).lower()
    if language not in {"vi", "en"}:
        language = "vi"
    voice = clean(source.get("voice", "")) or ("edge:vi-VN-NamMinhNeural" if language == "vi" else "kokoro:am_michael")
    voice_label = clean(source.get("voice_label", source.get("voiceLabel", "")))
    text = lesson_task_notice_text(source.get("text", ""))
    if not text:
        raise RuntimeError("Notice text is empty.")
    translation_en = lesson_task_notice_text(source.get("translation_en", source.get("translationEn", source.get("english", ""))))
    translation_vi = lesson_task_notice_text(source.get("translation_vi", source.get("translationVi", source.get("vietnamese", ""))))
    if language == "en":
        translation_en = translation_en or text
        if not translation_vi:
            translation_vi = task_notice_translate_to_vietnamese(text)
    else:
        translation_vi = translation_vi or text
        if not translation_en:
            translation_en = task_notice_translate_to_english(text)
    repeat_limit = max(0, min(999, space_w_int(source.get("repeat_limit", source.get("repeatLimit", source.get("max_shows", source.get("maxShows", 0)))), 0)))
    back_interval = max(1, min(99, space_w_int(source.get("back_interval", source.get("backInterval", source.get("back_gap", source.get("backGap", 1)))), 1)))
    until_tasks_complete = truthy(source.get("until_tasks_complete", source.get("untilTasksComplete", source.get("until_complete", source.get("untilComplete", False)))), False)
    next_notice = {
        "id": (f"instant-{uuid.uuid4().hex[:16]}" if transient else (notice_id or f"notice-{uuid.uuid4().hex[:16]}")),
        "text": text,
        "language": language,
        "translation_en": translation_en,
        "translation_vi": translation_vi,
        "mode": "day" if clean(source.get("mode", "")).lower() in {"day", "24h", "daily", "one_day", "oneday"} else ("always" if clean(source.get("mode", "")).lower() in {"always", "repeat", "every", "login"} or truthy(source.get("repeat", False), False) else "once"),
        "notice_style": normalize_task_notice_style(source.get("notice_style", source.get("noticeStyle", source.get("style", "hologram")))),
        "audio_enabled": truthy(source.get("audio_enabled", source.get("audioEnabled", False)), False),
        "require_ack": truthy(source.get("require_ack", source.get("requireAck", False)), False),
        "repeat_limit": repeat_limit,
        "back_interval": back_interval,
        "until_tasks_complete": until_tasks_complete,
        "voice": voice,
        "voice_label": voice_label,
        "speaker_name": clean(source.get("speaker_name", source.get("speakerName", source.get("name", ""))))[:120],
        "avatar": clean(source.get("avatar", source.get("avatar_url", source.get("avatarUrl", ""))))[:600],
        "created_by": admin_username,
        "updated_at": now,
        "active": True,
    }
    if transient or not notice_id:
        next_notice["created_at"] = now
    audio_payload = chat_synthesize_message_audio_queued(text, voice) if next_notice["audio_enabled"] else {}
    if audio_payload:
        next_notice.update(audio_payload)
    try:
        save_user_preferences(admin_username, {
            "task_notice_profile": {
                "speaker_name": next_notice["speaker_name"],
                "avatar": next_notice["avatar"],
            }
        })
    except Exception:
        pass
    return next_notice


def save_lesson_task_notice(target_user: str, payload: dict, admin_username: str) -> dict:
    target_user = normalize_username(target_user)
    source = payload if isinstance(payload, dict) else {}
    notice_id = clean(source.get("id", ""))
    now = utc_timestamp()
    next_notice = build_lesson_task_notice_record(target_user, payload, admin_username, transient=False)
    with LESSON_TASK_NOTICE_LOCK:
        store = read_lesson_task_notices_for_user_store(target_user)
        by_user = store.setdefault("by_user", {})
        record = by_user.setdefault(target_user, {"notices": [], "read": {}})
        rows = record.get("notices") if isinstance(record.get("notices"), list) else []
        existing = next((row for row in rows if isinstance(row, dict) and clean(row.get("id", "")) == notice_id), None)
        if existing:
            next_notice["created_at"] = clean(existing.get("created_at", "")) or now
            if not next_notice["voice_label"]:
                next_notice["voice_label"] = clean(existing.get("voice_label", ""))
        rows = [row for row in rows if isinstance(row, dict) and clean(row.get("id", "")) != next_notice["id"]]
        rows.append(next_notice)
        record["notices"] = rows[-200:]
        record.setdefault("read", {})
        by_user[target_user] = record
        write_lesson_task_notices_locked(store, target_user)
    return {"notice": normalize_lesson_task_notice(next_notice, target_user), "task_notices": lesson_task_notices_for_user(target_user, admin_view=True)}


def lesson_task_notice_immediate_payload(target_user: str, after_id: int = 0) -> dict:
    target_user = normalize_username(target_user)
    if not target_user:
        return {"immediate_latest_id": 0, "immediate_notices": []}
    now = time.time()
    with LESSON_TASK_NOTICE_LOCK:
        record = LESSON_TASK_NOTICE_INSTANT.setdefault(target_user, {"seq": 0, "events": []})
        rows = record.get("events") if isinstance(record.get("events"), list) else []
        live_rows = []
        for event in rows:
            if not isinstance(event, dict):
                continue
            try:
                created_epoch = float(event.get("created_epoch", 0) or 0)
            except Exception:
                created_epoch = 0.0
            if not created_epoch:
                created_epoch = timestamp_to_epoch(event.get("created_at", ""))
            if created_epoch and now - created_epoch > 60 * 60:
                continue
            live_rows.append(event)
        record["events"] = live_rows[-120:]
        latest_id = int(record.get("seq", 0) or 0)
    notices = []
    try:
        after_value = int(after_id or 0)
    except Exception:
        after_value = 0
    if after_value > latest_id:
        after_value = 0
    for event in live_rows:
        try:
            event_id = int(event.get("id", 0) or 0)
        except Exception:
            event_id = 0
        if event_id <= after_value:
            continue
        if clean(event.get("received_at", "")):
            continue
        notice = event.get("notice") if isinstance(event.get("notice"), dict) else {}
        normalized = normalize_lesson_task_notice(notice, target_user)
        if not normalized:
            continue
        normalized["_instant_id"] = event_id
        normalized["_immediate"] = True
        notices.append(normalized)
    return {"immediate_latest_id": latest_id, "immediate_notices": notices[-20:]}


def queue_lesson_task_notice_immediate(target_user: str, notice: dict) -> dict:
    target_user = normalize_username(target_user)
    normalized = normalize_lesson_task_notice(notice if isinstance(notice, dict) else {}, target_user)
    if not target_user or not normalized:
        raise RuntimeError("Missing notice to send.")
    with LESSON_TASK_NOTICE_LOCK:
        record = LESSON_TASK_NOTICE_INSTANT.setdefault(target_user, {"seq": 0, "events": []})
        next_id = max(int(record.get("seq", 0) or 0) + 1, int(time.time() * 1000))
        record["seq"] = next_id
        rows = record.get("events") if isinstance(record.get("events"), list) else []
        rows.append({
            "id": next_id,
            "notice_id": normalized.get("id", ""),
            "created_at": utc_timestamp(),
            "created_epoch": time.time(),
            "notice": normalized,
        })
        record["events"] = rows[-120:]
    immediate_notice = dict(normalized)
    immediate_notice["_instant_id"] = next_id
    immediate_notice["_immediate"] = True
    return {"immediate_event_id": next_id, "immediate_notice": immediate_notice}


def remove_lesson_task_notice(target_user: str, notice_id: str) -> dict:
    target_user = normalize_username(target_user)
    notice_id = clean(notice_id)
    if not target_user or not notice_id:
        raise RuntimeError("Missing notice id.")
    with LESSON_TASK_NOTICE_LOCK:
        store = read_lesson_task_notices_for_user_store(target_user)
        record = store.setdefault("by_user", {}).setdefault(target_user, {"notices": [], "read": {}})
        rows = record.get("notices") if isinstance(record.get("notices"), list) else []
        record["notices"] = [row for row in rows if isinstance(row, dict) and clean(row.get("id", "")) != notice_id]
        read_map = record.get("read") if isinstance(record.get("read"), dict) else {}
        read_map.pop(notice_id, None)
        record["read"] = read_map
        seen_map = record.get("seen") if isinstance(record.get("seen"), dict) else {}
        seen_map.pop(notice_id, None)
        record["seen"] = seen_map
        write_lesson_task_notices_locked(store, target_user)
    return {"removed": notice_id, "task_notices": lesson_task_notices_for_user(target_user, admin_view=True)}


def mark_lesson_task_notice_read(target_user: str, notice_id: str) -> dict:
    target_user = normalize_username(target_user)
    notice_id = clean(notice_id)
    if not target_user or not notice_id:
        raise RuntimeError("Missing notice id.")
    now = utc_timestamp()
    with LESSON_TASK_NOTICE_LOCK:
        store = read_lesson_task_notices_for_user_store(target_user)
        record = store.setdefault("by_user", {}).setdefault(target_user, {"notices": [], "read": {}})
        read_map = record.get("read") if isinstance(record.get("read"), dict) else {}
        read_map[notice_id] = now
        record["read"] = read_map
        write_lesson_task_notices_locked(store, target_user)
    return {"id": notice_id, "read_at": now, "task_notices": lesson_task_notices_for_user(target_user, admin_view=False)}


def mark_lesson_task_notice_seen(target_user: str, notice_id: str) -> dict:
    target_user = normalize_username(target_user)
    notice_id = clean(notice_id)
    if not target_user or not notice_id:
        raise RuntimeError("Missing notice id.")
    with LESSON_TASK_NOTICE_LOCK:
        store = read_lesson_task_notices_for_user_store(target_user)
        record = store.setdefault("by_user", {}).setdefault(target_user, {"notices": [], "read": {}, "seen": {}})
        seen_map = record.get("seen") if isinstance(record.get("seen"), dict) else {}
        seen_at = clean(seen_map.get(notice_id, ""))
        if not seen_at:
            seen_at = utc_timestamp()
            seen_map[notice_id] = seen_at
            record["seen"] = seen_map
            write_lesson_task_notices_locked(store, target_user)
    return {"id": notice_id, "seen_at": seen_at, "task_notices": lesson_task_notices_for_user(target_user, admin_view=False)}


def save_lesson_task_notice_avatar(upload: dict, admin_username: str = "") -> dict:
    source = upload if isinstance(upload, dict) else {}
    filename = clean(source.get("filename", "avatar.png"))
    data = source.get("data", b"")
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise RuntimeError("Avatar file is empty.")
    if len(data) > 8 * 1024 * 1024:
        raise RuntimeError("Avatar file is too large.")
    suffix = Path(filename).suffix.lower()
    mime = clean(source.get("content_type", "")).split(";")[0].lower()
    allowed_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
    allowed_mimes = {"image/png", "image/jpeg", "image/webp", "image/gif", "image/bmp"}
    if suffix not in allowed_suffixes and mime not in allowed_mimes:
        raise RuntimeError("Only image avatars are allowed.")
    if suffix not in allowed_suffixes:
        suffix = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/webp": ".webp",
            "image/gif": ".gif",
            "image/bmp": ".bmp",
        }.get(mime, ".png")
    TASK_NOTICE_AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(bytes(data[:65536]) + str(time.time()).encode("utf-8")).hexdigest()[:16]
    username = normalize_username(admin_username) or "admin"
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", Path(filename).stem).strip("-")[:36] or "avatar"
    target = TASK_NOTICE_AVATAR_DIR / f"{username}-{safe_name}-{digest}{suffix}"
    target.write_bytes(bytes(data))
    relative = server_data_relative(target)
    try:
        save_user_preferences(admin_username, {"task_notice_profile": {"avatar": relative}})
    except Exception:
        pass
    return {"avatar": relative, "path": relative, "mime": read_server_asset(relative)[1]}


def save_user_avatar(upload: dict, username: str = "") -> dict:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    source = upload if isinstance(upload, dict) else {}
    filename = clean(source.get("filename", "avatar.png"))
    data = source.get("data", b"")
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise RuntimeError("Avatar file is empty.")
    if len(data) > 16 * 1024 * 1024:
        raise RuntimeError("Avatar file is too large.")
    suffix = Path(filename).suffix.lower()
    mime = clean(source.get("content_type", "")).split(";")[0].lower()
    allowed_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
    allowed_mimes = {"image/png", "image/jpeg", "image/webp", "image/gif", "image/bmp"}
    if suffix not in allowed_suffixes and mime not in allowed_mimes:
        raise RuntimeError("Only image avatars are allowed.")
    USER_AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image, ImageFilter, ImageOps

        image = Image.open(io.BytesIO(bytes(data)))
        image = ImageOps.exif_transpose(image)
        if getattr(image, "is_animated", False):
            image.seek(0)
        image = image.convert("RGBA")
        width, height = image.size
        side = max(1, min(width, height))
        left = max(0, (width - side) // 2)
        top = max(0, (height - side) // 2)
        image = image.crop((left, top, left + side, top + side))
        avatar_size = 640
        image = image.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
        image = image.filter(ImageFilter.UnsharpMask(radius=0.65, percent=150, threshold=2))
        canvas = Image.new("RGBA", (avatar_size, avatar_size), (0, 0, 0, 0))
        canvas.alpha_composite(image)
        digest = hashlib.sha1(bytes(data[:65536]) + username.encode("utf-8") + str(time.time_ns()).encode("utf-8")).hexdigest()[:16]
        target = USER_AVATAR_DIR / f"{username}-{digest}.png"
        canvas.save(target, "PNG", optimize=True, compress_level=2)
    except Exception as exc:
        raise RuntimeError(f"Could not process avatar image: {exc}")
    relative = server_data_relative(target)
    profile = update_user_profile_fields(username, {"avatar": relative})
    return {
        "avatar": relative,
        "path": relative,
        "profile": profile,
        "bytes": int(target.stat().st_size),
        "mime": read_server_asset(relative)[1],
    }


def public_user_profile_card(username: str = "") -> dict:
    username = normalize_username(username)
    profile = read_user_profile(username) if username else {}
    display_name = clean(profile.get("full_name", "")) or username or "Learner"
    return {
        "username": username,
        "display_name": display_name,
        "full_name": clean(profile.get("full_name", "")),
        "gender": clean(profile.get("gender", "")) or "other",
        "avatar": clean(profile.get("avatar", "")),
        "intro": clean(profile.get("intro", "")),
        "profile_photos": normalize_profile_photos(profile.get("profile_photos", [])),
        "updated_at": clean(profile.get("updated_at", "")),
    }


def save_user_profile_card(username: str = "", payload: dict | None = None) -> dict:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    source = payload if isinstance(payload, dict) else {}
    profile = update_user_profile_fields(
        username,
        {
            "intro": clean(source.get("intro") or source.get("bio") or source.get("about") or "")[:1200],
            "profile_photos": normalize_profile_photos(
                source.get("profile_photos") or source.get("gallery") or source.get("photos") or []
            ),
        },
    )
    return public_user_profile_card(username) | {"profile": profile}


def save_user_profile_photo(upload: dict, username: str = "", slot: int = -1) -> dict:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    source = upload if isinstance(upload, dict) else {}
    filename = clean(source.get("filename", "profile-photo.png"))
    data = source.get("data", b"")
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise RuntimeError("Profile photo file is empty.")
    if len(data) > 18 * 1024 * 1024:
        raise RuntimeError("Profile photo file is too large.")
    suffix = Path(filename).suffix.lower()
    mime = clean(source.get("content_type", "")).split(";")[0].lower()
    allowed_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
    allowed_mimes = {"image/png", "image/jpeg", "image/webp", "image/gif", "image/bmp"}
    if suffix not in allowed_suffixes and mime not in allowed_mimes:
        raise RuntimeError("Only image profile photos are allowed.")
    USER_PROFILE_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image, ImageFilter, ImageOps

        image = Image.open(io.BytesIO(bytes(data)))
        image = ImageOps.exif_transpose(image)
        if getattr(image, "is_animated", False):
            image.seek(0)
        image = image.convert("RGBA")
        width, height = image.size
        max_side = 2200
        scale = min(1.0, max_side / max(1, max(width, height)))
        if scale < 1.0:
            image = image.resize((max(1, int(width * scale)), max(1, int(height * scale))), Image.Resampling.LANCZOS)
        image = image.filter(ImageFilter.UnsharpMask(radius=0.55, percent=135, threshold=2))
        background = Image.new("RGB", image.size, (7, 16, 18))
        if image.mode == "RGBA":
            background.paste(image.convert("RGB"), mask=image.getchannel("A"))
        else:
            background.paste(image.convert("RGB"))
        digest = hashlib.sha1(bytes(data[:65536]) + username.encode("utf-8") + str(time.time_ns()).encode("utf-8")).hexdigest()[:16]
        target = USER_PROFILE_PHOTO_DIR / f"{username}-profile-{digest}.webp"
        try:
            background.save(target, "WEBP", quality=98, method=6, exact=True)
        except Exception:
            target = USER_PROFILE_PHOTO_DIR / f"{username}-profile-{digest}.png"
            background.save(target, "PNG", optimize=True, compress_level=2)
    except Exception as exc:
        raise RuntimeError(f"Could not process profile photo: {exc}")
    relative = server_data_relative(target)
    profile = read_user_profile(username)
    photos = normalize_profile_photos(profile.get("profile_photos", []))
    safe_slot = max(-1, min(3, int(slot) if str(slot).lstrip("-").isdigit() else -1))
    if safe_slot >= 0:
        while len(photos) <= safe_slot:
            photos.append("")
        photos[safe_slot] = relative
    elif len(photos) < 4:
        photos.append(relative)
    else:
        photos[-1] = relative
    photos = normalize_profile_photos(photos)
    profile = update_user_profile_fields(username, {"profile_photos": photos})
    return {
        "photo": relative,
        "path": relative,
        "profile": profile,
        "profile_card": public_user_profile_card(username),
        "bytes": int(target.stat().st_size),
        "mime": read_server_asset(relative)[1],
    }


# Added 2026-07-20: short revision/file-keyed cache makes an exact add retry return its prior ACK.
def lesson_task_add_retry_cache_key(
    target_user: str,
    relative_path: str,
    actor_username: str,
    creator_role: str,
    severity: str,
    effective_path: str = "",
    link_target: str = "",
    title: str = "",
    name: str = "",
    folder_id: str = "",
    folder_path: str = "",
) -> tuple[str, ...]:
    return (
        normalize_username(target_user).lower(),
        clean_path_value(relative_path).lower(),
        normalize_username(actor_username).lower(),
        clean(creator_role).lower(),
        normalize_lesson_task_severity(severity),
        clean_path_value(effective_path).lower(),
        clean_path_value(link_target).lower(),
        clean(title),
        clean(name),
        clean(folder_id).lower()[:240],
        clean_path_value(folder_path).lower(),
    )


def lesson_task_add_retry_cache_get(cache_key: tuple[str, ...], target_user: str) -> dict | None:
    cache = globals().setdefault("LESSON_TASK_ADD_RETRY_CACHE", {})
    lock = globals().setdefault("LESSON_TASK_ADD_RETRY_CACHE_LOCK", threading.RLock())
    with lock:
        row = cache.get(cache_key) if isinstance(cache, dict) else None
        if not isinstance(row, dict) or time.time() - float(row.get("at", 0.0) or 0.0) > 30.0:
            return None
        if int(row.get("revision", -1) or -1) != lesson_tasks_user_revision(target_user):
            return None
        result = row.get("result") if isinstance(row.get("result"), dict) else None
        effective_target = Path(clean(row.get("effective_target", "")))
        expected_signature = row.get("file_signature")
    try:
        stat = effective_target.stat()
        current_signature = (int(stat.st_mtime_ns), int(stat.st_size))
    except Exception:
        return None
    if current_signature != expected_signature or not isinstance(result, dict) or not isinstance(result.get("task"), dict):
        return None
    return {"task": dict(result["task"]), "changed": False, "retry": True}


def lesson_task_add_retry_cache_put(
    cache_key: tuple[str, ...],
    target_user: str,
    effective_target: Path,
    result: dict,
) -> None:
    try:
        stat = Path(effective_target).stat()
        signature = (int(stat.st_mtime_ns), int(stat.st_size))
    except Exception:
        return
    cache = globals().setdefault("LESSON_TASK_ADD_RETRY_CACHE", {})
    lock = globals().setdefault("LESSON_TASK_ADD_RETRY_CACHE_LOCK", threading.RLock())
    with lock:
        cache[cache_key] = {
            "revision": lesson_tasks_user_revision(target_user),
            "effective_target": str(effective_target),
            "file_signature": signature,
            "result": {"task": dict(result.get("task") or {})},
            "at": time.time(),
        }
        if len(cache) > 512:
            stale = sorted(cache.items(), key=lambda item: float((item[1] or {}).get("at", 0.0) or 0.0))
            for old_key, _old_row in stale[:128]:
                if old_key != cache_key:
                    cache.pop(old_key, None)


# Added 2026-07-21: compare durable task fields so delayed exact retries bypass SQLite after later task revisions.
def lesson_task_add_semantic_identity(value: dict | None) -> tuple:
    source = value if isinstance(value, dict) else {}
    return (
        clean(source.get("id", "")),
        clean_path_value(source.get("path", "")).lower(),
        clean_path_value(source.get("effective_path", "")).lower(),
        clean_path_value(source.get("link_target", "")).lower(),
        clean(source.get("name", "")),
        clean(source.get("title", "")),
        clean(source.get("folder_id", "")).lower()[:240],
        clean_path_value(source.get("folder_path") or source.get("folder")).lower(),
        normalize_username(source.get("added_by", "")).lower(),
        lesson_task_creator_role(source),
        normalize_lesson_task_severity(source.get("severity", "")),
    )


def add_lesson_task(
    target_user: str,
    relative_path: str,
    actor_username: str = "",
    severity: str = "normal",
    creator_role: str = "admin",
    effective_path: str = "",
    link_target: str = "",
    title: str = "",
    name: str = "",
    folder_id: str = "",
    folder_path: str = "",
) -> dict:
    target_user = normalize_username(target_user)
    actor_username = normalize_username(actor_username)
    creator_role = "user" if clean(creator_role).lower() in {"user", "learner", "student", "self", "personal"} else "admin"
    ok, message = validate_username(target_user)
    if not ok:
        raise RuntimeError(message)
    if not learner_user_exists(target_user):
        raise RuntimeError("User does not exist.")
    if creator_role == "user" and actor_username != target_user:
        raise RuntimeError("Users can only add tasks to their own board.")
    retry_cache_key = lesson_task_add_retry_cache_key(
        target_user,
        relative_path,
        actor_username,
        creator_role,
        severity,
        effective_path,
        link_target,
        title,
        name,
        folder_id,
        folder_path,
    )
    cached_retry = lesson_task_add_retry_cache_get(retry_cache_key, target_user)
    if cached_retry:
        return cached_retry
    target = safe_server_data_path(relative_path, actor_username or target_user, admin=True)
    link_payload = read_server_data_link_payload(target)
    source_effective_path = clean_path_value(effective_path or link_target or link_payload.get("target", ""))
    if source_effective_path:
        effective_target = safe_server_data_path(source_effective_path, actor_username or target_user, admin=True)
        effective_target = server_data_effective_file_path(effective_target, username=actor_username or target_user, admin=True)
    else:
        effective_target = server_data_effective_file_path(target, username=actor_username or target_user, admin=True)
    if not link_payload:
        target = effective_target
    if not effective_target.is_file() or not is_lesson_file(effective_target):
        raise RuntimeError("Only lesson files can be added as tasks.")
    rel_path = server_data_relative(target)
    effective_rel_path = server_data_relative(effective_target)
    task_title = clean(title)
    try:
        manifest_entry = server_data_manifest_file_entry(effective_rel_path or rel_path)
        meta = lesson_task_file_meta_from_manifest(manifest_entry, effective_target)
        if not meta:
            meta = cached_lesson_file_metadata(effective_target, manifest_entry=manifest_entry)
    except Exception:
        meta = {}
    identity_reader = globals().get("server_database_lesson_file_id_for_path")
    canonical_lesson_id = clean(identity_reader(effective_rel_path or rel_path))[:240] if callable(identity_reader) else ""
    if not canonical_lesson_id.lower().startswith("ftg-lesson-"):
        canonical_lesson_id = clean(meta.get("lesson_id", ""))[:240]
    now = utc_timestamp()
    task = {
        "id": lesson_task_id(target_user, rel_path, canonical_lesson_id),
        "lesson_id": canonical_lesson_id,
        "file_id": canonical_lesson_id,
        "path": rel_path,
        "effective_path": effective_rel_path,
        "link_target": clean_path_value(link_payload.get("target", "") or link_target),
        "name": clean(name) or target.name,
        "title": task_title or clean(meta.get("title", "")) or effective_target.stem,
        "folder_id": clean(folder_id)[:240],
        "folder_path": clean_path_value(folder_path),
        "added_by": actor_username,
        "creator_role": creator_role,
        "added_at": now,
        "severity": normalize_lesson_task_severity(severity if creator_role == "admin" else "normal"),
    }
    with lesson_task_user_lock(target_user):
        user_record = read_lesson_task_user_locked(target_user)
        tasks = user_record.get("tasks") if isinstance(user_record.get("tasks"), list) else []
        next_tasks = []
        existing_task = None
        existing_index = -1
        matched_count = 0
        for item in tasks:
            if not isinstance(item, dict):
                continue
            if clean_path_value(item.get("path", "")).lower() == rel_path.lower():
                matched_count += 1
                if existing_task is None:
                    existing_task = dict(item)
                    existing_index = len(next_tasks)
                    next_tasks.append(None)
            else:
                next_tasks.append(item)
        if existing_task and creator_role == "user" and lesson_task_creator_role(existing_task) == "admin":
            task = existing_task
            if existing_index >= 0:
                next_tasks[existing_index] = task
            else:
                next_tasks.append(task)
        else:
            if existing_task:
                task["added_at"] = clean(existing_task.get("added_at", "")) or task["added_at"]
            if existing_index >= 0:
                next_tasks[existing_index] = task
            else:
                next_tasks.append(task)
        tasks = next_tasks
        user_record["tasks"] = tasks[-300:]
        changed = bool(
            existing_task is None
            or matched_count != 1
            or lesson_task_add_semantic_identity(existing_task) != lesson_task_add_semantic_identity(task)
        )
        if changed:
            write_lesson_task_user_locked(target_user, user_record)
        elif existing_task is not None:
            task = existing_task
    # Updated 2026-07-22: POST add must return the same canonical schema as the later GET hydrate.
    target_progress_index = lesson_progress_record_index(target_user)
    target_time_index = lesson_time_state_index(target_user)
    viewer_progress_user = actor_username if creator_role == "admin" and actor_username != target_user else ""
    task_out = normalize_lesson_task(
        task,
        target_user,
        actor_username,
        target_progress_index,
        target_time_index,
        include_admin=creator_role == "admin",
        viewer_progress_index=lesson_progress_record_index(viewer_progress_user) if viewer_progress_user else {},
        viewer_time_index=lesson_time_state_index(viewer_progress_user) if viewer_progress_user else {},
    )
    if not isinstance(task_out, dict):
        raise RuntimeError("Could not normalize the new lesson task.")
    result = {"task": task_out, "changed": changed}
    lesson_task_add_retry_cache_put(retry_cache_key, target_user, effective_target, result)
    return result


def update_lesson_task_severity(
    target_user: str,
    task_id: str = "",
    relative_path: str = "",
    severity: str = "normal",
    viewer_username: str = "",
) -> dict:
    target_user = normalize_username(target_user)
    ok, message = validate_username(target_user)
    if not ok:
        raise RuntimeError(message)
    wanted_id = clean(task_id)
    wanted_path = clean_path_value(relative_path).lower()
    if not wanted_id and not wanted_path:
        raise RuntimeError("Missing task id.")
    next_severity = normalize_lesson_task_severity(severity)
    updated_task = None
    with lesson_task_user_lock(target_user):
        user_record = read_lesson_task_user_locked(target_user)
        tasks = user_record.get("tasks") if isinstance(user_record.get("tasks"), list) else []
        changed = False
        for item in tasks:
            if not isinstance(item, dict):
                continue
            is_target = (
                clean_path_value(item.get("path", "")).lower() == wanted_path
                if wanted_path
                else bool(wanted_id and clean(item.get("id", "")) == wanted_id)
            )
            if is_target:
                item["severity"] = next_severity
                updated_task = dict(item)
                changed = True
        if not changed:
            raise RuntimeError("Task not found.")
        write_lesson_task_user_locked(target_user, user_record)
    return {"task": normalize_lesson_task(updated_task or {}, target_user, viewer_username)}


def remove_lesson_task(
    target_user: str,
    task_id: str = "",
    relative_path: str = "",
    viewer_username: str = "",
) -> dict:
    target_user = normalize_username(target_user)
    viewer_username = normalize_username(viewer_username)
    ok, message = validate_username(target_user)
    if not ok:
        raise RuntimeError(message)
    viewer_is_admin = bool(viewer_username and is_admin_user(viewer_username))
    if not viewer_is_admin and viewer_username != target_user:
        raise RuntimeError("Users can only remove their own tasks.")
    wanted_id = clean(task_id)
    wanted_path = clean_path_value(relative_path).lower()
    if not wanted_id and not wanted_path:
        raise RuntimeError("Missing task id.")
    removed_task = None
    removed_tasks = []
    folder_group = {}
    with lesson_task_user_lock(target_user):
        user_record = read_lesson_task_user_locked(target_user)
        tasks = user_record.get("tasks") if isinstance(user_record.get("tasks"), list) else []
        for item in tasks:
            if not isinstance(item, dict):
                continue
            is_target = (
                (wanted_id and clean(item.get("id", "")) == wanted_id) or
                (wanted_path and clean_path_value(item.get("path", "")).lower() == wanted_path)
            )
            if is_target:
                removed_task = dict(item)
                break
        if removed_task:
            folder_group = lesson_task_folder_group_metadata(removed_task)
        target_group_key = clean(folder_group.get("folder_group_key", "")).lower()
        next_tasks = []
        for item in tasks:
            if not isinstance(item, dict):
                continue
            item_id = clean(item.get("id", ""))
            item_path = clean_path_value(item.get("path", "")).lower()
            same_target = bool(item_path == wanted_path) if wanted_path else bool(wanted_id and item_id == wanted_id)
            same_group = bool(
                target_group_key
                and clean(lesson_task_folder_group_metadata(item).get("folder_group_key", "")).lower() == target_group_key
            )
            if same_target or same_group:
                removed_tasks.append(dict(item))
                continue
            next_tasks.append(item)
        user_record["tasks"] = next_tasks
        if removed_tasks:
            write_lesson_task_user_locked(target_user, user_record)
    if not removed_task:
        raise RuntimeError("Task not found.")
    removed_rows = [
        {
            "id": clean(item.get("id", "")),
            "path": clean_path_value(item.get("path", "")),
        }
        for item in removed_tasks
    ]
    return {
        "removed": removed_rows[0] if removed_rows else {
            "id": clean(removed_task.get("id", "")),
            "path": clean_path_value(removed_task.get("path", "")),
        },
        "removed_tasks": removed_rows,
        "removed_count": len(removed_rows),
        **folder_group,
    }


# Added 2026-07-09: completes tasks by visible, effective, or link target path so linked lessons advance the board.
def mark_lesson_task_completed(target_user: str, relative_path: str, new_relative_path: str = "", file_id: str = "") -> bool:
    target_user = normalize_username(target_user)
    rel_path = clean_path_value(relative_path).lower()
    new_path = clean_path_value(new_relative_path)
    canonical_id = clean(file_id)[:240].lower()
    if not target_user or (not rel_path and not canonical_id):
        return False
    with lesson_task_user_lock(target_user):
        record = read_lesson_task_user_locked(target_user)
        tasks = record.get("tasks") if isinstance(record, dict) and isinstance(record.get("tasks"), list) else []
        changed = False
        now = utc_timestamp()
        for item in tasks:
            if not isinstance(item, dict):
                continue
            item_paths = {
                clean_path_value(item.get("path", "")).lower(),
                clean_path_value(item.get("effective_path", "")).lower(),
                clean_path_value(item.get("link_target", "")).lower(),
            }
            item_paths = {path for path in item_paths if path}
            item_id = clean(item.get("lesson_id") or item.get("file_id") or item.get("identity"))[:240].lower()
            matches = bool(canonical_id and item_id == canonical_id)
            if not matches and not item_id:
                matches = bool(rel_path and rel_path in item_paths)
            if not matches:
                continue
            if new_path:
                item["path"] = new_path
            item["completed_at"] = clean(item.get("completed_at", "")) or now
            changed = True
        if changed:
            write_lesson_task_user_locked(target_user, record)
    if changed:
        invalidate_space_task_payload_cache(target_user)
    return changed


def read_jsonl_log(path: Path, limit: int = 800, date: str = "", search: str = "", keep_days: int = 31) -> list[dict]:
    rows: list[dict] = []
    cutoff = time.time() - max(1, int(keep_days or 31)) * 24 * 60 * 60
    wanted_date = clean(date)[:10]
    wanted_search = clean(search).lower()
    if Path(path) in {LEARNING_LOG_FILE, LOGIN_LOG_FILE}:
        stream = "learning" if Path(path) == LEARNING_LOG_FILE else "login"
        database_rows = server_database_read_events(stream, limit=max(5000, int(limit or 800)), keep_days=keep_days)
        for item in database_rows:
            at = clean(item.get("at", ""))
            if wanted_date and not at.startswith(wanted_date):
                continue
            if wanted_search and wanted_search not in json.dumps(item, ensure_ascii=False).lower():
                continue
            rows.append(item)
        return rows[: max(1, min(5000, int(limit or 800)))]
    if not path.is_file():
        return rows
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except Exception:
        return rows
    kept_lines: list[str] = []
    changed = False
    for line in lines:
        raw = str(line or "").strip()
        if not raw:
            changed = True
            continue
        try:
            item = json.loads(raw)
        except Exception:
            changed = True
            continue
        if not isinstance(item, dict):
            changed = True
            continue
        at = clean(item.get("at", ""))
        stamp = timestamp_to_epoch(at)
        if stamp and stamp < cutoff:
            changed = True
            continue
        kept_lines.append(json.dumps(item, ensure_ascii=False, separators=(",", ":")))
        if wanted_date and not at.startswith(wanted_date):
            continue
        if wanted_search and wanted_search not in json.dumps(item, ensure_ascii=False).lower():
            continue
        rows.append(item)
    if changed:
        try:
            atomic_write_text(path, ("\n".join(kept_lines) + ("\n" if kept_lines else "")), encoding="utf-8")
        except Exception:
            pass
    rows.sort(key=lambda item: clean(item.get("at", "")), reverse=True)
    return rows[: max(1, min(5000, int(limit or 800)))]


def append_jsonl_log(path: Path, record: dict, keep_days: int = 31, database_recorded: bool = False) -> dict:
    SERVER_LOG_ROOT.mkdir(parents=True, exist_ok=True)
    source_record = dict(record) if isinstance(record, dict) else {}
    source_record.pop("database_event_committed", None)
    if Path(path) == LEARNING_LOG_FILE and clean(source_record.get("event", "")) == "lesson_complete":
        source_record["status"] = "final"
    payload = {
        "at": utc_timestamp(),
        **source_record,
    }
    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    database_append = globals().get("server_database_append_event")
    if callable(database_append) and not database_recorded:
        stream = "learning" if Path(path) == LEARNING_LOG_FILE else "login" if Path(path) == LOGIN_LOG_FILE else Path(path).stem
        database_append(stream, payload)
    if Path(path) in {LEARNING_LOG_FILE, LOGIN_LOG_FILE}:
        return payload
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    # Added 2026-07-05: avoid pruning large logs on every learner completion.
    prune_state = getattr(append_jsonl_log, "_prune_state", None)
    if not isinstance(prune_state, dict):
        prune_state = {}
        setattr(append_jsonl_log, "_prune_state", prune_state)
    now = time.time()
    cache_key = str(path).lower()
    last_prune = float(prune_state.get(cache_key, 0) or 0)
    try:
        should_prune = path.stat().st_size > 512 * 1024 and now - last_prune > 300
    except Exception:
        should_prune = now - last_prune > 300
    if should_prune:
        prune_state[cache_key] = now
        read_jsonl_log(path, limit=1, keep_days=keep_days)
    return payload


def append_learning_log(record: dict) -> None:
    append_jsonl_log(
        LEARNING_LOG_FILE,
        record,
        database_recorded=bool(isinstance(record, dict) and record.get("database_final_event_committed")),
    )
    source = record if isinstance(record, dict) else {}
    bump_login_preload_cache_generation(source.get("user") or source.get("username") or "")


def record_login_event(username: str, info: dict | None = None) -> None:
    username = normalize_username(username)
    if not username:
        return
    source = info if isinstance(info, dict) else {}
    append_jsonl_log(
        LOGIN_LOG_FILE,
        {
            "event": "login",
            "user": username,
            "client": clean(source.get("client", ""))[:120],
            "user_agent": clean(source.get("user_agent", ""))[:260],
        },
    )


def active_session_login_rows(date: str = "", search: str = "") -> list[dict]:
    wanted_date = clean(date)[:10]
    wanted_search = clean(search).lower()
    rows: list[dict] = []
    with AUTH_LOCK:
        sessions = [dict(item) for item in AUTH_SESSIONS.values() if isinstance(item, dict)]
    for session in sessions:
        username = normalize_username(session.get("username", ""))
        if not username:
            continue
        created_at = float(session.get("created_at", 0) or 0)
        if not created_at:
            continue
        at = local_timestamp(created_at)
        row = {
            "at": at,
            "event": "active_session",
            "user": username,
            "client": "",
            "user_agent": "Active session loaded from server session cache",
        }
        if wanted_date and not at.startswith(wanted_date):
            continue
        if wanted_search and wanted_search not in json.dumps(row, ensure_ascii=False).lower():
            continue
        rows.append(row)
    rows.sort(key=lambda item: clean(item.get("at", "")), reverse=True)
    return rows
