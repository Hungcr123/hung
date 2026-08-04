# Loaded by FUTURE.server_parts.10_vocab_build_status into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def space_w_vocab_context(relative_path: str, username: str, lesson_id: str = "") -> dict:
    username = normalize_username(username)
    raw_path = clean_path_value(relative_path)
    if not raw_path:
        raise RuntimeError("Chua co duong dan bai hoc.")
    requested_target = safe_server_data_path(raw_path, username, admin=is_admin_user(username))
    # Updated 2026-07-03: linked Lesson Vault entries must scan/build Space_V from the effective source file.
    target = server_data_effective_file_path(requested_target, username=username, admin=is_admin_user(username))
    suffix = target.suffix.lower()
    if not target.is_file() or suffix not in {".space_w", ".space_q", ".space_p", ".space_s", ".space_l"}:
        raise RuntimeError("Tinh nang nay chi ap dung cho file .Space_W/Q/P/S/L tren server.")
    space_label = {
        ".space_w": "Space_W",
        ".space_q": "Space_Q",
        ".space_p": "Space_P",
        ".space_s": "Space_S",
        ".space_l": "Space_L",
    }.get(suffix, "Space_W")
    stat = target.stat()
    meta = lesson_vocab_meta_for_id(lesson_id)
    current_signature = qmdict_source_signature_key()
    current_signature_text = f"{int(current_signature[0])}:{int(current_signature[1])}"
    if (
        not lesson_vocab_meta_is_current(meta, None)
        or clean(meta.get("vocab_validated_signature", "")) != current_signature_text
        or clean(meta.get("vocab_extractor_version", "")) != VOCAB_FILE_META_EXTRACTOR_VERSION
    ):
        meta = lesson_file_vocab_meta_cached_for_target(target)
        if not meta:
            meta = lesson_file_vocab_meta_for_target(target)
    lesson_id = clean(meta.get("lesson_id", "")) if isinstance(meta, dict) else ""
    source_identity = lesson_id or str(target).lower()
    source_cache_key = (
        "lesson-vocab-source-v2",
        source_identity,
        0 if lesson_id else int(stat.st_mtime_ns),
        0 if lesson_id else int(stat.st_size),
        *qmdict_source_signature_key(),
    )
    with QMDICT_VOCAB_BASE_CACHE_LOCK:
        base = QMDICT_VOCAB_BASE_CACHE.get(source_cache_key)

    def build_source_base() -> dict:
        signature = qmdict_source_signature_key()
        signature_text = f"{int(signature[0])}:{int(signature[1])}"
        valid_keys = list(meta.get("vocab_valid_word_keys") or []) if isinstance(meta, dict) else []
        meta_validated = isinstance(meta, dict) and clean(meta.get("vocab_validated_signature", "")) == signature_text
        entries = []
        if meta_validated:
            from types import SimpleNamespace  # noqa: PLC0415

            summary_maps = qmdict_registry_summary_maps()
            for key in valid_keys:
                detail = summary_maps.get(vocab_key(key)) if isinstance(summary_maps, dict) else None
                if not isinstance(detail, dict) or not detail:
                    continue
                entries.append(SimpleNamespace(
                    word=clean(detail.get("word", "")) or clean(key),
                    meaning=clean(detail.get("meaning", "")),
                    pron=clean(detail.get("pron", "") or detail.get("pron_uk", "") or detail.get("pron_us", "")),
                    word_type=clean(detail.get("type", "")),
                    lookup_status="QmDict shared file index",
                ))
        if not meta_validated or (valid_keys and not entries):
            payload, _structure_path = load_future_lesson_document(target)
            text = lesson_english_text(payload)
            entries = resolve_vocab_entries_for_text(text)
            source_title = lesson_payload_title(payload, target.stem) or target.stem
        else:
            source_title = clean(meta.get("vocab_source_title", "")) or target.stem
        source_rel = server_data_relative(target)
        digest = hashlib.sha1(f"{source_identity}|{space_label.lower()}|words-only-v3".encode("utf-8", "replace")).hexdigest()[:12]
        mission_name = f"{safe_name_segment(source_title, f'{space_label} Vocabulary', 42)} {digest}"
        result = {
            "lesson_id": lesson_id,
            "source_path": source_rel,
            "source_title": source_title,
            "mission_id": mission_name,
            "entries": list(entries),
        }
        with QMDICT_VOCAB_BASE_CACHE_LOCK:
            QMDICT_VOCAB_BASE_CACHE[source_cache_key] = result
            if len(QMDICT_VOCAB_BASE_CACHE) > QMDICT_VOCAB_BASE_CACHE_LIMIT:
                QMDICT_VOCAB_BASE_CACHE.clear()
                QMDICT_VOCAB_BASE_CACHE[source_cache_key] = result
        return result

    if not isinstance(base, dict):
        inflight_runner = globals().get("pdf_vocab_inflight_run")
        base = inflight_runner(("lesson-vocab-source",) + source_cache_key, build_source_base) if callable(inflight_runner) else build_source_base()
    entries = list(base.get("entries", [])) if isinstance(base, dict) else []
    registry = read_user_vocab_registry(username)
    learned_keys = set(registry.get("words", {}).keys())
    new_entries = [entry for entry in entries if vocab_key(getattr(entry, "word", "")) not in learned_keys]
    mission_root = server_data_user_folder_path(username) / VOCAB_MISSION_PENDING_DIR / clean(base.get("mission_id", ""))
    return {
        "space": space_label,
        "target": target,
        "source_path": clean(base.get("source_path", "")),
        "source_title": clean(base.get("source_title", "")),
        "mission_id": clean(base.get("mission_id", "")),
        "mission_root": mission_root,
        "entries": entries,
        "new_entries": new_entries,
        "learned_keys": learned_keys,
        "learned_total": len(learned_keys),
    }


