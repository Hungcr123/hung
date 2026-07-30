# Loaded by FUTURE.server_parts.09_vocab_world_game into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

import copy


VOCAB_LEADERBOARD_REWARD_STATE_CACHE: dict[str, object] = {"signature": None, "state": None}
VOCAB_LEADERBOARD_REWARD_CANDIDATE_CACHE: dict[str, object] = {"signature": None, "users": set()}


def vocab_leaderboard_document_mtime(path: Path) -> int:
    return int(server_database_document_signature(path)[1] or 0)


def clone_vocab_leaderboard_reward_state(state: dict | None = None) -> dict:
    # Added 2026-07-06: isolates reward-claim RAM cache from request mutations.
    source = state if isinstance(state, dict) else {}
    return {
        "version": 1,
        "updated_at": clean(source.get("updated_at", "")),
        "closed": copy.deepcopy(source.get("closed") if isinstance(source.get("closed"), dict) else {}),
        "claims": copy.deepcopy(source.get("claims") if isinstance(source.get("claims"), dict) else {}),
    }


def vocab_leaderboard_reward_file_signature() -> tuple:
    return server_database_document_signature(VOCAB_LEADERBOARD_REWARD_FILE)


def load_vocab_leaderboard_reward_state(clone: bool = True) -> dict:
    signature = vocab_leaderboard_reward_file_signature()
    cached = VOCAB_LEADERBOARD_REWARD_STATE_CACHE.get("state")
    if VOCAB_LEADERBOARD_REWARD_STATE_CACHE.get("signature") == signature and isinstance(cached, dict):
        return clone_vocab_leaderboard_reward_state(cached) if clone else cached
    payload = server_database_read_document_json(VOCAB_LEADERBOARD_REWARD_FILE, {})
    if isinstance(payload, dict):
        closed = payload.get("closed") if isinstance(payload.get("closed"), dict) else {}
        claims = payload.get("claims") if isinstance(payload.get("claims"), dict) else {}
        state = {
            "version": 1,
            "updated_at": clean(payload.get("updated_at", "")),
            "closed": closed,
            "claims": claims,
        }
        VOCAB_LEADERBOARD_REWARD_STATE_CACHE["signature"] = signature
        VOCAB_LEADERBOARD_REWARD_STATE_CACHE["state"] = state
        return state
    state = {"version": 1, "updated_at": "", "closed": {}, "claims": {}}
    VOCAB_LEADERBOARD_REWARD_STATE_CACHE["signature"] = signature
    VOCAB_LEADERBOARD_REWARD_STATE_CACHE["state"] = state
    return state


def write_vocab_leaderboard_reward_state(state: dict) -> None:
    SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": utc_timestamp(),
        "closed": state.get("closed") if isinstance(state.get("closed"), dict) else {},
        "claims": state.get("claims") if isinstance(state.get("claims"), dict) else {},
    }
    atomic_write_json(VOCAB_LEADERBOARD_REWARD_FILE, payload, indent=2)
    VOCAB_LEADERBOARD_REWARD_STATE_CACHE["signature"] = vocab_leaderboard_reward_file_signature()
    VOCAB_LEADERBOARD_REWARD_STATE_CACHE["state"] = payload
    VOCAB_LEADERBOARD_REWARD_CANDIDATE_CACHE["signature"] = None
    VOCAB_LEADERBOARD_REWARD_CANDIDATE_CACHE["users"] = set()


VOCAB_LEADERBOARD_VIEWER_STATE_CACHE: dict[str, object] = {"mtime_ns": -1, "state": None, "dirty": False, "timer": None}
VOCAB_LEADERBOARD_VIEWER_FLUSH_DELAY_SECONDS = 2.0


def clone_vocab_leaderboard_viewer_state(state: dict | None = None) -> dict:
    source = state if isinstance(state, dict) else {}
    viewers = source.get("viewers") if isinstance(source.get("viewers"), dict) else {}
    return {
        "version": 1,
        "updated_at": clean(source.get("updated_at", "")),
        "viewers": {
            normalize_username(username): dict(row)
            for username, row in viewers.items()
            if normalize_username(username) and isinstance(row, dict)
        },
    }


def read_vocab_leaderboard_viewer_state_disk() -> dict:
    payload = server_database_read_document_json(VOCAB_LEADERBOARD_VIEWERS_FILE, {})
    if isinstance(payload, dict):
        return clone_vocab_leaderboard_viewer_state(payload)
    return {"version": 1, "updated_at": "", "viewers": {}}


def load_vocab_leaderboard_viewer_state() -> dict:
    mtime_ns = vocab_leaderboard_document_mtime(VOCAB_LEADERBOARD_VIEWERS_FILE)
    cached = VOCAB_LEADERBOARD_VIEWER_STATE_CACHE.get("state")
    if isinstance(cached, dict) and (
        bool(VOCAB_LEADERBOARD_VIEWER_STATE_CACHE.get("dirty"))
        or int(VOCAB_LEADERBOARD_VIEWER_STATE_CACHE.get("mtime_ns", -1) or -1) == int(mtime_ns)
    ):
        return clone_vocab_leaderboard_viewer_state(cached)
    state = read_vocab_leaderboard_viewer_state_disk()
    VOCAB_LEADERBOARD_VIEWER_STATE_CACHE["mtime_ns"] = mtime_ns
    VOCAB_LEADERBOARD_VIEWER_STATE_CACHE["state"] = clone_vocab_leaderboard_viewer_state(state)
    VOCAB_LEADERBOARD_VIEWER_STATE_CACHE["dirty"] = False
    return clone_vocab_leaderboard_viewer_state(state)


