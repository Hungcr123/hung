# Loaded by FUTURE.server_parts.08_progress_inventory_vocab into the shared Future server runtime namespace.
# Rebuilt 2026-07-06: minimal Space_V progress store, one record per user/file, no manifest rebuilds.


def space_v_progress_path(username: str) -> Path:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    return user_folder_path(username) / SPACE_V_PROGRESS_FILE_NAME


def space_v_progress_learned_count(record: dict) -> int:
    source = record if isinstance(record, dict) else {}
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    learned = state.get("learned") if isinstance(state.get("learned"), list) else []
    learned_words = state.get("learnedWords") if isinstance(state.get("learnedWords"), list) else []
    keys = {clean(item) for item in learned if clean(item)}
    for item in learned_words:
        if isinstance(item, dict):
            key = clean(item.get("key") or item.get("word") or item.get("text") or item.get("lemma"))
        else:
            key = clean(item)
        if key:
            keys.add(key)
    return max(
        0,
        len(keys),
        space_w_int(source.get("learnedCount", source.get("learned_count", 0)), 0),
        space_w_int(state.get("learnedCount", state.get("learned_count", 0)), 0),
    )


def normalize_space_v_terminal_progress_for_read(record: dict | None) -> dict | None:
    source = dict(record) if isinstance(record, dict) else None
    if not source:
        return source
    state = dict(source.get("state") if isinstance(source.get("state"), dict) else {})
    node_count = max(0, space_w_int(source.get("nodeCount", state.get("nodeCount", 0)), 0))
    node_index = max(0, space_w_int(source.get("nodeIndex", state.get("currentIndex", state.get("nodeIndex", 0))), 0))
    learned_count = space_v_progress_learned_count(source)
    active_run = truthy(source.get("activeRun"), False) or truthy(source.get("active_run"), False) or truthy(state.get("activeRun"), False) or truthy(state.get("active_run"), False)
    force_new = truthy(source.get("forceNewRun"), False) or truthy(state.get("forceNewRun"), False)
    if node_count and not active_run and not force_new and (learned_count >= node_count or node_index >= node_count):
        learned_count = node_count
        terminal_index = max(node_index, node_count)
        source["learnedCount"] = learned_count
        source["nodeIndex"] = terminal_index
        source["complete"] = True
        source["registryReady"] = True
        source["vocabComplete"] = True
        source["lessonComplete"] = True
        source["lessonCompletionSent"] = True
        source["activeRun"] = False
        source["active_run"] = False
        source["phase"] = "complete"
        state["learnedCount"] = learned_count
        state["nodeIndex"] = terminal_index
        state["currentIndex"] = terminal_index
        state["complete"] = True
        state["registryReady"] = True
        state["vocabComplete"] = True
        state["lessonComplete"] = True
        state["lessonCompletionSent"] = True
        state["activeRun"] = False
        state["active_run"] = False
        state["phase"] = "complete"
        source["state"] = state
    return source

def space_v_progress_key(username: str, relative_path: str = "", identity: str = "") -> str:
    return space_w_progress_key(username, relative_path, identity)


# Added 2026-07-06: makes Space_V progress use disk JSON as the source of truth across machines.
def clear_space_v_progress_ram_store(username: str = "") -> None:
    key = space_progress_store_entry_key("Space_V", username)
    with SPACE_PROGRESS_STORE_LOCK:
        row = SPACE_PROGRESS_STORE.get(key)
        lock = row.get("lock") if isinstance(row, dict) else None
        if lock is not None:
            SPACE_PROGRESS_STORE[key] = {"lock": lock}
        else:
            SPACE_PROGRESS_STORE.pop(key, None)


# Added 2026-07-06: direct disk reader for Space_V progress, bypassing the shared RAM/WAL progress cache.
def read_space_v_progress_disk_payload(username: str) -> dict:
    path = space_v_progress_path(username)
    if not path.is_file():
        return replay_space_progress_wal("Space_V", username, default_space_progress_payload())
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return replay_space_progress_wal("Space_V", username, normalize_space_progress_payload(payload))


