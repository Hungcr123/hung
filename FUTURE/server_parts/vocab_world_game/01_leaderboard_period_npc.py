# Loaded by FUTURE.server_parts.09_vocab_world_game into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def _merge_vocab_leaderboard_period_scope_row(existing: object, incoming: object) -> dict:
    current = existing if isinstance(existing, dict) else {}
    source = incoming if isinstance(incoming, dict) else {}
    current_bucket = clean(current.get("bucket", ""))
    source_bucket = clean(source.get("bucket", ""))
    current_updated = clean(current.get("updated_at", current.get("updatedAt", "")))
    source_updated = clean(source.get("updated_at", source.get("updatedAt", "")))
    if current_bucket and source_bucket and current_bucket != source_bucket:
        preferred = source if timestamp_order_key(source_updated) >= timestamp_order_key(current_updated) else current
        words = preferred.get("words") if isinstance(preferred.get("words"), dict) else {}
        return {
            "bucket": clean(preferred.get("bucket", "")),
            "words": {clean(key): clean(value) for key, value in words.items() if clean(key) and clean(value)},
            "updated_at": clean(preferred.get("updated_at", preferred.get("updatedAt", ""))),
        }
    bucket = source_bucket or current_bucket
    words = {}
    for row in (current, source):
        row_words = row.get("words") if isinstance(row.get("words"), dict) else {}
        for raw_key, raw_value in row_words.items():
            key = clean(raw_key)
            stamp = clean(raw_value)
            if key and stamp and timestamp_order_key(stamp) >= timestamp_order_key(words.get(key, "")):
                words[key] = stamp
    updated_at = source_updated if timestamp_order_key(source_updated) >= timestamp_order_key(current_updated) else current_updated
    if not bucket and not words and not updated_at:
        return {}
    return {"bucket": bucket, "words": words, "updated_at": updated_at}

def _clean_vocab_leaderboard_period_users(value: object) -> dict:
    source = value if isinstance(value, dict) else {}
    users = {}
    for raw_username, raw_row in source.items():
        username = normalize_username(raw_username)
        if not username or not isinstance(raw_row, dict):
            continue
        current = users.get(username, {})
        merged = {}
        for scope in ("day", "week", "month"):
            scope_row = _merge_vocab_leaderboard_period_scope_row(current.get(scope), raw_row.get(scope))
            if scope_row:
                merged[scope] = scope_row
        users[username] = merged
    return users

VOCAB_LEADERBOARD_PERIOD_STATE_RAM_CACHE: dict[str, object] = {"stamp": (), "state": {}}
VOCAB_LEADERBOARD_NPC_TOP_STATE_RAM_CACHE: dict[str, object] = {"stamp": (), "state": {}}
VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_LOCK = threading.Lock()
VOCAB_LEADERBOARD_PERIOD_DISK_WRITE_LOCK = threading.Lock()
VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_DELAY_SECONDS = 0.15
VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_STATE: dict[str, object] = {
    "version": 0,
    "pending": None,
    "timer": None,
    "writing": False,
}


def _leaderboard_state_file_stamp(path: Path) -> tuple:
    if server_database_document_local_only(path):
        _resolved, mtime_ns, size, _sha256 = server_database_document_signature(path)
        return (mtime_ns, size)
    try:
        stat = path.stat()
        return (int(stat.st_mtime_ns), int(stat.st_size))
    except Exception:
        return (0, 0)


# Added 2026-07-20: SQLite period rows use the database generation; avoid resolving and hashing a retired JSON document on every read.
def _vocab_leaderboard_period_cache_stamp() -> tuple:
    if server_database_document_local_only(VOCAB_LEADERBOARD_PERIOD_FILE):
        return (0, 0)
    return _leaderboard_state_file_stamp(VOCAB_LEADERBOARD_PERIOD_FILE)


# Added 2026-07-30: PostgreSQL period rows supersede the retired JSONL recovery WAL.
def vocab_leaderboard_period_legacy_wal_enabled() -> bool:
    return postgres_backend_mode("VOCABULARY") != "postgres"


