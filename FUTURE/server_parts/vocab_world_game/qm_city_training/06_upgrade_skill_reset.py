def qm_city_training_upgrade(username: str, payload: dict) -> dict:
    username = normalize_username(username)
    source_payload = payload if isinstance(payload, dict) else {}
    skill_id = clean(source_payload.get("skill", source_payload.get("skill_id", source_payload.get("skillId", "")))).lower()
    stat = clean(source_payload.get("stat", "")).lower()
    aliases = {"str": "strength", "def": "defense", "hp": "hp_bonus", "mana": "mana_bonus", "mp": "mana_bonus"}
    stat_key = aliases.get(stat, stat)
    skill_ids = {clean(skill.get("id", "")).lower(): skill for skill in qm_city_training_skill_tree()}
    if skill_id and skill_id not in skill_ids:
        raise RuntimeError("Unknown training skill.")
    if not skill_id and stat_key not in {"strength", "defense", "hp_bonus", "mana_bonus"}:
        raise RuntimeError("Unknown training stat.")
    with QM_CITY_TRAINING_LOCK:
        state = load_qm_city_training_state()
        _row, level_meta, stats, _changed = qm_city_training_ensure_user(state, username, tick_motion=False)
        raw_stats = state["users"][username].get("stats") if isinstance(state["users"][username].get("stats"), dict) else {}
        event_type = "upgrade"
        if skill_id:
            if space_w_int(stats.get("available_skill_points", 0), 0) <= 0:
                raise RuntimeError("No skill points available.")
            skill = skill_ids[skill_id]
            raw_levels = raw_stats.get("skill_levels") if isinstance(raw_stats.get("skill_levels"), dict) else {}
            current = space_w_int(raw_levels.get(skill_id, skill.get("base_level", 1)), skill.get("base_level", 1))
            max_level = space_w_int(skill.get("max_level", current), current)
            if current >= max_level:
                raise RuntimeError("This skill is already max level.")
            raw_levels[skill_id] = current + 1
            raw_stats["skill_levels"] = raw_levels
            event_type = "skill_upgrade"
        else:
            if space_w_int(stats.get("available_points", 0), 0) <= 0:
                raise RuntimeError("No upgrade points available.")
            raw_stats[stat_key] = space_w_int(raw_stats.get(stat_key, 1 if stat_key in {"strength", "defense"} else 0), 1 if stat_key in {"strength", "defense"} else 0) + 1
        stats = qm_city_training_normalize_stats(raw_stats, level_meta)
        stats["training_words"] = qm_city_training_bonus_words_from_row(state["users"][username])
        state["users"][username]["stats"] = stats
        arena = state["users"][username]["arena"]
        arena["player_hp"] = min(stats["max_hp"], space_w_int(arena.get("player_hp", stats["max_hp"]), stats["max_hp"]) + (10 if (not skill_id and stat_key == "hp_bonus") else 0))
        arena["player_mana"] = min(stats["max_mana"], space_w_int(arena.get("player_mana", 0), 0) + (10 if (not skill_id and stat_key == "mana_bonus") else 0))
        qm_city_training_rebalance_slime_positions(arena, level_meta, stats)
        arena["updated_at"] = utc_timestamp()
        write_qm_city_training_state(state)
        qm_city_training_clear_public_state_cache(username)
    return {
        "training": {
            "username": username,
            "stats": qm_city_training_public_stats(stats, level_meta),
            "arena": qm_city_training_public_arena(arena, stats),
            "event": {"type": event_type, "stat": stat_key if not skill_id else "", "skill": skill_id},
        }
    }


