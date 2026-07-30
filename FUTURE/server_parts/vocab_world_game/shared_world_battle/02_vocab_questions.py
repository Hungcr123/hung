def shared_world_battle_meaning_is_english_only(text: str) -> bool:
    value = clean(text)
    if not value:
        return False
    if re.search(r"[à-ỹÀ-ỸđĐ]", value):
        return False
    letters = len(re.findall(r"[A-Za-z]", value))
    return letters >= 5 and letters >= max(5, int(len(value) * 0.42))


def shared_world_battle_dictionary_entry(word: str) -> dict:
    key = vocab_key(word)
    if not key:
        return {}
    cached = SHARED_WORLD_BATTLE_DICT_CACHE.get(key)
    if cached and time.time() - cached[0] < 3600:
        return dict(cached[1])
    result: dict = {}
    try:
        vocab_runtime, qmdict = qmdict_runtime_and_dict()
        valid_lines = []
        vocab_runtime.is_valid_word(key, qmdict, valid_lines, number="1")
        for line in list(valid_lines or []):
            try:
                item = vocab_runtime.vocab_item_from_valid_line(line)
            except Exception:
                item = None
            summary = pdf_vocab_item_summary(item, surface=word)
            if not summary:
                continue
            summary_key = vocab_key(summary.get("word", ""))
            if summary_key and summary_key != key and key not in {vocab_key(summary.get("surface", "")), summary_key}:
                continue
            meaning = clean(summary.get("meaning", ""))
            if not meaning:
                continue
            result = {
                "word": clean(summary.get("word", "")) or word,
                "meaning": meaning,
                "type": clean(summary.get("type", "")),
                "pron": clean(summary.get("pron", "")) or clean(summary.get("pron_uk", "")) or clean(summary.get("pron_us", "")),
            }
            break
    except Exception:
        result = {}
    SHARED_WORLD_BATTLE_DICT_CACHE[key] = (time.time(), result)
    return dict(result)


def shared_world_battle_vocab_pool(username: str, limit: int = SHARED_WORLD_BATTLE_VOCAB_POOL_LIMIT) -> list[dict]:
    username = normalize_username(username)
    source_username = "hung" if shared_world_is_npc_identity(username) else username
    cache_key = f"{username}|source:{source_username}" if source_username != username else username
    cached = SHARED_WORLD_BATTLE_VOCAB_CACHE.get(cache_key)
    if cached and time.time() - cached[0] < 600:
        return cached[1][: max(1, min(SHARED_WORLD_BATTLE_VOCAB_POOL_LIMIT, int(limit or SHARED_WORLD_BATTLE_VOCAB_POOL_LIMIT)))]
    registry = read_user_vocab_registry_snapshot(source_username)
    words = registry.get("words") if isinstance(registry.get("words"), dict) else {}
    rows: list[dict] = []
    for key, item in words.items():
        if not isinstance(item, dict):
            continue
        word = clean(item.get("word") or key)
        if not word:
            continue
        raw_meaning = clean(item.get("meaning", ""))
        dictionary_entry = shared_world_battle_dictionary_entry(word)
        meaning = clean(dictionary_entry.get("meaning", "")) or raw_meaning
        if shared_world_battle_meaning_is_english_only(meaning):
            meaning = ""
        rows.append(
            {
                "word": clean(dictionary_entry.get("word", "")) or word,
                "answer": vocab_key(word),
                "meaning": meaning,
                "type": clean(dictionary_entry.get("type", "")) or clean(item.get("type", "")),
                "pron": clean(dictionary_entry.get("pron", "")) or clean(item.get("pron", "")),
            }
        )
    rows.sort(key=lambda item: (item.get("word", "").lower(), item.get("meaning", "").lower()))
    if not rows:
        rows = [
            {"word": "hello", "answer": "hello", "meaning": "lời chào; xin chào", "type": "thán từ", "pron": ""},
            {"word": "student", "answer": "student", "meaning": "học sinh; sinh viên; người học", "type": "danh từ", "pron": ""},
            {"word": "learn", "answer": "learn", "meaning": "học; học hỏi; tiếp thu kiến thức", "type": "động từ", "pron": ""},
        ]
    rows = rows[: max(1, min(SHARED_WORLD_BATTLE_VOCAB_POOL_LIMIT, int(limit or SHARED_WORLD_BATTLE_VOCAB_POOL_LIMIT)))]
    SHARED_WORLD_BATTLE_VOCAB_CACHE[cache_key] = (time.time(), rows)
    return rows


