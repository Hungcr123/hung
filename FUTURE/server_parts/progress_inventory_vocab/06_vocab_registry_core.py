# Loaded by FUTURE.server_parts.08_progress_inventory_vocab into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def safe_name_segment(value: str, fallback: str = "Mission", limit: int = 54) -> str:
    text = clean(value) or fallback
    text = re.sub(r'[<>:"/\\|?*\x00-\x1F]+', " ", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    text = text[: max(8, int(limit or 54))].strip(" .")
    return text or fallback


def vocab_key(value: str) -> str:
    return re.sub(r"\s+", " ", clean(value).lower()).strip()


def user_vocab_registry_path(username: str) -> Path:
    ensure_server_data_folders(username)
    return server_data_user_folder_path(username) / VOCAB_REGISTRY_FILE


def read_user_vocab_registry(username: str) -> dict:
    database_loader = globals().get("server_database_load_vocab_registry")
    if callable(database_loader):
        database_payload = database_loader(username)
        if isinstance(database_payload, dict):
            return database_payload
    return {"version": 1, "updated_at": "", "words": {}}


def write_user_vocab_registry(username: str, registry: dict) -> None:
    words = registry.get("words") if isinstance(registry.get("words"), dict) else {}
    payload = {
        **({key: value for key, value in registry.items() if key != "words"} if isinstance(registry, dict) else {}),
        "version": max(1, space_w_int(registry.get("version", 1), 1)) if isinstance(registry, dict) else 1,
        "updated_at": utc_timestamp(),
        "words": words,
    }
    database_replace = globals().get("server_database_replace_vocab_registry")
    if callable(database_replace):
        database_replace(username, payload)
    else:
        raise RuntimeError("Vocabulary PostgreSQL writer is unavailable; JSON fallback is disabled.")
    try:
        cache = globals().get("USER_VOCAB_REGISTRY_SNAPSHOT_CACHE")
        if isinstance(cache, dict):
            cache.pop(normalize_username(username).lower(), None)
        lesson_index_cache = globals().get("VOCAB_LESSON_INDEX_RAM_CACHE")
        if isinstance(lesson_index_cache, dict):
            lesson_index_cache["built_at"] = 0.0
    except Exception:
        pass


def normalize_vocabulary_registry_item(item: object) -> dict:
    count = 0
    last = ""
    if isinstance(item, (list, tuple)):
        word = clean(item[0] if len(item) > 0 else "")
        meaning = clean(item[1] if len(item) > 1 else "")
        pron = clean(item[2] if len(item) > 2 else "")
        word_type = clean(item[3] if len(item) > 3 else "")
    else:
        data = item if isinstance(item, dict) else {}
        word = clean(data.get("w") or data.get("word") or data.get("en") or data.get("e") or "")
        meaning = clean(data.get("m") or data.get("meaning") or data.get("vi") or data.get("q") or "")
        pron = clean(data.get("p") or data.get("pron") or data.get("ipa") or data.get("i") or "")
        word_type = clean(data.get("ty") or data.get("type") or data.get("pos") or "")
        count = max(0, space_w_int(data.get("count", data.get("c", 0)), 0))
        last = main_vocab_time_text(data.get("last", data.get("updated_at", ""))) if clean(data.get("last", data.get("updated_at", ""))) else ""
    if not word:
        return {}
    return {
        "word": word,
        "meaning": meaning,
        "pron": pron,
        "type": word_type,
        "count": count,
        "last": last,
    }


def qmdict_registry_summary_from_row(key: object = "", row: object = None) -> dict:
    if isinstance(row, dict):
        summary = pdf_vocab_item_summary(row)
    elif isinstance(row, (list, tuple)):
        values = list(row)
        while len(values) < 8:
            values.append("")
        summary = {
            "word": clean(values[0]) or clean(key),
            "meaning": clean(values[1]),
            "pron": clean(values[2]),
            "type": clean(values[3]),
            "pron_us": clean(values[4]),
            "pron_uk": clean(values[5]),
            "usage": clean(values[6]),
            "examples": word_agent_clean_examples(values[7]),
        }
    else:
        summary = {}
    if not clean(summary.get("word", "")) and clean(key):
        summary["word"] = clean(key).title()
    return summary if clean(summary.get("word", "")) else {}


def qmdict_registry_summary_maps() -> dict[str, dict]:
    signature_key = qmdict_source_signature_key()
    with QMDICT_SUMMARY_MAP_CACHE_LOCK:
        cached_signature = QMDICT_SUMMARY_MAP_CACHE.get("signature")
        cached_maps = QMDICT_SUMMARY_MAP_CACHE.get("maps")
        if cached_signature == signature_key and isinstance(cached_maps, dict) and cached_maps:
            return cached_maps
    # Added 2026-07-31: persist the derived QmDict lookup map and rebuild it
    # only when the source file signature changes. Audio availability is kept
    # separate and is never embedded in this catalog.
    index_file = Path(SERVER_DATA_ROOT) / "_future_qmdict_summary_index.json"
    try:
        cached_payload = json.loads(index_file.read_text(encoding="utf-8-sig", errors="replace"))
        cached_file_signature = tuple(cached_payload.get("signature") or [])
        cached_file_maps = cached_payload.get("maps")
        if cached_file_signature == signature_key and isinstance(cached_file_maps, dict) and cached_file_maps:
            with QMDICT_SUMMARY_MAP_CACHE_LOCK:
                QMDICT_SUMMARY_MAP_CACHE.update({"signature": signature_key, "maps": cached_file_maps, "built_at": time.time()})
            return cached_file_maps
    except Exception:
        pass
    try:
        _runtime, qmdict = qmdict_runtime_and_dict()
    except Exception:
        qmdict = {}
    if not isinstance(qmdict, dict) or not qmdict:
        return {}
    maps: dict[str, dict] = {}
    for raw_key, row in qmdict.items():
        summary = qmdict_registry_summary_from_row(raw_key, row)
        if not summary:
            continue
        for candidate in (raw_key, summary.get("word", "")):
            key = vocab_key(candidate)
            if key and key not in maps:
                maps[key] = summary
    with QMDICT_SUMMARY_MAP_CACHE_LOCK:
        QMDICT_SUMMARY_MAP_CACHE.update({"signature": signature_key, "maps": maps, "built_at": time.time()})
    try:
        atomic_write_json(index_file, {"version": 1, "signature": list(signature_key), "maps": maps}, indent=None)
    except Exception as exc:
        stt_debug_log("qmdict_summary_index_persist_failed", error=str(exc))
    return maps


def reconcile_vocab_registry_with_qmdict(registry: dict) -> tuple[dict, dict]:
    words = registry.get("words") if isinstance(registry.get("words"), dict) else {}
    if not words:
        return registry, {"updated": 0, "removed": 0, "total_words": 0}
    qmdict_maps = qmdict_registry_summary_maps()
    if not qmdict_maps:
        return registry, {"updated": 0, "removed": 0, "total_words": len(words), "error": "QmDict unavailable"}
    next_words: dict[str, dict] = {}
    updated = 0
    removed = 0
    for raw_key, raw_item in words.items():
        if not isinstance(raw_item, dict):
            removed += 1
            continue
        item = normalize_vocabulary_registry_item(raw_item)
        lookup_key = vocab_key(item.get("word", "")) or vocab_key(raw_key)
        current = qmdict_maps.get(lookup_key)
        if not current:
            keep_key = lookup_key or vocab_key(raw_key)
            if keep_key:
                kept = dict(raw_item)
                kept["word"] = clean(kept.get("word", "")) or clean(item.get("word", "")) or clean(raw_key)
                kept["count"] = max(1, space_w_int(kept.get("count", item.get("count", 0)), 0))
                kept["last"] = clean(kept.get("last", item.get("last", ""))) or utc_timestamp()
                kept["qmdict_missing"] = True
                next_words[keep_key] = kept
            else:
                removed += 1
            continue
        next_key = vocab_key(current.get("word", "")) or lookup_key
        if not next_key:
            removed += 1
            continue
        previous = next_words.get(next_key) if isinstance(next_words.get(next_key), dict) else {}
        previous_sources = previous.get("sources") if isinstance(previous.get("sources"), list) else []
        item_sources = raw_item.get("sources") if isinstance(raw_item.get("sources"), list) else []
        sources = []
        for source in [*previous_sources, *item_sources]:
            source_text = clean(source)
            if source_text and source_text not in sources:
                sources.append(source_text)
        previous_count = max(0, space_w_int(previous.get("count", 0), 0))
        item_count = max(0, space_w_int(raw_item.get("count", item.get("count", 0)), 0))
        merged = {
            **previous,
            "word": clean(current.get("word", "")),
            "meaning": clean(current.get("meaning", "")),
            "pron": clean(current.get("pron", "")),
            "type": clean(current.get("type", "")),
            "count": max(previous_count, item_count, 1),
            "first": clean(previous.get("first", "")) or clean(raw_item.get("first", "")),
            "last": timestamp_latest_text(previous.get("last", ""), raw_item.get("last", item.get("last", ""))) or utc_timestamp(),
            "sources": sources[-40:],
        }
        next_words[next_key] = merged
        if next_key != vocab_key(raw_key):
            updated += 1
        else:
            for field in ("word", "meaning", "pron", "type"):
                if clean(raw_item.get(field, "")) != clean(merged.get(field, "")):
                    updated += 1
                    break
    changed = updated or removed or len(next_words) != len(words)
    next_registry = {**registry, "words": next_words}
    return next_registry, {"updated": updated, "removed": removed, "changed": bool(changed), "total_words": len(next_words)}


def reconcile_user_vocab_registry_with_qmdict(username: str, write: bool = True) -> dict:
    username = normalize_username(username)
    if not username:
        return {"updated": 0, "removed": 0, "total_words": 0}
    signature_key = qmdict_source_signature_key()
    with VOCAB_REGISTRY_LOCK:
        registry = read_user_vocab_registry(username)
        words = registry.get("words") if isinstance(registry.get("words"), dict) else {}
        signature_cache = globals().setdefault("USER_VOCAB_QMDICT_SIGNATURE_CACHE", {})
        cache_key = username.lower()
        if words and (
            clean(registry.get("qmdict_signature", "")) == clean(signature_key)
            or clean(signature_cache.get(cache_key, "")) == clean(signature_key)
        ):
            return {
                "updated": 0,
                "removed": 0,
                "changed": False,
                "total_words": len(words),
                "signature_hit": True,
            }
        next_registry, result = reconcile_vocab_registry_with_qmdict(registry)
        next_registry["qmdict_signature"] = clean(signature_key)
        next_registry["qmdict_reconciled_at"] = utc_timestamp()
        if write and (result.get("changed") or clean(registry.get("qmdict_signature", "")) != clean(signature_key)):
            write_user_vocab_registry(username, next_registry)
        if isinstance(signature_cache, dict):
            signature_cache[cache_key] = clean(signature_key)
        if write and (result.get("changed") or clean(registry.get("qmdict_signature", "")) != clean(signature_key)):
            stt_debug_log(
                "user_vocab_registry_qmdict_reconciled",
                user=username,
                updated=result.get("updated", 0),
                removed=result.get("removed", 0),
                total=result.get("total_words", 0),
            )
    return result


def vocabulary_words_from_payload(payload: dict) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    if payload.get("k") == "ftv":
        raw_words = payload.get("w")
    elif payload.get("kind") == "future_vocabulary_payload":
        raw_words = payload.get("words")
    else:
        raw_words = []
    result = []
    seen = set()
    for item in raw_words if isinstance(raw_words, list) else []:
        normalized = normalize_vocabulary_registry_item(item)
        key = vocab_key(normalized.get("word", ""))
        if key and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result


# Added 2026-07-03: estimates vocabulary stats for non-Space_V lesson files in Lesson Vault chips.
VOCAB_STATS_SUPPORTED_EXTENSIONS = {".space_v", ".space_b", ".space_w", ".space_q", ".space_p", ".space_s", ".space_l"}
VOCAB_STATS_TEXT_KEYS = {
    "en", "english", "word", "words", "sentence", "sentences", "text", "question", "answer",
    "answers", "accepted", "accepted_answers", "correct", "correct_answer", "wrong", "wrongs",
    "choice", "choices", "option", "options", "tokens", "select_targets", "prompt", "target",
    "source", "line", "lines", "content", "title", "root", "root_text", "roottext", "caption",
    "picture_caption", "audio_text", "explain", "explanation", "explanation_text", "solution",
    "info", "info_text", "note", "card", "hint", "guide", "guidance", "instruction",
    "instructions", "description", "feedback", "main", "subtitle", "body", "definition", "translation",
    "english", "text_value",
}
VOCAB_STATS_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by", "can", "could",
    "did", "do", "does", "for", "from", "had", "has", "have", "he", "her", "his", "i", "if",
    "in", "into", "is", "it", "its", "me", "my", "not", "of", "on", "or", "our", "she",
    "should", "that", "the", "their", "them", "there", "they", "this", "to", "was", "we",
    "were", "will", "with", "you", "your",
}
VOCAB_STATS_SPACE_LABELS = {
    ".space_v": "Space_V",
    ".space_b": "Space_V",
    ".space_w": "Space_W",
    ".space_q": "Space_Q",
    ".space_p": "Space_P",
    ".space_s": "Space_S",
    ".space_l": "Space_L",
}
VOCAB_LESSON_INDEX_RAM_CACHE: dict[str, object] = {"signature": "", "built_at": 0.0, "files": []}
VOCAB_LESSON_INDEX_RAM_TTL_SECONDS = 180.0
VOCAB_FILE_META_RAM_CACHE: dict[str, dict] = {}
VOCAB_FILE_META_RAM_CACHE_LIMIT = 6000
VOCAB_FILE_META_INDEX_VERSION = 2
VOCAB_FILE_META_EXTRACTOR_VERSION = "spaceq-all-text-v2"
VOCAB_FILE_META_INDEX_PATH = RUNTIME_ROOT / "vocab_file_meta_index_v1.json"
VOCAB_FILE_META_INDEX_LOCK = threading.RLock()
VOCAB_FILE_META_INDEX_STATE: dict[str, object] = {
    "loaded": False,
    "rows": {},
    "lessons": {},
    "revision": 0,
    "first_dirty_at": 0.0,
    "timer": None,
}
VOCAB_LESSON_INDEX_WARM_LOCK = threading.Lock()
VOCAB_LESSON_INDEX_WARM_THREAD = None


