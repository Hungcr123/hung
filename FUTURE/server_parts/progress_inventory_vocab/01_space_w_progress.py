# Loaded by FUTURE.server_parts.08_progress_inventory_vocab into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def space_w_progress_path(username: str) -> Path:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    # Updated 2026-07-22: locating an optional legacy export must never create per-user filesystem state.
    return user_folder_path(username) / SPACE_W_PROGRESS_FILE_NAME


def normalize_space_w_progress_path(relative_path: str, username: str, admin: bool = False) -> str:
    raw = clean_path_value(relative_path)
    if not raw:
        return ""
    target = safe_server_data_path(raw, username, admin=admin)
    effective_target = server_data_effective_file_path(target, username=username, admin=admin)
    if not effective_target.is_file() or not is_lesson_file(effective_target):
        raise RuntimeError("Chi duoc luu trang thai cho file Space_W/Space_V/Space_Q/Space_P/PDF/TXT trong C:\\server data.")
    return server_data_relative(effective_target)


def space_w_progress_key(username: str, relative_path: str = "", identity: str = "") -> str:
    username = normalize_username(username)
    raw_source = clean_path_value(relative_path) or clean(relative_path)
    raw_identity = clean(identity)[:240]
    suffix = Path(raw_source).suffix.lower() if raw_source else ""
    stable_identity = raw_identity if raw_identity.lower().startswith("ftg-lesson-") else ""
    if stable_identity and suffix not in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}:
        source = f"identity:{stable_identity}"
    elif raw_source:
        source = f"path:{raw_source.lower()}"
    elif raw_identity:
        source = f"identity:{raw_identity}"
    else:
        raise RuntimeError("Thieu duong dan hoac identity cua Space_W.")
    digest = hashlib.sha256(f"{username.lower()}|{source}".encode("utf-8")).hexdigest()[:32]
    return digest


def space_progress_legacy_path_key(username: str, relative_path: str = "", identity: str = "") -> str:
    username = normalize_username(username)
    rel_path = clean_path_value(relative_path)
    raw_identity = clean(identity)[:240]
    if rel_path:
        source = f"path:{rel_path.lower()}"
    elif raw_identity:
        source = f"identity:{raw_identity}"
    else:
        return ""
    return hashlib.sha256(f"{username.lower()}|{source}".encode("utf-8")).hexdigest()[:32]


def space_progress_identity_for_path(relative_path: str, username: str, admin: bool = False) -> dict:
    raw = clean_path_value(relative_path)
    if not raw:
        return {}
    contract_resolver = globals().get("resolve_lesson_identity_contract")
    registry_ready = globals().get("server_database_lesson_identity_registry_ready")
    if callable(contract_resolver):
        contract = contract_resolver(raw, username, admin=admin, strict=False)
        return {
            **contract,
            "path": clean_path_value(contract.get("effective_path", "")) or raw,
            "legacy_path": raw,
            "lesson_id": clean(contract.get("lesson_id", ""))[:240],
            "identity_authoritative": bool(callable(registry_ready) and registry_ready()),
        }
    resolved_path = raw
    effective = None
    try:
        target = safe_server_data_path(raw, username, admin=admin)
        effective = server_data_effective_file_path(target, username=username, admin=admin)
        if effective.is_file():
            resolved_path = clean_path_value(server_data_relative(effective)) or raw
    except Exception:
        resolved_path = raw
    lesson_id = ""
    identity_authoritative = False
    suffix = Path(resolved_path).suffix.lower()
    if suffix not in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}:
        registry_ready = globals().get("server_database_lesson_identity_registry_ready")
        registry_resolver = globals().get("server_database_lesson_file_id_for_path")
        identity_authoritative = bool(callable(registry_ready) and callable(registry_resolver) and registry_ready())
        if identity_authoritative:
            lesson_id = clean(registry_resolver(resolved_path))[:240]
        else:
            manifest_reader = globals().get("server_data_manifest_file_entry")
            entry = manifest_reader(resolved_path) if callable(manifest_reader) else None
            lesson_id = clean((entry or {}).get("lesson_id", ""))[:240] if isinstance(entry, dict) else ""
        if not lesson_id and not identity_authoritative:
            try:
                metadata = cached_lesson_file_metadata(effective) if effective is not None else {}
                lesson_id = clean((metadata or {}).get("lesson_id", ""))[:240]
            except Exception:
                lesson_id = ""
    return {
        "path": resolved_path,
        "legacy_path": raw,
        "lesson_id": lesson_id,
        "identity_authoritative": identity_authoritative,
    }


def canonical_identity_rollout_snapshot() -> dict:
    with CANONICAL_ID_FALLBACK_LOCK:
        counters = dict(CANONICAL_ID_FALLBACK_COUNTERS)
    return {
        "id_canonical_read": bool(ID_CANONICAL_READ),
        "id_canonical_write": bool(ID_CANONICAL_WRITE),
        "path_legacy_fallback": bool(PATH_LEGACY_FALLBACK),
        "path_write_block": bool(PATH_WRITE_BLOCK),
        "counters": counters,
    }


# Added 2026-07-24: count legacy fallbacks cheaply before path-only writes are blocked in a later rollout gate.
def record_canonical_identity_resolution(operation: str, identity_info: dict | None = None) -> None:
    info = identity_info if isinstance(identity_info, dict) else {}
    action = clean(operation).lower() or "resolve"
    canonical = clean(info.get("lesson_id") or info.get("identity")).lower().startswith("ftg-lesson-")
    bucket = "canonical" if canonical else "path_fallback"
    counter_prefix = action if "." in action else f"progress.{action}"
    with CANONICAL_ID_FALLBACK_LOCK:
        CANONICAL_ID_FALLBACK_COUNTERS[f"{counter_prefix}.{bucket}"] += 1
    if canonical:
        return
    if action.rsplit(".", 1)[-1] in {"write", "clear"} and PATH_WRITE_BLOCK:
        raise RuntimeError("Canonical lesson_id is required for progress writes")
    if not PATH_LEGACY_FALLBACK:
        raise RuntimeError("Legacy path fallback is disabled")


def space_progress_identity_for_source(username: str, source: dict | None = None, operation: str = "resolve") -> dict:
    payload = source if isinstance(source, dict) else {}
    admin = is_admin_user(username)
    identity = clean(payload.get("lesson_id") or payload.get("lessonId") or payload.get("identity") or payload.get("lesson") or "")[:240]
    raw_path = clean_path_value(payload.get("path", ""))
    info = space_progress_identity_for_path(raw_path, username, admin=admin) if raw_path else {}
    resolved_identity = clean(info.get("lesson_id", ""))[:240]
    if not truthy(info.get("identity_authoritative"), False):
        resolved_identity = resolved_identity or identity
    result = {
        "path": clean_path_value(info.get("path", "")) or raw_path,
        "legacy_path": raw_path,
        "identity": resolved_identity,
        "lesson_id": resolved_identity if resolved_identity.lower().startswith("ftg-lesson-") else "",
        "key": space_w_progress_key(username, clean_path_value(info.get("path", "")) or raw_path, resolved_identity),
        "legacy_key": space_progress_legacy_path_key(username, raw_path, identity),
    }
    if operation != "resolve":
        record_canonical_identity_resolution(operation, result)
    return result


# Added 2026-07-24: canonical lesson identity collapses stale path/run aliases to one RAM row before SQLite commit.
def space_progress_existing_canonical_state(
    states: dict,
    key: str,
    legacy_key: str = "",
    identity: str = "",
) -> tuple[dict, str]:
    current_key = clean(key)
    old_key = clean(legacy_key)
    existing = states.get(current_key) if isinstance(states.get(current_key), dict) else {}
    if not existing and old_key and old_key != current_key and isinstance(states.get(old_key), dict):
        existing = states.get(old_key)
    canonical_id = clean(identity)[:240]
    if existing or not canonical_id.lower().startswith("ftg-lesson-"):
        return existing, old_key
    for candidate_key, candidate in states.items():
        if not isinstance(candidate, dict):
            continue
        candidate_id = clean(candidate.get("lesson_id") or candidate.get("file_id") or candidate.get("identity"))[:240]
        if candidate_id == canonical_id:
            return candidate, clean(candidate_key)
    return {}, old_key


# Added 2026-07-21: GET lookup never trusts a client ID when SQLite quarantines or does not map the requested path.
def space_progress_lookup_for_request(username: str, relative_path: str = "", identity: str = "") -> dict:
    raw_path = clean_path_value(relative_path)
    info = space_progress_identity_for_path(raw_path, username, admin=is_admin_user(username)) if raw_path else {}
    resolved_path = clean_path_value(info.get("path", "")) or raw_path
    trusted_identity = clean(info.get("lesson_id", ""))[:240]
    if not truthy(info.get("identity_authoritative"), False):
        trusted_identity = trusted_identity or clean(identity)[:240]
    result = {
        "raw_path": raw_path,
        "path": resolved_path,
        "identity": trusted_identity,
        "identity_authoritative": truthy(info.get("identity_authoritative"), False),
    }
    record_canonical_identity_resolution("read", result)
    return result


def space_progress_backup_root() -> Path:
    root = SERVER_DATA_ROOT / "_future_path_backups" / "progress"
    root.mkdir(parents=True, exist_ok=True)
    return root


