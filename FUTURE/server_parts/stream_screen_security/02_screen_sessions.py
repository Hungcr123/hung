# Loaded by FUTURE.server_parts.05_stream_screen_security into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def screen_public_session(session: dict | None) -> dict:
    if not isinstance(session, dict):
        return {}
    frame = session.get("frame")
    frame = frame if isinstance(frame, dict) else {}
    audio_rows = session.get("audio_chunks") if isinstance(session.get("audio_chunks"), list) else []
    audio_last = audio_rows[-1] if audio_rows else {}
    return {
        "id": clean(session.get("id", "")),
        "username": clean(session.get("username", "")),
        "state": clean(session.get("state", "")),
        "requested_by": clean(session.get("requested_by", "")),
        "user_accept": bool(session.get("user_accept")),
        "created_at": float(session.get("created_at", 0) or 0),
        "updated_at": float(session.get("updated_at", 0) or 0),
        "message": clean(session.get("message", "")),
        "frame_id": int(frame.get("id", 0) or 0),
        "frame_at": float(frame.get("at", 0) or 0),
        "width": int(frame.get("width", 0) or 0),
        "height": int(frame.get("height", 0) or 0),
        "audio_chunk_id": int(audio_last.get("id", 0) or 0),
        "audio_chunk_at": float(audio_last.get("at", 0) or 0),
        "signal_version": int((session.get("webrtc") or {}).get("version", 0) or 0) if isinstance(session.get("webrtc"), dict) else 0,
    }


def screen_webrtc_state(session: dict) -> dict:
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


def screen_cleanup_locked() -> None:
    now = time.time()
    expired = []
    for session_id, session in list(SCREEN_SESSIONS.items()):
        state = clean(session.get("state", ""))
        updated = float(session.get("updated_at", 0) or 0)
        ttl = 3600 if state == "active" else 300
        if state in {"ended", "rejected", "error"} and now - updated > 120:
            expired.append(session_id)
        elif updated and now - updated > ttl:
            session["state"] = "ended"
            session["message"] = "Screen preview timeout."
            session["updated_at"] = now
    for session_id in expired:
        SCREEN_SESSIONS.pop(session_id, None)


def screen_session_for_user(username: str) -> dict:
    username = normalize_username(username)
    with SCREEN_LOCK:
        screen_cleanup_locked()
        sessions = [
            session for session in SCREEN_SESSIONS.values()
            if normalize_username(session.get("username", "")) == username
            and clean(session.get("state", "")) in {"pending_user", "active"}
        ]
        sessions.sort(key=lambda item: float(item.get("updated_at", 0) or 0), reverse=True)
        return screen_public_session(sessions[0]) if sessions else {}


def screen_request(username: str, requested_by: str = "admin") -> dict:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    requested_by = "admin" if clean(requested_by).lower() == "admin" else "user"
    if requested_by == "admin" and not dashboard_is_online():
        raise RuntimeError("Admin dashboard chua online.")
    if not stream_user_online(username):
        raise RuntimeError("User chua online.")
    with SCREEN_LOCK:
        screen_cleanup_locked()
        existing = screen_session_for_user(username)
        if existing:
            return existing
        session_id = uuid.uuid4().hex
        now = time.time()
        session = {
            "id": session_id,
            "username": username,
            "state": "active" if requested_by == "user" else "pending_user",
            "requested_by": requested_by,
            "user_accept": requested_by == "user",
            "created_at": now,
            "updated_at": now,
            "message": "Screen preview active." if requested_by == "user" else "Waiting for user screen permission.",
            "frame": {},
        }
        if requested_by == "user":
            screen_webrtc_state(session)
        SCREEN_SESSIONS[session_id] = session
        return screen_public_session(session)


