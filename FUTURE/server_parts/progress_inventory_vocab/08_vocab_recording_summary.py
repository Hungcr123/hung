# Loaded by FUTURE.server_parts.08_progress_inventory_vocab into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

SPACE_V_REGISTRY_SYNC_LOCK = threading.Lock()
SPACE_V_REGISTRY_SYNC_STATE: dict[str, dict] = {}
SPACE_V_REGISTRY_SYNC_DEDUPE_SECONDS = 30.0
SPACE_V_REGISTRY_SYNC_WAL_LOCK = threading.Lock()


def append_space_v_registry_sync_wal(row: dict) -> None:
    SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(row, ensure_ascii=False, separators=(",", ":"), default=str) + "\n").encode("utf-8")
    with SPACE_V_REGISTRY_SYNC_WAL_LOCK:
        with SPACE_V_REGISTRY_SYNC_WAL_FILE.open("ab") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())


def pending_space_v_registry_sync_wal_jobs() -> list[dict]:
    if not SPACE_V_REGISTRY_SYNC_WAL_FILE.is_file():
        return []
    pending: dict[str, dict] = {}
    try:
        lines = SPACE_V_REGISTRY_SYNC_WAL_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []
    for line in lines:
        try:
            row = json.loads(line)
        except Exception:
            continue
        job_id = clean(row.get("id", "")) if isinstance(row, dict) else ""
        if not job_id:
            continue
        if clean(row.get("event", "")) == "ack":
            pending.pop(job_id, None)
        elif clean(row.get("event", "")) == "job" and isinstance(row.get("progress"), dict):
            pending[job_id] = row
    return list(pending.values())


