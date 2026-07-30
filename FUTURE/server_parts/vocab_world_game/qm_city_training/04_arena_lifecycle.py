def qm_city_training_ensure_slime_questions(username: str, arena: dict, selected_only: bool = False) -> bool:
    if not isinstance(arena, dict):
        return False
    slimes = arena.get("slimes") if isinstance(arena.get("slimes"), list) else []
    selected_id = clean(arena.get("selected_id", ""))
    changed = False
    for index, slime in enumerate(slimes):
        if not isinstance(slime, dict) or space_w_int(slime.get("hp", 0), 0) <= 0:
            continue
        if selected_only and clean(slime.get("id", "")) != selected_id:
            continue
        current_kind = qm_city_training_normalize_question_kind(slime.get("preferred_kind", ""))
        fixed_kind = qm_city_training_kind_for_slime_index(index, randomize_tail=False) if index < len(QM_CITY_TRAINING_FIXED_KIND_SEQUENCE) else ""
        preferred_kind = fixed_kind or current_kind or qm_city_training_kind_for_slime_index(index, randomize_tail=True)
        if fixed_kind and current_kind != fixed_kind:
            slime["preferred_kind"] = fixed_kind
            slime["question"] = {}
            slime.pop("respawn_at", None)
            slime.pop("kill_rewarded", None)
            changed = True
        slime["preferred_kind"] = preferred_kind
        question = slime.get("question") if isinstance(slime.get("question"), dict) else {}
        question_kind = qm_city_training_normalize_question_kind(question.get("training_kind", question.get("kind", ""))) if isinstance(question, dict) else ""
        if not clean(question.get("prompt", "")) or not clean(question.get("answer", "")) or question_kind != preferred_kind:
            slime["question"] = qm_city_training_pick_question(username, arena, preferred_kind)
            changed = True
    return changed


def qm_city_training_roll_slime_max_hp(stats: dict) -> int:
    strength = max(1, space_w_int((stats or {}).get("strength", 1), 1))
    factor = 5 + secrets.randbelow(4)
    return max(5, strength * factor)


