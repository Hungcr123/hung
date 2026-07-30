# Loaded by FUTURE.server_parts.08_progress_inventory_vocab into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def main_vocab_progress_path(username: str) -> Path:
    username = normalize_username(username)
    return USER_ROOT / f"{username}_vocab_progress.txt"


def main_server_user_dirs(username: str) -> list[Path]:
    username = normalize_username(username)
    if not username:
        return []
    result: list[Path] = []
    seen: set[str] = set()

    def _add(path: Path) -> None:
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            result.append(path)

    direct = MAIN_SERVER_USER_ROOT / username
    _add(direct)
    try:
        if not MAIN_SERVER_USER_ROOT.is_dir():
            return result
    except Exception:
        return result
    username_lower = username.lower()
    try:
        folders = list(MAIN_SERVER_USER_ROOT.iterdir())
    except Exception:
        folders = []
    for folder in folders:
        if not folder.is_dir():
            continue
        raw_name = folder.name
        raw_lower = raw_name.lower()
        matched = raw_lower == username_lower or raw_lower.startswith(f"{username_lower}__")
        if not matched:
            identity_path = folder / "_user_identity.json"
            try:
                identity = json.loads(identity_path.read_text(encoding="utf-8-sig", errors="replace")) if identity_path.is_file() else {}
            except Exception:
                identity = {}
            matched = normalize_username(identity.get("username", "") if isinstance(identity, dict) else "") == username
        if matched:
            _add(folder)
    return result


def main_vocab_progress_paths(username: str) -> list[Path]:
    username = normalize_username(username)
    if not username:
        return []
    rows = [
        USER_ROOT / f"{username}_vocab_progress.txt",
        MAIN_SERVER_USER_ROOT / f"{username}_vocab_progress.txt",
    ]
    rows.extend(folder / f"{username}_vocab_progress.txt" for folder in main_server_user_dirs(username))
    seen = set()
    unique = []
    for path in rows:
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def main_vocab_learned_root(username: str) -> Path:
    username = normalize_username(username)
    return USER_ROOT / username / "Learned Vocabulary"


def main_vocab_learned_roots(username: str) -> list[Path]:
    username = normalize_username(username)
    rows = [
        USER_ROOT / username / "Learned Vocabulary",
    ]
    rows.extend(folder / "Learned Vocabulary" for folder in main_server_user_dirs(username))
    seen = set()
    unique = []
    for path in rows:
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def main_vocab_time_text(value: object = "") -> str:
    # Regex-normalize legacy local values without thousands of strptime calls.
    return normalize_timestamp_text(value, fallback_now=True)


def parse_main_vocab_progress_line(line: str) -> dict:
    raw = str(line or "").strip()
    if not raw:
        return {}
    parts = [part.strip() for part in raw.split("|")]
    word = vocab_key(parts[0] if parts else "")
    if not word:
        return {}
    try:
        count = max(1, int(parts[2])) if len(parts) > 2 else 1
    except Exception:
        count = 1
    return {
        "word": word,
        "count": count,
        "last": main_vocab_time_text(parts[1] if len(parts) > 1 else ""),
    }


def format_main_vocab_progress_line(word: str, count: int = 1, last_time: str = "") -> str:
    safe_word = vocab_key(word)
    safe_count = max(1, int(count or 1))
    return f"{safe_word} | {main_vocab_time_text(last_time)} | {safe_count} | {safe_count}"


def parse_main_qmv_vocab_line(line: str) -> dict:
    raw = str(line or "").strip()
    if not raw:
        return {}
    if "\t" in raw:
        parts = [part.strip() for part in raw.split("\t")]
    elif "|" in raw:
        parts = [part.strip() for part in raw.split("|")]
        if len(parts) >= 4 and re.match(r"^\d+$", parts[2] if len(parts) > 2 else ""):
            return {}
    else:
        parts = [raw]
    return normalize_vocabulary_registry_item(
        {
            "word": parts[0] if len(parts) > 0 else "",
            "meaning": parts[1] if len(parts) > 1 else "",
            "pron": parts[2] if len(parts) > 2 else "",
            "type": parts[3] if len(parts) > 3 else "",
        }
    )