def write_vocab_leaderboard_viewer_state(state: dict, force: bool = False) -> None:
    SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    viewers = state.get("viewers") if isinstance(state.get("viewers"), dict) else {}
    payload = {
        "version": 1,
        "updated_at": utc_timestamp(),
        "viewers": viewers,
    }
    VOCAB_LEADERBOARD_VIEWER_STATE_CACHE["state"] = clone_vocab_leaderboard_viewer_state(payload)
    VOCAB_LEADERBOARD_VIEWER_STATE_CACHE["dirty"] = True
    if force:
        flush_vocab_leaderboard_viewer_state(True)
    else:
        schedule_vocab_leaderboard_viewer_flush()


def flush_vocab_leaderboard_viewer_state(force: bool = False) -> None:
    if not force and not bool(VOCAB_LEADERBOARD_VIEWER_STATE_CACHE.get("dirty")):
        return
    state = clone_vocab_leaderboard_viewer_state(VOCAB_LEADERBOARD_VIEWER_STATE_CACHE.get("state") if isinstance(VOCAB_LEADERBOARD_VIEWER_STATE_CACHE.get("state"), dict) else {})
    if not state.get("viewers"):
        return
    try:
        disk_state = read_vocab_leaderboard_viewer_state_disk()
        merged = disk_state.get("viewers") if isinstance(disk_state.get("viewers"), dict) else {}
        merged.update(state.get("viewers") if isinstance(state.get("viewers"), dict) else {})
        sorted_items = sorted(
            merged.items(),
            key=lambda pair: timestamp_to_epoch(clean((pair[1] or {}).get("viewed_at", ""))) if isinstance(pair[1], dict) else 0,
            reverse=True,
        )
        payload = {"version": 1, "updated_at": utc_timestamp(), "viewers": dict(sorted_items[:200])}
        atomic_write_json(VOCAB_LEADERBOARD_VIEWERS_FILE, payload, indent=2)
        mtime_ns = vocab_leaderboard_document_mtime(VOCAB_LEADERBOARD_VIEWERS_FILE)
        VOCAB_LEADERBOARD_VIEWER_STATE_CACHE["mtime_ns"] = mtime_ns
        VOCAB_LEADERBOARD_VIEWER_STATE_CACHE["state"] = clone_vocab_leaderboard_viewer_state(payload)
        VOCAB_LEADERBOARD_VIEWER_STATE_CACHE["dirty"] = False
    except Exception as exc:
        stt_debug_log("vocab_leaderboard_viewer_flush_failed", error=str(exc))
        if postgres_backend_mode("LEADERBOARD_DOCUMENTS") == "postgres":
            raise


def schedule_vocab_leaderboard_viewer_flush() -> None:
    timer = VOCAB_LEADERBOARD_VIEWER_STATE_CACHE.get("timer")
    if isinstance(timer, threading.Timer) and timer.is_alive():
        return
    timer = threading.Timer(VOCAB_LEADERBOARD_VIEWER_FLUSH_DELAY_SECONDS, lambda: flush_vocab_leaderboard_viewer_state(True))
    timer.daemon = True
    VOCAB_LEADERBOARD_VIEWER_STATE_CACHE["timer"] = timer
    timer.start()


atexit.register(lambda: flush_vocab_leaderboard_viewer_state(True))
atexit.register(lambda: flush_vocab_leaderboard_social_state(True))
atexit.register(lambda: flush_vocab_leaderboard_chat_state(True))


def record_vocab_leaderboard_view(username: str, scope: str = "total") -> None:
    username = normalize_username(username)
    if not username or server_database_is_test_user(username):
        return
    safe_scope = clean(scope).lower()
    if safe_scope not in {"total", "day", "week", "month"}:
        safe_scope = "total"
    now = utc_timestamp()
    with VOCAB_LEADERBOARD_VIEWER_LOCK:
        state = load_vocab_leaderboard_viewer_state()
        viewers = state.setdefault("viewers", {})
        current = viewers.get(username) if isinstance(viewers.get(username), dict) else {}
        viewers[username] = {
            "username": username,
            "viewed_at": now,
            "last_scope": safe_scope,
            "views": max(0, space_w_int(current.get("views", 0), 0)) + 1,
        }
        sorted_items = sorted(
            viewers.items(),
            key=lambda pair: timestamp_to_epoch(clean((pair[1] or {}).get("viewed_at", ""))) if isinstance(pair[1], dict) else 0,
            reverse=True,
        )
        state["viewers"] = dict(sorted_items[:200])
        write_vocab_leaderboard_viewer_state(state)


def vocab_leaderboard_viewer_rows(limit: int = 80) -> list[dict]:
    with VOCAB_LEADERBOARD_VIEWER_LOCK:
        state = load_vocab_leaderboard_viewer_state()
    viewers = state.get("viewers") if isinstance(state.get("viewers"), dict) else {}
    rows = []
    for username, item in viewers.items():
        username = normalize_username(username)
        if not username or server_database_is_test_user(username) or not isinstance(item, dict):
            continue
        if username.lower() == "testuser":
            continue
        profile = read_user_profile(username)
        display_name = clean(profile.get("full_name", "")) or username
        gender = clean(profile.get("gender", "")).lower()
        if gender not in {"male", "female", "other"}:
            gender = "other"
        rows.append(
            {
                "username": username,
                "display_name": display_name,
                "gender": gender,
                "avatar": clean(profile.get("avatar", "")),
                "viewed_at": clean(item.get("viewed_at", "")),
                "last_scope": clean(item.get("last_scope", "")) or "total",
                "views": max(0, space_w_int(item.get("views", 0), 0)),
            }
        )
    rows.sort(key=lambda item: timestamp_to_epoch(clean(item.get("viewed_at", ""))), reverse=True)
    return rows[: max(1, min(200, space_w_int(limit, 80)))]


