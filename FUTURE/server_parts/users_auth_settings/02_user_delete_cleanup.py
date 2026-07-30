# Loaded by FUTURE.server_parts.02_users_auth_settings into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def safe_delete_user_path(path: Path, allowed_roots: tuple[Path, ...], result: dict) -> None:
    try:
        target = Path(path).resolve()
    except Exception as exc:
        result.setdefault("errors", []).append(f"{path}: {exc}")
        return
    allowed = False
    for root in allowed_roots:
        try:
            root_resolved = root.resolve()
            if target == root_resolved:
                result.setdefault("errors", []).append(f"Refused to delete root: {target}")
                return
            target.relative_to(root_resolved)
            allowed = True
            break
        except Exception:
            continue
    if not allowed:
        result.setdefault("errors", []).append(f"Refused unsafe path: {target}")
        return
    if not target.exists():
        return
    try:
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
            result["deleted_dirs"] = int(result.get("deleted_dirs", 0) or 0) + 1
        else:
            target.unlink()
            result["deleted_files"] = int(result.get("deleted_files", 0) or 0) + 1
        result.setdefault("deleted_paths", []).append(str(target))
    except Exception as exc:
        result.setdefault("errors", []).append(f"{target}: {exc}")


def delete_matching_user_files(folder: Path, pattern: str, result: dict) -> None:
    try:
        if not folder.is_dir():
            return
        for path in folder.glob(pattern):
            safe_delete_user_path(path, (folder,), result)
    except Exception as exc:
        result.setdefault("errors", []).append(f"{folder}/{pattern}: {exc}")

def pop_username_keys(mapping: object, username: str) -> int:
    safe_user = normalize_username(username)
    if not safe_user or not isinstance(mapping, dict):
        return 0
    removed = 0
    for key in list(mapping.keys()):
        if normalize_username(key) == safe_user:
            mapping.pop(key, None)
            removed += 1
    return removed


def remove_user_from_runtime_state(username: str) -> dict:
    username = normalize_username(username)
    removed = {"sessions": 0, "stream_sessions": 0, "screen_sessions": 0, "paint_states": 0}
    with AUTH_LOCK:
        for token, session in list(AUTH_SESSIONS.items()):
            if normalize_username(session.get("username", "")) == username:
                AUTH_SESSIONS.pop(token, None)
                AUTH_REVOKED_SESSIONS[token] = {"reason": "user_deleted", "username": username, "at": time.time()}
                removed["sessions"] += 1
    server_database_delete_auth_sessions(username=username)
    with CHAT_LOCK:
        CHAT_ONLINE.pop(username, None)
        CHAT_ONLINE_FIRST_SEEN.pop(username, None)
    with USER_ACTIVITY_LOCK:
        USER_ACTIVITY.pop(username, None)
    with STREAM_LOCK:
        for session_id, session in list(STREAM_SESSIONS.items()):
            if normalize_username(session.get("username", "")) == username:
                STREAM_SESSIONS.pop(session_id, None)
                removed["stream_sessions"] += 1
    with SCREEN_LOCK:
        for session_id, session in list(SCREEN_SESSIONS.items()):
            if normalize_username(session.get("username", "")) == username:
                SCREEN_SESSIONS.pop(session_id, None)
                removed["screen_sessions"] += 1
    with PAINT_LOCK:
        if username in PAINT_STATES:
            PAINT_STATES.pop(username, None)
            removed["paint_states"] += 1
    invalidate_auth_me_cache(username)
    return removed


