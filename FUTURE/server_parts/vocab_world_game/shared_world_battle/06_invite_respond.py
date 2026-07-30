def shared_world_battle_create_from_invite(state: dict, invite: dict, auto: bool = False) -> dict:
    challenger = normalize_username(invite.get("from", ""))
    opponent = normalize_username(invite.get("to", ""))
    if not challenger or not opponent or challenger == opponent:
        raise RuntimeError("Invalid battle invite.")
    if shared_world_battle_active_for_user(state, challenger) or shared_world_battle_active_for_user(state, opponent):
        raise RuntimeError("One player is already in a battle.")
    game = clean(invite.get("game", "fireball_vocab")) or "fireball_vocab"
    shared_world_battle_vocab_pool(challenger)
    shared_world_battle_vocab_pool(opponent)
    battle_id = shared_world_battle_new_id("battle")
    battle = {
        "id": battle_id,
        "game": game,
        "status": "active",
        "players": [challenger, opponent],
        "npc_bots": [
            player for player in (challenger, opponent)
            if player in shared_world_npc_bot_names_snapshot()
            or shared_world_is_npc_identity(player)
            or (player == challenger and bool(invite.get("npc_bot_from")))
            or (player == opponent and bool(invite.get("npc_bot_to")))
        ],
        "hp": {challenger: 100, opponent: 100},
        "mp": {challenger: 0, opponent: 0},
        "buffs": {challenger: {}, opponent: {}},
        "recent_words": {challenger: [], opponent: []},
        "asked_words": {challenger: [], opponent: []},
        "wager": max(0, space_w_int((SHARED_WORLD_BATTLE_GAMES.get(game) or {}).get("wager", 2), 2)),
        "created_at": utc_timestamp(),
        "updated_at": utc_timestamp(),
        "log": [{"at": utc_timestamp(), "type": "start", "text": "Fireball battle started." + (" Auto accepted." if auto else "")}],
    }
    first_turn = [challenger, opponent][secrets.randbelow(2)]
    battle["first_turn"] = first_turn
    battle["log"].append({"at": utc_timestamp(), "type": "coin", "text": f"Coin flip: {first_turn} starts first."})
    shared_world_battle_start_turn(battle, first_turn)
    shared_world_battle_refresh_npc_players(battle)
    state.setdefault("battles", {})[battle_id] = battle
    invite["status"] = "accepted"
    invite["battle_id"] = battle_id
    invite["accepted_at"] = utc_timestamp()
    state.setdefault("declines", {}).pop(opponent, None)
    return battle


def shared_world_battle_invite(username: str, payload: dict) -> dict:
    username = normalize_username(username)
    target = normalize_username((payload if isinstance(payload, dict) else {}).get("target", ""))
    game = clean((payload if isinstance(payload, dict) else {}).get("game", "fireball_vocab")) or "fireball_vocab"
    if game not in SHARED_WORLD_BATTLE_GAMES:
        raise RuntimeError("Unknown QM-City game.")
    if not target or target == username:
        raise RuntimeError("Choose another player.")
    message = lesson_task_notice_text((payload if isinstance(payload, dict) else {}).get("message", ""), limit=180) or SHARED_WORLD_BATTLE_GAMES[game]["prompt"]
    with SHARED_WORLD_BATTLE_LOCK:
        state = load_shared_world_battle_state()
        shared_world_battle_prune(state)
        if shared_world_battle_active_for_user(state, username) or shared_world_battle_active_for_user(state, target):
            raise RuntimeError("A player is already in a battle.")
        npc_bots = shared_world_npc_bot_names_snapshot()
        username_is_npc = username in npc_bots or shared_world_is_npc_identity(username)
        target_is_npc = target in npc_bots or shared_world_is_npc_identity(target)
        invite_id = shared_world_battle_new_id("invite")
        invite = {
            "id": invite_id,
            "from": username,
            "to": target,
            "game": game,
            "game_name": SHARED_WORLD_BATTLE_GAMES[game]["name"],
            "message": message,
            "status": "pending",
            "created_at": utc_timestamp(),
        }
        if username_is_npc:
            invite["npc_bot_from"] = True
        if target_is_npc:
            invite["npc_bot_to"] = True
        state.setdefault("invites", {})[invite_id] = invite
        decline = state.setdefault("declines", {}).get(target)
        battle = None
        if target_is_npc:
            battle = shared_world_battle_create_from_invite(state, invite, auto=True)
        elif isinstance(decline, dict) and int(decline.get("count", 0) or 0) >= 1 and normalize_username(decline.get("from", "")) != username:
            battle = shared_world_battle_create_from_invite(state, invite, auto=True)
        write_shared_world_battle_state(state)
    return {"invite": shared_world_battle_public_invite(invite), "battle": shared_world_battle_public_payload(battle, username), **shared_world_battle_state_for_user(username)}


def shared_world_battle_respond(username: str, payload: dict) -> dict:
    username = normalize_username(username)
    invite_id = clean((payload if isinstance(payload, dict) else {}).get("invite_id", ""))
    accept = bool((payload if isinstance(payload, dict) else {}).get("accept", False))
    with SHARED_WORLD_BATTLE_LOCK:
        state = load_shared_world_battle_state()
        shared_world_battle_prune(state)
        invite = (state.get("invites") if isinstance(state.get("invites"), dict) else {}).get(invite_id)
        if not isinstance(invite, dict) or clean(invite.get("status", "")) != "pending":
            raise RuntimeError("Invite is no longer available.")
        if normalize_username(invite.get("to", "")) != username:
            raise RuntimeError("This invite is not for you.")
        decline = state.setdefault("declines", {}).get(username)
        forced_accept = (not accept) and isinstance(decline, dict) and int(decline.get("count", 0) or 0) >= 1
        battle = None
        if accept or forced_accept:
            battle = shared_world_battle_create_from_invite(state, invite, auto=forced_accept)
        else:
            invite["status"] = "declined"
            invite["declined_at"] = utc_timestamp()
            state.setdefault("declines", {})[username] = {
                "from": normalize_username(invite.get("from", "")),
                "count": int((decline or {}).get("count", 0) or 0) + 1,
                "updated_at": utc_timestamp(),
            }
        write_shared_world_battle_state(state)
    return {"battle": shared_world_battle_public_payload(battle, username), "forced_accept": forced_accept, **shared_world_battle_state_for_user(username)}