def screen_action(username: str, actor: str, action: str, session_id: str = "") -> dict:
    username = normalize_username(username)
    actor = "admin" if clean(actor).lower() == "admin" else "user"
    action = clean(action).lower()
    with SCREEN_LOCK:
        screen_cleanup_locked()
        session = None
        if session_id and session_id in SCREEN_SESSIONS:
            candidate = SCREEN_SESSIONS.get(session_id)
            if normalize_username(candidate.get("username", "")) == username:
                session = candidate
        if session is None:
            for candidate in SCREEN_SESSIONS.values():
                if normalize_username(candidate.get("username", "")) == username and clean(candidate.get("state", "")) in {"pending_user", "active"}:
                    session = candidate
                    break
        if not session:
            raise RuntimeError("Khong co yeu cau xem man hinh dang cho.")
        if action in {"reject", "end", "stop", "cancel"}:
            session["state"] = "rejected" if action == "reject" else "ended"
            session["message"] = "Screen preview stopped."
            session["updated_at"] = time.time()
            session["webrtc"] = {
                "offer": None,
                "answer": None,
                "admin_candidates": [],
                "user_candidates": [],
                "candidate_id": 0,
                "version": int((session.get("webrtc") or {}).get("version", 0) or 0) + 1 if isinstance(session.get("webrtc"), dict) else 1,
            }
            return screen_public_session(session)
        if action != "accept":
            raise RuntimeError("Screen action khong hop le.")
        if actor != "user":
            raise RuntimeError("Chi user moi co the cap quyen chia se man hinh.")
        session["user_accept"] = True
        session["state"] = "active"
        session["message"] = "Screen preview active."
        screen_webrtc_state(session)
        session["updated_at"] = time.time()
        return screen_public_session(session)


def screen_store_frame(username: str, session_id: str, data: str, width: int = 0, height: int = 0) -> dict:
    username = normalize_username(username)
    session_id = clean(session_id)
    raw_data = str(data or "")
    if not session_id or not raw_data:
        raise RuntimeError("Missing screen frame.")
    if not raw_data.startswith("data:image/"):
        raise RuntimeError("Screen frame khong hop le.")
    if len(raw_data) > SCREEN_FRAME_MAX_CHARS:
        raise RuntimeError("Screen frame qua lon.")
    with SCREEN_LOCK:
        screen_cleanup_locked()
        session = SCREEN_SESSIONS.get(session_id)
        if not session or normalize_username(session.get("username", "")) != username:
            raise RuntimeError("Screen session khong ton tai.")
        if clean(session.get("state", "")) != "active":
            raise RuntimeError("Screen session chua active.")
        previous = session.get("frame") if isinstance(session.get("frame"), dict) else {}
        next_id = int(previous.get("id", 0) or 0) + 1
        safe_width = max(0, min(4096, int(width or 0)))
        safe_height = max(0, min(4096, int(height or 0)))
        session["frame"] = {
            "id": next_id,
            "data": raw_data,
            "width": safe_width,
            "height": safe_height,
            "at": time.time(),
        }
        session["updated_at"] = time.time()
        session["message"] = "Screen preview active."
        return {"id": next_id, "session": screen_public_session(session)}


def screen_store_frame_bytes(username: str, session_id: str, frame_bytes: bytes, mime: str = "image/webp", width: int = 0, height: int = 0) -> dict:
    raw = bytes(frame_bytes or b"")
    safe_mime = clean(mime).split(";", 1)[0].strip().lower() or "image/webp"
    if safe_mime == "image/jpg":
        safe_mime = "image/jpeg"
    if safe_mime not in {"image/webp", "image/jpeg", "image/png"}:
        raise RuntimeError("Screen frame mime khong hop le.")
    max_bytes = max(1, int((SCREEN_FRAME_MAX_CHARS - 64) * 3 / 4))
    if not raw:
        raise RuntimeError("Missing screen frame.")
    if len(raw) > max_bytes:
        raise RuntimeError("Screen frame qua lon.")
    encoded = base64.b64encode(raw).decode("ascii")
    return screen_store_frame(username, session_id, f"data:{safe_mime};base64,{encoded}", width, height)