def _apply_vocab_leaderboard_period_wal(state: dict) -> dict:
    if not vocab_leaderboard_period_legacy_wal_enabled():
        clear_vocab_leaderboard_period_wal()
        return state
    if not VOCAB_LEADERBOARD_PERIOD_WAL_FILE.is_file():
        return state
    users = state.setdefault("users", {})
    try:
        lines = VOCAB_LEADERBOARD_PERIOD_WAL_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return state
    for line in lines:
        try:
            row = json.loads(line)
        except Exception:
            continue
        username = normalize_username(row.get("user", "")) if isinstance(row, dict) else ""
        scopes = row.get("scopes") if isinstance(row, dict) and isinstance(row.get("scopes"), dict) else {}
        if not username or not scopes:
            continue
        user_row = users.setdefault(username, {})
        for scope in ("day", "week", "month"):
            incoming = scopes.get(scope)
            if isinstance(incoming, dict):
                merged = _merge_vocab_leaderboard_period_scope_row(user_row.get(scope), incoming)
                if merged:
                    user_row[scope] = merged
        state["updated_at"] = normalize_timestamp_text(row.get("at", state.get("updated_at", "")))
    return state


def append_vocab_leaderboard_period_wal(username: str, scopes: dict, stamp: str) -> bool:
    if not vocab_leaderboard_period_legacy_wal_enabled():
        clear_vocab_leaderboard_period_wal()
        return False
    if not username or not isinstance(scopes, dict) or not scopes:
        return False
    SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {"v": 1, "at": normalize_timestamp_text(stamp, fallback_now=True), "user": username, "scopes": scopes}
    encoded = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    with VOCAB_LEADERBOARD_PERIOD_WAL_FILE.open("ab") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    return True


def clear_vocab_leaderboard_period_wal() -> None:
    try:
        VOCAB_LEADERBOARD_PERIOD_WAL_FILE.unlink(missing_ok=True)
    except Exception:
        if postgres_backend_mode("VOCABULARY") == "postgres":
            raise


def load_vocab_leaderboard_period_state(clone: bool = True) -> dict:
    try:
        stamp = _vocab_leaderboard_period_cache_stamp()
        database_generation_getter = globals().get("server_database_generation")
        database_generation = database_generation_getter("period") if callable(database_generation_getter) else 0
        cached = VOCAB_LEADERBOARD_PERIOD_STATE_RAM_CACHE.get("state")
        if stamp == VOCAB_LEADERBOARD_PERIOD_STATE_RAM_CACHE.get("stamp") and database_generation == VOCAB_LEADERBOARD_PERIOD_STATE_RAM_CACHE.get("database_generation") and isinstance(cached, dict) and cached:
            return clone_vocab_leaderboard_payload(cached) if clone else cached
        resets_loader = globals().get("server_database_load_period_resets")
        resets = resets_loader() if callable(resets_loader) else {}
        state = _apply_vocab_leaderboard_period_wal({"version": 1, "updated_at": "", "resets": resets, "users": {}})
        database_overlay = globals().get("server_database_overlay_period_state")
        if callable(database_overlay):
            state = database_overlay(state)
        VOCAB_LEADERBOARD_PERIOD_STATE_RAM_CACHE["stamp"] = stamp
        VOCAB_LEADERBOARD_PERIOD_STATE_RAM_CACHE["database_generation"] = database_generation
        VOCAB_LEADERBOARD_PERIOD_STATE_RAM_CACHE["state"] = state
        return clone_vocab_leaderboard_payload(state) if clone else state
    except Exception:
        if postgres_backend_mode("VOCABULARY") == "postgres":
            raise
    state = _apply_vocab_leaderboard_period_wal({"version": 1, "updated_at": "", "resets": {}, "users": {}})
    database_overlay = globals().get("server_database_overlay_period_state")
    state = database_overlay(state) if callable(database_overlay) else state
    return clone_vocab_leaderboard_payload(state) if clone else state


# Added 2026-07-29: apply a committed vocabulary delta without reloading every user's period rows.
def patch_vocab_leaderboard_period_state_from_delta(
    username: str,
    buckets: dict,
    word_keys: list[str] | tuple[str, ...],
    stamp: str,
) -> dict:
    username = normalize_username(username)
    normalized_keys = sorted({vocab_key(value) for value in word_keys if vocab_key(value)})
    now_stamp = normalize_timestamp_text(stamp, fallback_now=True)
    current_generation_getter = globals().get("server_database_generation")
    current_generation = int(current_generation_getter("period") or 0) if callable(current_generation_getter) else 0
    cached_generation = int(VOCAB_LEADERBOARD_PERIOD_STATE_RAM_CACHE.get("database_generation", 0) or 0)
    cached = VOCAB_LEADERBOARD_PERIOD_STATE_RAM_CACHE.get("state")
    can_patch_shared_cache = bool(
        isinstance(cached, dict)
        and cached
        and current_generation <= cached_generation + 1
    )
    state = cached if can_patch_shared_cache else {
        "version": 1,
        "updated_at": now_stamp,
        "resets": {},
        "users": {},
    }
    users = state.setdefault("users", {})
    user_row = vocab_leaderboard_period_user_row(users, username, create=True)
    for scope in ("day", "week", "month"):
        bucket = clean(buckets.get(scope, ""))
        if not bucket:
            continue
        scope_row = user_row.get(scope) if isinstance(user_row.get(scope), dict) else {}
        if clean(scope_row.get("bucket", "")) != bucket:
            scope_row = {"bucket": bucket, "words": {}, "updated_at": ""}
        words = scope_row.setdefault("words", {})
        for key in normalized_keys:
            words.setdefault(key, now_stamp)
        scope_row["updated_at"] = timestamp_latest_text(scope_row.get("updated_at", ""), now_stamp)
        user_row[scope] = scope_row
    state["updated_at"] = timestamp_latest_text(state.get("updated_at", ""), now_stamp)
    if can_patch_shared_cache:
        VOCAB_LEADERBOARD_PERIOD_STATE_RAM_CACHE["database_generation"] = current_generation
        VOCAB_LEADERBOARD_PERIOD_STATE_RAM_CACHE["state"] = state
    return state