# Added 2026-07-30: persist file word keys separately from the structural tree so restarts do not cold-decode unchanged lessons.
def load_vocab_file_meta_index_once() -> dict[str, dict]:
    with VOCAB_FILE_META_INDEX_LOCK:
        if VOCAB_FILE_META_INDEX_STATE.get("loaded"):
            rows = VOCAB_FILE_META_INDEX_STATE.get("rows")
            return rows if isinstance(rows, dict) else {}
        rows: dict[str, dict] = {}
        try:
            source = json.loads(VOCAB_FILE_META_INDEX_PATH.read_text(encoding="utf-8")) if VOCAB_FILE_META_INDEX_PATH.is_file() else {}
            dictionary = source.get("dictionary") if isinstance(source, dict) and isinstance(source.get("dictionary"), list) else []
            files = source.get("files") if isinstance(source, dict) and isinstance(source.get("files"), dict) else {}
            for path_key, record in files.items():
                if not isinstance(record, dict):
                    continue
                keys = []
                for index in record.get("keys") or []:
                    try:
                        word_key = clean(dictionary[int(index)])
                    except Exception:
                        word_key = ""
                    if word_key:
                        keys.append(word_key)
                valid_keys = []
                for index in record.get("valid_keys") or []:
                    try:
                        word_key = clean(dictionary[int(index)])
                    except Exception:
                        word_key = ""
                    if word_key:
                        valid_keys.append(word_key)
                rows[clean_path_value(path_key).lower()] = {
                    "mtime_ns": int(record.get("mtime_ns", 0) or 0),
                    "size": int(record.get("size", -1) or -1),
                    "lesson_id": clean(record.get("lesson_id", ""))[:240],
                    "vocab_word_keys": keys,
                    "vocab_valid_word_keys": valid_keys,
                    "vocab_validated_signature": clean(record.get("vocab_validated_signature", "")),
                    "vocab_extractor_version": clean(record.get("vocab_extractor_version", "")),
                    "vocab_source_revision": clean(record.get("vocab_source_revision", "")),
                    "vocab_source_title": clean(record.get("vocab_source_title", "")),
                    "vocab_total_words": max(0, int(record.get("vocab_total_words", len(keys)) or len(keys))),
                    "vocab_space": clean(record.get("vocab_space", "")),
                }
            lessons = source.get("lessons") if isinstance(source, dict) and isinstance(source.get("lessons"), dict) else {}
            lesson_rows = {}
            for lesson_id, record in lessons.items():
                if not isinstance(record, dict) or not clean(lesson_id):
                    continue
                raw_keys = []
                valid_keys = []
                for field, destination in (("keys", raw_keys), ("valid_keys", valid_keys)):
                    for index in record.get(field) or []:
                        try:
                            word_key = clean(dictionary[int(index)])
                        except Exception:
                            word_key = ""
                        if word_key:
                            destination.append(word_key)
                lesson_rows[clean(lesson_id)] = {
                    "lesson_id": clean(lesson_id),
                    "path": clean_path_value(record.get("path", "")),
                    "mtime_ns": int(record.get("mtime_ns", 0) or 0),
                    "size": int(record.get("size", -1) or -1),
                    "vocab_word_keys": raw_keys,
                    "vocab_valid_word_keys": valid_keys,
                    "vocab_validated_signature": clean(record.get("vocab_validated_signature", "")),
                    "vocab_extractor_version": clean(record.get("vocab_extractor_version", "")),
                    "vocab_source_revision": clean(record.get("vocab_source_revision", "")),
                }
        except Exception:
            rows = {}
            lesson_rows = {}
        VOCAB_FILE_META_INDEX_STATE["rows"] = rows
        VOCAB_FILE_META_INDEX_STATE["lessons"] = lesson_rows
        VOCAB_FILE_META_INDEX_STATE["loaded"] = True
        return rows


