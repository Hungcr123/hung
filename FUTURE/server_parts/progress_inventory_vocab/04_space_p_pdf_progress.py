# Loaded by FUTURE.server_parts.08_progress_inventory_vocab into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def space_p_progress_path(username: str) -> Path:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    return user_folder_path(username) / SPACE_P_PROGRESS_FILE_NAME


def space_p_progress_key(username: str, relative_path: str = "", identity: str = "") -> str:
    return space_w_progress_key(username, relative_path, identity)


# Added 2026-07-21: the shared paragraph route must preserve P/L/S identity for cache patches and history.
def normalize_paragraph_progress_space(value: object = "") -> str:
    raw = clean(value).lower().replace("-", "_")
    return {"space_l": "Space_L", "l": "Space_L", "space_s": "Space_S", "s": "Space_S"}.get(raw, "Space_P")


def read_space_p_progress_file(username: str) -> dict:
    path = space_p_progress_path(username)
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


def write_space_p_progress_file(username: str, payload: dict) -> None:
    path = space_p_progress_path(username)
    states = payload.get("states") if isinstance(payload.get("states"), dict) else {}
    out = {
        "version": 1,
        "updated_at": utc_timestamp(),
        "states": states,
    }
    atomic_write_json(path, out, indent=2)
    invalidate_cached_payload(f"space-p:{normalize_username(username).lower()}")


def read_space_p_progress(username: str, relative_path: str = "", identity: str = "") -> dict | None:
    username = normalize_username(username)
    if not space_progress_maybe_available("Space_P", username):
        return None
    raw_path = clean_path_value(relative_path)
    raw_key = space_p_progress_key(username, raw_path, "")
    with space_progress_user_lock("Space_P", username):
        row = load_space_progress_store("Space_P", username)
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
    key = space_p_progress_key(username, source_path, trusted_identity)
    with space_progress_user_lock("Space_P", username):
        row = load_space_progress_store("Space_P", username)
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


# Added 2026-07-21: supports cheap cross-device revalidation of one shared P/L/S checkpoint.
def space_p_progress_etag(record: dict | None, username: str = "", relative_path: str = "", identity: str = "") -> str:
    source = record if isinstance(record, dict) else {}
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    parts = (
        normalize_username(username).lower(),
        clean_path_value(relative_path).lower(),
        clean(identity or source.get("identity", "")).lower(),
        clean(source.get("space") or state.get("space") or state.get("spaceMode") or "Space_P"),
        clean(source.get("_serverRevision") or source.get("serverRevision") or source.get("server_revision") or "0"),
        clean(source.get("savedAt") or source.get("saved_at") or state.get("savedAt") or state.get("saved_at") or ""),
        clean(source.get("updatedAt") or source.get("updated_at") or state.get("updatedAt") or state.get("updated_at") or ""),
        clean(source.get("runId") or source.get("run_id") or state.get("runId") or state.get("run_id") or ""),
        clean(source.get("nodeIndex") or state.get("currentIndex") or state.get("nodeIndex") or "0"),
        clean(state.get("completedSegments") or state.get("segmentDone") or "0"),
        clean(state.get("totalSegments") or state.get("segmentTotal") or "0"),
        "1" if source.get("reviewing") or source.get("reviewRun") or state.get("reviewing") or state.get("reviewRun") else "0",
        "present" if source else "missing",
    )
    digest = hashlib.sha256("|".join(parts).encode("utf-8", "ignore")).hexdigest()[:24]
    return f'W/"space-p-progress-{digest}"'


def save_space_p_progress(username: str, progress_payload: dict) -> dict:
    username = normalize_username(username)
    source = progress_payload if isinstance(progress_payload, dict) else {}
    identity_info = space_progress_identity_for_source(username, source, operation="write")
    rel_path = clean_path_value(identity_info.get("path", ""))
    identity = clean(identity_info.get("identity", ""))
    key = space_p_progress_key(username, rel_path or clean_path_value(source.get("path", "")), identity)
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    state = dict(state)
    for heavy_key in ("nodes", "effects", "sounds", "fx", "audio"):
        state.pop(heavy_key, None)
    now = utc_timestamp()
    node_index_source = source.get("nodeIndex", state.get("currentIndex", state.get("nodeIndex", 0)))
    node_count_source = source.get("nodeCount", state.get("nodeCount", state.get("totalNodes", 0)))
    record = {
        "version": 1,
        "key": key,
        "username": username,
        "path": rel_path,
        "identity": identity[:240],
        "lesson_id": identity[:240] if identity.lower().startswith("ftg-lesson-") else "",
        "title": clean(source.get("title") or state.get("title") or "Space_P")[:180],
        "nodeIndex": max(0, space_w_int(node_index_source)),
        "nodeCount": max(0, space_w_int(node_count_source)),
        "savedAt": clean(source.get("savedAt") or state.get("savedAt") or now)[:80],
        "updatedAt": now,
        "state": state,
    }
    for id_key in ("runId", "run_id", "sessionId", "session_id", "completionRunId", "completion_run_id", "completedAt", "completed_at", "syncOperationId", "sync_operation_id"):
        value = clean(source.get(id_key) or state.get(id_key))
        if value:
            record[id_key] = value[:160]
    progress_space = normalize_paragraph_progress_space(source.get("space") or state.get("space") or state.get("spaceMode") or state.get("space_mode"))
    record["space"] = progress_space
    with space_progress_user_lock("Space_P", username):
        store = load_space_progress_store("Space_P", username)
        payload = store.get("payload") if isinstance(store.get("payload"), dict) else default_space_progress_payload()
        states = payload.setdefault("states", {})
        legacy_key = clean(identity_info.get("legacy_key", ""))
        existing, legacy_key = space_progress_existing_canonical_state(states, key, legacy_key, identity)
        operation_id = clean(record.get("syncOperationId") or record.get("sync_operation_id"))
        existing_operation_id = clean(existing.get("syncOperationId") or existing.get("sync_operation_id"))
        if operation_id and existing_operation_id == operation_id:
            return dict(existing)
        record = merge_space_progress_newest(existing, record, progress_space)
        if existing and space_w_progress_semantic_identity(existing) == space_w_progress_semantic_identity(record):
            return dict(existing)
        wal_entry = {"op": "upsert", "key": key, "record": record, "completion_event": source.get("_completionEvent")}
        # Added 2026-07-21: paragraph autosaves commit one SQLite delta before ACK and skip retry no-ops.
        remember_space_progress_store_entry(
            "Space_P",
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
    patch_lesson_vault_cache_for_space_progress(record, progress_space)
    invalidate_space_task_cache_after_space_progress(username, record, progress_space)
    return record


# Added 2026-07-21: compact ACKs carry only canonical ordering plus the shared route's P/L/S identity.
def space_p_progress_compact_response(record: dict | None) -> dict:
    source = record if isinstance(record, dict) else {}
    result = space_w_progress_compact_response(source)
    if clean(source.get("space")):
        result["space"] = clean(source.get("space"))
    return result


def clear_space_p_progress(username: str, progress_payload: dict) -> dict:
    username = normalize_username(username)
    source = progress_payload if isinstance(progress_payload, dict) else {}
    identity_info = space_progress_identity_for_source(username, source, operation="clear")
    key = space_p_progress_key(username, clean_path_value(identity_info.get("path", "")) or clean_path_value(source.get("path", "")), clean(identity_info.get("identity", "")))
    with space_progress_user_lock("Space_P", username):
        payload = clone_space_progress_payload(load_space_progress_store("Space_P", username).get("payload"))
        states = payload.setdefault("states", {})
        existing = states.get(key) if isinstance(states.get(key), dict) else {}
        if space_progress_clear_is_stale(existing, source):
            return {"key": key, "removed": False, "stale": True, "progress": existing}
        removed = states.pop(key, None)
        remember_space_progress_store(
            "Space_P",
            username,
            payload,
            force=True,
            merge_existing=False,
            wal_entry={"op": "remove", "key": key, "lesson_id": clean(identity_info.get("identity", ""))},
        )
    invalidate_space_task_cache_after_space_progress(username, None, clean(source.get("space") or "Space_P") or "Space_P", force=True)
    return {"key": key, "removed": bool(removed)}


def space_pdf_progress_path(username: str) -> Path:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    return user_folder_path(username) / SPACE_PDF_PROGRESS_FILE_NAME


def space_pdf_progress_key(username: str, relative_path: str = "", identity: str = "") -> str:
    stable_identity = clean(identity)[:240]
    if stable_identity.lower().startswith("ftg-lesson-"):
        return hashlib.sha256(f"{normalize_username(username).lower()}|identity:{stable_identity}".encode("utf-8")).hexdigest()[:32]
    key = space_progress_legacy_path_key(username, relative_path, identity)
    if key:
        return key
    return space_w_progress_key(username, "", identity)


# Added 2026-07-21: resolve manifest-known PDF/Picture identities without repeating filesystem stat/link work on every autosave.
def space_pdf_progress_manifest_path(username: str, raw_path: str = "") -> str:
    rel_path = clean_path_value(raw_path)
    if not rel_path:
        return ""
    top = rel_path.split("/", 1)[0].lower()
    if top not in {"common", normalize_username(username).lower()}:
        return ""
    manifest_lookup = globals().get("server_data_manifest_file_entry")
    if not callable(manifest_lookup):
        return ""
    entry = manifest_lookup(rel_path)
    if not isinstance(entry, dict) or clean(entry.get("type", "")).lower() != "file":
        return ""
    effective_path = clean_path_value(entry.get("link_target", "")) or rel_path
    effective_entry = manifest_lookup(effective_path) if effective_path != rel_path else entry
    if not isinstance(effective_entry, dict) or clean(effective_entry.get("type", "")).lower() != "file":
        return ""
    suffix = Path(effective_path).suffix.lower()
    return effective_path if suffix == ".pdf" or suffix in IMAGE_FILE_SUFFIXES else ""


def space_pdf_progress_identity_for_source(username: str, source: dict | None = None) -> dict:
    username = normalize_username(username)
    payload = source if isinstance(source, dict) else {}
    client_identity = clean(payload.get("lesson_id") or payload.get("lessonId") or payload.get("file_id") or payload.get("fileId") or payload.get("identity") or payload.get("lesson") or "")[:240]
    legacy_identity = clean(payload.get("identity") or payload.get("lesson") or "")[:240]
    lesson_handle = clean(payload.get("lesson_handle") or payload.get("lessonHandle"))
    raw_path = clean_path_value(payload.get("path", ""))
    manifest_path = space_pdf_progress_manifest_path(username, raw_path)
    rel_path = manifest_path or raw_path
    if raw_path and not manifest_path:
        try:
            target = safe_server_data_path(raw_path, username, admin=is_admin_user(username))
            effective = server_data_effective_file_path(target, username=username, admin=is_admin_user(username))
            effective_suffix = effective.suffix.lower()
            if not effective.is_file() or (effective_suffix != ".pdf" and effective_suffix not in IMAGE_FILE_SUFFIXES):
                raise RuntimeError("Chi duoc luu tien trinh cho file PDF/Picture trong server data.")
            rel_path = clean_path_value(server_data_relative(effective)) or raw_path
        except Exception:
            rel_path = raw_path
    manifest_reader = globals().get("server_data_manifest_file_entry")
    manifest_entry = manifest_reader(rel_path) if callable(manifest_reader) and rel_path else None
    package_lesson_id = clean((manifest_entry or {}).get("lesson_id", ""))[:240] if isinstance(manifest_entry, dict) and manifest_entry.get("package_backed") else ""
    identity = client_identity
    if lesson_handle:
        handle_row = validate_lesson_handle(username, client_identity or package_lesson_id, lesson_handle)
        identity = clean(handle_row.get("lesson_id", ""))[:240]
        handle_display_path = clean_path_value(handle_row.get("display_path", ""))
        handle_legacy_path = clean_path_value(handle_row.get("legacy_source_path", ""))
        display_mismatch = bool(handle_display_path and raw_path and handle_display_path.lower() != raw_path.lower())
        legacy_mismatch = bool(handle_legacy_path and rel_path and handle_legacy_path.lower() != rel_path.lower())
        if display_mismatch or legacy_mismatch:
            raise PermissionError("Lesson handle does not match this PDF path.")
    elif package_lesson_id:
        if client_identity.lower().startswith("ftg-lesson-") and client_identity != package_lesson_id:
            raise RuntimeError("PDF lesson ID does not match the selected package.")
        identity = package_lesson_id
    if identity.lower().startswith("ftg-lesson-"):
        legacy_identity = legacy_identity if not legacy_identity.lower().startswith("ftg-lesson-") else ""
    return {
        "path": rel_path,
        "legacy_path": raw_path,
        "identity": identity,
        "legacy_identity": legacy_identity,
        "lesson_handle": lesson_handle,
        "key": space_pdf_progress_key(username, rel_path or raw_path, identity),
        "legacy_key": space_progress_legacy_path_key(username, raw_path, legacy_identity),
    }


def _space_pdf_ai_fast_relative_media_path(value: object) -> str:
    # Added 2026-07-10: avoid repeated filesystem identity resolution on hot MishiKa question/progress routes.
    rel_path = clean_path_value(value)
    if not rel_path:
        return ""
    parts = [part for part in rel_path.split("/") if part]
    if not parts or any(part in {".", ".."} for part in parts):
        return ""
    suffix = Path(rel_path).suffix.lower()
    if suffix == ".pdf" or suffix in IMAGE_FILE_SUFFIXES:
        return rel_path
    return ""


def read_space_pdf_progress_file(username: str) -> dict:
    path = space_pdf_progress_path(username)
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


def write_space_pdf_progress_file(username: str, payload: dict) -> None:
    path = space_pdf_progress_path(username)
    states = payload.get("states") if isinstance(payload.get("states"), dict) else {}
    out = {
        "version": 1,
        "updated_at": utc_timestamp(),
        "states": states,
    }
    atomic_write_json(path, out, indent=2)
    invalidate_cached_payload(f"space-pdf:{normalize_username(username).lower()}")


def read_space_pdf_progress(username: str, relative_path: str = "", identity: str = "", lesson_id: str = "", lesson_handle: str = "") -> dict | None:
    username = normalize_username(username)
    identity_info = space_pdf_progress_identity_for_source(username, {
        "path": relative_path,
        "identity": identity,
        "lesson_id": lesson_id,
        "lesson_handle": lesson_handle,
    })
    record_canonical_identity_resolution("pdf_progress.read", identity_info)
    key = clean(identity_info.get("key", ""))
    legacy_key = clean(identity_info.get("legacy_key", ""))
    with space_progress_user_lock("Space_PDF", username):
        # Updated 2026-07-09: read the hot RAM row so a just-saved PDF/Picture page is visible before disk flush.
        payload = load_space_progress_store("Space_PDF", username).get("payload")
        states = payload.get("states", {}) if isinstance(payload.get("states", {}), dict) else {}
        record = states.get(key) or states.get(legacy_key)
        return record if isinstance(record, dict) and not record.get("_deleted") else None


def schedule_space_pdf_progress_startup_warm(delay: float = 1.5) -> None:
    def _warm() -> None:
        if delay > 0:
            time.sleep(delay)
        loaded = 0
        failed = 0
        started = time.perf_counter()
        try:
            usernames = list_dashboard_usernames()
        except Exception:
            usernames = []
        for username in usernames:
            if SERVER_STATE.get("shutdown_requested"):
                break
            try:
                progress_path = space_pdf_progress_path(username)
                wal_path = progress_path.with_name(f"{progress_path.name}.wal.jsonl")
                if not progress_path.is_file() and not wal_path.is_file():
                    continue
                load_space_progress_store("Space_PDF", username)
                loaded += 1
            except Exception:
                failed += 1
        SERVER_STATE["space_pdf_progress_warm"] = {
            "loaded": loaded,
            "failed": failed,
            "ms": int((time.perf_counter() - started) * 1000),
        }

    threading.Thread(target=_warm, daemon=True, name="future-space-pdf-progress-warm").start()

def space_pdf_progress_snapshot_for_path(username: str, relative_path: str = "") -> dict:
    username = normalize_username(username)
    rel_path = clean_path_value(relative_path)
    if not username or not rel_path:
        return {}
    try:
        info = space_progress_identity_for_path(rel_path, username, admin=is_admin_user(username))
        resolved_path = clean_path_value(info.get("path", "")) or rel_path
    except Exception:
        resolved_path = rel_path
    normalized_target = resolved_path.replace("\\", "/").strip("/").lower()
    candidates = {normalized_target}
    if rel_path.lower() != normalized_target:
        candidates.add(rel_path.replace("\\", "/").strip("/").lower())
    best = None
    best_updated = ""
    with space_progress_user_lock("Space_PDF", username):
        payload = load_space_progress_store("Space_PDF", username).get("payload")
        states = payload.get("states", {}) if isinstance(payload.get("states", {}), dict) else {}
        for record in states.values():
            if not isinstance(record, dict):
                continue
            if record.get("_deleted"):
                continue
            record_paths = [
                clean_path_value(record.get("path", "")),
            ]
            state = record.get("state") if isinstance(record.get("state"), dict) else {}
            record_paths.extend([
                clean_path_value(state.get("path", "")),
                clean_path_value(state.get("sourcePath", "")),
                clean_path_value(state.get("effectivePath", "")),
                clean_path_value(state.get("linkTarget", "")),
                clean_path_value(state.get("linkedPath", "")),
            ])
            if not any(path and path.replace("\\", "/").strip("/").lower() in candidates for path in record_paths):
                continue
            updated_at = clean(record.get("updatedAt", record.get("savedAt", "")))
            if best is None or timestamp_order_key(updated_at) >= timestamp_order_key(best_updated):
                best = record
                best_updated = updated_at
    if not isinstance(best, dict):
        return {}
    state = best.get("state") if isinstance(best.get("state"), dict) else {}
    raw_page = best.get("page") or state.get("page") or state.get("currentPage") or state.get("lastPage")
    if raw_page is None or clean(raw_page) == "":
        raw_node = best.get("currentNode", state.get("currentNode", best.get("nodeIndex", state.get("nodeIndex", 0))))
        one_based_node = space_w_int(best.get("nodeIndexBase", state.get("nodeIndexBase", 0)), 0) == 1 or space_w_int(best.get("version", 0), 0) >= 2
        raw_page = space_w_int(raw_node, 0) if one_based_node else space_w_int(raw_node, 0) + 1
    page = max(1, space_w_int(raw_page, 1))
    pages = max(0, space_w_int(best.get("pages") or state.get("pages") or state.get("totalPages") or state.get("nodeCount") or 0, 0))
    if not pages and page:
        pages = page
    return {
        "page": page,
        "pages": pages,
        "updatedAt": clean(best.get("updatedAt", best.get("savedAt", ""))),
    }


# Added 2026-07-09: keeps late Ghost Eye progress saves from wiping a newer selected/combined region.
def merge_space_pdf_ghost_state(existing: dict, incoming_state: dict, incoming_saved_at: str = "") -> dict:
    state = dict(incoming_state) if isinstance(incoming_state, dict) else {}
    existing_state = existing.get("state") if isinstance(existing.get("state"), dict) else {}
    existing_saved_at = clean(existing.get("savedAt", existing.get("updatedAt", "")))
    if not existing_state or not existing_saved_at or not incoming_saved_at or timestamp_order_key(existing_saved_at) <= timestamp_order_key(incoming_saved_at):
        return state
    ghost_keys = (
        "selection",
        "selections",
        "ocrText",
        "ocrRawText",
        "ocrFilteredText",
        "ocrViewMode",
        "exploreText",
        "translation",
        "translationVisible",
        "translationCache",
        "vocabStats",
        "ocrTab",
        "ghostConsoleVisible",
        "ghostConsoleFloating",
        "ghostConsolePosition",
        "translationPosition",
        "ocrMeta",
    )
    for key in ghost_keys:
        if key in existing_state:
            state[key] = existing_state.get(key)
    return state


# Added 2026-07-20: exact semantic retries must not create another SQLite revision or WAL write.
def space_pdf_progress_semantic_payload(record: dict | None = None) -> dict:
    def _clean_value(value):
        if isinstance(value, dict):
            return {
                key: _clean_value(item)
                for key, item in value.items()
                if key not in {"_serverRevision", "updatedAt", "savedAt", "pendingServerSync", "pinOnly"}
            }
        if isinstance(value, list):
            return [_clean_value(item) for item in value]
        return value

    return _clean_value(record if isinstance(record, dict) else {})


# Added 2026-07-20: Space_PDF ACKs only after its compact row is durable in authoritative SQLite.
def persist_space_pdf_progress_postgres(username: str, row: dict, payload: dict, entry: dict, revision: int) -> None:
    database_apply = globals().get("server_database_apply_progress_entry")
    if not callable(database_apply):
        raise RuntimeError("Server database progress writer is unavailable.")
    database_apply("Space_PDF", username, entry)
    with SPACE_PROGRESS_STORE_LOCK:
        row["payload"] = payload
        row["write_revision"] = max(max(0, space_w_int(row.get("write_revision", 0), 0)), max(0, revision))
        row["dirty"] = False
        row["force_flush"] = False
        row["merge_existing"] = False
        row["pending_wal_entries"] = []
        row["delta_flush_now"] = False
        row["wal_pending_compaction"] = False
        row["last_flush"] = time.time()
        row["touched_at"] = row["last_flush"]


def save_space_pdf_progress(username: str, progress_payload: dict) -> dict:
    username = normalize_username(username)
    source = progress_payload if isinstance(progress_payload, dict) else {}
    identity_info = space_pdf_progress_identity_for_source(username, source)
    record_canonical_identity_resolution("pdf_progress.write", identity_info)
    rel_path = clean_path_value(identity_info.get("path", ""))
    identity = clean(identity_info.get("identity", ""))
    key = space_pdf_progress_key(username, rel_path or source.get("path", ""), identity)
    legacy_key = clean(identity_info.get("legacy_key", ""))
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    state = dict(state)
    now = utc_timestamp()
    raw_page = source.get("page", state.get("page", None))
    if raw_page is None or clean(raw_page) == "":
        raw_node = source.get("currentNode", state.get("currentNode", source.get("nodeIndex", state.get("nodeIndex", 0))))
        one_based_node = space_w_int(source.get("nodeIndexBase", state.get("nodeIndexBase", 0)), 0) == 1 or space_w_int(source.get("version", 0), 0) >= 2
        page = max(1, space_w_int(raw_node, 0) if one_based_node else space_w_int(raw_node, 0) + 1)
    else:
        page = max(1, space_w_int(raw_page, 1))
    pages = max(0, space_w_int(source.get("pages", state.get("pages", source.get("nodeCount", 0))), 0))
    incoming_drawings = state.get("drawingLayers") if isinstance(state.get("drawingLayers"), dict) else None
    incoming_pinned_pages = source.get("pinnedPages") if isinstance(source.get("pinnedPages"), list) else state.get("pinnedPages")
    normalized_incoming_pins = [max(1, space_w_int(value, 0)) for value in incoming_pinned_pages if space_w_int(value, 0) > 0][:240] if isinstance(incoming_pinned_pages, list) else None
    incoming_pin_stamp = clean(source.get("pinnedPagesUpdatedAt") or state.get("pinnedPagesUpdatedAt"))[:80]
    incoming_recent_pages = source.get("recentPages") if isinstance(source.get("recentPages"), list) else state.get("recentPages")
    if isinstance(incoming_recent_pages, list):
        state["recentPages"] = [max(1, space_w_int(value, 0)) for value in incoming_recent_pages if space_w_int(value, 0) > 0][:240]
    state.update({"page": page, "pages": pages, "currentNode": page, "nodeIndex": page, "nodeIndexBase": 1})
    incoming_saved_at_raw = clean(source.get("savedAt") or state.get("savedAt"))[:80]
    incoming_saved_at = incoming_saved_at_raw or now
    immediate_pin_flush = False
    with space_progress_user_lock("Space_PDF", username):
        # Added 2026-07-09: mutate the hot Space_PDF progress row in RAM so page pins do not clone the whole user JSON on every click.
        row = load_space_progress_store("Space_PDF", username)
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else default_space_progress_payload()
        states = payload.setdefault("states", {})
        existing = states.get(key) if isinstance(states.get(key), dict) else {}
        if not existing and legacy_key and legacy_key != key and isinstance(states.get(legacy_key), dict):
            existing = states.get(legacy_key)
        existing_state = existing.get("state") if isinstance(existing.get("state"), dict) else {}
        existing_pins = existing.get("pinnedPages") if isinstance(existing.get("pinnedPages"), list) else existing_state.get("pinnedPages")
        normalized_existing_pins = [max(1, space_w_int(value, 0)) for value in existing_pins if space_w_int(value, 0) > 0][:240] if isinstance(existing_pins, list) else []
        existing_pin_stamp = clean(existing.get("pinnedPagesUpdatedAt") or existing_state.get("pinnedPagesUpdatedAt"))[:80]
        if not existing_pin_stamp and normalized_existing_pins:
            existing_pin_stamp = clean(existing.get("updatedAt") or existing.get("savedAt"))[:80]
        accept_incoming_pins = normalized_incoming_pins is not None and (
            not existing_pin_stamp
            or (
                incoming_pin_stamp
                and timestamp_order_key(incoming_pin_stamp) >= timestamp_order_key(existing_pin_stamp)
            )
        )
        if accept_incoming_pins:
            state["pinnedPages"] = normalized_incoming_pins
            state["pinnedPagesUpdatedAt"] = incoming_pin_stamp or incoming_saved_at or now
            immediate_pin_flush = normalized_incoming_pins != normalized_existing_pins
        else:
            state["pinnedPages"] = normalized_existing_pins
            if existing_pin_stamp:
                state["pinnedPagesUpdatedAt"] = existing_pin_stamp
        existing_saved_at = clean(existing.get("savedAt") or existing_state.get("savedAt") or existing.get("updatedAt"))[:80]
        existing_deleted = bool(existing.get("_deleted"))
        existing_page = max(1, space_w_int(existing.get("page", existing_state.get("page", 1)), 1))
        existing_epoch = timestamp_to_epoch(existing_saved_at) if existing_saved_at else 0.0
        incoming_epoch = timestamp_to_epoch(incoming_saved_at_raw) if incoming_saved_at_raw else 0.0
        same_instant = bool(existing_saved_at and incoming_saved_at_raw and timestamp_same_instant(existing_saved_at, incoming_saved_at_raw))
        existing_is_newer = bool(
            existing_saved_at
            and incoming_saved_at_raw
            and (
                (existing_epoch > 0 and incoming_epoch > 0 and existing_epoch > incoming_epoch + 0.001)
                or ((not existing_epoch or not incoming_epoch) and timestamp_order_key(existing_saved_at) > timestamp_order_key(incoming_saved_at_raw))
            )
        )
        incoming_is_stale = bool(
            existing
            and (
                not incoming_saved_at_raw
                or existing_is_newer
                or (same_instant and page < existing_page)
                or (existing_deleted and same_instant)
            )
        )
        if incoming_is_stale:
            selected_pins = list(state.get("pinnedPages", normalized_existing_pins))
            selected_pin_stamp = clean(state.get("pinnedPagesUpdatedAt") or existing_pin_stamp)
            state = dict(existing_state)
            state["pinnedPages"] = selected_pins
            if selected_pin_stamp:
                state["pinnedPagesUpdatedAt"] = selected_pin_stamp
            page = max(1, space_w_int(existing.get("page", state.get("page", page)), page))
            pages = max(0, space_w_int(existing.get("pages", state.get("pages", pages)), pages))
            state.update({"page": page, "pages": pages, "currentNode": page, "nodeIndex": page, "nodeIndexBase": 1})
        if incoming_drawings is None and isinstance(existing_state.get("drawingLayers"), dict):
            state["drawingLayers"] = existing_state.get("drawingLayers")
        state = merge_space_pdf_ghost_state(existing, state, incoming_saved_at)
        record = {
            "version": 2,
            "key": key,
            "username": username,
            "path": rel_path,
            "identity": identity[:240],
            "lesson_id": identity[:240] if identity.lower().startswith("ftg-lesson-") else "",
            "title": clean(source.get("title") or state.get("title") or "Space_PDF")[:180],
            "page": page,
            "pages": pages,
            "currentNode": page,
            "pinnedPages": state.get("pinnedPages", []),
            "pinnedPagesUpdatedAt": clean(state.get("pinnedPagesUpdatedAt", "")),
            "recentPages": state.get("recentPages", []),
            "nodeIndex": page,
            "nodeIndexBase": 1,
            "nodeCount": pages,
            "savedAt": existing_saved_at if incoming_is_stale else (incoming_saved_at or existing_saved_at or now),
            "updatedAt": now,
            "state": state,
        }
        if incoming_is_stale and existing_deleted:
            return existing
        if existing and not existing_deleted and space_pdf_progress_semantic_payload(existing) == space_pdf_progress_semantic_payload(record):
            return existing
        revision = max(
            max(0, space_w_int(row.get("write_revision", 0), 0)),
            max(0, space_w_int(existing.get("_serverRevision", 0), 0)),
        ) + 1
        record["_serverRevision"] = revision
        persist_space_pdf_progress_postgres(
            username,
            row,
            payload,
            {"op": "upsert", "key": key, "legacy_key": legacy_key, "record": record},
            revision,
        )
        states[key] = record
        if legacy_key and legacy_key != key:
            states.pop(legacy_key, None)
    bump_login_preload_cache_generation(username)
    patch_progress_index = globals().get("update_lesson_progress_index_cache_record")
    patched_progress_index = bool(callable(patch_progress_index) and patch_progress_index(username, "Space_PDF", record))
    if not patched_progress_index:
        invalidate_progress_index = globals().get("invalidate_lesson_progress_index_cache")
        if callable(invalidate_progress_index):
            invalidate_progress_index(username)
    return record


def clear_space_pdf_progress(username: str, progress_payload: dict) -> dict:
    username = normalize_username(username)
    source = progress_payload if isinstance(progress_payload, dict) else {}
    identity_info = space_pdf_progress_identity_for_source(username, source)
    record_canonical_identity_resolution("pdf_progress.clear", identity_info)
    key = space_pdf_progress_key(username, clean_path_value(identity_info.get("path", "")) or clean_path_value(source.get("path", "")), clean(identity_info.get("identity", "")))
    legacy_key = clean(identity_info.get("legacy_key", ""))
    with space_progress_user_lock("Space_PDF", username):
        row = load_space_progress_store("Space_PDF", username)
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else default_space_progress_payload()
        states = payload.setdefault("states", {})
        existing = states.get(key) if isinstance(states.get(key), dict) else {}
        if not existing and legacy_key and isinstance(states.get(legacy_key), dict):
            existing = states.get(legacy_key)
        if space_progress_clear_is_stale(existing, source):
            return {"key": key, "removed": False, "stale": True, "progress": existing}
        now = utc_timestamp()
        cleared_at = clean(source.get("savedAt") or source.get("updatedAt") or now)[:80]
        revision = max(
            max(0, space_w_int(row.get("write_revision", 0), 0)),
            max(0, space_w_int(existing.get("_serverRevision", 0), 0)),
        ) + 1
        tombstone = {
            "version": 1,
            "key": key,
            "username": username,
            "path": clean(existing.get("path") or identity_info.get("path") or source.get("path")),
            "identity": clean(existing.get("identity") or identity_info.get("identity"))[:240],
            "lesson_id": clean(identity_info.get("identity"))[:240] if clean(identity_info.get("identity")).lower().startswith("ftg-lesson-") else "",
            "title": clean(existing.get("title") or source.get("title") or "Space_PDF")[:180],
            "page": max(1, space_w_int(existing.get("page", source.get("page", 1)), 1)),
            "pages": max(0, space_w_int(existing.get("pages", source.get("pages", 0)), 0)),
            "nodeIndex": max(0, space_w_int(existing.get("nodeIndex", 0), 0)),
            "nodeCount": max(0, space_w_int(existing.get("nodeCount", source.get("pages", 0)), 0)),
            "savedAt": cleared_at,
            "updatedAt": now,
            "state": {},
            "_deleted": True,
            "_serverRevision": revision,
        }
        persist_space_pdf_progress_postgres(
            username,
            row,
            payload,
            {"op": "upsert", "key": key, "legacy_key": legacy_key, "record": tombstone},
            revision,
        )
        states[key] = tombstone
        if legacy_key and legacy_key != key:
            states.pop(legacy_key, None)
    bump_login_preload_cache_generation(username)
    invalidate_progress_index = globals().get("invalidate_lesson_progress_index_cache")
    if callable(invalidate_progress_index):
        invalidate_progress_index(username)
    return {"key": key, "removed": bool(existing and not existing.get("_deleted")), "serverRevision": revision}


def normalize_space_pdf_drawing_page(value: object = 1) -> int:
    return max(1, space_w_int(value, 1))


def normalize_space_pdf_drawing_data_url(value: object = "") -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) > 48 * 1024 * 1024:
        raise RuntimeError("PDF drawing is too large.")
    if not text.startswith("data:image/png;base64,"):
        raise RuntimeError("PDF drawing must be a PNG data URL.")
    return text


