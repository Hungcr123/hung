# Loaded by FUTURE.server_parts.08_progress_inventory_vocab into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

import copy

def inventory_path(username: str) -> Path:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    return user_folder_path(username) / INVENTORY_FILE_NAME


def clean_inventory_item_id(value: object) -> str:
    item_id = re.sub(r"[^a-z0-9_.-]+", "-", clean(value).lower()).strip("-")
    return item_id[:64] or "crystal"


def normalize_inventory_item(value: object = None) -> dict:
    data = value if isinstance(value, dict) else {}
    item_id = clean_inventory_item_id(data.get("id") or data.get("item_id") or data.get("itemId") or "crystal")
    name = clean(data.get("name") or data.get("title") or "Prism Crystal")[:120]
    use = clean(data.get("use") or data.get("purpose") or data.get("description") or "Stores learning energy for future item upgrades.")[:600]
    try:
        quantity = int(float(data.get("quantity", data.get("count", 0)) or 0))
    except Exception:
        quantity = 0
    return {
        "id": item_id,
        "name": name or "Prism Crystal",
        "use": use or "Stores learning energy for future item upgrades.",
        "quantity": max(0, quantity),
        "updated_at": clean(data.get("updated_at") or data.get("updatedAt") or ""),
    }


def normalize_inventory_payload(payload: object) -> dict:
    data = payload if isinstance(payload, dict) else {}
    raw_items = data.get("items") if isinstance(data.get("items"), dict) else {}
    items = {}
    for key, value in raw_items.items():
        item = normalize_inventory_item(value)
        if not item.get("id"):
            item["id"] = clean_inventory_item_id(key)
        items[item["id"]] = item
    events = data.get("events") if isinstance(data.get("events"), list) else []
    clean_events = [clean(event)[:240] for event in events if clean(event)]
    return {
        "version": 1,
        "updated_at": clean(data.get("updated_at") or data.get("updatedAt") or ""),
        "items": items,
        "events": clean_events[-5000:],
    }


INVENTORY_RAM_CACHE: dict[str, dict] = {}


def clone_inventory_payload(payload: dict | None = None) -> dict:
    # Added 2026-07-06: keeps inventory reads RAM-first while callers still get isolated payloads.
    return normalize_inventory_payload(copy.deepcopy(payload if isinstance(payload, dict) else {}))


def inventory_file_signature(username: str) -> tuple:
    normalized = normalize_username(username)
    return (normalized.lower(), server_database_user_generation("inventory", normalized))


def read_inventory_file(username: str, event_limit: int = 5000) -> dict:
    return normalize_inventory_payload(server_database_load_inventory_payload(username, event_limit=event_limit))


def write_inventory_file(username: str, payload: dict) -> None:
    server_database_replace_inventory_payload(username, normalize_inventory_payload(payload))


def public_inventory_from_payload(username: str, payload: dict) -> dict:
    username = normalize_username(username)
    items = payload.get("items") if isinstance(payload.get("items"), dict) else {}
    return {
        "username": username,
        "inventory": {
            "version": 1,
            "updated_at": clean(payload.get("updated_at", "")),
            "items": items,
            "events": list(payload.get("events") if isinstance(payload.get("events"), list) else [])[-5000:],
        },
    }


def public_inventory(username: str, compact: bool = False) -> dict:
    username = normalize_username(username)
    with INVENTORY_LOCK:
        payload = read_inventory_file(username, event_limit=0 if compact else 5000)
    return public_inventory_from_payload(username, payload)


def normalize_inventory_award_payload(username: str, award_payload: dict) -> dict:
    # Added 2026-07-06: normalizes one award entry so batch reward claims can write inventory once.
    source = award_payload if isinstance(award_payload, dict) else {}
    item = normalize_inventory_item(source.get("item") if isinstance(source.get("item"), dict) else source)
    try:
        quantity = int(float(source.get("quantity", source.get("count", 1)) or 1))
    except Exception:
        quantity = 1
    quantity = max(1, min(9999, quantity))
    event_id = clean(source.get("event_id") or source.get("eventId") or source.get("key") or "")[:240]
    if not event_id:
        raw = f"{username}|{item['id']}|{time.time_ns()}"
        event_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
    return {"item": item, "quantity": quantity, "event_id": event_id}


