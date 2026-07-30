# Loaded by FUTURE.server_parts.09_vocab_world_game into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def game_room_code() -> str:
    for _ in range(50):
        code = secrets.token_hex(3).upper()
        if code not in GAME_ROOMS:
            return code
    return secrets.token_hex(4).upper()


def game_room_word_limit(value: object = GAME_MAX_WORDS) -> int:
    try:
        limit = int(float(value or GAME_MAX_WORDS))
    except Exception:
        limit = GAME_MAX_WORDS
    return max(1, min(GAME_MAX_WORDS, limit))


def game_room_seat_count(value: object = GAME_DEFAULT_SEATS) -> int:
    try:
        count = int(float(value or GAME_DEFAULT_SEATS))
    except Exception:
        count = GAME_DEFAULT_SEATS
    return max(1, min(GAME_MAX_SEATS, count))


def game_player_words(username: str, limit: int = 240) -> list[dict]:
    summary = user_vocabulary_registry_summary(username)
    words = summary.get("words") if isinstance(summary.get("words"), list) else []
    return words[: max(0, int(limit or 0))]


def game_public_room(room: dict, viewer: str = "") -> dict:
    viewer = normalize_username(viewer)
    players = room.get("players") if isinstance(room.get("players"), dict) else {}
    selections = room.get("selections") if isinstance(room.get("selections"), dict) else {}
    ready = room.get("ready") if isinstance(room.get("ready"), dict) else {}
    player_rows = []
    for username, player in players.items():
        username = normalize_username(username)
        if not username:
            continue
        selected_for_user = []
        for selector, targets in selections.items():
            if isinstance(targets, dict) and username in targets:
                selected_for_user.extend(targets.get(username) if isinstance(targets.get(username), list) else [])
        player_rows.append(
            {
                "username": username,
                "host": username == normalize_username(room.get("host", "")),
                "ready": bool(ready.get(username)),
                "seat": int((player or {}).get("seat", 0) or 0),
                "selected_for": len({vocab_key(item.get("word", "")) for item in selected_for_user if isinstance(item, dict)}),
                "vocabulary": game_player_words(username),
            }
        )
    player_rows.sort(key=lambda item: item.get("seat", 0))
    return {
        "id": clean(room.get("id", "")),
        "host": normalize_username(room.get("host", "")),
        "status": clean(room.get("status", "lobby")),
        "seat_count": game_room_seat_count(room.get("seat_count", GAME_DEFAULT_SEATS)),
        "word_limit": game_room_word_limit(room.get("word_limit", GAME_MAX_WORDS)),
        "created_at": float(room.get("created_at", 0) or 0),
        "updated_at": float(room.get("updated_at", 0) or 0),
        "viewer": viewer,
        "players": player_rows,
        "selections": selections,
        "ready": ready,
        "battle": room.get("battle") if isinstance(room.get("battle"), dict) else None,
    }


def game_create_room(username: str, payload: dict) -> dict:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    now = time.time()
    with GAME_LOCK:
        room_id = game_room_code()
        room = {
            "id": room_id,
            "host": username,
            "status": "lobby",
            "seat_count": game_room_seat_count(payload.get("seat_count", GAME_DEFAULT_SEATS)),
            "word_limit": game_room_word_limit(payload.get("word_limit", GAME_MAX_WORDS)),
            "players": {username: {"seat": 1, "joined_at": now}},
            "selections": {},
            "ready": {username: False},
            "created_at": now,
            "updated_at": now,
        }
        GAME_ROOMS[room_id] = room
        return game_public_room(room, username)


def game_join_room(username: str, room_id: str) -> dict:
    username = normalize_username(username)
    room_id = clean(room_id).upper()
    with GAME_LOCK:
        room = GAME_ROOMS.get(room_id)
        if not room:
            raise RuntimeError("Khong tim thay phong game.")
        players = room.setdefault("players", {})
        if username not in players:
            if len(players) >= game_room_seat_count(room.get("seat_count", GAME_DEFAULT_SEATS)):
                raise RuntimeError("Phong game da day.")
            occupied = {int((item or {}).get("seat", 0) or 0) for item in players.values() if isinstance(item, dict)}
            seat = next((index for index in range(1, GAME_MAX_SEATS + 1) if index not in occupied), len(players) + 1)
            players[username] = {"seat": seat, "joined_at": time.time()}
        room.setdefault("ready", {})[username] = False
        room["updated_at"] = time.time()
        return game_public_room(room, username)