def normalize_space_pdf_drawing_vector(value: object = None) -> dict:
    if not isinstance(value, dict):
        return {}
    def _float(raw: object = 0, fallback: float = 0.0) -> float:
        try:
            return float(raw)
        except Exception:
            return fallback
    items = value.get("items")
    if not isinstance(items, list):
        return {}
    out_items = []
    for item in items[-600:]:
        if not isinstance(item, dict):
            continue
        kind = clean(item.get("kind", "")).lower()
        if kind in {"pen", "erase"}:
            raw_points = item.get("points")
            if not isinstance(raw_points, list):
                continue
            points = []
            for point in raw_points[:2400]:
                if not isinstance(point, dict):
                    continue
                try:
                    x = round(float(point.get("x", 0)), 1)
                    y = round(float(point.get("y", 0)), 1)
                except Exception:
                    continue
                if x < 0 or y < 0:
                    continue
                points.append({"x": x, "y": y})
            if not points:
                continue
            out_items.append({
                "kind": kind,
                "color": clean(item.get("color", ""))[:40] if kind == "pen" else "",
                "width": max(1, min(1400, _float(item.get("width", 1), 1))),
                "points": points,
            })
            continue
        if kind == "text":
            raw_lines = item.get("lines")
            if not isinstance(raw_lines, list):
                continue
            lines = []
            for line in raw_lines[:80]:
                if not isinstance(line, list):
                    continue
                segments = []
                for segment in line[:80]:
                    if not isinstance(segment, dict):
                        continue
                    text = str(segment.get("text", ""))[:1200]
                    if not text:
                        continue
                    segments.append({
                        "text": text,
                        "color": clean(segment.get("color", item.get("color", "")))[:40],
                    })
                if segments:
                    lines.append(segments)
            if not lines:
                continue
            out_items.append({
                "kind": "text",
                "x": max(0, round(_float(item.get("x", 0), 0), 1)),
                "y": max(0, round(_float(item.get("y", 0), 0), 1)),
                "font": clean(item.get("font", "Inter"))[:80],
                "fontSize": max(1, min(2400, _float(item.get("fontSize", 28), 28))),
                "lineHeight": max(1, min(2800, _float(item.get("lineHeight", item.get("fontSize", 28)), 28))),
                "bold": bool(item.get("bold")),
                "italic": bool(item.get("italic")),
                "color": clean(item.get("color", "#ffffff"))[:40],
                "lines": lines,
            })
    if not out_items:
        return {}
    vector = {
        "version": max(1, min(4, space_w_int(value.get("version", 2), 2))),
        "width": max(1, min(50000, space_w_int(value.get("width", 1), 1))),
        "height": max(1, min(50000, space_w_int(value.get("height", 1), 1))),
        "items": out_items,
    }
    if len(json.dumps(vector, ensure_ascii=False, separators=(",", ":"))) > 4 * 1024 * 1024:
        raise RuntimeError("PDF drawing vector is too large.")
    return vector


def space_pdf_drawing_document_key(relative_path: str = "", identity: str = "") -> str:
    rel_path = clean_path_value(relative_path).lower()
    identity_key = clean(identity).lower()
    if identity_key.startswith("ftg-lesson-"):
        return hashlib.sha256(f"lesson:{identity_key}".encode("utf-8")).hexdigest()[:32]
    return hashlib.sha256(f"{rel_path}|{identity_key}".encode("utf-8")).hexdigest()[:32]


# Added 2026-07-22: shared PDF/Picture child definitions use lesson_id while retaining path dual-read.
def space_pdf_child_document_key(relative_path: str = "", mode: object = "pdf", identity: str = "") -> str:
    normalized_mode = normalize_space_pdf_shared_audio_mode(mode)
    identity_key = clean(identity).lower()
    if identity_key.startswith("ftg-lesson-"):
        return hashlib.sha256(f"{normalized_mode}|lesson:{identity_key}".encode("utf-8")).hexdigest()[:32]
    rel_path = clean_path_value(relative_path)
    return hashlib.sha256(f"{normalized_mode}|{rel_path.lower()}".encode("utf-8")).hexdigest()[:32] if rel_path else ""


def normalize_space_pdf_drawing_record(value: object = None, *, page: int = 1) -> dict:
    source = value if isinstance(value, dict) else {}
    data_url = normalize_space_pdf_drawing_data_url(source.get("dataUrl", ""))
    vector = normalize_space_pdf_drawing_vector(source.get("vector"))
    if not data_url and not vector:
        return {}
    return {
        "page": page,
        "dataUrl": data_url,
        "vector": vector,
        "updatedAt": clean(source.get("updatedAt", "")),
        "updatedBy": clean(source.get("updatedBy", "")),
    }


def merge_space_pdf_drawing_vectors(existing: object = None, incoming: object = None) -> dict:
    def _scale_vector_to_size(vector: object = None, target_width: int = 10000, target_height: int = 10000) -> dict:
        normalized = normalize_space_pdf_drawing_vector(vector)
        if not normalized:
            return {}
        source_width = max(1, space_w_int(normalized.get("width", 1), 1))
        source_height = max(1, space_w_int(normalized.get("height", 1), 1))
        target_width = max(1, space_w_int(target_width, 10000))
        target_height = max(1, space_w_int(target_height, 10000))
        if source_width == target_width and source_height == target_height:
            return normalized
        scale_x = target_width / source_width
        scale_y = target_height / source_height
        scale_avg = (scale_x + scale_y) / 2
        scaled_items = []
        for item in normalized.get("items", []):
            if not isinstance(item, dict):
                continue
            kind = clean(item.get("kind", "")).lower()
            if kind in {"pen", "erase"}:
                scaled_items.append({
                    **item,
                    "width": max(1, float(item.get("width", 1)) * scale_avg),
                    "points": [
                        {
                            **point,
                            "x": float(point.get("x", 0)) * scale_x,
                            "y": float(point.get("y", 0)) * scale_y,
                        }
                        for point in item.get("points", [])
                        if isinstance(point, dict)
                    ],
                })
                continue
            if kind == "text":
                scaled_items.append({
                    **item,
                    "x": float(item.get("x", 0)) * scale_x,
                    "y": float(item.get("y", 0)) * scale_y,
                    "fontSize": max(1, float(item.get("fontSize", 28)) * scale_avg),
                    "lineHeight": max(1, float(item.get("lineHeight", item.get("fontSize", 28))) * scale_avg),
                })
        return normalize_space_pdf_drawing_vector({
            **normalized,
            "width": target_width,
            "height": target_height,
            "items": scaled_items,
        })

    existing_raw = normalize_space_pdf_drawing_vector(existing)
    incoming_raw = normalize_space_pdf_drawing_vector(incoming)
    target_width = max(10000, space_w_int(existing_raw.get("width", 1), 1), space_w_int(incoming_raw.get("width", 1), 1))
    target_height = max(10000, space_w_int(existing_raw.get("height", 1), 1), space_w_int(incoming_raw.get("height", 1), 1))
    existing_vector = _scale_vector_to_size(existing_raw, target_width, target_height)
    incoming_vector = _scale_vector_to_size(incoming_raw, target_width, target_height)
    if not existing_vector:
        return incoming_vector
    if not incoming_vector:
        return existing_vector
    existing_items = existing_vector.get("items") if isinstance(existing_vector.get("items"), list) else []
    incoming_items = incoming_vector.get("items") if isinstance(incoming_vector.get("items"), list) else []
    if not incoming_items:
        return existing_vector
    existing_keys = {
        json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for item in existing_items
        if isinstance(item, dict)
    }
    merged_items = list(existing_items)
    for item in incoming_items:
        if not isinstance(item, dict):
            continue
        item_key = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if item_key not in existing_keys:
            merged_items.append(item)
            existing_keys.add(item_key)
    return normalize_space_pdf_drawing_vector({
        "version": max(space_w_int(existing_vector.get("version", 2), 2), space_w_int(incoming_vector.get("version", 2), 2)),
        "width": max(space_w_int(existing_vector.get("width", 1), 1), space_w_int(incoming_vector.get("width", 1), 1)),
        "height": max(space_w_int(existing_vector.get("height", 1), 1), space_w_int(incoming_vector.get("height", 1), 1)),
        "items": merged_items,
    })


