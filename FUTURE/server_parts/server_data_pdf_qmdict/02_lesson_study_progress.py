# Loaded by FUTURE.server_parts.07_server_data_pdf_qmdict into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def normalize_study_block(payload: dict) -> dict:
    source = payload.get("st") if payload.get("k") in {"ftg", "ftv", "ftp"} else payload.get("study")
    study = source if isinstance(source, dict) else {}
    users = study.get("users") if isinstance(study.get("users"), dict) else {}
    admins = study.get("admins") if isinstance(study.get("admins"), dict) else {}
    history = study.get("history") if isinstance(study.get("history"), list) else []
    return {
        "total": int(study.get("total", 0) or 0),
        "admin_total": int(study.get("admin_total", 0) or 0),
        "last": clean(study.get("last", "")),
        "users": {clean(key): value for key, value in users.items() if clean(key) and isinstance(value, dict)},
        "admins": {clean(key): value for key, value in admins.items() if clean(key) and isinstance(value, dict)},
        "history": [item for item in history if isinstance(item, dict)][-200:],
    }


def set_study_block(payload: dict, study: dict) -> None:
    if payload.get("k") in {"ftg", "ftv", "ftp"}:
        payload["st"] = study
    else:
        payload["study"] = study


def merge_study_user_rows(existing: dict | None, incoming: dict | None) -> tuple[dict, int]:
    current = existing if isinstance(existing, dict) else {}
    source = incoming if isinstance(incoming, dict) else {}
    current_count = max(0, space_w_int(current.get("count", 0), 0))
    incoming_count = max(0, space_w_int(source.get("count", 0), 0))
    if incoming_count <= 0 and clean(source.get("last", "")):
        incoming_count = 1
    current_dates = current.get("dates") if isinstance(current.get("dates"), list) else []
    incoming_dates = source.get("dates") if isinstance(source.get("dates"), list) else []
    dates = []
    for item in [*current_dates, *incoming_dates]:
        day = clean(item)[:10]
        if day and day not in dates:
            dates.append(day)
    current_last = clean(current.get("last", ""))
    incoming_last = clean(source.get("last", ""))
    merged = dict(current)
    merged["count"] = current_count + incoming_count
    merged["last"] = timestamp_latest_text(current_last, incoming_last)
    if dates:
        merged["dates"] = dates[-60:]
    return merged, incoming_count


def migrate_admin_learning_to_user(username: str) -> dict:
    username = normalize_username(username)
    if not username:
        return {"migrated_files": 0, "migrated_runs": 0}
    migrated_files = 0
    migrated_runs = 0
    checked_files = 0
    changed_paths: list[str] = []
    lesson_suffixes = {".space_w", ".space_v", ".space_q", ".space_p", ".space_s", ".space_l", ".txt"}
    with SERVER_DATA_LOCK:
        try:
            root = SERVER_DATA_ROOT.resolve()
            paths = list(root.rglob("*"))
        except Exception:
            paths = []
        for path in paths:
            try:
                if not path.is_file() or path.suffix.lower() not in lesson_suffixes:
                    continue
                rel_parts = path.resolve().relative_to(SERVER_DATA_ROOT.resolve()).parts
                if rel_parts and rel_parts[0] in {"Sound", "Structure", "Picture", "server_log"}:
                    continue
                checked_files += 1
                file_payload, structure_path = load_future_lesson_document(path)
                study = normalize_study_block(file_payload)
                admins = study.get("admins") if isinstance(study.get("admins"), dict) else {}
                admin_row = admins.get(username)
                if not isinstance(admin_row, dict):
                    continue
                users = study.setdefault("users", {})
                user_row = users.get(username) if isinstance(users.get(username), dict) else {}
                merged_row, incoming_count = merge_study_user_rows(user_row, admin_row)
                if incoming_count <= 0:
                    admins.pop(username, None)
                    study["admins"] = admins
                    set_study_block(file_payload, study)
                    write_future_lesson_document(path, file_payload, structure_path, refresh_manifest=False)
                    continue
                users[username] = merged_row
                admins.pop(username, None)
                study["users"] = users
                study["admins"] = admins
                study["total"] = max(0, space_w_int(study.get("total", 0), 0)) + incoming_count
                study["admin_total"] = max(0, space_w_int(study.get("admin_total", 0), 0) - incoming_count)
                if clean(admin_row.get("last", "")) and timestamp_order_key(admin_row.get("last", "")) > timestamp_order_key(study.get("last", "")):
                    study["last"] = clean(admin_row.get("last", ""))
                history = study.get("history") if isinstance(study.get("history"), list) else []
                history.append({
                    "u": username,
                    "at": utc_timestamp(),
                    "count": merged_row.get("count", 0),
                    "role": "user",
                    "source": "admin-demotion-migration",
                })
                study["history"] = history[-200:]
                set_study_block(file_payload, study)
                write_future_lesson_document(path, file_payload, structure_path, refresh_manifest=False)
                migrated_files += 1
                migrated_runs += incoming_count
                if len(changed_paths) < 24:
                    changed_paths.append(server_data_relative(path))
            except Exception as exc:
                stt_debug_log("admin_learning_migration_file_failed", user=username, path=str(path), error=str(exc))
                continue
    try:
        learning_stats = lesson_user_learning_summary(username, force=True)
    except Exception as exc:
        learning_stats = {"error": str(exc)}
    return {
        "migrated_files": migrated_files,
        "migrated_runs": migrated_runs,
        "checked_files": checked_files,
        "paths": changed_paths,
        "learning_stats": learning_stats,
    }


def lesson_payload_title(payload: dict, fallback: str = "") -> str:
    return clean(payload.get("t") or payload.get("title") or fallback)


def lesson_payload_node_count(payload: dict) -> int:
    if payload.get("k") == "ftv":
        nodes = payload.get("w")
    elif payload.get("kind") == "future_vocabulary_payload":
        nodes = payload.get("words")
    elif payload.get("k") == "ftp" or payload.get("kind") == "future_paragraph_payload":
        nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else payload.get("n")
        if isinstance(nodes, list):
            sentence_count = sum(
                len(node.get("children"))
                for node in nodes
                if isinstance(node, dict) and isinstance(node.get("children"), list)
            )
            return sentence_count if sentence_count else len(nodes)
    else:
        nodes = payload.get("n") if payload.get("k") == "ftg" else payload.get("nodes")
    return len(nodes) if isinstance(nodes, list) else 0


def lesson_payload_guidance_node_count(value: object) -> int:
    """Added 2026-07-20: count real Space_Q guidance cards without counting container objects."""
    if isinstance(value, list):
        return sum(lesson_payload_guidance_node_count(item) for item in value)
    if not isinstance(value, dict):
        return 0
    children = value.get("children") if isinstance(value.get("children"), list) else value.get("items")
    return 1 + (lesson_payload_guidance_node_count(children) if isinstance(children, list) else 0)


def lesson_payload_question_breakdown(payload: dict) -> dict:
    """Added 2026-07-20: separate direct Space_Q questions from their recursive guidance workload."""
    if payload.get("k") not in {"ftq"} and payload.get("kind") != "future_question_payload":
        return {"topics": 0, "direct": 0, "recursive": 0, "total": 0}
    nodes = payload.get("nodes")
    if not isinstance(nodes, list) and payload.get("k") == "ftq":
        nodes = payload.get("n")
    if not isinstance(nodes, list):
        return {"topics": 0, "direct": 0, "recursive": 0, "total": 0}
    topics = len([node for node in nodes if isinstance(node, dict)])
    direct = 0
    recursive = 0
    for node in nodes:
        if not isinstance(node, dict):
            continue
        cards = node.get("cards") if isinstance(node.get("cards"), dict) else {}
        questions = cards.get("questions") if isinstance(cards.get("questions"), list) else None
        if questions is None:
            questions = node.get("questions") if isinstance(node.get("questions"), list) else node.get("qs")
        if isinstance(questions, list):
            for question in questions:
                if not isinstance(question, dict) and not clean(question):
                    continue
                direct += 1
                recursive += 1
                if isinstance(question, dict):
                    guidance = question.get("guidance_tree") or question.get("guidanceTree") or question.get("guide_tree") or question.get("gt")
                    if isinstance(guidance, dict):
                        items = guidance.get("items") if isinstance(guidance.get("items"), list) else guidance.get("answers")
                        if isinstance(items, list):
                            recursive += lesson_payload_guidance_node_count(items)
    return {"topics": topics, "direct": direct, "recursive": recursive, "total": topics + recursive}


def lesson_payload_question_count(payload: dict) -> int:
    return max(0, int(lesson_payload_question_breakdown(payload).get("recursive", 0) or 0))


def lesson_payload_direct_question_count(payload: dict) -> int:
    return max(0, int(lesson_payload_question_breakdown(payload).get("direct", 0) or 0))


def lesson_payload_question_total_count(payload: dict) -> int:
    return max(0, int(lesson_payload_question_breakdown(payload).get("total", 0) or 0))


def lesson_payload_paragraph_count(payload: dict | None = None) -> int:
    source = payload if isinstance(payload, dict) else {}
    if source.get("k") != "ftp" and source.get("kind") != "future_paragraph_payload":
        return 0
    nodes = source.get("nodes") if isinstance(source.get("nodes"), list) else source.get("n")
    return len([node for node in nodes if isinstance(node, dict)]) if isinstance(nodes, list) else 0


def lesson_payload_sentence_breakdown(payload: dict | None = None) -> dict:
    source = payload if isinstance(payload, dict) else {}
    if source.get("k") != "ftg" and source.get("kind") != "future_translation_payload":
        return {"sentences": 0, "normal_sentences": 0, "train_sentences": 0}
    nodes = source.get("n") if source.get("k") == "ftg" else source.get("nodes")
    if not isinstance(nodes, list):
        return {"sentences": 0, "normal_sentences": 0, "train_sentences": 0}
    normal = len([node for node in nodes if isinstance(node, dict)])
    train = 0
    for node in nodes:
        if not isinstance(node, dict):
            continue
        raw = next((node.get(key) for key in ("xp", "practice", "extra_practice", "extraPractice", "supplemental", "training", "train") if node.get(key) is not None), [])
        if isinstance(raw, dict):
            raw = raw.get("nodes") or raw.get("items") or raw.get("entries") or []
        valid = 0
        if isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict):
                    continue
                en = clean(item.get("en") or item.get("e") or item.get("text") or item.get("sentence"))
                vi = clean(item.get("vi") or item.get("q") or item.get("mn") or item.get("meaning"))
                if en and vi:
                    valid += 1
        train += valid if valid else 1
    return {
        "sentences": normal + train,
        "normal_sentences": normal,
        "train_sentences": train,
    }


def empty_study_block() -> dict:
    return {"total": 0, "admin_total": 0, "last": "", "users": {}, "admins": {}, "history": []}


def normalize_study_user_row(row: dict | None) -> dict:
    source = row if isinstance(row, dict) else {}
    count = max(0, space_w_int(source.get("count", 0), 0))
    last = clean(source.get("last", ""))
    dates = []
    for item in source.get("dates") if isinstance(source.get("dates"), list) else []:
        day = clean(item)[:10]
        if day and day not in dates:
            dates.append(day)
    out = {"count": count, "last": last}
    if dates:
        out["dates"] = dates[-60:]
    return out


def merge_study_user_row_max(existing: dict | None, incoming: dict | None) -> dict:
    current = normalize_study_user_row(existing)
    source = normalize_study_user_row(incoming)
    count = max(max(0, space_w_int(current.get("count", 0), 0)), max(0, space_w_int(source.get("count", 0), 0)))
    last = timestamp_latest_text(current.get("last", ""), source.get("last", ""))
    dates = []
    for row in (current, source):
        for item in row.get("dates") if isinstance(row.get("dates"), list) else []:
            day = clean(item)[:10]
            if day and day not in dates:
                dates.append(day)
    merged = {"count": count, "last": last}
    if dates:
        merged["dates"] = dates[-60:]
    return merged


def merge_study_blocks_max(existing: dict | None, incoming: dict | None) -> dict:
    current = existing if isinstance(existing, dict) else {}
    source = incoming if isinstance(incoming, dict) else {}
    out = {
        "total": max(0, space_w_int(current.get("total", 0), 0), space_w_int(source.get("total", 0), 0)),
        "admin_total": max(0, space_w_int(current.get("admin_total", 0), 0), space_w_int(source.get("admin_total", 0), 0)),
        "last": timestamp_latest_text(current.get("last", ""), source.get("last", "")),
        "users": {},
        "admins": {},
        "history": [],
    }
    for bucket, total_key in (("users", "total"), ("admins", "admin_total")):
        merged_rows: dict[str, dict] = {}
        for rows in (
            current.get(bucket) if isinstance(current.get(bucket), dict) else {},
            source.get(bucket) if isinstance(source.get(bucket), dict) else {},
        ):
            for username, row in rows.items():
                normalized = normalize_username(username)
                if not normalized or not isinstance(row, dict):
                    continue
                merged_rows[normalized] = merge_study_user_row_max(merged_rows.get(normalized), row)
        out[bucket] = merged_rows
        row_total = sum(max(0, space_w_int(row.get("count", 0), 0)) for row in merged_rows.values())
        out[total_key] = max(out[total_key], row_total)
    history = []
    for item in [*(current.get("history") if isinstance(current.get("history"), list) else []), *(source.get("history") if isinstance(source.get("history"), list) else [])]:
        if isinstance(item, dict):
            history.append(item)
    out["history"] = history[-200:]
    return out


def study_block_has_counts(study: dict | None) -> bool:
    source = study if isinstance(study, dict) else {}
    if max(0, space_w_int(source.get("total", 0), 0)) or max(0, space_w_int(source.get("admin_total", 0), 0)):
        return True
    for bucket in ("users", "admins"):
        rows = source.get(bucket) if isinstance(source.get(bucket), dict) else {}
        if any(max(0, space_w_int(row.get("count", 0), 0)) for row in rows.values() if isinstance(row, dict)):
            return True
    return False


