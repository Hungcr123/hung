# Loaded by FUTURE.server_parts.03_chat_paint_runtime into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def chat_add_message(username: str, sender: str, text: str, extra: dict | None = None) -> dict:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    clean_text = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    clean_text = re.sub(r"\n{3,}", "\n\n", clean_text)[:1200]
    attachments = chat_extra_attachments(extra)
    if not clean_text and not attachments:
        raise RuntimeError("Tin nhan dang trong.")
    sender = "admin" if clean(sender).lower() == "admin" else "user"
    item = {
        "username": username,
        "sender": sender,
        "text": clean_text,
        "at": chat_now(),
        "ts": time.time(),
    }
    if isinstance(extra, dict):
        for key in ("audio_path", "audio_mime", "audio_error", "voice", "voice_label", "language", "translated_from", "translation_source", "operation_id"):
            value = clean(extra.get(key, ""))
            if value:
                item[key] = value
        audio = extra.get("audio")
        if isinstance(audio, dict):
            clean_audio = {}
            for key in ("path", "mime", "voice", "label"):
                value = clean(audio.get(key, ""))
                if value:
                    clean_audio[key] = value
            if clean_audio:
                item["audio"] = clean_audio
        if attachments:
            item["attachments"] = attachments
    operation_id = clean(item.get("operation_id", ""))
    operation_key = (username.lower(), sender, operation_id)
    if operation_id:
        with CHAT_LOCK:
            cached_ack = CHAT_OPERATION_ACK_CACHE.get(operation_key)
            if isinstance(cached_ack, dict):
                return dict(cached_ack)
    persisted = server_database_add_chat_message(item, operation_id)
    stored = persisted.get("message") if isinstance(persisted, dict) and isinstance(persisted.get("message"), dict) else item
    with CHAT_LOCK:
        if operation_id:
            if len(CHAT_OPERATION_ACK_CACHE) >= CHAT_OPERATION_ACK_CACHE_MAX and operation_key not in CHAT_OPERATION_ACK_CACHE:
                for stale_key in tuple(CHAT_OPERATION_ACK_CACHE)[:500]:
                    CHAT_OPERATION_ACK_CACHE.pop(stale_key, None)
            CHAT_OPERATION_ACK_CACHE[operation_key] = dict(stored)
        state = load_chat_state_locked()
        messages = state.setdefault("messages", [])
        if not any(int(row.get("id", 0) or 0) == int(stored.get("id", 0) or 0) for row in messages if isinstance(row, dict)):
            messages.append(stored)
            messages.sort(key=lambda row: int(row.get("id", 0) or 0) if isinstance(row, dict) else 0)
        state["messages"] = messages[-800:]
        CHAT_STATE_CACHE.update({"state": state, "dirty": False})
        if attachments and enforce_chat_attachment_quota_locked(username, state):
            save_chat_state_locked(state)
        return stored


def chat_message_read_state(item: dict, admin_read: dict, user_read: dict) -> dict:
    row = dict(item) if isinstance(item, dict) else {}
    message_id = int(row.get("id", 0) or 0)
    sender = clean(row.get("sender", "")).lower()
    username = normalize_username(row.get("username", ""))
    if sender == "user":
        read = int(admin_read.get(username, 0) or 0) >= message_id
    elif sender == "admin":
        read = int(user_read.get(username, 0) or 0) >= message_id
    else:
        read = False
    row["peer_read"] = bool(read)
    row["read_state"] = "seen" if read else "sent"
    return row


def chat_messages_with_read_state(state: dict, rows: list[dict]) -> list[dict]:
    admin_read = state.get("admin_read", {}) if isinstance(state.get("admin_read", {}), dict) else {}
    user_read = state.get("user_read", {}) if isinstance(state.get("user_read", {}), dict) else {}
    return [chat_message_read_state(item, admin_read, user_read) for item in rows if isinstance(item, dict)]


def chat_read_markers(username: str) -> dict:
    username = normalize_username(username)
    with CHAT_LOCK:
        state = load_chat_state_locked()
        admin_read = state.get("admin_read", {}) if isinstance(state.get("admin_read", {}), dict) else {}
        user_read = state.get("user_read", {}) if isinstance(state.get("user_read", {}), dict) else {}
        return {
            "admin_read": int(admin_read.get(username, 0) or 0),
            "user_read": int(user_read.get(username, 0) or 0),
        }


