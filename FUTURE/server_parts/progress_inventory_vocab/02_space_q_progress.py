# Loaded by FUTURE.server_parts.08_progress_inventory_vocab into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def space_q_progress_path(username: str) -> Path:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    return user_folder_path(username) / SPACE_Q_PROGRESS_FILE_NAME


def space_q_progress_key(username: str, relative_path: str = "", identity: str = "") -> str:
    return space_w_progress_key(username, relative_path, identity)


def read_space_q_progress_file(username: str) -> dict:
    path = space_q_progress_path(username)
    if not path.is_file():
        return {"version": 1, "states": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(payload, dict):
            states = payload.get("states") if isinstance(payload.get("states"), dict) else {}
            return {
                "version": int(payload.get("version", 1) or 1),
                "updated_at": clean(payload.get("updated_at", "")),
                "states": {clean(key): value for key, value in states.items() if clean(key) and isinstance(value, dict)},
            }
    except Exception:
        pass
    return {"version": 1, "states": {}}


def write_space_q_progress_file(username: str, payload: dict) -> None:
    path = space_q_progress_path(username)
    states = payload.get("states") if isinstance(payload.get("states"), dict) else {}
    out = {
        "version": 1,
        "updated_at": utc_timestamp(),
        "states": states,
    }
    atomic_write_json(path, out, indent=2)
    invalidate_cached_payload(f"space-q:{normalize_username(username).lower()}")


def read_space_q_progress(username: str, relative_path: str = "", identity: str = "") -> dict | None:
    username = normalize_username(username)
    if not space_progress_maybe_available("Space_Q", username):
        return None
    raw_path = clean_path_value(relative_path)
    raw_key = space_q_progress_key(username, raw_path, "")
    with space_progress_user_lock("Space_Q", username):
        row = load_space_progress_store("Space_Q", username)
        payload = row.get("payload") if isinstance(row, dict) and isinstance(row.get("payload"), dict) else {}
        states = payload.get("states", {}) if isinstance(payload.get("states"), dict) else {}
        record = states.get(raw_key)
        if isinstance(record, dict):
            return dict(record)
        raw_lower = raw_path.lower()
        for record in states.values():
            if not isinstance(record, dict):
                continue
            record_path_lower = clean_path_value(record.get("path", "")).lower()
            legacy_path_lower = clean_path_value(record.get("legacy_path", "")).lower()
            if raw_lower and (raw_lower == record_path_lower or raw_lower == legacy_path_lower):
                return dict(record)
    lookup = space_progress_lookup_for_request(username, raw_path, identity)
    source_path = clean_path_value(lookup.get("path", "")) or raw_path
    trusted_identity = clean(lookup.get("identity", ""))
    key = space_q_progress_key(username, source_path, trusted_identity)
    with space_progress_user_lock("Space_Q", username):
        row = load_space_progress_store("Space_Q", username)
        payload = row.get("payload") if isinstance(row, dict) and isinstance(row.get("payload"), dict) else {}
        states = payload.get("states", {}) if isinstance(payload.get("states"), dict) else {}
        record = states.get(key)
        if isinstance(record, dict):
            return dict(record)
        source_lower = source_path.lower()
        identity_lower = trusted_identity.lower()
        for record in states.values():
            if not isinstance(record, dict):
                continue
            if source_lower and clean_path_value(record.get("path", "")).lower() == source_lower:
                return dict(record)
            if identity_lower and clean(record.get("identity", "")).lower() == identity_lower:
                return dict(record)
    return None


# Added 2026-07-21: supports cheap cross-device revalidation of one Space_Q checkpoint.
def space_q_progress_etag(record: dict | None, username: str = "", relative_path: str = "", identity: str = "") -> str:
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
        clean(state.get("questionDone") or state.get("completedQuestions") or "0"),
        clean(state.get("questionTotal") or state.get("totalQuestions") or "0"),
        "1" if source.get("reviewing") or source.get("reviewRun") or state.get("reviewing") or state.get("reviewRun") else "0",
        "present" if source else "missing",
    )
    digest = hashlib.sha256("|".join(parts).encode("utf-8", "ignore")).hexdigest()[:24]
    return f'W/"space-q-progress-{digest}"'