def backup_space_progress_file(path: Path, username: str = "", space: str = "", reason: str = "path-backup") -> str:
    try:
        source = Path(path)
        if not source.is_file():
            return ""
        stamp = time.strftime("%Y%m%d-%H%M%S")
        safe_user = normalize_username(username) or "unknown"
        safe_space = normalize_space_progress_space(space).lower()
        backup = space_progress_backup_root() / f"{safe_user}-{safe_space}-{clean(reason).replace(' ', '-') or 'backup'}-{stamp}-{source.name}"
        shutil.copy2(source, backup)
        return str(backup)
    except Exception:
        return ""


def space_progress_record_pick(existing: dict | None = None, incoming: dict | None = None) -> dict:
    left = existing if isinstance(existing, dict) else {}
    right = incoming if isinstance(incoming, dict) else {}
    if not left:
        return dict(right)
    if not right:
        return dict(left)
    left_stamp = timestamp_to_epoch(left.get("savedAt") or left.get("updatedAt"))
    right_stamp = timestamp_to_epoch(right.get("savedAt") or right.get("updatedAt"))
    return dict(right if right_stamp >= left_stamp else left)


def space_progress_saved_epoch(record: dict | None = None) -> float | None:
    source = record if isinstance(record, dict) else {}
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    return timestamp_to_epoch(source.get("savedAt") or source.get("saved_at") or state.get("savedAt") or state.get("saved_at"))


def merge_space_progress_newest(existing: dict | None, incoming: dict | None, space: str = "") -> dict:
    old = existing if isinstance(existing, dict) else {}
    new = incoming if isinstance(incoming, dict) else {}
    old_epoch = space_progress_saved_epoch(old)
    new_epoch = space_progress_saved_epoch(new)
    if old and old_epoch is not None and new_epoch is not None and old_epoch > new_epoch:
        # Preserve the newest active state while still carrying forward an older completion run.
        return merge_space_progress_completion_history(new, dict(old), space)
    return merge_space_progress_completion_history(old, new, space)


def space_progress_clear_is_stale(existing: dict | None, request_payload: dict | None) -> bool:
    old = existing if isinstance(existing, dict) else {}
    request = request_payload if isinstance(request_payload, dict) else {}
    old_state = old.get("state") if isinstance(old.get("state"), dict) else {}
    request_state = request.get("state") if isinstance(request.get("state"), dict) else {}
    expected_run_id = clean(
        request.get("expectedRunId")
        or request.get("expected_run_id")
        or request_state.get("expectedRunId")
        or request_state.get("expected_run_id")
    )
    active_run_id = clean(old.get("runId") or old.get("run_id") or old_state.get("runId") or old_state.get("run_id"))
    if expected_run_id and active_run_id and expected_run_id != active_run_id:
        return True
    base_revision = max(0, space_w_int(request.get("baseRevision", request.get("base_revision", 0)), 0))
    active_revision = max(0, space_w_int(old.get("_serverRevision", old.get("serverRevision", old.get("server_revision", 0))), 0))
    if base_revision and active_revision > base_revision:
        return True
    old_epoch = space_progress_saved_epoch(existing)
    clear_epoch = space_progress_saved_epoch(request_payload)
    return bool(old_epoch is not None and clear_epoch is not None and old_epoch > clear_epoch)


# Added 2026-07-15: keeps "learned at least once" history separate from the latest run progress.
def space_progress_completion_marker(record: dict | None = None, space: str = "") -> bool:
    source = record if isinstance(record, dict) else {}
    canonical_summary = globals().get("server_database_progress_completion_summary")
    if callable(canonical_summary):
        return bool(canonical_summary(source, space).get("current_run_complete"))
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    markers = (
        "complete",
        "lessonComplete",
        "lessonCompletionSent",
        "vocabComplete",
        "registryReady",
    )
    if any(truthy(source.get(key), False) or truthy(state.get(key), False) for key in markers):
        return True
    if clean(space) == "Space_W" and (truthy(source.get("reviewFinished"), False) or truthy(state.get("reviewFinished"), False)):
        return True
    total = max(0, space_w_int(source.get("nodeCount", state.get("nodeCount", 0)), 0))
    if clean(space) == "Space_V":
        learned_count = max(
            0,
            space_w_int(source.get("learnedCount", source.get("learned_count", 0)), 0),
            space_w_int(state.get("learnedCount", state.get("learned_count", 0)), 0),
            len({clean(item) for item in state.get("learned", []) if clean(item)}) if isinstance(state.get("learned"), list) else 0,
        )
        return bool(total and learned_count >= total)
    if clean(space) == "Space_Q":
        question_total = max(0, space_w_int(state.get("questionTotal", state.get("totalQuestions", 0)), 0))
        question_done = max(0, space_w_int(state.get("questionDone", state.get("completedQuestions", state.get("questionsDone", 0))), 0))
        if question_total:
            return question_done >= question_total
    if clean(space) in {"Space_P", "Space_S", "Space_L"}:
        segment_total = max(0, space_w_int(state.get("totalSegments", state.get("segmentTotal", state.get("totalTokens", state.get("tokenTotal", 0)))), 0))
        segment_done = max(0, space_w_int(state.get("completedSegments", state.get("segmentDone", state.get("completedTokens", state.get("tokenDone", 0)))), 0))
        if segment_total:
            return segment_done >= segment_total
    # Added 2026-07-24: Space_W stage 1 is not a lifetime completion.  Only
    # explicit completion/reviewFinished may create a completed run marker.
    node_progress = state.get("nodeProgress") if isinstance(state.get("nodeProgress"), dict) else {}
    if clean(space) != "Space_W" and total and len(node_progress) >= total:
        done_nodes = 0
        for item in node_progress.values():
            if not isinstance(item, dict):
                continue
            if item.get("nextPanelCanShow") or item.get("speakStepCompleted") or item.get("grammarStepCompleted") or item.get("reviewSpeakCompleted"):
                done_nodes += 1
        if done_nodes >= total:
            return True
    return False


# Added 2026-07-15: identifies a completed study run without mixing it with later partial autosaves.
def space_progress_completion_run_id(record: dict | None = None) -> str:
    source = record if isinstance(record, dict) else {}
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    for key in ("completionRunId", "completion_run_id", "runId", "run_id", "sessionId", "session_id"):
        value = clean(source.get(key) or state.get(key))
        if value:
            return value[:160]
    completed_at = clean(source.get("completedAt", source.get("completed_at", "")) or state.get("completedAt", state.get("completed_at", "")))
    return f"completed:{completed_at[:120]}" if completed_at else ""


# Added 2026-07-15: preserves historical completion runs while allowing a later partial run to drive the chart.
def merge_space_progress_completion_history(existing: dict | None, incoming: dict | None, space: str = "") -> dict:
    source = dict(incoming) if isinstance(incoming, dict) else {}
    old = existing if isinstance(existing, dict) else {}
    if not source:
        return source
    old_completed = space_progress_completion_marker(old, space)
    new_completed = space_progress_completion_marker(source, space)
    old_run_id = space_progress_completion_run_id(old)
    new_run_id = space_progress_completion_run_id(source)
    old_state = old.get("state") if isinstance(old.get("state"), dict) else {}
    source_state = source.get("state") if isinstance(source.get("state"), dict) else {}
    old_lesson_source = old_state.get("lessonSource") if isinstance(old_state.get("lessonSource"), dict) else {}
    source_lesson_source = source_state.get("lessonSource") if isinstance(source_state.get("lessonSource"), dict) else {}
    old_lesson_study = old_lesson_source.get("study") if isinstance(old_lesson_source.get("study"), dict) else {}
    source_lesson_study = source_lesson_source.get("study") if isinstance(source_lesson_source.get("study"), dict) else {}
    old_lesson_progress = old_lesson_study.get("progress") if isinstance(old_lesson_study.get("progress"), dict) else {}
    source_lesson_progress = source_lesson_study.get("progress") if isinstance(source_lesson_study.get("progress"), dict) else {}
    old_runs = max(
        0,
        space_w_int(old.get("completedRuns", old.get("completed_runs", 0)), 0),
        space_w_int(old_lesson_study.get("mine", 0), 0),
        space_w_int(old_lesson_study.get("completedRuns", old_lesson_study.get("completed_runs", 0)), 0),
        space_w_int(old_lesson_progress.get("completedRuns", old_lesson_progress.get("completed_runs", 0)), 0),
    )
    if old_completed:
        old_runs = max(old_runs, 1)
    new_runs = max(
        0,
        space_w_int(source.get("completedRuns", source.get("completed_runs", 0)), 0),
        space_w_int(source_lesson_study.get("mine", 0), 0),
        space_w_int(source_lesson_study.get("completedRuns", source_lesson_study.get("completed_runs", 0)), 0),
        space_w_int(source_lesson_progress.get("completedRuns", source_lesson_progress.get("completed_runs", 0)), 0),
    )
    runs = max(old_runs, new_runs)
    if new_completed and old_run_id and new_run_id and new_run_id != old_run_id:
        runs = max(runs, old_runs + 1)
    elif new_completed and not old_completed:
        runs = max(runs, old_runs + 1)
    elif new_completed:
        runs = max(runs, 1)
    old_at = clean(old.get("completedAt", old.get("completed_at", "")) or old_state.get("completedAt", old_state.get("completed_at", "")))
    new_at = clean(source.get("completedAt", source.get("completed_at", "")) or source_state.get("completedAt", source_state.get("completed_at", "")))
    if new_completed and not new_at:
        new_at = clean(source.get("updatedAt") or source.get("savedAt"))
    completed_at = timestamp_latest_text(old_at, new_at)
    if runs > 0:
        source["completedRuns"] = runs
        source["completed_runs"] = runs
        source["completedAt"] = completed_at
        if new_completed and new_run_id:
            source["completionRunId"] = new_run_id
        elif old_run_id:
            source["completionRunId"] = old_run_id
        source["learned"] = True
    return source