def chat_messages_for(username: str, since: int = 0) -> list[dict]:
    username = normalize_username(username)
    with CHAT_LOCK:
        state = load_chat_state_locked()
        rows = [
            item for item in state.get("messages", [])
            if normalize_username(item.get("username", "")) == username and int(item.get("id", 0) or 0) > since
        ][-200:]
        return chat_messages_with_read_state(state, rows)


# Added 2026-07-20: build one learner poll response from one locked state scan and persist only a newer read marker.
def chat_poll_snapshot(username: str, since: int = 0, mark_read: bool = False) -> dict:
    username = normalize_username(username)
    with CHAT_LOCK:
        state = load_chat_state_locked()
        admin_read = state.get("admin_read", {}) if isinstance(state.get("admin_read", {}), dict) else {}
        user_read = state.get("user_read", {}) if isinstance(state.get("user_read", {}), dict) else {}
        current_user_read = int(user_read.get(username, 0) or 0)
        latest_admin = 0
        unread = 0
        rows = []
        for item in state.get("messages", []):
            if not isinstance(item, dict) or normalize_username(item.get("username", "")) != username:
                continue
            message_id = int(item.get("id", 0) or 0)
            if clean(item.get("sender", "")).lower() == "admin":
                latest_admin = max(latest_admin, message_id)
                if message_id > current_user_read:
                    unread += 1
            if message_id > since:
                rows.append(item)
        messages = chat_messages_with_read_state(state, rows[-200:])
        if mark_read and latest_admin > current_user_read:
            server_database_update_chat_read(username, "user_read", latest_admin)
            state.setdefault("user_read", {})[username] = latest_admin
            current_user_read = latest_admin
            unread = 0
        return {
            "messages": messages,
            "unread": unread,
            "read": {
                "admin_read": int(admin_read.get(username, 0) or 0),
                "user_read": current_user_read,
            },
        }


def chat_mark_user_read(username: str) -> None:
    username = normalize_username(username)
    with CHAT_LOCK:
        state = load_chat_state_locked()
        latest = max([
            int(item.get("id", 0) or 0)
            for item in state.get("messages", [])
            if normalize_username(item.get("username", "")) == username and clean(item.get("sender", "")) == "admin"
        ] + [0])
        user_read = state.setdefault("user_read", {})
        if latest > int(user_read.get(username, 0) or 0):
            server_database_update_chat_read(username, "user_read", latest)
            user_read[username] = latest


def chat_mark_admin_read(username: str) -> None:
    username = normalize_username(username)
    with CHAT_LOCK:
        state = load_chat_state_locked()
        latest = max([
            int(item.get("id", 0) or 0)
            for item in state.get("messages", [])
            if normalize_username(item.get("username", "")) == username and clean(item.get("sender", "")) == "user"
        ] + [0])
        admin_read = state.setdefault("admin_read", {})
        if latest > int(admin_read.get(username, 0) or 0):
            server_database_update_chat_read(username, "admin_read", latest)
            admin_read[username] = latest


def chat_user_unread(username: str) -> int:
    username = normalize_username(username)
    with CHAT_LOCK:
        state = load_chat_state_locked()
        last_read = int(state.get("user_read", {}).get(username, 0) or 0)
        return sum(
            1 for item in state.get("messages", [])
            if normalize_username(item.get("username", "")) == username
            and clean(item.get("sender", "")) == "admin"
            and int(item.get("id", 0) or 0) > last_read
        )


def latest_progress_activity(username: str) -> dict:
    username = normalize_username(username)
    candidates: list[dict] = []
    for space, reader in (
        ("Space_W", read_space_w_progress_file),
        ("Space_Q", read_space_q_progress_file),
    ):
        try:
            payload = reader(username)
            states = payload.get("states", {}) if isinstance(payload.get("states", {}), dict) else {}
        except Exception:
            states = {}
        for record in states.values():
            if not isinstance(record, dict):
                continue
            updated = clean(record.get("updatedAt") or record.get("savedAt"))
            candidates.append({
                "status": f"Last active in {space}",
                "space": space,
                "title": clean(record.get("title", "")),
                "path": clean(record.get("path", "")),
                "nodeIndex": max(0, space_w_int(record.get("nodeIndex", 0), 0)),
                "nodeCount": max(0, space_w_int(record.get("nodeCount", 0), 0)),
                "updatedAt": updated,
                "_sort": timestamp_to_epoch(updated),
            })
    if not candidates:
        return {}
    candidates.sort(key=lambda item: float(item.get("_sort", 0) or 0), reverse=True)
    result = candidates[0]
    result.pop("_sort", None)
    return result