def prune_user_from_known_state(username: str) -> int:
    username = normalize_username(username)
    changed_count = 0
    with ADMIN_LOCK:
        admins = read_admins_locked()
        if username in admins:
            admins.discard(username)
            write_admins_locked(admins)
            changed_count += 1
    with AUTH_LOCK:
        pending = load_pending_users()
        if pop_username_keys(pending, username):
            save_pending_users(pending)
            changed_count += 1
        reset_state = load_password_reset_state()
        if pop_username_keys(reset_state, username):
            save_password_reset_state(reset_state)
            changed_count += 1
    with LESSON_TASK_LOCK:
        if delete_lesson_task_user_locked(username):
            changed_count += 1
    with LESSON_TASK_NOTICE_LOCK:
        payload = read_lesson_task_notices_locked()
        by_user = payload.get("by_user") if isinstance(payload.get("by_user"), dict) else {}
        if pop_username_keys(by_user, username):
            write_lesson_task_notices_locked(payload, username)
            changed_count += 1
    with VOCAB_LEADERBOARD_PERIOD_LOCK:
        state = load_vocab_leaderboard_period_state()
        users = state.get("users") if isinstance(state.get("users"), dict) else {}
        if pop_username_keys(users, username):
            write_vocab_leaderboard_period_state(state)
            changed_count += 1
    with VOCAB_LEADERBOARD_REWARD_LOCK:
        state = load_vocab_leaderboard_reward_state()
        changed = False
        claims = state.get("claims") if isinstance(state.get("claims"), dict) else {}
        if pop_username_keys(claims, username):
            changed = True
        closed = state.get("closed") if isinstance(state.get("closed"), dict) else {}
        for scope_closed in closed.values():
            if not isinstance(scope_closed, dict):
                continue
            for period in scope_closed.values():
                if not isinstance(period, dict):
                    continue
                rows = period.get("rows") if isinstance(period.get("rows"), list) else []
                next_rows = [row for row in rows if not (isinstance(row, dict) and normalize_username(row.get("username", "")) == username)]
                if len(next_rows) != len(rows):
                    period["rows"] = next_rows
                    changed = True
                claimed = period.get("claimed") if isinstance(period.get("claimed"), dict) else {}
                if pop_username_keys(claimed, username):
                    changed = True
        if changed:
            write_vocab_leaderboard_reward_state(state)
            changed_count += 1
    with VOCAB_LEADERBOARD_VIEWER_LOCK:
        state = load_vocab_leaderboard_viewer_state()
        viewers = state.get("viewers") if isinstance(state.get("viewers"), dict) else {}
        if pop_username_keys(viewers, username):
            write_vocab_leaderboard_viewer_state(state)
            changed_count += 1
    with VOCAB_LEADERBOARD_SOCIAL_LOCK:
        state = load_vocab_leaderboard_social_state()
        changed = False
        for root_key in ("statuses", "reactions"):
            root_map = state.get(root_key) if isinstance(state.get(root_key), dict) else {}
            for scope_map in root_map.values():
                if pop_username_keys(scope_map, username):
                    changed = True
        reactions = state.get("reactions") if isinstance(state.get("reactions"), dict) else {}
        for scope_map in reactions.values():
            if not isinstance(scope_map, dict):
                continue
            for target_reactions in scope_map.values():
                if not isinstance(target_reactions, dict):
                    continue
                for reaction_row in list(target_reactions.values()):
                    users = reaction_row.get("users") if isinstance(reaction_row, dict) and isinstance(reaction_row.get("users"), dict) else {}
                    if pop_username_keys(users, username):
                        changed = True
        if changed:
            write_vocab_leaderboard_social_state(state)
            changed_count += 1
    with VOCAB_LEADERBOARD_CHAT_LOCK:
        state = load_vocab_leaderboard_chat_state()
        messages = state.get("messages") if isinstance(state.get("messages"), list) else []
        next_messages = [row for row in messages if not (isinstance(row, dict) and normalize_username(row.get("username", "")) == username)]
        if len(next_messages) != len(messages):
            if vocab_leaderboard_chat_uses_postgres():
                VOCAB_LEADERBOARD_CHAT_STATE_CACHE["state"] = None
                VOCAB_LEADERBOARD_CHAT_STATE_CACHE["dirty"] = False
            else:
                state["messages"] = next_messages
                write_vocab_leaderboard_chat_state(state)
            changed_count += 1
    with VOCAB_LEADERBOARD_LOCK:
        state = load_vocab_leaderboard_rank_state()
        changed = False
        boards = state.get("boards") if isinstance(state.get("boards"), dict) else {}
        for board in boards.values():
            if not isinstance(board, dict):
                continue
            for key in ("ranks", "moves"):
                rows = board.get(key) if isinstance(board.get(key), dict) else {}
                if pop_username_keys(rows, username):
                    changed = True
        if changed:
            write_vocab_leaderboard_rank_state(state)
            changed_count += 1
    with SHARED_WORLD_LOCK:
        state = load_shared_world_state()
        players = state.get("players") if isinstance(state.get("players"), dict) else {}
        if pop_username_keys(players, username):
            write_shared_world_state(state, force=True)
            changed_count += 1
    with SHARED_WORLD_LOCK:
        state = load_shared_world_battle_state()
        changed = False
        for key in ("invites", "declines", "battles"):
            rows = state.get(key) if isinstance(state.get(key), dict) else {}
            for row_key, row in list(rows.items()):
                if normalize_username(row_key) == username or json_mentions_username(row, username):
                    rows.pop(row_key, None)
                    changed = True
        if changed:
            write_shared_world_battle_state(state, force=True)
            changed_count += 1
    try:
        users = load_shared_world_battle_word_history()
        if pop_username_keys(users, username):
            write_shared_world_battle_word_history(users)
            changed_count += 1
    except Exception:
        pass
    with QM_CITY_TRAINING_LOCK:
        state = load_qm_city_training_state()
        users = state.get("users") if isinstance(state.get("users"), dict) else {}
        if pop_username_keys(users, username):
            write_qm_city_training_state(state)
            changed_count += 1
    with WORD_AGENT_HISTORY_LOCK:
        payload = read_word_agent_history()
        rows = payload.get("history") if isinstance(payload.get("history"), list) else []
        next_rows = [row for row in rows if not (isinstance(row, dict) and normalize_username(row.get("username", "")) == username)]
        if len(next_rows) != len(rows):
            write_word_agent_history({"version": 1, "history": next_rows, "updated_at": utc_timestamp()})
            changed_count += 1
    try:
        state = load_space_leaderboard_activity_state(clone=False)
        boards = state.get("boards") if isinstance(state.get("boards"), dict) else {}
        changed = False
        for board in boards.values():
            users = board.get("users") if isinstance(board, dict) and isinstance(board.get("users"), dict) else {}
            if pop_username_keys(users, username):
                changed = True
        if changed:
            write_space_leaderboard_activity_state(state)
            changed_count += 1
    except Exception:
        pass
    return changed_count


