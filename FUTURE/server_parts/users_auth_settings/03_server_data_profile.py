# Loaded by FUTURE.server_parts.02_users_auth_settings into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def server_data_user_folder_path(username: str) -> Path:
    return SERVER_DATA_ROOT / normalize_username(username)


def learner_user_exists(username: str) -> bool:
    username = normalize_username(username)
    ok, _message = validate_username(username)
    if not ok:
        return False
    if server_database_user_exists(username):
        return True
    if user_folder_path(username).is_dir():
        return True
    if server_data_user_folder_path(username).is_dir():
        return True
    try:
        return any(path.is_dir() for path in main_server_user_dirs(username))
    except Exception:
        return False


def ensure_server_data_common_folder() -> dict:
    SERVER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    common_path = SERVER_DATA_ROOT / "common"
    common_path.mkdir(parents=True, exist_ok=True)
    SERVER_SOUND_DIR.mkdir(parents=True, exist_ok=True)
    # Added 2026-07-20: Structure is a logical SQLite asset namespace, not a physical JSON folder.
    SERVER_PICTURE_DIR.mkdir(parents=True, exist_ok=True)
    return {
        "root": str(SERVER_DATA_ROOT),
        "common": "common",
        "sound": "Sound",
        "structure": "Structure",
        "picture": "Picture",
    }


ENSURE_SERVER_DATA_FOLDERS_CACHE: dict[str, dict] = {}
ENSURE_SERVER_DATA_FOLDERS_CACHE_LOCK = threading.RLock()
ENSURE_SERVER_DATA_FOLDERS_CACHE_SECONDS = 60.0


def ensure_server_data_folders(username: str) -> dict:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    now = time.time()
    with ENSURE_SERVER_DATA_FOLDERS_CACHE_LOCK:
        cached = ENSURE_SERVER_DATA_FOLDERS_CACHE.get(username)
        if isinstance(cached, dict) and now - float(cached.get("at", 0) or 0) < ENSURE_SERVER_DATA_FOLDERS_CACHE_SECONDS:
            payload = cached.get("payload") if isinstance(cached.get("payload"), dict) else {}
            if payload:
                return dict(payload)
    info = ensure_server_data_common_folder()
    is_test_user = globals().get("server_database_is_test_user")
    if callable(is_test_user) and is_test_user(username):
        payload = {
            **info,
            "user": username,
            "user_folder": "",
            "created_user_folder": False,
            "load_test": True,
        }
        with ENSURE_SERVER_DATA_FOLDERS_CACHE_LOCK:
            ENSURE_SERVER_DATA_FOLDERS_CACHE[username] = {"at": now, "payload": dict(payload)}
        return payload
    user_path = server_data_user_folder_path(username)
    existed = user_path.is_dir()
    user_path.mkdir(parents=True, exist_ok=True)
    if not existed:
        try:
            schedule_server_data_manifest_paths_refresh([username, ""], 0.8, "new-user-folder")
        except Exception:
            pass
    payload = {
        **info,
        "user": username,
        "user_folder": str(user_path),
        "created_user_folder": not existed,
    }
    with ENSURE_SERVER_DATA_FOLDERS_CACHE_LOCK:
        ENSURE_SERVER_DATA_FOLDERS_CACHE[username] = {"at": now, "payload": dict(payload)}
        if len(ENSURE_SERVER_DATA_FOLDERS_CACHE) > 1200:
            for old_key in list(ENSURE_SERVER_DATA_FOLDERS_CACHE.keys())[:200]:
                ENSURE_SERVER_DATA_FOLDERS_CACHE.pop(old_key, None)
    return payload


def parse_user_header(line: str) -> tuple[str, str]:
    if ":" not in str(line or ""):
        return "", ""
    username, password = str(line or "").split(":", 1)
    return username.strip(), password


USER_PROFILE_RAM_CACHE: dict[str, dict] = {}


def user_profile_cache_signature(username: str) -> tuple:
    database_signature = server_database_user_profile_signature(username)
    if any(database_signature):
        return ("postgresql", *database_signature)
    path = user_file_path(username)
    try:
        stat = path.stat()
        mtime_ns = int(stat.st_mtime_ns)
        size = int(stat.st_size)
    except Exception:
        mtime_ns = 0
        size = 0
    return "legacy", mtime_ns, size