def chat_admin_state(message_user: str = "", include_all_messages: bool = False, include_activity: bool = True) -> dict:
    now = time.time()
    message_user = normalize_username(message_user)
    # Added 2026-07-23: load-test identities are operational fixtures, not dashboard learners.
    is_test_user = globals().get("server_database_is_test_user")
    def dashboard_user_allowed(username: str) -> bool:
        normalized = normalize_username(username)
        if not normalized:
            return False
        try:
            return not bool(is_test_user(normalized)) if callable(is_test_user) else not normalized.lower().startswith("codexload")
        except Exception:
            return not normalized.lower().startswith("codexload")
    online_map: dict[str, float] = {}
    with AUTH_LOCK:
        for session in AUTH_SESSIONS.values():
            username = normalize_username(session.get("username", ""))
            if dashboard_user_allowed(username):
                online_map[username] = max(float(session.get("last_seen", 0) or 0), online_map.get(username, 0))
    with CHAT_LOCK:
        for username, last_seen in list(CHAT_ONLINE.items()):
            username = normalize_username(username)
            if dashboard_user_allowed(username):
                online_map[username] = max(float(last_seen or 0), online_map.get(username, 0))
        state = load_chat_state_locked()
        messages = state.get("messages", [])
        admin_read = state.get("admin_read", {})
    messages_by_user: dict[str, list[dict]] = {}
    if isinstance(messages, list):
        for item in messages:
            if not isinstance(item, dict):
                continue
            msg_user = normalize_username(item.get("username", ""))
            if msg_user:
                messages_by_user.setdefault(msg_user, []).append(item)
    with STREAM_LOCK:
        stream_cleanup_locked()
        for session in STREAM_SESSIONS.values():
            if clean(session.get("state", "")) in {"pending_admin", "pending_user", "active"}:
                username = normalize_username(session.get("username", ""))
                if dashboard_user_allowed(username):
                    online_map[username] = max(float(session.get("updated_at", 0) or 0), online_map.get(username, 0))
    with SCREEN_LOCK:
        screen_cleanup_locked()
        for session in SCREEN_SESSIONS.values():
            if clean(session.get("state", "")) in {"pending_user", "active"}:
                username = normalize_username(session.get("username", ""))
                if dashboard_user_allowed(username):
                    online_map[username] = max(float(session.get("updated_at", 0) or 0), online_map.get(username, 0))
    with USER_ACTIVITY_LOCK:
        for username, activity in USER_ACTIVITY.items():
            username = normalize_username(username)
            if dashboard_user_allowed(username) and isinstance(activity, dict):
                online_map[username] = max(float(activity.get("_seen", 0) or 0), online_map.get(username, 0))
    speak_skip_map = latest_speak_skip_by_user()
    users = []
    for username, last_seen in sorted(online_map.items(), key=lambda item: item[0].lower()):
        user_messages = list(messages_by_user.get(username, []))
        user_messages = chat_messages_with_read_state(state, user_messages)
        last_message = user_messages[-1] if user_messages else {}
        last_read = int(admin_read.get(username, 0) or 0)
        unread = sum(
            1 for item in user_messages
            if clean(item.get("sender", "")) == "user" and int(item.get("id", 0) or 0) > last_read
        )
        users.append({
            "username": username,
            "online": now - float(last_seen or 0) <= CHAT_ONLINE_TTL_SECONDS,
            "last_seen": chat_now() if not last_seen else local_timestamp(last_seen),
            "unread": unread,
            "last_message": last_message,
            "messages": user_messages[-120:] if include_all_messages or username == message_user else [],
            "stream": stream_session_for_user(username),
            "screen": screen_session_for_user(username),
            "paint": paint_public_state(username, include_data=False),
            "speak_skip": speak_skip_map.get(username),
            "activity": user_activity_snapshot(username) or (latest_progress_activity(username) if include_activity else {}),
        })
    online_count = sum(1 for item in users if item.get("online"))
    return {"users": users, "online_count": online_count, "server_time": chat_now(), "stream_admin_online": dashboard_is_online()}
