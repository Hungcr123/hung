# Loaded by FUTURE.server_parts.04_ai_language_agents into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def phonetic_ipa_key(value: object = "") -> str:
    text = clean(value).replace("’", "'")
    text = re.sub(r"^[^A-Za-z0-9']+|[^A-Za-z0-9']+$", "", text)
    return re.sub(r"\s+", " ", text.lower()).strip()


def phonetic_speakable_text(value: object = "") -> str:
    text = clean(value).replace("’", "'")
    text = re.sub(r"[^A-Za-z0-9'\-\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -'")
    if not re.search(r"[A-Za-z]", text):
        return ""
    return text[:120]


def normalize_phonetic_ipa_entry(source: object = None) -> dict:
    data = source if isinstance(source, dict) else {}
    text = lesson_task_notice_text(data.get("text") or data.get("word") or data.get("surface"), limit=160)
    key = phonetic_ipa_key(data.get("key") or text)
    ipa_us = lesson_task_notice_text(data.get("ipa_us", data.get("ipaUS", "")), limit=240)
    ipa_uk = lesson_task_notice_text(data.get("ipa_uk", data.get("ipaUK", "")), limit=240)
    ipa = lesson_task_notice_text(data.get("ipa") or ipa_uk or ipa_us, limit=240)
    if not key or not (ipa or ipa_us or ipa_uk):
        return {}
    lemma = lesson_task_notice_text(data.get("lemma", ""), limit=160)
    return {
        "key": key,
        "text": text or key,
        "ipa": ipa,
        "ipa_us": ipa_us,
        "ipa_uk": ipa_uk,
        "lemma": lemma,
        "lemma_key": phonetic_ipa_key(data.get("lemma_key") or lemma),
        "source": clean(data.get("source", ""))[:80] or "server_phonetic",
        "updated_at": clean(data.get("updated_at") or utc_timestamp())[:80],
    }


def read_phonetic_ipa_cache() -> dict:
    if not PHONETIC_IPA_CACHE_FILE.is_file():
        return {"version": 1, "items": {}, "updated_at": ""}
    try:
        data = json.loads(PHONETIC_IPA_CACHE_FILE.read_text(encoding="utf-8-sig"))
    except Exception:
        return {"version": 1, "items": {}, "updated_at": ""}
    items = data.get("items", {}) if isinstance(data, dict) else {}
    if not isinstance(items, dict):
        items = {}
    normalized = {}
    for key, value in items.items():
        row = normalize_phonetic_ipa_entry({**(value if isinstance(value, dict) else {}), "key": key})
        if row:
            normalized[row["key"]] = row
    return {
        "version": 1,
        "items": normalized,
        "updated_at": clean(data.get("updated_at", "")) if isinstance(data, dict) else "",
    }


def rebuild_phonetic_ipa_cache(payload: dict, mtime_ns: int | None = None) -> dict:
    source = payload if isinstance(payload, dict) else {"version": 1, "items": {}, "updated_at": ""}
    items = source.get("items", {}) if isinstance(source.get("items"), dict) else {}
    normalized = {}
    for key, value in items.items():
        row = normalize_phonetic_ipa_entry({**(value if isinstance(value, dict) else {}), "key": key})
        if row:
            normalized[row["key"]] = row
    cache_payload = {
        "version": 1,
        "items": normalized,
        "updated_at": clean(source.get("updated_at", "")),
    }
    PHONETIC_IPA_CACHE["mtime_ns"] = int(mtime_ns if mtime_ns is not None else -1)
    PHONETIC_IPA_CACHE["payload"] = cache_payload
    PHONETIC_IPA_CACHE["items"] = normalized
    return PHONETIC_IPA_CACHE


def get_phonetic_ipa_cache() -> dict:
    try:
        mtime_ns = PHONETIC_IPA_CACHE_FILE.stat().st_mtime_ns if PHONETIC_IPA_CACHE_FILE.is_file() else -1
    except Exception:
        mtime_ns = -1
    if int(PHONETIC_IPA_CACHE.get("mtime_ns", -2)) == int(mtime_ns):
        return PHONETIC_IPA_CACHE
    payload = read_phonetic_ipa_cache()
    return rebuild_phonetic_ipa_cache(payload, mtime_ns)


def write_phonetic_ipa_cache(payload: dict) -> None:
    PHONETIC_IPA_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(PHONETIC_IPA_CACHE_FILE, payload, indent=2)
    try:
        mtime_ns = PHONETIC_IPA_CACHE_FILE.stat().st_mtime_ns
    except Exception:
        mtime_ns = -1
    rebuild_phonetic_ipa_cache(payload, mtime_ns)


def save_phonetic_ipa_entries(entries: object = None) -> dict:
    rows = entries if isinstance(entries, (list, tuple)) else [entries]
    normalized = [normalize_phonetic_ipa_entry(row) for row in rows]
    normalized = [row for row in normalized if row]
    if not normalized:
        return {}
    with PHONETIC_IPA_LOCK:
        cache = get_phonetic_ipa_cache()
        items = dict(cache.get("items") or {})
        for row in normalized:
            items[row["key"]] = row
        now = utc_timestamp()
        write_phonetic_ipa_cache({"version": 1, "items": items, "updated_at": now})
        return {row["key"]: row for row in normalized}