# Added 2026-07-24: one identity contract preserves link display context while all mutable state uses lesson_id.
def resolve_lesson_identity_contract(
    relative_path: str = "",
    username: str = "",
    admin: bool = False,
    requested_lesson_id: str = "",
    task_owner: str = "",
    strict: bool = False,
    require_file: bool = False,
) -> dict:
    raw = clean_path_value(relative_path)
    if not raw:
        return {}
    current_path = raw
    target = None
    effective = None
    identity_timing_ms = {}
    manifest_reader = globals().get("server_data_manifest_file_entry")
    manifest_entry = manifest_reader(raw) if callable(manifest_reader) else None
    requested_id_for_fast_path = clean(requested_lesson_id)[:240]
    try:
        raw_parts = [part.strip() for part in raw.split("/") if part.strip()]
        raw_top = clean(raw_parts[0]).lower() if raw_parts else ""
        normalized_user = normalize_username(username)
        manifest_path_allowed = bool(
            raw_parts
            and not any(part in {".", ".."} for part in raw_parts)
            and (
                raw_top == "common"
                or raw_top == normalized_user.lower()
                or (admin and bool(re.match(r"^[A-Za-z0-9_.-]{1,64}$", raw_parts[0])))
            )
        )
        fast_manifest_id = clean((manifest_entry or {}).get("lesson_id", ""))[:240] if isinstance(manifest_entry, dict) else ""
        direct_requested_file = bool(
            requested_id_for_fast_path
            and manifest_path_allowed
            and fast_manifest_id
            and fast_manifest_id.lower() == requested_id_for_fast_path.lower()
            and clean_path_value((manifest_entry or {}).get("path", "")).lower() == raw.lower()
            and clean((manifest_entry or {}).get("type", "")).lower() == "file"
            and not truthy((manifest_entry or {}).get("linked"), False)
            and not truthy((manifest_entry or {}).get("virtual"), False)
            and not truthy((manifest_entry or {}).get("source_missing"), False)
            and not clean((manifest_entry or {}).get("vault_entry_id", ""))
        )
        if direct_requested_file:
            # Added 2026-07-29: an exact revision-bound manifest identity is
            # already authorized above; avoid repeated folder creation and
            # component-by-component filesystem resolution under load.
            target = server_data_manifest_path(raw)
            effective = target
            identity_timing_ms["safe_path"] = 0
            identity_timing_ms["effective_path"] = 0
            current_path = raw
            identity_timing_ms["file_check"] = 0
        else:
            _identity_started = time.perf_counter()
            target = safe_server_data_path(raw, username, admin=admin)
            identity_timing_ms["safe_path"] = int((time.perf_counter() - _identity_started) * 1000)
            _identity_started = time.perf_counter()
            effective = server_data_effective_file_path(target, username=username, admin=admin)
            identity_timing_ms["effective_path"] = int((time.perf_counter() - _identity_started) * 1000)
            _identity_started = time.perf_counter()
            if effective.is_file():
                current_path = clean_path_value(server_data_relative(effective)) or raw
            elif require_file:
                raise RuntimeError("Selected lesson path does not resolve to a supported lesson file.")
            identity_timing_ms["file_check"] = int((time.perf_counter() - _identity_started) * 1000)
    except Exception:
        if strict:
            raise
        current_path = raw
    file_id = ""
    suffix = Path(current_path).suffix.lower()
    _identity_started = time.perf_counter()
    if not isinstance(manifest_entry, dict):
        manifest_entry = manifest_reader(current_path) if callable(manifest_reader) else None
    identity_timing_ms["manifest_entry"] = int((time.perf_counter() - _identity_started) * 1000)
    direct_manifest = bool(
        isinstance(manifest_entry, dict)
        and target is not None
        and effective == target
        and clean_path_value(manifest_entry.get("path", "")).lower() == current_path.lower()
        and not truthy(manifest_entry.get("linked"), False)
        and not truthy(manifest_entry.get("virtual"), False)
        and not clean(manifest_entry.get("vault_entry_id", ""))
    )
    if suffix != ".pdf" and suffix not in IMAGE_FILE_SUFFIXES:
        manifest_lesson_id = clean((manifest_entry or {}).get("lesson_id", ""))[:240] if direct_manifest else ""
        if manifest_lesson_id:
            file_id = manifest_lesson_id
        else:
            registry_ready = globals().get("server_database_lesson_identity_registry_ready")
            alias_reader = globals().get("server_database_lesson_file_id_for_path")
            authoritative = bool(callable(registry_ready) and callable(alias_reader) and registry_ready())
            if authoritative:
                _identity_started = time.perf_counter()
                file_id = clean(alias_reader(current_path))[:240]
                identity_timing_ms["alias_reader"] = int((time.perf_counter() - _identity_started) * 1000)
            else:
                file_id = clean((manifest_entry or {}).get("lesson_id", ""))[:240] if isinstance(manifest_entry, dict) else ""
    requested_id = clean(requested_lesson_id)[:240]
    if requested_id and file_id and requested_id != file_id:
        raise PermissionError("Lesson ID does not match the selected lesson path.")
    if requested_id and not file_id and strict and suffix.startswith(".space_"):
        raise RuntimeError("Canonical lesson ID is missing for this lesson path.")
    link_matcher = globals().get("server_database_folder_link_match")
    _identity_started = time.perf_counter()
    link_match = {} if direct_manifest else link_matcher(raw) if callable(link_matcher) else {}
    identity_timing_ms["link_match"] = int((time.perf_counter() - _identity_started) * 1000)
    link_root = clean_path_value((link_match or {}).get("link_path", ""))
    link_target_root = clean_path_value((link_match or {}).get("target", ""))
    is_link_context = bool(link_root or (raw and current_path and raw.lower() != current_path.lower()))
    normalized_task_owner = normalize_username(task_owner)
    if not normalized_task_owner:
        raw_top = clean(raw.split("/", 1)[0]).lower()
        normalized_user = normalize_username(username)
        normalized_task_owner = normalize_username(raw.split("/", 1)[0]) if raw_top and raw_top != "common" else normalized_user
    space_type = {
        ".space_v": "Space_V",
        ".space_b": "Space_V",
        ".space_w": "Space_W",
        ".space_q": "Space_Q",
        ".space_p": "Space_P",
        ".space_l": "Space_L",
        ".space_s": "Space_S",
        ".space_pdf": "Space_PDF",
        ".space_picture": "Space_Picture",
        ".pdf": "Space_PDF",
    }.get(suffix, "Space_Picture" if suffix in IMAGE_FILE_SUFFIXES else "")
    keys = []
    if file_id:
        keys.append(f"id:{file_id.lower()}")
    for candidate in (raw, current_path):
        clean_candidate = clean_path_value(candidate).lower()
        if clean_candidate and clean_candidate not in keys:
            keys.append(clean_candidate)
    return {
        "path": current_path,
        "legacy_path": raw,
        "requested_path": raw,
        "display_path": raw,
        "link_path": raw if is_link_context else "",
        "folder_link_path": link_root,
        "target_path": link_target_root or (current_path if is_link_context else ""),
        "source_path": current_path,
        "effective_path": current_path,
        "file_id": file_id,
        "lesson_id": file_id,
        "canonical_file_id": file_id,
        "task_owner": normalized_task_owner,
        "space_type": space_type,
        "index_keys": keys,
        "target": target,
        "effective_target": effective,
        "_manifest_entry": dict(manifest_entry) if isinstance(manifest_entry, dict) else None,
        "_identity_timing_ms": identity_timing_ms,
    }


def lesson_completion_identity(relative_path: str = "", username: str = "", admin: bool = False) -> dict:
    return resolve_lesson_identity_contract(relative_path, username, admin=admin)


def lesson_time_identity(relative_path: str = "", username: str = "", admin: bool = False) -> dict:
    info = lesson_completion_identity(relative_path, username, admin=admin)
    rel_path = clean_path_value(info.get("path", "")) or clean_path_value(relative_path)
    file_id = clean(info.get("file_id", ""))[:240]
    source = f"file_id:{file_id}" if file_id else (f"path:{rel_path.lower()}" if rel_path else "")
    legacy_rel_path = clean_path_value(relative_path)
    legacy_source = f"path:{legacy_rel_path.lower()}" if legacy_rel_path else ""
    return {
        **info,
        "source": source,
        "legacy_source": legacy_source,
    }


def learning_completion_log_index(force: bool = False) -> dict[str, dict]:
    signature = (server_database_generation("events"), 0)
    with LEARNING_COMPLETION_LOG_CACHE_LOCK:
        if not force and LEARNING_COMPLETION_LOG_CACHE.get("signature") == signature:
            cached = LEARNING_COMPLETION_LOG_CACHE.get("index")
            if isinstance(cached, dict):
                return cached
        # Added 2026-07-10: coalesce bursty Lesson Vault/Space Task cache misses so one thread parses the log.
        index: dict[str, dict] = {}
        seen_completion_events: set[tuple[str, str, str, str, str]] = set()
        rows = server_database_read_events("learning", limit=50000, keep_days=0)
        for row in rows:
                if not isinstance(row, dict) or clean(row.get("event", "")) != "lesson_complete":
                    continue
                rel_path = clean_path_value(row.get("path", ""))
                username = normalize_username(row.get("user", ""))
                if not rel_path or not username:
                    continue
                role = clean(row.get("role", "")).lower()
                is_admin_run = role == "admin" or max(0, space_w_int(row.get("admin_count", 0), 0)) > 0
                bucket = "admins" if is_admin_run else "users"
                total_key = "admin_total" if is_admin_run else "total"
                at = clean(row.get("at", ""))
                event_identity = clean(row.get("completion_run_id", "") or row.get("completionRunId", "") or row.get("client_completed_at", ""))
                index_keys = []
                file_id = clean(row.get("lesson_id") or row.get("file_id"))[:240]
                if not file_id:
                    alias_reader = globals().get("server_database_lesson_file_id_for_path")
                    file_id = clean(alias_reader(rel_path))[:240] if callable(alias_reader) else ""
                if file_id.lower().startswith("ftg-lesson-"):
                    index_keys.append(f"id:{file_id.lower()}")
                for candidate in (rel_path, clean_path_value(row.get("effective_path", ""))):
                    clean_candidate = clean_path_value(candidate).lower()
                    if clean_candidate and clean_candidate not in index_keys:
                        index_keys.append(clean_candidate)
                if event_identity:
                    event_scope = index_keys[0] if index_keys and index_keys[0].startswith("id:") else "|".join(index_keys)
                    event_key = (username.lower(), "admin" if is_admin_run else "user", event_scope, event_identity, clean(row.get("space_leaderboard_type", "")))
                    if event_key in seen_completion_events:
                        continue
                    seen_completion_events.add(event_key)
                for key in index_keys:
                    study = index.setdefault(key, empty_study_block())
                    rows = study.setdefault(bucket, {})
                    user_row = normalize_study_user_row(rows.get(username))
                    user_row["count"] = max(0, space_w_int(user_row.get("count", 0), 0)) + 1
                    user_row["last"] = timestamp_latest_text(user_row.get("last", ""), at)
                    dates = user_row.get("dates") if isinstance(user_row.get("dates"), list) else []
                    day = at[:10]
                    if day and day not in dates:
                        dates.append(day)
                    user_row["dates"] = dates[-60:]
                    rows[username] = user_row
                    study[total_key] = max(0, space_w_int(study.get(total_key, 0), 0)) + 1
                    study["last"] = timestamp_latest_text(study.get("last", ""), at)
                    history = study.get("history") if isinstance(study.get("history"), list) else []
                    history.append({"u": username, "at": at, "count": user_row["count"], "role": "admin" if is_admin_run else "user", "source": "learning-log-restore"})
                    study["history"] = history[-200:]
        LEARNING_COMPLETION_LOG_CACHE["signature"] = signature
        LEARNING_COMPLETION_LOG_CACHE["index"] = index
        return index


def learning_completion_study_for_paths(paths: list[str] | tuple[str, ...] | set[str], username: str = "", admin: bool = False) -> dict:
    index = learning_completion_log_index()
    merged = empty_study_block()
    seen_keys: set[str] = set()
    for path_value in paths:
        identity = lesson_completion_identity(path_value, username, admin=admin)
        keys = identity.get("index_keys") if isinstance(identity.get("index_keys"), list) else []
        if not keys:
            rel_path = clean_path_value(path_value)
            keys = [rel_path.lower()] if rel_path else []
        if not keys:
            continue
        for key in keys:
            clean_key = clean(key).lower()
            if not clean_key or clean_key in seen_keys:
                continue
            seen_keys.add(clean_key)
            study = index.get(clean_key)
            if isinstance(study, dict):
                merged = merge_study_blocks_max(merged, study)
    return merged if study_block_has_counts(merged) else {}


def learning_completion_user_row_for_paths(paths: list[str] | tuple[str, ...] | set[str], username: str = "", admin: bool = False) -> dict:
    # Added 2026-07-10: fetch one learner's completion from the RAM log index without merging whole path blocks.
    username = normalize_username(username)
    if not username:
        return {"count": 0, "last": ""}
    index = learning_completion_log_index()
    seen_keys: set[str] = set()
    best_count = 0
    best_last = ""
    for path_value in paths:
        identity = lesson_completion_identity(path_value, username, admin=admin)
        keys = identity.get("index_keys") if isinstance(identity.get("index_keys"), list) else []
        if not keys:
            rel_path = clean_path_value(path_value)
            keys = [rel_path.lower()] if rel_path else []
        for key in keys:
            clean_key = clean(key).lower()
            if not clean_key or clean_key in seen_keys:
                continue
            seen_keys.add(clean_key)
            study = index.get(clean_key)
            if not isinstance(study, dict):
                continue
            for bucket in ("users", "admins"):
                rows = study.get(bucket) if isinstance(study.get(bucket), dict) else {}
                row = merged_username_study_row(rows, username)
                best_count = max(best_count, int(row.get("count", 0) or 0))
                best_last = timestamp_latest_text(best_last, row.get("last", ""))
    return {"count": best_count, "last": best_last}


def backup_lesson_file_before_study_repair(target: Path, structure_path: Path | None = None) -> None:
    for path in [structure_path, target]:
        if path is None:
            continue
        try:
            source = Path(path)
            if source.is_file():
                backup = source.with_suffix(source.suffix + ".study.bak")
                if not backup.is_file():
                    shutil.copy2(source, backup)
        except Exception as exc:
            stt_debug_log("lesson_study_repair_backup_failed", path=str(path), error=str(exc))


def repair_lesson_study_from_learning_log(space_v_only: bool = True) -> dict:
    index = learning_completion_log_index(force=True)
    checked = restored = skipped = failed = 0
    paths: list[str] = []
    suffixes = {".space_v"} if space_v_only else {".space_w", ".space_v", ".space_q", ".space_p", ".space_s", ".space_l", ".txt"}
    with SERVER_DATA_LOCK:
        for rel_path, log_study in index.items():
            try:
                if clean(rel_path).lower().startswith("id:") or not clean_path_value(rel_path) or not study_block_has_counts(log_study):
                    skipped += 1
                    continue
                safe_user = next(iter((log_study.get("users") if isinstance(log_study.get("users"), dict) else {}) or {}), "")
                if not safe_user:
                    safe_user = next(iter((log_study.get("admins") if isinstance(log_study.get("admins"), dict) else {}) or {}), "")
                target = safe_server_data_path(rel_path, safe_user, admin=True)
                try:
                    effective = server_data_effective_file_path(target, username=safe_user, admin=True)
                except Exception:
                    effective = target
                if not effective.is_file() or effective.suffix.lower() not in suffixes:
                    skipped += 1
                    continue
                checked += 1
                payload, structure_path = load_future_lesson_document(effective)
                current_study = normalize_study_block(payload)
                merged = merge_study_blocks_max(current_study, log_study)
                if merged == current_study:
                    continue
                backup_lesson_file_before_study_repair(effective, structure_path)
                set_study_block(payload, merged)
                write_future_lesson_document(effective, payload, structure_path, refresh_manifest=False)
                restored += 1
                if len(paths) < 80:
                    paths.append(server_data_relative(effective))
            except Exception as exc:
                failed += 1
                stt_debug_log("lesson_study_repair_failed", path=rel_path, error=str(exc))
    if restored:
        clear_lesson_metadata_cache()
        with SERVER_DATA_LIST_CACHE_LOCK:
            SERVER_DATA_LIST_CACHE.clear()
        schedule_server_data_manifest_rebuild(0.5)
    result = {
        "checked": checked,
        "restored": restored,
        "skipped": skipped,
        "failed": failed,
        "paths": paths,
        "space_v_only": bool(space_v_only),
    }
    stt_debug_log("lesson_study_repair_done", **result)
    return result


def lesson_progress_space_for_path(relative_path: str = "", suffix: str = "") -> str:
    ext = clean(suffix).lower() or Path(clean_path_value(relative_path)).suffix.lower()
    if ext == ".space_v":
        return "Space_V"
    if ext == ".space_q":
        return "Space_Q"
    if ext == ".space_p":
        return "Space_P"
    if ext == ".space_s":
        return "Space_S"
    if ext == ".space_l":
        return "Space_L"
    if ext in {".pdf", ".space_pdf"}:
        return "Space_PDF"
    if ext == ".space_picture" or ext in IMAGE_FILE_SUFFIXES:
        return "Space_Picture"
    return "Space_W"


def lesson_progress_label(space: str = "") -> str:
    normalized = clean(space)
    if normalized == "Space_V":
        return "Words"
    if normalized == "Space_Q":
        return "Questions"
    if normalized == "Space_P":
        return "Sentences"
    if normalized == "Space_S":
        return "Sentences"
    if normalized == "Space_L":
        return "Sentences"
    if normalized == "Space_PDF":
        return "Pages"
    if normalized == "Space_Picture":
        return "Images"
    return "Nodes"


def file_cache_signature(path: Path) -> tuple[int, int]:
    try:
        stat = path.stat()
        return int(stat.st_mtime_ns), int(stat.st_size)
    except OSError:
        return 0, -1


def cached_payload_by_file(cache_key: str, path: Path, loader) -> dict:
    signature = file_cache_signature(path)
    with LESSON_PROGRESS_CACHE_LOCK:
        row = LESSON_PROGRESS_CACHE.get(cache_key)
        if isinstance(row, dict) and row.get("signature") == signature and isinstance(row.get("payload"), dict):
            return row["payload"]
    try:
        payload = loader()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    with LESSON_PROGRESS_CACHE_LOCK:
        LESSON_PROGRESS_CACHE[cache_key] = {
            "signature": signature,
            "payload": payload,
            "at": time.time(),
        }
        if len(LESSON_PROGRESS_CACHE) > 180:
            ordered = sorted(LESSON_PROGRESS_CACHE.items(), key=lambda item: float(item[1].get("at", 0) or 0))
            for old_key, _old_value in ordered[:40]:
                LESSON_PROGRESS_CACHE.pop(old_key, None)
    return payload


def invalidate_cached_payload(cache_key: str) -> None:
    with LESSON_PROGRESS_CACHE_LOCK:
        LESSON_PROGRESS_CACHE.pop(cache_key, None)


def read_cached_space_progress_file(username: str, space: str = "") -> dict:
    username = normalize_username(username)
    if not username:
        return {"version": 1, "states": {}}
    normalized_space = normalize_space_progress_space(space)
    if normalized_space == "Space_V" and callable(globals().get("read_space_v_progress_file")):
        return read_space_v_progress_file(username)
    lock = space_progress_user_lock(normalized_space, username)
    with lock:
        row = load_space_progress_store(normalized_space, username)
        payload = row.get("payload") if isinstance(row, dict) else {}
        return clone_space_progress_payload(payload)


def lesson_sort_timestamp(value: object = "") -> float:
    return timestamp_to_epoch(value)


def lesson_progress_states_for_user(username: str, space: str = "") -> list[dict]:
    username = normalize_username(username)
    if not username:
        return []
    try:
        payload = read_cached_space_progress_file(username, space)
        states = payload.get("states") if isinstance(payload, dict) and isinstance(payload.get("states"), dict) else {}
        return [item for item in states.values() if isinstance(item, dict)]
    except Exception:
        return []