def mission_file_records(
    mission_root: Path,
    username: str,
    learned_keys: set[str] | None = None,
    require_unlearned: bool = False,
) -> list[dict]:
    if not mission_root.is_dir():
        return []
    learned_lookup = learned_keys or set()
    records = []
    for item in sorted(mission_root.glob("*.Space_V"), key=lambda path: path.name.lower()):
        if not item.is_file():
            continue
        if require_unlearned:
            try:
                payload, _structure_path = load_future_lesson_document(item)
                word_keys = [
                    vocab_key(word.get("word", ""))
                    for word in vocabulary_words_from_payload(payload)
                    if vocab_key(word.get("word", ""))
                ]
                if word_keys and not any(key not in learned_lookup for key in word_keys):
                    continue
                if not word_keys:
                    continue
            except Exception:
                pass
        try:
            records.append(
                {
                    "name": item.name,
                    "path": server_data_relative(item),
                    "size": int(item.stat().st_size),
                    "study": summarize_lesson_study(item, username),
                }
            )
        except OSError:
            continue
    return records


def vocab_build_job_snapshot(job: dict | None) -> dict:
    if not isinstance(job, dict):
        return {}
    result = job.get("result") if isinstance(job.get("result"), dict) else {}
    return {
        "job_id": clean(job.get("job_id", "")),
        "status": clean(job.get("status", "running")) or "running",
        "message": clean(job.get("message", "")),
        "progress": max(0, min(100, int(job.get("progress", 0) or 0))),
        "path": clean(job.get("path", "")),
        "username": normalize_username(job.get("username", "")),
        "created_at": float(job.get("created_at", 0) or 0),
        "updated_at": float(job.get("updated_at", 0) or 0),
        "error": clean(job.get("error", "")),
        "result": result,
        "files": result.get("files", []) if isinstance(result.get("files"), list) else [],
        "pending_count": int(result.get("pending_count", 0) or 0) if result else 0,
        "new_count": int(result.get("new_count", 0) or 0) if result else 0,
    }