# Added 2026-07-06: direct disk writer for Space_V progress so other clients see saved progress immediately.
def write_space_v_progress_disk_payload(username: str, payload: dict | None = None, merge_existing: bool = False) -> dict:
    path = space_v_progress_path(username)
    out = clone_space_progress_payload(payload)
    if merge_existing and path.is_file():
        existing = read_space_v_progress_disk_payload(username)
        existing_states = existing.get("states") if isinstance(existing.get("states"), dict) else {}
        out_states = out.setdefault("states", {})
        for old_key, old_record in existing_states.items():
            clean_key = clean(old_key)
            if not clean_key or not isinstance(old_record, dict):
                continue
            picked = space_progress_record_pick(old_record, out_states.get(clean_key))
            out_states[clean_key] = merge_space_progress_completion_history(old_record, picked, "Space_V")
    out["updated_at"] = utc_timestamp()
    atomic_write_json(path, out, indent=None)
    truncate_space_progress_wal("Space_V", username)
    invalidate_cached_payload(space_progress_cache_key("Space_V", username))
    clear_space_v_progress_ram_store(username)
    return out


def read_space_v_progress_file(username: str) -> dict:
    with space_progress_user_lock("Space_V", username):
        row = load_space_progress_store("Space_V", username)
        return clone_space_progress_payload(row.get("payload"))


def read_space_v_progress(username: str, relative_path: str = "", identity: str = "") -> dict | None:
    username = normalize_username(username)
    raw_path = clean_path_value(relative_path)
    raw_key = space_v_progress_key(username, raw_path, "")
    # Added 2026-07-20: return one shallow-isolated record without cloning every Space_V row for the user.
    with space_progress_user_lock("Space_V", username):
        payload = load_space_progress_store("Space_V", username).get("payload")
        payload = payload if isinstance(payload, dict) else {}
        states = payload.get("states", {}) if isinstance(payload.get("states"), dict) else {}
        record = states.get(raw_key)
        if isinstance(record, dict):
            return normalize_space_v_terminal_progress_for_read(record)
        raw_lower = raw_path.lower()
        for record in states.values():
            if not isinstance(record, dict):
                continue
            record_path_lower = clean_path_value(record.get("path", "")).lower()
            legacy_path_lower = clean_path_value(record.get("legacy_path", "")).lower()
            if raw_lower and (raw_lower == record_path_lower or raw_lower == legacy_path_lower):
                return normalize_space_v_terminal_progress_for_read(record)
    lookup = space_progress_lookup_for_request(username, raw_path, identity)
    source_path = clean_path_value(lookup.get("path", "")) or raw_path
    trusted_identity = clean(lookup.get("identity", ""))
    key = space_v_progress_key(username, source_path, trusted_identity)
    with space_progress_user_lock("Space_V", username):
        payload = load_space_progress_store("Space_V", username).get("payload")
        payload = payload if isinstance(payload, dict) else {}
        states = payload.get("states", {}) if isinstance(payload.get("states"), dict) else {}
        record = states.get(key)
        if isinstance(record, dict):
            return normalize_space_v_terminal_progress_for_read(record)
        source_lower = source_path.lower()
        identity_lower = trusted_identity.lower()
        for record in states.values():
            if not isinstance(record, dict):
                continue
            if source_lower and clean_path_value(record.get("path", "")).lower() == source_lower:
                return normalize_space_v_terminal_progress_for_read(record)
            if identity_lower and clean(record.get("identity", "")).lower() == identity_lower:
                return normalize_space_v_terminal_progress_for_read(record)
    return None


