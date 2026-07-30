def shared_world_battle_new_id(prefix: str = "battle") -> str:
    return f"{prefix}_{int(time.time() * 1000)}_{secrets.token_hex(5)}"


def shared_world_battle_other(battle: dict, username: str) -> str:
    username = normalize_username(username)
    for player in battle.get("players") if isinstance(battle.get("players"), list) else []:
        player = normalize_username(player)
        if player and player != username:
            return player
    return ""


def shared_world_battle_start_turn(battle: dict, username: str) -> None:
    username = normalize_username(username)
    battle["turn"] = username
    battle["phase"] = "question"
    battle["question"] = shared_world_battle_pick_question(username, battle)
    battle["deadline_at"] = local_timestamp(time.time() + 30)
    battle.pop("next_turn_after_reveal", None)
    battle["updated_at"] = utc_timestamp()


def shared_world_battle_reveal_answer(battle: dict, next_turn: str, reason: str = "") -> None:
    question = battle.get("question") if isinstance(battle.get("question"), dict) else {}
    answer_text = clean(question.get("answer_text", "")) or clean(question.get("answer", ""))
    battle["phase"] = "reveal"
    battle["turn"] = ""
    battle["next_turn_after_reveal"] = normalize_username(next_turn)
    battle["deadline_at"] = local_timestamp(time.time() + 3)
    battle["updated_at"] = utc_timestamp()
    log = battle.setdefault("log", [])
    if not isinstance(log, list):
        log = []
    log.append({"at": utc_timestamp(), "type": "reveal", "text": reason or f"No one answered. Correct answer: {answer_text}."})
    battle["log"] = log[-40:]


def shared_world_battle_transfer_crystals(winner: str, loser: str, amount: int = 2) -> dict:
    winner = normalize_username(winner)
    loser = normalize_username(loser)
    amount = max(0, min(20, int(amount or 0)))
    if not winner or not loser or winner == loser or amount <= 0:
        return {"transferred": 0, "items": []}
    winner_is_npc = shared_world_is_npc_identity(winner)
    loser_is_npc = shared_world_is_npc_identity(loser)
    if winner_is_npc:
        return {"transferred": 0, "items": [], "symbolic": True}
    if loser_is_npc:
        item_id = "leaderboard_space_v_crystal"
        item = {
            "id": item_id,
            "name": "Golden Axe",
            "use": "A QM-City battle reward earned from vocabulary play.",
            "quantity": amount,
        }
        with INVENTORY_LOCK:
            winner_payload = read_inventory_file(winner)
            winner_items = winner_payload.setdefault("items", {})
            current = normalize_inventory_item(winner_items.get(item_id, {}))
            current["id"] = item_id
            current["name"] = item["name"]
            current["use"] = item["use"]
            current["quantity"] = max(0, int(current.get("quantity", 0) or 0)) + amount
            current["updated_at"] = utc_timestamp()
            winner_items[item_id] = current
            winner_payload["events"] = (winner_payload.get("events") if isinstance(winner_payload.get("events"), list) else [])[-4990:] + [f"qm-city-battle-win:npc:{loser}:{time.time_ns()}"]
            write_inventory_file(winner, winner_payload)
        return {"transferred": amount, "items": [item], "symbolic_source": True}
    moved: list[dict] = []
    with INVENTORY_LOCK:
        loser_payload = read_inventory_file(loser)
        winner_payload = read_inventory_file(winner)
        loser_items = loser_payload.setdefault("items", {})
        winner_items = winner_payload.setdefault("items", {})
        remaining = amount
        candidates = [
            normalize_inventory_item(item)
            for item in loser_items.values()
            if isinstance(item, dict)
            and int(item.get("quantity", 0) or 0) > 0
            and not clean_inventory_item_id(item.get("id", "")).startswith("leaderboard_badge")
        ]
        candidates.sort(key=lambda item: item.get("id", ""))
        for item in candidates:
            if remaining <= 0:
                break
            take = min(remaining, int(item.get("quantity", 0) or 0))
            if take <= 0:
                continue
            loser_current = normalize_inventory_item(loser_items.get(item["id"], {}))
            loser_current["quantity"] = max(0, int(loser_current.get("quantity", 0) or 0) - take)
            loser_items[item["id"]] = loser_current
            winner_current = normalize_inventory_item(winner_items.get(item["id"], {}))
            winner_current["id"] = item["id"]
            winner_current["name"] = item.get("name") or winner_current.get("name") or "Golden Axe"
            winner_current["use"] = item.get("use") or winner_current.get("use") or "Stores learning energy for future item upgrades."
            winner_current["quantity"] = max(0, int(winner_current.get("quantity", 0) or 0)) + take
            winner_current["updated_at"] = utc_timestamp()
            winner_items[item["id"]] = winner_current
            moved.append({"id": item["id"], "name": item.get("name", "Crystal"), "quantity": take})
            remaining -= take
        if moved:
            loser_payload["events"] = (loser_payload.get("events") if isinstance(loser_payload.get("events"), list) else [])[-4990:] + [f"qm-city-battle-lost:{winner}:{time.time_ns()}"]
            winner_payload["events"] = (winner_payload.get("events") if isinstance(winner_payload.get("events"), list) else [])[-4990:] + [f"qm-city-battle-win:{loser}:{time.time_ns()}"]
            write_inventory_file(loser, loser_payload)
            write_inventory_file(winner, winner_payload)
    return {"transferred": sum(int(item.get("quantity", 0) or 0) for item in moved), "items": moved}


def shared_world_battle_apply_damage(battle: dict, attacker: str, target: str, damage: int) -> int:
    attacker = normalize_username(attacker)
    target = normalize_username(target)
    hp = battle.setdefault("hp", {})
    buffs = battle.setdefault("buffs", {})
    safe_damage = max(0, int(damage or 0))
    target_buff = buffs.setdefault(target, {})
    if bool(target_buff.get("shield_next")) and safe_damage > 0:
        safe_damage = max(1, math.ceil(safe_damage / 2))
        target_buff["shield_next"] = False
    hp[target] = max(0, int(hp.get(target, 100) or 100) - safe_damage)
    return safe_damage


def shared_world_battle_finish(battle: dict, winner: str, loser: str, reason: str = "") -> None:
    if clean(battle.get("status", "")) == "finished":
        return
    winner = normalize_username(winner)
    loser = normalize_username(loser)
    battle["status"] = "finished"
    battle["winner"] = winner
    battle["loser"] = loser
    battle["message"] = reason or f"{winner} wins."
    battle["finished_at"] = utc_timestamp()
    battle["deadline_at"] = ""
    battle["_force_persist"] = True
    battle["reward"] = shared_world_battle_transfer_crystals(winner, loser, max(0, space_w_int(battle.get("wager", 2), 2)))
    log = battle.setdefault("log", [])
    if isinstance(log, list):
        log.append({"at": utc_timestamp(), "type": "finish", "text": battle["message"]})
        battle["log"] = log[-40:]
    shared_world_battle_flush_word_history(battle)


def shared_world_battle_check_hp(battle: dict) -> None:
    hp = battle.get("hp") if isinstance(battle.get("hp"), dict) else {}
    players = [normalize_username(item) for item in (battle.get("players") if isinstance(battle.get("players"), list) else []) if normalize_username(item)]
    for player in players:
        if int(hp.get(player, 100) or 0) <= 0:
            winner = next((item for item in players if item != player), "")
            if winner:
                shared_world_battle_finish(battle, winner, player, f"{winner} wins the fireball battle.")
            return