def json_mentions_username(value: object, username: str) -> bool:
    username = normalize_username(username)
    if not username:
        return False
    if isinstance(value, dict):
        for key, item in value.items():
            if clean(key).lower() in {"username", "user", "u", "target_user", "from", "to", "actor", "owner", "updated_by"} and normalize_username(item) == username:
                return True
            if json_mentions_username(item, username):
                return True
    elif isinstance(value, list):
        return any(json_mentions_username(item, username) for item in value)
    return False


# Added 2026-07-09: removes deleted users from JSON payloads that keep per-user maps/history rows.
def prune_username_from_json_value(value: object, username: str) -> tuple[object, bool]:
    username = normalize_username(username)
    if not username:
        return value, False
    if isinstance(value, dict):
        changed = False
        next_value = {}
        for key, item in value.items():
            if normalize_username(key) == username:
                changed = True
                continue
            next_item, item_changed = prune_username_from_json_value(item, username)
            next_value[key] = next_item
            changed = changed or item_changed
        return next_value, changed
    if isinstance(value, list):
        changed = False
        next_rows = []
        for item in value:
            if isinstance(item, dict) and json_mentions_username(item, username):
                changed = True
                continue
            next_item, item_changed = prune_username_from_json_value(item, username)
            next_rows.append(next_item)
            changed = changed or item_changed
        return next_rows, changed
    return value, False


# Updated 2026-07-20: dashboard events are deleted transactionally by server_database_delete_user().
def prune_user_from_dashboard_logs(username: str, result: dict) -> int:
    return 0


# Updated 2026-07-20: clears legacy embedded user rows from SQLite Structure assets without JSON fallback.
def scrub_user_from_structure_json(username: str, result: dict) -> int:
    username = normalize_username(username)
    if not username:
        return 0
    touched = 0
    try:
        for logical_path, raw in iter_structure_assets():
            try:
                text = raw.decode("utf-8-sig", errors="replace")
                if username not in text:
                    continue
                payload = json.loads(text)
                if not isinstance(payload, (dict, list)):
                    continue
                next_payload, changed = prune_username_from_json_value(payload, username)
                if changed:
                    write_structure_asset_json(logical_path, next_payload)
                    touched += 1
            except Exception as exc:
                result.setdefault("errors", []).append(f"{logical_path}: {exc}")
    except Exception as exc:
        result.setdefault("errors", []).append(f"Structure: {exc}")
    return touched


# Added 2026-07-09: clears per-user RAM caches after account/data deletion.
def clear_deleted_user_ram_caches(username: str, result: dict) -> int:
    username = normalize_username(username)
    if not username:
        return 0
    cleared = 0
    cache_pairs = [
        ("USER_LINES_RAM_CACHE", "USER_LINES_RAM_CACHE_LOCK"),
        ("ENSURE_SERVER_DATA_FOLDERS_CACHE", "ENSURE_SERVER_DATA_FOLDERS_CACHE_LOCK"),
        ("INVENTORY_RAM_CACHE", ""),
        ("VOCAB_LEADERBOARD_REWARD_CHECK_CACHE", ""),
    ]
    for cache_name, lock_name in cache_pairs:
        cache = globals().get(cache_name)
        if not isinstance(cache, dict):
            continue
        lock = globals().get(lock_name) if lock_name else None
        try:
            if lock is not None:
                with lock:
                    if cache.pop(username, None) is not None:
                        cleared += 1
            elif cache.pop(username, None) is not None:
                cleared += 1
        except Exception as exc:
            result.setdefault("errors", []).append(f"{cache_name}: {exc}")
    try:
        backfill_cache = globals().get("SPACE_LEADERBOARD_BACKFILL_CACHE")
        if isinstance(backfill_cache, dict):
            backfill_cache.clear()
            cleared += 1
    except Exception as exc:
        result.setdefault("errors", []).append(f"SPACE_LEADERBOARD_BACKFILL_CACHE: {exc}")
    try:
        invalidate_vocab_leaderboard_ram_cache(schedule_refresh=False)
        cleared += 1
    except Exception as exc:
        result.setdefault("errors", []).append(f"leaderboard-cache: {exc}")
    return cleared