def cleanup_vocab_build_jobs() -> None:
    cutoff = time.time() - VOCAB_BUILD_TTL_SECONDS
    with VOCAB_BUILD_LOCK:
        stale = [
            job_id
            for job_id, job in VOCAB_BUILD_JOBS.items()
            if float((job or {}).get("updated_at", 0) or 0) < cutoff
        ]
        for job_id in stale:
            VOCAB_BUILD_JOBS.pop(job_id, None)


def update_vocab_build_job(job_id: str, **updates) -> dict:
    with VOCAB_BUILD_LOCK:
        job = VOCAB_BUILD_JOBS.get(job_id)
        if not isinstance(job, dict):
            return {}
        job.update(updates)
        job["updated_at"] = time.time()
        return vocab_build_job_snapshot(job)


def get_vocab_build_job(job_id: str, username: str = "") -> dict:
    job_id = clean(job_id)
    username = normalize_username(username)
    cleanup_vocab_build_jobs()
    with VOCAB_BUILD_LOCK:
        job = VOCAB_BUILD_JOBS.get(job_id)
        if not isinstance(job, dict):
            raise RuntimeError("Khong tim thay job tao vocabulary.")
        if username and normalize_username(job.get("username", "")) != username:
            raise RuntimeError("Job tao vocabulary khong thuoc user nay.")
        return vocab_build_job_snapshot(job)


def start_space_w_vocab_build_job(relative_path: str, username: str) -> dict:
    username = normalize_username(username)
    raw_path = clean_path_value(relative_path)
    if not raw_path:
        raise RuntimeError("Chua co duong dan bai hoc.")
    cleanup_vocab_build_jobs()
    with VOCAB_BUILD_LOCK:
        for job in VOCAB_BUILD_JOBS.values():
            if (
                isinstance(job, dict)
                and normalize_username(job.get("username", "")) == username
                and clean_path_value(job.get("path", "")) == raw_path
                and clean(job.get("status", "")) in {"queued", "running"}
            ):
                return vocab_build_job_snapshot(job)
        job_id = uuid.uuid4().hex[:12]
        now = time.time()
        VOCAB_BUILD_JOBS[job_id] = {
            "job_id": job_id,
            "username": username,
            "path": raw_path,
            "status": "running",
            "message": "Preparing vocabulary build...",
            "progress": 1,
            "created_at": now,
            "updated_at": now,
            "error": "",
            "result": {},
        }

    def progress(message: str = "", done: int | None = None, total: int | None = None, progress_value: int | None = None) -> None:
        updates = {}
        if clean(message):
            updates["message"] = clean(message)
        if progress_value is not None:
            updates["progress"] = max(1, min(99, int(progress_value)))
        elif done is not None and total:
            updates["progress"] = max(1, min(99, int((max(0, done) / max(1, total)) * 92) + 4))
        if updates:
            update_vocab_build_job(job_id, **updates)

    def runner() -> None:
        try:
            progress("Scanning words and current learned memory...", progress_value=4)
            result = build_space_w_vocab_mission(raw_path, username, progress=progress)
            update_vocab_build_job(
                job_id,
                status="done",
                message="Vocabulary queue ready.",
                progress=100,
                result=result,
                error="",
            )
        except Exception as exc:
            update_vocab_build_job(
                job_id,
                status="error",
                message="Vocabulary build failed.",
                error=str(exc),
                progress=100,
            )

    threading.Thread(target=runner, name=f"space-w-vocab-build-{job_id}", daemon=True).start()
    return get_vocab_build_job(job_id, username)