def normalize_space_progress_record_to_path(space: str, username: str, record: dict | None = None, legacy_key: str = "") -> tuple[str, dict, bool]:
    source = dict(record) if isinstance(record, dict) else {}
    if not source:
        return clean(legacy_key), {}, False
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    identity = clean(source.get("identity") or source.get("lesson") or state.get("identity") or "")[:240]
    raw_path = clean_path_value(source.get("path") or state.get("path") or "")
    changed = False
    if raw_path:
        try:
            resolved = space_progress_identity_for_path(raw_path, username, admin=is_admin_user(username))
        except Exception:
            resolved = {}
        if resolved:
            next_path = clean_path_value(resolved.get("path", ""))
            if next_path and next_path != raw_path:
                raw_path = next_path
                changed = True
    next_key = space_w_progress_key(username, raw_path, identity) if raw_path or identity else clean(legacy_key)
    next_record = dict(source)
    next_record["path"] = raw_path
    next_record["identity"] = identity
    next_record["key"] = next_key
    if legacy_key and legacy_key != next_key:
        next_record["legacy_path_key"] = clean(legacy_key)
        changed = True
    if clean(source.get("key", "")) != next_key:
        changed = True
    return next_key, next_record, changed


def normalize_space_progress_payload_to_path(space: str, username: str, payload: dict | None = None) -> tuple[dict, bool]:
    return clone_space_progress_payload(payload), False


def read_space_w_progress_file(username: str) -> dict:
    path = space_w_progress_path(username)
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


def write_space_w_progress_file(username: str, payload: dict) -> None:
    path = space_w_progress_path(username)
    states = payload.get("states") if isinstance(payload.get("states"), dict) else {}
    out = {
        "version": 1,
        "updated_at": utc_timestamp(),
        "states": states,
    }
    atomic_write_json(path, out, indent=2)
    invalidate_cached_payload(f"space-w:{normalize_username(username).lower()}")


def normalize_space_progress_space(space: str = "") -> str:
    raw = clean(space or "Space_W")
    if raw in {"Space_V", "Space_Q", "Space_W", "Space_P", "Space_PDF"}:
        return raw
    if raw in {"Space_S", "Space_L"}:
        return "Space_P"
    if raw == "Space_Picture":
        return "Space_PDF"
    return "Space_W"


def default_space_progress_payload() -> dict:
    return {"version": 1, "updated_at": "", "states": {}}


def normalize_space_progress_payload(payload: dict | None = None) -> dict:
    source = payload if isinstance(payload, dict) else {}
    states = source.get("states") if isinstance(source.get("states"), dict) else {}
    return {
        "version": int(source.get("version", 1) or 1),
        "updated_at": clean(source.get("updated_at", "")),
        "states": {clean(key): value for key, value in states.items() if clean(key) and isinstance(value, dict)},
    }


def clone_space_progress_payload(payload: dict | None = None) -> dict:
    source = normalize_space_progress_payload(payload)
    states = source.get("states") if isinstance(source.get("states"), dict) else {}
    return {
        "version": int(source.get("version", 1) or 1),
        "updated_at": clean(source.get("updated_at", "")),
        "states": {clean(key): dict(value) for key, value in states.items() if clean(key) and isinstance(value, dict)},
    }


def space_progress_cache_key(space: str = "", username: str = "") -> str:
    username = normalize_username(username)
    normalized_space = normalize_space_progress_space(space)
    if normalized_space == "Space_V":
        return f"space-v:{username.lower()}"
    if normalized_space == "Space_Q":
        return f"space-q:{username.lower()}"
    if normalized_space == "Space_P":
        return f"space-p:{username.lower()}"
    if normalized_space == "Space_PDF":
        return f"space-pdf:{username.lower()}"
    return f"space-w:{username.lower()}"


def space_progress_path(space: str = "", username: str = "") -> Path:
    normalized_space = normalize_space_progress_space(space)
    if normalized_space == "Space_V":
        return space_v_progress_path(username)
    if normalized_space == "Space_Q":
        return space_q_progress_path(username)
    if normalized_space == "Space_P":
        return space_p_progress_path(username)
    if normalized_space == "Space_PDF":
        return space_pdf_progress_path(username)
    return space_w_progress_path(username)


def space_progress_existing_path(space: str = "", username: str = "") -> Path:
    # Added 2026-07-06: checks progress presence on open without creating user folders.
    username = normalize_username(username)
    normalized_space = normalize_space_progress_space(space)
    if normalized_space == "Space_V":
        name = SPACE_V_PROGRESS_FILE_NAME
    elif normalized_space == "Space_Q":
        name = SPACE_Q_PROGRESS_FILE_NAME
    elif normalized_space == "Space_P":
        name = SPACE_P_PROGRESS_FILE_NAME
    elif normalized_space == "Space_PDF":
        name = SPACE_PDF_PROGRESS_FILE_NAME
    else:
        name = SPACE_W_PROGRESS_FILE_NAME
    return USER_ROOT / username / name


def space_progress_maybe_available(space: str = "", username: str = "") -> bool:
    # Added 2026-07-06: lets progress GET for new lessons return fast without path resolution/disk setup.
    username = normalize_username(username)
    if not username:
        return False
    normalized_space = normalize_space_progress_space(space)
    key = space_progress_store_entry_key(normalized_space, username)
    with SPACE_PROGRESS_STORE_LOCK:
        row = SPACE_PROGRESS_STORE.get(key)
        if isinstance(row, dict) and isinstance(row.get("payload"), dict):
            return True
    progress_path = space_progress_existing_path(normalized_space, username)
    if progress_path.is_file():
        return True
    if space_progress_wal_enabled(normalized_space):
        wal_path = progress_path.with_name(f"{progress_path.name}.wal.jsonl")
        try:
            return wal_path.is_file() and int(wal_path.stat().st_size) > 0
        except OSError:
            return False
    return False


def space_progress_wal_enabled(space: str = "") -> bool:
    return normalize_space_progress_space(space) in {"Space_W", "Space_Q", "Space_V", "Space_P", "Space_PDF"}


def space_progress_wal_path(space: str = "", username: str = "") -> Path:
    progress_path = space_progress_path(space, username)
    return progress_path.with_name(f"{progress_path.name}.wal.jsonl")


def append_space_progress_wal(space: str = "", username: str = "", entry: dict | None = None) -> None:
    if not space_progress_wal_enabled(space) or not isinstance(entry, dict):
        return
    append_space_progress_wal_entries(space, username, [entry])

# Added 2026-07-15: batch delta WAL writes so many POSTs for one user hit disk once per flush window.
def append_space_progress_wal_entries(space: str = "", username: str = "", entries: list[dict] | tuple[dict, ...] | None = None) -> None:
    normalized_space = normalize_space_progress_space(space)
    if not space_progress_wal_enabled(normalized_space) or not isinstance(entries, (list, tuple)) or not entries:
        return
    wal_path = space_progress_wal_path(space, username)
    wal_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_user = normalize_username(username)
    written_at = utc_timestamp()
    with wal_path.open("a", encoding="utf-8", newline="\n") as handle:
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            row = {
                "version": 1,
                "space": normalized_space,
                "username": normalized_user,
                "written_at": written_at,
                **entry,
            }
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def apply_space_progress_wal_entry(payload: dict, entry: dict | None = None) -> dict:
    if not isinstance(entry, dict):
        return payload
    op = clean(entry.get("op", "upsert")).lower()
    key = clean(entry.get("key", ""))
    states = payload.setdefault("states", {})
    if op == "remove":
        if key:
            states.pop(key, None)
        return payload
    record = entry.get("record")
    if key and isinstance(record, dict):
        states[key] = space_progress_record_pick(record, states.get(key))
    return payload


def replay_space_progress_wal(space: str = "", username: str = "", payload: dict | None = None) -> dict:
    out = clone_space_progress_payload(payload)
    if not space_progress_wal_enabled(space):
        return out
    wal_path = space_progress_wal_path(space, username)
    if not wal_path.is_file():
        return out
    try:
        # Updated 2026-07-06: skip empty WAL files left after durable flushes on hot open paths.
        if int(wal_path.stat().st_size) <= 0:
            return out
        with wal_path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                raw = clean(line)
                if not raw:
                    continue
                try:
                    entry = json.loads(raw)
                except Exception:
                    continue
                apply_space_progress_wal_entry(out, entry if isinstance(entry, dict) else {})
    except Exception:
        return out
    return normalize_space_progress_payload(out)


def truncate_space_progress_wal(space: str = "", username: str = "") -> None:
    if not space_progress_wal_enabled(space):
        return
    wal_path = space_progress_wal_path(space, username)
    try:
        # Updated 2026-07-06: remove flushed WALs so later Space_W opens do not touch empty files.
        wal_path.unlink(missing_ok=True)
    except Exception:
        pass