LEADERBOARD_SOCIAL_SCOPES = {"total", "day", "week", "month"}
LEADERBOARD_REACTION_KEYS = {"like", "heart", "laugh", "angry", "love", "burn", "devil", "frost"}
LEADERBOARD_STATUS_WORD_LIMIT = 30
VOCAB_LEADERBOARD_SOCIAL_STATE_CACHE: dict[str, object] = {"mtime_ns": -1, "state": None, "dirty": False, "timer": None}
VOCAB_LEADERBOARD_CHAT_STATE_CACHE: dict[str, object] = {"mtime_ns": -1, "state": None, "dirty": False, "timer": None}
VOCAB_LEADERBOARD_SOCIAL_FLUSH_DELAY_SECONDS = 2.0
VOCAB_LEADERBOARD_CHAT_FLUSH_DELAY_SECONDS = 1.0

def vocab_leaderboard_chat_uses_postgres() -> bool:
    try:
        return bool(postgres_backend_enabled("LEADERBOARD_DOCUMENTS") or postgres_backend_enabled("VOCABULARY"))
    except Exception:
        return False

def normalize_leaderboard_scope(scope: str = "total") -> str:
    safe_scope = clean(scope).lower()
    return safe_scope if safe_scope in LEADERBOARD_SOCIAL_SCOPES else "total"


def clone_vocab_leaderboard_social_state(state: dict | None = None) -> dict:
    source = state if isinstance(state, dict) else {}
    return {
        "version": 1,
        "updated_at": clean(source.get("updated_at", "")),
        "statuses": json.loads(json.dumps(source.get("statuses") if isinstance(source.get("statuses"), dict) else {}, ensure_ascii=False)),
        "reactions": json.loads(json.dumps(source.get("reactions") if isinstance(source.get("reactions"), dict) else {}, ensure_ascii=False)),
    }


def clone_vocab_leaderboard_chat_state(state: dict | None = None) -> dict:
    source = state if isinstance(state, dict) else {}
    messages = source.get("messages") if isinstance(source.get("messages"), list) else []
    return {
        "version": 1,
        "updated_at": clean(source.get("updated_at", "")),
        "messages": [dict(item) for item in messages if isinstance(item, dict)][-100:],
    }


def vocab_leaderboard_social_file_has_rows() -> bool:
    payload = server_database_read_document_json(VOCAB_LEADERBOARD_SOCIAL_FILE, {})
    return vocab_leaderboard_social_state_has_rows(payload if isinstance(payload, dict) else {})


def vocab_leaderboard_chat_file_has_rows() -> bool:
    payload = server_database_read_document_json(VOCAB_LEADERBOARD_CHAT_FILE, {})
    messages = payload.get("messages") if isinstance(payload, dict) and isinstance(payload.get("messages"), list) else []
    return any(isinstance(item, dict) for item in messages)


def backup_vocab_leaderboard_chat_file(reason: str = "protect") -> str:
    signature = server_database_document_signature(VOCAB_LEADERBOARD_CHAT_FILE)
    return f"document:{signature[3]}:{clean(reason) or 'protect'}" if signature[3] else ""


def load_vocab_leaderboard_social_state() -> dict:
    mtime_ns = vocab_leaderboard_document_mtime(VOCAB_LEADERBOARD_SOCIAL_FILE)
    cached = VOCAB_LEADERBOARD_SOCIAL_STATE_CACHE.get("state")
    if isinstance(cached, dict) and (
        bool(VOCAB_LEADERBOARD_SOCIAL_STATE_CACHE.get("dirty"))
        or int(VOCAB_LEADERBOARD_SOCIAL_STATE_CACHE.get("mtime_ns", -1) or -1) == int(mtime_ns)
    ):
        return clone_vocab_leaderboard_social_state(cached)
    payload = server_database_read_document_json(VOCAB_LEADERBOARD_SOCIAL_FILE, {})
    if isinstance(payload, dict):
        statuses = payload.get("statuses") if isinstance(payload.get("statuses"), dict) else {}
        reactions = payload.get("reactions") if isinstance(payload.get("reactions"), dict) else {}
        state = {
            "version": 1,
            "updated_at": clean(payload.get("updated_at", "")),
            "statuses": statuses,
            "reactions": reactions,
        }
        VOCAB_LEADERBOARD_SOCIAL_STATE_CACHE["mtime_ns"] = mtime_ns
        VOCAB_LEADERBOARD_SOCIAL_STATE_CACHE["state"] = clone_vocab_leaderboard_social_state(state)
        VOCAB_LEADERBOARD_SOCIAL_STATE_CACHE["dirty"] = False
        return clone_vocab_leaderboard_social_state(state)
    return {"version": 1, "updated_at": "", "statuses": {}, "reactions": {}}


def write_vocab_leaderboard_social_state(state: dict, force: bool = False) -> None:
    SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": utc_timestamp(),
        "statuses": state.get("statuses") if isinstance(state.get("statuses"), dict) else {},
        "reactions": state.get("reactions") if isinstance(state.get("reactions"), dict) else {},
    }
    VOCAB_LEADERBOARD_SOCIAL_STATE_CACHE["state"] = clone_vocab_leaderboard_social_state(payload)
    invalidate_response = globals().get("invalidate_vocab_leaderboard_response_cache")
    if callable(invalidate_response):
        invalidate_response()
    VOCAB_LEADERBOARD_SOCIAL_STATE_CACHE["dirty"] = True
    if force:
        flush_vocab_leaderboard_social_state(True)
    else:
        schedule_vocab_leaderboard_social_flush()