def write_vocab_leaderboard_period_state(state: dict) -> None:
    payload = {
        "version": 1,
        "updated_at": utc_timestamp(),
        "resets": state.get("resets") if isinstance(state.get("resets"), dict) else {},
        "users": _clean_vocab_leaderboard_period_users(state.get("users")),
    }
    resets_writer = globals().get("server_database_store_period_resets")
    if not callable(resets_writer):
        raise RuntimeError("Vocabulary period database writer is unavailable; JSON fallback is disabled.")
    resets_writer(payload.get("resets"))
    VOCAB_LEADERBOARD_PERIOD_STATE_RAM_CACHE["stamp"] = _vocab_leaderboard_period_cache_stamp()
    VOCAB_LEADERBOARD_PERIOD_STATE_RAM_CACHE["state"] = payload


# Added 2026-07-19: one write-behind worker absorbs completion bursts and always persists the newest snapshot.
def _flush_vocab_leaderboard_period_state_worker() -> None:
    while True:
        with VOCAB_LEADERBOARD_PERIOD_LOCK:
            with VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_LOCK:
                snapshot = VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_STATE.get("pending")
                VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_STATE["pending"] = None
                VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_STATE["timer"] = None
                if not isinstance(snapshot, dict):
                    VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_STATE["writing"] = False
                    return
                VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_STATE["writing"] = True
            with VOCAB_LEADERBOARD_PERIOD_DISK_WRITE_LOCK:
                write_vocab_leaderboard_period_state(snapshot)
                clear_vocab_leaderboard_period_wal()
            with VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_LOCK:
                if not isinstance(VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_STATE.get("pending"), dict):
                    VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_STATE["writing"] = False
                    return


def write_vocab_leaderboard_period_state_async(state: dict) -> None:
    if not isinstance(state, dict):
        return
    snapshot = clone_vocab_leaderboard_payload(state)
    VOCAB_LEADERBOARD_PERIOD_STATE_RAM_CACHE["stamp"] = _vocab_leaderboard_period_cache_stamp()
    VOCAB_LEADERBOARD_PERIOD_STATE_RAM_CACHE["state"] = snapshot
    with VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_LOCK:
        VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_STATE["version"] = int(VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_STATE.get("version", 0) or 0) + 1
        VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_STATE["pending"] = snapshot
        timer = VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_STATE.get("timer")
        if bool(VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_STATE.get("writing")) or (timer and timer.is_alive()):
            return
        timer = threading.Timer(VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_DELAY_SECONDS, _flush_vocab_leaderboard_period_state_worker)
        timer.daemon = True
        VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_STATE["timer"] = timer
        timer.start()


def flush_vocab_leaderboard_period_state(force: bool = False) -> bool:
    with VOCAB_LEADERBOARD_PERIOD_LOCK:
        with VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_LOCK:
            timer = VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_STATE.get("timer")
            if timer and timer.is_alive():
                timer.cancel()
            VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_STATE["timer"] = None
            snapshot = VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_STATE.get("pending")
            VOCAB_LEADERBOARD_PERIOD_ASYNC_WRITE_STATE["pending"] = None
        if not isinstance(snapshot, dict):
            return False
        with VOCAB_LEADERBOARD_PERIOD_DISK_WRITE_LOCK:
            write_vocab_leaderboard_period_state(snapshot)
            clear_vocab_leaderboard_period_wal()
        return True