def read_space_progress_disk_payload(space: str = "", username: str = "") -> dict:
    database_loader = globals().get("server_database_load_progress_payload")
    if callable(database_loader):
        database_payload = database_loader(space, username)
        if isinstance(database_payload, dict):
            # Added 2026-07-20: migrate acknowledged legacy PDF WAL deltas into SQLite before retiring the file path.
            if normalize_space_progress_space(space) == "Space_PDF":
                wal_path = space_progress_wal_path(space, username)
                try:
                    has_legacy_wal = wal_path.is_file() and int(wal_path.stat().st_size) > 0
                except OSError:
                    has_legacy_wal = False
                if has_legacy_wal:
                    database_payload = replay_space_progress_wal(space, username, database_payload)
                    database_replace = globals().get("server_database_replace_progress_payload")
                    if callable(database_replace):
                        database_replace(space, username, database_payload)
                        truncate_space_progress_wal(space, username)
            return normalize_space_progress_payload(database_payload)
    path = space_progress_path(space, username)
    if not path.is_file():
        wal_path = space_progress_wal_path(space, username)
        try:
            has_legacy_wal = wal_path.is_file() and int(wal_path.stat().st_size) > 0
        except OSError:
            has_legacy_wal = False
        # Added 2026-07-20: a read of an untouched namespace must not create an empty SQLite row.
        if not has_legacy_wal:
            return default_space_progress_payload()
        payload = replay_space_progress_wal(space, username, default_space_progress_payload())
        database_replace = globals().get("server_database_replace_progress_payload")
        if callable(database_replace):
            database_replace(space, username, payload)
        return payload
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        payload = {}
    payload = replay_space_progress_wal(space, username, normalize_space_progress_payload(payload))
    database_replace = globals().get("server_database_replace_progress_payload")
    if callable(database_replace):
        database_replace(space, username, payload)
    return payload


def write_space_progress_disk_payload(space: str = "", username: str = "", payload: dict | None = None, merge_existing: bool = False) -> dict:
    path = space_progress_path(space, username)
    out = clone_space_progress_payload(payload)
    if merge_existing and path.is_file():
        existing = read_space_progress_disk_payload(space, username)
        existing_states = existing.get("states") if isinstance(existing.get("states"), dict) else {}
        out_states = out.setdefault("states", {})
        for key, record in existing_states.items():
            clean_key = clean(key)
            if not clean_key or not isinstance(record, dict):
                continue
            picked = space_progress_record_pick(record, out_states.get(clean_key))
            out_states[clean_key] = merge_space_progress_completion_history(record, picked, space)
    out["updated_at"] = utc_timestamp()
    atomic_write_json(path, out, indent=2)
    truncate_space_progress_wal(space, username)
    invalidate_cached_payload(space_progress_cache_key(space, username))
    return out


def trim_space_progress_payload(payload: dict | None = None, limit: int = 0) -> dict:
    source = normalize_space_progress_payload(payload)
    # Updated 2026-07-14: learner progress is durable history; do not drop old learned rows by default.
    if not limit:
        return source
    states = source.get("states") if isinstance(source.get("states"), dict) else {}
    if len(states) <= max(1, int(limit or 240)):
        return source
    ordered = sorted(states.items(), key=lambda item: timestamp_order_key(item[1].get("updatedAt") or item[1].get("savedAt")))
    source["states"] = dict(ordered[-max(1, int(limit or 240)):])
    return source


def space_progress_store_entry_key(space: str = "", username: str = "") -> str:
    return f"{normalize_space_progress_space(space)}|{normalize_username(username).lower()}"


def space_progress_user_lock(space: str = "", username: str = ""):
    key = space_progress_store_entry_key(space, username)
    with SPACE_PROGRESS_STORE_LOCK:
        row = SPACE_PROGRESS_STORE.get(key)
        if not isinstance(row, dict):
            row = {"lock": threading.RLock()}
            SPACE_PROGRESS_STORE[key] = row
        lock = row.get("lock")
        if lock is None:
            lock = threading.RLock()
            row["lock"] = lock
        return lock


def load_space_progress_store(space: str = "", username: str = "") -> dict:
    username = normalize_username(username)
    normalized_space = normalize_space_progress_space(space)
    key = space_progress_store_entry_key(normalized_space, username)
    now = time.time()
    with SPACE_PROGRESS_STORE_LOCK:
        row = SPACE_PROGRESS_STORE.get(key)
        if isinstance(row, dict) and isinstance(row.get("payload"), dict):
            row["space"] = normalized_space
            row["username"] = username
            row["touched_at"] = now
            return row
        lock = row.get("lock") if isinstance(row, dict) else None
    payload = read_space_progress_disk_payload(normalized_space, username)
    wal_path = space_progress_wal_path(normalized_space, username)
    try:
        wal_pending_compaction = bool(wal_path.is_file() and wal_path.stat().st_size > 0)
    except Exception:
        wal_pending_compaction = False
    with SPACE_PROGRESS_STORE_LOCK:
        row = SPACE_PROGRESS_STORE.get(key)
        if not isinstance(row, dict):
            row = {}
            SPACE_PROGRESS_STORE[key] = row
        row["space"] = normalized_space
        row["username"] = username
        row["lock"] = lock or row.get("lock") or threading.RLock()
        row["payload"] = clone_space_progress_payload(payload)
        states = row["payload"].get("states") if isinstance(row["payload"].get("states"), dict) else {}
        row["write_revision"] = max(
            [max(0, space_w_int(record.get("_serverRevision", 0), 0)) for record in states.values() if isinstance(record, dict)] or [0]
        )
        row["dirty"] = False
        row["force_flush"] = False
        row["wal_pending_compaction"] = wal_pending_compaction
        row["last_flush"] = now
        row["touched_at"] = now
        return row


def seed_space_progress_store_payload(space: str = "", username: str = "", payload: dict | None = None) -> None:
    """Added 2026-07-28: warm the RAM progress store from a batched DB read."""
    normalized_space = normalize_space_progress_space(space)
    normalized_user = normalize_username(username)
    if not normalized_user or not normalized_space:
        return
    key = space_progress_store_entry_key(normalized_space, normalized_user)
    now = time.time()
    source = normalize_space_progress_payload(payload if isinstance(payload, dict) else default_space_progress_payload())
    states = source.get("states") if isinstance(source.get("states"), dict) else {}
    with SPACE_PROGRESS_STORE_LOCK:
        row = SPACE_PROGRESS_STORE.get(key)
        if not isinstance(row, dict):
            row = {}
            SPACE_PROGRESS_STORE[key] = row
        row["space"] = normalized_space
        row["username"] = normalized_user
        row["lock"] = row.get("lock") or threading.RLock()
        row["payload"] = clone_space_progress_payload(source)
        row["write_revision"] = max(
            [max(0, space_w_int(record.get("_serverRevision", 0), 0)) for record in states.values() if isinstance(record, dict)] or [0]
        )
        row["dirty"] = False
        row["force_flush"] = False
        row["wal_pending_compaction"] = False
        row["last_flush"] = now
        row["touched_at"] = now

def remember_space_progress_store(space: str = "", username: str = "", payload: dict | None = None, force: bool = False, merge_existing: bool = False, wal_entry: dict | None = None) -> dict:
    normalized_space = normalize_space_progress_space(space)
    row = load_space_progress_store(space, username)
    row["payload"] = trim_space_progress_payload(payload)
    row["dirty"] = True
    row["force_flush"] = bool(force)
    row["merge_existing"] = bool(merge_existing or (normalized_space == "Space_V" and not force))
    if space_progress_wal_enabled(normalized_space) and isinstance(wal_entry, dict):
        persisted_wal_entry = {key: value for key, value in wal_entry.items() if key != "completion_event"}
        pending = row.get("pending_wal_entries")
        if not isinstance(pending, list):
            pending = []
        pending.append(persisted_wal_entry)
        if len(pending) > 500:
            pending = pending[-500:]
        row["pending_wal_entries"] = pending
    row["touched_at"] = time.time()
    database_apply = globals().get("server_database_apply_progress_entry")
    database_replace = globals().get("server_database_replace_progress_payload")
    if isinstance(wal_entry, dict) and callable(database_apply):
        database_apply(normalized_space, username, wal_entry)
    elif callable(database_replace):
        database_replace(normalized_space, username, row["payload"])
    bump_login_preload_cache_generation(username)
    start_space_progress_flusher()
    if force:
        flush_space_progress_store(force=True, target_keys=[space_progress_store_entry_key(space, username)])
    return row["payload"]


# Added 2026-07-20: hot autosaves mutate one RAM entry and persist one SQLite delta without cloning all user lessons.
def remember_space_progress_store_entry(
    space: str,
    username: str,
    key: str,
    record: dict,
    legacy_key: str = "",
    wal_entry: dict | None = None,
    postgres_authoritative: bool = False,
) -> dict:
    normalized_space = normalize_space_progress_space(space)
    row = load_space_progress_store(normalized_space, username)
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else default_space_progress_payload()
    states = payload.setdefault("states", {})
    revision = max(0, space_w_int(row.get("write_revision", 0), 0)) + 1
    record["_serverRevision"] = revision
    persisted_wal_entry = {item_key: value for item_key, value in (wal_entry or {}).items() if item_key != "completion_event"}
    if isinstance(wal_entry, dict):
        persisted_wal_entry["record"] = record
        if clean(legacy_key):
            persisted_wal_entry["legacy_key"] = clean(legacy_key)
    if postgres_authoritative:
        database_apply = globals().get("server_database_apply_progress_entry")
        if not callable(database_apply):
            raise RuntimeError("PostgreSQL progress writer is unavailable")
        database_apply(normalized_space, username, {**persisted_wal_entry, "completion_event": wal_entry.get("completion_event") if isinstance(wal_entry, dict) else None})
    row["write_revision"] = revision
    states[clean(key)] = record
    old_key = clean(legacy_key)
    if old_key and old_key != clean(key):
        states.pop(old_key, None)
    payload["updated_at"] = clean(record.get("updatedAt") or record.get("savedAt")) or utc_timestamp()
    row["payload"] = payload
    if not postgres_authoritative:
        row["dirty"] = True
        row["force_flush"] = False
        row["merge_existing"] = normalized_space == "Space_V"
    if not postgres_authoritative and space_progress_wal_enabled(normalized_space) and isinstance(wal_entry, dict):
        pending = row.get("pending_wal_entries")
        if not isinstance(pending, list):
            pending = []
        pending.append(persisted_wal_entry)
        row["pending_wal_entries"] = pending[-500:]
    row["touched_at"] = time.time()
    bump_login_preload_cache_generation(username)
    if not postgres_authoritative:
        start_space_progress_flusher()
    return record