def flush_vocab_leaderboard_social_state(force: bool = False) -> None:
    if not force and not bool(VOCAB_LEADERBOARD_SOCIAL_STATE_CACHE.get("dirty")):
        return
    cached_state = VOCAB_LEADERBOARD_SOCIAL_STATE_CACHE.get("state")
    if force and not bool(VOCAB_LEADERBOARD_SOCIAL_STATE_CACHE.get("dirty")) and not isinstance(cached_state, dict):
        # Updated 2026-07-06: shutdown flush must not overwrite existing social data with an unloaded empty cache.
        return
    state = clone_vocab_leaderboard_social_state(cached_state if isinstance(cached_state, dict) else {})
    if force and not bool(VOCAB_LEADERBOARD_SOCIAL_STATE_CACHE.get("dirty")) and not vocab_leaderboard_social_state_has_rows(state) and vocab_leaderboard_social_file_has_rows():
        # Added 2026-07-09: shutdown flush must not replace non-empty disk social state with an idle empty cache.
        return
    try:
        atomic_write_json(VOCAB_LEADERBOARD_SOCIAL_FILE, state, indent=2)
        mtime_ns = vocab_leaderboard_document_mtime(VOCAB_LEADERBOARD_SOCIAL_FILE)
        VOCAB_LEADERBOARD_SOCIAL_STATE_CACHE["mtime_ns"] = mtime_ns
        VOCAB_LEADERBOARD_SOCIAL_STATE_CACHE["state"] = clone_vocab_leaderboard_social_state(state)
        VOCAB_LEADERBOARD_SOCIAL_STATE_CACHE["dirty"] = False
    except Exception as exc:
        stt_debug_log("vocab_leaderboard_social_flush_failed", error=str(exc))
        if postgres_backend_mode("LEADERBOARD_DOCUMENTS") == "postgres":
            raise


def schedule_vocab_leaderboard_social_flush() -> None:
    timer = VOCAB_LEADERBOARD_SOCIAL_STATE_CACHE.get("timer")
    if isinstance(timer, threading.Timer) and timer.is_alive():
        return
    timer = threading.Timer(VOCAB_LEADERBOARD_SOCIAL_FLUSH_DELAY_SECONDS, lambda: flush_vocab_leaderboard_social_state(True))
    timer.daemon = True
    VOCAB_LEADERBOARD_SOCIAL_STATE_CACHE["timer"] = timer
    timer.start()


def leaderboard_status_word_count(value: object) -> tuple[str, int]:
    text = " ".join(clean(value).split())
    return text, len([part for part in text.split(" ") if part])


def leaderboard_status_text(value: object, limit: int = 280) -> str:
    text, _count = leaderboard_status_word_count(value)
    words = [part for part in text.split(" ") if part]
    if len(words) > LEADERBOARD_STATUS_WORD_LIMIT:
        text = " ".join(words[:LEADERBOARD_STATUS_WORD_LIMIT])
    return text[: max(0, min(280, int(limit or 280)))]


def set_vocab_leaderboard_status(username: str, scope: str, status: str) -> dict:
    username = normalize_username(username)
    if not username:
        return {"ok": False, "error": "Missing user."}
    safe_scope = normalize_leaderboard_scope(scope)
    text, word_count = leaderboard_status_word_count(status)
    if word_count > LEADERBOARD_STATUS_WORD_LIMIT:
        return {
            "ok": False,
            "error": f"Status is limited to {LEADERBOARD_STATUS_WORD_LIMIT} words. Current: {word_count}.",
            "word_count": word_count,
            "word_limit": LEADERBOARD_STATUS_WORD_LIMIT,
        }
    text = leaderboard_status_text(text)
    with VOCAB_LEADERBOARD_SOCIAL_LOCK:
        state = load_vocab_leaderboard_social_state()
        statuses = state.setdefault("statuses", {})
        scope_statuses = statuses.setdefault(safe_scope, {})
        if text:
            scope_statuses[username] = {
                "username": username,
                "scope": safe_scope,
                "text": text,
                "period_key": vocab_period_bucket(safe_scope),
                "updated_at": utc_timestamp(),
            }
        else:
            scope_statuses.pop(username, None)
            reactions = state.setdefault("reactions", {})
            scope_reactions = reactions.get(safe_scope) if isinstance(reactions.get(safe_scope), dict) else {}
            scope_reactions.pop(username, None)
        state["updated_at"] = utc_timestamp()
        write_vocab_leaderboard_social_state(state)
    return {"ok": True, "scope": safe_scope, "status": text}


def toggle_vocab_leaderboard_reaction(actor: str, target: str, scope: str, reaction: str) -> dict:
    actor = normalize_username(actor)
    target = normalize_username(target)
    safe_scope = normalize_leaderboard_scope(scope)
    safe_reaction = clean(reaction).lower()
    allowed_reactions = leaderboard_reaction_key_set() or {"love", "burn", "devil", "frost"}
    if safe_reaction not in allowed_reactions:
        safe_reaction = sorted(allowed_reactions)[0]
    if not actor or not target:
        return {"ok": False, "error": "Missing user."}
    if actor == target:
        return {"ok": False, "error": "You cannot react to your own status."}
    with VOCAB_LEADERBOARD_SOCIAL_LOCK:
        state = load_vocab_leaderboard_social_state()
        statuses = state.setdefault("statuses", {})
        scope_statuses = statuses.get(safe_scope) if isinstance(statuses.get(safe_scope), dict) else {}
        status_row = scope_statuses.get(target) if isinstance(scope_statuses.get(target), dict) else {}
        if not leaderboard_status_text(status_row.get("text", "")):
            return {"ok": False, "error": "This status is no longer active."}
        reactions = state.setdefault("reactions", {})
        scope_reactions = reactions.setdefault(safe_scope, {})
        target_reactions = scope_reactions.setdefault(target, {})
        # One reaction per actor per target per scope. Selecting a new icon replaces
        # the previous one; selecting the same icon keeps it active.
        for key in list(target_reactions.keys()):
            row = target_reactions.get(key) if isinstance(target_reactions.get(key), dict) else {}
            users = row.get("users") if isinstance(row.get("users"), dict) else {}
            if actor in users:
                users.pop(actor, None)
                row["users"] = users
                if users:
                    target_reactions[key] = row
                else:
                    target_reactions.pop(key, None)
        row = target_reactions.setdefault(safe_reaction, {})
        users = row.get("users") if isinstance(row.get("users"), dict) else {}
        users[actor] = utc_timestamp()
        row["users"] = users
        row["updated_at"] = utc_timestamp()
        target_reactions[safe_reaction] = row
        state["updated_at"] = utc_timestamp()
        write_vocab_leaderboard_social_state(state)
        summary = vocab_leaderboard_social_summary_for_user(target, safe_scope, state, actor)
    return {"ok": True, "scope": safe_scope, "target": target, "reaction": safe_reaction, "active": True, "social": summary}