def phonetic_dict_exact_ipa(term: object = "") -> dict:
    text = phonetic_speakable_text(term)
    key = phonetic_ipa_key(text)
    if not key:
        return {}
    try:
        vocab_runtime, qmdict = qmdict_runtime_and_dict()
    except Exception:
        return {}
    candidates = []
    try:
        valid_lines = []
        vocab_runtime.is_valid_word(key, qmdict, valid_lines, number="1")
        for line in list(valid_lines or []):
            try:
                item = vocab_runtime.vocab_item_from_valid_line(line)
            except Exception:
                item = None
            summary = pdf_vocab_item_summary(item, surface=text)
            if summary:
                candidates.append(summary)
    except Exception:
        pass
    try:
        for raw in list(vocab_runtime.extract_exact_vocab_words_from_text(text) or []):
            summary = pdf_vocab_phrase_summary(raw)
            if summary:
                candidates.append(summary)
    except Exception:
        pass
    lemma = ""
    for item in candidates:
        word = clean(item.get("word", ""))
        word_key = phonetic_ipa_key(word)
        if word_key and not lemma:
            lemma = word
        if word_key != key:
            continue
        ipa_us = lesson_task_notice_text(item.get("pron_us", ""), limit=240)
        ipa_uk = lesson_task_notice_text(item.get("pron_uk", ""), limit=240)
        ipa = lesson_task_notice_text(item.get("pron", "") or ipa_uk or ipa_us, limit=240)
        if ipa or ipa_us or ipa_uk:
            return {
                "text": text,
                "ipa": ipa,
                "ipa_us": ipa_us,
                "ipa_uk": ipa_uk,
                "lemma": lemma,
                "source": "qmdict",
            }
    return {"lemma": lemma} if lemma else {}


def phonetic_phonemize_text(term: object = "", voice: str = "en-US") -> str:
    text = phonetic_speakable_text(term)
    if not text:
        return ""
    try:
        configure_paths()
        from module_main.Learntheoryapp.LearnTheory_common import (  # noqa: PLC0415
            PHONEMIZER_READY,
            _normalize_ipa_text,
            phonemize,
        )
    except Exception:
        return ""
    if not PHONEMIZER_READY or phonemize is None:
        return ""
    lang = "en-gb" if clean(voice) == "en-GB" else "en-us"
    try:
        ipa = phonemize(
            text,
            language=lang,
            backend="espeak",
            strip=True,
            preserve_punctuation=False,
            with_stress=True,
        )
    except Exception:
        return ""
    try:
        return _normalize_ipa_text(str(ipa or "").strip(), "en-GB" if lang == "en-gb" else "en-US")
    except Exception:
        return clean(ipa)


def build_phonetic_ipa_entry(term: object = "") -> dict:
    text = phonetic_speakable_text(term)
    key = phonetic_ipa_key(text)
    if not key:
        return {}
    dict_entry = phonetic_dict_exact_ipa(text)
    ipa_us = clean(dict_entry.get("ipa_us", ""))
    ipa_uk = clean(dict_entry.get("ipa_uk", ""))
    ipa = clean(dict_entry.get("ipa", ""))
    source = clean(dict_entry.get("source", ""))
    if not ipa_us:
        ipa_us = phonetic_phonemize_text(text, "en-US")
        if ipa_us and not source:
            source = "server_phonetic"
    if not ipa_uk:
        ipa_uk = phonetic_phonemize_text(text, "en-GB")
        if ipa_uk and not source:
            source = "server_phonetic"
    if not ipa:
        ipa = ipa_uk or ipa_us
    lemma = clean(dict_entry.get("lemma", ""))
    if not (ipa or ipa_us or ipa_uk) and lemma and phonetic_ipa_key(lemma) != key:
        with PHONETIC_IPA_LOCK:
            lemma_cached = (get_phonetic_ipa_cache().get("items") or {}).get(phonetic_ipa_key(lemma), {})
        ipa = clean(lemma_cached.get("ipa", ""))
        ipa_us = clean(lemma_cached.get("ipa_us", ""))
        ipa_uk = clean(lemma_cached.get("ipa_uk", ""))
        if ipa or ipa_us or ipa_uk:
            source = "lemma_cache"
    return normalize_phonetic_ipa_entry({
        "key": key,
        "text": text,
        "ipa": ipa,
        "ipa_us": ipa_us,
        "ipa_uk": ipa_uk,
        "lemma": lemma,
        "source": source or "server_phonetic",
        "updated_at": utc_timestamp(),
    })


def get_or_create_phonetic_ipa(term: object = "", generate: bool = True) -> dict:
    key = phonetic_ipa_key(term)
    if not key:
        return {}
    with PHONETIC_IPA_LOCK:
        cached = (get_phonetic_ipa_cache().get("items") or {}).get(key)
        if isinstance(cached, dict) and cached:
            return cached
    if not generate:
        return {}
    entry = build_phonetic_ipa_entry(term)
    if entry:
        save_phonetic_ipa_entries(entry)
    return entry