def flush_space_progress_store(force: bool = False, target_keys: list[str] | tuple[str, ...] | None = None) -> None:
    now = time.time()
    persisted_any = False
    with SPACE_PROGRESS_STORE_LOCK:
        keys = list(target_keys) if isinstance(target_keys, (list, tuple)) else list(SPACE_PROGRESS_STORE.keys())
    for key in keys:
        with SPACE_PROGRESS_STORE_LOCK:
            row = SPACE_PROGRESS_STORE.get(key)
            if not isinstance(row, dict):
                continue
            dirty = bool(row.get("dirty"))
            wal_pending_compaction = bool(row.get("wal_pending_compaction"))
            force_flush = bool(row.get("force_flush"))
            delta_flush_now = bool(row.get("delta_flush_now"))
            last_flush = float(row.get("last_flush") or 0.0)
            lock = row.get("lock")
            if not dirty and not (force and wal_pending_compaction):
                continue
            if not force and not force_flush and not delta_flush_now and now - last_flush < SPACE_PROGRESS_FLUSH_INTERVAL_SECONDS:
                continue
            space = clean(row.get("space", ""))
            username = normalize_username(row.get("username", ""))
            if not username or lock is None:
                continue
        with lock:
            with SPACE_PROGRESS_STORE_LOCK:
                active = SPACE_PROGRESS_STORE.get(key)
                active_dirty = bool(active.get("dirty")) if isinstance(active, dict) else False
                active_wal_pending = bool(active.get("wal_pending_compaction")) if isinstance(active, dict) else False
                if active is not row or (not active_dirty and not (force and active_wal_pending)):
                    continue
                payload = clone_space_progress_payload(active.get("payload"))
                space = clean(active.get("space", ""))
                username = normalize_username(active.get("username", ""))
                merge_existing = bool(active.get("merge_existing"))
                pending_wal_entries = list(active.get("pending_wal_entries") or [])
                should_write_delta = bool(not force and not force_flush and space_progress_wal_enabled(space) and pending_wal_entries)
            if should_write_delta:
                append_space_progress_wal_entries(space, username, pending_wal_entries)
                with SPACE_PROGRESS_STORE_LOCK:
                    active = SPACE_PROGRESS_STORE.get(key)
                    if active is row:
                        active["dirty"] = False
                        active["force_flush"] = False
                        active["merge_existing"] = False
                        active["pending_wal_entries"] = []
                        active["delta_flush_now"] = False
                        active["wal_pending_compaction"] = True
                        active["last_flush"] = time.time()
                        active["touched_at"] = active["last_flush"]
                continue
            persisted = write_space_progress_disk_payload(space, username, payload, merge_existing=merge_existing)
            with SPACE_PROGRESS_STORE_LOCK:
                active = SPACE_PROGRESS_STORE.get(key)
                if active is row:
                    active["payload"] = clone_space_progress_payload(persisted)
                    active["dirty"] = False
                    active["force_flush"] = False
                    active["merge_existing"] = False
                    active["pending_wal_entries"] = []
                    active["delta_flush_now"] = False
                    active["wal_pending_compaction"] = False
                    active["last_flush"] = time.time()
                    active["touched_at"] = active["last_flush"]
            persisted_any = True
    # WAL deltas are already durable and startup replays them. Rewriting the boot
    # snapshot for every page-pin click adds avoidable CPU without changing recovery.
    if persisted_any:
        schedule_future_boot_snapshot_write("space_progress_flush", delay=1.0)


def start_space_progress_flusher() -> None:
    global SPACE_PROGRESS_FLUSHER_STARTED
    with SPACE_PROGRESS_STORE_LOCK:
        if SPACE_PROGRESS_FLUSHER_STARTED:
            return
        SPACE_PROGRESS_FLUSHER_STARTED = True

    def _runner() -> None:
        while not SERVER_STATE.get("shutdown_requested"):
            time.sleep(0.75)
            try:
                flush_space_progress_store(False)
            except Exception:
                pass
        try:
            flush_space_progress_store(True)
        except Exception:
            pass

    threading.Thread(target=_runner, daemon=True, name="future-space-progress-flusher").start()


def clear_space_progress_store_user(username: str = "") -> None:
    wanted = normalize_username(username).lower()
    if not wanted:
        return
    with SPACE_PROGRESS_STORE_LOCK:
        for key in list(SPACE_PROGRESS_STORE.keys()):
            if key.endswith(f"|{wanted}"):
                SPACE_PROGRESS_STORE.pop(key, None)


atexit.register(lambda: flush_space_progress_store(True))


def normalize_all_space_progress_to_path() -> dict:
    return {"ok": True, "users": len(list_dashboard_usernames()), "migrated_files": 0, "backups": 0}


def read_space_w_progress(username: str, relative_path: str = "", identity: str = "") -> dict | None:
    username = normalize_username(username)
    if not space_progress_maybe_available("Space_W", username):
        return None
    raw_path = clean_path_value(relative_path)
    raw_key = space_w_progress_key(username, raw_path, "")
    # Added 2026-07-20: find migrated Space_W records in RAM before cloning namespaces or resolving disk paths.
    with space_progress_user_lock("Space_W", username):
        row = load_space_progress_store("Space_W", username)
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
    key = space_w_progress_key(username, source_path, trusted_identity)
    with space_progress_user_lock("Space_W", username):
        row = load_space_progress_store("Space_W", username)
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


def space_w_int(value: object, default: int = 0) -> int:
    try:
        return int(value or default)
    except Exception:
        return int(default or 0)


# Added 2026-07-20: supports cheap cross-device revalidation of checkpoint plus voice preferences.
def space_w_progress_etag(record: dict | None, preferences: dict | None, username: str = "", relative_path: str = "", identity: str = "") -> str:
    source = record if isinstance(record, dict) else {}
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    prefs = preferences if isinstance(preferences, dict) else {}
    space_voice = prefs.get("space_w_voice") if isinstance(prefs.get("space_w_voice"), dict) else {}
    ghost_voice = prefs.get("ghost_en_voice") if isinstance(prefs.get("ghost_en_voice"), dict) else {}
    parts = (
        normalize_username(username).lower(),
        clean_path_value(relative_path).lower(),
        clean(identity or source.get("identity", "")).lower(),
        clean(source.get("key") or ""),
        clean(source.get("_serverRevision") or source.get("serverRevision") or source.get("server_revision") or "0"),
        clean(source.get("savedAt") or source.get("saved_at") or state.get("savedAt") or state.get("saved_at") or ""),
        clean(source.get("updatedAt") or source.get("updated_at") or state.get("updatedAt") or state.get("updated_at") or ""),
        clean(source.get("runId") or source.get("run_id") or state.get("runId") or state.get("run_id") or ""),
        clean(state.get("currentIndex") or state.get("nodeIndex") or source.get("nodeIndex") or "0"),
        clean(state.get("progressDone") or source.get("progressDone") or "0"),
        clean(state.get("progressTotal") or source.get("progressTotal") or "0"),
        "1" if state.get("trainEnabled") or source.get("trainEnabled") else "0",
        clean(prefs.get("_serverRevision") or "0"),
        clean(prefs.get("updated_at") or ""),
        clean(space_voice.get("value") or ""),
        clean(space_voice.get("updated_at") or ""),
        clean(ghost_voice.get("voice") or ""),
        clean(ghost_voice.get("updated_at") or ""),
        "present" if source else "missing",
    )
    digest = hashlib.sha256("|".join(parts).encode("utf-8", "ignore")).hexdigest()[:24]
    return f'W/"space-w-progress-{digest}"'


# Added 2026-07-21: identifies an acknowledged Space_W snapshot while ignoring server-only revision fields.
def space_w_progress_semantic_identity(record: dict | None) -> str:
    source = dict(record) if isinstance(record, dict) else {}
    for key in ("updatedAt", "updated_at", "_serverRevision", "serverRevision", "server_revision", "pendingServerSync", "serverSyncedAt", "serverSyncedSavedAt"):
        source.pop(key, None)
    encoded = json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8", "ignore")).hexdigest()


# Added 2026-07-21: autosave ACKs return only canonical ordering/history fields already missing locally.
def space_w_progress_compact_response(record: dict | None) -> dict:
    source = record if isinstance(record, dict) else {}
    keys = (
        "version", "key", "path", "legacy_path", "identity", "title", "nodeIndex", "nodeCount",
        "savedAt", "updatedAt", "runId", "run_id", "activeRun", "reviewing", "reviewRun",
        "progressDone", "progressTotal", "rootNodeCount", "normalSentenceCount", "trainSentenceCount",
        "sentenceCount", "complete", "lessonComplete", "completedRuns", "completed_runs", "completedAt",
        "completed_at", "completionRunId", "completion_run_id", "syncOperationId", "sync_operation_id",
        "_serverRevision",
    )
    return {key: source[key] for key in keys if key in source}