def read_space_pdf_drawing(username: str, relative_path: str = "", identity: str = "", page: object = 1, lesson_id: str = "", lesson_handle: str = "") -> dict:
    username = normalize_username(username)
    identity_info = space_pdf_progress_identity_for_source(username, {
        "path": relative_path,
        "identity": identity,
        "lesson_id": lesson_id,
        "lesson_handle": lesson_handle,
    })
    rel_path = clean_path_value(identity_info.get("path", ""))
    effective_identity = clean(identity_info.get("identity", ""))
    key = space_pdf_progress_key(username, rel_path, effective_identity)
    document_key = space_pdf_drawing_document_key(rel_path, effective_identity)
    page_number = normalize_space_pdf_drawing_page(page)
    row = server_database_read_pdf_drawing_row(username, document_key, page_number)
    if not row:
        legacy_document_key = space_pdf_drawing_document_key(rel_path, clean(identity_info.get("legacy_identity", "")))
        if legacy_document_key != document_key:
            row = server_database_read_pdf_drawing_row(username, legacy_document_key, page_number)
    if not row:
        row = server_database_read_pdf_drawing_row_by_path(username, rel_path, page_number)
    drawing = normalize_space_pdf_drawing_record(row.get("drawing"), page=page_number)
    if row.get("deleted"):
        return {
            "key": key,
            "page": page_number,
            "dataUrl": "",
            "vector": {},
            "updatedAt": clean(row.get("updated_at_utc", "")),
            "updatedBy": clean(row.get("updated_by", "")),
            "serverRevision": max(1, space_w_int(row.get("server_revision", 1), 1)),
            "operationId": clean(row.get("last_operation_id", "")),
            "deleted": True,
        }
    if drawing:
        return {
            "key": key,
            "page": page_number,
            "dataUrl": clean(drawing.get("dataUrl", "")),
            "vector": normalize_space_pdf_drawing_vector(drawing.get("vector")),
            "updatedAt": clean(drawing.get("updatedAt", "")),
            "updatedBy": clean(drawing.get("updatedBy", "")),
            "serverRevision": max(1, space_w_int(row.get("server_revision", 1), 1)),
            "operationId": clean(row.get("last_operation_id", "")),
        }
    return {
        "key": key,
        "page": page_number,
        "dataUrl": "",
        "vector": {},
        "updatedAt": "",
        "updatedBy": "",
        "serverRevision": 0,
        "operationId": "",
        "deleted": False,
    }


