# Loaded by FUTURE.server_parts.05_stream_screen_security into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def dashboard_is_online() -> bool:
    with DASHBOARD_LOCK:
        return (
            clean(SERVER_STATE.get("dashboard_status", "")) == "open"
            and time.time() - float(SERVER_STATE.get("dashboard_last_seen", 0) or 0) <= 35
        )


def stream_public_session(session: dict | None) -> dict:
    if not isinstance(session, dict):
        return {}
    return {
        "id": clean(session.get("id", "")),
        "username": clean(session.get("username", "")),
        "state": clean(session.get("state", "")),
        "requested_by": clean(session.get("requested_by", "")),
        "user_accept": bool(session.get("user_accept")),
        "admin_accept": bool(session.get("admin_accept")),
        "created_at": float(session.get("created_at", 0) or 0),
        "updated_at": float(session.get("updated_at", 0) or 0),
        "message": clean(session.get("message", "")),
        "signal_version": int((session.get("webrtc") or {}).get("version", 0) or 0) if isinstance(session.get("webrtc"), dict) else 0,
    }


def stream_webrtc_state(session: dict) -> dict:
    state = session.get("webrtc")
    if not isinstance(state, dict):
        state = {
            "offer": None,
            "answer": None,
            "admin_candidates": [],
            "user_candidates": [],
            "candidate_id": 0,
            "version": 0,
        }
        session["webrtc"] = state
    for key in ("admin_candidates", "user_candidates"):
        if not isinstance(state.get(key), list):
            state[key] = []
    state["candidate_id"] = int(state.get("candidate_id", 0) or 0)
    state["version"] = int(state.get("version", 0) or 0)
    return state


def stream_cleanup_locked() -> None:
    now = time.time()
    expired = []
    for session_id, session in list(STREAM_SESSIONS.items()):
        state = clean(session.get("state", ""))
        updated = float(session.get("updated_at", 0) or 0)
        ttl = 3600 if state == "active" else 300
        if state in {"ended", "rejected", "error"} and now - updated > 120:
            expired.append(session_id)
        elif updated and now - updated > ttl:
            session["state"] = "ended"
            session["message"] = "Stream timeout."
            session["updated_at"] = now
    for session_id in expired:
        STREAM_SESSIONS.pop(session_id, None)
        STREAM_CHUNKS.pop(session_id, None)


def stream_user_online(username: str) -> bool:
    username = normalize_username(username)
    if not username:
        return False
    with CHAT_LOCK:
        last_seen = float(CHAT_ONLINE.get(username, 0) or 0)
    return time.time() - last_seen <= CHAT_ONLINE_TTL_SECONDS


def stream_busy_locked(username: str = "") -> bool:
    user = normalize_username(username)
    for session in STREAM_SESSIONS.values():
        state = clean(session.get("state", ""))
        if state not in {"pending_admin", "pending_user", "active"}:
            continue
        if not user or normalize_username(session.get("username", "")) == user:
            return True
    return False


def stream_session_for_user(username: str) -> dict:
    username = normalize_username(username)
    with STREAM_LOCK:
        stream_cleanup_locked()
        sessions = [
            session for session in STREAM_SESSIONS.values()
            if normalize_username(session.get("username", "")) == username
            and clean(session.get("state", "")) in {"pending_admin", "pending_user", "active"}
        ]
        sessions.sort(key=lambda item: float(item.get("updated_at", 0) or 0), reverse=True)
        return stream_public_session(sessions[0]) if sessions else {}


def stream_request(username: str, requested_by: str) -> dict:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    requested_by = "admin" if clean(requested_by).lower() == "admin" else "user"
    if requested_by == "admin" and not dashboard_is_online():
        raise RuntimeError("Admin dashboard chua online.")
    if not stream_user_online(username):
        raise RuntimeError("User chua online.")
    with STREAM_LOCK:
        stream_cleanup_locked()
        existing = stream_session_for_user(username)
        if existing:
            return existing
        if stream_busy_locked(username):
            raise RuntimeError("Dang co stream khac hoat dong.")
        session_id = uuid.uuid4().hex
        now = time.time()
        session = {
            "id": session_id,
            "username": username,
            "state": "active" if requested_by == "user" else "pending_user",
            "requested_by": requested_by,
            "user_accept": requested_by == "user",
            "admin_accept": True,
            "created_at": now,
            "updated_at": now,
            "message": "Stream active." if requested_by == "user" else "Waiting for accept.",
        }
        if requested_by == "user":
            stream_webrtc_state(session)
        STREAM_SESSIONS[session_id] = session
        STREAM_CHUNKS[session_id] = []
        return stream_public_session(session)


def stream_action(username: str, actor: str, action: str, session_id: str = "") -> dict:
    username = normalize_username(username)
    actor = "admin" if clean(actor).lower() == "admin" else "user"
    action = clean(action).lower()
    with STREAM_LOCK:
        stream_cleanup_locked()
        session = None
        if session_id and session_id in STREAM_SESSIONS:
            candidate = STREAM_SESSIONS.get(session_id)
            if normalize_username(candidate.get("username", "")) == username:
                session = candidate
        if session is None:
            for candidate in STREAM_SESSIONS.values():
                if normalize_username(candidate.get("username", "")) == username and clean(candidate.get("state", "")) in {"pending_admin", "pending_user", "active"}:
                    session = candidate
                    break
        if not session:
            raise RuntimeError("Khong co stream dang cho.")
        if action in {"reject", "end", "stop", "cancel"}:
            session["state"] = "rejected" if action == "reject" else "ended"
            session["message"] = "Stream stopped."
            session["updated_at"] = time.time()
            session["webrtc"] = {
                "offer": None,
                "answer": None,
                "admin_candidates": [],
                "user_candidates": [],
                "candidate_id": 0,
                "version": int((session.get("webrtc") or {}).get("version", 0) or 0) + 1 if isinstance(session.get("webrtc"), dict) else 1,
            }
            return stream_public_session(session)
        if action != "accept":
            raise RuntimeError("Stream action khong hop le.")
        if actor == "admin":
            session["admin_accept"] = True
        else:
            session["user_accept"] = True
        if session.get("admin_accept") and session.get("user_accept"):
            session["state"] = "active"
            session["message"] = "Stream active."
            stream_webrtc_state(session)
        else:
            session["state"] = "pending_admin" if not session.get("admin_accept") else "pending_user"
            session["message"] = "Waiting for accept."
        session["updated_at"] = time.time()
        return stream_public_session(session)