def vocab_leaderboard_social_summary_for_user(
    username: str,
    scope: str,
    state: dict | None = None,
    viewer: str = "",
    reaction_options: list[dict] | None = None,
) -> dict:
    username = normalize_username(username)
    safe_scope = normalize_leaderboard_scope(scope)
    viewer = normalize_username(viewer)
    source = state if isinstance(state, dict) else load_vocab_leaderboard_social_state()
    statuses = source.get("statuses") if isinstance(source.get("statuses"), dict) else {}
    scope_statuses = statuses.get(safe_scope) if isinstance(statuses.get(safe_scope), dict) else {}
    status_row = scope_statuses.get(username) if isinstance(scope_statuses.get(username), dict) else {}
    reactions = source.get("reactions") if isinstance(source.get("reactions"), dict) else {}
    scope_reactions = reactions.get(safe_scope) if isinstance(reactions.get(safe_scope), dict) else {}
    target_reactions = scope_reactions.get(username) if isinstance(scope_reactions.get(username), dict) else {}
    counts = {}
    mine = []
    option_rows = reaction_options if isinstance(reaction_options, list) else leaderboard_reaction_options()
    configured_keys = [clean(item.get("key", "")).lower() for item in option_rows]
    stored_keys = [clean(key).lower() for key in target_reactions.keys() if clean(key)]
    summary_keys = []
    for key in [*configured_keys, *stored_keys]:
        if key and key not in summary_keys:
            summary_keys.append(key)
    for key in summary_keys:
        row = target_reactions.get(key) if isinstance(target_reactions.get(key), dict) else {}
        users = row.get("users") if isinstance(row.get("users"), dict) else {}
        count = len([name for name in users if normalize_username(name)])
        counts[key] = count
        if viewer and viewer in users:
            mine.append(key)
    return {
        "status": leaderboard_status_text(status_row.get("text", "")),
        "status_updated_at": clean(status_row.get("updated_at", "")),
        "status_period_key": clean(status_row.get("period_key", "")),
        "reactions": counts,
        "my_reactions": mine,
        "my_reaction": mine[0] if mine else "",
    }


def prune_vocab_leaderboard_social_state(state: dict, boards: dict[str, list[dict]] | None = None) -> bool:
    if not isinstance(state, dict):
        return False
    statuses = state.setdefault("statuses", {})
    reactions = state.setdefault("reactions", {})
    changed = False
    now_epoch = time.time()
    current_periods = {scope: vocab_period_bucket(scope, now_epoch) for scope in ("day", "week", "month")}
    active_top: dict[str, set[str]] = {}
    if isinstance(boards, dict):
        for scope, rows in boards.items():
            safe_scope = normalize_leaderboard_scope(scope)
            allowed: set[str] = set()
            for row in rows if isinstance(rows, list) else []:
                rank = space_w_int(row.get("rank", 0), 0) if isinstance(row, dict) else 0
                score = space_w_int(row.get("score", row.get("total_words", 0)), 0) if isinstance(row, dict) else 0
                username = normalize_username(row.get("username", "")) if isinstance(row, dict) else ""
                if username and rank and rank <= 3 and score > 0 and not row.get("placeholder"):
                    allowed.add(username)
            active_top[safe_scope] = allowed
    for raw_scope in list(statuses.keys()):
        safe_scope = normalize_leaderboard_scope(raw_scope)
        scope_statuses = statuses.get(raw_scope) if isinstance(statuses.get(raw_scope), dict) else {}
        if raw_scope != safe_scope:
            statuses.pop(raw_scope, None)
            scope_statuses = statuses.setdefault(safe_scope, scope_statuses)
            changed = True
        scope_reactions = reactions.get(safe_scope) if isinstance(reactions.get(safe_scope), dict) else {}
        for username in list(scope_statuses.keys()):
            row = scope_statuses.get(username) if isinstance(scope_statuses.get(username), dict) else {}
            remove = False
            if not leaderboard_status_text(row.get("text", "")):
                remove = True
            if safe_scope in current_periods:
                period_key = clean(row.get("period_key", ""))
                if not period_key:
                    row["period_key"] = current_periods[safe_scope]
                    scope_statuses[username] = row
                    changed = True
                elif period_key != current_periods[safe_scope]:
                    remove = True
            if safe_scope in active_top and normalize_username(username) not in active_top[safe_scope]:
                remove = True
            if remove:
                scope_statuses.pop(username, None)
                if isinstance(scope_reactions, dict):
                    scope_reactions.pop(username, None)
                changed = True
        statuses[safe_scope] = scope_statuses
        if isinstance(scope_reactions, dict):
            reactions[safe_scope] = scope_reactions
    state["statuses"] = statuses
    state["reactions"] = reactions
    if changed:
        state["updated_at"] = utc_timestamp()
    return changed


def clear_vocab_leaderboard_social_scopes(scopes: list[str] | tuple[str, ...] | set[str]) -> None:
    requested = [clean(scope).lower() for scope in scopes if clean(scope).lower() in LEADERBOARD_SOCIAL_SCOPES]
    if not requested:
        return
    with VOCAB_LEADERBOARD_SOCIAL_LOCK:
        state = load_vocab_leaderboard_social_state()
        statuses = state.setdefault("statuses", {})
        reactions = state.setdefault("reactions", {})
        changed = False
        for scope in requested:
            if statuses.pop(scope, None) is not None:
                changed = True
            if reactions.pop(scope, None) is not None:
                changed = True
        if changed:
            state["updated_at"] = utc_timestamp()
            write_vocab_leaderboard_social_state(state)


