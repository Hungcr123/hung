def shared_world_battle_target_running(battle: dict, username: str) -> bool:
    username = normalize_username(username)
    movement = battle.get("movement") if isinstance(battle.get("movement"), dict) else {}
    row = movement.get(username) if isinstance(movement.get(username), dict) else {}
    until_epoch = float(row.get("running_until_epoch", 0.0) or 0.0)
    if until_epoch <= time.time():
        return False
    distance = float(row.get("distance", 0.0) or 0.0)
    return distance >= 0.006

def shared_world_battle_roll_running_dodge(battle: dict, target: str, effect: str) -> dict | None:
    effect_key = clean(effect).lower()
    if effect_key not in {"basic_attack", "ultimate", "inferno", "triple"}:
        return None
    if not shared_world_battle_target_running(battle, target):
        return None
    chance = 0.2 if effect_key in {"ultimate", "inferno", "triple"} else 0.5
    if secrets.randbelow(10000) >= int(chance * 10000):
        return None
    side = "left" if secrets.randbelow(2) == 0 else "right"
    return {
        "chance": chance,
        "side": side,
        "offset_x": -0.055 if side == "left" else 0.055,
        "offset_y": -0.012,
    }

def shared_world_battle_dodge_log_row(
    attacker: str,
    target: str,
    effect: str,
    dodge: dict,
    client_action_id: str = "",
) -> dict:
    effect_key = clean(effect).lower() or "basic_attack"
    chance = float((dodge or {}).get("chance", 0.0) or 0.0)
    side = clean((dodge or {}).get("side", "right")).lower()
    if side not in {"left", "right"}:
        side = "right"
    return {
        "at": utc_timestamp(),
        "type": "miss",
        "attacker": normalize_username(attacker),
        "target": normalize_username(target),
        "damage": 0,
        "effect": effect_key,
        "skill": "ultimate" if effect_key in {"ultimate", "inferno", "triple"} else "basic_attack",
        "missed": True,
        "dodged": True,
        "dodge_chance": chance,
        "dodgeChance": chance,
        "impact_offset_side": side,
        "impactOffsetSide": side,
        "impact_offset_x": float((dodge or {}).get("offset_x", 0.055) or 0.055),
        "impactOffsetX": float((dodge or {}).get("offset_x", 0.055) or 0.055),
        "impact_offset_y": float((dodge or {}).get("offset_y", -0.012) or -0.012),
        "impactOffsetY": float((dodge or {}).get("offset_y", -0.012) or -0.012),
        "client_action_id": clean(client_action_id)[:96],
        "text": f"{normalize_username(target)} dodged {normalize_username(attacker)}'s {'Skill Nộ' if effect_key in {'ultimate', 'inferno', 'triple'} else 'Basic Skill'}. MISS.",
    }