def read_main_vocab_progress_items(username: str) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for path in main_vocab_progress_paths(username):
        if not path.is_file():
            continue
        try:
            for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
                item = parse_main_vocab_progress_line(raw)
                key = vocab_key(item.get("word", ""))
                if not key:
                    continue
                previous = rows.get(key, {})
                if max(0, space_w_int(item.get("count", 0), 0)) >= max(0, space_w_int(previous.get("count", 0), 0)):
                    rows[key] = item
        except Exception:
            continue
    return rows


def read_main_learned_qmv_items(username: str) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for root in main_vocab_learned_roots(username):
        if not root.is_dir():
            continue
        try:
            qmv_files = sorted(root.rglob("*.qmv"), key=lambda item: (item.stat().st_mtime, str(item).lower()))
        except Exception:
            qmv_files = []
        for path in qmv_files:
            try:
                for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
                    item = parse_main_qmv_vocab_line(raw)
                    key = vocab_key(item.get("word", ""))
                    if key:
                        item["source_path"] = str(path)
                        rows[key] = {**rows.get(key, {}), **{k: v for k, v in item.items() if clean(v)}}
            except Exception:
                continue
    return rows


def collect_main_vocab_items(username: str) -> list[dict]:
    progress_items = read_main_vocab_progress_items(username)
    qmv_items = read_main_learned_qmv_items(username)
    merged: dict[str, dict] = {}
    for key, item in progress_items.items():
        merged[key] = {
            "word": clean(item.get("word", "")) or key,
            "count": max(1, space_w_int(item.get("count", 1), 1)),
            "last": main_vocab_time_text(item.get("last", "")) if clean(item.get("last", "")) else "",
        }
    for key, item in qmv_items.items():
        previous = merged.get(key, {"word": key})
        merged[key] = {
            "word": clean(item.get("word", "")) or clean(previous.get("word", "")) or key,
            "meaning": clean(item.get("meaning", "")) or clean(previous.get("meaning", "")),
            "pron": clean(item.get("pron", "")) or clean(previous.get("pron", "")),
            "type": clean(item.get("type", "")) or clean(previous.get("type", "")),
            "count": max(1, space_w_int(previous.get("count", item.get("count", 1)), 1)),
            "last": clean(previous.get("last", "")) or (main_vocab_time_text(item.get("last", "")) if clean(item.get("last", "")) else ""),
        }
    return [item for item in merged.values() if vocab_key(item.get("word", ""))]