def save_space_pdf_drawing(username: str, drawing_payload: dict, updated_by: str = "") -> dict:
    username = normalize_username(username)
    source = drawing_payload if isinstance(drawing_payload, dict) else {}
    identity_info = space_pdf_progress_identity_for_source(username, source)
    rel_path = clean_path_value(identity_info.get("path", ""))
    identity = clean(identity_info.get("identity", ""))
    key = space_pdf_progress_key(username, rel_path or source.get("path", ""), identity)
    page = normalize_space_pdf_drawing_page(source.get("page", 1))
    document_key = space_pdf_drawing_document_key(rel_path, identity)
    legacy_document_key = space_pdf_drawing_document_key(rel_path, clean(identity_info.get("legacy_identity", "")))
    action = clean(source.get("action", "")).lower()
    now = utc_timestamp()
    has_base_revision = "baseRevision" in source or "base_revision" in source
    base_revision = max(0, space_w_int(source.get("baseRevision", source.get("base_revision", 0)), 0))
    incoming_updated_at = now if has_base_revision else normalize_timestamp_text(source.get("clientUpdatedAt", source.get("updatedAt", "")), fallback_now=True)
    incoming_epoch = max(0.0, timestamp_to_epoch(incoming_updated_at))
    updated_by_user = normalize_username(updated_by) or username
    removed = False
    drawing: dict = {}
    changed = False
    stale = False
    conflict = False
    revision = 0
    incoming_vector = normalize_space_pdf_drawing_vector(source.get("vector"))
    incoming_data_url = normalize_space_pdf_drawing_data_url(source.get("dataUrl", ""))
    incoming_hash_source = json.dumps(
        {"action": action, "dataUrl": incoming_data_url, "vector": incoming_vector},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    operation_id = clean(source.get("operationId") or source.get("operation_id"))[:160] or hashlib.sha256(
        f"{username.lower()}|{document_key}|{page}|{incoming_updated_at}|{incoming_hash_source}".encode("utf-8")
    ).hexdigest()
    with space_progress_user_lock("Space_PDF_Drawing", username):
        existing_row = server_database_read_pdf_drawing_row(username, document_key, page)
        if not existing_row and legacy_document_key != document_key:
            existing_row = server_database_read_pdf_drawing_row(username, legacy_document_key, page)
        if not existing_row:
            existing_row = server_database_read_pdf_drawing_row_by_path(username, rel_path, page)
        existing_drawing = normalize_space_pdf_drawing_record(existing_row.get("drawing"), page=page)
        existing_updated_at = clean(existing_drawing.get("updatedAt", ""))
        existing_epoch = max(0.0, float(existing_row.get("updated_epoch", 0.0) or timestamp_to_epoch(existing_updated_at)))
        revision = max(0, space_w_int(existing_row.get("server_revision", 0), 0))
        if operation_id and operation_id == clean(existing_row.get("last_operation_id", "")):
            drawing = existing_drawing
        elif has_base_revision and base_revision > revision:
            drawing = existing_drawing
            stale = True
            conflict = True
        elif has_base_revision and action in {"clear", "remove", "delete"} and base_revision < revision:
            drawing = existing_drawing
            stale = True
            conflict = True
        elif has_base_revision and existing_row.get("deleted") and base_revision < revision:
            stale = True
            conflict = True
        elif has_base_revision and existing_row and incoming_data_url and not incoming_vector and base_revision < revision:
            drawing = existing_drawing
            stale = True
            conflict = True
        elif not has_base_revision and existing_row and existing_epoch > incoming_epoch:
            drawing = existing_drawing
            stale = True
        elif not has_base_revision and existing_row.get("deleted") and existing_epoch >= incoming_epoch and action not in {"clear", "remove", "delete"}:
            stale = True
        elif action in {"clear", "remove", "delete"}:
            removed = bool(existing_drawing)
            tombstone = {
                "page": page,
                "dataUrl": "",
                "vector": {},
                "updatedAt": incoming_updated_at,
                "updatedBy": updated_by_user,
            }
            tombstone_json = json.dumps(tombstone, ensure_ascii=False, separators=(",", ":"), default=str)
            result = server_database_write_pdf_drawing_row(username, document_key, page, {
                "progress_key": key,
                "path": rel_path,
                "identity": identity[:240],
                "title": clean(source.get("title") or ("Space_Picture" if clean(source.get("mode", "")).lower() == "picture" else "Space_PDF"))[:180],
                "mode": "picture" if clean(source.get("mode", "")).lower() == "picture" else "pdf",
                "drawing": tombstone,
                "content_hash": hashlib.sha256(tombstone_json.encode("utf-8")).hexdigest(),
                "last_operation_id": operation_id,
                "deleted": True,
                "updated_at_utc": incoming_updated_at,
                "updated_epoch": incoming_epoch,
                "updated_by": updated_by_user,
            })
            revision = max(1, space_w_int(result.get("server_revision", 1), 1))
            changed = True
        else:
            vector = incoming_vector
            data_url = incoming_data_url
            existing_vector = normalize_space_pdf_drawing_vector(existing_drawing.get("vector"))
            if vector and existing_vector:
                vector = merge_space_pdf_drawing_vectors(existing_vector, vector)
            if not data_url and vector:
                data_url = clean(existing_drawing.get("dataUrl", ""))
            if data_url or vector:
                drawing = {
                    "page": page,
                    "dataUrl": data_url,
                    "vector": vector,
                    "updatedAt": incoming_updated_at,
                    "updatedBy": updated_by_user,
                }
                drawing_json = json.dumps(drawing, ensure_ascii=False, separators=(",", ":"), default=str)
                content_hash = hashlib.sha256(drawing_json.encode("utf-8")).hexdigest()
                if content_hash == clean(existing_row.get("content_hash", "")):
                    drawing = existing_drawing
                else:
                    result = server_database_write_pdf_drawing_row(username, document_key, page, {
                        "progress_key": key,
                        "path": rel_path,
                        "identity": identity[:240],
                        "title": clean(source.get("title") or ("Space_Picture" if clean(source.get("mode", "")).lower() == "picture" else "Space_PDF"))[:180],
                        "mode": "picture" if clean(source.get("mode", "")).lower() == "picture" else "pdf",
                        "drawing": drawing,
                        "content_hash": content_hash,
                        "last_operation_id": operation_id,
                        "deleted": False,
                        "updated_at_utc": incoming_updated_at,
                        "updated_epoch": incoming_epoch,
                        "updated_by": updated_by_user,
                    })
                    revision = max(1, space_w_int(result.get("server_revision", 1), 1))
                    changed = True
            elif existing_drawing:
                result = server_database_write_pdf_drawing_row(username, document_key, page, remove=True)
                removed = bool(result.get("removed"))
                changed = removed
                revision = 0
    return {
        "key": key,
        "page": page,
        "removed": removed,
        "changed": changed,
        "stale": stale,
        "conflict": conflict,
        "dataUrl": clean(drawing.get("dataUrl", "")),
        "vector": normalize_space_pdf_drawing_vector(drawing.get("vector")),
        "updatedAt": clean(drawing.get("updatedAt", "")),
        "updatedBy": clean(drawing.get("updatedBy", "")),
        "serverRevision": revision,
        "operationId": operation_id,
        "deleted": bool(
            (existing_row.get("deleted") and not changed)
            or (action in {"clear", "remove", "delete"} and changed and not stale)
        ),
    }


SPACE_PDF_AI_REGION_NOTICES_FILE = SERVER_DATA_ROOT / "_future_space_pdf_ai_region_notices.json"
SPACE_PDF_AI_REGION_NOTICES_LOCK = threading.RLock()
SPACE_PDF_AI_REGION_QUESTIONS_FILE = SERVER_DATA_ROOT / "_future_space_pdf_ai_region_questions.json"
SPACE_PDF_AI_REGION_QUESTIONS_LOCK = threading.RLock()
SPACE_PDF_AI_QUESTION_PROGRESS_FILE = SERVER_DATA_ROOT / "_future_space_pdf_ai_question_progress.json"
SPACE_PDF_AI_QUESTION_PROGRESS_LOCK = threading.RLock()
SPACE_PDF_AI_REGION_QUESTION_DEFAULT_VOICE = "kokoro:af_jessica"
SPACE_PDF_AI_JSON_STORE_LOCK = threading.RLock()
SPACE_PDF_AI_JSON_STORE_CACHE: dict[str, dict] = {}
SPACE_PDF_AI_JSON_STORE_FLUSH_INTERVAL_SECONDS = 1.5
SPACE_PDF_AI_JSON_STORE_FLUSHER_STARTED = False
SPACE_PDF_AI_REGION_NOTICES_PUBLIC_CACHE: dict[tuple, dict] = {}
SPACE_PDF_AI_REGION_QUESTIONS_PUBLIC_CACHE: dict[tuple, dict] = {}
SPACE_PDF_AI_REGION_QUESTIONS_PUBLIC_CACHE_LIMIT = 2048


def _space_pdf_ai_json_clone(value: object) -> dict:
    if not isinstance(value, dict):
        return {}
    try:
        return copy.deepcopy(value)
    except Exception:
        return dict(value)


def _space_pdf_ai_json_file_stamp(path: Path) -> tuple[int, int]:
    if str(os.environ.get("FUTURE_POSTGRES_ONLY", "") or "").strip().lower() in {"1", "true", "yes", "on"}:
        try:
            stat = path.stat()
            return int(stat.st_mtime_ns), int(stat.st_size)
        except Exception:
            return 0, 0
    _resolved, mtime_ns, size, _sha256 = server_database_document_signature(path)
    return mtime_ns, size


def _normalize_space_pdf_ai_json_store_payload(payload: object, root_key: str = "documents") -> dict:
    source = payload if isinstance(payload, dict) else {}
    rows = source.get(root_key) if isinstance(source.get(root_key), dict) else {}
    if root_key == "users":
        safe_rows = {
            normalize_username(key): value
            for key, value in rows.items()
            if clean(key) and isinstance(value, dict)
        }
    else:
        safe_rows = {
            clean(key): value
            for key, value in rows.items()
            if clean(key) and isinstance(value, dict)
        }
    return {
        "version": int(source.get("version", 1) or 1),
        "updated_at": clean(source.get("updated_at", "")),
        root_key: safe_rows,
    }


def _read_space_pdf_ai_json_store_disk(path: Path, root_key: str = "documents") -> dict:
    SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    return _normalize_space_pdf_ai_json_store_payload(
        server_database_read_document_json(path, {}),
        root_key,
    )


def _load_space_pdf_ai_json_store_locked(name: str, path: Path, root_key: str = "documents") -> dict:
    stamp = _space_pdf_ai_json_file_stamp(path)
    with SPACE_PDF_AI_JSON_STORE_LOCK:
        row = SPACE_PDF_AI_JSON_STORE_CACHE.get(name)
        if row and (row.get("dirty") or row.get("stamp") == stamp):
            return _space_pdf_ai_json_clone(row.get("payload"))
        payload = _read_space_pdf_ai_json_store_disk(path, root_key)
        SPACE_PDF_AI_JSON_STORE_CACHE[name] = {
            "path": path,
            "root_key": root_key,
            "payload": payload,
            "stamp": stamp,
            "dirty": False,
            "dirty_keys": set(),
            "dirty_nested_keys": set(),
            "last_dirty_at": 0.0,
        }
        return _space_pdf_ai_json_clone(payload)


# Added 2026-07-09: returns the live RAM store row so hot progress updates do not clone the whole JSON file.
def _space_pdf_ai_json_store_live_row(name: str, path: Path, root_key: str = "documents") -> dict:
    stamp = _space_pdf_ai_json_file_stamp(path)
    with SPACE_PDF_AI_JSON_STORE_LOCK:
        row = SPACE_PDF_AI_JSON_STORE_CACHE.get(name)
        if row and (row.get("dirty") or row.get("stamp") == stamp):
            return row
        payload = _read_space_pdf_ai_json_store_disk(path, root_key)
        row = {
            "path": path,
            "root_key": root_key,
            "payload": payload,
            "stamp": stamp,
            "dirty": False,
            "dirty_keys": set(),
            "dirty_nested_keys": set(),
            "last_dirty_at": 0.0,
        }
        SPACE_PDF_AI_JSON_STORE_CACHE[name] = row
        return row


def _remember_space_pdf_ai_json_store_locked(name: str, path: Path, payload: dict, root_key: str = "documents") -> None:
    normalized = _normalize_space_pdf_ai_json_store_payload(payload, root_key)
    with SPACE_PDF_AI_JSON_STORE_LOCK:
        row = SPACE_PDF_AI_JSON_STORE_CACHE.get(name)
        previous = row.get("payload") if isinstance(row, dict) else {}
        previous_rows = previous.get(root_key) if isinstance(previous.get(root_key), dict) else {}
        next_rows = normalized.get(root_key) if isinstance(normalized.get(root_key), dict) else {}
        dirty_keys = {key for key in set(previous_rows) | set(next_rows) if previous_rows.get(key) != next_rows.get(key)}
        dirty_nested_keys = set()
        if root_key == "users":
            for user_key in dirty_keys:
                previous_user_rows = previous_rows.get(user_key) if isinstance(previous_rows.get(user_key), dict) else {}
                next_user_rows = next_rows.get(user_key) if isinstance(next_rows.get(user_key), dict) else {}
                for record_key in set(previous_user_rows) | set(next_user_rows):
                    if previous_user_rows.get(record_key) != next_user_rows.get(record_key):
                        dirty_nested_keys.add((user_key, record_key))
        if row and isinstance(row.get("dirty_keys"), set):
            dirty_keys |= row.get("dirty_keys", set())
        if row and isinstance(row.get("dirty_nested_keys"), set):
            dirty_nested_keys |= row.get("dirty_nested_keys", set())
        SPACE_PDF_AI_JSON_STORE_CACHE[name] = {
            "path": path,
            "root_key": root_key,
            "payload": normalized,
            "stamp": _space_pdf_ai_json_file_stamp(path) if not row else row.get("stamp", (0, 0)),
            "dirty": True,
            "dirty_keys": dirty_keys,
            "dirty_nested_keys": dirty_nested_keys,
            "last_dirty_at": time.time(),
        }
    start_space_pdf_ai_json_store_flusher()


def _flush_space_pdf_ai_json_store_row(name: str, row: dict, force: bool = False) -> bool:
    path = row.get("path")
    root_key = clean(row.get("root_key", "documents")) or "documents"
    if not isinstance(path, Path):
        return False
    last_dirty_at = float(row.get("last_dirty_at", 0.0) or 0.0)
    if not force and time.time() - last_dirty_at < SPACE_PDF_AI_JSON_STORE_FLUSH_INTERVAL_SECONDS:
        return False
    cached = _normalize_space_pdf_ai_json_store_payload(row.get("payload"), root_key)
    cached_rows = cached.get(root_key) if isinstance(cached.get(root_key), dict) else {}
    dirty_keys = row.get("dirty_keys") if isinstance(row.get("dirty_keys"), set) else set(cached_rows)
    disk_payload = _read_space_pdf_ai_json_store_disk(path, root_key)
    merged_rows = disk_payload.get(root_key) if isinstance(disk_payload.get(root_key), dict) else {}
    merged_rows = dict(merged_rows)
    dirty_nested_keys = row.get("dirty_nested_keys") if isinstance(row.get("dirty_nested_keys"), set) else set()
    if root_key == "users" and dirty_nested_keys:
        for user_key, record_key in dirty_nested_keys:
            cached_user_rows = cached_rows.get(user_key) if isinstance(cached_rows.get(user_key), dict) else {}
            merged_user_rows = merged_rows.get(user_key) if isinstance(merged_rows.get(user_key), dict) else {}
            merged_user_rows = dict(merged_user_rows)
            if record_key in cached_user_rows:
                merged_user_rows[record_key] = cached_user_rows[record_key]
            else:
                merged_user_rows.pop(record_key, None)
            if merged_user_rows:
                merged_rows[user_key] = merged_user_rows
            else:
                merged_rows.pop(user_key, None)
    else:
        for key in dirty_keys:
            if key in cached_rows:
                merged_rows[key] = cached_rows[key]
            else:
                merged_rows.pop(key, None)
    out = {
        "version": 1,
        "updated_at": utc_timestamp(),
        root_key: merged_rows,
    }
    atomic_write_json(path, out, indent=2)
    with SPACE_PDF_AI_JSON_STORE_LOCK:
        latest = SPACE_PDF_AI_JSON_STORE_CACHE.get(name)
        if latest is row or latest and latest.get("last_dirty_at") == row.get("last_dirty_at"):
            SPACE_PDF_AI_JSON_STORE_CACHE[name] = {
                "path": path,
                "root_key": root_key,
                "payload": out,
                "stamp": _space_pdf_ai_json_file_stamp(path),
                "dirty": False,
                "dirty_keys": set(),
                "dirty_nested_keys": set(),
                "last_dirty_at": 0.0,
            }
    return True


def flush_space_pdf_ai_runtime_stores(force: bool = False) -> None:
    with SPACE_PDF_AI_JSON_STORE_LOCK:
        rows = [
            (name, dict(row))
            for name, row in SPACE_PDF_AI_JSON_STORE_CACHE.items()
            if isinstance(row, dict) and row.get("dirty")
        ]
    for name, row in rows:
        try:
            _flush_space_pdf_ai_json_store_row(name, row, force)
        except Exception as exc:
            print(f"Future PDF AI store flush failed for {name}: {exc}", flush=True)


def start_space_pdf_ai_json_store_flusher() -> None:
    global SPACE_PDF_AI_JSON_STORE_FLUSHER_STARTED
    with SPACE_PDF_AI_JSON_STORE_LOCK:
        if SPACE_PDF_AI_JSON_STORE_FLUSHER_STARTED:
            return
        SPACE_PDF_AI_JSON_STORE_FLUSHER_STARTED = True

    def _runner() -> None:
        while True:
            time.sleep(max(0.5, SPACE_PDF_AI_JSON_STORE_FLUSH_INTERVAL_SECONDS))
            flush_space_pdf_ai_runtime_stores(False)

    threading.Thread(target=_runner, daemon=True, name="future-pdf-ai-store-flusher").start()


atexit.register(lambda: flush_space_pdf_ai_runtime_stores(True))


def normalize_space_pdf_ai_notice_text(value: object = "", limit: int = 1800) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    return text[:max(0, int(limit or 0))] if limit and limit > 0 else text


SPACE_PDF_AI_NOTICE_FONTS = {
    "Inter",
    "Arial",
    "Georgia",
    "Times New Roman",
    "Verdana",
    "Tahoma",
    "Trebuchet MS",
    "Courier New",
}


def normalize_space_pdf_ai_notice_font(value: object = "", fallback: str = "Inter") -> str:
    font = clean(value)
    return font if font in SPACE_PDF_AI_NOTICE_FONTS else fallback


def normalize_space_pdf_ai_notice_display_mode(value: object = "type") -> str:
    mode = clean(value).lower()
    if mode in {"full", "instant", "static", "all"}:
        return "full"
    return "type"


def normalize_space_pdf_ai_notice_speak_mode(value: object = "once") -> str:
    mode = clean(value).lower().replace("-", "_")
    if mode in {"click", "when_click", "every", "always"}:
        return "click"
    if mode in {"off", "none", "silent"}:
        return "off"
    return "once"


def normalize_space_pdf_ai_notice_rect(value: object = None) -> dict:
    source = value if isinstance(value, dict) else {}

    def _num(name: str, fallback: float = 0.0) -> float:
        try:
            return float(source.get(name, fallback))
        except Exception:
            return fallback

    x = max(0.0, min(1.0, _num("x")))
    y = max(0.0, min(1.0, _num("y")))
    w = max(0.0, min(1.0, _num("w", _num("width"))))
    h = max(0.0, min(1.0, _num("h", _num("height"))))
    if x + w > 1.0:
        w = max(0.0, 1.0 - x)
    if y + h > 1.0:
        h = max(0.0, 1.0 - y)
    if w < 0.004 or h < 0.004:
        raise RuntimeError("Vung AI notice qua nho.")
    return {
        "x": round(x, 6),
        "y": round(y, 6),
        "w": round(w, 6),
        "h": round(h, 6),
    }


def normalize_space_pdf_ai_notice_item(item: dict | None = None, *, page: int = 1, mode: str = "pdf") -> dict:
    source = item if isinstance(item, dict) else {}
    notice_id = clean(source.get("id", ""))
    rect = normalize_space_pdf_ai_notice_rect(source.get("rect", source))
    text = normalize_space_pdf_ai_notice_text(source.get("text", source.get("message", source.get("notice", ""))))
    union_rects_raw = source.get("unionRects", source.get("union_rects", []))
    union_rects = [normalize_space_pdf_ai_notice_rect(u) for u in (union_rects_raw if isinstance(union_rects_raw, list) else []) if isinstance(u, dict)]
    union_rects = [r for r in union_rects if r.get("w", 0) >= 0.004 and r.get("h", 0) >= 0.004]
    voice, voice_label = _space_pdf_shared_audio_voice_details(source.get("voice", source.get("voiceKey", SPACE_PDF_SHARED_AUDIO_DEFAULT_VOICE)))
    audio_path = clean(source.get("audioPath", source.get("audio_path", "")))
    title = clean(source.get("title", "")) or (text.splitlines()[0][:56] if text else "AI notice")
    focus_text = normalize_space_pdf_ai_notice_text(source.get("focusText", source.get("focus_text", source.get("focus", source.get("hudText", source.get("hud_text", ""))))), 520)
    return {
        "id": notice_id,
        "page": normalize_space_pdf_drawing_page(source.get("page", page)),
        "mode": normalize_space_pdf_shared_audio_mode(source.get("mode", mode)),
        "rect": rect,
        "unionRects": union_rects,
        "text": text,
        "noticeTextHighlights": normalize_space_pdf_ai_question_highlights(source.get("noticeTextHighlights", source.get("notice_text_highlights", source.get("textHighlights", source.get("text_highlights", [])))), text),
        "noticeTextFont": normalize_space_pdf_ai_notice_font(source.get("noticeTextFont", source.get("notice_text_font", source.get("textFont", source.get("text_font", "Inter"))))),
        "focus_text": focus_text,
        "focusTextHighlights": normalize_space_pdf_ai_question_highlights(source.get("focusTextHighlights", source.get("focus_text_highlights", source.get("focusHighlights", source.get("focus_highlights", [])))), focus_text),
        "focusTextFont": normalize_space_pdf_ai_notice_font(source.get("focusTextFont", source.get("focus_text_font", source.get("focusFont", source.get("focus_font", "Inter"))))),
        "title": title[:120],
        "display_mode": normalize_space_pdf_ai_notice_display_mode(source.get("displayMode", source.get("display_mode", "type"))),
        "notice_style": clean(source.get("noticeStyle", source.get("notice_style", source.get("style", "fireball")))).lower() if clean(source.get("noticeStyle", source.get("notice_style", source.get("style", "fireball")))).lower() == "image" else "fireball",
        "image_src": normalize_space_pdf_ai_notice_text(source.get("imageSrc", source.get("image_src", source.get("imagePath", source.get("image_path", "")))), 240000),
        "notice_theme": "cyan" if clean(source.get("noticeTheme", source.get("notice_theme", source.get("theme", "red")))).lower() == "cyan" else "red",
        "voice": voice,
        "voice_label": clean(source.get("voiceLabel", source.get("voice_label", ""))) or voice_label,
        "speak_mode": normalize_space_pdf_ai_notice_speak_mode(source.get("speakMode", source.get("speak_mode", "once"))),
        "audio_text": normalize_space_pdf_ai_notice_text(source.get("audioText", source.get("audio_text", text)), 2400),
        "audio_path": audio_path,
        "audio_mime": _space_pdf_shared_audio_guess_mime(audio_path, clean(source.get("audioMime", source.get("audio_mime", "")))) if audio_path else "",
        "source_text": normalize_space_pdf_ai_notice_text(source.get("sourceText", source.get("source_text", "")), 2400),
        "created_at": clean(source.get("createdAt", source.get("created_at", ""))),
        "created_by": clean(source.get("createdBy", source.get("created_by", ""))),
        "updated_at": clean(source.get("updatedAt", source.get("updated_at", ""))),
        "updated_by": clean(source.get("updatedBy", source.get("updated_by", ""))),
    }


def _read_space_pdf_ai_region_notice_store_locked() -> dict:
    return _load_space_pdf_ai_json_store_locked(
        "region_notices",
        SPACE_PDF_AI_REGION_NOTICES_FILE,
        "documents",
    )


def _write_space_pdf_ai_region_notice_store_locked(payload: dict) -> None:
    _remember_space_pdf_ai_json_store_locked(
        "region_notices",
        SPACE_PDF_AI_REGION_NOTICES_FILE,
        payload,
        "documents",
    )


def read_space_pdf_ai_region_notices(username: str, relative_path: str = "", page: object = 1, mode: object = "pdf", lesson_id: str = "", lesson_handle: str = "") -> dict:
    viewer = normalize_username(username)
    normalized_mode = normalize_space_pdf_shared_audio_mode(mode)
    normalized_page = normalize_space_pdf_drawing_page(page)
    raw_rel_path = clean_path_value(relative_path)
    doc_info = space_pdf_progress_identity_for_source(viewer, {"path": raw_rel_path, "lesson_id": lesson_id, "lesson_handle": lesson_handle}) if raw_rel_path else {}
    rel_path = clean_path_value(doc_info.get("path", "")) or _space_pdf_ai_fast_relative_media_path(raw_rel_path)
    identity = clean(doc_info.get("identity", ""))
    if not rel_path:
        return {"key": "", "path": "", "page": normalized_page, "mode": normalized_mode, "notices": []}
    key = space_pdf_child_document_key(rel_path, normalized_mode, identity)
    legacy_key = space_pdf_child_document_key(rel_path, normalized_mode, "")
    cache_key = None
    with SPACE_PDF_AI_REGION_NOTICES_LOCK:
        store_row = _space_pdf_ai_json_store_live_row(
            "region_notices",
            SPACE_PDF_AI_REGION_NOTICES_FILE,
            "documents",
        )
        store_stamp = store_row.get("stamp", (0, 0))
        store_dirty_at = float(store_row.get("last_dirty_at", 0.0) or 0.0)
        cache_key = (normalized_mode, rel_path.lower(), normalized_page, store_stamp, store_dirty_at)
        cached = SPACE_PDF_AI_REGION_NOTICES_PUBLIC_CACHE.get(cache_key)
        if isinstance(cached, dict):
            return cached
        payload = store_row.get("payload") if isinstance(store_row.get("payload"), dict) else {}
        documents = payload.get("documents", {}) if isinstance(payload.get("documents", {}), dict) else {}
        document = documents.get(key) if isinstance(documents.get(key), dict) else {}
        if not document and legacy_key != key:
            document = documents.get(legacy_key) if isinstance(documents.get(legacy_key), dict) else {}
        if not document:
            document = next((
                value for value in documents.values()
                if isinstance(value, dict)
                and clean_path_value(value.get("path", "")).lower() == rel_path.lower()
                and normalize_space_pdf_shared_audio_mode(value.get("mode", normalized_mode)) == normalized_mode
            ), {})
        pages = document.get("pages") if isinstance(document.get("pages"), dict) else {}
        rows = pages.get(str(normalized_page)) if isinstance(pages.get(str(normalized_page)), list) else []
    notices = []
    for item in rows:
        if not isinstance(item, dict) or not clean(item.get("id", "")):
            continue
        try:
            normalized = normalize_space_pdf_ai_notice_item(item, page=normalized_page, mode=normalized_mode)
        except Exception:
            continue
        if clean(normalized.get("text", "")):
            notices.append(normalized)
    notices.sort(key=lambda item: (
        float(item.get("rect", {}).get("y", 0.0) or 0.0),
        float(item.get("rect", {}).get("x", 0.0) or 0.0),
        clean(item.get("updated_at", "")),
    ))
    result = {
        "key": key,
        "path": rel_path,
        "page": normalized_page,
        "mode": normalized_mode,
        "notices": notices,
    }
    with SPACE_PDF_AI_REGION_NOTICES_LOCK:
        if cache_key is not None:
            if len(SPACE_PDF_AI_REGION_NOTICES_PUBLIC_CACHE) > SPACE_PDF_AI_REGION_QUESTIONS_PUBLIC_CACHE_LIMIT:
                SPACE_PDF_AI_REGION_NOTICES_PUBLIC_CACHE.clear()
            SPACE_PDF_AI_REGION_NOTICES_PUBLIC_CACHE[cache_key] = result
    return result


def save_space_pdf_ai_region_notice(username: str, notice_payload: dict) -> dict:
    viewer = normalize_username(username)
    if not is_admin_user(viewer):
        raise RuntimeError("Only admins can update shared PDF/Picture AI notices.")
    source = notice_payload if isinstance(notice_payload, dict) else {}
    normalized_mode = normalize_space_pdf_shared_audio_mode(source.get("mode", "pdf"))
    doc_info = space_pdf_progress_identity_for_source(viewer, source) if clean_path_value(source.get("path", "")) else {}
    rel_path = clean_path_value(doc_info.get("path", ""))
    identity = clean(doc_info.get("identity", ""))
    normalized_page = normalize_space_pdf_drawing_page(source.get("page", 1))
    if not rel_path:
        raise RuntimeError("Thieu duong dan PDF/Picture.")
    key = hashlib.sha256(f"{normalized_mode}|{rel_path.lower()}".encode("utf-8")).hexdigest()[:32]
    page_key = str(normalized_page)
    action = clean(source.get("action", "save")).lower()
    notice_id = clean(source.get("id", ""))
    if action in {"remove", "delete"} and not notice_id:
        raise RuntimeError("Thieu ID cua AI notice.")
    now = utc_timestamp()
    removed = False
    with SPACE_PDF_AI_REGION_NOTICES_LOCK:
        payload = _read_space_pdf_ai_region_notice_store_locked()
        documents = payload.get("documents") if isinstance(payload.get("documents"), dict) else {}
        payload["documents"] = documents
        document = documents.get(key) if isinstance(documents.get(key), dict) else {}
        if not document:
            legacy_key = next((
                clean(item_key) for item_key, value in documents.items()
                if isinstance(value, dict)
                and clean_path_value(value.get("path", "")).lower() == rel_path.lower()
                and normalize_space_pdf_shared_audio_mode(value.get("mode", normalized_mode)) == normalized_mode
            ), "")
            if legacy_key and legacy_key != key:
                document = documents.pop(legacy_key, {}) if isinstance(documents.get(legacy_key), dict) else {}
        document.update({
            "key": key,
            "path": rel_path,
            "lesson_id": identity if identity.lower().startswith("ftg-lesson-") else "",
            "mode": normalized_mode,
            "updated_at": now,
            "updated_by": viewer,
        })
        pages = document.get("pages") if isinstance(document.get("pages"), dict) else {}
        rows = [item for item in (pages.get(page_key) if isinstance(pages.get(page_key), list) else []) if isinstance(item, dict)]
        existing_index = next((index for index, item in enumerate(rows) if clean(item.get("id", "")) == notice_id), -1)
        existing = rows[existing_index] if existing_index >= 0 else {}
        if action in {"remove", "delete"}:
            if existing_index >= 0:
                rows.pop(existing_index)
                removed = True
        else:
            text = normalize_space_pdf_ai_notice_text(source.get("text", source.get("message", existing.get("text", ""))))
            if not clean(text):
                raise RuntimeError("Nhap noi dung AI notice.")
            if not notice_id:
                notice_id = f"notice-{uuid.uuid4().hex[:12]}"
            rect = normalize_space_pdf_ai_notice_rect(source.get("rect", existing.get("rect", {})))
            union_rects_raw = source.get("unionRects", source.get("union_rects", existing.get("unionRects", existing.get("union_rects", []))))
            union_rects = [normalize_space_pdf_ai_notice_rect(u) for u in (union_rects_raw if isinstance(union_rects_raw, list) else []) if isinstance(u, dict)]
            union_rects = [r for r in union_rects if r.get("w", 0) >= 0.004 and r.get("h", 0) >= 0.004]
            voice, voice_label = _space_pdf_shared_audio_voice_details(source.get("voice", existing.get("voice", SPACE_PDF_SHARED_AUDIO_DEFAULT_VOICE)))
            audio_text = normalize_space_pdf_ai_notice_text(source.get("audioText", source.get("audio_text", existing.get("audioText", existing.get("audio_text", text)))), 2400)
            audio_path = clean(existing.get("audioPath", existing.get("audio_path", "")))
            audio_mime = clean(existing.get("audioMime", existing.get("audio_mime", "")))
            voice_changed = clean(voice).lower() != clean(existing.get("voice", "")).lower()
            audio_text_changed = audio_text != normalize_space_pdf_ai_notice_text(existing.get("audioText", existing.get("audio_text", "")), 2400)
            should_build_audio = action in {"build_audio", "set_voice"} or (audio_text and (not audio_path or voice_changed or audio_text_changed))
            if should_build_audio:
                if not audio_text:
                    raise RuntimeError("Nhap noi dung voice cho AI notice.")
                audio_payload = chat_synthesize_message_audio_queued(audio_text, voice)
                audio_path = normalize_space_pdf_shared_audio_link(audio_payload.get("audio_path", ""))
                audio_mime = clean(audio_payload.get("audio_mime", "")) or audio_mime
                voice = clean(audio_payload.get("voice", voice)) or voice
                voice_label = clean(audio_payload.get("voice_label", voice_label)) or voice_label
            elif "audioPath" in source or "audio_path" in source:
                audio_path = normalize_space_pdf_shared_audio_link(source.get("audioPath", source.get("audio_path", "")))
                audio_mime = clean(source.get("audioMime", source.get("audio_mime", audio_mime)))
            focus_text = normalize_space_pdf_ai_notice_text(source.get("focusText", source.get("focus_text", source.get("focus", source.get("hudText", source.get("hud_text", existing.get("focusText", existing.get("focus_text", ""))))))), 520)
            notice = {
                "id": notice_id,
                "page": normalized_page,
                "mode": normalized_mode,
                "rect": rect,
                "unionRects": union_rects,
                "text": text,
                "noticeTextHighlights": normalize_space_pdf_ai_question_highlights(source.get("noticeTextHighlights", source.get("notice_text_highlights", source.get("textHighlights", source.get("text_highlights", existing.get("noticeTextHighlights", existing.get("notice_text_highlights", existing.get("textHighlights", existing.get("text_highlights", [])))))))), text),
                "noticeTextFont": normalize_space_pdf_ai_notice_font(source.get("noticeTextFont", source.get("notice_text_font", source.get("textFont", source.get("text_font", existing.get("noticeTextFont", existing.get("notice_text_font", existing.get("textFont", existing.get("text_font", "Inter"))))))))),
                "focusText": focus_text,
                "focusTextHighlights": normalize_space_pdf_ai_question_highlights(source.get("focusTextHighlights", source.get("focus_text_highlights", source.get("focusHighlights", source.get("focus_highlights", existing.get("focusTextHighlights", existing.get("focus_text_highlights", existing.get("focusHighlights", existing.get("focus_highlights", [])))))))), focus_text),
                "focusTextFont": normalize_space_pdf_ai_notice_font(source.get("focusTextFont", source.get("focus_text_font", source.get("focusFont", source.get("focus_font", existing.get("focusTextFont", existing.get("focus_text_font", existing.get("focusFont", existing.get("focus_font", "Inter"))))))))),
                "displayMode": normalize_space_pdf_ai_notice_display_mode(source.get("displayMode", source.get("display_mode", existing.get("displayMode", existing.get("display_mode", "type"))))),
                "noticeStyle": clean(source.get("noticeStyle", source.get("notice_style", source.get("style", existing.get("noticeStyle", existing.get("notice_style", "fireball")))))).lower() if clean(source.get("noticeStyle", source.get("notice_style", source.get("style", existing.get("noticeStyle", existing.get("notice_style", "fireball")))))).lower() == "image" else "fireball",
                "imageSrc": normalize_space_pdf_ai_notice_text(source.get("imageSrc", source.get("image_src", source.get("imagePath", source.get("image_path", existing.get("imageSrc", existing.get("image_src", "")))))), 240000),
                "noticeTheme": "cyan" if clean(source.get("noticeTheme", source.get("notice_theme", source.get("theme", existing.get("noticeTheme", existing.get("notice_theme", "red")))))).lower() == "cyan" else "red",
                "voice": voice,
                "voiceLabel": voice_label,
                "speakMode": normalize_space_pdf_ai_notice_speak_mode(source.get("speakMode", source.get("speak_mode", existing.get("speakMode", existing.get("speak_mode", "once"))))),
                "audioText": audio_text,
                "audioPath": audio_path,
                "audioMime": _space_pdf_shared_audio_guess_mime(audio_path, audio_mime) if audio_path else "",
                "title": (clean(source.get("title", "")) or text.splitlines()[0])[:120],
                "sourceText": normalize_space_pdf_ai_notice_text(source.get("sourceText", source.get("source_text", existing.get("sourceText", ""))), 2400),
                "createdAt": clean(existing.get("createdAt", existing.get("created_at", ""))) or now,
                "createdBy": clean(existing.get("createdBy", existing.get("created_by", ""))) or viewer,
                "updatedAt": now,
                "updatedBy": viewer,
            }
            if existing_index >= 0:
                rows[existing_index] = notice
            else:
                rows.append(notice)
        if rows:
            pages[page_key] = rows
            document["pages"] = pages
            documents[key] = document
        else:
            pages.pop(page_key, None)
            if pages:
                document["pages"] = pages
                documents[key] = document
            else:
                documents.pop(key, None)
        payload["documents"] = documents
        _write_space_pdf_ai_region_notice_store_locked(payload)
        SPACE_PDF_AI_REGION_NOTICES_PUBLIC_CACHE.clear()
    snapshot = read_space_pdf_ai_region_notices(viewer, rel_path, normalized_page, normalized_mode)
    current_notice = next((item for item in snapshot.get("notices", []) if clean(item.get("id", "")) == notice_id), {})
    return {
        "key": key,
        "path": rel_path,
        "page": normalized_page,
        "mode": normalized_mode,
        "removed": removed,
        "notice": current_notice if isinstance(current_notice, dict) else {},
        "notices": snapshot.get("notices", []),
    }


def normalize_space_pdf_ai_question_answer(item: dict | None = None, *, index: int = 0) -> dict:
    source = item if isinstance(item, dict) else {}
    text = normalize_space_pdf_ai_notice_text(source.get("text", source.get("answer", "")), 1200)
    explanation_text = normalize_space_pdf_ai_notice_text(
        source.get("explanationText", source.get("explanation_text", source.get("explanation", ""))),
        2400,
    )
    voice, voice_label = _space_pdf_shared_audio_voice_details(
        source.get("explanationVoice", source.get("explanation_voice", source.get("voice", SPACE_PDF_AI_REGION_QUESTION_DEFAULT_VOICE)))
    )
    audio_path = normalize_space_pdf_shared_audio_link(source.get("audioPath", source.get("audio_path", "")))
    return {
        "id": clean(source.get("id", "")) or f"answer-{index + 1}",
        "text": text,
        "correct": bool(source.get("correct", source.get("isCorrect", False))),
        "explanationText": explanation_text,
        "explanationMode": normalize_space_pdf_ai_question_explanation_mode(source.get("explanationMode", source.get("explanation_mode", "text_voice"))),
        "explanationVoice": voice,
        "explanationVoiceLabel": clean(source.get("explanationVoiceLabel", source.get("explanation_voice_label", ""))) or voice_label,
        "audioPath": audio_path,
        "audioMime": _space_pdf_shared_audio_guess_mime(audio_path, clean(source.get("audioMime", source.get("audio_mime", "")))) if audio_path else "",
    }


def normalize_space_pdf_ai_question_explanation_mode(value: object = "text_voice") -> str:
    mode = clean(value).lower().replace("-", "_")
    if mode in {"text", "voice", "text_voice"}:
        return mode
    if mode in {"both", "textvoice", "speak", "once", "click"}:
        return "text_voice"
    if mode in {"off", "none", "silent"}:
        return "text"
    return "text_voice"


def normalize_space_pdf_ai_question_match_percent(value: object = 100) -> int:
    try:
        numeric = int(round(float(value)))
    except (TypeError, ValueError):
        numeric = 100
    return max(1, min(100, numeric))


def normalize_space_pdf_ai_question_type(value: object = "choice") -> str:
    raw = clean(value or "choice").lower().replace("-", "_").replace(" ", "_")
    if raw in {"input", "typed", "free", "text", "essay"}:
        return "input"
    if raw in {"theory", "theory_vi", "learn_theory", "read_theory"}:
        return "theory"
    if raw in {"speak_en", "speak_english", "speech_en", "read_en"}:
        return "speak_en"
    if raw in {"speak_vi", "speak_vn", "speak_vietnamese", "speech_vi", "read_vi"}:
        return "speak_vi"
    return "choice"


# Added 2026-07-02: preserves optional per-question MishiKa image URLs, local paths, and pasted data images.
def normalize_space_pdf_ai_question_image_src(value: object = "") -> str:
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return ""
    if len(text) > 2600000:
        raise RuntimeError("Question image is too large.")
    lowered = text.lower()
    if lowered.startswith(("http://", "https://", "data:image/", "blob:", "file://", "/server-data/asset?path=")):
        return text
    if ".." in [part.strip() for part in text.split("/")]:
        raise RuntimeError("Question image path is not valid.")
    return text


SPACE_PDF_AI_QUESTION_HIGHLIGHT_COLORS = {
    "gold": {"color": "#ffe78a"},
    "red": {"color": "#ff8aa0"},
    "cyan": {"color": "#7effe8"},
    "green": {"color": "#a7ffbd"},
    "violet": {"color": "#d9b7ff"},
    "rose": {"color": "#ff5d7f"},
    "orange": {"color": "#ffb25f"},
    "blue": {"color": "#7db7ff"},
    "lime": {"color": "#d8ff73"},
    "white": {"color": "#ffffff"},
}


def normalize_space_pdf_ai_question_highlight_color(value: object = "", fallback: str = "") -> str:
    raw = clean(value).strip()
    if re.match(r"^#[0-9a-fA-F]{6}$", raw):
        return raw.lower()
    if re.match(r"^#[0-9a-fA-F]{3}$", raw):
        body = raw[1:]
        return "#" + "".join(ch * 2 for ch in body).lower()
    return fallback


def normalize_space_pdf_ai_question_highlights(value: object = None, text: object = "") -> list[dict]:
    text_length = len(str(text or ""))
    rows = value if isinstance(value, list) else []
    normalized: list[dict] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        try:
            start = int(float(item.get("start", 0) or 0))
            end = int(float(item.get("end", 0) or 0))
        except (TypeError, ValueError):
            continue
        start = max(0, min(text_length, start))
        end = max(start, min(text_length, end))
        color_id = clean(item.get("colorId", item.get("color_id", ""))).lower()
        palette = SPACE_PDF_AI_QUESTION_HIGHLIGHT_COLORS.get(color_id)
        color = palette["color"] if isinstance(palette, dict) else normalize_space_pdf_ai_question_highlight_color(item.get("color", ""))
        if end <= start:
            continue
        font = normalize_space_pdf_ai_notice_font(item.get("font", item.get("fontFamily", item.get("font_family", ""))), "")
        bold = bool(item.get("bold", item.get("isBold", item.get("strong", False))))
        italic = bool(item.get("italic", item.get("isItalic", item.get("em", False))))
        if not color and not font and not bold and not italic:
            continue
        row = {
            "start": start,
            "end": end,
        }
        if color:
            row.update({
                "colorId": color_id if palette else "custom",
                "color": color,
            })
        if font:
            row["font"] = font
        if bold:
            row["bold"] = True
        if italic:
            row["italic"] = True
        normalized.append(row)
    return normalized[-80:]


def normalize_space_pdf_ai_question_timing_payload(value: object = None) -> dict:
    source = value if isinstance(value, dict) else {}
    timings: list[dict] = []
    for row in source.get("timings", []) if isinstance(source.get("timings", []), list) else []:
        if not isinstance(row, dict):
            continue
        try:
            start = max(0, int(float(row.get("s", row.get("start", row.get("startMs", 0))) or 0)))
            end = max(start + 1, int(float(row.get("e", row.get("end", row.get("endMs", 0))) or 0)))
        except (TypeError, ValueError):
            continue
        item = {"s": start, "e": end}
        token_index = row.get("i", row.get("index", row.get("word", None)))
        if token_index is not None:
            try:
                item["i"] = max(0, int(float(token_index or 0)))
            except (TypeError, ValueError):
                pass
        token_text = clean(row.get("t", row.get("text", row.get("wordText", ""))))
        if token_text:
            item["t"] = token_text[:80]
        timings.append(item)
    token_source = source.get("timing_tokens", source.get("timingTokens", []))
    timing_tokens: list[dict] = []
    for index, token in enumerate(token_source if isinstance(token_source, list) else []):
        if not isinstance(token, dict):
            continue
        text_value = clean(token.get("t", token.get("text", "")))
        if not text_value:
            continue
        try:
            start = max(0, int(float(token.get("s", index) or index)))
            end = max(start + 1, int(float(token.get("e", index + 1) or (index + 1))))
        except (TypeError, ValueError):
            start, end = index, index + 1
        timing_tokens.append({"t": text_value[:80], "s": start, "e": end})
    try:
        duration_ms = max(0, int(float(source.get("duration_ms", source.get("durationMs", 0)) or 0)))
    except (TypeError, ValueError):
        duration_ms = 0
    payload: dict = {}
    if duration_ms:
        payload["duration_ms"] = duration_ms
        payload["durationMs"] = duration_ms
    if timing_tokens:
        payload["timing_tokens"] = timing_tokens[:240]
        payload["timingTokens"] = timing_tokens[:240]
    if timings:
        payload["timings"] = timings[:240]
    return payload


def normalize_space_pdf_ai_question_item(item: dict | None = None, *, page: int = 1, mode: str = "pdf") -> dict:
    source = item if isinstance(item, dict) else {}
    question_id = clean(source.get("id", ""))
    rect = normalize_space_pdf_ai_notice_rect(source.get("rect", source))
    question = normalize_space_pdf_ai_notice_text(source.get("question", source.get("text", "")), 2400)
    union_rects_raw = source.get("unionRects", source.get("union_rects", []))
    union_rects = [normalize_space_pdf_ai_notice_rect(u) for u in (union_rects_raw if isinstance(union_rects_raw, list) else []) if isinstance(u, dict)]
    union_rects = [r for r in union_rects if r.get("w", 0) >= 0.004 and r.get("h", 0) >= 0.004]
    answers_raw = source.get("answers") if isinstance(source.get("answers"), list) else []
    answers = [normalize_space_pdf_ai_question_answer(answer, index=index) for index, answer in enumerate(answers_raw)]
    answers = [answer for answer in answers if answer.get("text")]
    if answers and not any(answer.get("correct") for answer in answers):
        answers[0]["correct"] = True
    image_src = normalize_space_pdf_ai_question_image_src(
        source.get(
            "imageSrc",
            source.get(
                "image_src",
                source.get("questionImage", source.get("question_image", source.get("imageUrl", source.get("image_url", "")))),
            ),
        )
    )
    image_alt = clean(source.get("imageAlt", source.get("image_alt", "")))[:180]
    region_name = clean(
        source.get(
            "regionName",
            source.get("region_name", source.get("aiQuestionRegionName", source.get("ai_question_region_name", ""))),
        )
    )[:120]
    return {
        "id": question_id,
        "page": normalize_space_pdf_drawing_page(source.get("page", page)),
        "mode": normalize_space_pdf_shared_audio_mode(source.get("mode", mode)),
        "rect": rect,
        "unionRects": union_rects,
        "regionName": region_name,
        "question": question,
        "imageSrc": image_src,
        "imageAlt": image_alt,
        "questionHighlights": normalize_space_pdf_ai_question_highlights(source.get("questionHighlights", source.get("question_highlights", [])), question),
        "title": (clean(source.get("title", "")) or question.splitlines()[0] if question else "AI question")[:120],
        "questionType": normalize_space_pdf_ai_question_type(source.get("questionType", source.get("question_type", "choice"))),
        "typedMatchPercent": normalize_space_pdf_ai_question_match_percent(
            source.get("typedMatchPercent", source.get("typed_match_percent", source.get("matchPercent", source.get("match_percent", 100))))
        ),
        "randomOrder": bool(source.get("randomOrder", source.get("random_order", False))),
        "pinned": bool(
            source.get(
                "pinned",
                source.get("pinNode", source.get("pin_node", source.get("pinnedNode", source.get("pinned_node", False)))),
            )
        ),
        "mikasaIntro": normalize_space_pdf_ai_notice_text(source.get("mikasaIntro", source.get("mikasa_intro", "")), 1200),
        "mikasaIntroHighlights": normalize_space_pdf_ai_question_highlights(
            source.get("mikasaIntroHighlights", source.get("mikasa_intro_highlights", [])),
            source.get("mikasaIntro", source.get("mikasa_intro", "")),
        ),
        "voice": clean(source.get("voice", SPACE_PDF_AI_REGION_QUESTION_DEFAULT_VOICE)) or SPACE_PDF_AI_REGION_QUESTION_DEFAULT_VOICE,
        "introAudioPath": normalize_space_pdf_shared_audio_link(source.get("introAudioPath", source.get("intro_audio_path", ""))),
        "introAudioMime": clean(source.get("introAudioMime", source.get("intro_audio_mime", ""))),
        "introTimingPayload": normalize_space_pdf_ai_question_timing_payload(source.get("introTimingPayload", source.get("intro_timing_payload", {}))),
        "answers": answers[:8],
        "created_at": clean(source.get("createdAt", source.get("created_at", ""))),
        "created_by": clean(source.get("createdBy", source.get("created_by", ""))),
        "updated_at": clean(source.get("updatedAt", source.get("updated_at", ""))),
        "updated_by": clean(source.get("updatedBy", source.get("updated_by", ""))),
    }


def _read_space_pdf_ai_region_question_store_locked() -> dict:
    return _load_space_pdf_ai_json_store_locked(
        "region_questions",
        SPACE_PDF_AI_REGION_QUESTIONS_FILE,
        "documents",
    )


def _write_space_pdf_ai_region_question_store_locked(payload: dict) -> None:
    _remember_space_pdf_ai_json_store_locked(
        "region_questions",
        SPACE_PDF_AI_REGION_QUESTIONS_FILE,
        payload,
        "documents",
    )


def read_space_pdf_ai_region_questions(username: str, relative_path: str = "", page: object = 1, mode: object = "pdf", lesson_id: str = "", lesson_handle: str = "") -> dict:
    viewer = normalize_username(username)
    normalized_mode = normalize_space_pdf_shared_audio_mode(mode)
    normalized_page = normalize_space_pdf_drawing_page(page)
    doc_info = space_pdf_progress_identity_for_source(viewer, {"path": relative_path, "lesson_id": lesson_id, "lesson_handle": lesson_handle}) if clean_path_value(relative_path) else {}
    rel_path = clean_path_value(doc_info.get("path", ""))
    identity = clean(doc_info.get("identity", ""))
    if not rel_path:
        return {"key": "", "path": "", "page": normalized_page, "mode": normalized_mode, "questions": []}
    key = space_pdf_child_document_key(rel_path, normalized_mode, identity)
    legacy_key = space_pdf_child_document_key(rel_path, normalized_mode, "")
    cache_key = None
    with SPACE_PDF_AI_REGION_QUESTIONS_LOCK:
        store_row = _space_pdf_ai_json_store_live_row(
            "region_questions",
            SPACE_PDF_AI_REGION_QUESTIONS_FILE,
            "documents",
        )
        store_stamp = store_row.get("stamp", (0, 0))
        store_dirty_at = float(store_row.get("last_dirty_at", 0.0) or 0.0)
        cache_key = (normalized_mode, rel_path.lower(), normalized_page, store_stamp, store_dirty_at)
        cached = SPACE_PDF_AI_REGION_QUESTIONS_PUBLIC_CACHE.get(cache_key)
        if isinstance(cached, dict):
            return cached
        payload = store_row.get("payload") if isinstance(store_row.get("payload"), dict) else {}
        documents = payload.get("documents", {}) if isinstance(payload.get("documents", {}), dict) else {}
        document = documents.get(key) if isinstance(documents.get(key), dict) else {}
        if not document and legacy_key != key:
            document = documents.get(legacy_key) if isinstance(documents.get(legacy_key), dict) else {}
        if not document:
            document = next((
                value for value in documents.values()
                if isinstance(value, dict)
                and clean_path_value(value.get("path", "")).lower() == rel_path.lower()
                and normalize_space_pdf_shared_audio_mode(value.get("mode", normalized_mode)) == normalized_mode
            ), {})
        pages = document.get("pages") if isinstance(document.get("pages"), dict) else {}
        rows = list(pages.get(str(normalized_page)) if isinstance(pages.get(str(normalized_page)), list) else [])
    questions = []
    for item in rows:
        if not isinstance(item, dict) or not clean(item.get("id", "")):
            continue
        try:
            normalized = normalize_space_pdf_ai_question_item(item, page=normalized_page, mode=normalized_mode)
        except Exception:
            continue
        if normalized.get("question") and isinstance(normalized.get("answers"), list):
            questions.append(normalized)
    questions.sort(key=lambda item: (
        float(item.get("rect", {}).get("y", 0.0) or 0.0),
        float(item.get("rect", {}).get("x", 0.0) or 0.0),
        clean(item.get("updated_at", "")),
    ))
    result = {
        "key": key,
        "path": rel_path,
        "page": normalized_page,
        "mode": normalized_mode,
        "questions": questions,
    }
    with SPACE_PDF_AI_REGION_QUESTIONS_LOCK:
        if cache_key is not None:
            if len(SPACE_PDF_AI_REGION_QUESTIONS_PUBLIC_CACHE) > SPACE_PDF_AI_REGION_QUESTIONS_PUBLIC_CACHE_LIMIT:
                SPACE_PDF_AI_REGION_QUESTIONS_PUBLIC_CACHE.clear()
            SPACE_PDF_AI_REGION_QUESTIONS_PUBLIC_CACHE[cache_key] = result
    return result


# Added 2026-07-09: warms all saved MishiKa PDF/Picture question regions at Server 2 startup.
def warm_space_pdf_ai_region_question_cache() -> dict:
    started = time.perf_counter()
    warmed_pages = 0
    warmed_questions = 0
    failed = 0
    with SPACE_PDF_AI_REGION_QUESTIONS_LOCK:
        store_row = _space_pdf_ai_json_store_live_row(
            "region_questions",
            SPACE_PDF_AI_REGION_QUESTIONS_FILE,
            "documents",
        )
        store_stamp = store_row.get("stamp", (0, 0))
        store_dirty_at = float(store_row.get("last_dirty_at", 0.0) or 0.0)
        payload = store_row.get("payload") if isinstance(store_row.get("payload"), dict) else {}
        documents = payload.get("documents") if isinstance(payload.get("documents"), dict) else {}
        for document in documents.values():
            if not isinstance(document, dict):
                continue
            rel_path = clean_path_value(document.get("path", ""))
            if not rel_path:
                continue
            normalized_mode = normalize_space_pdf_shared_audio_mode(document.get("mode", "pdf"))
            key = space_pdf_child_document_key(rel_path, normalized_mode, clean(document.get("lesson_id", "")))
            pages = document.get("pages") if isinstance(document.get("pages"), dict) else {}
            for page_key, rows in pages.items():
                if not isinstance(rows, list):
                    continue
                try:
                    normalized_page = normalize_space_pdf_drawing_page(page_key)
                    questions = []
                    for item in rows:
                        if not isinstance(item, dict) or not clean(item.get("id", "")):
                            continue
                        normalized = normalize_space_pdf_ai_question_item(item, page=normalized_page, mode=normalized_mode)
                        if normalized.get("question") and isinstance(normalized.get("answers"), list):
                            questions.append(normalized)
                    questions.sort(key=lambda item: (
                        float(item.get("rect", {}).get("y", 0.0) or 0.0),
                        float(item.get("rect", {}).get("x", 0.0) or 0.0),
                        clean(item.get("updated_at", "")),
                    ))
                    result = {
                        "key": key,
                        "path": rel_path,
                        "page": normalized_page,
                        "mode": normalized_mode,
                        "questions": questions,
                    }
                    cache_key = (normalized_mode, rel_path.lower(), normalized_page, store_stamp, store_dirty_at)
                    SPACE_PDF_AI_REGION_QUESTIONS_PUBLIC_CACHE[cache_key] = result
                    warmed_pages += 1
                    warmed_questions += len(questions)
                except Exception:
                    failed += 1
        if len(SPACE_PDF_AI_REGION_QUESTIONS_PUBLIC_CACHE) > SPACE_PDF_AI_REGION_QUESTIONS_PUBLIC_CACHE_LIMIT:
            SPACE_PDF_AI_REGION_QUESTIONS_PUBLIC_CACHE.clear()
    return {
        "pages": warmed_pages,
        "questions": warmed_questions,
        "failed": failed,
        "ms": int((time.perf_counter() - started) * 1000),
    }


# Added 2026-07-09: starts Mishika region cache warm without delaying HTTP startup.
def warm_space_pdf_ai_region_question_cache_async(delay_seconds: float = 0.4) -> None:
    def runner() -> None:
        if delay_seconds > 0:
            time.sleep(delay_seconds)
        try:
            result = warm_space_pdf_ai_region_question_cache()
            stt_debug_log("space_pdf_ai_question_cache_warmed", **result)
        except Exception as exc:
            stt_debug_log("space_pdf_ai_question_cache_warm_failed", error=str(exc))

    threading.Thread(target=runner, name="space-pdf-ai-question-cache-warm", daemon=True).start()


def save_space_pdf_ai_region_question(username: str, question_payload: dict) -> dict:
    viewer = normalize_username(username)
    if not is_admin_user(viewer):
        raise RuntimeError("Only admins can update shared PDF/Picture AI questions.")
    source = question_payload if isinstance(question_payload, dict) else {}
    normalized_mode = normalize_space_pdf_shared_audio_mode(source.get("mode", "pdf"))
    doc_info = space_pdf_progress_identity_for_source(viewer, source) if clean_path_value(source.get("path", "")) else {}
    rel_path = clean_path_value(doc_info.get("path", ""))
    identity = clean(doc_info.get("identity", ""))
    normalized_page = normalize_space_pdf_drawing_page(source.get("page", 1))
    if not rel_path:
        raise RuntimeError("Thieu duong dan PDF/Picture.")
    key = space_pdf_child_document_key(rel_path, normalized_mode, identity)
    page_key = str(normalized_page)
    action = clean(source.get("action", "save")).lower()
    question_id = clean(source.get("id", ""))
    if action in {"remove", "delete"} and not question_id:
        raise RuntimeError("Thieu ID cua AI question.")
    now = utc_timestamp()
    removed = False
    with SPACE_PDF_AI_REGION_QUESTIONS_LOCK:
        payload = _read_space_pdf_ai_region_question_store_locked()
        documents = payload.get("documents") if isinstance(payload.get("documents"), dict) else {}
        payload["documents"] = documents
        document = documents.get(key) if isinstance(documents.get(key), dict) else {}
        if not document:
            legacy_key = next((
                clean(item_key) for item_key, value in documents.items()
                if isinstance(value, dict)
                and clean_path_value(value.get("path", "")).lower() == rel_path.lower()
                and normalize_space_pdf_shared_audio_mode(value.get("mode", normalized_mode)) == normalized_mode
            ), "")
            if legacy_key and legacy_key != key:
                document = documents.pop(legacy_key, {}) if isinstance(documents.get(legacy_key), dict) else {}
        document.update({
            "key": key,
            "path": rel_path,
            "lesson_id": identity if identity.lower().startswith("ftg-lesson-") else "",
            "mode": normalized_mode,
            "updated_at": now,
            "updated_by": viewer,
        })
        pages = document.get("pages") if isinstance(document.get("pages"), dict) else {}
        rows = [item for item in (pages.get(page_key) if isinstance(pages.get(page_key), list) else []) if isinstance(item, dict)]
        existing_index = next((index for index, item in enumerate(rows) if clean(item.get("id", "")) == question_id), -1)
        existing = rows[existing_index] if existing_index >= 0 else {}
        if action in {"remove", "delete"}:
            if existing_index >= 0:
                rows.pop(existing_index)
                removed = True
        else:
            question = normalize_space_pdf_ai_notice_text(source.get("question", source.get("text", existing.get("question", ""))), 2400)
            if not question:
                raise RuntimeError("Nhap cau hoi AI question.")
            image_src = normalize_space_pdf_ai_question_image_src(
                source.get(
                    "imageSrc",
                    source.get(
                        "image_src",
                        source.get(
                            "questionImage",
                            source.get("question_image", source.get("imageUrl", source.get("image_url", existing.get("imageSrc", existing.get("image_src", ""))))),
                        ),
                    ),
                )
            )
            image_alt = clean(source.get("imageAlt", source.get("image_alt", existing.get("imageAlt", existing.get("image_alt", "")))))[:180]
            region_name = clean(
                source.get(
                    "regionName",
                    source.get(
                        "region_name",
                        source.get(
                            "aiQuestionRegionName",
                            source.get("ai_question_region_name", existing.get("regionName", existing.get("region_name", ""))),
                        ),
                    ),
                )
            )[:120]
            question_highlights = normalize_space_pdf_ai_question_highlights(
                source.get("questionHighlights", source.get("question_highlights", existing.get("questionHighlights", existing.get("question_highlights", [])))),
                question,
            )
            if not question_id:
                question_id = f"question-{uuid.uuid4().hex[:12]}"
            rect = normalize_space_pdf_ai_notice_rect(source.get("rect", existing.get("rect", {})))
            union_rects_raw = source.get("unionRects", source.get("union_rects", existing.get("unionRects", existing.get("union_rects", []))))
            union_rects = [normalize_space_pdf_ai_notice_rect(u) for u in (union_rects_raw if isinstance(union_rects_raw, list) else []) if isinstance(u, dict)]
            union_rects = [r for r in union_rects if r.get("w", 0) >= 0.004 and r.get("h", 0) >= 0.004]
            answers_raw = source.get("answers") if isinstance(source.get("answers"), list) else existing.get("answers", [])
            answers = [normalize_space_pdf_ai_question_answer(answer, index=index) for index, answer in enumerate(answers_raw if isinstance(answers_raw, list) else [])]
            answers = [answer for answer in answers if answer.get("text")]
            question_type = normalize_space_pdf_ai_question_type(source.get("questionType", source.get("question_type", existing.get("questionType", "choice"))))
            if question_type == "choice" and answers and len(answers) < 2:
                raise RuntimeError("AI question dang Choice can co it nhat 2 dap an. Input/Speak node co the chi can 1 dap an.")
            if answers and not any(answer.get("correct") for answer in answers):
                answers[0]["correct"] = True
            mikasa_intro = normalize_space_pdf_ai_notice_text(source.get("mikasaIntro", source.get("mikasa_intro", existing.get("mikasaIntro", ""))), 1200)
            mikasa_intro_highlights = normalize_space_pdf_ai_question_highlights(
                source.get("mikasaIntroHighlights", source.get("mikasa_intro_highlights", existing.get("mikasaIntroHighlights", existing.get("mikasa_intro_highlights", [])))),
                mikasa_intro,
            )
            intro_voice = clean(source.get("voice", existing.get("voice", SPACE_PDF_AI_REGION_QUESTION_DEFAULT_VOICE))) or SPACE_PDF_AI_REGION_QUESTION_DEFAULT_VOICE
            intro_audio_path = normalize_space_pdf_shared_audio_link(source.get("introAudioPath", source.get("intro_audio_path", existing.get("introAudioPath", existing.get("intro_audio_path", "")))))
            intro_audio_mime = clean(source.get("introAudioMime", source.get("intro_audio_mime", existing.get("introAudioMime", existing.get("intro_audio_mime", "")))))
            intro_timing_payload = normalize_space_pdf_ai_question_timing_payload(
                source.get("introTimingPayload", source.get("intro_timing_payload", existing.get("introTimingPayload", existing.get("intro_timing_payload", {}))))
            )
            intro_still_matches = (
                clean(existing.get("mikasaIntro", "")) == clean(mikasa_intro)
                and clean(existing.get("voice", "")) == clean(intro_voice)
            )
            if not intro_still_matches:
                intro_audio_path = ""
                intro_audio_mime = ""
                intro_timing_payload = {}
            if mikasa_intro and not intro_audio_path:
                audio_payload = chat_synthesize_ai_question_audio_queued(mikasa_intro, intro_voice)
                intro_audio_path = normalize_space_pdf_shared_audio_link(audio_payload.get("audio_path", ""))
                intro_audio_mime = _space_pdf_shared_audio_guess_mime(intro_audio_path, clean(audio_payload.get("audio_mime", ""))) if intro_audio_path else ""
                intro_voice = clean(audio_payload.get("voice", intro_voice)) or intro_voice
                intro_timing_payload = normalize_space_pdf_ai_question_timing_payload(audio_payload)
            existing_answers = existing.get("answers") if isinstance(existing.get("answers"), list) else []
            existing_answer_rows = [
                normalize_space_pdf_ai_question_answer(answer, index=index)
                for index, answer in enumerate(existing_answers)
                if isinstance(answer, dict)
            ]
            existing_answer_by_id = {
                clean(answer.get("id", "")): answer
                for answer in existing_answer_rows
                if clean(answer.get("id", ""))
            }
            used_existing_answer_keys: set[str] = set()
            for answer in answers:
                answer_id = clean(answer.get("id", ""))
                existing_answer = existing_answer_by_id.get(answer_id, {})
                if existing_answer:
                    used_existing_answer_keys.add(f"id:{answer_id}")
                if not existing_answer:
                    for existing_index, candidate in enumerate(existing_answer_rows):
                        candidate_key = f"row:{existing_index}"
                        if candidate_key in used_existing_answer_keys:
                            continue
                        if (
                            clean(candidate.get("text", "")) == clean(answer.get("text", ""))
                            and clean(candidate.get("explanationText", "")) == clean(answer.get("explanationText", ""))
                            and clean(candidate.get("explanationVoice", "")) == clean(answer.get("explanationVoice", ""))
                            and clean(candidate.get("explanationMode", "")) == clean(answer.get("explanationMode", ""))
                        ):
                            existing_answer = candidate
                            used_existing_answer_keys.add(candidate_key)
                            break
                if existing_answer:
                    audio_still_matches = (
                        clean(existing_answer.get("explanationText", "")) == clean(answer.get("explanationText", ""))
                        and clean(existing_answer.get("explanationVoice", "")) == clean(answer.get("explanationVoice", ""))
                        and clean(existing_answer.get("explanationMode", "")) == clean(answer.get("explanationMode", ""))
                    )
                    if audio_still_matches:
                        answer["audioPath"] = normalize_space_pdf_shared_audio_link(answer.get("audioPath") or existing_answer.get("audioPath", ""))
                        answer["audioMime"] = clean(answer.get("audioMime") or existing_answer.get("audioMime", ""))
                        answer["explanationVoiceLabel"] = clean(answer.get("explanationVoiceLabel") or existing_answer.get("explanationVoiceLabel", ""))
                    else:
                        answer["audioPath"] = ""
                        answer["audioMime"] = ""
                mode_value = clean(answer.get("explanationMode", "text_voice"))
                should_build = mode_value in {"text_voice", "voice"} and answer.get("explanationText")
                if should_build and not answer.get("audioPath"):
                    audio_payload = chat_synthesize_ai_question_audio_queued(answer.get("explanationText", ""), answer.get("explanationVoice") or SPACE_PDF_AI_REGION_QUESTION_DEFAULT_VOICE)
                    audio_path = normalize_space_pdf_shared_audio_link(audio_payload.get("audio_path", ""))
                    answer["audioPath"] = audio_path
                    answer["audioMime"] = _space_pdf_shared_audio_guess_mime(audio_path, clean(audio_payload.get("audio_mime", ""))) if audio_path else ""
                    answer["explanationVoice"] = clean(audio_payload.get("voice", answer.get("explanationVoice", ""))) or answer.get("explanationVoice", SPACE_PDF_AI_REGION_QUESTION_DEFAULT_VOICE)
                    answer["explanationVoiceLabel"] = clean(audio_payload.get("voice_label", answer.get("explanationVoiceLabel", ""))) or answer.get("explanationVoiceLabel", "")
            question_row = {
                "id": question_id,
                "page": normalized_page,
                "mode": normalized_mode,
                "rect": rect,
                "unionRects": union_rects,
                "regionName": region_name,
                "question": question,
                "imageSrc": image_src,
                "imageAlt": image_alt,
                "questionHighlights": question_highlights,
                "questionType": question_type,
                "typedMatchPercent": normalize_space_pdf_ai_question_match_percent(
                    source.get(
                        "typedMatchPercent",
                        source.get(
                            "typed_match_percent",
                            source.get("matchPercent", source.get("match_percent", existing.get("typedMatchPercent", 100))),
                        ),
                    )
                ),
                "randomOrder": bool(source.get("randomOrder", source.get("random_order", existing.get("randomOrder", existing.get("random_order", False))))),
                "pinned": bool(
                    source.get(
                        "pinned",
                        source.get(
                            "pinNode",
                            source.get(
                                "pin_node",
                                source.get("pinnedNode", source.get("pinned_node", existing.get("pinned", existing.get("pinned_node", False)))),
                            ),
                        ),
                    )
                ),
                "mikasaIntro": mikasa_intro,
                "mikasaIntroHighlights": mikasa_intro_highlights,
                "voice": intro_voice,
                "introAudioPath": intro_audio_path,
                "introAudioMime": intro_audio_mime,
                "introTimingPayload": intro_timing_payload,
                "title": (clean(source.get("title", "")) or question.splitlines()[0])[:120],
                "answers": answers[:8],
                "createdAt": clean(existing.get("createdAt", existing.get("created_at", ""))) or now,
                "createdBy": clean(existing.get("createdBy", existing.get("created_by", ""))) or viewer,
                "updatedAt": now,
                "updatedBy": viewer,
            }
            if existing_index >= 0:
                rows[existing_index] = question_row
            else:
                rows.append(question_row)
        if rows:
            pages[page_key] = rows
            document["pages"] = pages
            documents[key] = document
        else:
            pages.pop(page_key, None)
            if pages:
                document["pages"] = pages
                documents[key] = document
            else:
                documents.pop(key, None)
        payload["documents"] = documents
        _write_space_pdf_ai_region_question_store_locked(payload)
        SPACE_PDF_AI_REGION_QUESTIONS_PUBLIC_CACHE.clear()
    snapshot = read_space_pdf_ai_region_questions(viewer, rel_path, normalized_page, normalized_mode)
    current_question = next((item for item in snapshot.get("questions", []) if clean(item.get("id", "")) == question_id), {})
    return {
        "key": key,
        "path": rel_path,
        "page": normalized_page,
        "mode": normalized_mode,
        "removed": removed,
        "question": current_question if isinstance(current_question, dict) else {},
        "questions": snapshot.get("questions", []),
    }


def _read_space_pdf_ai_question_progress_store_locked() -> dict:
    return _load_space_pdf_ai_json_store_locked(
        "question_progress",
        SPACE_PDF_AI_QUESTION_PROGRESS_FILE,
        "users",
    )


def _write_space_pdf_ai_question_progress_store_locked(payload: dict) -> None:
    _remember_space_pdf_ai_json_store_locked(
        "question_progress",
        SPACE_PDF_AI_QUESTION_PROGRESS_FILE,
        payload,
        "users",
    )


# Added 2026-07-09: reads one MishiKa progress record from RAM without cloning all user progress.
def _read_space_pdf_ai_question_progress_record_fast(viewer: str, progress_key: str) -> dict:
    with SPACE_PDF_AI_JSON_STORE_LOCK:
        row = _space_pdf_ai_json_store_live_row(
            "question_progress",
            SPACE_PDF_AI_QUESTION_PROGRESS_FILE,
            "users",
        )
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        users = payload.get("users") if isinstance(payload.get("users"), dict) else {}
        user_rows = users.get(viewer) if isinstance(users.get(viewer), dict) else {}
        record = user_rows.get(progress_key) if isinstance(user_rows.get(progress_key), dict) else {}
        return _space_pdf_ai_json_clone(record)


def _space_pdf_ai_question_progress_has_answers(record: dict) -> bool:
    if not isinstance(record, dict):
        return False
    completed = record.get("completed") if isinstance(record.get("completed"), dict) else {}
    results = record.get("results") if isinstance(record.get("results"), dict) else {}
    return bool(completed or results)


def _space_pdf_ai_question_region_signature(region_key: str) -> str:
    parts = clean(region_key).split("::")
    if len(parts) < 4:
        return clean(region_key)
    return "::".join(parts[:4])


def _space_pdf_ai_question_progress_sort_value(record: dict) -> tuple:
    if not isinstance(record, dict):
        return (0, 0, "")
    results = record.get("results") if isinstance(record.get("results"), dict) else {}
    completed = record.get("completed") if isinstance(record.get("completed"), dict) else {}
    passed = sum(1 for value in results.values() if isinstance(value, dict) and (value.get("passed") or value.get("correct")))
    saved_at = clean(record.get("savedAt", record.get("saved_at", record.get("updatedAt", ""))))
    return (passed, len(results) + len(completed), saved_at)


def _find_compatible_space_pdf_ai_question_progress_record_fast(
    viewer: str,
    *,
    progress_key: str,
    rel_path: str,
    page: object,
    mode: str,
    region_key: str,
) -> dict:
    signature = _space_pdf_ai_question_region_signature(region_key)
    if not signature:
        return {}
    with SPACE_PDF_AI_JSON_STORE_LOCK:
        row = _space_pdf_ai_json_store_live_row(
            "question_progress",
            SPACE_PDF_AI_QUESTION_PROGRESS_FILE,
            "users",
        )
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        users = payload.get("users") if isinstance(payload.get("users"), dict) else {}
        user_rows = users.get(viewer) if isinstance(users.get(viewer), dict) else {}
        best_record = {}
        normalized_page = normalize_space_pdf_drawing_page(page)
        normalized_mode = normalize_space_pdf_shared_audio_mode(mode)
        for key, record in user_rows.items():
            if clean(key) == clean(progress_key) or not isinstance(record, dict):
                continue
            if clean_path_value(record.get("path", "")).lower() != clean_path_value(rel_path).lower():
                continue
            if normalize_space_pdf_drawing_page(record.get("page", 1)) != normalized_page:
                continue
            if normalize_space_pdf_shared_audio_mode(record.get("mode", "pdf")) != normalized_mode:
                continue
            if _space_pdf_ai_question_region_signature(record.get("regionKey", "")) != signature:
                continue
            if not _space_pdf_ai_question_progress_has_answers(record):
                continue
            if not best_record or _space_pdf_ai_question_progress_sort_value(record) > _space_pdf_ai_question_progress_sort_value(best_record):
                best_record = record
        return _space_pdf_ai_json_clone(best_record)


# Added 2026-07-09: updates one MishiKa progress record and lets the shared flusher batch disk writes.
def _write_space_pdf_ai_question_progress_record_fast(viewer: str, record: dict, *, reset: bool = False) -> dict:
    record_key = clean(record.get("key", ""))
    if not record_key:
        return record
    with SPACE_PDF_AI_JSON_STORE_LOCK:
        row = _space_pdf_ai_json_store_live_row(
            "question_progress",
            SPACE_PDF_AI_QUESTION_PROGRESS_FILE,
            "users",
        )
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        users = payload.get("users") if isinstance(payload.get("users"), dict) else {}
        if not isinstance(users, dict):
            users = {}
        user_rows = users.get(viewer) if isinstance(users.get(viewer), dict) else {}
        if not isinstance(user_rows, dict):
            user_rows = {}
        existing = user_rows.get(record_key) if isinstance(user_rows.get(record_key), dict) else {}
        if reset and _space_pdf_ai_question_reset_is_stale(existing, record):
            final_record = _merge_space_pdf_ai_question_progress_records(existing, record)
        else:
            final_record = record if reset else _merge_space_pdf_ai_question_progress_records(existing, record)
        if user_rows.get(record_key) == final_record:
            return final_record
        user_rows[record_key] = final_record
        users[viewer] = user_rows
        payload["users"] = users
        payload["version"] = int(payload.get("version", 1) or 1)
        payload["updated_at"] = utc_timestamp()
        row["payload"] = payload
        row["dirty"] = True
        dirty_keys = row.get("dirty_keys") if isinstance(row.get("dirty_keys"), set) else set()
        dirty_keys.add(viewer)
        row["dirty_keys"] = dirty_keys
        dirty_nested_keys = row.get("dirty_nested_keys") if isinstance(row.get("dirty_nested_keys"), set) else set()
        dirty_nested_keys.add((viewer, record_key))
        row["dirty_nested_keys"] = dirty_nested_keys
        row["last_dirty_at"] = time.time()
    start_space_pdf_ai_json_store_flusher()
    return final_record


# Added 2026-07-09: prevents older rapid MishiKa saves from overwriting newer answered questions.
def _merge_space_pdf_ai_question_progress_records(existing: dict, incoming: dict) -> dict:
    if not isinstance(existing, dict) or not existing:
        return incoming
    final_record = dict(incoming)
    existing_completed = existing.get("completed") if isinstance(existing.get("completed"), dict) else {}
    incoming_completed = incoming.get("completed") if isinstance(incoming.get("completed"), dict) else {}
    existing_results = existing.get("results") if isinstance(existing.get("results"), dict) else {}
    incoming_results = incoming.get("results") if isinstance(incoming.get("results"), dict) else {}
    merged_completed = dict(existing_completed)
    merged_completed.update(incoming_completed)
    merged_results = dict(existing_results)
    merged_results.update(incoming_results)
    final_record["completed"] = merged_completed
    final_record["results"] = merged_results
    existing_order = existing.get("order") if isinstance(existing.get("order"), list) else []
    incoming_order = incoming.get("order") if isinstance(incoming.get("order"), list) else []
    if len(existing_order) > len(incoming_order):
        final_record["order"] = existing_order
    final_record["questionIndex"] = max(
        space_w_int(existing.get("questionIndex", 0)),
        space_w_int(incoming.get("questionIndex", 0)),
    )
    existing_saved_at = clean(existing.get("savedAt", existing.get("saved_at", "")))
    incoming_saved_at = clean(incoming.get("savedAt", incoming.get("saved_at", "")))
    if existing_saved_at and (not incoming_saved_at or timestamp_order_key(existing_saved_at) > timestamp_order_key(incoming_saved_at)):
        final_record["savedAt"] = existing_saved_at
    return final_record


# Added 2026-07-09: keeps a late empty reset request from wiping answers saved after Start over.
def _space_pdf_ai_question_reset_is_stale(existing: dict, incoming: dict) -> bool:
    if not isinstance(existing, dict) or not existing:
        return False
    incoming_results = incoming.get("results") if isinstance(incoming.get("results"), dict) else {}
    incoming_completed = incoming.get("completed") if isinstance(incoming.get("completed"), dict) else {}
    if incoming_results or incoming_completed:
        return False
    existing_results = existing.get("results") if isinstance(existing.get("results"), dict) else {}
    existing_completed = existing.get("completed") if isinstance(existing.get("completed"), dict) else {}
    if not existing_results and not existing_completed:
        return False
    existing_saved_at = clean(existing.get("savedAt", existing.get("saved_at", "")))
    incoming_saved_at = clean(incoming.get("savedAt", incoming.get("saved_at", "")))
    return bool(existing_saved_at and incoming_saved_at and timestamp_order_key(existing_saved_at) > timestamp_order_key(incoming_saved_at))


def _space_pdf_ai_question_progress_key(username: str, mode: str, rel_path: str, page: object, region_key: str, identity: str = "") -> str:
    viewer = normalize_username(username)
    normalized_page = normalize_space_pdf_drawing_page(page)
    scope = clean(identity).lower() if clean(identity).lower().startswith("ftg-lesson-") else rel_path.lower()
    raw = f"{viewer.lower()}|{mode}|{scope}|{normalized_page}|{clean(region_key)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def _normalize_space_pdf_ai_question_progress_record(username: str, source: dict, *, rel_path: str, page: object, mode: str, region_key: str, identity: str = "") -> dict:
    order = source.get("order") if isinstance(source.get("order"), list) else []
    completed = source.get("completed") if isinstance(source.get("completed"), dict) else {}
    results = source.get("results") if isinstance(source.get("results"), dict) else {}
    normalized_page = normalize_space_pdf_drawing_page(page)
    normalized_mode = normalize_space_pdf_shared_audio_mode(mode)
    # Updated 2026-07-10: keep the full admin-defined MishiKa queue; only trim each key.
    safe_order = [clean(item)[:160] for item in order if clean(item)]
    safe_completed = {
        clean(key)[:160]: value
        for key, value in completed.items()
        if clean(key) and isinstance(value, dict)
    }
    safe_results = {
        clean(key)[:160]: value
        for key, value in results.items()
        if clean(key) and isinstance(value, dict)
    }
    question_index = max(0, min(max(0, len(safe_order) - 1), space_w_int(source.get("questionIndex", source.get("question_index", 0)))))
    progress_key = _space_pdf_ai_question_progress_key(username, normalized_mode, rel_path, normalized_page, region_key, identity)
    now = utc_timestamp()
    return {
        "version": 1,
        "key": progress_key,
        "username": normalize_username(username),
        "path": rel_path,
        "mode": normalized_mode,
        "page": normalized_page,
        "regionKey": clean(region_key)[:1200],
        "randomOrder": bool(source.get("randomOrder", source.get("random_order", False))),
        "order": safe_order,
        "questionIndex": question_index,
        "completed": safe_completed,
        "results": safe_results,
        "savedAt": clean(source.get("savedAt", source.get("saved_at", now)))[:80],
        "updatedAt": now,
    }


def read_space_pdf_ai_question_progress(username: str, relative_path: str = "", page: object = 1, mode: object = "pdf", region_key: str = "", lesson_id: str = "", lesson_handle: str = "") -> dict:
    viewer = normalize_username(username)
    normalized_mode = normalize_space_pdf_shared_audio_mode(mode)
    normalized_page = normalize_space_pdf_drawing_page(page)
    raw_rel_path = clean_path_value(relative_path)
    doc_info = space_pdf_progress_identity_for_source(viewer, {"path": raw_rel_path, "lesson_id": lesson_id, "lesson_handle": lesson_handle}) if raw_rel_path else {}
    rel_path = clean_path_value(doc_info.get("path", "")) or _space_pdf_ai_fast_relative_media_path(raw_rel_path)
    identity = clean(doc_info.get("identity", ""))
    safe_region_key = clean(region_key)
    if not rel_path or not safe_region_key:
        return {"key": "", "path": rel_path, "page": normalized_page, "mode": normalized_mode, "regionKey": safe_region_key, "progress": {}}
    progress_key = _space_pdf_ai_question_progress_key(viewer, normalized_mode, rel_path, normalized_page, safe_region_key, identity)
    with SPACE_PDF_AI_QUESTION_PROGRESS_LOCK:
        record = _read_space_pdf_ai_question_progress_record_fast(viewer, progress_key)
        if not _space_pdf_ai_question_progress_has_answers(record):
            compatible_record = _find_compatible_space_pdf_ai_question_progress_record_fast(
                viewer,
                progress_key=progress_key,
                rel_path=rel_path,
                page=normalized_page,
                mode=normalized_mode,
                region_key=safe_region_key,
            )
            if compatible_record:
                record = compatible_record
    return {
        "key": progress_key,
        "path": rel_path,
        "lesson_id": clean(identity) if clean(identity).lower().startswith("ftg-lesson-") else "",
        "page": normalized_page,
        "mode": normalized_mode,
        "regionKey": safe_region_key,
        "progress": record if isinstance(record, dict) else {},
    }


def save_space_pdf_ai_question_progress(username: str, progress_payload: dict) -> dict:
    viewer = normalize_username(username)
    source = progress_payload if isinstance(progress_payload, dict) else {}
    normalized_mode = normalize_space_pdf_shared_audio_mode(source.get("mode", "pdf"))
    normalized_page = normalize_space_pdf_drawing_page(source.get("page", 1))
    raw_rel_path = clean_path_value(source.get("path", ""))
    doc_info = space_pdf_progress_identity_for_source(viewer, source) if raw_rel_path else {}
    rel_path = clean_path_value(doc_info.get("path", "")) or _space_pdf_ai_fast_relative_media_path(raw_rel_path)
    identity = clean(doc_info.get("identity", ""))
    region_key = clean(source.get("regionKey", source.get("region_key", "")))
    if not rel_path:
        raise RuntimeError("Thieu duong dan PDF/Picture.")
    if not region_key:
        raise RuntimeError("Thieu ma vung cau hoi MishiKa.")
    record = _normalize_space_pdf_ai_question_progress_record(
        viewer,
        source,
        rel_path=rel_path,
        page=normalized_page,
        mode=normalized_mode,
        region_key=region_key,
        identity=identity,
    )
    with SPACE_PDF_AI_QUESTION_PROGRESS_LOCK:
        record = _write_space_pdf_ai_question_progress_record_fast(
            viewer,
            record,
            reset=bool(source.get("resetProgress", source.get("reset_progress", False))),
        )
    return {
        "key": record["key"],
        "path": rel_path,
        "page": normalized_page,
        "mode": normalized_mode,
        "regionKey": region_key,
        "progress": record,
    }


SPACE_PDF_SHARED_AUDIO_MARKERS_FILE = SERVER_DATA_ROOT / "_future_space_pdf_audio_markers.json"
SPACE_PDF_SHARED_AUDIO_MARKERS_LOCK = threading.RLock()
SPACE_PDF_SHARED_AUDIO_DEFAULT_VOICE = "edge:vi-VN-NamMinhNeural"
SPACE_PDF_SHARED_AUDIO_ALLOWED_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".ogg", ".aac", ".flac", ".webm", ".mp4", ".opus", ".aiff", ".aif", ".amr", ".caf", ".3gp",
    ".m4v", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".mpeg", ".mpg", ".m2ts", ".mts", ".ts", ".ogv", ".3g2", ".vob", ".asf", ".rm", ".rmvb", ".divx", ".f4v",
    ".png", ".jpg", ".jpeg", ".jfif", ".webp", ".gif", ".bmp", ".tif", ".tiff",
}
SPACE_PDF_SHARED_VIDEO_EXTENSIONS = {".mp4", ".m4v", ".webm", ".ogv", ".ogg", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".mpeg", ".mpg", ".m2ts", ".mts", ".ts", ".3gp", ".3g2", ".vob", ".asf", ".rm", ".rmvb", ".divx", ".f4v"}
SPACE_PDF_SHARED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".jfif", ".webp", ".gif", ".bmp", ".tif", ".tiff"}


