# Loaded by FUTURE.server_parts.04_ai_language_agents into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def word_agent_key(value: object = "") -> str:
    return vocab_key(clean(value))


def word_agent_clean_list(value: object = None, limit: int = 16) -> list[str]:
    raw = value
    if raw is None:
        return []
    if isinstance(raw, str):
        items = [raw]
    elif isinstance(raw, (list, tuple, set)):
        items = list(raw)
    else:
        items = [raw]
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = lesson_task_notice_text(item, limit=420)
        if not text:
            continue
        key = word_agent_key(text)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= max(1, int(limit or 16)):
            break
    return out


def word_agent_clean_examples(value: object = None, fallback_en: str = "", fallback_vi: str = "") -> list[dict]:
    if isinstance(value, str):
        text = clean(value)
        if text:
            try:
                decoded = json.loads(text)
                rows = decoded if isinstance(decoded, list) else [decoded]
            except Exception:
                rows = [text]
        else:
            rows = []
    elif isinstance(value, dict):
        rows = [value]
    else:
        rows = value if isinstance(value, list) else []
    out: list[dict] = []
    for row in rows:
        if isinstance(row, dict):
            en = lesson_task_notice_text(row.get("en", row.get("english", row.get("example", ""))), limit=520)
            vi = lesson_task_notice_text(row.get("vi", row.get("vietnamese", row.get("translation", ""))), limit=520)
        else:
            en = lesson_task_notice_text(row, limit=520)
            vi = ""
        if en or vi:
            out.append({"en": en, "vi": vi})
        if len(out) >= 8:
            break
    if not out and (fallback_en or fallback_vi):
        out.append({
            "en": lesson_task_notice_text(fallback_en, limit=520),
            "vi": lesson_task_notice_text(fallback_vi, limit=520),
        })
    return out


def word_agent_phrase_extra(word: object = "") -> dict:
    key = word_agent_key(word)
    if not key or " " not in key:
        return {}
    try:
        configure_paths()
        from module_main.GrammarPharse.qm_usage_data import QM_USAGE_NOTES  # noqa: PLC0415
    except Exception:
        return {}
    notes = QM_USAGE_NOTES if isinstance(QM_USAGE_NOTES, dict) else {}
    record = notes.get(key)
    if not isinstance(record, dict):
        for candidate_key, candidate in notes.items():
            if word_agent_key(candidate_key) == key and isinstance(candidate, dict):
                record = candidate
                break
    if not isinstance(record, dict):
        return {}
    examples = word_agent_clean_examples(record.get("examples"))
    return {
        "word": lesson_task_notice_text(record.get("word") or word, limit=180),
        "meaning": lesson_task_notice_text(record.get("meaning", ""), limit=900),
        "type": lesson_task_notice_text(record.get("type", record.get("pos", "")), limit=160),
        "usage": lesson_task_notice_text(record.get("usage", ""), limit=900),
        "context": lesson_task_notice_text(record.get("context", ""), limit=900),
        "note": lesson_task_notice_text(record.get("note", ""), limit=900),
        "collocations": word_agent_clean_list(record.get("collocations"), 16),
        "examples": examples,
        "notes": word_agent_clean_list(record.get("notes"), 10),
        "kind": "phrasal_verb" if re.search(r"\bphrasal\b|cụm\s+động\s+từ", lesson_task_notice_text(record.get("type", record.get("pos", ""))), re.IGNORECASE) else "phrase",
    }