def load_shared_world_battle_word_history() -> dict[str, list[str]]:
    try:
        mtime = float(server_database_document_signature(SHARED_WORLD_BATTLE_WORD_HISTORY_FILE)[1] or 0) / 1_000_000_000
        cached_users = SHARED_WORLD_BATTLE_WORD_HISTORY_CACHE.get("users")
        if isinstance(cached_users, dict) and float(SHARED_WORLD_BATTLE_WORD_HISTORY_CACHE.get("mtime") or -1.0) == mtime:
            return {normalize_username(user): list(words) for user, words in cached_users.items() if normalize_username(user)}
        payload = server_database_read_document_json(SHARED_WORLD_BATTLE_WORD_HISTORY_FILE, {})
        raw_users = payload.get("users") if isinstance(payload, dict) and isinstance(payload.get("users"), dict) else {}
        users: dict[str, list[str]] = {}
        for user, row in raw_users.items():
            safe_user = normalize_username(user)
            if not safe_user:
                continue
            words_source = row.get("words") if isinstance(row, dict) else row
            words = []
            seen = set()
            for value in words_source if isinstance(words_source, list) else []:
                key = vocab_key(value)
                if key and key not in seen:
                    seen.add(key)
                    words.append(key)
            users[safe_user] = words[-SHARED_WORLD_BATTLE_HISTORY_LIMIT:]
        SHARED_WORLD_BATTLE_WORD_HISTORY_CACHE["mtime"] = mtime
        SHARED_WORLD_BATTLE_WORD_HISTORY_CACHE["users"] = users
        return {user: list(words) for user, words in users.items()}
    except Exception:
        if postgres_backend_mode("QM_CITY_DOCUMENTS") == "postgres":
            raise
    SHARED_WORLD_BATTLE_WORD_HISTORY_CACHE["mtime"] = 0.0
    SHARED_WORLD_BATTLE_WORD_HISTORY_CACHE["users"] = {}
    return {}


def write_shared_world_battle_word_history(users: dict[str, list[str]]) -> None:
    SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    normalized: dict[str, list[str]] = {}
    for user, words in (users or {}).items():
        safe_user = normalize_username(user)
        if not safe_user:
            continue
        seen = set()
        clean_words = []
        for value in words if isinstance(words, list) else []:
            key = vocab_key(value)
            if key and key not in seen:
                seen.add(key)
                clean_words.append(key)
        normalized[safe_user] = clean_words[-SHARED_WORLD_BATTLE_HISTORY_LIMIT:]
    payload = {
        "version": 1,
        "updated_at": utc_timestamp(),
        "users": {
            user: {"words": words, "count": len(words), "updated_at": utc_timestamp()}
            for user, words in normalized.items()
        },
    }
    atomic_write_json(SHARED_WORLD_BATTLE_WORD_HISTORY_FILE, payload, indent=2)
    mtime = float(server_database_document_signature(SHARED_WORLD_BATTLE_WORD_HISTORY_FILE)[1] or time.time_ns()) / 1_000_000_000
    SHARED_WORLD_BATTLE_WORD_HISTORY_CACHE["mtime"] = mtime
    SHARED_WORLD_BATTLE_WORD_HISTORY_CACHE["users"] = normalized


def shared_world_battle_user_asked_set(username: str) -> set[str]:
    username = normalize_username(username)
    if not username:
        return set()
    users = load_shared_world_battle_word_history()
    history = set(vocab_key(item) for item in users.get(username, []) if vocab_key(item))
    history.update(SHARED_WORLD_BATTLE_ACTIVE_ASKED_CACHE.get(username, set()))
    return history


def shared_world_battle_mark_asked_word(battle: dict, username: str, word: str) -> None:
    username = normalize_username(username)
    key = vocab_key(word)
    if not username or not key or not isinstance(battle, dict):
        return
    asked_map = battle.setdefault("asked_words", {})
    if not isinstance(asked_map, dict):
        asked_map = {}
    current = [vocab_key(item) for item in (asked_map.get(username) if isinstance(asked_map.get(username), list) else [])]
    current = [item for item in current if item and item != key] + [key]
    asked_map[username] = current[-SHARED_WORLD_BATTLE_HISTORY_LIMIT:]
    battle["asked_words"] = asked_map
    SHARED_WORLD_BATTLE_ACTIVE_ASKED_CACHE.setdefault(username, set()).add(key)


def shared_world_battle_flush_word_history(battle: dict) -> None:
    if not isinstance(battle, dict):
        return
    asked_map = battle.get("asked_words") if isinstance(battle.get("asked_words"), dict) else {}
    if not asked_map:
        return
    users = load_shared_world_battle_word_history()
    changed = False
    for user, words in asked_map.items():
        safe_user = normalize_username(user)
        if not safe_user:
            continue
        existing = [vocab_key(item) for item in users.get(safe_user, []) if vocab_key(item)]
        seen = set(existing)
        merged = list(existing)
        for value in words if isinstance(words, list) else []:
            key = vocab_key(value)
            if key and key not in seen:
                seen.add(key)
                merged.append(key)
                changed = True
        active = SHARED_WORLD_BATTLE_ACTIVE_ASKED_CACHE.get(safe_user, set())
        for key in list(active):
            if key and key not in seen:
                seen.add(key)
                merged.append(key)
                changed = True
        users[safe_user] = merged[-SHARED_WORLD_BATTLE_HISTORY_LIMIT:]
        SHARED_WORLD_BATTLE_ACTIVE_ASKED_CACHE[safe_user] = set(users[safe_user])
    if changed:
        write_shared_world_battle_word_history(users)