def normalize_space_pdf_shared_audio_mode(value: object = "pdf") -> str:
    return "picture" if clean(value).lower() == "picture" else "pdf"


def normalize_space_pdf_shared_audio_text(value: object = "", limit: int = 4000) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    return text[:max(0, int(limit or 0))] if limit and limit > 0 else text


def normalize_space_pdf_shared_audio_xy(value: object = 0.5, fallback: float = 0.5) -> float:
    try:
        number = float(value)
    except Exception:
        number = float(fallback)
    return round(max(0.0, min(1.0, number)), 6)


def normalize_space_pdf_shared_media_size(value: object = 0.18, fallback: float = 0.18) -> float:
    try:
        number = float(value)
    except Exception:
        number = float(fallback)
    return round(max(0.04, min(0.95, number)), 6)


def normalize_space_pdf_shared_media_display_mode(value: object = "button") -> str:
    return "always" if clean(value).lower() in {"always", "show", "visible", "always_show", "always-show"} else "button"


def normalize_space_pdf_shared_audio_link(value: object = "") -> str:
    text = clean(value).replace("\\", "/")
    if not text:
        return ""
    if len(text) > 1600:
        raise RuntimeError("Media link is too long.")
    lowered = text.lower()
    if lowered.startswith(("http://", "https://", "data:", "blob:", "/server-data/asset?path=")):
        return text
    relative = text.lstrip("/")
    parts = [part for part in relative.split("/") if part]
    if not parts or any(part in {".", ".."} for part in parts):
        raise RuntimeError("Media link is not valid.")
    if parts[0].lower() not in {"sound", "common"}:
        raise RuntimeError("Shared media link must use Sound/... or an absolute URL.")
    return relative


