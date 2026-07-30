# Loaded by FUTURE.server_parts.09_vocab_world_game into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

QM_CITY_TRAINING_STATE_RAM_CACHE = {"mtime": None, "state": None}
QM_CITY_TRAINING_PUBLIC_STATE_CACHE: dict[str, tuple[float, dict]] = {}
QM_CITY_TRAINING_ASYNC_WRITE_LOCK = threading.RLock()
QM_CITY_TRAINING_ASYNC_WRITE_STATE = {"running": False, "pending": None}


# Added 2026-07-08: keeps repeated QM City training opens/polls in RAM instead of rebuilding public slime payloads.
def qm_city_training_clear_public_state_cache(username: str = "") -> None:
    if not isinstance(QM_CITY_TRAINING_PUBLIC_STATE_CACHE, dict):
        return
    clean_username = normalize_username(username)
    if clean_username:
        QM_CITY_TRAINING_PUBLIC_STATE_CACHE.pop(clean_username, None)
    else:
        QM_CITY_TRAINING_PUBLIC_STATE_CACHE.clear()


# Added 2026-07-08: normalizes QM City training state once for sync and coalesced async writes.
def qm_city_training_state_payload(state: dict) -> dict:
    return {
        "version": 1,
        "updated_at": utc_timestamp(),
        "users": _clean_qm_city_training_users(state.get("users") if isinstance(state, dict) else {}),
    }

def _clean_qm_city_training_users(value: object) -> dict:
    source = value if isinstance(value, dict) else {}
    users = {}
    for raw_username, raw_row in source.items():
        username = normalize_username(raw_username)
        if not username or not isinstance(raw_row, dict):
            continue
        current = users.get(username)
        current_updated = clean(current.get("updated_at", current.get("updatedAt", ""))) if isinstance(current, dict) else ""
        source_updated = clean(raw_row.get("updated_at", raw_row.get("updatedAt", "")))
        merged = dict(current) if isinstance(current, dict) else {}
        merged.update(raw_row)
        if not isinstance(current, dict) or timestamp_order_key(source_updated) >= timestamp_order_key(current_updated):
            users[username] = merged
    return users

def load_qm_city_training_state() -> dict:
    try:
        with QM_CITY_TRAINING_ASYNC_WRITE_LOCK:
            pending = QM_CITY_TRAINING_ASYNC_WRITE_STATE.get("pending")
            if isinstance(pending, dict):
                import copy
                return copy.deepcopy(pending)
        mtime = int(server_database_document_signature(QM_CITY_TRAINING_FILE)[1] or 0)
        cached = QM_CITY_TRAINING_STATE_RAM_CACHE.get("state")
        if QM_CITY_TRAINING_STATE_RAM_CACHE.get("mtime") == mtime and isinstance(cached, dict):
            import copy
            return copy.deepcopy(cached)
        payload = server_database_read_document_json(QM_CITY_TRAINING_FILE, {})
        if isinstance(payload, dict):
            state = {
                "version": 1,
                "updated_at": clean(payload.get("updated_at", "")),
                "users": _clean_qm_city_training_users(payload.get("users")),
            }
            import copy
            QM_CITY_TRAINING_STATE_RAM_CACHE["mtime"] = mtime
            QM_CITY_TRAINING_STATE_RAM_CACHE["state"] = copy.deepcopy(state)
            return state
    except Exception:
        if postgres_backend_mode("QM_CITY_DOCUMENTS") == "postgres":
            raise
    return {"version": 1, "updated_at": "", "users": {}}


def write_qm_city_training_state(state: dict) -> None:
    if not isinstance(state, dict):
        return
    SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    payload = qm_city_training_state_payload(state)
    atomic_write_json(QM_CITY_TRAINING_FILE, payload, indent=2)
    try:
        import copy
        QM_CITY_TRAINING_STATE_RAM_CACHE["mtime"] = int(server_database_document_signature(QM_CITY_TRAINING_FILE)[1] or 0)
        QM_CITY_TRAINING_STATE_RAM_CACHE["state"] = copy.deepcopy(payload)
    except Exception:
        QM_CITY_TRAINING_STATE_RAM_CACHE["mtime"] = None
        QM_CITY_TRAINING_STATE_RAM_CACHE["state"] = None


