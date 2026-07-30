# Loaded by FUTURE.server_parts.server_data_pdf_qmdict.04_server_data_manifest_listing into the shared Future server runtime namespace.
# This is a deeper transitional split; do not import directly yet.

LESSON_COMPLETION_SHARD_COUNT = 256
LESSON_COMPLETION_SHARD_LOCKS = [threading.RLock() for _ in range(LESSON_COMPLETION_SHARD_COUNT)]


# Added 2026-07-22: independent SQLite-backed completions must not queue behind one global filesystem lock.
def lesson_completion_shard_lock(username: str, lesson_id: str) -> threading.RLock:
    key = f"{normalize_username(username).lower()}|{clean(lesson_id).lower()}"
    return LESSON_COMPLETION_SHARD_LOCKS[int(hashlib.sha1(key.encode("utf-8")).hexdigest()[:8], 16) % LESSON_COMPLETION_SHARD_COUNT]


# Added 2026-07-24: folder-link display paths authorize normally, then resolve identity from their effective lesson file.
def lesson_completion_source_for_request(relative_path: str, username: str, requested_lesson_id: str = "") -> dict:
    raw_path = clean_path_value(relative_path)
    if not raw_path:
        return {"raw_path": "", "target": None, "effective_target": None, "effective_path": "", "lesson_id": "", "admin_run": False}
    raw_owner = normalize_username(raw_path.split("/", 1)[0])
    own_user_folder_run = bool(raw_owner and raw_owner.lower() == username.lower())
    # Added 2026-07-29: common and own-folder completions never need admin
    # authorization. Avoid serializing ordinary learners behind ADMIN_LOCK.
    normal_scope = raw_owner.lower() == "common" or own_user_folder_run
    admin_run = bool(not normal_scope and is_admin_user(username))
    contract = resolve_lesson_identity_contract(
        raw_path,
        username,
        admin=admin_run,
        requested_lesson_id=requested_lesson_id,
        task_owner=username,
        strict=True,
        require_file=True,
    )
    effective_target = contract.get("effective_target")
    if effective_target is None or not effective_target.is_file() or not is_lesson_file(effective_target):
        raise RuntimeError("Chi duoc danh dau file Space_W/Space_V/Space_Q/Space_P/TXT trong C:\\server data.")
    return {
        **contract,
        "raw_path": raw_path,
        "admin_run": admin_run,
    }

def completion_progress_space_name(space_type: str = "") -> str:
    safe_type = normalize_space_leaderboard_type(space_type)
    return {
        "space_w": "Space_W",
        "space_q": "Space_Q",
        "space_p": "Space_P",
        "space_s": "Space_S",
        "space_l": "Space_L",
    }.get(safe_type, "")


# Added 2026-07-29: reuse the warm structural manifest so node-space completion
# does not decode a large lesson merely to recover its authoritative point count.
def lesson_completion_manifest_structure(relative_path: str, lesson_id: str, space_type: str, fallback_title: str = "", manifest_entry: dict | None = None) -> dict:
    if truthy(os.environ.get("FUTURE_TEST_NODE_COMPLETION_FORCE_FILE_DECODE"), False):
        return {}
    safe_type = normalize_space_leaderboard_type(space_type)
    if safe_type not in SPACE_LEADERBOARD_NODE_TYPES or safe_type == "space_v":
        return {}
    entry = manifest_entry if isinstance(manifest_entry, dict) else None
    if not isinstance(entry, dict):
        entry_reader = globals().get("server_data_manifest_file_entry")
        if not callable(entry_reader):
            return {}
        entry = entry_reader(relative_path)
    if not isinstance(entry, dict):
        return {}
    entry_lesson_id = clean(entry.get("lesson_id", ""))[:240]
    canonical_lesson_id = clean(lesson_id)[:240]
    if entry_lesson_id and canonical_lesson_id and entry_lesson_id.lower() != canonical_lesson_id.lower():
        return {}
    nodes = max(0, space_w_int(entry.get("nodes", 0), 0))
    points = max(
        0,
        space_w_int(entry.get("total_nodes", 0), 0),
        space_w_int(entry.get("questions", 0), 0),
    ) if safe_type == "space_q" else nodes
    if points <= 0 or nodes <= 0:
        return {}
    return {
        "points": points,
        "nodes": nodes,
        "title": clean(fallback_title) or clean(entry.get("name", "")),
        "entry": entry,
    }