def normalize_space_pdf_shared_audio_source_kind(value: object = "", audio_path: object = "") -> str:
    lowered = clean(value).lower()
    if lowered in {"built", "uploaded", "linked", "server", "transcoded"}:
        return lowered
    return "linked" if clean(audio_path) else ""


def normalize_space_pdf_shared_media_kind(value: object = "", audio_path: object = "", audio_mime: object = "") -> str:
    lowered = clean(value).lower()
    if lowered in {"audio", "video", "url", "image", "picture"}:
        if lowered == "picture":
            return "image"
        return lowered
    raw = clean(audio_path)
    mime = clean(audio_mime).lower()
    raw_path = Path(raw.split("?", 1)[0])
    if mime.startswith("image/") or raw_path.suffix.lower() in SPACE_PDF_SHARED_IMAGE_EXTENSIONS:
        return "image"
    if raw.startswith(("http://", "https://")) and not (mime.startswith(("audio/", "video/", "image/")) or raw_path.suffix.lower() in SPACE_PDF_SHARED_AUDIO_ALLOWED_EXTENSIONS):
        return "url"
    if mime.startswith("video/") or raw_path.suffix.lower() in SPACE_PDF_SHARED_VIDEO_EXTENSIONS:
        return "video"
    return "audio"


def space_pdf_shared_audio_document_path(relative_path: str = "", username: str = "", admin: bool = False) -> str:
    return normalize_space_w_progress_path(relative_path, username, admin=admin) if clean_path_value(relative_path) else ""


