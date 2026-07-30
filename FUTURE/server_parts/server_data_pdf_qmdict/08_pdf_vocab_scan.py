# Loaded by FUTURE.server_parts.07_server_data_pdf_qmdict into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def pdf_vocab_phrase_summary(item: object = None) -> dict:
    source = item if isinstance(item, dict) else {}
    word = clean(source.get("word", ""))
    if not word or len(word.split()) < 2:
        return {}
    extra = word_agent_phrase_extra(word)
    match_span = source.get("_phrase_match_span") if isinstance(source.get("_phrase_match_span"), list) else []
    match_span = [space_w_int(value, -1) for value in match_span]
    match_span = [value for value in match_span if value >= 0]
    item_type = clean(source.get("type", "")) or clean(extra.get("type", ""))
    examples = word_agent_clean_examples(source.get("examples"), source.get("example", ""), source.get("example_vi", "")) or word_agent_clean_examples(extra.get("examples"))
    return {
        "word": word,
        "surface": clean(source.get("_phrase_match_surface") or source.get("surface") or word),
        "meaning": clean(source.get("meaning", "")) or clean(extra.get("meaning", "")),
        "pron": clean(source.get("pron", "")),
        "type": item_type,
        "usage": clean(source.get("usage", "")) or clean(extra.get("usage", "")),
        "context": clean(source.get("context", "")) or clean(extra.get("context", "")),
        "note": clean(source.get("note", "")) or clean(extra.get("note", "")),
        "collocations": word_agent_clean_list(source.get("collocations"), 16) or word_agent_clean_list(extra.get("collocations"), 16),
        "examples": examples,
        "notes": word_agent_clean_list(source.get("notes"), 10) or word_agent_clean_list(extra.get("notes"), 10),
        "example": clean(source.get("example", "")) or (examples[0].get("en", "") if examples else ""),
        "example_vi": clean(source.get("example_vi", "")) or (examples[0].get("vi", "") if examples else ""),
        "match_mode": clean(source.get("_phrase_match_mode", "")),
        "match_exact": bool(source.get("_phrase_match_exact")),
        "span": match_span,
        "kind": "phrasal_verb" if re.search(r"\bphrasal\b|cụm\s+động\s+từ", item_type, re.IGNORECASE) else "phrase",
    }


def fast_phrase_stats_for_text(text: str = "", learned_keys: set[str] | None = None) -> dict:
    source_text = clean(text)
    if not source_text:
        return {"phrases": [], "unknown_phrases": [], "known_phrases": [], "phrasal_verbs": [], "unknown_phrasal_verbs": []}
    learned = learned_keys if isinstance(learned_keys, set) else set()
    signature_key = qmdict_source_signature_key()
    text_hash = hashlib.sha1(source_text.encode("utf-8", "replace")).hexdigest()
    cache_key = (signature_key, text_hash)
    with QMDICT_TEXT_PHRASE_CACHE_LOCK:
        cached_phrases = QMDICT_TEXT_PHRASE_CACHE.get(cache_key)
    if isinstance(cached_phrases, list):
        phrases = [dict(item) for item in cached_phrases if isinstance(item, dict)]
    else:
        try:
            configure_paths()
            from module_main.QM_GATE import viewer_vocab_runtime as vocab_runtime  # noqa: PLC0415
        except Exception:
            return {"phrases": [], "unknown_phrases": [], "known_phrases": [], "phrasal_verbs": [], "unknown_phrasal_verbs": []}
        try:
            raw_items = list(vocab_runtime.extract_exact_vocab_words_from_text(source_text) or [])
        except Exception:
            raw_items = []
        phrases = []
        seen = set()
        for item in raw_items:
            summary = pdf_vocab_phrase_summary(item)
            key = vocab_key(summary.get("word", ""))
            if not summary or not key or key in seen:
                continue
            if not summary.get("match_exact") and summary.get("kind") != "phrasal_verb":
                continue
            seen.add(key)
            phrases.append(summary)
        with QMDICT_TEXT_PHRASE_CACHE_LOCK:
            QMDICT_TEXT_PHRASE_CACHE[cache_key] = [dict(item) for item in phrases]
            if len(QMDICT_TEXT_PHRASE_CACHE) > QMDICT_TEXT_PHRASE_CACHE_LIMIT:
                QMDICT_TEXT_PHRASE_CACHE.clear()
    known = [item for item in phrases if vocab_key(item.get("word", "")) in learned]
    unknown = [item for item in phrases if vocab_key(item.get("word", "")) not in learned]
    phrasal = [item for item in phrases if item.get("kind") == "phrasal_verb"]
    unknown_phrasal = [item for item in phrasal if vocab_key(item.get("word", "")) not in learned]
    return {
        "phrases": phrases[:180],
        "unknown_phrases": unknown[:120],
        "known_phrases": known[:80],
        "phrasal_verbs": phrasal[:120],
        "unknown_phrasal_verbs": unknown_phrasal[:80],
        "phrase_total": len(phrases),
        "phrase_unknown": len(unknown),
        "phrase_known": len(known),
        "phrasal_verb_total": len(phrasal),
        "phrasal_verb_unknown": len(unknown_phrasal),
    }