def shared_world_battle_apply_answer_locked(
    battle: dict,
    username: str,
    answer: str,
    client_action_id: str = "",
    defer_next_question: bool = False,
) -> bool:
    username = normalize_username(username)
    free_combat = clean(battle.get("phase", "")) == "free"
    questions = battle.get("questions") if isinstance(battle.get("questions"), dict) else {}
    question = questions.get(username) if free_combat and isinstance(questions.get(username), dict) else (battle.get("question") if isinstance(battle.get("question"), dict) else {})
    correct = shared_world_battle_question_answer_matches(answer, question)
    mp = battle.setdefault("mp", {})
    buffs = battle.setdefault("buffs", {})
    log = battle.setdefault("log", [])
    if not isinstance(log, list):
        log = []
    opponent = shared_world_battle_other(battle, username)
    if free_combat:
        if correct:
            buff = buffs.setdefault(username, {})
            triple_hit = bool(buff.get("triple_next"))
            damage = 30 if triple_hit else 10
            buff["triple_next"] = False
            attack_effect = "ultimate" if triple_hit else "basic_attack"
            mp[username] = min(100, int(mp.get(username, 0) or 0) + 10)
            dodge = shared_world_battle_roll_running_dodge(battle, opponent, attack_effect)
            if dodge:
                log.append(shared_world_battle_dodge_log_row(
                    username,
                    opponent,
                    attack_effect,
                    dodge,
                    client_action_id=client_action_id,
                ))
                if clean(battle.get("status", "")) == "active":
                    questions[username] = {} if defer_next_question else shared_world_battle_pick_question(username, battle)
                    battle["questions"] = questions
                    pending_refreshes = battle.setdefault("question_refresh_pending", {})
                    if defer_next_question:
                        pending_refreshes[username] = {
                            "request_id": f"answer_{clean(client_action_id)[:89]}",
                            "created_epoch": time.time(),
                        }
                    else:
                        pending_refreshes.pop(username, None)
                battle["log"] = log[-40:]
                battle["updated_at"] = utc_timestamp()
                return True
            damage = shared_world_battle_apply_damage(battle, username, opponent, damage)
            loot = shared_world_battle_schedule_settlement(
                battle, username, opponent, 1, "hit", clean(client_action_id) or secrets.token_hex(8),
            )
            log.append({
                "at": utc_timestamp(), "type": "hit", "attacker": username, "target": opponent,
                "damage": damage, "effect": attack_effect, "loot": loot,
                "settlement_id": clean(loot.get("settlement_id", "")),
                "client_action_id": clean(client_action_id)[:96],
                "text": f"{username} hit {opponent} with {attack_effect} for {damage} damage."
                + (f" Stole {int(loot.get('transferred', 0) or 0)} crystal." if int(loot.get("transferred", 0) or 0) > 0 else ""),
            })
            shared_world_battle_check_hp(battle)
        else:
            opponent_mana_before = max(0, int(mp.get(opponent, 0) or 0))
            mp[opponent] = min(100, opponent_mana_before + 10)
            opponent_mana_gain = mp[opponent] - opponent_mana_before
            log.append({
                "at": utc_timestamp(), "type": "miss", "attacker": username, "target": opponent,
                "damage": 0, "effect": "basic_attack", "missed": True,
                "client_action_id": clean(client_action_id)[:96],
                "mana_target": opponent, "mana_gain": opponent_mana_gain,
                "text": f"{username} attacked but missed. {opponent} gained {opponent_mana_gain} mana.",
            })
        if clean(battle.get("status", "")) == "active":
            questions[username] = {} if defer_next_question else shared_world_battle_pick_question(username, battle)
            battle["questions"] = questions
            pending_refreshes = battle.setdefault("question_refresh_pending", {})
            if defer_next_question:
                pending_refreshes[username] = {
                    "request_id": f"answer_{clean(client_action_id)[:89]}",
                    "created_epoch": time.time(),
                }
            else:
                pending_refreshes.pop(username, None)
        battle["log"] = log[-40:]
        battle["updated_at"] = utc_timestamp()
        return bool(correct)
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
            attack_effect = "ultimate" if triple_hit else "basic_attack"
            mp[username] = min(100, int(mp.get(username, 0) or 0) + 10)
            dodge = shared_world_battle_roll_running_dodge(battle, opponent, attack_effect)
            if dodge:
                log.append(shared_world_battle_dodge_log_row(username, opponent, attack_effect, dodge))
                if clean(battle.get("status", "")) == "active":
                    shared_world_battle_start_turn(battle, opponent)
                if clean(battle.get("phase", "")) != "reveal":
                    battle["log"] = log[-40:]
                battle["updated_at"] = utc_timestamp()
                return True
            damage = shared_world_battle_apply_damage(battle, username, opponent, damage)
            loot = shared_world_battle_schedule_settlement(
                battle, username, opponent, 1, "hit", clean(client_action_id) or secrets.token_hex(8),
            )
            log.append({
                "at": utc_timestamp(),
                "type": "hit",
                "attacker": username,
                "target": opponent,
                "damage": damage,
                "effect": attack_effect,
                "loot": loot,
                "settlement_id": clean(loot.get("settlement_id", "")),
                "text": f"{username} hit {opponent} with {attack_effect} for {damage} damage."
                + (f" Stole {int(loot.get('transferred', 0) or 0)} crystal." if int(loot.get("transferred", 0) or 0) > 0 else ""),
            })
            shared_world_battle_check_hp(battle)
            if clean(battle.get("status", "")) == "active":
                shared_world_battle_start_turn(battle, opponent)
    else:
        if clean(battle.get("phase", "question")) == "steal":
            opponent_mana_before = max(0, int(mp.get(opponent, 0) or 0))
            mp[opponent] = min(100, opponent_mana_before + 10)
            opponent_mana_gain = mp[opponent] - opponent_mana_before
            log.append({
                "at": utc_timestamp(),
                "type": "miss",
                "attacker": username,
                "target": opponent,
                "damage": 0,
                "effect": "basic_attack",
                "missed": True,
                "mana_target": opponent,
                "mana_gain": opponent_mana_gain,
                "text": (f"{username} skipped the steal chance." if not answer else f"{username} attacked but missed the steal chance.")
                + f" {opponent} gained {opponent_mana_gain} mana.",
            })
            battle["log"] = log[-40:]
            shared_world_battle_reveal_answer(battle, username, "No one answered. Revealing the correct word.")
        else:
            opponent_mana_before = max(0, int(mp.get(opponent, 0) or 0))
            mp[opponent] = min(100, opponent_mana_before + 10)
            opponent_mana_gain = mp[opponent] - opponent_mana_before
            log.append({
                "at": utc_timestamp(),
                "type": "miss",
                "attacker": username,
                "target": opponent,
                "damage": 0,
                "effect": "basic_attack",
                "missed": True,
                "mana_target": opponent,
                "mana_gain": opponent_mana_gain,
                "text": (f"{username} skipped the turn. {opponent} can steal for mana." if not answer else f"{username} attacked but missed. {opponent} can steal for mana.")
                + f" {opponent} gained {opponent_mana_gain} mana.",
            })
            battle["phase"] = "steal"
            battle["turn"] = opponent
            battle["deadline_at"] = local_timestamp(time.time() + 30)
            battle["updated_at"] = utc_timestamp()
    if clean(battle.get("phase", "")) != "reveal":
        battle["log"] = log[-40:]
    battle["updated_at"] = utc_timestamp()
    return bool(correct)