def space_v_progress_summary_from_record(record: dict) -> dict:
    source = normalize_space_v_terminal_progress_for_read(record) if isinstance(record, dict) else {}
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    total = max(0, space_w_int(source.get("nodeCount", state.get("nodeCount", 0)), 0))
    done = max(0, min(total or 10**9, space_v_progress_learned_count(source)))
    completed_marker = bool(
        source.get("complete")
        or source.get("completed")
        or source.get("lessonComplete")
        or source.get("lessonCompletionSent")
        or source.get("vocabComplete")
        or state.get("complete")
        or state.get("completed")
        or state.get("lessonComplete")
        or state.get("lessonCompletionSent")
        or state.get("vocabComplete")
    )
    if completed_marker and total:
        done = max(done, total)
    percent = 100 if total and done >= total else (max(0, min(99, int(round((done / total) * 100)))) if total else 0)
    completed_runs = max(0, space_w_int(source.get("completedRuns", source.get("completed_runs", 0)), 0))
    completed = bool(total and done >= total)
    active_run = bool(source.get("activeRun") or source.get("active_run") or state.get("activeRun") or state.get("active_run"))
    run_id = clean(source.get("runId") or source.get("run_id") or state.get("runId") or state.get("run_id"))
    if completed:
        completed_runs = max(completed_runs, 1)
    return {
        "space": "Space_V",
        "label": "Words",
        "done": done,
        "total": total,
        "percent": percent,
        "text": f"{done}/{total}" if total else str(done),
        "completed": completed,
        "in_progress": bool(not completed and (done > 0 or active_run)),
        "activeRun": active_run,
        "runId": run_id,
        "previously_completed": bool(completed_runs and not completed),
        "previouslyCompleted": bool(completed_runs and not completed),
        "completed_runs": completed_runs,
        "completedRuns": completed_runs,
        "updatedAt": clean(source.get("updatedAt") or source.get("savedAt")),
        "savedAt": clean(source.get("savedAt") or source.get("updatedAt")),
    }


# Added 2026-07-20: exposes a cheap dependency revision for conditional resume checks.
def space_v_progress_etag(record: dict | None, username: str = "", relative_path: str = "", identity: str = "") -> str:
    source = record if isinstance(record, dict) else {}
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    parts = (
        normalize_username(username).lower(),
        clean_path_value(relative_path).lower(),
        clean(identity or source.get("identity", "")).lower(),
        clean(source.get("_serverRevision") or source.get("serverRevision") or source.get("server_revision") or "0"),
        clean(source.get("savedAt") or source.get("saved_at") or state.get("savedAt") or state.get("saved_at") or ""),
        clean(source.get("updatedAt") or source.get("updated_at") or state.get("updatedAt") or state.get("updated_at") or ""),
        clean(source.get("runId") or source.get("run_id") or state.get("runId") or state.get("run_id") or ""),
        clean(source.get("nodeIndex") or state.get("currentIndex") or state.get("nodeIndex") or "0"),
        clean(source.get("learnedCount") or source.get("learned_count") or state.get("learnedCount") or state.get("learned_count") or "0"),
        "present" if source else "missing",
    )
    digest = hashlib.sha256("|".join(parts).encode("utf-8", "ignore")).hexdigest()[:24]
    return f'W/"space-v-progress-{digest}"'


# Added 2026-07-20: background autosaves need canonical ordering/progress fields, not the full drill/queue state echo.
def space_v_progress_compact_response(record: dict | None) -> dict:
    source = normalize_space_v_terminal_progress_for_read(record) if isinstance(record, dict) else {}
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    top_keys = (
        "version", "key", "path", "legacy_path", "identity", "title", "nodeIndex", "nodeCount",
        "learnedCount", "phase", "action", "savedAt", "updatedAt", "runId", "run_id", "complete",
        "completedRuns", "completed_runs", "completedAt", "completed_at", "completionRunId",
        "completion_run_id", "syncOperationId", "sync_operation_id", "learned", "_serverRevision",
    )
    state_keys = (
        "activeRun", "active_run", "currentIndex", "nodeIndex", "nodeCount", "learnedCount", "phase",
        "runId", "run_id", "savedAt", "reviewing", "reviewRun", "complete", "registryReady",
        "vocabComplete", "lessonComplete", "lessonCompletionSent", "newRun", "forceNewRun", "path",
        "effective_path", "link_target", "identity", "title", "syncOperationId", "sync_operation_id",
    )
    compact = {key: source[key] for key in top_keys if key in source}
    compact["state"] = {key: state[key] for key in state_keys if key in state}
    return compact


