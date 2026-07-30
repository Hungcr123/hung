# Loaded by FUTURE.server_parts.10_vocab_build_status into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def lesson_english_text(payload: dict) -> str:
    if not isinstance(payload, dict):
        return ""
    if payload.get("k") == "ftq" or payload.get("kind") == "future_question_payload":
        parts = []
        def walk(node: object) -> None:
            if isinstance(node, list):
                for item in node:
                    walk(item)
                return
            if not isinstance(node, dict):
                return
            for key in ("question", "q", "text", "prompt", "answer", "a", "en", "english"):
                value = clean(node.get(key, ""))
                if value:
                    parts.append(value)
            for key in ("answers", "choices", "options", "nodes", "questions", "cards", "children"):
                child = node.get(key)
                if isinstance(child, (list, dict)):
                    walk(child)
        walk(payload.get("nodes") if isinstance(payload.get("nodes"), list) else payload)
        return "\n".join(parts)
    if payload.get("k") == "ftp" or payload.get("kind") == "future_paragraph_payload":
        nodes = payload.get("nodes") if isinstance(payload.get("nodes"), list) else payload.get("n")
        parts = []
        for node in nodes if isinstance(nodes, list) else []:
            if not isinstance(node, dict):
                continue
            children = node.get("children") if isinstance(node.get("children"), list) else []
            child_parts = [
                clean(child.get("text", ""))
                for child in children
                if isinstance(child, dict) and clean(child.get("text", ""))
            ]
            if child_parts:
                parts.extend(child_parts)
                continue
            text = clean(node.get("text", ""))
            if text:
                parts.append(text)
        return "\n".join(parts)
    if payload.get("k") == "ftg":
        nodes = payload.get("n")
        keys = ("e", "en")
    elif payload.get("kind") == "future_translation_payload":
        nodes = payload.get("nodes")
        keys = ("en", "e")
    else:
        nodes = []
        keys = ("en", "e")
    parts = []
    for node in nodes if isinstance(nodes, list) else []:
        if not isinstance(node, dict):
            continue
        for key in keys:
            text = clean(node.get(key, ""))
            if text:
                parts.append(text)
                break
    return "\n".join(parts)


def resolve_vocab_entries_for_text(text: str):
    source_text = clean(text)
    if not source_text:
        return []
    signature_key = qmdict_source_signature_key()
    text_hash = hashlib.sha1(source_text.encode("utf-8", "replace")).hexdigest()
    cache_key = ("valid-space-v-runtime-v3", signature_key, text_hash)
    with QMDICT_TEXT_ENTRY_CACHE_LOCK:
        cached_entries = QMDICT_TEXT_ENTRY_CACHE.get(cache_key)
    if isinstance(cached_entries, list):
        return list(cached_entries)

    # Added 2026-07-21: Server 2 resolves lesson vocabulary through its QmDict runtime, without GUI/openpyxl imports.
    def compute_entries():
        from types import SimpleNamespace  # noqa: PLC0415

        candidate_words = []
        seen_candidates = set()
        stop_words = globals().get("VOCAB_STATS_STOP_WORDS", set())
        for match in re.finditer(r"[A-Za-z][A-Za-z'’-]{1,}", source_text):
            word = clean(match.group(0).replace("’", "'")).strip("'’-")
            key = vocab_key(word)
            if not key or key in seen_candidates or key in stop_words or not is_single_vocab_word(word):
                continue
            seen_candidates.add(key)
            candidate_words.append(word)
            if len(candidate_words) >= 800:
                break
        deduped = []
        seen_resolved = set()
        for word in candidate_words:
            detail = qmdict_lookup_summary(word, word)
            if not isinstance(detail, dict) or not detail:
                continue
            entry = SimpleNamespace(
                word=clean(detail.get("word", "")) or word,
                meaning=clean(detail.get("meaning", "")),
                pron=clean(detail.get("pron", "")),
                word_type=clean(detail.get("type", "")),
                lookup_status="QmDict runtime",
            )
            key = vocab_key(entry.word)
            if not key or key in seen_resolved or not is_valid_space_v_vocab_entry(entry):
                continue
            seen_resolved.add(key)
            deduped.append(entry)
        with QMDICT_TEXT_ENTRY_CACHE_LOCK:
            QMDICT_TEXT_ENTRY_CACHE[cache_key] = list(deduped)
            if len(QMDICT_TEXT_ENTRY_CACHE) > QMDICT_TEXT_ENTRY_CACHE_LIMIT:
                QMDICT_TEXT_ENTRY_CACHE.clear()
        return deduped

    inflight_runner = globals().get("pdf_vocab_inflight_run")
    if callable(inflight_runner):
        result = inflight_runner(("lesson-vocab-runtime",) + cache_key, compute_entries)
        return list(result) if isinstance(result, list) else []
    return compute_entries()