def lesson_vocab_meta_for_id(lesson_id: object = "") -> dict:
    normalized = clean(lesson_id)
    if not normalized:
        return {}
    load_vocab_file_meta_index_once()
    with VOCAB_FILE_META_INDEX_LOCK:
        lessons = VOCAB_FILE_META_INDEX_STATE.get("lessons")
        record = lessons.get(normalized) if isinstance(lessons, dict) else None
        return dict(record) if isinstance(record, dict) else {}


def remember_vocab_lesson_meta(record: dict, path_key: str = "") -> None:
    lesson_id = clean(record.get("lesson_id", "")) if isinstance(record, dict) else ""
    if not lesson_id:
        return
    with VOCAB_FILE_META_INDEX_LOCK:
        lessons = VOCAB_FILE_META_INDEX_STATE.setdefault("lessons", {})
        if isinstance(lessons, dict):
            lessons[lesson_id] = {
                "lesson_id": lesson_id,
                "path": clean_path_value(path_key),
                "mtime_ns": int(record.get("mtime_ns", 0) or 0),
                "size": int(record.get("size", -1) or -1),
                "vocab_word_keys": list(record.get("vocab_word_keys") or []),
                "vocab_valid_word_keys": list(record.get("vocab_valid_word_keys") or []),
                "vocab_validated_signature": clean(record.get("vocab_validated_signature", "")),
                "vocab_extractor_version": clean(record.get("vocab_extractor_version", "")),
                "vocab_source_revision": clean(record.get("vocab_source_revision", "")),
            }