def lesson_progress_done_count(record: dict, space: str = "", node_count_hint: int = 0) -> tuple[int, int]:
    source = record if isinstance(record, dict) else {}
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    file_id = clean(source.get("lesson_id") or source.get("file_id") or source.get("identity"))[:240]
    active_run = bool(source.get("activeRun") or source.get("active_run") or state.get("activeRun") or state.get("active_run"))
    total = max(0, space_w_int(source.get("nodeCount", source.get("node_count", state.get("nodeCount", state.get("node_count", node_count_hint)))), 0))
    if not total:
        total = max(0, int(node_count_hint or 0))
    node_index = max(0, space_w_int(source.get("nodeIndex", source.get("node_index", state.get("currentIndex", state.get("index", state.get("nodeIndex", state.get("node_index", 0)))))), 0))
    done = 0
    if space == "Space_V":
        learned_has_value = isinstance(state.get("learned"), list)
        learned = state.get("learned") if learned_has_value else []
        learned_done = len({clean(item) for item in learned if clean(item)})
        learned_done = max(
            learned_done,
            max(0, space_w_int(source.get("learnedCount", source.get("learned_count", 0)), 0)),
            max(0, space_w_int(state.get("learnedCount", state.get("learned_count", 0)), 0)),
        )
        # An explicit learned array is the authoritative current-run workload.
        # The resume pointer is navigation state, not completed-word progress;
        # using it here made login preload report 60% while /space-v/progress
        # correctly reported 0% for the same active run.
        done = learned_done if learned_has_value else node_index
        if not active_run and (space_v_registry_sync_has_completion_marker(source) or space_v_registry_sync_has_completion_marker({"state": state})):
            done = max(done, total)
    elif space == "Space_W" and callable(globals().get("space_progress_completion_marker")):
        work_counter = globals().get("space_w_progress_work_counts")
        if callable(work_counter):
            return work_counter(source)
        if space_progress_completion_marker(source, space) or space_progress_completion_marker({"state": state}, space):
            done = max(done, total)
    elif space == "Space_Q":
        explicit_question_total = next((state.get(key) for key in ("questionTotal", "totalQuestions") if key in state), None)
        explicit_question_done = next((state.get(key) for key in ("questionDone", "completedQuestions", "questionsDone") if key in state), None)
        question_total = max(0, space_w_int(explicit_question_total, 0))
        question_count = max(0, space_w_int(state.get("questionCount", 0), 0))
        pointer = max(0, space_w_int(state.get("nodePointer", 0), 0))
        queue = state.get("queue") if isinstance(state.get("queue"), list) else []
        completed_nodes = max(0, space_w_int(state.get("completedNodes", 0), 0))
        question_total_hint = max(0, int(node_count_hint or 0))
        if total and queue:
            completed_nodes = max(completed_nodes, total - len(queue) - 1)
        completed_nodes = max(completed_nodes, pointer - 1, node_index if node_index > 0 else 0)
        if not question_total:
            if question_total_hint > total:
                question_total = question_total_hint
            elif question_count:
                question_total = question_count * max(1, total)
        if question_total:
            if explicit_question_done is not None:
                done = max(0, space_w_int(explicit_question_done, 0))
            else:
                question_index = max(0, space_w_int(state.get("questionIndex", 0), 0))
                done = completed_nodes * max(1, question_count) + question_index
            if question_total_hint > question_total:
                done = round(done * question_total_hint / max(1, question_total))
                question_total = question_total_hint
            return max(0, min(done, question_total)), question_total
        if total and queue:
            done = max(done, total - len(queue) - 1)
        done = max(done, completed_nodes)
    elif space in {"Space_P", "Space_S", "Space_L"}:
        segment_total = max(0, space_w_int(state.get("totalSegments", state.get("segmentTotal", 0)), 0))
        segment_done = max(0, space_w_int(state.get("completedSegments", state.get("segmentDone", 0)), 0))
        if segment_total:
            return max(0, min(segment_done, segment_total)), segment_total
        token_total = max(0, space_w_int(state.get("totalTokens", state.get("tokenTotal", 0)), 0))
        token_done = max(0, space_w_int(state.get("completedTokens", state.get("tokenDone", 0)), 0))
        if token_total:
            return max(0, min(token_done, token_total)), token_total
        child_index = max(0, space_w_int(state.get("childIndex", 0), 0))
        done = max(0, space_w_int(state.get("completedNodes", 0), 0))
        done = max(done, node_index if node_index > 0 else 0)
        if child_index > 0:
            done = max(done, node_index)
    elif space in {"Space_PDF", "Space_Picture"}:
        raw_page = state.get("page", source.get("page"))
        if raw_page is None or clean(raw_page) == "":
            raw_node = source.get("currentNode", state.get("currentNode", source.get("nodeIndex", state.get("nodeIndex", 0))))
            one_based_node = space_w_int(source.get("nodeIndexBase", state.get("nodeIndexBase", 0)), 0) == 1 or space_w_int(source.get("version", 0), 0) >= 2
            raw_page = space_w_int(raw_node, 0) if one_based_node else space_w_int(raw_node, 0) + 1
        page = max(1, space_w_int(raw_page, 1))
        pages = max(total, space_w_int(state.get("pages", source.get("pages", total)), 0))
        if pages:
            return max(0, min(page, pages)), pages
        done = max(0, page)
    else:
        node_progress = state.get("nodeProgress") if isinstance(state.get("nodeProgress"), dict) else {}
        for item in node_progress.values():
            if not isinstance(item, dict):
                continue
            if item.get("nextPanelCanShow") or item.get("speakStepCompleted") or item.get("grammarStepCompleted") or item.get("reviewSpeakCompleted"):
                done += 1
        done = max(done, node_index if node_index > 0 else 0)
        if state.get("lessonCompletionSent") or state.get("reviewFinished"):
            done = max(done, total)
    if space in {"Space_Q", "Space_P", "Space_S", "Space_L"} and callable(globals().get("space_progress_completion_marker")):
        if space_progress_completion_marker(source, space) or space_progress_completion_marker({"state": state}, space):
            done = max(done, total)
    if total:
        done = max(0, min(done, total))
    return done, total


def lesson_progress_node_detail(record: dict) -> tuple[int, int]:
    source = record if isinstance(record, dict) else {}
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    total = max(0, space_w_int(state.get("totalNodes", source.get("nodeCount", state.get("nodeCount", 0))), 0))
    done = max(0, space_w_int(state.get("completedNodes", 0), 0))
    node_index = max(0, space_w_int(source.get("nodeIndex", state.get("currentIndex", state.get("index", state.get("nodeIndex", 0)))), 0))
    pointer = max(0, space_w_int(state.get("nodePointer", 0), 0))
    queue = state.get("queue") if isinstance(state.get("queue"), list) else []
    if total and queue:
        done = max(done, total - len(queue) - 1)
    done = max(done, pointer - 1, node_index if node_index > 0 else 0)
    if total:
        done = max(0, min(done, total))
    return done, total


# Added 2026-07-15: exposes durable completion runs independently from the latest run chart.
def lesson_progress_completed_runs(record: dict, space: str = "") -> int:
    source = record if isinstance(record, dict) else {}
    canonical_summary = globals().get("server_database_progress_completion_summary")
    if callable(canonical_summary):
        return max(0, space_w_int(canonical_summary(source, space).get("completed_runs", 0), 0))
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    lesson_source = state.get("lessonSource") if isinstance(state.get("lessonSource"), dict) else {}
    lesson_study = lesson_source.get("study") if isinstance(lesson_source.get("study"), dict) else {}
    lesson_progress = lesson_study.get("progress") if isinstance(lesson_study.get("progress"), dict) else {}
    runs = max(
        0,
        space_w_int(source.get("mine", 0), 0),
        space_w_int(source.get("completedRuns", source.get("completed_runs", 0)), 0),
        space_w_int(state.get("completedRuns", state.get("completed_runs", 0)), 0),
        space_w_int(lesson_study.get("mine", 0), 0),
        space_w_int(lesson_study.get("completedRuns", lesson_study.get("completed_runs", 0)), 0),
        space_w_int(lesson_progress.get("completedRuns", lesson_progress.get("completed_runs", 0)), 0),
    )
    marker_fn = globals().get("space_progress_completion_marker")
    if callable(marker_fn) and (marker_fn(source, space) or marker_fn({"state": state}, space)):
        runs = max(runs, 1)
    return runs


def lesson_progress_active_run_overrides_completion(
    progress_source: dict,
    progress_space: str,
    progress_hint: int = 0,
    completion_last: object = "",
) -> bool:
    source = progress_source if isinstance(progress_source, dict) else {}
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    if progress_space not in {"Space_V", "Space_W", "Space_Q", "Space_P", "Space_S", "Space_L"}:
        return False
    if source.get("reviewing") or source.get("reviewRun"):
        return False
    total = max(0, space_w_int(source.get("total", 0), 0), int(progress_hint or 0))
    done = max(0, space_w_int(source.get("done", 0), 0))
    percent = max(0, min(100, space_w_int(source.get("percent", 0), 0)))
    if not total or done >= total or percent >= 100:
        return False
    active_run = bool(source.get("activeRun") or source.get("active_run") or state.get("activeRun") or state.get("active_run"))
    run_id = clean(source.get("runId") or source.get("run_id") or state.get("runId") or state.get("run_id"))
    if active_run and run_id:
        # An identified New Study run owns the current chart even at 0/N.
        # Completion history remains a separate lifetime chip and must not overwrite it.
        return True
    progress_updated = lesson_sort_timestamp(source.get("updatedAt") or source.get("savedAt"))
    completion_updated = lesson_sort_timestamp(completion_last)
    return bool(
        (done > 0 or active_run)
        and (not completion_updated or progress_updated >= completion_updated)
    )


def build_lesson_progress_summary(best: dict, space: str = "", node_count_hint: int = 0) -> dict:
    done, total = lesson_progress_done_count(best, space, node_count_hint)
    percent = int(round((done / total) * 100)) if total else 0
    state = best.get("state") if isinstance(best.get("state"), dict) else {}
    reviewing = bool(best.get("reviewing") or best.get("reviewRun") or state.get("reviewing") or state.get("reviewRun"))
    active_run = bool(best.get("activeRun") or best.get("active_run") or state.get("activeRun") or state.get("active_run"))
    completed_runs = lesson_progress_completed_runs(best, space)
    marker_fn = globals().get("space_progress_completion_marker")
    completed = bool(callable(marker_fn) and (marker_fn(best, space) or marker_fn({"state": state}, space)))
    summary = {
        "space": space,
        "label": lesson_progress_label(space),
        "done": done,
        "total": total,
        "percent": max(0, min(100, percent)),
        "text": f"{done}/{total}" if total else "",
        "in_progress": bool(total and done < total and (done > 0 or active_run)),
        "activeRun": active_run,
        "reviewing": reviewing,
        "reviewRun": reviewing,
        "completed": completed,
        "previously_completed": bool(completed_runs and not completed),
        "previouslyCompleted": bool(completed_runs and not completed),
        "completed_runs": completed_runs,
        "completedRuns": completed_runs,
        "runId": clean(best.get("runId") or best.get("run_id") or state.get("runId") or state.get("run_id")),
        "root_node_total": max(0, space_w_int(best.get("rootNodeCount", state.get("rootNodeCount", 0)), 0)),
        "sentenceCount": max(0, space_w_int(best.get("sentenceCount", state.get("sentenceCount", 0)), 0)),
        "normalSentenceCount": max(0, space_w_int(best.get("normalSentenceCount", state.get("normalSentenceCount", 0)), 0)),
        "trainSentenceCount": max(0, space_w_int(best.get("trainSentenceCount", state.get("trainSentenceCount", 0)), 0)),
        "savedAt": clean(best.get("savedAt", "")),
        "updatedAt": clean(best.get("updatedAt", "")),
    }
    node_done, node_total = lesson_progress_node_detail(best)
    if node_total:
        summary.update({
            "node_done": node_done,
            "node_total": node_total,
            "nodes_text": f"{node_done}/{node_total}",
        })
    return summary


def lesson_progress_summary(username: str, relative_path: str = "", suffix: str = "", node_count_hint: int = 0) -> dict:
    username = normalize_username(username)
    rel_path = clean_path_value(relative_path)
    if not username or not rel_path:
        return {}
    space = lesson_progress_space_for_path(rel_path, suffix)
    rel_lower = rel_path.lower()
    best = None
    for record in lesson_progress_states_for_user(username, space):
        state = record.get("state") if isinstance(record.get("state"), dict) else {}
        record_paths = [
            record.get("path", ""),
            record.get("legacy_path", ""),
            state.get("path", ""),
            state.get("effective_path", ""),
            state.get("effectivePath", ""),
            state.get("link_target", ""),
            state.get("linkTarget", ""),
            state.get("linked_path", ""),
            state.get("linkedPath", ""),
        ]
        record_path_keys = {clean_path_value(value).lower() for value in record_paths if clean_path_value(value)}
        if rel_lower not in record_path_keys:
            continue
        if best is None or lesson_sort_timestamp(record.get("updatedAt") or record.get("savedAt")) >= lesson_sort_timestamp(best.get("updatedAt") or best.get("savedAt")):
            best = record
    if not best:
        return {}
    return build_lesson_progress_summary(best, space, node_count_hint)


LESSON_PROGRESS_INDEX_CACHE: dict[str, dict] = {}
LESSON_PROGRESS_INDEX_CACHE_LOCK = threading.RLock()
LESSON_PROGRESS_INDEX_SIGNATURE_TTL_SECONDS = 2.0


# Added 2026-07-15: progress saves invalidate one learner's Lesson Vault index instead of forcing list reads to stat every file.
def invalidate_lesson_progress_index_cache(username: str = "") -> None:
    cache_key = normalize_username(username).lower()
    if not cache_key:
        return
    with LESSON_PROGRESS_INDEX_CACHE_LOCK:
        LESSON_PROGRESS_INDEX_CACHE.pop(cache_key, None)


# Added 2026-07-20: task/list response caches use one learner-local revision instead of global progress invalidation.
def lesson_progress_index_runtime_token(username: str = "") -> tuple:
    cache_key = normalize_username(username).lower()
    if not cache_key:
        return ()
    with LESSON_PROGRESS_INDEX_CACHE_LOCK:
        cached = LESSON_PROGRESS_INDEX_CACHE.get(cache_key)
        if not isinstance(cached, dict):
            return ("missing",)
        return (
            "ram",
            float(cached.get("updated_at", 0.0) or 0.0),
            cached.get("signature"),
        )

# Added 2026-07-15: Space progress saves patch the hot per-user Lesson Vault index without forcing the next list read to reparse JSON.
def update_lesson_progress_index_cache_record(username: str = "", space: str = "", record: dict | None = None) -> bool:
    username = normalize_username(username)
    cache_key = username.lower()
    source = record if isinstance(record, dict) else {}
    if not cache_key or not source:
        return False
    normalized_space = clean(space or lesson_progress_space_for_path(source.get("path", ""))) or ""
    record_path = clean_path_value(source.get("path", ""))
    if not normalized_space or not record_path:
        return False
    state = source.get("state") if isinstance(source.get("state"), dict) else {}
    file_id = clean(source.get("lesson_id") or source.get("file_id") or source.get("identity"))[:240]
    alias_paths = [
        record_path,
        clean_path_value(source.get("legacy_path", "")),
        clean_path_value(state.get("path", "")),
        clean_path_value(state.get("effective_path", "")),
        clean_path_value(state.get("effectivePath", "")),
        clean_path_value(state.get("link_target", "")),
        clean_path_value(state.get("linkTarget", "")),
        clean_path_value(state.get("linked_path", "")),
        clean_path_value(state.get("linkedPath", "")),
    ]
    with LESSON_PROGRESS_INDEX_CACHE_LOCK:
        cached = LESSON_PROGRESS_INDEX_CACHE.get(cache_key)
        index = cached.get("index") if isinstance(cached, dict) else None
        if not isinstance(index, dict):
            return False
        seen: set[str] = set()
        if file_id.lower().startswith("ftg-lesson-"):
            index[(normalized_space, f"id:{file_id.lower()}")] = source
        for alias_path in alias_paths:
            alias_path = clean_path_value(alias_path)
            alias_key = alias_path.lower()
            if not alias_path or alias_key in seen:
                continue
            seen.add(alias_key)
            candidate_space = lesson_progress_space_for_path(alias_path) or normalized_space
            index[(normalized_space, alias_key)] = source
            index[(candidate_space, alias_key)] = source
            if normalized_space == "Space_PDF":
                index[("Space_Picture" if candidate_space == "Space_PDF" else "Space_PDF", alias_key)] = source
        cached["updated_at"] = time.time()
        cached["checked_at"] = time.time()
        return True


# Added 2026-07-15: keeps Lesson Vault/Space Task list loads from reparsing every progress JSON for hot users.
def lesson_progress_index_signature(username: str) -> tuple:
    username = normalize_username(username)
    # Added 2026-07-22: SQLite is authoritative; user generation invalidates RAM without statting five legacy exports.
    return (
        "postgres-progress-v1",
        username.lower(),
        server_database_user_generation("progress", username),
    )