def scan_space_w_vocabulary(relative_path: str, username: str, include_words: bool = True, lesson_id: str = "") -> dict:
    # Added 2026-07-21: scans are read-only and share QmDict/text caches instead of serializing on SERVER_DATA_LOCK.
    normalized_user = normalize_username(username)
    raw_path = clean_path_value(relative_path)
    requested_target = safe_server_data_path(raw_path, normalized_user, admin=is_admin_user(normalized_user))
    target = server_data_effective_file_path(requested_target, username=normalized_user, admin=is_admin_user(normalized_user))
    stat = target.stat()
    shared_meta = lesson_vocab_meta_for_id(lesson_id)
    shared_meta_current = lesson_vocab_meta_is_current(shared_meta, None)
    if not shared_meta_current:
        shared_meta = lesson_file_vocab_meta_cached_for_target(target)
        shared_meta_current = lesson_vocab_meta_is_current(shared_meta, stat)
    if not shared_meta_current:
        repair = schedule_lesson_vocab_meta_repair(target, lesson_id=lesson_id)
        return {
            "source_path": server_data_relative(target),
            "source_title": target.stem,
            "space": {
                ".space_w": "Space_W",
                ".space_q": "Space_Q",
                ".space_p": "Space_P",
                ".space_s": "Space_S",
                ".space_l": "Space_L",
            }.get(target.suffix.lower(), "Space_W"),
            "lesson_id": clean(lesson_id),
            "new_count": 0,
            "learned_total": 0,
            "files_needed": 0,
            "pending_count": 0,
            "pending_files": [],
            "index_pending": True,
            "repair_scheduled": bool(repair.get("scheduled")),
            "repair_single_flight": bool(repair.get("single_flight")),
        }
    lesson_id = clean(shared_meta.get("lesson_id", "")) or clean(lesson_id)
    generation_reader = globals().get("server_database_user_generation")
    registry_generation = int(generation_reader("registry", normalized_user) or 0) if callable(generation_reader) else 0
    scan_key = (
        normalized_user.lower(),
        str(target).lower(),
        clean(lesson_id),
        int(stat.st_mtime_ns),
        int(stat.st_size),
        *qmdict_source_signature_key(),
        registry_generation,
        bool(include_words),
    )
    cache = globals().setdefault("VOCAB_SCAN_RESPONSE_CACHE", {})
    now = time.monotonic()
    with VOCAB_BUILD_LOCK:
        cached = cache.get(scan_key)
        if isinstance(cached, dict) and now - float(cached.get("at", 0.0) or 0.0) <= 3.0 and isinstance(cached.get("result"), dict):
            return dict(cached["result"])

    def compute_scan() -> dict:
        ctx = space_w_vocab_context(raw_path, normalized_user, lesson_id=lesson_id)
        pending = mission_file_records(
            ctx["mission_root"],
            normalized_user,
            learned_keys=ctx.get("learned_keys", set()),
            require_unlearned=True,
        ) if include_words else []
        new_entries = ctx["new_entries"]
        result = {
            "source_path": ctx["source_path"],
            "source_title": ctx["source_title"],
            "space": ctx.get("space", "Space_W"),
            "mission_id": ctx["mission_id"],
            "lesson_id": lesson_id,
            "new_count": len(new_entries),
            "learned_total": ctx["learned_total"],
            "files_needed": math.ceil(len(new_entries) / VOCAB_MISSION_CHUNK_SIZE) if new_entries else 0,
            "pending_count": len(pending),
            "pending_files": pending,
        }
        if include_words:
            result["words"] = [entry_to_summary(entry) for entry in new_entries[:120]]
        with VOCAB_BUILD_LOCK:
            cache[scan_key] = {"at": time.monotonic(), "result": result}
            if len(cache) > 1000:
                ordered = sorted(cache.items(), key=lambda item: float(item[1].get("at", 0.0) or 0.0))
                for old_key, _row in ordered[: len(cache) - 800]:
                    cache.pop(old_key, None)
        return result

    inflight_runner = globals().get("pdf_vocab_inflight_run")
    result = inflight_runner(("lesson-vocab-scan",) + scan_key, compute_scan) if callable(inflight_runner) else compute_scan()
    return dict(result) if isinstance(result, dict) else {}