def is_single_vocab_word(value: str) -> bool:
    text = clean(value)
    if not text:
        return False
    tokens = re.findall(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)?", text)
    return len(tokens) == 1


# Added 2026-07-12: keeps Space_W/Q/P/S/L prerequisite Space_V packs limited to complete QmDict-valid words.
def is_valid_space_v_vocab_entry(entry) -> bool:
    word = clean(getattr(entry, "word", ""))
    if not word or not is_single_vocab_word(word):
        return False
    status = clean(getattr(entry, "lookup_status", "")).lower()
    if "không thấy" in status or status.startswith("thiếu"):
        return False
    if not clean(getattr(entry, "meaning", "")):
        return False
    if not clean(getattr(entry, "pron", "")):
        return False
    if not clean(getattr(entry, "word_type", "")):
        return False
    return True


def entry_to_summary(entry) -> dict:
    word = clean(getattr(entry, "word", ""))
    summary = {
        "word": clean(getattr(entry, "word", "")),
        "meaning": clean(getattr(entry, "meaning", "")),
        "pron": clean(getattr(entry, "pron", "")),
        "type": clean(getattr(entry, "word_type", "")),
    }
    try:
        detail = qmdict_lookup_summary_queued(word)
    except Exception:
        detail = {}
    if isinstance(detail, dict) and detail:
        for field in ("usage", "context", "note", "kind", "pron_us", "pron_uk"):
            value = clean(detail.get(field, ""))
            if value and not clean(summary.get(field, "")):
                summary[field] = value
        examples = word_agent_clean_examples(detail.get("examples", []))
        if examples:
            summary["examples"] = examples
    return summary


def lesson_progress_completed_summary(
    progress: dict | None,
    space: str = "",
    total_hint: int = 0,
    completed_at: str = "",
) -> dict:
    source = progress if isinstance(progress, dict) else {}
    completed_runs = max(1, space_w_int(source.get("completedRuns", source.get("completed_runs", 0)), 0))
    total = max(
        0,
        space_w_int(source.get("total", 0), 0),
        int(total_hint or 0),
    )
    if not total:
        return {
            **source,
            "space": space,
            "label": lesson_progress_label(space),
            "completed": True,
            "in_progress": False,
            "percent": 100,
            "completed_runs": completed_runs,
            "completedRuns": completed_runs,
        }
    out = {
        **source,
        "space": space,
        "label": lesson_progress_label(space),
        "done": total,
        "total": total,
        "percent": 100,
        "text": f"{total}/{total}",
        "completed": True,
        "in_progress": False,
        "completed_runs": completed_runs,
        "completedRuns": completed_runs,
    }
    if completed_at:
        out["completed_at"] = clean(completed_at)
    node_total = max(0, space_w_int(source.get("node_total", source.get("nodeTotal", 0)), 0))
    if node_total:
        out["node_done"] = node_total
        out["nodes_text"] = f"{node_total}/{node_total}"
    return out
