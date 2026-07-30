def shared_world_chat(username: str, payload: dict, real_username: str = "") -> dict:
    username = normalize_username(username)
    real_username = normalize_username(real_username) or username
    validation = validate_shared_world_chat_message(payload.get("message", ""))
    if not validation.get("ok"):
        raise RuntimeError(clean(validation.get("error", "")) or "Please chat in English.")
    message = validation.get("message", "")
    with SHARED_WORLD_LOCK:
        state = load_shared_world_state()
        shared_world_touch_player(username, state, chat=message, admin_actor=(username != real_username and shared_world_is_npc_identity(username)))
        try:
            shared_world_schedule_npc_chat_replies(state, username, message, payload)
        except Exception as exc:
            stt_debug_log("qm_city_npc_chat_schedule_failed", user=username, error=str(exc))
        state["updated_at"] = utc_timestamp()
        write_shared_world_state(state)
    result = shared_world_state_for_user(username, real_username=real_username)
    result["chat_validation"] = validation
    return result


SHARED_WORLD_ACTIONS = {"jump", "spin", "wave", "dance", "stop"}


def shared_world_action(username: str, payload: dict, real_username: str = "") -> dict:
    username = normalize_username(username)
    real_username = normalize_username(real_username) or username
    action = clean(payload.get("action", "")).lower()
    if action not in SHARED_WORLD_ACTIONS:
        raise RuntimeError("Unknown QM-City action.")
    with SHARED_WORLD_LOCK:
        state = load_shared_world_state()
        row = shared_world_touch_player(username, state, admin_actor=(username != real_username and shared_world_is_npc_identity(username)))
        row["action"] = "" if action == "stop" else action
        row["action_at"] = utc_timestamp()
        row["updated_at"] = utc_timestamp()
        state.setdefault("players", {})[username] = row
        state["updated_at"] = utc_timestamp()
        write_shared_world_state(state)
    return shared_world_state_for_user(username, real_username=real_username)


SHARED_WORLD_BATTLE_GAMES = {
    "fireball_vocab": {
        "id": "fireball_vocab",
        "name": "Fireball Vocabulary Battle",
        "prompt": "Would you like to play Fireball Vocabulary Battle with me?",
        "wager": 2,
    }
}
SHARED_WORLD_BATTLE_VOCAB_CACHE: dict[str, tuple[float, list[dict]]] = {}
SHARED_WORLD_BATTLE_DICT_CACHE: dict[str, tuple[float, dict]] = {}
SHARED_WORLD_BATTLE_PROFILE_CACHE: dict[str, tuple[float, dict]] = {}
SHARED_WORLD_BATTLE_STATE_CACHE: dict[str, object] = {"mtime": -1.0, "state": None, "dirty": False, "last_flush": 0.0}
SHARED_WORLD_BATTLE_WORD_HISTORY_CACHE: dict[str, object] = {"mtime": -1.0, "users": {}}
SHARED_WORLD_BATTLE_ACTIVE_ASKED_CACHE: dict[str, set[str]] = {}
SHARED_WORLD_BATTLE_VOCAB_POOL_LIMIT = 5000
SHARED_WORLD_BATTLE_HISTORY_LIMIT = 5000
SHARED_WORLD_BATTLE_STATE_FLUSH_INTERVAL_SECONDS = 1.0
QM_CITY_TRAINING_PROMPT_CACHE: dict[str, tuple[float, list[dict]]] = {}
QM_CITY_TRAINING_SLIME_COUNT = 10
QM_CITY_TRAINING_LAYOUT_VERSION = 8
QM_CITY_TRAINING_SPEECH_RESPAWN_SECONDS = 10
QM_CITY_TRAINING_SKILL_COOLDOWN_SECONDS = 10
QM_CITY_TRAINING_FOCUS_RADIUS_X = 0.115
QM_CITY_TRAINING_FOCUS_RADIUS_Y = 0.17
QM_CITY_TRAINING_FOCUS_RADIUS = QM_CITY_TRAINING_FOCUS_RADIUS_X
QM_CITY_TRAINING_FIXED_KIND_SEQUENCE = ("word", "sentence", "read_word", "read_sentence", "translate_vi", "translate_vi_speech", "audio_word", "speak_vi_sentence")
QM_CITY_TRAINING_RANDOM_KIND_SEQUENCE = ("word", "sentence", "read_word", "read_sentence", "translate_vi", "translate_vi_speech", "audio_word", "audio_sentence", "speak_vi_word", "speak_vi_sentence")
QM_CITY_TRAINING_KIND_SEQUENCE = QM_CITY_TRAINING_FIXED_KIND_SEQUENCE
