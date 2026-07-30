# Loaded by FUTURE.server_parts.09_vocab_world_game into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def flush_shared_world_state_cache(force: bool = False) -> None:
    state = SHARED_WORLD_STATE_CACHE.get("state")
    if not isinstance(state, dict) or not bool(SHARED_WORLD_STATE_CACHE.get("dirty")):
        return
    now = time.time()
    last_flush = float(SHARED_WORLD_STATE_CACHE.get("last_flush") or 0.0)
    if not force and now - last_flush < SHARED_WORLD_STATE_FLUSH_INTERVAL_SECONDS:
        return
    SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": clean(state.get("updated_at", "")) or utc_timestamp(),
        "players": state.get("players") if isinstance(state.get("players"), dict) else {},
    }
    atomic_write_json(SHARED_WORLD_FILE, payload, indent=2)
    mtime = float(server_database_document_signature(SHARED_WORLD_FILE)[1] or time.time_ns()) / 1_000_000_000
    SHARED_WORLD_STATE_CACHE["mtime"] = mtime
    SHARED_WORLD_STATE_CACHE["dirty"] = False
    SHARED_WORLD_STATE_CACHE["last_flush"] = now


def load_shared_world_state() -> dict:
    cached_state = SHARED_WORLD_STATE_CACHE.get("state")
    if isinstance(cached_state, dict):
        flush_shared_world_state_cache(False)
        return cached_state
    payload = server_database_read_document_json(SHARED_WORLD_FILE, {})
    if isinstance(payload, dict) and payload:
        mtime = float(server_database_document_signature(SHARED_WORLD_FILE)[1] or 0) / 1_000_000_000
        players = payload.get("players") if isinstance(payload.get("players"), dict) else {}
        state = {
            "version": 1,
            "updated_at": clean(payload.get("updated_at", "")),
            "players": players,
        }
        SHARED_WORLD_STATE_CACHE["mtime"] = mtime
        SHARED_WORLD_STATE_CACHE["state"] = state
        SHARED_WORLD_STATE_CACHE["dirty"] = False
        SHARED_WORLD_STATE_CACHE["last_flush"] = time.time()
        return state
    state = {"version": 1, "updated_at": "", "players": {}}
    SHARED_WORLD_STATE_CACHE["mtime"] = 0.0
    SHARED_WORLD_STATE_CACHE["state"] = state
    SHARED_WORLD_STATE_CACHE["dirty"] = False
    SHARED_WORLD_STATE_CACHE["last_flush"] = time.time()
    return state


def write_shared_world_state(state: dict, force: bool = False) -> None:
    if not isinstance(state, dict):
        return
    state["updated_at"] = utc_timestamp()
    state.pop("_volatile_changed", None)
    SHARED_WORLD_STATE_CACHE["state"] = state
    SHARED_WORLD_STATE_CACHE["dirty"] = True
    flush_shared_world_state_cache(force)


atexit.register(lambda: flush_shared_world_state_cache(True))


def shared_world_clamp(value: object, fallback: float = 0.5) -> float:
    try:
        number = float(value)
    except Exception:
        number = fallback
    if not math.isfinite(number):
        number = fallback
    return max(0.04, min(0.96, number))


def shared_world_city_npc_number(username: str = "") -> int:
    safe = normalize_username(username)
    match = re.fullmatch(rf"{re.escape(SHARED_WORLD_CITY_NPC_PREFIX)}(\d{{2}})", safe or "")
    if not match:
        return 0
    number = int(match.group(1) or 0)
    return number if 1 <= number <= SHARED_WORLD_CITY_NPC_COUNT else 0


def shared_world_city_npc_username(index: int) -> str:
    safe_index = max(1, min(SHARED_WORLD_CITY_NPC_COUNT, int(index or 1)))
    return f"{SHARED_WORLD_CITY_NPC_PREFIX}{safe_index:02d}"


def shared_world_city_npc_profile_for_user(username: str = "") -> dict:
    number = shared_world_city_npc_number(username)
    if not number:
        return {}
    gender_cycle = ("female", "male", "other", "female", "male")
    gender = gender_cycle[(number - 1) % len(gender_cycle)]
    display_name = f"QM-City Resident {number:02d}"
    return {
        "username": shared_world_city_npc_username(number),
        "full_name": display_name,
        "display_name": display_name,
        "gender": gender,
        "birth_date": "",
        "avatar": "",
        "intro": "A quiet resident of QM-City.",
        "profile_photos": [],
        "updated_at": "qm-city-resident",
        "npc": True,
        "city_npc": True,
    }


def shared_world_city_npc_rows() -> dict[str, dict]:
    return {
        shared_world_city_npc_username(index): shared_world_city_npc_profile_for_user(shared_world_city_npc_username(index))
        for index in range(1, SHARED_WORLD_CITY_NPC_COUNT + 1)
    }


def shared_world_city_npc_exp(username: str = "") -> int:
    number = shared_world_city_npc_number(username)
    if not number:
        return 0
    return 80 + number * 45


def shared_world_city_npc_seed_position(username: str = "") -> tuple[float, float]:
    number = shared_world_city_npc_number(username)
    if not number:
        return (0.5, 0.5)
    point = SHARED_WORLD_CITY_NPC_POINTS[(number - 1) % len(SHARED_WORLD_CITY_NPC_POINTS)]
    return shared_world_clamp(point[0]), shared_world_clamp(point[1])


def shared_world_seed_position(username: str) -> tuple[float, float]:
    city_point = shared_world_city_npc_seed_position(username)
    if shared_world_city_npc_number(username):
        return city_point
    seed = hashlib.sha256(normalize_username(username).encode("utf-8", errors="ignore")).digest()
    x = 0.14 + (seed[0] / 255) * 0.72
    y = 0.24 + (seed[1] / 255) * 0.56
    return shared_world_clamp(x), shared_world_clamp(y)