def space_pdf_shared_audio_document_key(relative_path: str = "", mode: object = "pdf", identity: str = "") -> str:
    return space_pdf_child_document_key(relative_path, mode, identity)


def backup_space_pdf_shared_audio_store(reason: str = "path-normalize") -> str:
    signature = server_database_document_signature(SPACE_PDF_SHARED_AUDIO_MARKERS_FILE)
    return f"postgres:{signature[3]}:{clean(reason) or 'path-normalize'}" if signature[3] else ""
 

def merge_space_pdf_shared_audio_page_rows(left: list | None = None, right: list | None = None) -> list[dict]:
    rows = []
    for item in (left or []):
        if isinstance(item, dict):
            rows.append(dict(item))
    for item in (right or []):
        if isinstance(item, dict):
            rows.append(dict(item))
    latest: dict[str, dict] = {}
    for row in rows:
        marker_id = clean(row.get("id", ""))
        if not marker_id:
            continue
        current = latest.get(marker_id)
        if not isinstance(current, dict):
            latest[marker_id] = row
            continue
        current_stamp = timestamp_to_epoch(current.get("updatedAt") or current.get("updated_at"))
        row_stamp = timestamp_to_epoch(row.get("updatedAt") or row.get("updated_at"))
        if row_stamp >= current_stamp:
            latest[marker_id] = row
    return list(latest.values())


def normalize_space_pdf_shared_audio_store_to_path(payload: dict | None = None) -> tuple[dict, bool]:
    source = payload if isinstance(payload, dict) else {}
    documents = source.get("documents") if isinstance(source.get("documents"), dict) else {}
    next_documents: dict[str, dict] = {}
    changed = False
    for old_key, raw_document in documents.items():
        if not isinstance(raw_document, dict):
            continue
        mode = normalize_space_pdf_shared_audio_mode(raw_document.get("mode", "pdf"))
        raw_path = clean_path_value(raw_document.get("path", ""))
        if not raw_path:
            continue
        next_key = space_pdf_shared_audio_document_key(raw_path, mode, clean(raw_document.get("lesson_id", "")))
        document = dict(raw_document)
        document["key"] = next_key
        document["mode"] = mode
        document["path"] = raw_path
        if next_key != clean(old_key):
            changed = True
        pages = document.get("pages") if isinstance(document.get("pages"), dict) else {}
        normalized_pages: dict[str, list] = {}
        for page_key, rows in pages.items():
            normalized_pages[str(normalize_space_pdf_drawing_page(page_key))] = merge_space_pdf_shared_audio_page_rows(rows, [])
        document["pages"] = normalized_pages
        existing = next_documents.get(next_key) if isinstance(next_documents.get(next_key), dict) else {}
        if existing:
            merged_pages = existing.get("pages") if isinstance(existing.get("pages"), dict) else {}
            for page_key, rows in normalized_pages.items():
                merged_pages[page_key] = merge_space_pdf_shared_audio_page_rows(merged_pages.get(page_key), rows)
            existing["pages"] = merged_pages
            existing["updated_at"] = clean(document.get("updated_at", "")) or clean(existing.get("updated_at", ""))
            next_documents[next_key] = existing
            changed = True
        else:
            next_documents[next_key] = document
    out = {
        "version": int(source.get("version", 1) or 1),
        "updated_at": clean(source.get("updated_at", "")),
        "documents": next_documents,
    }
    return out, changed


def _read_space_pdf_shared_audio_store_locked() -> dict:
    SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        payload = server_database_read_document_json(SPACE_PDF_SHARED_AUDIO_MARKERS_FILE, {})
        if isinstance(payload, dict):
            documents = payload.get("documents") if isinstance(payload.get("documents"), dict) else {}
            out = {
                "version": int(payload.get("version", 1) or 1),
                "updated_at": clean(payload.get("updated_at", "")),
                "documents": {clean(key): value for key, value in documents.items() if clean(key) and isinstance(value, dict)},
            }
            migrated, changed = normalize_space_pdf_shared_audio_store_to_path(out)
            if changed:
                backup_space_pdf_shared_audio_store("shared-audio-path")
                _write_space_pdf_shared_audio_store_locked(migrated)
                return migrated
            return migrated
    except Exception:
        pass
    return {"version": 1, "updated_at": "", "documents": {}}


def _write_space_pdf_shared_audio_store_locked(payload: dict) -> None:
    documents = payload.get("documents") if isinstance(payload.get("documents"), dict) else {}
    out = {
        "version": 1,
        "updated_at": utc_timestamp(),
        "documents": documents,
    }
    atomic_write_json(SPACE_PDF_SHARED_AUDIO_MARKERS_FILE, out, indent=2)


def _space_pdf_shared_audio_voice_details(voice_key: object = "") -> tuple[str, str]:
    raw_voice = clean(voice_key) or SPACE_PDF_SHARED_AUDIO_DEFAULT_VOICE
    try:
        builder = chat_builder_tools()
        normalized = builder.normalize_audio_voice_key(raw_voice) or raw_voice
        label = builder.embedded_voice_label(normalized, raw_voice)
        return normalized, label
    except Exception:
        return raw_voice, raw_voice


def _space_pdf_shared_audio_guess_mime(audio_path: str = "", fallback: str = "") -> str:
    if clean(fallback):
        return clean(fallback)
    raw = clean(audio_path)
    if not raw or re.match(r"^(https?:|data:|blob:)", raw, re.I):
        return clean(fallback) or "audio/mpeg"
    image_suffix = Path(raw).suffix.lower()
    if image_suffix == ".png":
        return "image/png"
    if image_suffix in {".jpg", ".jpeg", ".jfif"}:
        return "image/jpeg"
    if image_suffix == ".webp":
        return "image/webp"
    if image_suffix == ".gif":
        return "image/gif"
    if image_suffix == ".bmp":
        return "image/bmp"
    if image_suffix in {".tif", ".tiff"}:
        return "image/tiff"
    try:
        builder = chat_builder_tools()
        return clean(builder.mime_for_audio_path(Path(raw))) or "audio/mpeg"
    except Exception:
        suffix = Path(raw).suffix.lower()
        if suffix == ".wav":
            return "audio/wav"
        if suffix == ".ogg":
            return "audio/ogg"
        if suffix == ".m4a":
            return "audio/mp4"
        if suffix == ".webm":
            return "audio/webm"
        if suffix == ".png":
            return "image/png"
        if suffix in {".jpg", ".jpeg", ".jfif"}:
            return "image/jpeg"
        if suffix == ".webp":
            return "image/webp"
        if suffix == ".gif":
            return "image/gif"
        if suffix == ".bmp":
            return "image/bmp"
        if suffix in {".tif", ".tiff"}:
            return "image/tiff"
        if suffix in {".mp4", ".m4v"}:
            return "video/mp4"
        if suffix == ".mov":
            return "video/quicktime"
        if suffix == ".avi":
            return "video/x-msvideo"
        if suffix == ".mkv":
            return "video/x-matroska"
        if suffix == ".wmv":
            return "video/x-ms-wmv"
        if suffix == ".flv":
            return "video/x-flv"
        if suffix in {".mpeg", ".mpg"}:
            return "video/mpeg"
        if suffix in {".m2ts", ".mts", ".ts"}:
            return "video/mp2t"
        if suffix == ".ogv":
            return "video/ogg"
        if suffix == ".3g2":
            return "video/3gpp2"
        return "audio/mpeg"


def _space_pdf_shared_media_is_video(path: Path, content_type: str = "") -> bool:
    mime = clean(content_type).lower()
    return mime.startswith("video/") or Path(path).suffix.lower() in SPACE_PDF_SHARED_VIDEO_EXTENSIONS


def _space_pdf_shared_video_browser_copy(builder, source_path: Path, safe_stem: str = "", content_type: str = "") -> tuple[str, str, int, str]:
    source = Path(source_path)
    source_bytes = source.read_bytes()
    def _source_sound_link() -> str:
        try:
            rel = source.resolve().relative_to(builder.SERVER_SOUND_DIR.resolve())
            return f"Sound/{str(rel).replace(chr(92), '/')}"
        except Exception:
            return source.name
    if not _space_pdf_shared_media_is_video(source, content_type):
        return _source_sound_link(), content_type or _space_pdf_shared_audio_guess_mime(str(source), ""), len(source_bytes), ""
    suffix = source.suffix.lower()
    if suffix in {".mp4", ".m4v"}:
        return _source_sound_link(), "video/mp4", len(source_bytes), "uploaded"
    if suffix == ".webm":
        return _source_sound_link(), "video/webm", len(source_bytes), "uploaded"
    configure_paths()
    temp_out = builder.SERVER_SOUND_DIR / f".future-video-transcode-{uuid.uuid4().hex}.webm"
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libvpx-vp9",
            "-cpu-used",
            "2",
            "-deadline",
            "realtime",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "libopus",
            "-b:a",
            "96k",
            "-row-mt",
            "1",
            str(temp_out),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **subprocess_hidden_kwargs())
        webm_bytes = temp_out.read_bytes()
        if not webm_bytes:
            raise RuntimeError("FFmpeg created an empty WebM file.")
        # Added 2026-07-16: store transcoded PDF media through the shared sharded Sound index.
        asset_link = builder.write_server_sound_file_asset(f"pdf-video-{(safe_stem or source.stem)[:30]}", webm_bytes, "webm")
        return asset_link, "video/webm", len(webm_bytes), "transcoded"
    except FileNotFoundError as exc:
        raise RuntimeError("Khong tim thay ffmpeg de chuyen video sang WebM browser-compatible.") from exc
    except Exception as exc:
        message = clean(getattr(exc, "stderr", b"").decode("utf-8", errors="replace") if isinstance(getattr(exc, "stderr", b""), (bytes, bytearray)) else "")
        raise RuntimeError(f"Khong chuyen duoc video sang WebM browser-compatible. {message or exc}") from exc
    finally:
        try:
            temp_out.unlink(missing_ok=True)
        except Exception:
            pass