# Added 2026-07-08: lets training GET create/warm slime arenas without blocking on full JSON rewrites.
def write_qm_city_training_state_async(state: dict) -> None:
    if not isinstance(state, dict):
        return
    payload = qm_city_training_state_payload(state)
    try:
        import copy
        QM_CITY_TRAINING_STATE_RAM_CACHE["mtime"] = None
        QM_CITY_TRAINING_STATE_RAM_CACHE["state"] = copy.deepcopy(payload)
    except Exception:
        QM_CITY_TRAINING_STATE_RAM_CACHE["mtime"] = None
        QM_CITY_TRAINING_STATE_RAM_CACHE["state"] = None

    def flush_latest() -> None:
        while True:
            with QM_CITY_TRAINING_ASYNC_WRITE_LOCK:
                pending_payload = QM_CITY_TRAINING_ASYNC_WRITE_STATE.get("pending")
                QM_CITY_TRAINING_ASYNC_WRITE_STATE["pending"] = None
            if not isinstance(pending_payload, dict):
                with QM_CITY_TRAINING_ASYNC_WRITE_LOCK:
                    QM_CITY_TRAINING_ASYNC_WRITE_STATE["running"] = False
                return
            try:
                SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
                atomic_write_json(QM_CITY_TRAINING_FILE, pending_payload, indent=2)
                import copy
                QM_CITY_TRAINING_STATE_RAM_CACHE["mtime"] = int(server_database_document_signature(QM_CITY_TRAINING_FILE)[1] or 0)
                QM_CITY_TRAINING_STATE_RAM_CACHE["state"] = copy.deepcopy(pending_payload)
            except Exception as exc:
                with QM_CITY_TRAINING_ASYNC_WRITE_LOCK:
                    if not isinstance(QM_CITY_TRAINING_ASYNC_WRITE_STATE.get("pending"), dict):
                        QM_CITY_TRAINING_ASYNC_WRITE_STATE["pending"] = pending_payload
                    QM_CITY_TRAINING_ASYNC_WRITE_STATE["running"] = False
                stt_debug_log("qm_city_training_postgres_flush_failed", error=str(exc))
                return

    with QM_CITY_TRAINING_ASYNC_WRITE_LOCK:
        QM_CITY_TRAINING_ASYNC_WRITE_STATE["pending"] = payload
        if bool(QM_CITY_TRAINING_ASYNC_WRITE_STATE.get("running")):
            return
        QM_CITY_TRAINING_ASYNC_WRITE_STATE["running"] = True
    thread = threading.Thread(target=flush_latest, name="qm-city-training-flush", daemon=True)
    thread.start()


def qm_city_training_level_meta(username: str, bonus_words: int = 0) -> dict:
    try:
        settings = load_server_settings()
        levels = settings.get("qm_city_levels") if isinstance(settings.get("qm_city_levels"), list) else DEFAULT_QM_CITY_LEVELS
    except Exception:
        levels = DEFAULT_QM_CITY_LEVELS
    registry = read_user_vocab_registry_summary(username)
    summary_total = 0
    try:
        summary = read_cached_lesson_user_learning_summary(username)
        summary_total = max(
            space_w_int(summary.get("vocabulary_words", 0), 0),
            space_w_int(summary.get("total_words", 0), 0),
        ) if isinstance(summary, dict) else 0
    except Exception:
        summary_total = 0
    base_exp = max(max(0, space_w_int(registry.get("total_words", 0), 0)), max(0, summary_total))
    return qm_city_character_level_for_exp(base_exp + max(0, space_w_int(bonus_words, 0)), levels)