def lesson_progress_record_index(username: str) -> dict[tuple[str, str], dict]:
    username = normalize_username(username)
    if not username:
        return {}
    cache_key = username.lower()
    now = time.time()
    with LESSON_PROGRESS_INDEX_CACHE_LOCK:
        cached = LESSON_PROGRESS_INDEX_CACHE.get(cache_key)
        if (
            isinstance(cached, dict)
            and isinstance(cached.get("index"), dict)
            and now - float(cached.get("checked_at") or 0.0) <= LESSON_PROGRESS_INDEX_SIGNATURE_TTL_SECONDS
        ):
            return cached["index"]
    signature = lesson_progress_index_signature(username)
    with LESSON_PROGRESS_INDEX_CACHE_LOCK:
        cached = LESSON_PROGRESS_INDEX_CACHE.get(cache_key)
        if isinstance(cached, dict) and cached.get("signature") == signature and isinstance(cached.get("index"), dict):
            cached["checked_at"] = now
            return cached["index"]
    index: dict[tuple[str, str], dict] = {}
    progress_spaces = ("Space_W", "Space_Q", "Space_V", "Space_P", "Space_PDF")
    batched_payloads = None
    batch_loader = globals().get("server_database_load_progress_payloads")
    if callable(batch_loader):
        try:
            batched_payloads = batch_loader(username, progress_spaces)
            seeder = globals().get("seed_space_progress_store_payload")
            if callable(seeder) and isinstance(batched_payloads, dict):
                for space in progress_spaces:
                    seeder(space, username, batched_payloads.get(space) or default_space_progress_payload())
        except Exception:
            batched_payloads = None
    for space in progress_spaces:
        try:
            if isinstance(batched_payloads, dict) and space in batched_payloads:
                payload = normalize_space_progress_payload(batched_payloads.get(space))
            else:
                payload = read_cached_space_progress_file(username, space)
            states = payload.get("states") if isinstance(payload, dict) and isinstance(payload.get("states"), dict) else {}
        except Exception:
            states = {}
        for record in states.values():
            if not isinstance(record, dict):
                continue
            record_path = clean_path_value(record.get("path", ""))
            if not record_path:
                continue
            index_keys: list[tuple[str, str]] = []
            state = record.get("state") if isinstance(record.get("state"), dict) else {}
            file_id = clean(record.get("lesson_id") or record.get("file_id") or record.get("identity"))[:240]
            if file_id.lower().startswith("ftg-lesson-"):
                index_keys.append((space, f"id:{file_id.lower()}"))
            alias_paths = [
                record_path,
                clean_path_value(record.get("legacy_path", "")),
                clean_path_value(state.get("path", "")),
                clean_path_value(state.get("effective_path", "")),
                clean_path_value(state.get("effectivePath", "")),
                clean_path_value(state.get("link_target", "")),
                clean_path_value(state.get("linkTarget", "")),
                clean_path_value(state.get("linked_path", "")),
                clean_path_value(state.get("linkedPath", "")),
            ]
            seen_aliases: set[str] = set()
            for alias_path in alias_paths:
                alias_path = clean_path_value(alias_path)
                alias_key = alias_path.lower()
                if not alias_path or alias_key in seen_aliases:
                    continue
                seen_aliases.add(alias_key)
                index_keys.append((space, alias_key))
                alias_space = lesson_progress_space_for_path(alias_path)
                if alias_space and alias_space != space:
                    index_keys.append((alias_space, alias_key))
                if space == "Space_PDF":
                    # Added 2026-07-15: one PDF/Picture progress file serves both page and image rows without a second JSON read.
                    index_keys.append(("Space_Picture" if alias_space == "Space_PDF" else "Space_PDF", alias_key))
            for key in index_keys:
                previous = index.get(key)
                if previous is None or lesson_sort_timestamp(record.get("updatedAt") or record.get("savedAt")) >= lesson_sort_timestamp(previous.get("updatedAt") or previous.get("savedAt")):
                    index[key] = record
    with LESSON_PROGRESS_INDEX_CACHE_LOCK:
        LESSON_PROGRESS_INDEX_CACHE[cache_key] = {
            "signature": signature,
            "index": index,
            "updated_at": time.time(),
            "checked_at": time.time(),
        }
    return index


# Added 2026-07-15: gives the frontend one compact per-user progress snapshot at login so Lesson Vault/Space Task can render locally.
def lesson_progress_snapshot_for_client(username: str = "", trace: dict | None = None) -> dict:
    username = normalize_username(username)
    if not username:
        return {"username": "", "items": {}, "count": 0, "updated_at": ""}
    cache_key = (username.lower(), login_preload_cache_generation(username))
    cache = globals().setdefault("LESSON_PROGRESS_SNAPSHOT_CACHE", {})
    with SERVER_DATA_LIST_CACHE_LOCK:
        cached = cache.get(cache_key) if isinstance(cache, dict) else None
        if isinstance(cached, dict):
            return copy.deepcopy(cached)
    try:
        index_started = time.perf_counter()
        progress_index = lesson_progress_record_index(username)
        if isinstance(trace, dict):
            trace["progress_index_ms"] = round((time.perf_counter() - index_started) * 1000, 3)
    except Exception:
        progress_index = {}
        if isinstance(trace, dict):
            trace["progress_index_ms"] = 0.0
    try:
        time_started = time.perf_counter()
        time_index = lesson_time_state_index(username)
        if isinstance(trace, dict):
            trace["time_index_ms"] = round((time.perf_counter() - time_started) * 1000, 3)
    except Exception:
        time_index = {}
        if isinstance(trace, dict):
            trace["time_index_ms"] = 0.0
    items: dict[str, dict] = {}
    items_started = time.perf_counter()
    for key, record in (progress_index or {}).items():
        if not isinstance(key, tuple) or len(key) < 2 or not isinstance(record, dict):
            continue
        space = clean(key[0] or lesson_progress_space_for_path(record.get("path", "")))
        path_key = clean_path_value(key[1] or "")
        if not space or not path_key:
            continue
        state = record.get("state") if isinstance(record.get("state"), dict) else {}
        display_path = clean_path_value(
            record.get("path", "")
            or state.get("path", "")
            or state.get("effective_path", "")
            or state.get("effectivePath", "")
            or path_key
        )
        if not display_path:
            continue
        if space in {"Space_PDF", "Space_Picture"}:
            path_space = lesson_progress_space_for_path(display_path)
            if path_space in {"Space_PDF", "Space_Picture"}:
                space = path_space
        summary = build_lesson_progress_summary(record, space, 0)
        completed_runs = lesson_progress_completed_runs(record, space)
        if not summary.get("total") and completed_runs <= 0:
            continue
        saved_at = clean(record.get("savedAt", "") or state.get("savedAt", ""))
        updated_at = clean(record.get("updatedAt", "") or state.get("updatedAt", "") or saved_at)
        updated_ts = lesson_sort_timestamp(updated_at or saved_at)
        current = items.get(path_key)
        if current and lesson_sort_timestamp(current.get("updatedAt") or current.get("savedAt")) > updated_ts:
            continue
        study = {
            "title": clean(record.get("title", "") or state.get("title", "")),
            "space": space,
            "progress": summary,
            "progress_text": clean(summary.get("text", "")),
            "progress_percent": int(summary.get("percent", 0) or 0),
            "mine": completed_runs,
            "completedRuns": completed_runs,
            "completed_runs": completed_runs,
            "savedAt": saved_at,
            "updatedAt": updated_at,
        }
        # Added 2026-07-22: fresh login restores compact lesson time without a per-file request or filesystem scan.
        time_aliases = [
            path_key,
            record.get("path", ""),
            record.get("legacy_path", ""),
            state.get("path", ""),
            state.get("effective_path", ""),
            state.get("effectivePath", ""),
            state.get("link_target", ""),
            state.get("linkTarget", ""),
            state.get("linked_path", ""),
            state.get("linkedPath", ""),
        ]
        record_file_id = clean(record.get("file_id") or record.get("lesson_id") or record.get("identity"))[:240]
        direct_time_row = time_index.get(f"id:{record_file_id.lower()}") if record_file_id else None
        if isinstance(direct_time_row, dict):
            time_summary = {
                "seconds": max(0, space_w_int(direct_time_row.get("seconds", 0), 0)),
                "ticks": max(0, space_w_int(direct_time_row.get("ticks", 0), 0)),
                "updatedAt": clean(direct_time_row.get("updatedAt", "")),
            }
        elif record_file_id and isinstance(time_index.get("__canonical_v2__"), dict):
            time_summary = {"seconds": 0, "ticks": 0, "updatedAt": ""}
        else:
            time_summary = lesson_time_summary_from_index(time_index, username, display_path, time_aliases)
        if int(time_summary.get("seconds", 0) or 0) > 0:
            study["time"] = time_summary
            study["time_seconds"] = int(time_summary.get("seconds", 0) or 0)
            study["time_ticks"] = int(time_summary.get("ticks", 0) or 0)
        if summary.get("total"):
            study["nodes"] = int(summary.get("root_node_total") or summary.get("node_total") or summary.get("total", 0) or 0)
        item = {
            "path": display_path,
            "space": space,
            "study": study,
            "progress": summary,
            "savedAt": saved_at,
            "updatedAt": updated_at,
        }
        if record_file_id:
            item["lesson_id"] = record_file_id
            item["file_id"] = record_file_id
        if space in {"Space_PDF", "Space_Picture"}:
            pinned_pages = record.get("pinnedPages") if isinstance(record.get("pinnedPages"), list) else state.get("pinnedPages")
            recent_pages = record.get("recentPages") if isinstance(record.get("recentPages"), list) else state.get("recentPages")
            item["pdf_progress"] = {
                "path": display_path,
                "title": clean(record.get("title", "") or state.get("title", "")),
                "page": max(1, space_w_int(record.get("page", state.get("page", 1)), 1)),
                "pages": max(0, space_w_int(record.get("pages", state.get("pages", 0)), 0)),
                "pinnedPages": [max(1, space_w_int(value, 0)) for value in pinned_pages if space_w_int(value, 0) > 0][:240] if isinstance(pinned_pages, list) else [],
                "pinnedPagesUpdatedAt": clean(record.get("pinnedPagesUpdatedAt") or state.get("pinnedPagesUpdatedAt")),
                "recentPages": [max(1, space_w_int(value, 0)) for value in recent_pages if space_w_int(value, 0) > 0][:40] if isinstance(recent_pages, list) else [],
                "savedAt": saved_at,
                "updatedAt": updated_at,
                "state": {
                    "mode": clean(state.get("mode", "pdf")) or "pdf",
                    "page": max(1, space_w_int(record.get("page", state.get("page", 1)), 1)),
                    "pages": max(0, space_w_int(record.get("pages", state.get("pages", 0)), 0)),
                    "pinnedPages": [max(1, space_w_int(value, 0)) for value in pinned_pages if space_w_int(value, 0) > 0][:240] if isinstance(pinned_pages, list) else [],
                    "pinnedPagesUpdatedAt": clean(record.get("pinnedPagesUpdatedAt") or state.get("pinnedPagesUpdatedAt")),
                },
            }
        items[path_key] = item
    if isinstance(trace, dict):
        trace["items_ms"] = round((time.perf_counter() - items_started) * 1000, 3)
    payload = {
        "username": username,
        "items": items,
        "count": len(items),
        "updated_at": time.time(),
    }
    cache_started = time.perf_counter()
    with SERVER_DATA_LIST_CACHE_LOCK:
        cache[cache_key] = copy.deepcopy(payload)
        if len(cache) > 256:
            for old_key in list(cache.keys())[:64]:
                if old_key != cache_key:
                    cache.pop(old_key, None)
    if isinstance(trace, dict):
        trace["cache_ms"] = round((time.perf_counter() - cache_started) * 1000, 3)
    return copy.deepcopy(payload)

def lesson_progress_best_from_index(progress_index: dict[tuple[str, str], dict], keys: list[tuple[str, str]]) -> dict:
    best = {}
    for key in keys:
        candidate = progress_index.get(key)
        if not isinstance(candidate, dict):
            continue
        if not best or lesson_sort_timestamp(candidate.get("updatedAt") or candidate.get("savedAt")) >= lesson_sort_timestamp(best.get("updatedAt") or best.get("savedAt")):
            best = candidate
    return best


def lesson_progress_summary_from_index(
    progress_index: dict[tuple[str, str], dict] | None,
    username: str,
    relative_path: str = "",
    suffix: str = "",
    node_count_hint: int = 0,
    alias_paths: object = None,
    strict_paths: bool = False,
    lesson_id: str = "",
) -> dict:
    rel_path = clean_path_value(relative_path)
    if not rel_path:
        return {}
    space = lesson_progress_space_for_path(rel_path, suffix)
    if isinstance(progress_index, dict):
        lookup_keys = []
        canonical_id = clean(lesson_id)[:240]
        if canonical_id.lower().startswith("ftg-lesson-"):
            lookup_keys.append((space, f"id:{canonical_id.lower()}"))
            direct = lesson_progress_best_from_index(progress_index, lookup_keys)
            if isinstance(direct, dict):
                return build_lesson_progress_summary(direct, space, node_count_hint)
        path_candidates = [rel_path]
        if isinstance(alias_paths, (list, tuple, set)):
            path_candidates.extend(alias_paths)
        elif clean(alias_paths):
            path_candidates.append(alias_paths)
        seen_paths: set[str] = set()
        for candidate in path_candidates:
            candidate_path = clean_path_value(candidate)
            candidate_key = candidate_path.lower()
            if not candidate_path or candidate_key in seen_paths:
                continue
            seen_paths.add(candidate_key)
            candidate_space = lesson_progress_space_for_path(candidate_path, suffix) or space
            lookup_keys.append((candidate_space, candidate_key))
            if candidate_space != space:
                lookup_keys.append((space, candidate_key))
            alias_reader = globals().get("server_database_lesson_file_id_for_path") if not canonical_id else None
            file_id = clean(alias_reader(candidate_path))[:240] if callable(alias_reader) else ""
            if file_id:
                lookup_keys.append((candidate_space, f"id:{file_id.lower()}"))
                if candidate_space != space:
                    lookup_keys.append((space, f"id:{file_id.lower()}"))
            if not strict_paths and not canonical_id:
                identity = lesson_completion_identity(candidate_path, username, admin=True)
                identity_file_id = clean(identity.get("file_id", ""))[:240]
                if identity_file_id:
                    lookup_keys.append((candidate_space, f"id:{identity_file_id.lower()}"))
                    if candidate_space != space:
                        lookup_keys.append((space, f"id:{identity_file_id.lower()}"))
                identity_path = clean_path_value(identity.get("path", ""))
                identity_key = identity_path.lower()
                if identity_path and identity_key not in seen_paths:
                    seen_paths.add(identity_key)
                    lookup_keys.append((candidate_space, identity_key))
                    if candidate_space != space:
                        lookup_keys.append((space, identity_key))
        best = lesson_progress_best_from_index(progress_index, lookup_keys)
        if not isinstance(best, dict):
            return {}
        return build_lesson_progress_summary(best, space, node_count_hint)
    best = None
    if not isinstance(best, dict):
        return lesson_progress_summary(username, rel_path, suffix, node_count_hint)
    return build_lesson_progress_summary(best, space, node_count_hint)


def lesson_space_v_folder_progress_from_index(
    progress_index: dict[tuple[str, str], dict] | None,
    relative_path: str = "",
    word_count_hint: int = 0,
) -> dict:
    folder_path = clean_path_value(relative_path)
    if not isinstance(progress_index, dict) or not folder_path:
        return {}
    folder_key = folder_path.lower().rstrip("/") + "/"
    records: dict[str, dict] = {}
    for key, record in progress_index.items():
        if not isinstance(key, tuple) or len(key) != 2 or key[0] != "Space_V":
            continue
        record_path_key = clean_path_value(key[1]).lower()
        if not record_path_key.startswith(folder_key):
            continue
        record_path = clean_path_value(record.get("path", "")) or record_path_key
        if Path(record_path).suffix.lower() != ".space_v":
            continue
        previous = records.get(record_path.lower())
        if previous is None or lesson_sort_timestamp(record.get("updatedAt") or record.get("savedAt")) >= lesson_sort_timestamp(previous.get("updatedAt") or previous.get("savedAt")):
            records[record_path.lower()] = record
    if not records:
        return {}
    done = 0
    total = 0
    latest = ""
    for record in records.values():
        record_done, record_total = lesson_progress_done_count(record, "Space_V", 0)
        done += max(0, record_done)
        total += max(0, record_total)
        stamp = clean(record.get("updatedAt") or record.get("savedAt"))
        if lesson_sort_timestamp(stamp) >= lesson_sort_timestamp(latest):
            latest = stamp
    total = max(total, max(0, space_w_int(word_count_hint, 0)))
    if not total:
        return {}
    done = max(0, min(done, total))
    percent = int(round((done / total) * 100)) if total else 0
    return {
        "space": "Space_V",
        "label": lesson_progress_label("Space_V"),
        "done": done,
        "total": total,
        "percent": max(0, min(100, percent)),
        "text": f"{done}/{total}",
        "in_progress": bool(done > 0 and done < total),
        "savedAt": latest,
        "updatedAt": latest,
        "folder": True,
        "file_count": len(records),
    }


def lesson_time_path(username: str) -> Path:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    return user_folder_path(username) / LESSON_TIME_FILE_NAME


