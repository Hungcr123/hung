# Loaded by FUTURE.server_parts.02_users_auth_settings into the shared Future server runtime namespace.
# This is a nested transitional split; do not import directly yet.

def normalize_username(value: str) -> str:
    return clean(value).lower()


def validate_username(value: str) -> tuple[bool, str]:
    username = normalize_username(value)
    if not username:
        return False, "Ten user khong duoc de trong."
    if len(username) > 32:
        return False, "Ten user toi da 32 ky tu."
    if not username.isalnum():
        return False, "Ten user chi gom a-z, A-Z, 0-9."
    return True, ""


def validate_register_password(value: str) -> tuple[bool, str]:
    password = str(value or "")
    if len(password) < 6:
        return False, "Mat khau phai co it nhat 6 ky tu."
    if not any(ch.islower() for ch in password):
        return False, "Mat khau can co it nhat 1 chu thuong."
    if not any(ch.isupper() for ch in password):
        return False, "Mat khau can co it nhat 1 chu hoa."
    if not any(ch.isdigit() for ch in password):
        return False, "Mat khau can co it nhat 1 chu so."
    return True, ""


def user_file_path(username: str) -> Path:
    return USER_ROOT / f"{normalize_username(username)}.txt"


def user_folder_path(username: str) -> Path:
    return USER_ROOT / normalize_username(username)


USER_LINES_RAM_CACHE: dict[str, dict] = {}
USER_LINES_RAM_CACHE_LOCK = threading.RLock()


def read_user_lines(username: str) -> list[str]:
    path = user_file_path(username)
    cache_key = normalize_username(username)
    try:
        stat = path.stat()
        signature = (int(stat.st_mtime_ns), int(stat.st_size))
    except Exception:
        signature = (0, -1)
    with USER_LINES_RAM_CACHE_LOCK:
        cached = USER_LINES_RAM_CACHE.get(cache_key)
        if isinstance(cached, dict) and cached.get("signature") == signature and isinstance(cached.get("lines"), list):
            return list(cached.get("lines") or [])
    text = server_database_read_document_text(path, "") or ""
    lines = text.lstrip("\ufeff").splitlines()
    with USER_LINES_RAM_CACHE_LOCK:
        USER_LINES_RAM_CACHE[cache_key] = {"signature": signature, "lines": list(lines)}
        if len(USER_LINES_RAM_CACHE) > 1200:
            for old_key in list(USER_LINES_RAM_CACHE.keys())[:200]:
                USER_LINES_RAM_CACHE.pop(old_key, None)
    return lines


def write_user_lines(username: str, lines: list[str]) -> None:
    USER_ROOT.mkdir(parents=True, exist_ok=True)
    user_folder_path(username).mkdir(parents=True, exist_ok=True)
    payload = "\n".join(str(line or "") for line in lines)
    if payload and not payload.endswith("\n"):
        payload += "\n"
    atomic_write_text(user_file_path(username), payload, encoding="utf-8")
    with USER_LINES_RAM_CACHE_LOCK:
        USER_LINES_RAM_CACHE.pop(normalize_username(username), None)


def list_registered_users() -> list[str]:
    return [normalize_username(username) for username in postgres_list_registered_users() if normalize_username(username)]


def read_admins_locked() -> set[str]:
    now = time.time()
    cached = ADMINS_RAM_CACHE if isinstance(ADMINS_RAM_CACHE, dict) else {}
    if now - float(cached.get("checked_at", 0) or 0) <= ADMINS_CACHE_RECHECK_SECONDS:
        return set(cached.get("admins") or set())
    if postgres_backend_mode("USER_AUTH_DOCS") == "postgres":
        admins = set(postgres_load_admin_users() or [])
        ADMINS_RAM_CACHE["admins"] = set(admins)
        ADMINS_RAM_CACHE["checked_at"] = now
        return admins
    try:
        stat = ADMINS_FILE.stat()
        signature = (int(stat.st_mtime_ns), int(stat.st_size))
    except Exception:
        signature = (0, -1)
    if cached.get("signature") == signature:
        ADMINS_RAM_CACHE["checked_at"] = now
        return set(cached.get("admins") or set())
    payload = server_database_read_document_json(ADMINS_FILE, {})
    rows = payload.get("admins", payload) if isinstance(payload, dict) else payload
    if isinstance(rows, list):
        admins = {normalize_username(item) for item in rows if normalize_username(item)}
        ADMINS_RAM_CACHE["signature"] = signature
        ADMINS_RAM_CACHE["admins"] = set(admins)
        ADMINS_RAM_CACHE["checked_at"] = now
        return admins
    ADMINS_RAM_CACHE["signature"] = signature
    ADMINS_RAM_CACHE["admins"] = set()
    ADMINS_RAM_CACHE["checked_at"] = now
    return set()


