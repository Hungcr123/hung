def shared_world_is_npc_identity(username: str = "") -> bool:
    safe = normalize_username(username)
    return bool(npc_top_profile_for_user(safe) or shared_world_city_npc_profile_for_user(safe))


def shared_world_npc_randint(minimum: int, maximum: int) -> int:
    low = int(minimum)
    high = int(maximum)
    if high < low:
        high = low
    return low + secrets.randbelow(max(1, high - low + 1))


def shared_world_npc_bot_settings() -> dict:
    try:
        return normalize_qm_city_npc_settings(load_server_settings().get("qm_city_npc", DEFAULT_SETTINGS["qm_city_npc"]))
    except Exception:
        return normalize_qm_city_npc_settings(DEFAULT_SETTINGS["qm_city_npc"])


def shared_world_npc_mode(settings: dict | None = None) -> str:
    source = settings if isinstance(settings, dict) else shared_world_npc_bot_settings()
    mode = clean(source.get("mode", "")).lower()
    if mode in {"mixed", "city"}:
        return mode
    if mode == "top":
        return "top"
    return "top" if bool(source.get("enabled", True)) else "city"


def shared_world_npc_candidate_maps(settings: dict | None = None) -> tuple[str, dict[str, dict], dict[str, dict], dict[str, dict]]:
    source = settings if isinstance(settings, dict) else shared_world_npc_bot_settings()
    mode = shared_world_npc_mode(source)
    top_rows = npc_top_manifest() if mode in {"top", "mixed"} else {}
    city_rows = shared_world_city_npc_rows() if mode in {"city", "mixed"} else {}
    combined = {**top_rows, **city_rows}
    return mode, top_rows, city_rows, combined


def schedule_shared_world_npc_mode_transition(settings: dict | None = None) -> dict:
    mode, _top_rows, _city_rows, candidates = shared_world_npc_candidate_maps(settings)
    scheduled = 0
    cleared = 0
    removed = 0
    kept_admin_actors = 0
    now = time.time()
    with SHARED_WORLD_LOCK:
        state = load_shared_world_state()
        players = state.get("players") if isinstance(state.get("players"), dict) else {}
        for name, row in list(players.items()):
            if not isinstance(row, dict) or not bool(row.get("npc_bot")):
                continue
            safe_name = normalize_username(name)
            if bool(row.get("admin_actor")):
                kept_admin_actors += 1
                continue
            if safe_name in candidates:
                if row.pop("bot_retire_at", None) is not None:
                    cleared += 1
                row.pop("bot_retiring", None)
                players[safe_name] = row
                continue
            players.pop(safe_name, None)
            removed += 1
        if scheduled or cleared or removed:
            state["players"] = players
            state["updated_at"] = utc_timestamp()
            write_shared_world_state(state, force=True)
    return {
        "mode": mode,
        "scheduled_retire": scheduled,
        "cleared_retire": cleared,
        "removed": removed,
        "kept_admin_actors": kept_admin_actors,
    }


def shared_world_npc_bot_names_snapshot() -> set[str]:
    try:
        state = SHARED_WORLD_STATE_CACHE.get("state")
        if not isinstance(state, dict):
            state = load_shared_world_state()
        players = state.get("players") if isinstance(state.get("players"), dict) else {}
        return {
            normalize_username(name)
            for name, row in players.items()
            if normalize_username(name) and isinstance(row, dict) and bool(row.get("npc_bot"))
        }
    except Exception:
        return set()


def shared_world_active_battle_user_set() -> set[str]:
    users: set[str] = set()
    try:
        with SHARED_WORLD_BATTLE_LOCK:
            state = load_shared_world_battle_state()
            changed = shared_world_battle_prune(state)
            if changed:
                write_shared_world_battle_state(state)
            battles = state.get("battles") if isinstance(state.get("battles"), dict) else {}
            for battle in battles.values():
                if not isinstance(battle, dict) or clean(battle.get("status", "")) != "active":
                    continue
                for player in battle.get("players") if isinstance(battle.get("players"), list) else []:
                    safe = normalize_username(player)
                    if safe:
                        users.add(safe)
    except Exception:
        return users
    return users


