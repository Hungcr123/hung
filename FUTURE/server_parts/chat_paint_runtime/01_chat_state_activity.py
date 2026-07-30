# Loaded by FUTURE.server_parts.03_chat_paint_runtime into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

CHAT_STATE_WRITEBEHIND_SECONDS = 2.0
CHAT_STATE_CACHE = {"state": None, "mtime_ns": -1, "dirty": False, "timer": None}
CHAT_OPERATION_ACK_CACHE: dict[tuple[str, str, str], dict] = {}
CHAT_OPERATION_ACK_CACHE_MAX = 5000


def normalize_chat_state_payload(payload: dict | None = None) -> dict:
    source = payload if isinstance(payload, dict) else {}
    messages = source.get("messages", [])
    if not isinstance(messages, list):
        messages = []
    return {
        "messages": [item for item in messages if isinstance(item, dict)][-800:],
        "admin_read": source.get("admin_read", {}) if isinstance(source.get("admin_read", {}), dict) else {},
        "user_read": source.get("user_read", {}) if isinstance(source.get("user_read", {}), dict) else {},
    }


def load_chat_state_locked() -> dict:
    cached = CHAT_STATE_CACHE.get("state")
    if isinstance(cached, dict):
        return cached
    payload = server_database_load_chat_state()
    state = normalize_chat_state_payload(payload if isinstance(payload, dict) else {})
    CHAT_STATE_CACHE.update({"state": state, "mtime_ns": 0, "dirty": False})
    return state


def save_chat_state_locked(state: dict, *, force: bool = False) -> None:
    normalized = normalize_chat_state_payload(state)
    state.clear()
    state.update(normalized)
    CHAT_STATE_CACHE["state"] = state
    CHAT_STATE_CACHE["dirty"] = True
    if force:
        flush_chat_state_cache(True)
    else:
        schedule_chat_state_flush()


def flush_chat_state_cache(force: bool = False) -> None:
    with CHAT_LOCK:
        if not bool(CHAT_STATE_CACHE.get("dirty")):
            return
        state = CHAT_STATE_CACHE.get("state")
        if not isinstance(state, dict):
            return
        normalized = normalize_chat_state_payload(state if isinstance(state, dict) else {})
        server_database_replace_chat_state(normalized)
        CHAT_STATE_CACHE.update({"state": normalized, "mtime_ns": 0, "dirty": False})


def schedule_chat_state_flush() -> None:
    timer = CHAT_STATE_CACHE.get("timer")
    if isinstance(timer, threading.Timer) and timer.is_alive():
        return
    timer = threading.Timer(CHAT_STATE_WRITEBEHIND_SECONDS, lambda: flush_chat_state_cache(True))
    timer.daemon = True
    CHAT_STATE_CACHE["timer"] = timer
    timer.start()


atexit.register(lambda: flush_chat_state_cache(True))


def chat_now() -> str:
    return utc_timestamp()


# Added 2026-07-01: keeps dashboard presence alive between lightweight one-minute user polls.
CHAT_ONLINE_TTL_SECONDS = 60


def chat_mark_online(username: str) -> None:
            username = normalize_username(username)
            if not username:
                return
            now = time.time()
            with CHAT_LOCK:
                previous_seen = float(CHAT_ONLINE.get(username, 0) or 0)
                if not previous_seen or now - previous_seen > 75:
                    CHAT_ONLINE_FIRST_SEEN[username] = now
                CHAT_ONLINE[username] = now
                CHAT_ONLINE_FIRST_SEEN.setdefault(username, now)


def mark_user_activity(username: str, activity: dict | None = None, status: str = "Online") -> None:
    username = normalize_username(username)
    if not username:
        return
    if username.lower() == "testuser":
        return
    source = activity if isinstance(activity, dict) else {}
    now = time.time()
    row = {
        "username": username,
        "status": clean(source.get("status") or status or "Online")[:120],
        "space": clean(source.get("space") or source.get("type") or "")[:32],
        "title": clean(source.get("title") or "")[:180],
        "path": clean(source.get("path") or "")[:260],
        "nodeIndex": max(0, space_w_int(source.get("nodeIndex", source.get("node_index", 0)), 0)),
        "nodeCount": max(0, space_w_int(source.get("nodeCount", source.get("node_count", 0)), 0)),
        "updatedAt": utc_timestamp(),
        "_seen": now,
    }
    with USER_ACTIVITY_LOCK:
        existing = USER_ACTIVITY.get(username) if isinstance(USER_ACTIVITY.get(username), dict) else {}
        merged = {**existing, **{key: value for key, value in row.items() if value not in ("", 0) or key in {"nodeIndex", "nodeCount", "_seen"}}}
        merged["username"] = username
        merged["updatedAt"] = row["updatedAt"]
        merged["_seen"] = now
        USER_ACTIVITY[username] = merged


def touch_user_activity_seen(username: str) -> None:
    username = normalize_username(username)
    if not username:
        return
    now = time.time()
    with USER_ACTIVITY_LOCK:
        existing = USER_ACTIVITY.get(username) if isinstance(USER_ACTIVITY.get(username), dict) else {}
        if existing:
            existing["_seen"] = now
            existing["updatedAt"] = utc_timestamp()
            USER_ACTIVITY[username] = existing
        else:
            USER_ACTIVITY[username] = {
                "username": username,
                "status": "Online",
                "updatedAt": utc_timestamp(),
                "_seen": now,
            }


def user_activity_snapshot(username: str) -> dict:
    username = normalize_username(username)
    if not username:
        return {}
    with USER_ACTIVITY_LOCK:
        row = dict(USER_ACTIVITY.get(username) or {})
    if not row:
        return {}
    age = max(0, int(time.time() - float(row.get("_seen", 0) or 0)))
    row.pop("_seen", None)
    row["ageSeconds"] = age
    if age > 120:
        row["status"] = "Idle"
    return row


def user_recently_online(username: str, ttl: int = 75) -> bool:
    username = normalize_username(username)
    if not username:
        return False
    now = time.time()
    with CHAT_LOCK:
        if now - float(CHAT_ONLINE.get(username, 0) or 0) <= ttl:
            return True
    with AUTH_LOCK:
        for session in AUTH_SESSIONS.values():
            if normalize_username(session.get("username", "")) == username:
                if now - float(session.get("last_seen", 0) or 0) <= ttl:
                    return True
    with USER_ACTIVITY_LOCK:
        activity = USER_ACTIVITY.get(username) if isinstance(USER_ACTIVITY.get(username), dict) else {}
        if now - float(activity.get("_seen", 0) or 0) <= ttl:
            return True
    return False
