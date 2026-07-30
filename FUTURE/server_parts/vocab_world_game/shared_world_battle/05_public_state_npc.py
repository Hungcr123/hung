def shared_world_battle_public_question(battle: dict, viewer: str) -> dict:
    question = battle.get("question") if isinstance(battle.get("question"), dict) else {}
    result = {key: value for key, value in question.items() if key not in {"answer", "answer_text"}}
    if clean(battle.get("phase", "")) == "reveal":
        result["answer_text"] = clean(question.get("answer_text", ""))
    result["can_answer"] = clean(battle.get("phase", "")) != "reveal" and normalize_username(viewer) == normalize_username(battle.get("turn", ""))
    return result


def shared_world_battle_public_log(log: object, players: list[str]) -> list[dict]:
    rows = log if isinstance(log, list) else []
    profiles = {player: shared_world_battle_profile(player) for player in players if player}
    display_map = {
        player: (clean(profile.get("display_name", "")) or player)
        for player, profile in profiles.items()
    }

    def visible_text(text: object) -> str:
        value = clean(text)
        if not value:
            return ""
        for username, display_name in sorted(display_map.items(), key=lambda item: len(item[0]), reverse=True):
            if not username or not display_name or username == display_name:
                continue
            value = re.sub(
                rf"(?<![A-Za-z0-9_]){re.escape(username)}(?![A-Za-z0-9_])",
                display_name,
                value,
            )
        return value

    public_rows = []
    start_index = max(0, len(rows) - 8)
    for index, item in enumerate(rows[-8:], start_index + 1):
        row = dict(item) if isinstance(item, dict) else {"text": clean(item)}
        row["text"] = visible_text(row.get("text", ""))
        row["seq"] = int(row.get("seq", 0) or index)
        row["event_id"] = clean(row.get("event_id", row.get("eventId", ""))) or f"battle-log-{row['seq']}-{hashlib.sha1((clean(row.get('at', '')) + '|' + clean(row.get('type', '')) + '|' + clean(row.get('text', ''))).encode('utf-8', errors='ignore')).hexdigest()[:10]}"
        row["eventId"] = row["event_id"]
        public_rows.append(row)
    return public_rows


def shared_world_battle_public_payload(battle: dict | None, viewer: str) -> dict | None:
    if not isinstance(battle, dict):
        return None
    viewer = normalize_username(viewer)
    players = [normalize_username(item) for item in (battle.get("players") if isinstance(battle.get("players"), list) else []) if normalize_username(item)]
    deadline_text = clean(battle.get("deadline_at", ""))
    deadline_epoch = timestamp_to_epoch(deadline_text) if deadline_text else 0.0
    log_rows = battle.get("log") if isinstance(battle.get("log"), list) else []
    updated_seq = len(log_rows)
    updated_epoch = timestamp_to_epoch(clean(battle.get("updated_at", ""))) or time.time()
    return {
        "id": clean(battle.get("id", "")),
        "status": clean(battle.get("status", "active")),
        "game": clean(battle.get("game", "fireball_vocab")),
        "players": players,
        "profiles": {player: shared_world_battle_profile(player) for player in players},
        "hp": battle.get("hp") if isinstance(battle.get("hp"), dict) else {},
        "mp": battle.get("mp") if isinstance(battle.get("mp"), dict) else {},
        "turn": clean(battle.get("turn", "")),
        "phase": clean(battle.get("phase", "question")),
        "deadline_at": deadline_text,
        "deadlineAt": deadline_text,
        "deadline_epoch": deadline_epoch,
        "deadlineEpoch": deadline_epoch,
        "server_epoch": time.time(),
        "serverEpoch": time.time(),
        "updated_epoch": updated_epoch,
        "updatedEpoch": updated_epoch,
        "updated_seq": updated_seq,
        "updatedSeq": updated_seq,
        "question": shared_world_battle_public_question(battle, viewer),
        "winner": clean(battle.get("winner", "")),
        "loser": clean(battle.get("loser", "")),
        "wager": max(0, space_w_int(battle.get("wager", 2), 2)),
        "reward": battle.get("reward") if isinstance(battle.get("reward"), dict) else {},
        "message": clean(battle.get("message", "")),
        "log": shared_world_battle_public_log(battle.get("log"), players),
    }


