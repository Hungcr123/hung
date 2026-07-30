def shared_world_battle_apply_answer_locked(battle: dict, username: str, answer: str) -> bool:
    username = normalize_username(username)
    question = battle.get("question") if isinstance(battle.get("question"), dict) else {}
    correct = shared_world_battle_question_answer_matches(answer, question)
    mp = battle.setdefault("mp", {})
    buffs = battle.setdefault("buffs", {})
    log = battle.setdefault("log", [])
    if not isinstance(log, list):
        log = []
    opponent = shared_world_battle_other(battle, username)
    if correct:
        if clean(battle.get("phase", "question")) == "steal":
            mp[username] = min(100, int(mp.get(username, 0) or 0) + 10)
            log.append({"at": utc_timestamp(), "type": "steal", "text": f"{username} stole the word and gained 10 mana."})
            shared_world_battle_start_turn(battle, username)
        else:
            buff = buffs.setdefault(username, {})
            triple_hit = bool(buff.get("triple_next"))
            damage = 30 if triple_hit else 10
            buff["triple_next"] = False
            damage = shared_world_battle_apply_damage(battle, username, opponent, damage)
            mp[username] = min(100, int(mp.get(username, 0) or 0) + 25)
            attack_effect = "inferno" if triple_hit else secrets.choice(["fireball", "fireball", "laser"])
            loot = shared_world_battle_transfer_crystals(username, opponent, 1)
            log.append({
                "at": utc_timestamp(),
                "type": "hit",
                "attacker": username,
                "target": opponent,
                "damage": damage,
                "effect": attack_effect,
                "loot": loot,
                "text": f"{username} hit {opponent} with {attack_effect} for {damage} damage."
                + (f" Stole {int(loot.get('transferred', 0) or 0)} crystal." if int(loot.get("transferred", 0) or 0) > 0 else ""),
            })
            shared_world_battle_check_hp(battle)
            if clean(battle.get("status", "")) == "active":
                shared_world_battle_start_turn(battle, opponent)
    else:
        if clean(battle.get("phase", "question")) == "steal":
            log.append({"at": utc_timestamp(), "type": "miss", "text": f"{username} skipped the steal chance." if not answer else f"{username} missed the steal chance."})
            battle["log"] = log[-40:]
            shared_world_battle_reveal_answer(battle, username, "No one answered. Revealing the correct word.")
        else:
            log.append({"at": utc_timestamp(), "type": "miss", "text": f"{username} skipped the turn. {opponent} can steal for mana." if not answer else f"{username} missed. {opponent} can steal for mana."})
            battle["phase"] = "steal"
            battle["turn"] = opponent
            battle["deadline_at"] = local_timestamp(time.time() + 30)
            battle["updated_at"] = utc_timestamp()
    if clean(battle.get("phase", "")) != "reveal":
        battle["log"] = log[-40:]
    battle["updated_at"] = utc_timestamp()
    return bool(correct)


def shared_world_battle_answer(username: str, payload: dict) -> dict:
    username = normalize_username(username)
    battle_id = clean((payload if isinstance(payload, dict) else {}).get("battle_id", ""))
    answer = clean((payload if isinstance(payload, dict) else {}).get("answer", ""))
    with SHARED_WORLD_BATTLE_LOCK:
        state = load_shared_world_battle_state()
        shared_world_battle_prune(state)
        battle = (state.get("battles") if isinstance(state.get("battles"), dict) else {}).get(battle_id)
        if not isinstance(battle, dict) or clean(battle.get("status", "")) != "active":
            raise RuntimeError("Battle is not active.")
        players = [normalize_username(item) for item in (battle.get("players") if isinstance(battle.get("players"), list) else [])]
        if username not in players:
            raise RuntimeError("You are not in this battle.")
        if normalize_username(battle.get("turn", "")) != username:
            raise RuntimeError("Not your turn.")
        shared_world_battle_apply_answer_locked(battle, username, answer)
        write_shared_world_battle_state(state)
    return shared_world_battle_state_for_user(username)