LESSON_LAST_FILE_NAME = "lesson_last_file.json"
# Updated 2026-07-15: keep last-file writes in RAM and batch disk flushes with the shared 10s progress cadence.
LESSON_LAST_FILE_FLUSH_DELAY_SECONDS = 10.0
LESSON_LAST_FILE_LOCK = threading.RLock()
LESSON_LAST_FILE_CACHE: dict[str, dict] = {}
LESSON_LAST_FILE_USER_LOCKS: dict[str, threading.RLock] = {}
LESSON_LAST_FILE_DIRTY_USERS: set[str] = set()
LESSON_LAST_FILE_FLUSH_TIMER: threading.Timer | None = None
LESSON_LAST_FILE_REQUEST_CACHE: dict[str, dict] = {}
LESSON_LAST_FILE_REQUEST_CACHE_MAX_USERS = 512


def lesson_last_file_path(username: str) -> Path:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    return user_folder_path(username) / LESSON_LAST_FILE_NAME


def normalize_lesson_last_file_path(path_value: str = "", username: str = "") -> str:
    raw = clean(path_value)
    if not raw:
        return ""
    # Updated 2026-07-08: last-file navigation must remember the clicked Lesson Vault link,
    # while progress storage may still resolve that link to the effective lesson file.
    display_path = clean_path_value(raw)
    if not display_path:
        return ""
    try:
        target = safe_server_data_path(display_path, username, admin=is_admin_user(username))
        effective_target = server_data_effective_file_path(target, username=username, admin=is_admin_user(username))
        if target.exists() or (effective_target and effective_target.is_file() and is_lesson_file(effective_target)):
            return server_data_relative(target) or display_path
    except Exception:
        pass
    return display_path


def normalize_lesson_last_file_row(row: dict | str | None, username: str = "", trusted_persisted: bool = False) -> dict:
    source = row if isinstance(row, dict) else {"path": row}
    display_path = clean_path_value(source.get("path", ""))
    alias_reader = globals().get("server_database_lesson_file_id_for_path")
    file_id = clean(source.get("lesson_id") or source.get("file_id") or source.get("identity"))[:240]
    path_value = ""
    display_contract = {}
    # 2026-07-24: canonical ID + indexed alias is the hot path; only legacy rows
    # without a verified ID need the filesystem/identity contract resolver.
    if trusted_persisted and display_path:
        path_value = display_path
    elif file_id.lower().startswith("ftg-lesson-") and display_path and callable(alias_reader):
        if clean(alias_reader(display_path)) == file_id:
            path_value = display_path
    if not path_value and display_path:
        try:
            display_contract = resolve_lesson_identity_contract(
                display_path,
                username,
                admin=is_admin_user(username),
                requested_lesson_id=file_id,
                task_owner=source.get("task_owner", ""),
                strict=False,
            )
        except Exception:
            display_contract = {}
    contract_file_id = clean(display_contract.get("lesson_id", ""))[:240]
    display_context_valid = bool(
        display_contract.get("effective_path")
        and (not file_id or not contract_file_id or contract_file_id == file_id)
    )
    if display_context_valid:
        path_value = display_path
        file_id = file_id or contract_file_id
    if not path_value:
        path_value = normalize_lesson_last_file_path(display_path, username)
    if not path_value:
        return {}
    if not file_id and callable(alias_reader):
        file_id = clean(alias_reader(path_value))[:240]
    manifest_reader = globals().get("server_data_manifest_file_entry")
    if file_id and not display_context_valid and callable(manifest_reader) and not isinstance(manifest_reader(path_value), dict):
        current_path_reader = globals().get("server_database_lesson_current_path")
        current_path = clean_path_value(current_path_reader(file_id)) if callable(current_path_reader) else ""
        if current_path:
            path_value = current_path
    parent = clean_path_value(source.get("parentPath") or source.get("parent") or "")
    if not parent:
        slash = path_value.rfind("/")
        parent = path_value[:slash] if slash > 0 else ""
    page_value = max(0, space_w_int(source.get("page") or source.get("currentPage") or source.get("lastPage") or 0, 0))
    pages_value = max(0, space_w_int(source.get("pages") or source.get("totalPages") or source.get("nodeCount") or 0, 0))
    if (not page_value or not pages_value) and path_value.lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".jfif", ".webp", ".bmp", ".gif", ".tif", ".tiff")):
        try:
            progress_snapshot = {}
            if "space_pdf_progress_snapshot_for_path" in globals():
                progress_snapshot = space_pdf_progress_snapshot_for_path(username, path_value) or {}
            if isinstance(progress_snapshot, dict):
                page_value = max(page_value, max(0, space_w_int(progress_snapshot.get("page", 0), 0)))
                pages_value = max(pages_value, max(0, space_w_int(progress_snapshot.get("pages", 0), 0)))
        except Exception:
            pass
    return {
        "path": path_value,
        "lesson_id": file_id if file_id.lower().startswith("ftg-lesson-") else "",
        "file_id": file_id if file_id.lower().startswith("ftg-lesson-") else "",
        "parentPath": parent,
        "title": clean(source.get("title") or source.get("name") or "")[:180],
        "space": clean(source.get("space") or source.get("source") or "")[:40],
        "page": page_value,
        "pages": pages_value,
        "sourcePath": clean_path_value(source.get("sourcePath") or source.get("source_path") or source.get("linked_path") or source.get("linkedPath") or display_contract.get("display_path") or path_value)[:600],
        "effectivePath": clean_path_value(source.get("effectivePath") or source.get("effective_path") or display_contract.get("effective_path") or "")[:600],
        "linkTarget": clean_path_value(source.get("linkTarget") or source.get("link_target") or display_contract.get("target_path") or "")[:600],
        "linkedPath": clean_path_value(source.get("linkedPath") or source.get("linked_path") or display_contract.get("link_path") or "")[:600],
        "displayPath": clean_path_value(display_contract.get("display_path", ""))[:600],
        "folderLinkPath": clean_path_value(display_contract.get("folder_link_path", ""))[:600],
        "taskOwner": normalize_username(source.get("task_owner") or display_contract.get("task_owner") or username),
        "accessedAt": clean(source.get("accessedAt") or source.get("updatedAt") or source.get("at") or source.get("time") or "")[:80],
    }


def lesson_last_file_row_is_resumeable(row: dict | None) -> bool:
    path_value = clean_path_value((row or {}).get("path", ""))
    parts = [clean(part).lower() for part in path_value.split("/") if clean(part)]
    return not (len(parts) >= 2 and parts[1] == "immediate mission")


def normalize_lesson_last_folder_row(row: dict | str | None, username: str = "", trusted_persisted: bool = False) -> dict:
    source = row if isinstance(row, dict) else {"path": row}
    path_value = clean_path_value(source.get("path") or source.get("folder") or source.get("tree") or "")
    if not path_value:
        return {}
    if not trusted_persisted:
        try:
            target = safe_server_data_path(path_value, username, admin=is_admin_user(username))
            if target.exists() and not target.is_dir():
                parent = server_data_relative(target.parent)
                if parent is not None:
                    path_value = parent
        except Exception:
            pass
    return {
        "path": path_value,
        "task_owner": normalize_username(source.get("task_owner") or source.get("taskOwner") or source.get("owner") or ""),
        "selected_at": clean(source.get("selected_at") or source.get("selectedAt") or source.get("updated_at") or source.get("updatedAt") or source.get("at") or "")[:80] or utc_timestamp(),
        "source": clean(source.get("source") or source.get("src") or source.get("reason") or "")[:80],
    }


def normalize_lesson_last_file_payload(payload: dict | None, username: str = "", trusted_persisted: bool = False) -> dict:
    source = payload if isinstance(payload, dict) else {}
    file_source = source.get("file") if isinstance(source.get("file"), dict) else source
    file_row = normalize_lesson_last_file_row(file_source, username, trusted_persisted=trusted_persisted)
    selected_folder = normalize_lesson_last_folder_row(source.get("selectedFolder") or source.get("selected_folder") or source.get("folder"), username, trusted_persisted=trusted_persisted)
    rows = source.get("recentFiles") or source.get("recent_files") or source.get("recent")
    recent_files: list[dict] = []
    seen: set[str] = set()
    if file_row:
        key = file_row["path"].lower()
        seen.add(key)
        recent_files.append(file_row)
    if isinstance(rows, list):
        for item in rows:
            row = normalize_lesson_last_file_row(item, username, trusted_persisted=trusted_persisted)
            key = clean(row.get("path", "")).lower()
            if not key or key in seen:
                continue
            seen.add(key)
            recent_files.append(row)
            if len(recent_files) >= 20:
                break
    now = utc_timestamp()
    if file_row and not clean(file_row.get("accessedAt", "")):
        file_row["accessedAt"] = now
        if recent_files:
            recent_files[0]["accessedAt"] = now
    primary_file = next((row for row in recent_files if lesson_last_file_row_is_resumeable(row)), None) or file_row
    return {
        "version": 1,
        "updated_at": clean(source.get("updated_at") or source.get("updatedAt") or "") or now,
        "file": primary_file,
        "recentFiles": recent_files[:20],
        "selectedFolder": selected_folder,
    }


def read_lesson_last_file_disk(username: str) -> dict:
    if postgres_backend_mode("LESSON_LAST_FILE") == "postgres":
        payload = postgres_load_lesson_last_file(username)
        return normalize_lesson_last_file_payload(payload if isinstance(payload, dict) else {}, username, trusted_persisted=True)
    path = lesson_last_file_path(username)
    payload = server_database_read_document_json(path, {})
    # Added 2026-07-22: SQLite rows were validated on write; do not re-stat deleted history paths on every cold login.
    return normalize_lesson_last_file_payload(payload if isinstance(payload, dict) else {}, username, trusted_persisted=True)


def bump_login_preload_cache_generation(username: str = "") -> int:
    username = normalize_username(username)
    if not username:
        return 0
    key = username.lower()
    with SERVER_DATA_LIST_CACHE_LOCK:
        generations = globals().setdefault("LOGIN_PRELOAD_CACHE_USER_GENERATIONS", {})
        generation = int(generations.get(key, 0) or 0) + 1
        generations[key] = generation
        return generation


def login_preload_cache_generation(username: str = "") -> int:
    key = normalize_username(username).lower()
    if not key:
        return 0
    with SERVER_DATA_LIST_CACHE_LOCK:
        generations = globals().setdefault("LOGIN_PRELOAD_CACHE_USER_GENERATIONS", {})
        return int(generations.get(key, 0) or 0)


# Added 2026-07-20; updated 2026-07-22: cache legacy and compact response contracts separately.
def login_preload_response_signature(username: str = "", relative_path: str = "", response_mode: str = "") -> tuple:
    manifest = get_server_data_manifest()
    response_mode = "compact-v2" if clean(response_mode).lower() == "compact-v2" else "legacy"
    return (
        normalize_username(username),
        clean_path_value(relative_path),
        response_mode,
        login_preload_cache_generation(username),
        server_data_tree_runtime_revision(username, bool(is_admin_user(username)), manifest),
    )


def login_preload_response_cache_row(username: str = "", relative_path: str = "", response_mode: str = "") -> dict | None:
    username = normalize_username(username)
    relative_path = clean_path_value(relative_path)
    response_mode = "compact-v2" if clean(response_mode).lower() == "compact-v2" else "legacy"
    cache_key = (username, relative_path, response_mode)
    signature = login_preload_response_signature(username, relative_path, response_mode)
    cache = globals().setdefault("LOGIN_PRELOAD_RESPONSE_BYTES_CACHE", {})
    with SERVER_DATA_LIST_CACHE_LOCK:
        row = cache.get(cache_key) if isinstance(cache, dict) else None
        if isinstance(row, dict) and row.get("signature") == signature and isinstance(row.get("bytes"), bytes):
            return {**row, "cache_hit": True}
    return None


def build_login_preload_response_cache_row(username: str = "", relative_path: str = "", response_mode: str = "") -> dict:
    username = normalize_username(username)
    relative_path = clean_path_value(relative_path)
    response_mode = "compact-v2" if clean(response_mode).lower() == "compact-v2" else "legacy"
    started = time.perf_counter()
    list_ms = 0.0
    if response_mode == "compact-v2":
        # 2026-07-27: compact-v2 login warmup composes Lesson Vault from
        # /server-data/common-tree + /server-data/user-overlay, so avoid
        # duplicating the same folder/list payload inside login-preload.
        safe_payload = {
            "ok": True,
            "username": username,
            "path": relative_path,
            "entries": [],
            "manifest_snapshot": True,
            "preload_meta_only": True,
        }
    else:
        list_started = time.perf_counter()
        payload = list_server_data(relative_path, username, admin=bool(is_admin_user(username)), task_owner_hint="", fresh=False, lightweight=True)
        list_ms = (time.perf_counter() - list_started) * 1000
        safe_payload = dict(payload or {})
    safe_payload["tasks"] = []
    safe_payload["task_notices"] = []
    safe_payload["space_tasks"] = []
    safe_payload["space_task"] = {"enabled": False, "tasks": [], "preauth_hidden": True}
    safe_payload["preauth"] = True
    progress_started = time.perf_counter()
    progress_trace: dict[str, float] = {}
    progress_snapshot = lesson_progress_snapshot_for_client(username, trace=progress_trace)
    progress_ms = (time.perf_counter() - progress_started) * 1000
    safe_payload["progress_snapshot"] = progress_snapshot
    last_file_started = time.perf_counter()
    last_file_state = read_lesson_last_file_state(username)
    last_file_ms = (time.perf_counter() - last_file_started) * 1000
    json_started = time.perf_counter()
    data = json_bytes({
        "ok": True,
        "username": username,
        "path": clean(safe_payload.get("path", relative_path)),
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
        "preload": safe_payload,
        "last_file_state": last_file_state,
    })
    json_ms = (time.perf_counter() - json_started) * 1000
    response = {
        "ok": True,
        "username": username,
        "path": clean(safe_payload.get("path", relative_path)),
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
        "preload": safe_payload,
        "last_file_state": last_file_state,
    }
    if response_mode == "legacy":
        response["progress_snapshots"] = {username: progress_snapshot}
    row = {
        "signature": login_preload_response_signature(username, relative_path, response_mode),
        "response_mode": response_mode,
        "payload": response,
        "bytes": data,
        "etag": f'"login-preload-{hashlib.sha1(data).hexdigest()}"',
        "at": time.time(),
        "cache_hit": False,
        "timing": {
            "list_server_data_ms": round(list_ms, 3),
            "progress_snapshot_ms": round(progress_ms, 3),
            "progress_snapshot_index_ms": round(float(progress_trace.get("progress_index_ms", 0.0) or 0.0), 3),
            "progress_snapshot_time_ms": round(float(progress_trace.get("time_index_ms", 0.0) or 0.0), 3),
            "progress_snapshot_items_ms": round(float(progress_trace.get("items_ms", 0.0) or 0.0), 3),
            "progress_snapshot_cache_ms": round(float(progress_trace.get("cache_ms", 0.0) or 0.0), 3),
            "last_file_state_ms": round(last_file_ms, 3),
            "json_bytes_ms": round(json_ms, 3),
            "total_ms": round((time.perf_counter() - started) * 1000, 3),
        },
    }
    cache_key = (username, relative_path, response_mode)
    cache = globals().setdefault("LOGIN_PRELOAD_RESPONSE_BYTES_CACHE", {})
    with SERVER_DATA_LIST_CACHE_LOCK:
        cache[cache_key] = row
        if len(cache) > 256:
            stale = sorted(cache.items(), key=lambda item: float((item[1] or {}).get("at", 0.0) or 0.0))
            for old_key, _old_row in stale[:64]:
                if old_key != cache_key:
                    cache.pop(old_key, None)
    return row


def get_or_build_login_preload_response_cache_row(username: str = "", relative_path: str = "", response_mode: str = "") -> dict:
    username = normalize_username(username)
    relative_path = clean_path_value(relative_path)
    response_mode = "compact-v2" if clean(response_mode).lower() == "compact-v2" else "legacy"
    cached = login_preload_response_cache_row(username, relative_path, response_mode)
    if isinstance(cached, dict):
        return cached
    cache_key = (username, relative_path, response_mode)
    inflight = globals().setdefault("LOGIN_PRELOAD_RESPONSE_BUILD_INFLIGHT", {})
    should_build = False
    with SERVER_DATA_LIST_CACHE_LOCK:
        event = inflight.get(cache_key) if isinstance(inflight, dict) else None
        if not hasattr(event, "wait"):
            event = threading.Event()
            inflight[cache_key] = event
            should_build = True
    if not should_build:
        event.wait(15.0)
        cached = login_preload_response_cache_row(username, relative_path, response_mode)
        if isinstance(cached, dict):
            cached["coalesced"] = True
            return cached
    try:
        return build_login_preload_response_cache_row(username, relative_path, response_mode)
    finally:
        if should_build:
            with SERVER_DATA_LIST_CACHE_LOCK:
                inflight.pop(cache_key, None)
                event.set()