def sync_future_vocab_registry_to_main_progress(username: str, reconcile_qmdict: bool = True) -> dict:
    username = normalize_username(username)
    if not username:
        return {"updated": 0, "total": 0}
    if reconcile_qmdict:
        try:
            reconcile_user_vocab_registry_with_qmdict(username, write=True)
        except Exception as exc:
            stt_debug_log("main_vocab_progress_qmdict_reconcile_failed", user=username, error=str(exc))
    registry = read_user_vocab_registry(username)
    words = registry.get("words") if isinstance(registry.get("words"), dict) else {}
    if not words:
        return {"updated": 0, "total": 0}
    existing = {}
    updated = 0
    for key, item in words.items():
        safe_key = vocab_key(item.get("word") or key)
        if not safe_key:
            continue
        previous = existing.get(safe_key, {})
        previous_count = max(0, space_w_int(previous.get("count", 0), 0))
        next_count = max(previous_count, max(1, space_w_int(item.get("count", 1), 1)))
        if previous_count != next_count or safe_key not in existing:
            updated += 1
        existing[safe_key] = {
            "word": safe_key,
            "count": next_count,
            "last": main_vocab_time_text(item.get("last", "")),
        }
    if not updated:
        return {"updated": 0, "total": len(existing)}
    try:
        lines = [format_main_vocab_progress_line(item.get("word", key), item.get("count", 1), item.get("last", "")) for key, item in sorted(existing.items())]
        written = 0
        for path in main_vocab_progress_paths(username):
            path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(path, "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
            written += 1
    except Exception as exc:
        stt_debug_log("main_vocab_progress_sync_failed", user=username, error=str(exc))
        return {"updated": 0, "total": len(existing), "error": str(exc)}
    return {"updated": updated, "total": len(existing), "files": written}


def sync_main_vocabulary_for_user(username: str, force: bool = False) -> dict:
    username = normalize_username(username)
    if not username:
        return {"synced": False}
    now = time.time()
    with MAIN_VOCAB_SYNC_LOCK:
        state = MAIN_VOCAB_SYNC_STATE.get(username, {})
        if not force and now - float(state.get("at", 0) or 0) < MAIN_VOCAB_SYNC_MIN_SECONDS:
            return dict(state.get("result", {"synced": False, "throttled": True}))
        MAIN_VOCAB_SYNC_STATE[username] = {"at": now, "result": {"synced": False, "running": True}}
    try:
        items = collect_main_vocab_items(username)
        forward = record_user_vocabulary_items(
            username,
            items,
            "QMLearn main vocabulary",
            increment_count=False,
            sync_main=False,
            record_period_activity=False,
            verify_registry=False,
            enrich_qmdict=False,
        ) if items else {"learned_words": 0, "total_words": len(read_user_vocab_registry(username).get("words", {}) or {})}
        reverse = sync_future_vocab_registry_to_main_progress(username, reconcile_qmdict=False)
        result = {
            "synced": True,
            "main_items": len(items),
            "future_total": max(0, space_w_int(forward.get("total_words", 0), 0)),
            "main_progress_updated": max(0, space_w_int(reverse.get("updated", 0), 0)),
        }
    except Exception as exc:
        result = {"synced": False, "error": str(exc)}
        stt_debug_log("main_vocab_sync_failed", user=username, error=str(exc))
    with MAIN_VOCAB_SYNC_LOCK:
        MAIN_VOCAB_SYNC_STATE[username] = {"at": time.time(), "result": result}
    return result


# Added 2026-07-06: keeps test/internal folders out of periodic main-vocab sync scans.
def main_vocab_sync_candidate_allowed(username: str = "") -> bool:
    username = normalize_username(username)
    if not username:
        return False
    lowered = username.lower()
    if lowered in {"admin", "default", "server", "testuser"}:
        return False
    if lowered.startswith(("codex", "test", "perf")):
        return False
    ok, _message = validate_username(username)
    return bool(ok)


def main_vocab_candidate_usernames() -> list[str]:
    names: set[str] = set()
    roots = [USER_ROOT, MAIN_SERVER_USER_ROOT]
    suffix = "_vocab_progress"
    for root in roots:
        try:
            if not root.exists():
                continue
        except Exception:
            continue
        try:
            for path in root.rglob("*_vocab_progress.txt"):
                raw = path.stem
                username = raw[:-len(suffix)] if raw.lower().endswith(suffix) else raw
                username = normalize_username(username)
                if main_vocab_sync_candidate_allowed(username):
                    names.add(username)
        except Exception:
            pass
        try:
            for folder in root.iterdir():
                if not folder.is_dir():
                    continue
                if folder.name.startswith("_"):
                    continue
                raw_name = folder.name
                if root == MAIN_SERVER_USER_ROOT:
                    identity_path = folder / "_user_identity.json"
                    try:
                        identity = json.loads(identity_path.read_text(encoding="utf-8-sig", errors="replace")) if identity_path.is_file() else {}
                    except Exception:
                        identity = {}
                    raw_name = clean(identity.get("username", "")) if isinstance(identity, dict) else ""
                    if not raw_name:
                        raw_name = folder.name.split("__", 1)[0] if "__" in folder.name else folder.name
                username = normalize_username(raw_name)
                if main_vocab_sync_candidate_allowed(username) and not username.startswith("_"):
                    names.add(username)
        except Exception:
            pass
        try:
            for user_file in root.glob("*.txt"):
                stem = clean(user_file.stem)
                if not stem or stem.lower().endswith("_vocab_progress") or stem.startswith("_"):
                    continue
                username = normalize_username(stem)
                if main_vocab_sync_candidate_allowed(username):
                    names.add(username)
        except Exception:
            pass
    return sorted(names, key=str.lower)


def sync_all_main_vocabularies(force: bool = False, reason: str = "") -> dict:
    started = utc_timestamp()
    usernames = main_vocab_candidate_usernames()
    rows = []
    synced = 0
    failed = 0
    for username in usernames:
        try:
            result = sync_main_vocabulary_for_user(username, force=force)
            rows.append({"user": username, **(result if isinstance(result, dict) else {})})
            if result.get("synced"):
                synced += 1
        except Exception as exc:
            failed += 1
            rows.append({"user": username, "synced": False, "error": str(exc)})
    payload = {
        "started_at": started,
        "finished_at": utc_timestamp(),
        "reason": clean(reason),
        "users": len(usernames),
        "synced": synced,
        "failed": failed,
        "rows": rows[-200:],
    }
    with MAIN_VOCAB_SYNC_LOCK:
        MAIN_VOCAB_SYNC_ALL_STATE["last"] = payload["finished_at"]
        MAIN_VOCAB_SYNC_ALL_STATE["last_result"] = payload
    return payload


def sync_pushed_main_vocabularies(payload: dict, reason: str = "") -> dict:
    source = payload if isinstance(payload, dict) else {}
    rows = source.get("users") if isinstance(source.get("users"), list) else []
    started = utc_timestamp()
    results = []
    accepted = 0
    rejected = 0
    total_words = 0
    for row in rows[:80]:
        if not isinstance(row, dict):
            continue
        username = normalize_username(row.get("username", ""))
        password = str(row.get("password", "") or "")
        if not username or not password:
            rejected += 1
            results.append({"user": username, "ok": False, "reason": "missing_credentials"})
            continue
        ok, auth_reason, _profile = check_user_login(username, password)
        if not ok:
            rejected += 1
            results.append({"user": username, "ok": False, "reason": auth_reason})
            continue
        raw_words = row.get("words") if isinstance(row.get("words"), list) else []
        words = []
        seen = set()
        for item in raw_words[:20000]:
            normalized = normalize_vocabulary_registry_item(item)
            key = vocab_key(normalized.get("word", ""))
            if key and key not in seen:
                seen.add(key)
                words.append(normalized)
        if not words:
            results.append({"user": username, "ok": True, "words": 0, "synced": False})
            continue
        try:
            result = record_user_vocabulary_items(
                username,
                words,
                clean(row.get("source", "")) or "QMLearn remote offline push",
                increment_count=False,
                sync_main=True,
                record_period_activity=False,
                verify_registry=False,
                enrich_qmdict=False,
            )
            accepted += 1
            total_words += len(words)
            results.append({
                "user": username,
                "ok": True,
                "words": len(words),
                "added": int(result.get("added", 0) or 0),
                "updated": int(result.get("updated", 0) or 0),
                "total_words": int(result.get("total_words", 0) or 0),
            })
        except Exception as exc:
            rejected += 1
            results.append({"user": username, "ok": False, "reason": str(exc)})
    return {
        "started_at": started,
        "finished_at": utc_timestamp(),
        "reason": clean(reason),
        "machine": clean(source.get("machine", ""))[:120],
        "users": len(rows),
        "accepted": accepted,
        "rejected": rejected,
        "words": total_words,
        "rows": results[-200:],
    }


def start_pushed_main_vocab_sync(payload: dict, reason: str = "") -> dict:
    source = payload if isinstance(payload, dict) else {}
    user_count = len(source.get("users")) if isinstance(source.get("users"), list) else 0
    if user_count <= 0:
        return {"queued": False, "running": False, "users": 0}

    def _worker() -> None:
        try:
            result = sync_pushed_main_vocabularies(source, reason=reason)
            stt_debug_log(
                "main_vocab_remote_push_done",
                users=result.get("users", 0),
                accepted=result.get("accepted", 0),
                rejected=result.get("rejected", 0),
                words=result.get("words", 0),
                reason=reason,
            )
        except Exception as exc:
            stt_debug_log("main_vocab_remote_push_failed", error=str(exc), reason=reason)

    thread = threading.Thread(target=_worker, daemon=True, name="main-vocab-remote-push")
    thread.start()
    return {"queued": True, "running": True, "users": user_count, "reason": clean(reason)}


def start_main_vocab_sync_user(username: str, force: bool = False, reason: str = "", delay_seconds: float = 8.0) -> dict:
    username = normalize_username(username)
    if not username:
        return {"queued": False, "running": False, "user": ""}
    now = time.time()
    sync_reason = clean(reason)
    min_seconds = MAIN_VOCAB_LOGIN_SYNC_MIN_SECONDS if sync_reason == "future-login" else MAIN_VOCAB_SYNC_MIN_SECONDS
    with MAIN_VOCAB_SYNC_LOCK:
        state = MAIN_VOCAB_SYNC_STATE.get(username, {})
        result = state.get("result") if isinstance(state.get("result"), dict) else {}
        if not force and (
            bool(result.get("running"))
            or bool(result.get("scheduled"))
            or now - float(state.get("at", 0) or 0) < min_seconds
        ):
            return {"queued": False, "running": bool(result.get("running")), "scheduled": bool(result.get("scheduled")), "user": username, "reason": sync_reason}
        MAIN_VOCAB_SYNC_STATE[username] = {"at": now, "result": {"synced": False, "scheduled": True}}

    def _worker() -> None:
        try:
            if delay_seconds > 0:
                time.sleep(max(0.0, float(delay_seconds)))
            with MAIN_VOCAB_SYNC_LOCK:
                MAIN_VOCAB_SYNC_STATE[username] = {"at": now, "result": {"synced": False, "running": True, "scheduled": False}}
            result = sync_main_vocabulary_for_user(username, force=force)
            with MAIN_VOCAB_SYNC_LOCK:
                MAIN_VOCAB_SYNC_STATE[username] = {"at": time.time(), "result": dict(result or {}, running=False, scheduled=False)}
            stt_debug_log(
                "main_vocab_sync_user_done",
                user=username,
                synced=result.get("synced", False) if isinstance(result, dict) else False,
                  main_items=result.get("main_items", 0) if isinstance(result, dict) else 0,
                  future_total=result.get("future_total", 0) if isinstance(result, dict) else 0,
                  reason=sync_reason,
              )
        except Exception as exc:
            stt_debug_log("main_vocab_sync_user_failed", user=username, error=str(exc), reason=sync_reason)

    thread = threading.Thread(target=_worker, daemon=True, name=f"main-vocab-sync-{username[:24]}")
    thread.start()
    return {"queued": True, "running": False, "scheduled": True, "delay_seconds": max(0.0, float(delay_seconds)), "user": username, "reason": sync_reason}


def start_main_vocab_sync_all(force: bool = False, reason: str = "") -> dict:
    with MAIN_VOCAB_SYNC_LOCK:
        if MAIN_VOCAB_SYNC_ALL_STATE.get("running"):
            return {
                "queued": False,
                "running": True,
                "last_result": MAIN_VOCAB_SYNC_ALL_STATE.get("last_result", {}),
            }
        MAIN_VOCAB_SYNC_ALL_STATE["running"] = True

    def _worker() -> None:
        try:
            result = sync_all_main_vocabularies(force=force, reason=reason)
            stt_debug_log("main_vocab_sync_all_done", users=result.get("users", 0), synced=result.get("synced", 0), failed=result.get("failed", 0), reason=reason)
        except Exception as exc:
            stt_debug_log("main_vocab_sync_all_failed", error=str(exc), reason=reason)
        finally:
            with MAIN_VOCAB_SYNC_LOCK:
                MAIN_VOCAB_SYNC_ALL_STATE["running"] = False

    thread = threading.Thread(target=_worker, daemon=True, name="main-vocab-sync-all")
    thread.start()
    return {"queued": True, "running": True, "reason": clean(reason)}


def start_main_vocab_sync_monitor() -> None:
    def _loop() -> None:
        time.sleep(3.0)
        start_main_vocab_sync_all(force=False, reason="startup")
        while True:
            time.sleep(90.0)
            start_main_vocab_sync_all(force=False, reason="periodic")

    thread = threading.Thread(target=_loop, daemon=True, name="main-vocab-sync-monitor")
    thread.start()