def clone_user_profile_payload(profile: dict | None = None) -> dict:
    try:
        return json.loads(json.dumps(profile if isinstance(profile, dict) else {}, ensure_ascii=False))
    except Exception:
        return dict(profile or {})


def read_user_profile(username: str) -> dict:
    username = normalize_username(username)
    try:
        npc_profile_getter = globals().get("npc_top_profile_for_user")
        if callable(npc_profile_getter):
            npc_profile = npc_profile_getter(username)
            if npc_profile:
                return npc_profile
        city_npc_profile_getter = globals().get("shared_world_city_npc_profile_for_user")
        if callable(city_npc_profile_getter):
            city_npc_profile = city_npc_profile_getter(username)
            if city_npc_profile:
                return city_npc_profile
    except Exception:
        pass
    cache_key = username.lower()
    signature = user_profile_cache_signature(username)
    cached = USER_PROFILE_RAM_CACHE.get(cache_key)
    if isinstance(cached, dict) and cached.get("signature") == signature and isinstance(cached.get("profile"), dict):
        return clone_user_profile_payload(cached.get("profile"))
    if postgres_backend_mode("USER_AUTH_DOCS") == "postgres":
        postgres_profile = postgres_load_user_profile(username)
        if isinstance(postgres_profile, dict) and postgres_profile:
            USER_PROFILE_RAM_CACHE[cache_key] = {"signature": signature, "profile": clone_user_profile_payload(postgres_profile)}
            return clone_user_profile_payload(postgres_profile)
    database_loader = globals().get("server_database_load_user_profile")
    if callable(database_loader):
        database_profile = database_loader(username)
        if isinstance(database_profile, dict) and database_profile:
            USER_PROFILE_RAM_CACHE[cache_key] = {"signature": signature, "profile": clone_user_profile_payload(database_profile)}
            return clone_user_profile_payload(database_profile)
    for line in read_user_lines(username)[1:]:
        raw = str(line or "").strip()
        if not raw.startswith(PROFILE_PREFIX):
            continue
        try:
            payload = json.loads(raw[len(PROFILE_PREFIX):].strip())
            if isinstance(payload, dict):
                photos = normalize_profile_photos(
                    payload.get("profile_photos") or payload.get("gallery") or payload.get("photos") or []
                )
                profile = {
                    "full_name": clean(payload.get("full_name", "")),
                    "gender": clean(payload.get("gender", "")),
                    "birth_date": clean(payload.get("birth_date", "")),
                    "email": normalize_profile_email(payload.get("email", payload.get("gmail", ""))),
                    "email_alias": clean(payload.get("email_alias", payload.get("emailAlias", "")))[:254],
                    "avatar": clean(payload.get("avatar") or payload.get("avatar_url") or payload.get("avatarUrl") or "")[:600],
                    "intro": clean(payload.get("intro") or payload.get("bio") or payload.get("about") or "")[:1200],
                    "profile_photos": photos,
                    "updated_at": clean(payload.get("updated_at", "")),
                }
                USER_PROFILE_RAM_CACHE[cache_key] = {"signature": signature, "profile": clone_user_profile_payload(profile)}
                if len(USER_PROFILE_RAM_CACHE) > 1200:
                    for old_key in list(USER_PROFILE_RAM_CACHE.keys())[:200]:
                        USER_PROFILE_RAM_CACHE.pop(old_key, None)
                return profile
        except Exception:
            return {}
    npc_fallback_match = re.fullmatch(r"(?:citynpc|npc)_?(\d{1,8})", clean(username).lower())
    if npc_fallback_match:
        try:
            number = max(1, int(npc_fallback_match.group(1) or "1"))
        except Exception:
            number = 1
        display_name = f"QM-City Learner {number:02d}"
        profile = {
            "full_name": display_name,
            "display_name": display_name,
            "gender": "other",
            "birth_date": "",
            "avatar": "",
            "intro": "",
            "profile_photos": [],
            "updated_at": "",
        }
        USER_PROFILE_RAM_CACHE[cache_key] = {"signature": signature, "profile": clone_user_profile_payload(profile)}
        return profile
    USER_PROFILE_RAM_CACHE[cache_key] = {"signature": signature, "profile": {}}
    return {}