# Added 2026-07-21: fresh lesson opens must not rewrite progress just because the client minted a new sync ID/timestamp.
def space_v_progress_semantic_identity(record: dict | None) -> str:
    source = dict(record) if isinstance(record, dict) else {}
    for key in (
        "updatedAt", "updated_at", "savedAt", "saved_at", "_serverRevision", "serverRevision",
        "server_revision", "syncOperationId", "sync_operation_id", "pendingServerSync",
        "serverSyncedAt", "serverSyncedSavedAt", "action", "reason",
    ):
        source.pop(key, None)
    state = dict(source.get("state") if isinstance(source.get("state"), dict) else {})
    for key in (
        "updatedAt", "updated_at", "savedAt", "saved_at", "syncOperationId", "sync_operation_id",
        "pendingServerSync", "serverSyncedAt", "serverSyncedSavedAt", "lessonSource",
    ):
        state.pop(key, None)
    for key in ("path", "effective_path", "effectivePath", "link_target", "linkTarget", "linked_path", "linkedPath"):
        if not clean(state.get(key)):
            state.pop(key, None)
    source["state"] = state
    encoded = json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8", "ignore")).hexdigest()


# Added 2026-07-21: progress POSTs cannot erase server-enriched lesson metadata or a resolved link path.
def preserve_space_v_progress_context(existing: dict | None, record: dict | None) -> dict:
    old = existing if isinstance(existing, dict) else {}
    result = dict(record) if isinstance(record, dict) else {}
    old_state = old.get("state") if isinstance(old.get("state"), dict) else {}
    state = dict(result.get("state") if isinstance(result.get("state"), dict) else {})
    for key in ("path", "effective_path", "effectivePath", "link_target", "linkTarget", "linked_path", "linkedPath"):
        if not clean(state.get(key)) and clean(old_state.get(key)):
            state[key] = old_state[key]
    if isinstance(old_state.get("lessonSource"), dict):
        state["lessonSource"] = old_state["lessonSource"]
    result["state"] = state
    return result


def normalize_space_v_active_run_state(source: dict | None, state: dict | None, learned_count: int = 0) -> tuple[bool, int]:
    source_row = source if isinstance(source, dict) else {}
    state_row = state if isinstance(state, dict) else {}
    active_run = truthy(source_row.get("activeRun"), False) or truthy(state_row.get("activeRun"), False)
    explicit_learned = state_row.get("learned") if isinstance(state_row.get("learned"), list) else None
    normalized_count = max(0, space_w_int(learned_count, 0))
    if active_run and explicit_learned is not None:
        learned_keys = {clean(item) for item in explicit_learned if clean(item)}
        normalized_count = len(learned_keys)
        learned_words = state_row.get("learnedWords") if isinstance(state_row.get("learnedWords"), list) else []
        state_row["learnedWords"] = [
            item for item in learned_words
            if isinstance(item, dict) and clean(item.get("key") or item.get("word") or item.get("text") or item.get("lemma")) in learned_keys
        ] if learned_keys else []
    if active_run:
        state_row["learnedCount"] = normalized_count
        for marker in ("complete", "registryReady", "vocabComplete", "lessonComplete", "lessonCompletionSent"):
            state_row[marker] = False
    return active_run, normalized_count