def normalize_space_pdf_shared_audio_marker(item: dict | None = None, *, page: int = 1, mode: str = "pdf") -> dict:
    source = item if isinstance(item, dict) else {}
    marker_id = clean(source.get("id", ""))
    voice, voice_label = _space_pdf_shared_audio_voice_details(source.get("voice", source.get("voiceKey", SPACE_PDF_SHARED_AUDIO_DEFAULT_VOICE)))
    audio_path = clean(source.get("audioPath", source.get("audio_path", "")))
    text = normalize_space_pdf_shared_audio_text(source.get("text", ""))
    title = clean(source.get("title", "")) or clean(source.get("label", "")) or clean(source.get("name", ""))
    if not title:
        title = text.splitlines()[0][:42] if text else (Path(audio_path).name if audio_path and not re.match(r"^(https?:|data:|blob:)", audio_path, re.I) else "Shared Media")
    return {
        "id": marker_id,
        "page": max(1, int(source.get("page", page) or page)),
        "mode": normalize_space_pdf_shared_audio_mode(source.get("mode", mode)),
        "x": normalize_space_pdf_shared_audio_xy(source.get("x", 0.5), 0.5),
        "y": normalize_space_pdf_shared_audio_xy(source.get("y", 0.5), 0.5),
        "w": normalize_space_pdf_shared_media_size(source.get("w", source.get("width", 0.18)), 0.18),
        "h": normalize_space_pdf_shared_media_size(source.get("h", source.get("height", 0.14)), 0.14),
        "display_mode": normalize_space_pdf_shared_media_display_mode(source.get("displayMode", source.get("display_mode", "button"))),
        "text": text,
        "title": title[:120],
        "voice": voice,
        "voice_label": clean(source.get("voiceLabel", source.get("voice_label", ""))) or voice_label,
        "audio_path": audio_path,
        "audio_mime": _space_pdf_shared_audio_guess_mime(audio_path, clean(source.get("audioMime", source.get("audio_mime", "")))),
        "source_kind": normalize_space_pdf_shared_audio_source_kind(source.get("sourceKind", source.get("source_kind", "")), audio_path),
        "media_kind": normalize_space_pdf_shared_media_kind(source.get("mediaKind", source.get("media_kind", "")), audio_path, source.get("audioMime", source.get("audio_mime", ""))),
        "created_at": clean(source.get("createdAt", source.get("created_at", ""))),
        "created_by": clean(source.get("createdBy", source.get("created_by", ""))),
        "updated_at": clean(source.get("updatedAt", source.get("updated_at", ""))),
        "updated_by": clean(source.get("updatedBy", source.get("updated_by", ""))),
        "has_audio": bool(audio_path),
    }


def read_space_pdf_shared_audio_markers(username: str, relative_path: str = "", page: object = 1, mode: object = "pdf", lesson_id: str = "", lesson_handle: str = "") -> dict:
    viewer = normalize_username(username)
    normalized_mode = normalize_space_pdf_shared_audio_mode(mode)
    normalized_page = normalize_space_pdf_drawing_page(page)
    doc_info = space_pdf_progress_identity_for_source(viewer, {"path": relative_path, "lesson_id": lesson_id, "lesson_handle": lesson_handle}) if clean_path_value(relative_path) else {}
    rel_path = clean_path_value(doc_info.get("path", ""))
    identity = clean(doc_info.get("identity", ""))
    if not rel_path:
        return {"key": "", "path": "", "page": normalized_page, "mode": normalized_mode, "markers": []}
    key = space_pdf_shared_audio_document_key(rel_path, normalized_mode, identity)
    legacy_key = space_pdf_shared_audio_document_key(rel_path, normalized_mode, "")
    with SPACE_PDF_SHARED_AUDIO_MARKERS_LOCK:
        payload = _read_space_pdf_shared_audio_store_locked()
        documents = payload.get("documents", {}) if isinstance(payload.get("documents", {}), dict) else {}
        document = documents.get(key) if isinstance(documents.get(key), dict) else {}
        if not document and legacy_key != key:
            document = documents.get(legacy_key) if isinstance(documents.get(legacy_key), dict) else {}
        pages = document.get("pages") if isinstance(document.get("pages"), dict) else {}
        rows = pages.get(str(normalized_page)) if isinstance(pages.get(str(normalized_page)), list) else []
    markers = [
        normalize_space_pdf_shared_audio_marker(item, page=normalized_page, mode=normalized_mode)
        for item in rows
        if isinstance(item, dict) and clean(item.get("id", ""))
    ]
    markers.sort(key=lambda item: (float(item.get("y", 0.5) or 0.5), float(item.get("x", 0.5) or 0.5), timestamp_order_key(item.get("updated_at", ""))))
    return {
        "key": key,
        "path": rel_path,
        "page": normalized_page,
        "mode": normalized_mode,
        "markers": markers,
    }


def save_space_pdf_shared_audio_marker(username: str, marker_payload: dict) -> dict:
    viewer = normalize_username(username)
    if not is_admin_user(viewer):
        raise RuntimeError("Only admins can update shared PDF/Picture media markers.")
    source = marker_payload if isinstance(marker_payload, dict) else {}
    normalized_mode = normalize_space_pdf_shared_audio_mode(source.get("mode", "pdf"))
    doc_info = space_pdf_progress_identity_for_source(viewer, source) if clean_path_value(source.get("path", "")) else {}
    rel_path = clean_path_value(doc_info.get("path", ""))
    identity = clean(doc_info.get("identity", ""))
    normalized_page = normalize_space_pdf_drawing_page(source.get("page", 1))
    if not rel_path:
        raise RuntimeError("Thieu duong dan PDF/Picture.")
    key = space_pdf_shared_audio_document_key(rel_path, normalized_mode, identity)
    action = clean(source.get("action", "save")).lower()
    marker_id = clean(source.get("id", ""))
    if action in {"remove", "delete"} and not marker_id:
        raise RuntimeError("Thieu ID cua media marker.")
    now = utc_timestamp()
    marker = {}
    removed = False
    with SPACE_PDF_SHARED_AUDIO_MARKERS_LOCK:
        payload = _read_space_pdf_shared_audio_store_locked()
        documents = payload.get("documents") if isinstance(payload.get("documents"), dict) else {}
        payload["documents"] = documents
        document = documents.get(key) if isinstance(documents.get(key), dict) else {}
        if not document:
            legacy_key = space_pdf_shared_audio_document_key(rel_path, normalized_mode, "")
            if legacy_key and legacy_key != key and isinstance(documents.get(legacy_key), dict):
                document = documents.pop(legacy_key)
        document.update({
            "key": key,
            "path": rel_path,
            "lesson_id": identity if identity.lower().startswith("ftg-lesson-") else "",
            "mode": normalized_mode,
            "updated_at": now,
            "updated_by": viewer,
        })
        pages = document.get("pages") if isinstance(document.get("pages"), dict) else {}
        page_key = str(normalized_page)
        rows = [item for item in (pages.get(page_key) if isinstance(pages.get(page_key), list) else []) if isinstance(item, dict)]
        existing_index = next((index for index, item in enumerate(rows) if clean(item.get("id", "")) == marker_id), -1)
        existing = rows[existing_index] if existing_index >= 0 else {}
        if action in {"remove", "delete"}:
            if existing_index >= 0:
                rows.pop(existing_index)
                removed = True
        else:
            if not marker_id:
                marker_id = f"audio-{uuid.uuid4().hex[:12]}"
            voice, voice_label = _space_pdf_shared_audio_voice_details(source.get("voice", existing.get("voice", SPACE_PDF_SHARED_AUDIO_DEFAULT_VOICE)))
            next_audio_path = clean(existing.get("audioPath", existing.get("audio_path", "")))
            if "audioPath" in source or "audio_path" in source:
                next_audio_path = normalize_space_pdf_shared_audio_link(source.get("audioPath", source.get("audio_path", "")))
            next_audio_mime = clean(existing.get("audioMime", existing.get("audio_mime", "")))
            if "audioMime" in source or "audio_mime" in source:
                next_audio_mime = clean(source.get("audioMime", source.get("audio_mime", "")))
            next_source_kind = normalize_space_pdf_shared_audio_source_kind(source.get("sourceKind", source.get("source_kind", existing.get("sourceKind", existing.get("source_kind", "")))), next_audio_path)
            next_media_kind = normalize_space_pdf_shared_media_kind(source.get("mediaKind", source.get("media_kind", existing.get("mediaKind", existing.get("media_kind", "")))), next_audio_path, next_audio_mime)
            text = normalize_space_pdf_shared_audio_text(source.get("text", existing.get("text", "")))
            title = clean(source.get("title", existing.get("title", "")))
            if action == "build_audio":
                if not text:
                    raise RuntimeError("Nhap noi dung text de build audio.")
                audio_payload = chat_synthesize_message_audio_queued(text, voice)
                next_audio_path = normalize_space_pdf_shared_audio_link(audio_payload.get("audio_path", ""))
                next_audio_mime = clean(audio_payload.get("audio_mime", "")) or next_audio_mime
                voice = clean(audio_payload.get("voice", voice)) or voice
                voice_label = clean(audio_payload.get("voice_label", voice_label)) or voice_label
                next_source_kind = "built"
                next_media_kind = "audio"
            marker = {
                "id": marker_id,
                "page": normalized_page,
                "mode": normalized_mode,
                "x": normalize_space_pdf_shared_audio_xy(source.get("x", existing.get("x", 0.5)), existing.get("x", 0.5) if existing else 0.5),
                "y": normalize_space_pdf_shared_audio_xy(source.get("y", existing.get("y", 0.5)), existing.get("y", 0.5) if existing else 0.5),
                "w": normalize_space_pdf_shared_media_size(source.get("w", source.get("width", existing.get("w", existing.get("width", 0.18)))), existing.get("w", existing.get("width", 0.18)) if existing else 0.18),
                "h": normalize_space_pdf_shared_media_size(source.get("h", source.get("height", existing.get("h", existing.get("height", 0.14)))), existing.get("h", existing.get("height", 0.14)) if existing else 0.14),
                "displayMode": normalize_space_pdf_shared_media_display_mode(source.get("displayMode", source.get("display_mode", existing.get("displayMode", existing.get("display_mode", "button"))))),
                "text": text,
                "title": title[:120],
                "voice": voice,
                "voiceLabel": voice_label,
                "audioPath": next_audio_path,
                "audioMime": _space_pdf_shared_audio_guess_mime(next_audio_path, next_audio_mime),
                "sourceKind": next_source_kind,
                "mediaKind": next_media_kind,
                "createdAt": clean(existing.get("createdAt", existing.get("created_at", ""))) or now,
                "createdBy": clean(existing.get("createdBy", existing.get("created_by", ""))) or viewer,
                "updatedAt": now,
                "updatedBy": viewer,
            }
            if existing_index >= 0:
                rows[existing_index] = marker
            else:
                rows.append(marker)
        if rows:
            pages[page_key] = rows
        else:
            pages.pop(page_key, None)
        if pages:
            document["pages"] = pages
            documents[key] = document
        else:
            documents.pop(key, None)
        payload["documents"] = documents
        _write_space_pdf_shared_audio_store_locked(payload)
    snapshot = read_space_pdf_shared_audio_markers(viewer, rel_path, normalized_page, normalized_mode)
    current_marker = next((item for item in snapshot.get("markers", []) if clean(item.get("id", "")) == marker_id), {})
    return {
        "key": key,
        "path": rel_path,
        "page": normalized_page,
        "mode": normalized_mode,
        "removed": removed,
        "marker": current_marker if isinstance(current_marker, dict) else {},
        "markers": snapshot.get("markers", []),
    }


def save_space_pdf_shared_audio_upload(username: str, upload: dict, fields: dict | None = None) -> dict:
    viewer = normalize_username(username)
    if not is_admin_user(viewer):
        raise RuntimeError("Only admins can upload shared media markers.")
    item = upload if isinstance(upload, dict) else {}
    meta = fields if isinstance(fields, dict) else {}
    data = item.get("data", b"") if isinstance(item.get("data", b""), (bytes, bytearray)) else b""
    if not data:
        raise RuntimeError("No media file selected.")
    if len(data) > 512 * 1024 * 1024:
        raise RuntimeError("Media file is too large.")
    filename = clean(item.get("filename", "")) or "shared-media"
    suffix = Path(filename).suffix.lower()
    content_type = clean(item.get("content_type", ""))
    if suffix not in SPACE_PDF_SHARED_AUDIO_ALLOWED_EXTENSIONS:
        suffix = {
            "audio/mpeg": ".mp3",
            "audio/mp3": ".mp3",
            "audio/wav": ".wav",
            "audio/x-wav": ".wav",
            "audio/mp4": ".m4a",
            "audio/m4a": ".m4a",
            "audio/ogg": ".ogg",
            "audio/aac": ".aac",
            "audio/flac": ".flac",
            "audio/webm": ".webm",
            "video/mp4": ".mp4",
            "video/webm": ".webm",
            "video/quicktime": ".mov",
            "video/x-msvideo": ".avi",
            "video/x-matroska": ".mkv",
            "video/x-ms-wmv": ".wmv",
            "video/x-flv": ".flv",
            "video/mpeg": ".mpeg",
            "video/mp2t": ".ts",
            "video/ogg": ".ogv",
            "video/3gpp": ".3gp",
            "video/3gpp2": ".3g2",
            "audio/aiff": ".aiff",
            "audio/x-aiff": ".aiff",
            "audio/amr": ".amr",
            "audio/3gpp": ".3gp",
            "audio/x-caf": ".caf",
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/webp": ".webp",
            "image/gif": ".gif",
            "image/bmp": ".bmp",
            "image/tiff": ".tiff",
        }.get(content_type.lower(), "")
    if suffix not in SPACE_PDF_SHARED_AUDIO_ALLOWED_EXTENSIONS:
        raise RuntimeError("Unsupported media file type.")
    builder = chat_builder_tools()
    builder.ensure_server_asset_dirs()
    safe_stem = re.sub(r"[^0-9A-Za-z._-]+", "-", Path(filename).stem).strip("-") or "shared-media"
    # Added 2026-07-16: keep uploaded PDF/Picture media out of the flat Sound root and update the shared Sound index immediately.
    asset_link = builder.write_server_sound_file_asset(f"pdf-media-{safe_stem[:30]}", bytes(data), suffix.lstrip("."))
    asset_path = (builder.SERVER_DATA_ROOT / asset_link).resolve()
    stored_audio_path, stored_mime, stored_size, stored_note = _space_pdf_shared_video_browser_copy(builder, asset_path, safe_stem, content_type)
    marker_result = save_space_pdf_shared_audio_marker(viewer, {
        "action": "save",
        "id": meta.get("id", ""),
        "path": meta.get("path", ""),
        "mode": meta.get("mode", "pdf"),
        "page": meta.get("page", 1),
        "text": meta.get("text", ""),
        "voice": meta.get("voice", ""),
        "audioPath": stored_audio_path,
        "audioMime": stored_mime or content_type or _space_pdf_shared_audio_guess_mime(str(asset_path), ""),
        "sourceKind": stored_note or "uploaded",
        "mediaKind": normalize_space_pdf_shared_media_kind(meta.get("mediaKind", meta.get("media_kind", "")), stored_audio_path, stored_mime or content_type),
        "displayMode": meta.get("displayMode", meta.get("display_mode", "button")),
        "w": meta.get("w", meta.get("width", 0.18)),
        "h": meta.get("h", meta.get("height", 0.14)),
    })
    marker_result["upload"] = {
        "audio_path": stored_audio_path,
        "audio_mime": stored_mime or content_type or _space_pdf_shared_audio_guess_mime(str(asset_path), ""),
        "filename": filename,
        "size": stored_size or len(data),
        "source": stored_note or "uploaded",
    }
    return marker_result


def _space_pdf_shared_audio_server_source_path(raw_path: str = "") -> Path:
    raw = clean(str(raw_path or "").strip().strip("\"'"))
    if not raw:
        raise RuntimeError("Thieu duong dan media tren may chu.")
    if re.match(r"^(https?:|data:|blob:)", raw, flags=re.IGNORECASE):
        raise RuntimeError("Current Server Computer chi nhan duong dan file tren may chu, khong nhan URL.")
    try:
        relative = clean_path_value(raw)
        if relative.lower().startswith("sound/"):
            target = safe_server_asset_path(raw, required_top="Sound")
        elif relative and not re.match(r"^[A-Za-z]:", raw) and not raw.startswith(("/", "\\")):
            parts = [part for part in relative.split("/") if part]
            if any(part in (".", "..") for part in parts):
                raise RuntimeError("Duong dan media tren may chu khong hop le.")
            target = (SERVER_DATA_ROOT / relative).resolve()
            target.relative_to(SERVER_DATA_ROOT.resolve())
        else:
            target = Path(raw).expanduser().resolve()
    except Exception as exc:
        raise RuntimeError(f"Duong dan media tren may chu khong hop le: {exc}") from exc
    if not target.is_file():
        raise RuntimeError("Media tren may chu khong ton tai.")
    suffix = target.suffix.lower()
    if suffix not in SPACE_PDF_SHARED_AUDIO_ALLOWED_EXTENSIONS:
        raise RuntimeError("Unsupported media file type.")
    reason = public_path_block_reason(target)
    if reason:
        raise RuntimeError(reason)
    return target


def save_space_pdf_shared_audio_server_file(username: str, fields: dict | None = None) -> dict:
    viewer = normalize_username(username)
    if not is_admin_user(viewer):
        raise RuntimeError("Only admins can upload shared media markers.")
    meta = fields if isinstance(fields, dict) else {}
    source_path = _space_pdf_shared_audio_server_source_path(meta.get("server_path") or meta.get("audioPath") or meta.get("audio_path") or "")
    data = source_path.read_bytes()
    if not data:
        raise RuntimeError("Media tren may chu dang rong.")
    if len(data) > 512 * 1024 * 1024:
        raise RuntimeError("Media file is too large.")
    content_type = _space_pdf_shared_audio_guess_mime(str(source_path), clean(meta.get("audioMime", meta.get("audio_mime", ""))))
    builder = chat_builder_tools()
    builder.ensure_server_asset_dirs()
    safe_stem = re.sub(r"[^0-9A-Za-z._-]+", "-", source_path.stem).strip("-") or "server-media"
    # Added 2026-07-16: copy server-side PDF/Picture media through the shared sharded Sound index.
    asset_link = builder.write_server_sound_file_asset(f"pdf-media-{safe_stem[:30]}", data, source_path.suffix.lower().lstrip("."))
    asset_path = (builder.SERVER_DATA_ROOT / asset_link).resolve()
    stored_audio_path, stored_mime, stored_size, stored_note = _space_pdf_shared_video_browser_copy(builder, asset_path, safe_stem, content_type)
    marker_result = save_space_pdf_shared_audio_marker(viewer, {
        "action": "save",
        "id": meta.get("id", ""),
        "path": meta.get("path", ""),
        "mode": meta.get("mode", "pdf"),
        "page": meta.get("page", 1),
        "text": meta.get("text", ""),
        "voice": meta.get("voice", ""),
        "audioPath": stored_audio_path,
        "audioMime": stored_mime or content_type,
        "sourceKind": stored_note or "server",
        "mediaKind": normalize_space_pdf_shared_media_kind(meta.get("mediaKind", meta.get("media_kind", "")), stored_audio_path, stored_mime or content_type),
        "displayMode": meta.get("displayMode", meta.get("display_mode", "button")),
        "w": meta.get("w", meta.get("width", 0.18)),
        "h": meta.get("h", meta.get("height", 0.14)),
    })
    marker_result["upload"] = {
        "audio_path": stored_audio_path,
        "audio_mime": stored_mime or content_type,
        "filename": source_path.name,
        "size": stored_size or len(data),
        "source": stored_note or "server",
    }
    return marker_result


def pick_space_pdf_shared_audio_server_file(username: str, fields: dict | None = None) -> dict:
    viewer = normalize_username(username)
    if not is_admin_user(viewer):
        raise RuntimeError("Only admins can upload shared media markers.")
    meta = dict(fields) if isinstance(fields, dict) else {}
    try:
        tkinter = __import__("tkinter")
        filedialog = __import__("tkinter.filedialog", fromlist=["askopenfilename"])
    except Exception as exc:
        raise RuntimeError(f"Khong mo duoc hop chon file tren may chu: {exc}") from exc
    root = None
    selected = ""
    try:
        root = tkinter.Tk()
        root.withdraw()
        try:
            root.attributes("-topmost", True)
            root.update()
        except Exception:
            pass
        extensions = sorted(SPACE_PDF_SHARED_AUDIO_ALLOWED_EXTENSIONS)
        pattern = " ".join(f"*{ext}" for ext in extensions)
        selected = filedialog.askopenfilename(
            parent=root,
            title="Choose shared media file on this server computer",
            filetypes=[
                ("Audio/video/picture files", pattern),
                ("All files", "*.*"),
            ],
        )
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass
    selected = clean(str(selected or ""))
    if not selected:
        return {"canceled": True}
    meta["server_path"] = selected
    return save_space_pdf_shared_audio_server_file(viewer, meta)