def pdf_vocab_token_detail_map(text: str = "", learned_keys: set[str] | None = None) -> dict:
    source_text = clean(text)
    if not source_text:
        return {"token_details": {}, "unknown_tokens": [], "known_tokens": []}
    learned = learned_keys if isinstance(learned_keys, set) else set()
    signature_key = qmdict_source_signature_key()
    text_hash = hashlib.sha1(source_text.encode("utf-8", "replace")).hexdigest()
    cache_key = (signature_key, text_hash)
    with QMDICT_TEXT_TOKEN_DETAIL_CACHE_LOCK:
        cached_details = QMDICT_TEXT_TOKEN_DETAIL_CACHE.get(cache_key)
    if isinstance(cached_details, dict):
        token_details: dict[str, list[dict]] = {
            clean(key): [dict(item) for item in value if isinstance(item, dict)]
            for key, value in cached_details.items()
            if clean(key) and isinstance(value, list)
        }
    else:
        try:
            vocab_runtime, qmdict = qmdict_runtime_and_dict()
        except Exception:
            return {"token_details": {}, "unknown_tokens": [], "known_tokens": []}
        if not isinstance(qmdict, dict) or not qmdict:
            return {"token_details": {}, "unknown_tokens": [], "known_tokens": []}
        raw_tokens = re.findall(r"[A-Za-zÀ-ỹ]+(?:[-'’][A-Za-zÀ-ỹ]+)*", source_text, flags=re.UNICODE)
        token_details = {}
        seen_tokens: set[str] = set()
        for raw_token in raw_tokens:
            token = clean(str(raw_token or "").replace("’", "'")).strip("'")
            token_key = pdf_vocab_word_key(token)
            if not token_key or token_key in seen_tokens:
                continue
            seen_tokens.add(token_key)
            valid_lines = []
            try:
                vocab_runtime.is_valid_word(token_key, qmdict, valid_lines, number="1")
            except Exception:
                valid_lines = []
            details: list[dict] = []
            seen_words: set[str] = set()
            for line in list(valid_lines or []):
                try:
                    item = vocab_runtime.vocab_item_from_valid_line(line)
                except Exception:
                    item = None
                summary = pdf_vocab_item_summary(item, surface=token)
                word_key = vocab_key(summary.get("word", ""))
                if not summary or not word_key or word_key in seen_words:
                    continue
                seen_words.add(word_key)
                audio_map = qmdict_space_v_dynamic_audio_map(summary.get("word", ""), summary.get("meaning", ""))
                if audio_map:
                    summary["audio"] = audio_map
                    summary["au"] = audio_map
                details.append(summary)
            if not details:
                continue
            token_details[token_key] = details[:4]
        with QMDICT_TEXT_TOKEN_DETAIL_CACHE_LOCK:
            QMDICT_TEXT_TOKEN_DETAIL_CACHE[cache_key] = {
                key: [dict(item) for item in value]
                for key, value in token_details.items()
            }
            if len(QMDICT_TEXT_TOKEN_DETAIL_CACHE) > QMDICT_TEXT_TOKEN_DETAIL_CACHE_LIMIT:
                QMDICT_TEXT_TOKEN_DETAIL_CACHE.clear()
    for _token_key, details in list(token_details.items()):
        if not isinstance(details, list):
            continue
        for item in details:
            if not isinstance(item, dict):
                continue
            audio_map = qmdict_space_v_dynamic_audio_map(item.get("word", ""), item.get("meaning", ""))
            if audio_map:
                item["audio"] = audio_map
                item["au"] = audio_map
    unknown_tokens: list[str] = []
    known_tokens: list[str] = []
    for token_key, details in token_details.items():
        if any(vocab_key(item.get("word", "")) not in learned for item in details):
            unknown_tokens.append(token_key)
        else:
            known_tokens.append(token_key)
    return {
        "token_details": token_details,
        "unknown_tokens": unknown_tokens,
        "known_tokens": known_tokens,
    }


def pdf_vocab_inflight_run(cache_key: tuple[object, ...], compute_fn):
    leader = False
    with QMDICT_VOCAB_INFLIGHT_LOCK:
        row = QMDICT_VOCAB_INFLIGHT.get(cache_key)
        if not isinstance(row, dict):
            row = {"event": threading.Event(), "error": "", "value": None}
            QMDICT_VOCAB_INFLIGHT[cache_key] = row
            leader = True
        event = row.get("event")
    if leader:
        try:
            row["value"] = compute_fn()
        except Exception as exc:
            row["error"] = str(exc)
            raise
        finally:
            if isinstance(event, threading.Event):
                event.set()
            with QMDICT_VOCAB_INFLIGHT_LOCK:
                QMDICT_VOCAB_INFLIGHT.pop(cache_key, None)
        return row.get("value")
    if isinstance(event, threading.Event) and not event.wait(30.0):
        raise RuntimeError("Vocabulary analysis is still running. Please retry.")
    if row.get("error"):
        raise RuntimeError(clean(row.get("error", "")) or "Vocabulary analysis failed.")
    return row.get("value")


def copy_pdf_vocabulary_stats_payload(payload: object = None) -> dict:
    if not isinstance(payload, dict):
        return {}
    try:
        return json.loads(json.dumps(payload, ensure_ascii=False))
    except Exception:
        return dict(payload)


def pdf_empty_vocabulary_stats_payload() -> dict:
    return {
        "total": 0,
        "known": 0,
        "unknown": 0,
        "words": [],
        "unknown_words": [],
        "known_words": [],
        "phrases": [],
        "unknown_phrases": [],
        "known_phrases": [],
        "phrasal_verbs": [],
        "unknown_phrasal_verbs": [],
        "phrase_total": 0,
        "phrase_unknown": 0,
        "phrase_known": 0,
        "phrasal_verb_total": 0,
        "phrasal_verb_unknown": 0,
        "token_details": {},
        "unknown_tokens": [],
        "known_tokens": [],
        "word_agent_latest": {},
        "phonetic_ipa": {},
        "lazy_details": True,
    }