def shared_world_battle_answer(username: str, payload: dict) -> dict:
    request_started = time.perf_counter()
    username = normalize_username(username)
    battle_id = clean((payload if isinstance(payload, dict) else {}).get("battle_id", ""))
    answer = clean((payload if isinstance(payload, dict) else {}).get("answer", ""))
    source_payload = payload if isinstance(payload, dict) else {}
    client_action_id = clean(source_payload.get("client_action_id", source_payload.get("clientActionId", "")))[:96]
    defer_next_question = bool(source_payload.get("defer_next_question", source_payload.get("deferNextQuestion", False)))
    lock_started = time.perf_counter()
    with SHARED_WORLD_BATTLE_LOCK:
        lock_wait_ms = (time.perf_counter() - lock_started) * 1000
        state = shared_world_battle_ram_state_required()
        shared_world_battle_prune(state)
        battle = (state.get("battles") if isinstance(state.get("battles"), dict) else {}).get(battle_id)
        if not isinstance(battle, dict) or clean(battle.get("status", "")) != "active":
            raise RuntimeError("Battle is not active.")
        players = [normalize_username(item) for item in (battle.get("players") if isinstance(battle.get("players"), list) else [])]
        if username not in players:
            raise RuntimeError("You are not in this battle.")
        if not shared_world_battle_all_players_ready(battle):
            raise RuntimeError("Waiting for both players to enter the Battle arena.")
        mutation_started = time.perf_counter()
        shared_world_battle_apply_answer_locked(
            battle,
            username,
            answer,
            client_action_id=client_action_id,
            defer_next_question=defer_next_question,
        )
        mutation_ms = (time.perf_counter() - mutation_started) * 1000
        finished = clean(battle.get("status", "")) == "finished"
        persist_started = time.perf_counter()
        revision = write_shared_world_battle_state(state, notify_users=players)
        persist_ms = (time.perf_counter() - persist_started) * 1000
    result = shared_world_battle_state_for_user(username)
    total_ms = (time.perf_counter() - request_started) * 1000
    if finished or total_ms >= 250:
        stt_debug_log(
            "shared_world_battle_answer_timing",
            user=username, battle_id=battle_id, finished=finished,
            realtime_revision=revision, lock_wait_ms=round(lock_wait_ms, 3),
            mutation_ms=round(mutation_ms, 3), persist_ms=round(persist_ms, 3),
            total_ms=round(total_ms, 3),
        )
    return result


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
    # 2026-08-13: PvP owns a separate 0-100 combat meter; Nộ consumes it completely.
    mp[username] = 0
    if skill in {"inferno", "triple", "ultimate"}:
        buffs.setdefault(username, {})["triple_next"] = False
        dodge = shared_world_battle_roll_running_dodge(battle, opponent, "ultimate")
        if dodge:
            log.append(shared_world_battle_dodge_log_row(username, opponent, "ultimate", dodge))
        else:
            damage = shared_world_battle_apply_damage(battle, username, opponent, 35)
            log.append({
                "at": utc_timestamp(),
                "type": "hit",
                "skill": "ultimate",
                "attacker": username,
                "target": opponent,
                "damage": damage,
                "effect": "ultimate",
                "loot": {"transferred": 0, "items": []},
                "text": f"{username} used Skill Nộ on {opponent} for {damage} damage.",
            })
            shared_world_battle_check_hp(battle)
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
    request_started = time.perf_counter()
    username = normalize_username(username)
    source_payload = payload if isinstance(payload, dict) else {}
    battle_id = clean(source_payload.get("battle_id", ""))
    skill = clean(source_payload.get("skill", "")).lower()
    client_action_id = clean(source_payload.get("client_action_id", source_payload.get("clientActionId", "")))[:96]
    lock_started = time.perf_counter()
    with SHARED_WORLD_BATTLE_LOCK:
        lock_wait_ms = (time.perf_counter() - lock_started) * 1000
        state = shared_world_battle_ram_state_required()
        shared_world_battle_prune(state)
        battle = (state.get("battles") if isinstance(state.get("battles"), dict) else {}).get(battle_id)
        if not isinstance(battle, dict) or clean(battle.get("status", "")) != "active":
            raise RuntimeError("Battle is not active.")
        players = [normalize_username(item) for item in (battle.get("players") if isinstance(battle.get("players"), list) else [])]
        if username not in players:
            raise RuntimeError("You are not in this battle.")
        if not shared_world_battle_all_players_ready(battle):
            raise RuntimeError("Waiting for both players to enter the Battle arena.")
        if int((battle.get("mp") if isinstance(battle.get("mp"), dict) else {}).get(username, 0) or 0) < 100:
            raise RuntimeError("Battle mana is not full.")
        mutation_started = time.perf_counter()
        if not shared_world_battle_apply_skill_locked(battle, username, skill):
            raise RuntimeError("Unknown battle skill.")
        mutation_ms = (time.perf_counter() - mutation_started) * 1000
        log = battle.get("log") if isinstance(battle.get("log"), list) else []
        if client_action_id and log and isinstance(log[-1], dict):
            log[-1]["client_action_id"] = client_action_id
        durable_started = time.perf_counter()
        write_shared_world_battle_state(state, notify_users=players)
        durable_ms = (time.perf_counter() - durable_started) * 1000
    response_started = time.perf_counter()
    result = shared_world_battle_state_for_user(username)
    response_ms = (time.perf_counter() - response_started) * 1000
    stt_debug_log(
        "shared_world_battle_ultimate_timing",
        user=username,
        battle_id=battle_id,
        skill=skill,
        lock_wait_ms=round(lock_wait_ms, 3),
        mutation_ms=round(mutation_ms, 3),
        durable_ms=round(durable_ms, 3),
        response_ms=round(response_ms, 3),
        total_ms=round((time.perf_counter() - request_started) * 1000, 3),
    )
    return result