def build_space_w_vocab_mission(relative_path: str, username: str, progress=None) -> dict:
    def emit(message: str = "", done: int | None = None, total: int | None = None, progress_value: int | None = None) -> None:
        if callable(progress):
            try:
                progress(message, done=done, total=total, progress_value=progress_value)
            except TypeError:
                progress(message)
            except Exception:
                pass

    emit("Analyzing vocabulary source...", progress_value=5)
    with SERVER_DATA_LOCK:
        ctx = space_w_vocab_context(relative_path, username)
        space_label = clean(ctx.get("space", "Space_W")) or "Space_W"
        emit(f"Found {len(ctx['new_entries'])} new words in {space_label}. Checking existing queue...", progress_value=10)
        expected_batches = math.ceil(len(ctx.get("new_entries", [])) / VOCAB_MISSION_CHUNK_SIZE) if ctx.get("new_entries") else 0
        pending = mission_file_records(
            ctx["mission_root"],
            username,
            learned_keys=ctx.get("learned_keys", set()),
            require_unlearned=True,
        )
        if pending and (not expected_batches or len(pending) >= expected_batches):
            emit(f"Existing queue has {len(pending)} Space_V pack(s).", progress_value=100)
            return {
                "source_path": ctx["source_path"],
                "source_title": ctx["source_title"],
                "space": space_label,
                "mission_id": ctx["mission_id"],
                "new_count": len(ctx["new_entries"]),
                "files": pending,
                "pending_count": len(pending),
            }
        new_entries = ctx["new_entries"]
        if not new_entries:
            emit("No new vocabulary is required.", progress_value=100)
            return {
                "source_path": ctx["source_path"],
                "source_title": ctx["source_title"],
                "space": space_label,
                "mission_id": ctx["mission_id"],
                "new_count": 0,
                "files": [],
                "pending_count": 0,
            }
        if pending and expected_batches and len(pending) < expected_batches and ctx["mission_root"].is_dir():
            for stale_file in ctx["mission_root"].glob("*.Space_V"):
                stale_file.unlink()
        mission_root = ctx["mission_root"]
        mission_root.mkdir(parents=True, exist_ok=True)
        batches = [new_entries[index:index + VOCAB_MISSION_CHUNK_SIZE] for index in range(0, len(new_entries), VOCAB_MISSION_CHUNK_SIZE)]
        total_batches = len(batches)
        files = []
        title_root = safe_name_segment(f"{ctx['source_title']} Vocabulary", "Vocabulary", 72)

        def log(message: str) -> None:
            print(f"[vocab mission] {clean(message)}", flush=True)
            emit(clean(message))

        batch_workers = max(1, min(total_batches, 4))
        log(f"Build Space_V toi gian: batch_workers={batch_workers}")
        emit(f"Building {total_batches} Space_V pack(s)...", done=0, total=total_batches)

        def build_batch_file(batch_number: int, batch_entries) -> tuple[int, dict]:
            batch_title = title_root if total_batches == 1 else f"{title_root} {batch_number:03d}"
            payload = minimal_space_v_payload_from_entries(
                batch_entries,
                title=batch_title,
                batch_index=batch_number,
                batch_total=total_batches,
                mission={
                    "kind": f"{space_label.lower()}_vocab_prerequisite",
                    "source_path": ctx["source_path"],
                    "source_title": ctx["source_title"],
                    "source_space": space_label,
                    "mission_id": ctx["mission_id"],
                    "queue_index": batch_number,
                    "queue_total": total_batches,
                    "created_at": utc_timestamp(),
                },
            )
            target_stem = safe_name_segment(batch_title, "Vocabulary", 72)
            if total_batches > 1:
                target_stem = f"{safe_name_segment(title_root, 'Vocabulary', 68)} {batch_number:03d}"
            target = mission_root / f"{target_stem}.Space_V"
            write_generated_space_v_lesson(target, payload)
            return batch_number, {
                "name": target.name,
                "path": server_data_relative(target),
                "size": int(target.stat().st_size),
                "study": summarize_lesson_study(target, username),
            }

        if batch_workers <= 1:
            batch_records = []
            for batch_number, batch_entries in enumerate(batches, start=1):
                emit(f"Building pack {batch_number}/{total_batches}...", done=batch_number - 1, total=total_batches)
                batch_records.append(build_batch_file(batch_number, batch_entries))
                emit(f"Pack {batch_number}/{total_batches} ready.", done=batch_number, total=total_batches)
        else:
            batch_records = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=batch_workers) as executor:
                futures = [
                    executor.submit(build_batch_file, batch_number, batch_entries)
                    for batch_number, batch_entries in enumerate(batches, start=1)
                ]
                completed_batches = 0
                for future in concurrent.futures.as_completed(futures):
                    record = future.result()
                    batch_records.append(record)
                    completed_batches += 1
                    emit(f"Pack {completed_batches}/{total_batches} ready.", done=completed_batches, total=total_batches)
        for _batch_number, record in sorted(batch_records, key=lambda item: item[0]):
            files.append(record)
        # Identity and durable lesson publication must finish before optional media warming.
        prefetch_space_v_images_for_entries(new_entries)
        append_learning_log(
            {
                "event": "vocab_mission_build",
                "user": username,
                "source_path": ctx["source_path"],
                "source_title": ctx["source_title"],
                "space": space_label,
                "mission_id": ctx["mission_id"],
                "new_words": len(new_entries),
                "files": len(files),
            }
        )
        emit(f"Vocabulary queue ready: {len(files)} Space_V pack(s).", progress_value=100)
        return {
            "source_path": ctx["source_path"],
            "source_title": ctx["source_title"],
            "space": space_label,
            "mission_id": ctx["mission_id"],
            "new_count": len(new_entries),
            "files": files,
            "pending_count": len(files),
        }