# Added 2026-07-06: lets Top payload hits skip per-row social scans when no social data exists.
def vocab_leaderboard_social_state_has_rows(state: dict | None = None) -> bool:
    source = state if isinstance(state, dict) else {}
    statuses = source.get("statuses") if isinstance(source.get("statuses"), dict) else {}
    reactions = source.get("reactions") if isinstance(source.get("reactions"), dict) else {}
    for scope_rows in statuses.values():
        if isinstance(scope_rows, dict) and any(isinstance(row, dict) and leaderboard_status_text(row.get("text", "")) for row in scope_rows.values()):
            return True
    for scope_rows in reactions.values():
        if not isinstance(scope_rows, dict):
            continue
        for target_rows in scope_rows.values():
            if not isinstance(target_rows, dict):
                continue
            for reaction_row in target_rows.values():
                users = reaction_row.get("users") if isinstance(reaction_row, dict) and isinstance(reaction_row.get("users"), dict) else {}
                if any(normalize_username(name) for name in users):
                    return True
    return False


def attach_vocab_leaderboard_social(
    boards: dict[str, list[dict]],
    viewer: str = "",
    reaction_options: list[dict] | None = None,
) -> dict[str, list[dict]]:
    with VOCAB_LEADERBOARD_SOCIAL_LOCK:
        state = load_vocab_leaderboard_social_state()
        has_social_rows = vocab_leaderboard_social_state_has_rows(state)
        if has_social_rows and prune_vocab_leaderboard_social_state(state, boards):
            write_vocab_leaderboard_social_state(state)
    option_rows = reaction_options if isinstance(reaction_options, list) else leaderboard_reaction_options()
    if not has_social_rows:
        empty_social = {
            "status": "",
            "status_updated_at": "",
            "status_period_key": "",
            "reactions": {clean(item.get("key", "")).lower(): 0 for item in option_rows if clean(item.get("key", ""))},
            "my_reactions": [],
            "my_reaction": "",
        }
        for rows in boards.values():
            for row in rows if isinstance(rows, list) else []:
                if isinstance(row, dict):
                    row["social"] = {
                        **empty_social,
                        "reactions": dict(empty_social.get("reactions", {})),
                        "my_reactions": [],
                    }
        return boards
    for scope, rows in boards.items():
        safe_scope = normalize_leaderboard_scope(scope)
        for row in rows:
            username = normalize_username(row.get("username", ""))
            row["social"] = vocab_leaderboard_social_summary_for_user(username, safe_scope, state, viewer, option_rows)
    return boards


def vocab_leaderboard_my_statuses(username: str, state: dict | None = None) -> dict:
    username = normalize_username(username)
    source = state if isinstance(state, dict) else load_vocab_leaderboard_social_state()
    statuses = source.get("statuses") if isinstance(source.get("statuses"), dict) else {}
    result = {}
    for scope in ("total", "day", "week", "month"):
        scope_statuses = statuses.get(scope) if isinstance(statuses.get(scope), dict) else {}
        row = scope_statuses.get(username) if isinstance(scope_statuses.get(username), dict) else {}
        result[scope] = leaderboard_status_text(row.get("text", ""))
    return result


def load_vocab_leaderboard_chat_state() -> dict:
    if vocab_leaderboard_chat_uses_postgres():
        cached = VOCAB_LEADERBOARD_CHAT_STATE_CACHE.get("state")
        if isinstance(cached, dict) and not bool(VOCAB_LEADERBOARD_CHAT_STATE_CACHE.get("dirty")):
            return clone_vocab_leaderboard_chat_state(cached)
        payload = postgres_load_world_chat_state("world")
        messages = payload.get("messages") if isinstance(payload, dict) and isinstance(payload.get("messages"), list) else []
        state = {
            "version": 1,
            "updated_at": utc_timestamp(),
            "messages": [dict(item) for item in messages][-100:],
        }
        VOCAB_LEADERBOARD_CHAT_STATE_CACHE["mtime_ns"] = int(payload.get("revision", 0) or 0)
        VOCAB_LEADERBOARD_CHAT_STATE_CACHE["state"] = clone_vocab_leaderboard_chat_state(state)
        VOCAB_LEADERBOARD_CHAT_STATE_CACHE["dirty"] = False
        return clone_vocab_leaderboard_chat_state(state)
    mtime_ns = vocab_leaderboard_document_mtime(VOCAB_LEADERBOARD_CHAT_FILE)
    cached = VOCAB_LEADERBOARD_CHAT_STATE_CACHE.get("state")
    if isinstance(cached, dict) and (
        bool(VOCAB_LEADERBOARD_CHAT_STATE_CACHE.get("dirty"))
        or int(VOCAB_LEADERBOARD_CHAT_STATE_CACHE.get("mtime_ns", -1) or -1) == int(mtime_ns)
    ):
        return clone_vocab_leaderboard_chat_state(cached)
    payload = server_database_read_document_json(VOCAB_LEADERBOARD_CHAT_FILE, {})
    if isinstance(payload, dict):
        messages = payload.get("messages") if isinstance(payload.get("messages"), list) else []
        state = {
            "version": 1,
            "updated_at": clean(payload.get("updated_at", "")),
            "messages": [item for item in messages if isinstance(item, dict)][-100:],
        }
        VOCAB_LEADERBOARD_CHAT_STATE_CACHE["mtime_ns"] = mtime_ns
        VOCAB_LEADERBOARD_CHAT_STATE_CACHE["state"] = clone_vocab_leaderboard_chat_state(state)
        VOCAB_LEADERBOARD_CHAT_STATE_CACHE["dirty"] = False
        return clone_vocab_leaderboard_chat_state(state)
    return {"version": 1, "updated_at": "", "messages": []}