# Added 2026-08-11: make hung's PvP test buttons use the persisted Battle damage path without mana costs.
def shared_world_battle_admin_test_attack(username: str, payload: dict) -> dict:
    request_started = time.perf_counter()
    username = normalize_username(username)
    if username != "hung":
        raise RuntimeError("Only hung can use admin combat tests.")
    source_payload = payload if isinstance(payload, dict) else {}
    battle_id = clean(source_payload.get("battle_id", ""))
    attack = clean(source_payload.get("attack", "basic")).lower()
    lock_started = time.perf_counter()
    with SHARED_WORLD_BATTLE_LOCK:
        lock_wait_ms = (time.perf_counter() - lock_started) * 1000
        state = shared_world_battle_ram_state_required()
        shared_world_battle_prune(state)
        battle = (state.get("battles") if isinstance(state.get("battles"), dict) else {}).get(battle_id)
        if not isinstance(battle, dict) or clean(battle.get("status", "")) != "active":
            raise RuntimeError("Battle is not active.")
        players = [normalize_username(item) for item in (battle.get("players") if isinstance(battle.get("players"), list) else [])]
        if username not in players:
            raise RuntimeError("You are not in this battle.")
        if not shared_world_battle_all_players_ready(battle):
            raise RuntimeError("Waiting for both players to enter the Battle arena.")
        opponent = shared_world_battle_other(battle, username)
        requested_damage = 35 if attack in {"ultimate", "skill", "skill-no", "skill_nộ"} else 10
        effect = "ultimate" if requested_damage >= 35 else "basic_attack"
        damage = shared_world_battle_apply_damage(battle, username, opponent, requested_damage)
        log = battle.setdefault("log", [])
        if not isinstance(log, list):
            log = []
        log.append({
            "at": utc_timestamp(),
            "type": "hit",
            "admin_test": True,
            "attacker": username,
            "target": opponent,
            "damage": damage,
            "effect": effect,
            "loot": {"transferred": 0, "items": []},
            "text": f"Admin test {effect} hit {opponent} for {damage} damage.",
        })
        battle["log"] = log[-40:]
        battle["updated_at"] = utc_timestamp()
        finish_started = time.perf_counter()
        # Added 2026-08-14: admin tests may kill, but never run real reward
        # transfers while holding the Battle lock; keep the hit as the last log
        # so the client still plays the killing animation before the result.
        shared_world_battle_check_hp(battle, award_reward=False, append_finish_log=False)
        finish_ms = (time.perf_counter() - finish_started) * 1000
        persist_started = time.perf_counter()
        write_shared_world_battle_state(state, notify_users=players)
        persist_ms = (time.perf_counter() - persist_started) * 1000
        result = {
            "battle": shared_world_battle_public_payload(battle, username),
            "battle_realtime_revision": shared_world_battle_realtime_revision(username),
            "battle_obstacle_revision": int(shared_world_normalize_obstacles(state.get("battle_obstacles")).get("revision", 0) or 0),
            "incoming_invites": [],
            "outgoing_invites": [],
            "games": list(SHARED_WORLD_BATTLE_GAMES.values()),
        }
    total_ms = (time.perf_counter() - request_started) * 1000
    stt_debug_log(
        "shared_world_battle_admin_test_timing",
        user=username,
        battle_id=battle_id,
        attack=attack,
        finished=clean((result.get("battle") or {}).get("status", "")) == "finished",
        lock_wait_ms=round(lock_wait_ms, 3),
        finish_ms=round(finish_ms, 3),
        persist_ms=round(persist_ms, 3),
        total_ms=round(total_ms, 3),
    )
    return result