def save_space_q_progress(username: str, progress_payload: dict) -> dict:
    username = normalize_username(username)
    source = progress_payload if isinstance(progress_payload, dict) else {}
    identity_info = space_progress_identity_for_source(username, source, operation="write")
    rel_path = clean_path_value(identity_info.get("path", ""))
    identity = clean(identity_info.get("identity", ""))
    key = clean(identity_info.get("key", "")) or space_q_progress_key(username, rel_path, identity)
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    state = dict(state)
    for heavy_key in ("nodes", "effects", "sounds", "fx"):
        state.pop(heavy_key, None)
    now = utc_timestamp()
    record = {
        "version": 1,
        "key": key,
        "username": username,
        "path": rel_path,
        "identity": identity[:240],
        "lesson_id": identity[:240] if identity.lower().startswith("ftg-lesson-") else "",
        "title": clean(source.get("title") or state.get("title") or "Space_Q")[:180],
        "nodeIndex": max(0, space_w_int(source.get("nodeIndex", state.get("currentIndex", state.get("nodeIndex", 0))))),
        "nodeCount": max(0, space_w_int(source.get("nodeCount", state.get("nodeCount", 0)))),
        "savedAt": clean(source.get("savedAt") or state.get("savedAt") or now)[:80],
        "updatedAt": now,
        "state": state,
    }
    for id_key in ("runId", "run_id", "sessionId", "session_id", "completionRunId", "completion_run_id", "completedAt", "completed_at", "syncOperationId", "sync_operation_id"):
        value = clean(source.get(id_key) or state.get(id_key))
        if value:
            record[id_key] = value[:160]
    if source.get("reviewing") or source.get("reviewRun") or state.get("reviewing") or state.get("reviewRun"):
        record["reviewing"] = True
        record["reviewRun"] = True
    with space_progress_user_lock("Space_Q", username):
        store = load_space_progress_store("Space_Q", username)
        payload = store.get("payload") if isinstance(store.get("payload"), dict) else default_space_progress_payload()
        states = payload.setdefault("states", {})
        legacy_key = clean(identity_info.get("legacy_key", ""))
        existing, legacy_key = space_progress_existing_canonical_state(states, key, legacy_key, identity)
        operation_id = clean(record.get("syncOperationId") or record.get("sync_operation_id"))
        existing_operation_id = clean(existing.get("syncOperationId") or existing.get("sync_operation_id"))
        if operation_id and existing_operation_id == operation_id:
            return dict(existing)
        record = merge_space_progress_newest(existing, record, "Space_Q")
        if existing and space_w_progress_semantic_identity(existing) == space_w_progress_semantic_identity(record):
            return dict(existing)
        wal_entry = {"op": "upsert", "key": key, "record": record, "completion_event": source.get("_completionEvent")}
        # Added 2026-07-21: one Space_Q checkpoint commits one SQLite delta before ACK; retries are no-ops.
        remember_space_progress_store_entry(
            "Space_Q",
            username,
            key,
            record,
            legacy_key=legacy_key,
            wal_entry=wal_entry,
            postgres_authoritative=True,
        )
    invalidate_progress_index = globals().get("invalidate_lesson_progress_index_cache")
    if callable(invalidate_progress_index):
        invalidate_progress_index(username)
    patch_lesson_vault_cache_for_space_progress(record, "Space_Q")
    invalidate_space_task_cache_after_space_progress(username, record, "Space_Q")
    return record


def clear_space_q_progress(username: str, progress_payload: dict) -> dict:
    username = normalize_username(username)
    source = progress_payload if isinstance(progress_payload, dict) else {}
    identity_info = space_progress_identity_for_source(username, source, operation="clear")
    key = clean(identity_info.get("key", "")) or space_q_progress_key(username, "", clean(identity_info.get("identity", "")))
    with space_progress_user_lock("Space_Q", username):
        payload = clone_space_progress_payload(load_space_progress_store("Space_Q", username).get("payload"))
        states = payload.setdefault("states", {})
        existing = states.get(key) if isinstance(states.get(key), dict) else {}
        if space_progress_clear_is_stale(existing, source):
            return {"key": key, "removed": False, "stale": True, "progress": existing}
        removed = states.pop(key, None)
        remember_space_progress_store(
            "Space_Q",
            username,
            payload,
            force=True,
            merge_existing=False,
            wal_entry={"op": "remove", "key": key, "lesson_id": clean(identity_info.get("identity", ""))},
        )
    invalidate_space_task_cache_after_space_progress(username, None, "Space_Q", force=True)
    return {"key": key, "removed": bool(removed)}