def warm_vocab_leaderboard_chat_cache(limit: int = 100) -> dict:
    if not vocab_leaderboard_chat_uses_postgres():
        return {"ok": False, "source": "postgresql", "messages": 0, "revision": 0, "load_ms": 0.0}
    started = time.perf_counter()
    state = load_vocab_leaderboard_chat_state()
    max_rows = max(1, min(100, space_w_int(limit, 100)))
    messages = [dict(item) for item in (state.get("messages") if isinstance(state.get("messages"), list) else [])][-max_rows:]
    revision = vocab_leaderboard_chat_revision({"messages": messages})
    load_ms = round((time.perf_counter() - started) * 1000.0, 3)
    print(
        f"World Chat cache ready: room=world messages={len(messages)} revision={revision} source=postgresql load_ms={load_ms}",
        flush=True,
    )
    return {"ok": True, "source": "postgresql", "messages": len(messages), "revision": revision, "load_ms": load_ms}

def write_vocab_leaderboard_chat_state(state: dict, force: bool = False) -> None:
    if vocab_leaderboard_chat_uses_postgres():
        payload_messages = [dict(item) for item in (state.get("messages") if isinstance(state.get("messages"), list) else []) if isinstance(item, dict)][-100:]
        cache_state = {
            "version": 1,
            "updated_at": utc_timestamp(),
            "messages": payload_messages[-100:],
        }
        VOCAB_LEADERBOARD_CHAT_STATE_CACHE["state"] = clone_vocab_leaderboard_chat_state(cache_state)
        VOCAB_LEADERBOARD_CHAT_STATE_CACHE["mtime_ns"] = int(payload_messages[-1].get("id", 0) if payload_messages else 0)
        VOCAB_LEADERBOARD_CHAT_STATE_CACHE["dirty"] = False
        return
    SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": utc_timestamp(),
        "messages": (state.get("messages") if isinstance(state.get("messages"), list) else [])[-100:],
    }
    VOCAB_LEADERBOARD_CHAT_STATE_CACHE["state"] = clone_vocab_leaderboard_chat_state(payload)
    VOCAB_LEADERBOARD_CHAT_STATE_CACHE["dirty"] = True
    if force:
        flush_vocab_leaderboard_chat_state(True)
    else:
        schedule_vocab_leaderboard_chat_flush()


def flush_vocab_leaderboard_chat_state(force: bool = False) -> None:
    if vocab_leaderboard_chat_uses_postgres():
        cached_state = VOCAB_LEADERBOARD_CHAT_STATE_CACHE.get("state")
        if not isinstance(cached_state, dict):
            return
        if not bool(VOCAB_LEADERBOARD_CHAT_STATE_CACHE.get("dirty")):
            return
        try:
            write_vocab_leaderboard_chat_state(cached_state, True)
        except Exception:
            pass
        return
    if not force and not bool(VOCAB_LEADERBOARD_CHAT_STATE_CACHE.get("dirty")):
        return
    cached_state = VOCAB_LEADERBOARD_CHAT_STATE_CACHE.get("state")
    if force and not bool(VOCAB_LEADERBOARD_CHAT_STATE_CACHE.get("dirty")) and not isinstance(cached_state, dict):
        # Updated 2026-07-06: shutdown flush must not overwrite existing world chat with an unloaded empty cache.
        return
    state = clone_vocab_leaderboard_chat_state(cached_state if isinstance(cached_state, dict) else {})
    if force and not bool(VOCAB_LEADERBOARD_CHAT_STATE_CACHE.get("dirty")) and not state.get("messages") and vocab_leaderboard_chat_file_has_rows():
        # Added 2026-07-09: shutdown flush must not replace non-empty disk chat with an idle empty cache.
        return
    if not state.get("messages") and vocab_leaderboard_chat_file_has_rows():
        # Added 2026-07-16: dirty empty RAM must never erase existing world chat; this was the likely cause of lost Top chat.
        backup_vocab_leaderboard_chat_file("blocked_empty_overwrite")
        VOCAB_LEADERBOARD_CHAT_STATE_CACHE["dirty"] = False
        return
    try:
        if not state.get("messages") and server_database_document_exists(VOCAB_LEADERBOARD_CHAT_FILE):
            backup_vocab_leaderboard_chat_file("empty_write")
        atomic_write_json(VOCAB_LEADERBOARD_CHAT_FILE, state, indent=2)
        mtime_ns = vocab_leaderboard_document_mtime(VOCAB_LEADERBOARD_CHAT_FILE)
        VOCAB_LEADERBOARD_CHAT_STATE_CACHE["mtime_ns"] = mtime_ns
        VOCAB_LEADERBOARD_CHAT_STATE_CACHE["state"] = clone_vocab_leaderboard_chat_state(state)
        VOCAB_LEADERBOARD_CHAT_STATE_CACHE["dirty"] = False
    except Exception as exc:
        stt_debug_log("vocab_leaderboard_chat_flush_failed", error=str(exc))
        if postgres_backend_mode("LEADERBOARD_DOCUMENTS") == "postgres":
            raise


def schedule_vocab_leaderboard_chat_flush() -> None:
    timer = VOCAB_LEADERBOARD_CHAT_STATE_CACHE.get("timer")
    if isinstance(timer, threading.Timer) and timer.is_alive():
        return
    timer = threading.Timer(VOCAB_LEADERBOARD_CHAT_FLUSH_DELAY_SECONDS, lambda: flush_vocab_leaderboard_chat_state(True))
    timer.daemon = True
    VOCAB_LEADERBOARD_CHAT_STATE_CACHE["timer"] = timer
    timer.start()


def normalize_leaderboard_chat_message(value: object, limit: int = 420) -> str:
    text = clean(value)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]+", " ", text)
    text = re.sub(r"[ \t]+", " ", text).strip()
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join([line for line in lines if line])
    return text[: max(0, min(1200, int(limit or 420)))]


