def qm_city_training_pick_question(username: str, arena: dict | None = None, preferred_kind: str = "") -> dict:
    pool = qm_city_training_prompt_pool(username)
    asked = [vocab_key(item) for item in ((arena or {}).get("asked") if isinstance((arena or {}).get("asked"), list) else []) if vocab_key(item)]
    asked_set = set(asked[-120:])
    kind = qm_city_training_normalize_question_kind(preferred_kind)
    kind_pool = [row for row in pool if qm_city_training_question_matches_kind(row, kind)]
    if not kind_pool and kind in {"sentence", "read_sentence", "translate_vi", "translate_vi_speech", "audio_sentence", "speak_vi_sentence"}:
        kind_pool = [{
            "kind": "sentence",
            "prompt": "Câu tiếng Anh nào có nghĩa là: tôi là sinh viên?",
            "answer": vocab_key("I am a student."),
            "answer_text": "I am a student.",
            "meaning": "tôi là sinh viên",
            "type": "Space_W sentence",
            "source": "training-fallback",
        }]
    if not kind_pool and kind in {"word", "read_word", "audio_word", "speak_vi_word"}:
        kind_pool = [{
            "kind": "word",
            "prompt": "Từ tiếng Anh nào có nghĩa là: học sinh hoặc sinh viên?",
            "answer": "student",
            "answer_text": "student",
            "meaning": "học sinh; sinh viên",
            "type": "noun",
            "source": "training-fallback",
        }]
    if not kind_pool:
        kind_pool = pool
        kind = ""
    candidates = [row for row in kind_pool if vocab_key(row.get("answer_text", row.get("answer", ""))) not in asked_set]
    if not candidates:
        candidates = kind_pool
        asked = []
    row = qm_city_training_maybe_read_question(dict(secrets.choice(candidates)), kind)
    row["id"] = f"train_q_{int(time.time() * 1000)}_{secrets.token_hex(4)}"
    row["created_at"] = utc_timestamp()
    if isinstance(arena, dict):
        key = vocab_key(row.get("answer_text", row.get("answer", "")))
        if key:
            arena["asked"] = (asked + [key])[-120:]
    return row


def qm_city_training_public_question(question: object) -> dict:
    if not isinstance(question, dict):
        return {}
    return {
        key: value
        for key, value in question.items()
        if key not in {"answer", "answer_text"}
    }

