# Loaded by FUTURE.server_parts.09_vocab_world_game into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def flush_shared_world_battle_state_cache(force: bool = False) -> None:
    state = SHARED_WORLD_BATTLE_STATE_CACHE.get("state")
    if not isinstance(state, dict) or not bool(SHARED_WORLD_BATTLE_STATE_CACHE.get("dirty")):
        return
    battles = state.get("battles") if isinstance(state.get("battles"), dict) else {}
    force = bool(force) or any(isinstance(row, dict) and bool(row.get("_force_persist")) for row in battles.values())
    # Added 2026-07-30: PostgreSQL-authoritative battle mutations acknowledge durable storage immediately.
    force = force or postgres_backend_mode("QM_CITY_DOCUMENTS") == "postgres"
    now = time.time()
    last_flush = float(SHARED_WORLD_BATTLE_STATE_CACHE.get("last_flush") or 0.0)
    if not force and now - last_flush < SHARED_WORLD_BATTLE_STATE_FLUSH_INTERVAL_SECONDS:
        return
    SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    clean_battles = {}
    for battle_id, battle in battles.items():
        if isinstance(battle, dict):
            clean_battles[battle_id] = {key: value for key, value in battle.items() if not str(key).startswith("_")}
    payload = {
        "version": 1,
        "updated_at": clean(state.get("updated_at", "")) or utc_timestamp(),
        "invites": state.get("invites") if isinstance(state.get("invites"), dict) else {},
        "battles": clean_battles,
        "declines": state.get("declines") if isinstance(state.get("declines"), dict) else {},
    }
    atomic_write_json(SHARED_WORLD_BATTLE_FILE, payload, indent=2)
    for battle in battles.values():
        if isinstance(battle, dict):
            battle.pop("_force_persist", None)
    mtime = float(server_database_document_signature(SHARED_WORLD_BATTLE_FILE)[1] or time.time_ns()) / 1_000_000_000
    SHARED_WORLD_BATTLE_STATE_CACHE["mtime"] = mtime
    SHARED_WORLD_BATTLE_STATE_CACHE["state"] = state
    SHARED_WORLD_BATTLE_STATE_CACHE["dirty"] = False
    SHARED_WORLD_BATTLE_STATE_CACHE["last_flush"] = now


def load_shared_world_battle_state() -> dict:
    cached_state = SHARED_WORLD_BATTLE_STATE_CACHE.get("state")
    if isinstance(cached_state, dict):
        flush_shared_world_battle_state_cache(False)
        return cached_state
    payload = server_database_read_document_json(SHARED_WORLD_BATTLE_FILE, {})
    if isinstance(payload, dict) and payload:
        mtime = float(server_database_document_signature(SHARED_WORLD_BATTLE_FILE)[1] or 0) / 1_000_000_000
        state = {
            "version": 1,
            "updated_at": clean(payload.get("updated_at", "")),
            "invites": payload.get("invites") if isinstance(payload.get("invites"), dict) else {},
            "battles": payload.get("battles") if isinstance(payload.get("battles"), dict) else {},
            "declines": payload.get("declines") if isinstance(payload.get("declines"), dict) else {},
        }
        SHARED_WORLD_BATTLE_STATE_CACHE["mtime"] = mtime
        SHARED_WORLD_BATTLE_STATE_CACHE["state"] = state
        SHARED_WORLD_BATTLE_STATE_CACHE["dirty"] = False
        SHARED_WORLD_BATTLE_STATE_CACHE["last_flush"] = time.time()
        return state
    state = {"version": 1, "updated_at": "", "invites": {}, "battles": {}, "declines": {}}
    SHARED_WORLD_BATTLE_STATE_CACHE["mtime"] = 0.0
    SHARED_WORLD_BATTLE_STATE_CACHE["state"] = state
    SHARED_WORLD_BATTLE_STATE_CACHE["dirty"] = False
    SHARED_WORLD_BATTLE_STATE_CACHE["last_flush"] = time.time()
    return state


def write_shared_world_battle_state(state: dict, force: bool = False) -> None:
    if not isinstance(state, dict):
        return
    updated_at = utc_timestamp()
    state["updated_at"] = updated_at
    SHARED_WORLD_BATTLE_STATE_CACHE["state"] = state
    SHARED_WORLD_BATTLE_STATE_CACHE["dirty"] = True
    flush_shared_world_battle_state_cache(force)


atexit.register(lambda: flush_shared_world_battle_state_cache(True))


def shared_world_battle_profile(username: str) -> dict:
    username = normalize_username(username)
    cached = SHARED_WORLD_BATTLE_PROFILE_CACHE.get(username)
    if cached and time.time() - cached[0] < 90:
        return dict(cached[1])
    profile = read_user_profile(username)
    gender = clean(profile.get("gender", "")).lower()
    if gender not in {"male", "female", "other"}:
        gender = "other"
    result = {
        "username": username,
        "display_name": clean(profile.get("full_name", "")) or username,
        "avatar": clean(profile.get("avatar", "")),
        "gender": gender,
    }
    SHARED_WORLD_BATTLE_PROFILE_CACHE[username] = (time.time(), result)
    return dict(result)


def shared_world_battle_public_invite(invite: dict) -> dict:
    row = dict(invite) if isinstance(invite, dict) else {}
    challenger = normalize_username(row.get("from", ""))
    opponent = normalize_username(row.get("to", ""))
    from_profile = shared_world_battle_profile(challenger) if challenger else {}
    to_profile = shared_world_battle_profile(opponent) if opponent else {}
    row["from_profile"] = from_profile
    row["to_profile"] = to_profile
    row["from_display_name"] = clean(from_profile.get("display_name", "")) or challenger
    row["to_display_name"] = clean(to_profile.get("display_name", "")) or opponent
    # Keep bot internals private; the UI should treat all identities as normal
    # city learners and use display names for visible messaging.
    row.pop("npc_bot_from", None)
    row.pop("npc_bot_to", None)
    return row