def recover_vocab_leaderboard_period_wal_async() -> dict:
    if not VOCAB_LEADERBOARD_PERIOD_WAL_FILE.is_file():
        return {"scheduled": False}
    with VOCAB_LEADERBOARD_PERIOD_LOCK:
        state = load_vocab_leaderboard_period_state()
        write_vocab_leaderboard_period_state_async(state)
    return {"scheduled": True}


def npc_top_username_from_stt(stt: str = "") -> str:
    value = re.sub(r"\D+", "", clean(stt))[:8]
    return f"npc{value}" if value else ""


def npc_top_browser_image_path(path: Path) -> Path:
    try:
        source = Path(path)
        if not source.is_file() or source.suffix.lower() not in NPC_TOP_IMAGE_SUFFIXES:
            return source
        if source.suffix.lower() in NPC_TOP_BROWSER_IMAGE_SUFFIXES:
            return source
        target = source.with_suffix(".webp")
        try:
            if target.is_file() and target.stat().st_mtime >= source.stat().st_mtime and target.stat().st_size > 0:
                return target
        except Exception:
            pass
        try:
            from PIL import Image, ImageOps  # noqa: PLC0415
            with Image.open(source) as image:
                image = ImageOps.exif_transpose(image)
                if image.mode not in {"RGB", "RGBA"}:
                    image = image.convert("RGBA" if "A" in image.mode else "RGB")
                target.parent.mkdir(parents=True, exist_ok=True)
                image.save(target, "WEBP", quality=92, method=4)
            return target if target.is_file() else source
        except Exception:
            if source.suffix.lower() == ".jfif":
                fallback = source.with_suffix(".jpg")
                try:
                    if not fallback.is_file() or fallback.stat().st_mtime < source.stat().st_mtime:
                        shutil.copy2(source, fallback)
                    return fallback if fallback.is_file() else source
                except Exception:
                    return source
            return source
    except Exception:
        return Path(path)


def ensure_npc_top_browser_images() -> dict:
    converted = 0
    checked = 0
    failed = 0
    try:
        if not NPC_TOP_DIR.is_dir():
            return {"checked": 0, "converted": 0, "failed": 0}
        for path in NPC_TOP_DIR.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in NPC_TOP_IMAGE_SUFFIXES:
                continue
            checked += 1
            try:
                browser_path = npc_top_browser_image_path(path)
                if browser_path != path and browser_path.is_file():
                    converted += 1
            except Exception:
                failed += 1
    except Exception:
        failed += 1
    return {"checked": checked, "converted": converted, "failed": failed}


def parse_npc_top_image(path: Path) -> dict:
    try:
        if not path.is_file() or path.suffix.lower() not in NPC_TOP_IMAGE_SUFFIXES:
            return {}
        browser_path = npc_top_browser_image_path(path)
        stem = str(path.stem or "").replace("\u00a0", " ").strip(" _-.")
        match = re.match(r"^(\d{1,8})[\s_\-]+(.+)$", stem, flags=re.UNICODE)
        if not match:
            return {}
        stt = match.group(1)
        name_part = match.group(2).strip(" _-.")
        parts = [clean(part) for part in name_part.split("_") if clean(part)]
        login_alias = ""
        gender = "other"
        if parts:
            gender_token = clean(parts[-1]).lower()
            gender_map = {
                "male": "male",
                "man": "male",
                "nam": "male",
                "boy": "male",
                "female": "female",
                "woman": "female",
                "nu": "female",
                "nữ": "female",
                "girl": "female",
                "other": "other",
            }
            if gender_token in gender_map:
                gender = gender_map[gender_token]
                parts = parts[:-1]
        if len(parts) >= 2 and re.match(r"^[A-Za-z][A-Za-z0-9]{1,31}$", parts[0]):
            login_alias = parts[0]
            display_source = " ".join(parts[1:])
        else:
            display_source = " ".join(parts) if parts else name_part.replace("_", " ")
        display_name = clean(display_source).strip(" _-.")[:120]
        if not display_name or not any(ch.isalpha() for ch in display_name):
            return {}
        username = npc_top_username_from_stt(stt)
        if not username:
            return {}
        relative = browser_path.relative_to(SERVER_DATA_ROOT).as_posix()
        stat = path.stat()
        return {
            "username": username,
            "stt": stt,
            "display_name": display_name,
            "full_name": display_name,
            "gender": gender,
            "avatar": relative,
            "login_alias": login_alias,
            "source_name": path.name,
            "source_mtime": float(stat.st_mtime),
            "source_size": int(stat.st_size),
        }
    except Exception:
        return {}


NPC_TOP_MANIFEST_RAM_CACHE: dict[str, object] = {"at": 0.0, "payload": {}}
NPC_TOP_MANIFEST_RAM_CACHE_TTL_SECONDS = 60.0