def space_w_progress_work_counts(record: dict | None = None) -> tuple[int, int]:
    source = record if isinstance(record, dict) else {}
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    node_total = max(0, space_w_int(source.get("nodeCount", state.get("nodeCount", 0)), 0))
    if not node_total:
        return 0, 0
    explicit_total = max(0, space_w_int(source.get("progressTotal", source.get("progress_total", state.get("progressTotal", state.get("progress_total", 0)))), 0))
    total = max(node_total * 2, explicit_total)
    explicit_done_value = source.get("progressDone", source.get("progress_done", state.get("progressDone", state.get("progress_done"))))
    if explicit_done_value is not None:
        done = max(0, space_w_int(explicit_done_value, 0))
    else:
        reviewing = truthy(source.get("reviewing"), False) or truthy(source.get("reviewRun"), False) or truthy(state.get("reviewing"), False) or truthy(state.get("reviewRun"), False) or truthy(state.get("reviewModeActive"), False)
        review_mastered = state.get("reviewMastered") if isinstance(state.get("reviewMastered"), list) else []
        mastered_indexes: set[int] = set()
        for value in review_mastered:
            try:
                mastered_index = int(value)
            except (TypeError, ValueError):
                continue
            if 0 <= mastered_index < node_total:
                mastered_indexes.add(mastered_index)
        mastered_count = len(mastered_indexes)
        node_index = max(0, space_w_int(source.get("nodeIndex", state.get("currentIndex", state.get("index", state.get("nodeIndex", 0)))), 0))
        done = node_total + mastered_count if reviewing else node_index
    if space_progress_completion_marker(source, "Space_W") or space_progress_completion_marker({"state": state}, "Space_W"):
        done = total
    return max(0, min(done, total)), total


# Added 2026-07-06: patches the hot Lesson Vault row after path-based progress saves.
def space_progress_lesson_vault_study_patch(record: dict, space: str = "") -> dict:
    source = record if isinstance(record, dict) else {}
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    total = max(0, space_w_int(source.get("nodeCount", state.get("nodeCount", 0)), 0))
    node_index = max(0, space_w_int(source.get("nodeIndex", state.get("currentIndex", state.get("index", state.get("nodeIndex", 0)))), 0))
    done = node_index
    if space == "Space_W":
        done, total = space_w_progress_work_counts(source)
    elif space == "Space_Q":
        total = max(total, space_w_int(state.get("questionTotal", state.get("totalQuestions", 0)), 0))
        done = max(done, space_w_int(state.get("questionDone", state.get("completedQuestions", state.get("questionsDone", 0))), 0))
    elif space in {"Space_P", "Space_S", "Space_L"}:
        total = max(total, space_w_int(state.get("totalSegments", state.get("segmentTotal", state.get("totalTokens", state.get("tokenTotal", 0)))), 0))
        done = max(done, space_w_int(state.get("completedSegments", state.get("segmentDone", state.get("completedTokens", state.get("tokenDone", 0)))), 0))
    elif space_progress_completion_marker(source, space) or space_progress_completion_marker({"state": state}, space):
        done = max(done, total)
    if total:
        done = max(0, min(done, total))
    percent = int(round((done / total) * 100)) if total else 0
    progress = {
        "space": space,
        "label": lesson_progress_label(space) if "lesson_progress_label" in globals() else space,
        "done": done,
        "total": total,
        "percent": max(0, min(100, percent)),
        "text": f"{done}/{total}" if total else "",
        "completed": bool(total and done >= total),
        "in_progress": bool(total and done < total and done > 0),
        "updatedAt": clean(source.get("updatedAt") or source.get("savedAt")),
        "savedAt": clean(source.get("savedAt") or source.get("updatedAt")),
    }
    if space == "Space_W":
        reviewing = bool(source.get("reviewing") or source.get("reviewRun") or state.get("reviewing") or state.get("reviewRun") or state.get("reviewModeActive"))
        active_run = bool(source.get("activeRun") or source.get("active_run") or state.get("activeRun") or state.get("active_run"))
        progress.update({
            "activeRun": active_run,
            "reviewing": reviewing,
            "reviewRun": reviewing,
            "runId": clean(source.get("runId") or source.get("run_id") or state.get("runId") or state.get("run_id")),
            "node_done": max(0, min(node_index, max(0, space_w_int(source.get("nodeCount", state.get("nodeCount", 0)), 0)))),
            "node_total": max(0, space_w_int(source.get("nodeCount", state.get("nodeCount", 0)), 0)),
        })
        progress["nodes_text"] = f'{progress["node_done"]}/{progress["node_total"]}' if progress["node_total"] else ""
    completed_runs = lesson_progress_completed_runs(source, space) if callable(globals().get("lesson_progress_completed_runs")) else (1 if progress.get("completed") else 0)
    progress["completed_runs"] = completed_runs
    progress["completedRuns"] = completed_runs
    progress["previously_completed"] = bool(completed_runs and not progress.get("completed"))
    progress["previouslyCompleted"] = progress["previously_completed"]
    return {
        "title": clean(source.get("title", "")) or space,
        "nodes": max(0, space_w_int(source.get("rootNodeCount", state.get("rootNodeCount", source.get("nodeCount", state.get("nodeCount", 0)))), 0)),
        "sentences": max(0, space_w_int(source.get("sentenceCount", state.get("sentenceCount", 0)), 0)),
        "normal_sentences": max(0, space_w_int(source.get("normalSentenceCount", state.get("normalSentenceCount", 0)), 0)),
        "train_sentences": max(0, space_w_int(source.get("trainSentenceCount", state.get("trainSentenceCount", 0)), 0)),
        "mine": completed_runs,
        "mine_last": progress.get("updatedAt", "") if progress.get("completed") else "",
        "completed_runs": completed_runs,
        "completedRuns": completed_runs,
        "progress": progress,
    }


# Added 2026-07-06: updates only the touched Lesson Vault row instead of invalidating all folder caches.
def patch_lesson_vault_cache_for_space_progress(record: dict, space: str = "") -> int:
    source = record if isinstance(record, dict) else {}
    paths = [
        clean_path_value(source.get("path", "")),
        clean_path_value(source.get("legacy_path", "")),
    ]
    return patch_server_data_list_cache_study(
        paths,
        space_progress_lesson_vault_study_patch(source, space),
        username=normalize_username(source.get("username", "")),
    )


# Added 2026-07-09: keep auto Space Task fresh per learner after lightweight progress saves.
def invalidate_space_task_cache_after_space_progress(username: str, record: dict | None = None, space: str = "", force: bool = False) -> None:
    invalidate_space_task = globals().get("invalidate_space_task_payload_cache")
    if not callable(invalidate_space_task):
        return
    should_invalidate = bool(force)
    if not should_invalidate and isinstance(record, dict):
        summary = space_progress_lesson_vault_study_patch(record, space)
        progress = summary.get("progress") if isinstance(summary.get("progress"), dict) else {}
        should_invalidate = bool(progress.get("completed"))
    if should_invalidate:
        invalidate_space_task(username)


def space_progress_completion_transition(existing: dict | None, incoming: dict | None, space: str = "") -> dict:
    old = existing if isinstance(existing, dict) else {}
    new = incoming if isinstance(incoming, dict) else {}
    canonical_summary = globals().get("server_database_progress_completion_summary")
    if callable(canonical_summary):
        old_summary = canonical_summary(old, space)
        new_summary = canonical_summary(new, space)
        old_current = bool(old_summary.get("current_run_complete"))
        new_current = bool(new_summary.get("current_run_complete"))
        old_runs = max(0, space_w_int(old_summary.get("completed_runs", 0), 0))
        new_runs = max(0, space_w_int(new_summary.get("completed_runs", 0), 0))
    else:
        old_current = space_progress_completion_marker(old, space)
        new_current = space_progress_completion_marker(new, space)
        old_runs = 1 if old_current else 0
        new_runs = 1 if new_current else 0
    old_run_id = space_progress_completion_run_id(old)
    new_run_id = space_progress_completion_run_id(new)
    return {
        "transitioned": bool(
            new_current
            and (
                not old_current
                or old_runs <= 0
                or new_runs > old_runs
                or (new_run_id and old_run_id and new_run_id != old_run_id)
            )
        ),
        "old_current_complete": old_current,
        "new_current_complete": new_current,
        "old_completed_runs": old_runs,
        "new_completed_runs": new_runs,
        "old_run_id": old_run_id,
        "new_run_id": new_run_id,
    }