def compact_space_v_registry_sync_wal(force: bool = False) -> bool:
    try:
        if not SPACE_V_REGISTRY_SYNC_WAL_FILE.is_file() or (not force and SPACE_V_REGISTRY_SYNC_WAL_FILE.stat().st_size < 256 * 1024):
            return False
    except Exception:
        return False
    with SPACE_V_REGISTRY_SYNC_WAL_LOCK:
        jobs = pending_space_v_registry_sync_wal_jobs()
        if not jobs:
            SPACE_V_REGISTRY_SYNC_WAL_FILE.unlink(missing_ok=True)
            return True
        temp_path = SPACE_V_REGISTRY_SYNC_WAL_FILE.with_suffix(SPACE_V_REGISTRY_SYNC_WAL_FILE.suffix + ".tmp")
        with temp_path.open("wb") as handle:
            for row in jobs:
                handle.write((json.dumps(row, ensure_ascii=False, separators=(",", ":"), default=str) + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, SPACE_V_REGISTRY_SYNC_WAL_FILE)
        return True

def record_user_vocabulary_items(
    username: str,
    learned_items: list[dict],
    source_path: str = "",
    increment_count: bool = True,
    sync_main: bool = True,
    record_period_activity: bool = True,
    verify_registry: bool = True,
    enrich_qmdict: bool = True,
    update_learning_summary: bool = True,
    progress_record: dict | None = None,
    completion_event: dict | None = None,
) -> dict:
    raw_items = learned_items if isinstance(learned_items, list) else []
    if not raw_items:
        return {"learned_words": 0, "total_words": 0}
    learned = []
    seen = set()
    qmdict_maps = qmdict_registry_summary_maps() if enrich_qmdict else {}
    for item in raw_items:
        normalized = normalize_vocabulary_registry_item(item)
        key = vocab_key(normalized.get("word", ""))
        if key and key not in seen:
            current = qmdict_maps.get(key) if qmdict_maps else {}
            if qmdict_maps and not current:
                normalized["qmdict_missing"] = True
            if current:
                normalized = {
                    **normalized,
                    "word": clean(current.get("word", "")) or clean(normalized.get("word", "")),
                    "meaning": clean(current.get("meaning", "")) or clean(normalized.get("meaning", "")),
                    "pron": clean(current.get("pron", "")) or clean(normalized.get("pron", "")),
                    "type": clean(current.get("type", "")) or clean(normalized.get("type", "")),
                }
                key = vocab_key(normalized.get("word", ""))
                if not key or key in seen:
                    continue
            seen.add(key)
            learned.append(normalized)
    if not learned:
        return {"learned_words": 0, "total_words": 0}
    username = normalize_username(username)
    source = clean(source_path)
    now = utc_timestamp()
    added = 0
    updated = 0
    database_result = None
    database_recorder = globals().get("server_database_record_vocabulary_transaction")
    if callable(database_recorder):
        pg_trace_stage = globals().get("postgres_trace_set_stage")
        if callable(pg_trace_stage):
            pg_trace_stage("vocabulary_delta")
        now_epoch = timestamp_to_epoch(now) or time.time()
        database_result = database_recorder(
            username,
            learned,
            source,
            increment_count,
            now,
            {scope: vocab_period_bucket(scope, now_epoch) for scope in ("day", "week", "month")},
            run_marker=source,
            record_period_activity=record_period_activity,
            progress_record=progress_record,
            completion_event=completion_event,
        )
        registry = database_result.get("registry") if isinstance(database_result.get("registry"), dict) else {"version": 1, "updated_at": now, "words": {}}
        added = max(0, space_w_int(database_result.get("added", 0), 0))
        updated = max(0, space_w_int(database_result.get("updated", 0), 0))
        total_words = max(0, space_w_int(database_result.get("total_words", 0), 0))
    else:
        with VOCAB_REGISTRY_LOCK:
            registry = read_user_vocab_registry(username)
            words = registry.setdefault("words", {})
            for item in learned:
                key = vocab_key(item.get("word", ""))
                if not key:
                    continue
                previous = words.get(key) if isinstance(words.get(key), dict) else {}
                if not previous:
                    added += 1
                else:
                    updated += 1
                sources = previous.get("sources") if isinstance(previous.get("sources"), list) else []
                if source and source not in sources:
                    sources.append(source)
                previous_count = max(0, space_w_int(previous.get("count", 0), 0))
                source_count = max(0, space_w_int(item.get("count", 0), 0))
                next_count = previous_count + 1 if increment_count else max(1, previous_count, source_count)
                next_item = {
                    "word": clean(item.get("word", "")) or previous.get("word", key),
                    "meaning": clean(item.get("meaning", "")) or clean(previous.get("meaning", "")),
                    "pron": clean(item.get("pron", "")) or clean(previous.get("pron", "")),
                    "type": clean(item.get("type", "")) or clean(previous.get("type", "")),
                    "count": next_count,
                    "first": clean(previous.get("first", "")) or now,
                    "last": clean(item.get("last", "")) or now,
                    "sources": sources[-40:],
                }
                if item.get("qmdict_missing") or previous.get("qmdict_missing"):
                    next_item["qmdict_missing"] = True
                words[key] = next_item
            write_user_vocab_registry(username, registry)
            total_words = len(words)
    with VOCAB_REGISTRY_LOCK:
        update_user_vocab_registry_summary_cache(username, total_words, registry.get("updated_at", now))
    result = {
        "learned_words": len(learned),
        "accepted_word_keys": [vocab_key(item.get("word", "")) for item in learned if vocab_key(item.get("word", ""))],
        "learned_word_keys": [vocab_key(item.get("word", "")) for item in learned if vocab_key(item.get("word", ""))],
        "added": added,
        "updated": updated,
        "total_words": total_words,
    }
    generation_reader = globals().get("server_database_user_generation")
    if callable(generation_reader):
        try:
            result["registry_generation"] = int(generation_reader("registry", username) or 0)
            result["period_generation"] = int(generation_reader("period", username) or 0)
        except Exception:
            pass
    if isinstance(database_result, dict) and clean(database_result.get("event_key", "")):
        result["database_event_committed"] = True
        result["event_key"] = clean(database_result.get("event_key", ""))
    if record_period_activity:
        try:
            pg_trace_stage = globals().get("postgres_trace_set_stage")
            if callable(pg_trace_stage):
                pg_trace_stage("period_update")
            if isinstance(database_result, dict):
                recorded = database_result.get("recorded") if isinstance(database_result.get("recorded"), dict) else {}
                result["leaderboard_periods"] = {
                    "recorded": sum(max(0, space_w_int(recorded.get(scope, 0), 0)) for scope in ("day", "week", "month")),
                    **{scope: max(0, space_w_int(recorded.get(scope, 0), 0)) for scope in ("day", "week", "month")},
                    "database": True,
                }
                with VOCAB_LEADERBOARD_PERIOD_LOCK:
                    period_patcher = globals().get("patch_vocab_leaderboard_period_state_from_delta")
                    period_state = period_patcher(
                        username,
                        {scope: vocab_period_bucket(scope, timestamp_to_epoch(now) or time.time()) for scope in ("day", "week", "month")},
                        result.get("learned_word_keys", []),
                        now,
                    ) if callable(period_patcher) else load_vocab_leaderboard_period_state()
                    update_vocab_leaderboard_cache_for_user(
                        username,
                        "space_v",
                        vocabulary_result=result,
                        period_state=period_state,
                    )
            else:
                # Legacy fallback for environments that deliberately disable the database layer.
                period_learned = [{**item, "last": now, "learned_at": now} for item in learned if isinstance(item, dict)]
                result["leaderboard_periods"] = record_vocab_leaderboard_period_activity(
                    username,
                    period_learned,
                    default_epoch=timestamp_to_epoch(now) or time.time(),
                )
        except Exception as exc:
            result["leaderboard_period_error"] = str(exc)
    if update_learning_summary:
        learning_stats = update_lesson_user_learning_summary_vocabulary_count(username, total_words)
        if isinstance(learning_stats, dict):
            result["learning_stats"] = learning_stats
    if verify_registry:
        try:
            verified = reconcile_user_vocabulary_total(username, sync_main=False)
            verified_total = max(0, space_w_int(verified.get("total_words", total_words), total_words))
            result["verified_total_words"] = verified_total
            result["total_words"] = max(total_words, verified_total)
            if isinstance(verified.get("learning_stats"), dict):
                result["learning_stats"] = verified.get("learning_stats")
        except Exception as exc:
            result["verify_error"] = str(exc)
    if sync_main:
        try:
            result["main_sync"] = sync_future_vocab_registry_to_main_progress(username)
        except Exception as exc:
            result["main_sync"] = {"updated": 0, "error": str(exc)}
    return result


def record_user_vocabulary_words(
    username: str,
    file_payload: dict,
    source_path: str = "",
    sync_main: bool = True,
    verify_registry: bool = True,
    enrich_qmdict: bool = True,
    update_learning_summary: bool = True,
    completion_event: dict | None = None,
) -> dict:
    return record_user_vocabulary_items(
        username,
        vocabulary_words_from_payload(file_payload),
        source_path,
        increment_count=True,
        sync_main=sync_main,
        verify_registry=verify_registry,
        enrich_qmdict=enrich_qmdict,
        update_learning_summary=update_learning_summary,
        completion_event=completion_event,
    )


def vocabulary_words_from_space_v_progress(progress_record: dict) -> list[dict]:
    if not isinstance(progress_record, dict):
        return []
    state = progress_record.get("state") if isinstance(progress_record.get("state"), dict) else {}
    completed = any(
        truthy(progress_record.get(key), False) or truthy(state.get(key), False)
        for key in ("complete", "completed", "lessonComplete", "lessonCompletionSent", "vocabComplete", "registryReady")
    )
    raw_words = (
        state.get("learnedWords")
        if isinstance(state.get("learnedWords"), list)
        else state.get("learned_words")
        if isinstance(state.get("learned_words"), list)
        else state.get("learnedVocabulary")
        if isinstance(state.get("learnedVocabulary"), list)
        else progress_record.get("learnedWords")
        if isinstance(progress_record.get("learnedWords"), list)
        else []
    )
    learned_keys = {
        vocab_key(value)
        for value in (state.get("learned") if isinstance(state.get("learned"), list) else [])
        if vocab_key(value)
    }
    result = []
    seen = set()
    for item in raw_words:
        normalized = normalize_vocabulary_registry_item(item)
        key = vocab_key(normalized.get("word", ""))
        if not key or key in seen:
            continue
        if not completed and learned_keys and key not in learned_keys:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def record_user_vocabulary_from_space_v_progress(
    username: str,
    progress_record: dict,
    sync_main: bool = True,
    verify_registry: bool = True,
) -> dict:
    state = progress_record.get("state") if isinstance(progress_record, dict) and isinstance(progress_record.get("state"), dict) else {}
    lesson_source = state.get("lessonSource") if isinstance(state.get("lessonSource"), dict) else {}
    source_path = clean(progress_record.get("path", "")) or clean(state.get("path", "")) or clean(lesson_source.get("path", ""))
    return record_user_vocabulary_items(
        username,
        vocabulary_words_from_space_v_progress(progress_record),
        source_path,
        increment_count=False,
        sync_main=sync_main,
        verify_registry=verify_registry,
        enrich_qmdict=False,
        progress_record=progress_record,
    )


# Added 2026-07-09: marks terminal Space_V progress after server registry/Top sync succeeds.
def mark_space_v_progress_registry_ready(username: str, progress_record: dict, result: dict | None = None) -> dict:
    if not isinstance(progress_record, dict):
        return {}
    state = dict(progress_record.get("state") if isinstance(progress_record.get("state"), dict) else {})
    now = utc_timestamp()
    state.update({
        "complete": True,
        "registryReady": True,
        "vocabComplete": True,
        "lessonComplete": True,
        "lessonCompletionSent": True,
        "registrySyncedAt": now,
    })
    if isinstance(result, dict):
        state["registryLearnedWords"] = max(0, space_w_int(result.get("learned_words", 0), 0))
        state["registryTotalWords"] = max(0, space_w_int(result.get("total_words", 0), 0))
    payload = {
        **progress_record,
        "complete": True,
        "registryReady": True,
        "vocabComplete": True,
        "lessonComplete": True,
        "savedAt": clean(progress_record.get("savedAt", "")) or now,
        "state": state,
    }
    return save_space_v_progress(username, payload)


def start_space_v_registry_sync_job(
    username: str,
    progress_record: dict,
    reason: str = "space-v-complete",
    delay_seconds: float = 0.8,
    durable_job_id: str = "",
    persist_job: bool = True,
) -> dict:
    username = normalize_username(username)
    if not username or not isinstance(progress_record, dict):
        return {"queued": False, "running": False, "user": username}
    try:
        progress_copy = json.loads(json.dumps(progress_record, ensure_ascii=False, default=str))
    except Exception:
        progress_copy = dict(progress_record)
    state = progress_copy.get("state") if isinstance(progress_copy.get("state"), dict) else {}
    lesson_source = state.get("lessonSource") if isinstance(state.get("lessonSource"), dict) else {}
    source_path = clean(progress_copy.get("path", "")) or clean(state.get("path", "")) or clean(lesson_source.get("path", ""))
    identity = clean(progress_copy.get("lesson_id") or progress_copy.get("file_id") or progress_copy.get("identity") or state.get("lesson_id") or state.get("file_id") or state.get("identity"))
    run_marker = clean(
        progress_copy.get("completionRunId")
        or progress_copy.get("completion_run_id")
        or progress_copy.get("runId")
        or progress_copy.get("run_id")
        or state.get("completionRunId")
        or state.get("completion_run_id")
        or state.get("runId")
        or state.get("run_id")
        or "file"
    )[:160]
    identity_scope = f"id:{identity.lower()}" if identity.lower().startswith("ftg-lesson-") else f"path:{source_path.lower()}"
    sync_key = "|".join([username.lower(), identity_scope[:256], run_marker])
    job_id = clean(durable_job_id) or hashlib.sha1(sync_key.encode("utf-8", errors="replace")).hexdigest()
    now = time.time()
    with SPACE_V_REGISTRY_SYNC_LOCK:
        active = SPACE_V_REGISTRY_SYNC_STATE.get(sync_key)
        if isinstance(active, dict):
            if bool(active.get("running")):
                return {"queued": False, "running": True, "user": username, "path": source_path, "reason": clean(reason)}
            done_at = float(active.get("done_at", 0.0) or 0.0)
            if done_at and now - done_at < SPACE_V_REGISTRY_SYNC_DEDUPE_SECONDS:
                return {"queued": False, "running": False, "already_synced": True, "user": username, "path": source_path, "reason": clean(reason)}
        for old_key, old_row in list(SPACE_V_REGISTRY_SYNC_STATE.items()):
            if old_key != sync_key and isinstance(old_row, dict) and now - float(old_row.get("done_at", old_row.get("at", now)) or now) > 300:
                SPACE_V_REGISTRY_SYNC_STATE.pop(old_key, None)
        SPACE_V_REGISTRY_SYNC_STATE[sync_key] = {"at": now, "running": True, "user": username, "path": source_path}
    if persist_job:
        append_space_v_registry_sync_wal({
            "v": 1,
            "event": "job",
            "id": job_id,
            "at": utc_timestamp(),
            "user": username,
            "reason": clean(reason),
            "progress": progress_copy,
        })

    def _worker() -> None:
        trace_id = clean(progress_copy.get("completion_trace_id") or state.get("completion_trace_id"))[:160]
        worker_wall = time.perf_counter_ns()
        worker_thread_cpu = time.thread_time_ns()
        worker_process_cpu = time.process_time_ns()
        pg_getter = globals().get("postgres_metrics_snapshot")
        pg_before = pg_getter() if callable(pg_getter) else {}
        try:
            if delay_seconds > 0:
                time.sleep(max(0.0, float(delay_seconds)))
            result = record_user_vocabulary_from_space_v_progress(
                username,
                progress_copy,
                sync_main=False,
                verify_registry=False,
            )
            if isinstance(result, dict) and (result.get("learned_words") or result.get("total_words")):
                result["leaderboard_cache"] = update_vocab_leaderboard_cache_for_user(username, "space_v", result)
                try:
                    mark_space_v_progress_registry_ready(username, progress_copy, result)
                except Exception as ready_exc:
                    result["progress_ready_error"] = str(ready_exc)
                try:
                    start_main_vocab_sync_user(
                        username,
                        force=False,
                        reason="space-v-complete",
                        delay_seconds=2.0,
                    )
                except Exception as main_sync_exc:
                    result["main_vocab_sync_error"] = str(main_sync_exc)
            stt_debug_log(
                "SPACE_V_REGISTRY_SYNC_BACKGROUND done",
                trace_id=trace_id,
                user=username,
                path=source_path,
                learned=result.get("learned_words", 0) if isinstance(result, dict) else 0,
                total=result.get("total_words", 0) if isinstance(result, dict) else 0,
                reason=reason,
                wall_ms=round((time.perf_counter_ns() - worker_wall) / 1e6, 3),
                thread_cpu_ms=round((time.thread_time_ns() - worker_thread_cpu) / 1e6, 3),
                process_cpu_delta_ms=round((time.process_time_ns() - worker_process_cpu) / 1e6, 3),
                postgres={key: int((pg_getter() if callable(pg_getter) else {}).get(key, 0) or 0) - int(pg_before.get(key, 0) or 0) for key in ("transactions", "commits", "rollbacks", "sql_round_trips")},
            )
            append_space_v_registry_sync_wal({"v": 1, "event": "ack", "id": job_id, "at": utc_timestamp()})
            compact_space_v_registry_sync_wal(force=False)
        except Exception as exc:
            stt_debug_log("SPACE_V_REGISTRY_SYNC_BACKGROUND failed", user=username, path=source_path, error=str(exc), reason=reason)
        finally:
            with SPACE_V_REGISTRY_SYNC_LOCK:
                active = SPACE_V_REGISTRY_SYNC_STATE.get(sync_key)
                if isinstance(active, dict):
                    active["running"] = False
                    active["done_at"] = time.time()

    thread = threading.Thread(target=_worker, daemon=True, name=f"space-v-registry-sync-{username[:24]}")
    thread.start()
    return {
        "queued": True,
        "running": True,
        "scheduled": True,
        "delay_seconds": max(0.0, float(delay_seconds)),
        "user": username,
        "path": source_path,
        "reason": clean(reason),
        "durable": True,
        "job_id": job_id,
    }


def replay_space_v_registry_sync_wal_async() -> dict:
    jobs = pending_space_v_registry_sync_wal_jobs()
    if not jobs:
        return {"scheduled": 0}

    def _replay() -> None:
        for row in jobs:
            try:
                start_space_v_registry_sync_job(
                    clean(row.get("user", "")),
                    row.get("progress") if isinstance(row.get("progress"), dict) else {},
                    reason="crash-wal-replay",
                    delay_seconds=0.0,
                    durable_job_id=clean(row.get("id", "")),
                    persist_job=False,
                )
            except Exception as exc:
                stt_debug_log("SPACE_V_REGISTRY_SYNC_WAL replay failed", error=str(exc), job=clean(row.get("id", "")))

    threading.Thread(target=_replay, daemon=True, name="space-v-registry-wal-replay").start()
    return {"scheduled": len(jobs)}


def space_v_registry_sync_has_completion_marker(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False
    state = payload.get("state") if isinstance(payload.get("state"), dict) else {}
    completion_keys = (
        "complete",
        "registryReady",
        "vocabComplete",
        "lessonComplete",
        "lessonCompletionSent",
    )
    return any(truthy(payload.get(key), False) for key in completion_keys) or any(
        truthy(state.get(key), False) for key in completion_keys
    )


def space_v_registry_sync_allowed(username: str, payload: dict) -> tuple[bool, str]:
    if not space_v_registry_sync_has_completion_marker(payload):
        return False, "incomplete_space_v_progress"
    raw_path = clean(payload.get("path", "")) if isinstance(payload, dict) else ""
    if not raw_path:
        return True, ""
    try:
        raw_parts = [clean(part) for part in re.split(r"[\\/]+", raw_path) if clean(part)]
        raw_owner = normalize_username(raw_parts[0]) if raw_parts else ""
        own_user_folder_run = bool(raw_owner and raw_owner.lower() == normalize_username(username).lower())
        admin_run = bool(is_admin_user(username) and not own_user_folder_run)
        target = safe_server_data_path(raw_path, username, admin=admin_run)
    except Exception:
        return False, "invalid_space_v_path"
    if not target.is_file() or target.suffix.lower() not in {".space_v", ".space_b"}:
        return False, "space_v_file_not_found"
    try:
        file_payload, _structure_path = load_future_lesson_document(target)
        study = normalize_study_block(file_payload)
        bucket_name = "admins" if admin_run else "users"
        users = study.get(bucket_name, {}) if isinstance(study.get(bucket_name), dict) else {}
        user_study = users.get(normalize_username(username), {}) if isinstance(users.get(normalize_username(username)), dict) else {}
        if max(0, space_w_int(user_study.get("count", 0), 0)) <= 0:
            log_study = learning_completion_study_for_paths([raw_path, server_data_relative(target)])
            log_users = log_study.get(bucket_name, {}) if isinstance(log_study.get(bucket_name), dict) else {}
            log_user_study = log_users.get(normalize_username(username), {}) if isinstance(log_users.get(normalize_username(username)), dict) else {}
            if max(0, space_w_int(log_user_study.get("count", 0), 0)) <= 0:
                return False, "space_v_file_not_completed"
    except Exception:
        return False, "space_v_completion_check_failed"
    return True, ""


def user_vocabulary_registry_summary(username: str, sync_main: bool = True, reconcile_qmdict: bool = True) -> dict:
    if sync_main:
        try:
            sync_main_vocabulary_for_user(username)
        except Exception:
            pass
    if reconcile_qmdict:
        try:
            reconcile_user_vocab_registry_with_qmdict(username, write=True)
        except Exception as exc:
            stt_debug_log("user_vocab_registry_qmdict_reconcile_failed", user=normalize_username(username), error=str(exc))
    registry = read_user_vocab_registry(username)
    raw_words = registry.get("words") if isinstance(registry.get("words"), dict) else {}
    words = []
    for key, item in raw_words.items():
        if not isinstance(item, dict):
            continue
        word = clean(item.get("word") or key)
        if not word:
            continue
        words.append(
            {
                "key": vocab_key(word),
                "word": word,
                "meaning": clean(item.get("meaning", "")),
                "pron": clean(item.get("pron", "")),
                "type": clean(item.get("type", "")),
                "count": int(item.get("count", 0) or 0),
                "last": clean(item.get("last", "")),
            }
        )
    words.sort(key=lambda item: (item.get("word", "").lower(), item.get("meaning", "").lower()))
    try:
        period_state = load_vocab_leaderboard_period_state(clone=False)
        period_keys = vocab_leaderboard_period_word_keys_for_user(username, period_state)
        period_payload = {scope: sorted(period_keys.get(scope, set())) for scope in ("day", "week", "month")}
    except Exception:
        period_payload = {"day": [], "week": [], "month": []}
    return {
        "total_words": len(words),
        "updated_at": clean(registry.get("updated_at", "")),
        "period_keys": period_payload,
        "words": words,
    }


# Added 2026-07-20: serve the full registry from revision-keyed JSON bytes instead of rebuilding/sorting on every GET.
def vocab_registry_response_signature(username: str = "") -> tuple:
    resets = server_database_load_period_resets()
    return (
        normalize_username(username),
        server_database_user_generation("registry", username),
        server_database_user_generation("period", username),
        tuple(vocab_period_bucket(scope) for scope in ("day", "week", "month")),
        tuple(timestamp_to_epoch(resets.get(scope, "")) or 0.0 for scope in ("day", "week", "month")),
    )


def vocab_registry_response_cache_row(username: str = "") -> dict | None:
    username = normalize_username(username)
    signature = vocab_registry_response_signature(username)
    cache = globals().setdefault("VOCAB_REGISTRY_RESPONSE_BYTES_CACHE", {})
    lock = globals().setdefault("VOCAB_REGISTRY_RESPONSE_BYTES_CACHE_LOCK", threading.RLock())
    with lock:
        row = cache.get(username.lower()) if isinstance(cache, dict) else None
        if (
            isinstance(row, dict)
            and row.get("signature") == signature
            and isinstance(row.get("payload"), dict)
            and isinstance(row.get("bytes"), bytes)
        ):
            return {**row, "cache_hit": True}
    return None


def build_vocab_registry_response_cache_row(username: str = "", fresh: bool = False) -> dict:
    username = normalize_username(username)
    summary = user_vocabulary_registry_summary(username, sync_main=fresh, reconcile_qmdict=fresh)
    verified_total = max(0, space_w_int(summary.get("total_words", 0), 0))
    if fresh:
        verified = reconcile_user_vocabulary_total(username, sync_main=False)
        verified_total = max(verified_total, max(0, space_w_int(verified.get("total_words", verified_total), verified_total)))
    payload = {
        "ok": True,
        **summary,
        "verified_total_words": verified_total,
        "fast": not fresh,
    }
    data = json_bytes(payload)
    row = {
        "signature": vocab_registry_response_signature(username),
        "payload": payload,
        "bytes": data,
        "etag": f'"vocab-registry-{hashlib.sha1(data).hexdigest()}"',
        "at": time.time(),
        "cache_hit": False,
    }
    cache = globals().setdefault("VOCAB_REGISTRY_RESPONSE_BYTES_CACHE", {})
    lock = globals().setdefault("VOCAB_REGISTRY_RESPONSE_BYTES_CACHE_LOCK", threading.RLock())
    with lock:
        cache[username.lower()] = row
        if len(cache) > 256:
            stale = sorted(cache.items(), key=lambda item: float((item[1] or {}).get("at", 0.0) or 0.0))
            for old_key, _old_row in stale[:64]:
                if old_key != username.lower():
                    cache.pop(old_key, None)
    return row


def get_or_build_vocab_registry_response_cache_row(username: str = "", fresh: bool = False) -> dict:
    username = normalize_username(username)
    if fresh:
        return build_vocab_registry_response_cache_row(username, True)
    cached = vocab_registry_response_cache_row(username)
    if isinstance(cached, dict):
        return cached
    lock = globals().setdefault("VOCAB_REGISTRY_RESPONSE_BYTES_CACHE_LOCK", threading.RLock())
    inflight = globals().setdefault("VOCAB_REGISTRY_RESPONSE_BUILD_INFLIGHT", {})
    user_key = username.lower()
    should_build = False
    with lock:
        event = inflight.get(user_key) if isinstance(inflight, dict) else None
        if not hasattr(event, "wait"):
            event = threading.Event()
            inflight[user_key] = event
            should_build = True
    if not should_build:
        event.wait(12.0)
        cached = vocab_registry_response_cache_row(username)
        if isinstance(cached, dict):
            cached["coalesced"] = True
            return cached
    try:
        return build_vocab_registry_response_cache_row(username, False)
    finally:
        if should_build:
            with lock:
                inflight.pop(user_key, None)
                event.set()


USER_VOCAB_REGISTRY_SNAPSHOT_CACHE: dict[str, dict] = {}
USER_VOCAB_REGISTRY_SUMMARY_CACHE: dict[str, dict] = {}


def clone_user_vocab_registry_snapshot(payload: dict | None = None) -> dict:
    try:
        import copy
        return copy.deepcopy(payload if isinstance(payload, dict) else {})
    except Exception:
        return dict(payload or {})


def user_vocab_registry_file_signature(username: str) -> tuple[Path | None, tuple[int, int]]:
    username = normalize_username(username)
    if not username:
        return None, (0, 0)
    generation_getter = globals().get("server_database_user_generation")
    generation = generation_getter("registry", username) if callable(generation_getter) else 0
    return None, (int(generation), 0)


# Added 2026-07-06: lightweight Space_V Top count so leaderboard cold builds do not clone every learned word.
def read_user_vocab_registry_summary(username: str) -> dict:
    username = normalize_username(username)
    if not username:
        return {"total_words": 0, "updated_at": ""}
    _path, signature = user_vocab_registry_file_signature(username)
    cache_key = username.lower()
    cached = USER_VOCAB_REGISTRY_SUMMARY_CACHE.get(cache_key)
    if isinstance(cached, dict) and cached.get("signature") == signature:
        return dict(cached.get("payload") if isinstance(cached.get("payload"), dict) else {})
    summary_reader = globals().get("server_database_vocab_registry_summary")
    result = summary_reader(username) if callable(summary_reader) else {"total_words": 0, "updated_at": ""}
    USER_VOCAB_REGISTRY_SUMMARY_CACHE[cache_key] = {"signature": signature, "payload": dict(result)}
    return result


# Added 2026-07-06: keeps Space_V Top total-word summary hot immediately after a learner posts progress.
def update_user_vocab_registry_summary_cache(username: str, total_words: int, updated_at: str = "") -> dict:
    username = normalize_username(username)
    if not username:
        return {"updated": False, "reason": "missing_user"}
    _path, signature = user_vocab_registry_file_signature(username)
    payload = {
        "total_words": max(0, space_w_int(total_words, 0)),
        "updated_at": clean(updated_at) or utc_timestamp(),
    }
    USER_VOCAB_REGISTRY_SUMMARY_CACHE[username.lower()] = {"signature": signature, "payload": dict(payload)}
    return {"updated": True, **payload}


def read_user_vocab_registry_snapshot(username: str) -> dict:
    username = normalize_username(username)
    if not username:
        return {"version": 1, "updated_at": "", "words": {}}
    _path, signature = user_vocab_registry_file_signature(username)
    cache_key = username.lower()
    cached = USER_VOCAB_REGISTRY_SNAPSHOT_CACHE.get(cache_key)
    if isinstance(cached, dict) and cached.get("signature") == signature and isinstance(cached.get("payload"), dict):
        return clone_user_vocab_registry_snapshot(cached.get("payload"))
    result = read_user_vocab_registry(username)
    USER_VOCAB_REGISTRY_SNAPSHOT_CACHE[cache_key] = {"signature": signature, "payload": clone_user_vocab_registry_snapshot(result)}
    return result