def write_admins_locked(admins: set[str]) -> None:
    if postgres_backend_mode("USER_AUTH_DOCS") == "postgres":
        rows = {normalize_username(item) for item in admins if normalize_username(item)}
        postgres_replace_admin_users(rows)
        ADMINS_RAM_CACHE["signature"] = ("postgres", time.time())
        ADMINS_RAM_CACHE["admins"] = set(rows)
        ADMINS_RAM_CACHE["checked_at"] = time.time()
        return
    USER_ROOT.mkdir(parents=True, exist_ok=True)
    rows = sorted({normalize_username(item) for item in admins if normalize_username(item)}, key=str.lower)
    atomic_write_json(ADMINS_FILE, {"admins": rows, "updated_at": utc_timestamp()}, indent=2)
    try:
        stat = ADMINS_FILE.stat()
        signature = (int(stat.st_mtime_ns), int(stat.st_size))
    except Exception:
        signature = (0, -1)
    ADMINS_RAM_CACHE["signature"] = signature
    ADMINS_RAM_CACHE["admins"] = set(rows)
    ADMINS_RAM_CACHE["checked_at"] = time.time()


# Added 2026-07-09: keeps admin login blocks in a tiny RAM-cached JSON list.
BLOCKED_LOGIN_USERS_RAM_CACHE: dict[str, object] = {"signature": None, "users": set(), "checked_at": 0.0}


def read_blocked_login_users_locked() -> set[str]:
    now = time.time()
    cached = BLOCKED_LOGIN_USERS_RAM_CACHE if isinstance(BLOCKED_LOGIN_USERS_RAM_CACHE, dict) else {}
    if now - float(cached.get("checked_at", 0) or 0) <= ADMINS_CACHE_RECHECK_SECONDS:
        return set(cached.get("users") or set())
    try:
        stat = BLOCKED_LOGIN_USERS_FILE.stat()
        signature = (int(stat.st_mtime_ns), int(stat.st_size))
    except Exception:
        signature = (0, -1)
    if cached.get("signature") == signature:
        BLOCKED_LOGIN_USERS_RAM_CACHE["checked_at"] = now
        return set(cached.get("users") or set())
    users = set()
    payload = server_database_read_document_json(BLOCKED_LOGIN_USERS_FILE, {})
    rows = payload.get("users", payload.get("blocked", payload)) if isinstance(payload, dict) else payload
    if isinstance(rows, list):
        users = {normalize_username(item) for item in rows if normalize_username(item)}
    BLOCKED_LOGIN_USERS_RAM_CACHE["signature"] = signature
    BLOCKED_LOGIN_USERS_RAM_CACHE["users"] = set(users)
    BLOCKED_LOGIN_USERS_RAM_CACHE["checked_at"] = now
    return set(users)


# Added 2026-07-09: persists login block toggles from the local server dashboard.
def write_blocked_login_users_locked(users: set[str]) -> None:
    USER_ROOT.mkdir(parents=True, exist_ok=True)
    rows = sorted({normalize_username(item) for item in users if normalize_username(item)}, key=str.lower)
    atomic_write_json(BLOCKED_LOGIN_USERS_FILE, {"users": rows, "updated_at": utc_timestamp()}, indent=2)
    try:
        stat = BLOCKED_LOGIN_USERS_FILE.stat()
        signature = (int(stat.st_mtime_ns), int(stat.st_size))
    except Exception:
        signature = (0, -1)
    BLOCKED_LOGIN_USERS_RAM_CACHE["signature"] = signature
    BLOCKED_LOGIN_USERS_RAM_CACHE["users"] = set(rows)
    BLOCKED_LOGIN_USERS_RAM_CACHE["checked_at"] = time.time()