def save_space_w_progress(username: str, progress_payload: dict) -> dict:
    username = normalize_username(username)
    source = progress_payload if isinstance(progress_payload, dict) else {}
    identity_info = space_progress_identity_for_source(username, source, operation="write")
    rel_path = clean_path_value(identity_info.get("path", ""))
    identity = clean(identity_info.get("identity", ""))
    key = clean(identity_info.get("key", "")) or space_w_progress_key(username, rel_path, identity)
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    state = dict(state)
    # 2026-07-23: folder-link checkpoints must carry the canonical ID into the nested lesson descriptor.
    lesson_source = state.get("lessonSource") if isinstance(state.get("lessonSource"), dict) else None
    if lesson_source is not None and identity.lower().startswith("ftg-lesson-"):
        lesson_source = dict(lesson_source)
        lesson_source["lesson_id"] = identity[:240]
        lesson_source["file_id"] = identity[:240]
        lesson_source["identity"] = identity[:240]
        state["lessonSource"] = lesson_source
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
        "title": clean(source.get("title") or state.get("title") or "Space_W")[:180],
        "nodeIndex": max(0, space_w_int(source.get("nodeIndex", state.get("index", 0)))),
        "nodeCount": max(0, space_w_int(source.get("nodeCount", state.get("nodeCount", 0)))),
        "savedAt": clean(source.get("savedAt") or state.get("savedAt") or now)[:80],
        "updatedAt": now,
        "state": state,
    }
    for id_key in ("runId", "run_id", "sessionId", "session_id", "completionRunId", "completion_run_id", "completedAt", "completed_at", "syncOperationId", "sync_operation_id"):
        value = clean(source.get(id_key) or state.get(id_key))
        if value:
            record[id_key] = value[:160]
    with space_progress_user_lock("Space_W", username):
        store = load_space_progress_store("Space_W", username)
        payload = store.get("payload") if isinstance(store.get("payload"), dict) else default_space_progress_payload()
        states = payload.setdefault("states", {})
        legacy_key = clean(identity_info.get("legacy_key", ""))
        existing, legacy_key = space_progress_existing_canonical_state(states, key, legacy_key, identity)
        operation_id = clean(record.get("syncOperationId") or record.get("sync_operation_id"))
        existing_operation_id = clean(existing.get("syncOperationId") or existing.get("sync_operation_id"))
        if operation_id and existing_operation_id == operation_id:
            return dict(existing)
        completion_transition = space_progress_completion_transition(existing, record, "Space_W")
        record = merge_space_progress_newest(existing, record, "Space_W")
        if existing and space_w_progress_semantic_identity(existing) == space_w_progress_semantic_identity(record):
            return dict(existing)
        wal_entry = {"op": "upsert", "key": key, "record": record, "completion_event": source.get("_completionEvent")}
        remember_space_progress_store_entry(
            "Space_W",
            username,
            key,
            record,
            legacy_key=legacy_key,
            wal_entry=wal_entry,
            postgres_authoritative=True,
        )
    if completion_transition.get("transitioned") and not isinstance(source.get("_completionEvent"), dict):
        record["_completionSync"] = {
            "path": rel_path,
            "lesson_id": identity[:240] if identity.lower().startswith("ftg-lesson-") else "",
            "name": clean(source.get("name") or source.get("title") or record.get("title")),
            "title": clean(record.get("title")),
            "nodes": max(0, space_w_int(record.get("nodeCount", 0), 0)),
            "completed_at": clean(record.get("completedAt") or record.get("completed_at") or record.get("updatedAt")),
            "completion_run_id": clean(
                record.get("completionRunId")
                or record.get("completion_run_id")
                or completion_transition.get("new_run_id")
            ),
            "source": "space_w_progress_transition",
            "reason": "space_w_progress_complete",
        }
    invalidate_progress_index = globals().get("invalidate_lesson_progress_index_cache")
    if callable(invalidate_progress_index):
        invalidate_progress_index(username)
    patch_lesson_vault_cache_for_space_progress(record, "Space_W")
    invalidate_space_task_cache_after_space_progress(username, record, "Space_W")
    return record


def clear_space_w_progress(username: str, progress_payload: dict) -> dict:
    username = normalize_username(username)
    source = progress_payload if isinstance(progress_payload, dict) else {}
    identity_info = space_progress_identity_for_source(username, source, operation="clear")
    key = clean(identity_info.get("key", "")) or space_w_progress_key(username, "", clean(identity_info.get("identity", "")))
    with space_progress_user_lock("Space_W", username):
        payload = clone_space_progress_payload(load_space_progress_store("Space_W", username).get("payload"))
        states = payload.setdefault("states", {})
        existing = states.get(key) if isinstance(states.get(key), dict) else {}
        if space_progress_clear_is_stale(existing, source):
            return {"key": key, "removed": False, "stale": True, "progress": existing}
        removed = states.pop(key, None)
        remember_space_progress_store(
            "Space_W",
            username,
            payload,
            force=True,
            wal_entry={"op": "remove", "key": key, "lesson_id": clean(identity_info.get("identity", ""))},
        )
    invalidate_space_task_cache_after_space_progress(username, None, "Space_W", force=True)
    return {"key": key, "removed": bool(removed)}


def read_speak_skip_file_locked() -> dict:
    if postgres_backend_enabled("SPACE_W_SPEAK_SKIP"):
        from FUTURE.postgres.repositories import space_w_speak_skip as pg_speak_skip
        return pg_speak_skip.load_payload()
    payload = server_database_read_document_json(SPEAK_SKIP_REQUESTS_FILE, {})
    if isinstance(payload, dict):
        rows = payload.get("requests") if isinstance(payload.get("requests"), dict) else {}
        return {
            "version": int(payload.get("version", 1) or 1),
            "updated_at": clean(payload.get("updated_at", "")),
            "requests": {clean(key): value for key, value in rows.items() if clean(key) and isinstance(value, dict)},
        }
    return {"version": 1, "requests": {}}


def write_speak_skip_file_locked(payload: dict) -> None:
    if postgres_backend_enabled("SPACE_W_SPEAK_SKIP"):
        from FUTURE.postgres.repositories import space_w_speak_skip as pg_speak_skip
        pg_speak_skip.save_payload(payload)
        return
    USER_ROOT.mkdir(parents=True, exist_ok=True)
    rows = payload.get("requests") if isinstance(payload.get("requests"), dict) else {}
    out = {
        "version": 1,
        "updated_at": utc_timestamp(),
        "requests": rows,
    }
    atomic_write_json(SPEAK_SKIP_REQUESTS_FILE, out, indent=2)


def speak_skip_key_parts(username: str, payload: dict) -> tuple[str, str, str, str, int, str]:
    username = normalize_username(username)
    source = payload if isinstance(payload, dict) else {}
    identity_info = space_progress_identity_for_source(username, source)
    rel_path = clean_path_value(identity_info.get("path", ""))
    identity = clean(identity_info.get("identity", ""))[:240]
    progress_key = clean(identity_info.get("key", "")) or space_w_progress_key(username, rel_path, identity)
    node_index = max(0, space_w_int(source.get("nodeIndex", source.get("node_index", 0)), 0))
    session_id = clean(source.get("sessionId") or source.get("session_id") or "")[:96]
    request_id = hashlib.sha256(f"{username.lower()}|{progress_key}|{node_index}|{session_id or 'legacy'}".encode("utf-8")).hexdigest()[:32]
    return request_id, progress_key, rel_path, identity, node_index, session_id


def public_speak_skip_request(row: dict | None) -> dict | None:
    if not isinstance(row, dict):
        return None
    node_index = max(0, space_w_int(row.get("nodeIndex", row.get("node_index", 0)), 0))
    out = dict(row)
    out["id"] = clean(out.get("id", ""))
    out["username"] = normalize_username(out.get("username", ""))
    out["status"] = clean(out.get("status", "pending")).lower() or "pending"
    out["nodeIndex"] = node_index
    out["node_index"] = node_index
    out["identity"] = clean(out.get("identity", ""))
    out["sessionId"] = clean(out.get("sessionId", out.get("session_id", "")))[:96]
    out["session_id"] = out["sessionId"]
    out["title"] = clean(out.get("title", ""))[:180]
    out["expected"] = clean(out.get("expected", ""))[:600]
    out["reason"] = clean(out.get("reason", ""))[:400]
    return out


def request_space_w_speak_skip(username: str, payload: dict) -> dict:
    username = normalize_username(username)
    request_id, progress_key, rel_path, identity, node_index, session_id = speak_skip_key_parts(username, payload)
    now = utc_timestamp()
    source = payload if isinstance(payload, dict) else {}
    if postgres_backend_enabled("SPACE_W_SPEAK_SKIP"):
        from FUTURE.postgres.repositories import space_w_speak_skip as pg_speak_skip
        existing = pg_speak_skip.load_request(request_id) or {}
        if clean(existing.get("status", "")).lower() == "accepted":
            return public_speak_skip_request(existing) or {}
        row = {
            **existing,
            "id": request_id,
            "username": username,
            "status": "pending",
            "progressKey": progress_key,
            "sessionId": session_id,
            "path": rel_path,
            "identity": identity,
            "title": clean(source.get("title", existing.get("title", "Space_W")))[:180],
            "nodeIndex": node_index,
            "nodeCount": max(0, space_w_int(source.get("nodeCount", existing.get("nodeCount", 0)), 0)),
            "expected": clean(source.get("expected", existing.get("expected", "")))[:600],
            "reason": clean(source.get("reason", existing.get("reason", "Learner reported a Speak scoring error.")))[:400],
            "review": bool(source.get("review", existing.get("review", False))),
            "createdAt": clean(existing.get("createdAt", "")) or now,
            "updatedAt": now,
            "respondedAt": "",
        }
        pg_speak_skip.save_request(row)
        return public_speak_skip_request(row) or {}
    with SPEAK_SKIP_LOCK:
        store = read_speak_skip_file_locked()
        rows = store.setdefault("requests", {})
        existing = rows.get(request_id) if isinstance(rows.get(request_id), dict) else {}
        status = clean(existing.get("status", "")).lower()
        if status == "accepted":
            return public_speak_skip_request(existing) or {}
        row = {
            **existing,
            "id": request_id,
            "username": username,
            "status": "pending",
            "progressKey": progress_key,
            "sessionId": session_id,
            "path": rel_path,
            "identity": identity,
            "title": clean(source.get("title", existing.get("title", "Space_W")))[:180],
            "nodeIndex": node_index,
            "nodeCount": max(0, space_w_int(source.get("nodeCount", existing.get("nodeCount", 0)), 0)),
            "expected": clean(source.get("expected", existing.get("expected", "")))[:600],
            "reason": clean(source.get("reason", existing.get("reason", "Learner reported a Speak scoring error.")))[:400],
            "review": bool(source.get("review", existing.get("review", False))),
            "createdAt": clean(existing.get("createdAt", "")) or now,
            "updatedAt": now,
            "respondedAt": "",
        }
        rows[request_id] = row
        if len(rows) > 600:
            ordered = sorted(rows.items(), key=lambda item: timestamp_order_key(item[1].get("updatedAt") or item[1].get("createdAt")))
            store["requests"] = dict(ordered[-600:])
        write_speak_skip_file_locked(store)
        return public_speak_skip_request(row) or {}


