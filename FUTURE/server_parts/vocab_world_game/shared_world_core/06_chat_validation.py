VIETNAMESE_DIACRITIC_RE = re.compile(r"[ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠàáâãèéêìíòóôõùúăđĩũơƯưẠ-ỹ]")
COMMON_ENGLISH_CHAT_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "do", "does", "did", "for",
    "from", "go", "good", "hello", "hi", "how", "i", "if", "in", "is", "it", "like", "me", "my",
    "no", "not", "of", "ok", "okay", "on", "or", "please", "so", "the", "this", "to", "too",
    "up", "very", "we", "what", "when", "where", "who", "why", "with", "yes", "you", "your",
    "am", "im", "i'm", "dont", "don't", "cant", "can't", "lets", "let's", "thanks", "thank",
}


def shared_world_chat_token_valid(token: str, qmdict: dict) -> bool:
    key = clean(token).lower().replace("’", "'").strip("'")
    if not key:
        return False
    if key in COMMON_ENGLISH_CHAT_WORDS:
        return True
    if not re.fullmatch(r"[a-z]+(?:'[a-z]+)?", key):
        return False
    signature_key = qmdict_source_signature_key()
    cache_key = (signature_key, key)
    with QMDICT_CHAT_TOKEN_CACHE_LOCK:
        cached = QMDICT_CHAT_TOKEN_CACHE.get(cache_key)
        if isinstance(cached, bool):
            return cached
    lookup_key = key
    valid = False
    try:
        configure_paths()
        from module_main.QM_GATE import viewer_vocab_runtime as vocab_runtime  # noqa: PLC0415
        valid_lines = []
        vocab_runtime.is_valid_word(lookup_key, qmdict, valid_lines, number="1")
        if valid_lines:
            valid = True
        elif "'" in lookup_key:
            valid_lines = []
            vocab_runtime.is_valid_word(lookup_key.replace("'", ""), qmdict, valid_lines, number="1")
            valid = bool(valid_lines)
        else:
            valid = False
    except Exception:
        valid = bool(re.fullmatch(r"[a-z]{1,18}", key))
    with QMDICT_CHAT_TOKEN_CACHE_LOCK:
        QMDICT_CHAT_TOKEN_CACHE[cache_key] = bool(valid)
        if len(QMDICT_CHAT_TOKEN_CACHE) > QMDICT_CHAT_TOKEN_CACHE_LIMIT:
            QMDICT_CHAT_TOKEN_CACHE.clear()
    return bool(valid)


def validate_shared_world_chat_message(message: str) -> dict:
    text = lesson_task_notice_text(message, limit=160)
    if not text:
        return {"ok": False, "error": "Message is empty."}
    settings = load_server_settings()
    min_percent = max(1, min(100, space_w_int(settings.get("qm_city_chat_min_english_percent", 50), 50)))
    invalid_run_limit = max(1, min(20, space_w_int(settings.get("qm_city_chat_invalid_run_limit", 4), 4)))
    if VIETNAMESE_DIACRITIC_RE.search(text):
        return {"ok": False, "error": "Please chat in English. Vietnamese accents are not accepted in QM-City."}
    tokens = re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)?", text)
    if not tokens:
        return {"ok": False, "error": "Please chat in English words."}
    try:
        _vocab_runtime, qmdict = qmdict_runtime_and_dict()
    except Exception:
        qmdict = {}
    valid_count = 0
    invalid_run = 0
    longest_invalid_run = 0
    for token in tokens:
        if shared_world_chat_token_valid(token, qmdict if isinstance(qmdict, dict) else {}):
            valid_count += 1
            invalid_run = 0
        else:
            invalid_run += 1
            longest_invalid_run = max(longest_invalid_run, invalid_run)
    percent = round((valid_count / max(1, len(tokens))) * 100)
    if percent < min_percent:
        return {"ok": False, "error": f"Please chat in English. English word score {percent}% is below {min_percent}%."}
    if longest_invalid_run >= invalid_run_limit:
        return {"ok": False, "error": f"Please chat in English. {longest_invalid_run} invalid words appeared in a row."}
    return {
        "ok": True,
        "message": text,
        "english_percent": percent,
        "valid_tokens": valid_count,
        "token_count": len(tokens),
    }


def shared_world_chat_name_key(value: object = "") -> str:
    text = clean(value).lower().replace("’", "'")
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def shared_world_chat_row_display_name(username: str, row: dict | None = None) -> str:
    username = normalize_username(username)
    data = row if isinstance(row, dict) else {}
    return clean(data.get("display_name", "")) or clean(shared_world_profile(username).get("display_name", "")) or username


def shared_world_chat_current_xy(row: dict | None = None) -> tuple[float, float]:
    data = row if isinstance(row, dict) else {}
    return (
        shared_world_clamp(data.get("x", data.get("tx", 0.5))),
        shared_world_clamp(data.get("y", data.get("ty", 0.5))),
    )


def shared_world_chat_target_keys(username: str, row: dict | None = None) -> set[str]:
    username = normalize_username(username)
    data = row if isinstance(row, dict) else {}
    names = {
        username,
        clean(data.get("display_name", "")),
        clean(shared_world_profile(username).get("display_name", "")),
    }
    result = {shared_world_chat_name_key(name) for name in names if clean(name)}
    return {item for item in result if len(item.replace(" ", "")) >= 3}


def shared_world_chat_mentions_target(text: str, username: str, row: dict | None = None) -> bool:
    haystack = f" {shared_world_chat_name_key(text)} "
    if not haystack.strip():
        return False
    compact_haystack = haystack.replace(" ", "")
    for key in shared_world_chat_target_keys(username, row):
        if f" {key} " in haystack:
            return True
        compact_key = key.replace(" ", "")
        if len(compact_key) >= 4 and compact_key in compact_haystack:
            return True
    return False


def shared_world_npc_chat_available(row: dict, now: float) -> bool:
    if not isinstance(row, dict) or not bool(row.get("npc_bot")) or bool(row.get("admin_actor")):
        return False
    if now < float(row.get("bot_chat_next_allowed_at", 0) or 0):
        return False
    pending_until = float(row.get("bot_chat_pending_until", 0) or 0)
    if pending_until and now < pending_until:
        return False
    return True