def screen_add_audio_chunk(username: str, session_id: str, data: str, mime: str = "audio/webm", sender: str = "user") -> dict:
    username = normalize_username(username)
    session_id = clean(session_id)
    raw_data = str(data or "")
    safe_sender = clean(sender).lower() or "user"
    if safe_sender not in {"user", "admin"}:
        safe_sender = "user"
    if not session_id or not raw_data:
        raise RuntimeError("Missing screen audio chunk.")
    if not raw_data.startswith("data:audio/"):
        raise RuntimeError("Screen audio chunk khong hop le.")
    with SCREEN_LOCK:
        screen_cleanup_locked()
        session = SCREEN_SESSIONS.get(session_id)
        if not session or normalize_username(session.get("username", "")) != username:
            raise RuntimeError("Screen session khong ton tai.")
        if clean(session.get("state", "")) != "active":
            raise RuntimeError("Screen session chua active.")
        rows = session.setdefault("audio_chunks", [])
        if not isinstance(rows, list):
            rows = []
            session["audio_chunks"] = rows
        next_id = max([int(item.get("id", 0) or 0) for item in rows] + [0]) + 1
        item = {
            "id": next_id,
            "data": raw_data[:900000],
            "mime": clean(mime)[:80] or "audio/webm",
            "sender": safe_sender,
            "at": time.time(),
        }
        rows.append(item)
        del rows[:-90]
        session["updated_at"] = time.time()
        session["message"] = "Screen audio relay active."
        return {"id": next_id, "session": screen_public_session(session)}


def screen_poll_audio_chunks(username: str, session_id: str, after: int = 0, receiver: str = "admin") -> dict:
    username = normalize_username(username)
    session_id = clean(session_id)
    safe_receiver = clean(receiver).lower() or "admin"
    expected_sender = "admin" if safe_receiver == "user" else "user"
    with SCREEN_LOCK:
        screen_cleanup_locked()
        session = SCREEN_SESSIONS.get(session_id)
        if not session or normalize_username(session.get("username", "")) != username:
            return {"session": {}, "chunks": []}
        rows = session.get("audio_chunks") if isinstance(session.get("audio_chunks"), list) else []
        chunks = [
            item for item in list(rows)
            if int(item.get("id", 0) or 0) > int(after or 0)
            and clean(item.get("sender", "user")).lower() == expected_sender
        ][-30:]
        return {"session": screen_public_session(session), "chunks": chunks}


def screen_poll_frame(username: str, session_id: str, after: int = 0) -> dict:
    username = normalize_username(username)
    session_id = clean(session_id)
    with SCREEN_LOCK:
        screen_cleanup_locked()
        session = SCREEN_SESSIONS.get(session_id)
        if not session or normalize_username(session.get("username", "")) != username:
            return {"session": {}, "frame": None}
        frame = session.get("frame") if isinstance(session.get("frame"), dict) else {}
        public_frame = None
        if int(frame.get("id", 0) or 0) > int(after or 0):
            public_frame = {
                "id": int(frame.get("id", 0) or 0),
                "data": str(frame.get("data", "") or ""),
                "width": int(frame.get("width", 0) or 0),
                "height": int(frame.get("height", 0) or 0),
                "at": float(frame.get("at", 0) or 0),
            }
        return {"session": screen_public_session(session), "frame": public_frame}