def normalize_word_agent_detail(source: object = None) -> dict:
    data = source if isinstance(source, dict) else {}
    word = lesson_task_notice_text(data.get("word", data.get("w", data.get("lemma", ""))), limit=180)
    surface = lesson_task_notice_text(data.get("surface", data.get("token", data.get("original", ""))), limit=220)
    extra = word_agent_phrase_extra(word or surface)
    if not word:
        word = lesson_task_notice_text(extra.get("word", surface), limit=180)
    meaning = lesson_task_notice_text(data.get("meaning", data.get("m", "")), limit=1200) or lesson_task_notice_text(extra.get("meaning", ""), limit=1200)
    word_type = lesson_task_notice_text(data.get("type", data.get("ty", data.get("pos", ""))), limit=180) or lesson_task_notice_text(extra.get("type", ""), limit=180)
    example = lesson_task_notice_text(data.get("example", ""), limit=620)
    example_vi = lesson_task_notice_text(data.get("example_vi", data.get("exampleVi", "")), limit=620)
    examples = word_agent_clean_examples(data.get("examples"), example, example_vi)
    if not examples:
        examples = word_agent_clean_examples(extra.get("examples"))
    return {
        "word": word,
        "surface": surface,
        "meaning": meaning,
        "pron": lesson_task_notice_text(data.get("pron", data.get("p", "")), limit=180),
        "type": word_type,
        "pron_us": lesson_task_notice_text(data.get("pron_us", data.get("pronUS", "")), limit=180),
        "pron_uk": lesson_task_notice_text(data.get("pron_uk", data.get("pronUK", "")), limit=180),
        "usage": lesson_task_notice_text(data.get("usage", ""), limit=1200) or lesson_task_notice_text(extra.get("usage", ""), limit=1200),
        "context": lesson_task_notice_text(data.get("context", ""), limit=1200) or lesson_task_notice_text(extra.get("context", ""), limit=1200),
        "note": lesson_task_notice_text(data.get("note", data.get("notes_text", "")), limit=1200) or lesson_task_notice_text(extra.get("note", ""), limit=1200),
        "collocations": word_agent_clean_list(data.get("collocations"), 16) or word_agent_clean_list(extra.get("collocations"), 16),
        "examples": examples,
        "notes": word_agent_clean_list(data.get("notes"), 10) or word_agent_clean_list(extra.get("notes"), 10),
        "match_mode": lesson_task_notice_text(data.get("match_mode", data.get("matchMode", "")), limit=80),
        "kind": lesson_task_notice_text(data.get("kind", ""), limit=80) or lesson_task_notice_text(extra.get("kind", ""), limit=80),
    }


def word_agent_detail_text(detail: dict) -> str:
    parts = []
    for label, value in (
        ("Word or phrase", detail.get("word")),
        ("Matched text", detail.get("surface")),
        ("Type", detail.get("type")),
        ("Pronunciation", detail.get("pron")),
        ("Meaning", detail.get("meaning")),
        ("Usage", detail.get("usage")),
        ("Context", detail.get("context")),
        ("Note", detail.get("note")),
        ("Match mode", detail.get("match_mode")),
        ("Kind", detail.get("kind")),
    ):
        text = lesson_task_notice_text(value, limit=1200)
        if text:
            parts.append(f"{label}: {text}")
    collocations = word_agent_clean_list(detail.get("collocations"), 16)
    if collocations:
        parts.append("Collocations: " + "; ".join(collocations))
    examples = word_agent_clean_examples(detail.get("examples"))
    if examples:
        example_lines = []
        for example in examples:
            en = lesson_task_notice_text(example.get("en", ""), limit=520)
            vi = lesson_task_notice_text(example.get("vi", ""), limit=520)
            example_lines.append(f"- {en}" + (f" = {vi}" if vi else ""))
        parts.append("Known examples:\n" + "\n".join(example_lines))
    notes = word_agent_clean_list(detail.get("notes"), 10)
    if notes:
        parts.append("Extra notes: " + "; ".join(notes))
    return "\n".join(parts)


def read_word_agent_history() -> dict:
    if postgres_backend_mode("AI_HISTORY_DOCUMENTS") == "postgres":
        from FUTURE.postgres.repositories import ai_history_documents as pg_ai_history_documents
        data = pg_ai_history_documents.read_json(WORD_AGENT_HISTORY_FILE, {})
    else:
        data = server_database_read_document_json(WORD_AGENT_HISTORY_FILE, {})
    rows = data.get("history", []) if isinstance(data, dict) else []
    if not isinstance(rows, list):
        rows = []
    return {
        "version": 1,
        "history": [row for row in rows if isinstance(row, dict)],
        "updated_at": clean(data.get("updated_at", "")) if isinstance(data, dict) else "",
    }