def stream_submit_signal(username: str, actor: str, session_id: str, signal_type: str, data: object) -> dict:
    username = normalize_username(username)
    actor = "admin" if clean(actor).lower() == "admin" else "user"
    signal_type = clean(signal_type).lower()
    session_id = clean(session_id)
    if signal_type not in {"offer", "answer", "candidate"}:
        raise RuntimeError("WebRTC signal khong hop le.")
    if not isinstance(data, dict):
        raise RuntimeError("WebRTC data khong hop le.")
    with STREAM_LOCK:
        session = STREAM_SESSIONS.get(session_id)
        if not session or normalize_username(session.get("username", "")) != username:
            raise RuntimeError("Stream khong ton tai.")
        if clean(session.get("state", "")) != "active":
            raise RuntimeError("Stream chua active.")
        webrtc = stream_webrtc_state(session)
        if signal_type == "offer":
            if actor != "admin":
                raise RuntimeError("Chi admin tao offer WebRTC.")
            webrtc["offer"] = data
            webrtc["answer"] = None
            webrtc["admin_candidates"] = []
            webrtc["user_candidates"] = []
            webrtc["candidate_id"] = 0
        elif signal_type == "answer":
            if actor != "user":
                raise RuntimeError("Chi user tao answer WebRTC.")
            webrtc["answer"] = data
        else:
            key = "admin_candidates" if actor == "admin" else "user_candidates"
            webrtc["candidate_id"] = int(webrtc.get("candidate_id", 0) or 0) + 1
            item = {"id": webrtc["candidate_id"], "candidate": data, "sender": actor, "at": time.time()}
            webrtc.setdefault(key, []).append(item)
            del webrtc[key][:-80]
        webrtc["version"] = int(webrtc.get("version", 0) or 0) + 1
        session["updated_at"] = time.time()
        return stream_public_session(session)


def stream_poll_signal(username: str, actor: str, session_id: str, after_candidate: int = 0) -> dict:
    username = normalize_username(username)
    actor = "admin" if clean(actor).lower() == "admin" else "user"
    with STREAM_LOCK:
        stream_cleanup_locked()
        session = STREAM_SESSIONS.get(clean(session_id))
        if not session or normalize_username(session.get("username", "")) != username:
            return {"session": {}, "offer": None, "answer": None, "candidates": [], "version": 0}
        webrtc = stream_webrtc_state(session)
        remote_key = "user_candidates" if actor == "admin" else "admin_candidates"
        candidates = [
            item for item in list(webrtc.get(remote_key, []) or [])
            if int(item.get("id", 0) or 0) > int(after_candidate or 0)
        ][-80:]
        return {
            "session": stream_public_session(session),
            "offer": webrtc.get("offer") if actor == "user" else None,
            "answer": webrtc.get("answer") if actor == "admin" else None,
            "candidates": candidates,
            "version": int(webrtc.get("version", 0) or 0),
        }


def stream_add_chunk(username: str, sender: str, session_id: str, data: str, mime: str) -> dict:
    username = normalize_username(username)
    sender = "admin" if clean(sender).lower() == "admin" else "user"
    session_id = clean(session_id)
    raw_data = str(data or "")
    if not session_id or not raw_data:
        raise RuntimeError("Missing stream audio chunk.")
    with STREAM_LOCK:
        session = STREAM_SESSIONS.get(session_id)
        if not session or normalize_username(session.get("username", "")) != username:
            raise RuntimeError("Stream khong ton tai.")
        if clean(session.get("state", "")) != "active":
            raise RuntimeError("Stream chua active.")
        rows = STREAM_CHUNKS.setdefault(session_id, [])
        next_id = max([int(item.get("id", 0) or 0) for item in rows] + [0]) + 1
        item = {
            "id": next_id,
            "sender": sender,
            "data": raw_data[:900000],
            "mime": clean(mime)[:80] or "audio/webm",
            "at": time.time(),
        }
        rows.append(item)
        del rows[:-STREAM_CHUNK_LIMIT]
        session["updated_at"] = time.time()
        return {"id": next_id}


def stream_poll_chunks(username: str, session_id: str, after: int, receiver: str) -> dict:
    username = normalize_username(username)
    receiver = "admin" if clean(receiver).lower() == "admin" else "user"
    sender = "user" if receiver == "admin" else "admin"
    with STREAM_LOCK:
        stream_cleanup_locked()
        session = STREAM_SESSIONS.get(clean(session_id))
        if not session or normalize_username(session.get("username", "")) != username:
            return {"session": {}, "chunks": []}
        rows = [
            item for item in STREAM_CHUNKS.get(clean(session_id), [])
            if clean(item.get("sender", "")) == sender and int(item.get("id", 0) or 0) > int(after or 0)
        ][-30:]
        return {"session": stream_public_session(session), "chunks": rows}
