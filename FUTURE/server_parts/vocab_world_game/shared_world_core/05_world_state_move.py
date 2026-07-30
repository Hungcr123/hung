def shared_world_active_battle_pairs() -> list[dict]:
    pairs: list[dict] = []
    try:
        with SHARED_WORLD_BATTLE_LOCK:
            state = load_shared_world_battle_state()
            changed = shared_world_battle_prune(state)
            if changed:
                write_shared_world_battle_state(state)
            battles = state.get("battles") if isinstance(state.get("battles"), dict) else {}
            for battle_id, battle in battles.items():
                if not isinstance(battle, dict) or clean(battle.get("status", "")) != "active":
                    continue
                players = [
                    normalize_username(item)
                    for item in (battle.get("players") if isinstance(battle.get("players"), list) else [])
                    if normalize_username(item)
                ]
                if len(players) >= 2:
                    pairs.append(
                        {
                            "id": clean(battle.get("id", "")) or clean(battle_id),
                            "game": clean(battle.get("game", "fireball_vocab")) or "fireball_vocab",
                            "players": players[:2],
                            "updated_at": clean(battle.get("updated_at", "")),
                        }
                    )
    except Exception:
        return []
    return pairs[:50]


def shared_world_state_for_user(username: str, real_username: str = "") -> dict:
    username = normalize_username(username)
    real_username = normalize_username(real_username) or username
    with SHARED_WORLD_LOCK:
        state = load_shared_world_state()
        state.pop("_volatile_changed", None)
        shared_world_touch_player(username, state, admin_actor=(username != real_username and shared_world_is_npc_identity(username)))
        shared_world_prune_players(state)
        shared_world_npc_bot_tick(state, real_username=real_username, protected_actor=(username if username != real_username else ""))
        if bool(state.get("_volatile_changed")):
            write_shared_world_state(state)
        players = state.get("players") if isinstance(state.get("players"), dict) else {}
        player_names = [normalize_username(name) for name in players.keys() if normalize_username(name)]
        meta_map = shared_world_leaderboard_meta_map(player_names)
        settings = load_server_settings()
        level_map = shared_world_level_meta_map(player_names, settings.get("qm_city_levels", DEFAULT_QM_CITY_LEVELS))
        rows = [
            shared_world_player_payload(name, row, meta_map, level_map)
            for name, row in players.items()
            if normalize_username(name)
        ]
    rows.sort(key=lambda item: clean(item.get("display_name", item.get("username", ""))).lower())
    with SHARED_WORLD_KEYBOARD_LOCK:
        keyboard_state = load_shared_world_keyboard_state()
        keyboard_pass = shared_world_keyboard_pass_for_user(username, keyboard_state)
    return {
        "world": {
            "players": rows,
            "me": username,
            "updated_at": utc_timestamp(),
            "keyboard_pass": keyboard_pass,
            "active_battles": shared_world_active_battle_pairs(),
        }
    }


def shared_world_move(username: str, payload: dict, real_username: str = "") -> dict:
    username = normalize_username(username)
    real_username = normalize_username(real_username) or username
    with SHARED_WORLD_LOCK:
        state = load_shared_world_state()
        row = shared_world_touch_player(username, state, admin_actor=(username != real_username and shared_world_is_npc_identity(username)))
        if payload.get("current_x") is not None or payload.get("current_y") is not None:
            row["x"] = shared_world_clamp(payload.get("current_x", row.get("x", 0.5)))
            row["y"] = shared_world_clamp(payload.get("current_y", row.get("y", 0.5)))
        row["tx"] = shared_world_clamp(payload.get("x", row.get("tx", row.get("x", 0.5))))
        row["ty"] = shared_world_clamp(payload.get("y", row.get("ty", row.get("y", 0.5))))
        row["updated_at"] = utc_timestamp()
        state.setdefault("players", {})[username] = row
        state["updated_at"] = utc_timestamp()
        write_shared_world_state(state)
    return shared_world_state_for_user(username, real_username=real_username)