def game_room_state(username: str, room_id: str = "") -> dict:
    username = normalize_username(username)
    room_id = clean(room_id).upper()
    with GAME_LOCK:
        if room_id:
            room = GAME_ROOMS.get(room_id)
            if not room:
                raise RuntimeError("Khong tim thay phong game.")
            return game_public_room(room, username)
        rooms = [
            game_public_room(room, username)
            for room in GAME_ROOMS.values()
            if clean(room.get("status", "")) in {"lobby", "ready", "battle"}
        ]
        rooms.sort(key=lambda item: float(item.get("updated_at", 0) or 0), reverse=True)
        return {"rooms": rooms[:20]}


def game_select_words(username: str, payload: dict) -> dict:
    username = normalize_username(username)
    room_id = clean(payload.get("room", "")).upper()
    target = normalize_username(payload.get("target", ""))
    raw_words = payload.get("words") if isinstance(payload.get("words"), list) else []
    with GAME_LOCK:
        room = GAME_ROOMS.get(room_id)
        if not room:
            raise RuntimeError("Khong tim thay phong game.")
        players = room.get("players") if isinstance(room.get("players"), dict) else {}
        if username not in players or target not in players:
            raise RuntimeError("Nguoi choi khong nam trong phong.")
        if username == target:
            raise RuntimeError("Hay chon tu vung cho doi phuong.")
        limit = game_room_word_limit(room.get("word_limit", GAME_MAX_WORDS))
        known = {vocab_key(item.get("word", "")): item for item in game_player_words(target, 1000)}
        selected = []
        seen = set()
        for item in raw_words:
            key = vocab_key(item.get("word", "") if isinstance(item, dict) else item)
            if not key or key in seen or key not in known:
                continue
            selected.append(known[key])
            seen.add(key)
            if len(selected) >= limit:
                break
        selections = room.setdefault("selections", {})
        selections.setdefault(username, {})[target] = selected
        room["updated_at"] = time.time()
        return game_public_room(room, username)


def game_autofill_room_selections(room: dict) -> None:
    players = room.get("players") if isinstance(room.get("players"), dict) else {}
    if len(players) < 2:
        return
    limit = game_room_word_limit(room.get("word_limit", GAME_MAX_WORDS))
    selections = room.setdefault("selections", {})
    rng = secrets.SystemRandom()
    player_names = [normalize_username(name) for name in players.keys() if normalize_username(name)]
    for selector in player_names:
        selector_bucket = selections.setdefault(selector, {})
        for target in player_names:
            if target == selector:
                continue
            current = selector_bucket.setdefault(target, [])
            if not isinstance(current, list):
                current = []
                selector_bucket[target] = current
            seen = {vocab_key(item.get("word", "") if isinstance(item, dict) else item) for item in current}
            if len(seen) >= limit:
                selector_bucket[target] = current[:limit]
                continue
            pool = [
                item
                for item in game_player_words(target, 1000)
                if vocab_key(item.get("word", "")) and vocab_key(item.get("word", "")) not in seen
            ]
            rng.shuffle(pool)
            for item in pool:
                key = vocab_key(item.get("word", ""))
                if not key or key in seen:
                    continue
                current.append(item)
                seen.add(key)
                if len(seen) >= limit:
                    break
            selector_bucket[target] = current[:limit]


