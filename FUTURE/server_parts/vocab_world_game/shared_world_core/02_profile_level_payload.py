def shared_world_profile(username: str) -> dict:
    username = normalize_username(username)
    if not username:
        return {}
    city_profile = shared_world_city_npc_profile_for_user(username)
    if city_profile:
        return {
            "username": username,
            "display_name": clean(city_profile.get("display_name") or city_profile.get("full_name") or username),
            "gender": clean(city_profile.get("gender", "other")).lower() or "other",
            "avatar": clean(city_profile.get("avatar", "")),
        }
    cached = SHARED_WORLD_PROFILE_CACHE.get(username)
    if cached and time.time() - float(cached[0] or 0) < 90:
        return dict(cached[1])
    profile = read_user_profile(username)
    gender = clean(profile.get("gender", "")).lower()
    if gender not in {"male", "female", "other"}:
        gender = "other"
    result = {
        "username": username,
        "display_name": clean(profile.get("full_name", "")) or username,
        "gender": gender,
        "avatar": clean(profile.get("avatar", "")),
    }
    SHARED_WORLD_PROFILE_CACHE[username] = (time.time(), result)
    if len(SHARED_WORLD_PROFILE_CACHE) > 800:
        now = time.time()
        for key, row in list(SHARED_WORLD_PROFILE_CACHE.items())[:200]:
            if now - float(row[0] or 0) > 90:
                SHARED_WORLD_PROFILE_CACHE.pop(key, None)
    return dict(result)


def shared_world_leaderboard_meta_map(usernames: list[str] | set[str] | tuple[str, ...]) -> dict[str, dict]:
    wanted = {normalize_username(name) for name in usernames if normalize_username(name)}
    if not wanted:
        return {}
    cache_key = "|".join(sorted(wanted))
    cached_key = clean(SHARED_WORLD_LEADERBOARD_META_CACHE.get("key", ""))
    cached_payload = SHARED_WORLD_LEADERBOARD_META_CACHE.get("payload")
    if cached_key == cache_key and isinstance(cached_payload, dict):
        return {name: dict(row) for name, row in cached_payload.items() if name in wanted and isinstance(row, dict)}
    meta = {name: {"top_titles": [], "monthly_badge": {}} for name in wanted}
    try:
        period_state = load_vocab_leaderboard_period_state()
    except Exception:
        period_state = {}
    try:
        reward_settings = normalize_leaderboard_rewards(load_server_settings().get("leaderboard_rewards", DEFAULT_SETTINGS["leaderboard_rewards"]))
    except Exception:
        reward_settings = normalize_leaderboard_rewards(DEFAULT_SETTINGS["leaderboard_rewards"])

    for scope in ("day", "week", "month"):
        try:
            bucket = vocab_period_bucket(scope)
            rows = vocab_leaderboard_period_rows(period_state, scope, bucket, limit=10)
        except Exception:
            rows = []
        title = clean((reward_settings.get(scope) or {}).get("title", "")) or f"{scope.title()} Champion"
        for row in rows:
            username = normalize_username(row.get("username", ""))
            if username not in meta:
                continue
            rank = int(row.get("rank", 0) or 0)
            score = int(row.get("score", 0) or 0)
            if rank <= 0 or score <= 0:
                continue
            meta[username]["top_titles"].append(
                {
                    "scope": scope,
                    "title": title,
                    "rank": rank,
                    "score": score,
                    "label": f"{title} #{rank}",
                }
            )

    try:
        reward_state = load_vocab_leaderboard_reward_state()
        month_closed = ((reward_state.get("closed") if isinstance(reward_state.get("closed"), dict) else {}).get("month") or {})
        if isinstance(month_closed, dict):
            closed_periods = sorted(
                [item for item in month_closed.values() if isinstance(item, dict)],
                key=lambda item: (clean(item.get("closed_at", "")), clean(item.get("period_key", ""))),
                reverse=True,
            )
            month_title = clean((reward_settings.get("month") or {}).get("title", "")) or "Monthly Champion"
            for period in closed_periods[:1]:
                rows = period.get("rows") if isinstance(period.get("rows"), list) else []
                for row in rows:
                    username = normalize_username(row.get("username", ""))
                    if username in meta and int(row.get("rank", 0) or 0) == 1:
                        meta[username]["monthly_badge"] = {
                            "scope": "month",
                            "title": month_title,
                            "period_key": clean(period.get("period_key", "")),
                            "label": f"Previous {month_title}",
                        }
    except Exception:
        pass
    SHARED_WORLD_LEADERBOARD_META_CACHE["key"] = cache_key
    SHARED_WORLD_LEADERBOARD_META_CACHE["at"] = time.time()
    SHARED_WORLD_LEADERBOARD_META_CACHE["payload"] = meta
    return meta