def normalize_profile_photos(value: object) -> list[str]:
    source = value if isinstance(value, list) else []
    photos: list[str] = []
    seen: set[str] = set()
    for item in source:
        if isinstance(item, dict):
            raw = item.get("path") or item.get("photo") or item.get("url") or item.get("src") or ""
        else:
            raw = item
        path = clean(raw).replace("\\", "/")[:600]
        if not path or path in seen:
            continue
        photos.append(path)
        seen.add(path)
        if len(photos) >= 4:
            break
    return photos


# Added 2026-07-09: validates optional Gmail recovery addresses saved in user profiles.
def normalize_profile_email(value: object = "") -> str:
    email = clean(str(value or "")).strip().lower()
    if not email or len(email) > 254 or "@" not in email:
        return ""
    local, domain = email.rsplit("@", 1)
    if not local or not domain or len(local) > 64 or len(domain) > 253:
        return ""
    if not re.match(r"^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+$", local):
        return ""
    if not re.match(r"^[a-z0-9.-]+\.[a-z0-9.-]+$", domain):
        return ""
    return email


# Added 2026-07-09: derives a stable per-user recovery alias from the configured email-routing domain.
def user_email_alias(username: str) -> str:
    username = normalize_username(username)
    if not username:
        return ""
    domain = ""
    try:
        config_getter = globals().get("cloudflare_email_routing_effective_config")
        domain_normalizer = globals().get("normalize_email_routing_domain")
        if callable(config_getter) and callable(domain_normalizer):
            domain = domain_normalizer(config_getter().get("domain", ""))
    except Exception:
        domain = ""
    if not domain:
        try:
            domain = normalize_email_routing_domain(CLOUDFLARE_EMAIL_ROUTING_DEFAULT_DOMAIN)
        except Exception:
            domain = ""
    return f"{username}@{domain}" if domain else ""


def normalize_profile(payload: dict) -> dict:
    profile = payload if isinstance(payload, dict) else {}
    full_name = clean(profile.get("full_name", profile.get("name", "")))
    gender = clean(profile.get("gender", "")).lower()
    birth_date = clean(profile.get("birth_date", profile.get("birthday", "")))
    avatar = clean(profile.get("avatar") or profile.get("avatar_url") or profile.get("avatarUrl") or "")[:600]
    intro = clean(profile.get("intro") or profile.get("bio") or profile.get("about") or "")[:1200]
    email = normalize_profile_email(profile.get("email", profile.get("gmail", "")))
    email_alias = clean(profile.get("email_alias", profile.get("emailAlias", "")))[:254]
    photos = normalize_profile_photos(profile.get("profile_photos") or profile.get("gallery") or profile.get("photos") or [])
    if gender not in ("male", "female", "other"):
        gender = ""
    if birth_date and not re.match(r"^\d{4}-\d{2}-\d{2}$", birth_date):
        birth_date = ""
    return {
        "full_name": full_name[:120],
        "gender": gender,
        "birth_date": birth_date,
        "email": email,
        "email_alias": email_alias,
        "avatar": avatar,
        "intro": intro,
        "profile_photos": photos,
        "updated_at": utc_timestamp(),
    }


def profile_missing(profile: dict) -> list[str]:
    missing = []
    if not clean(profile.get("full_name", "")):
        missing.append("full_name")
    if clean(profile.get("gender", "")).lower() not in ("male", "female", "other"):
        missing.append("gender")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", clean(profile.get("birth_date", ""))):
        missing.append("birth_date")
    return missing


def auth_me_cache_signature(username: str) -> tuple:
    username = normalize_username(username)
    return (
        user_profile_cache_signature(username),
        file_cache_signature(ADMINS_FILE),
        user_preferences_runtime_signature(username),
    )

def auth_me_cache_key(username: str, include_rewards: bool) -> str:
    username = normalize_username(username)
    return f"{username.lower()}|{1 if include_rewards else 0}"