def apply_inventory_award_to_payload(payload: dict, award: dict) -> dict:
    item = normalize_inventory_item(award.get("item") if isinstance(award.get("item"), dict) else award)
    quantity = max(1, min(9999, space_w_int(award.get("quantity", 1), 1)))
    event_id = clean(award.get("event_id", ""))[:240]
    events = payload.setdefault("events", [])
    awarded = False
    if event_id and event_id not in events:
        items = payload.setdefault("items", {})
        current = normalize_inventory_item(items.get(item["id"], {}))
        current["id"] = item["id"]
        current["name"] = item.get("name") or current.get("name") or "Prism Crystal"
        current["use"] = item.get("use") or current.get("use") or "Stores learning energy for future item upgrades."
        current["quantity"] = max(0, int(current.get("quantity", 0) or 0)) + quantity
        current["updated_at"] = utc_timestamp()
        items[item["id"]] = current
        events.append(event_id)
        payload["events"] = events[-5000:]
        awarded = True
    return {"awarded": awarded, "event_id": event_id, "item": item, "quantity": quantity}


def award_inventory_items(
    username: str,
    award_payloads: list[dict] | tuple[dict, ...],
    authenticated_user: bool = False,
) -> dict:
    username = normalize_username(username)
    normalized_awards = [normalize_inventory_award_payload(username, payload) for payload in (award_payloads if isinstance(award_payloads, (list, tuple)) else [])]
    committed = server_database_award_inventory_items(username, normalized_awards, authenticated_user=authenticated_user)
    results = committed.get("results") if isinstance(committed.get("results"), list) else []
    inventory_delta = {
        "version": 1,
        "updated_at": clean(committed.get("updated_at", "")),
        "items": committed.get("items") if isinstance(committed.get("items"), dict) else {},
        "events": committed.get("events") if isinstance(committed.get("events"), list) else [],
    }
    return {
        "username": username,
        "inventory": inventory_delta,
        "inventory_delta": True,
        "awards": results,
        "awarded": any(bool(item.get("awarded")) for item in results),
    }


def award_inventory_item(username: str, award_payload: dict, authenticated_user: bool = False) -> dict:
    username = normalize_username(username)
    batch = award_inventory_items(username, [award_payload], authenticated_user=authenticated_user)
    result = batch.get("awards", [{}])[0] if isinstance(batch.get("awards"), list) and batch.get("awards") else {}
    return {**batch, **result}


def load_shared_world_keyboard_state() -> dict:
    payload = server_database_read_document_json(SHARED_WORLD_KEYBOARD_FILE, {})
    if isinstance(payload, dict):
        users = payload.get("users") if isinstance(payload.get("users"), dict) else {}
        return {"version": 1, "updated_at": clean(payload.get("updated_at", "")), "users": users}
    return {"version": 1, "users": {}}


def write_shared_world_keyboard_state(state: dict) -> None:
    payload = state if isinstance(state, dict) else {}
    payload["version"] = 1
    payload["updated_at"] = utc_timestamp()
    atomic_write_json(SHARED_WORLD_KEYBOARD_FILE, payload, indent=2)


def shared_world_keyboard_pass_for_user(username: str, state: dict | None = None) -> dict:
    username = normalize_username(username)
    source = state if isinstance(state, dict) else load_shared_world_keyboard_state()
    users = source.get("users") if isinstance(source.get("users"), dict) else {}
    row = users.get(username) if isinstance(users.get(username), dict) else {}
    expires_at = clean(row.get("expires_at", ""))
    expires_epoch = timestamp_to_epoch(expires_at)
    remaining = max(0, int(expires_epoch - time.time())) if expires_epoch else 0
    return {
        "enabled": remaining > 0,
        "expires_at": expires_at if remaining > 0 else "",
        "remaining_seconds": remaining,
        "cost": 10,
        "currency": "random_crystals",
    }


