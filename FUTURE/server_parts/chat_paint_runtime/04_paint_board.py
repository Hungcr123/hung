# Loaded by FUTURE.server_parts.03_chat_paint_runtime into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def normalize_paint_data(data: object) -> str:
    raw = str(data or "").strip()
    if not raw:
        return ""
    if not raw.startswith("data:image/png;base64,"):
        raise RuntimeError("Du lieu paint khong hop le.")
    if len(raw) > PAINT_MAX_CHARS:
        raise RuntimeError("Du lieu paint qua lon.")
    return raw


def normalize_paint_cursor(cursor: object, role: str, label: str = "") -> dict:
    source = cursor if isinstance(cursor, dict) else {}
    safe_role = "admin" if clean(role).lower() == "admin" else "user"
    try:
        x = max(0.0, min(4096.0, float(source.get("x", 0) or 0)))
    except Exception:
        x = 0.0
    try:
        y = max(0.0, min(4096.0, float(source.get("y", 0) or 0)))
    except Exception:
        y = 0.0
    try:
        width = max(1, min(4096, int(float(source.get("width", 0) or 0))))
    except Exception:
        width = 0
    try:
        height = max(1, min(4096, int(float(source.get("height", 0) or 0))))
    except Exception:
        height = 0
    mode = clean(source.get("mode", ""))[:32]
    safe_label = clean(source.get("label", "") or label or ("Admin" if safe_role == "admin" else "User"))[:48]
    return {
        "role": safe_role,
        "label": safe_label,
        "x": round(x, 2),
        "y": round(y, 2),
        "width": width,
        "height": height,
        "mode": mode,
        "visible": truthy(source.get("visible", True), True),
        "updated_at": time.time(),
    }


def paint_visible_cursors(source: dict) -> dict:
    cursors = source.get("cursors", {}) if isinstance(source, dict) else {}
    result = {}
    if isinstance(cursors, dict):
        for role in ("user", "admin"):
            cursor = cursors.get(role, {})
            if not isinstance(cursor, dict):
                continue
            updated_at = float(cursor.get("updated_at", 0) or 0)
            visible = bool(cursor.get("visible", False))
            result[role] = {
                "role": role,
                "label": clean(cursor.get("label", "")),
                "x": float(cursor.get("x", 0) or 0),
                "y": float(cursor.get("y", 0) or 0),
                "width": int(cursor.get("width", 0) or 0),
                "height": int(cursor.get("height", 0) or 0),
                "mode": clean(cursor.get("mode", "")),
                "visible": visible,
                "updated_at": updated_at,
            }
    return result


def paint_public_state(username: str, include_data: bool = True, after: int = 0) -> dict:
    username = normalize_username(username)
    with PAINT_LOCK:
        source = PAINT_STATES.get(username, {}) if username else {}
        revision = int(source.get("revision", 0) or 0)
        payload = {
            "username": username,
            "revision": revision,
            "updated_at": float(source.get("updated_at", 0) or 0),
            "updated_by": clean(source.get("updated_by", "")),
            "width": int(source.get("width", 0) or 0),
            "height": int(source.get("height", 0) or 0),
            "has_data": bool(source.get("data", "")),
            "cursors": paint_visible_cursors(source),
        }
        if include_data and revision > int(after or 0):
            payload["data"] = source.get("data", "")
        return payload


def paint_update_state(username: str, data: object, width: object = 0, height: object = 0, updated_by: str = "user") -> dict:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    clean_data = normalize_paint_data(data)
    try:
        safe_width = max(1, min(4096, int(float(width or 0))))
    except Exception:
        safe_width = 0
    try:
        safe_height = max(1, min(4096, int(float(height or 0))))
    except Exception:
        safe_height = 0
    with PAINT_LOCK:
        previous = PAINT_STATES.get(username, {})
        revision = int(previous.get("revision", 0) or 0) + 1
        PAINT_STATES[username] = {
            "revision": revision,
            "updated_at": time.time(),
            "updated_by": "admin" if clean(updated_by).lower() == "admin" else "user",
            "width": safe_width or int(previous.get("width", 0) or 0),
            "height": safe_height or int(previous.get("height", 0) or 0),
            "data": clean_data,
            "cursors": previous.get("cursors", {}) if isinstance(previous.get("cursors", {}), dict) else {},
        }
    return paint_public_state(username, include_data=True)


def paint_update_cursor(username: str, cursor: object, role: str = "user", label: str = "") -> dict:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    safe_role = "admin" if clean(role).lower() == "admin" else "user"
    with PAINT_LOCK:
        previous = PAINT_STATES.get(username, {})
        next_state = dict(previous) if isinstance(previous, dict) else {}
        cursors = next_state.get("cursors", {})
        if not isinstance(cursors, dict):
            cursors = {}
        cursors[safe_role] = normalize_paint_cursor(cursor, safe_role, label)
        next_state["cursors"] = cursors
        next_state["cursor_updated_at"] = time.time()
        PAINT_STATES[username] = next_state
    return paint_public_state(username, include_data=False)
