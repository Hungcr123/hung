# Loaded by FUTURE.server_parts.server_data_pdf_qmdict.03_space_task_auto into the shared Future server runtime namespace.


def space_task_cold_async_enabled() -> bool:
    return truthy(os.environ.get("FUTURE_SPACE_TASK_COLD_ASYNC", "1"), True)


# Added 2026-07-21: pending Task Board bytes must become stale exactly when the bounded build finishes or retries.
def space_task_payload_user_revision(target_user: str = "", bump: bool = False) -> int:
    cache_key = normalize_username(target_user).lower()
    if not cache_key:
        return 0
    with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
        revisions = globals().setdefault("SPACE_TASK_PAYLOAD_USER_REVISIONS", {})
        current = int(revisions.get(cache_key, 0) or 0)
        if bump:
            current += 1
            revisions[cache_key] = current
        return current

def _space_task_payload_clone(value):
    if isinstance(value, dict):
        return {key: _space_task_payload_clone(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_space_task_payload_clone(item) for item in value]
    return value


def _space_task_payload_cache_key(target_user: str, viewer_username: str = "", include_admin: bool = False) -> str:
    return "|".join([
        normalize_username(target_user),
        "admin" if include_admin else "user",
        normalize_username(viewer_username) if include_admin else "",
    ])

def _space_task_trace_enabled(target_user: str = "") -> bool:
    wanted = normalize_username(os.environ.get("FUTURE_SPACE_TASK_TRACE_USER", ""))
    return bool(wanted and wanted == normalize_username(target_user))

def _space_task_trace(event: str, target_user: str = "", **fields) -> None:
    if not _space_task_trace_enabled(target_user):
        return
    cache_key = clean(fields.pop("cache_key", ""))
    folders = fields.pop("folders", [])
    folder_paths = []
    if isinstance(folders, (list, tuple)):
        folder_paths = [clean_path_value(item)[:240] for item in folders if clean_path_value(item)][:8]
    payload = {
        "trace_event": clean(event),
        "at": utc_timestamp(),
        "user": normalize_username(target_user),
        "viewer": normalize_username(fields.pop("viewer", "")),
        "request_id": clean(fields.pop("request_id", "")),
        "cache_key_hash": hashlib.sha256(cache_key.encode("utf-8", errors="ignore")).hexdigest()[:12] if cache_key else "",
        "revision": clean(fields.pop("revision", "")),
        "folders": folder_paths,
        **{key: value for key, value in fields.items() if key not in {"token", "password", "dsn"}},
    }
    stt_debug_log("space_task_trace", **payload)


# Added 2026-07-21: bound settled payload RAM without evicting active cold builds during 100-user bursts.
def _space_task_payload_cache_prune(protected_key: str = "") -> int:
    max_items = max(1, int(globals().get("SPACE_TASK_PAYLOAD_CACHE_MAX_ITEMS", 256) or 256))
    evict_batch = max(1, int(globals().get("SPACE_TASK_PAYLOAD_CACHE_EVICT_BATCH", 64) or 64))
    overflow = len(SPACE_TASK_PAYLOAD_RAM_CACHE) - max_items
    if overflow <= 0:
        return 0
    remove_count = max(overflow, min(evict_batch, max_items))
    candidates = []
    for cache_key, row in SPACE_TASK_PAYLOAD_RAM_CACHE.items():
        if cache_key == protected_key or cache_key in SPACE_TASK_PAYLOAD_REFRESH_INFLIGHT:
            continue
        if not isinstance(row, dict) or row.get("cold_build_event") is not None:
            continue
        payload = row.get("payload")
        if isinstance(payload, dict) and payload.get("pending"):
            continue
        candidates.append((
            float(row.get("at", row.get("refresh_started_at", 0.0)) or 0.0),
            cache_key,
        ))
    removed = 0
    for _at, cache_key in sorted(candidates)[:remove_count]:
        if SPACE_TASK_PAYLOAD_RAM_CACHE.pop(cache_key, None) is not None:
            removed += 1
    return removed


def _space_task_empty_opt_in_payload(settings: dict | None = None) -> dict:
    source = settings if isinstance(settings, dict) else {}
    return {
        "enabled": True,
        "preferred_folders": [],
        "folders": [],
        "active_folders": [],
        "tasks": [],
        "counts": {space: 0 for space in SPACE_TASK_ACTIVE_LIMITS},
        "limits": SPACE_TASK_ACTIVE_LIMITS,
        "scanned_files": 0,
        "completed_skipped": 0,
        "unavailable_skipped": 0,
        "updated_at": clean(source.get("updated_at", "")),
        "updated_by": normalize_username(source.get("updated_by", "")),
        "updated_rev": clean(source.get("updated_rev", "")),
        "pending": False,
        "stale": False,
        "opt_in_required": True,
    }


def invalidate_space_task_payload_cache(target_user: str = "") -> None:
    target_user = normalize_username(target_user)
    if not target_user:
        return
    prefix = f"{target_user}|"
    # Added 2026-07-24: completion must invalidate every Space Task layer together.
    # Otherwise the hot payload can retain the just-completed file for up to 15s.
    with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
        removed_payload = 0
        removed_inflight = 0
        for key in list(SPACE_TASK_PAYLOAD_RAM_CACHE.keys()):
            if clean(key).startswith(prefix):
                SPACE_TASK_PAYLOAD_RAM_CACHE.pop(key, None)
                removed_payload += 1
        signature_cache = globals().get("SPACE_TASK_PAYLOAD_SIGNATURE_CACHE")
        if isinstance(signature_cache, dict):
            for key in list(signature_cache.keys()):
                if clean(key).startswith(prefix):
                    signature_cache.pop(key, None)
        for key in list(SPACE_TASK_PAYLOAD_REFRESH_INFLIGHT.keys()):
            if clean(key).startswith(prefix):
                SPACE_TASK_PAYLOAD_REFRESH_INFLIGHT.pop(key, None)
                removed_inflight += 1
        progress_signature_cache = globals().get("SPACE_TASK_PROGRESS_SIGNATURE_CACHE")
        if isinstance(progress_signature_cache, dict):
            progress_signature_cache.pop(target_user, None)
    # The HTTP response-byte cache has its own lock and signature. Drop it here
    # so a fresh Lesson Task request cannot replay the previous task selection.
    bump_revision = globals().get("space_task_payload_user_revision")
    if callable(bump_revision):
        bump_revision(target_user, bump=True)
    invalidate_response = globals().get("invalidate_lesson_tasks_response_cache")
    if callable(invalidate_response):
        invalidate_response(target_user)
    _space_task_trace(
        "invalidate",
        target_user,
        reason=clean(globals().get("SPACE_TASK_INVALIDATE_REASON", "")) or "direct",
        removed_payload=removed_payload,
        removed_inflight=removed_inflight,
    )


# Added 2026-08-03: patch an active Space Task card after a partial checkpoint without rescanning folders.
def patch_space_task_payload_cache_progress(target_user: str = "", record: dict | None = None, study: dict | None = None) -> int:
    target_user = normalize_username(target_user)
    source = record if isinstance(record, dict) else {}
    progress_study = study if isinstance(study, dict) else {}
    if not target_user or not progress_study:
        return 0
    wanted = {
        clean(value).lower()
        for value in (
            source.get("lesson_id"), source.get("identity"), source.get("path"),
            source.get("legacy_path"), source.get("effective_path"),
        ) if clean(value)
    }
    if not wanted:
        return 0
    patched = 0
    prefix = f"{target_user}|"
    with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
        for cache_key, row in list(SPACE_TASK_PAYLOAD_RAM_CACHE.items()):
            if not clean(cache_key).startswith(prefix) or not isinstance(row, dict):
                continue
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else None
            tasks = payload.get("tasks") if isinstance(payload, dict) and isinstance(payload.get("tasks"), list) else []
            for task in tasks:
                if not isinstance(task, dict):
                    continue
                candidates = {
                    clean(value).lower()
                    for value in (
                        task.get("lesson_id"), task.get("lessonId"), task.get("file_id"),
                        task.get("fileId"), task.get("path"), task.get("effective_path"),
                        task.get("effectivePath"), task.get("link_target"), task.get("linkTarget"),
                    ) if clean(value)
                }
                if not candidates.intersection(wanted):
                    continue
                base_study = task.get("study") if isinstance(task.get("study"), dict) else {}
                merged_study = {**base_study, **progress_study}
                base_progress = base_study.get("progress") if isinstance(base_study.get("progress"), dict) else {}
                next_progress = progress_study.get("progress") if isinstance(progress_study.get("progress"), dict) else progress_study
                merged_progress = {**base_progress, **next_progress}
                merged_study["progress"] = merged_progress
                task["study"] = merged_study
                task["progress"] = merged_progress
                task["completed"] = bool(merged_progress.get("completed"))
                task["progress_text"] = clean(merged_progress.get("text"))
                task["progress_percent"] = max(0, min(100, space_w_int(merged_progress.get("percent", 0), 0)))
                patched += 1
    if patched:
        with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
            progress_signature_cache = globals().get("SPACE_TASK_PROGRESS_SIGNATURE_CACHE")
            if isinstance(progress_signature_cache, dict):
                progress_signature_cache.pop(target_user, None)
            signature_cache = globals().get("SPACE_TASK_PAYLOAD_SIGNATURE_CACHE")
            if isinstance(signature_cache, dict):
                for key in list(signature_cache.keys()):
                    if clean(key).startswith(prefix):
                        signature_cache.pop(key, None)
        bump_revision = globals().get("space_task_payload_user_revision")
        if callable(bump_revision):
            bump_revision(target_user, bump=True)
        invalidate_response = globals().get("invalidate_lesson_tasks_response_cache")
        if callable(invalidate_response):
            invalidate_response(target_user)
    _space_task_trace("partial_patch", target_user, patched=patched)
    return patched


def _space_task_progress_runtime_signature(username: str = "") -> tuple:
    username = normalize_username(username)
    if not username:
        return ()
    # Added 2026-07-10: reuse the same user's progress signature during bursty Lesson Vault Space Task updates.
    now = time.time()
    progress_signature_cache = globals().setdefault("SPACE_TASK_PROGRESS_SIGNATURE_CACHE", {})
    with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
        cached = progress_signature_cache.get(username) if isinstance(progress_signature_cache, dict) else None
        if isinstance(cached, dict) and now - float(cached.get("at", 0.0) or 0.0) < 2.0:
            signature = cached.get("signature")
            if isinstance(signature, tuple):
                return signature
    rows = []
    for space in ("Space_W", "Space_Q", "Space_V", "Space_P", "Space_PDF"):
        try:
            store = load_space_progress_store(space, username)
            payload = store.get("payload") if isinstance(store.get("payload"), dict) else {}
            states = payload.get("states") if isinstance(payload.get("states"), dict) else {}
            newest_state = ""
            progress_sum = 0
            for record in states.values():
                if not isinstance(record, dict):
                    continue
                newest_state = timestamp_latest_text(newest_state, record.get("updatedAt") or record.get("savedAt") or "")
                state = record.get("state") if isinstance(record.get("state"), dict) else {}
                progress_sum += max(0, space_w_int(record.get("nodeIndex", state.get("currentIndex", state.get("nodeIndex", 0))), 0))
                progress_sum += max(0, space_w_int(record.get("nodeCount", state.get("nodeCount", 0)), 0))
            rows.append((
                space,
                clean(payload.get("updated_at", "")),
                bool(store.get("dirty")),
                len(states),
                newest_state,
                progress_sum,
            ))
        except Exception:
            rows.append((space, "", False, 0, "", 0))
    try:
        rows.append(("time", lesson_time_runtime_signature(username)))
    except Exception:
        rows.append(("time", (0, -1)))
    result = tuple(rows)
    with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
        if isinstance(progress_signature_cache, dict):
            progress_signature_cache[username] = {"signature": result, "at": time.time()}
            if len(progress_signature_cache) > 256:
                stale = sorted(progress_signature_cache.items(), key=lambda item: float((item[1] or {}).get("at", 0.0) or 0.0))
                for old_key, _value in stale[:64]:
                    if old_key != username:
                        progress_signature_cache.pop(old_key, None)
    return result


def _space_task_folder_runtime_signature(target_user: str, settings: dict | None = None) -> tuple:
    target_user = normalize_username(target_user)
    settings = settings if isinstance(settings, dict) else space_task_settings_for_user(target_user)
    folder_rows = _space_task_candidate_folder_rows(target_user, settings)
    folder_key_rows = []
    share_key = "common"
    for folder_row in folder_rows:
        rel_path = clean_path_value(folder_row.get("path", ""))
        direct_only = bool(folder_row.get("direct_only"))
        folder_key_rows.append((rel_path.lower(), direct_only))
        if rel_path.split("/", 1)[0].lower() != "common":
            share_key = target_user
    cache_key = (share_key, tuple(folder_key_rows))
    now = time.time()
    signature_cache = globals().setdefault("SPACE_TASK_FOLDER_RUNTIME_SIGNATURE_CACHE", {})
    with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
        cached = signature_cache.get(cache_key) if isinstance(signature_cache, dict) else None
        if isinstance(cached, dict) and now - float(cached.get("at", 0.0) or 0.0) < 2.0:
            signature = cached.get("signature")
            if isinstance(signature, tuple):
                return signature
    rows = []
    for folder_row in folder_rows:
        rel_path = clean_path_value(folder_row.get("path", ""))
        direct_only = bool(folder_row.get("direct_only"))
        try:
            folder = safe_server_data_path(rel_path, target_user, admin=True)
            effective_folder = server_data_resolve_folder_link_ancestor(folder, username=target_user, admin=True)
            rows.append((
                rel_path,
                server_data_relative(effective_folder) or rel_path,
                direct_only,
                _space_task_folder_scan_signature(folder),
                _space_task_folder_scan_signature(effective_folder),
            ))
        except Exception:
            rows.append((rel_path, "", direct_only, (0, -1), (0, -1)))
    result = tuple(rows)
    with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
        if isinstance(signature_cache, dict):
            signature_cache[cache_key] = {"signature": result, "at": now}
            if len(signature_cache) > 128:
                stale = sorted(signature_cache.items(), key=lambda item: float((item[1] or {}).get("at", 0.0) or 0.0))
                for old_key, _value in stale[:32]:
                    signature_cache.pop(old_key, None)
    return result


def _space_task_payload_runtime_signature(target_user: str, viewer_username: str = "", include_admin: bool = False) -> tuple:
    target_user = normalize_username(target_user)
    viewer_username = normalize_username(viewer_username)
    cache_key = f"{target_user}|{'admin' if include_admin else 'user'}|{viewer_username if include_admin else ''}"
    now = time.time()
    signature_cache = globals().setdefault("SPACE_TASK_PAYLOAD_SIGNATURE_CACHE", {})
    with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
        cached_signature = signature_cache.get(cache_key) if isinstance(signature_cache, dict) else None
        if isinstance(cached_signature, dict) and now - float(cached_signature.get("at", 0.0) or 0.0) < 2.0:
            signature = cached_signature.get("signature")
            if isinstance(signature, tuple):
                return signature
    settings = space_task_settings_for_user(target_user)
    if not settings.get("preferred_folders"):
        return (
            "opt-in-empty",
            clean(settings.get("updated_at", "")),
            normalize_username(settings.get("updated_by", "")),
            clean(settings.get("updated_rev", "")),
        )
    manifest = get_server_data_manifest()
    manifest_roots = {"common"}
    manifest_roots.update(
        clean_path_value(path).split("/", 1)[0].lower()
        for path in settings.get("preferred_folders", [])
        if clean_path_value(path)
    )
    signature = [
        tuple(settings.get("preferred_folders", [])) if isinstance(settings.get("preferred_folders", []), list) else (),
        clean(settings.get("updated_at", "")),
        normalize_username(settings.get("updated_by", "")),
        clean(settings.get("updated_rev", "")),
        _space_task_folder_runtime_signature(target_user, settings),
        server_data_manifest_runtime_revision(manifest, manifest_roots),
        _space_task_progress_runtime_signature(target_user),
    ]
    if include_admin and viewer_username and viewer_username != target_user:
        signature.append(viewer_username)
        signature.append(_space_task_progress_runtime_signature(viewer_username))
    else:
        signature.append("")
    result = tuple(signature)
    with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
        if isinstance(signature_cache, dict):
            signature_cache[cache_key] = {"signature": result, "at": time.time()}
            if len(signature_cache) > 192:
                stale = sorted(signature_cache.items(), key=lambda item: float((item[1] or {}).get("at", 0.0) or 0.0))
                for old_key, _value in stale[:48]:
                    if old_key != cache_key:
                        signature_cache.pop(old_key, None)
    return result


def _space_task_pending_payload(target_user: str, settings: dict | None = None, stale_payload: dict | None = None) -> dict:
    target_user = normalize_username(target_user)
    settings = settings if isinstance(settings, dict) else space_task_settings_for_user(target_user)
    if isinstance(stale_payload, dict):
        payload = _space_task_payload_clone(stale_payload)
        payload["preferred_folders"] = settings.get("preferred_folders", [])
        payload["folders"] = folder_rows = _space_task_candidate_folder_rows(target_user, settings)
        payload["updated_at"] = clean(settings.get("updated_at", ""))
        payload["updated_by"] = normalize_username(settings.get("updated_by", ""))
        payload["updated_rev"] = clean(settings.get("updated_rev", ""))
        if not settings.get("preferred_folders"):
            payload["active_folders"] = []
            payload["tasks"] = []
            payload["counts"] = {space: 0 for space in SPACE_TASK_ACTIVE_LIMITS}
        payload["pending"] = True
        payload["stale"] = True
        return payload
    folder_rows = _space_task_candidate_folder_rows(target_user, settings)
    return {
        "enabled": True,
        "preferred_folders": settings.get("preferred_folders", []),
        "folders": folder_rows,
        "active_folders": [],
        "tasks": [],
        "counts": {space: 0 for space in SPACE_TASK_ACTIVE_LIMITS},
        "limits": SPACE_TASK_ACTIVE_LIMITS,
        "scanned_files": 0,
        "completed_skipped": 0,
        "unavailable_skipped": 0,
        "updated_at": clean(settings.get("updated_at", "")),
        "updated_by": normalize_username(settings.get("updated_by", "")),
        "updated_rev": clean(settings.get("updated_rev", "")),
        "pending": True,
        "stale": False,
    }


def _space_task_cached_payload_matches_settings(payload: dict | None, settings: dict | None) -> bool:
    # Added 2026-07-10: do not return a hot cached Lesson Vault Space Task payload after folder settings changed.
    if not isinstance(payload, dict) or not isinstance(settings, dict):
        return False
    def clean_folder_rows(value: object) -> list[str]:
        rows = value if isinstance(value, list) else []
        return [clean_path_value(item) for item in rows if clean_path_value(item)]
    payload_folders = clean_folder_rows(payload.get("preferred_folders", []))
    settings_folders = clean_folder_rows(settings.get("preferred_folders", []))
    return (
        payload_folders == settings_folders
        and timestamp_same_instant(payload.get("updated_at", ""), settings.get("updated_at", ""))
        and normalize_username(payload.get("updated_by", "")) == normalize_username(settings.get("updated_by", ""))
        and clean(payload.get("updated_rev", "")) == clean(settings.get("updated_rev", ""))
    )


# Added 2026-07-09: cold/async Space Task builds need the learner progress index to skip completed auto files.
def _space_task_progress_index_for_build(username: str, progress_index: dict[tuple[str, str], dict] | None = None) -> dict[tuple[str, str], dict] | None:
    if isinstance(progress_index, dict):
        return progress_index
    loader = globals().get("lesson_progress_record_index")
    if callable(loader):
        return loader(username)
    return progress_index


# Added 2026-07-28: an identified unfinished run must stay ahead of untouched Space Task candidates.
def _space_task_task_has_active_run(task: dict | None) -> bool:
    task = task if isinstance(task, dict) else {}
    study = task.get("study") if isinstance(task.get("study"), dict) else {}
    progress = study.get("progress") if isinstance(study.get("progress"), dict) else {}
    values = [
        task.get("activeRun", task.get("active_run")),
        study.get("activeRun", study.get("active_run")),
        progress.get("activeRun", progress.get("active_run")),
    ]
    for value in values:
        if value is True:
            return True
        if isinstance(value, dict) and bool(value.get("active") or value.get("in_progress")):
            return True
    return bool(task.get("in_progress") or study.get("in_progress") or progress.get("in_progress"))


# Added 2026-07-28: keep active progress paths inside the bounded candidate window without rescanning lesson bytes.
def _space_task_active_progress_keys(progress_index: dict[tuple[str, str], dict] | None) -> set[tuple[str, str]]:
    active_keys: set[tuple[str, str]] = set()
    if not isinstance(progress_index, dict):
        return active_keys
    for (space, key), record in progress_index.items():
        if not isinstance(record, dict):
            continue
        state = record.get("state") if isinstance(record.get("state"), dict) else {}
        active_value = record.get("activeRun", record.get("active_run", state.get("activeRun", state.get("active_run"))))
        active = bool(
            active_value is True
            or (isinstance(active_value, dict) and (active_value.get("active") or active_value.get("in_progress")))
            or record.get("in_progress")
            or state.get("in_progress")
        )
        if not active:
            continue
        if not clean(key).startswith("id:"):
            active_keys.add((clean(space), clean_path_value(key).lower()))
    return active_keys


# Added 2026-07-28: active unfinished work outranks a new file; lifetime history only ranks inactive rows.
def _space_task_candidate_rank(task: dict | None):
    task = task if isinstance(task, dict) else {}
    space = clean(task.get("space", ""))
    order = int(task.get("space_task_order", 0) or 0)
    if _space_task_task_has_active_run(task):
        return (-1, order, natural_sort_key(task.get("path", "")))
    if space in {"Space_PDF", "Space_Picture"}:
        return (0, order, natural_sort_key(task.get("path", "")))
    study = task.get("study") if isinstance(task.get("study"), dict) else {}
    progress = study.get("progress") if isinstance(study.get("progress"), dict) else {}
    done = max(0, space_w_int(progress.get("done", 0), 0))
    completed_runs = max(
        0,
        space_w_int(study.get("completed_runs", study.get("completedRuns", 0)), 0),
        space_w_int(task.get("user_count", 0), 0),
    )
    if not task.get("completed") and completed_runs <= 0 and done <= 0:
        return (0, order, natural_sort_key(task.get("path", "")))
    if not task.get("completed") and completed_runs <= 0:
        return (1, order, natural_sort_key(task.get("path", "")))
    if not task.get("completed"):
        return (2, order, natural_sort_key(task.get("path", "")))
    return (3, completed_runs, order, natural_sort_key(task.get("path", "")))


def _space_task_payload_build_for_user(
    target_user: str,
    viewer_username: str = "",
    progress_index: dict[tuple[str, str], dict] | None = None,
    time_index: dict[str, dict] | None = None,
    include_admin: bool = False,
    viewer_progress_index: dict[tuple[str, str], dict] | None = None,
    viewer_time_index: dict[str, dict] | None = None,
) -> dict:
    target_user = normalize_username(target_user)
    if not target_user:
        return {"enabled": False, "preferred_folders": [], "folders": [], "active_folders": [], "tasks": []}
    settings = space_task_settings_for_user(target_user)
    folder_rows = _space_task_candidate_folder_rows(target_user, settings)
    tasks = []
    counts = {space: 0 for space in SPACE_TASK_ACTIVE_LIMITS}
    seen_files = set()
    active_folders = []
    active_folder_seen = set()
    scanned_files = 0
    completed_skipped = 0
    unavailable_skipped = 0
    pick_counts = {space: 0 for space in SPACE_TASK_ACTIVE_LIMITS}
    preferred_folders = settings.get("preferred_folders", []) if isinstance(settings.get("preferred_folders", []), list) else []
    use_folder_quota = len(preferred_folders) >= 1
    per_folder_space_limit = 1
    active_progress_keys = _space_task_active_progress_keys(progress_index)

    def prioritized_folder_files(folder_row):
        files = _space_task_files_in_folder(folder_row, target_user)
        return sorted(files, key=lambda path: (
            0 if (_space_task_file_space(path, server_data_relative(path)), server_data_relative(path).lower()) in active_progress_keys else 1,
            natural_sort_key(_space_task_fast_sort_path(path) or path.name),
        ))

    def prepare_space_task(path, folder_row, folder_index, order_index, enforce_space_limit=True):
        nonlocal scanned_files, completed_skipped, unavailable_skipped
        rel_path = server_data_relative(path)
        key = rel_path.lower()
        if not rel_path or key in seen_files:
            return None
        seen_files.add(key)
        space = _space_task_file_space(path, rel_path)
        if not space:
            return None
        if enforce_space_limit and int(counts.get(space, 0) or 0) >= int(SPACE_TASK_ACTIVE_LIMITS.get(space, 1) or 1):
            return None
        scanned_files += 1
        early_progress = lesson_progress_summary_from_index(
            progress_index,
            target_user,
            rel_path,
            path.suffix,
            0,
            [rel_path],
            strict_paths=True,
        ) if isinstance(progress_index, dict) else {}
        early_done = max(0, space_w_int(early_progress.get("done", 0), 0)) if isinstance(early_progress, dict) else 0
        early_total = max(0, space_w_int(early_progress.get("total", 0), 0)) if isinstance(early_progress, dict) else 0
        early_active_run_value = early_progress.get("activeRun", early_progress.get("active_run")) if isinstance(early_progress, dict) else False
        early_active_run = early_active_run_value if isinstance(early_active_run_value, dict) else {}
        early_active_in_progress = bool(
            early_active_run_value is True
            or (isinstance(early_progress, dict) and early_progress.get("in_progress"))
            or early_active_run.get("active")
            or early_active_run.get("in_progress")
        )
        # Added 2026-07-28: never skip a lesson whose newest identified run is still active.
        early_completed = bool(
            isinstance(early_progress, dict)
            and not early_active_in_progress
            and (
                early_progress.get("completed")
                or (early_total and early_done >= early_total)
                or max(0, space_w_int(early_progress.get("percent", 0), 0)) >= 100
            )
        )
        if space not in {"Space_PDF", "Space_Picture"} and early_completed:
            completed_skipped += 1
            return None
        task = normalize_lesson_task(
            _space_task_source_for_file(path, target_user, folder_row, folder_index, order_index),
            target_user,
            viewer_username,
            progress_index,
            time_index,
            include_admin=include_admin,
            viewer_progress_index=viewer_progress_index,
            viewer_time_index=viewer_time_index,
        )
        if not task or task.get("available") is False:
            unavailable_skipped += 1
            return None
        # Added 2026-07-09: completed auto lessons must not occupy the next Space Task slot.
        if task.get("completed") and not _space_task_task_has_active_run(task) and space not in {"Space_PDF", "Space_Picture"}:
            completed_skipped += 1
            return None
        task["space_task"] = True
        task["auto_task"] = True
        task["space"] = space
        task["folder_source"] = clean(folder_row.get("source", ""))
        task["folder_rank"] = int(folder_index)
        task["space_task_order"] = int(order_index)
        return task

    def remember_active_folder(folder_row):
        folder_key = clean_path_value(folder_row.get("path", "")).lower()
        if folder_key and folder_key not in active_folder_seen:
            active_folder_seen.add(folder_key)
            active_folders.append(clean_path_value(folder_row.get("path", "")))

    def accept_space_task(task, folder_row):
        if not task:
            return False
        space = clean(task.get("space", ""))
        if not use_folder_quota and int(counts.get(space, 0) or 0) >= int(SPACE_TASK_ACTIVE_LIMITS.get(space, 1) or 1):
            return False
        task["space_task_pick_rank"] = int(pick_counts.get(space, 0) or 0)
        pick_counts[space] = int(pick_counts.get(space, 0) or 0) + 1
        tasks.append(task)
        counts[space] = int(counts.get(space, 0) or 0) + 1
        remember_active_folder(folder_row)
        return True

    def folder_candidate_limits_satisfied(by_space):
        for space, limit in SPACE_TASK_ACTIVE_LIMITS.items():
            limit = per_folder_space_limit if use_folder_quota else int(limit or 0)
            value = by_space.get(space, 0)
            count = len(value) if isinstance(value, list) else int(value or 0)
            if limit > 0 and count < limit:
                return False
        return True

    # Added 2026-07-08: Space Task only needs a few candidates per type; avoid normalizing huge folders.
    def candidate_cap_for_space(space: str, per_folder: bool = False) -> int:
        limit = per_folder_space_limit if per_folder else int(SPACE_TASK_ACTIVE_LIMITS.get(space, 1) or 1)
        # Keep a small bounded candidate window so a later untouched file can
        # outrank an earlier repeat run without normalizing an entire folder.
        return max(8, limit)

    def candidate_caps_satisfied(by_space, per_folder: bool = False) -> bool:
        for space in SPACE_TASK_SPACE_ORDER:
            if space not in by_space:
                continue
            if len(by_space.get(space, [])) < candidate_cap_for_space(space, per_folder=per_folder):
                return False
        return True

    if use_folder_quota:
        for folder_index, folder_row in enumerate(folder_rows):
            by_space = {space: [] for space in SPACE_TASK_ACTIVE_LIMITS}
            for order_index, path in enumerate(prioritized_folder_files(folder_row)):
                rel_path = clean_path_value(_space_task_fast_sort_path(path))
                space = _space_task_file_space(path, rel_path)
                if not space or len(by_space.get(space, [])) >= candidate_cap_for_space(space, per_folder=True):
                    continue
                task = prepare_space_task(path, folder_row, folder_index, order_index, enforce_space_limit=False)
                if not task:
                    continue
                if space in by_space:
                    by_space[space].append(task)
                if candidate_caps_satisfied(by_space, per_folder=True):
                    break
            for space in SPACE_TASK_SPACE_ORDER:
                candidates = by_space.get(space, [])
                if not candidates:
                    continue
                for task in sorted(candidates, key=_space_task_candidate_rank)[:per_folder_space_limit]:
                    accept_space_task(task, folder_row)
    else:
        by_space = {space: [] for space in SPACE_TASK_ACTIVE_LIMITS}
        folder_lookup = {}
        for folder_index, folder_row in enumerate(folder_rows):
            for order_index, path in enumerate(prioritized_folder_files(folder_row)):
                rel_path = clean_path_value(_space_task_fast_sort_path(path))
                space = _space_task_file_space(path, rel_path)
                if not space or len(by_space.get(space, [])) >= candidate_cap_for_space(space):
                    continue
                task = prepare_space_task(path, folder_row, folder_index, order_index, enforce_space_limit=False)
                if not task:
                    continue
                if space in by_space:
                    by_space[space].append(task)
                    folder_lookup[clean_path_value(task.get("path", "")).lower()] = folder_row
                if candidate_caps_satisfied(by_space):
                    break
        for space in SPACE_TASK_SPACE_ORDER:
            limit = int(SPACE_TASK_ACTIVE_LIMITS.get(space, 0) or 0)
            if limit <= 0:
                continue
            for task in sorted(by_space.get(space, []), key=_space_task_candidate_rank)[:limit]:
                accept_space_task(task, folder_lookup.get(clean_path_value(task.get("path", "")).lower(), {}))
    # Updated 2026-07-22: type is primary (PDF first), folder is secondary, and original order stays stable inside each type/folder.
    display_space_order = ("Space_PDF", *[space for space in SPACE_TASK_SPACE_ORDER if space != "Space_PDF"])
    order_lookup = {space: index for index, space in enumerate(display_space_order)}
    tasks.sort(key=lambda item: (
        0 if _space_task_task_has_active_run(item) else 1,
        order_lookup.get(clean(item.get("space", "")), 99),
        int(item.get("folder_rank", 0) or 0),
        int(item.get("space_task_order", 0) or 0),
        int(item.get("space_task_pick_rank", item.get("space_task_order", 0)) or 0),
        natural_sort_key(item.get("path", "")),
    ))
    assignments = space_task_assignments_for_active_paths(
        target_user,
        [
            {"path": clean_path_value(task.get("path", ""))}
            for task in tasks
        ],
    )
    for task in tasks:
        assignment_key, _assignment_path = _space_task_assignment_identity(task)
        assignment = assignments.get(assignment_key, {})
        assigned_at = clean(assignment.get("assigned_at", ""))
        if assigned_at:
            task["assigned_at"] = assigned_at
            if not clean(task.get("added_at", "")):
                task["added_at"] = assigned_at
    return {
        "enabled": True,
        "preferred_folders": settings.get("preferred_folders", []),
        "folders": folder_rows,
        "active_folders": active_folders,
        "tasks": tasks,
        "counts": counts,
        "limits": SPACE_TASK_ACTIVE_LIMITS,
        "scanned_files": scanned_files,
        "completed_skipped": completed_skipped,
        "unavailable_skipped": unavailable_skipped,
        "updated_at": clean(settings.get("updated_at", "")),
        "updated_by": normalize_username(settings.get("updated_by", "")),
        "updated_rev": clean(settings.get("updated_rev", "")),
        "pending": False,
        "stale": False,
    }


def _refresh_space_task_payload_async(
    cache_key: str,
    target_user: str,
    viewer_username: str = "",
    progress_index: dict[tuple[str, str], dict] | None = None,
    time_index: dict[str, dict] | None = None,
    include_admin: bool = False,
    viewer_progress_index: dict[tuple[str, str], dict] | None = None,
    viewer_time_index: dict[str, dict] | None = None,
) -> bool:
    cache_key = clean(cache_key)
    if not cache_key:
        return False
    request_id = f"st-{time.time_ns()}"
    now = time.time()
    min_refresh_gap = max(1.0, float(globals().get("SPACE_TASK_PAYLOAD_REFRESH_DEBOUNCE_SECONDS", 4.0) or 4.0))
    with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
        inflight_at = float(SPACE_TASK_PAYLOAD_REFRESH_INFLIGHT.get(cache_key) or 0.0)
        if inflight_at and now - inflight_at < 90.0:
            _space_task_trace(
                "enqueue_skip_inflight",
                target_user,
                viewer=viewer_username,
                request_id=request_id,
                cache_key=cache_key,
                inflight_age_ms=round((now - inflight_at) * 1000, 3),
            )
            return True
        cached = SPACE_TASK_PAYLOAD_RAM_CACHE.get(cache_key)
        if isinstance(cached, dict) and now - float(cached.get("refresh_started_at", 0.0) or 0.0) < min_refresh_gap:
            _space_task_trace(
                "enqueue_skip_debounce",
                target_user,
                viewer=viewer_username,
                request_id=request_id,
                cache_key=cache_key,
                debounce_ms=round((now - float(cached.get("refresh_started_at", 0.0) or 0.0)) * 1000, 3),
            )
            return True
        if not isinstance(cached, dict):
            cached = {}
            SPACE_TASK_PAYLOAD_RAM_CACHE[cache_key] = cached
        cached["refresh_started_at"] = now
        SPACE_TASK_PAYLOAD_REFRESH_INFLIGHT[cache_key] = now
    settings_for_trace = space_task_settings_for_user(target_user)
    _space_task_trace(
        "enqueue",
        target_user,
        viewer=viewer_username,
        request_id=request_id,
        cache_key=cache_key,
        revision=clean(settings_for_trace.get("updated_rev", "")),
        folders=settings_for_trace.get("preferred_folders", []),
        include_admin=bool(include_admin),
    )

    def _runner():
        build_started = time.time()
        _space_task_trace(
            "builder_start",
            target_user,
            viewer=viewer_username,
            request_id=request_id,
            cache_key=cache_key,
            revision=clean(settings_for_trace.get("updated_rev", "")),
            folders=settings_for_trace.get("preferred_folders", []),
        )
        try:
            build_progress_index = _space_task_progress_index_for_build(target_user, progress_index)
            build_viewer_progress_index = _space_task_progress_index_for_build(viewer_username, viewer_progress_index) if include_admin and viewer_username and viewer_username != target_user else viewer_progress_index
            payload = _space_task_payload_build_for_user(
                target_user,
                viewer_username,
                build_progress_index,
                time_index,
                include_admin=include_admin,
                viewer_progress_index=build_viewer_progress_index,
                viewer_time_index=viewer_time_index,
            )
            signature = _space_task_payload_runtime_signature(target_user, viewer_username, include_admin)
            current_settings = space_task_settings_for_user(target_user)
            if not _space_task_cached_payload_matches_settings(payload, current_settings):
                _space_task_trace(
                    "builder_discard_revision_mismatch",
                    target_user,
                    viewer=viewer_username,
                    request_id=request_id,
                    cache_key=cache_key,
                    revision=clean(current_settings.get("updated_rev", "")),
                    task_count=len(payload.get("tasks") or []) if isinstance(payload, dict) else 0,
                )
                return
            with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
                SPACE_TASK_PAYLOAD_RAM_CACHE[cache_key] = {
                    "payload": payload,
                    "signature": signature,
                    "at": time.time(),
                }
                _space_task_payload_cache_prune(cache_key)
            _space_task_trace(
                "builder_end",
                target_user,
                viewer=viewer_username,
                request_id=request_id,
                cache_key=cache_key,
                revision=clean(current_settings.get("updated_rev", "")),
                task_count=len(payload.get("tasks") or []) if isinstance(payload, dict) else 0,
                active_folders=len(payload.get("active_folders") or []) if isinstance(payload, dict) else 0,
                ms=round((time.time() - build_started) * 1000, 3),
            )
        except Exception as exc:
            stt_debug_log(
                "space_task_payload_refresh_failed",
                user=normalize_username(target_user),
                viewer=normalize_username(viewer_username),
                admin=bool(include_admin),
                error=str(exc),
            )
            _space_task_trace(
                "builder_error",
                target_user,
                viewer=viewer_username,
                request_id=request_id,
                cache_key=cache_key,
                error=str(exc),
                ms=round((time.time() - build_started) * 1000, 3),
            )
        finally:
            with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
                SPACE_TASK_PAYLOAD_REFRESH_INFLIGHT.pop(cache_key, None)
            space_task_payload_user_revision(target_user, bump=True)
            invalidate_response = globals().get("invalidate_lesson_tasks_response_cache")
            if callable(invalidate_response):
                invalidate_response(target_user)

    if not SPACE_TASK_PAYLOAD_REFRESH_TICKET.acquire(blocking=False):
        with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
            SPACE_TASK_PAYLOAD_REFRESH_INFLIGHT.pop(cache_key, None)
        stt_debug_log("space_task_payload_refresh_rejected", user=normalize_username(target_user), reason="queue_full")
        _space_task_trace("enqueue_rejected", target_user, viewer=viewer_username, request_id=request_id, cache_key=cache_key, reason="queue_full")
        space_task_payload_user_revision(target_user, bump=True)
        return False
    try:
        future = SPACE_TASK_PAYLOAD_REFRESH_EXECUTOR.submit(_runner)
    except Exception:
        SPACE_TASK_PAYLOAD_REFRESH_TICKET.release()
        with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
            SPACE_TASK_PAYLOAD_REFRESH_INFLIGHT.pop(cache_key, None)
        raise
    future.add_done_callback(lambda _done: SPACE_TASK_PAYLOAD_REFRESH_TICKET.release())
    return True


# Added 2026-07-21: folder mutations ACK durable settings and let the bounded shared pool build derived task cards.
def queue_space_task_payload_refresh_for_user(
    target_user: str,
    viewer_username: str = "",
    progress_index: dict[tuple[str, str], dict] | None = None,
    time_index: dict[str, dict] | None = None,
    include_admin: bool = False,
    viewer_progress_index: dict[tuple[str, str], dict] | None = None,
    viewer_time_index: dict[str, dict] | None = None,
) -> dict:
    target_user = normalize_username(target_user)
    viewer_username = normalize_username(viewer_username)
    settings = space_task_settings_for_user(target_user)
    if not settings.get("preferred_folders"):
        return space_task_payload_for_user(target_user, viewer_username, include_admin=include_admin)
    cache_key = _space_task_payload_cache_key(target_user, viewer_username, include_admin)
    pending = _space_task_pending_payload(target_user, settings)
    with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
        SPACE_TASK_PAYLOAD_RAM_CACHE[cache_key] = {
            "payload": pending,
            "signature": (),
            "at": time.time(),
            "refresh_started_at": 0.0,
        }
    scheduled = _refresh_space_task_payload_async(
        cache_key,
        target_user,
        viewer_username,
        progress_index,
        time_index,
        include_admin=include_admin,
        viewer_progress_index=viewer_progress_index,
        viewer_time_index=viewer_time_index,
    )
    _space_task_trace(
        "queue_pending_payload",
        target_user,
        viewer=viewer_username,
        cache_key=cache_key,
        revision=clean(settings.get("updated_rev", "")),
        folders=settings.get("preferred_folders", []),
        scheduled=bool(scheduled),
    )
    if scheduled:
        wait_ms = max(0, min(1500, int(os.environ.get("FUTURE_SPACE_TASK_COLD_READY_WAIT_MS", "350") or 350)))
        deadline = time.time() + (wait_ms / 1000.0)
        while time.time() < deadline:
            with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
                row = SPACE_TASK_PAYLOAD_RAM_CACHE.get(cache_key)
                ready_payload = row.get("payload") if isinstance(row, dict) and isinstance(row.get("payload"), dict) else None
            if (
                isinstance(ready_payload, dict)
                and not ready_payload.get("pending")
                and _space_task_cached_payload_matches_settings(ready_payload, settings)
            ):
                _space_task_trace(
                    "queue_return_ready_after_wait",
                    target_user,
                    viewer=viewer_username,
                    cache_key=cache_key,
                    revision=clean(settings.get("updated_rev", "")),
                    task_count=len(ready_payload.get("tasks") or []),
                    wait_ms=wait_ms,
                )
                return _space_task_payload_clone(ready_payload)
            time.sleep(0.02)
    if not scheduled:
        space_task_payload_user_revision(target_user, bump=True)
    return pending


# Added 2026-07-21: poll derived-payload readiness from RAM without rebuilding the full Task Board response.
def space_task_payload_refresh_status(
    target_user: str,
    viewer_username: str = "",
    include_admin: bool = False,
) -> dict:
    target_user = normalize_username(target_user)
    viewer_username = normalize_username(viewer_username)
    settings = space_task_settings_for_user(target_user)
    if not settings.get("preferred_folders"):
        return {"ready": True, "pending": False, "updated_rev": clean(settings.get("updated_rev", "")), "task_count": 0}
    cache_key = _space_task_payload_cache_key(target_user, viewer_username, include_admin)
    with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
        row = SPACE_TASK_PAYLOAD_RAM_CACHE.get(cache_key)
        payload = row.get("payload") if isinstance(row, dict) and isinstance(row.get("payload"), dict) else None
        inflight = bool(SPACE_TASK_PAYLOAD_REFRESH_INFLIGHT.get(cache_key))
    ready = bool(
        isinstance(payload, dict)
        and not payload.get("pending")
        and _space_task_cached_payload_matches_settings(payload, settings)
    )
    if not ready and not inflight:
        _refresh_space_task_payload_async(
            cache_key,
            target_user,
            viewer_username,
            include_admin=include_admin,
        )
        inflight = True
    _space_task_trace(
        "status",
        target_user,
        viewer=viewer_username,
        cache_key=cache_key,
        revision=clean(settings.get("updated_rev", "")),
        folders=settings.get("preferred_folders", []),
        ready=bool(ready),
        pending=not ready,
        inflight=bool(inflight),
        payload_pending=bool(isinstance(payload, dict) and payload.get("pending")),
        task_count=len(payload.get("tasks") or []) if isinstance(payload, dict) else 0,
    )
    return {
        "ready": ready,
        "pending": not ready,
        "updated_rev": clean(settings.get("updated_rev", "")),
        "task_count": len(payload.get("tasks") or []) if ready and isinstance(payload, dict) else 0,
        "queued": inflight,
    }


def space_task_payload_for_user(
    target_user: str,
    viewer_username: str = "",
    progress_index: dict[tuple[str, str], dict] | None = None,
    time_index: dict[str, dict] | None = None,
    include_admin: bool = False,
    viewer_progress_index: dict[tuple[str, str], dict] | None = None,
    viewer_time_index: dict[str, dict] | None = None,
) -> dict:
    target_user = normalize_username(target_user)
    if not target_user:
        return {"enabled": False, "preferred_folders": [], "folders": [], "active_folders": [], "tasks": []}
    cache_key = _space_task_payload_cache_key(target_user, viewer_username, include_admin)
    current_settings = space_task_settings_for_user(target_user)
    if not current_settings.get("preferred_folders"):
        space_task_assignments_for_active_paths(target_user, [])
        payload = _space_task_empty_opt_in_payload(current_settings)
        with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
            SPACE_TASK_PAYLOAD_RAM_CACHE[cache_key] = {
                "payload": payload,
                "signature": _space_task_payload_runtime_signature(target_user, viewer_username, include_admin),
                "at": time.time(),
            }
        return _space_task_payload_clone(payload)
    now = time.time()
    cached_row = None
    with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
        row = SPACE_TASK_PAYLOAD_RAM_CACHE.get(cache_key)
        if isinstance(row, dict):
            cached_row = {
                "payload": row.get("payload") if isinstance(row.get("payload"), dict) else None,
                "signature": row.get("signature"),
                "at": float(row.get("at", 0.0) or 0.0),
            }
        refresh_inflight = bool(SPACE_TASK_PAYLOAD_REFRESH_INFLIGHT.get(cache_key))
    if refresh_inflight and (not isinstance(cached_row, dict) or not isinstance(cached_row.get("payload"), dict) or cached_row.get("payload", {}).get("pending")):
        return _space_task_pending_payload(target_user, current_settings, stale_payload=cached_row.get("payload") if isinstance(cached_row, dict) else None)
    if isinstance(cached_row, dict) and isinstance(cached_row.get("payload"), dict):
        cache_age = now - float(cached_row.get("at", 0.0) or 0.0)
        current_settings = space_task_settings_for_user(target_user)
        # Added 2026-07-08: burst logins get the hot payload immediately; signature checks run only after the short hot window.
        if cache_age < 15.0 and _space_task_cached_payload_matches_settings(cached_row.get("payload"), current_settings):
            return _space_task_payload_clone(cached_row.get("payload"))
        if not _space_task_cached_payload_matches_settings(cached_row.get("payload"), current_settings):
            with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
                current_cached = SPACE_TASK_PAYLOAD_RAM_CACHE.get(cache_key)
                if isinstance(current_cached, dict) and current_cached.get("payload") is cached_row.get("payload"):
                    SPACE_TASK_PAYLOAD_RAM_CACHE.pop(cache_key, None)
        signature = _space_task_payload_runtime_signature(target_user, viewer_username, include_admin)
        if cached_row.get("signature") == signature and cache_age < float(SPACE_TASK_PAYLOAD_CACHE_TTL_SECONDS or 0.0) and _space_task_cached_payload_matches_settings(cached_row.get("payload"), current_settings):
            return _space_task_payload_clone(cached_row.get("payload"))
        _refresh_space_task_payload_async(
            cache_key,
            target_user,
            viewer_username,
            progress_index,
            time_index,
            include_admin=include_admin,
            viewer_progress_index=viewer_progress_index,
            viewer_time_index=viewer_time_index,
        )
        return _space_task_pending_payload(
            target_user,
            current_settings,
            stale_payload=cached_row.get("payload"),
        )
    if space_task_cold_async_enabled():
        return queue_space_task_payload_refresh_for_user(
            target_user,
            viewer_username,
            progress_index,
            time_index,
            include_admin=include_admin,
            viewer_progress_index=viewer_progress_index,
            viewer_time_index=viewer_time_index,
        )
    # Added 2026-07-10: coalesce cold Space Task builds so concurrent logins for
    # the same learner do not all scan folders and normalize the same tasks.
    build_event = None
    should_build = False
    with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
        row = SPACE_TASK_PAYLOAD_RAM_CACHE.get(cache_key)
        if isinstance(row, dict) and isinstance(row.get("payload"), dict):
            return _space_task_payload_clone(row.get("payload"))
        if isinstance(row, dict) and hasattr(row.get("cold_build_event"), "wait"):
            build_event = row.get("cold_build_event")
        else:
            build_event = threading.Event()
            SPACE_TASK_PAYLOAD_RAM_CACHE[cache_key] = {
                "cold_build_event": build_event,
                "cold_build_started_at": time.time(),
            }
            should_build = True
    if not should_build and build_event is not None:
        build_event.wait(8.0)
        with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
            row = SPACE_TASK_PAYLOAD_RAM_CACHE.get(cache_key)
            if isinstance(row, dict) and isinstance(row.get("payload"), dict):
                return _space_task_payload_clone(row.get("payload"))
    build_progress_index = _space_task_progress_index_for_build(target_user, progress_index)
    build_viewer_progress_index = _space_task_progress_index_for_build(viewer_username, viewer_progress_index) if include_admin and viewer_username and viewer_username != target_user else viewer_progress_index
    try:
        payload = _space_task_payload_build_for_user(
            target_user,
            viewer_username,
            build_progress_index,
            time_index,
            include_admin=include_admin,
            viewer_progress_index=build_viewer_progress_index,
            viewer_time_index=viewer_time_index,
        )
        signature = _space_task_payload_runtime_signature(target_user, viewer_username, include_admin)
        with SPACE_TASK_PAYLOAD_RAM_CACHE_LOCK:
            SPACE_TASK_PAYLOAD_RAM_CACHE[cache_key] = {
                "payload": payload,
                "signature": signature,
                "at": time.time(),
            }
            _space_task_payload_cache_prune(cache_key)
    finally:
        if should_build and build_event is not None:
            build_event.set()
    return _space_task_payload_clone(payload)