def warm_login_preload_response_cache(users: object = None, response_mode: str = "compact-v2") -> dict:
    started_cpu = time.process_time()
    started_wall = time.perf_counter()
    usernames = select_startup_warmup_usernames(users, purpose="login-preload")
    warmed = 0
    for username in usernames:
        try:
            # Added 2026-07-30: the frontend's authenticated startup request
            # uses an empty path, so warm that exact revision-keyed response.
            get_or_build_login_preload_response_cache_row(username, "", response_mode)
            warmed += 1
            state = read_lesson_last_file_state(username)
            file_state = state.get("file") if isinstance(state, dict) and isinstance(state.get("file"), dict) else {}
            rel_path = clean_path_value(
                file_state.get("path")
                or file_state.get("effectivePath")
                or file_state.get("effective_path")
                or file_state.get("linkTarget")
                or file_state.get("link_target")
                or ""
            )
            if rel_path:
                get_or_build_login_preload_response_cache_row(username, rel_path, response_mode)
        except Exception:
            continue
    return {
        "users": warmed,
        "cpu_ms": round((time.process_time() - started_cpu) * 1000, 1),
        "wall_ms": round((time.perf_counter() - started_wall) * 1000, 1),
        **startup_warmup_selection_summary(usernames),
    }


# Added 2026-07-27: warm the exact first folder-list request used after login so
# cold login does not spend CPU rebuilding a small user folder on the hot path.
def warm_login_server_data_list_cache(users: object = None, max_users: int = 24) -> dict:
    started_cpu = time.process_time()
    started_wall = time.perf_counter()
    usernames = select_startup_warmup_usernames(users, purpose="folder-list")
    if future_warmup_mode() != "benchmark":
        usernames = []
    warmed = 0
    errors = 0
    for username in sorted(usernames, key=natural_sort_key)[: max(0, int(max_users or 0))]:
        try:
            state = read_lesson_last_file_state(username)
            file_state = state.get("file") if isinstance(state, dict) and isinstance(state.get("file"), dict) else {}
            selected = state.get("selectedFolder") if isinstance(state, dict) and isinstance(state.get("selectedFolder"), dict) else {}
            rel_path = clean_path_value(
                selected.get("path")
                or file_state.get("folder")
                or file_state.get("folderPath")
                or file_state.get("path")
                or username
            )
            top = clean_path_value(rel_path).split("/", 1)[0]
            if normalize_username(top).lower() != username.lower():
                rel_path = username
            list_server_data(
                rel_path,
                username,
                admin=bool(is_admin_user(username)),
                task_owner_hint=username if is_admin_user(username) else "",
                fresh=False,
                lightweight=False,
                include_task_board=False,
                include_space_task=False,
            )
            warmed += 1
        except Exception:
            errors += 1
            continue
    return {
        "users": warmed,
        "errors": errors,
        "cpu_ms": round((time.process_time() - started_cpu) * 1000, 1),
        "wall_ms": round((time.perf_counter() - started_wall) * 1000, 1),
        **startup_warmup_selection_summary(usernames),
    }

def read_lesson_last_file_state(username: str) -> dict:
    username = normalize_username(username)
    if not username:
        return {"version": 1, "updated_at": "", "file": {}, "recentFiles": [], "selectedFolder": {}}
    with LESSON_LAST_FILE_LOCK:
        cached = LESSON_LAST_FILE_CACHE.get(username.lower())
        if isinstance(cached, dict):
            return copy.deepcopy(cached)
        payload = read_lesson_last_file_disk(username)
        LESSON_LAST_FILE_CACHE[username.lower()] = copy.deepcopy(payload)
        return copy.deepcopy(payload)


def lesson_last_file_response_cache_row(username: str = "") -> dict:
    username = normalize_username(username)
    signature = (username, login_preload_cache_generation(username))
    cache = globals().setdefault("LESSON_LAST_FILE_RESPONSE_BYTES_CACHE", {})
    with LESSON_LAST_FILE_LOCK:
        row = cache.get(username.lower()) if isinstance(cache, dict) else None
        if isinstance(row, dict) and row.get("signature") == signature and isinstance(row.get("bytes"), bytes):
            return {**row, "cache_hit": True}
    payload = {"ok": True, "username": username, "state": read_lesson_last_file_state(username)}
    data = json_bytes(payload)
    row = {
        "signature": signature,
        "payload": payload,
        "bytes": data,
        "etag": f'"last-file-{hashlib.sha1(data).hexdigest()}"',
        "cache_hit": False,
    }
    with LESSON_LAST_FILE_LOCK:
        cache[username.lower()] = row
    return row


def lesson_last_file_user_lock(username: str) -> threading.RLock:
    key = normalize_username(username).lower()
    with LESSON_LAST_FILE_LOCK:
        lock = LESSON_LAST_FILE_USER_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            LESSON_LAST_FILE_USER_LOCKS[key] = lock
        return lock


def persist_lesson_last_file_database(username: str, payload: dict) -> None:
    if postgres_backend_mode("LESSON_LAST_FILE") == "postgres":
        postgres_upsert_lesson_last_file_row(username, payload)
        return
    target = lesson_last_file_path(username)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    database_store = globals().get("server_database_store_document_now")
    if not callable(database_store) or not database_store(target, text, "utf-8", authoritative=True):
        raise RuntimeError("Khong ghi duoc last-file vao PostgreSQL.")


def flush_lesson_last_file_state(username: str) -> None:
    username = normalize_username(username)
    if not username:
        return
    with LESSON_LAST_FILE_LOCK:
        key = username.lower()
        payload = normalize_lesson_last_file_payload(LESSON_LAST_FILE_CACHE.get(key), username, trusted_persisted=True)
    persist_lesson_last_file_database(username, payload)


def flush_lesson_last_file_dirty() -> None:
    global LESSON_LAST_FILE_FLUSH_TIMER
    with LESSON_LAST_FILE_LOCK:
        usernames = list(LESSON_LAST_FILE_DIRTY_USERS)
        LESSON_LAST_FILE_DIRTY_USERS.clear()
        LESSON_LAST_FILE_FLUSH_TIMER = None
    for username in usernames:
        try:
            flush_lesson_last_file_state(username)
        except Exception:
            pass


def flush_lesson_last_file_all() -> None:
    global LESSON_LAST_FILE_FLUSH_TIMER
    with LESSON_LAST_FILE_LOCK:
        usernames = list(LESSON_LAST_FILE_CACHE.keys())
        timer = LESSON_LAST_FILE_FLUSH_TIMER
        LESSON_LAST_FILE_FLUSH_TIMER = None
        LESSON_LAST_FILE_DIRTY_USERS.clear()
    try:
        if isinstance(timer, threading.Timer):
            timer.cancel()
    except Exception:
        pass
    for username in usernames:
        try:
            flush_lesson_last_file_state(username)
        except Exception:
            pass


atexit.register(flush_lesson_last_file_all)


def schedule_lesson_last_file_flush(username: str) -> None:
    global LESSON_LAST_FILE_FLUSH_TIMER
    username = normalize_username(username)
    if not username:
        return
    key = username.lower()
    with LESSON_LAST_FILE_LOCK:
        LESSON_LAST_FILE_DIRTY_USERS.add(key)
        timer = LESSON_LAST_FILE_FLUSH_TIMER
        if isinstance(timer, threading.Timer) and timer.is_alive():
            return
        timer = threading.Timer(LESSON_LAST_FILE_FLUSH_DELAY_SECONDS, flush_lesson_last_file_dirty)
        timer.daemon = True
        LESSON_LAST_FILE_FLUSH_TIMER = timer
        timer.start()


# Added 2026-07-21: rate-limit semantically identical navigation state without losing a later genuine reopen timestamp.
def lesson_last_file_semantic_identity(payload: dict | None) -> tuple:
    source = payload if isinstance(payload, dict) else {}
    file_row = source.get("file") if isinstance(source.get("file"), dict) else {}
    recent_rows = source.get("recentFiles") if isinstance(source.get("recentFiles"), list) else []
    folder = source.get("selectedFolder") if isinstance(source.get("selectedFolder"), dict) else {}

    def file_identity(row: dict | None) -> tuple:
        item = row if isinstance(row, dict) else {}
        return (
            clean(item.get("lesson_id") or item.get("file_id") or item.get("identity")).lower(),
            clean_path_value(item.get("path", "")).lower(),
            clean_path_value(item.get("parentPath", "")).lower(),
            max(0, space_w_int(item.get("page", 0), 0)),
            max(0, space_w_int(item.get("pages", 0), 0)),
            clean_path_value(item.get("sourcePath", "")).lower(),
            clean_path_value(item.get("effectivePath", "")).lower(),
            clean_path_value(item.get("linkTarget", "")).lower(),
            clean_path_value(item.get("linkedPath", "")).lower(),
        )

    return (
        file_identity(file_row),
        tuple(file_identity(row) for row in recent_rows[:20] if isinstance(row, dict)),
        (
            clean_path_value(folder.get("path", "")).lower(),
            normalize_username(folder.get("task_owner") or folder.get("taskOwner") or "").lower(),
        ),
    )


def remember_lesson_last_file(username: str, payload: dict) -> dict:
    username = normalize_username(username)
    if not username:
        raise RuntimeError("Chua dang nhap.")
    request_identity = lesson_last_file_semantic_identity(payload)
    request_now = time.monotonic()
    request_cache_key = username.lower()
    # Added 2026-07-21: reject old-client click storms from RAM before path resolution or SQLite state reads.
    with LESSON_LAST_FILE_LOCK:
        cached_request = LESSON_LAST_FILE_REQUEST_CACHE.get(request_cache_key)
        if (
            isinstance(cached_request, dict)
            and cached_request.get("identity") == request_identity
            and request_now - float(cached_request.get("at", 0.0) or 0.0) < 30.0
            and isinstance(cached_request.get("state"), dict)
        ):
            return cached_request["state"]
    incoming = normalize_lesson_last_file_payload(payload, username)
    if not incoming.get("file") and not incoming.get("selectedFolder"):
        raise RuntimeError("Thieu duong dan file hoac folder gan nhat.")
    with lesson_last_file_user_lock(username):
        with LESSON_LAST_FILE_LOCK:
            current = read_lesson_last_file_state(username)
            seen: set[str] = set()
            rows: list[dict] = []
            for item in [incoming.get("file"), *incoming.get("recentFiles", []), *current.get("recentFiles", [])]:
                # Incoming/current rows were already normalized and ID-verified above.
                row = normalize_lesson_last_file_row(item, username, trusted_persisted=True)
                key = clean(row.get("path", "")).lower()
                if not key or key in seen:
                    continue
                seen.add(key)
                rows.append(row)
                if len(rows) >= 20:
                    break
            result = {
                "version": 1,
                "updated_at": utc_timestamp(),
                "file": rows[0] if rows else incoming.get("file", {}),
                "recentFiles": rows,
                "selectedFolder": incoming.get("selectedFolder") or current.get("selectedFolder") or {},
            }
            current_updated_epoch = timestamp_to_epoch(current.get("updated_at", ""))
            if (
                current
                and lesson_last_file_semantic_identity(current) == lesson_last_file_semantic_identity(result)
                and current_updated_epoch > 0
                and time.time() - current_updated_epoch < 30.0
            ):
                LESSON_LAST_FILE_REQUEST_CACHE[request_cache_key] = {
                    "identity": request_identity,
                    "at": request_now,
                    "state": current,
                }
                return current
        # Per-user ordering stays strict while different users can enter SQLite's shared group commit together.
        with LESSON_LAST_FILE_LOCK:
            LESSON_LAST_FILE_CACHE[username.lower()] = result
            LESSON_LAST_FILE_REQUEST_CACHE[request_cache_key] = {
                "identity": request_identity,
                "at": request_now,
                "state": result,
            }
            LESSON_LAST_FILE_DIRTY_USERS.add(username.lower())
            if len(LESSON_LAST_FILE_REQUEST_CACHE) > LESSON_LAST_FILE_REQUEST_CACHE_MAX_USERS:
                oldest_key = min(
                    LESSON_LAST_FILE_REQUEST_CACHE,
                    key=lambda key: float(LESSON_LAST_FILE_REQUEST_CACHE[key].get("at", 0.0) or 0.0),
                )
                LESSON_LAST_FILE_REQUEST_CACHE.pop(oldest_key, None)
        # Navigation state is non-critical UX data: acknowledge from RAM and persist
        # the coalesced latest snapshot through the existing 10-second durable flush.
        schedule_lesson_last_file_flush(username)
    bump_login_preload_cache_generation(username)
    return result


def lesson_time_key(relative_path: str = "") -> str:
    raw = clean(relative_path)
    if raw.lower().startswith(("path:", "file_id:")):
        source = raw.lower()
    else:
        rel_path = clean_path_value(raw)
        source = f"path:{rel_path.lower()}" if rel_path else ""
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:32] if source else ""


def read_lesson_time_file(username: str) -> dict:
    return server_database_load_lesson_time_payload(username)


def read_cached_lesson_time_file(username: str) -> dict:
    username = normalize_username(username)
    if not username:
        return {"version": 1, "states": {}}
    return read_lesson_time_file(username)


def write_lesson_time_file(username: str, payload: dict) -> None:
    server_database_replace_lesson_time_payload(username, payload)
    bump_login_preload_cache_generation(username)


def lesson_time_runtime_signature(username: str) -> tuple:
    normalized = normalize_username(username)
    return (normalized.lower(), server_database_user_generation("lesson_time", normalized))


def lesson_time_summary(username: str, relative_path: str = "") -> dict:
    username = normalize_username(username)
    rel_path = clean_path_value(relative_path)
    if not username or not rel_path:
        return {"seconds": 0, "ticks": 0, "updatedAt": ""}
    try:
        identity = lesson_time_identity(rel_path, username, admin=is_admin_user(username))
        key = lesson_time_key(identity.get("source", ""))
        legacy_key = lesson_time_key(identity.get("legacy_source", ""))
        payload = read_cached_lesson_time_file(username)
        row = payload.get("states", {}).get(key)
        if not isinstance(row, dict) and legacy_key and legacy_key != key:
            row = payload.get("states", {}).get(legacy_key)
        if not isinstance(row, dict):
            return {"seconds": 0, "ticks": 0, "updatedAt": ""}
        return {
            "seconds": max(0, space_w_int(row.get("seconds", 0), 0)),
            "ticks": max(0, space_w_int(row.get("ticks", 0), 0)),
            "updatedAt": clean(row.get("updatedAt", "")),
        }
    except Exception:
        return {"seconds": 0, "ticks": 0, "updatedAt": ""}


def lesson_time_state_index(username: str) -> dict[str, dict]:
    username = normalize_username(username)
    if not username:
        return {}
    try:
        payload = read_cached_lesson_time_file(username)
        states = payload.get("states") if isinstance(payload, dict) and isinstance(payload.get("states"), dict) else {}
        index: dict[str, dict] = {}
        index["__canonical_v2__"] = {"complete": True}
        for key, value in states.items():
            clean_key = clean(key)
            if not clean_key or not isinstance(value, dict):
                continue
            index[clean_key] = value
            row_path = clean_path_value(value.get("path", ""))
            if row_path:
                index[lesson_time_key(f"path:{row_path.lower()}")] = value
                index[f"path:{row_path.lower()}"] = value
            file_id = clean(value.get("file_id") or value.get("lesson_id"))[:240]
            if file_id:
                index[f"id:{file_id.lower()}"] = value
        return index
    except Exception:
        return {}


def lesson_time_summary_from_index(time_index: dict[str, dict] | None, username: str, relative_path: str = "", alias_paths: object = None) -> dict:
    rel_path = clean_path_value(relative_path)
    if not rel_path:
        return {"seconds": 0, "ticks": 0, "updatedAt": ""}
    if not isinstance(time_index, dict):
        return lesson_time_summary(username, rel_path)
    path_candidates = [rel_path]
    if isinstance(alias_paths, (list, tuple, set)):
        path_candidates.extend(alias_paths)
    elif clean(alias_paths):
        path_candidates.append(alias_paths)
    row = None
    best_updated = 0.0
    canonical_index = bool(isinstance(time_index.get("__canonical_v2__"), dict))
    seen_paths: set[str] = set()
    for candidate in path_candidates:
        candidate_path = clean_path_value(candidate)
        candidate_key = candidate_path.lower()
        if not candidate_path or candidate_key in seen_paths:
            continue
        seen_paths.add(candidate_key)
        direct_row = time_index.get(f"path:{candidate_key}")
        if isinstance(direct_row, dict):
            updated = lesson_sort_timestamp(direct_row.get("updatedAt", ""))
            if row is None or updated >= best_updated:
                row = direct_row
                best_updated = updated
            continue
        alias_reader = globals().get("server_database_lesson_file_id_for_path")
        file_id = clean(alias_reader(candidate_path))[:240] if callable(alias_reader) else ""
        id_row = time_index.get(f"id:{file_id.lower()}") if file_id else None
        if isinstance(id_row, dict):
            updated = lesson_sort_timestamp(id_row.get("updatedAt", ""))
            if row is None or updated >= best_updated:
                row = id_row
                best_updated = updated
            continue
        if canonical_index:
            continue
        identity = lesson_time_identity(candidate_path, username, admin=is_admin_user(username))
        keys = [lesson_time_key(identity.get("source", ""))]
        legacy_key = lesson_time_key(identity.get("legacy_source", ""))
        if legacy_key and legacy_key not in keys:
            keys.append(legacy_key)
        for key in keys:
            candidate_row = time_index.get(key)
            if not isinstance(candidate_row, dict):
                continue
            updated = lesson_sort_timestamp(candidate_row.get("updatedAt", ""))
            if row is None or updated >= best_updated:
                row = candidate_row
                best_updated = updated
    if not isinstance(row, dict):
        return {"seconds": 0, "ticks": 0, "updatedAt": ""}
    return {
        "seconds": max(0, space_w_int(row.get("seconds", 0), 0)),
        "ticks": max(0, space_w_int(row.get("ticks", 0), 0)),
        "updatedAt": clean(row.get("updatedAt", "")),
    }