def shared_world_battle_pick_training_kind(username: str, battle: dict | None = None) -> str:
    username = normalize_username(username)
    sequence = [
        qm_city_training_normalize_question_kind(kind)
        for kind in QM_CITY_TRAINING_RANDOM_KIND_SEQUENCE
        if qm_city_training_normalize_question_kind(kind)
    ]
    if not sequence:
        return ""
    if not isinstance(battle, dict) or not username:
        return secrets.choice(sequence)
    recent_map = battle.setdefault("recent_question_kinds", {})
    if not isinstance(recent_map, dict):
        recent_map = {}
        battle["recent_question_kinds"] = recent_map
    recent = [
        qm_city_training_normalize_question_kind(item)
        for item in (recent_map.get(username) if isinstance(recent_map.get(username), list) else [])
    ]
    recent_tail = set(item for item in recent[-4:] if item)
    candidates = [kind for kind in sequence if kind not in recent_tail] or sequence
    kind = secrets.choice(candidates)
    recent_map[username] = ([item for item in recent if item] + [kind])[-12:]
    battle["recent_question_kinds"] = recent_map
    return kind


def shared_world_battle_pick_question(username: str, battle: dict | None = None) -> dict:
    if isinstance(battle, dict):
        recent_key = normalize_username(username)
        try:
            preferred_kind = shared_world_battle_pick_training_kind(recent_key, battle)
            asked_map = battle.setdefault("asked_words", {})
            battle_asked = [vocab_key(item) for item in (asked_map.get(recent_key) if isinstance(asked_map.get(recent_key), list) else [])]
            recent_map = battle.setdefault("recent_words", {})
            recent = [vocab_key(item) for item in (recent_map.get(recent_key) if isinstance(recent_map.get(recent_key), list) else [])]
            adapter = {"asked": [item for item in [*shared_world_battle_user_asked_set(recent_key), *recent, *battle_asked] if item]}
            question = qm_city_training_pick_question(recent_key, adapter, preferred_kind)
            if clean(question.get("prompt", "")) and clean(question.get("answer", "")):
                answer_key = vocab_key(question.get("answer_text", question.get("answer", "")))
                if answer_key:
                    items = [item for item in recent if item and item != answer_key] + [answer_key]
                    recent_map[recent_key] = items[-20:]
                    battle["recent_words"] = recent_map
                    shared_world_battle_mark_asked_word(battle, recent_key, answer_key)
                question["battle_source"] = "qm_city_training"
                question["battleSource"] = "qm_city_training"
                question["battle_kind"] = preferred_kind
                question["battleKind"] = preferred_kind
                return question
        except Exception as exc:
            stt_debug_log("shared_world_battle_training_question_failed", user=recent_key, error=str(exc))
    pool = shared_world_battle_vocab_pool(username)
    recent_key = normalize_username(username)
    recent_map = battle.setdefault("recent_words", {}) if isinstance(battle, dict) else {}
    recent = [vocab_key(item) for item in (recent_map.get(recent_key) if isinstance(recent_map.get(recent_key), list) else [])]
    asked_map = battle.setdefault("asked_words", {}) if isinstance(battle, dict) else {}
    battle_asked = [vocab_key(item) for item in (asked_map.get(recent_key) if isinstance(asked_map.get(recent_key), list) else [])]
    global_asked = shared_world_battle_user_asked_set(recent_key)
    recent_set = set(recent[-20:])
    battle_asked_set = set(item for item in battle_asked if item)
    excluded = global_asked | recent_set | battle_asked_set
    candidates = [row for row in pool if vocab_key(row.get("word", "")) not in excluded]
    if not candidates:
        # The learner has cycled through the whole available pool. Start a fresh cycle,
        # but still avoid words already seen inside the current battle.
        users = load_shared_world_battle_word_history()
        if recent_key in users:
            users[recent_key] = []
            write_shared_world_battle_word_history(users)
        SHARED_WORLD_BATTLE_ACTIVE_ASKED_CACHE[recent_key] = set()
        candidates = [row for row in pool if vocab_key(row.get("word", "")) not in (recent_set | battle_asked_set)]
    if not candidates:
        candidates = pool
    row = secrets.choice(candidates)
    word = clean(row.get("word", ""))
    meaning = clean(row.get("meaning", ""))
    word_type = clean(row.get("type", ""))
    if meaning:
        type_part = f" thuộc loại từ {word_type}" if word_type else ""
        prompt = f"Từ tiếng Anh nào{type_part} có nghĩa là: {meaning}?"
    else:
        hint = f"{word[:1]}{'*' * max(1, len(word) - 1)}"
        type_part = f" Loại từ: {word_type}." if word_type else ""
        prompt = f"Hãy nhập từ vựng tiếng Anh đã học.{type_part} Gợi ý: {hint}"
    question = {
        "owner": normalize_username(username),
        "prompt": prompt,
        "answer": vocab_key(word),
        "answer_text": word,
        "meaning": meaning,
        "type": word_type,
        "created_at": utc_timestamp(),
    }
    if isinstance(battle, dict):
        key = vocab_key(word)
        if key:
            items = [item for item in recent if item and item != key] + [key]
            recent_map[recent_key] = items[-20:]
            battle["recent_words"] = recent_map
            shared_world_battle_mark_asked_word(battle, recent_key, key)
    return question