def shared_world_battle_advance_timeout(battle: dict) -> bool:
    if clean(battle.get("status", "")) != "active":
        return False
    deadline = timestamp_to_epoch(clean(battle.get("deadline_at", "")))
    if not deadline or time.time() <= deadline:
        return False
    turn = normalize_username(battle.get("turn", ""))
    other = shared_world_battle_other(battle, turn)
    log = battle.setdefault("log", [])
    if not isinstance(log, list):
        log = []
    phase = clean(battle.get("phase", "question"))
    if phase == "reveal":
        shared_world_battle_start_turn(battle, normalize_username(battle.get("next_turn_after_reveal", "")) or other or turn)
    elif phase == "steal":
        log.append({"at": utc_timestamp(), "type": "timeout", "text": f"{turn} missed the steal chance."})
        battle["log"] = log[-40:]
        shared_world_battle_reveal_answer(battle, turn, "No one answered. Revealing the correct word.")
    else:
        log.append({"at": utc_timestamp(), "type": "timeout", "text": f"{turn} ran out of time."})
        battle["phase"] = "steal"
        battle["turn"] = other or turn
        battle["deadline_at"] = local_timestamp(time.time() + 30)
        battle["updated_at"] = utc_timestamp()
        battle["log"] = log[-40:]
    return True


# Added 2026-07-08: keeps QM City battle bots visible and responsive without adding a background worker.
def shared_world_battle_refresh_npc_players(battle: dict) -> tuple[set[str], bool]:
    if not isinstance(battle, dict):
        return set(), False
    players = [
        normalize_username(item)
        for item in (battle.get("players") if isinstance(battle.get("players"), list) else [])
        if normalize_username(item)
    ]
    player_set = set(players)
    active_bots = shared_world_npc_bot_names_snapshot()
    existing = {
        normalize_username(item)
        for item in (battle.get("npc_bots") if isinstance(battle.get("npc_bots"), list) else [])
        if normalize_username(item) in player_set
    }
    npc_bots = set(existing)
    for player in players:
        if player in active_bots or shared_world_is_npc_identity(player):
            npc_bots.add(player)
    current = [
        normalize_username(item)
        for item in (battle.get("npc_bots") if isinstance(battle.get("npc_bots"), list) else [])
        if normalize_username(item)
    ]
    next_list = [player for player in players if player in npc_bots]
    changed = current != next_list
    if changed:
        battle["npc_bots"] = next_list
    return npc_bots, changed


# Added 2026-07-08: makes NPC answers/skills feel alive while bounded to one cheap scheduled action per poll.
def shared_world_npc_battle_delay_seconds(action: str = "answer") -> int:
    action = clean(action).lower()
    roll = shared_world_npc_randint(1, 100)
    if action == "skill":
        return shared_world_npc_randint(2, 5) if roll <= 84 else shared_world_npc_randint(6, 9)
    if action == "steal":
        return shared_world_npc_randint(2, 5) if roll <= 86 else shared_world_npc_randint(6, 10)
    return shared_world_npc_randint(3, 7) if roll <= 86 else shared_world_npc_randint(8, 12)


# Added 2026-07-08: maps optional NPC battle difficulty onto the existing correct-percent settings.
def shared_world_battle_npc_correct_percent(settings: dict, phase: str) -> int:
    source = settings if isinstance(settings, dict) else {}
    key = "steal_correct_percent" if clean(phase) == "steal" else "answer_correct_percent"
    fallback = 34 if key == "steal_correct_percent" else 58
    try:
        percent = int(source.get(key, fallback) or fallback)
    except Exception:
        percent = fallback
    difficulty = clean(
        source.get("battle_difficulty", source.get("battleDifficulty", source.get("difficulty", "")))
    ).lower()
    if not difficulty:
        raw = load_server_settings().get("qm_city_npc", {})
        if isinstance(raw, dict):
            difficulty = clean(raw.get("battle_difficulty", raw.get("battleDifficulty", raw.get("difficulty", "")))).lower()
    if difficulty in {"easy", "beginner", "low"}:
        percent -= 14
    elif difficulty in {"hard", "advanced", "high"}:
        percent += 14
    elif difficulty in {"expert", "nightmare", "boss"}:
        percent += 24
    return max(0, min(100, percent))