def add_lesson_study_time(username: str, payload: dict) -> dict:
    username = normalize_username(username)
    source = payload if isinstance(payload, dict) else {}
    raw_path = clean(source.get("path", ""))
    requested_file_id = clean(source.get("lesson_id") or source.get("lessonId") or source.get("file_id") or source.get("fileId"))[:240]
    rel_path = ""
    if raw_path and requested_file_id.lower().startswith("ftg-lesson-"):
        candidate = clean_path_value(raw_path)
        parts = [part for part in candidate.split("/") if part]
        suffix = Path(candidate).suffix.lower()
        allowed_root = bool(parts) and (
            parts[0].lower() == "common"
            or parts[0].lower() == username.lower()
            or is_admin_user(username)
        )
        registry_ready = globals().get("server_database_lesson_identity_registry_ready")
        alias_reader = globals().get("server_database_lesson_file_id_for_path")
        # Added 2026-07-22: an active ID/path alias is durable access proof for structured lessons.
        if (
            allowed_root
            and not any(part in {".", ".."} for part in parts)
            and suffix != ".pdf"
            and suffix not in IMAGE_FILE_SUFFIXES
            and callable(registry_ready)
            and registry_ready()
            and callable(alias_reader)
            and clean(alias_reader(candidate)) == requested_file_id
        ):
            rel_path = candidate
    if not rel_path and raw_path:
        rel_path = normalize_space_w_progress_path(raw_path, username, admin=is_admin_user(username))
    if not rel_path:
        raise RuntimeError("Thieu file dang hoc de cap nhat thoi gian.")
    seconds = source.get("seconds", 30)
    # 2026-07-20: rel_path is already the validated effective lesson path; do not resolve the filesystem twice per heartbeat.
    alias_reader = globals().get("server_database_lesson_file_id_for_path")
    resolved_file_id = clean(alias_reader(rel_path))[:240] if callable(alias_reader) else ""
    file_id = requested_file_id if requested_file_id and resolved_file_id == requested_file_id else resolved_file_id
    record_canonical_identity_resolution("lesson_time.write", {"lesson_id": file_id, "path": rel_path})
    key = lesson_time_key(f"file_id:{file_id}" if file_id else rel_path)
    legacy_key = lesson_time_key(rel_path) if file_id else ""
    row = server_database_add_lesson_time(
        username,
        key,
        legacy_key,
        rel_path,
        clean(source.get("title", ""))[:180],
        clean(source.get("space") or source.get("source", ""))[:40],
        seconds,
        session_id=source.get("session_id") or source.get("sessionId") or "",
        sequence=source.get("sequence"),
        protocol=source.get("protocol", ""),
        offline_claims=source.get("offline_claims") if isinstance(source.get("offline_claims"), list) else None,
        offline_lease=clean(source.get("offline_lease", "")),
        authenticated_user=True,
    )
    if max(0, space_w_int(row.get("acceptedSeconds", 0), 0)) > 0:
        bump_login_preload_cache_generation(username)
    return row


def clear_lesson_metadata_cache() -> None:
    with LESSON_METADATA_CACHE_LOCK:
        LESSON_METADATA_CACHE.clear()


def lesson_dependency_signature(path_text: str = "") -> tuple[str, int, int]:
    raw = clean(path_text)
    if not raw:
        return "", 0, -1
    try:
        path = Path(raw)
        if server_asset_category(path) == "Structure":
            return structure_asset_signature(path)
        stat = path.stat()
        return str(path.resolve()).lower(), int(stat.st_mtime_ns), int(stat.st_size)
    except Exception:
        return raw.lower(), 0, -1


def pdf_lesson_page_count(path: Path) -> int:
    cached_reader = globals().get("get_cached_pdf_picture_metadata")
    if callable(cached_reader):
        try:
            cached = cached_reader("pdf", path)
            pages = max(0, space_w_int((cached or {}).get("pages", 0), 0))
            if pages:
                return pages
        except Exception:
            pass
    try:
        import fitz  # PyMuPDF
        document = fitz.open(str(path))
        try:
            return max(0, int(getattr(document, "page_count", 0) or len(document) or 0))
        finally:
            document.close()
    except Exception:
        return 0


def cached_lesson_file_metadata(path: Path, manifest_entry: dict | None = None) -> dict:
    path = Path(path)
    trusted_manifest = bool(
        isinstance(manifest_entry, dict)
        and clean(manifest_entry.get("type", "")).lower() == "file"
        and int(manifest_entry.get("modified_ns", 0) or 0) > 0
        and int(manifest_entry.get("size", -1) or -1) >= 0
    )
    if not trusted_manifest and not (path.is_file() and is_lesson_file(path)):
        path = server_data_effective_file_path(path, username="", admin=True)
    if (not trusted_manifest and not path.is_file()) or not is_lesson_file(path):
        return {}
    if trusted_manifest:
        resolved_key = str(path).replace("\\", "/").lower()
        signature = (
            int(manifest_entry.get("modified_ns", 0) or 0),
            int(manifest_entry.get("size", -1) or -1),
            int(manifest_entry.get("metadata_dependency_mtime_ns", 0) or 0),
            int(manifest_entry.get("metadata_dependency_size", -1) or -1),
        )
    else:
        try:
            resolved_key = str(path.resolve()).lower()
        except Exception:
            resolved_key = str(path).lower()
        signature = file_cache_signature(path)
    metadata_inflight = globals().setdefault("LESSON_METADATA_CACHE_INFLIGHT", {})
    event = None
    should_load = False
    while True:
        with LESSON_METADATA_CACHE_LOCK:
            cached = LESSON_METADATA_CACHE.get(resolved_key)
            if isinstance(cached, dict) and cached.get("signature") == signature:
                dependency = cached.get("dependency", ("", 0, -1))
                dependency_valid = trusted_manifest or dependency == lesson_dependency_signature(cached.get("dependency_path", ""))
                if dependency_valid:
                    meta = cached.get("meta")
                    if isinstance(meta, dict):
                        return meta
            event = metadata_inflight.get(resolved_key) if isinstance(metadata_inflight, dict) else None
            if event is None:
                event = threading.Event()
                if isinstance(metadata_inflight, dict):
                    metadata_inflight[resolved_key] = event
                should_load = True
                break
        event.wait(5.0)
        should_load = False
        if not event.is_set():
            break
    if not should_load:
        with LESSON_METADATA_CACHE_LOCK:
            cached = LESSON_METADATA_CACHE.get(resolved_key)
            if isinstance(cached, dict) and cached.get("signature") == signature:
                meta = cached.get("meta")
                if isinstance(meta, dict):
                    return meta
    try:
        suffix = path.suffix.lower()
        structure_path = None
        if suffix == ".pdf":
            meta = {
                "study": {},
                "title": path.stem,
                "nodes": pdf_lesson_page_count(path),
                "questions": 0,
                "direct_questions": 0,
                "total_nodes": 0,
                "paragraphs": 0,
                "space": "Space_PDF",
                "sentences": 0,
                "normal_sentences": 0,
                "train_sentences": 0,
            }
        elif suffix in IMAGE_FILE_SUFFIXES:
            meta = {
                "study": {},
                "title": path.stem,
                "nodes": 0,
                "questions": 0,
                "direct_questions": 0,
                "total_nodes": 0,
                "paragraphs": 0,
                "space": "Space_Picture",
                "sentences": 0,
                "normal_sentences": 0,
                "train_sentences": 0,
            }
        else:
            payload, structure_path = load_future_lesson_document(path)
            from future_lesson_identity import lesson_id_from_payload, lesson_payload_identity_fingerprint
            meta = {
                "study": normalize_study_block(payload),
                "title": lesson_payload_title(payload, path.stem),
                "lesson_id": clean(lesson_id_from_payload(payload))[:240],
                "content_fingerprint": clean(lesson_payload_identity_fingerprint(payload))[:320],
                "nodes": lesson_payload_node_count(payload),
                "questions": lesson_payload_question_count(payload),
                "direct_questions": lesson_payload_direct_question_count(payload),
                "total_nodes": lesson_payload_question_total_count(payload),
                "paragraphs": lesson_payload_paragraph_count(payload),
                **lesson_payload_sentence_breakdown(payload),
            }
        dependency_path = str(structure_path) if structure_path is not None else ""
        dependency = (
            clean(manifest_entry.get("metadata_dependency_path", "")),
            int(manifest_entry.get("metadata_dependency_mtime_ns", 0) or 0),
            int(manifest_entry.get("metadata_dependency_size", -1) or -1),
        ) if trusted_manifest else lesson_dependency_signature(dependency_path)
        meta.update({
            "metadata_dependency_path": dependency_path,
            "metadata_dependency_mtime_ns": dependency[1],
            "metadata_dependency_size": dependency[2],
        })
        with LESSON_METADATA_CACHE_LOCK:
            LESSON_METADATA_CACHE[resolved_key] = {
                "signature": signature,
                "dependency_path": dependency_path,
                "dependency": dependency,
                "meta": meta,
                "at": time.time(),
            }
            if len(LESSON_METADATA_CACHE) > 1400:
                ordered = sorted(LESSON_METADATA_CACHE.items(), key=lambda item: float(item[1].get("at", 0) or 0))
                for old_key, _old_value in ordered[:200]:
                    LESSON_METADATA_CACHE.pop(old_key, None)
        return meta
    except Exception:
        return {}
    finally:
        with LESSON_METADATA_CACHE_LOCK:
            inflight_event = metadata_inflight.get(resolved_key) if isinstance(metadata_inflight, dict) else None
            if inflight_event is event:
                metadata_inflight.pop(resolved_key, None)
            if event is not None:
                event.set()


def summarize_lesson_study(
    path: Path,
    username: str = "",
    progress_index: dict[tuple[str, str], dict] | None = None,
    time_index: dict[str, dict] | None = None,
    include_admin: bool = False,
    progress_relative_path: str = "",
    path_is_effective: bool = False,
    progress_relative_paths: object = None,
    include_log: bool = True,
    strict_progress_paths: bool = False,
    file_meta: dict | None = None,
    lesson_id: str = "",
) -> dict:
    display_path = path
    path = Path(path) if path_is_effective else server_data_effective_file_path(path, username=username, admin=True)
    trusted_meta = bool(path_is_effective and isinstance(file_meta, dict) and file_meta)
    if (not trusted_meta and not path.is_file()) or not is_lesson_file(path):
        return {}
    try:
        suffix = path.suffix.lower()
        primary_progress_path = clean_path_value(progress_relative_path)
        progress_path_aliases = []
        if isinstance(progress_relative_paths, (list, tuple, set)):
            progress_path_aliases.extend(progress_relative_paths)
        elif clean(progress_relative_paths):
            progress_path_aliases.append(progress_relative_paths)
        progress_path_aliases.append(primary_progress_path)
        if not strict_progress_paths:
            progress_path_aliases.extend([
                server_data_relative(display_path),
                server_data_relative(path),
            ])
        rel_path = primary_progress_path or server_data_relative(path)
        if not strict_progress_paths and not (path_is_effective and primary_progress_path):
            progress_identity = lesson_completion_identity(rel_path, username, admin=include_admin)
            rel_path = clean_path_value(progress_identity.get("path", "")) or rel_path
        progress_space = lesson_progress_space_for_path(rel_path, path.suffix)
        canonical_lesson_id = clean(
            lesson_id
            or (file_meta or {}).get("lesson_id", "")
            or (file_meta or {}).get("file_id", "")
        )[:240]
        if username and suffix in {".space_w", ".space_q", ".space_p", ".space_s", ".space_l", ".txt"}:
            fast_progress = lesson_progress_summary_from_index(
                progress_index,
                username,
                rel_path,
                path.suffix,
                0,
                progress_path_aliases,
                strict_paths=True,
                lesson_id=canonical_lesson_id,
            )
            if isinstance(fast_progress, dict) and (
                fast_progress.get("completed")
                or max(0, space_w_int(fast_progress.get("done", 0), 0)) > 0
                or max(0, space_w_int(fast_progress.get("percent", 0), 0)) > 0
            ):
                time_summary = lesson_time_summary_from_index(time_index, username, rel_path, progress_path_aliases) if username and time_index else {"seconds": 0, "ticks": 0, "updatedAt": ""}
                fast_total = max(0, space_w_int(fast_progress.get("total", 0), 0))
                fast_done = max(0, space_w_int(fast_progress.get("done", 0), 0))
                fast_nodes = max(0, space_w_int(fast_progress.get("root_node_total", fast_progress.get("node_total", fast_total)), 0))
                fast_completed = bool(fast_progress.get("completed") or (fast_total and fast_done >= fast_total))
                fast_last = clean(fast_progress.get("updatedAt") or fast_progress.get("savedAt"))
                return {
                    "total": 1 if fast_completed else 0,
                    "users": 1 if fast_completed else 0,
                    "last": fast_last if fast_completed else "",
                    "mine": 1 if fast_completed else 0,
                    "mine_last": fast_last if fast_completed else "",
                    "title": path.stem,
                    "nodes": fast_nodes,
                    "questions": max(0, fast_total - fast_nodes) if progress_space == "Space_Q" else 0,
                    "direct_questions": 0,
                    "total_nodes": fast_total if progress_space == "Space_Q" else 0,
                    "sentences": max(0, space_w_int(fast_progress.get("sentenceCount", fast_progress.get("sentences", 0)), 0)),
                    "normal_sentences": max(0, space_w_int(fast_progress.get("normalSentenceCount", fast_progress.get("normal_sentences", 0)), 0)),
                    "train_sentences": max(0, space_w_int(fast_progress.get("trainSentenceCount", fast_progress.get("train_sentences", 0)), 0)),
                    "progress": fast_progress,
                    "time": time_summary,
                    "time_seconds": int(time_summary.get("seconds", 0) or 0),
                    "time_ticks": int(time_summary.get("ticks", 0) or 0),
                }
        if suffix == ".pdf":
            meta = {
                "study": {},
                "title": path.stem,
                "nodes": 0,
                "questions": 0,
                "direct_questions": 0,
                "total_nodes": 0,
                "space": "Space_PDF",
            }
        elif suffix in IMAGE_FILE_SUFFIXES:
            meta = {
                "study": {},
                "title": path.stem,
                "nodes": 0,
                "questions": 0,
                "direct_questions": 0,
                "total_nodes": 0,
                "space": "Space_Picture",
            }
        else:
            meta = file_meta if isinstance(file_meta, dict) else cached_lesson_file_metadata(path)
        if not meta:
            return {}
        study = meta.get("study") if isinstance(meta.get("study"), dict) else {}
        if strict_progress_paths:
            # Updated 2026-07-21: links read target content and share one canonical progress record with the original file.
            study = {}
        if primary_progress_path and path_is_effective:
            log_path_candidates = tuple(progress_path_aliases)
        else:
            log_path_candidates = (
                primary_progress_path,
                server_data_relative(display_path),
                server_data_relative(path),
            )
        log_paths = []
        for candidate in log_path_candidates:
            candidate = clean_path_value(candidate)
            if candidate and candidate.lower() not in {item.lower() for item in log_paths}:
                log_paths.append(candidate)
        if include_log and strict_progress_paths:
            # Canonical lessons must not reintroduce alias/path completion history.
            # Legacy log lookup remains only for records that have no stable ID yet.
            log_mine = (
                learning_completion_user_row_for_paths(log_paths, username=username, admin=include_admin)
                if not canonical_lesson_id else {}
            )
            if int(log_mine.get("count", 0) or 0) > 0:
                study = {"users": {normalize_username(username): log_mine}, "total": int(log_mine.get("count", 0) or 0), "last": clean(log_mine.get("last", ""))}
        else:
            log_study = learning_completion_study_for_paths(log_paths, username=username, admin=include_admin) if include_log else {}
            if log_study:
                study = merge_study_blocks_max(study, log_study)
        users = study.get("users", {})
        admins = study.get("admins", {})
        username = normalize_username(username)
        mine = users.get(username, {}) if username else {}
        admin_mine = admins.get(username, {}) if username else {}
        mine_count = int(mine.get("count", 0) or 0) if isinstance(mine, dict) else 0
        admin_mine_count = int(admin_mine.get("count", 0) or 0) if isinstance(admin_mine, dict) else 0
        node_count = max(0, space_w_int(meta.get("nodes", 0), 0))
        question_count = max(0, space_w_int(meta.get("questions", 0), 0))
        question_total_count = max(0, space_w_int(meta.get("total_nodes", 0), 0))
        progress_hint = question_total_count if progress_space == "Space_Q" and question_total_count else node_count
        progress = lesson_progress_summary_from_index(
            progress_index,
            username,
            rel_path,
            path.suffix,
            progress_hint,
            progress_path_aliases,
            strict_paths=strict_progress_paths,
            lesson_id=canonical_lesson_id,
        ) if username else {}
        progress_source = progress if isinstance(progress, dict) else {}
        progress_completed = bool(
            progress_source.get("completed")
            or (
                max(0, space_w_int(progress_source.get("total", 0), 0))
                and max(0, space_w_int(progress_source.get("done", 0), 0)) >= max(0, space_w_int(progress_source.get("total", 0), 0))
            )
            or max(0, space_w_int(progress_source.get("percent", 0), 0)) >= 100
            or (
                callable(globals().get("space_progress_completion_marker"))
                and space_progress_completion_marker(progress_source, progress_space)
            )
        )
        progress_last = clean(progress_source.get("updatedAt") or progress_source.get("savedAt"))
        # Added 2026-07-22: canonical lesson_id progress owns lifetime runs after replicas/path logs are merged.
        progress_completed_runs = max(
            0,
            space_w_int(progress_source.get("completedRuns", progress_source.get("completed_runs", 0)), 0),
        )
        if username and progress_completed_runs > mine_count:
            prior_last = clean(mine.get("last", "")) if isinstance(mine, dict) else ""
            canonical_last = progress_last if lesson_sort_timestamp(progress_last) >= lesson_sort_timestamp(prior_last) else prior_last
            mine_count = progress_completed_runs
            mine = {**(mine if isinstance(mine, dict) else {}), "count": mine_count, "last": canonical_last}
            users = {**users, username: mine}
            study = {
                **study,
                "users": users,
                "total": max(int(study.get("total", 0) or 0), mine_count),
                "last": canonical_last if lesson_sort_timestamp(canonical_last) >= lesson_sort_timestamp(study.get("last", "")) else clean(study.get("last", "")),
            }
        if username and mine_count <= 0 and progress_completed:
            mine_count = 1
            mine = {"count": 1, "last": progress_last}
            if int(study.get("total", 0) or 0) <= 0:
                study = {**study, "total": 1, "last": progress_last}
                users = {**users, username: mine}
        completed_for_viewer = bool(mine_count > 0 or progress_completed or (include_admin and admin_mine_count > 0))
        if completed_for_viewer:
            progress_percent = max(0, min(100, space_w_int(progress_source.get("percent", 0), 0)))
            progress_done = max(0, space_w_int(progress_source.get("done", 0), 0))
            progress_total = max(0, space_w_int(progress_source.get("total", 0), 0), progress_hint)
            is_reviewing = bool(progress_source.get("reviewing") or progress_source.get("reviewRun"))
            completion_last = (
                clean(mine.get("last", "")) if isinstance(mine, dict) and mine_count > 0 else
                (clean(admin_mine.get("last", "")) if isinstance(admin_mine, dict) else "")
            )
            active_restart_progress = lesson_progress_active_run_overrides_completion(
                progress_source,
                progress_space,
                progress_hint,
                completion_last,
            )
            if active_restart_progress:
                progress = {
                    **progress_source,
                    "space": progress_space,
                    "label": lesson_progress_label(progress_space),
                    "completed": False,
                    "previously_completed": True,
                    "in_progress": True,
                }
            elif is_reviewing and progress_total and progress_percent < 100:
                progress = {
                    **progress_source,
                    "space": progress_space,
                    "label": lesson_progress_label(progress_space),
                    "completed": True,
                    "reviewing": True,
                    "review_percent": progress_percent,
                    "review_done": progress_done,
                    "review_total": progress_total,
                    "review_text": clean(progress_source.get("text", "")) or f"{progress_done}/{progress_total}",
                    "in_progress": progress_done < progress_total,
                }
            else:
                progress = lesson_progress_completed_summary(
                    progress_source,
                    progress_space,
                    progress_total,
                    completion_last,
                )
        if username and ((isinstance(time_index, dict) and bool(time_index)) or not strict_progress_paths):
            time_summary = lesson_time_summary_from_index(time_index, username, rel_path, progress_path_aliases)
        else:
            time_summary = {"seconds": 0, "ticks": 0, "updatedAt": ""}
        summary = {
            "total": int(study.get("total", 0) or 0),
            "users": len(users),
            "last": clean(study.get("last", "")),
            "mine": mine_count,
            "mine_last": clean(mine.get("last", "")) if isinstance(mine, dict) else "",
            "completed_runs": max(0, mine_count),
            "completedRuns": max(0, mine_count),
            "title": clean(meta.get("title", "")) or path.stem,
            "nodes": node_count,
            "questions": question_count,
            "direct_questions": max(0, space_w_int(meta.get("direct_questions", 0), 0)),
            "total_nodes": question_total_count,
            "paragraphs": max(0, space_w_int(meta.get("paragraphs", 0), 0)),
            "sentences": max(0, space_w_int(meta.get("sentences", 0), 0)),
            "normal_sentences": max(0, space_w_int(meta.get("normal_sentences", 0), 0)),
            "train_sentences": max(0, space_w_int(meta.get("train_sentences", 0), 0)),
            "progress": progress,
            "time": time_summary,
            "time_seconds": int(time_summary.get("seconds", 0) or 0),
            "time_ticks": int(time_summary.get("ticks", 0) or 0),
        }
        if include_admin:
            summary.update({
                "admin_total": int(study.get("admin_total", 0) or 0),
                "admins": len(admins),
                "admin_mine": admin_mine_count,
                "admin_mine_last": clean(admin_mine.get("last", "")) if isinstance(admin_mine, dict) else "",
            })
        return summary
    except Exception:
        return {}