def shared_world_battle_apply_skill_locked(battle: dict, username: str, skill: str) -> bool:
    username = normalize_username(username)
    skill = clean(skill).lower()
    players = [normalize_username(item) for item in (battle.get("players") if isinstance(battle.get("players"), list) else [])]
    if username not in players:
        return False
    mp = battle.setdefault("mp", {})
    hp = battle.setdefault("hp", {})
    buffs = battle.setdefault("buffs", {})
    if int(mp.get(username, 0) or 0) < 100:
        return False
    opponent = shared_world_battle_other(battle, username)
    log = battle.setdefault("log", [])
    if not isinstance(log, list):
        log = []
    mp[username] = 0
    if skill in {"inferno", "triple"}:
        buffs.setdefault(username, {})["triple_next"] = True
        log.append({"at": utc_timestamp(), "type": "skill", "skill": "inferno", "caster": username, "effect": "inferno", "text": f"{username} charged Inferno. The next correct hit deals triple damage."})
    elif skill == "meteor":
        damage = shared_world_battle_apply_damage(battle, username, opponent, 25)
        log.append({
            "at": utc_timestamp(),
            "type": "hit",
            "skill": "meteor",
            "attacker": username,
            "target": opponent,
            "damage": damage,
            "effect": "meteor",
            "loot": {"transferred": 0, "items": []},
            "text": f"{username} called a Meteor Strike on {opponent} for {damage} damage.",
        })
        shared_world_battle_check_hp(battle)
    elif skill == "shield":
        buffs.setdefault(username, {})["shield_next"] = True
        log.append({"at": utc_timestamp(), "type": "skill", "skill": "shield", "caster": username, "effect": "shield", "text": f"{username} raised a Crystal Guard. The next incoming hit is reduced."})
    elif skill == "drain":
        stolen = min(50, max(0, int(mp.get(opponent, 0) or 0)))
        mp[opponent] = max(0, int(mp.get(opponent, 0) or 0) - stolen)
        mp[username] = min(100, int(mp.get(username, 0) or 0) + max(0, stolen // 2))
        log.append({"at": utc_timestamp(), "type": "skill", "skill": "drain", "caster": username, "target": opponent, "effect": "drain", "text": f"{username} drained {stolen} MP from {opponent}."})
    elif skill in {"phoenix", "heal"}:
        recovered = min(45, max(0, 100 - int(hp.get(username, 100) or 100)))
        hp[username] = min(100, int(hp.get(username, 100) or 100) + 45)
        buffs.setdefault(username, {}).pop("shield_next", None)
        log.append({"at": utc_timestamp(), "type": "skill", "skill": "phoenix", "caster": username, "effect": "heal", "text": f"{username} used Phoenix Pulse and recovered {recovered} HP."})
    else:
        return False
    battle["log"] = log[-40:]
    battle["updated_at"] = utc_timestamp()
    return True


def shared_world_battle_skill(username: str, payload: dict) -> dict:
    username = normalize_username(username)
    battle_id = clean((payload if isinstance(payload, dict) else {}).get("battle_id", ""))
    skill = clean((payload if isinstance(payload, dict) else {}).get("skill", "")).lower()
    with SHARED_WORLD_BATTLE_LOCK:
        state = load_shared_world_battle_state()
        shared_world_battle_prune(state)
        battle = (state.get("battles") if isinstance(state.get("battles"), dict) else {}).get(battle_id)
        if not isinstance(battle, dict) or clean(battle.get("status", "")) != "active":
            raise RuntimeError("Battle is not active.")
        players = [normalize_username(item) for item in (battle.get("players") if isinstance(battle.get("players"), list) else [])]
        if username not in players:
            raise RuntimeError("You are not in this battle.")
        if int((battle.get("mp") if isinstance(battle.get("mp"), dict) else {}).get(username, 0) or 0) < 100:
            raise RuntimeError("Mana is not full.")
        if not shared_world_battle_apply_skill_locked(battle, username, skill):
            raise RuntimeError("Unknown battle skill.")
        write_shared_world_battle_state(state)
    return shared_world_battle_state_for_user(username)


def shared_world_battle_forfeit(username: str, payload: dict) -> dict:
    username = normalize_username(username)
    battle_id = clean((payload if isinstance(payload, dict) else {}).get("battle_id", ""))
    with SHARED_WORLD_BATTLE_LOCK:
        state = load_shared_world_battle_state()
        battle = (state.get("battles") if isinstance(state.get("battles"), dict) else {}).get(battle_id)
        if not isinstance(battle, dict) or clean(battle.get("status", "")) != "active":
            return shared_world_battle_state_for_user(username)
        players = [normalize_username(item) for item in (battle.get("players") if isinstance(battle.get("players"), list) else [])]
        if username not in players:
            raise RuntimeError("You are not in this battle.")
        winner = shared_world_battle_other(battle, username)
        shared_world_battle_finish(battle, winner, username, f"{username} left the battle and lost by forfeit.")
        write_shared_world_battle_state(state)
    return shared_world_battle_state_for_user(username)