def archive_completed_mission_vocab_file(username: str, target: Path) -> dict:
    user_root = server_data_user_folder_path(username)
    immediate_root = (user_root / VOCAB_MISSION_PENDING_DIR).resolve()
    try:
        target.resolve().relative_to(immediate_root)
    except Exception:
        return {}
    if not target.is_file():
        return {}
    mission_root = target.parent
    now = time.localtime()
    day = time.strftime("%Y-%m-%d", now)
    clock = time.strftime("%H%M%S", now)
    archive_root = user_root / VOCAB_MISSION_ARCHIVE_DIR / day
    archive_root.mkdir(parents=True, exist_ok=True)
    dest = archive_root / f"{safe_name_segment(target.stem, 'Vocabulary', 66)} learned {clock}{target.suffix}"
    counter = 2
    while dest.exists():
        dest = archive_root / f"{safe_name_segment(target.stem, 'Vocabulary', 60)} learned {clock} {counter}{target.suffix}"
        counter += 1
    shutil.move(str(target), str(dest))
    try:
        current = mission_root
        while current != immediate_root and current.is_dir() and not any(current.iterdir()):
            parent = current.parent
            current.rmdir()
            current = parent
    except Exception:
        pass
    try:
        registry = read_user_vocab_registry(username)
        learned_keys = set((registry.get("words", {}) or {}).keys())
    except Exception:
        learned_keys = set()
    clear_lesson_metadata_cache()
    clear_server_data_list_cache_paths(
        [
            server_data_relative(user_root),
            server_data_relative(immediate_root),
            server_data_relative(mission_root),
            server_data_relative(archive_root.parent),
            server_data_relative(archive_root),
        ]
    )
    mark_server_data_manifest_dirty("vocab-mission-archive")
    return {
        "archived_path": server_data_relative(dest),
        "remaining_files": mission_file_records(
            mission_root,
            username,
            learned_keys=learned_keys,
            require_unlearned=True,
        ),
    }