def is_user_login_blocked(username: str) -> bool:
    username = normalize_username(username)
    if not username:
        return False
    with ADMIN_LOCK:
        return username in read_blocked_login_users_locked()


# Added 2026-07-09: toggles login access and revokes active sessions when blocking a user.
def set_user_login_blocked(username: str, blocked: bool = True) -> dict:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    if not server_database_user_exists(username):
        raise RuntimeError("User does not exist.")
    with ADMIN_LOCK:
        users = read_blocked_login_users_locked()
        if blocked:
            users.add(username)
        else:
            users.discard(username)
        write_blocked_login_users_locked(users)
    revoked = 0
    if blocked:
        with AUTH_LOCK:
            now = time.time()
            stale_tokens = [key for key, session in AUTH_SESSIONS.items() if normalize_username(session.get("username", "")) == username]
            for token in stale_tokens:
                AUTH_SESSIONS.pop(token, None)
                AUTH_REVOKED_SESSIONS[token] = {"reason": "user_login_blocked", "username": username, "at": now}
                revoked += 1
        server_database_delete_auth_sessions(username=username)
    invalidate_auth_me_cache(username)
    return {"username": username, "login_blocked": username in users, "blocked_users": sorted(users, key=str.lower), "revoked_sessions": revoked}


def is_admin_user(username: str) -> bool:
    username = normalize_username(username)
    if not username:
        return False
    with ADMIN_LOCK:
        return username in read_admins_locked()


def set_admin_user(username: str, enabled: bool = True) -> dict:
    username = normalize_username(username)
    ok, message = validate_username(username)
    if not ok:
        raise RuntimeError(message)
    if not server_database_user_exists(username):
        raise RuntimeError("User does not exist.")
    migration = {}
    with ADMIN_LOCK:
        admins = read_admins_locked()
        if enabled:
            admins.add(username)
        else:
            was_admin = username in admins
            admins.discard(username)
        write_admins_locked(admins)
    if not enabled and was_admin:
        migration = migrate_admin_learning_to_user(username)
    return {"admins": sorted(admins, key=str.lower), "migration": migration}


def dashboard_admin_payload() -> dict:
    with ADMIN_LOCK:
        admins = read_admins_locked()
        blocked_login_users = read_blocked_login_users_locked()
    users = []
    for username in list_dashboard_usernames():
        profile = read_user_profile(username)
        data_flags = user_data_flags(username)
        users.append({
            "username": username,
            "full_name": clean(profile.get("full_name", "")),
            "is_admin": username in admins,
            "has_account": server_database_user_exists(username),
            "has_data": bool(data_flags),
            "data_flags": data_flags,
            "login_blocked": username in blocked_login_users,
        })
    return {"admins": sorted(admins, key=str.lower), "blocked_login_users": sorted(blocked_login_users, key=str.lower), "users": users}


# Added 2026-07-23: lightweight, paged target-user picker for Admin View.
def dashboard_admin_user_picker_payload(search: str = "", page: int = 1, page_size: int = 10) -> dict:
    query = clean(search).casefold()
    page_size = max(1, min(50, int(page_size or 10)))
    page = max(1, int(page or 1))
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT username,is_admin,profile_json FROM future_server2.users "
                "WHERE COALESCE(is_test,false)=false ORDER BY lower(username)"
            )
            return cursor.fetchall()

    rows = []
    for row in postgres_execute(_read):
        username = normalize_username(row[0])
        if not username or (query and query not in username.casefold()):
            continue
        profile = row[2] if isinstance(row[2], dict) else {}
        if not profile and row[2]:
            try:
                profile = json.loads(row[2])
            except Exception:
                profile = {}
        rows.append({
            "username": username,
            "full_name": clean(profile.get("full_name", "")) if isinstance(profile, dict) else "",
            "is_admin": bool(row[1]),
        })
    total = len(rows)
    start = (page - 1) * page_size
    return {
        "users": rows[start:start + page_size],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": max(1, (total + page_size - 1) // page_size),
        "search": clean(search),
    }