def shared_world_battle_forfeit(username: str, payload: dict) -> dict:
    username = normalize_username(username)
    battle_id = clean((payload if isinstance(payload, dict) else {}).get("battle_id", ""))
    with SHARED_WORLD_BATTLE_LOCK:
        state = shared_world_battle_ram_state_required()
        battle = (state.get("battles") if isinstance(state.get("battles"), dict) else {}).get(battle_id)
        if not isinstance(battle, dict) or clean(battle.get("status", "")) != "active":
            pass
        else:
            players = [normalize_username(item) for item in (battle.get("players") if isinstance(battle.get("players"), list) else [])]
            if username not in players:
                raise RuntimeError("You are not in this battle.")
            winner = shared_world_battle_other(battle, username)
            shared_world_battle_finish(battle, winner, username, f"{username} left the battle and lost by forfeit.")
            write_shared_world_battle_state(state, notify_users=players)
    return shared_world_battle_state_for_user(username)


# Added 2026-08-11: persist free arena movement with Battle-map obstacle projection.
def shared_world_battle_move(username: str, payload: dict) -> dict:
    username = normalize_username(username)
    source_payload = payload if isinstance(payload, dict) else {}
    battle_id = clean(source_payload.get("battle_id", ""))
    refresh_question = bool(source_payload.get("refresh_question", source_payload.get("refreshQuestion", False)))
    client_ready = bool(source_payload.get("client_ready", source_payload.get("clientReady", False)))
    question_request_id = clean(
        source_payload.get("question_request_id", source_payload.get("questionRequestId", ""))
    )[:96]
    with SHARED_WORLD_BATTLE_LOCK:
        state = shared_world_battle_ram_state_required()
        shared_world_battle_prune(state)
        battle = (state.get("battles") if isinstance(state.get("battles"), dict) else {}).get(battle_id)
        if not isinstance(battle, dict) or clean(battle.get("status", "")) != "active":
            raise RuntimeError("Battle is not active.")
        players = [normalize_username(item) for item in (battle.get("players") if isinstance(battle.get("players"), list) else [])]
        if username not in players:
            raise RuntimeError("You are not in this battle.")
        if client_ready:
            ready_players = {
                normalize_username(item)
                for item in (battle.get("ready_players") if isinstance(battle.get("ready_players"), list) else [])
                if normalize_username(item)
            }
            ready_players.add(username)
            battle["ready_players"] = [player for player in players if player in ready_players]
            if shared_world_battle_all_players_ready(battle) and not bool(battle.get("combat_ready")):
                battle["combat_ready"] = True
                battle["combat_ready_at"] = utc_timestamp()
                first_turn = normalize_username(battle.get("first_turn", "")) or players[secrets.randbelow(len(players))]
                log = battle.setdefault("log", [])
                if not isinstance(log, list):
                    log = []
                    battle["log"] = log
                log.append({"at": utc_timestamp(), "type": "coin", "text": f"Both players are ready. Coin flip: {first_turn} starts first."})
                shared_world_battle_start_turn(battle, first_turn)
        requested_kind = qm_city_training_normalize_question_kind(
            source_payload.get("training_kind", "")
        )
        allowed_kinds = SHARED_WORLD_BATTLE_BASIC_QUESTION_KINDS
        if requested_kind in allowed_kinds:
            preferred_map = battle.setdefault("preferred_question_kinds", {})
            preferred_map[username] = requested_kind
            loadout_map = battle.setdefault("basic_skill_loadouts", {})
            requested_loadout = source_payload.get("basic_skill_loadout", source_payload.get("basicSkillLoadout"))
            if isinstance(requested_loadout, list):
                normalized_loadout = [clean(item).lower() for item in requested_loadout[:3]]
                normalized_loadout.extend([""] * (3 - len(normalized_loadout)))
                loadout_map[username] = normalized_loadout
            selected_question = {}
            should_refresh = False
            refresh_ids = battle.setdefault("question_refresh_ids", {})
            previous_request_id = clean(refresh_ids.get(username, ""))
            if clean(battle.get("phase", "")) == "free":
                questions = battle.setdefault("questions", {})
                current_question = questions.get(username) if isinstance(questions.get(username), dict) else {}
                should_refresh = not current_question or (
                    refresh_question
                    and bool(question_request_id)
                    and question_request_id != previous_request_id
                )
                if should_refresh:
                    questions[username] = shared_world_battle_pick_question(username, battle)
                    if question_request_id:
                        refresh_ids[username] = question_request_id
                    pending_refreshes = battle.setdefault("question_refresh_pending", {})
                    pending_refreshes.pop(username, None)
                selected_question = questions[username]
            elif normalize_username(battle.get("turn", "")) == username and clean(battle.get("phase", "question")) == "question":
                current_question = battle.get("question") if isinstance(battle.get("question"), dict) else {}
                should_refresh = not current_question or (
                    refresh_question
                    and bool(question_request_id)
                    and question_request_id != previous_request_id
                )
                if should_refresh:
                    battle["question"] = shared_world_battle_pick_question(username, battle)
                    if question_request_id:
                        refresh_ids[username] = question_request_id
                    pending_refreshes = battle.setdefault("question_refresh_pending", {})
                    pending_refreshes.pop(username, None)
                selected_question = battle["question"]
                if should_refresh:
                    battle["deadline_at"] = local_timestamp(time.time() + 30)
            # Added 2026-08-12: prove the selected PvP Basic Skill produced the expected question contract.
            stt_debug_log(
                "shared_world_battle_basic_kind_selected",
                user=username,
                battle_id=battle_id,
                requested_kind=requested_kind,
                actual_kind=qm_city_training_normalize_question_kind(selected_question.get("training_kind", selected_question.get("kind", ""))),
                choices=len(selected_question.get("choices") if isinstance(selected_question.get("choices"), list) else []),
                refresh_question=refresh_question,
                question_request_id=question_request_id,
                question_refreshed=bool(should_refresh),
            )
        positions = battle.setdefault("positions", {})
        current = positions.get(username) if isinstance(positions.get(username), dict) else {"x": 0.5, "y": 0.58}
        requested_current = {
            "x": shared_world_clamp((payload if isinstance(payload, dict) else {}).get("current_x", current.get("x", 0.5))),
            "y": shared_world_clamp((payload if isinstance(payload, dict) else {}).get("current_y", current.get("y", 0.58))),
        }
        requested_destination = {
            "x": shared_world_clamp((payload if isinstance(payload, dict) else {}).get("x", requested_current["x"])),
            "y": shared_world_clamp((payload if isinstance(payload, dict) else {}).get("y", requested_current["y"])),
        }
        obstacles = shared_world_normalize_obstacles(state.get("battle_obstacles"))
        current = shared_world_project_orthogonal_destination(
            current,
            requested_current,
            obstacles,
            1672.0,
            941.0,
        )
        if shared_world_point_blocked(requested_destination, obstacles, 22.0, 1672.0, 941.0):
            requested_destination = shared_world_find_escape_point(requested_destination, obstacles, 22.0, 1672.0, 941.0)
        destination = shared_world_project_orthogonal_destination(current, requested_destination, obstacles, 1672.0, 941.0)
        positions[username] = destination
        dx = float(destination.get("x", 0.5) or 0.5) - float(current.get("x", 0.5) or 0.5)
        dy = float(destination.get("y", 0.58) or 0.58) - float(current.get("y", 0.58) or 0.58)
        distance = ((dx * dx) + (dy * dy)) ** 0.5
        distance_px = (((dx * 1672.0) ** 2) + ((dy * 941.0) ** 2)) ** 0.5
        duration = min(3.0, max(0.0, distance_px / 285.0))
        movement = battle.setdefault("movement", {})
        if isinstance(movement, dict):
            moving = distance >= 0.006
            movement[username] = {
                "from": current,
                "to": destination,
                "distance": distance,
                "distance_px": distance_px,
                "started_epoch": time.time(),
                "running_until_epoch": time.time() + duration + 0.45 if moving else 0.0,
            }
        battle["updated_at"] = utc_timestamp()
        write_shared_world_battle_state(state, notify_users=players)
    return shared_world_battle_state_for_user(username)