def game_build_battle_plan(room: dict) -> dict:
    players = room.get("players") if isinstance(room.get("players"), dict) else {}
    selections = room.get("selections") if isinstance(room.get("selections"), dict) else {}
    player_names = [normalize_username(name) for name in players.keys() if normalize_username(name)]
    limit = game_room_word_limit(room.get("word_limit", GAME_MAX_WORDS))
    rng = secrets.SystemRandom()
    battle = {
        "created_at": time.time(),
        "round_count": 3,
        "break_seconds": 120,
        "word_limit": limit,
        "players": {},
    }
    for target in player_names:
        incoming = []
        seen = set()
        if len(player_names) == 1:
            raw_solo_items = game_player_words(target, 1000)
            rng.shuffle(raw_solo_items)
            raw_sources = [("system", raw_solo_items)]
        else:
            raw_sources = [
                (
                    selector,
                    selections.get(selector, {}).get(target, []) if isinstance(selections.get(selector), dict) else [],
                )
                for selector in player_names
                if selector != target
            ]
        for selector, raw_items in raw_sources:
            for item in raw_items if isinstance(raw_items, list) else []:
                if not isinstance(item, dict):
                    continue
                key = vocab_key(item.get("word", ""))
                if not key or key in seen:
                    continue
                seen.add(key)
                incoming.append(
                    {
                        "key": key,
                        "word": clean(item.get("word", "")),
                        "meaning": clean(item.get("meaning", "")),
                        "pron": clean(item.get("pron", "")),
                        "type": clean(item.get("type", "")),
                        "source": "system" if selector == "system" else clean(selector),
                    }
                )
        rng.shuffle(incoming)
        incoming = incoming[:limit]
        rounds = [{"round": index + 1, "monsters": []} for index in range(3)]
        for index, item in enumerate(incoming):
            round_index = min(2, int(index * 3 / max(1, len(incoming))))
            hp_base = (95, 155, 235)[round_index]
            speed_base = (0.82, 0.96, 1.12)[round_index]
            word_length = max(1, len(clean(item.get("word", "")).replace(" ", "")))
            rounds[round_index]["monsters"].append(
                {
                    **item,
                    "id": f"{target}-{round_index + 1}-{index + 1}",
                    "hp": hp_base + word_length * (7 + round_index * 2),
                    "speed": speed_base,
                    "reward": 3 + round_index * 2,
                }
            )
        battle["players"][target] = {
            "castle_hp": 1000,
            "crystals": 120,
            "incoming_total": len(incoming),
            "rounds": rounds,
        }
    room["battle"] = battle
    return battle


def game_ready(username: str, payload: dict) -> dict:
    username = normalize_username(username)
    room_id = clean(payload.get("room", "")).upper()
    with GAME_LOCK:
        room = GAME_ROOMS.get(room_id)
        if not room:
            raise RuntimeError("Khong tim thay phong game.")
        players = room.get("players") if isinstance(room.get("players"), dict) else {}
        if username not in players:
            raise RuntimeError("Nguoi choi khong nam trong phong.")
        room.setdefault("ready", {})[username] = bool(payload.get("ready", True))
        room_full = len(players) >= game_room_seat_count(room.get("seat_count", GAME_DEFAULT_SEATS))
        if players and room_full and all(bool(room.get("ready", {}).get(name)) for name in players):
            game_autofill_room_selections(room)
            game_build_battle_plan(room)
            room["status"] = "battle"
        else:
            room["status"] = "lobby"
        room["updated_at"] = time.time()
        return game_public_room(room, username)


def game_cancel_room(username: str, payload: dict) -> dict:
    username = normalize_username(username)
    room_id = clean(payload.get("room", "")).upper()
    with GAME_LOCK:
        room = GAME_ROOMS.get(room_id)
        if not room:
            raise RuntimeError("Khong tim thay phong game.")
        players = room.get("players") if isinstance(room.get("players"), dict) else {}
        if username not in players:
            raise RuntimeError("Nguoi choi khong nam trong phong.")
        is_host = username == normalize_username(room.get("host", ""))
        if is_host or len(players) <= 1:
            GAME_ROOMS.pop(room_id, None)
            return {"cancelled": True, "room_id": room_id, **game_room_state(username)}

        players.pop(username, None)
        ready = room.get("ready") if isinstance(room.get("ready"), dict) else {}
        ready.pop(username, None)
        selections = room.get("selections") if isinstance(room.get("selections"), dict) else {}
        selections.pop(username, None)
        for targets in selections.values():
            if isinstance(targets, dict):
                targets.pop(username, None)
        room.pop("battle", None)
        room["status"] = "lobby"
        room["updated_at"] = time.time()
        return {"cancelled": False, "room": game_public_room(room, username)}