def qm_city_character_level_for_exp(exp: int, levels: list[dict] | None = None) -> dict:
    safe_exp = max(0, int(exp or 0))
    rows = normalize_qm_city_levels(levels or DEFAULT_QM_CITY_LEVELS)
    current = rows[0]
    next_row = None
    for index, row in enumerate(rows):
        if safe_exp >= int(row.get("total_exp", 0) or 0):
            current = row
            next_row = rows[index + 1] if index + 1 < len(rows) else None
        else:
            next_row = row
            break
    current_exp = int(current.get("total_exp", 0) or 0)
    next_exp = int(next_row.get("total_exp", 0) or 0) if next_row else current_exp
    span = max(1, next_exp - current_exp)
    progress = 1.0 if not next_row else max(0.0, min(1.0, (safe_exp - current_exp) / span))
    return {
        "level": int(current.get("level", 1) or 1),
        "exp": safe_exp,
        "current_exp": current_exp,
        "next_exp": next_exp,
        "progress": progress,
        "max_level": not bool(next_row),
    }


def shared_world_level_meta_map(usernames: list[str] | set[str] | tuple[str, ...], levels: list[dict] | None = None) -> dict[str, dict]:
    normalized_levels = normalize_qm_city_levels(levels or DEFAULT_QM_CITY_LEVELS)
    level_signature = json.dumps(normalized_levels, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    now = time.time()
    result: dict[str, dict] = {}
    try:
        training_state = load_qm_city_training_state()
        training_users = training_state.get("users") if isinstance(training_state.get("users"), dict) else {}
    except Exception:
        training_users = {}
    for raw_username in usernames:
        username = normalize_username(raw_username)
        if not username:
            continue
        if npc_top_profile_for_user(username):
            npc_exp = npc_top_total_words(username)
        elif shared_world_city_npc_profile_for_user(username):
            npc_exp = shared_world_city_npc_exp(username)
        else:
            npc_exp = None
        training_bonus = 0 if npc_exp is not None else qm_city_training_bonus_words_from_row(training_users.get(username))
        cache_key = f"{username}|{hashlib.sha1(level_signature.encode('utf-8')).hexdigest()[:12]}|{npc_exp if npc_exp is not None else 'user'}|train:{training_bonus}"
        with SHARED_WORLD_LEVEL_CACHE_LOCK:
            cached = SHARED_WORLD_LEVEL_CACHE.get(cache_key)
            if cached:
                result[username] = cached.get("payload", {})
                continue
        if npc_exp is not None:
            meta = qm_city_character_level_for_exp(npc_exp, normalized_levels)
        else:
            registry = read_user_vocab_registry_snapshot(username)
            words = registry.get("words") if isinstance(registry.get("words"), dict) else {}
            summary_total = 0
            try:
                summary = read_cached_lesson_user_learning_summary(username)
                summary_total = max(
                    space_w_int(summary.get("vocabulary_words", 0), 0),
                    space_w_int(summary.get("total_words", 0), 0),
                ) if isinstance(summary, dict) else 0
            except Exception:
                summary_total = 0
            meta = qm_city_character_level_for_exp(max(len(words), max(0, summary_total)) + training_bonus, normalized_levels)
        with SHARED_WORLD_LEVEL_CACHE_LOCK:
            SHARED_WORLD_LEVEL_CACHE[cache_key] = {"at": now, "payload": meta}
            if len(SHARED_WORLD_LEVEL_CACHE) > 1000:
                for key, row in list(SHARED_WORLD_LEVEL_CACHE.items())[:200]:
                    if now - float(row.get("at", 0) or 0) > 60:
                        SHARED_WORLD_LEVEL_CACHE.pop(key, None)
        result[username] = meta
    return result


def shared_world_player_payload(username: str, row: dict, meta_map: dict[str, dict] | None = None, level_map: dict[str, dict] | None = None) -> dict:
    profile = shared_world_profile(username)
    display_name = clean(profile.get("display_name", "")) or username
    gender = clean(profile.get("gender", "")).lower()
    meta = (meta_map or {}).get(username, {}) if isinstance(meta_map, dict) else {}
    level_meta = (level_map or {}).get(username, {}) if isinstance(level_map, dict) else {}
    return {
        "username": username,
        "display_name": clean(row.get("display_name", "")) or display_name,
        "gender": gender,
        "avatar": clean(profile.get("avatar", "")),
        "top_titles": meta.get("top_titles", []) if isinstance(meta.get("top_titles", []), list) else [],
        "monthly_badge": meta.get("monthly_badge", {}) if isinstance(meta.get("monthly_badge", {}), dict) else {},
        "character_level": level_meta,
        "x": shared_world_clamp(row.get("x", row.get("tx", 0.5))),
        "y": shared_world_clamp(row.get("y", row.get("ty", 0.5))),
        "tx": shared_world_clamp(row.get("tx", row.get("x", 0.5))),
        "ty": shared_world_clamp(row.get("ty", row.get("y", 0.5))),
        "chat": lesson_task_notice_text(row.get("chat", ""), limit=160),
        "chat_at": clean(row.get("chat_at", "")),
        "action": clean(row.get("action", "")),
        "action_at": clean(row.get("action_at", "")),
        "updated_at": clean(row.get("updated_at", "")),
    }