def buy_shared_world_keyboard_pass(username: str) -> dict:
    username = normalize_username(username)
    if is_admin_user(username):
        expires_epoch = time.time() + 24 * 60 * 60
        with SHARED_WORLD_KEYBOARD_LOCK:
            state = load_shared_world_keyboard_state()
            users = state.setdefault("users", {})
            users[username] = {"expires_at": local_timestamp(expires_epoch), "admin": True, "updated_at": utc_timestamp()}
            write_shared_world_keyboard_state(state)
        return {"keyboard_pass": shared_world_keyboard_pass_for_user(username), "spent": [], **public_inventory(username)}

    cost = 10
    spent: list[dict] = []
    with INVENTORY_LOCK:
        payload = read_inventory_file(username)
        items = payload.setdefault("items", {})
        available = [
            item_id for item_id, item in items.items()
            if isinstance(item, dict) and int(item.get("quantity", 0) or 0) > 0 and not clean_inventory_item_id(item_id).startswith("leaderboard_badge")
        ]
        total = sum(int(items[item_id].get("quantity", 0) or 0) for item_id in available)
        if total < cost:
            raise RuntimeError("You need 10 crystals to unlock arrow movement for 1 hour.")
        for _ in range(cost):
            available = [item_id for item_id in available if int(items[item_id].get("quantity", 0) or 0) > 0]
            item_id = secrets.choice(available)
            item = normalize_inventory_item(items.get(item_id, {}))
            item["quantity"] = max(0, int(item.get("quantity", 0) or 0) - 1)
            item["updated_at"] = utc_timestamp()
            items[item_id] = item
            row = next((entry for entry in spent if entry.get("id") == item_id), None)
            if row:
                row["quantity"] += 1
            else:
                spent.append({"id": item_id, "name": item.get("name", item_id), "quantity": 1})
        payload["events"] = list(payload.get("events") if isinstance(payload.get("events"), list) else [])[-4990:] + [f"qm-city-keyboard-pass:{time.time_ns()}"]
        write_inventory_file(username, payload)

    expires_epoch = time.time() + 60 * 60
    with SHARED_WORLD_KEYBOARD_LOCK:
        state = load_shared_world_keyboard_state()
        users = state.setdefault("users", {})
        users[username] = {"expires_at": local_timestamp(expires_epoch), "spent": spent, "updated_at": utc_timestamp()}
        write_shared_world_keyboard_state(state)
    return {"keyboard_pass": shared_world_keyboard_pass_for_user(username), "spent": spent, **public_inventory(username)}


def read_server_asset(relative_path: str = "") -> tuple[bytes, str]:
    target = safe_server_asset_path(relative_path)
    structure_asset = server_asset_category(target) == "Structure"
    if not structure_asset and not target.is_file():
        raise RuntimeError("Asset khong ton tai.")
    assert_server_asset_allowed(target)
    suffix = target.suffix.lower()
    content_type = {
        ".json": "application/json; charset=utf-8",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".webm": "video/webm",
        ".mp4": "video/mp4",
        ".m4v": "video/mp4",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
        ".wmv": "video/x-ms-wmv",
        ".flv": "video/x-flv",
        ".mpeg": "video/mpeg",
        ".mpg": "video/mpeg",
        ".m2ts": "video/mp2t",
        ".mts": "video/mp2t",
        ".ts": "video/mp2t",
        ".ogv": "video/ogg",
        ".3gp": "video/3gpp",
        ".3g2": "video/3gpp2",
        ".vob": "video/dvd",
        ".asf": "video/x-ms-asf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".jfif": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml; charset=utf-8",
        ".bmp": "image/bmp",
    }.get(suffix, "application/octet-stream")
    if structure_asset:
        return structure_asset_bytes(relative_path), content_type
    return target.read_bytes(), content_type


def read_qmlearn_data_sound(relative_path: str = "") -> tuple[bytes, str]:
    target = safe_qmlearn_data_sound_path(relative_path)
    return read_qmlearn_data_sound_file(target)


def read_qmlearn_data_sound_by_text(text: object = "") -> tuple[bytes, str]:
    target = qmdict_meaning_audio_local_path(text)
    if target is None:
        raise RuntimeError("Audio QMLearn theo meaning khong ton tai.")
    return read_qmlearn_data_sound_file(target)


def read_qmlearn_data_sound_by_voice_text(text: object = "", voice_key: object = "") -> tuple[bytes, str]:
    target_text = clean(text)
    target_voice = clean(voice_key) or "sot:en-GB"
    if not target_text:
        raise RuntimeError("Missing audio text.")
    target = fast_qmlearn_audio_path(target_text, target_voice)
    if target is None:
        raise RuntimeError("Audio QMLearn theo word/voice khong ton tai.")
    return read_qmlearn_data_sound_file(target)


