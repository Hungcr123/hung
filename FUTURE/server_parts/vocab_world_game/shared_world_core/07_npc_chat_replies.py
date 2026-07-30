def shared_world_npc_chat_worker(
    npc_username: str,
    speaker_username: str,
    speaker_display: str,
    message: str,
    pending_id: str,
    direct: bool,
    nearby_names: list[str],
) -> None:
    npc_username = normalize_username(npc_username)
    speaker_username = normalize_username(speaker_username)
    if not npc_username or not speaker_username:
        return
    try:
        npc_display = shared_world_chat_row_display_name(npc_username)
        reply = request_gemini_qm_city_npc_reply(
            npc_display,
            speaker_display,
            message,
            direct=direct,
            nearby_names=nearby_names,
        )
        reply_text = lesson_task_notice_text(reply.get("text", ""), limit=160)
    except Exception as exc:
        stt_debug_log("qm_city_npc_chat_gemini_failed", npc=npc_username, speaker=speaker_username, error=str(exc))
        reply_text = ""
    try:
        active_battle_users = shared_world_active_battle_user_set()
    except Exception:
        active_battle_users = set()
    with SHARED_WORLD_LOCK:
        state = load_shared_world_state()
        players = state.get("players") if isinstance(state.get("players"), dict) else {}
        row = players.get(npc_username) if isinstance(players.get(npc_username), dict) else {}
        if not row or clean(row.get("bot_chat_pending_id", "")) != pending_id:
            return
        row.pop("bot_chat_pending_id", None)
        row.pop("bot_chat_pending_until", None)
        now = time.time()
        if reply_text and bool(row.get("npc_bot")) and not bool(row.get("admin_actor")) and npc_username not in active_battle_users:
            row["chat"] = reply_text
            row["chat_at"] = utc_timestamp()
            row["action"] = "wave"
            row["action_at"] = utc_timestamp()
            row["bot_chat_next_allowed_at"] = now + shared_world_npc_randint(
                SHARED_WORLD_NPC_CHAT_COOLDOWN_MIN_SECONDS,
                SHARED_WORLD_NPC_CHAT_COOLDOWN_MAX_SECONDS,
            )
            row["bot_last_chat_to"] = speaker_username
            row["bot_last_chat_message"] = lesson_task_notice_text(message, limit=160)
        else:
            row["bot_chat_next_allowed_at"] = now + shared_world_npc_randint(60, 90)
        row["updated_at"] = utc_timestamp()
        players[npc_username] = row
        state["players"] = players
        state["updated_at"] = utc_timestamp()
        write_shared_world_state(state)


def shared_world_schedule_npc_chat_reply(
    state: dict,
    npc_username: str,
    speaker_username: str,
    message: str,
    *,
    direct: bool = False,
    nearby_names: list[str] | None = None,
) -> bool:
    npc_username = normalize_username(npc_username)
    speaker_username = normalize_username(speaker_username)
    players = state.get("players") if isinstance(state.get("players"), dict) else {}
    row = players.get(npc_username) if isinstance(players.get(npc_username), dict) else {}
    now = time.time()
    if not npc_username or not speaker_username or not shared_world_npc_chat_available(row, now):
        return False
    pending_id = f"{int(now)}-{secrets.token_hex(5)}"
    delay = shared_world_npc_randint(
        SHARED_WORLD_NPC_CHAT_DELAY_MIN_SECONDS,
        SHARED_WORLD_NPC_CHAT_DELAY_MAX_SECONDS,
    )
    row["bot_chat_pending_id"] = pending_id
    row["bot_chat_pending_until"] = now + delay + 55
    row["bot_last_heard_at"] = utc_timestamp()
    players[npc_username] = row
    state["players"] = players
    state["_volatile_changed"] = True
    speaker_row = players.get(speaker_username) if isinstance(players.get(speaker_username), dict) else {}
    speaker_display = shared_world_chat_row_display_name(speaker_username, speaker_row)
    timer = threading.Timer(
        delay,
        shared_world_npc_chat_worker,
        args=(npc_username, speaker_username, speaker_display, message, pending_id, bool(direct), list(nearby_names or [])),
    )
    timer.daemon = True
    timer.start()
    return True


def shared_world_schedule_npc_chat_replies(state: dict, speaker_username: str, message: str, payload: dict | None = None) -> int:
    speaker_username = normalize_username(speaker_username)
    source = payload if isinstance(payload, dict) else {}
    players = state.get("players") if isinstance(state.get("players"), dict) else {}
    speaker_row = players.get(speaker_username) if isinstance(players.get(speaker_username), dict) else {}
    if not speaker_username or not speaker_row:
        return 0
    if shared_world_is_npc_identity(speaker_username):
        return 0
    now = time.time()
    active_battle_users = shared_world_active_battle_user_set()
    direct_targets: list[str] = []
    selected_target = normalize_username(source.get("selected_target", source.get("selectedTarget", "")))
    if selected_target and selected_target in players:
        direct_targets.append(selected_target)
    for name, row in players.items():
        safe_name = normalize_username(name)
        if not safe_name or safe_name == speaker_username or safe_name in direct_targets:
            continue
        if shared_world_chat_mentions_target(message, safe_name, row if isinstance(row, dict) else {}):
            direct_targets.append(safe_name)

    def is_reply_npc(name: str, row: dict) -> bool:
        safe = normalize_username(name)
        return (
            safe
            and safe != speaker_username
            and safe not in active_battle_users
            and shared_world_is_npc_identity(safe)
            and shared_world_npc_chat_available(row, now)
        )

    direct_targets = [
        name for name in direct_targets
        if isinstance(players.get(name), dict) and is_reply_npc(name, players[name])
    ]

    nearby_names = [
        shared_world_chat_row_display_name(name, row)
        for name, row in players.items()
        if normalize_username(name) != speaker_username and isinstance(row, dict)
    ][:8]
    scheduled = 0
    if direct_targets:
        for target in direct_targets[:2]:
            if shared_world_schedule_npc_chat_reply(state, target, speaker_username, message, direct=True, nearby_names=nearby_names):
                scheduled += 1
        return scheduled

    sx, sy = shared_world_chat_current_xy(speaker_row)
    candidates: list[str] = []
    for name, row in players.items():
        safe = normalize_username(name)
        if not safe or not isinstance(row, dict) or not is_reply_npc(safe, row):
            continue
        nx, ny = shared_world_chat_current_xy(row)
        if math.hypot(nx - sx, ny - sy) <= SHARED_WORLD_NPC_CHAT_RADIUS:
            candidates.append(safe)
    if not candidates:
        return 0
    chosen = [
        name for name in candidates
        if shared_world_npc_randint(1, 100) <= SHARED_WORLD_NPC_CHAT_REPLY_CHANCE_PERCENT
    ]
    if not chosen:
        chosen = [secrets.choice(candidates)]
    for target in chosen[:3]:
        if shared_world_schedule_npc_chat_reply(state, target, speaker_username, message, direct=False, nearby_names=nearby_names):
            scheduled += 1
    return scheduled