# Added 2026-08-11: keep Battle-map Pen strokes separate from City and Training.
def shared_world_battle_update_obstacles(username: str, payload: dict) -> dict:
    username = normalize_username(username)
    action = clean((payload if isinstance(payload, dict) else {}).get("action", "get")).lower()
    if username != "hung" and action != "get":
        raise ValueError("Only hung can edit battle obstacles.")
    with SHARED_WORLD_BATTLE_LOCK:
        state = shared_world_battle_ram_state_required()
        obstacles = shared_world_normalize_obstacles(state.get("battle_obstacles"))
        if action == "get":
            return {"battle_obstacles": obstacles}
        strokes = obstacles["strokes"]
        if action == "add":
            raw = (payload if isinstance(payload, dict) else {}).get("stroke")
            candidate = shared_world_normalize_obstacles({"strokes": [raw] if isinstance(raw, dict) else []})
            if not candidate["strokes"]:
                raise ValueError("Invalid battle obstacle stroke.")
            stroke = candidate["strokes"][0]
            stroke["id"] = f"battle-obstacle-{int(time.time() * 1000)}-{secrets.token_hex(4)}"
            strokes.append(stroke)
        elif action == "erase":
            eraser = (payload if isinstance(payload, dict) else {}).get("stroke")
            strokes = shared_world_erase_strokes(strokes, eraser if isinstance(eraser, dict) else {}, 1672.0, 941.0)
        elif action == "delete":
            stroke_id = clean((payload if isinstance(payload, dict) else {}).get("id", ""))
            strokes = [stroke for stroke in strokes if clean(stroke.get("id", "")) != stroke_id]
        elif action == "clear":
            strokes = []
        else:
            raise ValueError("Unsupported battle obstacle action.")
        obstacles = {
            "revision": int(obstacles.get("revision", 0) or 0) + 1,
            "updated_at_epoch": time.time(),
            "strokes": strokes,
        }
        state["battle_obstacles"] = obstacles
        rescued_count = 0
        for battle in (state.get("battles") if isinstance(state.get("battles"), dict) else {}).values():
            if not isinstance(battle, dict) or clean(battle.get("status", "")) != "active":
                continue
            positions = battle.get("positions") if isinstance(battle.get("positions"), dict) else {}
            for player, position in list(positions.items()):
                if isinstance(position, dict) and shared_world_point_blocked(position, obstacles, 22.0, 1672.0, 941.0):
                    positions[player] = shared_world_find_escape_point(position, obstacles, 22.0, 1672.0, 941.0)
                    rescued_count += 1
        write_shared_world_battle_state(state, force=True)
    return {"battle_obstacles": obstacles, "rescued_count": rescued_count}