def shared_world_battle_npc_bot_tick(battle: dict) -> bool:
    if not isinstance(battle, dict) or clean(battle.get("status", "")) != "active":
        return False
    npc_bots, changed = shared_world_battle_refresh_npc_players(battle)
    if not npc_bots:
        return False
    settings = shared_world_npc_bot_settings()
    now = time.time()
    mp = battle.setdefault("mp", {})

    skill_schedule = battle.setdefault("npc_skill_at", {})
    if not isinstance(skill_schedule, dict):
        skill_schedule = {}
        battle["npc_skill_at"] = skill_schedule
    for npc in list(npc_bots):
        if clean(battle.get("status", "")) != "active":
            break
        if int(mp.get(npc, 0) or 0) < 100:
            skill_schedule.pop(npc, None)
            continue
        scheduled = float(skill_schedule.get(npc, 0) or 0)
        if scheduled <= 0:
            skill_schedule[npc] = now + shared_world_npc_battle_delay_seconds("skill")
            changed = True
            continue
        if now >= scheduled:
            skill = secrets.choice(["inferno", "meteor", "shield", "drain", "phoenix"])
            if shared_world_battle_apply_skill_locked(battle, npc, skill):
                changed = True
            skill_schedule.pop(npc, None)

    if clean(battle.get("status", "")) != "active":
        return True
    phase = clean(battle.get("phase", "question"))
    if phase not in {"question", "steal"}:
        return changed
    turn = normalize_username(battle.get("turn", ""))
    if turn not in npc_bots:
        return changed
    question = battle.get("question") if isinstance(battle.get("question"), dict) else {}
    question_key = f"{turn}|{phase}|{clean(question.get('created_at', ''))}|{vocab_key(question.get('answer_text', question.get('answer', '')))}"
    answer_schedule = battle.setdefault("npc_answer_at", {})
    if not isinstance(answer_schedule, dict):
        answer_schedule = {}
        battle["npc_answer_at"] = answer_schedule
    active_key = clean(answer_schedule.get("_key", ""))
    if active_key != question_key:
        answer_schedule.clear()
        answer_schedule["_key"] = question_key
        answer_schedule["at"] = now + shared_world_npc_battle_delay_seconds("steal" if phase == "steal" else "answer")
        changed = True
        return changed
    scheduled = float(answer_schedule.get("at", 0) or 0)
    if scheduled and now >= scheduled:
        percent = shared_world_battle_npc_correct_percent(settings, phase)
        correct = shared_world_npc_randint(1, 100) <= percent
        answer = clean(question.get("answer_text", "")) if correct else ""
        shared_world_battle_apply_answer_locked(battle, turn, answer)
        answer_schedule.clear()
        changed = True
    return changed


def shared_world_battle_prune(state: dict) -> bool:
    now = time.time()
    # Added 2026-07-08: coalesces burst polling/answer requests so 100 online clients do not rescan all battles per request.
    last_prune = float(state.get("_last_prune_at", 0.0) or 0.0) if isinstance(state, dict) else 0.0
    if last_prune and now - last_prune < 0.15:
        return False
    state["_last_prune_at"] = now
    changed = False
    invites = state.setdefault("invites", {})
    if isinstance(invites, dict):
        for invite_id, invite in list(invites.items()):
            row = invite if isinstance(invite, dict) else {}
            created = timestamp_to_epoch(clean(row.get("created_at", "")))
            status = clean(row.get("status", "pending"))
            if (status != "pending" and now - created > 3600) or (status == "pending" and now - created > 180):
                invites.pop(invite_id, None)
                changed = True
    battles = state.setdefault("battles", {})
    if isinstance(battles, dict):
        for battle_id, battle in list(battles.items()):
            if not isinstance(battle, dict):
                battles.pop(battle_id, None)
                changed = True
                continue
            if shared_world_battle_advance_timeout(battle):
                changed = True
            if shared_world_battle_npc_bot_tick(battle):
                changed = True
            finished = timestamp_to_epoch(clean(battle.get("finished_at", "")))
            if clean(battle.get("status", "")) == "finished" and finished and now - finished > 600:
                shared_world_battle_flush_word_history(battle)
                battles.pop(battle_id, None)
                changed = True
    return changed


def shared_world_battle_active_for_user(state: dict, username: str) -> dict | None:
    username = normalize_username(username)
    battles = state.get("battles") if isinstance(state.get("battles"), dict) else {}
    for battle in battles.values():
        if not isinstance(battle, dict):
            continue
        players = [normalize_username(item) for item in (battle.get("players") if isinstance(battle.get("players"), list) else [])]
        if username in players and clean(battle.get("status", "")) == "active":
            return battle
    return None


def shared_world_battle_state_for_user(username: str) -> dict:
    username = normalize_username(username)
    with SHARED_WORLD_BATTLE_LOCK:
        state = load_shared_world_battle_state()
        changed = shared_world_battle_prune(state)
        if changed:
            write_shared_world_battle_state(state)
        incoming = []
        outgoing = []
        for invite in (state.get("invites") if isinstance(state.get("invites"), dict) else {}).values():
            if not isinstance(invite, dict) or clean(invite.get("status", "")) != "pending":
                continue
            if normalize_username(invite.get("to", "")) == username:
                incoming.append(shared_world_battle_public_invite(invite))
            elif normalize_username(invite.get("from", "")) == username:
                outgoing.append(shared_world_battle_public_invite(invite))
        battle = shared_world_battle_active_for_user(state, username)
        if not battle:
            for row in (state.get("battles") if isinstance(state.get("battles"), dict) else {}).values():
                if isinstance(row, dict) and clean(row.get("status", "")) == "finished":
                    players = [normalize_username(item) for item in (row.get("players") if isinstance(row.get("players"), list) else [])]
                    finished = timestamp_to_epoch(clean(row.get("finished_at", "")))
                    if username in players and finished and time.time() - finished < 120:
                        battle = row
                        break
    return {
        "battle": shared_world_battle_public_payload(battle, username),
        "incoming_invites": incoming[:5],
        "outgoing_invites": outgoing[:5],
        "games": list(SHARED_WORLD_BATTLE_GAMES.values()),
    }