def get_space_w_speak_skip(username: str, payload: dict) -> dict | None:
    username = normalize_username(username)
    request_id, progress_key, _rel_path, _identity, _node_index, session_id = speak_skip_key_parts(username, payload)
    if postgres_backend_enabled("SPACE_W_SPEAK_SKIP"):
        from FUTURE.postgres.repositories import space_w_speak_skip as pg_speak_skip
        accepted = pg_speak_skip.latest_accepted(username, progress_key, session_id)
        if accepted:
            return public_speak_skip_request(accepted)
        exact = pg_speak_skip.load_request(request_id)
        public_exact = public_speak_skip_request(exact)
        if public_exact and clean(public_exact.get("status", "")).lower() in {"pending", "accepted"}:
            return public_exact
        return public_exact
    with SPEAK_SKIP_LOCK:
        store = read_speak_skip_file_locked()
        rows = store.get("requests", {})
        exact = rows.get(request_id) if isinstance(rows, dict) else None
        if isinstance(rows, dict):
            accepted = [
                row for row in rows.values()
                if isinstance(row, dict)
                and normalize_username(row.get("username", "")) == username
                and clean(row.get("progressKey", row.get("progress_key", ""))) == progress_key
                and clean(row.get("sessionId", row.get("session_id", ""))) == session_id
                and clean(row.get("status", "")).lower() == "accepted"
            ]
            accepted.sort(key=lambda item: timestamp_order_key(item.get("updatedAt") or item.get("createdAt")), reverse=True)
            if accepted:
                return public_speak_skip_request(accepted[0])
        public_exact = public_speak_skip_request(exact)
        if public_exact and clean(public_exact.get("status", "")).lower() in {"pending", "accepted"}:
            return public_exact
        return public_exact


def latest_speak_skip_by_user() -> dict[str, dict]:
    if postgres_backend_enabled("SPACE_W_SPEAK_SKIP"):
        from FUTURE.postgres.repositories import space_w_speak_skip as pg_speak_skip
        result = {}
        for username, row in pg_speak_skip.latest_by_user().items():
            public = public_speak_skip_request(row)
            if public:
                result[username] = public
        return result
    now_ts = time.time()
    with SPEAK_SKIP_LOCK:
        store = read_speak_skip_file_locked()
        rows = [public_speak_skip_request(row) for row in store.get("requests", {}).values()]
    result: dict[str, dict] = {}
    for row in rows:
        if not row:
            continue
        username = normalize_username(row.get("username", ""))
        if not username:
            continue
        timestamp_text = clean(row.get("updatedAt") or row.get("createdAt"))
        try:
            timestamp_value = time.mktime(time.strptime(timestamp_text[:19], "%Y-%m-%dT%H:%M:%S"))
        except Exception:
            timestamp_value = now_ts
        current = result.get(username)
        current_status = clean(current.get("status", "")) if isinstance(current, dict) else ""
        row_status = clean(row.get("status", ""))
        choose = False
        if not current:
            choose = True
        elif current_status == "pending" and row_status != "pending":
            choose = False
        elif row_status == "pending" and current_status != "pending":
            choose = True
        else:
            choose = timestamp_value >= float(current.get("_sort", 0) or 0)
        if choose:
            row["_sort"] = timestamp_value
            result[username] = row
    for row in result.values():
        row.pop("_sort", None)
    return result


def list_space_w_speak_skip_requests(status: str = "pending", username: str = "") -> list[dict]:
    status_filter = clean(status).lower()
    username_filter = normalize_username(username) if clean(username) else ""
    if postgres_backend_enabled("SPACE_W_SPEAK_SKIP"):
        from FUTURE.postgres.repositories import space_w_speak_skip as pg_speak_skip
        return [row for row in (public_speak_skip_request(item) for item in pg_speak_skip.list_requests(status_filter, username_filter)) if row]
    with SPEAK_SKIP_LOCK:
        store = read_speak_skip_file_locked()
        rows = [public_speak_skip_request(row) for row in store.get("requests", {}).values()]
    out: list[dict] = []
    for row in rows:
        if not row:
            continue
        row_status = clean(row.get("status", "pending")).lower() or "pending"
        row_user = normalize_username(row.get("username", ""))
        if username_filter and row_user != username_filter:
            continue
        if status_filter and status_filter not in {"all", "*"} and row_status != status_filter:
            continue
        out.append(row)
    out.sort(key=lambda item: timestamp_order_key(item.get("updatedAt") or item.get("createdAt")), reverse=True)
    return out


def respond_space_w_speak_skip(username: str, request_id: str = "", action: str = "accept") -> dict:
    username = normalize_username(username)
    request_id = clean(request_id)
    action = clean(action).lower() or "accept"
    next_status = "accepted" if action in {"accept", "approve", "accepted", "approved"} else "rejected"
    if postgres_backend_enabled("SPACE_W_SPEAK_SKIP"):
        from FUTURE.postgres.repositories import space_w_speak_skip as pg_speak_skip
        return public_speak_skip_request(pg_speak_skip.respond_request(username, request_id, action)) or {}
    with SPEAK_SKIP_LOCK:
        store = read_speak_skip_file_locked()
        rows = store.setdefault("requests", {})
        row = rows.get(request_id) if request_id else None
        if not isinstance(row, dict):
            candidates = [
                item for item in rows.values()
                if isinstance(item, dict)
                and normalize_username(item.get("username", "")) == username
                and clean(item.get("status", "pending")).lower() == "pending"
            ]
            candidates.sort(key=lambda item: timestamp_order_key(item.get("updatedAt") or item.get("createdAt")), reverse=True)
            row = candidates[0] if candidates else None
        if not isinstance(row, dict) or normalize_username(row.get("username", "")) != username:
            raise RuntimeError("No matching Speak skip request.")
        now = utc_timestamp()
        row_progress_key = clean(row.get("progressKey", row.get("progress_key", "")))
        row_session_id = clean(row.get("sessionId", row.get("session_id", "")))
        if next_status == "accepted" and row_progress_key:
            for item in rows.values():
                if not isinstance(item, dict):
                    continue
                if normalize_username(item.get("username", "")) != username:
                    continue
                if clean(item.get("progressKey", item.get("progress_key", ""))) != row_progress_key:
                    continue
                if clean(item.get("sessionId", item.get("session_id", ""))) != row_session_id:
                    continue
                if clean(item.get("status", "pending")).lower() not in {"pending", "accepted"}:
                    continue
                item["status"] = next_status
                item["updatedAt"] = now
                item["respondedAt"] = now
        else:
            row["status"] = next_status
            row["updatedAt"] = now
            row["respondedAt"] = row["updatedAt"]
            rows[clean(row.get("id", ""))] = row
        write_speak_skip_file_locked(store)
        return public_speak_skip_request(row) or {}


def respond_space_w_speak_skip_many(username: str = "", action: str = "accept") -> list[dict]:
    username = normalize_username(username) if clean(username) else ""
    action = clean(action).lower() or "accept"
    next_status = "accepted" if action in {"accept", "approve", "accepted", "approved"} else "rejected"
    if postgres_backend_enabled("SPACE_W_SPEAK_SKIP"):
        from FUTURE.postgres.repositories import space_w_speak_skip as pg_speak_skip
        changed = [row for row in (public_speak_skip_request(item) for item in pg_speak_skip.respond_many(username, action)) if row]
        changed.sort(key=lambda item: timestamp_order_key(item.get("updatedAt") or item.get("createdAt")), reverse=True)
        return changed
    changed: list[dict] = []
    with SPEAK_SKIP_LOCK:
        store = read_speak_skip_file_locked()
        rows = store.setdefault("requests", {})
        now = utc_timestamp()
        for row in rows.values():
            if not isinstance(row, dict):
                continue
            if clean(row.get("status", "pending")).lower() != "pending":
                continue
            if username and normalize_username(row.get("username", "")) != username:
                continue
            row["status"] = next_status
            row["updatedAt"] = now
            row["respondedAt"] = now
            public = public_speak_skip_request(row)
            if public:
                changed.append(public)
        if changed:
            write_speak_skip_file_locked(store)
    changed.sort(key=lambda item: timestamp_order_key(item.get("updatedAt") or item.get("createdAt")), reverse=True)
    return changed