def npc_top_manifest() -> dict[str, dict]:
    cached_payload = NPC_TOP_MANIFEST_RAM_CACHE.get("payload")
    if (
        isinstance(cached_payload, dict)
        and time.time() - float(NPC_TOP_MANIFEST_RAM_CACHE.get("at", 0.0) or 0.0) <= NPC_TOP_MANIFEST_RAM_CACHE_TTL_SECONDS
    ):
        return clone_vocab_leaderboard_payload(cached_payload)
    entries: dict[str, dict] = {}
    try:
        if not NPC_TOP_DIR.is_dir():
            return entries
        ensure_npc_top_browser_images()
        for path in sorted(NPC_TOP_DIR.rglob("*"), key=lambda item: str(item.relative_to(NPC_TOP_DIR)).lower()):
            row = parse_npc_top_image(path)
            username = normalize_username(row.get("username", "")) if row else ""
            if not username:
                continue
            previous = entries.get(username)
            if previous and float(previous.get("source_mtime", 0) or 0) >= float(row.get("source_mtime", 0) or 0):
                continue
            entries[username] = row
    except Exception:
        return entries
    NPC_TOP_MANIFEST_RAM_CACHE["at"] = time.time()
    NPC_TOP_MANIFEST_RAM_CACHE["payload"] = clone_vocab_leaderboard_payload(entries)
    return entries


def load_vocab_leaderboard_npc_top_state() -> dict:
    try:
        stamp = _leaderboard_state_file_stamp(VOCAB_LEADERBOARD_NPC_TOP_FILE)
        cached = VOCAB_LEADERBOARD_NPC_TOP_STATE_RAM_CACHE.get("state")
        if stamp == VOCAB_LEADERBOARD_NPC_TOP_STATE_RAM_CACHE.get("stamp") and isinstance(cached, dict) and cached:
            return clone_vocab_leaderboard_payload(cached)
        payload = server_database_read_document_json(VOCAB_LEADERBOARD_NPC_TOP_FILE, {})
        if isinstance(payload, dict):
            npcs = payload.get("npcs") if isinstance(payload.get("npcs"), dict) else {}
            state = {
                "version": 1,
                "updated_at": clean(payload.get("updated_at", "")),
                "npcs": {normalize_username(key): value for key, value in npcs.items() if normalize_username(key) and isinstance(value, dict)},
            }
            VOCAB_LEADERBOARD_NPC_TOP_STATE_RAM_CACHE["stamp"] = stamp
            VOCAB_LEADERBOARD_NPC_TOP_STATE_RAM_CACHE["state"] = clone_vocab_leaderboard_payload(state)
            return state
    except Exception:
        if postgres_backend_mode("LEADERBOARD_DOCUMENTS") == "postgres":
            raise
    return {"version": 1, "updated_at": "", "npcs": {}}


def write_vocab_leaderboard_npc_top_state(state: dict) -> None:
    SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": utc_timestamp(),
        "npcs": state.get("npcs") if isinstance(state.get("npcs"), dict) else {},
    }
    atomic_write_json(VOCAB_LEADERBOARD_NPC_TOP_FILE, payload, indent=2)
    VOCAB_LEADERBOARD_NPC_TOP_STATE_RAM_CACHE["stamp"] = _leaderboard_state_file_stamp(VOCAB_LEADERBOARD_NPC_TOP_FILE)
    VOCAB_LEADERBOARD_NPC_TOP_STATE_RAM_CACHE["state"] = clone_vocab_leaderboard_payload(payload)


def npc_top_profile_for_user(username: str = "") -> dict:
    username = normalize_username(username)
    if not username or not re.match(r"^npc\d{1,8}$", username, flags=re.IGNORECASE):
        return {}
    # A real registered account wins: never treat a human learner as an NPC racer,
    # even if their username happens to match the npc<digits> pattern.
    try:
        if callable(globals().get("server_database_user_exists")) and server_database_user_exists(username):
            return {}
    except Exception:
        pass
    manifest = npc_top_manifest()
    row = manifest.get(username)
    if not isinstance(row, dict):
        try:
            state = load_vocab_leaderboard_npc_top_state()
            row = (state.get("npcs") if isinstance(state.get("npcs"), dict) else {}).get(username)
        except Exception:
            row = {}
    if not isinstance(row, dict):
        return {}
    display_name = clean(row.get("display_name") or row.get("full_name") or "")
    avatar = clean(row.get("avatar", ""))
    gender = clean(row.get("gender", "")).lower()
    if gender not in {"male", "female", "other"}:
        gender = "other"
    if not display_name or not avatar:
        return {}
    return {
        "username": username,
        "full_name": display_name,
        "gender": gender,
        "birth_date": "",
        "avatar": avatar,
        "login_alias": clean(row.get("login_alias", "")),
        "intro": "A simulated QM vocabulary racer.",
        "profile_photos": [avatar],
        "updated_at": clean(row.get("updated_at", "")) or clean(row.get("source_name", "")),
        "npc": True,
    }


