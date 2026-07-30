# Loaded by FUTURE.server_parts.02_users_auth_settings into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def sentence_case_first(value: str) -> str:
    text = clean(value)
    if not text:
        return ""
    for index, char in enumerate(text):
        if char.isalpha():
            return text[:index] + char.upper() + text[index + 1:]
    return text


def split_announcement_text(value: str) -> list[str]:
    raw = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    parts: list[str] = []
    for line in raw.split("\n"):
        item = sentence_case_first(line)
        if item:
            parts.append(item[:240])
        if len(parts) >= 8:
            break
    return parts


def load_announcements() -> dict:
    if postgres_backend_mode("ANNOUNCEMENTS") == "postgres":
        from FUTURE.postgres.repositories import announcements as pg_announcements
        payload = pg_announcements.load()
        if isinstance(payload, dict):
            return {
                "items": split_announcement_text("\n".join(str(item or "") for item in payload.get("items", []))),
                "updated_at": clean(payload.get("updated_at", "")),
            }
    with ANNOUNCEMENT_LOCK:
        payload = server_database_read_document_json(ANNOUNCEMENTS_FILE, None)
        if not isinstance(payload, dict):
            return {
                "items": [
                    "Chào mừng học viên đến hệ thống luyện dịch Future.",
                    "Hãy đăng nhập để tải bài học và bắt đầu luyện tập.",
                ],
                "updated_at": "",
            }
        items = payload.get("items", [])
        return {
            "items": split_announcement_text("\n".join(str(item or "") for item in items)),
            "updated_at": clean(payload.get("updated_at", "")),
        }


def announcements_response_cache_row() -> dict:
    if postgres_backend_mode("ANNOUNCEMENTS") == "postgres":
        from FUTURE.postgres.repositories import announcements as pg_announcements
        signature = pg_announcements.signature()
    else:
        signature = server_database_document_signature(ANNOUNCEMENTS_FILE)
    cache = globals().setdefault("ANNOUNCEMENTS_RESPONSE_BYTES_CACHE", {})
    lock = globals().setdefault("ANNOUNCEMENTS_RESPONSE_BYTES_CACHE_LOCK", threading.RLock())
    with lock:
        row = cache.get("row") if isinstance(cache, dict) else None
        if isinstance(row, dict) and row.get("signature") == signature and isinstance(row.get("bytes"), bytes):
            return {**row, "cache_hit": True}
    payload = load_announcements()
    response = {"ok": True, "raw": "\n".join(payload.get("items", [])), **payload}
    data = json_bytes(response)
    row = {
        "signature": signature,
        "bytes": data,
        "etag": f'"announcements-{hashlib.sha1(data).hexdigest()}"',
        "cache_hit": False,
    }
    with lock:
        cache["row"] = row
    return row


def save_announcements(text: str) -> dict:
    items = split_announcement_text(text)
    payload = {
        "items": items,
        "updated_at": utc_timestamp(),
    }
    if postgres_backend_mode("ANNOUNCEMENTS") == "postgres":
        from FUTURE.postgres.repositories import announcements as pg_announcements
        saved = pg_announcements.save_items(items, payload["updated_at"])
        return {"items": list(saved.get("items", items)), "updated_at": clean(saved.get("updated_at", payload["updated_at"]))}
    with ANNOUNCEMENT_LOCK:
        USER_ROOT.mkdir(parents=True, exist_ok=True)
        atomic_write_json(ANNOUNCEMENTS_FILE, payload, indent=2)
    return payload