def reserved_user_data_names() -> set[str]:
    return {
        "common",
        "sound",
        "structure",
        "picture",
        "server_log",
        "npc_top",
    }


def list_dashboard_usernames() -> list[str]:
    usernames: set[str] = set(list_registered_users())
    reserved = reserved_user_data_names()
    for root in (USER_ROOT, SERVER_DATA_ROOT, MAIN_SERVER_USER_ROOT):
        try:
            if not root.is_dir():
                continue
            for item in root.iterdir():
                raw_name = item.stem if item.is_file() else item.name
                username = normalize_username(raw_name)
                ok, _message = validate_username(username)
                if not ok or username.lower() in reserved:
                    continue
                if root == USER_ROOT and item.is_file() and not item.name.lower().endswith(".txt"):
                    continue
                if root == USER_ROOT and item.name.startswith("_"):
                    continue
                if root == MAIN_SERVER_USER_ROOT and item.is_dir():
                    identity_path = item / "_user_identity.json"
                    try:
                        identity = json.loads(identity_path.read_text(encoding="utf-8-sig", errors="replace")) if identity_path.is_file() else {}
                        identity_user = normalize_username(identity.get("username", "") if isinstance(identity, dict) else "")
                        if identity_user:
                            username = identity_user
                    except Exception:
                        pass
                usernames.add(username)
        except Exception:
            continue
    return sorted(usernames, key=str.lower)


# Added 2026-07-28: production startup warmup skips benchmark/test users,
# while 18877 benchmark runs can opt them back in explicitly.
def future_warmup_mode() -> str:
    mode = clean(os.environ.get("FUTURE_WARMUP_MODE", "")).lower()
    return mode if mode in {"production", "benchmark", "lazy"} else "production"

def future_include_test_users() -> bool:
    value = clean(os.environ.get("FUTURE_INCLUDE_TEST_USERS", "")).lower()
    return value in {"1", "true", "yes", "on"}

def _future_warmup_env_users() -> set[str]:
    raw = clean(os.environ.get("FUTURE_WARMUP_USERS", ""))
    return {
        normalize_username(item)
        for item in re.split(r"[,;\s]+", raw)
        if normalize_username(item)
    }

def _future_warmup_env_prefixes() -> tuple[str, ...]:
    raw = clean(os.environ.get("FUTURE_WARMUP_USER_PREFIXES", ""))
    return tuple(
        normalize_username(item)
        for item in re.split(r"[,;\s]+", raw)
        if normalize_username(item)
    )


# Added 2026-07-30: bound startup user-cache work so stale account growth
# cannot turn warmup into an unbounded resource consumer.
def future_warmup_max_users() -> int:
    try:
        return max(1, min(100, int(os.environ.get("FUTURE_WARMUP_MAX_USERS", "50") or 50)))
    except Exception:
        return 50

def future_warmup_user_records() -> list[dict]:
    records_reader = globals().get("postgres_list_user_warmup_records")
    if postgres_backend_mode("USER_AUTH_DOCS") == "postgres" and callable(records_reader):
        try:
            rows = records_reader()
            if isinstance(rows, list):
                return [dict(row) for row in rows if isinstance(row, dict) and normalize_username(row.get("username", ""))]
        except Exception:
            pass
    real_users = {normalize_username(item) for item in list_registered_users() if normalize_username(item)}
    dashboard_users = {normalize_username(item) for item in list_dashboard_usernames() if normalize_username(item)}
    return [
        {"username": username, "is_test": username not in real_users, "is_admin": bool(is_admin_user(username))}
        for username in sorted(dashboard_users | real_users, key=natural_sort_key)
    ]