def lesson_vocab_meta_is_current(record: object, stat_result=None) -> bool:
    if not isinstance(record, dict):
        return False
    signature = qmdict_source_signature_key()
    signature_text = f"{int(signature[0])}:{int(signature[1])}"
    source_revision = f"{int(stat_result.st_mtime_ns)}:{int(stat_result.st_size)}" if stat_result is not None else ""
    return (
        (stat_result is None or clean(record.get("vocab_source_revision", "")) == source_revision)
        and clean(record.get("vocab_validated_signature", "")) == signature_text
        and clean(record.get("vocab_extractor_version", "")) == VOCAB_FILE_META_EXTRACTOR_VERSION
    )


def lesson_file_vocab_meta_cached_for_target(target: Path) -> dict:
    try:
        path = Path(target)
        stat = path.stat()
        relative_key = clean_path_value(server_data_relative(path)).lower()
        record = load_vocab_file_meta_index_once().get(relative_key) if relative_key else None
        if not lesson_vocab_meta_is_current(record, stat):
            return {}
        result = dict(record)
        result["vocab_source_revision"] = f"{int(stat.st_mtime_ns)}:{int(stat.st_size)}"
        return result
    except Exception:
        return {}


# Added 2026-08-01: repairs one stale lesson in the background without blocking Question Card entry.
def schedule_lesson_vocab_meta_repair(target: Path, lesson_id: object = "") -> dict:
    path = Path(target)
    repair_key = clean(lesson_id) or str(path.resolve()).lower()
    lock = globals().setdefault("VOCAB_LESSON_REPAIR_LOCK", threading.RLock())
    jobs = globals().setdefault("VOCAB_LESSON_REPAIR_JOBS", {})
    with lock:
        current = jobs.get(repair_key) if isinstance(jobs, dict) else None
        if isinstance(current, dict) and current.get("running"):
            return {"scheduled": False, "single_flight": True, "repair_key": repair_key}
        if isinstance(jobs, dict):
            jobs[repair_key] = {"running": True, "started_at": time.time(), "path": str(path)}

    def runner() -> None:
        try:
            lesson_file_vocab_meta_for_target(path)
        finally:
            with lock:
                if isinstance(jobs, dict):
                    jobs.pop(repair_key, None)

    threading.Thread(target=runner, daemon=True, name=f"lesson-vocab-repair-{hashlib.sha1(repair_key.encode('utf-8', 'replace')).hexdigest()[:10]}").start()
    return {"scheduled": True, "single_flight": False, "repair_key": repair_key}