def shared_world_npc_bot_tick(state: dict, real_username: str = "", protected_actor: str = "") -> bool:
    settings = shared_world_npc_bot_settings()
    mode, top_manifest, city_manifest, all_candidates = shared_world_npc_candidate_maps(settings)
    players = state.setdefault("players", {})
    if not isinstance(players, dict):
        return False
    now = time.time()
    changed = False
    protected = {normalize_username(protected_actor)}
    protected.discard("")
    for name, row in players.items():
        if isinstance(row, dict) and bool(row.get("admin_actor")):
            safe_name = normalize_username(name)
            if safe_name:
                protected.add(safe_name)

    real_players = []
    for name, row in players.items():
        safe_name = normalize_username(name)
        if not safe_name or not isinstance(row, dict):
            continue
        if shared_world_is_npc_identity(safe_name) or safe_name == "witch":
            continue
        updated = timestamp_to_epoch(clean(row.get("updated_at", "")))
        if updated and now - updated <= 180:
            real_players.append(safe_name)

    if not real_players:
        for name, row in list(players.items()):
            if isinstance(row, dict) and bool(row.get("npc_bot")) and normalize_username(name) not in protected:
                players.pop(name, None)
                changed = True
        return changed

    if not all_candidates:
        for name, row in list(players.items()):
            safe_name = normalize_username(name)
            if not safe_name or not isinstance(row, dict) or not bool(row.get("npc_bot")):
                continue
            if safe_name in protected:
                continue
            players.pop(name, None)
            changed = True
        return changed

    active_battle_users = shared_world_active_battle_user_set()
    active_top_bots = []
    active_city_bots = []
    moving_bots = []
    for name, row in list(players.items()):
        safe_name = normalize_username(name)
        if not safe_name or not isinstance(row, dict) or not bool(row.get("npc_bot")):
            continue
        if safe_name in protected:
            continue
        if safe_name not in all_candidates:
            players.pop(safe_name, None)
            changed = True
            continue
        if row.pop("bot_retire_at", None) is not None:
            changed = True
        if row.pop("bot_retiring", None) is not None:
            changed = True
        if safe_name in city_manifest:
            active_city_bots.append(safe_name)
            moving_bots.append(safe_name)
            continue
        expires = float(row.get("bot_online_until", 0) or 0)
        if expires and now >= expires:
            players.pop(name, None)
            changed = True
            continue
        active_top_bots.append(safe_name)
        moving_bots.append(safe_name)

    min_active = int(settings.get("min_active", 1) or 1)
    max_active = int(settings.get("max_active", 5) or 5)
    if len(active_top_bots) > max_active:
        for safe_name in active_top_bots[max_active:]:
            players.pop(safe_name, None)
            changed = True
        active_top_bots = active_top_bots[:max_active]

    for safe_name in sorted(city_manifest.keys()):
        if safe_name in protected or safe_name in active_city_bots or safe_name in active_battle_users:
            continue
        row = shared_world_touch_player(safe_name, state, npc_bot=True)
        profile = shared_world_profile(safe_name)
        row["display_name"] = clean(profile.get("display_name", "")) or safe_name
        row["bot_online_until"] = 0
        row["bot_next_move_at"] = now + shared_world_npc_randint(2, 12)
        row["bot_next_invite_at"] = 0
        row["updated_at"] = utc_timestamp()
        players[safe_name] = row
        active_city_bots.append(safe_name)
        moving_bots.append(safe_name)
        changed = True

    top_candidates = [name for name in sorted(top_manifest.keys()) if normalize_username(name) not in protected]
    should_spawn = bool(top_candidates) and len(active_top_bots) < min_active
    if top_candidates and len(active_top_bots) < max_active and not should_spawn:
        should_spawn = shared_world_npc_randint(1, 100) <= int(settings.get("spawn_chance_percent", 55) or 55)
    if should_spawn:
        target_count = shared_world_npc_randint(max(min_active, len(active_top_bots) + 1), max_active)
        for safe_name in top_candidates:
            if len(active_top_bots) >= target_count:
                break
            if safe_name in active_top_bots or safe_name in active_battle_users:
                continue
            row = shared_world_touch_player(safe_name, state, npc_bot=True)
            profile = shared_world_profile(safe_name)
            row["display_name"] = clean(profile.get("display_name", "")) or clean(top_manifest.get(safe_name, {}).get("display_name", "")) or safe_name
            row["bot_online_until"] = now + shared_world_npc_randint(int(settings.get("online_min_minutes", 20)), int(settings.get("online_max_minutes", 40))) * 60
            row["bot_next_move_at"] = now + shared_world_npc_randint(2, 8)
            row["bot_next_invite_at"] = now + shared_world_npc_randint(int(settings.get("invite_cooldown_min_seconds", 70)), int(settings.get("invite_cooldown_max_seconds", 180)))
            row["updated_at"] = utc_timestamp()
            players[safe_name] = row
            active_top_bots.append(safe_name)
            moving_bots.append(safe_name)
            changed = True

    for safe_name in list(dict.fromkeys(moving_bots)):
        row = players.get(safe_name) if isinstance(players.get(safe_name), dict) else {}
        if not row:
            continue
        if now >= float(row.get("bot_next_move_at", 0) or 0) and safe_name not in active_battle_users:
            row["x"] = shared_world_clamp(row.get("tx", row.get("x", 0.5)))
            row["y"] = shared_world_clamp(row.get("ty", row.get("y", 0.5)))
            if shared_world_npc_randint(1, 100) <= 24:
                row["tx"] = row["x"]
                row["ty"] = row["y"]
            else:
                row["tx"] = shared_world_clamp(row["x"] + (shared_world_npc_randint(-18, 18) / 100.0), row["x"])
                row["ty"] = shared_world_clamp(row["y"] + (shared_world_npc_randint(-14, 14) / 100.0), row["y"])
            row["bot_next_move_at"] = now + shared_world_npc_randint(5, 16)
            row["updated_at"] = utc_timestamp()
            players[safe_name] = row
            changed = True
        if safe_name in top_manifest and now >= float(row.get("bot_next_invite_at", 0) or 0) and safe_name not in active_battle_users:
            row["bot_next_invite_at"] = now + shared_world_npc_randint(int(settings.get("invite_cooldown_min_seconds", 70)), int(settings.get("invite_cooldown_max_seconds", 180)))
            players[safe_name] = row
            changed = True
            if shared_world_npc_randint(1, 100) <= int(settings.get("invite_chance_percent", 8) or 8):
                targets = [name for name in real_players if name not in active_battle_users]
                if targets:
                    target = secrets.choice(targets)
                    try:
                        shared_world_battle_invite(
                            safe_name,
                            {
                                "target": target,
                                "game": "fireball_vocab",
                                "message": "Would you like to play Fireball Vocabulary Battle with me?",
                            },
                        )
                    except Exception:
                        pass
    if changed:
        state["_volatile_changed"] = True
    return changed