# Added 2026-07-06: records node-space completion in the small path progress store instead of rewriting large lesson JSON.
def save_node_space_completion_progress(username: str, relative_path: str, title: str, space_type: str, points: int, node_count: int, completed_at: str, lesson_id: str = "", completion_run_id: str = "", completion_event: dict | None = None) -> dict:
    space_name = completion_progress_space_name(space_type)
    if not space_name:
        return {}
    total = max(1, int(points or node_count or 1))
    canonical_id = clean(lesson_id)[:240]
    identity_key = f"id:{canonical_id.lower()}" if canonical_id.lower().startswith("ftg-lesson-") else f"path:{clean_path_value(relative_path).lower()}"
    completion_run_id = clean(completion_run_id)[:160] or hashlib.sha256(
        f"{normalize_username(username).lower()}|{identity_key}|{space_name}|{clean(completed_at)}".encode("utf-8")
    ).hexdigest()[:32]
    state = {
        "title": clean(title) or space_name,
        "nodeCount": max(1, int(node_count or total)),
        "lessonCompletionSent": True,
        "complete": True,
        "completedAt": completed_at,
        "completionRunId": completion_run_id,
        "savedAt": completed_at,
    }
    payload = {
        "path": clean_path_value(relative_path),
        "identity": canonical_id or clean_path_value(relative_path),
        "lesson_id": canonical_id,
        "title": clean(title) or space_name,
        "nodeIndex": max(1, int(node_count or total)),
        "nodeCount": total,
        "savedAt": completed_at,
        "completedAt": completed_at,
        "completionRunId": completion_run_id,
        "complete": True,
        "forceFlush": True,
        "state": state,
    }
    if isinstance(completion_event, dict):
        payload["_completionEvent"] = {
            **completion_event,
            "completion_run_id": completion_run_id,
            "status": "core_committed",
        }
    if space_name == "Space_Q":
        state.update({"questionTotal": total, "questionDone": total, "totalQuestions": total, "completedQuestions": total})
        return save_space_q_progress(username, payload)
    if space_name in {"Space_P", "Space_S", "Space_L"}:
        state.update({"space": space_name, "totalSegments": total, "completedSegments": total})
        payload["space"] = space_name
        return save_space_p_progress(username, payload)
    return save_space_w_progress(username, payload)