# Added 2026-07-01: isolates qmdict-backed IPA generation in a dedicated phonetic worker.
def get_or_create_phonetic_ipa_queued(term: object = "", generate: bool = True) -> dict:
    key = phonetic_ipa_key(term)
    if not key:
        return {}
    with PHONETIC_IPA_LOCK:
        cached = (get_phonetic_ipa_cache().get("items") or {}).get(key)
        if isinstance(cached, dict) and cached:
            return cached
    if not generate:
        return {}
    from FUTURE.server_parts.worker_jobs.heavy_language_jobs import phonetic_ipa_entry_worker

    entry = PHONETIC_WORK_QUEUE.run(
        f"ipa:{key[:60]}",
        phonetic_ipa_entry_worker,
        term,
        bool(generate),
        timeout=PHONETIC_WORK_QUEUE.timeout_seconds,
    )
    if isinstance(entry, dict) and entry:
        save_phonetic_ipa_entries(entry)
        return entry
    return {}


def warm_phonetic_ipa_terms_async(terms: object = None, limit: int = 80) -> None:
    raw_terms = terms if isinstance(terms, (list, tuple, set)) else [terms]
    todo: list[tuple[str, str]] = []
    with PHONETIC_IPA_LOCK:
        cached = get_phonetic_ipa_cache().get("items") or {}
        for term in raw_terms:
            text = phonetic_speakable_text(term)
            key = phonetic_ipa_key(text)
            if not key or key in cached or key in PHONETIC_IPA_WARMING_KEYS:
                continue
            PHONETIC_IPA_WARMING_KEYS.add(key)
            todo.append((key, text))
            if len(todo) >= max(1, int(limit or 80)):
                break
    if not todo:
        return

    def worker(items: list[tuple[str, str]]) -> None:
        made = []
        try:
            for _key, text in items:
                entry = build_phonetic_ipa_entry(text)
                if entry:
                    made.append(entry)
            if made:
                save_phonetic_ipa_entries(made)
        finally:
            with PHONETIC_IPA_LOCK:
                for key, _text in items:
                    PHONETIC_IPA_WARMING_KEYS.discard(key)

    threading.Thread(target=worker, args=(todo,), daemon=True, name="future-phonetic-ipa-warm").start()


def phonetic_ipa_map_for_terms(terms: object = None, generate_missing: bool = False, schedule_missing: bool = False) -> dict:
    raw_terms = terms if isinstance(terms, (list, tuple, set)) else [terms]
    ordered: list[str] = []
    seen: set[str] = set()
    for term in raw_terms:
        text = phonetic_speakable_text(term)
        key = phonetic_ipa_key(text)
        if key and key not in seen:
            seen.add(key)
            ordered.append(text)
    if not ordered:
        return {}
    out: dict[str, dict] = {}
    missing = []
    with PHONETIC_IPA_LOCK:
        cached = get_phonetic_ipa_cache().get("items") or {}
        for text in ordered:
            key = phonetic_ipa_key(text)
            row = cached.get(key)
            if isinstance(row, dict) and row:
                out[key] = row
            else:
                missing.append(text)
    if generate_missing:
        made = []
        for text in missing[:160]:
            row = build_phonetic_ipa_entry(text)
            if row:
                out[row["key"]] = row
                made.append(row)
        if made:
            save_phonetic_ipa_entries(made)
    elif schedule_missing and missing:
        warm_phonetic_ipa_terms_async(missing, limit=80)
    return out


# Added 2026-07-01: keeps batch phonetic generation off the main request process.
def phonetic_ipa_map_for_terms_queued(terms: object = None, generate_missing: bool = False, schedule_missing: bool = False) -> dict:
    raw_terms = terms if isinstance(terms, (list, tuple, set)) else [terms]
    ordered: list[str] = []
    seen: set[str] = set()
    for term in raw_terms:
        text = phonetic_speakable_text(term)
        key = phonetic_ipa_key(text)
        if key and key not in seen:
            seen.add(key)
            ordered.append(text)
    if not ordered:
        return {}
    out: dict[str, dict] = {}
    missing = []
    with PHONETIC_IPA_LOCK:
        cached = get_phonetic_ipa_cache().get("items") or {}
        for text in ordered:
            key = phonetic_ipa_key(text)
            row = cached.get(key)
            if isinstance(row, dict) and row:
                out[key] = row
            else:
                missing.append(text)
    if not missing:
        return out
    if not generate_missing:
        if schedule_missing:
            warm_phonetic_ipa_terms_async(missing, limit=80)
        return out
    from FUTURE.server_parts.worker_jobs.heavy_language_jobs import phonetic_ipa_map_worker

    made = PHONETIC_WORK_QUEUE.run(
        f"ipa-map:{len(missing)}",
        phonetic_ipa_map_worker,
        missing[:160],
        True,
        False,
        timeout=PHONETIC_WORK_QUEUE.timeout_seconds,
    )
    if isinstance(made, dict):
        entries = [row for row in made.values() if isinstance(row, dict) and row]
        if entries:
            save_phonetic_ipa_entries(entries)
        out.update(made)
    return out
