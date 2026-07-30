# Loaded by FUTURE.server_parts.04_ai_language_agents into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def ai_agent_history_path(username: str) -> Path:
    safe_user = normalize_username(username)
    if not safe_user:
        raise RuntimeError("Chua dang nhap.")
    return USER_ROOT / safe_user / AI_AGENT_HISTORY_FILE_NAME


def normalize_ai_agent_history_entry(source: dict, existing: dict | None = None) -> dict:
    if not isinstance(source, dict):
        source = {}
    if not isinstance(existing, dict):
        existing = {}
    title = lesson_task_notice_text(source.get("title", source.get("topic", "")), limit=160)
    if not title:
        raise RuntimeError("Please edit a topic title before saving this AI answer.")
    english = lesson_task_notice_text(
        source.get("english", source.get("answer_en", source.get("translation_en", source.get("text", "")))),
        limit=12000,
    )
    vietnamese = lesson_task_notice_text(
        source.get("vietnamese", source.get("answer_vi", source.get("translation_vi", ""))),
        limit=12000,
    )
    if not english and not vietnamese:
        raise RuntimeError("AI answer text is empty.")
    created_at = clean(existing.get("created_at") or source.get("created_at") or utc_timestamp())
    entry_id = clean(existing.get("id") or source.get("id") or f"aihist-{uuid.uuid4().hex[:18]}")
    raw_context = source.get("context", {})
    context = ai_agent_scrub_runtime_context(raw_context) if isinstance(raw_context, dict) else {}
    return {
        "id": entry_id[:80],
        "title": title,
        "english": english,
        "vietnamese": vietnamese,
        "user_prompt": lesson_task_notice_text(source.get("user_prompt", source.get("prompt", "")), limit=3600),
        "space": clean(source.get("space", ""))[:80],
        "file": clean_path_value(source.get("file", ""))[:420],
        "word": clean(source.get("word", ""))[:180],
        "context": context,
        "created_at": created_at,
        "updated_at": utc_timestamp(),
    }


def read_ai_agent_history(username: str) -> dict:
    path = ai_agent_history_path(username)
    if postgres_backend_mode("AI_HISTORY_DOCUMENTS") == "postgres":
        from FUTURE.postgres.repositories import ai_history_documents as pg_ai_history_documents
        data = pg_ai_history_documents.read_json(path, {})
    else:
        data = server_database_read_document_json(path, {})
    rows = data.get("history", []) if isinstance(data, dict) else []
    if not isinstance(rows, list):
        rows = []
    return {
        "version": 1,
        "history": [item for item in rows if isinstance(item, dict)],
        "updated_at": clean(data.get("updated_at", "")) if isinstance(data, dict) else "",
    }


def write_ai_agent_history(username: str, payload: dict) -> None:
    path = ai_agent_history_path(username)
    if postgres_backend_mode("AI_HISTORY_DOCUMENTS") == "postgres":
        from FUTURE.postgres.repositories import ai_history_documents as pg_ai_history_documents
        pg_ai_history_documents.upsert_json(path, payload if isinstance(payload, dict) else {})
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, payload, indent=2)


def list_ai_agent_history(username: str, limit: int = 80) -> list[dict]:
    with AI_AGENT_HISTORY_LOCK:
        payload = read_ai_agent_history(username)
    rows = payload.get("history", [])
    rows = [item for item in rows if isinstance(item, dict)]
    rows.sort(key=lambda item: timestamp_order_key(item.get("updated_at") or item.get("created_at")), reverse=True)
    safe_limit = max(1, min(240, int(limit or 80)))
    return rows[:safe_limit]


def save_ai_agent_history(username: str, source: dict) -> dict:
    with AI_AGENT_HISTORY_LOCK:
        payload = read_ai_agent_history(username)
        rows = [item for item in payload.get("history", []) if isinstance(item, dict)]
        requested_id = clean(source.get("id", "")) if isinstance(source, dict) else ""
        existing = next((item for item in rows if requested_id and clean(item.get("id", "")) == requested_id), None)
        entry = normalize_ai_agent_history_entry(source, existing)
        rows = [item for item in rows if clean(item.get("id", "")) != clean(entry.get("id", ""))]
        rows.insert(0, entry)
        rows = rows[:240]
        out = {"version": 1, "history": rows, "updated_at": utc_timestamp()}
        write_ai_agent_history(username, out)
    return entry


def remove_ai_agent_history(username: str, entry_id: str) -> dict:
    wanted = clean(entry_id)
    if not wanted:
        raise RuntimeError("Missing history id.")
    with AI_AGENT_HISTORY_LOCK:
        payload = read_ai_agent_history(username)
        rows = [item for item in payload.get("history", []) if isinstance(item, dict)]
        next_rows = [item for item in rows if clean(item.get("id", "")) != wanted]
        out = {"version": 1, "history": next_rows, "updated_at": utc_timestamp()}
        write_ai_agent_history(username, out)
    return {"removed": len(rows) != len(next_rows), "history": next_rows}
