def shared_world_touch_player(username: str, state: dict, *, x: object = None, y: object = None, chat: object = None, admin_actor: object | None = None, npc_bot: object | None = None) -> dict:
    username = normalize_username(username)
    players = state.setdefault("players", {})
    row = players.get(username) if isinstance(players.get(username), dict) else {}
    changed = False
    if not row:
        sx, sy = shared_world_seed_position(username)
        row = {"x": sx, "y": sy, "tx": sx, "ty": sy}
        changed = True
    profile = shared_world_profile(username)
    display_name = clean(profile.get("display_name", "")) or username
    if row.get("username") != username:
        row["username"] = username
        changed = True
    if clean(row.get("display_name", "")) != display_name:
        row["display_name"] = display_name
        changed = True
    if x is not None or y is not None:
        next_x = shared_world_clamp(x if x is not None else row.get("tx", row.get("x", 0.5)))
        next_y = shared_world_clamp(y if y is not None else row.get("ty", row.get("y", 0.5)))
        if row.get("x") != next_x or row.get("y") != next_y or row.get("tx") != next_x or row.get("ty") != next_y:
            row["x"] = next_x
            row["y"] = next_y
            row["tx"] = next_x
            row["ty"] = next_y
            changed = True
    if chat is not None:
        row["chat"] = lesson_task_notice_text(chat, limit=160)
        row["chat_at"] = utc_timestamp()
        changed = True
    if admin_actor is not None:
        should_mark_admin_actor = bool(admin_actor)
        if should_mark_admin_actor:
            if row.get("admin_actor") is not True:
                row["admin_actor"] = True
                changed = True
        elif row.pop("admin_actor", None) is not None:
            changed = True
    if npc_bot is not None:
        should_mark_bot = bool(npc_bot)
        if should_mark_bot:
            if row.get("npc_bot") is not True:
                row["npc_bot"] = True
                changed = True
        elif row.pop("npc_bot", None) is not None:
            changed = True
    updated_epoch = timestamp_to_epoch(clean(row.get("updated_at", "")))
    if changed or not updated_epoch or time.time() - updated_epoch > 18:
        row["updated_at"] = utc_timestamp()
        state["_volatile_changed"] = True
    players[username] = row
    return row


def shared_world_prune_players(state: dict, max_age_seconds: int = 360) -> int:
    players = state.setdefault("players", {})
    now = time.time()
    removed = 0
    for username in list(players.keys()):
        row = players.get(username) if isinstance(players.get(username), dict) else {}
        updated = timestamp_to_epoch(clean(row.get("updated_at", "")))
        if updated and now - updated > max_age_seconds:
            players.pop(username, None)
            removed += 1
    if removed:
        state["_volatile_changed"] = True
    return removed