def npc_top_rng(username: str, day_key: str) -> random.Random:
    seed = hashlib.sha256(f"npc-top|{normalize_username(username)}|{clean(day_key)}".encode("utf-8", errors="ignore")).hexdigest()
    return random.Random(int(seed[:16], 16))


def npc_top_split_words(rng: random.Random, session_count: int, total_words: int) -> list[int]:
    result: list[int] = []
    remaining = max(0, int(total_words or 0))
    count = max(1, min(3, int(session_count or 1)))
    for index in range(count):
        slots_left = count - index - 1
        if slots_left <= 0:
            result.append(max(NPC_TOP_SESSION_MIN_WORDS, min(NPC_TOP_SESSION_MAX_WORDS, remaining)))
            break
        minimum = max(NPC_TOP_SESSION_MIN_WORDS, remaining - (NPC_TOP_SESSION_MAX_WORDS * slots_left))
        maximum = min(NPC_TOP_SESSION_MAX_WORDS, remaining - (NPC_TOP_SESSION_MIN_WORDS * slots_left))
        if minimum > maximum:
            minimum = maximum = max(NPC_TOP_SESSION_MIN_WORDS, min(NPC_TOP_SESSION_MAX_WORDS, remaining // (slots_left + 1)))
        value = rng.randint(int(minimum), int(maximum))
        result.append(value)
        remaining -= value
    return result


def npc_top_session_minutes(rng: random.Random, session_count: int) -> list[int]:
    count = max(1, min(3, int(session_count or 1)))
    gap = max(1, int(NPC_TOP_MIN_SESSION_GAP_MINUTES))
    for _attempt in range(300):
        minutes = sorted(rng.sample(range(0, 24 * 60), count))
        if all((minutes[index] - minutes[index - 1]) >= gap for index in range(1, len(minutes))):
            return minutes
    start = rng.randint(0, max(0, (24 * 60 - 1) - gap * (count - 1)))
    return [min(24 * 60 - 1, start + gap * index) for index in range(count)]


def npc_top_generate_day_sessions(username: str, day_key: str) -> list[dict]:
    rng = npc_top_rng(username, day_key)
    session_count = rng.randint(1, 3)
    minimum_total = max(NPC_TOP_DAILY_TOTAL_MIN, NPC_TOP_SESSION_MIN_WORDS * session_count)
    maximum_total = min(NPC_TOP_DAILY_TOTAL_MAX, NPC_TOP_SESSION_MAX_WORDS * session_count)
    if minimum_total > maximum_total:
        minimum_total = maximum_total
    total_words = rng.randint(int(minimum_total), int(maximum_total))
    words_per_session = npc_top_split_words(rng, session_count, total_words)
    minutes = npc_top_session_minutes(rng, session_count)
    sessions = []
    for index, (minute, words) in enumerate(zip(minutes, words_per_session), 1):
        sessions.append(
            {
                "id": f"{day_key}-{index}",
                "minute": int(minute),
                "words": int(words),
                "total_increment": rng.randint(8, max(8, min(25, int(words)))),
            }
        )
    return sessions


def npc_top_total_words(username: str = "", state: dict | None = None) -> int:
    username = normalize_username(username)
    source = state if isinstance(state, dict) else load_vocab_leaderboard_npc_top_state()
    row = (source.get("npcs") if isinstance(source.get("npcs"), dict) else {}).get(username)
    if not isinstance(row, dict):
        return 0
    return max(0, space_w_int(row.get("total_words", row.get("total", 0)), 0))


def resolve_admin_npc_actor(session_username: str = "", actor_username: object = "") -> str:
    session_username = normalize_username(session_username)
    actor = normalize_username(actor_username)
    if not actor or actor == session_username:
        return session_username
    if is_admin_user(session_username) and npc_top_profile_for_user(actor):
        return actor
    return session_username


def npc_top_public_roster() -> list[dict]:
    try:
        apply_vocab_leaderboard_npc_top_activity()
    except Exception:
        pass
    manifest = npc_top_manifest()
    state = load_vocab_leaderboard_npc_top_state()
    settings = load_server_settings()
    levels = settings.get("qm_city_levels", DEFAULT_QM_CITY_LEVELS)
    rows = []
    for username, entry in manifest.items():
        try:
            if callable(globals().get("server_database_user_exists")) and server_database_user_exists(username):
                continue
        except Exception:
            pass
        profile = npc_top_profile_for_user(username)
        total_words = npc_top_total_words(username, state)
        rows.append(
            {
                "username": username,
                "stt": clean(entry.get("stt", "")),
                "login_alias": clean(entry.get("login_alias", "")),
                "display_name": clean(profile.get("full_name") or entry.get("display_name") or username),
                "gender": clean(profile.get("gender") or entry.get("gender") or "other"),
                "avatar": clean(profile.get("avatar") or entry.get("avatar", "")),
                "total_words": total_words,
                "character_level": qm_city_character_level_for_exp(total_words, levels),
                "source_name": clean(entry.get("source_name", "")),
            }
        )
    rows.sort(key=lambda item: (space_w_int(item.get("stt", 0), 0), clean(item.get("display_name", "")).lower()))
    return rows


def apply_vocab_leaderboard_npc_top_activity(now_epoch: float | None = None) -> dict:
    now_value = time.time() if now_epoch is None else float(now_epoch or time.time())
    manifest = npc_top_manifest()
    if not manifest:
        return {"enabled": False, "npcs": 0, "applied": 0}
    day_key = vocab_period_bucket("day", now_value)
    day_start = float(local_period_starts_epoch().get("day", now_value) or now_value)
    applied_count = 0
    changed = False
    with VOCAB_LEADERBOARD_NPC_TOP_LOCK:
        state = load_vocab_leaderboard_npc_top_state()
        npcs = state.setdefault("npcs", {})
        for username, manifest_row in manifest.items():
            try:
                if callable(globals().get("server_database_user_exists")) and server_database_user_exists(username):
                    continue
            except Exception:
                pass
            npc = npcs.get(username) if isinstance(npcs.get(username), dict) else {}
            if not npc:
                npc = {"username": username, "total_words": 0, "days": {}}
                npcs[username] = npc
                changed = True
            for key in ("stt", "display_name", "full_name", "gender", "avatar", "source_name", "source_mtime", "source_size"):
                if npc.get(key) != manifest_row.get(key):
                    npc[key] = manifest_row.get(key)
                    changed = True
            npc.setdefault("days", {})
            days = npc["days"] if isinstance(npc.get("days"), dict) else {}
            if days is not npc.get("days"):
                npc["days"] = days
                changed = True
            for stale_key in list(days.keys()):
                if stale_key != day_key and len(days) > 14:
                    days.pop(stale_key, None)
                    changed = True
            day_row = days.get(day_key) if isinstance(days.get(day_key), dict) else {}
            if not day_row:
                day_row = {
                    "date": day_key,
                    "sessions": npc_top_generate_day_sessions(username, day_key),
                    "applied": {},
                    "generated_at": utc_timestamp(),
                }
                days[day_key] = day_row
                changed = True
            sessions = day_row.get("sessions") if isinstance(day_row.get("sessions"), list) else []
            applied = day_row.get("applied") if isinstance(day_row.get("applied"), dict) else {}
            if applied is not day_row.get("applied"):
                day_row["applied"] = applied
                changed = True
            for session in sessions:
                if not isinstance(session, dict):
                    continue
                session_id = clean(session.get("id", ""))
                if not session_id:
                    continue
                was_applied = bool(clean(applied.get(session_id, "")))
                planned_words_count = max(1, min(100, space_w_int(session.get("words", 0), 0)))
                next_total_increment = max(1, min(25, planned_words_count, space_w_int(session.get("total_increment", 0), 0) or 8))
                if session.get("total_increment") != next_total_increment:
                    session["total_increment"] = next_total_increment
                    changed = True
                session_epoch = day_start + max(0, min(24 * 60 - 1, space_w_int(session.get("minute", 0), 0))) * 60
                if now_value < session_epoch:
                    continue
                words_count = planned_words_count
                try:
                    current_period_state = load_vocab_leaderboard_period_state(clone=False)
                    current_day_count = max(0, space_w_int(vocab_leaderboard_period_counts_for_user(username, current_period_state).get("day", 0), 0))
                except Exception:
                    current_day_count = 0
                daily_remaining = max(0, 150 - current_day_count)
                if daily_remaining <= 0:
                    applied[session_id] = f"{utc_timestamp()} capped"
                    changed = True
                    continue
                words_count = min(words_count, daily_remaining)
                learned_items = [
                    {
                        "word": f"npc race {username} {day_key} {session_id} {index + 1}",
                        "last": local_timestamp(session_epoch),
                    }
                    for index in range(words_count)
                ]
                try:
                    record_vocab_leaderboard_period_activity(username, learned_items, default_epoch=session_epoch)
                    for viewed_scope in ("day", "week", "month", "total"):
                        record_vocab_leaderboard_view(username, viewed_scope)
                except Exception as exc:
                    stt_debug_log("npc_top_period_activity_failed", user=username, error=str(exc))
                    continue
                if was_applied:
                    continue
                increment = max(0, min(words_count, space_w_int(session.get("total_increment", 0), 0)))
                npc["total_words"] = npc_top_total_words(username, state) + increment
                applied[session_id] = utc_timestamp()
                npc["updated_at"] = utc_timestamp()
                applied_count += 1
                changed = True
        state["updated_at"] = utc_timestamp()
        if changed:
            write_vocab_leaderboard_npc_top_state(state)
    if changed:
        invalidate_vocab_leaderboard_ram_cache("space_v")
    return {"enabled": True, "npcs": len(manifest), "applied": applied_count, "updated_at": utc_timestamp()}


def buff_vocab_leaderboard_npc_top(username: str, amount: int, admin_username: str = "") -> dict:
    username = normalize_username(username)
    admin_username = normalize_username(admin_username)
    manifest = npc_top_manifest()
    if username not in manifest:
        raise RuntimeError("NPC racer khong hop le.")
    try:
        requested = int(amount)
    except (TypeError, ValueError):
        requested = 0
    if requested < 1 or requested > 25:
        raise RuntimeError("Chi duoc buff 1-25 words moi lan.")
    period_state = load_vocab_leaderboard_period_state(clone=False)
    current_counts = vocab_leaderboard_period_counts_for_user(username, period_state)
    today_count = max(0, space_w_int(current_counts.get("day", 0), 0))
    allowed = max(0, 150 - today_count)
    if allowed <= 0:
        raise RuntimeError("NPC racer da dat gioi han 150 words trong ngay.")
    applied_words = min(requested, allowed)
    now_epoch = time.time()
    event_id = f"manual-{int(now_epoch)}-{secrets.token_hex(4)}"
    learned_items = [
        {
            "word": f"npc manual buff {username} {event_id} {index + 1}",
            "last": local_timestamp(now_epoch),
        }
        for index in range(applied_words)
    ]
    period_result = record_vocab_leaderboard_period_activity(username, learned_items, default_epoch=now_epoch)
    total_percent = shared_world_npc_randint(60, 80)
    total_increment = max(1, int(round(applied_words * (total_percent / 100.0))))
    with VOCAB_LEADERBOARD_NPC_TOP_LOCK:
        state = load_vocab_leaderboard_npc_top_state()
        npcs = state.setdefault("npcs", {})
        row = npcs.get(username) if isinstance(npcs.get(username), dict) else {}
        if not row:
            row = {"username": username, "total_words": 0, "days": {}}
            npcs[username] = row
        manifest_row = manifest.get(username, {})
        for key in ("stt", "display_name", "full_name", "gender", "avatar", "source_name", "source_mtime", "source_size"):
            if key in manifest_row:
                row[key] = manifest_row.get(key)
        row["total_words"] = npc_top_total_words(username, state) + total_increment
        buffs = row.setdefault("manual_buffs", [])
        if not isinstance(buffs, list):
            buffs = []
        buffs.append(
            {
                "id": event_id,
                "admin": admin_username,
                "requested": requested,
                "applied_words": applied_words,
                "total_percent": total_percent,
                "total_increment": total_increment,
                "created_at": utc_timestamp(),
            }
        )
        row["manual_buffs"] = buffs[-200:]
        row["updated_at"] = utc_timestamp()
        state["updated_at"] = utc_timestamp()
        write_vocab_leaderboard_npc_top_state(state)
    invalidate_vocab_leaderboard_ram_cache("space_v")
    for viewed_scope in ("day", "week", "month", "total"):
        try:
            record_vocab_leaderboard_view(username, viewed_scope)
        except Exception:
            pass
    refreshed_counts = vocab_leaderboard_period_counts_for_user(username)
    return {
        "username": username,
        "requested": requested,
        "applied_words": applied_words,
        "total_increment": total_increment,
        "day_words": refreshed_counts.get("day", 0),
        "week_words": refreshed_counts.get("week", 0),
        "month_words": refreshed_counts.get("month", 0),
        "total_words": npc_top_total_words(username),
        "period_result": period_result,
        "updated_at": utc_timestamp(),
    }