def merge_space_v_progress_record(existing: dict | None, record: dict | None, force_new_run: bool = False) -> dict:
    old = existing if isinstance(existing, dict) else {}
    new = record if isinstance(record, dict) else {}
    old_epoch = space_progress_saved_epoch(old)
    new_epoch = space_progress_saved_epoch(new)
    if old and old_epoch is not None and new_epoch is not None and old_epoch > new_epoch:
        old_runs = lesson_progress_completed_runs(old, "Space_V")
        new_runs = lesson_progress_completed_runs(new, "Space_V")
        if not space_progress_completion_marker(new, "Space_V") and new_runs <= old_runs:
            # Added 2026-07-21: a stale active packet with no new lifetime history is a strict no-op.
            return dict(old)
    if force_new_run:
        old_state = old.get("state") if isinstance(old.get("state"), dict) else {}
        new_state = new.get("state") if isinstance(new.get("state"), dict) else {}
        old_run_id = clean(old.get("runId") or old.get("run_id") or old_state.get("runId") or old_state.get("run_id"))
        new_run_id = clean(new.get("runId") or new.get("run_id") or new_state.get("runId") or new_state.get("run_id"))
        if old and old_epoch is not None and new_epoch is not None and old_epoch > new_epoch:
            # A delayed/stale device cannot reset a newer run. Ordering is epoch-based.
            return merge_space_progress_completion_history(new, dict(old), "Space_V")
        if old_run_id and new_run_id and old_run_id == new_run_id and old_epoch == new_epoch:
            if space_v_progress_learned_count(old) > space_v_progress_learned_count(new):
                # A late duplicate New Study packet must not erase a same-run answer.
                return merge_space_progress_completion_history(new, dict(old), "Space_V")
        return merge_space_progress_completion_history(old, new, "Space_V")
    return merge_space_progress_newest(existing, record, "Space_V")