def delete_user_data(username: str) -> dict:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    if username.lower() in reserved_user_data_names():
        raise RuntimeError("Ten nay trung voi thu muc he thong cua server, khong the xoa bang cong cu user.")
    had_user_data = learner_user_exists(username)
    result = {
        "username": username,
        "had_user_data": had_user_data,
        "deleted_files": 0,
        "deleted_dirs": 0,
        "deleted_paths": [],
        "errors": [],
    }
    runtime_removed = remove_user_from_runtime_state(username)
    chat_result = {}
    try:
        chat_result = clear_chat_for_user(username)
    except Exception as exc:
        result["errors"].append(f"chat: {exc}")
    state_changes = prune_user_from_known_state(username)

    allowed_roots = (USER_ROOT, MAIN_SERVER_USER_ROOT, SERVER_DATA_ROOT, USER_AVATAR_DIR, USER_PROFILE_PHOTO_DIR, TASK_NOTICE_AVATAR_DIR)
    delete_matching_user_files(USER_AVATAR_DIR, f"{username}-*", result)
    delete_matching_user_files(USER_PROFILE_PHOTO_DIR, f"{username}-profile-*", result)
    delete_matching_user_files(TASK_NOTICE_AVATAR_DIR, f"{username}-*", result)
    for path in [
        *main_vocab_progress_paths(username),
        *main_vocab_learned_roots(username),
        *main_server_user_dirs(username),
        server_data_user_folder_path(username),
        user_folder_path(username),
        user_file_path(username),
    ]:
        safe_delete_user_path(path, allowed_roots, result)

    invalidate_auth_me_cache(username)
    with LESSON_PROGRESS_CACHE_LOCK:
        prefix_candidates = (
            f"space-w:{username.lower()}",
            f"space-q:{username.lower()}",
            f"space-v:{username.lower()}",
            f"space-p:{username.lower()}",
            f"space-pdf:{username.lower()}",
            f"lesson-time:{username.lower()}",
        )
        for key in list(LESSON_PROGRESS_CACHE.keys()):
            if str(key).startswith(prefix_candidates):
                LESSON_PROGRESS_CACHE.pop(key, None)
    clear_lesson_metadata_cache()
    clear_space_progress_store_user(username)
    # Flush any pending task/notice writes (the RAM store is global across all
    # users) before dropping the cache so a delete never discards another
    # learner's unsaved changes.
    try:
        flush_lesson_tasks_ram_cache(True)
        flush_lesson_task_notices_ram_cache(True)
    except Exception:
        pass
    with LESSON_TASKS_RAM_CACHE_LOCK:
        LESSON_TASKS_RAM_CACHE.clear()
    with LESSON_TASK_NOTICES_RAM_CACHE_LOCK:
        LESSON_TASK_NOTICES_RAM_CACHE.clear()
    log_rows_removed = prune_user_from_dashboard_logs(username, result)
    structure_files_touched = scrub_user_from_structure_json(username, result)
    database_delete = globals().get("server_database_delete_user")
    if callable(database_delete):
        try:
            result["database"] = database_delete(username)
        except Exception as exc:
            result["errors"].append(f"database: {exc}")
    ram_caches_cleared = clear_deleted_user_ram_caches(username, result)
    clear_server_data_list_cache()
    try:
        refresh_server_data_manifest_now("user-delete")
    except Exception as exc:
        result["errors"].append(f"manifest: {exc}")
    result.update(
        {
            "ok": not result["errors"],
            "revoked_sessions": runtime_removed.get("sessions", 0),
            "runtime_removed": runtime_removed,
            "chat": chat_result,
            "state_changes": state_changes,
            "log_rows_removed": log_rows_removed,
            "structure_files_touched": structure_files_touched,
            "ram_caches_cleared": ram_caches_cleared,
            "deleted_path_count": len(result.get("deleted_paths", [])),
        }
    )
    return result