def screen_submit_signal(username: str, actor: str, session_id: str, signal_type: str, data: object) -> dict:
    username = normalize_username(username)
    actor = "admin" if clean(actor).lower() == "admin" else "user"
    signal_type = clean(signal_type).lower()
    session_id = clean(session_id)
    if signal_type not in {"offer", "answer", "candidate"}:
        raise RuntimeError("Screen WebRTC signal khong hop le.")
    if not isinstance(data, dict):
        raise RuntimeError("Screen WebRTC data khong hop le.")
    with SCREEN_LOCK:
        session = SCREEN_SESSIONS.get(session_id)
        if not session or normalize_username(session.get("username", "")) != username:
            raise RuntimeError("Screen session khong ton tai.")
        if clean(session.get("state", "")) != "active":
            raise RuntimeError("Screen session chua active.")
        webrtc = screen_webrtc_state(session)
        if signal_type == "offer":
            if actor != "admin":
                raise RuntimeError("Chi admin tao offer screen WebRTC.")
            webrtc["offer"] = data
            webrtc["answer"] = None
            webrtc["admin_candidates"] = []
            webrtc["user_candidates"] = []
            webrtc["candidate_id"] = 0
        elif signal_type == "answer":
            if actor != "user":
                raise RuntimeError("Chi user tao answer screen WebRTC.")
            webrtc["answer"] = data
        else:
            key = "admin_candidates" if actor == "admin" else "user_candidates"
            webrtc["candidate_id"] = int(webrtc.get("candidate_id", 0) or 0) + 1
            item = {"id": webrtc["candidate_id"], "candidate": data, "sender": actor, "at": time.time()}
            webrtc.setdefault(key, []).append(item)
            del webrtc[key][:-80]
        webrtc["version"] = int(webrtc.get("version", 0) or 0) + 1
        session["updated_at"] = time.time()
        return screen_public_session(session)


def screen_poll_signal(username: str, actor: str, session_id: str, after_candidate: int = 0) -> dict:
    username = normalize_username(username)
    actor = "admin" if clean(actor).lower() == "admin" else "user"
    with SCREEN_LOCK:
        screen_cleanup_locked()
        session = SCREEN_SESSIONS.get(clean(session_id))
        if not session or normalize_username(session.get("username", "")) != username:
            return {"session": {}, "offer": None, "answer": None, "candidates": [], "version": 0}
        webrtc = screen_webrtc_state(session)
        remote_key = "user_candidates" if actor == "admin" else "admin_candidates"
        candidates = [
            item for item in list(webrtc.get(remote_key, []) or [])
            if int(item.get("id", 0) or 0) > int(after_candidate or 0)
        ][-80:]
        return {
            "session": screen_public_session(session),
            "offer": webrtc.get("offer") if actor == "user" else None,
            "answer": webrtc.get("answer") if actor == "admin" else None,
            "candidates": candidates,
            "version": int(webrtc.get("version", 0) or 0),
        }


def normalize_screen_control_command(command: object) -> dict:
    source = command if isinstance(command, dict) else {}
    command_type = clean(source.get("type", "")).lower()
    allowed_types = {
        "cursor",
        "pointermove",
        "pointerdown",
        "pointerup",
        "click",
        "dblclick",
        "wheel",
        "keydown",
        "keyup",
    }
    if command_type not in allowed_types:
        raise RuntimeError("Lenh dieu khien man hinh khong hop le.")
    def unit(value: object) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.0
    def number(value: object, fallback: float = 0.0, minimum: float = -10000.0, maximum: float = 10000.0) -> float:
        try:
            return max(minimum, min(maximum, float(value)))
        except (TypeError, ValueError):
            return fallback
    row = {
        "type": command_type,
        "x": unit(source.get("x", 0)),
        "y": unit(source.get("y", 0)),
        "visible": bool(source.get("visible", True)),
        "button": int(number(source.get("button", 0), 0, -1, 4)),
        "buttons": int(number(source.get("buttons", 0), 0, 0, 7)),
        "delta_x": number(source.get("delta_x", source.get("deltaX", 0)), 0, -2400, 2400),
        "delta_y": number(source.get("delta_y", source.get("deltaY", 0)), 0, -2400, 2400),
        "ctrl": bool(source.get("ctrl", source.get("ctrlKey", False))),
        "alt": bool(source.get("alt", source.get("altKey", False))),
        "shift": bool(source.get("shift", source.get("shiftKey", False))),
        "meta": bool(source.get("meta", source.get("metaKey", False))),
        "dispatch": bool(source.get("dispatch", command_type != "cursor")),
    }
    if command_type in {"keydown", "keyup"}:
        row["key"] = str(source.get("key", "") or "")[:32]
        row["code"] = clean(source.get("code", ""))[:48]
        row["repeat"] = bool(source.get("repeat", False))
    return row