def rebuild_word_agent_history_cache(payload: dict, mtime_ns: int | None = None) -> dict:
    source = payload if isinstance(payload, dict) else {"version": 1, "history": [], "updated_at": ""}
    rows = [row for row in source.get("history", []) if isinstance(row, dict)]
    normalized_rows = []
    for row in rows:
        key = clean(row.get("word_key", "")) or word_agent_key(row.get("word", ""))
        if not key:
            continue
        if clean(row.get("word_key", "")) != key:
            row = dict(row)
            row["word_key"] = key
        normalized_rows.append(row)
    normalized_rows.sort(key=lambda row: timestamp_order_key(row.get("created_at", "")), reverse=True)
    by_key: dict[str, list[dict]] = {}
    latest_by_key: dict[str, dict] = {}
    for row in normalized_rows:
        key = clean(row.get("word_key", ""))
        if not key:
            continue
        by_key.setdefault(key, []).append(row)
        latest_by_key.setdefault(key, row)
    cache_payload = {
        "version": 1,
        "history": normalized_rows,
        "updated_at": clean(source.get("updated_at", "")),
    }
    WORD_AGENT_HISTORY_CACHE["mtime_ns"] = int(mtime_ns if mtime_ns is not None else -1)
    WORD_AGENT_HISTORY_CACHE["payload"] = cache_payload
    WORD_AGENT_HISTORY_CACHE["rows"] = normalized_rows
    WORD_AGENT_HISTORY_CACHE["by_key"] = by_key
    WORD_AGENT_HISTORY_CACHE["latest_by_key"] = latest_by_key
    return WORD_AGENT_HISTORY_CACHE


def get_word_agent_history_cache() -> dict:
    if postgres_backend_mode("AI_HISTORY_DOCUMENTS") == "postgres":
        from FUTURE.postgres.repositories import ai_history_documents as pg_ai_history_documents
        mtime_ns = int(pg_ai_history_documents.signature(WORD_AGENT_HISTORY_FILE)[1] or -1)
    else:
        mtime_ns = int(server_database_document_signature(WORD_AGENT_HISTORY_FILE)[1] or -1)
    if int(WORD_AGENT_HISTORY_CACHE.get("mtime_ns", -2)) == int(mtime_ns):
        return WORD_AGENT_HISTORY_CACHE
    payload = read_word_agent_history()
    return rebuild_word_agent_history_cache(payload, mtime_ns)


def write_word_agent_history(payload: dict) -> None:
    if postgres_backend_mode("AI_HISTORY_DOCUMENTS") == "postgres":
        from FUTURE.postgres.repositories import ai_history_documents as pg_ai_history_documents
        pg_ai_history_documents.upsert_json(WORD_AGENT_HISTORY_FILE, payload if isinstance(payload, dict) else {})
        mtime_ns = int(pg_ai_history_documents.signature(WORD_AGENT_HISTORY_FILE)[1] or -1)
        rebuild_word_agent_history_cache(payload, mtime_ns)
        return
    WORD_AGENT_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(WORD_AGENT_HISTORY_FILE, payload, indent=2)
    mtime_ns = int(server_database_document_signature(WORD_AGENT_HISTORY_FILE)[1] or -1)
    rebuild_word_agent_history_cache(payload, mtime_ns)


def list_word_agent_history(word: object = "", limit: int = 80) -> list[dict]:
    wanted_key = word_agent_key(word)
    safe_limit = max(1, min(240, int(limit or 80)))
    with WORD_AGENT_HISTORY_LOCK:
        cache = get_word_agent_history_cache()
        if wanted_key:
            rows = list((cache.get("by_key") or {}).get(wanted_key, []))
        else:
            rows = list(cache.get("rows") or [])
    return rows[:safe_limit]


def word_agent_latest_map_for_terms(terms: object = None) -> dict:
    raw_terms = terms if isinstance(terms, (list, tuple, set)) else [terms]
    wanted: set[str] = set()
    for term in raw_terms:
        key = word_agent_key(term)
        if key:
            wanted.add(key)
    if not wanted:
        return {}
    with WORD_AGENT_HISTORY_LOCK:
        latest_by_key = dict((get_word_agent_history_cache().get("latest_by_key") or {}))
    return {key: latest_by_key[key] for key in wanted if key in latest_by_key}