def auth_me_payload(username: str, include_rewards: bool = True) -> dict:
    username = normalize_username(username)
    if not username:
        raise RuntimeError("Chua dang nhap.")
    signature = auth_me_cache_signature(username)
    now = time.time()
    cache_key = auth_me_cache_key(username, include_rewards)
    with AUTH_ME_CACHE_LOCK:
        row = AUTH_ME_CACHE.get(cache_key)
        if (
            isinstance(row, dict)
            and row.get("signature") == signature
            and now - float(row.get("at", 0) or 0) <= AUTH_ME_CACHE_TTL_SECONDS
            and isinstance(row.get("payload"), dict)
        ):
            return dict(row["payload"])
    profile = read_user_profile(username)
    preferences = read_user_preferences(username)
    load_test = server_database_is_test_user(username)
    server_data = {"load_test": True} if load_test else ensure_server_data_folders(username)
    if load_test:
        leaderboard_rewards_claimed = {"claims": [], "items": [], "skipped": "load_test"}
    else:
        try:
            leaderboard_rewards_claimed = maybe_claim_pending_vocab_leaderboard_rewards(username, force=False) if include_rewards else {"claims": [], "items": [], "skipped": "disabled"}
        except Exception as exc:
            leaderboard_rewards_claimed = {"claims": [], "items": [], "error": str(exc)}
    missing = profile_missing(profile)
    payload = {
        "ok": True,
        "username": username,
        "is_admin": is_admin_user(username),
        "profile": profile,
        "preferences": preferences,
        "needs_profile": bool(missing),
        "missing": missing,
        "server_data": server_data,
        "leaderboard_rewards_claimed": leaderboard_rewards_claimed,
    }
    with AUTH_ME_CACHE_LOCK:
        AUTH_ME_CACHE[cache_key] = {"signature": signature, "payload": dict(payload), "at": now}
        if len(AUTH_ME_CACHE) > 256:
            ordered = sorted(AUTH_ME_CACHE.items(), key=lambda item: float(item[1].get("at", 0) or 0))
            for old_key, _old_value in ordered[:64]:
                AUTH_ME_CACHE.pop(old_key, None)
    return payload


def invalidate_auth_me_cache(username: str = "") -> None:
    username = normalize_username(username)
    with AUTH_ME_CACHE_LOCK:
        if username:
            AUTH_ME_CACHE.pop(auth_me_cache_key(username, False), None)
            AUTH_ME_CACHE.pop(auth_me_cache_key(username, True), None)
        else:
            AUTH_ME_CACHE.clear()


def save_user_profile(username: str, profile_payload: dict) -> dict:
    username = normalize_username(username)
    lines = read_user_lines(username)
    if not lines:
        raise RuntimeError("User khong ton tai.")
    existing = read_user_profile(username)
    source = profile_payload if isinstance(profile_payload, dict) else {}
    profile = normalize_profile({**existing, **source})
    if not profile.get("email_alias"):
        profile["email_alias"] = user_email_alias(username)
    missing = profile_missing(profile)
    if missing:
        raise RuntimeError("Thieu thong tin profile: " + ", ".join(missing))
    profile_line = PROFILE_PREFIX + json.dumps(profile, ensure_ascii=False, separators=(",", ":"))
    out = [lines[0]]
    inserted = False
    for line in lines[1:]:
        if str(line or "").strip().startswith(PROFILE_PREFIX):
            if not inserted:
                out.append(profile_line)
                inserted = True
            continue
        out.append(line)
    if not inserted:
        out.insert(1, profile_line)
    write_user_lines(username, out)
    database_upsert = globals().get("server_database_upsert_user")
    if callable(database_upsert):
        database_upsert(username, profile)
    USER_PROFILE_RAM_CACHE[username.lower()] = {"signature": user_profile_cache_signature(username), "profile": clone_user_profile_payload(profile)}
    return profile


def update_user_profile_fields(username: str, fields: dict) -> dict:
    username = normalize_username(username)
    lines = read_user_lines(username)
    if not lines:
        raise RuntimeError("User khong ton tai.")
    existing = read_user_profile(username)
    source = fields if isinstance(fields, dict) else {}
    profile = normalize_profile({**existing, **source})
    profile_line = PROFILE_PREFIX + json.dumps(profile, ensure_ascii=False, separators=(",", ":"))
    out = [lines[0]]
    inserted = False
    for line in lines[1:]:
        if str(line or "").strip().startswith(PROFILE_PREFIX):
            if not inserted:
                out.append(profile_line)
                inserted = True
            continue
        out.append(line)
    if not inserted:
        out.insert(1, profile_line)
    write_user_lines(username, out)
    database_upsert = globals().get("server_database_upsert_user")
    if callable(database_upsert):
        database_upsert(username, profile)
    USER_PROFILE_RAM_CACHE[username.lower()] = {"signature": user_profile_cache_signature(username), "profile": clone_user_profile_payload(profile)}
    return profile