def vocab_leaderboard_chat_rows(limit: int = 100) -> list[dict]:
    max_rows = max(1, min(100, space_w_int(limit, 100)))
    with VOCAB_LEADERBOARD_CHAT_LOCK:
        state = load_vocab_leaderboard_chat_state()
    rows = []
    for item in (state.get("messages") if isinstance(state.get("messages"), list) else [])[-max_rows:]:
        username = normalize_username(item.get("username", ""))
        profile = read_user_profile(username) if username else {}
        display_name = clean(item.get("display_name", "")) or clean(profile.get("full_name", "")) or username
        rows.append(
            {
                "id": clean(item.get("id", "")),
                "username": username,
                "display_name": display_name,
                "avatar": clean(item.get("avatar", "")) or clean(profile.get("avatar", "")),
                "message": normalize_leaderboard_chat_message(item.get("message", ""), 420),
                "created_at": clean(item.get("created_at", "")),
            }
        )
    return rows

def vocab_leaderboard_chat_revision(state: dict | None = None) -> int:
    source = state if isinstance(state, dict) else load_vocab_leaderboard_chat_state()
    messages = source.get("messages") if isinstance(source.get("messages"), list) else []
    latest = 0
    for item in messages:
        if isinstance(item, dict):
            latest = max(latest, space_w_int(item.get("id", 0), 0))
    return latest

def vocab_leaderboard_chat_sync(after_id: int = 0, limit: int = 100) -> dict:
    max_rows = max(1, min(100, space_w_int(limit, 100)))
    since = max(0, space_w_int(after_id, 0))
    with VOCAB_LEADERBOARD_CHAT_LOCK:
        state = load_vocab_leaderboard_chat_state()
    revision = vocab_leaderboard_chat_revision(state)
    if since >= revision:
        return {"ok": True, "changed": False, "revision": revision, "messages": []}
    messages = state.get("messages") if isinstance(state.get("messages"), list) else []
    oldest = min([space_w_int(item.get("id", 0), 0) for item in messages if isinstance(item, dict)] or [0])
    reset = bool(since and oldest and since < oldest)
    if reset:
        selected = messages[-max_rows:]
    else:
        selected = [item for item in messages if isinstance(item, dict) and space_w_int(item.get("id", 0), 0) > since][-max_rows:]
    rows = []
    for item in selected:
        username = normalize_username(item.get("username", ""))
        profile = read_user_profile(username) if username else {}
        rows.append(
            {
                "id": clean(item.get("id", "")),
                "username": username,
                "display_name": clean(item.get("display_name", "")) or clean(profile.get("full_name", "")) or username,
                "avatar": clean(item.get("avatar", "")) or clean(profile.get("avatar", "")),
                "message": normalize_leaderboard_chat_message(item.get("message", ""), 420),
                "created_at": clean(item.get("created_at", "")),
            }
        )
    return {"ok": True, "changed": bool(rows), "reset": reset, "revision": revision, "messages": rows}


# Added 2026-07-05: updates hot leaderboard chat payloads without rebuilding score boards.
def refresh_vocab_leaderboard_chat_rows_in_cache(limit: int = 100) -> dict:
    rows = vocab_leaderboard_chat_rows(limit)
    touched = 0
    with VOCAB_LEADERBOARD_LOCK:
        for _cache_key, cached in VOCAB_LEADERBOARD_RAM_CACHE.items():
            if not isinstance(cached, dict):
                continue
            payload = cached.get("payload") if isinstance(cached.get("payload"), dict) else {}
            if not payload:
                continue
            payload["world_chat"] = rows
            cached["payload"] = payload
            cached["at"] = time.time()
            touched += 1
    invalidate_response = globals().get("invalidate_vocab_leaderboard_response_cache")
    if callable(invalidate_response):
        invalidate_response()
    return {"updated": touched, "messages": len(rows)}


def add_vocab_leaderboard_chat_message(username: str, message: object, operation_id: object = "") -> dict:
    username = normalize_username(username)
    text = normalize_leaderboard_chat_message(message, 420)
    if not username:
        return {"ok": False, "error": "Missing user."}
    if not text:
        return {"ok": False, "error": "Message is empty."}
    profile = read_user_profile(username)
    now = utc_timestamp()
    operation = clean(operation_id)[:160]
    row = {
        "id": f"{int(time.time() * 1000)}-{secrets.token_hex(4)}",
        "room_id": "world",
        "username": username,
        "sender": "user",
        "operation_id": operation,
        "display_name": clean(profile.get("full_name", "")) or username,
        "avatar": clean(profile.get("avatar", "")),
        "message": text,
        "created_at": now,
    }
    with VOCAB_LEADERBOARD_CHAT_LOCK:
        if vocab_leaderboard_chat_uses_postgres():
            persisted = postgres_add_world_chat_message(row, operation, "world")
            state = load_vocab_leaderboard_chat_state()
            messages = state.setdefault("messages", [])
            if isinstance(persisted, dict) and isinstance(persisted.get("message"), dict):
                stored = dict(persisted.get("message"))
                if not any(int(existing.get("id", 0) or 0) == int(stored.get("id", 0) or 0) for existing in messages if isinstance(existing, dict)):
                    messages.append(stored)
                    messages.sort(key=lambda item: int(item.get("id", 0) or 0) if isinstance(item, dict) else 0)
                state["messages"] = messages[-100:]
                state["updated_at"] = now
                VOCAB_LEADERBOARD_CHAT_STATE_CACHE["state"] = clone_vocab_leaderboard_chat_state(state)
                VOCAB_LEADERBOARD_CHAT_STATE_CACHE["dirty"] = False
                refresh_vocab_leaderboard_chat_rows_in_cache(100)
                return {"ok": True, "message": stored, "messages": vocab_leaderboard_chat_rows(100)}
            raise RuntimeError("World chat post failed.")
        state = load_vocab_leaderboard_chat_state()
        messages = state.setdefault("messages", [])
        if not isinstance(messages, list):
            messages = []
            state["messages"] = messages
        messages.append(row)
        state["messages"] = messages[-100:]
        state["updated_at"] = now
        write_vocab_leaderboard_chat_state(state)
    refresh_vocab_leaderboard_chat_rows_in_cache(100)
    return {"ok": True, "message": row, "messages": vocab_leaderboard_chat_rows(100)}