def save_space_v_progress(username: str, progress_payload: dict) -> dict:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    source = progress_payload if isinstance(progress_payload, dict) else {}
    identity_info = space_progress_identity_for_source(username, source, operation="write")
    rel_path = clean_path_value(identity_info.get("path", ""))
    identity = clean(identity_info.get("identity", ""))[:240]
    if not rel_path or not identity:
        missing = "path" if not rel_path else "identity"
        raise RuntimeError(f"Space_V progress missing {missing}.")
    key = clean(identity_info.get("key", "")) or space_v_progress_key(username, rel_path, identity)
    state = dict(source.get("state") if isinstance(source.get("state"), dict) else {})
    for heavy_key in ("words", "nodes", "effects", "sounds", "fx", "audio"):
        state.pop(heavy_key, None)
    now = utc_timestamp()
    learned_count = max(
        0,
        space_w_int(source.get("learnedCount", source.get("learned_count", 0)), 0),
        space_w_int(state.get("learnedCount", state.get("learned_count", 0)), 0),
        len({clean(item) for item in state.get("learned", []) if clean(item)}) if isinstance(state.get("learned"), list) else 0,
        len({
            clean(item.get("word") or item.get("key") or item.get("text") or item.get("lemma"))
            for item in (state.get("learnedWords") if isinstance(state.get("learnedWords"), list) else state.get("learned_words") if isinstance(state.get("learned_words"), list) else state.get("learnedVocabulary") if isinstance(state.get("learnedVocabulary"), list) else [])
            if isinstance(item, dict) and clean(item.get("word") or item.get("key") or item.get("text") or item.get("lemma"))
        }) if any(isinstance(state.get(key), list) for key in ("learnedWords", "learned_words", "learnedVocabulary")) else 0,
    )
    active_run, learned_count = normalize_space_v_active_run_state(source, state, learned_count)
    if learned_count:
        state["learnedCount"] = learned_count
    elif active_run:
        state["learnedCount"] = 0
    node_count = max(0, space_w_int(source.get("nodeCount", state.get("nodeCount", 0)), 0))
    node_index = max(0, space_w_int(source.get("nodeIndex", state.get("currentIndex", state.get("nodeIndex", 0))), 0))
    action = clean(source.get("action", ""))[:80]
    # Added 2026-07-26: an older frontend can autosave the final word with
    # activeRun still true; close the run when the payload proves completion.
    completion_payload = bool(
        action == "complete"
        or truthy(source.get("complete"), False)
        or truthy(state.get("complete"), False)
        or truthy(source.get("lessonComplete"), False)
        or truthy(state.get("lessonComplete"), False)
        or truthy(source.get("vocabComplete"), False)
        or truthy(state.get("vocabComplete"), False)
        or (node_count > 0 and learned_count >= node_count)
        or (node_count > 0 and node_index >= node_count)
    )
    if completion_payload:
        learned_count = max(learned_count, node_count)
        state["learnedCount"] = learned_count
        active_run = False
        state["activeRun"] = False
        state["active_run"] = False
        state["complete"] = True
        state["vocabComplete"] = True
        state["lessonComplete"] = True
        state["lessonCompletionSent"] = True
    force_new_run = action in {"new_run", "new-study", "new_study"} or truthy(state.get("forceNewRun"), False)
    record = {
        "version": 2,
        "key": key,
        "username": username,
        "path": rel_path,
        "legacy_path": clean_path_value(identity_info.get("legacy_path", "")),
        "identity": identity,
        "lesson_id": identity if identity.lower().startswith("ftg-lesson-") else "",
        "title": clean(source.get("title") or state.get("title") or "Space_V")[:180],
        "nodeIndex": node_index,
        "nodeCount": node_count,
        "learnedCount": learned_count,
        "phase": clean(source.get("phase") or state.get("phase")),
        "action": action,
        "reason": clean(source.get("reason", ""))[:120],
        "savedAt": clean(source.get("savedAt") or state.get("savedAt") or now)[:80],
        "updatedAt": now,
        "state": state,
    }
    completion_trace_id = clean(source.get("completion_trace_id") or state.get("completion_trace_id"))[:160]
    if completion_trace_id:
        record["completion_trace_id"] = completion_trace_id
        state["completion_trace_id"] = completion_trace_id
    for id_key in ("runId", "run_id", "sessionId", "session_id", "completionRunId", "completion_run_id", "completedAt", "completed_at", "syncOperationId", "sync_operation_id"):
        value = clean(source.get(id_key) or state.get(id_key))
        if value:
            record[id_key] = value[:160]
    if not active_run and bool(source.get("complete") or state.get("complete") or (node_count and learned_count >= node_count)):
        record["complete"] = True
        state["complete"] = True
    for marker in ("registryReady", "vocabComplete", "lessonComplete", "lessonCompletionSent"):
        if not active_run and (truthy(source.get(marker), False) or truthy(state.get(marker), False)):
            record[marker] = True
            state[marker] = True
    if active_run:
        record["complete"] = False
        for marker in ("complete", "registryReady", "vocabComplete", "lessonComplete", "lessonCompletionSent"):
            state[marker] = False
    if force_new_run:
        record["complete"] = False
        for marker in ("complete", "registryReady", "vocabComplete", "lessonComplete", "lessonCompletionSent"):
            state[marker] = False
        state["activeRun"] = True
        state["newRun"] = True
        state["forceNewRun"] = True
    wal_entry = None
    with space_progress_user_lock("Space_V", username):
        store = load_space_progress_store("Space_V", username)
        payload = store.get("payload") if isinstance(store.get("payload"), dict) else default_space_progress_payload()
        states = payload.setdefault("states", {})
        legacy_key = clean(identity_info.get("legacy_key", ""))
        existing, legacy_key = space_progress_existing_canonical_state(states, key, legacy_key, identity)
        operation_id = clean(record.get("syncOperationId") or record.get("sync_operation_id"))
        existing_operation_id = clean(existing.get("syncOperationId") or existing.get("sync_operation_id"))
        if operation_id and existing_operation_id == operation_id:
            return dict(existing)
        record = preserve_space_v_progress_context(existing, merge_space_v_progress_record(existing, record, force_new_run))
        if existing and space_v_progress_semantic_identity(existing) == space_v_progress_semantic_identity(record):
            return dict(existing)
        wal_entry = {"op": "upsert", "key": key, "record": record, "completion_event": source.get("_completionEvent")}
        remember_space_progress_store_entry(
            "Space_V",
            username,
            key,
            record,
            legacy_key=legacy_key,
            wal_entry=wal_entry,
            postgres_authoritative=True,
        )
    update_progress_index = globals().get("update_lesson_progress_index_cache_record")
    updated_progress_index = callable(update_progress_index) and update_progress_index(username, "Space_V", record)
    if not updated_progress_index:
        invalidate_progress_index = globals().get("invalidate_lesson_progress_index_cache")
        if callable(invalidate_progress_index):
            invalidate_progress_index(username)
    try:
        # Added 2026-07-09: patch both the effective file and link/display aliases so Lesson Vault rows update immediately.
        cache_paths = [
            rel_path,
            clean_path_value(identity_info.get("legacy_path", "")),
            clean_path_value(state.get("path", "")),
            clean_path_value(state.get("effective_path", "")),
            clean_path_value(state.get("effectivePath", "")),
            clean_path_value(state.get("link_target", "")),
            clean_path_value(state.get("linkTarget", "")),
            clean_path_value(state.get("linked_path", "")),
            clean_path_value(state.get("linkedPath", "")),
        ]
        progress_summary = space_v_progress_summary_from_record(record)
        patch_server_data_list_cache_study(cache_paths, {
            "title": record.get("title", "Space_V"),
            "nodes": node_count,
            "progress": progress_summary,
        }, username=username)
    except Exception:
        pass
    if bool(record.get("complete")):
        invalidate_space_task = globals().get("invalidate_space_task_payload_cache")
        if callable(invalidate_space_task):
            # Added 2026-07-09: a completed Space_V autosave should reveal the next auto task immediately.
            invalidate_space_task(username)
    return record