def lesson_space_key_for_path(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".space_v":
        return "space_v_files"
    if ext == ".space_q":
        return "space_q_files"
    if ext == ".space_p":
        return "space_p_files"
    if ext == ".space_s":
        return "space_p_files"
    if ext == ".space_l":
        return "space_p_files"
    return "space_w_files"


def empty_lesson_learning_summary(username: str = "") -> dict:
    username = normalize_username(username)
    return {
        "username": username,
        "vocabulary_words": 0,
        "space_v_files": 0,
        "space_w_files": 0,
        "space_q_files": 0,
        "space_p_files": 0,
        "total_files": 0,
        "completed_runs": 0,
        "last": "",
        "updatedAt": "",
        "cached": False,
    }


LEARNING_SUMMARY_SHARD_COUNT = 256
LEARNING_SUMMARY_SHARD_LOCKS = [threading.RLock() for _ in range(LEARNING_SUMMARY_SHARD_COUNT)]


# Added 2026-07-22: summaries are isolated by user, so unrelated learners must not share one global lock.
def learning_summary_user_lock(username: str) -> threading.RLock:
    key = normalize_username(username).lower()
    return LEARNING_SUMMARY_SHARD_LOCKS[int(hashlib.sha1(key.encode("utf-8")).hexdigest()[:8], 16) % LEARNING_SUMMARY_SHARD_COUNT]


def learning_summary_path(username: str, create_parent: bool = True) -> Path:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    folder = user_folder_path(username)
    if create_parent:
        USER_ROOT.mkdir(parents=True, exist_ok=True)
        folder.mkdir(parents=True, exist_ok=True)
    return folder / LEARNING_SUMMARY_FILE_NAME


def normalize_lesson_learning_summary(payload: dict, username: str = "") -> dict:
    username = normalize_username(username or (payload.get("username", "") if isinstance(payload, dict) else ""))
    stats = empty_lesson_learning_summary(username)
    source = payload if isinstance(payload, dict) else {}
    for key in ("vocabulary_words", "space_v_files", "space_w_files", "space_q_files", "space_p_files", "total_files", "completed_runs"):
        stats[key] = max(0, space_w_int(source.get(key, 0), 0))
    stats["last"] = clean(source.get("last", ""))
    stats["updatedAt"] = clean(source.get("updatedAt") or source.get("updated_at") or "")
    stats["cached"] = bool(stats["updatedAt"])
    return stats


def read_cached_lesson_user_learning_summary(username: str = "") -> dict:
    username = normalize_username(username)
    if not username:
        return {}
    try:
        path = learning_summary_path(username, create_parent=False)
        if postgres_backend_mode("LEARNING_SUMMARY_DOCUMENTS") == "postgres":
            from FUTURE.postgres.repositories import learning_summary_documents as pg_learning_summary_documents
            payload = pg_learning_summary_documents.read_json(path, {})
            if not isinstance(payload, dict):
                return {}
            return normalize_lesson_learning_summary(payload, username)
        if not path.is_file() and not server_database_document_exists(path):
            return {}
        payload = server_database_read_document_json(path, {})
        if not isinstance(payload, dict):
            return {}
        return normalize_lesson_learning_summary(payload, username)
    except Exception:
        return {}


def write_cached_lesson_user_learning_summary(username: str, stats: dict) -> dict:
    username = normalize_username(username)
    if not username:
        return {}
    summary = normalize_lesson_learning_summary(stats if isinstance(stats, dict) else {}, username)
    summary["username"] = username
    summary["updatedAt"] = clean(summary.get("updatedAt", "")) or utc_timestamp()
    summary["cached"] = True
    payload = {
        "version": 1,
        **summary,
    }
    path = learning_summary_path(username, create_parent=False)
    if postgres_backend_mode("LEARNING_SUMMARY_DOCUMENTS") == "postgres":
        from FUTURE.postgres.repositories import learning_summary_documents as pg_learning_summary_documents
        pg_learning_summary_documents.upsert_json(path, payload)
        bump_login_preload_cache_generation(username)
        return summary
    atomic_write_json(path, payload, indent=2)
    bump_login_preload_cache_generation(username)
    return summary


def user_learning_artifact_paths(username: str) -> list[Path]:
    username = normalize_username(username)
    if not username:
        return []
    paths: list[Path] = []
    for getter in (
        space_w_progress_path,
        space_q_progress_path,
        space_v_progress_path,
        space_p_progress_path,
        space_pdf_progress_path,
        lesson_time_path,
    ):
        try:
            paths.append(getter(username))
        except Exception:
            pass
    try:
        paths.extend(main_vocab_progress_paths(username))
    except Exception:
        paths.append(USER_ROOT / f"{username}_vocab_progress.txt")
        paths.append(MAIN_SERVER_USER_ROOT / f"{username}_vocab_progress.txt")
    try:
        paths.extend(main_vocab_learned_roots(username))
    except Exception:
        paths.append(USER_ROOT / username / "Learned Vocabulary")
    try:
        paths.append(inventory_path(username))
    except Exception:
        pass
    seen = set()
    unique = []
    for path in paths:
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def user_has_learning_artifacts(username: str) -> bool:
    for path in user_learning_artifact_paths(username):
        try:
            if path.is_file() and path.stat().st_size > 0:
                return True
            if path.is_dir() and any(path.iterdir()):
                return True
        except Exception:
            continue
    return False


def recent_user_without_learning_artifacts(username: str, max_age_seconds: int = 7 * 24 * 3600) -> bool:
    username = normalize_username(username)
    if not username:
        return False
    if user_has_learning_artifacts(username):
        return False
    try:
        account_path = user_file_path(username)
        if not account_path.is_file():
            return False
        age = time.time() - float(account_path.stat().st_mtime or 0)
        return age >= 0 and age <= max_age_seconds
    except Exception:
        return False


def compute_lesson_user_learning_summary(username: str = "") -> dict:
    username = normalize_username(username)
    if not username:
        return {}
    stats = empty_lesson_learning_summary(username)
    if recent_user_without_learning_artifacts(username):
        stats["updatedAt"] = utc_timestamp()
        stats["cached"] = True
        stats["fast_empty"] = True
        return stats
    try:
        vocab = user_vocabulary_registry_summary(username)
        stats["vocabulary_words"] = int(vocab.get("total_words", 0) or 0)
    except Exception:
        pass
    try:
        root = SERVER_DATA_ROOT.resolve()
        for path in root.rglob("*"):
            try:
                if not path.is_file() or not is_lesson_file(path):
                    continue
                rel_parts = path.resolve().relative_to(root).parts
                if rel_parts and rel_parts[0] in {"Sound", "Structure", "Picture", "server_log"}:
                    continue
                payload, _structure_path = load_future_lesson_document(path)
                study = normalize_study_block(payload)
                log_study = learning_completion_study_for_paths([server_data_relative(path)])
                if log_study:
                    study = merge_study_blocks_max(study, log_study)
                users = study.get("users", {}) if isinstance(study.get("users"), dict) else {}
                mine = users.get(username, {}) if isinstance(users.get(username), dict) else {}
                if int(mine.get("count", 0) or 0) <= 0:
                    continue
                key = lesson_space_key_for_path(path)
                mine_count = max(0, space_w_int(mine.get("count", 0), 0))
                stats[key] = int(stats.get(key, 0) or 0) + 1
                stats["total_files"] = int(stats.get("total_files", 0) or 0) + 1
                stats["completed_runs"] = int(stats.get("completed_runs", 0) or 0) + max(1, mine_count)
                last = clean(mine.get("last", ""))
                if last and timestamp_order_key(last) > timestamp_order_key(stats.get("last", "")):
                    stats["last"] = last
            except Exception:
                continue
    except Exception:
        pass
    stats["updatedAt"] = utc_timestamp()
    stats["cached"] = True
    return stats


def lesson_user_learning_summary(username: str = "", force: bool = False) -> dict:
    username = normalize_username(username)
    if not username:
        return {}
    with learning_summary_user_lock(username):
        if not force:
            cached = read_cached_lesson_user_learning_summary(username)
            if cached:
                return cached
        return write_cached_lesson_user_learning_summary(username, compute_lesson_user_learning_summary(username))


# Added 2026-07-06: Lesson Vault navigation must not scan all server data when a user has no cached summary yet.
def lesson_user_learning_summary_cached_or_empty(username: str = "") -> dict:
    username = normalize_username(username)
    if not username:
        return {}
    cached = read_cached_lesson_user_learning_summary(username)
    if cached:
        return cached
    stats = empty_lesson_learning_summary(username)
    stats["updatedAt"] = utc_timestamp()
    stats["cached"] = True
    stats["fast_empty"] = True
    return stats


def update_lesson_user_learning_summary_after_completion(
    username: str,
    path: Path,
    first_user_completion: bool = False,
    vocabulary_result: dict | None = None,
    completed_at: str = "",
    persist: bool = True,
) -> dict:
    username = normalize_username(username)
    if not username:
        return {}
    with learning_summary_user_lock(username):
        stats = read_cached_lesson_user_learning_summary(username)
        if not stats:
            # Added 2026-07-06: keep lesson completion incremental instead of scanning all server data.
            stats = empty_lesson_learning_summary(username)
        if first_user_completion:
            key = lesson_space_key_for_path(path)
            stats[key] = max(0, space_w_int(stats.get(key, 0), 0)) + 1
            stats["total_files"] = max(0, space_w_int(stats.get("total_files", 0), 0)) + 1
        stats["completed_runs"] = max(0, space_w_int(stats.get("completed_runs", 0), 0)) + 1
        vocab = vocabulary_result if isinstance(vocabulary_result, dict) else {}
        if vocab:
            stats["vocabulary_words"] = max(
                max(0, space_w_int(stats.get("vocabulary_words", 0), 0)),
                max(0, space_w_int(vocab.get("total_words", 0), 0)),
            )
        last = clean(completed_at)
        if last and timestamp_order_key(last) > timestamp_order_key(stats.get("last", "")):
            stats["last"] = last
        stats["updatedAt"] = utc_timestamp()
        if not persist:
            summary = normalize_lesson_learning_summary(stats, username)
            summary["updatedAt"] = clean(stats.get("updatedAt", "")) or utc_timestamp()
            summary["cached"] = True
            return summary
        return write_cached_lesson_user_learning_summary(username, stats)


def update_lesson_user_learning_summary_vocabulary_count(username: str, total_words: int = 0) -> dict:
    username = normalize_username(username)
    if not username:
        return {}
    with learning_summary_user_lock(username):
        stats = read_cached_lesson_user_learning_summary(username)
        if not stats:
            stats = empty_lesson_learning_summary(username)
        stats["vocabulary_words"] = max(
            max(0, space_w_int(stats.get("vocabulary_words", 0), 0)),
            max(0, space_w_int(total_words, 0)),
        )
        stats["updatedAt"] = utc_timestamp()
        return write_cached_lesson_user_learning_summary(username, stats)


def reconcile_user_vocabulary_total(username: str, sync_main: bool = False) -> dict:
    username = normalize_username(username)
    if not username:
        return {"total_words": 0, "learning_stats": {}}
    if sync_main:
        try:
            sync_main_vocabulary_for_user(username, force=False)
        except Exception:
            pass
    try:
        reconcile_user_vocab_registry_with_qmdict(username, write=True)
    except Exception:
        pass
    registry = read_user_vocab_registry(username)
    words = registry.get("words") if isinstance(registry.get("words"), dict) else {}
    total_words = len([key for key, item in words.items() if key and isinstance(item, dict)])
    stats = update_lesson_user_learning_summary_vocabulary_count(username, total_words)
    return {
        "total_words": total_words,
        "registry_updated_at": clean(registry.get("updated_at", "")),
        "learning_stats": stats,
    }