def record_lesson_completion(relative_path: str, username: str, info: dict | None = None) -> dict:
    _completion_started = time.perf_counter()
    _completion_thread_cpu_started = time.thread_time_ns()
    _completion_process_cpu_started = time.process_time_ns()
    _phase_started = _completion_started
    _timing_ms: dict[str, int] = {}
    def _mark_phase(name: str) -> None:
        nonlocal _phase_started
        now = time.perf_counter()
        _timing_ms[name] = int((now - _phase_started) * 1000)
        _phase_started = now

    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    payload_info = info if isinstance(info, dict) else {}
    completion_trace_id = clean(payload_info.get("completion_trace_id") or "")[:160]
    pg_trace_begin = globals().get("postgres_trace_begin")
    pg_trace_stage = globals().get("postgres_trace_set_stage")
    if completion_trace_id and callable(pg_trace_begin):
        pg_trace_begin(completion_trace_id)
    if callable(pg_trace_stage):
        pg_trace_stage("authentication_user_loading")
    raw_path = clean_path_value(relative_path)
    requested_lesson_id = clean(payload_info.get("lesson_id") or payload_info.get("lessonId") or payload_info.get("file_id") or payload_info.get("fileId"))[:240]
    now = utc_timestamp()
    client_completed_at = clean(payload_info.get("completed_at", ""))
    requested_completion_run_id = clean(
        payload_info.get("completion_run_id") or payload_info.get("completionRunId")
    )[:160]
    completion_event_at = client_completed_at or now
    _source_resolution_started = time.perf_counter()
    source_info = lesson_completion_source_for_request(raw_path, username, requested_lesson_id)
    _timing_ms["source_resolution"] = int((time.perf_counter() - _source_resolution_started) * 1000)
    for _name, _value in (source_info.get("_identity_timing_ms") or {}).items():
        _timing_ms[f"identity_{_name}"] = max(0, int(_value or 0))
    target = source_info.get("target")
    effective_target = source_info.get("effective_target")
    effective_relative_path = clean_path_value(source_info.get("effective_path", ""))
    canonical_lesson_id = clean(source_info.get("lesson_id", ""))[:240]
    _identity_log_started = time.perf_counter()
    record_canonical_identity_resolution("completion.write", {"lesson_id": canonical_lesson_id, "path": raw_path})
    _timing_ms["identity_resolution_log"] = int((time.perf_counter() - _identity_log_started) * 1000)
    admin_run = bool(source_info.get("admin_run"))
    record = {
        "at": now,
        "event": "lesson_complete",
        "user": username,
        "path": raw_path,
        "lesson_id": canonical_lesson_id,
        "file_id": canonical_lesson_id,
        "canonical_file_id": canonical_lesson_id,
        "requested_path": raw_path,
        "display_path": clean_path_value(source_info.get("display_path", "")) or raw_path,
        "link_path": clean_path_value(source_info.get("link_path", "")),
        "source_path": clean_path_value(source_info.get("source_path", "")) or effective_relative_path,
        "effective_path": effective_relative_path,
        "task_owner": normalize_username(payload_info.get("task_owner") or source_info.get("task_owner") or username),
        "space_type": clean(source_info.get("space_type", "")),
        "file": clean(payload_info.get("name", "")),
        "title": clean(payload_info.get("title", "")),
        "nodes": int(payload_info.get("nodes", 0) or 0),
        "client_completed_at": client_completed_at,
        "completion_run_id": requested_completion_run_id,
        "source": clean(payload_info.get("source", "")) or ("server" if raw_path else "local"),
    }
    event_identity = f"id:{canonical_lesson_id.lower()}" if canonical_lesson_id else f"path:{raw_path.lower()}"
    event_version = f"run:{requested_completion_run_id}" if requested_completion_run_id else (
        f"at:{normalize_timestamp_text(completion_event_at, fallback_now=True)}"
    )
    recovery_event_key = clean(payload_info.get("event_key", ""))[:160] if truthy(payload_info.get("recovery_after_restart"), False) else ""
    completion_event_key = recovery_event_key or hashlib.sha256(
        f"{username.lower()}|{event_identity}|{event_version}".encode("utf-8")
    ).hexdigest()
    record["event_key"] = completion_event_key
    result = {"logged": True, "updated_file": False, "path": raw_path, "lesson_id": canonical_lesson_id, "event_key": completion_event_key, "study": {}}
    path_space_type = space_leaderboard_type_for_path(effective_relative_path, None, record.get("source", "")) if effective_relative_path else ""
    # Added 2026-07-24: expose one canonical completion/Top contract to every
    # frontend Space, including duplicate retries that return before board work.
    result["leaderboard_type"] = path_space_type
    fast_node_candidate = bool(path_space_type in SPACE_LEADERBOARD_NODE_TYPES and path_space_type != "space_v" and not admin_run and canonical_lesson_id)
    # Added 2026-07-25: Space_V vocabulary completion still touches the lesson
    # study block, so shard by lesson instead of using the global Server Data lock.
    space_v_lesson_shard_candidate = bool(path_space_type == "space_v" and not admin_run and canonical_lesson_id)
    intent_with_progress = bool(fast_node_candidate and completion_progress_space_name(path_space_type))
    if fast_node_candidate:
        # Updated 2026-07-29: a learner may finish different tabs together;
        # serialize only that learner's summary delta while other users stay parallel.
        completion_lock = learning_summary_user_lock(username)
        result["lock_scope"] = "user-summary-shard"
    elif space_v_lesson_shard_candidate:
        completion_lock = lesson_completion_shard_lock("", canonical_lesson_id)
        result["lock_scope"] = "lesson-shard-space-v"
    else:
        completion_lock = SERVER_DATA_LOCK
        result["lock_scope"] = "server-data-global"
    _mark_phase("pre_lock")
    _timing_ms["pre_lock_other"] = max(
        0,
        _timing_ms.get("pre_lock", 0)
        - _timing_ms.get("source_resolution", 0)
        - _timing_ms.get("identity_resolution_log", 0),
    )
    _lock_wait_started = time.perf_counter()
    with completion_lock:
        _lock_acquired = time.perf_counter()
        _timing_ms["lock_wait"] = int((_lock_acquired - _lock_wait_started) * 1000)
        _phase_started = _lock_acquired
        completion_transaction_activate = globals().get("postgres_request_transaction_activate")
        if intent_with_progress:
            # Updated 2026-07-30: structural metadata is CPU-only. Delay the
            # request transaction until it is ready so pool connections are not
            # held while a worker is descheduled before the first SQL statement.
            record["intent_with_progress"] = True
        else:
            if callable(pg_trace_stage):
                pg_trace_stage("idempotency_check")
            begin_completion = globals().get("server_database_begin_learning_completion")
            if callable(begin_completion):
                begin_result = begin_completion(record)
                if isinstance(begin_result, dict) and begin_result.get("complete"):
                    _timing_ms["lock_hold"] = int((time.perf_counter() - _lock_acquired) * 1000)
                    _timing_ms["total"] = int((time.perf_counter() - _completion_started) * 1000)
                    return {
                        **result,
                        "deduplicated": True,
                        "duplicate": True,
                        "recorded": False,
                        "completion_confirmed": True,
                        "timing_ms": dict(_timing_ms),
                    }
        if not intent_with_progress and callable(completion_transaction_activate):
            completion_transaction_activate()
        if raw_path:
            if callable(pg_trace_stage):
                pg_trace_stage("lesson_progress_finalize")
            client_title = clean(record.get("title", "")) or effective_target.stem
            manifest_structure = lesson_completion_manifest_structure(
                effective_relative_path,
                canonical_lesson_id,
                path_space_type,
                client_title,
                source_info.get("_manifest_entry"),
            ) if fast_node_candidate else {}
            force_legacy_decode = truthy(os.environ.get("FUTURE_TEST_NODE_COMPLETION_FORCE_FILE_DECODE"), False)
            force_strict_file_decode = truthy(os.environ.get("FUTURE_TEST_NODE_COMPLETION_STRICT_FILE_DECODE"), False)
            if manifest_structure:
                file_payload = {"k": "ftg", "title": manifest_structure["title"]}
                structure_path = None
                result["structural_source"] = "manifest"
            elif force_legacy_decode and not force_strict_file_decode and path_space_type == "space_w" and int(record.get("nodes", 0) or 0) > 0:
                file_payload = {"k": "ftg", "title": client_title, "n": [{} for _ in range(int(record.get("nodes", 0) or 0))]}
                structure_path = None
                result["structural_source"] = "legacy-synthetic"
            else:
                file_payload, structure_path = load_future_lesson_document(effective_target)
                result["structural_source"] = "lesson-file"
            _mark_phase("load_lesson")
            space_leaderboard_type = space_leaderboard_type_for_path(effective_relative_path, file_payload, record.get("source", ""))
            fast_node_space_completion = bool(space_leaderboard_type in SPACE_LEADERBOARD_NODE_TYPES)
            structural_node_count = max(0, space_w_int(manifest_structure.get("nodes", 0), 0)) or lesson_payload_node_count(file_payload)
            space_leaderboard_points = max(0, space_w_int(manifest_structure.get("points", 0), 0)) or space_leaderboard_points_from_payload(
                space_leaderboard_type, file_payload, record.get("nodes", 0)
            )
            resolved_lesson_title = clean(manifest_structure.get("title", "")) or lesson_payload_title(file_payload, record.get("title", ""))
            study = normalize_study_block(file_payload)
            bucket_name = "admins" if admin_run else "users"
            users = study.setdefault(bucket_name, {})
            user_study = users.get(username) if isinstance(users.get(username), dict) else {}
            if intent_with_progress:
                if callable(pg_trace_stage):
                    pg_trace_stage("idempotency_check")
                # Updated 2026-07-30: persist the recovery intent in its own
                # committed transaction before opening the atomic core transaction.
                begin_completion = globals().get("server_database_begin_learning_completion")
                begin_result = begin_completion(record) if callable(begin_completion) else {}
                if isinstance(begin_result, dict) and begin_result.get("complete"):
                    _timing_ms["lock_hold"] = int((time.perf_counter() - _lock_acquired) * 1000)
                    _timing_ms["total"] = int((time.perf_counter() - _completion_started) * 1000)
                    return {
                        **result,
                        "deduplicated": True,
                        "duplicate": True,
                        "recorded": False,
                        "completion_confirmed": True,
                        "timing_ms": dict(_timing_ms),
                    }
                if callable(completion_transaction_activate):
                    completion_transaction_activate()
            previous_user_count = int(user_study.get("count", 0) or 0)
            completion_progress_record = {}
            precomputed_learning_stats = {}
            if fast_node_space_completion and not admin_run:
                progress_before = lesson_progress_summary(
                    username,
                    clean_path_value(raw_path) or effective_relative_path,
                    effective_target.suffix,
                    space_leaderboard_points or structural_node_count,
                )
                if isinstance(progress_before, dict) and progress_before.get("completed"):
                    previous_user_count = max(previous_user_count, 1)
                if fast_node_candidate:
                    precomputed_learning_stats = update_lesson_user_learning_summary_after_completion(
                        username,
                        effective_target,
                        first_user_completion=previous_user_count <= 0,
                        vocabulary_result={},
                        completed_at=now,
                        persist=False,
                    )
                    record["learning_summary_payload"] = {"version": 1, **precomputed_learning_stats, "username": username}
                user_study = {
                    **user_study,
                    "count": max(1, int(user_study.get("count", 0) or 0) + 1),
                    "last": completion_event_at,
                }
                completion_progress_record = save_node_space_completion_progress(
                    username,
                    clean_path_value(raw_path) or effective_relative_path,
                    resolved_lesson_title,
                    space_leaderboard_type,
                    space_leaderboard_points,
                    structural_node_count or record.get("nodes", 0),
                    completion_event_at,
                    canonical_lesson_id,
                    requested_completion_run_id,
                    completion_event=record,
                )
                record["database_event_committed"] = True
                # Added 2026-07-22: deterministic codexload-only crash window for restart recovery regression.
                recovery_delay_ms = max(0, min(5000, space_w_int(os.environ.get("FUTURE_TEST_COMPLETION_AFTER_PROGRESS_DELAY_MS", 0), 0)))
                if recovery_delay_ms and username.lower().startswith("codexload"):
                    time.sleep(recovery_delay_ms / 1000.0)
                if completion_progress_record.get("completionRunId") or completion_progress_record.get("completion_run_id"):
                    record["completion_run_id"] = clean(completion_progress_record.get("completionRunId") or completion_progress_record.get("completion_run_id"))
            else:
                previous_completion_epoch = timestamp_to_epoch(user_study.get("last", ""))
                current_completion_epoch = timestamp_to_epoch(completion_event_at)
                duplicate_completion = bool(
                    previous_completion_epoch is not None
                    and current_completion_epoch is not None
                    and abs(previous_completion_epoch - current_completion_epoch) < 0.001
                )
                if not duplicate_completion:
                    user_study["count"] = int(user_study.get("count", 0) or 0) + 1
                user_study["last"] = completion_event_at
                dates = user_study.get("dates") if isinstance(user_study.get("dates"), list) else []
                day = completion_event_at[:10]
                if day not in dates:
                    dates.append(day)
                user_study["dates"] = dates[-60:]
                users[username] = user_study
                total_key = "admin_total" if admin_run else "total"
                if not duplicate_completion:
                    study[total_key] = int(study.get(total_key, 0) or 0) + 1
                study["last"] = completion_event_at
                history = study.get("history") if isinstance(study.get("history"), list) else []
                if not duplicate_completion:
                    history.append({"u": username, "at": completion_event_at, "count": user_study["count"], "role": "admin" if admin_run else "user"})
                study["history"] = history[-200:]
                set_study_block(file_payload, study)
                # Added 2026-07-29: learner Space_V state belongs to the durable
                # progress/event stores; rewriting the shared lesson file wakes
                # the native manifest watcher and rebuilds unrelated caches.
                if not (space_leaderboard_type == "space_v" and not admin_run):
                    write_future_lesson_document(effective_target, file_payload, structure_path, refresh_manifest=False)
                else:
                    result["updated_file"] = False
            _mark_phase("write_study")
            mission_vocab_run = False
            if not admin_run:
                try:
                    target.resolve().relative_to((server_data_user_folder_path(username) / VOCAB_MISSION_PENDING_DIR).resolve())
                    mission_vocab_run = True
                except Exception:
                    mission_vocab_run = False
            if fast_node_space_completion and completion_progress_record:
                study_summary = space_progress_lesson_vault_study_patch(
                    completion_progress_record,
                    completion_progress_space_name(space_leaderboard_type),
                )
            elif space_leaderboard_type == "space_v" and not admin_run:
                progress_summary = lesson_progress_summary(
                    username,
                    clean_path_value(raw_path) or effective_relative_path,
                    effective_target.suffix,
                    lesson_payload_node_count(file_payload),
                )
                study_summary = {
                    "total": int(study.get("total", 0) or 0),
                    "users": len(users),
                    "mine": int(user_study.get("count", 0) or 0),
                    "mine_last": clean(user_study.get("last", "")),
                    "completed_runs": int(user_study.get("count", 0) or 0),
                    "completedRuns": int(user_study.get("count", 0) or 0),
                    "title": lesson_payload_title(file_payload, record.get("title", "")),
                    "nodes": lesson_payload_node_count(file_payload),
                    "progress": progress_summary if isinstance(progress_summary, dict) else {},
                }
            else:
                study_summary = summarize_lesson_study(
                    effective_target,
                    username,
                    include_admin=bool(admin_run),
                    path_is_effective=True,
                    progress_relative_path=clean_path_value(raw_path) or effective_relative_path,
                    progress_relative_paths=[clean_path_value(raw_path), effective_relative_path],
                    strict_progress_paths=bool(clean_path_value(raw_path) and clean_path_value(raw_path).lower() != effective_relative_path.lower()),
                    # Updated 2026-07-06: completion just wrote study, so skip wide learning-log merge on the hot path.
                    include_log=False,
                )
            _mark_phase("study_summary")
            # Added 2026-07-06: node-space completions update hot RAM/registry incrementally and skip legacy sync work.
            # Added 2026-07-06: Space_V completion must update Top from the just-learned words without loading full QmDict maps.
            fast_space_v_completion = bool(space_leaderboard_type == "space_v")
            if callable(pg_trace_stage):
                pg_trace_stage("vocabulary_delta")
            vocabulary_result = {} if fast_node_space_completion else record_user_vocabulary_words(
                username,
                file_payload,
                effective_relative_path,
                sync_main=not (mission_vocab_run or fast_space_v_completion),
                verify_registry=not (mission_vocab_run or fast_space_v_completion),
                enrich_qmdict=not (mission_vocab_run or fast_space_v_completion),
                update_learning_summary=not fast_space_v_completion,
                completion_event={**record, "status": "core_committed"},
            )
            if vocabulary_result.get("database_event_committed"):
                record["database_event_committed"] = True
            _mark_phase("vocab_registry")
            archive_result = archive_completed_mission_vocab_file(username, target) if (not admin_run and not read_server_data_link_payload(target) and vocabulary_result.get("learned_words")) else {}
            _mark_phase("archive_vocab")
            final_relative_path = archive_result.get("archived_path") or clean_path_value(raw_path)
            result.update({
                "updated_file": not (space_leaderboard_type == "space_v" and not admin_run),
                "path": final_relative_path,
                "study": study_summary,
            })
            if not admin_run:
                if callable(pg_trace_stage):
                    pg_trace_stage("space_task_update")
                task_completed = bool(mark_lesson_task_completed(username, raw_path, "", canonical_lesson_id))
                linked_task_path = clean_path_value(payload_info.get("linked_path", ""))
                if not canonical_lesson_id and linked_task_path and linked_task_path.lower() != raw_path.lower():
                    task_completed = bool(mark_lesson_task_completed(username, linked_task_path, "")) or task_completed
                if not canonical_lesson_id and effective_relative_path and effective_relative_path.lower() not in {raw_path.lower(), linked_task_path.lower()}:
                    task_completed = bool(mark_lesson_task_completed(username, effective_relative_path, "")) or task_completed
                result["task_completed"] = task_completed
                invalidate_space_task = globals().get("invalidate_space_task_payload_cache")
                if callable(invalidate_space_task):
                    # Added 2026-07-09: completion should drop only this learner's auto Space Task cache.
                    invalidate_space_task(username)
                result["learning_stats"] = precomputed_learning_stats or update_lesson_user_learning_summary_after_completion(
                    username,
                    effective_target,
                    first_user_completion=previous_user_count <= 0,
                    vocabulary_result=vocabulary_result,
                    completed_at=now,
                    persist=False,
                )
                _mark_phase("learning_stats")
            elif vocabulary_result:
                try:
                    result["learning_stats"] = reconcile_user_vocabulary_total(username, sync_main=False).get("learning_stats", {})
                except Exception:
                    pass
                _mark_phase("learning_stats")
            if vocabulary_result.get("learned_words"):
                result["vocabulary"] = {
                    **vocabulary_result,
                    **archive_result,
                }
            record.update({
                "path": final_relative_path,
                "effective_path": effective_relative_path,
                "display_path": clean_path_value(source_info.get("display_path", "")) or raw_path,
                "link_path": clean_path_value(source_info.get("link_path", "")),
                "task_owner": normalize_username(payload_info.get("task_owner") or source_info.get("task_owner") or username),
                "space_type": space_leaderboard_type,
                "file": target.name,
                "title": resolved_lesson_title,
                "nodes": structural_node_count or record.get("nodes", 0),
                "user_count": int(study_summary.get("mine", user_study.get("count", 0)) or 0) if fast_node_space_completion else user_study["count"],
                "total": int(study_summary.get("total", study.get("total", 0)) or 0) if fast_node_space_completion else study.get("total", 0),
                "admin_count": user_study["count"] if admin_run else 0,
                "admin_total": study.get("admin_total", 0),
                "role": "admin" if admin_run else "user",
            })
            if space_leaderboard_type in SPACE_LEADERBOARD_NODE_TYPES and space_leaderboard_points > 0:
                if callable(pg_trace_stage):
                    pg_trace_stage("leaderboard_update")
                result["space_leaderboard"] = record_space_leaderboard_completion(
                    username,
                    final_relative_path,
                    space_leaderboard_type,
                    space_leaderboard_points,
                    record.get("title", ""),
                    now,
                    canonical_lesson_id,
                )
                record["space_leaderboard_type"] = space_leaderboard_type
                record["space_leaderboard_points"] = space_leaderboard_points
                result["leaderboard_type"] = space_leaderboard_type
                result["recorded"] = bool(result["space_leaderboard"].get("recorded"))
                result["duplicate"] = bool(result["space_leaderboard"].get("duplicate"))
                _mark_phase("space_leaderboard")
        learning_stats = result.get("learning_stats") if isinstance(result.get("learning_stats"), dict) else {}
        finalize_completion = globals().get("server_database_finalize_learning_completion")
        if learning_stats and callable(finalize_completion):
            if callable(pg_trace_stage):
                pg_trace_stage("completion_event_persistence")
            fail_prefix = clean(os.environ.get("FUTURE_TEST_FAIL_COMPLETION_BEFORE_FINALIZE", ""))
            if fail_prefix and clean(record.get("completion_run_id", "")).startswith(fail_prefix):
                raise RuntimeError("Injected completion failure before final event for PostgreSQL recovery gate.")
            summary_payload = {"version": 1, **learning_stats, "username": username}
            finalize_completion(record, learning_summary_path(username, create_parent=False), summary_payload)
            record["database_final_event_committed"] = True
            record["database_event_committed"] = True
        if callable(pg_trace_stage):
            pg_trace_stage("snapshot_outbox_enqueue")
        append_learning_log(record)
        _mark_phase("append_log")
        # Added 2026-07-29: commit while the user-summary lock is still held.
        # PostgreSQL visibility must precede the next same-user completion so
        # its response cannot read the previous summary snapshot.
        completion_transaction_commit = globals().get("postgres_request_transaction_commit")
        if callable(completion_transaction_commit):
            completion_transaction_commit()
        _timing_ms["lock_hold"] = int((time.perf_counter() - _lock_acquired) * 1000)
    SERVER_STATE["learning_total"] = int(SERVER_STATE.get("learning_total", 0) or 0) + 1
    SERVER_STATE["last_learning_event"] = record
    if callable(pg_trace_stage):
        pg_trace_stage("cache_invalidation")
    mark_user_activity(username, {
        "status": "Completed lesson",
        "space": clean(record.get("source", "")),
        "title": clean(record.get("title", "")),
        "path": clean(record.get("path", "")),
        "nodeIndex": max(0, int(record.get("nodes", 0) or 0)),
        "nodeCount": max(0, int(record.get("nodes", 0) or 0)),
    })
    result["timing_ms"] = {
        **_timing_ms,
        "total": int((time.perf_counter() - _completion_started) * 1000),
        "thread_cpu": round((time.thread_time_ns() - _completion_thread_cpu_started) / 1e6, 3),
        "process_cpu_delta": round((time.process_time_ns() - _completion_process_cpu_started) / 1e6, 3),
    }
    try:
        pg_getter = globals().get("postgres_trace_snapshot")
        if callable(pg_getter):
            result["postgres_delta"] = pg_getter()
    except Exception:
        pass
    _trace_disk_log = clean(os.environ.get("FUTURE_COMPLETION_TRACE_DISK_LOG", "")).lower() in {"1", "true", "yes", "on"}
    if completion_trace_id and _trace_disk_log:
        stt_debug_log("completion_trace_lesson_stage", trace_id=completion_trace_id, user=username, timing_ms=result.get("timing_ms", {}), postgres=result.get("postgres_delta", {}))
    if completion_trace_id:
        result["completion_trace_id"] = completion_trace_id
    result["completion_confirmed"] = True
    return result