def clear_space_v_progress(username: str, progress_payload: dict) -> dict:
    username = normalize_username(username)
    source = progress_payload if isinstance(progress_payload, dict) else {}
    identity_info = space_progress_identity_for_source(username, source, operation="clear")
    key = clean(identity_info.get("key", "")) or space_v_progress_key(username, clean_path_value(identity_info.get("path", "")), clean(identity_info.get("identity", "")))
    with space_progress_user_lock("Space_V", username):
        payload = clone_space_progress_payload(load_space_progress_store("Space_V", username).get("payload"))
        states = payload.setdefault("states", {})
        existing = states.get(key) if isinstance(states.get(key), dict) else {}
        if space_progress_clear_is_stale(existing, source):
            return {"key": key, "removed": False, "stale": True, "progress": existing}
        removed = states.pop(key, None)
        remember_space_progress_store(
            "Space_V",
            username,
            payload,
            force=True,
            merge_existing=False,
            # Canonical clears must target the single (username, file_id) row;
            # the key alone is only a legacy RAM/WAL alias.
            wal_entry={
                "op": "remove",
                "key": key,
                "lesson_id": clean(identity_info.get("identity", "")),
            },
        )
    try:
        source_state = source.get("state") if isinstance(source.get("state"), dict) else {}
        clear_server_data_list_cache_paths([
            clean_path_value(identity_info.get("path", "")),
            clean_path_value(identity_info.get("legacy_path", "")),
            clean_path_value(source_state.get("path", "")),
            clean_path_value(source_state.get("effective_path", "")),
            clean_path_value(source_state.get("link_target", "")),
            clean_path_value(source_state.get("linked_path", "")),
        ])
    except Exception:
        pass
    invalidate_space_task = globals().get("invalidate_space_task_payload_cache")
    if callable(invalidate_space_task):
        # Added 2026-07-09: clearing Space_V progress can make an auto task active again.
        invalidate_space_task(username)
    return {"key": key, "removed": bool(removed)}