def screen_add_control(username: str, session_id: str, commands: object) -> dict:
    username = normalize_username(username)
    session_id = clean(session_id)
    raw_commands = commands if isinstance(commands, list) else [commands]
    normalized = [normalize_screen_control_command(item) for item in raw_commands][-40:]
    if not normalized:
        raise RuntimeError("Khong co lenh dieu khien man hinh.")
    with SCREEN_LOCK:
        screen_cleanup_locked()
        session = SCREEN_SESSIONS.get(session_id)
        if not session or normalize_username(session.get("username", "")) != username:
            raise RuntimeError("Screen session khong ton tai.")
        if clean(session.get("state", "")) != "active":
            raise RuntimeError("Screen session chua active.")
        control_id = int(session.get("control_id", 0) or 0)
        rows = session.get("controls")
        if not isinstance(rows, list):
            rows = []
        now = time.time()
        for command in normalized:
            control_id += 1
            rows.append({"id": control_id, "at": now, **command})
        del rows[:-SCREEN_CONTROL_LIMIT]
        session["controls"] = rows
        session["control_id"] = control_id
        session["updated_at"] = now
        return {"id": control_id, "session": screen_public_session(session)}


def screen_poll_control(username: str, session_id: str, after: int = 0) -> dict:
    username = normalize_username(username)
    session_id = clean(session_id)
    with SCREEN_LOCK:
        screen_cleanup_locked()
        session = SCREEN_SESSIONS.get(session_id)
        if not session or normalize_username(session.get("username", "")) != username:
            return {"session": {}, "commands": [], "control_id": int(after or 0)}
        rows = session.get("controls") if isinstance(session.get("controls"), list) else []
        commands = [
            item for item in rows
            if isinstance(item, dict) and int(item.get("id", 0) or 0) > int(after or 0)
        ][-80:]
        return {
            "session": screen_public_session(session),
            "commands": commands,
            "control_id": int(session.get("control_id", 0) or 0),
        }


def screen_transport_log_append(username: str, admin_username: str, payload: object = None) -> dict:
    source = payload if isinstance(payload, dict) else {}
    safe_urls = []
    raw_urls = source.get("ice_urls", source.get("iceUrls", []))
    if isinstance(raw_urls, list):
        for item in raw_urls[:12]:
            raw = clean(item)[:320]
            if raw:
                safe_urls.append(raw)
    row = {
        "at": utc_timestamp(),
        "username": normalize_username(username),
        "admin": normalize_username(admin_username),
        "event": clean(source.get("event", "manual-check"))[:80],
        "mode": clean(source.get("mode", ""))[:40],
        "session": clean(source.get("session", source.get("session_id", "")))[:80],
        "transport": clean(source.get("transport", ""))[:80],
        "control": clean(source.get("control", ""))[:80],
        "peer_state": clean(source.get("peer_state", source.get("peerState", "")))[:80],
        "ice_state": clean(source.get("ice_state", source.get("iceState", "")))[:80],
        "data_channel": clean(source.get("data_channel", source.get("dataChannel", "")))[:80],
        "frame_id": max(0, int(float(source.get("frame_id", source.get("frameId", 0)) or 0))),
        "has_turn": bool(source.get("has_turn", source.get("hasTurn", False))),
        "force_relay": bool(source.get("force_relay", source.get("forceRelay", False))),
        "ice_urls": safe_urls,
    }
    # Updated 2026-07-20: screen diagnostics share the durable SQLite event stream.
    database_append = globals().get("server_database_append_event")
    if not callable(database_append):
        raise RuntimeError("Screen transport PostgreSQL event writer is unavailable.")
    database_append("screen_transport", row)
    return {"log": row}