def qm_city_training_make_slimes(level_meta: dict, stats: dict | None = None) -> list[dict]:
    base_level = max(1, space_w_int(level_meta.get("level", 1), 1))
    stat_row = stats if isinstance(stats, dict) else {"strength": qm_city_training_strength_for_level(base_level)}
    balance_strength = max(1, space_w_int(stat_row.get("strength", qm_city_training_strength_for_level(base_level)), qm_city_training_strength_for_level(base_level)))
    anchors = qm_city_training_slime_anchors()
    slimes = []
    for index in range(QM_CITY_TRAINING_SLIME_COUNT):
        level = max(1, base_level + secrets.randbelow(5) - 2)
        max_hp = qm_city_training_roll_slime_max_hp(stat_row)
        max_mana = 18 + level * 4
        x, y = anchors[index % len(anchors)]
        slimes.append(
            {
                "id": f"slime_{index + 1:02d}",
                "name": "Slime",
                "level": level,
                "hp": max_hp,
                "max_hp": max_hp,
                "balance_strength": balance_strength,
                "mana": secrets.randbelow(max(1, max_mana // 2 + 1)),
                "max_mana": max_mana,
                "preferred_kind": qm_city_training_kind_for_slime_index(index, randomize_tail=True),
                "motion_seed": secrets.randbelow(1000000),
                "motion_anchor_x": round(shared_world_clamp(x), 4),
                "motion_anchor_y": round(shared_world_clamp(y), 4),
                "x": round(shared_world_clamp(x + (secrets.randbelow(7) - 3) / 100.0), 4),
                "y": round(shared_world_clamp(y + (secrets.randbelow(7) - 3) / 100.0), 4),
                "tx": round(shared_world_clamp(x + (secrets.randbelow(9) - 4) / 100.0), 4),
                "ty": round(shared_world_clamp(y + (secrets.randbelow(9) - 4) / 100.0), 4),
                "next_move_at": time.time() + shared_world_npc_randint(3, 10),
                "mood": "idle",
            }
        )
    return slimes


def qm_city_training_rebalance_slime_positions(arena: dict, level_meta: dict | None = None, stats: dict | None = None) -> bool:
    if not isinstance(arena, dict):
        return False
    current_layout = space_w_int(arena.get("layout_version", 0), 0)
    slimes = arena.get("slimes") if isinstance(arena.get("slimes"), list) else []
    if not slimes:
        return False
    stat_row = stats if isinstance(stats, dict) else {}
    balance_strength = max(1, space_w_int(stat_row.get("strength", 0), 0))
    fixed_kind_mismatch = any(
        isinstance(slime, dict)
        and qm_city_training_normalize_question_kind(slime.get("preferred_kind", "")) != qm_city_training_kind_for_slime_index(index, randomize_tail=False)
        for index, slime in enumerate(slimes[:len(QM_CITY_TRAINING_FIXED_KIND_SEQUENCE)])
    )
    strength_mismatch = bool(balance_strength) and any(
        isinstance(slime, dict)
        and space_w_int(slime.get("balance_strength", 0), 0) != balance_strength
        for slime in slimes
    )
    if current_layout >= QM_CITY_TRAINING_LAYOUT_VERSION and not fixed_kind_mismatch and not strength_mismatch:
        return False
    anchors = qm_city_training_slime_anchors()
    changed = False
    for index, slime in enumerate(slimes):
        if not isinstance(slime, dict):
            continue
        if balance_strength:
            old_strength = max(0, space_w_int(slime.get("balance_strength", 0), 0))
            if old_strength != balance_strength:
                old_max_hp = max(1, space_w_int(slime.get("max_hp", 1), 1))
                old_hp = max(0, space_w_int(slime.get("hp", 0), 0))
                new_max_hp = qm_city_training_roll_slime_max_hp(stat_row)
                slime["max_hp"] = new_max_hp
                slime["balance_strength"] = balance_strength
                if old_hp > 0:
                    ratio = max(0.0, min(1.0, old_hp / old_max_hp))
                    slime["hp"] = max(1, min(new_max_hp, int(round(new_max_hp * ratio))))
                changed = True
        preferred_kind = qm_city_training_kind_for_slime_index(index, randomize_tail=True)
        expected_fixed_kind = qm_city_training_kind_for_slime_index(index, randomize_tail=False) if index < len(QM_CITY_TRAINING_FIXED_KIND_SEQUENCE) else ""
        current_kind = qm_city_training_normalize_question_kind(slime.get("preferred_kind", ""))
        must_reset_kind = current_layout < 5 or (expected_fixed_kind and current_kind != expected_fixed_kind)
        if must_reset_kind:
            preferred_kind = expected_fixed_kind or preferred_kind
            slime["preferred_kind"] = preferred_kind
            slime["question"] = {}
            max_hp = max(1, space_w_int(slime.get("max_hp", 50), 50))
            max_mana = max(1, space_w_int(slime.get("max_mana", 20), 20))
            if space_w_int(slime.get("hp", 0), 0) <= 0:
                slime["hp"] = max_hp
                slime["mana"] = secrets.randbelow(max(1, max_mana // 2 + 1))
                slime["mood"] = "respawn"
            slime.pop("respawn_at", None)
            slime.pop("kill_rewarded", None)
        x, y = anchors[index % len(anchors)]
        slime["motion_seed"] = secrets.randbelow(1000000)
        slime["motion_anchor_x"] = round(shared_world_clamp(x), 4)
        slime["motion_anchor_y"] = round(shared_world_clamp(y), 4)
        slime["x"] = round(shared_world_clamp(x + (secrets.randbelow(5) - 2) / 100.0), 4)
        slime["y"] = round(shared_world_clamp(y + (secrets.randbelow(5) - 2) / 100.0), 4)
        slime["tx"] = slime["x"]
        slime["ty"] = slime["y"]
        slime["next_move_at"] = time.time() + shared_world_npc_randint(4, 11)
        changed = True
    arena["layout_version"] = QM_CITY_TRAINING_LAYOUT_VERSION
    arena["updated_at"] = utc_timestamp()
    return True


def qm_city_training_tick_arena(arena: dict, username: str = "") -> bool:
    if not isinstance(arena, dict):
        return False
    slimes = arena.get("slimes") if isinstance(arena.get("slimes"), list) else []
    if not slimes:
        return False
    now = time.time()
    selected_id = clean(arena.get("selected_id", ""))
    changed = False
    for index, slime in enumerate(slimes):
        if not isinstance(slime, dict):
            continue
        hp = space_w_int(slime.get("hp", 0), 0)
        if hp <= 0:
            preferred_kind = qm_city_training_normalize_question_kind(slime.get("preferred_kind", "")) or qm_city_training_kind_for_slime_index(index, randomize_tail=True)
            respawn_at = float(slime.get("respawn_at", 0) or 0)
            if respawn_at <= 0:
                slime["respawn_at"] = now + QM_CITY_TRAINING_SPEECH_RESPAWN_SECONDS
                changed = True
                continue
            if now < respawn_at:
                continue
            max_hp = max(1, space_w_int(slime.get("max_hp", 50), 50))
            max_mana = max(1, space_w_int(slime.get("max_mana", 20), 20))
            slime["hp"] = max_hp
            slime["mana"] = secrets.randbelow(max(1, max_mana // 2 + 1))
            slime["preferred_kind"] = preferred_kind
            slime["question"] = qm_city_training_pick_question(username, arena, preferred_kind) if normalize_username(username) else {}
            slime["mood"] = "respawn"
            slime["next_move_at"] = now + shared_world_npc_randint(2, 6)
            slime["motion_seed"] = secrets.randbelow(1000000)
            slime.pop("respawn_at", None)
            slime.pop("kill_rewarded", None)
            if clean(arena.get("selected_id", "")) and not qm_city_training_selected_slime(arena, clean(arena.get("selected_id", ""))):
                arena["selected_id"] = ""
                arena["question"] = {}
            changed = True
            continue
        slime_id = clean(slime.get("id", ""))
        current_x = shared_world_clamp(slime.get("x", slime.get("tx", 0.5)))
        current_y = shared_world_clamp(slime.get("y", slime.get("ty", 0.5)))
        target_x = shared_world_clamp(slime.get("tx", current_x))
        target_y = shared_world_clamp(slime.get("ty", current_y))
        if "tx" not in slime or "ty" not in slime:
            slime["tx"] = target_x
            slime["ty"] = target_y
            changed = True
        if now < float(slime.get("next_move_at", 0) or 0):
            continue
        slime["x"] = target_x
        slime["y"] = target_y
        if shared_world_npc_randint(1, 100) <= 24:
            slime["tx"] = target_x
            slime["ty"] = target_y
        elif selected_id and slime_id == selected_id:
            anchor_x = shared_world_clamp(slime.get("focus_anchor_x", target_x), target_x)
            anchor_y = shared_world_clamp(slime.get("focus_anchor_y", target_y), target_y)
            slime["focus_anchor_x"] = round(anchor_x, 4)
            slime["focus_anchor_y"] = round(anchor_y, 4)
            span_x = max(1, int(round(QM_CITY_TRAINING_FOCUS_RADIUS_X * 1000)))
            span_y = max(1, int(round(QM_CITY_TRAINING_FOCUS_RADIUS_Y * 1000)))
            offset_x = shared_world_npc_randint(-span_x, span_x) / 1000.0
            offset_y = shared_world_npc_randint(-span_y, span_y) / 1000.0
            distance = math.hypot(
                offset_x / max(QM_CITY_TRAINING_FOCUS_RADIUS_X, 0.001),
                offset_y / max(QM_CITY_TRAINING_FOCUS_RADIUS_Y, 0.001),
            )
            if distance > 1:
                scale = 1 / max(distance, 0.001)
                offset_x *= scale
                offset_y *= scale
            slime["tx"] = round(shared_world_clamp(anchor_x + offset_x, anchor_x), 4)
            slime["ty"] = round(shared_world_clamp(anchor_y + offset_y, anchor_y), 4)
        else:
            slime["tx"] = round(shared_world_clamp(target_x + shared_world_npc_randint(-18, 18) / 100.0), 4)
            slime["ty"] = round(shared_world_clamp(target_y + shared_world_npc_randint(-14, 14) / 100.0), 4)
        slime["next_move_at"] = now + shared_world_npc_randint(4, 12)
        slime["mood"] = "roam"
        changed = True
    if changed:
        arena["updated_at"] = utc_timestamp()
    return changed


def qm_city_training_new_arena(username: str, level_meta: dict, stats: dict) -> dict:
    arena = {
        "id": f"train_{normalize_username(username)}_{int(time.time() * 1000)}_{secrets.token_hex(4)}",
        "layout_version": QM_CITY_TRAINING_LAYOUT_VERSION,
        "created_at": utc_timestamp(),
        "updated_at": utc_timestamp(),
        "selected_id": "",
        "player_hp": max(1, space_w_int(stats.get("max_hp", 100), 100)),
        "player_mana": 0,
        "slimes": qm_city_training_make_slimes(level_meta, stats),
        "log": [{"at": utc_timestamp(), "type": "start", "text": "Practice gate opened. Choose a slime and answer in English."}],
        "asked": [],
    }
    qm_city_training_ensure_slime_questions(username, arena)
    arena["question"] = {}
    return arena


def qm_city_training_ensure_user(state: dict, username: str, tick_motion: bool = True, lazy_questions: bool = False) -> tuple[dict, dict, dict, bool]:
    username = normalize_username(username)
    users = state.setdefault("users", {})
    row = users.get(username) if isinstance(users.get(username), dict) else {}
    previous_row = row
    changed = False
    training_words = qm_city_training_bonus_words_from_row(row)
    level_meta = qm_city_training_level_meta(username, training_words)
    stats = qm_city_training_normalize_stats(row.get("stats", {}), level_meta)
    stats["training_words"] = training_words
    arena = row.get("arena") if isinstance(row.get("arena"), dict) else {}
    if not isinstance(arena.get("slimes"), list) or len(arena.get("slimes", [])) < QM_CITY_TRAINING_SLIME_COUNT:
        arena = qm_city_training_new_arena(username, level_meta, stats)
        changed = True
    else:
        player_hp = max(0, min(stats["max_hp"], space_w_int(arena.get("player_hp", stats["max_hp"]), stats["max_hp"])))
        player_mana = max(0, min(stats["max_mana"], space_w_int(arena.get("player_mana", 0), 0)))
        if arena.get("player_hp") != player_hp:
            arena["player_hp"] = player_hp
            changed = True
        if arena.get("player_mana") != player_mana:
            arena["player_mana"] = player_mana
            changed = True
        if qm_city_training_rebalance_slime_positions(arena, level_meta, stats):
            changed = True
        if qm_city_training_ensure_slime_questions(username, arena, selected_only=lazy_questions):
            changed = True
        selected_now = qm_city_training_selected_slime(arena)
        if isinstance(selected_now, dict) and space_w_int(selected_now.get("hp", 0), 0) <= 0:
            selected_now.pop("focus_anchor_x", None)
            selected_now.pop("focus_anchor_y", None)
            arena["selected_id"] = ""
            arena["question"] = {}
            changed = True
        if not isinstance(arena.get("question"), dict) or not clean(arena.get("question", {}).get("prompt", "")):
            slime = qm_city_training_selected_slime(arena)
            if isinstance(slime, dict):
                slime_kind = qm_city_training_normalize_question_kind(slime.get("preferred_kind", ""))
                if lazy_questions:
                    arena["question"] = slime.get("question") if isinstance(slime.get("question"), dict) else {}
                else:
                    arena["question"] = slime.get("question") if isinstance(slime.get("question"), dict) else qm_city_training_pick_question(username, arena, slime_kind)
                    if isinstance(arena["question"], dict) and clean(arena["question"].get("prompt", "")):
                        slime["question"] = arena["question"]
                        changed = True
            else:
                if arena.get("question") != {}:
                    arena["question"] = {}
                    changed = True
        if tick_motion and qm_city_training_tick_arena(arena, username):
            changed = True
    row = {
        "stats": stats,
        "training_words": training_words,
        "arena": arena,
        "updated_at": utc_timestamp() if changed or not isinstance(previous_row, dict) else clean(previous_row.get("updated_at", "")),
    }
    users[username] = row
    state["users"] = users
    return row, level_meta, stats, changed


def qm_city_training_public_arena(arena: dict, stats: dict) -> dict:
    question = arena.get("question") if isinstance(arena.get("question"), dict) else {}
    safe_question = qm_city_training_public_question(question)
    public_slimes = []
    for item in (arena.get("slimes") if isinstance(arena.get("slimes"), list) else []):
        if not isinstance(item, dict):
            continue
        row = dict(item)
        row["question"] = qm_city_training_public_question(row.get("question"))
        public_slimes.append(row)
    return {
        "id": clean(arena.get("id", "")),
        "selected_id": clean(arena.get("selected_id", "")),
        "player_hp": max(0, space_w_int(arena.get("player_hp", stats.get("max_hp", 100)), stats.get("max_hp", 100))),
        "player_mana": max(0, space_w_int(arena.get("player_mana", 0), 0)),
        "slimes": public_slimes,
        "question": safe_question,
        "log": (arena.get("log") if isinstance(arena.get("log"), list) else [])[-10:],
        "skill_cooldowns": arena.get("skill_cooldowns") if isinstance(arena.get("skill_cooldowns"), dict) else {},
        "skillCooldowns": arena.get("skill_cooldowns") if isinstance(arena.get("skill_cooldowns"), dict) else {},
        "updated_at": clean(arena.get("updated_at", "")),
    }


def qm_city_training_state_for_user(username: str) -> dict:
    username = normalize_username(username)
    with QM_CITY_TRAINING_LOCK:
        cached = QM_CITY_TRAINING_PUBLIC_STATE_CACHE.get(username) if isinstance(QM_CITY_TRAINING_PUBLIC_STATE_CACHE, dict) else None
        if isinstance(cached, tuple) and len(cached) == 2:
            cached_at, cached_payload = cached
            if time.time() - float(cached_at or 0) <= 180 and isinstance(cached_payload, dict):
                import copy
                return copy.deepcopy(cached_payload)
        state = load_qm_city_training_state()
        _row, level_meta, stats, changed = qm_city_training_ensure_user(state, username, tick_motion=False, lazy_questions=False)
        if changed:
            write_qm_city_training_state_async(state)
        arena = state["users"][username]["arena"]
    payload = {
        "training": {
            "username": username,
            "stats": qm_city_training_public_stats(stats, level_meta),
            "arena": qm_city_training_public_arena(arena, stats),
        }
    }
    with QM_CITY_TRAINING_LOCK:
        if isinstance(QM_CITY_TRAINING_PUBLIC_STATE_CACHE, dict):
            import copy
            QM_CITY_TRAINING_PUBLIC_STATE_CACHE[username] = (time.time(), copy.deepcopy(payload))
    return payload


# Added 2026-07-08: selects recent real learners from the already-loaded manifest for startup RAM warm.
def qm_city_training_manifest_user_candidates(max_items: int = 80) -> list[str]:
    try:
        manifest = get_server_data_manifest()
        folders = manifest.get("folders") if isinstance(manifest.get("folders"), dict) else {}
        root_rows = folders.get("") if isinstance(folders.get(""), list) else []
    except Exception:
        root_rows = []
    rows = []
    skip_names = {"", "common", "admin", "default", "server", "testuser"}
    for item in root_rows:
        if not isinstance(item, dict) or clean(item.get("type", "")) != "folder":
            continue
        username = normalize_username(item.get("path", item.get("name", "")))
        valid_username, _message = validate_username(username)
        if (
            not username
            or not valid_username
            or not learner_user_exists(username)
            or username in skip_names
            or username.startswith("codex")
            or username.startswith("test")
            or username.startswith("perf")
        ):
            continue
        rows.append((space_w_int(item.get("modified", 0), 0), username))
    rows.sort(key=lambda item: item[0], reverse=True)
    seen = set()
    result = []
    for _modified, username in rows:
        if username in seen:
            continue
        seen.add(username)
        result.append(username)
        if len(result) >= max(1, int(max_items or 80)):
            break
    return result


# Added 2026-07-08: reads recent manifest lesson JSON into RAM caches so Space opens reuse startup warm work.
def warm_qm_city_manifest_space_cache(manifest_users: list[str], max_files: int = 240) -> tuple[int, int]:
    try:
        manifest = get_server_data_manifest()
        folders = manifest.get("folders") if isinstance(manifest.get("folders"), dict) else {}
    except Exception:
        folders = {}
    if not isinstance(folders, dict):
        return 0, 0
    wanted_tops = {"common", *[normalize_username(user) for user in manifest_users if normalize_username(user)]}
    rows = []
    for folder_rel, entries in folders.items():
        clean_folder = clean_path_value(folder_rel)
        top = clean_folder.split("/", 1)[0] if clean_folder else ""
        if top not in wanted_tops or not isinstance(entries, list):
            continue
        for item in entries:
            if not isinstance(item, dict) or clean(item.get("type", "")) != "file":
                continue
            rel_path = clean_path_value(item.get("path", ""))
            extension = clean(item.get("extension", "")).lower()
            if not rel_path or extension not in LESSON_FILE_SUFFIXES:
                continue
            rows.append((space_w_int(item.get("modified", 0), 0), rel_path, extension, space_w_int(item.get("size", 0), 0)))
    rows.sort(key=lambda item: item[0], reverse=True)
    warmed = 0
    failed = 0
    for _modified, rel_path, extension, _size in rows[:max(1, int(max_files or 240))]:
        try:
            target = server_data_manifest_path(rel_path)
            if not target.is_file():
                continue
            cached_server_data_file_bytes(target)
            warmed += 1
        except Exception as exc:
            failed += 1
            stt_debug_log("qm_city_training_manifest_file_warm_failed", path=rel_path, error=str(exc))
    return warmed, failed


# Added 2026-07-08: primes shared Space/QM City RAM caches and reports CPU/wall timing.
def warm_qm_city_training_cache(limit: int = 80) -> dict:
    start_wall = time.perf_counter()
    start_cpu = time.process_time()
    manifest_users = qm_city_training_manifest_user_candidates(limit)
    manifest_warmed = 0
    list_warmed = 0
    for username in manifest_users:
        try:
            read_user_vocab_registry_summary(username)
            read_cached_lesson_user_learning_summary(username)
            list_server_data("", username, admin=False, lightweight=True, include_task_board=False)
            list_server_data(username, username, admin=False, lightweight=True, include_task_board=False)
            list_server_data("common", username, admin=False, lightweight=True, include_task_board=False)
            list_warmed += 3
            manifest_warmed += 1
        except Exception as exc:
            stt_debug_log("qm_city_training_manifest_warm_user_failed", user=username, error=str(exc))
    file_warmed, file_failed = warm_qm_city_manifest_space_cache(manifest_users, max_files=max(40, int(limit or 80) * 3))
    with QM_CITY_TRAINING_LOCK:
        state = load_qm_city_training_state()
        users = state.get("users") if isinstance(state.get("users"), dict) else {}
        candidates = []
        for username, row in users.items():
            clean_username = normalize_username(username)
            if not clean_username or not isinstance(row, dict):
                continue
            arena = row.get("arena") if isinstance(row.get("arena"), dict) else {}
            if not isinstance(arena.get("slimes"), list):
                continue
            candidates.append((clean(row.get("updated_at", row.get("updatedAt", ""))), clean_username))
    candidates.sort(key=lambda item: item[0], reverse=True)
    warmed = 0
    for _updated_at, username in candidates[:max(1, int(limit or 80))]:
        try:
            qm_city_training_state_for_user(username)
            warmed += 1
        except Exception as exc:
            stt_debug_log("qm_city_training_warm_user_failed", user=username, error=str(exc))
    return {
        "manifest_candidates": len(manifest_users),
        "manifest_warmed": manifest_warmed,
        "list_warmed": list_warmed,
        "file_warmed": file_warmed,
        "file_failed": file_failed,
        "training_candidates": len(candidates),
        "training_warmed": warmed,
        "elapsed_ms": int((time.perf_counter() - start_wall) * 1000),
        "cpu_ms": int((time.process_time() - start_cpu) * 1000),
    }


# Added 2026-07-08: primes QM City training RAM caches at Server 2 startup for existing learners.
def warm_qm_city_training_cache_async(delay_seconds: float = 1.0, limit: int = 80) -> None:

    def runner() -> None:
        try:
            time.sleep(max(0.0, float(delay_seconds or 0.0)))
            result = warm_qm_city_training_cache(limit=limit)
            stt_debug_log("qm_city_training_cache_warmed", **result)
        except Exception as exc:
            stt_debug_log("qm_city_training_cache_warm_failed", error=str(exc))

    threading.Thread(target=runner, name="qm-city-training-cache-warm", daemon=True).start()


def qm_city_training_alive_slimes(arena: dict) -> list[dict]:
    return [
        slime for slime in (arena.get("slimes") if isinstance(arena.get("slimes"), list) else [])
        if isinstance(slime, dict) and space_w_int(slime.get("hp", 0), 0) > 0
    ]


def qm_city_training_pending_speech_respawns(arena: dict) -> list[dict]:
    now = time.time()
    rows = []
    for slime in (arena.get("slimes") if isinstance(arena.get("slimes"), list) else []):
        if not isinstance(slime, dict) or space_w_int(slime.get("hp", 0), 0) > 0:
            continue
        respawn_at = float(slime.get("respawn_at", 0) or 0)
        if respawn_at > 0 and respawn_at > now:
            rows.append(slime)
    return rows


def qm_city_training_selected_slime(arena: dict, requested_id: str = "") -> dict | None:
    slimes = arena.get("slimes") if isinstance(arena.get("slimes"), list) else []
    target_id = clean(requested_id) or clean(arena.get("selected_id", ""))
    if not target_id:
        return None
    for slime in slimes:
        if isinstance(slime, dict) and clean(slime.get("id", "")) == target_id:
            return slime
    return None