QMLEARN_DATA_SOUND_BYTES_CACHE: dict[str, dict] = {}
QMLEARN_DATA_SOUND_BYTES_CACHE_LOCK = threading.RLock()
QMLEARN_DATA_SOUND_BYTES_CACHE_MAX_ITEMS = 384
QMLEARN_DATA_SOUND_BYTES_CACHE_MAX_BYTES = 160 * 1024 * 1024
QMLEARN_DATA_ROOT_RESOLVED_CACHE = None


def qmlearn_data_root_resolved() -> Path:
    global QMLEARN_DATA_ROOT_RESOLVED_CACHE
    if QMLEARN_DATA_ROOT_RESOLVED_CACHE is None:
        QMLEARN_DATA_ROOT_RESOLVED_CACHE = QMLEARN_DATA_ROOT.resolve()
    return QMLEARN_DATA_ROOT_RESOLVED_CACHE


def qmlearn_sound_cache_key(target: Path) -> tuple[str, tuple[int, int]]:
    resolved = target.resolve()
    try:
        resolved.relative_to(qmlearn_data_root_resolved())
    except Exception as exc:
        raise RuntimeError("Chi duoc tai audio trong C:\\QMLearn\\Data.") from exc
    try:
        stat = resolved.stat()
        signature = (int(stat.st_mtime_ns), int(stat.st_size))
    except OSError as exc:
        raise RuntimeError("Audio QMLearn khong ton tai.") from exc
    return str(resolved).lower(), signature


def prune_qmlearn_data_sound_bytes_cache_locked() -> None:
    total = 0
    for row in QMLEARN_DATA_SOUND_BYTES_CACHE.values():
        if isinstance(row, dict):
            total += int(row.get("size", 0) or 0)
    if total <= QMLEARN_DATA_SOUND_BYTES_CACHE_MAX_BYTES and len(QMLEARN_DATA_SOUND_BYTES_CACHE) <= QMLEARN_DATA_SOUND_BYTES_CACHE_MAX_ITEMS:
        return
    ordered = sorted(QMLEARN_DATA_SOUND_BYTES_CACHE.items(), key=lambda item: float(item[1].get("at", 0) or 0))
    for old_key, row in ordered:
        if total <= QMLEARN_DATA_SOUND_BYTES_CACHE_MAX_BYTES and len(QMLEARN_DATA_SOUND_BYTES_CACHE) <= QMLEARN_DATA_SOUND_BYTES_CACHE_MAX_ITEMS:
            break
        QMLEARN_DATA_SOUND_BYTES_CACHE.pop(old_key, None)
        if isinstance(row, dict):
            total -= int(row.get("size", 0) or 0)


def read_qmlearn_data_sound_file(target: Path) -> tuple[bytes, str]:
    # Added 2026-07-06: caches repeated Space_V word audio reads when many users open the same lesson.
    target = Path(target)
    cache_key, signature = qmlearn_sound_cache_key(target)
    suffix = Path(cache_key).suffix.lower()
    if suffix not in {".mp3", ".txt"}:
        raise RuntimeError("Audio QMLearn khong ton tai.")
    now = time.time()
    with QMLEARN_DATA_SOUND_BYTES_CACHE_LOCK:
        row = QMLEARN_DATA_SOUND_BYTES_CACHE.get(cache_key)
        if isinstance(row, dict) and row.get("signature") == signature and isinstance(row.get("data"), bytes):
            row["at"] = now
            return row["data"], "audio/mpeg"
    try:
        resolved = Path(cache_key)
        if suffix == ".mp3":
            audio_bytes = resolved.read_bytes()
        else:
            if str(PROGRAME_ROOT) not in sys.path:
                sys.path.insert(0, str(PROGRAME_ROOT))
            from module_main.Data_Input.local_sound_loader import read_sound_file_bytes  # noqa: PLC0415

            audio_bytes = read_sound_file_bytes(resolved, migrate=True)
    except Exception as exc:
        raise RuntimeError(f"Khong doc duoc audio QMLearn: {exc}") from exc
    if not audio_bytes:
        raise RuntimeError("Audio QMLearn rong.")
    data = bytes(audio_bytes)
    with QMLEARN_DATA_SOUND_BYTES_CACHE_LOCK:
        QMLEARN_DATA_SOUND_BYTES_CACHE[cache_key] = {"signature": signature, "data": data, "size": len(data), "at": now}
        prune_qmlearn_data_sound_bytes_cache_locked()
    return data, "audio/mpeg"