def pdf_cache_ocr_normalize_name(value: object = "") -> str:
    text = clean(value).lower()
    text = re.sub(r"\.[a-z0-9]{1,8}$", "", text)
    text = text.replace("'", "_").replace("’", "_").replace("`", "_")
    text = re.sub(r"[^a-z0-9\u00c0-\u1ef9]+", " ", text, flags=re.UNICODE)
    return clean(text)


def pdf_cache_ocr_text_variants(value: object = "") -> list[str]:
    text = clean(value)
    if not text:
        return []
    variants = [text]
    for encoding in ("cp1252", "latin1"):
        try:
            repaired = text.encode(encoding).decode("utf-8")
        except Exception:
            continue
        repaired = clean(repaired)
        if repaired and repaired not in variants:
            variants.append(repaired)
    return variants


def pdf_cache_ocr_folded_name(value: object = "") -> str:
    text = pdf_cache_ocr_normalize_name(value).replace("đ", "d").replace("Đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return clean(text)


def pdf_cache_ocr_name_keys(value: object = "") -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for variant in pdf_cache_ocr_text_variants(value):
        for key in (pdf_cache_ocr_normalize_name(variant), pdf_cache_ocr_folded_name(variant)):
            if not key or key in seen:
                continue
            seen.add(key)
            keys.append(key)
    return keys


def pdf_cache_ocr_root() -> Path:
    return SERVER_DATA_ROOT / "Cache ORC"


def pdf_cache_ocr_name_hints(relative_path: str = "", mode: str = "pdf", hints: list[object] | None = None) -> list[str]:
    names: list[str] = []
    for hint in list(hints or []):
        value = clean(hint)
        if value:
            names.append(Path(value).stem)
            names.append(value)
    rel = clean_path_value(relative_path)
    parts = [part for part in rel.replace("\\", "/").split("/") if clean(part)]
    if parts:
        last = clean(parts[-1])
        suffix = Path(last).suffix.lower()
        if mode == "picture" and suffix in IMAGE_FILE_SUFFIXES and len(parts) >= 2:
            names.append(clean(parts[-2]))
        names.append(Path(last).stem)
        names.append(last)
        if mode == "picture" and suffix not in IMAGE_FILE_SUFFIXES:
            names.append(last)
    out = []
    seen = set()
    for item in names:
        for name in pdf_cache_ocr_text_variants(item):
            if not name:
                continue
            keys = pdf_cache_ocr_name_keys(name)
            key = keys[0] if keys else ""
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(name)
    return out


def pdf_cache_ocr_child(root: Path, *parts: object) -> Path | None:
    current = root
    for raw in parts:
        name = clean(raw)
        if not name:
            return None
        current = current / name
    try:
        resolved = current.resolve()
        if not str(resolved).lower().startswith(str(root.resolve()).lower()):
            return None
        return resolved
    except Exception:
        return None


def pdf_cache_ocr_find_folder(target: Path, mode: str = "pdf", hints: list[object] | None = None, page: object = 1) -> Path | None:
    root = pdf_cache_ocr_root()
    cache_index = ocr_cache_index()
    if not cache_index:
        return None
    is_picture = mode == "picture"
    desired = target.parent.name if is_picture else target.stem
    hint_names = [clean(item) for item in (hints or []) if clean(item)]
    direct_candidates: list[Path] = []
    for hint in [desired, *hint_names]:
        candidate = pdf_cache_ocr_child(root, hint)
        if candidate is not None:
            direct_candidates.append(candidate)
    seen: set[str] = set()
    for candidate in direct_candidates:
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            candidate_key = candidate.relative_to(root).as_posix().lower()
        except Exception:
            candidate_key = ""
        if candidate_key in cache_index:
            return candidate
    desired_keys = []
    for lookup_name in [desired, *hint_names]:
        desired_keys.extend(pdf_cache_ocr_name_keys(lookup_name))
    desired_keys = [key for key in dict.fromkeys(desired_keys) if key]
    if not desired_keys:
        return None
    try:
        page_number = max(1, int(page or 1))
    except Exception:
        page_number = 1
    possible_page_files = {f"{page_number}.txt", f"{page_number:03d}.txt", f"{page_number:04d}.txt"}
    if is_picture:
        possible_page_files.add(f"{target.stem}.txt")
    fuzzy_matches: list[tuple[int, Path]] = []
    try:
        for folder_key, folder_row in cache_index.items():
            folder = root / Path(clean(folder_row.get("path", folder_key)))
            folder_keys = pdf_cache_ocr_name_keys(folder.name)
            if not folder_keys:
                continue
            score = 0
            for desired_key in desired_keys:
                for folder_key in folder_keys:
                    if folder_key == desired_key:
                        score = max(score, 100)
                    elif desired_key in folder_key or folder_key in desired_key:
                        score = max(score, 70)
            if score <= 0:
                continue
            available_files = folder_row.get("files") if isinstance(folder_row.get("files"), set) else set()
            if any(name.lower() in available_files for name in possible_page_files):
                score += 20
            fuzzy_matches.append((score, folder))
    except Exception:
        return None
    if fuzzy_matches:
        fuzzy_matches.sort(key=lambda item: (-item[0], len(str(item[1]))))
        return fuzzy_matches[0][1]
    return None


def pdf_cache_ocr_picture_target(relative_path: str = "", username: str = "", admin: bool = False, page: object = 1, hints: list[object] | None = None) -> tuple[Path, int, str]:
    hint_stems = []
    image_stem = ""
    folder_name = ""
    for hint in list(hints or []):
        value = clean(hint)
        if not value:
            continue
        suffix = Path(value).suffix.lower()
        stem = clean(Path(value).stem)
        if stem:
            hint_stems.append(stem)
        if suffix in IMAGE_FILE_SUFFIXES and stem:
            image_stem = stem
    try:
        page_number = max(1, int(page or 1))
    except Exception:
        page_number = 1
    rel = clean_path_value(relative_path)
    parts = [clean(part) for part in rel.replace("\\", "/").split("/") if clean(part)]
    if parts:
        last = parts[-1]
        suffix = Path(last).suffix.lower()
        if suffix in IMAGE_FILE_SUFFIXES:
            image_stem = image_stem or clean(Path(last).stem)
            if len(parts) >= 2:
                folder_name = parts[-2]
        else:
            if len(parts) >= 2 and (re.fullmatch(r"\d+", last) or image_stem):
                image_stem = image_stem or last
                folder_name = parts[-2]
            else:
                folder_name = last
    for hint in list(hints or []):
        value = clean(hint)
        if not value:
            continue
        suffix = Path(value).suffix.lower()
        if suffix not in IMAGE_FILE_SUFFIXES and pdf_cache_ocr_normalize_name(value) not in {pdf_cache_ocr_normalize_name(image_stem), pdf_cache_ocr_normalize_name(str(page_number))}:
            folder_name = folder_name or value
    page_stem = image_stem or (hint_stems[-1] if hint_stems else str(page_number))
    folder_name = folder_name or (hint_stems[0] if hint_stems else "picture")
    return Path(folder_name) / f"{page_stem}.jpg", page_number, page_stem


def pdf_cache_ocr_page_text(relative_path: str = "", username: str = "", admin: bool = False, page: object = 1, mode: str = "pdf", hints: list[object] | None = None) -> dict:
    clean_mode = "picture" if clean(mode).lower() == "picture" else "pdf"
    if clean_mode == "picture":
        target, page_number, page_stem = pdf_cache_ocr_picture_target(relative_path, username, admin=admin, page=page, hints=hints)
    else:
        name_hints = pdf_cache_ocr_name_hints(relative_path, "pdf", hints)
        fallback_name = name_hints[0] if name_hints else (Path(clean_path_value(relative_path)).stem or "document")
        target = Path(f"{fallback_name}.pdf")
        try:
            page_number = max(1, int(page or 1))
        except Exception:
            page_number = 1
        page_stem = str(page_number)
    name_hints = pdf_cache_ocr_name_hints(relative_path, clean_mode, hints)
    folder = pdf_cache_ocr_find_folder(target, clean_mode, hints=[*name_hints, *(hints or [])], page=page_number)
    if folder is None:
        folder_candidates = [str(pdf_cache_ocr_root() / name) for name in name_hints[:12]]
        return {
            "cache_hit": False,
            "text": "",
            "page": page_number,
            "mode": clean_mode,
            "reason": "cache_folder_missing",
            "cache_root": str(pdf_cache_ocr_root()),
            "lookup_names": name_hints[:12],
            "candidates": folder_candidates,
        }
    candidates = [
        folder / f"{page_number}.txt",
        folder / f"{page_number:03d}.txt",
        folder / f"{page_number:04d}.txt",
    ]
    if clean_mode == "picture":
        candidates.insert(0, folder / f"{page_stem}.txt")
        for hint in list(hints or []):
            hint_stem = clean(Path(clean(hint)).stem)
            if hint_stem:
                candidates.insert(0, folder / f"{hint_stem}.txt")
    seen_candidate_paths: set[str] = set()
    unique_candidates: list[Path] = []
    for candidate in candidates:
        key = str(candidate).lower()
        if key in seen_candidate_paths:
            continue
        seen_candidate_paths.add(key)
        unique_candidates.append(candidate)
    candidates = unique_candidates
    for file_path in candidates:
        try:
            folder_relative = folder.relative_to(pdf_cache_ocr_root()).as_posix()
            text = pdf_ocr_raw_candidate_text(structure_ocr_cache_page_text(folder_relative, file_path.name))
            if not text:
                continue
            return {
                "cache_hit": True,
                "text": lesson_task_notice_text(text, limit=24000),
                "page": page_number,
                "mode": clean_mode,
                "engine": "cache-ocr",
                "cache_folder": str(folder),
                "cache_file": f"PG:Cache ORC/{folder_relative}/{file_path.name}",
                "candidates": [str(item) for item in candidates[:12]],
            }
        except Exception:
            continue
    return {
        "cache_hit": False,
        "text": "",
        "page": page_number,
        "mode": clean_mode,
        "reason": "cache_page_missing",
        "cache_folder": str(folder),
        "candidates": [str(item) for item in candidates[:12]],
    }


def pdf_vocabulary_base_cache_key(text: str = "") -> tuple[object, ...]:
    source_text = clean(text)
    return (
        qmdict_source_signature_key(),
        hashlib.sha1(source_text.encode("utf-8", "replace")).hexdigest(),
    )


# Added 2026-07-07: shares PDF/Picture vocabulary scans for users with no learned registry.
def pdf_vocabulary_registry_cache_state(username: str = "") -> dict:
    normalized_user = normalize_username(username)
    generation_getter = globals().get("server_database_generation")
    registry_signature = (int(generation_getter("registry") if callable(generation_getter) else 0), 0)
    payload = read_user_vocab_registry(normalized_user)
    words = payload.get("words") if isinstance(payload, dict) and isinstance(payload.get("words"), dict) else {}
    learned_keys = {vocab_key(key) for key, value in words.items() if vocab_key(key) and isinstance(value, dict)}
    if not learned_keys:
        return {
            "identity": "__empty_vocab_registry__",
            "signature": (0, -1),
            "learned_keys": set(),
            "worker_username": "",
        }
    return {
        "identity": normalized_user.lower(),
        "signature": registry_signature,
        "learned_keys": learned_keys,
        "worker_username": normalized_user,
    }


def pdf_vocabulary_stats_cache_key(text: str = "", username: str = "", registry_state: dict | None = None) -> tuple[object, ...]:
    source_text = clean(text)
    state = registry_state if isinstance(registry_state, dict) else pdf_vocabulary_registry_cache_state(username)
    return (
        qmdict_source_signature_key(),
        clean(state.get("identity", "")) or "__empty_vocab_registry__",
        state.get("signature") if isinstance(state.get("signature"), tuple) else (0, -1),
        hashlib.sha1(source_text.encode("utf-8", "replace")).hexdigest(),
    )


def pdf_vocabulary_base_for_text(text: str = "") -> dict:
    source_text = clean(text)
    if not source_text:
        return {"words": [], "phrases": [], "token_details": {}}
    cache_key = pdf_vocabulary_base_cache_key(source_text)
    with QMDICT_VOCAB_BASE_CACHE_LOCK:
        cached_base = QMDICT_VOCAB_BASE_CACHE.get(cache_key)
    if isinstance(cached_base, dict):
        return copy_pdf_vocabulary_stats_payload(cached_base)

    def compute_base() -> dict:
        with QMDICT_VOCAB_BASE_CACHE_LOCK:
            cached_inside = QMDICT_VOCAB_BASE_CACHE.get(cache_key)
        if isinstance(cached_inside, dict):
            return copy_pdf_vocabulary_stats_payload(cached_inside)
        entries = resolve_vocab_entries_for_text(source_text)
        all_items = [entry_to_summary(entry) for entry in entries]
        phrase_stats = fast_phrase_stats_for_text(source_text, set())
        token_stats = pdf_vocab_token_detail_map(source_text, set())
        payload = {
            "words": all_items[:240],
            "phrases": list(phrase_stats.get("phrases", []) or [])[:180],
            "token_details": token_stats.get("token_details") if isinstance(token_stats.get("token_details"), dict) else {},
        }
        with QMDICT_VOCAB_BASE_CACHE_LOCK:
            QMDICT_VOCAB_BASE_CACHE[cache_key] = copy_pdf_vocabulary_stats_payload(payload)
            if len(QMDICT_VOCAB_BASE_CACHE) > QMDICT_VOCAB_BASE_CACHE_LIMIT:
                QMDICT_VOCAB_BASE_CACHE.clear()
        return payload

    return copy_pdf_vocabulary_stats_payload(pdf_vocab_inflight_run(("base", *cache_key), compute_base))


def vocabulary_stats_for_text(text: str = "", username: str = "", learned_keys_override: object = None) -> dict:
    source_text = clean(text)
    if not source_text:
        return pdf_empty_vocabulary_stats_payload()
    if isinstance(learned_keys_override, (list, tuple, set, frozenset)):
        learned_snapshot = {vocab_key(item) for item in learned_keys_override if vocab_key(item)}
        learned_signature = hashlib.sha1("\n".join(sorted(learned_snapshot)).encode("utf-8", "replace")).hexdigest()
        registry_state = {
            "identity": normalize_username(username).lower() or "__learned_snapshot__",
            "signature": ("snapshot", learned_signature),
            "learned_keys": learned_snapshot,
            "worker_username": normalize_username(username),
        }
    else:
        registry_state = pdf_vocabulary_registry_cache_state(username)
    cache_key = pdf_vocabulary_stats_cache_key(source_text, username, registry_state)
    with QMDICT_VOCAB_STATS_CACHE_LOCK:
        cached_stats = QMDICT_VOCAB_STATS_CACHE.get(cache_key)
    if isinstance(cached_stats, dict):
        return copy_pdf_vocabulary_stats_payload(cached_stats)
    learned_keys = registry_state.get("learned_keys") if isinstance(registry_state.get("learned_keys"), set) else set()
    base = pdf_vocabulary_base_for_text(source_text)
    all_items = list(base.get("words", []) or [])
    unknown_items = [
        item for item in all_items
        if vocab_key(item.get("word", "")) and vocab_key(item.get("word", "")) not in learned_keys
    ]
    known_items = [
        item for item in all_items
        if vocab_key(item.get("word", "")) and vocab_key(item.get("word", "")) in learned_keys
    ]
    phrases = [item for item in list(base.get("phrases", []) or []) if isinstance(item, dict)]
    known_phrases = [item for item in phrases if vocab_key(item.get("word", "")) in learned_keys]
    unknown_phrases = [item for item in phrases if vocab_key(item.get("word", "")) not in learned_keys]
    phrasal_verbs = [item for item in phrases if item.get("kind") == "phrasal_verb"]
    unknown_phrasal_verbs = [item for item in phrasal_verbs if vocab_key(item.get("word", "")) not in learned_keys]
    token_details = base.get("token_details") if isinstance(base.get("token_details"), dict) else {}
    unknown_tokens: list[str] = []
    known_tokens: list[str] = []
    for token_key, details in token_details.items():
        detail_list = details if isinstance(details, list) else [details]
        candidate_keys = {
            vocab_key(item.get("word", ""))
            for item in detail_list
            if isinstance(item, dict) and vocab_key(item.get("word", ""))
        }
        # Updated 2026-07-22: a learned surface or any learned lemma makes the
        # visible token known; an alternative dictionary sense must not turn it yellow.
        if token_key in learned_keys or bool(candidate_keys & learned_keys):
            known_tokens.append(token_key)
        else:
            unknown_tokens.append(token_key)
    payload = {
        "total": len(all_items),
        "known": len(known_items),
        "unknown": len(unknown_items),
        "words": all_items[:240],
        "unknown_words": unknown_items[:160],
        "known_words": known_items[:80],
        "phrases": phrases[:180],
        "unknown_phrases": unknown_phrases[:120],
        "known_phrases": known_phrases[:80],
        "phrasal_verbs": phrasal_verbs[:120],
        "unknown_phrasal_verbs": unknown_phrasal_verbs[:80],
        "phrase_total": len(phrases),
        "phrase_unknown": len(unknown_phrases),
        "phrase_known": len(known_phrases),
        "phrasal_verb_total": len(phrasal_verbs),
        "phrasal_verb_unknown": len(unknown_phrasal_verbs),
        "token_details": token_details,
        "unknown_tokens": unknown_tokens,
        "known_tokens": known_tokens,
        "word_agent_latest": {},
        "phonetic_ipa": {},
        "lazy_details": True,
    }
    with QMDICT_VOCAB_STATS_CACHE_LOCK:
        QMDICT_VOCAB_STATS_CACHE[cache_key] = copy_pdf_vocabulary_stats_payload(payload)
        if len(QMDICT_VOCAB_STATS_CACHE) > QMDICT_VOCAB_STATS_CACHE_LIMIT:
            QMDICT_VOCAB_STATS_CACHE.clear()
    return payload


# Added 2026-07-01: runs QmDict/phrase text scans in a dedicated process worker for multi-user smoothness.
def qmdict_vocabulary_stats_queued(text: str = "", username: str = "") -> dict:
    source_text = clean(text)
    if not source_text:
        return pdf_empty_vocabulary_stats_payload()
    registry_state = pdf_vocabulary_registry_cache_state(username)
    cache_key = pdf_vocabulary_stats_cache_key(source_text, username, registry_state)
    with QMDICT_VOCAB_STATS_CACHE_LOCK:
        cached_stats = QMDICT_VOCAB_STATS_CACHE.get(cache_key)
    if isinstance(cached_stats, dict):
        return copy_pdf_vocabulary_stats_payload(cached_stats)
    from FUTURE.server_parts.worker_jobs.heavy_language_jobs import qmdict_vocabulary_stats_worker

    def compute_stats() -> dict:
        worker_username = clean(registry_state.get("worker_username", ""))
        learned_snapshot = sorted(registry_state.get("learned_keys") or [])
        label_user = worker_username or "empty-registry"
        worker_payload = QMDICT_WORK_QUEUE.run(
            f"vocab-stats:{label_user[:32]}",
            qmdict_vocabulary_stats_worker,
            source_text,
            worker_username,
            learned_snapshot,
            timeout=QMDICT_WORK_QUEUE.timeout_seconds,
        )
        if isinstance(worker_payload, dict):
            with QMDICT_VOCAB_STATS_CACHE_LOCK:
                QMDICT_VOCAB_STATS_CACHE[cache_key] = copy_pdf_vocabulary_stats_payload(worker_payload)
                if len(QMDICT_VOCAB_STATS_CACHE) > QMDICT_VOCAB_STATS_CACHE_LIMIT:
                    QMDICT_VOCAB_STATS_CACHE.clear()
        return worker_payload

    payload = pdf_vocab_inflight_run(("stats", *cache_key), compute_stats)
    if isinstance(payload, dict):
        with QMDICT_VOCAB_STATS_CACHE_LOCK:
            QMDICT_VOCAB_STATS_CACHE[cache_key] = copy_pdf_vocabulary_stats_payload(payload)
            if len(QMDICT_VOCAB_STATS_CACHE) > QMDICT_VOCAB_STATS_CACHE_LIMIT:
                QMDICT_VOCAB_STATS_CACHE.clear()
        return copy_pdf_vocabulary_stats_payload(payload)
    return pdf_empty_vocabulary_stats_payload()


def pdf_scan_page_vocabulary(relative_path: str = "", username: str = "", admin: bool = False, page: object = 1) -> dict:
    result = ocr_pdf_region(
        relative_path,
        username,
        admin=admin,
        page=page,
        rect={"x": 0, "y": 0, "w": 1, "h": 1},
        zoom=2.2,
    )
    text = clean(result.get("text", ""))
    return {
        **result,
        "text": text,
        "vocabulary": qmdict_vocabulary_stats_queued(text, username),
    }


# Added 2026-07-12: builds Space_V missions from Ghost Eye word-bank rows without re-parsing them as prose.
def pdf_vocab_entries_from_word_bank(text: str = "", word_items: object = None):
    raw_words: list[str] = []
    manual_items = []
    if isinstance(word_items, list):
        for item in word_items:
            if not isinstance(item, dict):
                continue
            word = clean(item.get("word", ""))
            if not word or not is_single_vocab_word(word):
                continue
            raw_words.append(word)
            manual_items.append(item)
    if not raw_words:
        for line in str(text or "").splitlines():
            word = clean(str(line or "").strip(" -\t\r\n"))
            if word and is_single_vocab_word(word):
                raw_words.append(word)
                manual_items.append({"word": word})
    if not raw_words:
        return []
    cache_items = [
        {
            "word": clean(item.get("word", "")),
            "meaning": clean(item.get("meaning", "")),
            "pron": clean(item.get("pron", "")),
            "type": clean(item.get("type", "")),
        }
        for item in manual_items
        if isinstance(item, dict) and clean(item.get("word", ""))
    ]
    cache_blob = json.dumps(cache_items, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    cache_hash = hashlib.sha1(cache_blob.encode("utf-8", "replace")).hexdigest()
    cache_key = ("word-bank-v4", *qmdict_source_signature_key(), cache_hash)
    with QMDICT_TEXT_ENTRY_CACHE_LOCK:
        cached_entries = QMDICT_TEXT_ENTRY_CACHE.get(cache_key)
    if isinstance(cached_entries, list):
        return list(cached_entries)
    try:
        from scratch_vocab_builder_gui import VocabularyEntry, resolve_vocab_entries  # noqa: PLC0415
    except Exception:
        return resolve_vocab_entries_for_text("\n".join(raw_words))
    entries = []
    seen = set()
    for item in manual_items:
        word = clean(item.get("word", ""))
        key = pdf_vocab_word_key(word)
        if not key or key in seen or not is_single_vocab_word(word):
            continue
        seen.add(key)
        entries.append(
            VocabularyEntry(
                word=word,
                meaning=clean(item.get("meaning", "")),
                pron=clean(item.get("pron", "")),
                word_type=clean(item.get("type", "")),
                lookup_status="Ghost Eye word bank",
            )
        )
    resolved = resolve_vocab_entries(entries)
    allowed_keys = {pdf_vocab_word_key(item.get("word", "")) for item in manual_items if isinstance(item, dict)}
    valid_entries = []
    seen_valid = set()
    for entry in resolved:
        word = clean(getattr(entry, "word", ""))
        key = pdf_vocab_word_key(word)
        status = clean(getattr(entry, "lookup_status", "")).lower()
        if not word or not key or key in seen_valid or key not in allowed_keys or not is_single_vocab_word(word):
            continue
        if "không thấy" in status or status.startswith("thiếu"):
            continue
        if not clean(getattr(entry, "meaning", "")):
            continue
        if not clean(getattr(entry, "pron", "")):
            continue
        if not clean(getattr(entry, "word_type", "")):
            continue
        seen_valid.add(key)
        valid_entries.append(entry)
    with QMDICT_TEXT_ENTRY_CACHE_LOCK:
        QMDICT_TEXT_ENTRY_CACHE[cache_key] = list(valid_entries)
        if len(QMDICT_TEXT_ENTRY_CACHE) > QMDICT_TEXT_ENTRY_CACHE_LIMIT:
            QMDICT_TEXT_ENTRY_CACHE.clear()
    return valid_entries

def build_pdf_vocab_mission(
    relative_path: str = "",
    username: str = "",
    page: object = 1,
    text: str = "",
    include_known: bool = False,
    source: str = "",
    word_items: object = None,
) -> dict:
    username = normalize_username(username)
    raw_path = clean_path_value(relative_path)
    if not raw_path:
        raise RuntimeError("Chua co duong dan nguon.")
    raw_target = safe_server_data_path(raw_path, username, admin=is_admin_user(username))
    if raw_target.suffix.lower() == ".pdf":
        target = safe_pdf_server_data_path(raw_path, username, admin=is_admin_user(username))
        source_space = "Space_PDF"
        source_kind = "space_pdf_vocab_page"
    elif raw_target.suffix.lower() in IMAGE_FILE_SUFFIXES:
        target, _siblings, _index = picture_target_for_page(raw_path, username, admin=is_admin_user(username), page=page)
        source_space = "Space_Picture"
        source_kind = "space_picture_vocab_image"
    else:
        raise RuntimeError("Chi tao vocabulary tu PDF hoac anh.")
    page_number = max(1, space_w_int(page, 1))
    source_text = lesson_task_notice_text(text, limit=18000)
    scan_result = {}
    if not source_text:
        if source_space == "Space_Picture":
            scan_result = picture_scan_vocabulary(raw_path, username, admin=is_admin_user(username), page=page_number)
        else:
            scan_result = pdf_scan_page_vocabulary(raw_path, username, admin=is_admin_user(username), page=page_number)
        source_text = lesson_task_notice_text(scan_result.get("text", ""), limit=18000)
    if not source_text:
        raise RuntimeError("Ghost Eye chua co text de tao vocabulary.")
    word_bank_source = clean(source).lower() == "unlearned_word_bank"
    effective_include_known = bool(include_known) and not word_bank_source
    if word_bank_source:
        entries = pdf_vocab_entries_from_word_bank(source_text, word_items)
    else:
        entries = resolve_vocab_entries_for_text(source_text)
    registry = read_user_vocab_registry(username)
    learned_keys = set((registry.get("words", {}) or {}).keys())
    vocab_stats = qmdict_vocabulary_stats_queued(source_text, username)
    new_entries = [
        entry for entry in entries
        if vocab_key(getattr(entry, "word", "")) and vocab_key(getattr(entry, "word", "")) not in learned_keys
    ]
    if effective_include_known:
        new_entries = [
            entry for entry in entries
            if vocab_key(getattr(entry, "word", ""))
        ]
    source_title = target.stem
    source_rel = server_data_relative(target)
    if word_bank_source:
        digest_mode = "pdf-vocab-word-bank-v2"
        digest_source = "|".join(clean(getattr(entry, "word", "")) for entry in entries[:240])
    else:
        digest_mode = "pdf-vocab-v1-force" if effective_include_known else "pdf-vocab-v1"
        digest_source = source_text[:1200]
    digest = hashlib.sha1(f"{source_rel}|page:{page_number}|{digest_source}|{digest_mode}".encode("utf-8", "replace")).hexdigest()[:12]
    mission_name = safe_name_segment(f"{source_title} Page {page_number} {digest}", "PDF Vocabulary", 74)
    mission_root = server_data_user_folder_path(username) / VOCAB_MISSION_PENDING_DIR / mission_name
    expected_batches = math.ceil(len(new_entries) / VOCAB_MISSION_CHUNK_SIZE) if new_entries else 0
    pending = mission_file_records(mission_root, username, learned_keys=learned_keys, require_unlearned=not effective_include_known)
    if pending and (not expected_batches or len(pending) >= expected_batches):
        clear_lesson_metadata_cache()
        clear_server_data_list_cache()
        refresh_server_data_manifest_paths_now(
            [server_data_relative(mission_root.parent), server_data_relative(mission_root)],
            "pdf-vocab-mission-pending",
        )
        return {
            "source_path": source_rel,
            "source_title": source_title,
            "space": source_space,
            "page": page_number,
            "mission_id": mission_name,
            "mission_folder": server_data_relative(mission_root),
            "new_count": len(new_entries),
            "include_known": effective_include_known,
            "pending_count": len(pending),
            "files": pending,
            "vocabulary": scan_result.get("vocabulary", {}) if isinstance(scan_result, dict) else {},
        }
    if not new_entries:
        return {
            "source_path": source_rel,
            "source_title": source_title,
            "space": source_space,
            "page": page_number,
            "mission_id": mission_name,
            "mission_folder": server_data_relative(mission_root),
            "new_count": 0,
            "include_known": effective_include_known,
            "pending_count": 0,
            "files": [],
            "vocabulary": vocab_stats,
        }
    if pending and expected_batches and len(pending) < expected_batches and mission_root.is_dir():
        for stale_file in mission_root.glob("*.Space_V"):
            stale_file.unlink()
    mission_root.mkdir(parents=True, exist_ok=True)
    batches = [new_entries[index:index + VOCAB_MISSION_CHUNK_SIZE] for index in range(0, len(new_entries), VOCAB_MISSION_CHUNK_SIZE)]
    total_batches = len(batches)
    files = []
    title_root = safe_name_segment(f"{source_title} Page {page_number} Vocabulary", "PDF Vocabulary", 72)

    for batch_number, batch_entries in enumerate(batches, start=1):
        batch_title = title_root if total_batches == 1 else f"{title_root} {batch_number:03d}"
        payload = minimal_space_v_payload_from_entries(
            batch_entries,
            title=batch_title,
            batch_index=batch_number,
            batch_total=total_batches,
            mission={
                "kind": source_kind,
                "source_path": source_rel,
                "source_title": source_title,
                "source_space": source_space,
                "page": page_number,
                "mission_id": mission_name,
                "include_known": effective_include_known,
                "queue_index": batch_number,
                "queue_total": total_batches,
                "created_at": utc_timestamp(),
            },
        )
        target_stem = safe_name_segment(batch_title, "PDF Vocabulary", 72)
        if total_batches > 1:
            target_stem = f"{safe_name_segment(title_root, 'PDF Vocabulary', 68)} {batch_number:03d}"
        target_file = mission_root / f"{target_stem}.Space_V"
        write_generated_space_v_lesson(target_file, payload)
        files.append({
            "name": target_file.name,
            "path": server_data_relative(target_file),
            "size": int(target_file.stat().st_size),
            "study": summarize_lesson_study(target_file, username),
        })
    # Identity and durable lesson publication must finish before optional media warming.
    prefetch_space_v_images_for_entries(new_entries)
    clear_lesson_metadata_cache()
    clear_server_data_list_cache()
    refresh_server_data_manifest_paths_now(
        [server_data_relative(mission_root.parent), server_data_relative(mission_root)],
        "pdf-vocab-mission-build",
    )
    append_learning_log({
        "event": "pdf_vocab_mission_build",
        "user": username,
        "source_path": source_rel,
        "source_title": source_title,
        "space": source_space,
        "page": page_number,
        "mission_id": mission_name,
        "new_words": len(new_entries),
        "files": len(files),
    })
    return {
        "source_path": source_rel,
        "source_title": source_title,
        "space": source_space,
        "page": page_number,
        "mission_id": mission_name,
        "mission_folder": server_data_relative(mission_root),
        "new_count": len(new_entries),
        "include_known": effective_include_known,
        "pending_count": len(files),
        "files": files,
        "vocabulary": vocab_stats,
    }