# Added 2026-07-30: coalesced writer persists the compact derived index off the request path.
def write_vocab_file_meta_index_snapshot(expected_revision: int) -> None:
    with VOCAB_FILE_META_INDEX_LOCK:
        rows = dict(VOCAB_FILE_META_INDEX_STATE.get("rows") or {})
        VOCAB_FILE_META_INDEX_STATE["timer"] = None
        VOCAB_FILE_META_INDEX_STATE["first_dirty_at"] = 0.0
    dictionary: list[str] = []
    dictionary_index: dict[str, int] = {}
    files = {}
    lessons = {}
    for path_key, record in rows.items():
        indexes = []
        for word_key in record.get("vocab_word_keys") or []:
            word_key = clean(word_key)
            if not word_key:
                continue
            index = dictionary_index.get(word_key)
            if index is None:
                index = len(dictionary)
                dictionary_index[word_key] = index
                dictionary.append(word_key)
            indexes.append(index)
        valid_indexes = []
        for word_key in record.get("vocab_valid_word_keys") or []:
            word_key = clean(word_key)
            if not word_key:
                continue
            index = dictionary_index.get(word_key)
            if index is None:
                index = len(dictionary)
                dictionary_index[word_key] = index
                dictionary.append(word_key)
            valid_indexes.append(index)
        files[path_key] = {
            "mtime_ns": int(record.get("mtime_ns", 0) or 0),
            "size": int(record.get("size", -1) or -1),
            "lesson_id": clean(record.get("lesson_id", ""))[:240],
            "keys": indexes,
            "valid_keys": valid_indexes,
            "vocab_validated_signature": clean(record.get("vocab_validated_signature", "")),
            "vocab_extractor_version": clean(record.get("vocab_extractor_version", "")),
            "vocab_source_revision": clean(record.get("vocab_source_revision", "")),
            "vocab_source_title": clean(record.get("vocab_source_title", "")),
            "vocab_total_words": max(0, int(record.get("vocab_total_words", len(indexes)) or len(indexes))),
            "vocab_space": clean(record.get("vocab_space", "")),
        }
        lesson_id = clean(record.get("lesson_id", ""))
        if lesson_id:
            lessons[lesson_id] = {
                "path": path_key,
                "mtime_ns": int(record.get("mtime_ns", 0) or 0),
                "size": int(record.get("size", -1) or -1),
                "keys": indexes,
                "valid_keys": valid_indexes,
                "vocab_validated_signature": clean(record.get("vocab_validated_signature", "")),
                "vocab_extractor_version": clean(record.get("vocab_extractor_version", "")),
                "vocab_source_revision": clean(record.get("vocab_source_revision", "")),
            }
    try:
        VOCAB_FILE_META_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        index_payload = {
            "version": VOCAB_FILE_META_INDEX_VERSION,
            "extractor_version": VOCAB_FILE_META_EXTRACTOR_VERSION,
            "dictionary": dictionary,
            "files": files,
            "lessons": lessons,
        }
        atomic_write_text(
            VOCAB_FILE_META_INDEX_PATH,
            json.dumps(index_payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
            sync_database=False,
        )
    finally:
        with VOCAB_FILE_META_INDEX_LOCK:
            if int(VOCAB_FILE_META_INDEX_STATE.get("revision", 0) or 0) != expected_revision:
                schedule_vocab_file_meta_index_write()


# Added 2026-07-30: one bounded timer batches changed lesson metadata without a thread per file/user.
def schedule_vocab_file_meta_index_write() -> None:
    with VOCAB_FILE_META_INDEX_LOCK:
        now = time.monotonic()
        first_dirty_at = float(VOCAB_FILE_META_INDEX_STATE.get("first_dirty_at", 0.0) or 0.0)
        if first_dirty_at <= 0:
            first_dirty_at = now
            VOCAB_FILE_META_INDEX_STATE["first_dirty_at"] = now
        timer = VOCAB_FILE_META_INDEX_STATE.get("timer")
        if hasattr(timer, "cancel"):
            timer.cancel()
        revision = int(VOCAB_FILE_META_INDEX_STATE.get("revision", 0) or 0)
        delay = max(0.05, min(1.0, first_dirty_at + 2.0 - now))
        timer = threading.Timer(delay, write_vocab_file_meta_index_snapshot, args=(revision,))
        timer.daemon = True
        VOCAB_FILE_META_INDEX_STATE["timer"] = timer
        timer.start()


def vocabulary_text_words_from_payload(payload: object, limit: int = 0) -> list[dict]:
    result: list[dict] = []
    seen: set[str] = set()

    def limit_reached() -> bool:
        return limit > 0 and len(result) >= limit

    def add_text(value: object) -> None:
        if limit_reached():
            return
        text = clean(value)
        if not text:
            return
        for match in re.finditer(r"[A-Za-z][A-Za-z'’-]{1,}", text):
            word = clean(match.group(0).replace("’", "'")).strip("'’-")
            key = vocab_key(word)
            if not key or key in seen or key in VOCAB_STATS_STOP_WORDS or len(key) < 2:
                continue
            seen.add(key)
            result.append({"word": word, "meaning": "", "pron": "", "type": ""})
            if limit_reached():
                break

    def walk(node: object, parent_key: str = "") -> None:
        if limit_reached():
            return
        if isinstance(node, str):
            if parent_key in VOCAB_STATS_TEXT_KEYS:
                add_text(node)
            return
        if isinstance(node, list):
            for item in node:
                walk(item, parent_key)
                if limit_reached():
                    break
            return
        if isinstance(node, dict):
            for key, value in node.items():
                normalized_key = clean(key).lower()
                if isinstance(value, str) and normalized_key in VOCAB_STATS_TEXT_KEYS:
                    add_text(value)
                else:
                    walk(value, normalized_key)
                if limit_reached():
                    break

    walk(payload)
    return result


# Added 2026-07-03: extracts lightweight Space_W/translation vocab keys from saved token rows.
def future_translation_payload_vocabulary_words(payload: dict, limit: int = 0) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    if payload.get("k") == "ftg":
        nodes = payload.get("n")
    elif payload.get("kind") == "future_translation_payload":
        nodes = payload.get("nodes")
    else:
        return []
    result: list[dict] = []
    seen: set[str] = set()

    def limit_reached() -> bool:
        return limit > 0 and len(result) >= limit

    def add_word(word_value: object, meaning_value: object = "", pron_value: object = "", type_value: object = "") -> None:
        if limit_reached():
            return
        word = clean(word_value).replace("’", "'").strip("'’-")
        key = vocab_key(word)
        if not key or key in seen or key in VOCAB_STATS_STOP_WORDS or len(key) < 2:
            return
        if not re.fullmatch(r"[A-Za-z][A-Za-z'’-]*", word):
            return
        seen.add(key)
        result.append({
            "word": word,
            "meaning": clean(meaning_value),
            "pron": clean(pron_value),
            "type": clean(type_value),
        })

    def add_text(text_value: object) -> None:
        if limit_reached():
            return
        text = clean(text_value)
        if not text:
            return
        for match in re.finditer(r"[A-Za-z][A-Za-z'’-]{1,}", text):
            add_word(match.group(0))
            if limit_reached():
                break

    for node in nodes if isinstance(nodes, list) else []:
        if not isinstance(node, dict):
            continue
        token_rows = []
        for token_key in ("tk", "sc", "an"):
            rows = node.get(token_key)
            if isinstance(rows, list):
                token_rows = rows
                break
        for token in token_rows:
            if not isinstance(token, dict):
                continue
            add_word(
                token.get("l") or token.get("n") or token.get("t"),
                token.get("m", ""),
                token.get("i") or token.get("iu") or token.get("ik") or "",
                token.get("p", ""),
            )
            if limit_reached():
                break
        if not token_rows:
            add_text(node.get("e") or node.get("en") or "")
        if limit_reached():
            break
    return result


def lesson_payload_vocabulary_words(payload: dict) -> list[dict]:
    words = vocabulary_words_from_payload(payload)
    if words:
        return words
    words = future_translation_payload_vocabulary_words(payload)
    return words if words else vocabulary_text_words_from_payload(payload)


def lesson_vocabulary_stats_from_words(
    words: list[dict],
    target_user: str,
    path: str = "",
    space: str = "Lesson",
    title: str = "",
) -> dict:
    registry = read_user_vocab_registry(target_user)
    learned_keys = set((registry.get("words", {}) or {}).keys())
    unique_words = []
    seen = set()
    for item in words if isinstance(words, list) else []:
        key = vocab_key((item or {}).get("word", "")) if isinstance(item, dict) else ""
        if not key or key in seen:
            continue
        seen.add(key)
        unique_words.append(item)
    new_words = [item for item in unique_words if vocab_key(item.get("word", "")) not in learned_keys]
    known_words = [item for item in unique_words if vocab_key(item.get("word", "")) in learned_keys]
    unique_keys = [vocab_key(item.get("word", "")) for item in unique_words]
    period_state = load_vocab_leaderboard_period_state()
    period_keys = vocab_leaderboard_period_word_keys_for_user(target_user, period_state)
    top_earnable = {
        scope: len([key for key in unique_keys if key and key not in period_keys.get(scope, set())])
        for scope in ("day", "week", "month")
    }
    top_recorded = {
        scope: len(period_keys.get(scope, set()))
        for scope in ("day", "week", "month")
    }
    return {
        "user": target_user,
        "path": clean_path_value(path),
        "space": clean(space) or "Lesson",
        "title": clean(title),
        "total_words": len(unique_words),
        "new_words": len(new_words),
        "known_words": len(known_words),
        "top_earnable": top_earnable,
        "top_recorded": top_recorded,
        "word_keys": unique_keys,
        "sample_new": [clean(item.get("word", "")) for item in new_words[:12] if clean(item.get("word", ""))],
    }


def lesson_file_vocabulary_stats(relative_path: str, viewer_username: str, target_username: str = "") -> dict:
    viewer = normalize_username(viewer_username)
    target_user = normalize_username(target_username or viewer)
    ok, message = validate_username(viewer)
    if not ok:
        raise RuntimeError(message)
    ok, message = validate_username(target_user)
    if not ok:
        raise RuntimeError(message)
    raw_path = clean_path_value(relative_path)
    if not raw_path:
        raise RuntimeError("Thieu duong dan file lesson.")
    target = safe_server_data_path(raw_path, viewer, admin=is_admin_user(viewer))
    suffix = target.suffix.lower()
    if not target.is_file() or suffix not in VOCAB_STATS_SUPPORTED_EXTENSIONS:
        raise RuntimeError("Chi ho tro dem tu vung cho Space_V/W/Q/P/S/L.")
    file_payload, _structure_path = load_future_lesson_document(target)
    return lesson_vocabulary_stats_from_words(
        lesson_payload_vocabulary_words(file_payload),
        target_user,
        server_data_relative(target),
        VOCAB_STATS_SPACE_LABELS.get(suffix, "Lesson"),
        lesson_payload_title(file_payload, target.stem),
    )


def space_v_file_vocabulary_stats(relative_path: str, viewer_username: str, target_username: str = "") -> dict:
    return lesson_file_vocabulary_stats(relative_path, viewer_username, target_username)


# Added 2026-08-01: validates lesson vocabulary once against the shared QmDict revision for every user.
def qmdict_valid_vocab_keys_for_words(words: object) -> tuple[list[str], str]:
    signature = qmdict_source_signature_key()
    signature_text = f"{int(signature[0])}:{int(signature[1])}"
    summary_maps = qmdict_registry_summary_maps()
    valid_keys: list[str] = []
    seen: set[str] = set()
    for item in words if isinstance(words, list) else []:
        surface = clean(item.get("word", "")) if isinstance(item, dict) else clean(item)
        key = vocab_key(surface)
        if not key or key in seen:
            continue
        detail = summary_maps.get(key) if isinstance(summary_maps, dict) and summary_maps else None
        if (not isinstance(summary_maps, dict) or not summary_maps) and (not isinstance(detail, dict) or not detail):
            detail = qmdict_lookup_summary(surface, surface)
        if not isinstance(detail, dict) or not detail:
            continue
        resolved_key = vocab_key(detail.get("word", "")) or key
        pronunciation = clean(detail.get("pron", "") or detail.get("pron_uk", "") or detail.get("pron_us", ""))
        if (
            not resolved_key
            or resolved_key in seen
            or not clean(detail.get("meaning", ""))
            or not pronunciation
            or not clean(detail.get("type", ""))
        ):
            continue
        seen.add(resolved_key)
        valid_keys.append(resolved_key)
    return valid_keys, signature_text


def lesson_file_vocab_meta_for_target(target: Path) -> dict:
    try:
        path = Path(target)
        suffix = path.suffix.lower()
        if not path.is_file() or suffix not in VOCAB_STATS_SUPPORTED_EXTENSIONS:
            return {}
        stat = path.stat()
        cache_key = str(path.resolve()).lower()
        current_qmdict_signature = qmdict_source_signature_key()
        current_qmdict_signature_text = f"{int(current_qmdict_signature[0])}:{int(current_qmdict_signature[1])}"
        source_revision = f"{stat.st_mtime_ns}:{stat.st_size}"
        signature = f"{source_revision}:{current_qmdict_signature_text}:{VOCAB_FILE_META_EXTRACTOR_VERSION}"
        cached = VOCAB_FILE_META_RAM_CACHE.get(cache_key)
        if isinstance(cached, dict) and cached.get("signature") == signature:
            return dict(cached.get("payload") or {})
        relative_key = clean_path_value(server_data_relative(path)).lower()
        persistent_rows = load_vocab_file_meta_index_once()
        persistent = persistent_rows.get(relative_key) if relative_key else None
        if (
            isinstance(persistent, dict)
            and int(persistent.get("mtime_ns", 0) or 0) == int(stat.st_mtime_ns)
            and int(persistent.get("size", -1) or -1) == int(stat.st_size)
            and clean(persistent.get("vocab_extractor_version", "")) == VOCAB_FILE_META_EXTRACTOR_VERSION
        ):
            raw_keys = list(persistent.get("vocab_word_keys") or [])
            valid_keys = list(persistent.get("vocab_valid_word_keys") or [])
            if clean(persistent.get("vocab_validated_signature", "")) != current_qmdict_signature_text:
                valid_keys, current_qmdict_signature_text = qmdict_valid_vocab_keys_for_words(raw_keys)
                with VOCAB_FILE_META_INDEX_LOCK:
                    persistent.update({
                        "vocab_valid_word_keys": valid_keys,
                        "vocab_validated_signature": current_qmdict_signature_text,
                    })
                    VOCAB_FILE_META_INDEX_STATE["revision"] = int(VOCAB_FILE_META_INDEX_STATE.get("revision", 0) or 0) + 1
                schedule_vocab_file_meta_index_write()
            result = {
                "lesson_id": clean(persistent.get("lesson_id", ""))[:240],
                "vocab_word_keys": raw_keys,
                "vocab_valid_word_keys": valid_keys,
                "vocab_validated_signature": current_qmdict_signature_text,
                "vocab_extractor_version": VOCAB_FILE_META_EXTRACTOR_VERSION,
                "vocab_source_revision": source_revision,
                "vocab_source_title": clean(persistent.get("vocab_source_title", "")) or path.stem,
                "vocab_total_words": max(0, int(persistent.get("vocab_total_words", 0) or 0)),
                "vocab_space": clean(persistent.get("vocab_space", "")) or VOCAB_STATS_SPACE_LABELS.get(suffix, "Lesson"),
            }
            remember_vocab_lesson_meta({**result, "mtime_ns": int(stat.st_mtime_ns), "size": int(stat.st_size)}, relative_key)
            VOCAB_FILE_META_RAM_CACHE[cache_key] = {"signature": signature, "payload": result, "at": time.time()}
            return result
        payload, _structure_path = load_future_lesson_document(path)
        try:
            from future_lesson_identity import lesson_id_from_payload
            lesson_id = clean(lesson_id_from_payload(payload))[:240]
        except Exception:
            lesson_id = ""
        word_keys = []
        seen = set()
        vocabulary_words = lesson_payload_vocabulary_words(payload)
        for item in vocabulary_words:
            key = vocab_key(item.get("word", "")) if isinstance(item, dict) else ""
            if key and key not in seen:
                seen.add(key)
                word_keys.append(key)
        valid_word_keys, qmdict_signature_text = qmdict_valid_vocab_keys_for_words(vocabulary_words)
        result = {
            "lesson_id": lesson_id,
            "vocab_word_keys": word_keys,
            "vocab_valid_word_keys": valid_word_keys,
            "vocab_validated_signature": qmdict_signature_text,
            "vocab_extractor_version": VOCAB_FILE_META_EXTRACTOR_VERSION,
            "vocab_source_revision": source_revision,
            "vocab_source_title": lesson_payload_title(payload, path.stem) or path.stem,
            "vocab_total_words": len(word_keys),
            "vocab_space": VOCAB_STATS_SPACE_LABELS.get(suffix, "Lesson"),
        }
        VOCAB_FILE_META_RAM_CACHE[cache_key] = {"signature": signature, "payload": result, "at": time.time()}
        if relative_key:
            with VOCAB_FILE_META_INDEX_LOCK:
                persistent_rows[relative_key] = {
                    "mtime_ns": int(stat.st_mtime_ns),
                    "size": int(stat.st_size),
                    **result,
                }
                VOCAB_FILE_META_INDEX_STATE["revision"] = int(VOCAB_FILE_META_INDEX_STATE.get("revision", 0) or 0) + 1
            remember_vocab_lesson_meta({**result, "mtime_ns": int(stat.st_mtime_ns), "size": int(stat.st_size)}, relative_key)
            schedule_vocab_file_meta_index_write()
        if len(VOCAB_FILE_META_RAM_CACHE) > VOCAB_FILE_META_RAM_CACHE_LIMIT:
            stale = sorted(VOCAB_FILE_META_RAM_CACHE.items(), key=lambda item: float((item[1] or {}).get("at", 0) or 0))
            for old_key, _old_value in stale[: max(1, len(stale) - VOCAB_FILE_META_RAM_CACHE_LIMIT)]:
                VOCAB_FILE_META_RAM_CACHE.pop(old_key, None)
        return dict(result)
    except Exception:
        return {}


def vocab_lesson_index_signature() -> str:
    try:
        latest = 0
        count = 0
        for path in SERVER_DATA_ROOT.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in VOCAB_STATS_SUPPORTED_EXTENSIONS:
                continue
            count += 1
            try:
                latest = max(latest, path.stat().st_mtime_ns)
            except OSError:
                pass
        qmdict_signature = qmdict_source_signature_key()
        return f"{count}:{latest}:{int(qmdict_signature[0])}:{int(qmdict_signature[1])}"
    except Exception:
        return f"error:{time.time():.0f}"


def build_vocab_lesson_index(max_files: int = 6000) -> list[dict]:
    rows = []
    checked = 0
    for target in SERVER_DATA_ROOT.rglob("*"):
        if checked >= max_files:
            break
        if not target.is_file():
            continue
        suffix = target.suffix.lower()
        if suffix not in VOCAB_STATS_SUPPORTED_EXTENSIONS:
            continue
        checked += 1
        try:
            meta = lesson_file_vocab_meta_for_target(target)
            word_keys = list(meta.get("vocab_valid_word_keys") or []) if isinstance(meta, dict) else []
            if not word_keys:
                continue
            rows.append({
                "path": server_data_relative(target),
                "space": clean(meta.get("vocab_space", "")) or VOCAB_STATS_SPACE_LABELS.get(suffix, "Lesson"),
                "title": clean(meta.get("vocab_source_title", "")) or target.stem,
                "word_keys": word_keys,
                "total_words": len(word_keys),
            })
        except Exception:
            continue
    return rows

def warm_vocab_lesson_index_cache() -> dict:
    started = time.perf_counter()
    signature = vocab_lesson_index_signature()
    with VOCAB_LESSON_INDEX_WARM_LOCK:
        cached_signature = clean(VOCAB_LESSON_INDEX_RAM_CACHE.get("signature", ""))
        files = VOCAB_LESSON_INDEX_RAM_CACHE.get("files") if isinstance(VOCAB_LESSON_INDEX_RAM_CACHE.get("files"), list) else []
        if files and cached_signature == signature:
            return {
                "ok": True,
                "signature": signature,
                "files": len(files),
                "cached": True,
                "ms": int((time.perf_counter() - started) * 1000),
            }
        files = build_vocab_lesson_index()
        VOCAB_LESSON_INDEX_RAM_CACHE.update({"signature": signature, "built_at": time.time(), "files": files})
    return {
        "ok": True,
        "signature": signature,
        "files": len(files),
        "cached": False,
        "ms": int((time.perf_counter() - started) * 1000),
    }

def warm_vocab_lesson_index_cache_async(delay_seconds: float = 0.8) -> None:
    global VOCAB_LESSON_INDEX_WARM_THREAD
    thread = VOCAB_LESSON_INDEX_WARM_THREAD
    if isinstance(thread, threading.Thread) and thread.is_alive():
        return

    def _runner() -> None:
        try:
            if delay_seconds > 0:
                time.sleep(delay_seconds)
            result = warm_vocab_lesson_index_cache()
            print(
                f"Vocabulary lesson index warm: files {result.get('files', 0)}, {result.get('ms', 0)}ms"
                f"{' (cached)' if result.get('cached') else ''}.",
                flush=True,
            )
        except Exception as exc:
            stt_debug_log("vocab_lesson_index_warm_failed", error=str(exc))

    thread = threading.Thread(target=_runner, daemon=True, name="vocab-lesson-index-warm")
    VOCAB_LESSON_INDEX_WARM_THREAD = thread
    thread.start()


def vocab_lesson_index_for_user(username: str, build_missing: bool = False) -> dict:
    username = normalize_username(username)
    now = time.time()
    cached_signature = clean(VOCAB_LESSON_INDEX_RAM_CACHE.get("signature", ""))
    cached_at = float(VOCAB_LESSON_INDEX_RAM_CACHE.get("built_at", 0) or 0)
    files = VOCAB_LESSON_INDEX_RAM_CACHE.get("files") if isinstance(VOCAB_LESSON_INDEX_RAM_CACHE.get("files"), list) else []
    signature = cached_signature
    if build_missing and (not files or now - cached_at > VOCAB_LESSON_INDEX_RAM_TTL_SECONDS):
        signature = vocab_lesson_index_signature()
    if build_missing and (not files or cached_signature != signature):
        files = build_vocab_lesson_index()
        VOCAB_LESSON_INDEX_RAM_CACHE.update({"signature": signature, "built_at": now, "files": files})
    registry = read_user_vocab_registry(username)
    learned_keys = sorted([key for key in (registry.get("words", {}) or {}).keys() if clean(key)])
    period_state = load_vocab_leaderboard_period_state()
    period_keys = vocab_leaderboard_period_word_keys_for_user(username, period_state)
    return {
        "user": username,
        "signature": signature,
        "built_at": VOCAB_LESSON_INDEX_RAM_CACHE.get("built_at", now),
        "files": files,
        "learned_keys": learned_keys,
        "period_keys": {scope: sorted(period_keys.get(scope, set())) for scope in ("day", "week", "month")},
    }