# Added 2026-07-30: read bytes and revision as one stable observation so a
# replacement cannot pair an old payload with a new immutable URL revision.
def read_qmlearn_data_sound_file_revisioned(target: Path, attempts: int = 3) -> tuple[bytes, str, str]:
    target = Path(target)
    for _ in range(max(1, int(attempts or 1))):
        try:
            _cache_key, before = qmlearn_sound_cache_key(target)
            data, content_type = read_qmlearn_data_sound_file(target)
            _cache_key, after = qmlearn_sound_cache_key(target)
        except Exception:
            raise
        if before == after:
            revision = f"{after[0]:x}-{after[1]:x}"
            return data, content_type, revision
    raise RuntimeError("Audio QMLearn dang duoc thay trong luc doc.")


# Added 2026-07-30: serve immutable revision URLs from bounded RAM after the first stable file observation.
def qmlearn_http_audio_cache_get(cache_key: object = "") -> dict | None:
    key = clean(cache_key)
    if not key:
        return None
    with QMLEARN_HTTP_AUDIO_CACHE_LOCK:
        row = QMLEARN_HTTP_AUDIO_CACHE.get(key)
        if not isinstance(row, dict) or not isinstance(row.get("data"), bytes):
            return None
        row["at"] = time.time()
        return row


# Added 2026-07-31: stale revision URLs must never revive overwritten audio from Server 2 RAM.
def qmlearn_http_audio_cache_get_current(
    cache_key: object,
    requested_revision: object,
    current_revision: object,
) -> dict | None:
    requested = clean(requested_revision)
    current = clean(current_revision)
    if not requested or requested != current:
        return None
    row = qmlearn_http_audio_cache_get(cache_key)
    if not row or clean(row.get("revision")) != current:
        return None
    return row


# Added 2026-07-30: bound immutable audio RAM by both item count and payload bytes.
def qmlearn_http_audio_cache_put(cache_key: object, data: bytes, content_type: str, revision: str, etag: str) -> None:
    key = clean(cache_key)
    payload = bytes(data or b"")
    if not key or not payload:
        return
    now = time.time()
    with QMLEARN_HTTP_AUDIO_CACHE_LOCK:
        QMLEARN_HTTP_AUDIO_CACHE[key] = {
            "data": payload,
            "content_type": clean(content_type) or "audio/mpeg",
            "revision": clean(revision),
            "etag": clean(etag),
            "size": len(payload),
            "at": now,
        }
        total = sum(int(row.get("size", 0) or 0) for row in QMLEARN_HTTP_AUDIO_CACHE.values() if isinstance(row, dict))
        if total <= QMLEARN_HTTP_AUDIO_CACHE_MAX_BYTES and len(QMLEARN_HTTP_AUDIO_CACHE) <= QMLEARN_HTTP_AUDIO_CACHE_MAX_ITEMS:
            return
        for old_key, row in sorted(QMLEARN_HTTP_AUDIO_CACHE.items(), key=lambda item: float(item[1].get("at", 0) or 0)):
            if total <= QMLEARN_HTTP_AUDIO_CACHE_MAX_BYTES and len(QMLEARN_HTTP_AUDIO_CACHE) <= QMLEARN_HTTP_AUDIO_CACHE_MAX_ITEMS:
                break
            QMLEARN_HTTP_AUDIO_CACHE.pop(old_key, None)
            if isinstance(row, dict):
                total -= int(row.get("size", 0) or 0)


VOCAB_MISSION_PENDING_DIR = "Immediate Mission"
VOCAB_MISSION_ARCHIVE_DIR = "Learned Vocabulary"
VOCAB_REGISTRY_FILE = "_future_learned_vocabulary.json"
VOCAB_MISSION_CHUNK_SIZE = 25