def qm_city_training_normalize_stats(raw_stats: object, level_meta: dict | None = None) -> dict:
    source = raw_stats if isinstance(raw_stats, dict) else {}
    level = max(1, space_w_int((level_meta or {}).get("level", 1), 1))
    total_points = max(0, (level - 1) * 3)
    total_skill_points = max(0, (level - 1) * 2)
    raw_skill_levels = source.get("skill_levels")
    if not isinstance(raw_skill_levels, dict):
        raw_skill_levels = source.get("skills") if isinstance(source.get("skills"), dict) else {}
    skill_levels = qm_city_training_normalize_skill_levels(raw_skill_levels)
    skill_spent = qm_city_training_skill_spent_points(skill_levels)
    raw_strength = max(1, min(200, space_w_int(source.get("strength", 1), 1)))
    raw_defense = max(1, min(200, space_w_int(source.get("defense", 1), 1)))
    stats = {
        "strength": qm_city_training_strength_for_level(level) + raw_strength - 1,
        "defense": max(1, level + raw_defense - 1),
        "raw_strength": raw_strength,
        "raw_defense": raw_defense,
        "hp_bonus": max(0, min(200, space_w_int(source.get("hp_bonus", source.get("hp", 0)), 0))),
        "mana_bonus": max(0, min(200, space_w_int(source.get("mana_bonus", source.get("mana", 0)), 0))),
        "skill_levels": skill_levels,
    }
    spent = max(0, (raw_strength - 1) + (raw_defense - 1) + stats["hp_bonus"] + stats["mana_bonus"])
    if spent > total_points and spent > 0:
        # Keep old data usable if level settings were lowered. The UI will show no
        # free points until the learner catches up again.
        available = 0
    else:
        available = total_points - spent
    skill_available = 0 if skill_spent > total_skill_points and skill_spent > 0 else total_skill_points - skill_spent
    stats.update(
        {
            "total_points": total_points,
            "spent_points": spent,
            "available_points": available,
            "total_skill_points": total_skill_points,
            "spent_skill_points": skill_spent,
            "available_skill_points": skill_available,
            "max_hp": qm_city_training_max_hp_for_level(level) + stats["hp_bonus"] * 10,
            "max_mana": qm_city_training_max_mana_for_level(level) + stats["mana_bonus"] * 10,
        }
    )
    return stats


def qm_city_training_public_stats(stats: dict, level_meta: dict) -> dict:
    level = max(1, space_w_int(level_meta.get("level", 1), 1))
    return {
        "level": level,
        "exp": max(0, space_w_int(level_meta.get("exp", 0), 0)),
        "current_exp": max(0, space_w_int(level_meta.get("current_exp", 0), 0)),
        "next_exp": max(0, space_w_int(level_meta.get("next_exp", 0), 0)),
        "progress": max(0.0, min(1.0, float(level_meta.get("progress", 0) or 0))),
        "max_level": bool(level_meta.get("max_level")),
        "training_words": max(0, space_w_int(stats.get("training_words", 0), 0)),
        "strength": max(1, space_w_int(stats.get("strength", 1), 1)),
        "defense": max(1, space_w_int(stats.get("defense", 1), 1)),
        "raw_strength": max(1, space_w_int(stats.get("raw_strength", 1), 1)),
        "rawStrength": max(1, space_w_int(stats.get("raw_strength", 1), 1)),
        "raw_defense": max(1, space_w_int(stats.get("raw_defense", 1), 1)),
        "rawDefense": max(1, space_w_int(stats.get("raw_defense", 1), 1)),
        "hp_bonus": max(0, space_w_int(stats.get("hp_bonus", 0), 0)),
        "mana_bonus": max(0, space_w_int(stats.get("mana_bonus", 0), 0)),
        "max_hp": max(1, space_w_int(stats.get("max_hp", 100), 100)),
        "max_mana": max(1, space_w_int(stats.get("max_mana", 60), 60)),
        "total_points": max(0, space_w_int(stats.get("total_points", 0), 0)),
        "spent_points": max(0, space_w_int(stats.get("spent_points", 0), 0)),
        "available_points": max(0, space_w_int(stats.get("available_points", 0), 0)),
        "total_skill_points": max(0, space_w_int(stats.get("total_skill_points", 0), 0)),
        "totalSkillPoints": max(0, space_w_int(stats.get("total_skill_points", 0), 0)),
        "spent_skill_points": max(0, space_w_int(stats.get("spent_skill_points", 0), 0)),
        "spentSkillPoints": max(0, space_w_int(stats.get("spent_skill_points", 0), 0)),
        "skill_levels": stats.get("skill_levels", {}) if isinstance(stats.get("skill_levels"), dict) else {},
        "skillLevels": stats.get("skill_levels", {}) if isinstance(stats.get("skill_levels"), dict) else {},
        "skill_points": max(0, space_w_int(stats.get("available_skill_points", 0), 0)),
        "skillPoints": max(0, space_w_int(stats.get("available_skill_points", 0), 0)),
        "skills": qm_city_training_public_skills(level, stats),
    }
