def qm_city_training_clean_text(value: object, limit: int = 220) -> str:
    return re.sub(r"\s+", " ", clean(value)).strip()[: max(1, int(limit or 220))]


def qm_city_training_sentence_candidates_from_payload(payload: object, limit: int = 80) -> list[dict]:
    rows: list[dict] = []

    def add_pair(vi_value: object, en_value: object, source: str = "") -> None:
        if len(rows) >= limit:
            return
        vi = qm_city_training_clean_text(vi_value, 260)
        en = qm_city_training_clean_text(en_value, 260)
        if not vi or not en or vi == en:
            return
        if not re.search(r"[A-Za-z]", en):
            return
        rows.append(
            {
                "kind": "sentence",
                "prompt": f"Câu tiếng Anh nào có nghĩa là: {vi}",
                "answer": vocab_key(en),
                "answer_text": en,
                "meaning": vi,
                "type": "Space_W sentence",
                "source": source,
            }
        )

    def walk(node: object, source: str = "") -> None:
        if len(rows) >= limit:
            return
        if isinstance(node, dict):
            vi = node.get("q", node.get("vi", node.get("vietnamese", node.get("meaning", node.get("translation", "")))))
            en = node.get("e", node.get("en", node.get("english", node.get("answer", node.get("text", node.get("sentence", ""))))))
            add_pair(vi, en, source)
            for key in ("n", "nodes", "items", "children", "xp", "practice", "training", "train"):
                child = node.get(key)
                if isinstance(child, (list, dict)):
                    walk(child, source)
        elif isinstance(node, list):
            for item in node:
                walk(item, source)
                if len(rows) >= limit:
                    break

    walk(payload)
    deduped = []
    seen = set()
    for row in rows:
        key = vocab_key(row.get("answer_text", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped[:limit]


def qm_city_training_space_w_sentence_pool(username: str, limit: int = 80) -> list[dict]:
    username = normalize_username(username)
    if not username:
        return []
    cache_key = f"spacew:{username}"
    with QM_CITY_TRAINING_PROMPT_CACHE_LOCK:
        cached = QM_CITY_TRAINING_PROMPT_CACHE.get(cache_key)
        if cached and time.time() - cached[0] < 600:
            return cached[1][:limit]
    rows: list[dict] = []
    try:
        index = learning_completion_log_index()
        paths = []
        for rel_path, study in index.items():
            rel_path = clean_path_value(rel_path)
            lower_rel_path = rel_path.lower()
            if not (lower_rel_path.endswith(".space_w") or lower_rel_path.endswith(".space_p")):
                continue
            user_rows = (study.get("users") if isinstance(study.get("users"), dict) else {})
            admin_rows = (study.get("admins") if isinstance(study.get("admins"), dict) else {})
            if username not in user_rows and username not in admin_rows:
                continue
            paths.append((clean(study.get("last", "")), rel_path))
        paths.sort(reverse=True)
        for _, rel_path in paths[:12]:
            if len(rows) >= limit:
                break
            try:
                target = safe_server_data_path(rel_path, username=username, admin=is_admin_user(username))
                target = server_data_effective_file_path(target, username=username, admin=is_admin_user(username))
                payload, _structure_path = load_future_lesson_document(target)
                for item in qm_city_training_sentence_candidates_from_payload(payload, limit=max(1, limit - len(rows))):
                    item["source"] = rel_path
                    rows.append(item)
            except Exception:
                continue
    except Exception:
        rows = []
    with QM_CITY_TRAINING_PROMPT_CACHE_LOCK:
        QM_CITY_TRAINING_PROMPT_CACHE[cache_key] = (time.time(), rows[:limit])
    return rows[:limit]


def qm_city_training_prompt_pool(username: str, limit: int = 220) -> list[dict]:
    username = normalize_username(username)
    if not username:
        return []
    cache_key = f"pool:{username}"
    with QM_CITY_TRAINING_PROMPT_CACHE_LOCK:
        cached = QM_CITY_TRAINING_PROMPT_CACHE.get(cache_key)
        if cached and time.time() - cached[0] < 480:
            return cached[1][:limit]
    rows: list[dict] = []
    try:
        for item in shared_world_battle_vocab_pool(username, limit=180):
            word = qm_city_training_clean_text(item.get("word", ""), 120)
            answer = vocab_key(word)
            if not word or not answer:
                continue
            meaning = qm_city_training_clean_text(item.get("meaning", ""), 240)
            word_type = qm_city_training_clean_text(item.get("type", ""), 80)
            if meaning:
                type_part = f" ({word_type})" if word_type else ""
                prompt = f"Từ tiếng Anh nào{type_part} có nghĩa là: {meaning}?"
            else:
                prompt = f"Nhập từ tiếng Anh đã học. Gợi ý: {word[:1]}{'*' * max(1, len(word) - 1)}"
            rows.append(
                {
                    "kind": "word",
                    "prompt": prompt,
                    "answer": answer,
                    "answer_text": word,
                    "meaning": meaning,
                    "type": word_type,
                }
            )
    except Exception:
        rows = []
    rows.extend(qm_city_training_space_w_sentence_pool(username, limit=80))
    if not rows:
        rows = [
            {"kind": "word", "prompt": "Từ tiếng Anh nào có nghĩa là: học sinh hoặc sinh viên?", "answer": "student", "answer_text": "student", "meaning": "học sinh; sinh viên", "type": "noun"},
            {"kind": "word", "prompt": "Từ tiếng Anh nào có nghĩa là: học hoặc học hỏi?", "answer": "learn", "answer_text": "learn", "meaning": "học; học hỏi", "type": "verb"},
        ]
    secrets.SystemRandom().shuffle(rows)
    rows = rows[: max(1, min(400, int(limit or 220)))]
    with QM_CITY_TRAINING_PROMPT_CACHE_LOCK:
        QM_CITY_TRAINING_PROMPT_CACHE[cache_key] = (time.time(), rows)
    return rows


def qm_city_training_question_is_sentence(question: object) -> bool:
    row = question if isinstance(question, dict) else {}
    kind = clean(row.get("kind", "")).lower()
    type_text = clean(row.get("type", "")).lower()
    answer_text = clean(row.get("answer_text", row.get("read_text", "")))
    return (
        kind in {"sentence", "read_sentence", "translate_vi", "translate_vi_speech", "audio_sentence", "speak_vi_sentence"}
        or "sentence" in type_text
        or "space_w" in type_text
        or "space_p" in type_text
        or "translate to vietnamese" in type_text
        or "vietnamese cue speak sentence" in type_text
        or "audio dictation sentence" in type_text
        or len(re.findall(r"[A-Za-z]+", answer_text)) >= 4
    )


def qm_city_training_question_exp(question: object) -> int:
    return 5 if qm_city_training_question_is_sentence(question) else 1


def qm_city_training_crystal_drop_pool() -> list[dict]:
    return [
        {
            "id": "vocab_crystal_yellow",
            "name": "Golden Axe",
            "use": "Earned when a new vocabulary word is learned cleanly.",
        },
        {
            "id": "vocab_crystal_blue",
            "name": "Silver Axe",
            "use": "Earned when a new word returns after drills and is answered correctly.",
        },
        {
            "id": "vocab_crystal_green",
            "name": "Silver Axe",
            "use": "Earned by correctly recalling vocabulary already stored in learner memory.",
        },
        {
            "id": "paragraph_crystal_golden",
            "name": "Golden Magic Bow",
            "use": "Earned by completing a new Space_P sentence correctly.",
        },
        {
            "id": "crystal",
            "name": "Prism Crystal",
            "use": "Stores learning energy for future item upgrades.",
        },
    ]


def qm_city_training_make_crystal_drops(event_id: str = "") -> list[dict]:
    count = secrets.randbelow(3) + 1
    pool = qm_city_training_crystal_drop_pool()
    drops = []
    for index in range(count):
        item = dict(secrets.choice(pool))
        drops.append({
            "id": f"{clean(event_id) or secrets.token_hex(6)}_drop_{index + 1}",
            "item": item,
            "quantity": 1,
        })
    return drops


def qm_city_training_ipa_for_text(text: object = "") -> str:
    value = qm_city_training_clean_text(text, 320)
    if not value:
        return ""
    try:
        ipa_map = phonetic_ipa_map_for_terms_queued([value], generate_missing=True, schedule_missing=False)
        row = ipa_map.get(phonetic_ipa_key(value), {}) if isinstance(ipa_map, dict) else {}
        return clean(row.get("ipa_uk", "") or row.get("ipa_us", "") or row.get("ipa", ""))
    except Exception:
        return ""


def qm_city_training_normalize_question_kind(value: object = "") -> str:
    kind = clean(value).lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "vocab": "word",
        "vocabulary": "word",
        "write_word": "word",
        "write_sentence": "sentence",
        "speak_word": "read_word",
        "speak_sentence": "read_sentence",
        "speak_passage": "read_sentence",
        "read_passage": "read_sentence",
        "listen": "audio_word",
        "listening": "audio_word",
        "listen_word": "audio_word",
        "listen_sentence": "audio_sentence",
        "dictation": "audio_word",
        "dictation_word": "audio_word",
        "dictation_sentence": "audio_sentence",
        "speak_vi": "speak_vi_sentence",
        "speak_vietnamese": "speak_vi_sentence",
        "speak_from_vi": "speak_vi_sentence",
        "speak_from_vietnamese": "speak_vi_sentence",
        "read_vi_prompt": "speak_vi_sentence",
        "read_vietnamese_prompt": "speak_vi_sentence",
        "translate": "translate_vi",
        "translate_vietnamese": "translate_vi",
        "vietnamese_translation": "translate_vi",
        "translate_to_vietnamese": "translate_vi",
        "speak_translate_vi": "translate_vi_speech",
        "speak_translation_vi": "translate_vi_speech",
        "speak_vietnamese_translation": "translate_vi_speech",
        "spoken_vietnamese_translation": "translate_vi_speech",
        "translate_to_vietnamese_speech": "translate_vi_speech",
    }
    valid = {"word", "sentence", "read_word", "read_sentence", "translate_vi", "translate_vi_speech", "audio_word", "audio_sentence", "speak_vi_word", "speak_vi_sentence"}
    return aliases.get(kind, kind if kind in valid else "")


def qm_city_training_kind_for_slime_index(index: int, randomize_tail: bool = False) -> str:
    safe_index = max(0, int(index or 0))
    fixed = QM_CITY_TRAINING_FIXED_KIND_SEQUENCE
    if safe_index < len(fixed):
        return fixed[safe_index]
    sequence = QM_CITY_TRAINING_RANDOM_KIND_SEQUENCE
    if randomize_tail:
        return secrets.choice(sequence)
    return sequence[(safe_index - len(fixed)) % len(sequence)]


def qm_city_training_kind_is_speech(value: object = "") -> bool:
    return qm_city_training_normalize_question_kind(value) in {"read_word", "read_sentence", "translate_vi_speech", "speak_vi_word", "speak_vi_sentence"}


def qm_city_training_kind_is_audio_input(value: object = "") -> bool:
    return qm_city_training_normalize_question_kind(value) in {"audio_word", "audio_sentence"}


def qm_city_training_kind_is_vi_prompt_speech(value: object = "") -> bool:
    return qm_city_training_normalize_question_kind(value) in {"speak_vi_word", "speak_vi_sentence"}


def qm_city_training_kind_is_server_speech(value: object = "") -> bool:
    return qm_city_training_normalize_question_kind(value) in {"translate_vi_speech"}


def qm_city_training_question_matches_kind(question: object, preferred_kind: str = "") -> bool:
    kind = qm_city_training_normalize_question_kind(preferred_kind)
    if not kind:
        return True
    sentence_like = qm_city_training_question_is_sentence(question)
    if kind in {"sentence", "read_sentence", "translate_vi", "translate_vi_speech", "audio_sentence", "speak_vi_sentence"}:
        if not sentence_like:
            return False
        if kind in {"translate_vi", "translate_vi_speech", "speak_vi_sentence"}:
            row = question if isinstance(question, dict) else {}
            return bool(qm_city_training_clean_text(row.get("meaning", row.get("translation", row.get("vietnamese", ""))), 420))
        return True
    if kind == "speak_vi_word":
        row = question if isinstance(question, dict) else {}
        return (not sentence_like) and bool(qm_city_training_clean_text(row.get("meaning", row.get("translation", row.get("vietnamese", ""))), 420))
    return not sentence_like


def qm_city_training_make_translate_vi_question(question: dict) -> dict:
    row = dict(question) if isinstance(question, dict) else {}
    source_text = qm_city_training_clean_text(row.get("answer_text", row.get("answer", row.get("english", row.get("text", "")))), 520)
    meaning = qm_city_training_clean_text(row.get("meaning", row.get("translation", row.get("vietnamese", ""))), 520)
    if not source_text or not meaning:
        return row
    row["base_kind"] = clean(row.get("kind", "sentence")) or "sentence"
    row["kind"] = "translate_vi"
    row["training_kind"] = "translate_vi"
    row["source_text"] = source_text
    row["sourceText"] = source_text
    row["answer"] = meaning
    row["answer_text"] = meaning
    row["meaning"] = meaning
    row["accept_percent"] = 70
    row["prompt"] = f"Dịch câu này sang tiếng Việt. Chỉ cần đúng khoảng 70% ý chính: {source_text}"
    row["type"] = "Translate to Vietnamese"
    row.pop("local_speech", None)
    row.pop("read_text", None)
    return row


def qm_city_training_make_translate_vi_speech_question(question: dict) -> dict:
    row = dict(question) if isinstance(question, dict) else {}
    source_text = qm_city_training_clean_text(row.get("answer_text", row.get("answer", row.get("english", row.get("text", "")))), 520)
    meaning = qm_city_training_clean_text(row.get("meaning", row.get("translation", row.get("vietnamese", ""))), 520)
    if not source_text or not meaning or not re.search(r"[A-Za-z]", source_text):
        return row
    row["base_kind"] = clean(row.get("kind", "sentence")) or "sentence"
    row["kind"] = "translate_vi_speech"
    row["training_kind"] = "translate_vi_speech"
    row["source_text"] = source_text
    row["sourceText"] = source_text
    row["answer"] = meaning
    row["answer_text"] = meaning
    row["meaning"] = meaning
    row["accept_percent"] = 60
    row["server_speech"] = True
    row["serverSpeech"] = True
    row["speech_language"] = "vi"
    row["speechLanguage"] = "vi"
    row["prompt"] = f"Speak the Vietnamese meaning for this English sentence: {source_text}"
    row["type"] = "Spoken Vietnamese translation"
    row.pop("local_speech", None)
    row.pop("localSpeech", None)
    row.pop("read_text", None)
    row.pop("readText", None)
    row.pop("hide_read_text", None)
    row.pop("hideReadText", None)
    return row


def qm_city_training_make_audio_input_question(question: dict, preferred_kind: str = "") -> dict:
    row = dict(question) if isinstance(question, dict) else {}
    source_text = qm_city_training_clean_text(row.get("answer_text", row.get("answer", row.get("english", row.get("text", "")))), 520)
    if not source_text or not re.search(r"[A-Za-z]", source_text):
        return row
    normalized_kind = qm_city_training_normalize_question_kind(preferred_kind)
    sentence_like = normalized_kind == "audio_sentence" if normalized_kind else qm_city_training_question_is_sentence(row)
    row["base_kind"] = clean(row.get("kind", "sentence" if sentence_like else "word")) or ("sentence" if sentence_like else "word")
    row["kind"] = "audio_sentence" if sentence_like else "audio_word"
    row["training_kind"] = row["kind"]
    row["answer"] = vocab_key(source_text)
    row["answer_text"] = source_text
    row["audio_text"] = source_text
    row["audioText"] = source_text
    row["audio_voice"] = clean(row.get("audio_voice", row.get("audioVoice", ""))) or "sot:en-GB"
    row["audioVoice"] = row["audio_voice"]
    row["prompt"] = "Nghe âm thanh rồi nhập lại câu tiếng Anh." if sentence_like else "Nghe âm thanh rồi nhập lại từ tiếng Anh."
    row["type"] = "Audio dictation sentence" if sentence_like else "Audio dictation word"
    row.pop("local_speech", None)
    row.pop("read_text", None)
    return row


def qm_city_training_make_vi_prompt_speech_question(question: dict, preferred_kind: str = "") -> dict:
    row = dict(question) if isinstance(question, dict) else {}
    source_text = qm_city_training_clean_text(row.get("answer_text", row.get("answer", row.get("english", row.get("text", "")))), 520)
    meaning = qm_city_training_clean_text(row.get("meaning", row.get("translation", row.get("vietnamese", ""))), 520)
    if not source_text or not meaning or not re.search(r"[A-Za-z]", source_text):
        return row
    normalized_kind = qm_city_training_normalize_question_kind(preferred_kind)
    sentence_like = normalized_kind == "speak_vi_sentence" if normalized_kind else qm_city_training_question_is_sentence(row)
    row["base_kind"] = clean(row.get("kind", "sentence" if sentence_like else "word")) or ("sentence" if sentence_like else "word")
    row["kind"] = "speak_vi_sentence" if sentence_like else "speak_vi_word"
    row["training_kind"] = row["kind"]
    row["local_speech"] = True
    row["hide_read_text"] = True
    row["hideReadText"] = True
    row["read_text"] = source_text
    row["answer"] = vocab_key(source_text)
    row["answer_text"] = source_text
    row["meaning"] = meaning
    row["prompt"] = f"Nói tiếng Anh theo nghĩa tiếng Việt này: {meaning}"
    row["type"] = "Vietnamese cue speak sentence" if sentence_like else "Vietnamese cue speak word"
    row["time_limit_seconds"] = 20 if sentence_like else 10
    row["accept_percent"] = 70
    row.pop("ipa", None)
    return row


def qm_city_training_maybe_read_question(question: dict, preferred_kind: str = "") -> dict:
    row = dict(question) if isinstance(question, dict) else {}
    answer_text = qm_city_training_clean_text(row.get("answer_text", row.get("answer", "")), 320)
    if not answer_text or not re.search(r"[A-Za-z]", answer_text):
        return row
    normalized_kind = qm_city_training_normalize_question_kind(preferred_kind)
    if normalized_kind == "translate_vi":
        return qm_city_training_make_translate_vi_question(row)
    if qm_city_training_kind_is_server_speech(normalized_kind):
        result = qm_city_training_make_translate_vi_speech_question(row)
        if qm_city_training_kind_is_server_speech(result.get("training_kind", result.get("kind", ""))):
            return result
        return qm_city_training_make_translate_vi_speech_question({
            "kind": "sentence",
            "answer": vocab_key("I am a student."),
            "answer_text": "I am a student.",
            "meaning": "tôi là sinh viên",
            "type": "training-fallback",
        })
    if qm_city_training_kind_is_audio_input(normalized_kind):
        result = qm_city_training_make_audio_input_question(row, normalized_kind)
        if qm_city_training_kind_is_audio_input(result.get("training_kind", result.get("kind", ""))):
            return result
        fallback_text = "I am a student." if normalized_kind == "audio_sentence" else "student"
        return qm_city_training_make_audio_input_question({
            "kind": "sentence" if normalized_kind == "audio_sentence" else "word",
            "answer": vocab_key(fallback_text),
            "answer_text": fallback_text,
            "meaning": "tôi là sinh viên" if normalized_kind == "audio_sentence" else "học sinh; sinh viên",
            "type": "training-fallback",
        }, normalized_kind)
    if qm_city_training_kind_is_vi_prompt_speech(normalized_kind):
        result = qm_city_training_make_vi_prompt_speech_question(row, normalized_kind)
        if qm_city_training_kind_is_vi_prompt_speech(result.get("training_kind", result.get("kind", ""))):
            return result
        fallback_text = "I am a student." if normalized_kind == "speak_vi_sentence" else "student"
        return qm_city_training_make_vi_prompt_speech_question({
            "kind": "sentence" if normalized_kind == "speak_vi_sentence" else "word",
            "answer": vocab_key(fallback_text),
            "answer_text": fallback_text,
            "meaning": "tôi là sinh viên" if normalized_kind == "speak_vi_sentence" else "học sinh; sinh viên",
            "type": "training-fallback",
        }, normalized_kind)
    if normalized_kind in {"word", "sentence"}:
        row.pop("local_speech", None)
        row.pop("read_text", None)
        row["training_kind"] = normalized_kind
        row["kind"] = "sentence" if normalized_kind == "sentence" else "word"
        if normalized_kind == "sentence":
            row["type"] = clean(row.get("type", "")) or "Sentence writing"
        return row
    force_read = normalized_kind in {"read_word", "read_sentence"}
    if not force_read and secrets.randbelow(100) >= 30:
        row["training_kind"] = clean(row.get("kind", "word")) or "word"
        return row
    sentence_like = normalized_kind == "read_sentence" if force_read else qm_city_training_question_is_sentence(row)
    row["base_kind"] = clean(row.get("kind", "word")) or "word"
    row["kind"] = "read_sentence" if sentence_like else "read_word"
    row["training_kind"] = row["kind"]
    row["local_speech"] = True
    row["read_text"] = answer_text
    row["ipa"] = qm_city_training_ipa_for_text(answer_text)
    row["time_limit_seconds"] = 20 if sentence_like else 10
    row["prompt"] = "Đọc câu tiếng Anh này thật rõ." if sentence_like else "Đọc từ tiếng Anh này thật rõ."
    row["type"] = "Read aloud sentence" if sentence_like else "Read aloud word"
    return row