def qm_city_training_cast_skill(username: str, payload: dict) -> dict:
    username = normalize_username(username)
    source_payload = payload if isinstance(payload, dict) else {}
    skill_id = clean(source_payload.get("skill", source_payload.get("skill_id", source_payload.get("skillId", "earthquake")))).lower() or "earthquake"
    skill_rows = {clean(skill.get("id", "")).lower(): skill for skill in qm_city_training_skill_tree()}
    if skill_id not in skill_rows:
        raise RuntimeError("Unknown training skill.")
    with QM_CITY_TRAINING_LOCK:
        state = load_qm_city_training_state()
        _row, level_meta, stats, _changed = qm_city_training_ensure_user(state, username, tick_motion=False)
        arena = state["users"][username]["arena"]
        skill = skill_rows[skill_id]
        skill_levels = qm_city_training_normalize_skill_levels(stats.get("skill_levels", {}))
        current_level = max(0, space_w_int(skill_levels.get(skill_id, skill.get("base_level", 1)), skill.get("base_level", 1)))
        if current_level <= 0:
            raise RuntimeError("This skill is not unlocked.")
        now = time.time()
        cooldowns = arena.get("skill_cooldowns") if isinstance(arena.get("skill_cooldowns"), dict) else {}
        cooldown_until = float(cooldowns.get(skill_id) or 0.0)
        if cooldown_until > now:
            raise RuntimeError(f"Skill is cooling down. Try again in {max(1, int(math.ceil(cooldown_until - now)))}s.")
        max_mana = max(1, space_w_int(stats.get("max_mana", 60), 60))
        mana_cost = max(1, int(math.ceil(max_mana * float(skill.get("mana_cost_ratio", 1 / 3) or (1 / 3)))))
        current_mana = max(0, space_w_int(arena.get("player_mana", 0), 0))
        if current_mana < mana_cost:
            raise RuntimeError(f"Not enough mana. Need {mana_cost} mana.")
        player_x = shared_world_clamp(source_payload.get("player_x", source_payload.get("playerX", 0.5)))
        player_y = shared_world_clamp(source_payload.get("player_y", source_payload.get("playerY", 0.5)))
        client_slime_positions = {}
        raw_positions = source_payload.get("slime_positions", source_payload.get("slimePositions", []))
        if isinstance(raw_positions, list):
            for raw_position in raw_positions[:QM_CITY_TRAINING_SLIME_COUNT]:
                if not isinstance(raw_position, dict):
                    continue
                position_id = clean(raw_position.get("id", raw_position.get("slime_id", raw_position.get("slimeId", ""))))
                if not position_id:
                    continue
                client_slime_positions[position_id] = (
                    shared_world_clamp(raw_position.get("x", raw_position.get("slime_x", raw_position.get("slimeX", 0.5)))),
                    shared_world_clamp(raw_position.get("y", raw_position.get("slime_y", raw_position.get("slimeY", 0.5)))),
                )
        radius_x = max(0.02, min(1.0, float(source_payload.get("radius_x", source_payload.get("radiusX", 0.32)) or 0.32)))
        radius_y = max(0.02, min(1.0, float(source_payload.get("radius_y", source_payload.get("radiusY", 0.44)) or 0.44)))
        base_percent = space_w_int(skill.get("base_percent", 100), 100)
        per_level = space_w_int(skill.get("per_level_percent", 10), 10)
        base_level = max(0, space_w_int(skill.get("base_level", 1), 1))
        damage_percent = base_percent + max(0, current_level - base_level) * per_level
        base_damage = max(1, space_w_int(stats.get("strength", 1), 1))
        damage = max(1, int(round(base_damage * damage_percent / 100.0)))
        arena["player_mana"] = max(0, current_mana - mana_cost)
        affected = []
        slimes = arena.get("slimes") if isinstance(arena.get("slimes"), list) else []
        for slime in slimes:
            if not isinstance(slime, dict) or space_w_int(slime.get("hp", 0), 0) <= 0:
                continue
            client_position = client_slime_positions.get(clean(slime.get("id", "")))
            if isinstance(client_position, tuple):
                sx, sy = client_position
            else:
                sx = shared_world_clamp(slime.get("tx", slime.get("x", 0.5)))
                sy = shared_world_clamp(slime.get("ty", slime.get("y", 0.5)))
            distance = math.hypot((sx - player_x) / radius_x, (sy - player_y) / radius_y)
            if distance > 1:
                continue
            before_hp = space_w_int(slime.get("hp", 0), 0)
            slime["hp"] = max(0, before_hp - damage)
            slime["mood"] = "hurt" if slime["hp"] > 0 else "defeated"
            defeated_now = before_hp > 0 and slime["hp"] <= 0
            if defeated_now:
                slime["respawn_at"] = time.time() + QM_CITY_TRAINING_SPEECH_RESPAWN_SECONDS
            affected.append({
                "slime_id": clean(slime.get("id", "")),
                "slimeId": clean(slime.get("id", "")),
                "slime_name": clean(slime.get("name", "Slime")),
                "slimeName": clean(slime.get("name", "Slime")),
                "slime_x": sx,
                "slimeX": sx,
                "slime_y": sy,
                "slimeY": sy,
                "damage": damage,
                "slime_hp": slime["hp"],
                "slimeHp": slime["hp"],
                "slime_defeated": defeated_now,
                "slimeDefeated": defeated_now,
            })
        if not affected:
            arena["player_mana"] = current_mana
            raise RuntimeError("No slime inside the Earthquake range.")
        next_cooldown_until = time.time() + QM_CITY_TRAINING_SKILL_COOLDOWN_SECONDS
        cooldowns[skill_id] = next_cooldown_until
        arena["skill_cooldowns"] = cooldowns
        if not qm_city_training_alive_slimes(arena) and not qm_city_training_pending_speech_respawns(arena):
            arena = qm_city_training_new_arena(username, level_meta, stats)
            arena["skill_cooldowns"] = cooldowns
            state["users"][username]["arena"] = arena
        else:
            if clean(arena.get("selected_id", "")):
                selected = qm_city_training_selected_slime(arena)
                if not selected or space_w_int(selected.get("hp", 0), 0) <= 0:
                    arena["selected_id"] = ""
                    arena["question"] = {}
            qm_city_training_ensure_slime_questions(username, arena)
        log = arena.setdefault("log", [])
        if isinstance(log, list):
            log.append({"at": utc_timestamp(), "type": "skill", "text": f"Earthquake hit {len(affected)} slime(s) for {damage} damage."})
            arena["log"] = log[-24:]
        arena["updated_at"] = utc_timestamp()
        state["users"][username]["updated_at"] = utc_timestamp()
        write_qm_city_training_state(state)
        qm_city_training_clear_public_state_cache(username)
    return {
        "training": {
            "username": username,
            "stats": qm_city_training_public_stats(stats, level_meta),
            "arena": qm_city_training_public_arena(arena, stats),
            "event": {
                "event_id": f"training_skill_{time.time_ns()}",
                "type": "skill",
                "skill": {"id": skill_id, "name": clean(skill.get("name", "Earthquake")), "tone": clean(skill.get("tone", "earth")), "level": current_level},
                "skill_id": skill_id,
                "skillId": skill_id,
                "damage": damage,
                "damage_percent": damage_percent,
                "damagePercent": damage_percent,
                "mana_cost": mana_cost,
                "manaCost": mana_cost,
                "cooldown_seconds": QM_CITY_TRAINING_SKILL_COOLDOWN_SECONDS,
                "cooldownSeconds": QM_CITY_TRAINING_SKILL_COOLDOWN_SECONDS,
                "cooldown_until": next_cooldown_until,
                "cooldownUntil": next_cooldown_until,
                "player_mana": arena.get("player_mana", 0),
                "playerMana": arena.get("player_mana", 0),
                "player_x": player_x,
                "playerX": player_x,
                "player_y": player_y,
                "playerY": player_y,
                "radius_px": max(1, space_w_int(skill.get("radius_px", 400), 400)),
                "radiusPx": max(1, space_w_int(skill.get("radius_px", 400), 400)),
                "affected": affected,
            },
        }
    }


def qm_city_training_reset(username: str) -> dict:
    username = normalize_username(username)
    with QM_CITY_TRAINING_LOCK:
        state = load_qm_city_training_state()
        _row, level_meta, stats, _changed = qm_city_training_ensure_user(state, username, tick_motion=False)
        arena = qm_city_training_new_arena(username, level_meta, stats)
        state["users"][username]["arena"] = arena
        state["users"][username]["updated_at"] = utc_timestamp()
        write_qm_city_training_state(state)
        qm_city_training_clear_public_state_cache(username)
    return {
        "training": {
            "username": username,
            "stats": qm_city_training_public_stats(stats, level_meta),
            "arena": qm_city_training_public_arena(arena, stats),
            "event": {"type": "reset"},
        }
    }