# Added 2026-07-30: rank bounded warmup candidates by numeric activity time;
# legacy states with paths but no timestamp remain eligible at the lowest rank.
def future_user_warmup_activity_epoch(username: str) -> float:
    reader = globals().get("read_lesson_last_file_state")
    if not callable(reader):
        return 1.0
    try:
        state = reader(username)
    except Exception:
        return 0.0
    if not isinstance(state, dict):
        return 0.0
    file_state = state.get("file") if isinstance(state.get("file"), dict) else {}
    selected = state.get("selectedFolder") if isinstance(state.get("selectedFolder"), dict) else {}
    recent = state.get("recentFiles") if isinstance(state.get("recentFiles"), list) else []
    has_activity = bool(
        clean_path_value(file_state.get("path") or file_state.get("effectivePath") or file_state.get("effective_path") or "")
        or clean_path_value(selected.get("path") or "")
        or recent
    )
    if not has_activity:
        return 0.0
    timestamps = [
        state.get("updated_at"), state.get("updatedAt"),
        file_state.get("selected_at"), file_state.get("selectedAt"), file_state.get("updated_at"), file_state.get("updatedAt"),
        selected.get("selected_at"), selected.get("selectedAt"), selected.get("updated_at"), selected.get("updatedAt"),
    ]
    for row in recent:
        if isinstance(row, dict):
            timestamps.extend((row.get("selected_at"), row.get("selectedAt"), row.get("updated_at"), row.get("updatedAt")))
    epochs = [timestamp_to_epoch(value) or 0.0 for value in timestamps if value]
    return max([1.0, *epochs])


def future_user_has_warmup_activity(username: str) -> bool:
    return future_user_warmup_activity_epoch(username) > 0

def select_startup_warmup_usernames(users: object = None, purpose: str = "") -> list[str]:
    mode = future_warmup_mode()
    explicit = {
        normalize_username(item)
        for item in (users if isinstance(users, (list, tuple, set)) else [])
        if normalize_username(item)
    } or _future_warmup_env_users()
    prefixes = _future_warmup_env_prefixes()
    if mode == "lazy" and not explicit:
        return []
    include_test = future_include_test_users()
    selected = []
    for row in future_warmup_user_records():
        username = normalize_username(row.get("username", ""))
        if not username:
            continue
        if explicit and username not in explicit:
            continue
        if prefixes and not any(username.startswith(prefix) for prefix in prefixes):
            continue
        is_test = bool(row.get("is_test"))
        if is_test and not (mode == "benchmark" and include_test and (explicit or prefixes)):
            continue
        activity_epoch = future_user_warmup_activity_epoch(username) if mode == "production" and not explicit else 1.0
        if mode == "production" and not explicit and activity_epoch <= 0:
            continue
        selected.append((username, activity_epoch))
    seen = set()
    result = []
    ordered = sorted(selected, key=lambda item: (-float(item[1] or 0.0), natural_sort_key(item[0])))
    for username, _activity_epoch in ordered:
        key = username.lower()
        if key not in seen:
            seen.add(key)
            result.append(username)
    if not explicit and not prefixes:
        result = result[: future_warmup_max_users()]
    return result

def startup_warmup_selection_summary(selected_users: object = None) -> dict:
    selected = {normalize_username(item) for item in (selected_users or []) if normalize_username(item)}
    records = future_warmup_user_records()
    real_total = sum(1 for row in records if not bool(row.get("is_test")))
    test_total = sum(1 for row in records if bool(row.get("is_test")))
    selected_test = sum(1 for row in records if normalize_username(row.get("username", "")) in selected and bool(row.get("is_test")))
    return {
        "mode": future_warmup_mode(),
        "include_test_users": future_include_test_users(),
        "real_users_total": real_total,
        "test_users_total": test_total,
        "selected_users": len(selected),
        "selected_test_users": selected_test,
        "test_users_skipped": max(0, test_total - selected_test),
    }

def user_data_flags(username: str) -> list[str]:
    username = normalize_username(username)
    flags = []
    try:
        if server_database_user_exists(username):
            flags.append("account")
    except Exception:
        pass
    try:
        if user_folder_path(username).is_dir():
            flags.append("progress")
    except Exception:
        pass
    try:
        if server_data_user_folder_path(username).is_dir():
            flags.append("server-data")
    except Exception:
        pass
    try:
        if any(path.exists() for path in main_vocab_progress_paths(username)):
            flags.append("main-vocab")
    except Exception:
        pass
    try:
        if any(path.exists() for path in main_server_user_dirs(username)):
            flags.append("server-users")
    except Exception:
        pass
    return flags
